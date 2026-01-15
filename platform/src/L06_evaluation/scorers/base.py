"""Base scorer protocol for quality dimensions"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Protocol

from ..models.quality_score import DimensionScore


class ScorerProtocol(Protocol):
    """Protocol for dimension scorers"""

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """
        Compute dimension score for agent in time window.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            time_window: (start, end) datetime tuple

        Returns:
            DimensionScore with score 0-100
        """
        ...


class Scorer(ABC):
    """
    Base class for dimension scorers.

    All scorers must return score 0-100 where:
    - 100: Perfect performance
    - 80+: Good
    - 60-79: Warning
    - <60: Critical
    """

    def __init__(self, dimension_name: str, weight: float = 0.2):
        """
        Initialize scorer.

        Args:
            dimension_name: Name of dimension (accuracy, latency, cost, etc.)
            weight: Weight for this dimension (0-1, all weights must sum to 1.0)
        """
        self.dimension_name = dimension_name
        self.weight = weight

    @abstractmethod
    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """
        Compute dimension score.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def _clamp_score(self, score: float) -> float:
        """Clamp score to 0-100 range"""
        return max(0.0, min(100.0, score))

    def _linear_score(
        self,
        value: float,
        min_value: float,
        max_value: float,
        invert: bool = False,
    ) -> float:
        """
        Calculate linear score between min and max.

        Args:
            value: Actual value
            min_value: Minimum value (worst)
            max_value: Maximum value (best)
            invert: If True, lower values are better

        Returns:
            Score 0-100
        """
        if min_value == max_value:
            return 100.0

        if invert:
            # Lower is better (e.g., latency, cost)
            if value <= min_value:
                return 100.0
            elif value >= max_value:
                return 0.0
            else:
                ratio = (value - min_value) / (max_value - min_value)
                return 100.0 * (1.0 - ratio)
        else:
            # Higher is better (e.g., accuracy, reliability)
            if value >= max_value:
                return 100.0
            elif value <= min_value:
                return 0.0
            else:
                ratio = (value - min_value) / (max_value - min_value)
                return 100.0 * ratio

    def _create_dimension_score(
        self,
        score: float,
        raw_metrics: Dict[str, float],
    ) -> DimensionScore:
        """
        Create DimensionScore with clamped score.

        Args:
            score: Computed score (will be clamped to 0-100)
            raw_metrics: Raw metric values used in computation

        Returns:
            DimensionScore
        """
        return DimensionScore(
            dimension=self.dimension_name,
            score=self._clamp_score(score),
            weight=self.weight,
            raw_metrics=raw_metrics,
        )
