import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from cleanup.engine import ActionType, CleanupItem, CleanupPlan, RiskLevel
from persistence.database import (
    CleanupPlanItemRecord,
    Base,
    Persistence,
    ProjectRecord,
    ScanRecord,
)
from security.workspace_access import DirectoryIdentity
from config import settings


def auth_for(path: Path):
    stat = path.stat()
    identity = DirectoryIdentity(int(stat.st_dev), int(stat.st_ino), getattr(stat, "st_birthtime_ns", None))
    return SimpleNamespace(canonical_path=path.resolve(), identity=identity)


@pytest.mark.asyncio
async def test_fresh_schema_and_history_survive_reopen(tmp_path):
    db_path = tmp_path / "history.db"
    project = tmp_path / "project"
    project.mkdir()
    auth = auth_for(project)
    first = Persistence(db_path)
    await first.initialize()
    async with first.engine.connect() as connection:
        assert (await connection.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1
    payload = {"project_path": str(project), "project_type": "node", "cleanup_candidates": [], "access_grant_id": "must-not-be-stored", "analysis_id": "also-must-not-be-stored"}
    project_id, scan_id = await first.persist_scan(auth, payload)
    plan = CleanupPlan(items=[CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "Generated output", 32)])
    _, _ = await first.persist_plan(auth, "plan-test", plan, {".env": True}, scan_id)
    async with first.sessions() as session:
        assert (await session.get(ProjectRecord, project_id)) is not None
        assert (await session.get(ScanRecord, scan_id)) is not None
        items = (await session.execute(select(CleanupPlanItemRecord))).scalars().all()
        assert len(items) == 1
        stored_scan = (await session.get(ScanRecord, scan_id)).summary_json
        assert "must-not-be-stored" not in stored_scan
        assert "also-must-not-be-stored" not in stored_scan
        table_names = set((await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).scalars().all())
        assert "external_project_grants" not in table_names
        assert "verified_analyses" not in table_names
    with pytest.raises(IntegrityError):
        async with first.sessions() as session:
            session.add(ScanRecord(id="orphan-scan", project_id="no-such-project", scanned_at="now", status="completed", summary_json="{}"))
            await session.commit()
    await first.close()

    second = Persistence(db_path)
    await second.initialize()
    assert (await second.projects())[0]["project_id"] == project_id
    assert (await second.scans())[0]["scan_id"] == scan_id
    plans = await second.plans()
    assert plans[0]["status"] == "review_only"
    assert plans[0]["can_execute"] is False
    await second.close()


