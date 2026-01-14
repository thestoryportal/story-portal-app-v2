"""
Tests for Resource Manager

Basic tests for resource quota management and enforcement.
"""

import pytest
import asyncio

from ..services.resource_manager import (
    ResourceManager,
    ResourceError,
    EnforcementMode,
    QuotaAction,
)
from ..models import ResourceLimits
from ..models.resource_models import QuotaScope


@pytest.fixture
def resource_manager():
    """Create ResourceManager instance"""
    return ResourceManager(config={
        "default_limits": {
            "cpu": "1",
            "memory": "1Gi",
            "tokens_per_hour": 50000,
        },
        "enforcement": {
            "cpu": "hard",
            "memory": "hard",
            "tokens": "soft_then_hard",
        },
        "token_budget_action": "suspend",
        "usage_report_interval_seconds": 1,
    })


@pytest.mark.asyncio
async def test_resource_manager_initialization(resource_manager):
    """Test resource manager initialization"""
    await resource_manager.initialize()
    assert resource_manager.cpu_enforcement == EnforcementMode.HARD
    assert resource_manager.memory_enforcement == EnforcementMode.HARD
    assert resource_manager.token_enforcement == EnforcementMode.SOFT_THEN_HARD
    assert resource_manager.token_budget_action == QuotaAction.SUSPEND


@pytest.mark.asyncio
async def test_create_quota(resource_manager):
    """Test quota creation"""
    await resource_manager.initialize()

    quota = await resource_manager.create_quota(
        agent_id="test-agent-1",
        limits=ResourceLimits(
            cpu="2",
            memory="2Gi",
            tokens_per_hour=100000,
        ),
    )

    assert quota.scope == QuotaScope.AGENT
    assert quota.target_id == "test-agent-1"
    assert quota.limits["cpu"] == "2"
    assert quota.limits["memory"] == "2Gi"
    assert quota.limits["tokens_per_hour"] == 100000


@pytest.mark.asyncio
async def test_create_quota_with_defaults(resource_manager):
    """Test quota creation with default limits"""
    await resource_manager.initialize()

    quota = await resource_manager.create_quota(agent_id="test-agent-2")

    assert quota.limits["cpu"] == "1"
    assert quota.limits["memory"] == "1Gi"
    assert quota.limits["tokens_per_hour"] == 50000


@pytest.mark.asyncio
async def test_get_quota(resource_manager):
    """Test getting quota"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    quota = await resource_manager.get_quota("test-agent-1")
    assert quota.target_id == "test-agent-1"


@pytest.mark.asyncio
async def test_get_quota_not_found(resource_manager):
    """Test getting non-existent quota"""
    await resource_manager.initialize()

    with pytest.raises(ResourceError) as exc_info:
        await resource_manager.get_quota("nonexistent-agent")

    assert exc_info.value.code == "E2070"


@pytest.mark.asyncio
async def test_update_quota(resource_manager):
    """Test quota update"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    new_limits = ResourceLimits(
        cpu="4",
        memory="4Gi",
        tokens_per_hour=200000,
    )

    updated_quota = await resource_manager.update_quota(
        agent_id="test-agent-1",
        limits=new_limits,
    )

    assert updated_quota.limits["cpu"] == "4"
    assert updated_quota.limits["memory"] == "4Gi"
    assert updated_quota.limits["tokens_per_hour"] == 200000


@pytest.mark.asyncio
async def test_report_usage(resource_manager):
    """Test usage reporting"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    await resource_manager.report_usage(
        agent_id="test-agent-1",
        cpu_seconds=0.5,
        memory_mb=512,
        tokens=1000,
    )

    usage = await resource_manager.get_usage("test-agent-1")
    assert usage.cpu_seconds == 0.5
    assert usage.memory_peak_mb == 512
    assert usage.tokens_consumed == 1000


@pytest.mark.asyncio
async def test_report_usage_accumulation(resource_manager):
    """Test usage accumulation"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    # Report usage multiple times
    await resource_manager.report_usage(
        agent_id="test-agent-1",
        cpu_seconds=0.5,
        memory_mb=512,
        tokens=1000,
    )

    await resource_manager.report_usage(
        agent_id="test-agent-1",
        cpu_seconds=0.3,
        memory_mb=600,
        tokens=500,
    )

    usage = await resource_manager.get_usage("test-agent-1")
    assert usage.cpu_seconds == 0.8
    assert usage.memory_peak_mb == 600  # Max of 512 and 600
    assert usage.tokens_consumed == 1500


@pytest.mark.asyncio
async def test_reset_quota(resource_manager):
    """Test quota reset"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    await resource_manager.report_usage(
        agent_id="test-agent-1",
        cpu_seconds=0.5,
        tokens=1000,
    )

    quota_before = await resource_manager.get_quota("test-agent-1")
    assert quota_before.usage.cpu_seconds == 0.5

    await resource_manager.reset_quota("test-agent-1")

    quota_after = await resource_manager.get_quota("test-agent-1")
    assert quota_after.usage.cpu_seconds == 0.0
    assert quota_after.usage.tokens_consumed == 0


@pytest.mark.asyncio
async def test_cleanup_quota(resource_manager):
    """Test quota cleanup"""
    await resource_manager.initialize()

    await resource_manager.create_quota(agent_id="test-agent-1")

    assert "test-agent-1" in resource_manager._quotas

    await resource_manager.cleanup_quota("test-agent-1")

    assert "test-agent-1" not in resource_manager._quotas


@pytest.mark.asyncio
async def test_parse_cpu_limit(resource_manager):
    """Test CPU limit parsing"""
    assert resource_manager._parse_cpu_limit("2") == 2.0
    assert resource_manager._parse_cpu_limit("500m") == 0.5
    assert resource_manager._parse_cpu_limit("1.5") == 1.5


@pytest.mark.asyncio
async def test_parse_memory_limit(resource_manager):
    """Test memory limit parsing"""
    assert resource_manager._parse_memory_to_mb("1Gi") == 1024.0
    assert resource_manager._parse_memory_to_mb("512Mi") == 512.0
    assert resource_manager._parse_memory_to_mb("2G") == 2000.0
    assert resource_manager._parse_memory_to_mb("256M") == 256.0
