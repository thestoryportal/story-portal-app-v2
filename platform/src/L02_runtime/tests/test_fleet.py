"""
Tests for Fleet Manager and Warm Pool Manager

Basic tests for fleet scaling and warm pool operations.
"""

import pytest
import asyncio

from ..services.fleet_manager import FleetManager, ScalingDecision
from ..services.warm_pool_manager import WarmPoolManager
from ..models import AgentConfig, TrustLevel, ResourceLimits
from ..models.fleet_models import ScalingMetrics


@pytest.fixture
def fleet_manager():
    """Create FleetManager instance"""
    return FleetManager(config={
        "min_replicas": 1,
        "max_replicas": 10,
        "target_cpu_utilization": 70,
        "scale_up_stabilization_seconds": 5,
        "scale_down_stabilization_seconds": 10,
    })


@pytest.fixture
def warm_pool_manager():
    """Create WarmPoolManager instance"""
    return WarmPoolManager(config={
        "enabled": True,
        "size": 3,
        "runtime_class": "gvisor",
        "refresh_interval_seconds": 60,
        "max_instance_age_seconds": 300,
    })


@pytest.mark.asyncio
async def test_fleet_manager_initialization(fleet_manager):
    """Test fleet manager initialization"""
    await fleet_manager.initialize()
    assert fleet_manager.min_replicas == 1
    assert fleet_manager.max_replicas == 10
    assert fleet_manager.target_cpu_utilization == 70


@pytest.mark.asyncio
async def test_evaluate_scaling_no_action(fleet_manager):
    """Test scaling evaluation with no action needed"""
    await fleet_manager.initialize()

    metrics = ScalingMetrics(
        current_replicas=5,
        desired_replicas=5,
        avg_cpu_utilization=70.0,  # At target
        avg_memory_utilization=50.0,
        pending_requests=0,
    )

    decision = await fleet_manager.evaluate_scaling(metrics)

    assert decision.action == "no_action"
    assert decision.current_replicas == 5


@pytest.mark.asyncio
async def test_evaluate_scaling_scale_up(fleet_manager):
    """Test scaling evaluation with scale up needed"""
    await fleet_manager.initialize()

    metrics = ScalingMetrics(
        current_replicas=5,
        desired_replicas=5,
        avg_cpu_utilization=90.0,  # Above target
        avg_memory_utilization=50.0,
        pending_requests=10,
    )

    decision = await fleet_manager.evaluate_scaling(metrics)

    assert decision.action == "scale_up"
    assert decision.target_replicas > decision.current_replicas


@pytest.mark.asyncio
async def test_evaluate_scaling_scale_down(fleet_manager):
    """Test scaling evaluation with scale down needed"""
    await fleet_manager.initialize()

    metrics = ScalingMetrics(
        current_replicas=5,
        desired_replicas=5,
        avg_cpu_utilization=30.0,  # Below target
        avg_memory_utilization=20.0,
        pending_requests=0,
    )

    decision = await fleet_manager.evaluate_scaling(metrics)

    assert decision.action == "scale_down"
    assert decision.target_replicas < decision.current_replicas


@pytest.mark.asyncio
async def test_evaluate_scaling_respects_min_max(fleet_manager):
    """Test scaling respects min/max limits"""
    await fleet_manager.initialize()

    # Test max limit
    metrics = ScalingMetrics(
        current_replicas=10,
        desired_replicas=10,
        avg_cpu_utilization=100.0,
        avg_memory_utilization=90.0,
        pending_requests=100,
    )

    decision = await fleet_manager.evaluate_scaling(metrics)
    assert decision.target_replicas <= fleet_manager.max_replicas

    # Test min limit
    metrics = ScalingMetrics(
        current_replicas=1,
        desired_replicas=1,
        avg_cpu_utilization=10.0,
        avg_memory_utilization=10.0,
        pending_requests=0,
    )

    decision = await fleet_manager.evaluate_scaling(metrics)
    assert decision.target_replicas >= fleet_manager.min_replicas


@pytest.mark.asyncio
async def test_warm_pool_manager_initialization(warm_pool_manager):
    """Test warm pool manager initialization"""
    # Note: This will try to fill the pool, which requires lifecycle manager
    # For testing without dependencies, just check config
    assert warm_pool_manager.enabled is True
    assert warm_pool_manager.pool_size == 3


@pytest.mark.asyncio
async def test_warm_pool_get_status(warm_pool_manager):
    """Test warm pool status retrieval"""
    status = await warm_pool_manager.get_pool_status()

    assert "enabled" in status
    assert "target_size" in status
    assert "current_size" in status
    assert status["enabled"] is True
    assert status["target_size"] == 3


@pytest.mark.asyncio
async def test_warm_pool_cache_key_generation(warm_pool_manager):
    """Test warm pool manager configuration"""
    assert warm_pool_manager.pool_size == 3
    assert warm_pool_manager.max_instance_age == 300
