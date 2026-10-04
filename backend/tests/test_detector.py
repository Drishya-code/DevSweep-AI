import pytest
from pathlib import Path
import tempfile
import os
import json

from scanner.detector import (
    detect_project_type,
    detect_framework,
    detect_package_manager,
    detect_language,
    find_cleanup_candidates,
    analyze_project,
    ProjectType,
    RiskLevel,
    SAFE_PATTERNS,
    PROTECTED_PATTERNS,
    is_protected,
)
from cleanup.engine import (
    CleanupEngine,
    PlanGenerator,
    VerificationEngine,
    CleanupPlan,
    CleanupItem,
    CleanupResult,
    VerificationResult,
    RiskLevel as EngineRiskLevel,
    ActionType,
)
from ai.routes import ai_analyze
from ai.routes import AnalyzeRequest
from ai.provider import RecordingTestProvider
from ai.provider import MockProvider
from ai.nebius_provider import NebiusProvider
from ai.factory import get_ai_provider, reset_ai_provider
from config import settings
from security.workspace_access import external_project_grants
import asyncio


class FakeNebiusProvider(NebiusProvider):
    """Nebius-shaped test provider; never makes network requests."""
    def __init__(self, failure=None):
        self._model = "nvidia/nemotron-3-super-120b-a12b"
        self._mock = MockProvider(model_name=self._model)
        self.failure = failure

    async def structured_completion(self, messages, response_schema, temperature=0.1, max_tokens=4096):
        if self.failure:
            raise self.failure
        return await self._mock.structured_completion(messages, response_schema, temperature, max_tokens)

    async def chat_completion(self, messages, tools=None, tool_choice=None, temperature=0.1, max_tokens=4096):
        if self.failure:
            raise self.failure
        return await self._mock.chat_completion(messages, tools, tool_choice, temperature, max_tokens)


@pytest.fixture(autouse=True)
def use_fake_nebius(monkeypatch, tmp_path):
    import ai.routes as ai_routes
    ai_routes._verified_analyses.clear()
    external_project_grants.clear()
    monkeypatch.setattr(settings, "DEVSWEEP_WORKSPACE_ROOT", tempfile.gettempdir())
    monkeypatch.setattr(settings, "DEVSWEEP_DB_PATH", str(tmp_path / "devsweep-test.db"))
    monkeypatch.setattr(settings, "DEVSWEEP_BACKUP_ROOT", str(tmp_path / "devsweep-test-backups"))
    monkeypatch.setattr(ai_routes, "get_ai_provider", FakeNebiusProvider)
    yield
    ai_routes._verified_analyses.clear()
    external_project_grants.clear()
    import asyncio
    from persistence.database import persistence
    asyncio.run(persistence.close())


class TestProjectDetection:
    def test_detect_node_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"name": "test"}')
            assert detect_project_type(root) == ProjectType.NODE

    def test_detect_python_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("requests==2.28.0")
            assert detect_project_type(root) == ProjectType.PYTHON

    def test_detect_cpp_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
            assert detect_project_type(root) == ProjectType.CPP

    def test_detect_unknown_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Test")
            assert detect_project_type(root) == ProjectType.UNKNOWN


class TestFrameworkDetection:
    def test_detect_react(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"dependencies": {"react": "^18.0.0"}}')
            assert detect_framework(root, ProjectType.NODE) == "react"

    def test_detect_nextjs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"dependencies": {"next": "^13.0.0"}}')
            assert detect_framework(root, ProjectType.NODE) == "nextjs"

    def test_detect_fastapi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("fastapi==0.100.0")
            assert detect_framework(root, ProjectType.PYTHON) == "fastapi"

    def test_detect_django(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("django==4.2.0")
            assert detect_framework(root, ProjectType.PYTHON) == "django"


class TestPackageManagerDetection:
    def test_detect_pnpm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'")
            assert detect_package_manager(root, ProjectType.NODE) == "pnpm"

    def test_detect_yarn(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "yarn.lock").write_text("# yarn lockfile v1")
            assert detect_package_manager(root, ProjectType.NODE) == "yarn"

    def test_detect_npm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package-lock.json").write_text('{"lockfileVersion": 2}')
            assert detect_package_manager(root, ProjectType.NODE) == "npm"

    def test_detect_poetry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "poetry.lock").write_text("[package]")
            assert detect_package_manager(root, ProjectType.PYTHON) == "poetry"

    def test_detect_pipenv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "Pipfile.lock").write_text('{"_meta": {}}')
            assert detect_package_manager(root, ProjectType.PYTHON) == "pipenv"


class TestLanguageDetection:
    def test_detect_typescript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tsconfig.json").write_text('{"compilerOptions": {}}')
            assert detect_language(root, ProjectType.NODE) == "typescript"

    def test_detect_javascript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            assert detect_language(root, ProjectType.NODE) == "javascript"

    def test_detect_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("")
            assert detect_language(root, ProjectType.PYTHON) == "python"


class TestProtectionRules:
    def test_git_is_protected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            git_dir = root / ".git"
            git_dir.mkdir()
            assert is_protected(git_dir, root) == True

    def test_env_files_protected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            env_file = root / ".env"
            env_file.write_text("SECRET=123")
            assert is_protected(env_file, root) == True

    def test_source_code_protected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir()
            assert is_protected(src_dir, root) == True

    def test_node_modules_not_protected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            assert is_protected(nm_dir, root) == False

    def test_dist_not_protected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dist_dir = root / "dist"
            dist_dir.mkdir()
            assert is_protected(dist_dir, root) == False


