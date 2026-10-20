"""Session-isolated, synthetic hosted demonstration workspaces."""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ai.factory import get_ai_provider
from ai.provider import ChatMessage
from config import settings

router = APIRouter(prefix="/api/demo", tags=["hosted-demo"])
DEMO_ROOT = Path(os.getenv("DEVSWEEP_DEMO_ROOT", str(Path(__file__).resolve().parent.parent / "data" / "demo-workspaces")))
MAX_ITEMS = 20
PREVIEW_TTL = 15 * 60
FIXTURE = {
    ".cache/demo-cache.json": '{"fixture":"synthetic","cache_entries":24}\n',
    "dist/demo.bundle.js": "// Synthetic generated bundle\n" + "/* sample build artifact */\n" * 50,
    "logs/build.log": "[synthetic] build complete\n" * 12,
    "src/app.js": "// Synthetic source file: protected from cleanup\nexport const app = 'demo';\n",
    "README.md": "# Synthetic DevSweep sample\nThis workspace contains safe generated artifacts and protected source.\n",
}

class PathsRequest(BaseModel):
    paths: List[str] = Field(min_length=1, max_length=MAX_ITEMS)

class ConfirmRequest(PathsRequest):
    approved: bool = False
    preview_id: str | None = None

class AnalyzeRequest(BaseModel):
    files: List[dict] = Field(min_length=1, max_length=200)

def _session_id(value: str | None) -> str:
    try:
        return str(uuid.UUID(value or ""))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Start a demo session before continuing.")

def _root(session: str, create: bool = True) -> Path:
    root = DEMO_ROOT.resolve(strict=False)
    target = root / session
    if target.is_symlink():
        raise HTTPException(status_code=503, detail="Demo session storage failed validation.")
    if create:
        target.mkdir(parents=True, exist_ok=True)
        marker = target / ".devsweep-session"
        if not marker.exists():
            for relative, content in FIXTURE.items():
                path = target.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            marker.write_text(str(time.time()), encoding="ascii")
    try:
        target.resolve(strict=True).relative_to(root)
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Demo session storage failed validation.")
    return target

def _safe_file(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative or relative.startswith("/") or ".." in relative.split("/"):
        raise HTTPException(status_code=400, detail="Invalid demo file path.")
    candidate = root.joinpath(*relative.split("/"))
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise HTTPException(status_code=400, detail="Symbolic links are not allowed in the demo workspace.")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="File is outside this demo workspace or unavailable.")
    if not resolved.is_file() or relative.startswith(".trash/") or relative == ".devsweep-session":
        raise HTTPException(status_code=400, detail="Only available workspace files can be selected.")
    return resolved

def _inventory(root: Path):
    result = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise HTTPException(status_code=503, detail="Demo workspace failed symlink validation.")
        if not path.is_file() or path.name == ".devsweep-session" or ".trash" in path.parts or ".pending" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except (OSError, ValueError):
            raise HTTPException(status_code=503, detail="Demo workspace failed path validation.")
        generated = relative in {".cache/demo-cache.json", "dist/demo.bundle.js", "logs/build.log"}
        result.append({"path": relative, "size_bytes": path.stat().st_size, "risk": "SAFE" if generated else "DANGEROUS", "reason": "Synthetic generated artifact; can be recreated." if generated else "Protected sample source or documentation."})
    return sorted(result, key=lambda item: item["path"])

@router.post("/sessions")
async def start_session():
    session = str(uuid.uuid4())
    _root(session)
    return {"session_id": session, "storage": "persistent"}

@router.get("/workspace")
async def workspace(x_devsweep_session: str | None = Header(default=None)):
    root = _root(_session_id(x_devsweep_session))
    return {"name": "Your isolated synthetic sample", "read_only": False, "files": _inventory(root)}

@router.post("/preview")
async def preview(request: PathsRequest, x_devsweep_session: str | None = Header(default=None)):
    root = _root(_session_id(x_devsweep_session))
    known = {item["path"]: item for item in _inventory(root)}
    if len(set(request.paths)) != len(request.paths) or any(path not in known or known[path]["risk"] != "SAFE" for path in request.paths):
        raise HTTPException(status_code=400, detail="Only listed safe generated artifacts can be cleaned.")
    items = []
    for name in request.paths:
        file = _safe_file(root, name)
        items.append({**known[name], "size_bytes": file.stat().st_size})
    preview_id = str(uuid.uuid4())
    pending = root / ".pending"
    if pending.is_symlink():
        raise HTTPException(status_code=503, detail="Demo preview storage failed validation.")
    pending.mkdir(exist_ok=True)
    try:
        pending.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Demo preview storage failed validation.")
    (pending / f"{preview_id}.json").write_text(json.dumps({"created_at": time.time(), "paths": request.paths}), encoding="utf-8")
    return {"preview_id": preview_id, "expires_in_seconds": PREVIEW_TTL, "items": items, "total_bytes": sum(x["size_bytes"] for x in items), "requires_confirmation": True, "will_modify_files": True}

