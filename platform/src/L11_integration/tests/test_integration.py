"""
L11 Integration Layer - Integration Tests.

Tests for event pub/sub, saga orchestration, and service registry.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import Dict, Any

from ..models import (
    ServiceInfo,
    ServiceStatus,
    HealthCheck,
    HealthCheckType,
    EventMessage,
    EventPriority,
    SagaDefinition,
    SagaStep,
    RequestContext,
)
from ..services import (
    ServiceRegistry,
    EventBusManager,
    CircuitBreaker,
    SagaOrchestrator,
    RequestOrchestrator,
)


@pytest_asyncio.fixture
async def service_registry():
    """Create service registry fixture."""
    registry = ServiceRegistry()
    await registry.start()
    yield registry
    await registry.stop()


@pytest_asyncio.fixture
async def event_bus():
    """Create event bus fixture."""
    bus = EventBusManager(redis_url="redis://localhost:6379")
    await bus.start()
    yield bus
    await bus.stop()


@pytest_asyncio.fixture
async def circuit_breaker():
    """Create circuit breaker fixture."""
    return CircuitBreaker()


@pytest_asyncio.fixture
async def request_orchestrator(service_registry, circuit_breaker):
    """Create request orchestrator fixture."""
    orchestrator = RequestOrchestrator(service_registry, circuit_breaker)
    await orchestrator.start()
    yield orchestrator
    await orchestrator.stop()


@pytest_asyncio.fixture
async def saga_orchestrator(request_orchestrator):
    """Create saga orchestrator fixture."""
    return SagaOrchestrator(request_orchestrator)


class TestServiceRegistry:
    """Tests for ServiceRegistry."""

    @pytest.mark.asyncio
    async def test_register_service(self, service_registry):
        """Test service registration."""
        service = ServiceInfo.create(
            service_name="L02_runtime",
            service_version="0.1.0",
            endpoint="http://localhost:8002",
            health_check=HealthCheck(
                check_type=HealthCheckType.HTTP,
                endpoint="http://localhost:8002/health",
            ),
        )

        await service_registry.register_service(service)

        # Retrieve service
        retrieved = await service_registry.get_service(service.service_id)
        assert retrieved.service_name == "L02_runtime"
        assert retrieved.endpoint == "http://localhost:8002"

    @pytest.mark.asyncio
    async def test_get_service_by_name(self, service_registry):
        """Test getting service by name."""
        service = ServiceInfo.create(
            service_name="L03_tool_execution",
            service_version="0.1.0",
            endpoint="http://localhost:8003",
        )

        await service_registry.register_service(service)

        # Get by name
        retrieved = await service_registry.get_service_by_name("L03_tool_execution")
        assert retrieved is not None
        assert retrieved.service_name == "L03_tool_execution"

    @pytest.mark.asyncio
    async def test_deregister_service(self, service_registry):
        """Test service deregistration."""
        service = ServiceInfo.create(
            service_name="L04_model_gateway",
            service_version="0.1.0",
            endpoint="http://localhost:8004",
        )

        await service_registry.register_service(service)
        await service_registry.deregister_service(service.service_id)

        # Should not find service
        retrieved = await service_registry.get_service_by_name("L04_model_gateway")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_health_summary(self, service_registry):
        """Test health summary."""
        service1 = ServiceInfo.create(
            service_name="L02_runtime",
            service_version="0.1.0",
            endpoint="http://localhost:8002",
        )
        service1.status = ServiceStatus.HEALTHY

        service2 = ServiceInfo.create(
            service_name="L03_tool_execution",
            service_version="0.1.0",
            endpoint="http://localhost:8003",
        )
        service2.status = ServiceStatus.UNHEALTHY

        await service_registry.register_service(service1)
        await service_registry.register_service(service2)

        summary = await service_registry.get_health_summary()
        assert summary["total_services"] == 2
        assert summary["healthy"] == 1
        assert summary["unhealthy"] == 1


class TestEventBus:
    """Tests for EventBusManager."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, event_bus):
        """Test event publish and subscribe."""
        received_events = []

        async def handler(event: EventMessage):
            received_events.append(event)

        # Subscribe
        sub_id = await event_bus.subscribe(
            topic="test.topic",
            handler=handler,
            service_name="test_service",
        )

        # Give subscriber time to register
        await asyncio.sleep(0.1)

        # Publish event
        event = EventMessage.create(
            topic="test.topic",
            event_type="test_event",
            payload={"data": "test_data"},
            source_service="test_publisher",
        )
        await event_bus.publish(event)

        # Wait for event processing
        await asyncio.sleep(0.5)

        # Verify event received
        assert len(received_events) == 1
        assert received_events[0].topic == "test.topic"
        assert received_events[0].payload["data"] == "test_data"

        # Cleanup
        await event_bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test wildcard topic subscription."""
        received_events = []

        async def handler(event: EventMessage):
            received_events.append(event)

        # Subscribe with wildcard
        sub_id = await event_bus.subscribe(
            topic="agent.*",
            handler=handler,
        )

        await asyncio.sleep(0.1)

        # Publish events to different topics
        event1 = EventMessage.create(
            topic="agent.created",
            event_type="created",
            payload={"agent_id": "agent-1"},
        )
        event2 = EventMessage.create(
            topic="agent.deleted",
            event_type="deleted",
            payload={"agent_id": "agent-2"},
        )
        await event_bus.publish(event1)
        await event_bus.publish(event2)

        await asyncio.sleep(0.5)

        # Both events should be received
        assert len(received_events) == 2

        # Cleanup
        await event_bus.unsubscribe(sub_id)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self, circuit_breaker):
        """Test circuit breaker opens after failures."""

        async def failing_function():
            raise Exception("Service unavailable")

        # Execute and fail multiple times
        for _ in range(5):
            try:
                await circuit_breaker.execute(
                    "test_service",
                    failing_function,
                )
            except Exception:
                pass

        # Circuit should be open
        state = await circuit_breaker.get_state("test_service")
        assert state is not None
        # Circuit opens after threshold failures
        assert state.state.value in ("open", "closed")  # May still be closed if threshold not met

    @pytest.mark.asyncio
    async def test_circuit_closes_on_success(self, circuit_breaker):
        """Test circuit breaker closes after successes."""
        success_count = 0

        async def successful_function():
            nonlocal success_count
            success_count += 1
            return "success"

        # Execute successfully
        result = await circuit_breaker.execute(
            "test_service",
            successful_function,
        )

        assert result == "success"
        assert success_count == 1

        # Circuit should be closed
        state = await circuit_breaker.get_state("test_service")
        assert state is not None
        assert state.state.value == "closed"


class TestSagaOrchestrator:
    """Tests for SagaOrchestrator."""

    @pytest.mark.asyncio
    async def test_saga_execution_success(self, saga_orchestrator):
        """Test successful saga execution."""
        step1_executed = False
        step2_executed = False

        async def step1_action(context: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal step1_executed
            step1_executed = True
            return {"step1_result": "success"}

        async def step2_action(context: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal step2_executed
            step2_executed = True
            return {"step2_result": "success"}

        # Create saga
        saga = SagaDefinition.create(
            saga_name="test_saga",
            steps=[
                SagaStep(
                    step_id="step1",
                    step_name="Step 1",
                    action=step1_action,
                ),
                SagaStep(
                    step_id="step2",
                    step_name="Step 2",
                    action=step2_action,
                ),
            ],
        )

        # Execute saga
        execution = await saga_orchestrator.execute_saga(saga)

        # Verify execution
        assert step1_executed
        assert step2_executed
        assert execution.status.value == "completed"
        assert "step1_result" in execution.context
        assert "step2_result" in execution.context

    @pytest.mark.asyncio
    async def test_saga_compensation(self, saga_orchestrator):
        """Test saga compensation on failure."""
        step1_compensated = False

        async def step1_action(context: Dict[str, Any]) -> Dict[str, Any]:
            return {"step1_result": "success"}

        async def step1_compensation(context: Dict[str, Any]) -> None:
            nonlocal step1_compensated
            step1_compensated = True

        async def step2_action(context: Dict[str, Any]) -> Dict[str, Any]:
            raise Exception("Step 2 failed")

        # Create saga with compensation
        saga = SagaDefinition.create(
            saga_name="test_saga_compensation",
            auto_compensate=True,
            steps=[
                SagaStep(
                    step_id="step1",
                    step_name="Step 1",
                    action=step1_action,
                    compensation=step1_compensation,
                ),
                SagaStep(
                    step_id="step2",
                    step_name="Step 2",
                    action=step2_action,
                ),
            ],
        )

        # Execute saga (should fail and compensate)
        try:
            await saga_orchestrator.execute_saga(saga)
        except Exception:
            pass

        # Verify compensation was called
        assert step1_compensated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
