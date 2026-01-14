"""
Unit tests for Lifecycle Manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ..models import (
    AgentConfig,
    AgentState,
    TrustLevel,
    ResourceLimits,
    SpawnResult,
)
from ..services import LifecycleManager, LifecycleError, SandboxManager


class TestLifecycleManager:
    """Test Lifecycle Manager"""

    @pytest.fixture
    def mock_backend(self):
        """Create mock runtime backend"""
        backend = AsyncMock()
        backend.initialize = AsyncMock()
        backend.spawn_container = AsyncMock()
        backend.terminate_container = AsyncMock()
        backend.suspend_container = AsyncMock()
        backend.resume_container = AsyncMock()
        backend.get_resource_usage = AsyncMock()
        backend.cleanup = AsyncMock()
        return backend

    @pytest.fixture
    def sandbox_manager(self):
        """Create sandbox manager"""
        config = {
            "default_runtime_class": "runc",
            "available_runtimes": ["runc"],
        }
        return SandboxManager(config)

    @pytest.fixture
    def manager(self, mock_backend, sandbox_manager):
        """Create lifecycle manager"""
        config = {
            "spawn_timeout_seconds": 60,
            "graceful_shutdown_seconds": 30,
            "max_restart_count": 5,
            "enable_suspend": True,
        }
        return LifecycleManager(
            backend=mock_backend,
            sandbox_manager=sandbox_manager,
            config=config
        )

    @pytest.mark.asyncio
    async def test_initialize(self, manager, mock_backend):
        """Test manager initialization"""
        await manager.initialize()
        mock_backend.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_success(self, manager, mock_backend):
        """Test successful agent spawn"""
        config = AgentConfig(
            agent_id="agent-123",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-123",
            session_id="session-456",
            state=AgentState.RUNNING,
            sandbox_type="runc",
            container_id="container-789"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result

        result = await manager.spawn(config)

        assert result.agent_id == "agent-123"
        assert result.state == AgentState.RUNNING
        mock_backend.spawn_container.assert_called_once()

        # Check instance is tracked
        assert "agent-123" in manager._instances

    @pytest.mark.asyncio
    async def test_spawn_with_initial_context(self, manager, mock_backend):
        """Test spawn with initial context"""
        config = AgentConfig(
            agent_id="agent-456",
            trust_level=TrustLevel.TRUSTED
        )

        initial_context = {"session": "abc", "user_id": "user-123"}

        mock_spawn_result = SpawnResult(
            agent_id="agent-456",
            session_id="session-789",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result

        result = await manager.spawn(config, initial_context)

        assert result.agent_id == "agent-456"
        # Verify environment was passed to backend
        call_args = mock_backend.spawn_container.call_args
        assert call_args[1]["environment"]["INITIAL_CONTEXT"] is not None

    @pytest.mark.asyncio
    async def test_terminate_success(self, manager, mock_backend):
        """Test successful agent termination"""
        # First spawn an agent
        config = AgentConfig(
            agent_id="agent-789",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-789",
            session_id="session-111",
            state=AgentState.RUNNING,
            sandbox_type="runc",
            container_id="container-222"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result
        await manager.spawn(config)

        # Now terminate it
        await manager.terminate("agent-789", "test_terminate")

        mock_backend.terminate_container.assert_called_once()
        instance = manager._instances["agent-789"]
        assert instance.state == AgentState.TERMINATED

    @pytest.mark.asyncio
    async def test_terminate_force(self, manager, mock_backend):
        """Test forced termination"""
        config = AgentConfig(
            agent_id="agent-999",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-999",
            session_id="session-333",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result
        await manager.spawn(config)

        await manager.terminate("agent-999", "force_test", force=True)

        call_args = mock_backend.terminate_container.call_args
        assert call_args[1]["force"] == True

    @pytest.mark.asyncio
    async def test_terminate_not_found(self, manager):
        """Test terminate fails for non-existent agent"""
        with pytest.raises(LifecycleError) as exc_info:
            await manager.terminate("nonexistent", "test")

        assert exc_info.value.code == "E2022"

    @pytest.mark.asyncio
    async def test_suspend_success(self, manager, mock_backend):
        """Test successful agent suspend"""
        config = AgentConfig(
            agent_id="agent-suspend",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-suspend",
            session_id="session-suspend",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result
        mock_backend.suspend_container.return_value = "checkpoint-123"

        await manager.spawn(config)
        checkpoint_id = await manager.suspend("agent-suspend")

        assert checkpoint_id == "checkpoint-123"
        instance = manager._instances["agent-suspend"]
        assert instance.state == AgentState.SUSPENDED

    @pytest.mark.asyncio
    async def test_suspend_not_running(self, manager, mock_backend):
        """Test suspend fails if agent not running"""
        config = AgentConfig(
            agent_id="agent-terminated",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-terminated",
            session_id="session-terminated",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result

        await manager.spawn(config)
        await manager.terminate("agent-terminated", "test")

        with pytest.raises(LifecycleError) as exc_info:
            await manager.suspend("agent-terminated")

        assert exc_info.value.code == "E2023"

    @pytest.mark.asyncio
    async def test_resume_success(self, manager, mock_backend):
        """Test successful agent resume"""
        config = AgentConfig(
            agent_id="agent-resume",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-resume",
            session_id="session-resume",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result
        mock_backend.suspend_container.return_value = "checkpoint-456"

        await manager.spawn(config)
        await manager.suspend("agent-resume")

        state = await manager.resume("agent-resume", "checkpoint-456")

        assert state == AgentState.RUNNING
        instance = manager._instances["agent-resume"]
        assert instance.state == AgentState.RUNNING

    @pytest.mark.asyncio
    async def test_get_state(self, manager, mock_backend):
        """Test getting agent state"""
        config = AgentConfig(
            agent_id="agent-state",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-state",
            session_id="session-state",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result

        await manager.spawn(config)

        state = await manager.get_state("agent-state")
        assert state == AgentState.RUNNING

    @pytest.mark.asyncio
    async def test_get_state_not_found(self, manager):
        """Test get_state fails for non-existent agent"""
        with pytest.raises(LifecycleError) as exc_info:
            await manager.get_state("nonexistent")

        assert exc_info.value.code == "E2000"

    @pytest.mark.asyncio
    async def test_list_instances(self, manager, mock_backend):
        """Test listing all instances"""
        config1 = AgentConfig(agent_id="agent-1", trust_level=TrustLevel.STANDARD)
        config2 = AgentConfig(agent_id="agent-2", trust_level=TrustLevel.TRUSTED)

        mock_backend.spawn_container.side_effect = [
            SpawnResult(
                agent_id="agent-1",
                session_id="session-1",
                state=AgentState.RUNNING,
                sandbox_type="runc"
            ),
            SpawnResult(
                agent_id="agent-2",
                session_id="session-2",
                state=AgentState.RUNNING,
                sandbox_type="runc"
            )
        ]

        await manager.spawn(config1)
        await manager.spawn(config2)

        instances = await manager.list_instances()
        assert len(instances) == 2
        assert "agent-1" in instances
        assert "agent-2" in instances

    @pytest.mark.asyncio
    async def test_cleanup(self, manager, mock_backend):
        """Test cleanup terminates all agents"""
        config = AgentConfig(
            agent_id="agent-cleanup",
            trust_level=TrustLevel.STANDARD
        )

        mock_spawn_result = SpawnResult(
            agent_id="agent-cleanup",
            session_id="session-cleanup",
            state=AgentState.RUNNING,
            sandbox_type="runc"
        )
        mock_backend.spawn_container.return_value = mock_spawn_result

        await manager.spawn(config)
        await manager.cleanup()

        mock_backend.cleanup.assert_called_once()
        assert len(manager._instances) == 0
