"""Quality scorer service for multi-dimensional scoring"""

import logging
from datetime import datetime
from typing import Dict, Optional

from ..models.quality_score import QualityScore, DimensionScore, Assessment
from ..models.error_codes import ErrorCode
from ..scorers.accuracy_scorer import AccuracyScorer
from ..scorers.latency_scorer import LatencyScorer
from ..scorers.cost_scorer import CostScorer
from ..scorers.reliability_scorer import ReliabilityScorer
from ..scorers.compliance_scorer import ComplianceScorer
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class QualityScorer:
    """
    Computes multi-dimensional quality scores for agent execution.

    Per spec Section 3.2 (Component Responsibilities #4):
    - 5 dimensions: accuracy, latency, cost, reliability, compliance
    - Configurable weights (must sum to 1.0)
    - Score range 0-100
    - Assessment thresholds: Good (>=80), Warning (60-79), Critical (<60)
    """

    def __init__(
        self,
        metrics_engine: Optional[any] = None,
        compliance_validator: Optional[any] = None,
        cache_manager: Optional[CacheManager] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize quality scorer.

        Args:
            metrics_engine: MetricsEngine for querying metrics (optional, created in initialize())
            compliance_validator: ComplianceValidator for compliance scoring
            cache_manager: CacheManager for score caching (optional)
            weights: Dimension weights (default: balanced)
        """
        self.metrics_engine = metrics_engine
        self.cache = cache_manager
        self.compliance_validator = compliance_validator
        self._initialized = False

        # Default weights (must sum to 1.0)
        self.weights = weights or {
            "accuracy": 0.3,
            "latency": 0.25,
            "cost": 0.15,
            "reliability": 0.2,
            "compliance": 0.1,
        }

        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        # Dimension scorers - initialized in initialize()
        self.scorers = {}

        # Statistics
        self.scores_computed = 0
        self.cache_hits = 0

        # Dimensions list for tests
        self.dimensions = list(self.weights.keys())

    async def initialize(self):
        """Initialize quality scorer and create dependencies if needed."""
        if self._initialized:
            return

        # Create metrics engine if not provided
        if self.metrics_engine is None:
            from .metrics_engine import MetricsEngine
            self.metrics_engine = MetricsEngine()
            await self.metrics_engine.initialize()

        # Initialize dimension scorers
        self.scorers = {
            "accuracy": AccuracyScorer(self.metrics_engine, self.weights["accuracy"]),
            "latency": LatencyScorer(self.metrics_engine, self.weights["latency"]),
            "cost": CostScorer(self.metrics_engine, self.weights["cost"]),
            "reliability": ReliabilityScorer(self.metrics_engine, self.weights["reliability"]),
            "compliance": ComplianceScorer(self.compliance_validator, self.weights["compliance"]),
        }

        self._initialized = True
        logger.info("QualityScorer initialized")

    async def cleanup(self):
        """Cleanup quality scorer resources."""
        if self.metrics_engine and not self._initialized:
            # Only cleanup if we created it
            if hasattr(self.metrics_engine, 'cleanup'):
                await self.metrics_engine.cleanup()
        self._initialized = False
        logger.info("QualityScorer cleaned up")

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> QualityScore:
        """
        Compute multi-dimensional quality score.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            time_window: (start, end) datetime tuple

        Returns:
            QualityScore with overall score and dimension scores
        """
        start, end = time_window

        try:
            # Check cache first
            if self.cache:
                cached = await self.cache.get_quality_score(agent_id, start)
                if cached:
                    self.cache_hits += 1
                    logger.debug(f"Quality score cache hit: {agent_id}")
                    cached["cached"] = True
                    return QualityScore.from_dict(cached)

            # Compute dimension scores in parallel
            import asyncio
            dimension_tasks = {
                name: scorer.compute_score(agent_id, tenant_id, time_window)
                for name, scorer in self.scorers.items()
            }

            dimension_results = await asyncio.gather(
                *dimension_tasks.values(),
                return_exceptions=True,
            )

            # Build dimensions dict
            dimensions = {}
            data_completeness = 1.0

            for (name, _), result in zip(dimension_tasks.items(), dimension_results):
                if isinstance(result, Exception):
                    logger.error(f"Dimension {name} failed: {result}")
                    # Use default score on error
                    dimensions[name] = DimensionScore(
                        dimension=name,
                        score=50.0,
                        weight=self.weights[name],
                        raw_metrics={"error": str(result)},
                    )
                    data_completeness -= 0.2  # Penalize for missing dimension
                else:
                    dimensions[name] = result

            # Calculate overall score
            overall_score = sum(
                dim.score * dim.weight for dim in dimensions.values()
            )

            # Determine assessment
            assessment = QualityScore.determine_assessment(overall_score)

            # Create quality score
            score = QualityScore(
                score_id="",  # Will be auto-generated
                agent_id=agent_id,
                tenant_id=tenant_id,
                timestamp=start,
                overall_score=overall_score,
                dimensions=dimensions,
                assessment=assessment,
                data_completeness=max(0.0, data_completeness),
                cached=False,
            )

            # Cache result
            if self.cache:
                await self.cache.set_quality_score(agent_id, start, score.to_dict())

            self.scores_computed += 1
            return score

        except Exception as e:
            logger.error(f"Quality score computation failed: {e}")
            raise Exception(f"Quality score calculation error: {e}")

    async def get_dimension_score(
        self,
        dimension: str,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> Optional[DimensionScore]:
        """
        Get score for a single dimension.

        Args:
            dimension: Dimension name (accuracy, latency, cost, reliability, compliance)
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            time_window: (start, end) datetime tuple

        Returns:
            DimensionScore or None if dimension not found
        """
        if dimension not in self.scorers:
            logger.error(f"Unknown dimension: {dimension}")
            return None

        try:
            scorer = self.scorers[dimension]
            return await scorer.compute_score(agent_id, tenant_id, time_window)
        except Exception as e:
            logger.error(f"Dimension score computation failed: {e}")
            return None

    def update_weights(self, weights: Dict[str, float]):
        """
        Update dimension weights.

        Args:
            weights: New weights (must sum to 1.0)

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        self.weights = weights

        # Update scorer weights
        for dimension, weight in weights.items():
            if dimension in self.scorers:
                self.scorers[dimension].weight = weight

        logger.info(f"Updated quality scorer weights: {weights}")

    def get_weights(self) -> Dict[str, float]:
        """Get current dimension weights"""
        return self.weights.copy()

    def get_statistics(self) -> dict:
        """Get quality scorer statistics"""
        total_requests = self.scores_computed + self.cache_hits
        cache_hit_rate = (
            self.cache_hits / total_requests if total_requests > 0 else 0.0
        )

        return {
            "scores_computed": self.scores_computed,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "weights": self.weights,
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.scores_computed = 0
        self.cache_hits = 0
