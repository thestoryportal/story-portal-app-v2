"""
E2E tests for L11 Integration Layer - L01 Data Layer Bridge

Tests the integration between L11 Integration Layer and L01 Data Layer for:
- Saga execution tracking
- Saga step recording and updates
- Circuit breaker event recording
- Service registry event tracking
"""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4

from src.L01_data_layer.client import L01Client
from src.L11_integration.services.l01_bridge import L11Bridge


@pytest.fixture
async def l01_client():
    """Create L01 client for testing."""
    client = L01Client(base_url="http://localhost:8002")
    yield client
    await client.close()


@pytest.fixture
async def l11_bridge():
    """Create L11 bridge for testing."""
    bridge = L11Bridge(l01_base_url="http://localhost:8002")
    await bridge.initialize()
    yield bridge
    await bridge.cleanup()


# ============================================================================
# Saga Execution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_record_saga_execution(l11_bridge, l01_client):
    """Test recording a saga execution."""
    # Arrange
    saga_id = f"saga-test-{uuid4()}"
    started_at = datetime.utcnow()

    # Act
    success = await l11_bridge.record_saga_execution(
        saga_id=saga_id,
        saga_name="order_processing",
        started_at=started_at,
        steps_total=3,
        status="running",
        context={"order_id": "12345", "customer_id": "cust_123"},
        metadata={"priority": "high"},
    )

    # Assert
    assert success is True


@pytest.mark.asyncio
async def test_saga_execution_lifecycle(l11_bridge, l01_client):
    """Test full saga execution lifecycle."""
    # Arrange
    saga_id = f"saga-lifecycle-{uuid4()}"
    started_at = datetime.utcnow()

    # Act 1 - Create saga
    create_success = await l11_bridge.record_saga_execution(
        saga_id=saga_id,
        saga_name="payment_processing",
        started_at=started_at,
        steps_total=4,
        status="running",
    )
    assert create_success is True

    # Act 2 - Update saga progress
    update_progress = await l11_bridge.update_saga_execution(
        saga_id=saga_id,
        status="running",
        steps_completed=2,
        current_step="validate_payment",
    )
    assert update_progress is True

    # Act 3 - Complete saga
    update_complete = await l11_bridge.update_saga_execution(
        saga_id=saga_id,
        status="completed",
        steps_completed=4,
        completed_at=datetime.utcnow(),
    )
    assert update_complete is True


@pytest.mark.asyncio
async def test_saga_execution_failure(l11_bridge, l01_client):
    """Test saga execution failure and compensation."""
    # Arrange
    saga_id = f"saga-fail-{uuid4()}"
    started_at = datetime.utcnow()

    # Act 1 - Create saga
    create_success = await l11_bridge.record_saga_execution(
        saga_id=saga_id,
        saga_name="refund_processing",
        started_at=started_at,
        steps_total=3,
        status="running",
    )
    assert create_success is True

    # Act 2 - Mark as compensating
    update_compensate = await l11_bridge.update_saga_execution(
        saga_id=saga_id,
        status="compensating",
        steps_completed=2,
        steps_failed=1,
        compensation_mode=True,
    )
    assert update_compensate is True

    # Act 3 - Mark as failed
    update_fail = await l11_bridge.update_saga_execution(
        saga_id=saga_id,
        status="failed",
        completed_at=datetime.utcnow(),
        error_message="Payment gateway timeout",
    )
    assert update_fail is True


# ============================================================================
# Saga Step Tests
# ============================================================================

@pytest.mark.asyncio
async def test_record_saga_step(l11_bridge, l01_client):
    """Test recording saga steps."""
    # Arrange
    saga_id = f"saga-steps-{uuid4()}"
    step_id = f"step-{uuid4()}"

    # Act - Record step
    success = await l11_bridge.record_saga_step(
        step_id=step_id,
        saga_id=saga_id,
        step_name="reserve_inventory",
        step_index=0,
        service_id="inventory-service",
        request={"product_id": "prod_123", "quantity": 5},
        status="pending",
    )

    # Assert
    assert success is True


@pytest.mark.asyncio
async def test_saga_step_lifecycle(l11_bridge, l01_client):
    """Test full saga step lifecycle."""
    # Arrange
    saga_id = f"saga-step-lifecycle-{uuid4()}"
    step_id = f"step-{uuid4()}"

    # Act 1 - Create step
    create_success = await l11_bridge.record_saga_step(
        step_id=step_id,
        saga_id=saga_id,
        step_name="charge_payment",
        step_index=1,
        service_id="payment-service",
        request={"amount": 99.99, "currency": "USD"},
        status="pending",
    )
    assert create_success is True

    # Act 2 - Update to executing
    update_executing = await l11_bridge.update_saga_step(
        step_id=step_id,
        status="executing",
        started_at=datetime.utcnow(),
    )
    assert update_executing is True

    # Act 3 - Complete step
    update_complete = await l11_bridge.update_saga_step(
        step_id=step_id,
        status="completed",
        completed_at=datetime.utcnow(),
        response={"transaction_id": "txn_123", "status": "success"},
    )
    assert update_complete is True


@pytest.mark.asyncio
async def test_saga_step_with_compensation(l11_bridge, l01_client):
    """Test saga step failure with compensation."""
    # Arrange
    saga_id = f"saga-compensate-{uuid4()}"
    step_id = f"step-{uuid4()}"

    # Act 1 - Create step
    create_success = await l11_bridge.record_saga_step(
        step_id=step_id,
        saga_id=saga_id,
        step_name="create_order",
        step_index=2,
        service_id="order-service",
        status="pending",
    )
    assert create_success is True

    # Act 2 - Mark as failed
    update_fail = await l11_bridge.update_saga_step(
        step_id=step_id,
        status="failed",
        completed_at=datetime.utcnow(),
        error_message="Database connection lost",
        retry_count=3,
    )
    assert update_fail is True

    # Act 3 - Execute compensation
    update_compensate = await l11_bridge.update_saga_step(
        step_id=step_id,
        compensation_executed=True,
        compensation_result={"rollback": "success"},
    )
    assert update_compensate is True


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

