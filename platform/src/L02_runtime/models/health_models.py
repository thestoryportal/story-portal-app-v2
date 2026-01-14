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
    liveness: LivenessState = LivenessState.UNKNOWN
    readiness: ReadinessState = ReadinessState.UNKNOWN
    last_liveness_check: datetime = field(default_factory=datetime.utcnow)
    last_readiness_check: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    metrics: HealthMetrics = field(default_factory=HealthMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "liveness": self.liveness.value,
            "readiness": self.readiness.value,
            "last_liveness_check": self.last_liveness_check.isoformat(),
            "last_readiness_check": self.last_readiness_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "metrics": self.metrics.to_dict(),
        }
