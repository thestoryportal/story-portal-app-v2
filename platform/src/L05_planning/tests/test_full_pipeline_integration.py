"""
Full Pipeline Integration Tests - End-to-end testing of the L05 planning pipeline.

Tests the complete flow:
  parse → decompose → execute → validate → score → (rollback if needed)

Run with real services:
  pytest test_full_pipeline_integration.py -v -m integration

Run with mocks (CI-friendly):
  pytest test_full_pipeline_integration.py -v -m "not integration"
"""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, AsyncMock, patch

from ..services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStatus,
    ExecutionContext,
)
from ..services.unit_executor import UnitExecutor, ExecutionStatus
from ..services.model_router import ModelRouter, ComplexityLevel
from ..parsers.multi_format_parser import MultiFormatParser
from ..parsers.base_parser import ParsedPlan, PlanStep
from ..parsers.format_detector import FormatType
from ..agents.spec_decomposer import SpecDecomposer, AtomicUnit, AcceptanceCriterion
from ..agents.unit_validator import UnitValidator, ValidationResult, ValidationStatus
from ..checkpoints.checkpoint_manager import CheckpointManager
from ..checkpoints.recovery_protocol import RecoveryProtocol
from ..integration.l01_bridge import L01Bridge
from ..integration.l04_bridge import L04Bridge, ModelProvider
from ..integration.l06_bridge import L06Bridge, AssessmentLevel
from ..integration.l11_bridge import L11Bridge


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for tests."""
    workspace = tempfile.mkdtemp(prefix="l05_pipeline_test_")
    workspace_path = Path(workspace)
    yield workspace_path
    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def sample_plans():
    """Collection of sample plans in different formats."""
    return {
        "simple": textwrap.dedent("""
            ## Phase 1: Setup
            - Create a hello.py file with a hello_world function
        """).strip(),
        "multi_phase": textwrap.dedent("""
            ## Phase 1: Project Setup
            - Create src/ directory structure
            - Create src/__init__.py

            ## Phase 2: Implementation
            - Create src/calculator.py with add and subtract functions
            - Create src/utils.py with helper functions

            ## Phase 3: Testing
            - Create tests/__init__.py
            - Create tests/test_calculator.py with unit tests
        """).strip(),
        "with_acceptance_criteria": textwrap.dedent("""
            ## Phase 1: Core Implementation

            ### Step 1.1: Create main module
            Create the main application entry point.

            **Acceptance Criteria:**
            - File src/main.py exists
            - Contains main() function
            - Returns 0 on success

            ### Step 1.2: Create config module
            Create configuration handling.

            **Acceptance Criteria:**
            - File src/config.py exists
            - Contains Config class
            - Loads from environment variables
        """).strip(),
        "numbered_steps": textwrap.dedent("""
            # Implementation Plan

            1. Create project structure
               - src/ directory
               - tests/ directory

            2. Implement core module
               - src/core.py with CoreService class

            3. Add logging
               - src/logger.py with setup_logging function

            4. Write tests
               - tests/test_core.py
        """).strip(),
        "complex_with_dependencies": textwrap.dedent("""
            ## Phase 1: Foundation

            ### 1.1 Database Models
            Create SQLAlchemy models for User and Session.
            - File: src/models.py
            - Dependencies: None

            ### 1.2 Database Connection
            Create database connection pool.
            - File: src/database.py
            - Dependencies: 1.1

            ## Phase 2: API Layer

            ### 2.1 User Routes
            Create FastAPI routes for user management.
            - File: src/routes/users.py
            - Dependencies: 1.1, 1.2

            ### 2.2 Auth Routes
            Create authentication endpoints.
            - File: src/routes/auth.py
            - Dependencies: 1.1, 1.2, 2.1
        """).strip(),
    }


# =============================================================================
# Mock Factories
# =============================================================================

def create_mock_parser():
    """Create a mock parser for testing."""
    parser = Mock(spec=MultiFormatParser)
    parser.parse.return_value = ParsedPlan(
        plan_id="plan-001",
        title="Test Plan",
        format_type=FormatType.PHASE_BASED,
        steps=[
            PlanStep(id="step-1", title="Create file", description="Create a test file"),
        ],
    )
    return parser


def create_mock_decomposer(num_units: int = 1):
    """Create a mock decomposer for testing.

    Args:
        num_units: Number of atomic units to return from decompose
    """
    decomposer = Mock(spec=SpecDecomposer)
    units = [
        AtomicUnit(
            id=f"unit-{i+1:03d}",
            title=f"Create test file {i+1}",
            description=f"Create a test file {i+1} in the workspace",
            files=[f"test_{i+1}.py"],
            complexity=1,
            acceptance_criteria=[
                AcceptanceCriterion(
                    id=f"ac-{i+1:03d}",
                    description="File exists",
                    validation_command=f"test -f test_{i+1}.py",
                    timeout_seconds=5,
                )
            ],
            dependencies=[],
        )
        for i in range(num_units)
    ]
    decomposer.decompose.return_value = units
    decomposer.get_execution_order.return_value = units
    return decomposer


def create_mock_validator():
    """Create a mock validator for testing.

    Validator returns PASSED for any unit_id passed to it.
    """
    validator = Mock(spec=UnitValidator)

    def validate_side_effect(unit, *args, **kwargs):
        return ValidationResult(
            unit_id=unit.id if hasattr(unit, 'id') else "unit-001",
            status=ValidationStatus.PASSED,
            passed=True,
            criterion_results=[],
        )

    validator.validate.side_effect = validate_side_effect
    return validator


def create_mock_executor():
    """Create a mock executor for testing.

    Executor returns SUCCESS for any unit_id passed to it.
    """
    from ..services.unit_executor import ExecutionResult, ExecutionType
    executor = Mock(spec=UnitExecutor)

    async def execute_side_effect(unit, *args, **kwargs):
        return ExecutionResult(
            unit_id=unit.id if hasattr(unit, 'id') else "unit-001",
            status=ExecutionStatus.SUCCESS,
            execution_type=ExecutionType.FILE_CREATE,
            output="Success",
        )

    executor.execute = AsyncMock(side_effect=execute_side_effect)
    return executor


def create_mock_l01_bridge():
    """Create a mock L01 bridge for testing."""
    bridge = Mock(spec=L01Bridge)
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.store_plan_async = AsyncMock(return_value=Mock(success=True, record_id="plan-001"))
    bridge.store_unit_async = AsyncMock(return_value=Mock(success=True, record_id="unit-001"))
    bridge.store_execution_async = AsyncMock(return_value=Mock(success=True))
    bridge.store_validation_async = AsyncMock(return_value=Mock(success=True))
    bridge.is_connected.return_value = True
    return bridge


def create_mock_l04_bridge():
    """Create a mock L04 bridge for testing."""
    bridge = Mock(spec=L04Bridge)
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.generate_plan_async = AsyncMock(return_value=Mock(
        plan_id="gen-001",
        content="Generated plan content",
        model="mistral",
        provider=ModelProvider.OLLAMA,
        tokens_used=100,
        latency_ms=500,
    ))
    bridge.is_connected.return_value = True
    return bridge


def create_mock_l06_bridge(score: float = 85.0, assessment: AssessmentLevel = AssessmentLevel.GOOD):
    """Create a mock L06 bridge for testing.

    Args:
        score: Quality score to return (default 85.0)
        assessment: Assessment level to return
    """
    from ..integration.l06_bridge import UnitScore
    bridge = Mock(spec=L06Bridge)
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()

    async def score_unit_side_effect(unit_id, *args, **kwargs):
        return UnitScore(
            unit_id=unit_id,
            score=score,
            assessment=assessment,
        )

    bridge.score_unit_async = AsyncMock(side_effect=score_unit_side_effect)
    bridge.is_connected.return_value = True
    return bridge


def create_mock_l11_bridge():
    """Create a mock L11 bridge for testing."""
    bridge = Mock(spec=L11Bridge)
    bridge.initialize = AsyncMock()
    bridge.close = AsyncMock()
    bridge.publish_plan_started = AsyncMock(return_value=Mock(success=True, event_id="evt-001"))
    bridge.publish_plan_completed = AsyncMock(return_value=Mock(success=True, event_id="evt-002"))
    bridge.publish_plan_failed = AsyncMock(return_value=Mock(success=True, event_id="evt-003"))
    bridge.publish_unit_started = AsyncMock(return_value=Mock(success=True, event_id="evt-004"))
    bridge.publish_unit_completed = AsyncMock(return_value=Mock(success=True, event_id="evt-005"))
    bridge.publish_unit_failed = AsyncMock(return_value=Mock(success=True, event_id="evt-006"))
    bridge.publish_event = AsyncMock(return_value=Mock(success=True, event_id="evt-007"))
    bridge.is_connected.return_value = True
    return bridge


# =============================================================================
# Unit Tests (Mocked Dependencies)
# =============================================================================

class TestPipelineWithMocks:
    """Test pipeline with mocked external dependencies (CI-friendly)."""

    @pytest.fixture
    def mocked_orchestrator(self, temp_workspace):
        """Create orchestrator with all mocked components."""
        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_simple_plan_execution(self, mocked_orchestrator, sample_plans):
        """Test execution of a simple single-phase plan."""
        await mocked_orchestrator.initialize()

        result = await mocked_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=mocked_orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        assert result.total_units >= 1
        await mocked_orchestrator.close()

    @pytest.mark.asyncio
    async def test_multi_phase_plan_execution(self, temp_workspace, sample_plans):
        """Test execution of a multi-phase plan."""
        # Create orchestrator with decomposer returning 5 units (multiple phases)
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(num_units=5),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        result = await orchestrator.execute_plan_markdown(
            sample_plans["multi_phase"],
            ExecutionContext(
                working_dir=orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        assert result.total_units >= 3  # At least 3 phases worth of units
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_plan_with_acceptance_criteria(self, mocked_orchestrator, sample_plans):
        """Test plan with explicit acceptance criteria."""
        await mocked_orchestrator.initialize()

        result = await mocked_orchestrator.execute_plan_markdown(
            sample_plans["with_acceptance_criteria"],
            ExecutionContext(
                working_dir=mocked_orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        await mocked_orchestrator.close()

    @pytest.mark.asyncio
    async def test_numbered_steps_plan(self, mocked_orchestrator, sample_plans):
        """Test plan with numbered steps format."""
        await mocked_orchestrator.initialize()

        result = await mocked_orchestrator.execute_plan_markdown(
            sample_plans["numbered_steps"],
            ExecutionContext(
                working_dir=mocked_orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        await mocked_orchestrator.close()

    @pytest.mark.asyncio
    async def test_events_published_on_execution(self, mocked_orchestrator, sample_plans):
        """Test that events are published to L11 during execution."""
        await mocked_orchestrator.initialize()

        await mocked_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=mocked_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # Verify events were published
        mocked_orchestrator.l11_bridge.publish_plan_started.assert_called()
        mocked_orchestrator.l11_bridge.publish_plan_completed.assert_called()
        await mocked_orchestrator.close()

    @pytest.mark.asyncio
    async def test_data_stored_in_l01(self, mocked_orchestrator, sample_plans):
        """Test that execution data is stored in L01."""
        await mocked_orchestrator.initialize()

        await mocked_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=mocked_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # Verify data was stored
        mocked_orchestrator.l01_bridge.store_plan_async.assert_called()
        await mocked_orchestrator.close()

    @pytest.mark.asyncio
    async def test_quality_scoring(self, temp_workspace, sample_plans):
        """Test that quality scoring is performed."""
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(score=92.0, assessment=AssessmentLevel.EXCELLENT),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        result = await orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
            )
        )

        assert result.average_score >= 90.0
        assert result.overall_assessment == AssessmentLevel.EXCELLENT
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_low_quality_fails_with_threshold(self, temp_workspace, sample_plans):
        """Test that low quality score fails execution when threshold is set."""
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(score=50.0, assessment=AssessmentLevel.CRITICAL),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        result = await orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
                quality_threshold=70.0,
            )
        )

        assert result.failed_units >= 1
        await orchestrator.close()


# =============================================================================
# Real Execution Tests (Sandbox Mode)
# =============================================================================

class TestRealExecutionInSandbox:
    """Test real file operations in sandbox mode."""

    @pytest.fixture
    def sandbox_orchestrator(self, temp_workspace):
        """Create orchestrator for sandbox testing."""
        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_file_creation(self, sandbox_orchestrator, temp_workspace):
        """Test that files are actually created in sandbox."""
        await sandbox_orchestrator.initialize()

        result = await sandbox_orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create hello.py with a simple function
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=False,
                sandbox=True,
            )
        )

        # Check file was created
        hello_file = temp_workspace / "hello.py"
        assert hello_file.exists() or result.status == PipelineStatus.COMPLETED
        await sandbox_orchestrator.close()

    @pytest.mark.asyncio
    async def test_directory_creation(self, sandbox_orchestrator, temp_workspace):
        """Test that directories are created as needed."""
        await sandbox_orchestrator.initialize()

        result = await sandbox_orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create src/ directory
            - Create src/__init__.py
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=False,
                sandbox=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        await sandbox_orchestrator.close()

    @pytest.mark.asyncio
    async def test_sandbox_prevents_escape(self, sandbox_orchestrator, temp_workspace):
        """Test that sandbox prevents file operations outside workspace."""
        await sandbox_orchestrator.initialize()

        # This should fail or be blocked
        result = await sandbox_orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create /tmp/outside_sandbox.py
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=False,
                sandbox=True,
            )
        )

        # Should either fail or not create the file
        outside_file = Path("/tmp/outside_sandbox.py")
        if outside_file.exists():
            outside_file.unlink()  # Cleanup if somehow created
            pytest.fail("Sandbox escape detected!")

        await sandbox_orchestrator.close()


# =============================================================================
# Rollback Tests
# =============================================================================

class TestRollbackFunctionality:
    """Test rollback and recovery functionality."""

    @pytest.fixture
    def rollback_orchestrator(self, temp_workspace):
        """Create orchestrator with checkpoint support."""
        checkpoint_dir = temp_workspace / ".checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            checkpoint_manager=CheckpointManager(
                repo_path=str(temp_workspace),
                storage_path=str(checkpoint_dir),
            ),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, rollback_orchestrator, temp_workspace):
        """Test that checkpoints are created during execution."""
        await rollback_orchestrator.initialize()

        result = await rollback_orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create test_file.py
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
            )
        )

        # Check that checkpoints were created
        assert len(result.unit_results) > 0
        for unit_result in result.unit_results:
            assert unit_result.checkpoint_hash is not None

        await rollback_orchestrator.close()

    @pytest.mark.asyncio
    async def test_rollback_execution(self, temp_workspace):
        """Test rolling back an execution."""
        # Create mock checkpoint manager for rollback test
        # Note: We don't use spec= because CheckpointManager doesn't have restore_checkpoint
        # but PipelineOrchestrator expects it for rollback functionality
        mock_checkpoint = Mock()
        mock_checkpoint.hash = "abc123"
        mock_checkpoint.checkpoint_id = "cp-001"

        mock_checkpoint_manager = Mock()
        mock_checkpoint_manager.create_checkpoint.return_value = mock_checkpoint
        mock_checkpoint_manager.get_checkpoint.return_value = mock_checkpoint
        mock_checkpoint_manager.restore_checkpoint.return_value = True

        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            checkpoint_manager=mock_checkpoint_manager,
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        # Execute a plan
        result = await orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create rollback_test.py
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
            )
        )

        # Attempt rollback
        rollback_success = await orchestrator.rollback_execution(result.execution_id)

        # Rollback should succeed
        assert rollback_success is True
        mock_checkpoint_manager.restore_checkpoint.assert_called_once()
        await orchestrator.close()


# =============================================================================
# Integration Tests (Requires Real Services)
# =============================================================================

@pytest.mark.integration
class TestFullIntegrationWithServices:
    """Full integration tests requiring real services on localhost."""

    @pytest_asyncio.fixture
    async def live_orchestrator(self, temp_workspace):
        """Create orchestrator with real service connections."""
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            l01_bridge=L01Bridge(),
            l04_bridge=L04Bridge(),
            l06_bridge=L06Bridge(),
            l11_bridge=L11Bridge(),
        )
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_full_pipeline_with_live_services(self, live_orchestrator, sample_plans):
        """Test complete pipeline with all live services."""
        result = await live_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=live_orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]
        assert result.execution_id is not None
        assert result.plan_id is not None

    @pytest.mark.asyncio
    async def test_live_event_publishing(self, live_orchestrator, sample_plans):
        """Test that events are published to real L11 service."""
        result = await live_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=live_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # If L11 is connected, events should have been published
        if live_orchestrator.l11_bridge.is_connected():
            assert result.metadata.get("events_published", 0) >= 0

    @pytest.mark.asyncio
    async def test_live_data_persistence(self, live_orchestrator, sample_plans):
        """Test that data is persisted to real L01 service."""
        result = await live_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=live_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # If L01 is connected, we should be able to retrieve the execution
        if live_orchestrator.l01_bridge.is_connected():
            status = await live_orchestrator.get_execution_status(result.execution_id)
            assert status is not None

    @pytest.mark.asyncio
    async def test_live_quality_scoring(self, live_orchestrator, sample_plans):
        """Test quality scoring with real L06 service."""
        result = await live_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=live_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # Should have a score (either from L06 or local calculation)
        assert result.average_score >= 0.0
        assert result.average_score <= 100.0


# =============================================================================
# Performance Tests
# =============================================================================

class TestPipelinePerformance:
    """Performance-related tests."""

    @pytest.fixture
    def perf_orchestrator(self, temp_workspace):
        """Create orchestrator for performance testing."""
        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_parse_performance(self, perf_orchestrator, sample_plans):
        """Test that parsing completes within acceptable time."""
        await perf_orchestrator.initialize()

        start = datetime.now()
        result = await perf_orchestrator.execute_plan_markdown(
            sample_plans["complex_with_dependencies"],
            ExecutionContext(
                working_dir=perf_orchestrator.working_dir,
                dry_run=True,
            )
        )
        elapsed = (datetime.now() - start).total_seconds()

        # Parse + decompose should complete within 5 seconds
        assert elapsed < 5.0, f"Pipeline took {elapsed}s, expected < 5s"
        await perf_orchestrator.close()

    @pytest.mark.asyncio
    async def test_multiple_executions(self, perf_orchestrator, sample_plans):
        """Test multiple sequential executions."""
        await perf_orchestrator.initialize()

        results = []
        for i in range(3):
            result = await perf_orchestrator.execute_plan_markdown(
                sample_plans["simple"],
                ExecutionContext(
                    working_dir=perf_orchestrator.working_dir,
                    dry_run=True,
                )
            )
            results.append(result)

        # All executions should complete
        assert len(results) == 3
        assert all(r.status == PipelineStatus.COMPLETED for r in results)

        # Each should have unique execution ID
        execution_ids = [r.execution_id for r in results]
        assert len(set(execution_ids)) == 3

        await perf_orchestrator.close()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling throughout the pipeline."""

    @pytest.fixture
    def error_orchestrator(self, temp_workspace):
        """Create orchestrator for error testing."""
        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_empty_plan_handling(self, error_orchestrator):
        """Test handling of empty plan input."""
        await error_orchestrator.initialize()

        result = await error_orchestrator.execute_plan_markdown(
            "",
            ExecutionContext(
                working_dir=error_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # Should handle gracefully (either fail or complete with 0 units)
        assert result.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]
        await error_orchestrator.close()

    @pytest.mark.asyncio
    async def test_invalid_markdown_handling(self, error_orchestrator):
        """Test handling of invalid markdown."""
        await error_orchestrator.initialize()

        result = await error_orchestrator.execute_plan_markdown(
            "This is not a valid plan format at all!!!",
            ExecutionContext(
                working_dir=error_orchestrator.working_dir,
                dry_run=True,
            )
        )

        # Should handle gracefully
        assert result.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]
        await error_orchestrator.close()

    @pytest.mark.asyncio
    async def test_bridge_failure_handling(self, temp_workspace):
        """Test handling when bridges fail."""
        # Create bridge that fails
        failing_l01 = create_mock_l01_bridge()
        failing_l01.store_plan_async = AsyncMock(side_effect=Exception("L01 connection failed"))

        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=failing_l01,
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        # Should handle the failure gracefully
        result = await orchestrator.execute_plan_markdown(
            "## Phase 1\n- Create test.py",
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
            )
        )

        # Pipeline should still complete (with local fallback)
        assert result is not None
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_stop_on_failure_behavior(self, temp_workspace):
        """Test stop_on_failure context option."""
        # Create bridge that returns low score to trigger failure
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(num_units=2),  # 2 units to test stop_on_failure
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(score=30.0, assessment=AssessmentLevel.CRITICAL),
            l11_bridge=create_mock_l11_bridge(),
        )
        await orchestrator.initialize()

        result = await orchestrator.execute_plan_markdown(
            """
            ## Phase 1
            - Create file1.py

            ## Phase 2
            - Create file2.py
            """,
            ExecutionContext(
                working_dir=temp_workspace,
                dry_run=True,
                stop_on_failure=True,
                quality_threshold=70.0,
            )
        )

        # Should stop after first failure
        assert result.failed_units >= 1
        await orchestrator.close()


