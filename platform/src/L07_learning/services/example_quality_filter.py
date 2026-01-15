"""L07 Learning Layer - Example Quality Filter Service.

Scores and filters training examples by quality, diversity, and anomaly detection.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ..models.training_example import TrainingExample, DatasetStatistics
from ..models.error_codes import LearningErrorCode, ExampleFilteringError

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for quality filtering."""
    quality_threshold: float = 70.0
    confidence_threshold: float = 0.6
    max_outlier_probability: float = 0.15
    diversity_weight: float = 0.2
    min_dataset_size: int = 100
    max_dataset_size: int = 500000
    target_dataset_size: int = 50000


@dataclass
class FilteredExample:
    """Training example with quality assessment."""
    example: TrainingExample
    final_score: float
    recommendation: str  # "ACCEPT" | "REVIEW" | "REJECT"
    scores_breakdown: Dict[str, float]


class ExampleQualityFilter:
    """Filter and score training examples by quality signals.

    This service implements multi-criteria filtering to ensure only high-quality,
    diverse examples are used for model training.
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        """Initialize Example Quality Filter.

        Args:
            config: Filter configuration
        """
        self.config = config or FilterConfig()
        self.filtered_count = 0
        self.accepted_count = 0
        self.rejected_count = 0

        logger.info(
            f"Initialized ExampleQualityFilter: "
            f"quality_threshold={self.config.quality_threshold}, "
            f"confidence_threshold={self.config.confidence_threshold}"
        )

    async def filter_examples(
        self,
        examples: List[TrainingExample]
    ) -> Tuple[List[TrainingExample], Dict[str, Any]]:
        """Filter list of training examples.

        Args:
            examples: List of training examples to filter

        Returns:
            Tuple of (filtered_examples, metadata)

        Raises:
            ExampleFilteringError: If filtering fails critically
        """
        if not examples:
            logger.warning("Empty example list provided to filter")
            return [], {'total_input': 0, 'accepted': 0}

        logger.info(f"Filtering {len(examples)} examples")

        # Score all examples
        scored = [await self.score_example(ex, examples) for ex in examples]

        # Anomaly detection
        try:
            is_anomaly = await self._detect_anomalies(examples)
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {e}, continuing without it")
            is_anomaly = np.zeros(len(examples), dtype=bool)

        # Separate by recommendation
        accepted = []
        review = []
        rejected = []

        for i, scored_ex in enumerate(scored):
            if is_anomaly[i]:
                rejected.append(scored_ex.example)
                self.rejected_count += 1
            elif scored_ex.recommendation == "ACCEPT":
                accepted.append(scored_ex.example)
                self.accepted_count += 1
            elif scored_ex.recommendation == "REVIEW":
                review.append(scored_ex.example)
            else:
                rejected.append(scored_ex.example)
                self.rejected_count += 1

        # Stratified sampling if too large
        if len(accepted) > self.config.target_dataset_size:
            logger.info(f"Stratified sampling from {len(accepted)} to {self.config.target_dataset_size}")
            accepted = await self._stratified_sample(accepted, self.config.target_dataset_size)

        # Check if too few examples
        if len(accepted) < self.config.min_dataset_size:
            logger.warning(
                f"Insufficient examples after filtering: {len(accepted)} < {self.config.min_dataset_size}",
                extra={'error_code': LearningErrorCode.E7100.name}
            )

        self.filtered_count = len(examples)

        # Compute metadata
        metadata = {
            'total_input': len(examples),
            'accepted': len(accepted),
            'review': len(review),
            'rejected': len(rejected),
            'anomalies_detected': int(np.sum(is_anomaly)),
            'filter_rate': len(accepted) / len(examples) if examples else 0,
            'quality_mean': np.mean([ex.quality_score for ex in accepted]) if accepted else 0,
            'confidence_mean': np.mean([ex.confidence for ex in accepted]) if accepted else 0,
            'domain_distribution': self._domain_distribution(accepted),
            'difficulty_distribution': self._difficulty_distribution(accepted),
        }

        logger.info(
            f"Filtering complete: {metadata['accepted']} accepted, "
            f"{metadata['rejected']} rejected, "
            f"{metadata['anomalies_detected']} anomalies"
        )

        return accepted, metadata

    async def score_example(
        self,
        example: TrainingExample,
        existing_examples: Optional[List[TrainingExample]] = None
    ) -> FilteredExample:
        """Score single training example with multi-criteria assessment.

        Args:
            example: Training example to score
            existing_examples: Optional existing examples for diversity

        Returns:
            FilteredExample with scores and recommendation
        """
        # Component 1: L06 Quality Score (normalized 0-1)
        l06_score = example.quality_score / 100.0

        # Component 2: Confidence
        confidence_score = example.confidence

        # Component 3: Diversity (if we have existing examples)
        if existing_examples and len(existing_examples) > 10:
            diversity_score = self._compute_diversity(example, existing_examples)
        else:
            diversity_score = 0.5  # Default

        # Component 4: Informativeness (how valuable for learning)
        informativeness = self._estimate_informativeness(example)

        # Weighted aggregation
        final_score = (
            0.6 * l06_score +
            0.2 * confidence_score +
            0.1 * diversity_score +
            0.1 * informativeness
        )

        # Decision logic
        if (final_score >= (self.config.quality_threshold / 100.0) and
            confidence_score >= self.config.confidence_threshold):
            recommendation = "ACCEPT"
        elif final_score >= (self.config.quality_threshold / 100.0 * 0.8):
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"

        return FilteredExample(
            example=example,
            final_score=final_score,
            recommendation=recommendation,
            scores_breakdown={
                'l06_quality': l06_score,
                'confidence': confidence_score,
                'diversity': diversity_score,
                'informativeness': informativeness
            }
        )

    def _compute_diversity(
        self,
        example: TrainingExample,
        existing: List[TrainingExample]
    ) -> float:
        """Compute diversity score (0-1, higher = more diverse).

        Args:
            example: Example to score
            existing: Existing examples

        Returns:
            Diversity score
        """
        if not existing:
            return 0.5

        # Simple heuristic: compare task types and domains
        same_type = sum(1 for ex in existing if ex.task_type == example.task_type)
        same_domain = sum(1 for ex in existing if ex.domain == example.domain)

        diversity = 1.0 - (same_type + same_domain) / (2 * len(existing))
        return max(0, min(1, diversity))

    def _estimate_informativeness(self, example: TrainingExample) -> float:
        """Estimate how much learning value this example provides.

        Args:
            example: Training example

        Returns:
            Informativeness score (0-1)
        """
        # Harder examples are more informative
        difficulty_component = example.difficulty * 0.5

        # More steps = more reasoning shown = more informative
        num_steps = len(example.expected_actions)
        steps_component = min(num_steps / 5, 1.0) * 0.5

        return difficulty_component + steps_component

    async def _detect_anomalies(
        self,
        examples: List[TrainingExample]
    ) -> np.ndarray:
        """Detect anomalous examples using isolation forest.

        Args:
            examples: List of examples

        Returns:
            Boolean array indicating anomalies
        """
        if len(examples) < 100:
            return np.zeros(len(examples), dtype=bool)

        try:
            from sklearn.ensemble import IsolationForest

            # Extract features
            features = np.array([
                [ex.quality_score, ex.confidence, ex.difficulty]
                for ex in examples
            ])

            # Fit isolation forest
            clf = IsolationForest(
                contamination=self.config.max_outlier_probability,
                random_state=42
            )
            predictions = clf.fit_predict(features)

            # -1 indicates anomaly, 1 indicates normal
            return predictions == -1

        except ImportError:
            logger.warning("scikit-learn not available, skipping anomaly detection")
            return np.zeros(len(examples), dtype=bool)
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            raise ExampleFilteringError(
                LearningErrorCode.E7103,
                f"Anomaly detection failed: {e}"
            )

    async def _stratified_sample(
        self,
        examples: List[TrainingExample],
        target_size: int
    ) -> List[TrainingExample]:
        """Sample examples while preserving distribution.

        Args:
            examples: Examples to sample from
            target_size: Target number of examples

        Returns:
            Sampled examples
        """
        # Group by domain and task type
        strata: Dict[tuple, List[TrainingExample]] = {}
        for ex in examples:
            key = (ex.domain, ex.task_type.value if hasattr(ex.task_type, 'value') else str(ex.task_type))
            if key not in strata:
                strata[key] = []
            strata[key].append(ex)

        # Sample from each stratum proportionally
        sampled = []
        for stratum_key, items in strata.items():
            quota = int(target_size * len(items) / len(examples))
            if quota > 0:
                selected = np.random.choice(
                    len(items),
                    size=min(quota, len(items)),
                    replace=False
                )
                sampled.extend([items[i] for i in selected])

        # If we haven't reached target, randomly sample remainder
        if len(sampled) < target_size:
            remaining_quota = target_size - len(sampled)
            remaining_pool = [ex for ex in examples if ex not in sampled]
            if remaining_pool:
                selected = np.random.choice(
                    len(remaining_pool),
                    size=min(remaining_quota, len(remaining_pool)),
                    replace=False
                )
                sampled.extend([remaining_pool[i] for i in selected])

        return sampled[:target_size]

    def _domain_distribution(self, examples: List[TrainingExample]) -> Dict[str, int]:
        """Count examples per domain.

        Args:
            examples: List of examples

        Returns:
            Domain distribution dictionary
        """
        dist: Dict[str, int] = {}
        for ex in examples:
            dist[ex.domain] = dist.get(ex.domain, 0) + 1
        return dist

    def _difficulty_distribution(self, examples: List[TrainingExample]) -> Dict[str, int]:
        """Count examples by difficulty bin.

        Args:
            examples: List of examples

        Returns:
            Difficulty distribution dictionary
        """
        bins = {'easy': 0, 'medium': 0, 'hard': 0}
        for ex in examples:
            if ex.difficulty < 0.33:
                bins['easy'] += 1
            elif ex.difficulty < 0.66:
                bins['medium'] += 1
            else:
                bins['hard'] += 1
        return bins

    def get_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'total_filtered': self.filtered_count,
            'total_accepted': self.accepted_count,
            'total_rejected': self.rejected_count,
            'acceptance_rate': self.accepted_count / max(1, self.filtered_count)
        }