@router.post("/confirm")
async def confirm(request: ConfirmRequest, x_devsweep_session: str | None = Header(default=None)):
    if not request.approved:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    root = _root(_session_id(x_devsweep_session))
    try:
        preview_id = str(uuid.UUID(request.preview_id or ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="Review a cleanup preview before confirming.")
    pending = root / ".pending"
    if pending.is_symlink():
        raise HTTPException(status_code=503, detail="Demo preview storage failed validation.")
    try:
        pending.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Review a cleanup preview before confirming.")
    pending_file = pending / f"{preview_id}.json"
    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="This cleanup preview is unavailable or already used.")
    if time.time() - pending.get("created_at", 0) > PREVIEW_TTL:
        pending_file.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="This cleanup preview expired. Review the files again.")
    if request.paths != pending.get("paths"):
        raise HTTPException(status_code=400, detail="The approved files must match the reviewed preview.")
    allowed = {item["path"] for item in _inventory(root) if item["risk"] == "SAFE"}
    if len(set(request.paths)) != len(request.paths) or any(path not in allowed for path in request.paths):
        raise HTTPException(status_code=400, detail="Only listed safe generated artifacts can be cleaned.")
    trash = root / ".trash" / str(uuid.uuid4())
    moved = []
    for relative in request.paths:
        source = _safe_file(root, relative)
        dest = trash.joinpath(*relative.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, dest)
        moved.append(relative)
    pending_file.unlink(missing_ok=True)
    return {"status": "completed", "items_processed": len(moved), "files_changed": True, "removed_paths": moved, "restore_id": trash.name, "message": f"Moved {len(moved)} synthetic artifact(s) to the private restore area."}

@router.post("/restore/{restore_id}")
async def restore(restore_id: str, x_devsweep_session: str | None = Header(default=None)):
    try:
        uuid.UUID(restore_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid restore identifier.")
    root = _root(_session_id(x_devsweep_session))
    trash = root / ".trash" / restore_id
    if not trash.is_dir() or trash.is_symlink():
        raise HTTPException(status_code=404, detail="Restore data was not found in this session.")
    restored = []
    for path in trash.rglob("*"):
        if path.is_symlink():
            raise HTTPException(status_code=400, detail="Restore data failed validation.")
        if path.is_file():
            relative = path.relative_to(trash)
            dest = root / relative
            if dest.exists():
                raise HTTPException(status_code=409, detail="A restored path now exists. Remove it before restoring.")
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path, dest)
            restored.append(relative.as_posix())
    shutil.rmtree(trash, ignore_errors=True)
    return {"status": "restored", "paths": restored}

@router.post("/reset")
async def reset(x_devsweep_session: str | None = Header(default=None)):
    session = _session_id(x_devsweep_session)
    root = _root(session)
    shutil.rmtree(root)
    _root(session)
    return {"status": "reset", "files": len(FIXTURE)}

@router.post("/analyze")
async def analyze(request: AnalyzeRequest, x_devsweep_session: str | None = Header(default=None)):
    root = _root(_session_id(x_devsweep_session))
    known = {item["path"]: item for item in _inventory(root)}
    for item in request.files:
        relative = item.get("path")
        if (set(item) - {"path", "size_bytes", "risk", "reason"} or not isinstance(relative, str)
                or relative not in known or item.get("size_bytes") != known[relative]["size_bytes"]
                or item.get("risk") != known[relative]["risk"]):
            raise HTTPException(status_code=400, detail="AI analysis accepts only current metadata from this synthetic session.")
    if len({item["path"] for item in request.files}) != len(request.files):
        raise HTTPException(status_code=400, detail="Duplicate file metadata is not allowed.")
    try:
        provider = get_ai_provider()
        response = await provider.chat_completion([
            ChatMessage(role="system", content="You analyze file metadata for a safe cleanup demo. Recommend only generated artifacts explicitly marked SAFE. Never invent paths. Return concise JSON with recommendations array containing path, action, reason."),
            ChatMessage(role="user", content=json.dumps(request.files, ensure_ascii=True)),
        ])
    except Exception as exc:
        name = type(exc).__name__
        code = 503 if not settings.NEBIUS_API_KEY or "Configuration" in name or "credential" in str(exc).lower() else 502
        raise HTTPException(status_code=code, detail="Nebius AI analysis is unavailable. Check server configuration and retry.") from exc
    return {"provider": provider.provider_name, "model": provider.model_name, "analysis": response.content}
