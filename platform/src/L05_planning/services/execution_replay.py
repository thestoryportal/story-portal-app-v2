"""
Execution Replay - Debug failed runs step-by-step
Path: platform/src/L05_planning/services/execution_replay.py

Features:
- Record execution frames with input/output state
- Get timeline for any execution
- Replay to specific frame
- Diff between frames
"""

import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class FrameType(Enum):
    """Types of execution frames."""
    PARSE_START = "parse_start"
    PARSE_COMPLETE = "parse_complete"
    DECOMPOSE_START = "decompose_start"
    DECOMPOSE_COMPLETE = "decompose_complete"
    UNIT_START = "unit_start"
    UNIT_CHECKPOINT = "unit_checkpoint"
    UNIT_EXECUTE = "unit_execute"
    UNIT_VALIDATE = "unit_validate"
    UNIT_SCORE = "unit_score"
    UNIT_COMPLETE = "unit_complete"
    UNIT_FAILED = "unit_failed"
    RECOVERY_START = "recovery_start"
    RECOVERY_COMPLETE = "recovery_complete"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    ERROR = "error"


@dataclass
class ExecutionFrame:
    """A single frame in the execution timeline."""
    frame_id: str
    execution_id: str
    frame_type: FrameType
    timestamp: datetime
    sequence: int  # Order in the execution

    # State at this frame
    input_state: Dict[str, Any] = field(default_factory=dict)
    output_state: Dict[str, Any] = field(default_factory=dict)

    # Context
    unit_id: Optional[str] = None
    checkpoint_hash: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert frame to dictionary for serialization."""
        return {
            "frame_id": self.frame_id,
            "execution_id": self.execution_id,
            "frame_type": self.frame_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "unit_id": self.unit_id,
            "checkpoint_hash": self.checkpoint_hash,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionFrame":
        """Create frame from dictionary."""
        return cls(
            frame_id=data["frame_id"],
            execution_id=data["execution_id"],
            frame_type=FrameType(data["frame_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sequence=data["sequence"],
            input_state=data.get("input_state", {}),
            output_state=data.get("output_state", {}),
            unit_id=data.get("unit_id"),
            checkpoint_hash=data.get("checkpoint_hash"),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FrameDiff:
    """Difference between two frames."""
    from_frame: str
    to_frame: str
    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    changed_keys: List[str] = field(default_factory=list)
    changes: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)  # key -> (old, new)


@dataclass
class ExecutionTimeline:
    """Complete timeline of an execution."""
    execution_id: str
    frames: List[ExecutionFrame] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "unknown"
    total_duration_ms: int = 0

    @property
    def frame_count(self) -> int:
        """Total number of frames."""
        return len(self.frames)

    @property
    def error_frames(self) -> List[ExecutionFrame]:
        """Get all error frames."""
        return [f for f in self.frames if f.frame_type in (FrameType.ERROR, FrameType.UNIT_FAILED, FrameType.EXECUTION_FAILED)]


class ExecutionReplay:
    """
    Debug failed runs step-by-step.

    Features:
    - Record execution frames with input/output state
    - Get timeline for any execution
    - Replay to specific frame
    - Diff between frames
    - Persist frames to disk for later analysis
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_frames_per_execution: int = 1000,
        persist_frames: bool = True,
    ):
        """
        Initialize execution replay.

        Args:
            storage_path: Path for persisting frames
            max_frames_per_execution: Maximum frames to keep per execution
            persist_frames: Whether to persist frames to disk
        """
        self.storage_path = Path(storage_path) if storage_path else Path.cwd() / ".l05_replay"
        self.max_frames_per_execution = max_frames_per_execution
        self.persist_frames = persist_frames

        # In-memory storage
        self._frames: Dict[str, List[ExecutionFrame]] = {}  # execution_id -> frames
        self._sequence_counters: Dict[str, int] = {}  # execution_id -> current sequence

        # Ensure storage directory exists
        if self.persist_frames:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def record_frame(
        self,
        execution_id: str,
        frame_type: FrameType,
        input_state: Optional[Dict[str, Any]] = None,
        output_state: Optional[Dict[str, Any]] = None,
        unit_id: Optional[str] = None,
        checkpoint_hash: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionFrame:
        """
        Record a new execution frame.

        Args:
            execution_id: Execution identifier
            frame_type: Type of frame
            input_state: State before this frame
            output_state: State after this frame
            unit_id: Associated unit ID
            checkpoint_hash: Associated checkpoint hash
            error: Error message if any
            duration_ms: Duration of this step
            metadata: Additional metadata

        Returns:
            Recorded ExecutionFrame
        """
        # Get sequence number
        if execution_id not in self._sequence_counters:
            self._sequence_counters[execution_id] = 0

        sequence = self._sequence_counters[execution_id]
        self._sequence_counters[execution_id] += 1

        frame = ExecutionFrame(
            frame_id=f"{execution_id}-{sequence:04d}",
            execution_id=execution_id,
            frame_type=frame_type,
            timestamp=datetime.now(),
            sequence=sequence,
            input_state=copy.deepcopy(input_state) if input_state else {},
            output_state=copy.deepcopy(output_state) if output_state else {},
            unit_id=unit_id,
            checkpoint_hash=checkpoint_hash,
            error=error,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        # Store in memory
        if execution_id not in self._frames:
            self._frames[execution_id] = []

        self._frames[execution_id].append(frame)

        # Trim if over limit
        if len(self._frames[execution_id]) > self.max_frames_per_execution:
            self._frames[execution_id] = self._frames[execution_id][-self.max_frames_per_execution:]

        # Persist if enabled
        if self.persist_frames:
            self._persist_frame(frame)

        logger.debug(f"Recorded frame: {frame.frame_id} ({frame_type.value})")

        return frame

    def get_timeline(self, execution_id: str) -> ExecutionTimeline:
        """
        Get the complete timeline for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            ExecutionTimeline with all frames
        """
        frames = self._frames.get(execution_id, [])

        # Try loading from disk if not in memory
        if not frames and self.persist_frames:
            frames = self._load_frames(execution_id)
            if frames:
                self._frames[execution_id] = frames

        if not frames:
            return ExecutionTimeline(execution_id=execution_id, status="not_found")

        # Sort by sequence
        frames = sorted(frames, key=lambda f: f.sequence)

        # Determine status
        if any(f.frame_type == FrameType.EXECUTION_COMPLETE for f in frames):
            status = "completed"
        elif any(f.frame_type == FrameType.EXECUTION_FAILED for f in frames):
            status = "failed"
        elif any(f.frame_type == FrameType.ERROR for f in frames):
            status = "error"
        else:
            status = "in_progress"

        # Calculate duration
        started_at = frames[0].timestamp if frames else None
        completed_at = frames[-1].timestamp if frames else None
        total_duration_ms = sum(f.duration_ms for f in frames)

        return ExecutionTimeline(
            execution_id=execution_id,
            frames=frames,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            total_duration_ms=total_duration_ms,
        )

    def get_frame(self, execution_id: str, sequence: int) -> Optional[ExecutionFrame]:
        """
        Get a specific frame by sequence number.

        Args:
            execution_id: Execution identifier
            sequence: Frame sequence number

        Returns:
            ExecutionFrame if found
        """
        frames = self._frames.get(execution_id, [])
        for frame in frames:
            if frame.sequence == sequence:
                return frame
        return None

    def get_frame_by_id(self, frame_id: str) -> Optional[ExecutionFrame]:
        """
        Get a frame by its ID.

        Args:
            frame_id: Frame identifier

        Returns:
            ExecutionFrame if found
        """
        # Parse execution_id from frame_id
        parts = frame_id.rsplit("-", 1)
        if len(parts) != 2:
            return None

        execution_id = parts[0]
        try:
            sequence = int(parts[1])
        except ValueError:
            return None

        return self.get_frame(execution_id, sequence)

    def replay_to_frame(
        self,
        execution_id: str,
        target_sequence: int,
    ) -> Tuple[Optional[ExecutionFrame], Dict[str, Any]]:
        """
        Replay execution to a specific frame, returning the state at that point.

        Args:
            execution_id: Execution identifier
            target_sequence: Target frame sequence

        Returns:
            Tuple of (target frame, accumulated state)
        """
        frames = self._frames.get(execution_id, [])
        frames = sorted(frames, key=lambda f: f.sequence)

        if not frames:
            return None, {}

        # Accumulate state up to target
        accumulated_state: Dict[str, Any] = {}
        target_frame = None

        for frame in frames:
            if frame.sequence > target_sequence:
                break

            # Apply output state
            accumulated_state.update(frame.output_state)
            target_frame = frame

        return target_frame, accumulated_state

    def diff_frames(
        self,
        execution_id: str,
        from_sequence: int,
        to_sequence: int,
    ) -> Optional[FrameDiff]:
        """
        Get the difference between two frames.

        Args:
            execution_id: Execution identifier
            from_sequence: Starting frame sequence
            to_sequence: Ending frame sequence

        Returns:
            FrameDiff with changes
        """
        from_frame = self.get_frame(execution_id, from_sequence)
        to_frame = self.get_frame(execution_id, to_sequence)

        if not from_frame or not to_frame:
            return None

        from_state = from_frame.output_state
        to_state = to_frame.output_state

        # Calculate differences
        from_keys = set(from_state.keys())
        to_keys = set(to_state.keys())

        added_keys = list(to_keys - from_keys)
        removed_keys = list(from_keys - to_keys)
        common_keys = from_keys & to_keys

        changed_keys = []
        changes = {}

        for key in common_keys:
            if from_state[key] != to_state[key]:
                changed_keys.append(key)
                changes[key] = (from_state[key], to_state[key])

        return FrameDiff(
            from_frame=from_frame.frame_id,
            to_frame=to_frame.frame_id,
            added_keys=added_keys,
            removed_keys=removed_keys,
            changed_keys=changed_keys,
            changes=changes,
        )

    def get_frames_by_type(
        self,
        execution_id: str,
        frame_type: FrameType,
    ) -> List[ExecutionFrame]:
        """
        Get all frames of a specific type.

        Args:
            execution_id: Execution identifier
            frame_type: Type of frames to get

        Returns:
            List of matching frames
        """
        frames = self._frames.get(execution_id, [])
        return [f for f in frames if f.frame_type == frame_type]

    def get_unit_frames(
        self,
        execution_id: str,
        unit_id: str,
    ) -> List[ExecutionFrame]:
        """
        Get all frames for a specific unit.

        Args:
            execution_id: Execution identifier
            unit_id: Unit identifier

        Returns:
            List of frames for the unit
        """
        frames = self._frames.get(execution_id, [])
        return sorted(
            [f for f in frames if f.unit_id == unit_id],
            key=lambda f: f.sequence,
        )

    def get_error_context(
        self,
        execution_id: str,
        context_frames: int = 5,
    ) -> List[ExecutionFrame]:
        """
        Get frames around the first error for debugging.

        Args:
            execution_id: Execution identifier
            context_frames: Number of frames before error to include

        Returns:
            List of frames around the error
        """
        frames = self._frames.get(execution_id, [])
        frames = sorted(frames, key=lambda f: f.sequence)

        # Find first error frame
        error_idx = None
        for i, frame in enumerate(frames):
            if frame.frame_type in (FrameType.ERROR, FrameType.UNIT_FAILED, FrameType.EXECUTION_FAILED):
                error_idx = i
                break

        if error_idx is None:
            return []

        # Get context
        start_idx = max(0, error_idx - context_frames)
        end_idx = min(len(frames), error_idx + 2)  # Include error and one after

        return frames[start_idx:end_idx]

    def _persist_frame(self, frame: ExecutionFrame):
        """Persist a frame to disk."""
        execution_dir = self.storage_path / frame.execution_id
        execution_dir.mkdir(parents=True, exist_ok=True)

        frame_file = execution_dir / f"{frame.sequence:04d}.json"

        try:
            with open(frame_file, "w") as f:
                json.dump(frame.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to persist frame {frame.frame_id}: {e}")

    def _load_frames(self, execution_id: str) -> List[ExecutionFrame]:
        """Load frames from disk."""
        execution_dir = self.storage_path / execution_id
        if not execution_dir.exists():
            return []

        frames = []
        for frame_file in sorted(execution_dir.glob("*.json")):
            try:
                with open(frame_file) as f:
                    data = json.load(f)
                    frames.append(ExecutionFrame.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load frame {frame_file}: {e}")

        return frames

    def clear_execution(self, execution_id: str):
        """
        Clear all frames for an execution.

        Args:
            execution_id: Execution identifier
        """
        if execution_id in self._frames:
            del self._frames[execution_id]

        if execution_id in self._sequence_counters:
            del self._sequence_counters[execution_id]

        # Clear from disk
        execution_dir = self.storage_path / execution_id
        if execution_dir.exists():
            import shutil
            shutil.rmtree(execution_dir)

        logger.info(f"Cleared frames for execution: {execution_id}")

    def list_executions(self) -> List[str]:
        """
        List all executions with recorded frames.

        Returns:
            List of execution IDs
        """
        executions = set(self._frames.keys())

        # Add from disk
        if self.persist_frames and self.storage_path.exists():
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    executions.add(item.name)

        return sorted(executions)

    def get_statistics(self) -> Dict[str, Any]:
        """Returns replay statistics."""
        total_frames = sum(len(frames) for frames in self._frames.values())
        execution_count = len(self._frames)

        return {
            "total_frames": total_frames,
            "execution_count": execution_count,
            "storage_path": str(self.storage_path),
            "persist_frames": self.persist_frames,
            "max_frames_per_execution": self.max_frames_per_execution,
        }
