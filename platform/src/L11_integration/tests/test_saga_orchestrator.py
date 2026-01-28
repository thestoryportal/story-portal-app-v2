"""
L11 Integration Layer - Saga Orchestrator Tests.

Tests for the SagaOrchestrator service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from L11_integration.services import SagaOrchestrator, RequestOrchestrator, ServiceRegistry, CircuitBreaker
from L11_integration.models import (
    SagaDefinition,
    SagaStep,
    SagaStatus,
    StepStatus,
    RequestContext,
    IntegrationError,
)


@pytest.mark.l11
@pytest.mark.unit
class TestSagaOrchestratorUnit:
    """Unit tests for SagaOrchestrator."""

    @pytest.fixture
    def mock_request_orchestrator(self):
        """Create mock request orchestrator."""
        orchestrator = MagicMock(spec=RequestOrchestrator)
        orchestrator.route_request = AsyncMock(return_value={"status": "ok"})
        return orchestrator

    @pytest.fixture
    def saga_orchestrator(self, mock_request_orchestrator):
        """Create saga orchestrator for testing."""
        return SagaOrchestrator(
            request_orchestrator=mock_request_orchestrator,
            l11_bridge=None,
        )

    @pytest.mark.asyncio
    async def test_execute_simple_saga(self, saga_orchestrator):
        """Test executing a simple saga with action functions."""
        step1_called = False
        step2_called = False

        async def step1_action(context):
            nonlocal step1_called
            step1_called = True
            return {"step1_result": "done"}

        async def step2_action(context):
            nonlocal step2_called
            step2_called = True
            assert "step1_result" in context  # Context should have step1 output
            return {"step2_result": "done"}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Step 1",
                    action=step1_action,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Step 2",
                    action=step2_action,
                ),
            ],
        )

        execution = await saga_orchestrator.execute_saga(saga)

        assert step1_called
        assert step2_called
        assert execution.status == SagaStatus.COMPLETED
        assert "step1_result" in execution.context
        assert "step2_result" in execution.context

    @pytest.mark.asyncio
    async def test_saga_failure_triggers_compensation(self, saga_orchestrator):
        """Test that saga failure triggers compensation."""
        compensated = False

        async def step1_action(context):
            return {"step1": "done"}

        async def step1_compensation(context):
            nonlocal compensated
            compensated = True

        async def step2_action(context):
            raise ValueError("Step 2 failed")

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga with Compensation",
            auto_compensate=True,
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Step 1",
                    action=step1_action,
                    compensation=step1_compensation,
                    required=True,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Step 2",
                    action=step2_action,
                    required=True,
                ),
            ],
        )

        with pytest.raises(IntegrationError):
            await saga_orchestrator.execute_saga(saga)

        assert compensated

    @pytest.mark.asyncio
    async def test_saga_skips_non_required_step(self, saga_orchestrator):
        """Test that non-required step failure is skipped."""
        async def step1_action(context):
            return {"step1": "done"}

        async def step2_action(context):
            raise ValueError("Non-critical failure")

        async def step3_action(context):
            return {"step3": "done"}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Step 1",
                    action=step1_action,
                    required=True,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Step 2",
                    action=step2_action,
                    required=False,  # Not required
                ),
                SagaStep(
                    step_id="step-2",
                    step_name="Step 3",
                    action=step3_action,
                    required=True,
                ),
            ],
        )

        execution = await saga_orchestrator.execute_saga(saga)

        assert execution.status == SagaStatus.COMPLETED
        assert saga.steps[1].status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_get_execution(self, saga_orchestrator):
        """Test retrieving a saga execution."""
        async def step_action(context):
            return {}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Step 1",
                    action=step_action,
                ),
            ],
        )

        execution = await saga_orchestrator.execute_saga(saga)
        retrieved = await saga_orchestrator.get_execution(execution.execution_id)

        assert retrieved is not None
        assert retrieved.execution_id == execution.execution_id

    @pytest.mark.asyncio
    async def test_get_metrics(self, saga_orchestrator):
        """Test getting saga metrics."""
        async def step_action(context):
            return {}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[
                SagaStep(step_id="step-0", step_name="Step", action=step_action),
            ],
        )

        await saga_orchestrator.execute_saga(saga)
        await saga_orchestrator.execute_saga(saga)

        metrics = saga_orchestrator.get_metrics()

        assert metrics["total_executions"] == 2
        assert metrics["completed"] == 2

    @pytest.mark.asyncio
    async def test_get_execution_trace(self, saga_orchestrator):
        """Test getting execution trace."""
        async def step_action(context):
            return {"result": "ok"}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[
                SagaStep(step_id="step-0", step_name="Step 1", action=step_action),
                SagaStep(step_id="step-1", step_name="Step 2", action=step_action),
            ],
        )

        execution = await saga_orchestrator.execute_saga(saga)
        trace = await saga_orchestrator.get_execution_trace(execution.execution_id)

        assert trace is not None
        assert trace["saga_name"] == "Test Saga"
        assert len(trace["steps"]) == 2
        assert trace["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_executions(self, saga_orchestrator):
        """Test listing executions with filters."""
        async def step_action(context):
            return {}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[SagaStep(step_id="step-0", step_name="Step", action=step_action)],
        )

        await saga_orchestrator.execute_saga(saga)
        await saga_orchestrator.execute_saga(saga)

        executions = await saga_orchestrator.list_executions()
        assert len(executions) == 2

        # Filter by status
        completed = await saga_orchestrator.list_executions(status_filter=SagaStatus.COMPLETED)
        assert len(completed) == 2

    @pytest.mark.asyncio
    async def test_health_status(self, saga_orchestrator):
        """Test health status reporting."""
        async def step_action(context):
            return {}

        saga = SagaDefinition(
            saga_id="test-saga",
            saga_name="Test Saga",
            steps=[SagaStep(step_id="step-0", step_name="Step", action=step_action)],
        )

        await saga_orchestrator.execute_saga(saga)

        health = saga_orchestrator.get_health_status()
        assert health["healthy"] is True
        assert health["success_rate_percent"] == 100.0


@pytest.mark.l11
@pytest.mark.unit
class TestSagaRetry:
    """Tests for saga step retry behavior."""

    @pytest.mark.asyncio
    async def test_step_retry_on_failure(self):
        """Test that steps are retried on failure."""
        mock_orchestrator = MagicMock(spec=RequestOrchestrator)
        saga_orchestrator = SagaOrchestrator(mock_orchestrator, l11_bridge=None)

        attempt_count = 0

        async def flaky_action(context):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Transient failure")
            return {"result": "success"}

        saga = SagaDefinition(
            saga_id="retry-saga",
            saga_name="Retry Test",
            steps=[
                SagaStep(
                    step_id="step-flaky",
                    step_name="Flaky Step",
                    action=flaky_action,
                    max_retries=3,
                ),
            ],
        )

        execution = await saga_orchestrator.execute_saga(saga)

        assert execution.status == SagaStatus.COMPLETED
        assert attempt_count == 2  # Initial + 1 retry
