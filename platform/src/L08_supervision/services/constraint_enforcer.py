"""
L08 Supervision Layer - Constraint Enforcer

Rate limiting, quota management, and constraint enforcement
using Redis-based token bucket with atomic CAS operations.
"""

import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from ..models.domain import (
    Constraint,
    ConstraintType,
    ConstraintViolation,
    TemporalConstraintConfig,
)
from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, ConstraintError
from ..integration.redis_client import RedisRateLimiter
from ..integration.l01_bridge import L08Bridge
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


class ConstraintEnforcer:
    """
    Constraint enforcement engine with Redis-based rate limiting.

    Features:
    - Token bucket rate limiting with atomic CAS
    - Quota management per agent/team/department
    - Temporal constraints (business hours, allowed days)
    - Resource caps and operation restrictions
    """

    def __init__(
        self,
        redis_limiter: RedisRateLimiter,
        l01_bridge: L08Bridge,
        audit_manager: AuditManager,
        config: SupervisionConfiguration
    ):
        """
        Initialize Constraint Enforcer.

        Args:
            redis_limiter: Redis rate limiter for atomic operations
            l01_bridge: L01 bridge for constraint storage
            audit_manager: Audit manager for logging violations
            config: Supervision configuration
        """
        self.redis = redis_limiter
        self.l01 = l01_bridge
        self.audit = audit_manager
        self.config = config

        # In-memory constraint cache
        self._constraints: Dict[str, Constraint] = {}
        self._violations: List[ConstraintViolation] = []

        # Metrics
        self._check_count: int = 0
        self._violation_count: int = 0

        logger.info("ConstraintEnforcer initialized")

    async def initialize(self) -> None:
        """Initialize constraint enforcer"""
        await self.redis.initialize()
        logger.info("ConstraintEnforcer ready")

    async def create_constraint(
        self,
        constraint: Constraint
    ) -> Tuple[Optional[Constraint], Optional[str]]:
        """
        Create a new constraint.

        Args:
            constraint: Constraint definition

        Returns:
            Tuple of (created constraint, error message)
        """
        try:
            # Store in L01
            success = await self.l01.store_constraint(constraint.to_dict())
            if not success:
                return None, f"{ErrorCodes.CONSTRAINT_INVALID.value}: Failed to store constraint"

            # Update local cache
            self._constraints[constraint.constraint_id] = constraint

            # Log creation
            await self.audit.log_action(
                action="constraint_created",
                actor_id="system",
                actor_type="system",
                resource_type="constraint",
                resource_id=constraint.constraint_id,
                details={
                    "name": constraint.name,
                    "type": constraint.constraint_type.value,
                    "limit": constraint.limit,
                }
            )

            logger.info(
                f"Created constraint {constraint.constraint_id}: {constraint.name} "
                f"(type={constraint.constraint_type.value}, limit={constraint.limit})"
            )
            return constraint, None

        except Exception as e:
            logger.error(f"Failed to create constraint: {e}")
            return None, str(e)

    async def check_rate_limit(
        self,
        agent_id: str,
        constraint_id: str,
        requested: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Check rate limit constraint.

        Args:
            agent_id: Agent making the request
            constraint_id: Constraint ID to check
            requested: Number of tokens/units requested

        Returns:
            Tuple of (allowed, error message)
        """
        self._check_count += 1

        try:
            # Get constraint
            constraint = await self._get_constraint(constraint_id)
            if not constraint:
                return False, f"{ErrorCodes.CONSTRAINT_NOT_FOUND.value}: Constraint {constraint_id} not found"

            if not constraint.enabled:
                return True, None

            # Check temporal constraints first
            if constraint.temporal_config:
                allowed, error = await self._check_temporal_constraint(
                    constraint.temporal_config
                )
                if not allowed:
                    await self._record_violation(
                        constraint, agent_id, 0, constraint.limit, error
                    )
                    return False, error

            # Check rate limit via Redis
            key = f"ratelimit:{agent_id}:{constraint_id}"
            result = await self.redis.check_rate_limit(
                key=key,
                limit=constraint.limit,
                window_seconds=constraint.window_seconds,
                requested=requested
            )

            if result.error:
                # Redis error - check fail-open config
                if self.config.allow_on_consensus_fail:
                    logger.warning(
                        f"Redis error, allowing request due to fail-open config: {result.error}"
                    )
                    return True, None
                return False, f"{ErrorCodes.CONSENSUS_TIMEOUT.value}: {result.error}"

            if not result.allowed:
                error_msg = (
                    f"{ErrorCodes.RATE_LIMIT_EXCEEDED.value}: "
                    f"Rate limit exceeded ({result.remaining:.0f}/{constraint.limit} remaining)"
                )
                await self._record_violation(
                    constraint, agent_id,
                    constraint.limit - result.remaining, constraint.limit,
                    error_msg
                )
                return False, error_msg

            return True, None

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            if self.config.allow_on_consensus_fail:
                return True, None
            return False, str(e)

    async def check_quota(
        self,
        agent_id: str,
        constraint_id: str,
        usage: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check quota constraint.

        Args:
            agent_id: Agent to check
            constraint_id: Constraint ID
            usage: Current usage amount

        Returns:
            Tuple of (allowed, error message)
        """
        self._check_count += 1

        try:
            constraint = await self._get_constraint(constraint_id)
            if not constraint:
                return False, f"{ErrorCodes.CONSTRAINT_NOT_FOUND.value}: Constraint {constraint_id} not found"

            if not constraint.enabled:
                return True, None

            if usage > constraint.limit:
                error_msg = (
                    f"{ErrorCodes.QUOTA_EXCEEDED.value}: "
                    f"Quota exceeded ({usage}/{constraint.limit})"
                )
                await self._record_violation(
                    constraint, agent_id, usage, constraint.limit, error_msg
                )
                return False, error_msg

            return True, None

        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            return False, str(e)

    async def check_resource_cap(
        self,
        agent_id: str,
        constraint_id: str,
        resource_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check resource cap constraint.

        Args:
            agent_id: Agent to check
            constraint_id: Constraint ID
            resource_count: Current resource count

        Returns:
            Tuple of (allowed, error message)
        """
        self._check_count += 1

        try:
            constraint = await self._get_constraint(constraint_id)
            if not constraint:
                return False, f"{ErrorCodes.CONSTRAINT_NOT_FOUND.value}: Constraint {constraint_id} not found"

            if not constraint.enabled:
                return True, None

            if resource_count > constraint.limit:
                error_msg = (
                    f"{ErrorCodes.RESOURCE_CAP_EXCEEDED.value}: "
                    f"Resource cap exceeded ({resource_count}/{int(constraint.limit)})"
                )
                await self._record_violation(
                    constraint, agent_id, resource_count, constraint.limit, error_msg
                )
                return False, error_msg

            return True, None

        except Exception as e:
            logger.error(f"Resource cap check failed: {e}")
            return False, str(e)

    async def check_constraint(
        self,
        agent_id: str,
        constraint_id: str,
        current_usage: Optional[float] = None,
        requested: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Check any type of constraint.

        Args:
            agent_id: Agent making the request
            constraint_id: Constraint ID to check
            current_usage: Current usage (for quota/resource cap)
            requested: Requested amount (for rate limits)

        Returns:
            Tuple of (allowed, error message)
        """
        constraint = await self._get_constraint(constraint_id)
        if not constraint:
            return False, f"{ErrorCodes.CONSTRAINT_NOT_FOUND.value}: Constraint {constraint_id} not found"

        if constraint.constraint_type == ConstraintType.RATE_LIMIT:
            return await self.check_rate_limit(agent_id, constraint_id, requested)
        elif constraint.constraint_type == ConstraintType.QUOTA:
            return await self.check_quota(agent_id, constraint_id, current_usage or 0)
        elif constraint.constraint_type == ConstraintType.RESOURCE_CAP:
            return await self.check_resource_cap(agent_id, constraint_id, int(current_usage or 0))
        elif constraint.constraint_type == ConstraintType.TEMPORAL:
            if constraint.temporal_config:
                return await self._check_temporal_constraint(constraint.temporal_config)
            return True, None
        else:
            return False, f"{ErrorCodes.CONSTRAINT_INVALID.value}: Unknown constraint type"

    async def _check_temporal_constraint(
        self,
        config: TemporalConstraintConfig
    ) -> Tuple[bool, Optional[str]]:
        """
        Check temporal constraint (business hours, allowed days).

        Args:
            config: Temporal constraint configuration

        Returns:
            Tuple of (allowed, error message)
        """
        now = datetime.now(timezone.utc)

        # Check business hours
        if config.business_hours_only:
            if not (config.start_hour <= now.hour < config.end_hour):
                return False, (
                    f"{ErrorCodes.BUSINESS_HOURS_VIOLATION.value}: "
                    f"Operation not allowed outside business hours "
                    f"({config.start_hour}:00-{config.end_hour}:00 UTC)"
                )

        # Check allowed days (0=Monday, 6=Sunday)
        if config.allowed_days and now.weekday() not in config.allowed_days:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            allowed = [day_names[d] for d in config.allowed_days]
            return False, (
                f"{ErrorCodes.TEMPORAL_CONSTRAINT_VIOLATION.value}: "
                f"Operation not allowed on {day_names[now.weekday()]}. "
                f"Allowed days: {', '.join(allowed)}"
            )

        return True, None

    async def _get_constraint(self, constraint_id: str) -> Optional[Constraint]:
        """Get constraint from cache or L01"""
        # Check cache first
        if constraint_id in self._constraints:
            return self._constraints[constraint_id]

        # Load from L01
        data = await self.l01.get_constraint(constraint_id)
        if not data:
            return None

        constraint = self._dict_to_constraint(data)
        self._constraints[constraint_id] = constraint
        return constraint

    async def _record_violation(
        self,
        constraint: Constraint,
        agent_id: str,
        current_usage: float,
        limit: float,
        error_msg: str
    ) -> None:
        """Record a constraint violation"""
        self._violation_count += 1

        violation = ConstraintViolation(
            constraint_id=constraint.constraint_id,
            constraint_name=constraint.name,
            agent_id=agent_id,
            current_usage=current_usage,
            limit=limit,
            violation_type=constraint.constraint_type.value,
            details={"error": error_msg},
        )

        self._violations.append(violation)

        # Log to audit
        await self.audit.log_constraint_violation(
            violation_id=violation.violation_id,
            agent_id=agent_id,
            constraint_type=constraint.constraint_type.value,
            current_usage=current_usage,
            limit=limit,
        )

        logger.warning(
            f"Constraint violation: {violation.violation_id} "
            f"(agent={agent_id}, constraint={constraint.name})"
        )

    def _dict_to_constraint(self, data: Dict[str, Any]) -> Constraint:
        """Convert dictionary to Constraint"""
        temporal_config = None
        if data.get("temporal_config"):
            tc = data["temporal_config"]
            temporal_config = TemporalConstraintConfig(
                business_hours_only=tc.get("business_hours_only", False),
                start_hour=tc.get("start_hour", 9),
                end_hour=tc.get("end_hour", 17),
                allowed_days=tc.get("allowed_days", [0, 1, 2, 3, 4]),
                timezone=tc.get("timezone", "UTC"),
            )

        return Constraint(
            constraint_id=data.get("constraint_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            constraint_type=ConstraintType(data.get("constraint_type", "RATE_LIMIT")),
            limit=data.get("limit", 0),
            window_seconds=data.get("window_seconds", 3600),
            agent_id=data.get("agent_id"),
            scope=data.get("scope", "global"),
            temporal_config=temporal_config,
            enabled=data.get("enabled", True),
        )

    async def get_constraints_for_agent(
        self,
        agent_id: str
    ) -> List[Constraint]:
        """Get all constraints applicable to an agent"""
        try:
            data_list = await self.l01.get_constraints_for_agent(agent_id)
            return [self._dict_to_constraint(d) for d in data_list]
        except Exception as e:
            logger.error(f"Failed to get constraints for agent: {e}")
            return []

    async def get_usage(
        self,
        agent_id: str,
        constraint_id: str
    ) -> Dict[str, Any]:
        """Get current usage for a rate limit"""
        key = f"ratelimit:{agent_id}:{constraint_id}"
        return await self.redis.get_usage(key)

    async def reset_limit(
        self,
        agent_id: str,
        constraint_id: str
    ) -> bool:
        """Reset rate limit for an agent"""
        key = f"ratelimit:{agent_id}:{constraint_id}"
        return await self.redis.reset(key)

    def get_violations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ConstraintViolation]:
        """Get recent violations"""
        violations = self._violations
        if agent_id:
            violations = [v for v in violations if v.agent_id == agent_id]
        return violations[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get constraint enforcer statistics"""
        return {
            "check_count": self._check_count,
            "violation_count": self._violation_count,
            "violation_rate": self._violation_count / max(1, self._check_count),
            "cached_constraints": len(self._constraints),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for constraint enforcer"""
        redis_health = await self.redis.health_check()
        return {
            "status": "healthy" if redis_health.get("status") == "healthy" else "degraded",
            "redis": redis_health,
            "stats": self.get_stats(),
        }
