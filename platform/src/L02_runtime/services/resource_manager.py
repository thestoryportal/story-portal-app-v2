"""
Resource Manager

Enforces CPU, memory, and token quotas for agent instances.
Tracks resource usage and implements enforcement actions.

Based on Section 3.3.8 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum

from ..models import (
    AgentConfig,
    ResourceLimits,
    ResourceUsage,
)
from ..models.resource_models import (
    ResourceQuota,
    QuotaScope,
    QuotaUsage,
)


logger = logging.getLogger(__name__)


class EnforcementMode(Enum):
    """Resource enforcement mode"""
    HARD = "hard"  # Immediately terminate/suspend on breach
    SOFT_THEN_HARD = "soft_then_hard"  # Warn first, then enforce
    WARN_ONLY = "warn_only"  # Only log warnings


class QuotaAction(Enum):
    """Action to take when quota exceeded"""
    WARN = "warn"
    THROTTLE = "throttle"
    SUSPEND = "suspend"
    TERMINATE = "terminate"


class ResourceError(Exception):
    """Resource management error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ResourceManager:
    """
    Manages resource quotas and enforcement for agent instances.

    Responsibilities:
    - Track CPU, memory, and token usage
    - Enforce resource limits
    - Report usage statistics
    - Trigger enforcement actions (warn, throttle, suspend, terminate)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ResourceManager.

        Args:
            config: Configuration dict with:
                - default_limits: Default resource limits
                - enforcement: Enforcement modes for each resource type
                - token_budget_action: Action when token budget exceeded
                - usage_report_interval_seconds: Usage reporting interval
        """
        self.config = config or {}

        # Default limits
        default_limits = self.config.get("default_limits", {})
        self.default_cpu = default_limits.get("cpu", "2")
        self.default_memory = default_limits.get("memory", "2Gi")
        self.default_tokens_per_hour = default_limits.get("tokens_per_hour", 100000)

        # Enforcement modes
        enforcement = self.config.get("enforcement", {})
        self.cpu_enforcement = EnforcementMode(enforcement.get("cpu", "hard"))
        self.memory_enforcement = EnforcementMode(enforcement.get("memory", "hard"))
        self.token_enforcement = EnforcementMode(
            enforcement.get("tokens", "soft_then_hard")
        )

        # Token budget action
        action_str = self.config.get("token_budget_action", "suspend")
        self.token_budget_action = QuotaAction(action_str)

        # Usage reporting interval
        self.usage_report_interval = self.config.get(
            "usage_report_interval_seconds", 60
        )

        # Active quotas: agent_id -> ResourceQuota
        self._quotas: Dict[str, ResourceQuota] = {}

        # Usage tracking: agent_id -> ResourceUsage
        self._usage: Dict[str, ResourceUsage] = {}

        # Warning flags: agent_id -> set of warned resource types
        self._warned: Dict[str, set] = {}

        # Background tasks
        self._report_task: Optional[asyncio.Task] = None

        logger.info(
            f"ResourceManager initialized: "
            f"cpu_enforcement={self.cpu_enforcement.value}, "
            f"memory_enforcement={self.memory_enforcement.value}, "
            f"token_enforcement={self.token_enforcement.value}"
        )

    async def initialize(self) -> None:
        """Initialize resource manager and start background tasks"""
        # Start usage reporting task
        self._report_task = asyncio.create_task(self._usage_reporting_loop())
        logger.info("ResourceManager initialization complete")

    async def create_quota(
        self,
        agent_id: str,
        limits: Optional[ResourceLimits] = None
    ) -> ResourceQuota:
        """
        Create resource quota for an agent.

        Args:
            agent_id: Agent identifier
            limits: Optional resource limits (uses defaults if not provided)

        Returns:
            ResourceQuota
        """
        if limits is None:
            limits = ResourceLimits(
                cpu=self.default_cpu,
                memory=self.default_memory,
                tokens_per_hour=self.default_tokens_per_hour,
            )

        quota = ResourceQuota(
            scope=QuotaScope.AGENT,
            target_id=agent_id,
            limits={
                "cpu": limits.cpu,
                "memory": limits.memory,
                "tokens_per_hour": limits.tokens_per_hour,
            },
            usage=QuotaUsage(),
            reset_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        self._quotas[agent_id] = quota
        self._usage[agent_id] = ResourceUsage()
        self._warned[agent_id] = set()

        logger.info(
            f"Created quota for agent {agent_id}: "
            f"cpu={limits.cpu}, memory={limits.memory}, "
            f"tokens={limits.tokens_per_hour}/hour"
        )

        return quota

    async def get_quota(self, agent_id: str) -> ResourceQuota:
        """
        Get quota for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            ResourceQuota

        Raises:
            ResourceError: If quota not found
        """
        quota = self._quotas.get(agent_id)
        if not quota:
            raise ResourceError(
                code="E2070",
                message=f"Quota not found for agent {agent_id}"
            )
        return quota

    async def update_quota(
        self,
        agent_id: str,
        limits: ResourceLimits
    ) -> ResourceQuota:
        """
        Update quota limits for an agent.

        Args:
            agent_id: Agent identifier
            limits: New resource limits

        Returns:
            Updated ResourceQuota

        Raises:
            ResourceError: If quota update fails
        """
        try:
            quota = await self.get_quota(agent_id)
            quota.limits = {
                "cpu": limits.cpu,
                "memory": limits.memory,
                "tokens_per_hour": limits.tokens_per_hour,
            }
            logger.info(f"Updated quota for agent {agent_id}")
            return quota

        except Exception as e:
            logger.error(f"Failed to update quota for agent {agent_id}: {e}")
            raise ResourceError(
                code="E2073",
                message=f"Quota update failed: {str(e)}"
            )

    async def report_usage(
        self,
        agent_id: str,
        cpu_seconds: Optional[float] = None,
        memory_mb: Optional[float] = None,
        tokens: Optional[int] = None
    ) -> None:
        """
        Report resource usage for an agent.

        Args:
            agent_id: Agent identifier
            cpu_seconds: CPU seconds consumed
            memory_mb: Current memory usage in MB
            tokens: Tokens consumed

        Raises:
            ResourceError: If usage reporting fails
        """
        usage = self._usage.get(agent_id)
        quota = self._quotas.get(agent_id)

        if not usage or not quota:
            raise ResourceError(
                code="E2070",
                message=f"No quota/usage tracking for agent {agent_id}"
            )

        # Update usage
        if cpu_seconds is not None:
            usage.cpu_seconds += cpu_seconds
            quota.usage.cpu_seconds += cpu_seconds

        if memory_mb is not None:
            usage.memory_peak_mb = max(usage.memory_peak_mb, memory_mb)
            quota.usage.memory_peak_mb = max(quota.usage.memory_peak_mb, memory_mb)

        if tokens is not None:
            usage.tokens_consumed += tokens
            quota.usage.tokens_consumed += tokens

        # Check for quota violations
        await self._check_quota_violations(agent_id, quota)

    async def _check_quota_violations(
        self,
        agent_id: str,
        quota: ResourceQuota
    ) -> None:
        """
        Check for quota violations and take enforcement actions.

        Args:
            agent_id: Agent identifier
            quota: Resource quota
        """
        violations = []

        # Check CPU
        cpu_limit = self._parse_cpu_limit(quota.limits.get("cpu", "0"))
        if cpu_limit > 0 and quota.usage.cpu_seconds > cpu_limit:
            violations.append(("cpu", quota.usage.cpu_seconds, cpu_limit))

        # Check memory
        memory_limit = self._parse_memory_to_mb(quota.limits.get("memory", "0Gi"))
        if memory_limit > 0 and quota.usage.memory_peak_mb > memory_limit:
            violations.append(("memory", quota.usage.memory_peak_mb, memory_limit))

        # Check tokens
        token_limit = quota.limits.get("tokens_per_hour", 0)
        if token_limit > 0 and quota.usage.tokens_consumed > token_limit:
            violations.append(("tokens", quota.usage.tokens_consumed, token_limit))

        # Process violations
        for resource_type, current, limit in violations:
            await self._handle_violation(agent_id, resource_type, current, limit)

    async def _handle_violation(
        self,
        agent_id: str,
        resource_type: str,
        current: float,
        limit: float
    ) -> None:
        """
        Handle resource quota violation.

        Args:
            agent_id: Agent identifier
            resource_type: Type of resource (cpu, memory, tokens)
            current: Current usage
            limit: Limit value
        """
        # Get enforcement mode
        if resource_type == "cpu":
            enforcement = self.cpu_enforcement
        elif resource_type == "memory":
            enforcement = self.memory_enforcement
        elif resource_type == "tokens":
            enforcement = self.token_enforcement
        else:
            enforcement = EnforcementMode.WARN_ONLY

        # Check if already warned
        warned_set = self._warned.get(agent_id, set())

        if enforcement == EnforcementMode.WARN_ONLY:
            if resource_type not in warned_set:
                logger.warning(
                    f"Agent {agent_id} {resource_type} quota exceeded: "
                    f"{current:.2f} > {limit:.2f}"
                )
                warned_set.add(resource_type)

        elif enforcement == EnforcementMode.SOFT_THEN_HARD:
            if resource_type not in warned_set:
                # First violation: warn
                logger.warning(
                    f"Agent {agent_id} {resource_type} quota exceeded (warning): "
                    f"{current:.2f} > {limit:.2f}"
                )
                warned_set.add(resource_type)
            else:
                # Second violation: enforce
                logger.error(
                    f"Agent {agent_id} {resource_type} quota exceeded (enforcing): "
                    f"{current:.2f} > {limit:.2f}"
                )
                await self._take_enforcement_action(agent_id, resource_type)

        elif enforcement == EnforcementMode.HARD:
            # Immediate enforcement
            logger.error(
                f"Agent {agent_id} {resource_type} quota exceeded (hard enforcement): "
                f"{current:.2f} > {limit:.2f}"
            )
            await self._take_enforcement_action(agent_id, resource_type)

        self._warned[agent_id] = warned_set

    async def _take_enforcement_action(
        self,
        agent_id: str,
        resource_type: str
    ) -> None:
        """
        Take enforcement action for quota violation.

        Args:
            agent_id: Agent identifier
            resource_type: Type of resource
        """
        # Determine action based on resource type
        if resource_type == "tokens":
            action = self.token_budget_action
        else:
            # For CPU/memory, always suspend or terminate
            action = QuotaAction.SUSPEND

        logger.info(
            f"Taking enforcement action for agent {agent_id}: {action.value}"
        )

        # TODO: Integrate with LifecycleManager to actually suspend/terminate
        # For now, just log the action
        if action == QuotaAction.WARN:
            logger.warning(f"Agent {agent_id} quota exceeded (warn)")
        elif action == QuotaAction.THROTTLE:
            logger.warning(f"Agent {agent_id} quota exceeded (throttle)")
        elif action == QuotaAction.SUSPEND:
            logger.warning(f"Agent {agent_id} should be suspended (stub)")
        elif action == QuotaAction.TERMINATE:
            logger.warning(f"Agent {agent_id} should be terminated (stub)")

    async def get_usage(self, agent_id: str) -> ResourceUsage:
        """
        Get current resource usage for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            ResourceUsage

        Raises:
            ResourceError: If usage not found
        """
        usage = self._usage.get(agent_id)
        if not usage:
            raise ResourceError(
                code="E2070",
                message=f"Usage not found for agent {agent_id}"
            )
        return usage

    async def reset_quota(self, agent_id: str) -> None:
        """
        Reset quota usage for an agent.

        Args:
            agent_id: Agent identifier
        """
        quota = self._quotas.get(agent_id)
        if quota:
            quota.usage = QuotaUsage()
            quota.reset_at = datetime.now(timezone.utc) + timedelta(hours=1)
            logger.info(f"Reset quota for agent {agent_id}")

        # Clear warnings
        if agent_id in self._warned:
            self._warned[agent_id].clear()

    async def cleanup_quota(self, agent_id: str) -> None:
        """
        Remove quota and usage tracking for an agent.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._quotas:
            del self._quotas[agent_id]
        if agent_id in self._usage:
            del self._usage[agent_id]
        if agent_id in self._warned:
            del self._warned[agent_id]

        logger.info(f"Cleaned up quota for agent {agent_id}")

    async def _usage_reporting_loop(self) -> None:
        """Background task to periodically report usage statistics"""
        logger.info("Starting usage reporting loop")

        while True:
            try:
                await asyncio.sleep(self.usage_report_interval)

                # Report usage for all active agents
                for agent_id, usage in self._usage.items():
                    logger.debug(
                        f"Agent {agent_id} usage: "
                        f"cpu={usage.cpu_seconds:.2f}s, "
                        f"memory={usage.memory_peak_mb:.2f}MB, "
                        f"tokens={usage.tokens_consumed}"
                    )

            except asyncio.CancelledError:
                logger.info("Usage reporting loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in usage reporting loop: {e}")

    @staticmethod
    def _parse_cpu_limit(cpu_str: str) -> float:
        """Parse CPU limit string to float (cores)"""
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000
        return float(cpu_str)

    @staticmethod
    def _parse_memory_to_mb(memory_str: str) -> float:
        """Parse Kubernetes memory string to MB"""
        if memory_str.endswith("Gi"):
            return float(memory_str[:-2]) * 1024
        elif memory_str.endswith("Mi"):
            return float(memory_str[:-2])
        elif memory_str.endswith("G"):
            return float(memory_str[:-1]) * 1000
        elif memory_str.endswith("M"):
            return float(memory_str[:-1])
        return 0.0

    async def cleanup(self) -> None:
        """Cleanup resource manager"""
        logger.info("Cleaning up ResourceManager")

        # Cancel background tasks
        if self._report_task:
            self._report_task.cancel()
            try:
                await self._report_task
            except asyncio.CancelledError:
                pass

        self._quotas.clear()
        self._usage.clear()
        self._warned.clear()

        logger.info("ResourceManager cleanup complete")
