"""
Resume Manager - Recover from crashes
Path: platform/src/L05_planning/services/resume_manager.py

Features:
- List resumable executions
- Resume from specific checkpoint
- Cleanup stale executions
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """State of an execution for resume purposes."""
    RUNNING = "running"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"  # Crashed/unexpected termination
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"  # Old enough to be cleaned up


@dataclass
class ResumableExecution:
    """An execution that can be resumed."""
    execution_id: str
    plan_id: str
    state: ExecutionState
    started_at: datetime
    last_activity: datetime

    # Progress tracking
    total_units: int = 0
    completed_units: int = 0
    current_unit_id: Optional[str] = None
    current_unit_index: int = 0

    # Checkpoint info
    last_checkpoint_hash: Optional[str] = None
    last_checkpoint_unit: Optional[str] = None

    # Error info
    error: Optional[str] = None
    error_unit_id: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percent(self) -> float:
        """Calculate completion percentage."""
        if self.total_units == 0:
            return 0.0
        return (self.completed_units / self.total_units) * 100

    @property
    def is_resumable(self) -> bool:
        """Check if this execution can be resumed."""
        return self.state in (ExecutionState.INTERRUPTED, ExecutionState.PAUSED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_units": self.total_units,
            "completed_units": self.completed_units,
            "current_unit_id": self.current_unit_id,
            "current_unit_index": self.current_unit_index,
            "last_checkpoint_hash": self.last_checkpoint_hash,
            "last_checkpoint_unit": self.last_checkpoint_unit,
            "error": self.error,
            "error_unit_id": self.error_unit_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumableExecution":
        """Create from dictionary."""
        return cls(
            execution_id=data["execution_id"],
            plan_id=data["plan_id"],
            state=ExecutionState(data["state"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            total_units=data.get("total_units", 0),
            completed_units=data.get("completed_units", 0),
            current_unit_id=data.get("current_unit_id"),
            current_unit_index=data.get("current_unit_index", 0),
            last_checkpoint_hash=data.get("last_checkpoint_hash"),
            last_checkpoint_unit=data.get("last_checkpoint_unit"),
            error=data.get("error"),
            error_unit_id=data.get("error_unit_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ResumeResult:
    """Result of a resume operation."""
    success: bool
    execution_id: str
    resumed_from_unit: Optional[str] = None
    resumed_from_checkpoint: Optional[str] = None
    skipped_units: int = 0
    message: str = ""
    error: Optional[str] = None


class ResumeManager:
    """
    Manage execution recovery from crashes.

    Features:
    - Track execution progress for resume
    - List resumable executions
    - Resume from specific checkpoint
    - Cleanup stale executions
    - Persist state for context compaction survival
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        stale_threshold_hours: int = 24,
        max_stored_executions: int = 100,
    ):
        """
        Initialize resume manager.

        Args:
            storage_path: Path for persisting execution state
            stale_threshold_hours: Hours after which interrupted executions are stale
            max_stored_executions: Maximum number of execution records to keep
        """
        self.storage_path = Path(storage_path) if storage_path else Path.cwd() / ".l05_resume"
        self.stale_threshold_hours = stale_threshold_hours
        self.max_stored_executions = max_stored_executions

        # In-memory storage
        self._executions: Dict[str, ResumableExecution] = {}

        # Ensure storage exists and load existing
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_executions()

    def register_execution(
        self,
        execution_id: str,
        plan_id: str,
        total_units: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResumableExecution:
        """
        Register a new execution for resume tracking.

        Args:
            execution_id: Execution identifier
            plan_id: Plan identifier
            total_units: Total number of units to execute
            metadata: Optional metadata

        Returns:
            ResumableExecution record
        """
        now = datetime.now()

        execution = ResumableExecution(
            execution_id=execution_id,
            plan_id=plan_id,
            state=ExecutionState.RUNNING,
            started_at=now,
            last_activity=now,
            total_units=total_units,
            metadata=metadata or {},
        )

        self._executions[execution_id] = execution
        self._persist_execution(execution)

        logger.info(f"Registered execution for resume tracking: {execution_id}")

        return execution

    def update_progress(
        self,
        execution_id: str,
        current_unit_id: str,
        current_unit_index: int,
        checkpoint_hash: Optional[str] = None,
    ):
        """
        Update execution progress.

        Args:
            execution_id: Execution identifier
            current_unit_id: Current unit being executed
            current_unit_index: Index of current unit (0-based)
            checkpoint_hash: Checkpoint hash if one was created
        """
        execution = self._executions.get(execution_id)
        if not execution:
            logger.warning(f"Unknown execution: {execution_id}")
            return

        execution.current_unit_id = current_unit_id
        execution.current_unit_index = current_unit_index
        execution.last_activity = datetime.now()

        if checkpoint_hash:
            execution.last_checkpoint_hash = checkpoint_hash
            execution.last_checkpoint_unit = current_unit_id

        self._persist_execution(execution)

    def mark_unit_complete(
        self,
        execution_id: str,
        unit_id: str,
    ):
        """
        Mark a unit as completed.

        Args:
            execution_id: Execution identifier
            unit_id: Completed unit identifier
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.completed_units += 1
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

    def mark_unit_failed(
        self,
        execution_id: str,
        unit_id: str,
        error: str,
    ):
        """
        Mark a unit as failed.

        Args:
            execution_id: Execution identifier
            unit_id: Failed unit identifier
            error: Error message
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.error = error
        execution.error_unit_id = unit_id
        execution.state = ExecutionState.INTERRUPTED
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

    def mark_complete(self, execution_id: str):
        """
        Mark an execution as complete.

        Args:
            execution_id: Execution identifier
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.state = ExecutionState.COMPLETED
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

        logger.info(f"Execution completed: {execution_id}")

    def mark_failed(self, execution_id: str, error: str):
        """
        Mark an execution as failed.

        Args:
            execution_id: Execution identifier
            error: Error message
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.state = ExecutionState.FAILED
        execution.error = error
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

        logger.info(f"Execution failed: {execution_id}")

    def pause_execution(self, execution_id: str):
        """
        Pause an execution for later resume.

        Args:
            execution_id: Execution identifier
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.state = ExecutionState.PAUSED
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

        logger.info(f"Execution paused: {execution_id}")

    def list_resumable(self) -> List[ResumableExecution]:
        """
        List all resumable executions.

        Returns:
            List of resumable executions
        """
        self._check_stale_executions()

        resumable = [
            e for e in self._executions.values()
            if e.is_resumable
        ]

        # Sort by last activity, most recent first
        resumable.sort(key=lambda e: e.last_activity, reverse=True)

        return resumable

    def list_all(
        self,
        state: Optional[ExecutionState] = None,
        limit: int = 50,
    ) -> List[ResumableExecution]:
        """
        List all tracked executions.

        Args:
            state: Filter by state
            limit: Maximum number to return

        Returns:
            List of executions
        """
        executions = list(self._executions.values())

        if state:
            executions = [e for e in executions if e.state == state]

        # Sort by last activity
        executions.sort(key=lambda e: e.last_activity, reverse=True)

        return executions[:limit]

    def get_execution(self, execution_id: str) -> Optional[ResumableExecution]:
        """
        Get a specific execution record.

        Args:
            execution_id: Execution identifier

        Returns:
            ResumableExecution if found
        """
        return self._executions.get(execution_id)

    def can_resume(self, execution_id: str) -> bool:
        """
        Check if an execution can be resumed.

        Args:
            execution_id: Execution identifier

        Returns:
            True if resumable
        """
        execution = self._executions.get(execution_id)
        return execution is not None and execution.is_resumable

    def get_resume_point(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the resume point for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Dictionary with resume information
        """
        execution = self._executions.get(execution_id)
        if not execution or not execution.is_resumable:
            return None

        return {
            "execution_id": execution_id,
            "plan_id": execution.plan_id,
            "start_from_unit_index": execution.current_unit_index,
            "start_from_unit_id": execution.current_unit_id,
            "checkpoint_hash": execution.last_checkpoint_hash,
            "completed_units": execution.completed_units,
            "remaining_units": execution.total_units - execution.completed_units,
            "last_error": execution.error,
        }

    def prepare_resume(
        self,
        execution_id: str,
        from_checkpoint: bool = True,
    ) -> ResumeResult:
        """
        Prepare an execution for resume.

        Args:
            execution_id: Execution identifier
            from_checkpoint: If True, resume from last checkpoint

        Returns:
            ResumeResult with resume information
        """
        execution = self._executions.get(execution_id)

        if not execution:
            return ResumeResult(
                success=False,
                execution_id=execution_id,
                error="Execution not found",
            )

        if not execution.is_resumable:
            return ResumeResult(
                success=False,
                execution_id=execution_id,
                error=f"Execution state is {execution.state.value}, cannot resume",
            )

        # Determine resume point
        if from_checkpoint and execution.last_checkpoint_hash:
            resumed_from = execution.last_checkpoint_unit
            checkpoint = execution.last_checkpoint_hash
            # May need to skip some units if checkpoint is before current
            skipped = 0
        else:
            resumed_from = execution.current_unit_id
            checkpoint = None
            skipped = execution.completed_units

        # Update state
        execution.state = ExecutionState.RUNNING
        execution.error = None
        execution.last_activity = datetime.now()
        self._persist_execution(execution)

        logger.info(f"Prepared resume for {execution_id} from unit {resumed_from}")

        return ResumeResult(
            success=True,
            execution_id=execution_id,
            resumed_from_unit=resumed_from,
            resumed_from_checkpoint=checkpoint,
            skipped_units=skipped,
            message=f"Ready to resume from unit {resumed_from}",
        )

    def cleanup_stale(self) -> int:
        """
        Cleanup stale executions.

        Returns:
            Number of executions cleaned up
        """
        self._check_stale_executions()

        stale = [
            e for e in self._executions.values()
            if e.state == ExecutionState.STALE
        ]

        for execution in stale:
            self._remove_execution(execution.execution_id)

        logger.info(f"Cleaned up {len(stale)} stale executions")

        return len(stale)

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        """
        Cleanup completed executions older than threshold.

        Args:
            older_than_hours: Remove completed executions older than this

        Returns:
            Number of executions cleaned up
        """
        threshold = datetime.now() - timedelta(hours=older_than_hours)

        to_remove = [
            e for e in self._executions.values()
            if e.state == ExecutionState.COMPLETED and e.last_activity < threshold
        ]

        for execution in to_remove:
            self._remove_execution(execution.execution_id)

        logger.info(f"Cleaned up {len(to_remove)} completed executions")

        return len(to_remove)

    def _check_stale_executions(self):
        """Check and mark stale executions."""
        threshold = datetime.now() - timedelta(hours=self.stale_threshold_hours)

        for execution in self._executions.values():
            if execution.state == ExecutionState.INTERRUPTED:
                if execution.last_activity < threshold:
                    execution.state = ExecutionState.STALE
                    self._persist_execution(execution)

    def _persist_execution(self, execution: ResumableExecution):
        """Persist execution state to disk."""
        file_path = self.storage_path / f"{execution.execution_id}.json"

        try:
            with open(file_path, "w") as f:
                json.dump(execution.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist execution {execution.execution_id}: {e}")

    def _load_executions(self):
        """Load executions from disk."""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    execution = ResumableExecution.from_dict(data)
                    self._executions[execution.execution_id] = execution
            except Exception as e:
                logger.warning(f"Failed to load execution {file_path}: {e}")

        # Trim if over limit
        if len(self._executions) > self.max_stored_executions:
            # Remove oldest completed/failed first
            executions = sorted(
                self._executions.values(),
                key=lambda e: (e.state in (ExecutionState.COMPLETED, ExecutionState.FAILED), e.last_activity),
            )

            to_remove = executions[:len(self._executions) - self.max_stored_executions]
            for execution in to_remove:
                self._remove_execution(execution.execution_id)

        logger.info(f"Loaded {len(self._executions)} execution records")

    def _remove_execution(self, execution_id: str):
        """Remove an execution record."""
        if execution_id in self._executions:
            del self._executions[execution_id]

        file_path = self.storage_path / f"{execution_id}.json"
        if file_path.exists():
            file_path.unlink()

    def get_statistics(self) -> Dict[str, Any]:
        """Returns resume manager statistics."""
        by_state = {}
        for state in ExecutionState:
            by_state[state.value] = len([
                e for e in self._executions.values() if e.state == state
            ])

        resumable_count = len(self.list_resumable())

        return {
            "total_tracked": len(self._executions),
            "resumable_count": resumable_count,
            "by_state": by_state,
            "storage_path": str(self.storage_path),
            "stale_threshold_hours": self.stale_threshold_hours,
            "max_stored_executions": self.max_stored_executions,
        }
