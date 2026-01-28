"""
Tests for Fleet Manager Drain Logic

Tests for graceful drain with in-flight task tracking.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from ..services.fleet_manager import (
    FleetManager,
    FleetError,
    DrainState,
)
from ..models import AgentState


@pytest.fixture
def fleet_manager():
    """Create FleetManager instance with test config"""
    return FleetManager(config={
        "min_replicas": 1,
        "max_replicas": 10,
        "graceful_drain": {
            "timeout_seconds": 5,
            "checkpoint_before_drain": True,
        },
    })


@pytest.fixture
def mock_lifecycle_manager():
    """Create mock LifecycleManager"""
    manager = MagicMock()
    manager.terminate = AsyncMock()
    return manager


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager"""
    manager = MagicMock()
    manager.create_checkpoint = AsyncMock()
    return manager


class TestDrainState:
    """Tests for DrainState enum"""

    def test_drain_states_exist(self):
        """Test DrainState enum values"""
        assert DrainState.ACTIVE.value == "active"
        assert DrainState.DRAINING.value == "draining"
        assert DrainState.DRAINED.value == "drained"


class TestFleetManagerDrain:
    """Tests for FleetManager drain functionality"""

    @pytest.mark.asyncio
    async def test_initial_drain_state_is_active(self, fleet_manager):
        """Test agents start with ACTIVE drain state"""
        assert fleet_manager.get_drain_state("agent-1") == DrainState.ACTIVE

    @pytest.mark.asyncio
    async def test_register_task(self, fleet_manager):
        """Test task registration"""
        fleet_manager.register_task("agent-1", "task-1")
        fleet_manager.register_task("agent-1", "task-2")

        in_flight = await fleet_manager._get_in_flight_tasks("agent-1")
        assert "task-1" in in_flight
        assert "task-2" in in_flight

    @pytest.mark.asyncio
    async def test_complete_task(self, fleet_manager):
        """Test task completion"""
        fleet_manager.register_task("agent-1", "task-1")
        fleet_manager.register_task("agent-1", "task-2")

        fleet_manager.complete_task("agent-1", "task-1")

        in_flight = await fleet_manager._get_in_flight_tasks("agent-1")
        assert "task-1" not in in_flight
        assert "task-2" in in_flight

    @pytest.mark.asyncio
    async def test_graceful_drain_no_tasks(
        self,
        fleet_manager,
        mock_state_manager
    ):
        """Test graceful drain when no tasks in-flight"""
        fleet_manager._state_manager = mock_state_manager
        fleet_manager._active_instances["agent-1"] = {
            "agent_id": "agent-1",
            "session_id": "session-1",
        }

        await fleet_manager._graceful_drain("agent-1")

        # Should complete immediately and be drained
        assert fleet_manager.get_drain_state("agent-1") == DrainState.DRAINED

        # Should have checkpointed
        mock_state_manager.create_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_drain_waits_for_tasks(
        self,
        fleet_manager,
        mock_state_manager
    ):
        """Test graceful drain waits for in-flight tasks"""
        fleet_manager._state_manager = mock_state_manager
        fleet_manager._active_instances["agent-1"] = {
            "agent_id": "agent-1",
            "session_id": "session-1",
        }

        # Register a task
        fleet_manager.register_task("agent-1", "task-1")

        # Start drain in background
        drain_task = asyncio.create_task(
            fleet_manager._graceful_drain("agent-1")
        )

        # Wait a bit then complete the task
        await asyncio.sleep(0.1)
        assert fleet_manager.get_drain_state("agent-1") == DrainState.DRAINING

        fleet_manager.complete_task("agent-1", "task-1")

        # Wait for drain to complete
        await drain_task

        assert fleet_manager.get_drain_state("agent-1") == DrainState.DRAINED

    @pytest.mark.asyncio
    async def test_graceful_drain_timeout(self, fleet_manager):
        """Test graceful drain times out"""
        # Use short timeout
        fleet_manager.drain_timeout = 1

        fleet_manager._active_instances["agent-1"] = {
            "agent_id": "agent-1",
            "session_id": "session-1",
        }

        # Register task that won't complete
        fleet_manager.register_task("agent-1", "stuck-task")

        # Should complete (with timeout) without raising
        await fleet_manager._graceful_drain("agent-1")

        # Should still be marked as drained (for termination to proceed)
        assert fleet_manager.get_drain_state("agent-1") == DrainState.DRAINED

    @pytest.mark.asyncio
    async def test_is_draining(self, fleet_manager, mock_state_manager):
        """Test is_draining check"""
        fleet_manager._state_manager = mock_state_manager
        fleet_manager._active_instances["agent-1"] = {
            "agent_id": "agent-1",
        }

        # Not draining initially
        assert not fleet_manager.is_draining("agent-1")

        # Register task and start drain
        fleet_manager.register_task("agent-1", "task-1")

        drain_task = asyncio.create_task(
            fleet_manager._graceful_drain("agent-1")
        )

        await asyncio.sleep(0.05)

        # Should be draining now
        assert fleet_manager.is_draining("agent-1")

        # Complete task
        fleet_manager.complete_task("agent-1", "task-1")
        await drain_task

        # No longer draining
        assert not fleet_manager.is_draining("agent-1")

    @pytest.mark.asyncio
    async def test_checkpoint_includes_in_flight_tasks(
        self,
        fleet_manager,
        mock_state_manager
    ):
        """Test checkpoint includes in-flight task info"""
        fleet_manager._state_manager = mock_state_manager
        fleet_manager._active_instances["agent-1"] = {
            "agent_id": "agent-1",
            "session_id": "session-1",
        }
        fleet_manager.drain_timeout = 1

        # Register task that won't complete
        fleet_manager.register_task("agent-1", "task-1")

        await fleet_manager._graceful_drain("agent-1")

        # Verify checkpoint was called with in-flight tasks
        call_args = mock_state_manager.create_checkpoint.call_args
        context = call_args.kwargs.get("context") or call_args[1].get("context")
        assert "task-1" in context["in_flight_at_drain"]
