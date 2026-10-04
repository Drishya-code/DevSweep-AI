"""Content backup and no-overwrite restoration primitives for cleanup items."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any
from uuid import uuid4

from config import settings

MAX_BACKUP_ENTRIES = 100_000


class BackupError(Exception):
    pass


class PartialRestoreError(BackupError):
    pass


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_relative(raw: str) -> Path:
    normalized = raw.replace("\\", "/")
    windows = PureWindowsPath(normalized)
    if not normalized or normalized.startswith("/") or windows.is_absolute() or windows.drive or any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise BackupError("Cleanup item path is not a safe relative path.")
    return Path(*normalized.split("/"))


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _check_isolated(project_root: Path, backup_root: Path) -> None:
    project = project_root.resolve(strict=True)
    store = backup_root.resolve(strict=False)
    if _within(store, project) or _within(project, store):
        raise BackupError("Backup storage must be separate from the project tree.")


def _entries(source: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def walk(path: Path, relative: str) -> None:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise BackupError("Cleanup item contains a symbolic link or reparse point; backup was refused.")
        if stat.S_ISDIR(info.st_mode):
            result.append({"path": relative, "type": "directory", "size": 0, "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns})
            if len(result) > MAX_BACKUP_ENTRIES:
                raise BackupError(f"Cleanup item exceeds the {MAX_BACKUP_ENTRIES}-entry backup safety limit.")
            with os.scandir(path) as children:
                ordered = sorted(children, key=lambda entry: entry.name.casefold())
                for child in ordered:
                    child_rel = child.name if relative == "." else f"{relative}/{child.name}"
                    walk(path / child.name, child_rel)
        elif stat.S_ISREG(info.st_mode):
            result.append({"path": relative, "type": "file", "size": info.st_size, "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns})
            if len(result) > MAX_BACKUP_ENTRIES:
                raise BackupError(f"Cleanup item exceeds the {MAX_BACKUP_ENTRIES}-entry backup safety limit.")
        else:
            raise BackupError("Cleanup item contains an unsupported filesystem object; backup was refused.")

    walk(source, ".")
    return result


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_hash(entries: list[dict[str, Any]]) -> str:
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_verified_backup(project_root: Path, relative_path: str, backup_id: str | None = None, project_id: str = "", execution_id: str = "") -> dict[str, Any]:
    """Copy one cleanup candidate, reject links, and verify copied bytes before returning."""
    root = project_root.resolve(strict=True)
    relative = _safe_relative(relative_path)
    if len(relative.parts) != 1:
        raise BackupError("Only top-level scanner candidates can be backed up.")
    source = root / relative
    # Resolve the candidate without allowing a link at the candidate itself or in its parents.
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        info = cursor.lstat()
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise BackupError("Cleanup item path includes a symbolic link or reparse point; backup was refused.")
    resolved = source.resolve(strict=True)
    if not _within(resolved, root):
        raise BackupError("Cleanup item resolves outside the authorized project.")

    backup_root = settings.backup_root
    backup_root.mkdir(parents=True, exist_ok=True)
    _check_isolated(root, backup_root)
    entries = _entries(source)
    total = sum(entry["size"] for entry in entries if entry["type"] == "file")
    try:
        free = shutil.disk_usage(backup_root).free
    except OSError as exc:
        raise BackupError("Could not check free space in backup storage; cleanup was refused.") from exc
    if free < total:
        raise BackupError("Insufficient free space for a verified backup; original files were not deleted.")

    backup_id = backup_id or str(uuid4())
    backup_dir = backup_root / backup_id
    backup_dir.mkdir(mode=0o700, exist_ok=False)
    payload = backup_dir / "payload"
    if source.is_dir():
        payload.mkdir()

    try:
        for entry in entries:
            rel = entry["path"]
            destination = payload if rel == "." else payload.joinpath(*rel.split("/"))
            if entry["type"] == "directory":
                destination.mkdir(exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            before = source if rel == "." else source.joinpath(*rel.split("/"))
            before_info = before.lstat()
            if stat.S_ISLNK(before_info.st_mode) or _is_reparse(before_info) or not stat.S_ISREG(before_info.st_mode):
                raise BackupError("A file changed type during backup; cleanup was refused.")
            with before.open("rb") as incoming, destination.open("xb") as outgoing:
                opened = os.fstat(incoming.fileno())
                if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (before_info.st_dev, before_info.st_ino, before_info.st_size, before_info.st_mtime_ns):
                    raise BackupError("A file changed while backup was starting; cleanup was refused.")
                for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                    digest.update(chunk)
                    outgoing.write(chunk)
                outgoing.flush()
                os.fsync(outgoing.fileno())
                after = os.fstat(incoming.fileno())
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (before_info.st_dev, before_info.st_ino, before_info.st_size, before_info.st_mtime_ns):
                raise BackupError("A file changed during backup; cleanup was refused.")
            entry["sha256"] = digest.hexdigest()
            os.chmod(destination, 0o600)
            if _file_hash(destination) != entry["sha256"]:
                raise BackupError("Copied content failed SHA-256 verification; cleanup was refused.")

        if source.is_dir():
            for entry in reversed(entries):
                if entry["type"] == "directory":
                    dest = payload if entry["path"] == "." else payload.joinpath(*entry["path"].split("/"))
                    os.chmod(dest, 0o700)
        verified_entries = _entries(payload)
        by_path = {entry["path"]: entry for entry in entries}
        if [(x["path"], x["type"], x["size"]) for x in verified_entries] != [(x["path"], x["type"], x["size"]) for x in entries]:
            raise BackupError("Backup contents differ from the source manifest; cleanup was refused.")
        for entry in entries:
            if entry["type"] == "file":
                dest = payload.joinpath(*entry["path"].split("/"))
                if _file_hash(dest) != entry.get("sha256"):
                    raise BackupError("Backup integrity verification failed; cleanup was refused.")
        total_hash = _manifest_hash(entries)
        manifest = {
            "format_version": 1, "backup_id": backup_id, "project_id": project_id,
            "execution_id": execution_id, "relative_path": relative_path,
            "created_at": datetime.now(timezone.utc).isoformat(), "size_bytes": total,
            "sha256": total_hash, "entry_count": len(entries), "entries": entries,
        }
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        manifest_path = backup_dir / "manifest.json"
        with manifest_path.open("x", encoding="utf-8", newline="\n") as manifest_file:
            manifest_file.write(manifest_json)
            manifest_file.flush()
            os.fsync(manifest_file.fileno())
        if manifest_path.read_text(encoding="utf-8") != manifest_json:
            raise BackupError("Durable backup manifest failed verification; cleanup was refused.")
        return {"backup_id": backup_id, "execution_id": execution_id, "project_id": project_id, "path": relative_path, "storage_path": str(backup_dir), "payload_path": str(payload), "size_bytes": total, "sha256": total_hash, "entries": entries, "manifest_json": json.dumps({"format_version": 1, "entry_count": len(entries), "sha256": total_hash}, sort_keys=True, separators=(",", ":")), "created_at": manifest["created_at"]}
    except Exception:
        # Keep incomplete data for diagnosis; it is not recorded as recoverable.
        raise


def verify_backup(backup: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    backup_root = settings.backup_root.resolve(strict=True)
    directory = Path(backup["storage_path"]).resolve(strict=True)
    if not _within(directory, backup_root):
        raise BackupError("Backup record points outside configured backup storage.")
    payload = directory / "payload"
    try:
        db_manifest = json.loads(backup["manifest_json"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise BackupError("Backup history manifest is invalid.") from exc
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file() or stat.S_ISLNK(manifest_path.lstat().st_mode) or _is_reparse(manifest_path.lstat()):
        raise BackupError("Durable backup manifest is missing or unsafe.")
    try:
        durable = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("Durable backup manifest is unreadable.") from exc
    if (
        durable.get("backup_id") != backup["backup_id"]
        or durable.get("project_id") != backup["project_id"]
        or durable.get("execution_id") != backup["execution_id"]
        or durable.get("relative_path") != backup["path"]
        or durable.get("size_bytes") != backup["size_bytes"]
        or durable.get("sha256") != backup["sha256"]
        or durable.get("format_version") != 1
        or durable.get("entry_count") != len(durable.get("entries", []))
        or db_manifest.get("format_version") != 1
        or db_manifest.get("entry_count") != durable.get("entry_count")
        or db_manifest.get("sha256") != backup["sha256"]
    ):
        raise BackupError("Durable backup manifest does not match its history record.")
    entries = durable.get("entries")
    if not isinstance(entries, list) or len(entries) != db_manifest.get("entry_count"):
        raise BackupError("Durable backup manifest entries are invalid.")
    actual = _entries(payload)
    expected_shape = [(e["path"], e["type"], e["size"]) for e in entries]
    actual_shape = [(e["path"], e["type"], e["size"]) for e in actual]
    if expected_shape != actual_shape or _manifest_hash(entries) != backup["sha256"]:
        raise BackupError("Backup is missing or its manifest has changed.")
    for entry in entries:
        if entry["type"] == "file":
            file_path = payload.joinpath(*entry["path"].split("/"))
            if _file_hash(file_path) != entry["sha256"]:
                raise BackupError("Backup content failed SHA-256 integrity verification.")
    return payload, entries


def verify_source_matches(project_root: Path, relative_path: str, entries: list[dict[str, Any]]) -> None:
    source = project_root.resolve(strict=True) / _safe_relative(relative_path)
    current = _entries(source)
    if [(x["path"], x["type"], x["size"]) for x in current] != [(x["path"], x["type"], x["size"]) for x in entries]:
        raise BackupError("Original changed after backup; cleanup was refused.")
    for entry in entries:
        if entry["type"] == "file":
            file_path = source if entry["path"] == "." else source.joinpath(*entry["path"].split("/"))
            if _file_hash(file_path) != entry["sha256"]:
                raise BackupError("Original content changed after backup; cleanup was refused.")


def restore_verified_backup(project_root: Path, relative_path: str, backup: dict[str, Any], revalidate: Any) -> str:
    """Restore without overwriting. Directory restores can end partially and are reported as partial."""
    root = project_root.resolve(strict=True)
    rel = _safe_relative(relative_path)
    if len(rel.parts) != 1:
        raise BackupError("Backup path is not a top-level scanner candidate.")
    _check_isolated(root, settings.backup_root)
    payload, entries = verify_backup(backup)
    destination = root / rel
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Restore destination already exists; no files were overwritten.")
    revalidate()
    if len(entries) == 1 and entries[0]["type"] == "file":
        entry = entries[0]
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.parent / f".devsweep-restore-{uuid4().hex}.tmp"
        temporary_created = False
        source = payload
        digest = hashlib.sha256()
        try:
            with source.open("rb") as incoming:
                outgoing = temporary.open("xb")
                temporary_created = True
                with outgoing:
                    for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                        digest.update(chunk)
                        outgoing.write(chunk)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
            if digest.hexdigest() != entry["sha256"]:
                raise BackupError("Staged restore failed integrity verification.")
            os.chmod(temporary, entry["mode"])
            os.utime(temporary, ns=(entry["mtime_ns"], entry["mtime_ns"]))
            revalidate()
            # Hard-link creation is atomic and fails if the destination exists.
            os.link(temporary, destination)
        except FileExistsError:
            raise FileExistsError("Restore destination appeared during restoration; no files were overwritten.")
        except OSError as exc:
            raise BackupError("Filesystem does not support safe no-overwrite file restoration.") from exc
        finally:
            if temporary_created:
                try:
                    temporary.unlink()
                except OSError:
                    pass
        return "completed"

    # Reserve the directory exclusively, then create children with exclusive
    # semantics. A failure is explicitly partial and is never reported complete.
    destination.mkdir(parents=False, exist_ok=False)
    try:
        for entry in entries:
            if entry["path"] == ".":
                continue
            revalidate()
            target = destination.joinpath(*entry["path"].split("/"))
            if entry["type"] == "directory":
                target.mkdir(exist_ok=False)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = payload.joinpath(*entry["path"].split("/"))
                with source.open("rb") as incoming, target.open("xb") as outgoing:
                    for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                        outgoing.write(chunk)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if _file_hash(target) != entry["sha256"]:
                    raise BackupError("Restored file failed integrity verification.")
                os.chmod(target, entry["mode"])
                os.utime(target, ns=(entry["mtime_ns"], entry["mtime_ns"]))
        for entry in reversed(entries):
            if entry["type"] == "directory":
                target = destination if entry["path"] == "." else destination.joinpath(*entry["path"].split("/"))
                os.chmod(target, entry["mode"])
                os.utime(target, ns=(entry["mtime_ns"], entry["mtime_ns"]))
    except Exception as exc:
        raise PartialRestoreError(f"Directory restore was partial at {relative_path}; inspect the destination before retrying ({type(exc).__name__}: {exc}).") from exc
    return "completed"
