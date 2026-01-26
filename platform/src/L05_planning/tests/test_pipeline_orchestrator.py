"""
Test Pipeline Orchestrator - Tests for PipelineOrchestrator service
Path: platform/src/L05_planning/tests/test_pipeline_orchestrator.py
"""

import asyncio
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from ..services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStatus,
    UnitResult,
    ExecutionContext,
)
from ..services.unit_executor import ExecutionResult, ExecutionStatus
from ..parsers.base_parser import ParsedPlan, PlanStep
from ..parsers.format_detector import FormatType
from ..agents.spec_decomposer import AtomicUnit, AcceptanceCriterion
from ..agents.unit_validator import ValidationResult, ValidationStatus
from ..integration.l06_bridge import UnitScore, PlanScore, AssessmentLevel


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_parser():
    """Create a mock parser."""
    parser = Mock()
    parser.parse.return_value = ParsedPlan(
        plan_id="plan-001",
        title="Test Plan",
        format_type=FormatType.PHASE_BASED,
        steps=[PlanStep(id="step-1", title="Step 1", description="Do something")],
    )
    return parser


@pytest.fixture
def mock_decomposer():
    """Create a mock decomposer."""
    decomposer = Mock()
    decomposer.decompose.return_value = [
        AtomicUnit(
            id="unit-001",
            title="Test Unit",
            description="Test description",
            files=["test.py"],
            complexity=1,
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="ac-001",
                    description="File exists",
                    validation_command="test -f test.py",
                    timeout_seconds=5,
                )
            ],
            dependencies=[],
        )
    ]
    decomposer.get_execution_order.return_value = decomposer.decompose.return_value
    return decomposer


@pytest.fixture
def mock_validator():
    """Create a mock validator."""
    validator = Mock()
    validator.validate.return_value = ValidationResult(
        unit_id="unit-001",
        status=ValidationStatus.PASSED,
        passed=True,
        criterion_results=[],
    )
    return validator


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = Mock()
    executor.execute = AsyncMock(return_value=ExecutionResult(
        unit_id="unit-001",
        status=ExecutionStatus.SUCCESS,
        execution_type=Mock(value="file_create"),
        output="Success",
    ))
    return executor


@pytest.fixture
def mock_checkpoint_manager():
    """Create a mock checkpoint manager."""
    manager = Mock()
    checkpoint = Mock()
    checkpoint.hash = "abc123"
    checkpoint.checkpoint_id = "cp-001"
    manager.create_checkpoint.return_value = checkpoint
    manager.get_checkpoint.return_value = checkpoint
    manager.restore_checkpoint.return_value = True
    return manager


@pytest.fixture
def mock_recovery_protocol():
    """Create a mock recovery protocol."""
    return Mock()


@pytest.fixture
def mock_l01_bridge():
    """Create a mock L01 bridge."""
    bridge = Mock()
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.store_plan_async = AsyncMock()
    bridge.store_unit_async = AsyncMock()
    bridge.store_execution_async = AsyncMock()
    bridge.store_validation_async = AsyncMock()
    bridge.is_connected.return_value = True
    return bridge


@pytest.fixture
def mock_l04_bridge():
    """Create a mock L04 bridge."""
    bridge = Mock()
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.is_connected.return_value = True
    return bridge


@pytest.fixture
def mock_l06_bridge():
    """Create a mock L06 bridge."""
    bridge = Mock()
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.score_unit_async = AsyncMock(return_value=UnitScore(
        unit_id="unit-001",
        score=85.0,
        assessment=AssessmentLevel.GOOD,
    ))
    bridge.is_connected.return_value = True
    return bridge


@pytest.fixture
def mock_l11_bridge():
    """Create a mock L11 bridge."""
    bridge = Mock()
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.publish_plan_started = AsyncMock()
    bridge.publish_plan_completed = AsyncMock()
    bridge.publish_plan_failed = AsyncMock()
    bridge.publish_unit_started = AsyncMock()
    bridge.publish_unit_completed = AsyncMock()
    bridge.publish_unit_failed = AsyncMock()
    bridge.publish_event = AsyncMock()
    bridge.is_connected.return_value = True
    return bridge


@pytest.fixture
def orchestrator(
    temp_dir,
    mock_parser,
    mock_decomposer,
    mock_validator,
    mock_executor,
    mock_checkpoint_manager,
    mock_recovery_protocol,
    mock_l01_bridge,
    mock_l04_bridge,
    mock_l06_bridge,
    mock_l11_bridge,
):
    """Create a PipelineOrchestrator with mocked dependencies."""
    return PipelineOrchestrator(
        working_dir=temp_dir,
        parser=mock_parser,
        decomposer=mock_decomposer,
        validator=mock_validator,
        executor=mock_executor,
        checkpoint_manager=mock_checkpoint_manager,
        recovery_protocol=mock_recovery_protocol,
        l01_bridge=mock_l01_bridge,
        l04_bridge=mock_l04_bridge,
        l06_bridge=mock_l06_bridge,
        l11_bridge=mock_l11_bridge,
    )


