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
from enum import Enum

from ..models import AgentConfig, AgentState, SpawnResult
from ..models.fleet_models import ScalingMetrics, WarmInstance


logger = logging.getLogger(__name__)


class DrainState(Enum):
    """Agent drain state"""
    ACTIVE = "active"
    DRAINING = "draining"
    DRAINED = "drained"


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

        # Warm pool
        self._warm_pool: List[WarmInstance] = []
        self._warm_pool_lock = asyncio.Lock()

        # Autoscaling state
        self._autoscaling_enabled = False
        self._autoscaling_task: Optional[asyncio.Task] = None
        self._autoscaling_interval = self.config.get("autoscaling_interval_seconds", 30)

        # Dependencies (to be injected)
        self._lifecycle_manager = None
        self._state_manager = None
        self._resource_manager = None

        # Metrics
        self._scale_up_count = 0
        self._scale_down_count = 0
        self._warm_pool_hits = 0
        self._warm_pool_misses = 0

        # Drain state tracking: agent_id -> DrainState
        self._drain_states: Dict[str, DrainState] = {}

        # In-flight tasks tracking: agent_id -> set of task_ids
        self._in_flight_tasks: Dict[str, set] = {}

        logger.info(
            f"FleetManager initialized: "
            f"min={self.min_replicas}, max={self.max_replicas}, "
            f"target_cpu={self.target_cpu_utilization}%, "
            f"warm_pool={'enabled' if self.warm_pool_enabled else 'disabled'}"
        )

    async def initialize(
        self,
        lifecycle_manager=None,
        state_manager=None,
        resource_manager=None
    ) -> None:
        """
        Initialize fleet manager.

        Args:
            lifecycle_manager: LifecycleManager instance
            state_manager: StateManager instance
            resource_manager: ResourceManager instance for metrics
        """
        self._lifecycle_manager = lifecycle_manager
        self._state_manager = state_manager
        self._resource_manager = resource_manager

        # Pre-warm the pool if enabled
        if self.warm_pool_enabled:
            asyncio.create_task(self._maintain_warm_pool())

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

        Waits for in-flight tasks to complete before draining.

        Args:
            agent_id: Agent to drain
        """
        logger.info(f"Gracefully draining agent {agent_id}")

        try:
            # Mark as draining
            self._drain_states[agent_id] = DrainState.DRAINING

            # 1. Wait for in-flight tasks to complete (with timeout)
            start_time = datetime.now(timezone.utc)
            while True:
                in_flight = await self._get_in_flight_tasks(agent_id)
                if not in_flight:
                    break

                # Check timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= self.drain_timeout:
                    logger.warning(
                        f"Drain timeout for agent {agent_id}: "
                        f"{len(in_flight)} tasks still in-flight"
                    )
                    break

                logger.debug(
                    f"Agent {agent_id} has {len(in_flight)} in-flight tasks, "
                    f"waiting... ({elapsed:.1f}s elapsed)"
                )
                await asyncio.sleep(1)

            # 2. Checkpoint state before drain if enabled
            if self.checkpoint_before_drain and self._state_manager:
                instance = self._active_instances.get(agent_id)
                if instance:
                    await self._state_manager.create_checkpoint(
                        agent_id=agent_id,
                        session_id=instance.get("session_id", ""),
                        state=AgentState.SUSPENDED,
                        context={
                            "drain_reason": "scale_down",
                            "in_flight_at_drain": list(self._in_flight_tasks.get(agent_id, set())),
                        },
                        metadata={
                            "drain_initiated_at": start_time.isoformat(),
                            "drain_completed_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            # 3. Mark as drained
            self._drain_states[agent_id] = DrainState.DRAINED

            # 4. Cleanup tracking
            if agent_id in self._in_flight_tasks:
                del self._in_flight_tasks[agent_id]

            logger.info(f"Agent {agent_id} drained successfully")

        except asyncio.TimeoutError:
            logger.warning(f"Drain timeout for agent {agent_id}")
            self._drain_states[agent_id] = DrainState.DRAINED  # Mark drained anyway
            raise FleetError(
                code="E2093",
                message=f"Graceful drain timeout ({self.drain_timeout}s)"
            )
        except Exception as e:
            logger.warning(f"Drain failed for agent {agent_id}: {e}")
            self._drain_states[agent_id] = DrainState.DRAINED  # Mark drained to allow termination

    async def _get_in_flight_tasks(self, agent_id: str) -> set:
        """
        Get in-flight tasks for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Set of in-flight task IDs
        """
        return self._in_flight_tasks.get(agent_id, set())

    def register_task(self, agent_id: str, task_id: str) -> None:
        """
        Register an in-flight task for an agent.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
        """
        if agent_id not in self._in_flight_tasks:
            self._in_flight_tasks[agent_id] = set()
        self._in_flight_tasks[agent_id].add(task_id)
        logger.debug(f"Registered task {task_id} for agent {agent_id}")

    def complete_task(self, agent_id: str, task_id: str) -> None:
        """
        Mark a task as complete for an agent.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
        """
        if agent_id in self._in_flight_tasks:
            self._in_flight_tasks[agent_id].discard(task_id)
            logger.debug(f"Completed task {task_id} for agent {agent_id}")

    def get_drain_state(self, agent_id: str) -> DrainState:
        """
        Get drain state for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            DrainState
        """
        return self._drain_states.get(agent_id, DrainState.ACTIVE)

    def is_draining(self, agent_id: str) -> bool:
        """
        Check if an agent is currently draining.

        Args:
            agent_id: Agent identifier

        Returns:
            True if draining
        """
        state = self._drain_states.get(agent_id, DrainState.ACTIVE)
        return state == DrainState.DRAINING

    async def get_fleet_metrics(self) -> ScalingMetrics:
        """
        Get current fleet metrics.

        Collects real metrics from resource manager if available,
        otherwise returns estimated values.

        Returns:
            ScalingMetrics
        """
        avg_cpu = 0.0
        avg_memory = 0.0
        pending_requests = 0

        if self._resource_manager and self._active_instances:
            # Collect real metrics from resource manager
            cpu_values = []
            memory_values = []

            for agent_id in self._active_instances.keys():
                try:
                    metrics = await self._resource_manager.get_agent_metrics(agent_id)
                    if metrics:
                        cpu_values.append(metrics.get("cpu_percent", 0.0))
                        memory_values.append(metrics.get("memory_percent", 0.0))
                except Exception as e:
                    logger.warning(f"Failed to get metrics for {agent_id}: {e}")

            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
            if memory_values:
                avg_memory = sum(memory_values) / len(memory_values)

        elif self._active_instances:
            # Estimate based on instance count (fallback)
            # Higher instance count typically means higher load
            load_factor = min(1.0, self._current_replicas / max(1, self.max_replicas))
            avg_cpu = 30.0 + (load_factor * 50.0)  # 30-80%
            avg_memory = 40.0 + (load_factor * 40.0)  # 40-80%

        return ScalingMetrics(
            current_replicas=self._current_replicas,
            desired_replicas=self._current_replicas,
            avg_cpu_utilization=avg_cpu,
            avg_memory_utilization=avg_memory,
            pending_requests=pending_requests,
        )

    # ==================== Warm Pool Methods ====================

    async def _maintain_warm_pool(self) -> None:
        """
        Maintain warm pool at desired size.

        Runs periodically to ensure warm instances are available.
        """
        while self.warm_pool_enabled:
            try:
                async with self._warm_pool_lock:
                    # Remove stale instances
                    await self._cleanup_stale_warm_instances()

                    # Add instances if below target
                    current_size = len(self._warm_pool)
                    needed = self.warm_pool_size - current_size

                    if needed > 0:
                        logger.info(f"Warm pool: adding {needed} instances")
                        for _ in range(needed):
                            await self._create_warm_instance()

            except Exception as e:
                logger.error(f"Warm pool maintenance failed: {e}")

            # Wait for next refresh cycle
            await asyncio.sleep(self.warm_pool_refresh_interval)

    async def _create_warm_instance(self) -> Optional[WarmInstance]:
        """
        Create a warm (pre-initialized) instance.

        Returns:
            WarmInstance or None if creation failed
        """
        if not self._lifecycle_manager:
            return None

        try:
            # Create minimal config for warm instance
            warm_config = AgentConfig(
                agent_id=f"warm-{datetime.now(timezone.utc).timestamp()}",
                trust_level="restricted",
                resource_limits={"cpu_limit": 0.5, "memory_limit_mb": 512},
                tools=[],
                environment={"WARM_INSTANCE": "true"},
            )

            # Spawn in suspended state
            result = await self._lifecycle_manager.spawn(
                warm_config,
                start_suspended=True
            )

            warm_instance = WarmInstance(
                agent_id=result.agent_id,
                created_at=datetime.now(timezone.utc),
                state=AgentState.SUSPENDED,
            )

            self._warm_pool.append(warm_instance)
            logger.debug(f"Created warm instance: {result.agent_id}")

            return warm_instance

        except Exception as e:
            logger.warning(f"Failed to create warm instance: {e}")
            return None

    async def _cleanup_stale_warm_instances(self) -> int:
        """
        Remove stale warm instances.

        Returns:
            Number of instances cleaned up
        """
        max_age = self.warm_pool_refresh_interval * 2
        now = datetime.now(timezone.utc)
        cleaned = 0

        for instance in list(self._warm_pool):
            age = (now - instance.created_at).total_seconds()
            if age > max_age:
                # Terminate stale instance
                if self._lifecycle_manager:
                    try:
                        await self._lifecycle_manager.terminate(
                            instance.agent_id,
                            reason="warm_pool_refresh"
                        )
                    except Exception:
                        pass

                self._warm_pool.remove(instance)
                cleaned += 1

        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} stale warm instances")

        return cleaned

    async def acquire_from_warm_pool(
        self,
        config: AgentConfig
    ) -> Optional[SpawnResult]:
        """
        Acquire an instance from the warm pool.

        Args:
            config: Agent configuration to apply

        Returns:
            SpawnResult if warm instance acquired, None otherwise
        """
        async with self._warm_pool_lock:
            if not self._warm_pool:
                self._warm_pool_misses += 1
                return None

            # Get oldest warm instance
            warm_instance = self._warm_pool.pop(0)
            self._warm_pool_hits += 1

        try:
            # Configure and activate the warm instance
            if self._lifecycle_manager:
                await self._lifecycle_manager.reconfigure(
                    warm_instance.agent_id,
                    config
                )
                await self._lifecycle_manager.resume(warm_instance.agent_id)

            logger.info(f"Acquired warm instance: {warm_instance.agent_id}")

            return SpawnResult(
                agent_id=warm_instance.agent_id,
                state=AgentState.RUNNING,
                from_warm_pool=True
            )

        except Exception as e:
            logger.error(f"Failed to acquire warm instance: {e}")
            self._warm_pool_misses += 1
            return None

    def get_warm_pool_stats(self) -> Dict[str, Any]:
        """
        Get warm pool statistics.

        Returns:
            Warm pool stats dictionary
        """
        total_requests = self._warm_pool_hits + self._warm_pool_misses
        hit_rate = (
            self._warm_pool_hits / total_requests * 100
            if total_requests > 0 else 0.0
        )

        return {
            "enabled": self.warm_pool_enabled,
            "target_size": self.warm_pool_size,
            "current_size": len(self._warm_pool),
            "hits": self._warm_pool_hits,
            "misses": self._warm_pool_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "refresh_interval_seconds": self.warm_pool_refresh_interval,
        }

    # ==================== Autoscaling Methods ====================

    async def start_autoscaling(
        self,
        config_template: AgentConfig
    ) -> bool:
        """
        Start the autoscaling loop.

        Args:
            config_template: Template for new instances

        Returns:
            True if started, False if already running
        """
        if self._autoscaling_enabled:
            logger.warning("Autoscaling already enabled")
            return False

        self._autoscaling_enabled = True
        self._autoscaling_task = asyncio.create_task(
            self._autoscaling_loop(config_template)
        )

        logger.info("Autoscaling started")
        return True

    async def stop_autoscaling(self) -> bool:
        """
        Stop the autoscaling loop.

        Returns:
            True if stopped, False if not running
        """
        if not self._autoscaling_enabled:
            return False

        self._autoscaling_enabled = False

        if self._autoscaling_task:
            self._autoscaling_task.cancel()
            try:
                await self._autoscaling_task
            except asyncio.CancelledError:
                pass
            self._autoscaling_task = None

        logger.info("Autoscaling stopped")
        return True

    async def _autoscaling_loop(
        self,
        config_template: AgentConfig
    ) -> None:
        """
        Main autoscaling loop.

        Periodically evaluates metrics and scales the fleet.

        Args:
            config_template: Template for new instances
        """
        logger.info(
            f"Autoscaling loop started "
            f"(interval={self._autoscaling_interval}s)"
        )

        while self._autoscaling_enabled:
            try:
                # Collect metrics
                metrics = await self.get_fleet_metrics()

                # Evaluate scaling
                decision = await self.evaluate_scaling(metrics)

                # Record decision
                self._scaling_history.append(decision)
                if len(self._scaling_history) > 100:
                    self._scaling_history = self._scaling_history[-100:]

                # Execute scaling action
                if decision.action == "scale_up":
                    # Try warm pool first
                    warm_result = await self.acquire_from_warm_pool(config_template)
                    if warm_result:
                        self._active_instances[warm_result.agent_id] = {
                            "agent_id": warm_result.agent_id,
                            "spawned_at": datetime.now(timezone.utc),
                            "from_warm_pool": True,
                        }
                        self._current_replicas += 1
                        self._scale_up_count += 1
                    else:
                        await self.scale_up(decision.target_replicas, config_template)

                elif decision.action == "scale_down":
                    await self.scale_down(decision.target_replicas)

            except Exception as e:
                logger.error(f"Autoscaling loop error: {e}")

            # Wait for next interval
            await asyncio.sleep(self._autoscaling_interval)

    def get_autoscaling_status(self) -> Dict[str, Any]:
        """
        Get autoscaling status.

        Returns:
            Autoscaling status dictionary
        """
        return {
            "enabled": self._autoscaling_enabled,
            "interval_seconds": self._autoscaling_interval,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "target_cpu_percent": self.target_cpu_utilization,
            "current_replicas": self._current_replicas,
            "scale_up_count": self._scale_up_count,
            "scale_down_count": self._scale_down_count,
            "last_scale_action": (
                self._last_scale_action_time.isoformat()
                if self._last_scale_action_time else None
            ),
        }

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

        # Stop autoscaling
        await self.stop_autoscaling()

        # Clear warm pool
        self.warm_pool_enabled = False
        async with self._warm_pool_lock:
            for instance in self._warm_pool:
                if self._lifecycle_manager:
                    try:
                        await self._lifecycle_manager.terminate(
                            instance.agent_id,
                            reason="cleanup",
                            force=True
                        )
                    except Exception:
                        pass
            self._warm_pool.clear()

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

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get fleet manager health status.

        Returns:
            Health status dictionary
        """
        return {
            "healthy": self._lifecycle_manager is not None,
            "current_replicas": self._current_replicas,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "autoscaling": self.get_autoscaling_status(),
            "warm_pool": self.get_warm_pool_stats(),
            "active_instances": len(self._active_instances),
        }
