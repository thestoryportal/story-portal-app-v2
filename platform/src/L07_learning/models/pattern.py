"""L07 Learning Layer - Behavioral Pattern Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class PatternType(Enum):
    """Type of behavioral pattern."""
    TOOL_SEQUENCE = "tool_sequence"
    DECISION_STRATEGY = "decision_strategy"
    ERROR_RECOVERY = "error_recovery"
    OPTIMIZATION = "optimization"


class PatternConfidence(Enum):
    """Confidence level in pattern."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class BehavioralPattern:
    """Extracted behavioral pattern from execution traces.

    Represents a recurring decision-making pattern or strategy
    observed in successful executions.
    """

    # Identifiers
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Pattern definition
    pattern_type: PatternType = PatternType.TOOL_SEQUENCE
    pattern_signature: str = ""  # Unique signature for matching
    pattern_template: Dict[str, Any] = field(default_factory=dict)

    # Observed statistics
    observation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0

    # Quality metrics
    average_quality_score: float = 0.0
    average_confidence: float = 0.0
    pattern_confidence: PatternConfidence = PatternConfidence.MEDIUM

    # Context
    domains: List[str] = field(default_factory=list)
    task_types: List[str] = field(default_factory=list)
    applicable_conditions: List[str] = field(default_factory=list)

    # Examples
    example_execution_ids: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    extracted_by: str = "PatternExtractor v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['pattern_type'] = self.pattern_type.value
        data['pattern_confidence'] = self.pattern_confidence.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    def update_statistics(self, success: bool, quality_score: float, confidence: float) -> None:
        """Update pattern statistics with new observation.

        Args:
            success: Whether observation was successful
            quality_score: Quality score of execution
            confidence: Confidence in quality score
        """
        self.observation_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.success_rate = self.success_count / self.observation_count

        # Update rolling averages
        weight = 0.9  # Weight for existing average
        self.average_quality_score = (
            weight * self.average_quality_score +
            (1 - weight) * quality_score
        )
        self.average_confidence = (
            weight * self.average_confidence +
            (1 - weight) * confidence
        )

        # Update pattern confidence
        if self.observation_count >= 100 and self.success_rate >= 0.9:
            self.pattern_confidence = PatternConfidence.VERY_HIGH
        elif self.observation_count >= 50 and self.success_rate >= 0.8:
            self.pattern_confidence = PatternConfidence.HIGH
        elif self.observation_count >= 20 and self.success_rate >= 0.7:
            self.pattern_confidence = PatternConfidence.MEDIUM
        else:
            self.pattern_confidence = PatternConfidence.LOW

        self.updated_at = datetime.utcnow()


@dataclass
class PlanningStrategy:
    """Optimized planning strategy extracted from traces.

    Represents a high-level strategy for task planning that has
    shown consistent success.
    """

    # Identifiers
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Strategy definition
    strategy_type: str = "sequential"  # sequential, parallel, adaptive
    decision_tree: Dict[str, Any] = field(default_factory=dict)
    heuristics: List[str] = field(default_factory=list)

    # Performance metrics
    average_success_rate: float = 0.0
    average_execution_time_seconds: float = 0.0
    average_quality_score: float = 0.0

    # Usage statistics
    usage_count: int = 0
    domains: List[str] = field(default_factory=list)

    # Recommendation
    recommended_for: List[str] = field(default_factory=list)
    confidence_score: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    optimized_by: str = "StrategyOptimizer v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    def apply_to_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Apply strategy to task (stub).

        Args:
            task: Task definition

        Returns:
            Modified task with strategy applied
        """
        # Stub implementation
        return task