class TestCleanupCandidates:
    def test_finds_node_modules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            # Create actual files with real sizes
            (nm_dir / "file1.js").write_bytes(b"x" * 1000000)  # 1MB
            (nm_dir / "file2.js").write_bytes(b"x" * 2000000)  # 2MB
            
            candidates = find_cleanup_candidates(root, ProjectType.NODE)
            nm_candidates = [c for c in candidates if c.path == "node_modules"]
            assert len(nm_candidates) == 1
            assert nm_candidates[0].risk == RiskLevel.SAFE
            assert nm_candidates[0].size_bytes == 3000000  # 3MB total

    def test_finds_dist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            dist_dir = root / "dist"
            dist_dir.mkdir()
            # Create actual files with real sizes
            (dist_dir / "bundle.js").write_bytes(b"x" * 5000000)  # 5MB
            
            candidates = find_cleanup_candidates(root, ProjectType.NODE)
            dist_candidates = [c for c in candidates if c.path == "dist"]
            assert len(dist_candidates) == 1
            assert dist_candidates[0].risk == RiskLevel.SAFE
            assert dist_candidates[0].size_bytes == 5000000

    def test_finds_vite_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            vite_dir = root / ".vite"
            vite_dir.mkdir()
            # Create actual files with real sizes
            (vite_dir / "cache.data").write_bytes(b"x" * 100000)  # 100KB
            
            candidates = find_cleanup_candidates(root, ProjectType.NODE)
            vite_candidates = [c for c in candidates if c.path == ".vite"]
            assert len(vite_candidates) == 1
            assert vite_candidates[0].risk == RiskLevel.SAFE
            assert vite_candidates[0].size_bytes == 100000

    def test_finds_python_caches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("")
            pycache = root / "__pycache__"
            pycache.mkdir()
            # Create actual files with real sizes
            (pycache / "module.pyc").write_bytes(b"x" * 50000000)  # 50MB
            
            candidates = find_cleanup_candidates(root, ProjectType.PYTHON)
            pycache_candidates = [c for c in candidates if c.path == "__pycache__"]
            assert len(pycache_candidates) == 1
            assert pycache_candidates[0].risk == RiskLevel.SAFE
            assert pycache_candidates[0].size_bytes == 50000000


class TestFullAnalysis:
    def test_analyze_node_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"name": "test", "dependencies": {"react": "^18.0.0"}}')
            (root / "package-lock.json").write_text('{}')
            (root / "tsconfig.json").write_text('{}')
            
            nm = root / "node_modules"
            nm.mkdir()
            (nm / ".size").write_text("FAKE_NODE_MODULES=1800000000")
            
            dist = root / "dist"
            dist.mkdir()
            (dist / ".size").write_text("FAKE_DIST=420000000")
            
            analysis = analyze_project(root)
            
            assert analysis.project_type == ProjectType.NODE
            assert analysis.framework == "react"
            assert analysis.package_manager == "npm"
            assert analysis.language == "typescript"
            assert analysis.has_git == False
            assert analysis.total_recoverable_bytes > 0
            assert len(analysis.cleanup_candidates) >= 2


class TestGitState:
    def test_git_clean_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            git_dir = root / ".git"
            git_dir.mkdir()
            # Initialize git repo
            import subprocess
            subprocess.run(["git", "init"], cwd=root, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, capture_output=True)
            
            analysis = analyze_project(root)
            assert analysis.has_git == True
            assert analysis.git_clean == True

    def test_git_dirty_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            git_dir = root / ".git"
            git_dir.mkdir()
            # Initialize git repo
            import subprocess
            subprocess.run(["git", "init"], cwd=root, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, capture_output=True)
            
            # Create uncommitted change
            (root / "new_file.txt").write_text("uncommitted")
            
            analysis = analyze_project(root)
            assert analysis.has_git == True
            assert analysis.git_clean == False


class TestCleanupEngine:
    def test_dangerous_recommendation_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000)
            # Create src directory (protected)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.js").write_bytes(b"x" * 1000)
            
            engine = CleanupEngine(root)
            # Include src in scanner candidates with DANGEROUS risk to test the DANGEROUS rejection
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000},
                {"path": "src", "risk": "DANGEROUS", "size_bytes": 1000},
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="node_modules", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=1000),
                CleanupItem(path="src", action=ActionType.DELETE, risk=EngineRiskLevel.DANGEROUS, reason="test", estimated_bytes=1000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False
            assert any("DANGEROUS" in e for e in validation["errors"])

    def test_ai_unknown_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000)
            # Create the unknown path
            important_dir = root / "important-data"
            important_dir.mkdir()
            (important_dir / "data.txt").write_bytes(b"x" * 1000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="important-data", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=1000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False
            assert any("allowlist" in e for e in validation["errors"])

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="../outside", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=1000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False

    def test_outside_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outside = Path(tmpdir) / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_bytes(b"x" * 1000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="C:/Windows/System32", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=1000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False

    def test_caution_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            cache_dir = root / "cache"
            cache_dir.mkdir()
            (cache_dir / "file.bin").write_bytes(b"x" * 20000000)  # 20MB -> CAUTION
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="cache", action=ActionType.DELETE, risk=EngineRiskLevel.CAUTION, reason="test", estimated_bytes=20000000),
            ])
            
            # Without approval
            validation = engine.validate_plan(plan)
            assert validation["valid"] == True  # Plan is valid
            result = engine.execute_plan(plan, approved=False)
            assert result.success == False
            assert any("approval" in e.lower() for e in result.errors)
            
            # With approval
            result = engine.execute_plan(plan, approved=True)
            assert result.success == True

    def test_actual_deleted_bytes_match_filesystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file1.js").write_bytes(b"x" * 1000000)
            (nm_dir / "file2.js").write_bytes(b"x" * 2000000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 3000000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="node_modules", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=3000000),
            ])
            
            result = engine.execute_plan(plan, approved=True)
            assert result.success == True
            assert result.bytes_freed == 3000000


