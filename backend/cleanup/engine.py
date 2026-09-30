"""Cleanup engine with safety validation and execution."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import time
import json

from tools.filesystem import FilesystemTools, GitTools


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGEROUS = "DANGEROUS"


class ActionType(str, Enum):
    DELETE = "DELETE"
    KEEP = "KEEP"


@dataclass
class CleanupItem:
    path: str
    action: ActionType
    risk: RiskLevel
    reason: str
    estimated_bytes: int
    regeneration_command: Optional[str] = None


@dataclass
class CleanupPlan:
    items: List[CleanupItem]
    total_safe_bytes: int = 0
    total_caution_bytes: int = 0
    total_dangerous_bytes: int = 0
    requires_approval: bool = True
    warnings: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)


@dataclass
class CleanupResult:
    success: bool
    items_processed: int = 0
    items_deleted: int = 0
    items_failed: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class VerificationResult:
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class CleanupEngine:
    """Core cleanup engine with safety validation."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.fs_tools = FilesystemTools(workspace_root)
        self.git_tools = GitTools(workspace_root)
    
    def validate_plan(self, plan: CleanupPlan) -> Dict[str, Any]:
        """Validate a cleanup plan against safety rules."""
        errors = []
        warnings = []
        
        # Check workspace accessibility
        if not self.workspace_root.exists():
            errors.append(f"Workspace root does not exist: {self.workspace_root}")
        
        # Check each item
        for item in plan.items:
            item_path = self.workspace_root / item.path
            
            # Path must exist
            if not self.fs_tools.path_exists(item_path):
                errors.append(f"Path does not exist: {item.path}")
                continue
            
            # Check protection
            if self.fs_tools.is_protected(item_path):
                errors.append(f"Path is protected: {item.path}")
                continue
            
            # Risk level consistency
            if item.risk == RiskLevel.DANGEROUS:
                errors.append(f"DANGEROUS items not allowed in plan: {item.path}")
            elif item.risk == RiskLevel.CAUTION and item.action == ActionType.DELETE:
                warnings.append(f"CAUTION item requires explicit approval: {item.path}")
        
        # Check git status
        if self.git_tools.is_git_repo(self.workspace_root):
            if self.git_tools.has_uncommitted_changes(self.workspace_root):
                warnings.append("Git repository has uncommitted changes")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def execute_plan(self, plan: CleanupPlan, approved: bool = False) -> CleanupResult:
        """Execute a validated cleanup plan."""
        start_time = time.time()
        
        # Validate first
        validation = self.validate_plan(plan)
        if not validation["valid"]:
            return CleanupResult(
                success=False,
                items_processed=0,
                items_deleted=0,
                items_failed=0,
                bytes_freed=0,
                errors=validation["errors"],
                duration_seconds=time.time() - start_time,
            )
        
        # Check approval for CAUTION items
        caution_items = [i for i in plan.items if i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE]
        if caution_items and not approved:
            return CleanupResult(
                success=False,
                items_processed=0,
                items_deleted=0,
                items_failed=0,
                bytes_freed=0,
                errors=["CAUTION items require explicit approval"],
                duration_seconds=time.time() - start_time,
            )
        
        # Execute deletions
        bytes_freed = 0
        items_deleted = 0
        items_failed = 0
        errors = []
        
        for item in plan.items:
            if item.action != ActionType.DELETE:
                continue
            
            item_path = self.workspace_root / item.path
            result = self.fs_tools.delete_path(item_path)
            
            if result.success:
                bytes_freed += result.bytes_freed
                items_deleted += 1
            else:
                items_failed += 1
                errors.append(f"{item.path}: {result.error}")
        
        return CleanupResult(
            success=items_failed == 0,
            items_processed=len([i for i in plan.items if i.action == ActionType.DELETE]),
            items_deleted=items_deleted,
            items_failed=items_failed,
            bytes_freed=bytes_freed,
            errors=errors,
            duration_seconds=time.time() - start_time,
        )


