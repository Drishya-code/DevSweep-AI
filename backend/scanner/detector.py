"""Project detection and analysis utilities."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class ProjectType(str, Enum):
    NODE = "node"
    PYTHON = "python"
    CPP = "cpp"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGEROUS = "DANGEROUS"


@dataclass
class CleanupCandidate:
    path: str
    risk: RiskLevel
    reason: str
    size_bytes: int


@dataclass
class ProjectAnalysis:
    project_type: ProjectType
    framework: str
    package_manager: str
    language: str
    has_git: bool
    git_clean: bool
    cleanup_candidates: List[CleanupCandidate]
    total_recoverable_bytes: int
    protected_paths: List[str]
    notes: str = ""


# Known regenerable patterns (SAFE to delete)
SAFE_PATTERNS: Dict[str, Dict] = {
    "node_modules": {
        "risk": RiskLevel.SAFE,
        "reason": "Regenerable dependencies from package-lock.json/yarn.lock/pnpm-lock.yaml",
        "project_types": [ProjectType.NODE],
    },
    "dist": {
        "risk": RiskLevel.SAFE,
        "reason": "Generated build output",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON],
    },
    "build": {
        "risk": RiskLevel.SAFE,
        "reason": "Generated build output",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    ".next": {
        "risk": RiskLevel.SAFE,
        "reason": "Next.js build cache and output",
        "project_types": [ProjectType.NODE],
    },
    ".vite": {
        "risk": RiskLevel.SAFE,
        "reason": "Vite cache directory",
        "project_types": [ProjectType.NODE],
    },
    ".parcel-cache": {
        "risk": RiskLevel.SAFE,
        "reason": "Parcel bundler cache",
        "project_types": [ProjectType.NODE],
    },
    "__pycache__": {
        "risk": RiskLevel.SAFE,
        "reason": "Python bytecode cache",
        "project_types": [ProjectType.PYTHON],
    },
    ".pytest_cache": {
        "risk": RiskLevel.SAFE,
        "reason": "Pytest cache",
        "project_types": [ProjectType.PYTHON],
    },
    ".mypy_cache": {
        "risk": RiskLevel.SAFE,
        "reason": "MyPy type checker cache",
        "project_types": [ProjectType.PYTHON],
    },
    ".ruff_cache": {
        "risk": RiskLevel.SAFE,
        "reason": "Ruff linter cache",
        "project_types": [ProjectType.PYTHON],
    },
    "venv": {
        "risk": RiskLevel.SAFE,
        "reason": "Python virtual environment (regenerable from requirements.txt/pyproject.toml)",
        "project_types": [ProjectType.PYTHON],
    },
    ".venv": {
        "risk": RiskLevel.SAFE,
        "reason": "Python virtual environment (regenerable from requirements.txt/pyproject.toml)",
        "project_types": [ProjectType.PYTHON],
    },
    "env": {
        "risk": RiskLevel.SAFE,
        "reason": "Python virtual environment (regenerable from requirements.txt/pyproject.toml)",
        "project_types": [ProjectType.PYTHON],
    },
    ".tox": {
        "risk": RiskLevel.SAFE,
        "reason": "Tox test environments",
        "project_types": [ProjectType.PYTHON],
    },
    "htmlcov": {
        "risk": RiskLevel.SAFE,
        "reason": "Coverage HTML reports",
        "project_types": [ProjectType.PYTHON],
    },
    ".coverage": {
        "risk": RiskLevel.SAFE,
        "reason": "Coverage data file",
        "project_types": [ProjectType.PYTHON],
    },
    "target": {
        "risk": RiskLevel.SAFE,
        "reason": "Rust/Cargo build output",
        "project_types": [ProjectType.CPP],  # Also for Rust
    },
    "CMakeFiles": {
        "risk": RiskLevel.SAFE,
        "reason": "CMake build files",
        "project_types": [ProjectType.CPP],
    },
    "cmake-build-debug": {
        "risk": RiskLevel.SAFE,
        "reason": "CLion/CMake debug build",
        "project_types": [ProjectType.CPP],
    },
    "cmake-build-release": {
        "risk": RiskLevel.SAFE,
        "reason": "CLion/CMake release build",
        "project_types": [ProjectType.CPP],
    },
    "*.log": {
        "risk": RiskLevel.SAFE,
        "reason": "Log files",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    "*.tmp": {
        "risk": RiskLevel.SAFE,
        "reason": "Temporary files",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    "*.temp": {
        "risk": RiskLevel.SAFE,
        "reason": "Temporary files",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    "tmp": {
        "risk": RiskLevel.SAFE,
        "reason": "Temporary directory",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    "temp": {
        "risk": RiskLevel.SAFE,
        "reason": "Temporary directory",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON, ProjectType.CPP],
    },
    "coverage": {
        "risk": RiskLevel.SAFE,
        "reason": "Test coverage reports",
        "project_types": [ProjectType.NODE, ProjectType.PYTHON],
    },
    ".nyc_output": {
        "risk": RiskLevel.SAFE,
        "reason": "NYC coverage output",
        "project_types": [ProjectType.NODE],
    },
    ".eslintcache": {
        "risk": RiskLevel.SAFE,
        "reason": "ESLint cache",
        "project_types": [ProjectType.NODE],
    },
    ".stylelintcache": {
        "risk": RiskLevel.SAFE,
        "reason": "Stylelint cache",
        "project_types": [ProjectType.NODE],
    },
    "*.tsbuildinfo": {
        "risk": RiskLevel.SAFE,
        "reason": "TypeScript build info",
        "project_types": [ProjectType.NODE],
    },
}

# Protected patterns (NEVER delete)
PROTECTED_PATTERNS: Set[str] = {
    ".git",
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".env",
    ".env.local",
    ".env.*.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    "src",
    "lib",
    "app",
    "pages",
    "components",
    "hooks",
    "utils",
    "services",
    "types",
    "interfaces",
    "models",
    "controllers",
    "views",
    "templates",
    "static",
    "public",
    "assets",
    "images",
    "fonts",
    "styles",
    "css",
    "scss",
    "sass",
    "less",
    "*.py",
    "*.js",
    "*.ts",
    "*.jsx",
    "*.tsx",
    "*.vue",
    "*.svelte",
    "*.cpp",
    "*.hpp",
    "*.h",
    "*.c",
    "*.cc",
    "*.cxx",
    "*.rs",
    "*.go",
    "*.java",
    "*.kt",
    "*.swift",
    "*.rb",
    "*.php",
    "*.cs",
    "*.fs",
    "*.ml",
    "*.mli",
    "*.clj",
    "*.cljs",
    "*.edn",
    "*.scala",
    "*.sbt",
    "*.gradle",
    "*.maven",
    "*.pom",
    "*.xml",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.toml",
    "*.ini",
    "*.cfg",
    "*.conf",
    "*.config",
    "*.properties",
    "*.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "pyproject.toml",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "Makefile",
    "CMakeLists.txt",
    "meson.build",
    "README*",
    "LICENSE*",
    "CHANGELOG*",
    "CONTRIBUTING*",
    "CODEOWNERS",
    ".github",
    ".gitlab",
    ".vscode",
    ".idea",
    "*.key",
    "*.pem",
    "*.crt",
    "*.p12",
    "*.pfx",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.realm",
    "*.mdb",
    "*.accdb",
    "*.dump",
    "*.sql",
    "*.bak",
    "*.backup",
}


def detect_project_type(path: Path) -> ProjectType:
    """Detect the project type based on marker files."""
    markers = {
        ProjectType.NODE: ["package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"],
        ProjectType.PYTHON: ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "setup.cfg", "poetry.lock"],
        ProjectType.CPP: ["CMakeLists.txt", "Makefile", "meson.build", "*.cpp", "*.hpp", "*.c", "*.h"],
    }

    for ptype, files in markers.items():
        for pattern in files:
            if list(path.glob(pattern)):
                return ptype
    return ProjectType.UNKNOWN


def detect_framework(path: Path, project_type: ProjectType) -> str:
    """Detect the framework based on config files and dependencies."""
    if project_type == ProjectType.NODE:
        package_json = path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "next" in deps:
                    return "nextjs"
                if "react" in deps:
                    return "react"
                if "vue" in deps:
                    return "vue"
                if "@angular/core" in deps:
                    return "angular"
                if "svelte" in deps:
                    return "svelte"
                if "vite" in deps:
                    return "vite"
                if "express" in deps:
                    return "express"
                if "fastify" in deps:
                    return "fastify"
                if "nest" in str(deps).lower():
                    return "nestjs"
            except Exception:
                pass
    elif project_type == ProjectType.PYTHON:
        pyproject = path / "pyproject.toml"
        requirements = path / "requirements.txt"
        if pyproject.exists():
            try:
                import tomllib
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                deps = data.get("project", {}).get("dependencies", [])
                deps_str = " ".join(deps).lower()
                if "fastapi" in deps_str:
                    return "fastapi"
                if "django" in deps_str:
                    return "django"
                if "flask" in deps_str:
                    return "flask"
                if "starlette" in deps_str:
                    return "starlette"
                if "typer" in deps_str:
                    return "typer"
            except Exception:
                pass
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                if "fastapi" in content:
                    return "fastapi"
                if "django" in content:
                    return "django"
                if "flask" in content:
                    return "flask"
            except Exception:
                pass
    return "unknown"


def detect_package_manager(path: Path, project_type: ProjectType) -> str:
    """Detect the package manager."""
    if project_type == ProjectType.NODE:
        if (path / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (path / "yarn.lock").exists():
            return "yarn"
        if (path / "package-lock.json").exists():
            return "npm"
        return "npm"
    elif project_type == ProjectType.PYTHON:
        if (path / "poetry.lock").exists():
            return "poetry"
        if (path / "Pipfile.lock").exists():
            return "pipenv"
        if (path / "uv.lock").exists():
            return "uv"
        return "pip"
    return "unknown"


def detect_language(path: Path, project_type: ProjectType) -> str:
    """Detect the primary language."""
    if project_type == ProjectType.NODE:
        if (path / "tsconfig.json").exists():
            return "typescript"
        return "javascript"
    elif project_type == ProjectType.PYTHON:
        return "python"
    elif project_type == ProjectType.CPP:
        return "cpp"
    return "unknown"


def get_dir_size(path: Path) -> int:
    """Get directory size in bytes - actual filesystem size only."""
    try:
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
        return total
    except Exception:
        return 0


def is_protected(path: Path, root: Path) -> bool:
    """Check if a path is protected."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True  # Outside root = protected

    rel_str = str(rel)
    name = path.name

    # Check exact matches
    if rel_str in PROTECTED_PATTERNS or name in PROTECTED_PATTERNS:
        return True

    # Check glob patterns
    import fnmatch
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(name, pattern):
            return True

    # Check if any parent is .git
    for parent in rel.parents:
        if parent.name == ".git":
            return True

    return False


