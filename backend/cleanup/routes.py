"""API routes for cleanup operations."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path

from cleanup.engine import (
    CleanupEngine,
    VerificationEngine,
    PlanGenerator,
    CleanupPlan,
    CleanupItem,
    CleanupResult,
    VerificationResult,
    RiskLevel,
    ActionType,
)
from scanner.detector import analyze_project
from config import settings


router = APIRouter(tags=["cleanup"])


class CleanupItemRequest(BaseModel):
    path: str
    action: str  # DELETE or KEEP
    risk: str
    reason: str
    estimated_bytes: int
    regeneration_command: Optional[str] = None


class CleanupPlanRequest(BaseModel):
    items: List[CleanupItemRequest]
    project_path: str
    approved: bool = False


class CleanupPlanResponse(BaseModel):
    plan_id: str
    items: List[CleanupItemRequest]
    total_safe_bytes: int
    total_caution_bytes: int
    total_dangerous_bytes: int
    requires_approval: bool
    warnings: List[str]
    verification_steps: List[str]


class ExecuteCleanupRequest(BaseModel):
    plan_id: str
    approved: bool = True


class ExecuteCleanupResponse(BaseModel):
    success: bool
    items_processed: int
    items_deleted: int
    items_failed: int
    bytes_freed: int
    bytes_freed_human: str
    errors: List[str]
    duration_seconds: float


class VerificationResponse(BaseModel):
    passed: bool
    checks: List[Dict[str, Any]]
    errors: List[str]


# In-memory storage for plans (use database in production)
_cleanup_plans: Dict[str, Dict] = {}


def format_bytes(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


@router.post("/plan", response_model=CleanupPlanResponse)
async def create_cleanup_plan(request: CleanupPlanRequest):
    """Create a cleanup plan from scan results."""
    # Validate project path
    project_path = Path(request.project_path).resolve()
    try:
        project_path.relative_to(settings.workspace_root.resolve())
    except ValueError:
        pass  # Allow explicit paths
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")
    
    # Convert request items to engine items
    items = []
    for item_req in request.items:
        items.append(CleanupItem(
            path=item_req.path,
            action=ActionType(item_req.action),
            risk=RiskLevel(item_req.risk),
            reason=item_req.reason,
            estimated_bytes=item_req.estimated_bytes,
            regeneration_command=item_req.regeneration_command,
        ))
    
    # Create plan
    plan = CleanupPlan(
        items=items,
        total_safe_bytes=sum(i.estimated_bytes for i in items if i.risk == RiskLevel.SAFE and i.action == ActionType.DELETE),
        total_caution_bytes=sum(i.estimated_bytes for i in items if i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE),
        total_dangerous_bytes=sum(i.estimated_bytes for i in items if i.risk == RiskLevel.DANGEROUS and i.action == ActionType.DELETE),
        requires_approval=any(i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE for i in items),
        warnings=[],
        verification_steps=["Verify project still builds", "Run tests if available", "Check git status"],
    )
    
    # Add warnings for CAUTION items
    caution_items = [i for i in items if i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE]
    if caution_items:
        plan.warnings.append(f"{len(caution_items)} CAUTION items require explicit approval")
    
    # Generate plan ID and store
    import uuid
    plan_id = str(uuid.uuid4())[:8]
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(project_path),
    }
    
    return CleanupPlanResponse(
        plan_id=plan_id,
        items=request.items,
        total_safe_bytes=plan.total_safe_bytes,
        total_caution_bytes=plan.total_caution_bytes,
        total_dangerous_bytes=plan.total_dangerous_bytes,
        requires_approval=plan.requires_approval,
        warnings=plan.warnings,
        verification_steps=plan.verification_steps,
    )


@router.post("/execute", response_model=ExecuteCleanupResponse)
async def execute_cleanup(request: ExecuteCleanupRequest):
    """Execute an approved cleanup plan."""
    plan_data = _cleanup_plans.get(request.plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Cleanup plan not found")
    
    plan = plan_data["plan"]
    project_path = Path(plan_data["project_path"])
    
    # Get fresh scanner candidates for allowlist validation
    analysis = analyze_project(project_path)
    scanner_candidates = [
        {
            "path": c.path,
            "risk": c.risk.value,
            "reason": c.reason,
            "size_bytes": c.size_bytes,
        }
        for c in analysis.cleanup_candidates
    ]
    
    engine = CleanupEngine(project_path)
    engine.set_scanner_candidates(scanner_candidates)
    result = engine.execute_plan(plan, approved=request.approved)
    
    return ExecuteCleanupResponse(
        success=result.success,
        items_processed=result.items_processed,
        items_deleted=result.items_deleted,
        items_failed=result.items_failed,
        bytes_freed=result.bytes_freed,
        bytes_freed_human=format_bytes(result.bytes_freed),
        errors=result.errors,
        duration_seconds=result.duration_seconds,
    )


@router.post("/verify", response_model=VerificationResponse)
async def verify_project(request: dict, project_type: str = "unknown"):
    """Verify project health after cleanup."""
    project_path = request.get("project_path")
    if not project_path:
        raise HTTPException(status_code=422, detail="project_path is required")
    
    path = Path(project_path).resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")
    
    engine = VerificationEngine(path)
    result = engine.verify(project_type)
    
    return VerificationResponse(
        passed=result.passed,
        checks=result.checks,
        errors=result.errors,
    )


@router.get("/plan/{plan_id}")
async def get_cleanup_plan(plan_id: str):
    """Get a stored cleanup plan."""
    plan = _cleanup_plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Cleanup plan not found")
    
    return CleanupPlanResponse(
        plan_id=plan_id,
        items=[
            CleanupItemRequest(
                path=i.path,
                action=i.action.value,
                risk=i.risk.value,
                reason=i.reason,
                estimated_bytes=i.estimated_bytes,
                regeneration_command=i.regeneration_command,
            )
            for i in plan.items
        ],
        total_safe_bytes=plan.total_safe_bytes,
        total_caution_bytes=plan.total_caution_bytes,
        total_dangerous_bytes=plan.total_dangerous_bytes,
        requires_approval=plan.requires_approval,
        warnings=plan.warnings,
        verification_steps=plan.verification_steps,
    )


@router.post("/generate-plan")
async def generate_plan_from_scan(request: dict, default_risk_level: str = "SAFE"):
    """Generate a cleanup plan directly from a project scan."""
    project_path = request.get("project_path")
    if not project_path:
        raise HTTPException(status_code=422, detail="project_path is required")
    
    # Analyze project with AI
    from ai.routes import ai_analyze
    from ai.routes import AnalyzeRequest
    
    # Run the AI analysis
    analyze_request = AnalyzeRequest(project_path=project_path)
    analysis = await ai_analyze(analyze_request)
    
    # Generate plan from AI-analyzed candidates
    path = Path(project_path).resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")
    
    generator = PlanGenerator(path)
    plan = generator.generate_plan(
        [
            {
                "path": c["path"],
                "risk": c["risk"],
                "reason": c["reason"],
                "size_bytes": c["size_bytes"],
            }
            for c in analysis.candidates if c["action"] == "DELETE"
        ],
        default_risk_level=RiskLevel(default_risk_level),
    )
    
    # Store plan
    import uuid
    plan_id = str(uuid.uuid4())[:8]
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(path),
    }
    
    return CleanupPlanResponse(
        plan_id=plan_id,
        items=[
            CleanupItemRequest(
                path=i.path,
                action=i.action.value,
                risk=i.risk.value,
                reason=i.reason,
                estimated_bytes=i.estimated_bytes,
                regeneration_command=i.regeneration_command,
            )
            for i in plan.items
        ],
        total_safe_bytes=plan.total_safe_bytes,
        total_caution_bytes=plan.total_caution_bytes,
        total_dangerous_bytes=plan.total_dangerous_bytes,
        requires_approval=plan.requires_approval,
        warnings=plan.warnings,
        verification_steps=plan.verification_steps,
    )