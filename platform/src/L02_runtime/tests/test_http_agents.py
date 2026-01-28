"""
Tests for L02 Agent HTTP API Routes

Tests for agent lifecycle endpoints: spawn, terminate, suspend, resume, state.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..routes.agents import router as agents_router
from ..models import (
    AgentState,
    TrustLevel,
    SpawnResult,
    AgentInstance,
    AgentConfig,
    ResourceLimits,
    SandboxConfiguration,
    ResourceUsage,
    RuntimeClass,
    NetworkPolicy,
)


@pytest.fixture
def mock_runtime():
    """Create mock AgentRuntime"""
    runtime = MagicMock()
    runtime.lifecycle_manager = MagicMock()
    return runtime


@pytest.fixture
def app(mock_runtime):
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(agents_router)
    app.state.runtime = mock_runtime
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestSpawnEndpoint:
    """Tests for POST /api/agents/spawn"""

    def test_spawn_basic(self, client, mock_runtime):
        """Test basic agent spawn"""
        # Setup mock
        spawn_result = SpawnResult(
            agent_id="test-agent-1",
            session_id="session-123",
            state=AgentState.RUNNING,
            sandbox_type="gvisor",
            created_at=datetime.utcnow(),
        )
        mock_runtime.spawn = AsyncMock(return_value=spawn_result)

        # Make request
        response = client.post("/api/agents/spawn", json={
            "agent_id": "test-agent-1",
            "trust_level": "standard",
        })

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent-1"
        assert data["session_id"] == "session-123"
        assert data["state"] == "running"
        assert data["sandbox_type"] == "gvisor"

    def test_spawn_with_full_config(self, client, mock_runtime):
        """Test spawn with full configuration"""
        spawn_result = SpawnResult(
            agent_id="test-agent-2",
            session_id="session-456",
            state=AgentState.RUNNING,
            sandbox_type="kata",
            created_at=datetime.utcnow(),
        )
        mock_runtime.spawn = AsyncMock(return_value=spawn_result)

        response = client.post("/api/agents/spawn", json={
            "agent_id": "test-agent-2",
            "trust_level": "untrusted",
            "resource_limits": {
                "cpu": "4",
                "memory": "4Gi",
                "tokens_per_hour": 200000
            },
            "tools": [
                {
                    "name": "calculator",
                    "description": "A calculator tool",
                    "parameters": {"type": "number"}
                }
            ],
            "environment": {"DEBUG": "true"}
        })

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent-2"
        assert data["sandbox_type"] == "kata"

    def test_spawn_without_runtime(self, client, mock_runtime):
        """Test spawn when runtime is not initialized"""
        client.app.state.runtime = None

        response = client.post("/api/agents/spawn", json={
            "agent_id": "test-agent",
            "trust_level": "standard",
        })

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["error_code"] == "E2000"

    def test_spawn_failure(self, client, mock_runtime):
        """Test spawn failure handling"""
        mock_runtime.spawn = AsyncMock(side_effect=Exception("Spawn failed"))

        response = client.post("/api/agents/spawn", json={
            "agent_id": "test-agent",
            "trust_level": "standard",
        })

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "E2001"


class TestTerminateEndpoint:
    """Tests for POST /api/agents/{agent_id}/terminate"""

    def test_terminate_basic(self, client, mock_runtime):
        """Test basic agent termination"""
        mock_runtime.terminate = AsyncMock()

        response = client.post("/api/agents/test-agent/terminate", json={
            "reason": "User requested termination"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "terminated"
        assert data["agent_id"] == "test-agent"

    def test_terminate_force(self, client, mock_runtime):
        """Test forced termination"""
        mock_runtime.terminate = AsyncMock()

        response = client.post("/api/agents/test-agent/terminate", json={
            "reason": "Emergency shutdown",
            "force": True
        })

        assert response.status_code == 200
        mock_runtime.terminate.assert_called_with(
            agent_id="test-agent",
            reason="Emergency shutdown",
            force=True
        )

    def test_terminate_not_found(self, client, mock_runtime):
        """Test termination of non-existent agent"""
        mock_runtime.terminate = AsyncMock(
            side_effect=Exception("Agent not found")
        )

        response = client.post("/api/agents/nonexistent/terminate", json={
            "reason": "Test"
        })

        assert response.status_code == 404


class TestSuspendEndpoint:
    """Tests for POST /api/agents/{agent_id}/suspend"""

    def test_suspend_with_checkpoint(self, client, mock_runtime):
        """Test suspend with checkpoint creation"""
        mock_runtime.suspend = AsyncMock(return_value="checkpoint-123")
        mock_runtime.get_state = AsyncMock(return_value=AgentState.SUSPENDED)

        response = client.post("/api/agents/test-agent/suspend", json={
            "checkpoint": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert data["checkpoint_id"] == "checkpoint-123"
        assert data["state"] == "suspended"

    def test_suspend_without_checkpoint(self, client, mock_runtime):
        """Test suspend without checkpoint"""
        mock_runtime.suspend = AsyncMock(return_value=None)
        mock_runtime.get_state = AsyncMock(return_value=AgentState.SUSPENDED)

        response = client.post("/api/agents/test-agent/suspend", json={
            "checkpoint": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["checkpoint_id"] is None


class TestResumeEndpoint:
    """Tests for POST /api/agents/{agent_id}/resume"""

    def test_resume_basic(self, client, mock_runtime):
        """Test basic agent resume"""
        mock_runtime.resume = AsyncMock(return_value=AgentState.RUNNING)

        response = client.post("/api/agents/test-agent/resume", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert data["state"] == "running"
        assert data["restored_from_checkpoint"] is False

    def test_resume_from_checkpoint(self, client, mock_runtime):
        """Test resume from specific checkpoint"""
        mock_runtime.resume = AsyncMock(return_value=AgentState.RUNNING)

        response = client.post("/api/agents/test-agent/resume", json={
            "checkpoint_id": "checkpoint-123"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["restored_from_checkpoint"] is True


class TestStateEndpoint:
    """Tests for GET /api/agents/{agent_id}/state"""

    def test_get_state(self, client, mock_runtime):
        """Test getting agent state"""
        instance = AgentInstance(
            agent_id="test-agent",
            session_id="session-123",
            state=AgentState.RUNNING,
            config=AgentConfig(
                agent_id="test-agent",
                trust_level=TrustLevel.STANDARD,
            ),
            sandbox=SandboxConfiguration(
                runtime_class=RuntimeClass.GVISOR,
                trust_level=TrustLevel.STANDARD,
                security_context={},
                network_policy=NetworkPolicy.RESTRICTED,
                resource_limits=ResourceLimits(),
            ),
            resource_usage=ResourceUsage(
                cpu_seconds=10.5,
                memory_peak_mb=256.0,
                tokens_consumed=1000,
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_runtime.lifecycle_manager.get_instance = AsyncMock(return_value=instance)

        response = client.get("/api/agents/test-agent/state")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert data["session_id"] == "session-123"
        assert data["state"] == "running"
        assert data["sandbox_type"] == "gvisor"
        assert data["resource_usage"]["cpu_seconds"] == 10.5

    def test_get_state_not_found(self, client, mock_runtime):
        """Test getting state of non-existent agent"""
        mock_runtime.lifecycle_manager.get_instance = AsyncMock(return_value=None)

        response = client.get("/api/agents/nonexistent/state")

        assert response.status_code == 404