@pytest.mark.asyncio
async def test_record_circuit_breaker_event(l11_bridge, l01_client):
    """Test recording circuit breaker events."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record state change
    success = await l11_bridge.record_circuit_breaker_event(
        timestamp=timestamp,
        service_id="payment-service",
        circuit_name="payment_gateway_circuit",
        event_type="state_change",
        state_to="open",
        state_from="closed",
        failure_count=5,
        failure_threshold=5,
        timeout_seconds=60,
    )

    # Assert
    assert success is True


@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions(l11_bridge, l01_client):
    """Test circuit breaker state transitions."""
    # Arrange
    timestamp = datetime.utcnow()
    service_id = "auth-service"
    circuit_name = "auth_circuit"

    # Act 1 - Open circuit (too many failures)
    open_success = await l11_bridge.record_circuit_breaker_event(
        timestamp=timestamp,
        service_id=service_id,
        circuit_name=circuit_name,
        event_type="state_change",
        state_to="open",
        state_from="closed",
        failure_count=10,
        failure_threshold=10,
        timeout_seconds=30,
        error_message="Too many connection failures",
    )
    assert open_success is True

    # Act 2 - Half-open (after timeout)
    half_open_success = await l11_bridge.record_circuit_breaker_event(
        timestamp=timestamp,
        service_id=service_id,
        circuit_name=circuit_name,
        event_type="state_change",
        state_to="half_open",
        state_from="open",
        failure_count=10,
    )
    assert half_open_success is True

    # Act 3 - Close circuit (successes detected)
    close_success = await l11_bridge.record_circuit_breaker_event(
        timestamp=timestamp,
        service_id=service_id,
        circuit_name=circuit_name,
        event_type="state_change",
        state_to="closed",
        state_from="half_open",
        success_count=5,
    )
    assert close_success is True


# ============================================================================
# Service Registry Tests
# ============================================================================

@pytest.mark.asyncio
async def test_record_service_registry_event(l11_bridge, l01_client):
    """Test recording service registry events."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record service registration
    success = await l11_bridge.record_service_registry_event(
        timestamp=timestamp,
        service_id="agent-executor-1",
        event_type="registered",
        layer="L02",
        host="localhost",
        port=8003,
        health_status="healthy",
        capabilities=["execute_agent", "stream_events"],
        metadata={"version": "1.0.0"},
    )

    # Assert
    assert success is True


@pytest.mark.asyncio
async def test_service_lifecycle_events(l11_bridge, l01_client):
    """Test full service lifecycle in registry."""
    # Arrange
    timestamp = datetime.utcnow()
    service_id = "test-service-123"

    # Act 1 - Register service
    register_success = await l11_bridge.record_service_registry_event(
        timestamp=timestamp,
        service_id=service_id,
        event_type="registered",
        layer="L04",
        host="10.0.0.5",
        port=9000,
        health_status="healthy",
        capabilities=["model_inference"],
    )
    assert register_success is True

    # Act 2 - Health status change
    health_change = await l11_bridge.record_service_registry_event(
        timestamp=timestamp,
        service_id=service_id,
        event_type="health_change",
        health_status="degraded",
        metadata={"reason": "high_latency"},
    )
    assert health_change is True

    # Act 3 - Deregister service
    deregister_success = await l11_bridge.record_service_registry_event(
        timestamp=timestamp,
        service_id=service_id,
        event_type="deregistered",
        health_status="offline",
    )
    assert deregister_success is True


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_distributed_transaction(l11_bridge, l01_client):
    """Test complete distributed transaction with saga and steps."""
    # Arrange
    saga_id = f"saga-distributed-{uuid4()}"
    started_at = datetime.utcnow()

    # Act 1 - Create saga
    saga_success = await l11_bridge.record_saga_execution(
        saga_id=saga_id,
        saga_name="order_fulfillment",
        started_at=started_at,
        steps_total=3,
        status="running",
    )
    assert saga_success is True

    # Act 2 - Record all steps
    step_ids = []
    for i, step_name in enumerate(["reserve_inventory", "charge_payment", "ship_order"]):
        step_id = f"step-{uuid4()}"
        step_ids.append(step_id)

        step_success = await l11_bridge.record_saga_step(
            step_id=step_id,
            saga_id=saga_id,
            step_name=step_name,
            step_index=i,
            service_id=f"{step_name}-service",
            status="pending",
        )
        assert step_success is True

    # Act 3 - Complete all steps
    for step_id in step_ids:
        complete = await l11_bridge.update_saga_step(
            step_id=step_id,
            status="completed",
            completed_at=datetime.utcnow(),
        )
        assert complete is True

    # Act 4 - Complete saga
    saga_complete = await l11_bridge.update_saga_execution(
        saga_id=saga_id,
        status="completed",
        steps_completed=3,
        completed_at=datetime.utcnow(),
    )
    assert saga_complete is True


@pytest.mark.asyncio
async def test_bridge_disabled(l11_bridge):
    """Test that bridge gracefully handles being disabled."""
    # Arrange
    l11_bridge.enabled = False
    timestamp = datetime.utcnow()

    # Act - Try to record when disabled
    saga_success = await l11_bridge.record_saga_execution(
        saga_id="test",
        saga_name="test",
        started_at=timestamp,
        steps_total=1,
    )

    # Assert - Should return False when disabled
    assert saga_success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
