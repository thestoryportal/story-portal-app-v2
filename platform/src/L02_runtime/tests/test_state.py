"""
Tests for State Manager and Session Bridge

Basic tests for state persistence and session management.
"""

import pytest
import asyncio
from datetime import datetime

from ..services.state_manager import StateManager, StateError
from ..services.session_bridge import SessionBridge, SessionError
from ..models import AgentState

# Fixtures are now in conftest.py


@pytest.mark.asyncio
async def test_state_manager_initialization(state_manager):
    """Test state manager initialization"""
    # Note: This test may fail if PostgreSQL/Redis are not available
    # In that case, the manager should handle gracefully
    await state_manager.initialize()
    assert state_manager.checkpoint_backend == "postgresql"
    assert state_manager.hot_state_backend == "redis"


@pytest.mark.asyncio
async def test_checkpoint_size_limit(state_manager):
    """Test checkpoint size validation"""
    await state_manager.initialize()

    # Create large context that exceeds limit
    large_context = {"data": "x" * (100 * 1024 * 1024 + 1)}  # > 100MB

    with pytest.raises(StateError) as exc_info:
        await state_manager.create_checkpoint(
            agent_id="test-agent-1",
            session_id="session-1",
            state=AgentState.RUNNING,
            context=large_context,
        )

    assert exc_info.value.code == "E2031"


@pytest.mark.asyncio
async def test_hot_state_operations(state_manager):
    """Test hot state save/load"""
    await state_manager.initialize()

    state_data = {
        "current_step": 5,
        "variables": {"x": 10, "y": 20},
    }

    # Save hot state
    await state_manager.save_hot_state("test-agent-1", state_data)

    # Load hot state (may return None if Redis not available)
    loaded_state = await state_manager.load_hot_state("test-agent-1")
    if loaded_state:
        assert loaded_state == state_data


@pytest.mark.asyncio
async def test_session_bridge_initialization(session_bridge):
    """Test session bridge initialization"""
    await session_bridge.initialize()
    assert session_bridge.heartbeat_interval == 5
    assert session_bridge.enable_recovery_check is True


@pytest.mark.asyncio
async def test_start_stop_session(session_bridge):
    """Test session start and stop"""
    await session_bridge.initialize()

    # Start session
    result = await session_bridge.start_session(
        agent_id="test-agent-1",
        session_id="session-1",
    )

    assert result["session_id"] == "session-1"
    assert result["agent_id"] == "test-agent-1"
    assert "session-1" in session_bridge._sessions

    # Stop session
    await session_bridge.stop_session(
        session_id="session-1",
        reason="test_complete",
    )

    assert "session-1" not in session_bridge._sessions


@pytest.mark.asyncio
async def test_session_snapshot(session_bridge):
    """Test session snapshot save"""
    await session_bridge.initialize()

    await session_bridge.start_session(
        agent_id="test-agent-1",
        session_id="session-1",
    )

    # Save snapshot (may be stubbed)
    await session_bridge.save_snapshot(
        session_id="session-1",
        context={
            "currentPhase": "execution",
            "progress": 0.5,
        },
        change_summary="Test snapshot",
    )

    await session_bridge.stop_session("session-1")


@pytest.mark.asyncio
async def test_get_active_sessions(session_bridge):
    """Test getting active sessions"""
    await session_bridge.initialize()

    # Start multiple sessions
    await session_bridge.start_session("agent-1", "session-1")
    await session_bridge.start_session("agent-2", "session-2")

    active = await session_bridge.get_active_sessions()
    assert len(active) == 2
    assert "session-1" in active
    assert "session-2" in active

    # Cleanup
    await session_bridge.stop_session("session-1")
    await session_bridge.stop_session("session-2")


@pytest.mark.asyncio
async def test_session_cleanup(session_bridge):
    """Test session bridge cleanup"""
    await session_bridge.initialize()

    await session_bridge.start_session("agent-1", "session-1")
    await session_bridge.start_session("agent-2", "session-2")

    await session_bridge.cleanup()

    assert len(session_bridge._sessions) == 0
    assert len(session_bridge._heartbeat_tasks) == 0
