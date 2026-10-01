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
from ai.factory import get_ai_provider, reset_ai_provider
import asyncio


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