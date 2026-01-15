"""
Fleet Management Data Models

Models for fleet scaling and management operations.
Based on Section 4.1.3 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class ScalePriority(Enum):
    """Priority level for scaling operations"""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ScaleRequest:
    """Request to scale fleet size"""
    target_replicas: int
    reason: str
    priority: ScalePriority = ScalePriority.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_replicas": self.target_replicas,
            "reason": self.reason,
            "priority": self.priority.value,
        }


@dataclass
class FleetStatus:
    """Current fleet status"""
    total_instances: int = 0
    running: int = 0
    suspended: int = 0
    warm_pool_size: int = 0
    pending_scale_operations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_instances": self.total_instances,
            "running": self.running,
            "suspended": self.suspended,
            "warm_pool_size": self.warm_pool_size,
            "pending_scale_operations": self.pending_scale_operations,
        }


@dataclass
class ScalingMetrics:
    """
    Metrics used for fleet scaling decisions.

    Used by FleetManager to evaluate scaling actions.
    """
    current_replicas: int
    desired_replicas: int
    avg_cpu_utilization: float       # Percentage (0-100)
    avg_memory_utilization: float    # Percentage (0-100)
    pending_requests: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_replicas": self.current_replicas,
            "desired_replicas": self.desired_replicas,
            "avg_cpu_utilization": self.avg_cpu_utilization,
            "avg_memory_utilization": self.avg_memory_utilization,
            "pending_requests": self.pending_requests,
        }


@dataclass
class WarmInstance:
    """
    Pre-warmed agent instance in the warm pool.

    Used by WarmPoolManager to track ready-to-allocate instances.
    """
    agent_id: str
    session_id: str
    runtime_class: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    allocated: bool = False
    allocated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "runtime_class": self.runtime_class,
            "created_at": self.created_at.isoformat(),
            "allocated": self.allocated,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
        }
