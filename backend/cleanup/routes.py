"""API routes for cleanup operations."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid
import asyncio

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
from security.workspace_access import ProjectAccessError, ProjectAuthorization, authorize_project_path
from persistence.database import persistence, project_key
from persistence.backups import BackupError, PartialRestoreError, create_verified_backup, restore_verified_backup, verify_backup, verify_source_matches
from config import settings
import json


router = APIRouter(tags=["cleanup"])


@router.get("/history/projects")
async def get_project_history():
    """Return project metadata without treating history as filesystem authorization."""
    from persistence.database import project_key
    records = await persistence.projects()
    for record in records:
        record.pop("identity", None)
        path = Path(record["project_path"])
        if not path.exists():
            record["availability"] = "missing"
            continue
        try:
            current = authorize_project_path(str(path))
            record["availability"] = "available" if project_key(current) == record["project_id"] else "identity_changed"
        except ProjectAccessError:
            record["availability"] = "requires_grant"
    return {"projects": records}


@router.get("/history/scans")
async def get_scan_history(limit: int = 100):
    return {"scans": await persistence.scans(max(1, min(limit, 500)))}


@router.get("/history/summary")
async def get_persistent_history_summary():
    return await persistence.history_summary()


@router.get("/history/plans")
async def get_plan_history(project_id: Optional[str] = None, limit: int = 100):
    return {"plans": await persistence.plans(project_id, max(1, min(limit, 500)))}


@router.get("/history/executions")
async def get_execution_history(limit: int = 100):
    return {"executions": await persistence.executions(max(1, min(limit, 500)))}


@router.get("/history/executions/{execution_id}")
async def get_execution_history_detail(execution_id: str):
    rows = await persistence.executions(1, execution_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Cleanup execution history not found")
    return rows[0]


@router.get("/backups")
async def get_recoverable_backups(project_id: Optional[str] = None):
    """List only integrity-verified backups whose cleanup item was recorded deleted."""
    return {"backups": await persistence.list_recoverable_backups(project_id)}


@router.get("/backups/{backup_id}")
async def inspect_recoverable_backup(backup_id: str, offset: int = 0, limit: int = 100):
    backup = await persistence.get_recoverable_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Verified backup for a completed cleanup item was not found.")
    try:
        _, entries = await asyncio.to_thread(verify_backup, backup)
    except BackupError as exc:
        raise HTTPException(status_code=409, detail=f"Backup integrity check failed: {exc}") from exc
    safe_offset = max(0, offset)
    safe_limit = max(1, min(limit, 500))
    return {
        "backup_id": backup["backup_id"], "path": backup["path"],
        "size_bytes": backup["size_bytes"], "sha256": backup["sha256"],
        "entry_count": len(entries), "offset": safe_offset, "limit": safe_limit,
        "entries": entries[safe_offset:safe_offset + safe_limit],
        "has_more": safe_offset + safe_limit < len(entries),
    }


@router.get("/restore/history")
async def get_restore_history(limit: int = 100):
    return {"restores": await persistence.list_restore_records(max(1, min(limit, 500)))}


class RestoreRequest(BaseModel):
    backup_id: str
    project_path: str
    approved: bool = False
    access_grant_id: Optional[str] = None


@router.post("/restore")
async def restore_backup(request: RestoreRequest):
    if not request.approved:
        raise HTTPException(status_code=400, detail="Explicit approval is required to restore this backup.")
    backup = await persistence.get_recoverable_backup(request.backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Verified backup for a completed cleanup item was not found.")
    try:
        authorization = authorize_project_path(request.project_path, request.access_grant_id)
        if authorization.canonical_path != Path(backup["project_path"]).resolve(strict=True) or project_key(authorization) != backup["project_id"]:
            raise ProjectAccessError("Backup belongs to a different project identity.")
        authorization.revalidate()
    except (ProjectAccessError, OSError) as exc:
        status_code = exc.status_code if isinstance(exc, ProjectAccessError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc) if isinstance(exc, ProjectAccessError) else "Backup project is unavailable or changed.") from exc

    restore_id = str(uuid.uuid4())
    await persistence.create_restore_record(restore_id, request.backup_id, backup["project_id"])
    try:
        status = await asyncio.to_thread(restore_verified_backup, authorization.canonical_path, backup["path"], backup, authorization.revalidate)
        summary = "Backup content verified and restored without overwriting existing files." if status == "completed" else "Restore stopped after a partial write. Existing files were not overwritten; inspect the destination before retrying."
        await persistence.finish_restore_record(restore_id, status, summary)
        return {"restore_id": restore_id, "backup_id": request.backup_id, "status": status, "summary": summary}
    except PartialRestoreError as exc:
        await persistence.finish_restore_record(restore_id, "partial", str(exc))
        return {"restore_id": restore_id, "backup_id": request.backup_id, "status": "partial", "summary": str(exc)}
    except FileExistsError as exc:
        await persistence.finish_restore_record(restore_id, "conflict", str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (BackupError, ProjectAccessError, OSError) as exc:
        await persistence.finish_restore_record(restore_id, "failed", str(exc))
        if isinstance(exc, ProjectAccessError):
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=f"Restore failed safely: {exc}") from exc


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
    analysis_id: Optional[str] = None
    approved: bool = False
    scan_id: Optional[str] = None


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
    execution_id: Optional[str] = None
    status: str = "completed"
    success: bool
    items_processed: int
    items_deleted: int
    items_failed: int
    items_skipped: int = 0
    items_unknown: int = 0
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
    # Require a successful Nebius analysis for this exact project. Use server-side
    # analysis data so client-supplied risks/actions cannot replace AI output.
    from ai.routes import take_verified_analysis
    verified = take_verified_analysis(request.analysis_id or "", Path(request.project_path))
    if not verified:
        raise HTTPException(status_code=403, detail="Successful Nebius analysis is required before creating a cleanup plan.")
    authorization: ProjectAuthorization = verified["authorization"]
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    project_path = authorization.canonical_path

    # Authoritative scanner validation: re-scan the project to get real scanner risks
    try:
        analysis = analyze_project(project_path)
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    scanner_candidate_map = {c.path: c for c in analysis.cleanup_candidates}

    verified_candidates = {c["path"]: c for c in verified["candidates"]}
    # The client may select analyzed paths, but risk/action/reason/size come from
    # the server's verified analysis result.
    items = []
    for item_req in request.items:
        ai_candidate = verified_candidates.get(item_req.path)
        if ai_candidate is None:
            raise HTTPException(status_code=400, detail=f"Path '{item_req.path}' was not part of the verified AI analysis.")
        if item_req.path not in scanner_candidate_map:
            raise HTTPException(status_code=400, detail=f"Path '{item_req.path}' not found in authoritative scanner results.")
        if ai_candidate["action"] != "DELETE":
            continue
        # Re-scan authoritative risk check: client-supplied risk/scanner_risk CANNOT override real scanner
        if item_req.path in scanner_candidate_map:
            authoritative_scanner_risk = scanner_candidate_map[item_req.path].risk.value
        else:
            # Reject unknown paths that are not in authoritative scanner results
            raise HTTPException(
                status_code=400,
                detail=f"Path '{item_req.path}' not found in authoritative scanner results. Only scanner-validated paths may be included in a cleanup plan."
            )

        ai_risk = ai_candidate.get("ai_risk")

        items.append(CleanupItem(
            path=item_req.path,
            action=ActionType(ai_candidate["action"]),
            risk=RiskLevel(authoritative_scanner_risk),
            reason=ai_candidate["reason"],
            estimated_bytes=ai_candidate["size_bytes"],
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
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    pre_cleanup_engine = VerificationEngine(project_path)
    pre_cleanup_engine.capture_pre_cleanup_state()
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    pre_cleanup_snapshot = pre_cleanup_engine._pre_cleanup_protected

    # Generate plan ID and store
    plan_id = str(uuid.uuid4())[:8]
    try:
        project_id, item_ids = await persistence.persist_plan(authorization, plan_id, plan, pre_cleanup_snapshot, request.scan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(project_path),
        "authorization": authorization,
        "project_id": project_id,
        "item_ids": item_ids,
        "execution_id": None,
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
    authorization: ProjectAuthorization = plan_data["authorization"]
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    project_path = authorization.canonical_path

    # Get the pre-cleanup snapshot for verification
    pre_cleanup_snapshot = _pre_cleanup_snapshots.get(request.plan_id, {})

    # Get fresh scanner candidates for allowlist validation
    try:
        analysis = analyze_project(project_path)
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
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
    engine.set_authorization_guard(authorization.revalidate)
    execution_id = str(uuid.uuid4())
    delete_items = [item for item in plan.items if item.action == ActionType.DELETE]
    eligible_count = sum(
        get_effective_risk(item) == RiskLevel.SAFE
        or (get_effective_risk(item) == RiskLevel.CAUTION and request.approved)
        for item in delete_items
    )
    await persistence.create_execution(execution_id, request.plan_id, plan_data["project_id"], len(delete_items), eligible_count, request.approved)
    indexes_by_path: Dict[str, List[int]] = {}
    for index, item in enumerate(plan.items):
        if item.action == ActionType.DELETE:
            indexes_by_path.setdefault(item.path, []).append(index)
    cursors: Dict[str, int] = {}
    active_item_ids: Dict[str, str] = {}
    attempted = 0
    deleted = 0
    failed_items = 0

    def record_item(state: str, item_path: str, error: str, byte_count: int) -> None:
        nonlocal attempted, deleted, failed_items
        indexes = indexes_by_path.get(item_path, [])
        if state == "attempt":
            cursor = cursors.get(item_path, 0)
            if cursor >= len(indexes):
                return
            index = indexes[cursor]
            cursors[item_path] = cursor + 1
            item_id = plan_data["item_ids"][index]
            active_item_ids[item_path] = item_id
            attempted += 1
            persistence.record_outcome_sync(execution_id, item_id, "in_progress")
        elif item_path in active_item_ids:
            if state == "completed": deleted += 1
            else: failed_items += 1
            persistence.record_outcome_sync(execution_id, active_item_ids[item_path], state, error, byte_count, complete=True)

    engine.set_execution_recorder(record_item)

    def backup_before_delete(item_path: Path, item: CleanupItem) -> None:
        authorization.revalidate()
        item_id = active_item_ids.get(item.path)
        if not item_id:
            raise BackupError("Cleanup item could not be linked to its execution record.")
        backup_id = str(uuid.uuid4())
        storage_path = str(settings.backup_root / backup_id)
        try:
            saved = create_verified_backup(project_path, item.path, backup_id, plan_data["project_id"], execution_id)
            verify_source_matches(project_path, item.path, saved["entries"])
            authorization.revalidate()
            persistence.record_backup_sync(
                backup_id, execution_id, item_id, plan_data["project_id"], item.path,
                saved["storage_path"], saved["size_bytes"], saved["sha256"],
                saved["manifest_json"], "verified",
            )
        except Exception:
            # A failed/partial artifact is never listed as recoverable. The original
            # remains untouched because the engine will not call delete_path.
            try:
                persistence.record_backup_sync(backup_id, execution_id, item_id, plan_data["project_id"], item.path, storage_path, 0, "0" * 64, "[]", "failed")
            except Exception:
                pass
            raise

    engine.set_pre_delete_guard(backup_before_delete)
    try:
        result = await asyncio.to_thread(engine.execute_plan, plan, request.approved)
        execution_status = "completed" if result.success and deleted == len(delete_items) else "partial" if deleted else "failed"
        skipped = max(0, len(delete_items) - attempted)
        await persistence.finish_execution(execution_id, execution_status, attempted, deleted, failed_items, skipped, 0, result.bytes_freed, "; ".join(result.errors))
    except Exception as exc:
        execution_status = "unknown"
        unknown = max(1, len(delete_items) - attempted)
        await persistence.finish_execution(execution_id, execution_status, attempted, deleted, failed_items, 0, unknown, result.bytes_freed if "result" in locals() else 0, f"Execution raised {type(exc).__name__}; filesystem outcome may be unknown.")
        raise HTTPException(status_code=500, detail="Cleanup execution failed; recorded outcome is unknown.") from exc
    plan_data["execution_id"] = execution_id

    return ExecuteCleanupResponse(
        execution_id=execution_id,
        status=execution_status,
        success=result.success,
        items_processed=result.items_processed,
        items_deleted=result.items_deleted,
        items_failed=result.items_failed,
        items_skipped=max(0, len(delete_items) - attempted),
        items_unknown=0,
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

    plan_data = _cleanup_plans.get(plan_id) if plan_id else None
    if plan_id and not plan_data:
        raise HTTPException(status_code=404, detail="Cleanup plan not found")
    supplied_grant_id = request.get("access_grant_id")
    try:
        authorization = authorize_project_path(project_path, supplied_grant_id)
        if plan_data:
            plan_authorization: ProjectAuthorization = plan_data["authorization"]
            plan_authorization.revalidate()
            if authorization != plan_authorization:
                raise ProjectAccessError("Project authorization does not match the cleanup plan.")
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    path = authorization.canonical_path

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
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    await persistence.persist_verification(plan_data.get("execution_id") if plan_data else None, plan_id, result)

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
    try:
        plan["authorization"].revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

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

    try:
        authorization = authorize_project_path(project_path, request.get("access_grant_id"))
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    # Analyze project with AI
    from ai.routes import ai_analyze
    from ai.routes import AnalyzeRequest

    # Run the AI analysis
    analyze_request = AnalyzeRequest(
        project_path=project_path,
        access_grant_id=request.get("access_grant_id"),
    )
    analysis = await ai_analyze(analyze_request)
    if not analysis.ai_used:
        raise HTTPException(
            status_code=403,
            detail=f"Successful Nebius inference is required to generate a cleanup plan (provider: {analysis.provider_name}).",
        )
    from ai.routes import take_verified_analysis
    verified = take_verified_analysis(analysis.analysis_id or "", authorization)
    if not verified:
        raise HTTPException(status_code=403, detail="Verified Nebius analysis is unavailable or expired.")

    # Generate plan from AI-analyzed candidates
    path = authorization.canonical_path

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
            for c in verified["candidates"] if c["action"] == "DELETE"
        ],
        default_risk_level=RiskLevel(default_risk_level),
    )

    # Capture pre-cleanup protected file state
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    pre_cleanup_engine = VerificationEngine(path)
    pre_cleanup_engine.capture_pre_cleanup_state()
    try:
        authorization.revalidate()
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    pre_cleanup_snapshot = pre_cleanup_engine._pre_cleanup_protected

    # Store plan
    plan_id = str(uuid.uuid4())[:8]
    try:
        project_id, item_ids = await persistence.persist_plan(authorization, plan_id, plan, pre_cleanup_snapshot, request.get("scan_id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _cleanup_plans[plan_id] = {
        "plan": plan,
        "project_path": str(path),
        "authorization": authorization,
        "project_id": project_id,
        "item_ids": item_ids,
        "execution_id": None,
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
