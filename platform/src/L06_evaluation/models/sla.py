"""SLA (Service Level Agreement) models"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
import uuid


class SLAStatus(str, Enum):
    """SLA compliance status"""
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    BREACHED = "breached"


@dataclass
class SLAMetric:
    """Single SLA metric target and actual"""
    name: str
    target: float
    actual: float
    unit: str
    status: str = "pass"
    breaches: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "target": self.target,
            "actual": self.actual,
            "unit": self.unit,
            "status": self.status,
            "breaches": self.breaches,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SLAMetric":
        """Create SLAMetric from dictionary"""
        return cls(
            name=data["name"],
            target=data["target"],
            actual=data["actual"],
            unit=data.get("unit", ""),
            status=data.get("status", "pass"),
            breaches=data.get("breaches", 0),
        )

    def check_compliance(self) -> bool:
        """Check if metric is within SLA target"""
        # For metrics like error_rate, lower is better
        if self.name in ["error_rate", "latency_p99", "latency_p95"]:
            return self.actual <= self.target
        # For metrics like availability, higher is better
        elif self.name in ["availability", "success_rate"]:
            return self.actual >= self.target
        else:
            # Default: actual should be <= target
            return self.actual <= self.target


@dataclass
class SLADefinition:
    """
    SLA definition with targets and error budget.

    Defines service level objectives for agent execution.
    """
    sla_id: str
    name: str
    agent_id: str
    tenant_id: str
    metrics: Dict[str, SLAMetric] = field(default_factory=dict)
    error_budget: float = 1.0
    error_budget_remaining: float = 1.0
    window_days: int = 30

    def __post_init__(self):
        """Generate ID if not provided"""
        if not self.sla_id:
            self.sla_id = f"sla-{uuid.uuid4()}"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "sla_id": self.sla_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "error_budget": self.error_budget,
            "error_budget_remaining": self.error_budget_remaining,
            "window_days": self.window_days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SLADefinition":
        """Create SLADefinition from dictionary"""
        metrics = {}
        for k, v in data.get("metrics", {}).items():
            if isinstance(v, dict):
                metrics[k] = SLAMetric.from_dict(v)
            else:
                metrics[k] = v

        return cls(
            sla_id=data.get("sla_id", ""),
            name=data["name"],
            agent_id=data["agent_id"],
            tenant_id=data["tenant_id"],
            metrics=metrics,
            error_budget=data.get("error_budget", 1.0),
            error_budget_remaining=data.get("error_budget_remaining", 1.0),
            window_days=data.get("window_days", 30),
        )

    def check_overall_compliance(self) -> SLAStatus:
        """Check overall SLA compliance status"""
        failing_metrics = sum(1 for m in self.metrics.values() if not m.check_compliance())

        if failing_metrics == 0:
            return SLAStatus.COMPLIANT
        elif self.error_budget_remaining > 0.2:
            return SLAStatus.AT_RISK
        else:
            return SLAStatus.BREACHED

    def consume_error_budget(self, amount: float):
        """Consume error budget"""
        self.error_budget_remaining = max(0.0, self.error_budget_remaining - amount)


@dataclass
class SLAViolation:
    """
    SLA violation instance.

    Records when SLA was breached.
    """
    violation_id: str
    sla_id: str
    agent_id: str
    tenant_id: str
    timestamp: datetime
    metric_name: str
    target: float
    actual: float
    duration_seconds: float = 0.0
    resolved_at: Optional[datetime] = None

    def __post_init__(self):
        """Generate ID and validate"""
        if not self.violation_id:
            self.violation_id = f"sla-viol-{uuid.uuid4()}"

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

        if isinstance(self.resolved_at, str):
            self.resolved_at = datetime.fromisoformat(self.resolved_at.replace('Z', '+00:00'))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "violation_id": self.violation_id,
            "sla_id": self.sla_id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "metric_name": self.metric_name,
            "target": self.target,
            "actual": self.actual,
            "duration_seconds": self.duration_seconds,
            "resolved_at": self.resolved_at.isoformat() + "Z" if isinstance(self.resolved_at, datetime) and self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SLAViolation":
        """Create SLAViolation from dictionary"""
        return cls(
            violation_id=data.get("violation_id", ""),
            sla_id=data["sla_id"],
            agent_id=data["agent_id"],
            tenant_id=data["tenant_id"],
            timestamp=data["timestamp"],
            metric_name=data["metric_name"],
            target=data["target"],
            actual=data["actual"],
            duration_seconds=data.get("duration_seconds", 0.0),
            resolved_at=data.get("resolved_at"),
        )

    def resolve(self):
        """Mark violation as resolved"""
        self.resolved_at = datetime.utcnow()
        if self.resolved_at and isinstance(self.timestamp, datetime):
            self.duration_seconds = (self.resolved_at - self.timestamp).total_seconds()

    def is_resolved(self) -> bool:
        """Check if violation is resolved"""
        return self.resolved_at is not None
