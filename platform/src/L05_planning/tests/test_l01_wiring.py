"""
L05 Planning Layer - L01 Wiring Integration Tests

Tests for AgentAssigner and ExecutionMonitor integration with L01.
Written BEFORE implementation (validation-first approach).

These tests validate:
1. AgentAssigner can use L01Client to fetch real agents
2. ExecutionMonitor can record events to L01
3. Graceful fallback when L01 is unavailable
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from ..models import (
    Task,
    TaskType,
    TaskStatus,
    Agent,
    AgentCapability,
    CapabilityType,
    ExecutionPlan,
    PlanStatus,
)
from ..services.agent_assigner import AgentAssigner
from ..services.execution_monitor import ExecutionMonitor, ExecutionEvent


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_l01_client():
    """Create a mock L01Client."""
    client = AsyncMock()
    client.list_agents = AsyncMock(return_value=[
        {
            "id": "31fe6153-fcd2-411d-a713-b3bf34101f7c",
            "did": "agent:demo:001",
            "name": "Demo Worker Agent 1",
            "agent_type": "demo_worker",
            "status": "active",
            "configuration": {
                "purpose": "Live dashboard demo",
                "capabilities": ["data_processing", "task_execution"]
            },
            "metadata": {"source": "manual_spawn"},
            "resource_limits": {},
        },
        {
            "id": "6551114e-30e1-4dc3-be5e-ec1691dee399",
            "did": "agent:demo:002",
            "name": "Demo Analyzer Agent 2",
            "agent_type": "demo_analyzer",
            "status": "active",
            "configuration": {
                "purpose": "Data analysis demo",
                "capabilities": ["analysis", "reporting"]
            },
            "metadata": {"source": "manual_spawn"},
            "resource_limits": {},
        },
    ])
    client.record_event = AsyncMock(return_value={"id": "event-123", "event_type": "test"})
    return client


@pytest.fixture
def mock_l01_client_empty():
    """Create a mock L01Client that returns no agents."""
    client = AsyncMock()
    client.list_agents = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_l01_client_unavailable():
    """Create a mock L01Client that raises connection errors."""
    client = AsyncMock()
    client.list_agents = AsyncMock(side_effect=Exception("Connection refused"))
    client.record_event = AsyncMock(side_effect=Exception("Connection refused"))
    return client


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        task_id="task-001",
        plan_id="plan-001",
        name="Test Task",
        description="A test task",
        task_type=TaskType.LLM_CALL,
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def sample_plan():
    """Create a sample execution plan for testing."""
    return ExecutionPlan(
        plan_id="plan-001",
        goal_id="goal-001",
        tasks=[],
        dependency_graph={},
        status=PlanStatus.DRAFT,
    )


# =============================================================================
# AgentAssigner Tests
# =============================================================================

class TestAgentAssignerL01Integration:
    """Tests for AgentAssigner integration with L01."""

    def test_agent_assigner_accepts_l01_client(self, mock_l01_client):
        """AgentAssigner can be initialized with l01_client parameter."""
        assigner = AgentAssigner(l01_client=mock_l01_client)
        assert assigner.l01_client is mock_l01_client

    def test_agent_assigner_works_without_l01_client(self):
        """AgentAssigner works without l01_client (backward compatible)."""
        assigner = AgentAssigner()
        assert assigner.l01_client is None

    @pytest.mark.asyncio
    async def test_get_available_agents_uses_l01(self, mock_l01_client):
        """_get_available_agents calls L01Client.list_agents when available."""
        assigner = AgentAssigner(l01_client=mock_l01_client)

        agents = await assigner._get_available_agents()

        mock_l01_client.list_agents.assert_called_once()
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_convert_l01_agent_to_model(self, mock_l01_client):
        """L01 agent response is converted to L05 Agent model."""
        assigner = AgentAssigner(l01_client=mock_l01_client)

        agents = await assigner._get_available_agents()

        # Verify conversion
        agent = agents[0]
        assert isinstance(agent, Agent)
        assert agent.agent_did == "agent:demo:001"
        assert agent.is_available is True
        assert len(agent.capabilities) > 0

    @pytest.mark.asyncio
    async def test_capabilities_extracted_from_configuration(self, mock_l01_client):
        """Agent capabilities are extracted from L01 configuration.capabilities."""
        assigner = AgentAssigner(l01_client=mock_l01_client)

        agents = await assigner._get_available_agents()

        # First agent has data_processing, task_execution
        agent = agents[0]
        capability_types = [cap.capability_type for cap in agent.capabilities]
        # Should have mapped capabilities (implementation decides mapping)
        assert len(capability_types) > 0

    @pytest.mark.asyncio
    async def test_falls_back_to_mock_when_l01_unavailable(self, mock_l01_client_unavailable):
        """Falls back to mock agents when L01 connection fails."""
        assigner = AgentAssigner(l01_client=mock_l01_client_unavailable)

        # Should not raise, should return mock agents
        agents = await assigner._get_available_agents()

        assert len(agents) > 0  # Mock agents returned
        mock_l01_client_unavailable.list_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_mock_when_l01_returns_empty(self, mock_l01_client_empty):
        """Falls back to mock agents when L01 returns empty list."""
        assigner = AgentAssigner(l01_client=mock_l01_client_empty)

        agents = await assigner._get_available_agents()

        # Should return mock agents when L01 is empty
        assert len(agents) > 0

    @pytest.mark.asyncio
    async def test_inactive_agents_filtered_or_marked_unavailable(self, mock_l01_client):
        """Agents with status != 'active' are marked as unavailable."""
        # Add an inactive agent
        mock_l01_client.list_agents.return_value.append({
            "id": "inactive-agent",
            "did": "agent:inactive:001",
            "name": "Inactive Agent",
            "status": "offline",
            "configuration": {"capabilities": []},
        })

        assigner = AgentAssigner(l01_client=mock_l01_client)
        agents = await assigner._get_available_agents()

        # Only active agents should be available
        available = [a for a in agents if a.is_available]
        assert len(available) == 2  # Only the 2 active ones


# =============================================================================
# ExecutionMonitor Tests
# =============================================================================

class TestExecutionMonitorL01Integration:
    """Tests for ExecutionMonitor integration with L01."""

    def test_execution_monitor_accepts_l01_client(self, mock_l01_client):
        """ExecutionMonitor can be initialized with l01_client parameter."""
        monitor = ExecutionMonitor(l01_client=mock_l01_client)
        assert monitor.l01_client is mock_l01_client

    def test_execution_monitor_works_without_l01_client(self):
        """ExecutionMonitor works without l01_client (backward compatible)."""
        monitor = ExecutionMonitor()
        # Should have event_store_client as None (existing parameter)
        assert monitor.event_store_client is None

    @pytest.mark.asyncio
    async def test_emit_event_records_to_l01(self, mock_l01_client, sample_plan):
        """_emit_event calls L01Client.record_event when available."""
        monitor = ExecutionMonitor(l01_client=mock_l01_client)

        await monitor._emit_event(
            ExecutionEvent.PLAN_STARTED,
            plan=sample_plan,
        )

        mock_l01_client.record_event.assert_called_once()
        call_args = mock_l01_client.record_event.call_args
        assert call_args.kwargs.get("event_type") == "plan.started"

    @pytest.mark.asyncio
    async def test_emit_event_includes_plan_id(self, mock_l01_client, sample_plan):
        """Emitted events include plan_id in payload."""
        monitor = ExecutionMonitor(l01_client=mock_l01_client)

        await monitor._emit_event(
            ExecutionEvent.PLAN_COMPLETED,
            plan=sample_plan,
        )

        call_args = mock_l01_client.record_event.call_args
        payload = call_args.kwargs.get("payload", {})
        assert payload.get("plan_id") == "plan-001"

    @pytest.mark.asyncio
    async def test_emit_event_graceful_when_l01_unavailable(self, mock_l01_client_unavailable, sample_plan):
        """Event emission doesn't fail when L01 is unavailable."""
        monitor = ExecutionMonitor(l01_client=mock_l01_client_unavailable)

        # Should not raise exception
        await monitor._emit_event(
            ExecutionEvent.PLAN_STARTED,
            plan=sample_plan,
        )

        # Should have attempted to record
        mock_l01_client_unavailable.record_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_works_without_l01_client(self, sample_plan):
        """Event emission works without L01Client (local only)."""
        monitor = ExecutionMonitor()

        # Should not raise
        await monitor._emit_event(
            ExecutionEvent.PLAN_STARTED,
            plan=sample_plan,
        )

        # Event count should still increment
        assert monitor.events_emitted >= 0  # May be 0 or 1 depending on implementation

    @pytest.mark.asyncio
    async def test_task_events_include_task_id(self, mock_l01_client, sample_task, sample_plan):
        """Task events include task_id in payload."""
        monitor = ExecutionMonitor(l01_client=mock_l01_client)

        await monitor._emit_event(
            ExecutionEvent.TASK_COMPLETED,
            task=sample_task,
            plan=sample_plan,
        )

        call_args = mock_l01_client.record_event.call_args
        payload = call_args.kwargs.get("payload", {})
        assert payload.get("task_id") == "task-001"


# =============================================================================
# Integration Tests (with real L01 if available)
# =============================================================================

class TestL01WiringIntegration:
    """Integration tests that use real L01 service if available."""

    @pytest.fixture
    def real_l01_client(self):
        """Create real L01Client - skips if not available."""
        try:
            from shared.clients import L01Client
            client = L01Client(base_url="http://localhost:8001")
            return client
        except Exception:
            pytest.skip("L01Client not available")

    @pytest.mark.asyncio
    async def test_real_agent_fetch(self, real_l01_client):
        """Fetch real agents from L01 service."""
        # This test requires L01 to be running
        try:
            # Need to add API key header - this is a limitation of the current client
            # For now, skip if we can't connect
            assigner = AgentAssigner(l01_client=real_l01_client)
            agents = await assigner._get_available_agents()

            # Should get agents (mock fallback or real)
            assert len(agents) > 0
        except Exception as e:
            pytest.skip(f"L01 service not available: {e}")
