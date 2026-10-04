import asyncio
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from cleanup.engine import ActionType, CleanupEngine, CleanupItem, CleanupPlan, RiskLevel
from config import settings
from main import app
from persistence.backups import BackupError, create_verified_backup, restore_verified_backup, verify_source_matches
from persistence.database import Persistence, project_key
from security.workspace_access import DirectoryIdentity, authorize_project_path


def test_verified_directory_backup_restore_and_no_overwrite(tmp_path, monkeypatch):
    project = tmp_path / "workspace" / "sample"
    project.mkdir(parents=True)
    candidate = project / "dist"
    candidate.mkdir()
    (candidate / "index.html").write_text("original build", encoding="utf-8")
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "appdata" / "backups"))
    saved = create_verified_backup(project, "dist")
    verify_source_matches(project, "dist", saved["entries"])
    shutil.rmtree(candidate)  # Test fixture only; exercise a deleted candidate.
    status = restore_verified_backup(project, "dist", saved, lambda: None)
    assert status == "completed"
    assert (candidate / "index.html").read_text(encoding="utf-8") == "original build"
    (candidate / "index.html").write_text("user change", encoding="utf-8")
    with pytest.raises(FileExistsError):
        restore_verified_backup(project, "dist", saved, lambda: None)
    assert (candidate / "index.html").read_text(encoding="utf-8") == "user change"


def test_backup_refuses_symlink_and_storage_inside_project(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "dist"
    candidate.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("do not follow", encoding="utf-8")
    try:
        (candidate / "linked.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable on this host.")
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "external"))
    with pytest.raises(BackupError, match="symbolic link"):
        create_verified_backup(project, "dist")
    (candidate / "linked.txt").unlink()
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(project / "backups"))
    with pytest.raises(BackupError, match="separate"):
        create_verified_backup(project, "dist")


def test_corrupt_backup_is_never_restored(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "dist"
    candidate.mkdir()
    (candidate / "bundle.js").write_text("original", encoding="utf-8")
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "backups"))
    saved = create_verified_backup(project, "dist")
    shutil.rmtree(candidate)
    (Path(saved["payload_path"]) / "bundle.js").write_text("tampered", encoding="utf-8")
    with pytest.raises(BackupError, match="integrity"):
        restore_verified_backup(project, "dist", saved, lambda: None)
    assert not candidate.exists()