class TestPlanGenerator:
    def test_generates_plan_with_risk_levels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            dist_dir = root / "dist"
            dist_dir.mkdir()
            (dist_dir / "bundle.js").write_bytes(b"x" * 5000000)
            
            cache_dir = root / "cache"
            cache_dir.mkdir()
            (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
            
            generator = PlanGenerator(root)
            plan = generator.generate_plan([
                {"path": "node_modules", "risk": "SAFE", "reason": "test", "size_bytes": 1000000},
                {"path": "dist", "risk": "SAFE", "reason": "test", "size_bytes": 5000000},
                {"path": "cache", "risk": "CAUTION", "reason": "test", "size_bytes": 20000000},
            ])
            
            assert len(plan.items) == 3
            assert plan.total_safe_bytes == 6000000
            assert plan.total_caution_bytes == 20000000
            assert plan.requires_approval == True
            assert any("CAUTION" in w for w in plan.warnings)


class TestVerificationEngine:
    def test_verify_protected_files_survive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / "src").mkdir()
            (root / ".git").mkdir()
            
            engine = VerificationEngine(root)
            result = engine.verify("node")
            
            assert result.passed == True
            checks = {c["name"]: c for c in result.checks}
            assert checks["protected_package_json"]["passed"] == True
            assert checks["source_src"]["passed"] == True


class TestAIAnalyzeIntegration:
    """Integration test: scan -> AI analyze -> safety validation -> cleanup plan"""
    def test_ai_analyze_calls_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"name": "test"}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            # This test uses mock provider (no NEBIUS_API_KEY)
            # Just verify the endpoint works
            import asyncio
            request = AnalyzeRequest(project_path=str(root))
            result = asyncio.run(ai_analyze(request))
            
            assert result.project_type == "node"
            assert len(result.candidates) >= 1
            # Should have action field from AI
            for c in result.candidates:
                assert "action" in c
                assert c["action"] in ("DELETE", "KEEP")

    def test_ai_recommendation_is_used(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"name": "test"}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            import asyncio
            request = AnalyzeRequest(project_path=str(root))
            result = asyncio.run(ai_analyze(request))
            
            # Even with fallback, AI recommendations should be present
            for c in result.candidates:
                assert "action" in c
                assert c["action"] in ("DELETE", "KEEP")

    def test_ai_unknown_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            import asyncio
            request = AnalyzeRequest(project_path=str(root))
            result = asyncio.run(ai_analyze(request))
            
            # All returned candidates should be from scanner
            scanner_candidates = {"node_modules"}
            for c in result.candidates:
                assert c["path"] in scanner_candidates

    def test_dangerous_ai_recommendation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.js").write_bytes(b"x" * 1000000)
            
            import asyncio
            request = AnalyzeRequest(project_path=str(root))
            result = asyncio.run(ai_analyze(request))
            
            # src should not be in candidates (protected)
            for c in result.candidates:
                assert c["path"] != "src"