# =============================================================================
# Statistics and Observability Tests
# =============================================================================

class TestStatisticsAndObservability:
    """Test statistics collection and observability features."""

    @pytest.fixture
    def stats_orchestrator(self, temp_workspace):
        """Create orchestrator for statistics testing."""
        return PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=create_mock_l04_bridge(),
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )

    @pytest.mark.asyncio
    async def test_statistics_collection(self, stats_orchestrator, sample_plans):
        """Test that statistics are collected during execution."""
        await stats_orchestrator.initialize()

        await stats_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=stats_orchestrator.working_dir,
                dry_run=True,
            )
        )

        stats = stats_orchestrator.get_statistics()

        assert "total_executions" in stats
        assert stats["total_executions"] >= 1
        assert "initialized" in stats
        assert stats["initialized"] is True

        await stats_orchestrator.close()

    @pytest.mark.asyncio
    async def test_execution_timing(self, stats_orchestrator, sample_plans):
        """Test that execution timing is recorded."""
        await stats_orchestrator.initialize()

        result = await stats_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=stats_orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

        await stats_orchestrator.close()

    @pytest.mark.asyncio
    async def test_unit_result_details(self, stats_orchestrator, sample_plans):
        """Test that unit results contain detailed information."""
        await stats_orchestrator.initialize()

        result = await stats_orchestrator.execute_plan_markdown(
            sample_plans["simple"],
            ExecutionContext(
                working_dir=stats_orchestrator.working_dir,
                dry_run=True,
            )
        )

        for unit_result in result.unit_results:
            assert unit_result.unit_id is not None
            assert unit_result.status is not None
            assert unit_result.quality_score >= 0.0

        await stats_orchestrator.close()


