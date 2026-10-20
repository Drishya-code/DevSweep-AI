import pytest
from fastapi.testclient import TestClient

from config import settings
import demo_routes


@pytest.fixture
def hosted_client(monkeypatch):
    monkeypatch.setattr(settings, "DEVSWEEP_HOSTED_DEMO", True)
    monkeypatch.setattr(settings, "DEVSWEEP_DEMO_MODE", False)
    return TestClient(__import__("main").app)


def test_hosted_demo_initialization_and_safe_health(hosted_client):
    config = hosted_client.get("/api/config")
    assert config.status_code == 200
    assert config.json() == {"hosted_demo": True, "demo_mode": True}
    health = hosted_client.get("/health")
    assert health.json() == {"status": "healthy"}


def demo_headers(client):
    session = client.post("/api/demo/sessions").json()["session_id"]
    return {"X-DevSweep-Session": session}


def test_demo_sessions_are_isolated_and_cleanup_can_be_undone(hosted_client, monkeypatch, tmp_path):
    monkeypatch.setattr(demo_routes, "DEMO_ROOT", tmp_path / "demo")
    first, second = demo_headers(hosted_client), demo_headers(hosted_client)
    workspace = hosted_client.get("/api/demo/workspace", headers=first)
    assert workspace.status_code == 200
    files = [f for f in workspace.json()["files"] if f["risk"] == "SAFE"]
    assert files and workspace.json()["read_only"] is False
    selected = [files[0]["path"]]
    before = demo_routes._safe_file(demo_routes._root(first["X-DevSweep-Session"]), selected[0]).read_bytes()
    preview = hosted_client.post("/api/demo/preview", json={"paths": selected}, headers=first)
    assert preview.status_code == 200
    assert preview.json()["requires_confirmation"] is True
    assert preview.json()["will_modify_files"] is True
    assert hosted_client.post("/api/demo/confirm", json={"paths": selected, "approved": True}, headers=first).status_code == 400
    result = hosted_client.post("/api/demo/confirm", json={"paths": selected, "preview_id": preview.json()["preview_id"], "approved": True}, headers=first)
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["files_changed"] is True
    assert hosted_client.get("/api/demo/workspace", headers=first).json()["files"] != workspace.json()["files"]
    assert hosted_client.get("/api/demo/workspace", headers=second).json()["files"] == workspace.json()["files"]
    restore = hosted_client.post(f"/api/demo/restore/{result.json()['restore_id']}", headers=first)
    assert restore.status_code == 200
    assert demo_routes._safe_file(demo_routes._root(first["X-DevSweep-Session"]), selected[0]).read_bytes() == before


def test_demo_reset_restores_only_the_callers_fixture(hosted_client, monkeypatch, tmp_path):
    monkeypatch.setattr(demo_routes, "DEMO_ROOT", tmp_path / "demo")
    owner, other = demo_headers(hosted_client), demo_headers(hosted_client)
    path = ".cache/demo-cache.json"
    preview = hosted_client.post("/api/demo/preview", json={"paths": [path]}, headers=owner).json()
    hosted_client.post("/api/demo/confirm", json={"paths": [path], "preview_id": preview["preview_id"], "approved": True}, headers=owner)
    response = hosted_client.post("/api/demo/reset", headers=owner)
    assert response.status_code == 200
    assert path in {item["path"] for item in hosted_client.get("/api/demo/workspace", headers=owner).json()["files"]}
    assert path in {item["path"] for item in hosted_client.get("/api/demo/workspace", headers=other).json()["files"]}


def test_demo_workspace_requires_a_session(hosted_client):
    assert hosted_client.get("/api/demo/workspace").status_code == 401


def test_demo_confirmation_requires_matching_preview(hosted_client, monkeypatch, tmp_path):
    monkeypatch.setattr(demo_routes, "DEMO_ROOT", tmp_path / "demo")
    headers = demo_headers(hosted_client)
    selected = [".cache/demo-cache.json"]
    preview = hosted_client.post("/api/demo/preview", json={"paths": selected}, headers=headers).json()
    mismatch = hosted_client.post("/api/demo/confirm", json={"paths": ["logs/build.log"], "preview_id": preview["preview_id"], "approved": True}, headers=headers)
    assert mismatch.status_code == 400
    success = hosted_client.post("/api/demo/confirm", json={"paths": selected, "preview_id": preview["preview_id"], "approved": True}, headers=headers)
    assert success.status_code == 200
    assert hosted_client.post("/api/demo/confirm", json={"paths": selected, "preview_id": preview["preview_id"], "approved": True}, headers=headers).status_code == 400


@pytest.mark.parametrize("path", ["../README.md", "/etc/passwd", "C:\\Windows\\win.ini", "dist/../../README.md"])
def test_hosted_demo_rejects_traversal_and_absolute_paths(hosted_client, path):
    response = hosted_client.post("/api/demo/preview", json={"paths": [path]}, headers=demo_headers(hosted_client))
    assert response.status_code == 400


def test_hosted_mode_never_allows_general_filesystem_routes(hosted_client, tmp_path):
    response = hosted_client.post("/api/scan/", json={"path": str(tmp_path)})
    assert response.status_code == 404
    assert hosted_client.post("/api/access/grants", json={"project_path": str(tmp_path)}).status_code == 404
    assert hosted_client.get("/api/cleanup/history/projects").status_code == 404


def test_hosted_demo_rejects_symlink_escape(hosted_client, tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    (root / "dist").mkdir(parents=True)
    outside = tmp_path / "outside.js"
    outside.write_text("secret")
    try:
        (root / "dist" / "demo.bundle.js").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation unavailable")
    (root / ".cache").mkdir()
    (root / ".cache" / "demo-cache.json").write_text("{}")
    (root / "logs").mkdir()
    (root / "logs" / "build.log").write_text("demo")
    monkeypatch.setattr(demo_routes, "DEMO_ROOT", root.resolve())
    response = hosted_client.get("/api/demo/workspace")
    assert response.status_code == 503


def test_hosted_demo_rejects_oversized_request(hosted_client):
    response = hosted_client.post("/api/demo/confirm", content=b" " * 32769, headers={**demo_headers(hosted_client), "content-length": "32769"})
    assert response.status_code == 413


def test_missing_nebius_key_fails_clearly(monkeypatch):
    from ai.factory import create_ai_provider
    monkeypatch.setattr(settings, "DEVSWEEP_DEMO_MODE", False)
    monkeypatch.setattr(settings, "NEBIUS_API_KEY", None)
    with pytest.raises(RuntimeError, match="NEBIUS_API_KEY"):
        create_ai_provider()


def test_metadata_inference_reports_missing_credentials_without_mock_fallback(monkeypatch):
    from ai.factory import reset_ai_provider
    monkeypatch.setattr(settings, "DEVSWEEP_HOSTED_DEMO", False)
    monkeypatch.setattr(settings, "NEBIUS_API_KEY", None)
    reset_ai_provider()
    try:
        response = TestClient(__import__("main").app).post("/api/ai/metadata", json={"files": [{"path": "dist", "size_bytes": 42}]})
        assert response.status_code == 503
        assert "Nebius metadata analysis is unavailable" in response.json()["detail"]
    finally:
        reset_ai_provider()