@pytest.mark.asyncio
async def test_existing_database_is_backed_up_before_versioned_migration(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE legacy_records (value TEXT NOT NULL)")
    connection.execute("INSERT INTO legacy_records(value) VALUES ('preserve-me')")
    connection.commit(); connection.close()

    store = Persistence(db_path)
    await store.initialize()
    backups = list(tmp_path.glob("legacy.db.pre-migration-*.bak"))
    assert len(backups) == 1
    backup = sqlite3.connect(f"file:{backups[0].as_posix()}?mode=ro", uri=True)
    assert backup.execute("SELECT value FROM legacy_records").fetchone()[0] == "preserve-me"
    assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    backup.close()
    original = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    assert original.execute("SELECT value FROM legacy_records").fetchone()[0] == "preserve-me"
    assert original.execute("PRAGMA user_version").fetchone()[0] == 2
    original.close()
    await store.close()


@pytest.mark.asyncio
async def test_phase_two_database_is_backed_up_before_phase_three_schema_upgrade(tmp_path):
    db_path = tmp_path / "phase-two.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (1, 'phase-two')")
    connection.execute("CREATE TABLE retained_data (value TEXT NOT NULL)")
    connection.execute("INSERT INTO retained_data(value) VALUES ('keep-history')")
    connection.execute("PRAGMA user_version=1")
    connection.commit(); connection.close()

    store = Persistence(db_path)
    await store.initialize()
    backups = list(tmp_path.glob("phase-two.db.pre-migration-*.bak"))
    assert len(backups) == 1
    backup = sqlite3.connect(f"file:{backups[0].as_posix()}?mode=ro", uri=True)
    assert backup.execute("PRAGMA user_version").fetchone()[0] == 1
    assert backup.execute("SELECT value FROM retained_data").fetchone()[0] == "keep-history"
    backup.close()
    async with store.engine.connect() as connection:
        names = set((await connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")).scalars().all())
        assert "content_backups" in names and "restore_records" in names
        assert (await connection.exec_driver_sql("PRAGMA user_version")).scalar_one() == 2
    await store.close()


@pytest.mark.asyncio
async def test_migration_failure_keeps_original_data_and_verified_backup(tmp_path, monkeypatch):
    db_path = tmp_path / "migration-failure.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE legacy_records (value TEXT NOT NULL)")
    connection.execute("INSERT INTO legacy_records(value) VALUES ('original-intact')")
    connection.commit(); connection.close()

    store = Persistence(db_path)
    def fail_schema_change(*_args, **_kwargs):
        raise RuntimeError("simulated DDL failure")
    monkeypatch.setattr(Base.metadata, "create_all", fail_schema_change)
    with pytest.raises(RuntimeError, match="simulated DDL failure"):
        await store.initialize()
    backup_path = next(tmp_path.glob("migration-failure.db.pre-migration-*.bak"))
    backup = sqlite3.connect(f"file:{backup_path.as_posix()}?mode=ro", uri=True)
    assert backup.execute("SELECT value FROM legacy_records").fetchone()[0] == "original-intact"
    backup.close()
    original = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    assert original.execute("SELECT value FROM legacy_records").fetchone()[0] == "original-intact"
    original.close()
    await store.close()


@pytest.mark.asyncio
async def test_plan_rejects_a_scan_record_from_another_project(tmp_path):
    db_path = tmp_path / "project-match.db"
    first_path = tmp_path / "one"
    second_path = tmp_path / "two"
    first_path.mkdir(); second_path.mkdir()
    store = Persistence(db_path)
    await store.initialize()
    first_auth = auth_for(first_path)
    second_auth = auth_for(second_path)
    _, foreign_scan_id = await store.persist_scan(second_auth, {"project_type": "unknown"})
    plan = CleanupPlan(items=[])
    with pytest.raises(ValueError, match="does not belong"):
        await store.persist_plan(first_auth, "wrong-project-plan", plan, {}, foreign_scan_id)
    assert await store.plans() == []
    await store.close()


@pytest.mark.asyncio
async def test_incompatible_existing_schema_fails_closed_without_modifying_source(tmp_path):
    db_path = tmp_path / "ambiguous.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE projects (id TEXT, display_name TEXT)")
    connection.execute("INSERT INTO projects VALUES ('old', 'keep')")
    connection.commit(); connection.close()

    store = Persistence(db_path)
    with pytest.raises(RuntimeError, match="incompatible schema"):
        await store.initialize()
    original = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    assert original.execute("SELECT * FROM projects").fetchone() == ("old", "keep")
    assert original.execute("PRAGMA user_version").fetchone()[0] == 0
    original.close()


@pytest.mark.asyncio
async def test_restart_marks_unfinished_execution_and_item_unknown_without_retry(tmp_path):
    db_path = tmp_path / "recovery.db"
    project = tmp_path / "project"
    project.mkdir()
    auth = auth_for(project)
    store = Persistence(db_path)
    await store.initialize()
    project_id, scan_id = await store.persist_scan(auth, {"project_type": "unknown"})
    plan = CleanupPlan(items=[CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "Generated", 1)])
    _, ids = await store.persist_plan(auth, "plan-recovery", plan, {}, scan_id)
    await store.create_execution("execution-recovery", "plan-recovery", project_id, 1, 1, True)
    with pytest.raises(IntegrityError):
        await store.create_execution("execution-recovery", "plan-recovery", project_id, 1, 1, True)
    store.record_outcome_sync("execution-recovery", ids[0], "in_progress")
    await store.close()

    restarted = Persistence(db_path)
    await restarted.initialize()
    history = await restarted.executions()
    assert history[0]["status"] == "interrupted"
    assert history[0]["items_unknown"] == 1
    assert history[0]["outcomes"][0]["outcome"] == "unknown"
    assert "No deletion was resumed" in history[0]["error_summary"]
    assert (await restarted.plans())[0]["status"] == "review_only"
    await restarted.close()


