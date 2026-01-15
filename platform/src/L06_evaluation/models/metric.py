"""Metric models for time-series data"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict


class MetricType(str, Enum):
    """Metric types per Prometheus conventions"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricAggregation(str, Enum):
    """Metric aggregation functions"""
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    STDDEV = "stddev"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"
    COUNT = "count"


@dataclass
class MetricPoint:
    """
    Single metric data point for time-series storage.

    Follows Prometheus data model with labels for dimensionality.
    """
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

    def __post_init__(self):
        """Validate metric point"""
        # Ensure timestamp is datetime
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

        # Validate value is not NaN or Inf
        if not isinstance(self.value, (int, float)):
            raise ValueError(f"Metric value must be numeric, got {type(self.value)}")

        import math
        if math.isnan(self.value) or math.isinf(self.value):
            raise ValueError(f"Metric value cannot be NaN or Inf: {self.value}")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "labels": self.labels,
            "metric_type": self.metric_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricPoint":
        """Create MetricPoint from dictionary"""
        return cls(
            metric_name=data["metric_name"],
            value=data["value"],
            timestamp=data["timestamp"],
            labels=data.get("labels", {}),
            metric_type=MetricType(data.get("metric_type", "gauge")),
        )

    def label_hash(self) -> str:
        """Generate hash of labels for cardinality tracking"""
        import hashlib
        label_str = ",".join(f"{k}={v}" for k, v in sorted(self.labels.items()))
        return hashlib.md5(label_str.encode()).hexdigest()

    def series_key(self) -> str:
        """Generate unique key for this metric series"""
        return f"{self.metric_name}:{self.label_hash()}"
