"""
Athena DevLoop - Self-Improvement Pipeline (SCAFFOLD)
======================================================
Blueprint-to-code pipeline with tests and rollback.

WARNING: This is a SCAFFOLD. DevLoop is disabled by default.
Human approval is ALWAYS required before merging changes.
"""

import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Lazy imports
_logger = None
_settings = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.devloop")
    return _logger

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings


@dataclass
class ChangeRequest:
    """A request for code changes."""
    id: str
    description: str
    files_to_modify: List[str] = field(default_factory=list)
    rationale: str = ""
    requested_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class DevLoopResult:
    """Result of a DevLoop execution."""
    request_id: str
    branch_name: str
    success: bool
    tests_passed: bool
    changes_made: List[str]
    error: Optional[str] = None
    requires_approval: bool = True


class DevLoop:
    """
    Self-improvement pipeline.
    
    Steps:
    1. Create git branch
    2. Generate plan (LLM or template)
    3. Implement changes
    4. Run tests
    5. If fail: revert and log failure
    6. If pass: wait for human approval
    
    SAFETY RULES:
    - NEVER auto-merge to main
    - NEVER run arbitrary shell commands
    - ALWAYS log everything
    - ALWAYS require human approval
    """
    
    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path(__file__).parent.parent
        self.enabled = False  # Disabled by default
        
    def execute(self, request: ChangeRequest, dry_run: bool = True) -> DevLoopResult:
        """
        Execute a change request.
        
        Args:
            request: The change request to execute
            dry_run: If True, don't actually make changes
            
        Returns:
            DevLoopResult with execution details
        """
        logger = _get_logger()
        
        if not self.enabled and not dry_run:
            return DevLoopResult(
                request_id=request.id,
                branch_name="",
                success=False,
                tests_passed=False,
                changes_made=[],
                error="DevLoop is disabled. Set enabled=True to activate."
            )
        
        branch_name = f"devloop/{request.id[:8]}"
        
        logger.info(f"DevLoop starting: {request.id} (dry_run={dry_run})")
        
        try:
            # Step 1: Create branch
            if not dry_run:
                self._create_branch(branch_name)
            logger.info(f"Created branch: {branch_name}")
            
            # Step 2: Generate plan
            plan = self._generate_plan(request)
            logger.info(f"Generated plan with {len(plan)} steps")
            
            # Step 3: Implement changes (NOT IMPLEMENTED - scaffold only)
            changes_made = []
            if not dry_run:
                # This would implement actual changes
                # For now, just log
                logger.warning("Change implementation not yet enabled")
            
            # Step 4: Run tests
            tests_passed = self._run_tests(dry_run=dry_run)
            
            # Step 5: Handle result
            if not tests_passed:
                if not dry_run:
                    self._revert_changes(branch_name)
                    self._log_failure(request, "Tests failed")
                
                return DevLoopResult(
                    request_id=request.id,
                    branch_name=branch_name,
                    success=False,
                    tests_passed=False,
                    changes_made=changes_made,
                    error="Tests failed"
                )
            
            # Step 6: Success - wait for approval
            logger.info(f"DevLoop completed: {request.id} - awaiting approval")
            
            return DevLoopResult(
                request_id=request.id,
                branch_name=branch_name,
                success=True,
                tests_passed=True,
                changes_made=changes_made,
                requires_approval=True
            )
            
        except Exception as e:
            logger.error(f"DevLoop failed: {e}")
            return DevLoopResult(
                request_id=request.id,
                branch_name=branch_name,
                success=False,
                tests_passed=False,
                changes_made=[],
                error=str(e)
            )
    
    def _create_branch(self, branch_name: str) -> bool:
        """Create a new git branch."""
        try:
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _generate_plan(self, request: ChangeRequest) -> List[Dict[str, Any]]:
        """Generate an implementation plan."""
        # Scaffold - just returns empty plan
        return [
            {"step": 1, "action": "analyze", "description": request.description},
            {"step": 2, "action": "implement", "files": request.files_to_modify},
            {"step": 3, "action": "test", "command": "pytest tests/"},
        ]
    
    def _run_tests(self, dry_run: bool = True) -> bool:
        """Run the test suite."""
        if dry_run:
            return True  # Assume pass in dry run
        
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _revert_changes(self, branch_name: str) -> bool:
        """Revert changes and return to main."""
        try:
            # Discard changes
            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=str(self.project_dir),
                capture_output=True,
                timeout=30
            )
            # Return to main
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=str(self.project_dir),
                capture_output=True,
                timeout=30
            )
            # Delete the branch
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=str(self.project_dir),
                capture_output=True,
                timeout=30
            )
            return True
        except Exception:
            return False
    
    def _log_failure(self, request: ChangeRequest, reason: str) -> None:
        """Log failure to memory."""
        logger = _get_logger()
        logger.warning(f"DevLoop failure logged: {request.id} - {reason}")
        
        try:
            from services.memory.client import get_memory
            memory = get_memory()
            memory.upsert_fact(
                user_id="system",
                key=f"devloop_failure_{request.id}",
                value={
                    "request": request.description,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                },
                category="system",
                source="devloop"
            )
        except Exception:
            pass


def create_change_request(description: str, files: List[str] = None) -> ChangeRequest:
    """Convenience function to create a change request."""
    return ChangeRequest(
        id=uuid.uuid4().hex[:12],
        description=description,
        files_to_modify=files or []
    )
