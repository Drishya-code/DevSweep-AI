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
    scanner_risk: Optional[str] = None  # Authoritative deterministic scanner risk
    ai_risk: Optional[str] = None       # AI-assessed risk (can be higher)
    effective_risk: Optional[str] = None # Max of scanner and AI risk (used for approval)
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
    approved: bool = False


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

# In-memory storage for pre-cleanup protected file state (persisted per plan)
_pre_cleanup_snapshots: Dict[str, Dict[str, bool]] = {}


def format_bytes(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def get_effective_risk(item: CleanupItem) -> RiskLevel:
    risk_order = {"SAFE": 0, "CAUTION": 1, "DANGEROUS": 2}
    scanner_val = risk_order.get(item.risk.value, 0)
    if item.ai_risk:
        ai_val = risk_order.get(item.ai_risk.value, 0)
        effective_val = max(scanner_val, ai_val)
    else:
        effective_val = scanner_val
    return RiskLevel(["SAFE", "CAUTION", "DANGEROUS"][effective_val])


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

    # Authoritative scanner validation: re-scan the project to get real scanner risks
    analysis = analyze_project(project_path)
    scanner_candidate_map = {c.path: c for c in analysis.cleanup_candidates}

    # Convert request items to engine items
    items = []
    for item_req in request.items:
        # Re-scan authoritative risk check: client-supplied risk/scanner_risk CANNOT override real scanner
        if item_req.path in scanner_candidate_map:
            authoritative_scanner_risk = scanner_candidate_map[item_req.path].risk.value
        else:
            # Reject unknown paths that are not in authoritative scanner results
            raise HTTPException(
                status_code=400,
                detail=f"Path '{item_req.path}' not found in authoritative scanner results. Only scanner-validated paths may be included in a cleanup plan."
            )

        ai_risk = item_req.ai_risk if item_req.ai_risk else None

        items.append(CleanupItem(
            path=item_req.path,
            action=ActionType(item_req.action),
            risk=RiskLevel(authoritative_scanner_risk),
            reason=item_req.reason,
            estimated_bytes=item_req.estimated_bytes,
            regeneration_command=item_req.regeneration_command,
            ai_risk=RiskLevel(ai_risk) if ai_risk else None,
        ))

    # Create plan - use effective risk for totals and approval
    plan = CleanupPlan(
        items=items,
        total_safe_bytes=sum(i.estimated_bytes for i in items if get_effective_risk(i) == RiskLevel.SAFE and i.action == ActionType.DELETE),
        total_caution_bytes=sum(i.estimated_bytes for i in items if get_effective_risk(i) == RiskLevel.CAUTION and i.action == ActionType.DELETE),
        total_dangerous_bytes=sum(i.estimated_bytes for i in items if get_effective_risk(i) == RiskLevel.DANGEROUS and i.action == ActionType.DELETE),
        requires_approval=any(get_effective_risk(i) == RiskLevel.CAUTION and i.action == ActionType.DELETE for i in items),
        warnings=[],
        verification_steps=["Verify project still builds", "Run tests if available", "Check git status"],
    )

    # Add warnings for CAUTION items (based on effective risk)
    caution_items = [i for i in items if get_effective_risk(i) == RiskLevel.CAUTION and i.action == ActionType.DELETE]
    if caution_items:
        plan.warnings.append(f"{len(caution_items)} CAUTION items require explicit approval")

    # Capture pre-cleanup protected file state
    pre_cleanup_engine = VerificationEngine(project_path)
    pre_cleanup_engine.capture_pre_cleanup_state()
    pre_cleanup_snapshot = pre_cleanup_engine._pre_cleanup_protected

    # Generate plan ID and store
    import uuid
    plan_id = str(uuid.uuid4())[:8]
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(project_path),
    }
    _pre_cleanup_snapshots[plan_id] = pre_cleanup_snapshot

    return CleanupPlanResponse(
        plan_id=plan_id,
        items=[
            CleanupItemRequest(
                path=i.path,
                action=i.action.value,
                risk=i.risk.value,
                scanner_risk=i.risk.value,
                ai_risk=i.ai_risk.value if i.ai_risk else None,
                effective_risk=get_effective_risk(i).value,
                reason=i.reason,
                estimated_bytes=i.estimated_bytes,
                regeneration_command=i.regeneration_command,
            )
            for i in items
        ],
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

    # Get the pre-cleanup snapshot for verification
    pre_cleanup_snapshot = _pre_cleanup_snapshots.get(request.plan_id, {})

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
    plan_id = request.get("plan_id")
    if not project_path:
        raise HTTPException(status_code=422, detail="project_path is required")

    path = Path(project_path).resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")

    engine = VerificationEngine(path)

    # Use pre-cleanup snapshot if plan_id provided
    if plan_id:
        if plan_id not in _pre_cleanup_snapshots:
            raise HTTPException(status_code=404, detail=f"Pre-cleanup snapshot not found for plan {plan_id}. Cannot verify without original snapshot.")
        engine._pre_cleanup_protected = _pre_cleanup_snapshots[plan_id]
    else:
        # Standalone verification without plan_id - capture current state
        engine.capture_pre_cleanup_state()

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
                scanner_risk=i.risk.value,
                ai_risk=i.ai_risk.value if i.ai_risk else None,
                effective_risk=get_effective_risk(i).value,
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
                "risk": c["risk"],  # This is scanner risk
                "ai_risk": c.get("ai_risk"),  # This is AI risk
                "reason": c["reason"],
                "size_bytes": c["size_bytes"],
            }
            for c in analysis.candidates if c["action"] == "DELETE"
        ],
        default_risk_level=RiskLevel(default_risk_level),
    )

    # Capture pre-cleanup protected file state
    pre_cleanup_engine = VerificationEngine(path)
    pre_cleanup_engine.capture_pre_cleanup_state()
    pre_cleanup_snapshot = pre_cleanup_engine._pre_cleanup_protected

    # Store plan
    import uuid
    plan_id = str(uuid.uuid4())[:8]
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(path),
    }
    _pre_cleanup_snapshots[plan_id] = pre_cleanup_snapshot

    return CleanupPlanResponse(
        plan_id=plan_id,
        items=[
            CleanupItemRequest(
                path=i.path,
                action=i.action.value,
                risk=i.risk.value,
                scanner_risk=i.risk.value,
                ai_risk=i.ai_risk.value if i.ai_risk else None,
                effective_risk=get_effective_risk(i).value,
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
