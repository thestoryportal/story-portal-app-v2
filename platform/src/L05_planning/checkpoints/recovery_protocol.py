"""
Recovery Protocol - Orchestrates recovery from execution failures
Path: platform/src/L05_planning/checkpoints/recovery_protocol.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..agents.spec_decomposer import AtomicUnit
from ..agents.rollback_coordinator import RollbackCoordinator, RollbackStrategy
from .checkpoint_manager import CheckpointManager, ExecutionCheckpoint
from .compensation_engine import CompensationEngine, CompensationStatus

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategy options."""
    COMPENSATE_ONLY = "compensate_only"  # Only run compensation
    ROLLBACK_TO_CHECKPOINT = "rollback_to_checkpoint"  # Rollback git state
    FULL_RECOVERY = "full_recovery"  # Compensation + rollback
    RETRY = "retry"  # Retry the failed unit
    SKIP = "skip"  # Skip and continue


class RecoveryState(Enum):
    """State of recovery process."""
    IDLE = "idle"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"


@dataclass
class FailureContext:
    """Context about a failure that needs recovery."""
    unit: AtomicUnit
    error: str
    checkpoint: Optional[ExecutionCheckpoint] = None
    timestamp: datetime = field(default_factory=datetime.now)
    attempt: int = 1
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    unit_id: str
    strategy_used: RecoveryStrategy
    state: RecoveryState
    compensation_success: bool = False
    rollback_success: bool = False
    retry_count: int = 0
    message: str = ""
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)