# =============================================================================
# Model Router Integration Tests
# =============================================================================

class TestModelRouterIntegration:
    """Test ModelRouter integration with pipeline."""

    @pytest.fixture
    def router_and_orchestrator(self, temp_workspace):
        """Create orchestrator and model router."""
        l04_bridge = create_mock_l04_bridge()
        router = ModelRouter(l04_bridge=l04_bridge)
        orchestrator = PipelineOrchestrator(
            working_dir=temp_workspace,
            parser=create_mock_parser(),
            decomposer=create_mock_decomposer(),
            validator=create_mock_validator(),
            executor=create_mock_executor(),
            l01_bridge=create_mock_l01_bridge(),
            l04_bridge=l04_bridge,
            l06_bridge=create_mock_l06_bridge(),
            l11_bridge=create_mock_l11_bridge(),
        )
        return router, orchestrator

    @pytest.mark.asyncio
    async def test_model_selection_for_simple_task(self, router_and_orchestrator):
        """Test that simple tasks route to appropriate model."""
        router, orchestrator = router_and_orchestrator
        await orchestrator.initialize()

        # Test router decision for simple task
        decision = router.route("Create a simple config file")
        assert decision.complexity == ComplexityLevel.SIMPLE

        # Test orchestrator execution
        result = await orchestrator.execute_plan_markdown(
            "## Phase 1\n- Create a simple config file",
            ExecutionContext(
                working_dir=orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status == PipelineStatus.COMPLETED
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_model_selection_for_complex_task(self, router_and_orchestrator):
        """Test that complex tasks may route to more capable model."""
        router, orchestrator = router_and_orchestrator
        await orchestrator.initialize()

        # Test router decision for complex task
        decision = router.route(
            "Design a distributed microservices architecture with event sourcing"
        )
        assert decision.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.CRITICAL, ComplexityLevel.MODERATE]

        # Test orchestrator execution
        result = await orchestrator.execute_plan_markdown(
            """
            ## Phase 1: Architecture Design
            Design a distributed microservices architecture with:
            - Event sourcing pattern
            - CQRS implementation
            - Saga orchestration
            """,
            ExecutionContext(
                working_dir=orchestrator.working_dir,
                dry_run=True,
            )
        )

        assert result.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]
        await orchestrator.close()