class TestPipelineOrchestratorInit:
    """Tests for PipelineOrchestrator initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        orchestrator = PipelineOrchestrator()
        assert orchestrator.working_dir == Path.cwd()
        assert orchestrator.parser is not None
        assert orchestrator.decomposer is not None

    def test_init_with_custom_working_dir(self, temp_dir):
        """Test initialization with custom working directory."""
        orchestrator = PipelineOrchestrator(working_dir=temp_dir)
        assert orchestrator.working_dir == temp_dir


class TestPipelineInitialization:
    """Tests for pipeline initialization."""

    @pytest.mark.asyncio
    async def test_initialize_bridges(self, orchestrator):
        """Test that all bridges are initialized."""
        await orchestrator.initialize()

        orchestrator.l01_bridge.initialize.assert_called_once()
        orchestrator.l04_bridge.initialize.assert_called_once()
        orchestrator.l06_bridge.initialize.assert_called_once()
        orchestrator.l11_bridge.initialize.assert_called_once()
        assert orchestrator._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, orchestrator):
        """Test that initialization is idempotent."""
        await orchestrator.initialize()
        await orchestrator.initialize()

        # Should only initialize once
        assert orchestrator.l01_bridge.initialize.call_count == 1


class TestPlanExecution:
    """Tests for plan execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_plan(self, orchestrator):
        """Test execution of a simple plan."""
        markdown = "## Phase 1\n- Step 1: Create test file"

        result = await orchestrator.execute_plan_markdown(markdown)

        assert result.status == PipelineStatus.COMPLETED
        assert result.total_units == 1
        assert result.passed_units == 1
        assert result.failed_units == 0
        assert result.average_score == 85.0

    @pytest.mark.asyncio
    async def test_execute_plan_publishes_events(self, orchestrator):
        """Test that execution publishes events to L11."""
        markdown = "## Phase 1\n- Step 1: Test"

        await orchestrator.execute_plan_markdown(markdown)

        orchestrator.l11_bridge.publish_plan_started.assert_called_once()
        orchestrator.l11_bridge.publish_unit_started.assert_called_once()
        orchestrator.l11_bridge.publish_unit_completed.assert_called_once()
        orchestrator.l11_bridge.publish_plan_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan_stores_in_l01(self, orchestrator):
        """Test that execution stores data in L01."""
        markdown = "## Phase 1\n- Step 1: Test"

        await orchestrator.execute_plan_markdown(markdown)

        orchestrator.l01_bridge.store_plan_async.assert_called_once()
        orchestrator.l01_bridge.store_unit_async.assert_called_once()
        orchestrator.l01_bridge.store_execution_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan_creates_checkpoints(self, orchestrator):
        """Test that checkpoints are created during execution."""
        markdown = "## Phase 1\n- Step 1: Test"

        result = await orchestrator.execute_plan_markdown(markdown)

        orchestrator.checkpoint_manager.create_checkpoint.assert_called()
        assert result.unit_results[0].checkpoint_hash is not None


class TestExecutionFailures:
    """Tests for handling execution failures."""

    @pytest.mark.asyncio
    async def test_execution_failure_stops_pipeline(self, orchestrator, mock_executor):
        """Test that execution failure stops pipeline when stop_on_failure is True."""
        mock_executor.execute = AsyncMock(return_value=ExecutionResult(
            unit_id="unit-001",
            status=ExecutionStatus.FAILED,
            execution_type=Mock(value="file_create"),
            output="",
            error="Execution failed",
        ))

        context = ExecutionContext(
            working_dir=orchestrator.working_dir,
            stop_on_failure=True,
        )

        result = await orchestrator.execute_plan_markdown("## Test", context)

        assert result.failed_units == 1
        orchestrator.l11_bridge.publish_unit_failed.assert_called()

    @pytest.mark.asyncio
    async def test_parse_error_handling(self, orchestrator, mock_parser):
        """Test handling of parse errors."""
        from ..parsers.multi_format_parser import ParseError
        mock_parser.parse.side_effect = ParseError("Invalid markdown")

        result = await orchestrator.execute_plan_markdown("invalid")

        assert result.status == PipelineStatus.FAILED
        assert "Parse error" in result.metadata.get("error", "")
        orchestrator.l11_bridge.publish_plan_failed.assert_called()


class TestValidationAndScoring:
    """Tests for validation and scoring."""

    @pytest.mark.asyncio
    async def test_low_quality_score_fails_unit(self, orchestrator, mock_l06_bridge):
        """Test that low quality score fails the unit."""
        mock_l06_bridge.score_unit_async = AsyncMock(return_value=UnitScore(
            unit_id="unit-001",
            score=50.0,
            assessment=AssessmentLevel.CRITICAL,
        ))

        context = ExecutionContext(
            working_dir=orchestrator.working_dir,
            quality_threshold=70.0,
        )

        result = await orchestrator.execute_plan_markdown("## Test", context)

        assert result.failed_units == 1
        assert result.unit_results[0].status == PipelineStatus.FAILED

    @pytest.mark.asyncio
    async def test_validation_failure_fails_unit(self, orchestrator, mock_validator):
        """Test that validation failure fails the unit."""
        mock_validator.validate.return_value = ValidationResult(
            unit_id="unit-001",
            status=ValidationStatus.FAILED,
            passed=False,
            criterion_results=[],
        )

        result = await orchestrator.execute_plan_markdown("## Test")

        assert result.failed_units == 1