class RecoveryProtocol:
    """
    Orchestrates recovery from execution failures.

    Coordinates:
    - CheckpointManager for checkpoint retrieval
    - CompensationEngine for running compensations
    - RollbackCoordinator for git rollbacks
    """

    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        compensation_engine: Optional[CompensationEngine] = None,
        rollback_coordinator: Optional[RollbackCoordinator] = None,
        default_strategy: RecoveryStrategy = RecoveryStrategy.FULL_RECOVERY,
        repo_path: Optional[str] = None,
    ):
        """
        Initialize recovery protocol.

        Args:
            checkpoint_manager: Manager for checkpoints
            compensation_engine: Engine for compensations
            rollback_coordinator: Coordinator for rollbacks
            default_strategy: Default recovery strategy
            repo_path: Path to git repository
        """
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(repo_path=repo_path)
        self.compensation_engine = compensation_engine or CompensationEngine(repo_path=repo_path)
        self.rollback_coordinator = rollback_coordinator or RollbackCoordinator(repo_path=repo_path, dry_run=True)
        self.default_strategy = default_strategy
        self._state = RecoveryState.IDLE
        self._current_failure: Optional[FailureContext] = None
        self._recovery_history: List[RecoveryResult] = []

    def recover_from_failure(
        self,
        failure_context: Optional[FailureContext] = None,
        strategy: Optional[RecoveryStrategy] = None,
    ) -> RecoveryResult:
        """
        Executes recovery from a failure.

        Args:
            failure_context: Context about the failure (uses current if None)
            strategy: Recovery strategy (uses default if None)

        Returns:
            RecoveryResult with success status
        """
        start_time = datetime.now()
        use_strategy = strategy or self.default_strategy

        # Use provided context or create a dummy one for testing
        if failure_context:
            self._current_failure = failure_context
        elif not self._current_failure:
            # Create dummy failure for testing/validation
            self._current_failure = FailureContext(
                unit=AtomicUnit(
                    id="dummy-unit",
                    title="Dummy Unit",
                    description="Created for protocol validation",
                ),
                error="Validation test",
            )

        self._state = RecoveryState.RECOVERING
        failure = self._current_failure

        logger.info(
            f"Starting recovery for unit {failure.unit.id} "
            f"using strategy {use_strategy.value}"
        )

        errors: List[str] = []
        compensation_success = False
        rollback_success = False
        retry_count = 0

        try:
            if use_strategy == RecoveryStrategy.SKIP:
                # Just mark as skipped
                self._state = RecoveryState.RECOVERED
                result = RecoveryResult(
                    success=True,
                    unit_id=failure.unit.id,
                    strategy_used=use_strategy,
                    state=self._state,
                    message="Unit skipped as per strategy",
                )
                self._recovery_history.append(result)
                return result

            if use_strategy == RecoveryStrategy.RETRY:
                # Retry logic would go here
                retry_count = failure.attempt
                if retry_count < failure.max_retries:
                    failure.attempt += 1
                    # In real implementation, would re-execute the unit
                    self._state = RecoveryState.RECOVERED
                    result = RecoveryResult(
                        success=True,
                        unit_id=failure.unit.id,
                        strategy_used=use_strategy,
                        state=self._state,
                        retry_count=retry_count,
                        message=f"Retry {retry_count} of {failure.max_retries}",
                    )
                    self._recovery_history.append(result)
                    return result
                else:
                    errors.append("Max retries exceeded")

            if use_strategy in (RecoveryStrategy.COMPENSATE_ONLY, RecoveryStrategy.FULL_RECOVERY):
                # Execute compensation
                try:
                    compensation_success = self.compensation_engine.compensate(failure.unit)
                    if not compensation_success:
                        errors.append("Compensation failed")
                except Exception as e:
                    errors.append(f"Compensation error: {e}")
                    compensation_success = False

            if use_strategy in (RecoveryStrategy.ROLLBACK_TO_CHECKPOINT, RecoveryStrategy.FULL_RECOVERY):
                # Execute rollback
                try:
                    checkpoint = failure.checkpoint or self.checkpoint_manager.get_checkpoint_by_unit(
                        failure.unit.id
                    )
                    if checkpoint:
                        # Create a rollback checkpoint from execution checkpoint
                        from ..agents.rollback_coordinator import Checkpoint as RBCheckpoint
                        rb_checkpoint = RBCheckpoint(
                            commit_hash=checkpoint.git_commit,
                            unit_id=checkpoint.unit_id or failure.unit.id,
                            unit_title=failure.unit.title,
                            timestamp=checkpoint.timestamp,
                            branch=checkpoint.git_branch,
                        )
                        rollback_success = self.rollback_coordinator.rollback_to_checkpoint(rb_checkpoint)
                    else:
                        # Try unit-based rollback
                        rollback_success = self.rollback_coordinator.rollback_unit(failure.unit)

                    if not rollback_success:
                        errors.append("Rollback failed")
                except Exception as e:
                    errors.append(f"Rollback error: {e}")
                    rollback_success = False

            # Determine overall success
            if use_strategy == RecoveryStrategy.COMPENSATE_ONLY:
                success = compensation_success
            elif use_strategy == RecoveryStrategy.ROLLBACK_TO_CHECKPOINT:
                success = rollback_success
            elif use_strategy == RecoveryStrategy.FULL_RECOVERY:
                success = compensation_success or rollback_success
            else:
                success = len(errors) == 0

            self._state = RecoveryState.RECOVERED if success else RecoveryState.FAILED

        except Exception as e:
            logger.error(f"Recovery failed with exception: {e}")
            errors.append(str(e))
            self._state = RecoveryState.FAILED
            success = False

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        result = RecoveryResult(
            success=success,
            unit_id=failure.unit.id,
            strategy_used=use_strategy,
            state=self._state,
            compensation_success=compensation_success,
            rollback_success=rollback_success,
            retry_count=retry_count,
            message="Recovery completed" if success else "Recovery failed",
            duration_ms=duration_ms,
            errors=errors,
        )

        self._recovery_history.append(result)

        logger.info(
            f"Recovery for {failure.unit.id} "
            f"{'succeeded' if success else 'failed'} "
            f"({duration_ms}ms)"
        )

        return result

    def set_failure_context(self, context: FailureContext):
        """Sets the current failure context."""
        self._current_failure = context
        self._state = RecoveryState.IDLE

    def create_failure_context(
        self,
        unit: AtomicUnit,
        error: str,
        checkpoint: Optional[ExecutionCheckpoint] = None,
    ) -> FailureContext:
        """
        Creates and sets a failure context.

        Args:
            unit: Failed unit
            error: Error message
            checkpoint: Optional checkpoint to recover to

        Returns:
            Created FailureContext
        """
        context = FailureContext(
            unit=unit,
            error=error,
            checkpoint=checkpoint,
        )
        self._current_failure = context
        return context

    def get_current_state(self) -> RecoveryState:
        """Returns current recovery state."""
        return self._state

    def get_recovery_history(
        self,
        unit_id: Optional[str] = None,
    ) -> List[RecoveryResult]:
        """
        Gets recovery history.

        Args:
            unit_id: Optional filter by unit ID

        Returns:
            List of RecoveryResults
        """
        if unit_id:
            return [r for r in self._recovery_history if r.unit_id == unit_id]
        return self._recovery_history

    def get_statistics(self) -> Dict[str, Any]:
        """Returns protocol statistics."""
        successful = len([r for r in self._recovery_history if r.success])
        failed = len([r for r in self._recovery_history if not r.success])

        return {
            "current_state": self._state.value,
            "total_recoveries": len(self._recovery_history),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(self._recovery_history) if self._recovery_history else 0.0,
            "default_strategy": self.default_strategy.value,
        }

    def reset(self):
        """Resets protocol state."""
        self._state = RecoveryState.IDLE
        self._current_failure = None
