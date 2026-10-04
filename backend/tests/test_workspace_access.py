import os
import subprocess
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import Settings, settings
from security.workspace_access import (
    ProjectAccessError,
    authorize_project_path,
    create_external_project_grant,
    external_project_grants,
)


@pytest.fixture
def workspace_pair(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "inside-project"
    inside.mkdir()
    external = tmp_path / "external-project"
    external.mkdir()
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setattr(settings, "DEVSWEEP_DB_PATH", str(tmp_path / "devsweep-test.db"))
    external_project_grants.clear()
    yield workspace, inside, external
    external_project_grants.clear()


def test_in_root_project_is_authorized_without_grant(workspace_pair):
    _, inside, _ = workspace_pair
    authorization = authorize_project_path(str(inside))
    assert authorization.canonical_path == inside.resolve()
    assert authorization.grant_id is None


def test_external_project_requires_an_explicit_grant(workspace_pair):
    _, _, external = workspace_pair
    with pytest.raises(ProjectAccessError, match="explicit folder grant"):
        authorize_project_path(str(external))

    grant = create_external_project_grant(str(external))
    authorization = authorize_project_path(str(external), grant.grant_id)
    assert authorization.canonical_path == external.resolve()
    assert authorization.grant_id == grant.grant_id


def test_revoked_grant_no_longer_authorizes_project(workspace_pair):
    _, _, external = workspace_pair
    grant = create_external_project_grant(str(external))
    assert external_project_grants.revoke(grant.grant_id)
    with pytest.raises(ProjectAccessError, match="explicit folder grant"):
        authorize_project_path(str(external), grant.grant_id)


def test_grant_cannot_be_reused_for_another_project(workspace_pair, tmp_path):
    _, _, external = workspace_pair
    other = tmp_path / "other-project"
    other.mkdir()
    grant = create_external_project_grant(str(external))
    with pytest.raises(ProjectAccessError, match="different project"):
        authorize_project_path(str(other), grant.grant_id)


def test_parent_traversal_is_rejected_before_resolution(workspace_pair):
    workspace, _, external = workspace_pair
    traversal = str(workspace / ".." / external.name)
    with pytest.raises(ProjectAccessError, match="traversal"):
        authorize_project_path(traversal)


def test_windows_drive_relative_paths_are_rejected(workspace_pair):
    if os.name != "nt":
        pytest.skip("Windows drive-relative path semantics apply only on Windows.")
    with pytest.raises(ProjectAccessError, match="Drive-relative"):
        authorize_project_path("C:relative-project")


def test_windows_case_variants_resolve_to_the_same_in_root_directory(workspace_pair):
    if os.name != "nt":
        pytest.skip("Windows path casing semantics apply only on Windows.")
    _, inside, _ = workspace_pair
    case_variant = str(inside).swapcase()
    assert authorize_project_path(case_variant).canonical_path == inside.resolve()


def test_replacing_a_granted_directory_invalidates_its_identity(workspace_pair, tmp_path):
    _, _, external = workspace_pair
    moved = tmp_path / "moved-project"
    grant = create_external_project_grant(str(external))
    external.rename(moved)
    external.mkdir()
    with pytest.raises(ProjectAccessError, match="identity changed"):
        authorize_project_path(str(external), grant.grant_id)


def test_symlink_escape_requires_grant_and_replacement_is_rejected(workspace_pair, tmp_path):
    workspace, _, external = workspace_pair
    other = tmp_path / "other-project"
    other.mkdir()
    alias = workspace / "project-link"
    def create_directory_link(target):
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            if os.name != "nt":
                pytest.skip("Symlink creation is unavailable in this environment.")
            junction = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(alias), str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if junction.returncode != 0:
                pytest.skip("Neither symlink nor junction creation is available in this Windows environment.")

    create_directory_link(external)

    with pytest.raises(ProjectAccessError):
        authorize_project_path(str(alias))

    grant = create_external_project_grant(str(external))
    authorize_project_path(str(alias), grant.grant_id)
    if os.name == "nt":
        os.rmdir(alias)
    else:
        alias.unlink()
    create_directory_link(other)
    with pytest.raises(ProjectAccessError, match="different project"):
        authorize_project_path(str(alias), grant.grant_id)


def test_broad_external_locations_are_not_grantable(workspace_pair, tmp_path, monkeypatch):
    workspace, _, _ = workspace_pair
    with pytest.raises(ProjectAccessError, match="include the configured workspace"):
        create_external_project_grant(str(workspace.parent))
    broad_system_dir = tmp_path / "configured-system-dir"
    broad_system_dir.mkdir()
    monkeypatch.setenv("ProgramFiles", str(broad_system_dir))
    with pytest.raises(ProjectAccessError, match="Broad system directories"):
        create_external_project_grant(str(broad_system_dir))


def test_backend_host_defaults_to_loopback_and_rejects_remote_bind():
    assert Settings.model_fields["BACKEND_HOST"].default == "127.0.0.1"
    with pytest.raises(ValidationError, match="Remote binding is disabled"):
        Settings(_env_file=None, BACKEND_HOST="0.0.0.0")
    with pytest.raises(ValidationError, match="local loopback origin"):
        Settings(_env_file=None, FRONTEND_URL="https://example.com")
    assert Settings(_env_file=None, BACKEND_HOST="127.0.0.1").BACKEND_HOST == "127.0.0.1"
    assert Settings(_env_file=None, BACKEND_HOST="::1").BACKEND_HOST == "::1"
    from main import _is_loopback_listener
    assert _is_loopback_listener("127.0.0.1")
    assert _is_loopback_listener("::1")
    assert not _is_loopback_listener("0.0.0.0")
    assert not _is_loopback_listener("192.168.1.20")


def test_routes_reject_ungranted_external_paths_at_sensitive_entry_points(workspace_pair):
    from main import app

    _, _, external = workspace_pair
    client = TestClient(app)
    path = str(external)

    assert client.post("/api/scan", json={"path": path}).status_code == 403
    assert client.post("/api/ai/analyze", json={"project_path": path}).status_code == 403
    assert client.post("/api/ai/chat", json={"message": "summarize", "project_path": path}).status_code == 403
    assert client.post("/api/cleanup/generate-plan", json={"project_path": path}).status_code == 403
    assert client.post("/api/cleanup/plan", json={
        "project_path": path, "analysis_id": "untrusted", "items": [],
    }).status_code == 403
    assert client.post("/api/cleanup/verify", json={"project_path": path}).status_code == 403


def test_grant_endpoint_returns_scoped_token_and_revoke_endpoint_invalidates_it(workspace_pair):
    from main import app

    _, _, external = workspace_pair
    client = TestClient(app)
    grant_response = client.post("/api/access/grants", json={"project_path": str(external)})
    assert grant_response.status_code == 201
    grant = grant_response.json()
    assert grant["project_path"] == str(external.resolve())
    assert grant["expires_in_seconds"] > 0

    scan_response = client.post("/api/scan", json={
        "path": str(external),
        "access_grant_id": grant["grant_id"],
    })
    assert scan_response.status_code == 200
    assert scan_response.json()["access_grant_id"] == grant["grant_id"]

    revoke_response = client.delete(f"/api/access/grants/{grant['grant_id']}")
    assert revoke_response.status_code == 204
    assert client.post("/api/scan", json={
        "path": str(external),
        "access_grant_id": grant["grant_id"],
    }).status_code == 403


def test_revoked_external_project_plan_cannot_execute(workspace_pair):
    from cleanup.engine import ActionType, CleanupItem, CleanupPlan, RiskLevel
    from cleanup.routes import _cleanup_plans
    from main import app

    _, _, external = workspace_pair
    candidate = external / ".nyc_output"
    candidate.mkdir()
    (candidate / "fixture.json").write_text("{}")
    grant = create_external_project_grant(str(external))
    authorization = authorize_project_path(str(external), grant.grant_id)
    plan_id = "phase1-test-plan"
    _cleanup_plans[plan_id] = {
        "plan": CleanupPlan(items=[
            CleanupItem(
                path=".nyc_output",
                action=ActionType.DELETE,
                risk=RiskLevel.SAFE,
                reason="test fixture",
                estimated_bytes=2,
            ),
        ]),
        "project_path": str(external.resolve()),
        "authorization": authorization,
    }
    external_project_grants.revoke(grant.grant_id)
    try:
        response = TestClient(app).post("/api/cleanup/execute", json={
            "plan_id": plan_id,
            "approved": True,
        })
        assert response.status_code == 403
        assert candidate.exists()
    finally:
        _cleanup_plans.pop(plan_id, None)
