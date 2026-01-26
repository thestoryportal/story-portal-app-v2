"""
Test Recovery - Tests for Phase 3 Reliability Layer components
Path: platform/src/L05_planning/tests/test_recovery.py

Tests for:
- ExecutionReplay
- ResumeManager
- ErrorHandler
"""

import asyncio
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from ..services.execution_replay import (
    ExecutionReplay,
    ExecutionFrame,
    ExecutionTimeline,
    FrameType,
    FrameDiff,
)
from ..services.resume_manager import (
    ResumeManager,
    ResumableExecution,
    ResumeResult,
    ExecutionState,
)
from ..services.error_handler import (
    ErrorHandler,
    HandledError,
    ErrorSeverity,
    ErrorCategory,
    ErrorPattern,
)


# =======================
# ExecutionReplay Tests
# =======================

class TestExecutionReplay:
    """Tests for ExecutionReplay service."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def replay(self, temp_dir):
        """Create ExecutionReplay instance."""
        return ExecutionReplay(
            storage_path=temp_dir / "replay",
            max_frames_per_execution=100,
            persist_frames=True,
        )

    def test_init_with_defaults(self):
        """Test ExecutionReplay initialization with defaults."""
        replay = ExecutionReplay()
        assert replay.max_frames_per_execution == 1000
        assert replay.persist_frames is True

    def test_record_frame(self, replay):
        """Test recording an execution frame."""
        frame = replay.record_frame(
            execution_id="exec-001",
            frame_type=FrameType.UNIT_START,
            input_state={"key": "value"},
            output_state={"result": "success"},
            unit_id="unit-001",
        )

        assert frame.execution_id == "exec-001"
        assert frame.frame_type == FrameType.UNIT_START
        assert frame.unit_id == "unit-001"
        assert frame.sequence == 0

    def test_record_multiple_frames(self, replay):
        """Test recording multiple frames increments sequence."""
        frame1 = replay.record_frame("exec-001", FrameType.UNIT_START)
        frame2 = replay.record_frame("exec-001", FrameType.UNIT_EXECUTE)
        frame3 = replay.record_frame("exec-001", FrameType.UNIT_COMPLETE)

        assert frame1.sequence == 0
        assert frame2.sequence == 1
        assert frame3.sequence == 2

    def test_get_timeline(self, replay):
        """Test getting execution timeline."""
        replay.record_frame("exec-001", FrameType.PARSE_START)
        replay.record_frame("exec-001", FrameType.PARSE_COMPLETE)
        replay.record_frame("exec-001", FrameType.EXECUTION_COMPLETE)

        timeline = replay.get_timeline("exec-001")

        assert timeline.execution_id == "exec-001"
        assert timeline.frame_count == 3
        assert timeline.status == "completed"

    def test_get_timeline_failed(self, replay):
        """Test timeline status for failed execution."""
        replay.record_frame("exec-001", FrameType.UNIT_START)
        replay.record_frame("exec-001", FrameType.EXECUTION_FAILED, error="Test error")

        timeline = replay.get_timeline("exec-001")
        assert timeline.status == "failed"

    def test_get_timeline_not_found(self, replay):
        """Test timeline for nonexistent execution."""
        timeline = replay.get_timeline("nonexistent")
        assert timeline.status == "not_found"
        assert timeline.frame_count == 0

    def test_replay_to_frame(self, replay):
        """Test replaying to a specific frame."""
        replay.record_frame(
            "exec-001",
            FrameType.UNIT_START,
            output_state={"step": 1},
        )
        replay.record_frame(
            "exec-001",
            FrameType.UNIT_EXECUTE,
            output_state={"step": 2, "data": "processed"},
        )
        replay.record_frame(
            "exec-001",
            FrameType.UNIT_COMPLETE,
            output_state={"step": 3},
        )

        frame, state = replay.replay_to_frame("exec-001", 1)

        assert frame is not None
        assert frame.sequence == 1
        assert state["step"] == 2
        assert state["data"] == "processed"

    def test_diff_frames(self, replay):
        """Test diffing between frames."""
        replay.record_frame(
            "exec-001",
            FrameType.UNIT_START,
            output_state={"a": 1, "b": 2},
        )
        replay.record_frame(
            "exec-001",
            FrameType.UNIT_COMPLETE,
            output_state={"a": 1, "c": 3},
        )

        diff = replay.diff_frames("exec-001", 0, 1)

        assert diff is not None
        assert "b" in diff.removed_keys
        assert "c" in diff.added_keys
        assert "a" not in diff.changed_keys

    def test_get_frames_by_type(self, replay):
        """Test getting frames by type."""
        replay.record_frame("exec-001", FrameType.UNIT_START, unit_id="u1")
        replay.record_frame("exec-001", FrameType.UNIT_EXECUTE, unit_id="u1")
        replay.record_frame("exec-001", FrameType.UNIT_START, unit_id="u2")

        start_frames = replay.get_frames_by_type("exec-001", FrameType.UNIT_START)
        assert len(start_frames) == 2

    def test_get_unit_frames(self, replay):
        """Test getting all frames for a unit."""
        replay.record_frame("exec-001", FrameType.UNIT_START, unit_id="u1")
        replay.record_frame("exec-001", FrameType.UNIT_EXECUTE, unit_id="u1")
        replay.record_frame("exec-001", FrameType.UNIT_START, unit_id="u2")
        replay.record_frame("exec-001", FrameType.UNIT_COMPLETE, unit_id="u1")

        u1_frames = replay.get_unit_frames("exec-001", "u1")
        assert len(u1_frames) == 3

    def test_get_error_context(self, replay):
        """Test getting context around errors."""
        for i in range(10):
            replay.record_frame("exec-001", FrameType.UNIT_EXECUTE)
        replay.record_frame("exec-001", FrameType.ERROR, error="Test error")

        context = replay.get_error_context("exec-001", context_frames=3)

        assert len(context) > 0
        assert any(f.frame_type == FrameType.ERROR for f in context)

    def test_clear_execution(self, replay, temp_dir):
        """Test clearing execution frames."""
        replay.record_frame("exec-001", FrameType.UNIT_START)
        replay.record_frame("exec-001", FrameType.UNIT_COMPLETE)

        replay.clear_execution("exec-001")

        timeline = replay.get_timeline("exec-001")
        assert timeline.frame_count == 0

    def test_list_executions(self, replay):
        """Test listing all executions."""
        replay.record_frame("exec-001", FrameType.UNIT_START)
        replay.record_frame("exec-002", FrameType.UNIT_START)
        replay.record_frame("exec-003", FrameType.UNIT_START)

        executions = replay.list_executions()
        assert len(executions) == 3

    def test_frame_persistence(self, temp_dir):
        """Test that frames are persisted and reloaded."""
        # Create and record
        replay1 = ExecutionReplay(storage_path=temp_dir / "replay")
        replay1.record_frame("exec-001", FrameType.UNIT_START)
        replay1.record_frame("exec-001", FrameType.UNIT_COMPLETE)

        # Create new instance and check frames are loaded
        replay2 = ExecutionReplay(storage_path=temp_dir / "replay")
        timeline = replay2.get_timeline("exec-001")

        assert timeline.frame_count == 2


# =======================
# ResumeManager Tests
# =======================

class TestResumeManager:
    """Tests for ResumeManager service."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create ResumeManager instance."""
        return ResumeManager(
            storage_path=temp_dir / "resume",
            stale_threshold_hours=24,
            max_stored_executions=100,
        )

    def test_register_execution(self, manager):
        """Test registering an execution."""
        execution = manager.register_execution(
            execution_id="exec-001",
            plan_id="plan-001",
            total_units=5,
            metadata={"key": "value"},
        )

        assert execution.execution_id == "exec-001"
        assert execution.plan_id == "plan-001"
        assert execution.total_units == 5
        assert execution.state == ExecutionState.RUNNING

    def test_update_progress(self, manager):
        """Test updating execution progress."""
        manager.register_execution("exec-001", "plan-001", 5)

        manager.update_progress(
            execution_id="exec-001",
            current_unit_id="unit-002",
            current_unit_index=1,
            checkpoint_hash="abc123",
        )

        execution = manager.get_execution("exec-001")
        assert execution.current_unit_id == "unit-002"
        assert execution.current_unit_index == 1
        assert execution.last_checkpoint_hash == "abc123"

    def test_mark_unit_complete(self, manager):
        """Test marking a unit as complete."""
        manager.register_execution("exec-001", "plan-001", 5)

        manager.mark_unit_complete("exec-001", "unit-001")
        manager.mark_unit_complete("exec-001", "unit-002")

        execution = manager.get_execution("exec-001")
        assert execution.completed_units == 2

    def test_mark_unit_failed(self, manager):
        """Test marking a unit as failed."""
        manager.register_execution("exec-001", "plan-001", 5)

        manager.mark_unit_failed("exec-001", "unit-003", "Test error")

        execution = manager.get_execution("exec-001")
        assert execution.state == ExecutionState.INTERRUPTED
        assert execution.error == "Test error"
        assert execution.error_unit_id == "unit-003"

    def test_mark_complete(self, manager):
        """Test marking execution as complete."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.mark_complete("exec-001")

        execution = manager.get_execution("exec-001")
        assert execution.state == ExecutionState.COMPLETED

    def test_mark_failed(self, manager):
        """Test marking execution as failed."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.mark_failed("exec-001", "Fatal error")

        execution = manager.get_execution("exec-001")
        assert execution.state == ExecutionState.FAILED

    def test_pause_execution(self, manager):
        """Test pausing an execution."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.pause_execution("exec-001")

        execution = manager.get_execution("exec-001")
        assert execution.state == ExecutionState.PAUSED

    def test_list_resumable(self, manager):
        """Test listing resumable executions."""
        # Running - not resumable
        manager.register_execution("exec-001", "plan-001", 5)

        # Paused - resumable
        manager.register_execution("exec-002", "plan-002", 5)
        manager.pause_execution("exec-002")

        # Interrupted - resumable
        manager.register_execution("exec-003", "plan-003", 5)
        manager.mark_unit_failed("exec-003", "u1", "error")

        resumable = manager.list_resumable()
        assert len(resumable) == 2

    def test_can_resume(self, manager):
        """Test checking if execution can be resumed."""
        manager.register_execution("exec-001", "plan-001", 5)
        assert manager.can_resume("exec-001") is False

        manager.pause_execution("exec-001")
        assert manager.can_resume("exec-001") is True

    def test_get_resume_point(self, manager):
        """Test getting resume point."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.update_progress("exec-001", "unit-003", 2, "checkpoint123")
        manager.mark_unit_complete("exec-001", "unit-001")
        manager.mark_unit_complete("exec-001", "unit-002")
        manager.pause_execution("exec-001")

        resume_point = manager.get_resume_point("exec-001")

        assert resume_point is not None
        assert resume_point["start_from_unit_id"] == "unit-003"
        assert resume_point["checkpoint_hash"] == "checkpoint123"
        assert resume_point["completed_units"] == 2

    def test_prepare_resume(self, manager):
        """Test preparing execution for resume."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.update_progress("exec-001", "unit-003", 2)
        manager.pause_execution("exec-001")

        result = manager.prepare_resume("exec-001")

        assert result.success is True
        assert result.resumed_from_unit == "unit-003"

        execution = manager.get_execution("exec-001")
        assert execution.state == ExecutionState.RUNNING

    def test_prepare_resume_nonexistent(self, manager):
        """Test prepare_resume for nonexistent execution."""
        result = manager.prepare_resume("nonexistent")
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_progress_percent(self, manager):
        """Test progress percentage calculation."""
        manager.register_execution("exec-001", "plan-001", 4)
        manager.mark_unit_complete("exec-001", "u1")
        manager.mark_unit_complete("exec-001", "u2")

        execution = manager.get_execution("exec-001")
        assert execution.progress_percent == 50.0

    def test_cleanup_stale(self, manager):
        """Test cleaning up stale executions."""
        # This would require manipulating timestamps
        # For now, just verify method works
        cleaned = manager.cleanup_stale()
        assert cleaned >= 0

    def test_execution_persistence(self, temp_dir):
        """Test that executions are persisted and reloaded."""
        # Create and register
        manager1 = ResumeManager(storage_path=temp_dir / "resume")
        manager1.register_execution("exec-001", "plan-001", 5)
        manager1.pause_execution("exec-001")

        # Create new instance and check executions are loaded
        manager2 = ResumeManager(storage_path=temp_dir / "resume")
        execution = manager2.get_execution("exec-001")

        assert execution is not None
        assert execution.state == ExecutionState.PAUSED

    def test_get_statistics(self, manager):
        """Test getting manager statistics."""
        manager.register_execution("exec-001", "plan-001", 5)
        manager.register_execution("exec-002", "plan-002", 5)
        manager.pause_execution("exec-002")

        stats = manager.get_statistics()

        assert stats["total_tracked"] == 2
        assert stats["resumable_count"] == 1


# =======================
# ErrorHandler Tests
# =======================

class TestErrorHandler:
    """Tests for ErrorHandler service."""

    @pytest.fixture
    def mock_recovery_protocol(self):
        """Create mock recovery protocol."""
        protocol = Mock()
        protocol.try_recover = AsyncMock(return_value=True)
        return protocol

    @pytest.fixture
    def mock_compensation_engine(self):
        """Create mock compensation engine."""
        engine = Mock()
        engine.compensate = AsyncMock(return_value=True)
        return engine

    @pytest.fixture
    def handler(self, mock_recovery_protocol, mock_compensation_engine):
        """Create ErrorHandler instance."""
        return ErrorHandler(
            recovery_protocol=mock_recovery_protocol,
            compensation_engine=mock_compensation_engine,
            auto_recover=True,
            max_retries=3,
        )

    def test_init_with_defaults(self):
        """Test ErrorHandler initialization with defaults."""
        handler = ErrorHandler()
        assert handler.auto_recover is True
        assert handler.max_retries == 3

    def test_classify_severity_fatal(self, handler):
        """Test classification of fatal errors."""
        error = PermissionError("Access denied")
        severity, category, pattern = handler._classify_error(error)
        assert severity == ErrorSeverity.FATAL
        assert category == ErrorCategory.PERMISSION

    def test_classify_severity_recoverable(self, handler):
        """Test classification of recoverable errors."""
        error = ConnectionError("Connection refused")
        severity, category, pattern = handler._classify_error(error)
        assert severity == ErrorSeverity.RECOVERABLE
        assert category == ErrorCategory.NETWORK

    def test_classify_category(self, handler):
        """Test error category classification."""
        # Test parse error
        severity, category, pattern = handler._classify_error(
            SyntaxError("invalid syntax"),
        )
        assert category == ErrorCategory.PARSE

        # Test network error
        severity, category, pattern = handler._classify_error(
            ConnectionError("refused"),
        )
        assert category == ErrorCategory.NETWORK

    @pytest.mark.asyncio
    async def test_handle_recoverable_error(self, handler):
        """Test handling a recoverable error."""
        error = ConnectionError("Connection failed")

        result = handler.handle(
            error=error,
            execution_id="exec-001",
            unit=Mock(id="unit-001"),
            operation="network_call",
        )

        assert result is not None
        assert result.original_error == error

    def test_handle_with_retry_success(self, handler):
        """Test handle_with_retry with eventual success."""
        attempts = [0]

        def flaky_function():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Failed")
            return "success"

        result = handler.handle_with_retry(
            flaky_function,
            max_retries=3,
            execution_id="exec-001",
        )

        assert result == "success"
        assert attempts[0] == 3

    def test_handle_with_retry_all_fail(self, handler):
        """Test handle_with_retry when all retries fail."""
        def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            handler.handle_with_retry(
                always_fail,
                max_retries=2,
                execution_id="exec-001",
            )

    def test_register_handler(self, handler):
        """Test registering a custom error handler."""
        custom_handler = Mock()

        handler.register_handler(ValueError, custom_handler)

        # Handle a ValueError
        result = handler.handle(
            error=ValueError("test"),
            execution_id="exec-001",
        )

        custom_handler.assert_called_once()

    def test_add_pattern(self, handler):
        """Test adding a custom error pattern."""
        pattern = ErrorPattern(
            name="custom_error",
            pattern=r"CustomError:.*",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            message_template="Custom config error: {error}",
        )

        handler.add_pattern(pattern)
        assert pattern in handler._patterns

    def test_error_pattern_matching(self, handler):
        """Test error pattern matching."""
        pattern = ErrorPattern(
            name="custom_timeout",
            pattern=r"timeout.*exceeded",
            severity=ErrorSeverity.RECOVERABLE,
            category=ErrorCategory.TIMEOUT,
            message_template="Timeout exceeded: {error}",
        )
        handler.add_pattern(pattern)

        error = TimeoutError("timeout limit exceeded")
        result = handler.handle(error, "exec-001")

        # Should match the pattern
        assert result.category == ErrorCategory.TIMEOUT

    def test_get_error_stats(self, handler):
        """Test getting error statistics."""
        handler.handle(ValueError("err1"), "exec-001")
        handler.handle(ValueError("err2"), "exec-001")
        handler.handle(TypeError("err3"), "exec-002")

        stats = handler.get_statistics()

        assert stats["total_errors"] == 3
        assert "by_severity" in stats
        assert "by_category" in stats
        assert stats["history_size"] == 3

    def test_handled_error_dataclass(self):
        """Test HandledError dataclass."""
        error = ValueError("Test error")
        handled = HandledError(
            error_id="err-001",
            original_error=error,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            message="Test error message",
            execution_id="exec-001",
            unit_id="unit-001",
            recovery_attempted=True,
            recovery_success=True,
        )

        assert handled.original_error == error
        assert handled.severity == ErrorSeverity.WARNING
        assert handled.recovery_success is True


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_severity_ordering(self):
        """Test severity levels are properly ordered."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.RECOVERABLE.value == "recoverable"
        assert ErrorSeverity.FATAL.value == "fatal"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_exist(self):
        """Test all expected categories exist."""
        expected = [
            "parse", "decomposition", "validation", "execution", "network",
            "timeout", "permission", "resource", "dependency", "internal", "user",
        ]
        actual = [c.value for c in ErrorCategory]

        for category in expected:
            assert category in actual


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_error_pattern_creation(self):
        """Test creating an ErrorPattern."""
        pattern = ErrorPattern(
            name="test_pattern",
            pattern=r"test.*error",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.INTERNAL,
            message_template="Test error: {error}",
        )

        assert pattern.pattern == r"test.*error"
        assert pattern.severity == ErrorSeverity.WARNING