class VerificationEngine:
    """Project verification after cleanup."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.fs_tools = FilesystemTools(workspace_root)
        self.git_tools = GitTools(workspace_root)
    
    def verify(self, project_type: str = "unknown") -> VerificationResult:
        """Run verification checks based on project type."""
        checks = []
        errors = []
        
        # Check 1: Workspace root exists
        checks.append({
            "name": "workspace_exists",
            "passed": self.workspace_root.exists(),
            "message": "Workspace root exists",
        })
        
        # Check 2: Git repo integrity
        if self.git_tools.is_git_repo(self.workspace_root):
            checks.append({
                "name": "git_repo_intact",
                "passed": True,
                "message": "Git repository intact",
            })
        else:
            checks.append({
                "name": "git_repo_intact",
                "passed": True,
                "message": "Not a git repository (skipped)",
            })
        
        # Check 3: Protected files still exist
        protected_checks = [
            ("package.json", "package.json exists"),
            (".git", "git directory exists"),
            (".env", ".env not deleted"),
        ]
        
        for path_name, message in protected_checks:
            path = self.workspace_root / path_name
            if path.exists() or not self.fs_tools.is_protected(path):
                checks.append({
                    "name": f"protected_{path_name.replace('.', '_')}",
                    "passed": True,
                    "message": message,
                })
        
        # Check 4: Source code directories exist
        for src_dir in ["src", "lib", "app"]:
            path = self.workspace_root / src_dir
            if path.exists():
                checks.append({
                    "name": f"source_{src_dir}",
                    "passed": True,
                    "message": f"Source directory {src_dir} exists",
                })
        
        # Project-specific checks
        if project_type == "node":
            checks.extend(self._verify_node())
        elif project_type == "python":
            checks.extend(self._verify_python())
        
        passed = all(c["passed"] for c in checks)
        errors = [c["message"] for c in checks if not c["passed"]]
        
        return VerificationResult(
            passed=passed,
            checks=checks,
            errors=errors,
        )
    
    def _verify_node(self) -> List[Dict[str, Any]]:
        """Node.js specific verification."""
        checks = []
        # Check package.json exists
        pkg = self.workspace_root / "package.json"
        if pkg.exists():
            checks.append({
                "name": "package_json",
                "passed": True,
                "message": "package.json exists",
            })
        return checks
    
    def _verify_python(self) -> List[Dict[str, Any]]:
        """Python specific verification."""
        checks = []
        # Check pyproject.toml or requirements.txt
        for f in ["pyproject.toml", "requirements.txt"]:
            path = self.workspace_root / f
            if path.exists():
                checks.append({
                    "name": f"python_{f.replace('.', '_')}",
                    "passed": True,
                    "message": f"{f} exists",
                })
        return checks


class PlanGenerator:
    """Generate cleanup plans from scan results."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.fs_tools = FilesystemTools(workspace_root)
    
    def generate_plan(
        self,
        scan_candidates: List[Dict[str, Any]],
        default_risk_level: RiskLevel = RiskLevel.SAFE,
    ) -> CleanupPlan:
        """Generate a cleanup plan from scan candidates."""
        items = []
        
        for candidate in scan_candidates:
            path = candidate["path"]
            risk = RiskLevel(candidate["risk"])
            reason = candidate["reason"]
            size = candidate["size_bytes"]
            
            # Determine action based on risk
            if risk == RiskLevel.SAFE:
                action = ActionType.DELETE
            elif risk == RiskLevel.CAUTION:
                action = ActionType.DELETE  # Requires approval
            else:
                action = ActionType.KEEP
            
            # Determine regeneration command
            regen_cmd = self._get_regeneration_command(path)
            
            items.append(CleanupItem(
                path=path,
                action=action,
                risk=risk,
                reason=reason,
                estimated_bytes=size,
                regeneration_command=regen_cmd,
            ))
        
        # Calculate totals
        safe_bytes = sum(i.estimated_bytes for i in items if i.risk == RiskLevel.SAFE and i.action == ActionType.DELETE)
        caution_bytes = sum(i.estimated_bytes for i in items if i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE)
        dangerous_bytes = sum(i.estimated_bytes for i in items if i.risk == RiskLevel.DANGEROUS and i.action == ActionType.DELETE)
        
        # Warnings
        warnings = []
        caution_items = [i for i in items if i.risk == RiskLevel.CAUTION and i.action == ActionType.DELETE]
        if caution_items:
            warnings.append(f"{len(caution_items)} CAUTION items require explicit approval")
        
        # Verification steps
        verification_steps = [
            "Verify project still builds",
            "Run tests if available",
            "Check git status",
        ]
        
        return CleanupPlan(
            items=items,
            total_safe_bytes=safe_bytes,
            total_caution_bytes=caution_bytes,
            total_dangerous_bytes=dangerous_bytes,
            requires_approval=len(caution_items) > 0,
            warnings=warnings,
            verification_steps=verification_steps,
        )
    
    def _get_regeneration_command(self, path: str) -> Optional[str]:
        """Get regeneration command for a path."""
        commands = {
            "node_modules": "npm install",
            "dist": "npm run build",
            "build": "npm run build",
            ".next": "npm run build",
            ".vite": "npm run dev",
            ".parcel-cache": "npm run dev",
            "__pycache__": "python -m compileall .",
            ".pytest_cache": "pytest",
            ".mypy_cache": "mypy .",
            ".ruff_cache": "ruff check .",
            "venv": "python -m venv venv && pip install -r requirements.txt",
            ".venv": "python -m venv .venv && pip install -r requirements.txt",
            "env": "python -m venv env && pip install -r requirements.txt",
            ".tox": "tox",
            "target": "cargo build",
        }
        return commands.get(path)