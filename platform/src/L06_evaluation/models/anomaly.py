"""Anomaly detection models"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class AnomalySeverity(str, Enum):
    """Anomaly severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Baseline:
    """
    Statistical baseline for anomaly detection.

    Tracks running mean and standard deviation for z-score calculation.
    """
    metric_name: str
    mean: float
    stddev: float
    sample_count: int
    last_updated: datetime
    window_hours: int = 24

    def __post_init__(self):
        """Validate baseline"""
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated.replace('Z', '+00:00'))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "metric_name": self.metric_name,
            "mean": self.mean,
            "stddev": self.stddev,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat() + "Z" if isinstance(self.last_updated, datetime) else self.last_updated,
            "window_hours": self.window_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Baseline":
        """Create Baseline from dictionary"""
        return cls(
            metric_name=data["metric_name"],
            mean=data["mean"],
            stddev=data["stddev"],
            sample_count=data["sample_count"],
            last_updated=data["last_updated"],
            window_hours=data.get("window_hours", 24),
        )

    def is_established(self, min_samples: int = 100) -> bool:
        """Check if baseline has enough samples"""
        return self.sample_count >= min_samples and self.stddev > 0

    def calculate_z_score(self, value: float) -> float:
        """Calculate z-score for given value"""
        if self.stddev == 0:
            return 0.0
        return abs(value - self.mean) / self.stddev


@dataclass
class Anomaly:
    """
    Detected anomaly in metric or quality score.

    Uses z-score based statistical detection.
    """
    anomaly_id: str
    metric_name: str
    severity: AnomalySeverity
    baseline_value: float
    current_value: float
    z_score: float
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    deviation_percent: float = field(init=False)
    confidence: float = 0.95
    status: str = "alerting"
    alert_sent: bool = False

    def __post_init__(self):
        """Generate ID and calculate deviation"""
        if not self.anomaly_id:
            self.anomaly_id = f"anom-{uuid.uuid4()}"

        if isinstance(self.detected_at, str):
            self.detected_at = datetime.fromisoformat(self.detected_at.replace('Z', '+00:00'))

        if isinstance(self.resolved_at, str):
            self.resolved_at = datetime.fromisoformat(self.resolved_at.replace('Z', '+00:00'))

        # Calculate deviation percentage
        if self.baseline_value != 0:
            self.deviation_percent = ((self.current_value - self.baseline_value) / abs(self.baseline_value)) * 100
        else:
            self.deviation_percent = 100.0 if self.current_value != 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "anomaly_id": self.anomaly_id,
            "metric_name": self.metric_name,
            "severity": self.severity.value,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "z_score": self.z_score,
            "detected_at": self.detected_at.isoformat() + "Z" if isinstance(self.detected_at, datetime) else self.detected_at,
            "resolved_at": self.resolved_at.isoformat() + "Z" if isinstance(self.resolved_at, datetime) and self.resolved_at else None,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "deviation_percent": self.deviation_percent,
            "confidence": self.confidence,
            "status": self.status,
            "alert_sent": self.alert_sent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Anomaly":
        """Create Anomaly from dictionary"""
        return cls(
            anomaly_id=data["anomaly_id"],
            metric_name=data["metric_name"],
            severity=AnomalySeverity(data["severity"]),
            baseline_value=data["baseline_value"],
            current_value=data["current_value"],
            z_score=data["z_score"],
            detected_at=data["detected_at"],
            resolved_at=data.get("resolved_at"),
            agent_id=data.get("agent_id"),
            tenant_id=data.get("tenant_id"),
            confidence=data.get("confidence", 0.95),
            status=data.get("status", "alerting"),
            alert_sent=data.get("alert_sent", False),
        )

    def resolve(self):
        """Mark anomaly as resolved"""
        self.resolved_at = datetime.utcnow()
        self.status = "resolved"

    def is_resolved(self) -> bool:
        """Check if anomaly is resolved"""
        return self.resolved_at is not None

    @staticmethod
    def determine_severity(z_score: float) -> AnomalySeverity:
        """Determine severity based on z-score"""
        if z_score >= 4.0:
            return AnomalySeverity.CRITICAL
        elif z_score >= 3.0:
            return AnomalySeverity.WARNING
        else:
            return AnomalySeverity.INFO
