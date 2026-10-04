"""Versioned SQLite persistence for project and cleanup history."""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, URL, event, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_path: Mapped[str] = mapped_column(Text, nullable=False)
    identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    last_accessed_at: Mapped[str] = mapped_column(String(40), nullable=False)


class ScanRecord(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    scanned_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class CleanupPlanRecord(Base):
    __tablename__ = "cleanup_plans"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    scan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scans.id"), nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="review_only")
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class CleanupPlanItemRecord(Base):
    __tablename__ = "cleanup_plan_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("cleanup_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    scanner_risk: Mapped[str] = mapped_column(String(16), nullable=False)
    ai_risk: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class CleanupExecutionRecord(Base):
    __tablename__ = "cleanup_executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("cleanup_plans.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ended_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    planned_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_unknown: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ExecutionOutcomeRecord(Base):
    __tablename__ = "execution_outcomes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("cleanup_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("cleanup_plan_items.id"), nullable=False, index=True)
    attempted_at: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    error_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bytes_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")


class VerificationRecord(Base):
    __tablename__ = "verification_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cleanup_executions.id"), nullable=True, index=True)
    plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cleanup_plans.id"), nullable=True, index=True)
    verified_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    protected_file_checks_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)


class ProtectedFileMetadataRecord(Base):
    __tablename__ = "protected_file_metadata"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("cleanup_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    existed_before: Mapped[bool] = mapped_column(Boolean, nullable=False)
    captured_at: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BackupRecord(Base):
    __tablename__ = "content_backups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("cleanup_executions.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("cleanup_plan_items.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class RestoreRecord(Base):
    __tablename__ = "restore_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    backup_id: Mapped[str] = mapped_column(ForeignKey("content_backups.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False)
    finished_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity_json(identity: Any) -> str:
    return json.dumps({"device": identity.device, "inode": identity.inode, "birth_time_ns": identity.birth_time_ns}, separators=(",", ":"))


def project_key(authorization: Any) -> str:
    """Identity-scoped ID: replacement at the same path is a different project."""
    import hashlib
    material = f"{authorization.canonical_path}\0{_identity_json(authorization.identity)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def project_name(path: Path) -> str:
    return path.name or str(path)


class Persistence:
    def __init__(self, database_path: Optional[Path] = None):
        configured = database_path or Path(settings.DEVSWEEP_DB_PATH)
        if not configured.is_absolute():
            configured = settings.workspace_root / configured
        self.path = configured.resolve(strict=False)
        self._explicit_path = database_path is not None
        self.engine = None
        self.sessions = None
        self._configured_path = self.path

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._inspect_and_backup_before_migration()
        self.engine = create_async_engine(URL.create("sqlite+aiosqlite", database=str(self.path)), connect_args={"timeout": 10})
        @event.listens_for(self.engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            await conn.run_sync(Base.metadata.create_all)
            for version in (1, 2):
                result = await conn.exec_driver_sql("SELECT version FROM schema_migrations WHERE version = ?", (version,))
                if result.first() is None:
                    await conn.exec_driver_sql("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (version, utc_now()))
            await conn.exec_driver_sql("PRAGMA user_version=2")
        await self.recover_interrupted_executions()

    def _inspect_and_backup_before_migration(self) -> None:
        """Read existing state first; preserve any pre-versioned schema via SQLite backup."""
        try:
            source = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
            integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
            tables = [row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            version = source.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                for table in set(tables).intersection(Base.metadata.tables):
                    required_columns = {column.name for column in Base.metadata.tables[table].columns}
                    existing = {row[1] for row in source.execute(f'PRAGMA table_info("{table}")')}
                    if not required_columns.issubset(existing):
                        source.close()
                        raise RuntimeError(f"Existing SQLite table '{table}' has an incompatible schema; refusing migration.")
            source.close()
        except sqlite3.Error as exc:
            raise RuntimeError("Configured SQLite database cannot be safely inspected; refusing migration.") from exc
        if integrity != "ok":
            raise RuntimeError("Configured SQLite database failed integrity_check; refusing migration.")
        if version > 2:
            raise RuntimeError(f"Database schema version {version} is newer than this application supports.")
        if version < 2:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = self.path.with_name(f"{self.path.name}.pre-migration-{stamp}.bak")
            if backup.exists():
                raise RuntimeError("Migration backup path already exists; refusing to overwrite it.")
            try:
                src = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
                dst = sqlite3.connect(backup)
                src.backup(dst)
                dst.close()
                src.close()
                check = sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)
                ok = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                check.close()
                if not ok:
                    raise RuntimeError("Migration backup did not pass integrity_check.")
            except Exception:
                # Keep any generated backup for inspection; never alter the source.
                raise RuntimeError("Could not verify the required migration backup; refusing migration.")

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.sessions = None

    async def session(self) -> AsyncSession:
        await self.ensure_initialized()
        return self.sessions()

    async def ensure_initialized(self) -> None:
        configured = self.path if self._explicit_path else Path(settings.DEVSWEEP_DB_PATH)
        if not configured.is_absolute(): configured = settings.workspace_root / configured
        configured = configured.resolve(strict=False)
        if self.sessions is None or configured != self.path:
            if self.engine is not None:
                await self.close()
            self.path = configured
            await self.initialize()

    async def recover_interrupted_executions(self) -> None:
        async with self.sessions() as session:
            async with session.begin():
                rows = (await session.execute(select(CleanupExecutionRecord).where(CleanupExecutionRecord.status == "in_progress"))).scalars().all()
                for row in rows:
                    outcomes = (await session.execute(select(ExecutionOutcomeRecord).where(ExecutionOutcomeRecord.execution_id == row.id))).scalars().all()
                    deleted = sum(outcome.outcome == "completed" for outcome in outcomes)
                    failed = sum(outcome.outcome == "failed" for outcome in outcomes)
                    unknown = sum(outcome.outcome == "in_progress" for outcome in outcomes)
                    attempted = len(outcomes)
                    row.status = "interrupted"
                    row.ended_at = utc_now()
                    row.items_processed = attempted
                    row.items_deleted = deleted
                    row.items_failed = failed
                    row.items_unknown = unknown
                    row.items_skipped = max(0, row.approved_candidates - attempted)
                    row.error_summary = "Backend restarted during execution; unfinished item outcomes are unknown. No deletion was resumed."
                await session.execute(
                    update(ExecutionOutcomeRecord)
                    .where(ExecutionOutcomeRecord.outcome == "in_progress")
                    .values(outcome="unknown", completed_at=utc_now(), error_summary="Backend restarted while this item was being processed; final filesystem state is unknown.")
                )
                restores = (await session.execute(select(RestoreRecord).where(RestoreRecord.status == "in_progress"))).scalars().all()
                for restore in restores:
                    restore.status = "interrupted"
                    restore.finished_at = utc_now()
                    restore.summary = "Backend restarted during restoration. Inspect the destination; no restore was resumed."
                # Disk history never carries execution authority across restarts.
                await session.execute(update(CleanupPlanRecord).values(status="review_only"))

    async def persist_scan(self, authorization: Any, payload: dict[str, Any]) -> tuple[str, str]:
        await self.ensure_initialized()
        payload = dict(payload)
        payload.pop("access_grant_id", None)
        payload.pop("analysis_id", None)
        project_id = project_key(authorization)
        now = utc_now()
        scan_id = str(uuid4())
        async with self.sessions() as session:
            async with session.begin():
                project = await session.get(ProjectRecord, project_id)
                if project is None:
                    project = ProjectRecord(id=project_id, canonical_path=str(authorization.canonical_path), identity_json=_identity_json(authorization.identity), display_name=project_name(authorization.canonical_path), project_type=str(payload.get("project_type", "unknown")), created_at=now, last_accessed_at=now)
                    session.add(project)
                else:
                    project.last_accessed_at = now
                    project.project_type = str(payload.get("project_type", project.project_type))
                session.add(ScanRecord(id=scan_id, project_id=project_id, scanned_at=now, status="completed", summary_json=json.dumps(payload, separators=(",", ":"))))
        return project_id, scan_id

    async def persist_plan(self, authorization: Any, plan_id: str, plan: Any, pre_cleanup: dict[str, bool], scan_id: Optional[str] = None) -> tuple[str, dict[int, str]]:
        await self.ensure_initialized()
        project_id = project_key(authorization)
        now = utc_now()
        async with self.sessions() as session:
            async with session.begin():
                project = await session.get(ProjectRecord, project_id)
                if project is None:
                    project = ProjectRecord(id=project_id, canonical_path=str(authorization.canonical_path), identity_json=_identity_json(authorization.identity), display_name=project_name(authorization.canonical_path), project_type="unknown", created_at=now, last_accessed_at=now)
                    session.add(project)
                    await session.flush()
                if scan_id:
                    scan = await session.get(ScanRecord, scan_id)
                    if scan is None or scan.project_id != project_id:
                        raise ValueError("Scan history record does not belong to the authorized project.")
                session.add(CleanupPlanRecord(id=plan_id, project_id=project_id, scan_id=scan_id, created_at=now, status="pending_review", approved=False, summary_json=json.dumps({"total_safe_bytes": plan.total_safe_bytes, "total_caution_bytes": plan.total_caution_bytes, "total_dangerous_bytes": plan.total_dangerous_bytes, "requires_approval": plan.requires_approval, "warnings": plan.warnings, "verification_steps": plan.verification_steps}, separators=(",", ":"))))
                await session.flush()
                item_ids: dict[int, str] = {}
                for index, item in enumerate(plan.items):
                    item_id = str(uuid4())
                    item_ids[index] = item_id
                    session.add(CleanupPlanItemRecord(id=item_id, plan_id=plan_id, relative_path=item.path, action=item.action.value, scanner_risk=item.risk.value, ai_risk=item.ai_risk.value if item.ai_risk else None, reason=item.reason, estimated_bytes=item.estimated_bytes, approval_required=item.action == ActionType.DELETE and (item.risk.value == "CAUTION" or (item.ai_risk and item.ai_risk.value == "CAUTION")), metadata_json=json.dumps({"regeneration_command": item.regeneration_command}, separators=(",", ":"))))
                for path, existed in pre_cleanup.items():
                    session.add(ProtectedFileMetadataRecord(id=str(uuid4()), plan_id=plan_id, relative_path=path, existed_before=bool(existed), captured_at=now, metadata_only=True))
        return project_id, item_ids

    async def create_execution(self, execution_id: str, plan_id: str, project_id: str, planned_items: int, approved_candidates: int, approved: bool) -> None:
        await self.ensure_initialized()
        async with self.sessions() as session:
            async with session.begin():
                session.add(CleanupExecutionRecord(id=execution_id, plan_id=plan_id, project_id=project_id, started_at=utc_now(), status="in_progress", planned_items=planned_items, approved_candidates=approved_candidates))
                plan = await session.get(CleanupPlanRecord, plan_id)
                if plan is not None:
                    plan.approved = approved
                    plan.status = "in_progress"

    async def finish_execution(self, execution_id: str, status: str, processed: int, deleted: int, failed: int, skipped: int, unknown: int, bytes_processed: int, error: str) -> None:
        await self.ensure_initialized()
        async with self.sessions() as session:
            async with session.begin():
                row = await session.get(CleanupExecutionRecord, execution_id)
                if row:
                    row.ended_at = utc_now(); row.status = status; row.items_processed = processed; row.items_deleted = deleted; row.items_failed = failed; row.items_skipped = skipped; row.items_unknown = unknown; row.bytes_processed = bytes_processed; row.error_summary = error[:2000]
                    plan = await session.get(CleanupPlanRecord, row.plan_id)
                    if plan:
                        plan.status = status

    async def persist_verification(self, execution_id: Optional[str], plan_id: Optional[str], result: Any) -> None:
        await self.ensure_initialized()
        checks = result.checks or []
        now = utc_now()
        async with self.sessions() as session:
            async with session.begin():
                session.add(VerificationRecord(id=str(uuid4()), execution_id=execution_id, plan_id=plan_id, verified_at=now, status="passed" if result.passed else "issues_found", protected_file_checks_json=json.dumps(checks, separators=(",", ":")), summary="Protected-path existence and configured project checks only; no file contents were backed up or verified."))
                if execution_id:
                    await session.execute(update(ExecutionOutcomeRecord).where(ExecutionOutcomeRecord.execution_id == execution_id).values(verification_status="passed" if result.passed else "issues_found"))

    async def projects(self) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            rows = (await session.execute(select(ProjectRecord).order_by(ProjectRecord.last_accessed_at.desc()))).scalars().all()
            output = []
            for p in rows:
                latest = (await session.execute(select(ScanRecord).where(ScanRecord.project_id == p.id).order_by(ScanRecord.scanned_at.desc()).limit(1))).scalars().first()
                output.append({"project_id": p.id, "project_path": p.canonical_path, "name": p.display_name, "project_type": p.project_type, "created_at": p.created_at, "last_accessed_at": p.last_accessed_at, "identity": json.loads(p.identity_json), "latest_scan": json.loads(latest.summary_json) if latest else None, "latest_scan_at": latest.scanned_at if latest else None})
            return output

    async def scans(self, limit: int = 100) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            rows = (await session.execute(select(ScanRecord).order_by(ScanRecord.scanned_at.desc()).limit(limit))).scalars().all()
            return [{"scan_id": r.id, "project_id": r.project_id, "scanned_at": r.scanned_at, "status": r.status, "summary": json.loads(r.summary_json)} for r in rows]

    async def plans(self, project_id: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            query = select(CleanupPlanRecord).order_by(CleanupPlanRecord.created_at.desc()).limit(limit)
            if project_id: query = query.where(CleanupPlanRecord.project_id == project_id)
            rows = (await session.execute(query)).scalars().all()
            output = []
            for p in rows:
                items = (await session.execute(select(CleanupPlanItemRecord).where(CleanupPlanItemRecord.plan_id == p.id))).scalars().all()
                output.append({"plan_id": p.id, "project_id": p.project_id, "scan_id": p.scan_id, "created_at": p.created_at, "status": "review_only", "can_execute": False, "summary": json.loads(p.summary_json), "items": [{"item_id": i.id, "path": i.relative_path, "action": i.action, "risk": i.scanner_risk, "ai_risk": i.ai_risk, "reason": i.reason, "estimated_bytes": i.estimated_bytes, "approval_required": i.approval_required, **json.loads(i.metadata_json)} for i in items]} )
            return output

    async def executions(self, limit: int = 100, execution_id: Optional[str] = None) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            query = select(CleanupExecutionRecord).order_by(CleanupExecutionRecord.started_at.desc()).limit(limit)
            if execution_id: query = query.where(CleanupExecutionRecord.id == execution_id)
            rows = (await session.execute(query)).scalars().all()
            output = []
            for r in rows:
                outcomes = (await session.execute(select(ExecutionOutcomeRecord).where(ExecutionOutcomeRecord.execution_id == r.id))).scalars().all()
                verifications = (await session.execute(select(VerificationRecord).where(VerificationRecord.execution_id == r.id).order_by(VerificationRecord.verified_at.desc()))).scalars().all()
                outcome_details = []
                for outcome in outcomes:
                    item = await session.get(CleanupPlanItemRecord, outcome.item_id)
                    outcome_details.append({"item_id": outcome.item_id, "path": item.relative_path if item else "(historical item unavailable)", "action": item.action if item else "unknown", "risk": item.scanner_risk if item else "unknown", "outcome": outcome.outcome, "error_summary": outcome.error_summary, "bytes_processed": outcome.bytes_processed, "verification_status": outcome.verification_status, "attempted_at": outcome.attempted_at, "completed_at": outcome.completed_at})
                output.append({"execution_id": r.id, "plan_id": r.plan_id, "project_id": r.project_id, "started_at": r.started_at, "ended_at": r.ended_at, "status": r.status, "planned_items": r.planned_items, "approved_candidates": r.approved_candidates, "items_processed": r.items_processed, "items_deleted": r.items_deleted, "items_skipped": r.items_skipped, "items_failed": r.items_failed, "items_unknown": r.items_unknown, "bytes_processed": r.bytes_processed, "error_summary": r.error_summary, "outcomes": outcome_details, "verifications": [{"status": v.status, "verified_at": v.verified_at, "checks": json.loads(v.protected_file_checks_json), "summary": v.summary} for v in verifications]})
            return output

    async def history_summary(self) -> dict[str, int]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            async def count(model):
                return int((await session.execute(select(func.count()).select_from(model))).scalar_one())
            backups = int((await session.execute(select(func.count()).select_from(BackupRecord).join(ExecutionOutcomeRecord, (ExecutionOutcomeRecord.execution_id == BackupRecord.execution_id) & (ExecutionOutcomeRecord.item_id == BackupRecord.item_id)).where(BackupRecord.status == "verified", ExecutionOutcomeRecord.outcome == "completed"))).scalar_one())
            return {"projects": await count(ProjectRecord), "scans": await count(ScanRecord), "plans": await count(CleanupPlanRecord), "executions": await count(CleanupExecutionRecord), "recoverable_backups": backups}

    def record_backup_sync(self, backup_id: str, execution_id: str, item_id: str, project_id: str, relative_path: str, storage_path: str, size_bytes: int, sha256: str, manifest_json: str, status: str) -> None:
        """Persist a backup record from the worker thread before deletion proceeds."""
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("INSERT INTO content_backups(id, execution_id, item_id, project_id, relative_path, storage_path, size_bytes, sha256, manifest_json, status, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (backup_id, execution_id, item_id, project_id, relative_path, storage_path, size_bytes, sha256, manifest_json, status, utc_now()))
            conn.commit()
        finally:
            conn.close()

    async def list_recoverable_backups(self, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            query = select(BackupRecord, CleanupExecutionRecord, ExecutionOutcomeRecord).join(CleanupExecutionRecord, BackupRecord.execution_id == CleanupExecutionRecord.id).join(ExecutionOutcomeRecord, (ExecutionOutcomeRecord.execution_id == BackupRecord.execution_id) & (ExecutionOutcomeRecord.item_id == BackupRecord.item_id)).where(BackupRecord.status == "verified", ExecutionOutcomeRecord.outcome == "completed")
            if project_id:
                query = query.where(BackupRecord.project_id == project_id)
            rows = (await session.execute(query.order_by(BackupRecord.created_at.desc()))).all()
            return [{"backup_id": b.id, "execution_id": b.execution_id, "project_id": b.project_id, "path": b.relative_path, "size_bytes": b.size_bytes, "sha256": b.sha256, "entry_count": json.loads(b.manifest_json).get("entry_count", 0), "created_at": b.created_at, "status": b.status, "execution_status": e.status} for b, e, _ in rows]

    async def get_recoverable_backup(self, backup_id: str) -> Optional[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            query = select(BackupRecord, ProjectRecord).join(ProjectRecord, BackupRecord.project_id == ProjectRecord.id).join(ExecutionOutcomeRecord, (ExecutionOutcomeRecord.execution_id == BackupRecord.execution_id) & (ExecutionOutcomeRecord.item_id == BackupRecord.item_id)).where(BackupRecord.id == backup_id, BackupRecord.status == "verified", ExecutionOutcomeRecord.outcome == "completed")
            row = (await session.execute(query)).first()
            if not row:
                return None
            backup, project = row
            return {"backup_id": backup.id, "execution_id": backup.execution_id, "item_id": backup.item_id, "project_id": backup.project_id, "project_path": project.canonical_path, "identity_json": project.identity_json, "path": backup.relative_path, "storage_path": backup.storage_path, "size_bytes": backup.size_bytes, "sha256": backup.sha256, "manifest_json": backup.manifest_json, "created_at": backup.created_at}

    async def create_restore_record(self, restore_id: str, backup_id: str, project_id: str) -> None:
        await self.ensure_initialized()
        async with self.sessions() as session:
            async with session.begin():
                session.add(RestoreRecord(id=restore_id, backup_id=backup_id, project_id=project_id, status="in_progress", started_at=utc_now()))

    async def finish_restore_record(self, restore_id: str, status: str, summary: str) -> None:
        await self.ensure_initialized()
        async with self.sessions() as session:
            async with session.begin():
                record = await session.get(RestoreRecord, restore_id)
                if record:
                    record.status = status
                    record.finished_at = utc_now()
                    record.summary = summary[:2000]

    async def list_restore_records(self, limit: int = 100) -> list[dict[str, Any]]:
        await self.ensure_initialized()
        async with self.sessions() as session:
            rows = (await session.execute(select(RestoreRecord).order_by(RestoreRecord.started_at.desc()).limit(limit))).scalars().all()
            return [{"restore_id": r.id, "backup_id": r.backup_id, "project_id": r.project_id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at, "summary": r.summary} for r in rows]

    def record_outcome_sync(self, execution_id: str, item_id: str, outcome: str, error: str = "", bytes_processed: int = 0, complete: bool = False) -> None:
        """Short transaction invoked around an individual filesystem operation."""
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            now = utc_now()
            row = conn.execute("SELECT id FROM execution_outcomes WHERE execution_id=? AND item_id=?", (execution_id, item_id)).fetchone()
            if row:
                conn.execute("UPDATE execution_outcomes SET completed_at=?, outcome=?, error_summary=?, bytes_processed=? WHERE id=?", (now if complete else None, outcome, error[:1000], bytes_processed, row[0]))
            else:
                conn.execute("INSERT INTO execution_outcomes(id, execution_id, item_id, attempted_at, completed_at, outcome, error_summary, bytes_processed, verification_status) VALUES(?,?,?,?,?,?,?,?,?)", (str(uuid4()), execution_id, item_id, now, now if complete else None, outcome, error[:1000], bytes_processed, "pending"))
            conn.commit()
        finally:
            conn.close()


from cleanup.engine import ActionType  # noqa: E402


persistence = Persistence()
