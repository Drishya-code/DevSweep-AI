"""Canonical project path authorization and short-lived external project grants."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PureWindowsPath
import secrets
import threading
import time
from typing import Dict, Optional, Tuple

from config import settings


class ProjectAccessError(Exception):
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DirectoryIdentity:
    device: int
    inode: int
    birth_time_ns: Optional[int]


def _identity(path: Path) -> DirectoryIdentity:
    try:
        stat = path.stat()
    except OSError as exc:
        raise ProjectAccessError("Project path is unavailable.", 404) from exc
    if not path.is_dir():
        raise ProjectAccessError("Project path must be a directory.", 400)
    # Windows supplies a file index through st_ino. Refuse filesystems that
    # cannot provide an identity because replacement detection would be weak.
    if not stat.st_ino:
        raise ProjectAccessError("The filesystem cannot establish a stable project identity.")
    birth_time = getattr(stat, "st_birthtime_ns", None)
    if birth_time is None and getattr(stat, "st_birthtime", None) is not None:
        birth_time = int(stat.st_birthtime * 1_000_000_000)
    return DirectoryIdentity(int(stat.st_dev), int(stat.st_ino), birth_time)


def _canonical_directory(raw_path: str) -> tuple[Path, DirectoryIdentity]:
    if not raw_path or "\x00" in raw_path:
        raise ProjectAccessError("A valid project path is required.", 400)
    # Reject traversal syntax before canonicalization, including mixed Windows
    # separators. This avoids accepting ambiguous path spellings.
    if ".." in PureWindowsPath(raw_path.replace("/", "\\")).parts:
        raise ProjectAccessError("Parent-directory traversal is not allowed.", 400)
    windows_path = PureWindowsPath(raw_path)
    if os.name == "nt" and windows_path.drive and not windows_path.root:
        raise ProjectAccessError("Drive-relative Windows paths are not allowed.", 400)
    try:
        candidate = Path(raw_path).expanduser()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProjectAccessError("Project path cannot be resolved safely.", 400) from exc
    if not candidate.is_absolute():
        candidate = settings.workspace_root / candidate
    try:
        canonical = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProjectAccessError("Project path is unavailable or cannot be resolved safely.", 404) from exc
    return canonical, _identity(canonical)


def _canonical_workspace_root() -> Path:
    try:
        root = settings.workspace_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProjectAccessError("Configured workspace root is unavailable.") from exc
    if not root.is_dir():
        raise ProjectAccessError("Configured workspace root is not a directory.")
    return root


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class ProjectAuthorization:
    canonical_path: Path
    identity: DirectoryIdentity
    grant_id: Optional[str] = None

    def revalidate(self) -> "ProjectAuthorization":
        """Re-check path identity, workspace membership and grant revocation."""
        current = authorize_project_path(str(self.canonical_path), self.grant_id)
        if current != self:
            raise ProjectAccessError("Project identity changed after authorization.")
        return current


@dataclass(frozen=True)
class ExternalProjectGrant:
    grant_id: str
    canonical_path: Path
    identity: DirectoryIdentity
    expires_at: float


class InMemoryExternalGrantStore:
    """Replaceable store interface; grants intentionally expire on backend restart."""

    TTL_SECONDS = 60 * 60
    MAX_GRANTS = 256

    def __init__(self):
        self._grants: Dict[str, ExternalProjectGrant] = {}
        self._lock = threading.RLock()

    def create(self, canonical_path: Path, identity: DirectoryIdentity) -> ExternalProjectGrant:
        with self._lock:
            self._purge_expired()
            if len(self._grants) >= self.MAX_GRANTS:
                raise ProjectAccessError("Too many active folder grants. Revoke an existing grant first.", 429)
            grant = ExternalProjectGrant(
                grant_id=secrets.token_urlsafe(32),
                canonical_path=canonical_path,
                identity=identity,
                expires_at=time.monotonic() + self.TTL_SECONDS,
            )
            self._grants[grant.grant_id] = grant
            return grant

    def get(self, grant_id: str) -> Optional[ExternalProjectGrant]:
        with self._lock:
            self._purge_expired()
            return self._grants.get(grant_id)

    def revoke(self, grant_id: str) -> bool:
        with self._lock:
            return self._grants.pop(grant_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._grants.clear()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        for grant_id in [key for key, grant in self._grants.items() if grant.expires_at <= now]:
            self._grants.pop(grant_id, None)


external_project_grants = InMemoryExternalGrantStore()


def create_external_project_grant(raw_path: str) -> ExternalProjectGrant:
    canonical_path, identity = _canonical_directory(raw_path)
    workspace_root = _canonical_workspace_root()
    if _is_relative_to(canonical_path, workspace_root):
        raise ProjectAccessError("This project is already inside the configured workspace.", 409)

    # A grant scopes access to one selected project folder, never a filesystem
    # root, home directory, or ancestor that would implicitly include the
    # configured workspace or unrelated projects.
    anchor = Path(canonical_path.anchor).resolve()
    home = Path.home().resolve()
    if canonical_path == anchor or canonical_path == home or _is_relative_to(home, canonical_path):
        raise ProjectAccessError("Broad filesystem locations cannot be granted; select one project folder.", 400)
    if _is_relative_to(workspace_root, canonical_path):
        raise ProjectAccessError("A grant cannot include the configured workspace or its parent.", 400)
    broad_roots = {
        Path(os.path.abspath(os.path.expanduser(path))).resolve()
        for path in (
            os.getenv("SystemRoot"),
            os.getenv("ProgramFiles"),
            os.getenv("ProgramFiles(x86)"),
            os.getenv("ProgramData"),
            os.getenv("ALLUSERSPROFILE"),
        )
        if path
    }
    try:
        import tempfile
        broad_roots.add(Path(tempfile.gettempdir()).resolve())
    except OSError:
        pass
    if os.name != "nt":
        broad_roots.update(Path(path).resolve() for path in ("/tmp", "/var", "/usr", "/etc", "/opt", "/mnt", "/media"))
    if canonical_path in broad_roots:
        raise ProjectAccessError("Broad system directories cannot be granted; select one project folder.", 400)
    return external_project_grants.create(canonical_path, identity)


def authorize_project_path(raw_path: str, grant_id: Optional[str] = None) -> ProjectAuthorization:
    canonical_path, identity = _canonical_directory(raw_path)
    workspace_root = _canonical_workspace_root()
    if _is_relative_to(canonical_path, workspace_root):
        if grant_id:
            grant = external_project_grants.get(grant_id)
            if not grant or grant.canonical_path != canonical_path:
                raise ProjectAccessError("Folder grant is invalid for this project.")
            # A grant for an external project cannot be reused for an in-root project.
            raise ProjectAccessError("Folder grant is bound to a different project.")
        return ProjectAuthorization(canonical_path, identity)

    grant = external_project_grants.get(grant_id or "")
    if not grant:
        raise ProjectAccessError("Project is outside the configured workspace; an explicit folder grant is required.")
    if grant.canonical_path != canonical_path:
        raise ProjectAccessError("Folder grant is bound to a different project.")
    if grant.identity != identity:
        external_project_grants.revoke(grant.grant_id)
        raise ProjectAccessError("Granted project identity changed. Create a new folder grant.")
    return ProjectAuthorization(canonical_path, identity, grant.grant_id)
