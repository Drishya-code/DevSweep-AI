import asyncio
import sqlite3

from fastapi.testclient import TestClient

from config import settings
from main import app
from persistence.database import persistence


def test_successful_scan_is_saved_and_history_api_returns_persistent_records(tmp_path, monkeypatch):
    project = tmp_path / "workspace" / "sample"
    project.mkdir(parents=True)
    (project / "package.json").write_text('{"name":"sample","scripts":{"build":"vite build"}}', encoding="utf-8")
    (project / "dist").mkdir()
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setattr(settings, "DEVSWEEP_DB_PATH", str(tmp_path / "history.db"))
    try:
        client = TestClient(app)
        scan = client.post("/api/scan/", json={"path": str(project)})
        assert scan.status_code == 200, scan.text
        payload = scan.json()
        assert payload["scan_id"] and payload["project_id"]

        projects = client.get("/api/cleanup/history/projects")
        scans = client.get("/api/cleanup/history/scans")
        summary = client.get("/api/cleanup/history/summary")
        assert projects.status_code == scans.status_code == summary.status_code == 200
        assert projects.json()["projects"][0]["project_id"] == payload["project_id"]
        assert scans.json()["scans"][0]["scan_id"] == payload["scan_id"]
        assert summary.json()["projects"] == 1
        assert summary.json()["scans"] == 1

        connection = sqlite3.connect(f"file:{(tmp_path / 'history.db').as_posix()}?mode=ro", uri=True)
        stored = connection.execute("SELECT summary_json FROM scans").fetchone()[0]
        assert "access_grant_id" not in stored
        connection.close()
    finally:
        asyncio.run(persistence.close())
