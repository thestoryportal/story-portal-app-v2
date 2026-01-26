"""
Compensation Engine - Executes compensation actions for failed units
Path: platform/src/L05_planning/checkpoints/compensation_engine.py
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..agents.spec_decomposer import AtomicUnit

logger = logging.getLogger(__name__)


class CompensationType(Enum):
    """Types of compensation actions."""
    GIT_CHECKOUT = "git_checkout"
    GIT_RESET = "git_reset"
    GIT_CLEAN = "git_clean"
    CUSTOM_COMMAND = "custom_command"
    CUSTOM_FUNCTION = "custom_function"
    FILE_RESTORE = "file_restore"


class CompensationStatus(Enum):
    """Status of compensation execution."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class CompensationResult:
    """Result of a compensation action."""
    unit_id: str
    status: CompensationStatus
    compensation_type: CompensationType
    message: str = ""
    output: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """Returns True if compensation succeeded."""
        return self.status == CompensationStatus.SUCCESS


@dataclass
class CompensationAction:
    """A registered compensation action."""
    unit_id: str
    compensation_type: CompensationType
    action: str  # Command string or function name
    priority: int = 0  # Higher = executed first
    files: List[str] = field(default_factory=list)


class CompensationEngine:
    """
    Executes compensation actions to restore system state after failures.

    Supports:
    - Git-based compensation (checkout, reset)
    - Custom shell commands
    - Custom functions
    - File restoration
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        dry_run: bool = False,
    ):
        """
        Initialize compensation engine.

        Args:
            repo_path: Path to git repository (defaults to cwd)
            dry_run: If True, don't execute actual commands
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.dry_run = dry_run
        self._actions: Dict[str, List[CompensationAction]] = {}
        self._custom_functions: Dict[str, Callable[[], bool]] = {}
        self._history: List[CompensationResult] = []

    def register_action(
        self,
        unit_id: str,
        compensation_type: CompensationType,
        action: str,
        priority: int = 0,
        files: Optional[List[str]] = None,
    ):
        """
        Registers a compensation action for a unit.

        Args:
            unit_id: Unit ID to register action for
            compensation_type: Type of compensation
            action: Command or function name
            priority: Execution priority (higher = first)
            files: List of affected files
        """
        if unit_id not in self._actions:
            self._actions[unit_id] = []

        compensation = CompensationAction(
            unit_id=unit_id,
            compensation_type=compensation_type,
            action=action,
            priority=priority,
            files=files or [],
        )

        self._actions[unit_id].append(compensation)
        # Sort by priority (descending)
        self._actions[unit_id].sort(key=lambda x: x.priority, reverse=True)

        logger.debug(f"Registered compensation action for unit {unit_id}: {compensation_type.value}")

    def register_function(self, name: str, func: Callable[[], bool]):
        """
        Registers a custom compensation function.

        Args:
            name: Function name
            func: Callable that returns True if compensation succeeded
        """
        self._custom_functions[name] = func
        logger.debug(f"Registered compensation function: {name}")

    def compensate(self, unit: AtomicUnit) -> bool:
        """
        Executes compensation for a unit.

        Args:
            unit: AtomicUnit that failed and needs compensation

        Returns:
            True if compensation succeeded, False otherwise
        """
        start_time = datetime.now()

        logger.info(f"Starting compensation for unit {unit.id}")

        # Try registered actions first
        if unit.id in self._actions:
            for action in self._actions[unit.id]:
                result = self._execute_action(action)
                self._history.append(result)
                if result.status == CompensationStatus.SUCCESS:
                    return True

        # Fall back to unit's compensation_action
        if unit.compensation_action:
            result = self._execute_unit_compensation(unit)
            self._history.append(result)
            return result.status == CompensationStatus.SUCCESS

        # Auto-generate git-based compensation from unit files
        if unit.files:
            result = self._execute_file_checkout(unit)
            self._history.append(result)
            return result.status == CompensationStatus.SUCCESS

        # No compensation available
        logger.warning(f"No compensation action available for unit {unit.id}")
        self._history.append(CompensationResult(
            unit_id=unit.id,
            status=CompensationStatus.SKIPPED,
            compensation_type=CompensationType.CUSTOM_COMMAND,
            message="No compensation action available",
        ))
        return False

    def _execute_action(self, action: CompensationAction) -> CompensationResult:
        """Executes a registered compensation action."""
        start_time = datetime.now()

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {action.compensation_type.value} - {action.action}")
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.SUCCESS,
                compensation_type=action.compensation_type,
                message="Dry run - no changes made",
            )

        try:
            if action.compensation_type == CompensationType.GIT_CHECKOUT:
                return self._git_checkout(action)
            elif action.compensation_type == CompensationType.GIT_RESET:
                return self._git_reset(action)
            elif action.compensation_type == CompensationType.GIT_CLEAN:
                return self._git_clean(action)
            elif action.compensation_type == CompensationType.CUSTOM_COMMAND:
                return self._run_command(action)
            elif action.compensation_type == CompensationType.CUSTOM_FUNCTION:
                return self._run_function(action)
            elif action.compensation_type == CompensationType.FILE_RESTORE:
                return self._restore_files(action)
            else:
                return CompensationResult(
                    unit_id=action.unit_id,
                    status=CompensationStatus.FAILED,
                    compensation_type=action.compensation_type,
                    error=f"Unknown compensation type: {action.compensation_type}",
                )
        except Exception as e:
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.FAILED,
                compensation_type=action.compensation_type,
                error=str(e),
            )

    def _execute_unit_compensation(self, unit: AtomicUnit) -> CompensationResult:
        """Executes unit's built-in compensation action."""
        start_time = datetime.now()

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {unit.compensation_action}")
            return CompensationResult(
                unit_id=unit.id,
                status=CompensationStatus.SUCCESS,
                compensation_type=CompensationType.CUSTOM_COMMAND,
                message="Dry run - no changes made",
            )

        try:
            result = subprocess.run(
                unit.compensation_action,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=60,
            )

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            if result.returncode == 0:
                return CompensationResult(
                    unit_id=unit.id,
                    status=CompensationStatus.SUCCESS,
                    compensation_type=CompensationType.CUSTOM_COMMAND,
                    message="Unit compensation executed successfully",
                    output=result.stdout,
                    duration_ms=duration_ms,
                )
            else:
                return CompensationResult(
                    unit_id=unit.id,
                    status=CompensationStatus.FAILED,
                    compensation_type=CompensationType.CUSTOM_COMMAND,
                    output=result.stdout,
                    error=result.stderr,
                    duration_ms=duration_ms,
                )

        except subprocess.TimeoutExpired:
            return CompensationResult(
                unit_id=unit.id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_COMMAND,
                error="Compensation command timed out",
            )
        except Exception as e:
            return CompensationResult(
                unit_id=unit.id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_COMMAND,
                error=str(e),
            )

    def _execute_file_checkout(self, unit: AtomicUnit) -> CompensationResult:
        """Executes git checkout for unit files."""
        start_time = datetime.now()

        if self.dry_run:
            logger.info(f"[DRY RUN] Would checkout: {unit.files}")
            return CompensationResult(
                unit_id=unit.id,
                status=CompensationStatus.SUCCESS,
                compensation_type=CompensationType.GIT_CHECKOUT,
                message="Dry run - no changes made",
            )

        cmd = ["git", "checkout", "--"] + unit.files

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            if result.returncode == 0:
                return CompensationResult(
                    unit_id=unit.id,
                    status=CompensationStatus.SUCCESS,
                    compensation_type=CompensationType.GIT_CHECKOUT,
                    message=f"Checked out {len(unit.files)} files",
                    duration_ms=duration_ms,
                )
            else:
                return CompensationResult(
                    unit_id=unit.id,
                    status=CompensationStatus.FAILED,
                    compensation_type=CompensationType.GIT_CHECKOUT,
                    error=result.stderr,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            return CompensationResult(
                unit_id=unit.id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.GIT_CHECKOUT,
                error=str(e),
            )

    def _git_checkout(self, action: CompensationAction) -> CompensationResult:
        """Executes git checkout."""
        cmd = ["git", "checkout", "--"]
        if action.files:
            cmd.extend(action.files)
        else:
            cmd.append(".")

        return self._run_git_command(action.unit_id, cmd, CompensationType.GIT_CHECKOUT)

    def _git_reset(self, action: CompensationAction) -> CompensationResult:
        """Executes git reset."""
        cmd = ["git", "reset", "--hard", action.action] if action.action else ["git", "reset", "--hard"]
        return self._run_git_command(action.unit_id, cmd, CompensationType.GIT_RESET)

    def _git_clean(self, action: CompensationAction) -> CompensationResult:
        """Executes git clean."""
        cmd = ["git", "clean", "-fd"]
        return self._run_git_command(action.unit_id, cmd, CompensationType.GIT_CLEAN)

    def _run_command(self, action: CompensationAction) -> CompensationResult:
        """Runs a custom command."""
        try:
            result = subprocess.run(
                action.action,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=60,
            )

            status = CompensationStatus.SUCCESS if result.returncode == 0 else CompensationStatus.FAILED

            return CompensationResult(
                unit_id=action.unit_id,
                status=status,
                compensation_type=CompensationType.CUSTOM_COMMAND,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_COMMAND,
                error=str(e),
            )

    def _run_function(self, action: CompensationAction) -> CompensationResult:
        """Runs a custom function."""
        func = self._custom_functions.get(action.action)
        if not func:
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_FUNCTION,
                error=f"Function not registered: {action.action}",
            )

        try:
            success = func()
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.SUCCESS if success else CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_FUNCTION,
                message=f"Function {action.action} executed",
            )

        except Exception as e:
            return CompensationResult(
                unit_id=action.unit_id,
                status=CompensationStatus.FAILED,
                compensation_type=CompensationType.CUSTOM_FUNCTION,
                error=str(e),
            )

    def _restore_files(self, action: CompensationAction) -> CompensationResult:
        """Restores files from backup (placeholder)."""
        # This would integrate with a backup system
        return CompensationResult(
            unit_id=action.unit_id,
            status=CompensationStatus.SKIPPED,
            compensation_type=CompensationType.FILE_RESTORE,
            message="File restore not implemented",
        )

    def _run_git_command(
        self,
        unit_id: str,
        cmd: List[str],
        comp_type: CompensationType,
    ) -> CompensationResult:
        """Runs a git command."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )

            status = CompensationStatus.SUCCESS if result.returncode == 0 else CompensationStatus.FAILED

            return CompensationResult(
                unit_id=unit_id,
                status=status,
                compensation_type=comp_type,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return CompensationResult(
                unit_id=unit_id,
                status=CompensationStatus.FAILED,
                compensation_type=comp_type,
                error=str(e),
            )

    def get_history(self, unit_id: Optional[str] = None) -> List[CompensationResult]:
        """Gets compensation history."""
        if unit_id:
            return [r for r in self._history if r.unit_id == unit_id]
        return self._history

    def get_statistics(self) -> Dict[str, Any]:
        """Returns engine statistics."""
        successful = len([r for r in self._history if r.status == CompensationStatus.SUCCESS])
        failed = len([r for r in self._history if r.status == CompensationStatus.FAILED])

        return {
            "registered_actions": sum(len(actions) for actions in self._actions.values()),
            "registered_functions": len(self._custom_functions),
            "total_compensations": len(self._history),
            "successful": successful,
            "failed": failed,
            "dry_run": self.dry_run,
        }

    def clear_history(self):
        """Clears compensation history."""
        self._history = []
