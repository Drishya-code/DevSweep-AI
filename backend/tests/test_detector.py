import pytest
from pathlib import Path
import tempfile
import os

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])