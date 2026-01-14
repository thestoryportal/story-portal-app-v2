"""
Fleet Management Data Models

Models for fleet scaling and management operations.
Based on Section 4.1.3 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


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