class TestRollback:
    """Tests for rollback functionality."""

    @pytest.mark.asyncio
    async def test_rollback_execution(self, orchestrator):
        """Test rolling back an execution."""
        # First execute
        result = await orchestrator.execute_plan_markdown("## Test")

        # Then rollback
        success = await orchestrator.rollback_execution(result.execution_id)

        assert success is True
        orchestrator.checkpoint_manager.restore_checkpoint.assert_called()
        orchestrator.l11_bridge.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_execution(self, orchestrator):
        """Test rollback of nonexistent execution returns False."""
        success = await orchestrator.rollback_execution("nonexistent-id")
        assert success is False


class TestExecutionStatus:
    """Tests for execution status retrieval."""

    @pytest.mark.asyncio
    async def test_get_execution_status(self, orchestrator):
        """Test getting execution status."""
        result = await orchestrator.execute_plan_markdown("## Test")

        status = await orchestrator.get_execution_status(result.execution_id)

        assert status is not None
        assert status.execution_id == result.execution_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_execution_status(self, orchestrator):
        """Test getting status of nonexistent execution."""
        status = await orchestrator.get_execution_status("nonexistent")
        assert status is None


class TestStatistics:
    """Tests for orchestrator statistics."""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, orchestrator):
        """Test that statistics are tracked correctly."""
        await orchestrator.execute_plan_markdown("## Test")

        stats = orchestrator.get_statistics()

        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["initialized"] is True
        assert "bridges" in stats


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_execution_context_defaults(self, temp_dir):
        """Test ExecutionContext default values."""
        context = ExecutionContext(working_dir=temp_dir)

        assert context.dry_run is False
        assert context.sandbox is True
        assert context.stop_on_failure is True
        assert context.quality_threshold == 70.0

    @pytest.mark.asyncio
    async def test_dry_run_context(self, orchestrator, mock_executor):
        """Test execution with dry_run context."""
        mock_executor.execute = AsyncMock(return_value=ExecutionResult(
            unit_id="unit-001",
            status=ExecutionStatus.FAILED,
            execution_type=Mock(value="file_create"),
            output="DRY RUN",
            error="Execution failed",
        ))

        context = ExecutionContext(
            working_dir=orchestrator.working_dir,
            dry_run=True,
        )

        # In dry_run mode, failures should not stop the pipeline
        result = await orchestrator.execute_plan_markdown("## Test", context)

        # The executor was called
        mock_executor.execute.assert_called()


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_pipeline_result_success(self):
        """Test PipelineResult success property."""
        result = PipelineResult(
            execution_id="exec-001",
            plan_id="plan-001",
            status=PipelineStatus.COMPLETED,
            failed_units=0,
        )
        assert result.success is True

    def test_pipeline_result_failure(self):
        """Test PipelineResult failure."""
        result = PipelineResult(
            execution_id="exec-001",
            plan_id="plan-001",
            status=PipelineStatus.COMPLETED,
            failed_units=1,
        )
        assert result.success is False

    def test_pipeline_result_failed_status(self):
        """Test PipelineResult with FAILED status."""
        result = PipelineResult(
            execution_id="exec-001",
            plan_id="plan-001",
            status=PipelineStatus.FAILED,
            failed_units=0,
        )
        assert result.success is False


class TestFinalScoring:
    """Tests for final score calculation."""

    @pytest.mark.asyncio
    async def test_excellent_score(self, orchestrator, mock_l06_bridge):
        """Test excellent assessment for high scores."""
        mock_l06_bridge.score_unit_async = AsyncMock(return_value=UnitScore(
            unit_id="unit-001",
            score=95.0,
            assessment=AssessmentLevel.EXCELLENT,
        ))

        result = await orchestrator.execute_plan_markdown("## Test")

        assert result.overall_assessment == AssessmentLevel.EXCELLENT

    @pytest.mark.asyncio
    async def test_warning_score(self, orchestrator, mock_l06_bridge, mock_validator):
        """Test warning assessment for low scores."""
        mock_l06_bridge.score_unit_async = AsyncMock(return_value=UnitScore(
            unit_id="unit-001",
            score=65.0,
            assessment=AssessmentLevel.WARNING,
        ))
        # Make sure validation passes so we don't fail early
        mock_validator.validate.return_value = ValidationResult(
            unit_id="unit-001",
            status=ValidationStatus.PASSED,
            passed=True,
            criterion_results=[],
        )

        context = ExecutionContext(
            working_dir=orchestrator.working_dir,
            quality_threshold=60.0,  # Lower threshold to allow unit to pass
        )

        result = await orchestrator.execute_plan_markdown("## Test", context)

        assert result.average_score == 65.0