def test_engine_does_not_delete_when_backup_guard_fails(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "node_modules"
    candidate.mkdir()
    (candidate / "pkg.txt").write_text("keep", encoding="utf-8")
    engine = CleanupEngine(project)
    engine.set_scanner_candidates([{"path": "node_modules", "risk": "SAFE", "size_bytes": 4}])
    engine.set_pre_delete_guard(lambda *_: (_ for _ in ()).throw(BackupError("test backup failure")))
    plan = CleanupPlan([CleanupItem("node_modules", ActionType.DELETE, RiskLevel.SAFE, "generated", 4)])
    result = engine.execute_plan(plan, approved=True)
    assert not result.success
    assert result.items_deleted == 0
    assert candidate.exists()
    assert (candidate / "pkg.txt").read_text(encoding="utf-8") == "keep"


def test_filesystem_cleanup_refuses_candidate_symlink(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    link = project / "dist"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable on this host.")
    engine = CleanupEngine(project)
    engine.set_scanner_candidates([{"path": "dist", "risk": "SAFE", "size_bytes": 4}])
    plan = CleanupPlan([CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "generated", 4)])
    result = engine.execute_plan(plan, approved=True)
    assert not result.success
    assert link.is_symlink()
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.asyncio
async def test_backup_history_only_exposes_verified_backups_after_completed_delete(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = Persistence(tmp_path / "history.db")
    await store.initialize()
    stats = project.stat()
    auth = SimpleNamespace(canonical_path=project.resolve(), identity=DirectoryIdentity(stats.st_dev, stats.st_ino, getattr(stats, "st_birthtime_ns", None)))
    project_id, scan_id = await store.persist_scan(auth, {"project_type": "unknown"})
    plan = CleanupPlan([CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "generated", 10)])
    _, items = await store.persist_plan(auth, "plan-backup", plan, {}, scan_id)
    execution_id = "execution-backup"
    await store.create_execution(execution_id, "plan-backup", project_id, 1, 1, True)
    store.record_backup_sync("backup-test", execution_id, items[0], project_id, "dist", str(tmp_path / "backups"), 10, "a" * 64, json.dumps({"format_version": 1, "entry_count": 0, "sha256": "a" * 64}), "verified")
    assert await store.list_recoverable_backups() == []
    store.record_outcome_sync(execution_id, items[0], "completed", bytes_processed=10, complete=True)
    await store.finish_execution(execution_id, "completed", 1, 1, 0, 0, 0, 10, "")
    assert (await store.list_recoverable_backups())[0]["backup_id"] == "backup-test"
    assert (await store.history_summary())["recoverable_backups"] == 1
    await store.close()


def test_restore_api_requires_approval_and_rejects_existing_destination(tmp_path, monkeypatch):
    async def seed(project: Path, store: Persistence, backup):
        stats = project.stat()
        auth = SimpleNamespace(canonical_path=project.resolve(), identity=DirectoryIdentity(stats.st_dev, stats.st_ino, getattr(stats, "st_birthtime_ns", None)))
        project_id, scan_id = await store.persist_scan(auth, {"project_type": "unknown"})
        plan = CleanupPlan([CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "generated", 7)])
        _, item_ids = await store.persist_plan(auth, "plan-api-restore", plan, {}, scan_id)
        await store.create_execution("execution-api-restore", "plan-api-restore", project_id, 1, 1, True)
        store.record_backup_sync(backup["backup_id"], "execution-api-restore", item_ids[0], project_id, "dist", backup["storage_path"], backup["size_bytes"], backup["sha256"], backup["manifest_json"], "verified")
        store.record_outcome_sync("execution-api-restore", item_ids[0], "completed", bytes_processed=backup["size_bytes"], complete=True)
        await store.finish_execution("execution-api-restore", "completed", 1, 1, 0, 0, 0, backup["size_bytes"], "")

    async def setup_case(project: Path, store: Persistence, backup):
        await store.initialize()
        await seed(project, store, backup)

    project = tmp_path / "workspace" / "project"
    project.mkdir(parents=True)
    (project / "dist").mkdir()
    (project / "dist" / "bundle.js").write_text("bundle", encoding="utf-8")
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "appdata" / "backups"))
    auth = authorize_project_path(str(project))
    backup = create_verified_backup(project, "dist", "backup-api-restore", project_key(auth), "execution-api-restore")
    shutil.rmtree(project / "dist")
    store = Persistence(tmp_path / "restore-api.db")
    asyncio.run(setup_case(project, store, backup))
    import cleanup.routes as routes
    monkeypatch.setattr(routes, "persistence", store)
    client = TestClient(app)
    denied = client.post("/api/cleanup/restore", json={"backup_id": backup["backup_id"], "project_path": str(project), "approved": False})
    assert denied.status_code == 400
    response = client.post("/api/cleanup/restore", json={"backup_id": backup["backup_id"], "project_path": str(project), "approved": True})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert (project / "dist" / "bundle.js").read_text(encoding="utf-8") == "bundle"
    conflict = client.post("/api/cleanup/restore", json={"backup_id": backup["backup_id"], "project_path": str(project), "approved": True})
    assert conflict.status_code == 409
    assert (project / "dist" / "bundle.js").read_text(encoding="utf-8") == "bundle"
    asyncio.run(store.close())


def test_cleanup_route_verifies_backup_before_deleting_candidate(tmp_path, monkeypatch):
    project = tmp_path / "workspace" / "sample"
    project.mkdir(parents=True)
    (project / "package.json").write_text('{"name":"sample"}', encoding="utf-8")
    candidate = project / "dist"
    candidate.mkdir()
    (candidate / "index.html").write_text("generated", encoding="utf-8")
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "appdata" / "backups"))
    store = Persistence(tmp_path / "execute-backup.db")
    asyncio.run(store.initialize())
    auth = authorize_project_path(str(project))
    project_id, scan_id = asyncio.run(store.persist_scan(auth, {"project_type": "node"}))
    plan = CleanupPlan([CleanupItem("dist", ActionType.DELETE, RiskLevel.SAFE, "generated output", 9)])
    _, item_ids = asyncio.run(store.persist_plan(auth, "plan-route-backup", plan, {}, scan_id))
    import cleanup.routes as routes
    monkeypatch.setattr(routes, "persistence", store)
    routes._cleanup_plans["plan-route-backup"] = {
        "plan": plan, "project_path": str(project), "authorization": auth,
        "project_id": project_id, "item_ids": item_ids, "execution_id": None,
    }
    routes._pre_cleanup_snapshots["plan-route-backup"] = {}
    try:
        response = TestClient(app).post("/api/cleanup/execute", json={"plan_id": "plan-route-backup", "approved": True})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"
        assert not candidate.exists()
        history = asyncio.run(store.list_recoverable_backups(project_id))
        assert len(history) == 1
        assert history[0]["path"] == "dist"
    finally:
        routes._cleanup_plans.pop("plan-route-backup", None)
        routes._pre_cleanup_snapshots.pop("plan-route-backup", None)
        asyncio.run(store.close())
