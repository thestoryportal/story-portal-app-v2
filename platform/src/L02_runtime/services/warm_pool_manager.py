"""
Warm Pool Manager

Manages pre-warmed agent instances for fast allocation.
Maintains a pool of ready-to-use agent instances.

Based on Section 3.3.10 warm_pool configuration
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..models import AgentConfig, AgentState, SpawnResult, RuntimeClass, TrustLevel, ResourceLimits
from ..models.fleet_models import WarmInstance


logger = logging.getLogger(__name__)


class WarmPoolError(Exception):
    """Warm pool management error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class WarmPoolManager:
    """
    Manages warm instance pool for fast agent allocation.

    Responsibilities:
    - Maintain pool of pre-warmed instances
    - Allocate instances from pool
    - Refresh stale instances
    - Monitor pool health
    - Replenish pool as instances are allocated
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize WarmPoolManager.

        Args:
            config: Configuration dict with:
                - enabled: Enable warm pool
                - size: Target pool size
                - runtime_class: Runtime class for warm instances
                - refresh_interval_seconds: Instance refresh interval
                - max_instance_age_seconds: Maximum instance age
        """
        self.config = config or {}

        # Configuration
        self.enabled = self.config.get("enabled", True)
        self.pool_size = self.config.get("size", 5)
        self.runtime_class = RuntimeClass(
            self.config.get("runtime_class", "gvisor")
        )
        self.refresh_interval = self.config.get("refresh_interval_seconds", 3600)
        self.max_instance_age = self.config.get("max_instance_age_seconds", 7200)

        # Warm pool: instance_id -> WarmInstance
        self._pool: Dict[str, WarmInstance] = {}

        # Allocated instances (removed from pool)
        self._allocated: Dict[str, WarmInstance] = {}

        # Dependencies (to be injected)
        self._lifecycle_manager = None
        self._sandbox_manager = None

        # Background tasks
        self._refresh_task: Optional[asyncio.Task] = None
        self._replenish_task: Optional[asyncio.Task] = None

        logger.info(
            f"WarmPoolManager initialized: enabled={self.enabled}, "
            f"size={self.pool_size}, runtime_class={self.runtime_class.value}"
        )

    async def initialize(
        self,
        lifecycle_manager=None,
        sandbox_manager=None
    ) -> None:
        """
        Initialize warm pool manager.

        Args:
            lifecycle_manager: LifecycleManager instance
            sandbox_manager: SandboxManager instance
        """
        self._lifecycle_manager = lifecycle_manager
        self._sandbox_manager = sandbox_manager

        if self.enabled:
            # Fill initial pool
            await self._fill_pool()

            # Start background tasks
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            self._replenish_task = asyncio.create_task(self._replenish_loop())

        logger.info("WarmPoolManager initialization complete")

    async def _fill_pool(self) -> None:
        """Fill pool to target size"""
        current_size = len(self._pool)
        needed = self.pool_size - current_size

        if needed <= 0:
            return

        logger.info(f"Filling warm pool: {current_size} -> {self.pool_size} (+{needed})")

        for i in range(needed):
            try:
                instance = await self._create_warm_instance()
                self._pool[instance.agent_id] = instance
            except Exception as e:
                logger.error(f"Failed to create warm instance: {e}")

        logger.info(f"Warm pool filled: {len(self._pool)} instances")

    async def _create_warm_instance(self) -> WarmInstance:
        """
        Create a new warm instance.

        Returns:
            WarmInstance
        """
        if not self._lifecycle_manager:
            raise WarmPoolError(
                code="E2092",
                message="Lifecycle manager not available"
            )

        # Create agent config for warm instance
        agent_config = AgentConfig(
            agent_id=f"warm-{datetime.utcnow().timestamp()}",
            trust_level=TrustLevel.STANDARD,
            resource_limits=ResourceLimits(),
            tools=[],
            environment={"WARM_POOL": "true"},
        )

        # Spawn instance
        result = await self._lifecycle_manager.spawn(agent_config)

        # Create warm instance record
        warm_instance = WarmInstance(
            agent_id=result.agent_id,
            session_id=result.session_id,
            runtime_class=self.runtime_class.value,
            created_at=datetime.utcnow(),
            allocated=False,
        )

        logger.debug(f"Created warm instance: {warm_instance.agent_id}")

        return warm_instance

    async def allocate_instance(
        self,
        config: Optional[AgentConfig] = None
    ) -> Optional[WarmInstance]:
        """
        Allocate an instance from the warm pool.

        Args:
            config: Optional agent configuration to apply

        Returns:
            WarmInstance or None if pool is empty

        Raises:
            WarmPoolError: If allocation fails
        """
        if not self.enabled:
            logger.debug("Warm pool is disabled")
            return None

        if not self._pool:
            logger.warning("Warm pool is empty")
            raise WarmPoolError(
                code="E2092",
                message="Warm pool exhausted"
            )

        # Get oldest instance from pool
        instance = min(self._pool.values(), key=lambda x: x.created_at)

        # Remove from pool
        del self._pool[instance.agent_id]

        # Mark as allocated
        instance.allocated = True
        instance.allocated_at = datetime.utcnow()
        self._allocated[instance.agent_id] = instance

        logger.info(
            f"Allocated warm instance: {instance.agent_id} "
            f"(pool size: {len(self._pool)})"
        )

        # TODO: Apply configuration to allocated instance if provided

        return instance

    async def return_instance(self, agent_id: str) -> None:
        """
        Return an instance to the pool.

        Args:
            agent_id: Agent identifier
        """
        if agent_id not in self._allocated:
            logger.warning(f"Instance {agent_id} not in allocated set")
            return

        instance = self._allocated[agent_id]

        # Check if instance is too old
        age = (datetime.utcnow() - instance.created_at).total_seconds()
        if age > self.max_instance_age:
            logger.info(f"Instance {agent_id} too old ({age:.0f}s), terminating")
            await self._terminate_instance(agent_id)
            return

        # Reset instance state
        instance.allocated = False
        instance.allocated_at = None

        # Return to pool
        del self._allocated[agent_id]
        self._pool[agent_id] = instance

        logger.info(
            f"Returned instance to pool: {agent_id} "
            f"(pool size: {len(self._pool)})"
        )

    async def _terminate_instance(self, agent_id: str) -> None:
        """Terminate an instance"""
        if self._lifecycle_manager:
            try:
                await self._lifecycle_manager.terminate(
                    agent_id,
                    reason="warm_pool_refresh"
                )
            except Exception as e:
                logger.error(f"Failed to terminate instance {agent_id}: {e}")

        # Remove from allocated set
        if agent_id in self._allocated:
            del self._allocated[agent_id]

    async def _refresh_loop(self) -> None:
        """Background task to refresh stale instances"""
        logger.info("Starting warm pool refresh loop")

        while True:
            try:
                await asyncio.sleep(self.refresh_interval)

                logger.debug("Refreshing warm pool instances")

                # Check for stale instances
                now = datetime.utcnow()
                stale_instances = []

                for agent_id, instance in self._pool.items():
                    age = (now - instance.created_at).total_seconds()
                    if age > self.max_instance_age:
                        stale_instances.append(agent_id)

                # Remove stale instances
                for agent_id in stale_instances:
                    logger.info(f"Removing stale instance: {agent_id}")
                    await self._terminate_instance(agent_id)
                    if agent_id in self._pool:
                        del self._pool[agent_id]

                logger.info(f"Refreshed pool: removed {len(stale_instances)} stale instances")

            except asyncio.CancelledError:
                logger.info("Refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")

    async def _replenish_loop(self) -> None:
        """Background task to replenish pool"""
        logger.info("Starting warm pool replenish loop")

        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Replenish pool if below target size
                current_size = len(self._pool)
                if current_size < self.pool_size:
                    logger.debug(f"Replenishing pool: {current_size}/{self.pool_size}")
                    await self._fill_pool()

            except asyncio.CancelledError:
                logger.info("Replenish loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in replenish loop: {e}")

    async def get_pool_status(self) -> Dict[str, Any]:
        """
        Get warm pool status.

        Returns:
            Pool status information
        """
        return {
            "enabled": self.enabled,
            "target_size": self.pool_size,
            "current_size": len(self._pool),
            "allocated_count": len(self._allocated),
            "runtime_class": self.runtime_class.value,
            "instances": [
                {
                    "agent_id": inst.agent_id,
                    "age_seconds": (datetime.utcnow() - inst.created_at).total_seconds(),
                    "allocated": inst.allocated,
                }
                for inst in list(self._pool.values())[:10]  # Limit to 10 for display
            ],
        }

    async def cleanup(self) -> None:
        """Cleanup warm pool manager"""
        logger.info("Cleaning up WarmPoolManager")

        # Cancel background tasks
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self._replenish_task:
            self._replenish_task.cancel()
            try:
                await self._replenish_task
            except asyncio.CancelledError:
                pass

        # Terminate all instances
        if self._lifecycle_manager:
            all_instances = list(self._pool.keys()) + list(self._allocated.keys())
            for agent_id in all_instances:
                try:
                    await self._lifecycle_manager.terminate(
                        agent_id,
                        reason="cleanup",
                        force=True
                    )
                except Exception as e:
                    logger.error(f"Failed to terminate {agent_id}: {e}")

        self._pool.clear()
        self._allocated.clear()

        logger.info("WarmPoolManager cleanup complete")
