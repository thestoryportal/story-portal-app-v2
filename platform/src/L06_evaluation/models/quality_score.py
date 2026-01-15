"""Quality score models for multi-dimensional evaluation"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict
import uuid


class Assessment(str, Enum):
    """Quality assessment categories"""
    GOOD = "Good"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class DimensionScore:
    """
    Score for a single quality dimension.

    Dimensions: accuracy, latency, cost, reliability, compliance
    """
    dimension: str
    score: float
    weight: float
    raw_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate dimension score"""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Dimension score must be 0-100, got {self.score}")

        if not 0 <= self.weight <= 1:
            raise ValueError(f"Dimension weight must be 0-1, got {self.weight}")

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "raw_metrics": self.raw_metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DimensionScore":
        """Create DimensionScore from dictionary"""
        return cls(
            dimension=data["dimension"],
            score=data["score"],
            weight=data["weight"],
            raw_metrics=data.get("raw_metrics", {}),
        )


@dataclass
class QualityScore:
    """
    Multi-dimensional quality score for agent execution.

    Combines 5 dimensions with configurable weights to produce
    an overall quality assessment.
    """
    score_id: str
    agent_id: str
    tenant_id: str
    timestamp: datetime
    overall_score: float
    dimensions: Dict[str, DimensionScore]
    assessment: Assessment
    data_completeness: float = 1.0
    cached: bool = False

    def __post_init__(self):
        """Validate quality score"""
        if not self.score_id:
            self.score_id = str(uuid.uuid4())

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

        if not 0 <= self.overall_score <= 100:
            raise ValueError(f"Overall score must be 0-100, got {self.overall_score}")

        if not 0 <= self.data_completeness <= 1:
            raise ValueError(f"Data completeness must be 0-1, got {self.data_completeness}")

        # Validate weights sum to 1.0 (with tolerance)
        if self.dimensions:
            total_weight = sum(d.weight for d in self.dimensions.values())
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(f"Dimension weights must sum to 1.0, got {total_weight}")

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "score_id": self.score_id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "overall_score": self.overall_score,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "assessment": self.assessment.value,
            "data_completeness": self.data_completeness,
            "cached": self.cached,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QualityScore":
        """Create QualityScore from dictionary"""
        dimensions = {}
        for k, v in data.get("dimensions", {}).items():
            if isinstance(v, dict):
                dimensions[k] = DimensionScore.from_dict(v)
            else:
                dimensions[k] = v

        return cls(
            score_id=data["score_id"],
            agent_id=data["agent_id"],
            tenant_id=data["tenant_id"],
            timestamp=data["timestamp"],
            overall_score=data["overall_score"],
            dimensions=dimensions,
            assessment=Assessment(data["assessment"]),
            data_completeness=data.get("data_completeness", 1.0),
            cached=data.get("cached", False),
        )

    @staticmethod
    def determine_assessment(score: float) -> Assessment:
        """Determine assessment category based on score"""
        if score >= 80:
            return Assessment.GOOD
        elif score >= 60:
            return Assessment.WARNING
        else:
            return Assessment.CRITICAL

    def get_dimension_score(self, dimension: str) -> float:
        """Get score for specific dimension"""
        if dimension in self.dimensions:
            return self.dimensions[dimension].score
        return 0.0
