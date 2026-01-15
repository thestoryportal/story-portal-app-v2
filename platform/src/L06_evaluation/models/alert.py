"""Alert models for notification routing"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
import uuid


class AlertChannel(str, Enum):
    """Alert delivery channels"""
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """
    Alert message for anomalies and violations.

    Routes to configured channels (Slack, PagerDuty, email).
    """
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    type: str
    metric: str
    message: str
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    channels: list[AlertChannel] = field(default_factory=lambda: [AlertChannel.SLACK])
    metadata: Dict[str, any] = field(default_factory=dict)
    delivery_attempts: int = 0
    delivered: bool = False
    last_attempt: Optional[datetime] = None

    def __post_init__(self):
        """Generate ID and validate"""
        if not self.alert_id:
            self.alert_id = f"alert-{uuid.uuid4()}"

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

        if isinstance(self.last_attempt, str):
            self.last_attempt = datetime.fromisoformat(self.last_attempt.replace('Z', '+00:00'))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "severity": self.severity.value,
            "type": self.type,
            "metric": self.metric,
            "message": self.message,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "channels": [c.value for c in self.channels],
            "metadata": self.metadata,
            "delivery_attempts": self.delivery_attempts,
            "delivered": self.delivered,
            "last_attempt": self.last_attempt.isoformat() + "Z" if isinstance(self.last_attempt, datetime) and self.last_attempt else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """Create Alert from dictionary"""
        channels = [AlertChannel(c) if isinstance(c, str) else c for c in data.get("channels", ["slack"])]

        return cls(
            alert_id=data.get("alert_id", ""),
            timestamp=data["timestamp"],
            severity=AlertSeverity(data["severity"]),
            type=data["type"],
            metric=data["metric"],
            message=data["message"],
            agent_id=data.get("agent_id"),
            tenant_id=data.get("tenant_id"),
            channels=channels,
            metadata=data.get("metadata", {}),
            delivery_attempts=data.get("delivery_attempts", 0),
            delivered=data.get("delivered", False),
            last_attempt=data.get("last_attempt"),
        )

    def increment_attempts(self):
        """Increment delivery attempt counter"""
        self.delivery_attempts += 1
        self.last_attempt = datetime.utcnow()

    def mark_delivered(self):
        """Mark alert as successfully delivered"""
        self.delivered = True

    def should_retry(self, max_retries: int = 6) -> bool:
        """Check if alert should be retried"""
        return not self.delivered and self.delivery_attempts < max_retries

    def calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay in seconds"""
        # Backoff: 100ms, 200ms, 500ms, 1s, 2s, 60s
        backoff_schedule = [0.1, 0.2, 0.5, 1.0, 2.0, 60.0]
        attempt = min(self.delivery_attempts, len(backoff_schedule) - 1)
        return backoff_schedule[attempt]

    @staticmethod
    def from_anomaly(anomaly: any) -> "Alert":
        """Create alert from anomaly"""
        from .anomaly import Anomaly, AnomalySeverity

        if isinstance(anomaly, Anomaly):
            severity_map = {
                AnomalySeverity.INFO: AlertSeverity.INFO,
                AnomalySeverity.WARNING: AlertSeverity.WARNING,
                AnomalySeverity.CRITICAL: AlertSeverity.CRITICAL,
            }

            return Alert(
                alert_id=f"alert-{anomaly.anomaly_id}",
                timestamp=anomaly.detected_at,
                severity=severity_map.get(anomaly.severity, AlertSeverity.WARNING),
                type="anomaly",
                metric=anomaly.metric_name,
                message=f"Anomaly detected: {anomaly.metric_name} deviation {anomaly.deviation_percent:.1f}% (z-score: {anomaly.z_score:.2f})",
                agent_id=anomaly.agent_id,
                tenant_id=anomaly.tenant_id,
                metadata={
                    "baseline_value": anomaly.baseline_value,
                    "current_value": anomaly.current_value,
                    "z_score": anomaly.z_score,
                    "deviation_percent": anomaly.deviation_percent,
                },
            )
        else:
            raise ValueError(f"Cannot create alert from {type(anomaly)}")

    @staticmethod
    def from_violation(violation: any) -> "Alert":
        """Create alert from compliance violation"""
        from .compliance import Violation

        if isinstance(violation, Violation):
            severity_map = {
                "info": AlertSeverity.INFO,
                "warning": AlertSeverity.WARNING,
                "critical": AlertSeverity.CRITICAL,
            }

            return Alert(
                alert_id=f"alert-{violation.violation_id}",
                timestamp=violation.timestamp,
                severity=severity_map.get(violation.severity, AlertSeverity.WARNING),
                type="compliance_violation",
                metric=violation.constraint.name,
                message=f"Compliance violation: {violation.constraint.name} limit {violation.constraint.limit} {violation.constraint.unit}, actual {violation.actual}",
                agent_id=violation.agent_id,
                tenant_id=violation.tenant_id,
                metadata={
                    "constraint_type": violation.constraint.constraint_type.value,
                    "limit": violation.constraint.limit,
                    "actual": violation.actual,
                    "task_id": violation.task_id,
                    "remediation": violation.remediation_suggested,
                },
            )
        else:
            raise ValueError(f"Cannot create alert from {type(violation)}")
