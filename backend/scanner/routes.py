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


router = APIRouter(tags=["scanner"])


class ScanRequest(BaseModel):
    path: Optional[str] = None
    include_hidden: bool = False
    max_depth: int = 3


class CleanupCandidateResponse(BaseModel):
    path: str
    risk: str
    reason: str
    size_bytes: int
    size_human: str


class ScanResponse(BaseModel):
    project_path: str
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
    # Determine scan path
    if request.path:
        scan_path = Path(request.path).resolve()
    else:
        scan_path = settings.workspace_root

    # Validate path exists and is within workspace
    try:
        scan_path.resolve().relative_to(settings.workspace_root.resolve())
    except ValueError:
        # Allow scanning outside workspace root if explicitly requested
        pass

    if not scan_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {scan_path}")

    if not scan_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {scan_path}")

    # Perform analysis
    analysis = analyze_project(scan_path)

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

    return ScanResponse(
        project_path=str(scan_path),
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


@router.get("/demo", response_model=ScanResponse)
async def scan_demo():
    """Scan the demo project fixture."""
    demo_path = Path(__file__).parent.parent.parent / "demo-project"
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo project not found. Run setup script first.")

    analysis = analyze_project(demo_path)

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

    return ScanResponse(
        project_path=str(demo_path),
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


@router.get("/types")
async def get_project_types():
    """Get supported project types."""
    return {
        "types": [pt.value for pt in ProjectType],
        "risk_levels": [rl.value for rl in RiskLevel],
    }


@router.post("/demo/reset")
async def reset_demo():
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
    
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Demo reset failed: {result.stderr}")
    
    return {"success": True, "message": "Demo project regenerated"}