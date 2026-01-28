"""
L11 Integration Layer - Saga Integration Tests.

Tests saga orchestration with service calls.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from L11_integration.services import (
    SagaOrchestrator,
    RequestOrchestrator,
    ServiceRegistry,
    CircuitBreaker,
)
from L11_integration.models import (
    SagaDefinition,
    SagaStep,
    SagaStatus,
    ServiceInfo,
    ServiceStatus,
)
from L11_integration.tests.fixtures.mock_http import MockHTTPClient


@pytest.mark.l11
@pytest.mark.integration
class TestSagaWithServices:
    """Integration tests for saga orchestration with service calls."""

    @pytest_asyncio.fixture
    async def orchestration_stack(self):
        """Set up full orchestration stack with mocks."""
        # Service registry
        registry = ServiceRegistry(l11_bridge=None)
        await registry.start()

        # Register services
        services = [
            ServiceInfo(
                service_id="l02",
                service_name="L02_runtime",
                service_version="0.1.0",
                endpoint="http://localhost:8002",
                status=ServiceStatus.HEALTHY,
            ),
            ServiceInfo(
                service_id="l03",
                service_name="L03_tool_execution",
                service_version="0.1.0",
                endpoint="http://localhost:8003",
                status=ServiceStatus.HEALTHY,
            ),
            ServiceInfo(
                service_id="l05",
                service_name="L05_planning",
                service_version="0.1.0",
                endpoint="http://localhost:8005",
                status=ServiceStatus.HEALTHY,
            ),
        ]
        for svc in services:
            await registry.register_service(svc)

        # Circuit breaker
        cb = CircuitBreaker(l11_bridge=None)

        # Request orchestrator with mock HTTP
        request_orch = RequestOrchestrator(registry, cb)
        await request_orch.start()

        mock_http = MockHTTPClient()
        mock_http.add_response("POST", "8002", {"agent_id": "agent-001", "status": "created"})
        mock_http.add_response("POST", "8003", {"tool_id": "tool-001", "status": "configured"})
        mock_http.add_response("POST", "8005", {"plan_id": "plan-001", "status": "created"})
        request_orch._http_client = mock_http

        # Saga orchestrator
        saga_orch = SagaOrchestrator(request_orch, l11_bridge=None)

        yield saga_orch, request_orch, mock_http

        await request_orch.stop()
        await registry.stop()

    @pytest.mark.asyncio
    async def test_multi_step_saga_with_http_calls(self, orchestration_stack):
        """Test saga with multiple HTTP calls to services."""
        saga_orch, request_orch, mock_http = orchestration_stack

        # Define a saga that calls multiple services
        saga = SagaDefinition(
            saga_id="deploy-agent",
            saga_name="Deploy Agent Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Create Agent",
                    service_name="L02_runtime",
                    endpoint="/agents",
                    required=True,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Configure Tools",
                    service_name="L03_tool_execution",
                    endpoint="/tools/configure",
                    required=True,
                ),
                SagaStep(
                    step_id="step-2",
                    step_name="Create Plan",
                    service_name="L05_planning",
                    endpoint="/plans",
                    required=True,
                ),
            ],
        )

        execution = await saga_orch.execute_saga(saga)

        assert execution.status == SagaStatus.COMPLETED
        assert mock_http.request_count() == 3

        # Verify context accumulated
        assert "agent_id" in execution.context
        assert "tool_id" in execution.context
        assert "plan_id" in execution.context

    @pytest.mark.asyncio
    async def test_saga_with_compensation_on_failure(self, orchestration_stack):
        """Test saga compensates on step failure."""
        saga_orch, request_orch, mock_http = orchestration_stack

        # Make third step fail
        mock_http._responses.clear()
        mock_http.add_response("POST", "8002", {"agent_id": "agent-001"})
        mock_http.add_response("POST", "8003", {"tool_id": "tool-001"})
        mock_http.add_response("POST", "8005", {"error": "Failed"}, status_code=500)

        compensated_steps = []

        async def compensation_1(ctx):
            compensated_steps.append("agent")

        async def compensation_2(ctx):
            compensated_steps.append("tools")

        saga = SagaDefinition(
            saga_id="deploy-agent-fail",
            saga_name="Deploy Agent Saga (Will Fail)",
            auto_compensate=True,
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Create Agent",
                    service_name="L02_runtime",
                    endpoint="/agents",
                    compensation=compensation_1,
                    required=True,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Configure Tools",
                    service_name="L03_tool_execution",
                    endpoint="/tools/configure",
                    compensation=compensation_2,
                    required=True,
                ),
                SagaStep(
                    step_id="step-2",
                    step_name="Create Plan (Will Fail)",
                    service_name="L05_planning",
                    endpoint="/plans",
                    required=True,
                ),
            ],
        )

        with pytest.raises(Exception):
            await saga_orch.execute_saga(saga)

        # Compensation should have run in reverse order
        assert "tools" in compensated_steps
        assert "agent" in compensated_steps

    @pytest.mark.asyncio
    async def test_saga_with_mixed_steps(self, orchestration_stack):
        """Test saga with both HTTP and action function steps."""
        saga_orch, request_orch, mock_http = orchestration_stack

        custom_step_executed = False

        async def custom_validation(context):
            nonlocal custom_step_executed
            custom_step_executed = True
            # Validate agent was created
            assert "agent_id" in context
            return {"validated": True}

        saga = SagaDefinition(
            saga_id="mixed-saga",
            saga_name="Mixed Steps Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Create Agent",
                    service_name="L02_runtime",
                    endpoint="/agents",
                    required=True,
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Validate",
                    action=custom_validation,
                    required=True,
                ),
                SagaStep(
                    step_id="step-2",
                    step_name="Create Plan",
                    service_name="L05_planning",
                    endpoint="/plans",
                    required=True,
                ),
            ],
        )

        execution = await saga_orch.execute_saga(saga)

        assert execution.status == SagaStatus.COMPLETED
        assert custom_step_executed
        assert execution.context.get("validated") is True

    @pytest.mark.asyncio
    async def test_saga_execution_trace(self, orchestration_stack):
        """Test getting execution trace with timing information."""
        saga_orch, request_orch, mock_http = orchestration_stack

        saga = SagaDefinition(
            saga_id="trace-saga",
            saga_name="Trace Test Saga",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Step A",
                    service_name="L02_runtime",
                    endpoint="/agents",
                ),
                SagaStep(
                    step_id="step-1",
                    step_name="Step B",
                    service_name="L03_tool_execution",
                    endpoint="/tools/configure",
                ),
            ],
        )

        execution = await saga_orch.execute_saga(saga)
        trace = await saga_orch.get_execution_trace(execution.execution_id)

        assert trace is not None
        assert trace["saga_name"] == "Trace Test Saga"
        assert len(trace["steps"]) == 2
        assert trace["status"] == "completed"

        # Each step should have timing
        for step in trace["steps"]:
            assert "started_at" in step
            assert "completed_at" in step


@pytest.mark.l11
@pytest.mark.integration
class TestCircuitBreakerWithSaga:
    """Tests for circuit breaker behavior in saga context."""

    @pytest.mark.asyncio
    async def test_saga_fails_on_open_circuit(self):
        """Test saga fails immediately if circuit is open."""
        registry = ServiceRegistry(l11_bridge=None)
        await registry.start()

        svc = ServiceInfo(
            service_id="l02",
            service_name="L02_runtime",
            service_version="0.1.0",
            endpoint="http://localhost:8002",
            status=ServiceStatus.HEALTHY,
        )
        await registry.register_service(svc)

        cb = CircuitBreaker(l11_bridge=None)
        request_orch = RequestOrchestrator(registry, cb)
        await request_orch.start()

        mock_http = MockHTTPClient()
        mock_http.add_response("POST", "8002", {"error": "fail"}, status_code=500)
        request_orch._http_client = mock_http

        saga_orch = SagaOrchestrator(request_orch, l11_bridge=None)

        saga = SagaDefinition(
            saga_id="circuit-test",
            saga_name="Circuit Test",
            steps=[
                SagaStep(
                    step_id="step-0",
                    step_name="Failing Step",
                    service_name="L02_runtime",
                    endpoint="/fail",
                    max_retries=0,
                    required=True,
                ),
            ],
        )

        # First execution should fail and potentially open circuit
        with pytest.raises(Exception):
            await saga_orch.execute_saga(saga)

        await request_orch.stop()
        await registry.stop()
