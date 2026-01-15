"""
Health Monitoring Data Models

Models for agent health status and metrics.
Based on Section 5.1.5 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any


class LivenessState(Enum):
    """Agent liveness status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ReadinessState(Enum):
    """Agent readiness status"""
    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Collected health metrics"""
    error_rate: float = 0.0          # Errors per 5 minutes
    avg_latency_ms: float = 0.0      # Average response latency
    escalation_rate: float = 0.0     # Handoffs to human per hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_rate": self.error_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "escalation_rate": self.escalation_rate,
        }


@dataclass
class HealthStatus:
    """
    Agent health monitoring state.

    Tracks liveness and readiness for Kubernetes-style health checks.
    """
    agent_id: str
    state: Any  # AgentState - imported from agent_models to avoid circular import
    is_healthy: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    liveness: LivenessState = LivenessState.UNKNOWN
    readiness: ReadinessState = ReadinessState.UNKNOWN
    last_liveness_check: datetime = field(default_factory=datetime.utcnow)
    last_readiness_check: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    metrics: HealthMetrics = field(default_factory=HealthMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value if hasattr(self.state, 'value') else str(self.state),
            "is_healthy": self.is_healthy,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "liveness": self.liveness.value,
            "readiness": self.readiness.value,
            "last_liveness_check": self.last_liveness_check.isoformat(),
            "last_readiness_check": self.last_readiness_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "error_rate": self.error_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "metrics": self.metrics.to_dict(),
        }


@dataclass
class ProbeResult:
    """
    Result of a health probe check.

    Used by HealthMonitor for liveness and readiness probe results.
    """
    probe_type: str           # "liveness" or "readiness"
    agent_id: str
    success: bool
    message: str
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_type": self.probe_type,
            "agent_id": self.agent_id,
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }
