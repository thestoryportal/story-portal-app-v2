"""
Fleet Manager

Manages horizontal scaling, warm pools, and graceful drain operations.
Implements local process pool for development, with stubs for K8s HPA.

Based on Section 3.3.10 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from ..models import AgentConfig, AgentState, SpawnResult
from ..models.fleet_models import ScalingMetrics, WarmInstance


logger = logging.getLogger(__name__)


class FleetError(Exception):
    """Fleet management error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class ScalingDecision:
    """Scaling decision result"""
    action: str  # scale_up, scale_down, no_action
    target_replicas: int
    current_replicas: int
    reason: str


class FleetManager:
    """
    Manages agent fleet scaling and warm pool operations.

    Responsibilities:
    - Monitor resource utilization
    - Make scaling decisions (scale up/down)
    - Manage warm instance pool
    - Coordinate graceful drain operations
    - Track scaling metrics
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FleetManager.

        Args:
            config: Configuration dict with:
                - min_replicas: Minimum agent instances
                - max_replicas: Maximum agent instances
                - target_cpu_utilization: Target CPU percentage
                - scale_up_stabilization_seconds: Scale up delay
                - scale_down_stabilization_seconds: Scale down delay
                - warm_pool: Warm pool configuration
                - graceful_drain: Drain configuration
        """
        self.config = config or {}

        # Scaling configuration
        self.min_replicas = self.config.get("min_replicas", 1)
        self.max_replicas = self.config.get("max_replicas", 100)
        self.target_cpu_utilization = self.config.get("target_cpu_utilization", 70)
        self.scale_up_stabilization = self.config.get(
            "scale_up_stabilization_seconds", 60
        )
        self.scale_down_stabilization = self.config.get(
            "scale_down_stabilization_seconds", 300
        )

        # Warm pool configuration
        warm_pool_config = self.config.get("warm_pool", {})
        self.warm_pool_enabled = warm_pool_config.get("enabled", True)
        self.warm_pool_size = warm_pool_config.get("size", 5)
        self.warm_pool_refresh_interval = warm_pool_config.get(
            "refresh_interval_seconds", 3600
        )

        # Graceful drain configuration
        drain_config = self.config.get("graceful_drain", {})
        self.drain_timeout = drain_config.get("timeout_seconds", 30)
        self.checkpoint_before_drain = drain_config.get(
            "checkpoint_before_drain", True
        )

        # Fleet state
        self._current_replicas = 0
        self._active_instances: Dict[str, Dict[str, Any]] = {}
        self._scaling_history: List[ScalingDecision] = []
        self._last_scale_action_time: Optional[datetime] = None

        # Dependencies (to be injected)
        self._lifecycle_manager = None
        self._state_manager = None

        logger.info(
            f"FleetManager initialized: "
            f"min={self.min_replicas}, max={self.max_replicas}, "
            f"target_cpu={self.target_cpu_utilization}%"
        )

    async def initialize(
        self,
        lifecycle_manager=None,
        state_manager=None
    ) -> None:
        """
        Initialize fleet manager.

        Args:
            lifecycle_manager: LifecycleManager instance
            state_manager: StateManager instance
        """
        self._lifecycle_manager = lifecycle_manager
        self._state_manager = state_manager

        logger.info("FleetManager initialization complete")

    async def evaluate_scaling(
        self,
        metrics: ScalingMetrics
    ) -> ScalingDecision:
        """
        Evaluate whether scaling is needed based on metrics.

        Args:
            metrics: Current fleet metrics

        Returns:
            ScalingDecision
        """
        current_replicas = metrics.current_replicas
        avg_cpu = metrics.avg_cpu_utilization
        avg_memory = metrics.avg_memory_utilization

        logger.debug(
            f"Evaluating scaling: replicas={current_replicas}, "
            f"cpu={avg_cpu:.1f}%, memory={avg_memory:.1f}%"
        )

        # Calculate desired replicas based on CPU utilization
        if avg_cpu > 0:
            desired_replicas = int(
                current_replicas * (avg_cpu / self.target_cpu_utilization)
            )
        else:
            desired_replicas = current_replicas

        # Apply min/max constraints
        desired_replicas = max(self.min_replicas, desired_replicas)
        desired_replicas = min(self.max_replicas, desired_replicas)

        # Determine action
        if desired_replicas > current_replicas:
            action = "scale_up"
            reason = f"CPU utilization {avg_cpu:.1f}% > target {self.target_cpu_utilization}%"
        elif desired_replicas < current_replicas:
            action = "scale_down"
            reason = f"CPU utilization {avg_cpu:.1f}% < target {self.target_cpu_utilization}%"
        else:
            action = "no_action"
            reason = "Replica count is optimal"

        # Check stabilization period
        if action != "no_action" and self._last_scale_action_time:
            stabilization_period = (
                self.scale_up_stabilization if action == "scale_up"
                else self.scale_down_stabilization
            )
            time_since_last_scale = (
                datetime.now(timezone.utc) - self._last_scale_action_time
            ).total_seconds()

            if time_since_last_scale < stabilization_period:
                action = "no_action"
                reason = f"Within stabilization period ({time_since_last_scale:.0f}s < {stabilization_period}s)"

        decision = ScalingDecision(
            action=action,
            target_replicas=desired_replicas,
            current_replicas=current_replicas,
            reason=reason,
        )

        logger.info(
            f"Scaling decision: {action} (current={current_replicas}, "
            f"target={desired_replicas}, reason={reason})"
        )

        return decision

    async def scale_up(
        self,
        target_replicas: int,
        config_template: AgentConfig
    ) -> List[SpawnResult]:
        """
        Scale up fleet to target replica count.

        Args:
            target_replicas: Target number of replicas
            config_template: Agent configuration template

        Returns:
            List of spawn results for new instances

        Raises:
            FleetError: If scale up fails
        """
        current = self._current_replicas
        count = target_replicas - current

        if count <= 0:
            return []

        logger.info(f"Scaling up: {current} -> {target_replicas} (+{count})")

        try:
            # Check lifecycle manager
            if not self._lifecycle_manager:
                raise FleetError(
                    code="E2090",
                    message="Lifecycle manager not available"
                )

            # Spawn new instances
            results = []
            for i in range(count):
                # Create agent config
                agent_config = AgentConfig(
                    agent_id=f"agent-{datetime.now(timezone.utc).timestamp()}-{i}",
                    trust_level=config_template.trust_level,
                    resource_limits=config_template.resource_limits,
                    tools=config_template.tools,
                    environment=config_template.environment.copy(),
                )

                # Spawn agent
                result = await self._lifecycle_manager.spawn(agent_config)
                results.append(result)

                # Track instance
                self._active_instances[result.agent_id] = {
                    "agent_id": result.agent_id,
                    "spawned_at": datetime.now(timezone.utc),
                    "state": result.state,
                }

            self._current_replicas = target_replicas
            self._last_scale_action_time = datetime.now(timezone.utc)

            logger.info(f"Scale up complete: spawned {count} instances")

            return results

        except Exception as e:
            logger.error(f"Scale up failed: {e}")
            raise FleetError(
                code="E2090",
                message=f"Scale up failed: {str(e)}"
            )

    async def scale_down(
        self,
        target_replicas: int
    ) -> List[str]:
        """
        Scale down fleet to target replica count.

        Args:
            target_replicas: Target number of replicas

        Returns:
            List of terminated agent IDs

        Raises:
            FleetError: If scale down fails
        """
        current = self._current_replicas
        count = current - target_replicas

        if count <= 0:
            return []

        logger.info(f"Scaling down: {current} -> {target_replicas} (-{count})")

        try:
            # Check lifecycle manager
            if not self._lifecycle_manager:
                raise FleetError(
                    code="E2091",
                    message="Lifecycle manager not available"
                )

            # Select instances to terminate (oldest first)
            instances_sorted = sorted(
                self._active_instances.items(),
                key=lambda x: x[1].get("spawned_at", datetime.now(timezone.utc))
            )

            terminated_ids = []
            for agent_id, instance in instances_sorted[:count]:
                # Graceful drain
                await self._graceful_drain(agent_id)

                # Terminate
                await self._lifecycle_manager.terminate(
                    agent_id,
                    reason="scale_down"
                )

                # Remove from tracking
                del self._active_instances[agent_id]
                terminated_ids.append(agent_id)

            self._current_replicas = target_replicas
            self._last_scale_action_time = datetime.now(timezone.utc)

            logger.info(f"Scale down complete: terminated {count} instances")

            return terminated_ids

        except Exception as e:
            logger.error(f"Scale down failed: {e}")
            raise FleetError(
                code="E2091",
                message=f"Scale down failed: {str(e)}"
            )

    async def _graceful_drain(self, agent_id: str) -> None:
        """
        Perform graceful drain of an agent instance.

        Args:
            agent_id: Agent to drain
        """
        logger.info(f"Gracefully draining agent {agent_id}")

        try:
            # Checkpoint before drain if enabled
            if self.checkpoint_before_drain and self._state_manager:
                instance = self._active_instances.get(agent_id)
                if instance:
                    await self._state_manager.create_checkpoint(
                        agent_id=agent_id,
                        session_id=instance.get("session_id", ""),
                        state=AgentState.SUSPENDED,
                        context={"drain_reason": "scale_down"},
                        metadata={"drain_initiated_at": datetime.now(timezone.utc).isoformat()},
                    )

            # Wait for drain timeout (TODO: implement actual drain logic)
            await asyncio.sleep(1)  # Stub drain wait

            logger.info(f"Agent {agent_id} drained successfully")

        except asyncio.TimeoutError:
            logger.warning(f"Drain timeout for agent {agent_id}")
            raise FleetError(
                code="E2093",
                message=f"Graceful drain timeout ({self.drain_timeout}s)"
            )
        except Exception as e:
            logger.warning(f"Drain failed for agent {agent_id}: {e}")

    async def get_fleet_metrics(self) -> ScalingMetrics:
        """
        Get current fleet metrics.

        Returns:
            ScalingMetrics
        """
        # TODO: Collect actual metrics from instances
        # For now, return stub metrics
        return ScalingMetrics(
            current_replicas=self._current_replicas,
            desired_replicas=self._current_replicas,
            avg_cpu_utilization=50.0,
            avg_memory_utilization=60.0,
            pending_requests=0,
        )

    async def get_scaling_history(
        self,
        limit: int = 10
    ) -> List[ScalingDecision]:
        """
        Get recent scaling history.

        Args:
            limit: Maximum number of entries

        Returns:
            List of scaling decisions
        """
        return self._scaling_history[-limit:]

    async def cleanup(self) -> None:
        """Cleanup fleet manager"""
        logger.info("Cleaning up FleetManager")

        # Terminate all active instances
        if self._lifecycle_manager:
            for agent_id in list(self._active_instances.keys()):
                try:
                    await self._lifecycle_manager.terminate(
                        agent_id,
                        reason="cleanup",
                        force=True
                    )
                except Exception as e:
                    logger.error(f"Failed to terminate {agent_id}: {e}")

        self._active_instances.clear()
        self._scaling_history.clear()

        logger.info("FleetManager cleanup complete")
