"""Filesystem operations with safety allowlists."""

import os
import shutil
import stat
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DeleteResult:
    success: bool
    path: str
    error: Optional[str] = None
    bytes_freed: int = 0


class FilesystemTools:
    """Safe filesystem operations with allowlist-based protection."""
    
    # Patterns that are NEVER allowed to be deleted
    PROTECTED_PATTERNS = {
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
    
    # Patterns that are SAFE to delete (regenerable)
    SAFE_PATTERNS = {
        "node_modules",
        "dist",
        "build",
        ".next",
        ".vite",
        ".parcel-cache",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "venv",
        ".venv",
        "env",
        ".tox",
        "htmlcov",
        ".coverage",
        "target",
        "CMakeFiles",
        "cmake-build-debug",
        "cmake-build-release",
        "*.log",
        "*.tmp",
        "*.temp",
        "tmp",
        "temp",
        "coverage",
        ".nyc_output",
        ".eslintcache",
        ".stylelintcache",
        "*.tsbuildinfo",
    }

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
    
    def is_protected(self, path: Path) -> bool:
        """Check if a path is protected from deletion."""
        try:
            rel = path.relative_to(self.workspace_root)
        except ValueError:
            return True  # Outside workspace = protected
        
        rel_str = str(rel)
        name = path.name
        
        # Check exact matches
        if rel_str in self.PROTECTED_PATTERNS or name in self.PROTECTED_PATTERNS:
            return True
        
        # Check glob patterns
        import fnmatch
        for pattern in self.PROTECTED_PATTERNS:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(name, pattern):
                return True
        
        # Check if any parent is .git
        for parent in rel.parents:
            if parent.name == ".git":
                return True
        
        return False
    
    def is_safe(self, path: Path) -> bool:
        """Check if a path matches a known safe pattern."""
        name = path.name
        import fnmatch
        for pattern in self.SAFE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def get_size(self, path: Path) -> int:
        """Get size of file or directory in bytes."""
        try:
            if path.is_file():
                return path.stat().st_size
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
    
    def delete_path(self, path: Path) -> DeleteResult:
        """Safely delete a path with protection checks."""
        # Do not resolve a candidate symlink/junction to its target and then
        # delete that target. Scanner candidates are relative to the project;
        # each component must remain a real directory/file at execution time.
        raw_path = Path(path)
        try:
            lexical = raw_path.absolute().relative_to(self.workspace_root)
        except ValueError:
            return DeleteResult(success=False, path=str(raw_path), error="Path outside workspace root")
        if any(part in {".", ".."} for part in lexical.parts):
            return DeleteResult(success=False, path=str(raw_path), error="Path traversal is not allowed")
        cursor = self.workspace_root
        try:
            for part in lexical.parts:
                cursor = cursor / part
                component = cursor.lstat()
                is_reparse = bool(getattr(component, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                if stat.S_ISLNK(component.st_mode) or is_reparse:
                    return DeleteResult(success=False, path=str(raw_path), error="Symlinks and reparse points cannot be deleted as cleanup candidates")
        except OSError:
            return DeleteResult(success=False, path=str(raw_path), error="Path does not exist or cannot be inspected")

        # Resolve path
        try:
            path = raw_path.resolve(strict=True)
        except Exception as e:
            return DeleteResult(success=False, path=str(path), error=f"Path resolution failed: {e}")
        
        # Check if within workspace
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            return DeleteResult(success=False, path=str(path), error="Path outside workspace root")
        
        # Check protection
        if self.is_protected(path):
            return DeleteResult(success=False, path=str(path), error="Path is protected")
        
        # Get size before deletion
        size = self.get_size(path)
        
        # Perform deletion
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            else:
                return DeleteResult(success=False, path=str(path), error="Path does not exist")
            
            return DeleteResult(success=True, path=str(path), bytes_freed=size)
        except PermissionError:
            return DeleteResult(success=False, path=str(path), error="Permission denied")
        except Exception as e:
            return DeleteResult(success=False, path=str(path), error=f"Deletion failed: {e}")
    
    def list_directory(self, path: Path) -> List[Path]:
        """List directory contents safely."""
        try:
            path = path.resolve()
            path.relative_to(self.workspace_root)
            return list(path.iterdir())
        except Exception:
            return []
    
    def path_exists(self, path: Path) -> bool:
        """Check if path exists within workspace."""
        try:
            path = path.resolve()
            path.relative_to(self.workspace_root)
            return path.exists()
        except Exception:
            return False


class GitTools:
    """Git operations for safety checks."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
    
    def is_git_repo(self, path: Path) -> bool:
        """Check if path is a git repository."""
        return (path / ".git").exists()
    
    def has_uncommitted_changes(self, path: Path) -> bool:
        """Check if repo has uncommitted changes."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return len(result.stdout.strip()) > 0
        except Exception:
            return False
    
    def get_current_branch(self, path: Path) -> Optional[str]:
        """Get current git branch."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or None
        except Exception:
            return None
    
    def get_remote_url(self, path: Path) -> Optional[str]:
        """Get git remote origin URL."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or None
        except Exception:
            return None