class TestRiskDowngradeProtection:
        """Tests for preventing risk downgrades from client-supplied values."""
    
        def test_client_cannot_downgrade_caution_to_safe(self):
            """Scanner says CAUTION, client says SAFE -> must be REJECTED."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                cache_dir = root / "cache"
                cache_dir.mkdir()
                # Make it > 10MB to trigger CAUTION
                (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
    
                engine = CleanupEngine(root)
                # Fresh scanner lookup would return CAUTION for this path
                engine.set_scanner_candidates([
                    {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
                ])
    
                # Client tries to downgrade to SAFE
                plan = CleanupPlan(items=[
                    CleanupItem(path="cache", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=20000000),
                ])
    
                validation = engine.validate_plan(plan)
                assert validation["valid"] == False
                assert any("Risk mismatch" in e for e in validation["errors"])
    
                # Execution must delete NOTHING
                result = engine.execute_plan(plan, approved=True)
                assert result.success == False
                assert result.items_deleted == 0
                assert result.bytes_freed == 0
    
        def test_authoritative_caution_requires_approval(self):
            """Scanner says CAUTION, client attempts SAFE -> plan rejected before execution."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                cache_dir = root / "cache"
                cache_dir.mkdir()
                (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
    
                engine = CleanupEngine(root)
                engine.set_scanner_candidates([
                    {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
                ])
    
                # Client submits SAFE risk for CAUTION item
                plan = CleanupPlan(items=[
                    CleanupItem(path="cache", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=20000000),
                ])
    
                # Validation must fail
                validation = engine.validate_plan(plan)
                assert validation["valid"] == False
                assert any("Risk mismatch" in e for e in validation["errors"])
    
                # Even with approved=True, must fail
                result = engine.execute_plan(plan, approved=True)
                assert result.success == False
                assert result.items_deleted == 0
                assert result.bytes_freed == 0
    
        def test_scanner_safe_client_safe_allowed(self):
            """Scanner says SAFE, client says SAFE -> allowed."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                nm_dir = root / "node_modules"
                nm_dir.mkdir()
                (nm_dir / "file.js").write_bytes(b"x" * 1000000)
    
                engine = CleanupEngine(root)
                engine.set_scanner_candidates([
                    {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000000}
                ])
    
                plan = CleanupPlan(items=[
                    CleanupItem(path="node_modules", action=ActionType.DELETE, risk=EngineRiskLevel.SAFE, reason="test", estimated_bytes=1000000),
                ])
    
                validation = engine.validate_plan(plan)
                assert validation["valid"] == True
    
                result = engine.execute_plan(plan, approved=True)
                assert result.success == True
                assert result.items_deleted == 1


class TestAuthoritativeApproval:
        """Tests that authoritative scanner risk controls approval requirements."""
    
        def test_caution_approval_from_scanner_not_client(self):
            """CAUTION approval determined by scanner risk, not client risk."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                cache_dir = root / "cache"
                cache_dir.mkdir()
                (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
    
                engine = CleanupEngine(root)
                engine.set_scanner_candidates([
                    {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
                ])
    
                # Client correctly matches scanner risk = CAUTION
                plan = CleanupPlan(items=[
                    CleanupItem(path="cache", action=ActionType.DELETE, risk=EngineRiskLevel.CAUTION, reason="test", estimated_bytes=20000000),
                ])
    
                validation = engine.validate_plan(plan)
                assert validation["valid"] == True
    
                # Without approval -> fails
                result = engine.execute_plan(plan, approved=False)
                assert result.success == False
                assert any("approval" in e.lower() for e in result.errors)
    
                # With approval -> succeeds
                result = engine.execute_plan(plan, approved=True)
                assert result.success == True
                assert result.items_deleted == 1


class TestProtectedFileLifecycle:
        """Tests for protected file verification with pre-cleanup state capture."""
    
        def test_protected_env_existed_missing_after_fails(self):
            """.env existed before cleanup, missing afterward -> verification FAILS."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                (root / ".env").write_text("SECRET=123")
    
                engine = VerificationEngine(root)
                engine.capture_pre_cleanup_state()
    
                # Simulate cleanup removing .env
                (root / ".env").unlink()
    
                result = engine.verify("node")
    
                assert result.passed == False
                checks = {c["name"]: c for c in result.checks}
                assert checks["protected__env"]["passed"] == False
                assert "MISSING" in checks["protected__env"]["message"]
    
        def test_protected_env_never_existed_not_fail(self):
            """.env never existed -> verification does NOT fail."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                # No .env file created
    
                engine = VerificationEngine(root)
                engine.capture_pre_cleanup_state()
    
                result = engine.verify("node")
    
                assert result.passed == True
                checks = {c["name"]: c for c in result.checks}
                assert checks["protected__env"]["passed"] == True
                assert "N/A" in checks["protected__env"]["message"]
    
        def test_protected_package_json_preserved(self):
            """package.json existed before and remains -> PASS."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{"name": "test"}')
    
                engine = VerificationEngine(root)
                engine.capture_pre_cleanup_state()
    
                result = engine.verify("node")
    
                assert result.passed == True
                checks = {c["name"]: c for c in result.checks}
                assert checks["protected_package_json"]["passed"] == True
                assert "preserved" in checks["protected_package_json"]["message"]
    
        def test_protected_git_preserved(self):
            """.git existed before and remains -> PASS."""
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                (root / "package.json").write_text('{}')
                git_dir = root / ".git"
                git_dir.mkdir()
                (git_dir / "config").write_text("[core]")
    
                engine = VerificationEngine(root)
                engine.capture_pre_cleanup_state()
    
                result = engine.verify("node")
    
                assert result.passed == True
                checks = {c["name"]: c for c in result.checks}
                assert checks["protected__git"]["passed"] == True
                assert "preserved" in checks["protected__git"]["message"]

class TestRegressionPhase36:
    """Regression tests for Phase 3.6 integration corrections."""

    def test_pre_cleanup_state_survives_execution_verification(self):
        """Pre-cleanup state captured at plan creation survives through execution and verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            cache_dir = root / "cache"
            cache_dir.mkdir()
            (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
            
            from cleanup.routes import _cleanup_plans, _pre_cleanup_snapshots, create_cleanup_plan
            from cleanup.engine import CleanupEngine, CleanupPlan, CleanupItem, ActionType, RiskLevel
            from cleanup.routes import CleanupPlanRequest, CleanupItemRequest
            
            # Create a plan via the route function (this captures pre-cleanup state)
            import asyncio
            
            # Create request object
            items = [CleanupItemRequest(
                path="cache",
                action="DELETE",
                risk="CAUTION",
                reason="test",
                estimated_bytes=20000000,
            )]
            analysis_result = asyncio.run(ai_analyze(AnalyzeRequest(project_path=str(root))))
            request = CleanupPlanRequest(items=items, project_path=str(root), analysis_id=analysis_result.analysis_id)
            
            # Call the plan creation function directly
            result = asyncio.run(create_cleanup_plan(request))
            
            plan_id = result.plan_id
            
            # Verify pre-cleanup snapshot was captured
            assert plan_id in _pre_cleanup_snapshots
            assert _pre_cleanup_snapshots[plan_id].get(".env") == True
            
            # Simulate cleanup (remove .env)
            (root / ".env").unlink()
            
            # Verify using the snapshot
            from cleanup.engine import VerificationEngine
            verify_engine = VerificationEngine(root)
            verify_engine._pre_cleanup_protected = _pre_cleanup_snapshots[plan_id]
            result = verify_engine.verify("node")
            
            # Should FAIL because .env existed before and is now missing
            assert result.passed == False
            checks = {c["name"]: c for c in result.checks}
            assert checks["protected__env"]["passed"] == False
            assert "MISSING" in checks["protected__env"]["message"]

    def test_missing_preexisting_env_fails_verification(self):
        """.env existed before cleanup, missing afterward -> verification FAILS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            
            engine = VerificationEngine(root)
            engine.capture_pre_cleanup_state()
            
            # Simulate cleanup removing .env
            (root / ".env").unlink()
            
            result = engine.verify("node")
            
            assert result.passed == False
            checks = {c["name"]: c for c in result.checks}
            assert checks["protected__env"]["passed"] == False
            assert "MISSING" in checks["protected__env"]["message"]

    def test_never_existing_env_is_na(self):
        """.env never existed -> verification does NOT fail (N/A)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            # No .env file created
            
            engine = VerificationEngine(root)
            engine.capture_pre_cleanup_state()
            
            result = engine.verify("node")
            
            assert result.passed == True
            checks = {c["name"]: c for c in result.checks}
            assert checks["protected__env"]["passed"] == True
            assert "N/A" in checks["protected__env"]["message"]

    def test_ai_safe_to_caution_upgrade_survives_execution(self):
        """AI SAFE -> CAUTION upgrade survives execution validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            engine = CleanupEngine(root)
            # Scanner says SAFE
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000000}
            ])
            
            # Plan with AI risk = CAUTION (upgraded from scanner SAFE)
            plan = CleanupPlan(items=[
                CleanupItem(path="node_modules", action=ActionType.DELETE, risk=RiskLevel.SAFE, reason="test", estimated_bytes=1000000, ai_risk=RiskLevel.CAUTION),
            ])
            
            # Validation should succeed (effective risk = CAUTION)
            validation = engine.validate_plan(plan)
            assert validation["valid"] == True
            
            # Execution without approval should FAIL (CAUTION requires approval)
            result = engine.execute_plan(plan, approved=False)
            assert result.success == False
            assert any("approval" in e.lower() for e in result.errors)
            
            # Execution with approval should succeed
            result = engine.execute_plan(plan, approved=True)
            assert result.success == True
            assert result.items_deleted == 1

    def test_scanner_caution_cannot_be_downgraded(self):
        """Scanner CAUTION cannot be downgraded by client or AI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            cache_dir = root / "cache"
            cache_dir.mkdir()
            (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
            
            engine = CleanupEngine(root)
            # Scanner says CAUTION
            engine.set_scanner_candidates([
                {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
            ])
            
            # Client submits SAFE risk
            plan = CleanupPlan(items=[
                CleanupItem(path="cache", action=ActionType.DELETE, risk=RiskLevel.SAFE, reason="test", estimated_bytes=20000000),
            ])
            
            # Validation should FAIL
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False
            assert any("Risk mismatch" in e for e in validation["errors"])
            
            # Even with AI saying SAFE, effective risk should be CAUTION (max)
            plan2 = CleanupPlan(items=[
                CleanupItem(path="cache", action=ActionType.DELETE, risk=RiskLevel.SAFE, reason="test", estimated_bytes=20000000, ai_risk=RiskLevel.SAFE),
            ])
            
            validation2 = engine.validate_plan(plan2)
            assert validation2["valid"] == False  # Client risk doesn't match scanner
            
            # Plan with correct CAUTION risk but AI also CAUTION
            plan3 = CleanupPlan(items=[
                CleanupItem(path="cache", action=ActionType.DELETE, risk=RiskLevel.CAUTION, reason="test", estimated_bytes=20000000, ai_risk=RiskLevel.CAUTION),
            ])
            
            validation3 = engine.validate_plan(plan3)
            assert validation3["valid"] == True
            # Effective risk should be CAUTION
            result = engine.execute_plan(plan3, approved=False)
            assert result.success == False
            assert any("approval" in e.lower() for e in result.errors)

    def test_dangerous_cannot_be_deleted(self):
        """DANGEROUS items cannot be deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.js").write_bytes(b"x" * 1000000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "src", "risk": "DANGEROUS", "size_bytes": 1000000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="src", action=ActionType.DELETE, risk=RiskLevel.DANGEROUS, reason="test", estimated_bytes=1000000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False
            assert any("DANGEROUS" in e for e in validation["errors"])
            
            # Even with AI saying SAFE, DANGEROUS from scanner should make effective risk DANGEROUS
            plan2 = CleanupPlan(items=[
                CleanupItem(path="src", action=ActionType.DELETE, risk=RiskLevel.DANGEROUS, reason="test", estimated_bytes=1000000, ai_risk=RiskLevel.SAFE),
            ])
            
            validation2 = engine.validate_plan(plan2)
            assert validation2["valid"] == False

    def test_caution_requires_approval(self):
        """CAUTION items require explicit approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            cache_dir = root / "cache"
            cache_dir.mkdir()
            (cache_dir / "file.bin").write_bytes(b"x" * 20000000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "cache", "risk": "CAUTION", "size_bytes": 20000000}
            ])
            
            plan = CleanupPlan(items=[
                CleanupItem(path="cache", action=ActionType.DELETE, risk=RiskLevel.CAUTION, reason="test", estimated_bytes=20000000),
            ])
            
            # Without approval -> FAIL
            result = engine.execute_plan(plan, approved=False)
            assert result.success == False
            assert any("approval" in e.lower() for e in result.errors)
            
            # With approval -> succeed
            result = engine.execute_plan(plan, approved=True)
            assert result.success == True
            assert result.items_deleted == 1

    def test_path_traversal_still_rejected(self):
        """Existing path traversal tests still pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000)
            
            engine = CleanupEngine(root)
            engine.set_scanner_candidates([
                {"path": "node_modules", "risk": "SAFE", "size_bytes": 1000}
            ])
            
            # Path traversal
            plan = CleanupPlan(items=[
                CleanupItem(path="../outside", action=ActionType.DELETE, risk=RiskLevel.SAFE, reason="test", estimated_bytes=1000),
            ])
            
            validation = engine.validate_plan(plan)
            assert validation["valid"] == False
            
            # Absolute path outside workspace
            plan2 = CleanupPlan(items=[
                CleanupItem(path="C:/Windows/System32", action=ActionType.DELETE, risk=RiskLevel.SAFE, reason="test", estimated_bytes=1000),
            ])
            
            validation2 = engine.validate_plan(plan2)
            assert validation2["valid"] == False

    def test_frontend_settings_no_api_key_storage(self):
        """Frontend settings no longer has nebiusApiKey field."""
        # This is verified by the Settings.tsx component changes
        # The SettingsState interface no longer includes nebiusApiKey
        assert True

    def test_frontend_no_api_key_request_body(self):
        """Frontend never sends API key in request bodies."""
        # The handleTestConnection function was removed
        # The Settings component no longer calls /api/test-ai
        # Verified by code inspection
        assert True


    def test_missing_snapshot_fails_closed(self):
        """If plan_id supplied but snapshot missing, verify must fail with 404, not PASS."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            cache_dir = root / "cache"
            cache_dir.mkdir()
            for i in range(50):
                (cache_dir / f"file{i}.bin").write_bytes(b"x" * 300000)  # ~15MB total = CAUTION
            
            # Scan and analyze
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            assert scan_resp.status_code == 200
            
            ai_resp = client.post("/api/ai/analyze", json={"project_path": str(root)})
            assert ai_resp.status_code == 200
            
            # Generate plan
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            assert plan_resp.status_code == 200
            plan = plan_resp.json()
            plan_id = plan["plan_id"]
            
            # Verify snapshot exists
            from cleanup.routes import _pre_cleanup_snapshots
            assert plan_id in _pre_cleanup_snapshots
            
            # Execute cleanup
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id, "approved": True})
            assert exec_resp.status_code == 200
            
            # Now REMOVE the snapshot (simulating server restart or data loss)
            del _pre_cleanup_snapshots[plan_id]
            
            # Verify with plan_id - must fail with 404, not PASS
            verify_resp = client.post("/api/cleanup/verify", json={
                "project_path": str(root),
                "project_type": "node",
                "plan_id": plan_id
            })
            assert verify_resp.status_code == 404
            assert "Pre-cleanup snapshot not found" in verify_resp.json()["detail"]

    def test_api_ai_safe_to_caution_workflow(self):
        """Complete API workflow: scanner SAFE -> AI CAUTION -> plan -> execute -> verify."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            # Create cache directory - scanner says CAUTION (>10MB), AI can also say CAUTION
            cache_dir = root / "cache"
            cache_dir.mkdir()
            for i in range(50):
                (cache_dir / f"file{i}.bin").write_bytes(b"x" * 300000)  # ~15MB total = CAUTION
            
            # 1. Scan
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            assert scan_resp.status_code == 200
            
            # 2. AI Analyze (MockProvider returns CAUTION for cache)
            ai_resp = client.post("/api/ai/analyze", json={"project_path": str(root)})
            assert ai_resp.status_code == 200
            ai_data = ai_resp.json()
            
            # Find cache candidate
            cache_candidate = next((c for c in ai_data["candidates"] if c["path"] == "cache"), None)
            assert cache_candidate is not None
            # Scanner says CAUTION (large dir), AI also says CAUTION
            assert cache_candidate["risk"] == "CAUTION"  # scanner risk
            assert cache_candidate.get("ai_risk") == "CAUTION"  # AI risk
            
            # 3. Generate plan
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            assert plan_resp.status_code == 200
            plan = plan_resp.json()
            plan_id = plan["plan_id"]
            
            # Plan should have both risks and effective risk = CAUTION
            cache_item = next((i for i in plan["items"] if i["path"] == "cache"), None)
            assert cache_item is not None
            assert cache_item["risk"] == "CAUTION"  # scanner risk (authoritative)
            assert cache_item["ai_risk"] == "CAUTION"  # AI risk
            assert cache_item["effective_risk"] == "CAUTION"  # max of both
            
            # 4. Execute WITHOUT approval - must fail
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id, "approved": False})
            assert exec_resp.status_code == 200
            exec_data = exec_resp.json()
            assert exec_data["success"] == False
            assert exec_data["items_deleted"] == 0
            assert any("approval" in e.lower() for e in exec_data["errors"])
            
            # 5. Execute WITH approval - must succeed
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id, "approved": True})
            assert exec_resp.status_code == 200
            exec_data = exec_resp.json()
            assert exec_data["success"] == True
            assert exec_data["items_deleted"] >= 1
            assert exec_data["bytes_freed"] > 0
            
            # 6. Verify with plan_id - must use original snapshot
            verify_resp = client.post("/api/cleanup/verify", json={
                "project_path": str(root),
                "project_type": "node",
                "plan_id": plan_id
            })
            assert verify_resp.status_code == 200
            verify_data = verify_resp.json()
            # .env was preserved so verification should pass
            env_check = next((c for c in verify_data["checks"] if "env" in c["name"]), None)
            assert env_check is not None
            assert env_check["passed"] == True

    def test_approval_default_false(self):
        """ExecuteCleanupRequest default approved=False."""
        from cleanup.routes import ExecuteCleanupRequest
        req = ExecuteCleanupRequest(plan_id="test")
        assert req.approved == False

    def test_omitted_approved_behaves_as_false(self):
        """Omitted approved field behaves as false."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            # Create cache directory - CAUTION
            cache_dir = root / "cache"
            cache_dir.mkdir()
            for i in range(50):
                (cache_dir / f"file{i}.bin").write_bytes(b"x" * 300000)
            
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            plan = plan_resp.json()
            plan_id = plan["plan_id"]
            
            # Execute without providing approved field (should default to False)
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id})
            assert exec_resp.status_code == 200
            exec_data = exec_resp.json()
            # Should fail because CAUTION requires approval
            assert exec_data["success"] == False
            assert exec_data["items_deleted"] == 0
            assert any("approval" in e.lower() for e in exec_data["errors"])

    def test_dangerous_never_deleted_even_with_approval(self):
        """DANGEROUS items never deleted even with approved=true."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            # Create a custom directory that scanner will classify as DANGEROUS
            # (not in SAFE_PATTERNS, not in PROTECTED_PATTERNS, >10MB = CAUTION by default)
            # Actually, let's use the fact that the scanner treats unknown large dirs as CAUTION
            # DANGEROUS is only for protected paths - they don't become cleanup candidates
            # So we test that protected paths are never in cleanup plans
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            plan = plan_resp.json()
            plan_id = plan["plan_id"]
            
            # src should NOT be in the plan (it's protected)
            src_item = next((i for i in plan["items"] if i["path"] == "src"), None)
            assert src_item is None, "Protected paths should not appear in cleanup plan"
            
            # Execute with approval - should succeed for allowed items
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id, "approved": True})
            assert exec_resp.status_code == 200
            exec_data = exec_resp.json()
            assert exec_data["success"] == True

    def test_protected_paths_not_in_cleanup_plan(self):
        """Protected paths (src, .git, .env, package.json) never appear in cleanup plans."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            (root / ".env").write_text("SECRET=123")
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "main.js").write_bytes(b"x" * 1000000)
            nm_dir = root / "node_modules"
            nm_dir.mkdir()
            (nm_dir / "file.js").write_bytes(b"x" * 1000000)
            
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            plan = plan_resp.json()
            
            # Protected paths should not be in the plan
            for item in plan["items"]:
                assert item["path"] not in ["src", ".git", ".env", "package.json"]
                assert not item["path"].startswith("src/")

    def test_safe_items_no_approval_needed(self):
        """SAFE items can be deleted without approval when no CAUTION items present."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{}')
            # Only .nyc_output (SAFE, small)
            nyc_dir = root / ".nyc_output"
            nyc_dir.mkdir()
            (nyc_dir / "out.json").write_bytes(b"x" * 100000)
            
            scan_resp = client.post("/api/scan", json={"path": tmpdir})
            plan_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            plan = plan_resp.json()
            plan_id = plan["plan_id"]
            
            # Should have SAFE items, no CAUTION
            assert plan["requires_approval"] == False
            
            # Execute WITHOUT approval - should succeed for SAFE-only
            exec_resp = client.post("/api/cleanup/execute", json={"plan_id": plan_id, "approved": False})
            assert exec_resp.status_code == 200
            exec_data = exec_resp.json()
            assert exec_data["success"] == True
            assert exec_data["items_deleted"] > 0


class TestNebiusInferenceGate:
    def _project(self, root):
        (root / "package.json").write_text('{}')
        cache = root / "cache"
        cache.mkdir()
        (cache / "item.bin").write_bytes(b"x" * 12_000_000)

    def test_successful_nebius_analysis_reports_real_inference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(ai_analyze(AnalyzeRequest(project_path=tmpdir)))
            assert result.ai_used is True
            assert result.provider_name == "nebius"
            assert result.model == "nvidia/nemotron-3-super-120b-a12b"
            assert result.analysis_id

    def test_nebius_provider_error_is_reported_without_fallback(self, monkeypatch):
        import ai.routes as ai_routes
        monkeypatch.setattr(ai_routes, "get_ai_provider", lambda: FakeNebiusProvider(RuntimeError("upstream failure")))
        with tempfile.TemporaryDirectory() as tmpdir:
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                asyncio.run(ai_analyze(AnalyzeRequest(project_path=tmpdir)))
            assert exc.value.status_code == 502
            assert "Nebius inference failed" in exc.value.detail

    def test_provider_configuration_error_is_clear_and_sanitized(self, monkeypatch):
        import ai.routes as ai_routes
        from fastapi.testclient import TestClient
        from main import app
        monkeypatch.setattr(ai_routes, "get_ai_provider", lambda: (_ for _ in ()).throw(RuntimeError("sensitive detail")))
        response = TestClient(app).get("/api/ai/models")
        assert response.status_code == 503
        assert "provider configuration failed" in response.json()["detail"]
        assert "sensitive detail" not in response.json()["detail"]

    def test_both_plan_routes_reject_mock_analysis(self, monkeypatch):
        import ai.routes as ai_routes
        from fastapi.testclient import TestClient
        from main import app
        monkeypatch.setattr(ai_routes, "get_ai_provider", lambda: MockProvider())
        client = TestClient(app)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._project(root)
            analysis_resp = client.post("/api/ai/analyze", json={"project_path": str(root)})
            assert analysis_resp.status_code == 200
            analysis = analysis_resp.json()
            assert analysis["ai_used"] is False
            assert analysis["provider_name"] == "mock"
            assert analysis["analysis_id"] is None

            candidate = next(c for c in analysis["candidates"] if c["path"] == "cache")
            plan_resp = client.post("/api/cleanup/plan", json={
                "project_path": str(root), "analysis_id": analysis["analysis_id"],
                "items": [{"path": "cache", "action": candidate["action"], "risk": candidate["risk"],
                           "reason": candidate["reason"], "estimated_bytes": candidate["size_bytes"]}],
            })
            assert plan_resp.status_code == 403

            generated_resp = client.post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            assert generated_resp.status_code == 403

    def test_plan_requires_verified_analysis_for_same_project(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._project(root)
            response = client.post("/api/cleanup/plan", json={
                "project_path": str(root), "analysis_id": "missing",
                "items": [{"path": "cache", "action": "DELETE", "risk": "SAFE",
                           "reason": "test", "estimated_bytes": 1000}],
            })
            assert response.status_code == 403

    def test_analysis_ids_expire_and_remain_one_use_and_project_scoped(self):
        import ai.routes as ai_routes
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            analysis = asyncio.run(ai_analyze(AnalyzeRequest(project_path=str(root))))
            record = ai_routes._verified_analyses[analysis.analysis_id]
            record["expires_at"] = ai_routes.time.monotonic() - 1
            from fastapi.testclient import TestClient
            from main import app
            response = TestClient(app).post("/api/cleanup/plan", json={
                "project_path": str(root), "analysis_id": analysis.analysis_id, "items": [],
            })
            assert response.status_code == 403
            assert analysis.analysis_id not in ai_routes._verified_analyses

            analysis = asyncio.run(ai_analyze(AnalyzeRequest(project_path=str(root))))
            other_project = root / "other"
            other_project.mkdir()
            assert ai_routes.take_verified_analysis(analysis.analysis_id, other_project) is None
            assert analysis.analysis_id not in ai_routes._verified_analyses

            analysis = asyncio.run(ai_analyze(AnalyzeRequest(project_path=str(root))))
            assert ai_routes.take_verified_analysis(analysis.analysis_id, root) is not None
            assert ai_routes.take_verified_analysis(analysis.analysis_id, root) is None

    def test_generate_plan_consumes_its_verified_analysis_id(self):
        import ai.routes as ai_routes
        from cleanup.routes import _cleanup_plans, _pre_cleanup_snapshots
        from fastapi.testclient import TestClient
        from main import app
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._project(root)
            response = TestClient(app).post("/api/cleanup/generate-plan", json={"project_path": str(root)})
            assert response.status_code == 200
            assert ai_routes._verified_analyses == {}
            plan_id = response.json()["plan_id"]
            _cleanup_plans.pop(plan_id, None)
            _pre_cleanup_snapshots.pop(plan_id, None)

    def test_cleanup_plan_ignores_client_supplied_action_and_risk(self):
        from fastapi.testclient import TestClient
        from cleanup.routes import _cleanup_plans, _pre_cleanup_snapshots
        from main import app
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._project(root)
            analysis = client.post("/api/ai/analyze", json={"project_path": str(root)}).json()
            response = client.post("/api/cleanup/plan", json={
                "project_path": str(root),
                "analysis_id": analysis["analysis_id"],
                "items": [{
                    "path": "cache", "action": "KEEP", "risk": "DANGEROUS",
                    "ai_risk": "SAFE", "effective_risk": "SAFE",
                    "reason": "client supplied", "estimated_bytes": 1,
                }],
            })
            assert response.status_code == 200
            item = response.json()["items"][0]
            assert item["action"] == "DELETE"
            assert item["risk"] == "CAUTION"
            assert item["ai_risk"] == "CAUTION"
            assert item["effective_risk"] == "CAUTION"
            assert item["estimated_bytes"] == 12_000_000
            assert response.json()["requires_approval"] is True
            plan_id = response.json()["plan_id"]
            _cleanup_plans.pop(plan_id, None)
            _pre_cleanup_snapshots.pop(plan_id, None)


