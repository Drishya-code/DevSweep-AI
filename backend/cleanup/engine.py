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
    # AI-validated risk (from Nemotron analysis), used alongside scanner risk
    ai_risk: Optional[RiskLevel] = None


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
        # Cache scanner results for allowlist validation
        self._scanner_candidates: List[Dict[str, Any]] = []
  
    def set_scanner_candidates(self, candidates: List[Dict[str, Any]]):
        """Set the allowed cleanup candidates from scanner for validation."""
        self._scanner_candidates = candidates
  
    def _is_allowed_candidate(self, path: str, action: ActionType, risk: RiskLevel) -> bool:
        """Check if a path is in the scanner's allowlist and valid for deletion.
        
        The scanner risk is authoritative - client cannot downgrade risk.
        Returns (allowed, final_risk) tuple where final_risk is the authoritative scanner risk.
        """
        if action != ActionType.DELETE:
            return True, risk  # KEEP actions are always allowed
        
        # Check if path exists in scanner results
        for candidate in self._scanner_candidates:
            if candidate["path"] == path:
                # Scanner risk is authoritative
                candidate_risk = candidate.get("risk", "SAFE")
                risk_order = {"SAFE": 0, "CAUTION": 1, "DANGEROUS": 2}
                candidate_risk_val = risk_order.get(candidate_risk, 0)
                
                # Must be SAFE or CAUTION (never DANGEROUS)
                if candidate_risk_val >= 2:  # DANGEROUS
                    return False, RiskLevel.DANGEROUS
                
                # Return scanner risk as authoritative (cannot be downgraded by client)
                final_risk = RiskLevel(candidate_risk)
                return True, final_risk
        
        # Not found in scanner results = not allowed
        return False, risk
    
    def _get_authoritative_risk(self, path: str) -> Optional[RiskLevel]:
        """Get the authoritative scanner risk for a path."""
        for candidate in self._scanner_candidates:
            if candidate["path"] == path:
                candidate_risk = candidate.get("risk", "SAFE")
                return RiskLevel(candidate_risk)
        return None
    
    def _get_effective_risk(self, item: CleanupItem, scanner_risk: RiskLevel) -> RiskLevel:
        """Calculate effective risk: max of scanner risk and AI risk (more restrictive wins).
        
        Rules:
        - Scanner SAFE + AI CAUTION = CAUTION
        - Scanner CAUTION + AI SAFE = CAUTION
        - Scanner DANGEROUS = DANGEROUS (DELETE prohibited)
        """
        risk_order = {"SAFE": 0, "CAUTION": 1, "DANGEROUS": 2}
        scanner_val = risk_order.get(scanner_risk.value, 0)
        
        # If item has AI risk, use the more restrictive (max)
        if item.ai_risk:
            ai_val = risk_order.get(item.ai_risk.value, 0)
            effective_val = max(scanner_val, ai_val)
        else:
            effective_val = scanner_val
        
        return RiskLevel(["SAFE", "CAUTION", "DANGEROUS"][effective_val])
    
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
            
            # Get authoritative scanner risk for this path
            auth_risk = self._get_authoritative_risk(item.path)
            if auth_risk is None:
                errors.append(f"Path not in scanner allowlist: {item.path}")
                continue
            
            # REJECT if client risk doesn't match authoritative scanner risk
            # Client cannot downgrade risk (e.g., scanner=CAUTION, client=SAFE)
            if item.risk != auth_risk:
                errors.append(f"Risk mismatch for {item.path}: client={item.risk.value} scanner={auth_risk.value}")
                continue
            
            # Calculate effective risk (max of scanner and AI risk) for approval
            effective_risk = self._get_effective_risk(item, auth_risk)
            
            # DANGEROUS check
            if effective_risk == RiskLevel.DANGEROUS:
                errors.append(f"DANGEROUS items not allowed in plan: {item.path}")
                continue
            
            # Check protection
            if self.fs_tools.is_protected(item_path):
                errors.append(f"Path is protected: {item.path}")
                continue
            
            # Check if in scanner allowlist (using authoritative risk)
            allowed, final_risk = self._is_allowed_candidate(item.path, item.action, auth_risk)
            if not allowed:
                errors.append(f"Path not allowed: {item.path}")
                continue
            
            # Use effective risk for warnings
            if effective_risk == RiskLevel.CAUTION and item.action == ActionType.DELETE:
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
        
        # Check approval for CAUTION items using EFFECTIVE risk (max of scanner + AI)
        caution_items = []
        for item in plan.items:
            if item.action == ActionType.DELETE:
                auth_risk = self._get_authoritative_risk(item.path)
                if auth_risk:
                    effective_risk = self._get_effective_risk(item, auth_risk)
                    if effective_risk == RiskLevel.CAUTION:
                        caution_items.append(item)
        
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
                # Use actual filesystem bytes freed from the deletion result
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
        # Track protected files that existed before cleanup
        self._pre_cleanup_protected: Dict[str, bool] = {}
    
    def capture_pre_cleanup_state(self):
        """Capture which protected files exist before cleanup."""
        self._pre_cleanup_protected = {}
        protected_files = ["package.json", ".git", ".env"]
        for path_name in protected_files:
            path = self.workspace_root / path_name
            if self.fs_tools.is_protected(path):
                self._pre_cleanup_protected[path_name] = path.exists()
    
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
        
        # Check 3: Protected files lifecycle
        protected_checks = [
            ("package.json", "package.json"),
            (".git", "git directory"),
            (".env", ".env file"),
        ]
        
        for path_name, display_name in protected_checks:
            path = self.workspace_root / path_name
            is_protected = self.fs_tools.is_protected(path)
            
            if not is_protected:
                # Not a protected file for this project type
                continue
            
            # Check if it existed before cleanup
            existed_before = self._pre_cleanup_protected.get(path_name, False)
            exists_now = path.exists()
            
            if existed_before and not exists_now:
                # Existed before, now missing = FAIL
                checks.append({
                    "name": f"protected_{path_name.replace('.', '_')}",
                    "passed": False,
                    "message": f"{display_name} existed before cleanup but is now MISSING",
                })
            elif existed_before and exists_now:
                # Existed before, still there = PASS
                checks.append({
                    "name": f"protected_{path_name.replace('.', '_')}",
                    "passed": True,
                    "message": f"{display_name}: OK (preserved)",
                })
            elif not existed_before and not exists_now:
                # Never existed = NOT APPLICABLE
                checks.append({
                    "name": f"protected_{path_name.replace('.', '_')}",
                    "passed": True,
                    "message": f"{display_name}: not present in project (N/A)",
                })
            else:
                # Not existed before but exists now (shouldn't happen in cleanup)
                checks.append({
                    "name": f"protected_{path_name.replace('.', '_')}",
                    "passed": True,
                    "message": f"{display_name}: newly created (OK)",
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
            
            # Create item with AI risk if provided
            ai_risk = candidate.get("ai_risk")
            item = CleanupItem(
                path=path,
                action=action,
                risk=risk,
                reason=reason,
                estimated_bytes=size,
                regeneration_command=regen_cmd,
                ai_risk=RiskLevel(ai_risk) if ai_risk else None,
            )
            items.append(item)
        
        # Calculate effective risk for each item and totals using effective risk
        def get_effective_risk(item: CleanupItem) -> RiskLevel:
            risk_order = {"SAFE": 0, "CAUTION": 1, "DANGEROUS": 2}
            scanner_val = risk_order.get(item.risk.value, 0)
            if item.ai_risk:
                ai_val = risk_order.get(item.ai_risk.value, 0)
                effective_val = max(scanner_val, ai_val)
            else:
                effective_val = scanner_val
            return RiskLevel(["SAFE", "CAUTION", "DANGEROUS"][effective_val])
        
        # Calculate totals using effective risk
        safe_bytes = 0
        caution_bytes = 0
        dangerous_bytes = 0
        
        for item in items:
            effective = get_effective_risk(item)
            if item.action == ActionType.DELETE:
                if effective == RiskLevel.SAFE:
                    safe_bytes += item.estimated_bytes
                elif effective == RiskLevel.CAUTION:
                    caution_bytes += item.estimated_bytes
                elif effective == RiskLevel.DANGEROUS:
                    dangerous_bytes += item.estimated_bytes
        
        # Warnings - based on effective risk
        warnings = []
        caution_items = [i for i in items if get_effective_risk(i) == RiskLevel.CAUTION and i.action == ActionType.DELETE]
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