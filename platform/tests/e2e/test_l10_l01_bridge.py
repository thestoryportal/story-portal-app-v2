"""
E2E tests for L10 Human Interface - L01 Data Layer Bridge

Tests the integration between L10 Human Interface and L01 Data Layer for:
- User interaction tracking
- Control operation recording and updates
"""

import asyncio
import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.L01_data_layer.client import L01Client
from src.L10_human_interface.services.l01_bridge import L10Bridge


@pytest.fixture
async def l01_client():
    """Create L01 client for testing."""
    client = L01Client(base_url="http://localhost:8002")
    yield client
    await client.close()


@pytest.fixture
async def l10_bridge():
    """Create L10 bridge for testing."""
    bridge = L10Bridge(l01_base_url="http://localhost:8002")
    await bridge.initialize()
    yield bridge
    await bridge.cleanup()


@pytest.mark.asyncio
async def test_record_user_interaction(l10_bridge, l01_client):
    """Test recording user interactions."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record WebSocket connection
    success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="websocket",
        action="connect",
        user_id="test_user",
        client_ip="127.0.0.1",
        user_agent="test-browser",
        session_id="test_session",
        result="success",
    )

    # Assert
    assert success is True


@pytest.mark.asyncio
async def test_record_api_call_interaction(l10_bridge, l01_client):
    """Test recording API call interactions."""
    # Arrange
    timestamp = datetime.utcnow()
    agent_id = uuid4()

    # Act - Record successful API call
    success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="api_call",
        action="list_agents",
        user_id="test_user",
        target_type="agent",
        parameters={"status": "active", "limit": 100},
        result="success",
        client_ip="127.0.0.1",
        session_id="test_session",
    )

    # Assert
    assert success is True

    # Act - Record failed API call
    success_fail = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="api_call",
        action="get_agent",
        user_id="test_user",
        target_type="agent",
        target_id=str(agent_id),
        result="failure",
        error_message="Agent not found",
        client_ip="127.0.0.1",
    )

    # Assert
    assert success_fail is True


@pytest.mark.asyncio
async def test_record_control_operation(l10_bridge, l01_client):
    """Test recording control operations."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record control operation (without target_agent_id to avoid FK constraint)
    operation_id = await l10_bridge.record_control_operation(
        timestamp=timestamp,
        user_id="admin_user",
        operation_type="agent_control",
        command="start",
        target_agent_did="did:example:agent123",
        parameters={"mode": "manual"},
        status="pending",
    )

    # Assert
    assert operation_id != ""
    assert operation_id.startswith("ctrl-")


@pytest.mark.asyncio
async def test_control_operation_lifecycle(l10_bridge, l01_client):
    """Test full control operation lifecycle with updates."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act 1 - Create control operation (without target_agent_id to avoid FK constraint)
    operation_id = await l10_bridge.record_control_operation(
        timestamp=timestamp,
        user_id="admin_user",
        operation_type="agent_control",
        command="stop",
        target_agent_did="did:example:agent456",
        status="pending",
    )
    assert operation_id != ""

    # Act 2 - Update to executing
    update_success = await l10_bridge.update_control_operation(
        operation_id=operation_id,
        status="executing",
        executed_at=datetime.utcnow(),
    )
    assert update_success is True

    # Act 3 - Update to completed
    update_complete = await l10_bridge.update_control_operation(
        operation_id=operation_id,
        status="completed",
        result={"agent_status": "stopped", "shutdown_time_ms": 250},
        completed_at=datetime.utcnow(),
    )
    assert update_complete is True


@pytest.mark.asyncio
async def test_control_operation_failure(l10_bridge, l01_client):
    """Test control operation failure tracking."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act 1 - Create control operation (without target_agent_id to avoid FK constraint)
    operation_id = await l10_bridge.record_control_operation(
        timestamp=timestamp,
        user_id="admin_user",
        operation_type="agent_control",
        command="restart",
        target_agent_did="did:example:agent789",
        status="pending",
    )
    assert operation_id != ""

    # Act 2 - Update to failed
    update_fail = await l10_bridge.update_control_operation(
        operation_id=operation_id,
        status="failed",
        error_message="Agent not responding",
        executed_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    assert update_fail is True


@pytest.mark.asyncio
async def test_multiple_user_interactions(l10_bridge, l01_client):
    """Test recording multiple user interactions from different users."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record interactions from multiple users
    for i in range(5):
        success = await l10_bridge.record_user_interaction(
            timestamp=timestamp,
            interaction_type="click",
            action=f"view_agent_{i}",
            user_id=f"user_{i}",
            target_type="agent",
            target_id=str(uuid4()),
            result="success",
            session_id=f"session_{i}",
        )
        assert success is True

    # Give it a moment to persist
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_dashboard_interaction_flow(l10_bridge, l01_client):
    """Test typical dashboard interaction flow."""
    # Arrange
    user_id = "dashboard_user"
    session_id = f"session-{uuid4()}"
    timestamp = datetime.utcnow()

    # Act 1 - WebSocket connection
    connect_success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="websocket",
        action="connect",
        user_id=user_id,
        session_id=session_id,
        result="success",
    )
    assert connect_success is True

    # Act 2 - View dashboard
    view_success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="view",
        action="dashboard_load",
        user_id=user_id,
        session_id=session_id,
        result="success",
    )
    assert view_success is True

    # Act 3 - List agents
    list_success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="api_call",
        action="list_agents",
        user_id=user_id,
        target_type="agent",
        session_id=session_id,
        result="success",
    )
    assert list_success is True

    # Act 4 - View specific agent
    agent_id = uuid4()
    get_success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="api_call",
        action="get_agent",
        user_id=user_id,
        target_type="agent",
        target_id=str(agent_id),
        session_id=session_id,
        result="success",
    )
    assert get_success is True


@pytest.mark.asyncio
async def test_bridge_disabled(l10_bridge):
    """Test that bridge gracefully handles being disabled."""
    # Arrange
    l10_bridge.enabled = False
    timestamp = datetime.utcnow()

    # Act - Try to record when disabled
    success = await l10_bridge.record_user_interaction(
        timestamp=timestamp,
        interaction_type="click",
        action="test",
    )

    # Assert - Should return False when disabled
    assert success is False

    # Act - Try to record control operation when disabled
    operation_id = await l10_bridge.record_control_operation(
        timestamp=timestamp,
        user_id="test",
        operation_type="test",
        command="test",
    )

    # Assert - Should return empty string when disabled
    assert operation_id == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