@pytest.mark.asyncio
async def test_execution_is_committed_before_delete_and_verification_is_persisted(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import cleanup.routes as cleanup_routes
    from cleanup.routes import ExecuteCleanupRequest
    from security.workspace_access import authorize_project_path
    from tools.filesystem import FilesystemTools

    project = tmp_path / "workspace" / "project"
    target = project / "node_modules"
    target.mkdir(parents=True)
    (target / "module.txt").write_text("temporary fixture", encoding="utf-8")
    (project / "package.json").write_text('{"name":"fixture"}', encoding="utf-8")
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "backups"))
    store = Persistence(tmp_path / "execution.db")
    await store.initialize()
    monkeypatch.setattr(cleanup_routes, "persistence", store)
    authorization = authorize_project_path(str(project))
    candidate = SimpleNamespace(path="node_modules", risk=RiskLevel.SAFE, reason="Generated dependencies", size_bytes=17)
    monkeypatch.setattr(cleanup_routes, "analyze_project", lambda _path: SimpleNamespace(cleanup_candidates=[candidate]))
    plan = CleanupPlan(items=[CleanupItem("node_modules", ActionType.DELETE, RiskLevel.SAFE, "Generated dependencies", 17)])
    project_id, item_ids = await store.persist_plan(authorization, "plan-execution-test", plan, {"package.json": True})
    cleanup_routes._cleanup_plans["plan-execution-test"] = {"plan": plan, "project_path": str(project), "authorization": authorization, "project_id": project_id, "item_ids": item_ids, "execution_id": None}
    cleanup_routes._pre_cleanup_snapshots["plan-execution-test"] = {"package.json": True}

    original_delete = FilesystemTools.delete_path
    def assert_committed_before_delete(fs_tools, item_path):
        connection = sqlite3.connect(f"file:{store.path.as_posix()}?mode=ro", uri=True)
        # The API execution ID is generated at request time; locate its in-progress record.
        execution = connection.execute("SELECT id, status FROM cleanup_executions WHERE plan_id='plan-execution-test'").fetchone()
        assert execution and execution[1] == "in_progress"
        attempt = connection.execute("SELECT outcome FROM execution_outcomes WHERE execution_id=?", (execution[0],)).fetchone()
        assert attempt == ("in_progress",)
        connection.close()
        return original_delete(fs_tools, item_path)

    monkeypatch.setattr(FilesystemTools, "delete_path", assert_committed_before_delete)
    result = await cleanup_routes.execute_cleanup(ExecuteCleanupRequest(plan_id="plan-execution-test", approved=True))
    assert result.status == "completed" and not target.exists()
    verification = await cleanup_routes.verify_project({"project_path": str(project), "plan_id": "plan-execution-test"}, "node")
    assert verification.passed
    history = await store.executions()
    assert history[0]["status"] == "completed"
    assert history[0]["items_deleted"] == 1
    assert history[0]["outcomes"][0]["outcome"] == "completed"
    assert history[0]["outcomes"][0]["verification_status"] == "passed"
    assert "no file contents were backed up" in history[0]["verifications"][0]["summary"]
    cleanup_routes._cleanup_plans.pop("plan-execution-test", None)
    cleanup_routes._pre_cleanup_snapshots.pop("plan-execution-test", None)
    await store.close()
