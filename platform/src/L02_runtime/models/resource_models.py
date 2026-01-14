"""
Resource Management Data Models

Models for resource quotas and usage tracking.
Based on Section 5.1.3 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from uuid import uuid4


class QuotaScope(Enum):
    """Scope of resource quota"""
    AGENT = "agent"         # Per-agent quota
    TENANT = "tenant"       # Per-tenant quota
    NAMESPACE = "namespace" # Per-namespace quota


@dataclass
class QuotaUsage:
    """Current resource usage against quota"""
    cpu_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    tokens_consumed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_seconds": self.cpu_seconds,
            "memory_peak_mb": self.memory_peak_mb,
            "tokens_consumed": self.tokens_consumed,
        }


@dataclass
class ResourceQuota:
    """
    Resource allocation for an agent or tenant.

    Tracks usage against limits with automatic reset.
    """
    quota_id: str = field(default_factory=lambda: str(uuid4()))
    scope: QuotaScope = QuotaScope.AGENT
    target_id: str = ""              # Agent ID, tenant ID, or namespace
    limits: Dict[str, Any] = field(default_factory=dict)
    usage: QuotaUsage = field(default_factory=QuotaUsage)
    reset_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quota_id": self.quota_id,
            "scope": self.scope.value,
            "target_id": self.target_id,
            "limits": self.limits,
            "usage": self.usage.to_dict(),
            "reset_at": self.reset_at.isoformat(),
        }

    def is_exceeded(self) -> bool:
        """Check if any quota limit is exceeded"""
        cpu_limit = float(self.limits.get("cpu", "0").rstrip("m"))
        memory_limit_str = self.limits.get("memory", "0Gi")
        memory_limit_mb = self._parse_memory_to_mb(memory_limit_str)
        tokens_limit = self.limits.get("tokens_per_hour", 0)

        return (
            (cpu_limit > 0 and self.usage.cpu_seconds > cpu_limit) or
            (memory_limit_mb > 0 and self.usage.memory_peak_mb > memory_limit_mb) or
            (tokens_limit > 0 and self.usage.tokens_consumed > tokens_limit)
        )

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