def find_cleanup_candidates(root: Path, project_type: ProjectType) -> List[CleanupCandidate]:
    """Find cleanup candidates in the project."""
    candidates = []

    for item in root.iterdir():
        if item.name.startswith(".") and item.name not in [".next", ".vite", ".parcel-cache", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".coverage", ".nyc_output", ".eslintcache", ".stylelintcache"]:
            continue

        if is_protected(item, root):
            continue

        # Check against known safe patterns
        matched = False
        for pattern, info in SAFE_PATTERNS.items():
            import fnmatch
            if fnmatch.fnmatch(item.name, pattern):
                if project_type in info["project_types"] or ProjectType.UNKNOWN in info["project_types"]:
                    size = get_dir_size(item) if item.is_dir() else item.stat().st_size
                    if size > 0:
                        candidates.append(CleanupCandidate(
                            path=str(item.relative_to(root)),
                            risk=info["risk"],
                            reason=info["reason"],
                            size_bytes=size,
                        ))
                    matched = True
                    break

        # Also check for large unknown directories (CAUTION)
        if not matched and item.is_dir():
            size = get_dir_size(item)
            if size > 10 * 1024 * 1024:  # > 10MB
                candidates.append(CleanupCandidate(
                    path=str(item.relative_to(root)),
                    risk=RiskLevel.CAUTION,
                    reason=f"Large directory ({size / (1024*1024):.1f} MB) - verify before deleting",
                    size_bytes=size,
                ))

    return candidates


def analyze_project(path: Path) -> ProjectAnalysis:
    """Perform full project analysis."""
    project_type = detect_project_type(path)
    framework = detect_framework(path, project_type)
    package_manager = detect_package_manager(path, project_type)
    language = detect_language(path, project_type)
    has_git = (path / ".git").exists()
    
    # Real git status check
    git_clean = True
    if has_git:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            git_clean = len(result.stdout.strip()) == 0
        except Exception:
            git_clean = True  # Default to clean if git check fails

    candidates = find_cleanup_candidates(path, project_type)
    total_recoverable = sum(c.size_bytes for c in candidates if c.risk in (RiskLevel.SAFE, RiskLevel.CAUTION))

    protected = [p for p in PROTECTED_PATTERNS if not p.startswith("*")]

    return ProjectAnalysis(
        project_type=project_type,
        framework=framework,
        package_manager=package_manager,
        language=language,
        has_git=has_git,
        git_clean=git_clean,
        cleanup_candidates=candidates,
        total_recoverable_bytes=total_recoverable,
        protected_paths=protected,
    )