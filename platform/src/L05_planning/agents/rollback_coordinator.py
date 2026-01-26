"""
Rollback Coordinator Agent - Git-based rollback functionality
Path: platform/src/L05_planning/agents/rollback_coordinator.py
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .spec_decomposer import AtomicUnit

logger = logging.getLogger(__name__)


class RollbackStrategy(Enum):
    """Rollback strategy options."""
    HARD_RESET = "hard_reset"  # git reset --hard
    SOFT_RESET = "soft_reset"  # git reset --soft
    REVERT = "revert"  # git revert
    CHECKOUT_FILES = "checkout_files"  # git checkout -- files


@dataclass
class Checkpoint:
    """Represents a git checkpoint."""
    commit_hash: str
    unit_id: str
    unit_title: str
    timestamp: datetime
    message: str = ""
    branch: str = "main"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    from_commit: str
    to_commit: str
    strategy: RollbackStrategy
    files_affected: List[str] = field(default_factory=list)
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class RollbackCoordinator:
    """
    Coordinates git-based rollback operations for failed units.

    Manages checkpoints and provides safe rollback mechanisms.
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        strategy: RollbackStrategy = RollbackStrategy.CHECKOUT_FILES,
        dry_run: bool = False,
    ):
        """
        Initialize rollback coordinator.

        Args:
            repo_path: Path to git repository (defaults to cwd)
            strategy: Default rollback strategy
            dry_run: If True, don't actually execute git commands
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.strategy = strategy
        self.dry_run = dry_run
        self._checkpoints: List[Checkpoint] = []
        self._rollback_history: List[RollbackResult] = []

    def create_checkpoint(
        self,
        unit: AtomicUnit,
        message: Optional[str] = None,
    ) -> Checkpoint:
        """
        Creates a checkpoint for a unit before execution.

        Args:
            unit: AtomicUnit to create checkpoint for
            message: Optional checkpoint message

        Returns:
            Checkpoint with current git state
        """
        commit_hash = self._get_current_commit()
        branch = self._get_current_branch()

        checkpoint = Checkpoint(
            commit_hash=commit_hash,
            unit_id=unit.id,
            unit_title=unit.title,
            timestamp=datetime.now(),
            message=message or f"Checkpoint before {unit.id}",
            branch=branch,
            metadata={
                "files": unit.files,
                "dependencies": unit.dependencies,
            }
        )

        self._checkpoints.append(checkpoint)
        logger.info(f"Created checkpoint {commit_hash[:8]} for unit {unit.id}")

        return checkpoint

    def get_checkpoint(self, unit_id: str) -> Optional[Checkpoint]:
        """Gets checkpoint for a specific unit."""
        for cp in reversed(self._checkpoints):
            if cp.unit_id == unit_id:
                return cp
        return None

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Gets the most recent checkpoint."""
        return self._checkpoints[-1] if self._checkpoints else None

    def rollback_to_checkpoint(
        self,
        checkpoint: Optional[Checkpoint] = None,
        strategy: Optional[RollbackStrategy] = None,
    ) -> bool:
        """
        Rolls back to a checkpoint.

        Args:
            checkpoint: Checkpoint to rollback to (defaults to latest)
            strategy: Rollback strategy (defaults to instance default)

        Returns:
            True if rollback succeeded, False otherwise
        """
        if checkpoint is None:
            checkpoint = self.get_latest_checkpoint()

        if checkpoint is None:
            logger.error("No checkpoint available for rollback")
            return False

        use_strategy = strategy or self.strategy
        current_commit = self._get_current_commit()

        logger.info(
            f"Rolling back from {current_commit[:8]} to {checkpoint.commit_hash[:8]} "
            f"using {use_strategy.value}"
        )

        try:
            result = self._execute_rollback(checkpoint, use_strategy)
            self._rollback_history.append(result)
            return result.success

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            self._rollback_history.append(RollbackResult(
                success=False,
                from_commit=current_commit,
                to_commit=checkpoint.commit_hash,
                strategy=use_strategy,
                error=str(e),
            ))
            return False

    def rollback_unit(
        self,
        unit: AtomicUnit,
        strategy: Optional[RollbackStrategy] = None,
    ) -> bool:
        """
        Rolls back changes for a specific unit.

        Args:
            unit: AtomicUnit to rollback
            strategy: Rollback strategy

        Returns:
            True if rollback succeeded
        """
        checkpoint = self.get_checkpoint(unit.id)
        if not checkpoint:
            # Try to use unit's compensation action
            if unit.compensation_action:
                return self._execute_compensation(unit)
            logger.error(f"No checkpoint found for unit {unit.id}")
            return False

        return self.rollback_to_checkpoint(checkpoint, strategy)

    def _execute_rollback(
        self,
        checkpoint: Checkpoint,
        strategy: RollbackStrategy,
    ) -> RollbackResult:
        """Executes the actual rollback operation."""
        current_commit = self._get_current_commit()
        files_affected: List[str] = []

        if self.dry_run:
            logger.info(f"[DRY RUN] Would rollback to {checkpoint.commit_hash}")
            return RollbackResult(
                success=True,
                from_commit=current_commit,
                to_commit=checkpoint.commit_hash,
                strategy=strategy,
                message="Dry run - no changes made",
            )

        if strategy == RollbackStrategy.CHECKOUT_FILES:
            # Rollback specific files
            files = checkpoint.metadata.get("files", [])
            if files:
                cmd = ["git", "checkout", checkpoint.commit_hash, "--"] + files
                files_affected = files
            else:
                # Fallback to checkout all
                cmd = ["git", "checkout", checkpoint.commit_hash, "--", "."]

        elif strategy == RollbackStrategy.HARD_RESET:
            cmd = ["git", "reset", "--hard", checkpoint.commit_hash]

        elif strategy == RollbackStrategy.SOFT_RESET:
            cmd = ["git", "reset", "--soft", checkpoint.commit_hash]

        elif strategy == RollbackStrategy.REVERT:
            # Create revert commits for commits after checkpoint
            commits_to_revert = self._get_commits_since(checkpoint.commit_hash)
            if commits_to_revert:
                for commit in commits_to_revert:
                    revert_cmd = ["git", "revert", "--no-edit", commit]
                    self._run_git_command(revert_cmd)

            return RollbackResult(
                success=True,
                from_commit=current_commit,
                to_commit=checkpoint.commit_hash,
                strategy=strategy,
                message=f"Reverted {len(commits_to_revert)} commits",
            )

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Execute the command
        self._run_git_command(cmd)

        return RollbackResult(
            success=True,
            from_commit=current_commit,
            to_commit=checkpoint.commit_hash,
            strategy=strategy,
            files_affected=files_affected,
            message=f"Rolled back using {strategy.value}",
        )

    def _execute_compensation(self, unit: AtomicUnit) -> bool:
        """Executes unit's compensation action."""
        if not unit.compensation_action:
            return False

        logger.info(f"Executing compensation action for {unit.id}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {unit.compensation_action}")
            return True

        try:
            result = subprocess.run(
                unit.compensation_action,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Compensation failed: {e}")
            return False

    def _get_current_commit(self) -> str:
        """Gets current HEAD commit hash."""
        result = self._run_git_command(["git", "rev-parse", "HEAD"])
        return result.strip()

    def _get_current_branch(self) -> str:
        """Gets current branch name."""
        result = self._run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return result.strip()

    def _get_commits_since(self, commit_hash: str) -> List[str]:
        """Gets list of commit hashes since given commit."""
        result = self._run_git_command([
            "git", "log", "--format=%H", f"{commit_hash}..HEAD"
        ])
        return [c for c in result.strip().split('\n') if c]

    def _run_git_command(self, cmd: List[str]) -> str:
        """Runs a git command and returns output."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.repo_path),
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")
        return result.stdout

    def get_rollback_history(self) -> List[RollbackResult]:
        """Returns rollback history."""
        return self._rollback_history

    def get_checkpoints(self) -> List[Checkpoint]:
        """Returns all checkpoints."""
        return self._checkpoints

    def get_statistics(self) -> Dict[str, Any]:
        """Returns coordinator statistics."""
        successful = len([r for r in self._rollback_history if r.success])
        failed = len([r for r in self._rollback_history if not r.success])

        return {
            "checkpoints": len(self._checkpoints),
            "rollbacks_total": len(self._rollback_history),
            "rollbacks_successful": successful,
            "rollbacks_failed": failed,
            "default_strategy": self.strategy.value,
            "dry_run": self.dry_run,
        }

    def clear_checkpoints(self):
        """Clears all checkpoints."""
        self._checkpoints = []

    def clear_history(self):
        """Clears rollback history."""
        self._rollback_history = []
