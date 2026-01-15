"""
L10 Human Interface Layer - Alert Models

Models for alert management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric: str
    current_value: float
    threshold: float
    triggered_at: datetime
    status: AlertStatus = AlertStatus.TRIGGERED
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    channels_notified: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            "message": self.message,
            "metric": self.metric,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat(),
            "status": self.status.value if isinstance(self.status, AlertStatus) else self.status,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "channels_notified": self.channels_notified,
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    rule_name: str
    metric: str
    condition: str  # "gt", "lt", "eq", etc.
    threshold: float
    severity: AlertSeverity
    evaluation_interval_sec: int = 60
    consecutive_breaches_required: int = 2
    enabled: bool = True
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "metric": self.metric,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            "evaluation_interval_sec": self.evaluation_interval_sec,
            "consecutive_breaches_required": self.consecutive_breaches_required,
            "enabled": self.enabled,
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
        }


@dataclass
class AcknowledgeRequest:
    """Request to acknowledge alert."""
    alert_id: str
    user_id: str
    comment: Optional[str] = None


@dataclass
class SnoozeRequest:
    """Request to snooze alert."""
    alert_id: str
    duration_minutes: int
    user_id: str
    reason: Optional[str] = None
