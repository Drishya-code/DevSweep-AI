"""API routes for project scanning."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from scanner.detector import (
    analyze_project,
    ProjectAnalysis,
    CleanupCandidate,
    ProjectType,
    RiskLevel,
)
from config import settings
from security.workspace_access import ProjectAccessError, authorize_project_path
from persistence.database import persistence


router = APIRouter(tags=["scanner"])


class ScanRequest(BaseModel):
    path: Optional[str] = None
    access_grant_id: Optional[str] = None
    include_hidden: bool = False
    max_depth: int = 3


class CleanupCandidateResponse(BaseModel):
    path: str
    risk: str
    reason: str
    size_bytes: int
    size_human: str


class ScanResponse(BaseModel):
    scan_id: Optional[str] = None
    project_id: Optional[str] = None
    project_path: str
    access_grant_id: Optional[str] = None
    project_type: str
    framework: str
    package_manager: str
    language: str
    has_git: bool
    git_clean: bool
    cleanup_candidates: List[CleanupCandidateResponse]
    total_recoverable_bytes: int
    total_recoverable_human: str
    protected_paths: List[str]
    notes: str


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


@router.post("/", response_model=ScanResponse)
async def scan_workspace(request: ScanRequest):
    """Scan a workspace for cleanup opportunities."""
    try:
        authorization = authorize_project_path(
            request.path or str(settings.workspace_root),
            request.access_grant_id,
        )
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    scan_path = authorization.canonical_path

    # Perform analysis
    try:
        authorization.revalidate()
        analysis = analyze_project(scan_path)
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    # Convert to response model
    candidates = [
        CleanupCandidateResponse(
            path=c.path,
            risk=c.risk.value,
            reason=c.reason,
            size_bytes=c.size_bytes,
            size_human=format_bytes(c.size_bytes),
        )
        for c in analysis.cleanup_candidates
    ]

    response = ScanResponse(
        project_path=str(scan_path),
        access_grant_id=authorization.grant_id,
        project_type=analysis.project_type.value,
        framework=analysis.framework,
        package_manager=analysis.package_manager,
        language=analysis.language,
        has_git=analysis.has_git,
        git_clean=analysis.git_clean,
        cleanup_candidates=candidates,
        total_recoverable_bytes=analysis.total_recoverable_bytes,
        total_recoverable_human=format_bytes(analysis.total_recoverable_bytes),
        protected_paths=analysis.protected_paths,
        notes=analysis.notes,
    )
    authorization.revalidate()
    project_id, scan_id = await persistence.persist_scan(authorization, response.model_dump(exclude={"scan_id", "project_id", "access_grant_id"}))
    response.scan_id = scan_id
    response.project_id = project_id
    return response


@router.get("/demo", response_model=ScanResponse)
async def scan_demo(access_grant_id: Optional[str] = Query(default=None)):
    """Scan the demo project fixture."""
    demo_path = Path(__file__).parent.parent.parent / "demo-project"
    try:
        authorization = authorize_project_path(str(demo_path), access_grant_id)
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    analysis = analyze_project(authorization.canonical_path)
    authorization.revalidate()

    candidates = [
        CleanupCandidateResponse(
            path=c.path,
            risk=c.risk.value,
            reason=c.reason,
            size_bytes=c.size_bytes,
            size_human=format_bytes(c.size_bytes),
        )
        for c in analysis.cleanup_candidates
    ]

    response = ScanResponse(
        project_path=str(authorization.canonical_path),
        access_grant_id=authorization.grant_id,
        project_type=analysis.project_type.value,
        framework=analysis.framework,
        package_manager=analysis.package_manager,
        language=analysis.language,
        has_git=analysis.has_git,
        git_clean=analysis.git_clean,
        cleanup_candidates=candidates,
        total_recoverable_bytes=analysis.total_recoverable_bytes,
        total_recoverable_human=format_bytes(analysis.total_recoverable_bytes),
        protected_paths=analysis.protected_paths,
        notes=analysis.notes + " (DEMO MODE)",
    )
    authorization.revalidate()
    response.project_id, response.scan_id = await persistence.persist_scan(authorization, response.model_dump(exclude={"scan_id", "project_id", "access_grant_id"}))
    return response


@router.get("/types")
async def get_project_types():
    """Get supported project types."""
    return {
        "types": [pt.value for pt in ProjectType],
        "risk_levels": [rl.value for rl in RiskLevel],
    }


@router.post("/demo/reset")
async def reset_demo(access_grant_id: Optional[str] = Query(default=None)):
    """Regenerate demo project with fresh realistic data."""
    import subprocess
    import sys
    from pathlib import Path
    
    # From backend/scanner/routes.py -> project root is 3 levels up
    script_path = Path(__file__).parent.parent.parent / "generate_demo.py"
    if not script_path.exists():
        # Fallback to cwd
        script_path = Path.cwd() / "generate_demo.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Demo generation script not found")

    demo_path = script_path.parent / "demo-project"
    try:
        authorization = authorize_project_path(str(demo_path), access_grant_id)
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Demo reset failed: {result.stderr}")
    
    return {"success": True, "message": "Demo project regenerated"}
