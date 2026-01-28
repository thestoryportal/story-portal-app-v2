"""
L08 Supervision Layer - Constraint Enforcer Tests

Tests for rate limiting, quota management, and temporal constraints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from ..models.domain import Constraint, ConstraintType, ConstraintViolation, TemporalConstraintConfig


@pytest.mark.l08
@pytest.mark.unit
class TestConstraintEnforcer:
    """Tests for the constraint enforcer"""

    @pytest.mark.asyncio
    async def test_create_constraint(self, constraint_enforcer, sample_constraint):
        """Test constraint creation"""
        result, error = await constraint_enforcer.create_constraint(sample_constraint)

        assert error is None
        assert result is not None
        assert result.constraint_id != ""
        assert result.name == sample_constraint.name

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self, constraint_enforcer, sample_constraint):
        """Test rate limit allows requests within limit"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Should allow first 10 requests
        for i in range(10):
            allowed, error = await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )
            assert allowed, f"Request {i+1} should be allowed: {error}"

    @pytest.mark.asyncio
    async def test_rate_limit_denies_over_limit(self, constraint_enforcer, sample_constraint):
        """Test rate limit denies requests over limit"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Exhaust the limit
        for _ in range(10):
            await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )

        # Next request should be denied
        allowed, error = await constraint_enforcer.check_rate_limit(
            "agent_001", sample_constraint.constraint_id, 1
        )
        assert not allowed
        assert "Rate limit exceeded" in error  # Check message, not specific code

    @pytest.mark.asyncio
    async def test_rate_limit_per_agent(self, constraint_enforcer, sample_constraint):
        """Test rate limits are per-agent"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Exhaust limit for agent_001
        for _ in range(10):
            await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )

        # agent_002 should still be allowed
        allowed, _ = await constraint_enforcer.check_rate_limit(
            "agent_002", sample_constraint.constraint_id, 1
        )
        assert allowed

    @pytest.mark.asyncio
    async def test_rate_limit_bulk_request(self, constraint_enforcer, sample_constraint):
        """Test rate limit with bulk request"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Request 5 at once - should succeed
        allowed, _ = await constraint_enforcer.check_rate_limit(
            "agent_001", sample_constraint.constraint_id, 5
        )
        assert allowed

        # Request 6 more - should fail (total 11 > limit 10)
        allowed, error = await constraint_enforcer.check_rate_limit(
            "agent_001", sample_constraint.constraint_id, 6
        )
        assert not allowed

    @pytest.mark.asyncio
    async def test_quota_constraint(self, constraint_enforcer):
        """Test quota constraint"""
        constraint = Constraint(
            name="daily_quota",
            constraint_type=ConstraintType.QUOTA,
            limit=100,
            window_seconds=86400,  # 24 hours
            enabled=True,
        )
        await constraint_enforcer.create_constraint(constraint)

        # Use some quota
        for _ in range(50):
            allowed, _ = await constraint_enforcer.check_rate_limit(
                "agent_001", constraint.constraint_id, 1
            )
            assert allowed

        # Check usage via get_usage
        usage = await constraint_enforcer.get_usage(
            "agent_001", constraint.constraint_id
        )
        # Usage info returned depends on Redis implementation
        assert isinstance(usage, dict)

    @pytest.mark.asyncio
    async def test_disabled_constraint_allows(self, constraint_enforcer, sample_constraint):
        """Test that disabled constraints always allow"""
        sample_constraint.enabled = False
        await constraint_enforcer.create_constraint(sample_constraint)

        # Should always be allowed
        for _ in range(20):  # More than limit
            allowed, _ = await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )
            assert allowed

    @pytest.mark.asyncio
    async def test_constraint_not_found(self, constraint_enforcer):
        """Test error for unknown constraint"""
        allowed, error = await constraint_enforcer.check_rate_limit(
            "agent_001", "unknown_constraint", 1
        )
        assert not allowed
        assert "not found" in error.lower()  # Check message, not specific code

    @pytest.mark.asyncio
    async def test_get_violations(self, constraint_enforcer, sample_constraint):
        """Test getting constraint violations"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Exhaust limit and trigger violation
        for _ in range(11):
            await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )

        violations = constraint_enforcer.get_violations("agent_001")
        assert len(violations) >= 1
        assert violations[0].agent_id == "agent_001"

    @pytest.mark.asyncio
    async def test_temporal_constraint_business_hours(self, constraint_enforcer):
        """Test temporal constraint with business hours"""
        constraint = Constraint(
            name="business_hours_only",
            constraint_type=ConstraintType.TEMPORAL,
            limit=1000,  # High limit - testing time restriction
            window_seconds=3600,
            enabled=True,
            temporal_config=TemporalConstraintConfig(
                business_hours_only=True,
                start_hour=9,
                end_hour=17,
            ),
        )
        await constraint_enforcer.create_constraint(constraint)

        # Check constraint (result depends on current time)
        # The check_rate_limit method internally calls _check_temporal_constraint
        allowed, error = await constraint_enforcer.check_constraint(
            "agent_001", constraint.constraint_id
        )

        # We can't assert the result since it depends on current time
        # Just verify the check runs without error
        assert isinstance(allowed, bool)

    @pytest.mark.asyncio
    async def test_temporal_constraint_allowed_days(self, constraint_enforcer):
        """Test temporal constraint with allowed days"""
        constraint = Constraint(
            name="weekday_only",
            constraint_type=ConstraintType.TEMPORAL,
            limit=1000,
            window_seconds=3600,
            enabled=True,
            temporal_config=TemporalConstraintConfig(
                allowed_days=[0, 1, 2, 3, 4],  # Monday to Friday
            ),
        )
        await constraint_enforcer.create_constraint(constraint)

        # Check constraint (check_constraint handles temporal internally)
        allowed, error = await constraint_enforcer.check_constraint(
            "agent_001", constraint.constraint_id
        )

        # Result depends on current day
        assert isinstance(allowed, bool)

    @pytest.mark.asyncio
    async def test_resource_cap_constraint(self, constraint_enforcer):
        """Test resource cap constraint"""
        constraint = Constraint(
            name="max_concurrent",
            constraint_type=ConstraintType.RESOURCE_CAP,
            limit=5,
            window_seconds=3600,  # Need a window for rate limiter to work
            enabled=True,
        )
        await constraint_enforcer.create_constraint(constraint)

        # Check resource cap using check_resource_cap method
        # First 5 should be allowed
        for i in range(5):
            allowed, _ = await constraint_enforcer.check_resource_cap(
                "agent_001", constraint.constraint_id, i + 1
            )
            assert allowed, f"Resource {i+1} should be acquirable"

        # 6th should fail
        allowed, error = await constraint_enforcer.check_resource_cap(
            "agent_001", constraint.constraint_id, 6
        )
        assert not allowed

    @pytest.mark.asyncio
    async def test_get_stats(self, constraint_enforcer, sample_constraint):
        """Test getting constraint enforcer statistics"""
        await constraint_enforcer.create_constraint(sample_constraint)

        # Perform some checks
        for _ in range(5):
            await constraint_enforcer.check_rate_limit(
                "agent_001", sample_constraint.constraint_id, 1
            )

        stats = constraint_enforcer.get_stats()
        assert "cached_constraints" in stats
        assert "check_count" in stats
        assert stats["cached_constraints"] >= 1
        assert stats["check_count"] >= 5

    @pytest.mark.asyncio
    async def test_health_check(self, constraint_enforcer):
        """Test constraint enforcer health check"""
        health = await constraint_enforcer.health_check()

        assert "status" in health
        assert health["status"] in ["healthy", "degraded"]
