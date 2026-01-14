"""
Health Monitor

Monitors agent health via probes and collects agent-specific metrics.
Provides Kubernetes-compatible health endpoints and Prometheus metrics.

Based on Section 3.3.9 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..models import AgentState
from ..models.health_models import HealthStatus, ProbeResult


logger = logging.getLogger(__name__)


class ProbeType(Enum):
    """Health probe type"""
    LIVENESS = "liveness"
    READINESS = "readiness"


@dataclass
class MetricsSnapshot:
    """Metrics snapshot at a point in time"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    active_agents: int = 0


class HealthMonitor:
    """
    Monitors agent health and collects metrics.

    Responsibilities:
    - Execute liveness and readiness probes
    - Track agent health status
    - Collect and expose Prometheus metrics
    - Detect stuck agents
    - Monitor error rates and latency
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize HealthMonitor.

        Args:
            config: Configuration dict with:
                - liveness_probe: Liveness probe configuration
                - readiness_probe: Readiness probe configuration
                - metrics: Metrics collection configuration
                - stuck_agent_timeout_seconds: Timeout for stuck detection
        """
        self.config = config or {}

        # Liveness probe configuration
        liveness_config = self.config.get("liveness_probe", {})
        self.liveness_path = liveness_config.get("path", "/healthz")
        self.liveness_interval = liveness_config.get("interval_seconds", 10)
        self.liveness_timeout = liveness_config.get("timeout_seconds", 5)
        self.liveness_failure_threshold = liveness_config.get("failure_threshold", 3)

        # Readiness probe configuration
        readiness_config = self.config.get("readiness_probe", {})
        self.readiness_path = readiness_config.get("path", "/ready")
        self.readiness_interval = readiness_config.get("interval_seconds", 5)
        self.readiness_timeout = readiness_config.get("timeout_seconds", 3)
        self.readiness_failure_threshold = readiness_config.get("failure_threshold", 2)

        # Metrics configuration
        metrics_config = self.config.get("metrics", {})
        self.error_rate_window = metrics_config.get("error_rate_window_seconds", 300)
        self.latency_buckets = metrics_config.get(
            "latency_buckets",
            [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        # Stuck agent detection
        self.stuck_agent_timeout = self.config.get("stuck_agent_timeout_seconds", 600)

        # Health tracking: agent_id -> health status
        self._health_status: Dict[str, HealthStatus] = {}

        # Probe results: agent_id -> consecutive failures
        self._liveness_failures: Dict[str, int] = {}
        self._readiness_failures: Dict[str, int] = {}

        # Metrics
        self._metrics_history: List[MetricsSnapshot] = []
        self._request_latencies: List[float] = []

        # Dependencies (to be injected)
        self._agent_executor = None

        # Background tasks
        self._liveness_probe_task: Optional[asyncio.Task] = None
        self._readiness_probe_task: Optional[asyncio.Task] = None
        self._metrics_collection_task: Optional[asyncio.Task] = None

        logger.info(
            f"HealthMonitor initialized: "
            f"liveness_interval={self.liveness_interval}s, "
            f"readiness_interval={self.readiness_interval}s"
        )

    async def initialize(self, agent_executor=None) -> None:
        """
        Initialize health monitor.

        Args:
            agent_executor: AgentExecutor instance
        """
        self._agent_executor = agent_executor

        # Start background probe tasks
        self._liveness_probe_task = asyncio.create_task(self._liveness_probe_loop())
        self._readiness_probe_task = asyncio.create_task(self._readiness_probe_loop())
        self._metrics_collection_task = asyncio.create_task(
            self._metrics_collection_loop()
        )

        logger.info("HealthMonitor initialization complete")

    async def check_liveness(self, agent_id: str) -> ProbeResult:
        """
        Check agent liveness.

        Args:
            agent_id: Agent identifier

        Returns:
            ProbeResult
        """
        start_time = datetime.utcnow()

        try:
            # Check if agent is tracked
            if agent_id not in self._health_status:
                return ProbeResult(
                    probe_type=ProbeType.LIVENESS.value,
                    agent_id=agent_id,
                    success=False,
                    message="Agent not tracked",
                )

            status = self._health_status[agent_id]

            # Check if agent is alive (has recent activity)
            if status.last_heartbeat:
                time_since_heartbeat = (
                    datetime.utcnow() - status.last_heartbeat
                ).total_seconds()

                if time_since_heartbeat > self.stuck_agent_timeout:
                    return ProbeResult(
                        probe_type=ProbeType.LIVENESS.value,
                        agent_id=agent_id,
                        success=False,
                        message=f"Agent stuck (no heartbeat for {time_since_heartbeat:.0f}s)",
                        duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    )

            # Basic liveness check passed
            return ProbeResult(
                probe_type=ProbeType.LIVENESS.value,
                agent_id=agent_id,
                success=True,
                message="Agent is alive",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.LIVENESS.value,
                agent_id=agent_id,
                success=False,
                message=f"Liveness check failed: {str(e)}",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

    async def check_readiness(self, agent_id: str) -> ProbeResult:
        """
        Check agent readiness.

        Args:
            agent_id: Agent identifier

        Returns:
            ProbeResult
        """
        start_time = datetime.utcnow()

        try:
            # Check if agent is tracked
            if agent_id not in self._health_status:
                return ProbeResult(
                    probe_type=ProbeType.READINESS.value,
                    agent_id=agent_id,
                    success=False,
                    message="Agent not tracked",
                )

            status = self._health_status[agent_id]

            # Check if agent is in a ready state
            if status.state not in [AgentState.RUNNING]:
                return ProbeResult(
                    probe_type=ProbeType.READINESS.value,
                    agent_id=agent_id,
                    success=False,
                    message=f"Agent not ready (state: {status.state.value})",
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Check error rate
            if status.error_rate > 0.5:  # More than 50% errors
                return ProbeResult(
                    probe_type=ProbeType.READINESS.value,
                    agent_id=agent_id,
                    success=False,
                    message=f"High error rate ({status.error_rate:.2%})",
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Readiness check passed
            return ProbeResult(
                probe_type=ProbeType.READINESS.value,
                agent_id=agent_id,
                success=True,
                message="Agent is ready",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.READINESS.value,
                agent_id=agent_id,
                success=False,
                message=f"Readiness check failed: {str(e)}",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

    async def register_agent(
        self,
        agent_id: str,
        state: AgentState
    ) -> None:
        """
        Register agent for health monitoring.

        Args:
            agent_id: Agent identifier
            state: Initial agent state
        """
        self._health_status[agent_id] = HealthStatus(
            agent_id=agent_id,
            state=state,
            is_healthy=True,
            last_heartbeat=datetime.utcnow(),
            consecutive_failures=0,
            error_rate=0.0,
            avg_latency_ms=0.0,
        )

        self._liveness_failures[agent_id] = 0
        self._readiness_failures[agent_id] = 0

        logger.info(f"Registered agent for health monitoring: {agent_id}")

    async def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister agent from health monitoring.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._health_status:
            del self._health_status[agent_id]
        if agent_id in self._liveness_failures:
            del self._liveness_failures[agent_id]
        if agent_id in self._readiness_failures:
            del self._readiness_failures[agent_id]

        logger.info(f"Unregistered agent from health monitoring: {agent_id}")

    async def record_request(
        self,
        agent_id: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """
        Record request metrics.

        Args:
            agent_id: Agent identifier
            success: Whether request succeeded
            latency_ms: Request latency in milliseconds
        """
        if agent_id in self._health_status:
            status = self._health_status[agent_id]

            # Update request counts
            status.total_requests += 1
            if success:
                status.successful_requests += 1
            else:
                status.failed_requests += 1

            # Calculate error rate
            if status.total_requests > 0:
                status.error_rate = status.failed_requests / status.total_requests

            # Update average latency (exponential moving average)
            alpha = 0.2  # Smoothing factor
            status.avg_latency_ms = (
                alpha * latency_ms + (1 - alpha) * status.avg_latency_ms
            )

            # Track latency for histograms
            self._request_latencies.append(latency_ms)

            # Update heartbeat
            status.last_heartbeat = datetime.utcnow()

    async def get_health_status(self, agent_id: str) -> Optional[HealthStatus]:
        """
        Get health status for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            HealthStatus or None if not tracked
        """
        return self._health_status.get(agent_id)

    async def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """
        Get health status for all agents.

        Returns:
            Dict mapping agent_id to HealthStatus
        """
        return self._health_status.copy()

    async def get_metrics_snapshot(self) -> MetricsSnapshot:
        """
        Get current metrics snapshot.

        Returns:
            MetricsSnapshot
        """
        total_requests = sum(s.total_requests for s in self._health_status.values())
        successful_requests = sum(
            s.successful_requests for s in self._health_status.values()
        )
        failed_requests = sum(s.failed_requests for s in self._health_status.values())

        avg_latency = (
            sum(s.avg_latency_ms for s in self._health_status.values()) /
            len(self._health_status)
            if self._health_status else 0.0
        )

        error_rate = (
            failed_requests / total_requests if total_requests > 0 else 0.0
        )

        return MetricsSnapshot(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_latency_ms=avg_latency,
            error_rate=error_rate,
            active_agents=len(self._health_status),
        )

    async def _liveness_probe_loop(self) -> None:
        """Background task for liveness probes"""
        logger.info("Starting liveness probe loop")

        while True:
            try:
                await asyncio.sleep(self.liveness_interval)

                # Check liveness for all agents
                for agent_id in list(self._health_status.keys()):
                    result = await self.check_liveness(agent_id)

                    if not result.success:
                        self._liveness_failures[agent_id] = (
                            self._liveness_failures.get(agent_id, 0) + 1
                        )

                        if self._liveness_failures[agent_id] >= self.liveness_failure_threshold:
                            logger.error(
                                f"Agent {agent_id} failed liveness check "
                                f"{self._liveness_failures[agent_id]} times"
                            )
                            # Mark as unhealthy
                            if agent_id in self._health_status:
                                self._health_status[agent_id].is_healthy = False
                    else:
                        self._liveness_failures[agent_id] = 0

            except asyncio.CancelledError:
                logger.info("Liveness probe loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in liveness probe loop: {e}")

    async def _readiness_probe_loop(self) -> None:
        """Background task for readiness probes"""
        logger.info("Starting readiness probe loop")

        while True:
            try:
                await asyncio.sleep(self.readiness_interval)

                # Check readiness for all agents
                for agent_id in list(self._health_status.keys()):
                    result = await self.check_readiness(agent_id)

                    if not result.success:
                        self._readiness_failures[agent_id] = (
                            self._readiness_failures.get(agent_id, 0) + 1
                        )

                        if self._readiness_failures[agent_id] >= self.readiness_failure_threshold:
                            logger.warning(
                                f"Agent {agent_id} not ready "
                                f"({self._readiness_failures[agent_id]} checks)"
                            )
                    else:
                        self._readiness_failures[agent_id] = 0

            except asyncio.CancelledError:
                logger.info("Readiness probe loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in readiness probe loop: {e}")

    async def _metrics_collection_loop(self) -> None:
        """Background task for metrics collection"""
        logger.info("Starting metrics collection loop")

        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute

                snapshot = await self.get_metrics_snapshot()
                self._metrics_history.append(snapshot)

                # Keep only recent history (last hour)
                if len(self._metrics_history) > 60:
                    self._metrics_history = self._metrics_history[-60:]

                logger.debug(
                    f"Metrics snapshot: {snapshot.active_agents} agents, "
                    f"error_rate={snapshot.error_rate:.2%}, "
                    f"avg_latency={snapshot.avg_latency_ms:.2f}ms"
                )

            except asyncio.CancelledError:
                logger.info("Metrics collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

    async def cleanup(self) -> None:
        """Cleanup health monitor"""
        logger.info("Cleaning up HealthMonitor")

        # Cancel background tasks
        if self._liveness_probe_task:
            self._liveness_probe_task.cancel()
            try:
                await self._liveness_probe_task
            except asyncio.CancelledError:
                pass

        if self._readiness_probe_task:
            self._readiness_probe_task.cancel()
            try:
                await self._readiness_probe_task
            except asyncio.CancelledError:
                pass

        if self._metrics_collection_task:
            self._metrics_collection_task.cancel()
            try:
                await self._metrics_collection_task
            except asyncio.CancelledError:
                pass

        self._health_status.clear()
        self._liveness_failures.clear()
        self._readiness_failures.clear()
        self._metrics_history.clear()

        logger.info("HealthMonitor cleanup complete")