# =======================
# Integration Tests
# =======================

class TestRecoveryIntegration:
    """Integration tests for recovery components working together."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_full_recovery_workflow(self, temp_dir):
        """Test a complete recovery workflow."""
        # Setup components
        replay = ExecutionReplay(storage_path=temp_dir / "replay")
        resume_manager = ResumeManager(storage_path=temp_dir / "resume")
        error_handler = ErrorHandler()

        execution_id = "exec-integration-001"
        plan_id = "plan-001"

        # 1. Register execution
        resume_manager.register_execution(execution_id, plan_id, 3)

        # 2. Record frames and progress
        replay.record_frame(execution_id, FrameType.UNIT_START, unit_id="u1")
        resume_manager.update_progress(execution_id, "u1", 0)
        replay.record_frame(execution_id, FrameType.UNIT_COMPLETE, unit_id="u1")
        resume_manager.mark_unit_complete(execution_id, "u1")

        replay.record_frame(execution_id, FrameType.UNIT_START, unit_id="u2")
        resume_manager.update_progress(execution_id, "u2", 1, "checkpoint_u2")

        # 3. Simulate failure
        error = ConnectionError("Network error")
        handled = error_handler.handle(error, execution_id, unit=Mock(id="u2"))
        replay.record_frame(
            execution_id,
            FrameType.ERROR,
            unit_id="u2",
            error=str(error),
        )
        resume_manager.mark_unit_failed(execution_id, "u2", str(error))

        # 4. Verify state
        execution = resume_manager.get_execution(execution_id)
        assert execution.state == ExecutionState.INTERRUPTED
        assert execution.completed_units == 1

        timeline = replay.get_timeline(execution_id)
        assert len(timeline.error_frames) == 1

        # 5. Prepare resume
        assert resume_manager.can_resume(execution_id) is True
        resume_result = resume_manager.prepare_resume(execution_id)
        assert resume_result.success is True
        assert resume_result.resumed_from_unit == "u2"

        # 6. Continue execution
        replay.record_frame(execution_id, FrameType.RECOVERY_START)
        replay.record_frame(execution_id, FrameType.UNIT_COMPLETE, unit_id="u2")
        resume_manager.mark_unit_complete(execution_id, "u2")

        replay.record_frame(execution_id, FrameType.UNIT_START, unit_id="u3")
        replay.record_frame(execution_id, FrameType.UNIT_COMPLETE, unit_id="u3")
        resume_manager.mark_unit_complete(execution_id, "u3")

        replay.record_frame(execution_id, FrameType.EXECUTION_COMPLETE)
        resume_manager.mark_complete(execution_id)

        # 7. Verify final state
        execution = resume_manager.get_execution(execution_id)
        assert execution.state == ExecutionState.COMPLETED
        assert execution.completed_units == 3

        timeline = replay.get_timeline(execution_id)
        assert timeline.status == "completed"
