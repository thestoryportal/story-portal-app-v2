"""
Tests for Health Monitor

Basic tests for health monitoring and probes.
"""

import pytest
import asyncio

from ..services.health_monitor import HealthMonitor, ProbeType
from ..models import AgentState


@pytest.fixture
def health_monitor():
    """Create HealthMonitor instance"""
    return HealthMonitor(config={
        "liveness_probe": {
            "interval_seconds": 1,
            "failure_threshold": 3,
        },
        "readiness_probe": {
            "interval_seconds": 1,
            "failure_threshold": 2,
        },
        "stuck_agent_timeout_seconds": 60,
    })


@pytest.mark.asyncio
async def test_health_monitor_initialization(health_monitor):
    """Test health monitor initialization"""
    await health_monitor.initialize()
    assert health_monitor.liveness_interval == 1
    assert health_monitor.readiness_interval == 1


@pytest.mark.asyncio
async def test_register_unregister_agent(health_monitor):
    """Test agent registration and unregistration"""
    await health_monitor.initialize()

    # Register agent
    await health_monitor.register_agent("agent-1", AgentState.RUNNING)

    assert "agent-1" in health_monitor._health_status
    assert health_monitor._health_status["agent-1"].agent_id == "agent-1"

    # Unregister agent
    await health_monitor.unregister_agent("agent-1")

    assert "agent-1" not in health_monitor._health_status


@pytest.mark.asyncio
async def test_liveness_check_success(health_monitor):
    """Test successful liveness check"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.RUNNING)

    result = await health_monitor.check_liveness("agent-1")

    assert result.success is True
    assert result.probe_type == ProbeType.LIVENESS.value
    assert result.agent_id == "agent-1"


@pytest.mark.asyncio
async def test_liveness_check_untracked_agent(health_monitor):
    """Test liveness check for untracked agent"""
    await health_monitor.initialize()

    result = await health_monitor.check_liveness("nonexistent-agent")

    assert result.success is False
    assert "not tracked" in result.message.lower()


@pytest.mark.asyncio
async def test_readiness_check_success(health_monitor):
    """Test successful readiness check"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.RUNNING)

    result = await health_monitor.check_readiness("agent-1")

    assert result.success is True
    assert result.probe_type == ProbeType.READINESS.value


@pytest.mark.asyncio
async def test_readiness_check_not_running(health_monitor):
    """Test readiness check for non-running agent"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.PENDING)

    result = await health_monitor.check_readiness("agent-1")

    assert result.success is False
    assert "not ready" in result.message.lower()


@pytest.mark.asyncio
async def test_record_request_metrics(health_monitor):
    """Test request metrics recording"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.RUNNING)

    # Record successful request
    await health_monitor.record_request("agent-1", success=True, latency_ms=100.0)

    status = await health_monitor.get_health_status("agent-1")
    assert status.total_requests == 1
    assert status.successful_requests == 1
    assert status.failed_requests == 0
    assert status.error_rate == 0.0

    # Record failed request
    await health_monitor.record_request("agent-1", success=False, latency_ms=200.0)

    status = await health_monitor.get_health_status("agent-1")
    assert status.total_requests == 2
    assert status.successful_requests == 1
    assert status.failed_requests == 1
    assert status.error_rate == 0.5


@pytest.mark.asyncio
async def test_get_metrics_snapshot(health_monitor):
    """Test metrics snapshot retrieval"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.RUNNING)
    await health_monitor.record_request("agent-1", success=True, latency_ms=100.0)

    snapshot = await health_monitor.get_metrics_snapshot()

    assert snapshot.active_agents == 1
    assert snapshot.total_requests == 1
    assert snapshot.successful_requests == 1


@pytest.mark.asyncio
async def test_get_all_health_status(health_monitor):
    """Test getting all health statuses"""
    await health_monitor.initialize()

    await health_monitor.register_agent("agent-1", AgentState.RUNNING)
    await health_monitor.register_agent("agent-2", AgentState.RUNNING)

    all_status = await health_monitor.get_all_health_status()

    assert len(all_status) == 2
    assert "agent-1" in all_status
    assert "agent-2" in all_status