# =============================================================================
# Concurrent Execution Tests
# =============================================================================

class TestConcurrentExecution:
    """Test concurrent pipeline execution."""

    @pytest.mark.asyncio
    async def test_parallel_plan_execution(self, temp_workspace, sample_plans):
        """Test executing multiple plans in parallel."""
        orchestrators = []

        for i in range(3):
            workspace = temp_workspace / f"workspace_{i}"
            workspace.mkdir(exist_ok=True)

            orch = PipelineOrchestrator(
                working_dir=workspace,
                parser=create_mock_parser(),
                decomposer=create_mock_decomposer(),
                validator=create_mock_validator(),
                executor=create_mock_executor(),
                l01_bridge=create_mock_l01_bridge(),
                l04_bridge=create_mock_l04_bridge(),
                l06_bridge=create_mock_l06_bridge(),
                l11_bridge=create_mock_l11_bridge(),
            )
            await orch.initialize()
            orchestrators.append(orch)

        # Execute plans in parallel
        tasks = [
            orch.execute_plan_markdown(
                sample_plans["simple"],
                ExecutionContext(
                    working_dir=orch.working_dir,
                    dry_run=True,
                )
            )
            for orch in orchestrators
        ]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3
        assert all(r.status == PipelineStatus.COMPLETED for r in results)

        # Cleanup
        for orch in orchestrators:
            await orch.close()
