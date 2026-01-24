"""
Hybrid Classifier for L13 Role Management Layer.

Combines keyword-based classification with semantic classification
using configurable weights.
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from ..models import (
    RoleType,
    TaskRequirements,
    ClassificationResult,
)
from .classification_engine import ClassificationEngine
from .semantic_classifier import SemanticClassifier

logger = logging.getLogger(__name__)


class HybridClassifier:
    """
    Hybrid classifier combining keyword-based and semantic classification.

    Default weights: keyword (80%) + semantic (20%), configurable via
    environment variables or constructor parameters.
    """

    def __init__(
        self,
        keyword_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        human_threshold: float = 0.6,
        ai_threshold: float = 0.6,
        ollama_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize the hybrid classifier.

        Args:
            keyword_weight: Weight for keyword-based classification (default: 0.8)
            semantic_weight: Weight for semantic classification (default: 0.2)
            human_threshold: Score threshold for human_primary classification
            ai_threshold: Score threshold for ai_primary classification
            ollama_base_url: Ollama API endpoint for semantic classifier
            embedding_model: Model name for embeddings
        """
        # Get weights from environment or use defaults
        self.keyword_weight = keyword_weight or float(
            os.environ.get("L13_KEYWORD_WEIGHT", "0.8")
        )
        self.semantic_weight = semantic_weight or float(
            os.environ.get("L13_SEMANTIC_WEIGHT", "0.2")
        )

        # Normalize weights to sum to 1.0
        total = self.keyword_weight + self.semantic_weight
        if total != 1.0:
            self.keyword_weight /= total
            self.semantic_weight /= total
            logger.info(
                f"Normalized weights: keyword={self.keyword_weight:.2f}, "
                f"semantic={self.semantic_weight:.2f}"
            )

        # Initialize classifiers
        self.keyword_classifier = ClassificationEngine(
            human_threshold=human_threshold,
            ai_threshold=ai_threshold,
            default_to_hybrid=True,
        )

        self.semantic_classifier = SemanticClassifier(
            ollama_base_url=ollama_base_url,
            embedding_model=embedding_model,
        )

        self._initialized = False

        logger.info(
            f"HybridClassifier initialized: "
            f"keyword_weight={self.keyword_weight:.2f}, "
            f"semantic_weight={self.semantic_weight:.2f}"
        )

    async def initialize(self) -> None:
        """Initialize the semantic classifier (keyword classifier needs no init)."""
        if self._initialized:
            return
        await self.semantic_classifier.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close resources."""
        await self.semantic_classifier.close()

    async def classify_task(
        self,
        task_id: str,
        requirements: TaskRequirements,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classify a task using hybrid approach.

        Args:
            task_id: Task identifier
            requirements: Task requirements
            context: Optional additional context

        Returns:
            ClassificationResult with routing decision
        """
        if not self._initialized:
            await self.initialize()

        context = context or {}

        # Get keyword-based classification
        keyword_result = await self.keyword_classifier.classify_task(
            task_id=task_id,
            requirements=requirements,
            context=context,
        )

        # Get semantic scores
        semantic_scores = await self.semantic_classifier.get_semantic_scores(
            requirements
        )

        # Convert keyword scores to 0-1 range for each category
        keyword_factors = keyword_result.factors
        keyword_human = keyword_factors.get("human_total", 0)
        keyword_ai = keyword_factors.get("ai_total", 0)
        keyword_hybrid = 1 - abs(keyword_human - keyword_ai)  # High when balanced

        # Semantic scores are already 0-1
        semantic_human = semantic_scores.get("human_similarity", 0)
        semantic_ai = semantic_scores.get("ai_similarity", 0)
        semantic_hybrid = semantic_scores.get("hybrid_similarity", 0)

        # Compute weighted scores
        final_human = (
            keyword_human * self.keyword_weight +
            semantic_human * self.semantic_weight
        )
        final_ai = (
            keyword_ai * self.keyword_weight +
            semantic_ai * self.semantic_weight
        )
        final_hybrid = (
            keyword_hybrid * self.keyword_weight +
            semantic_hybrid * self.semantic_weight
        )

        # Determine classification
        classification, confidence, reasoning = self._determine_classification(
            human_score=final_human,
            ai_score=final_ai,
            hybrid_score=final_hybrid,
            keyword_result=keyword_result,
            semantic_scores=semantic_scores,
        )

        # Combine factors for transparency
        combined_factors = {
            **keyword_factors,
            "semantic_human": semantic_human,
            "semantic_ai": semantic_ai,
            "semantic_hybrid": semantic_hybrid,
            "final_human": final_human,
            "final_ai": final_ai,
            "final_hybrid": final_hybrid,
            "keyword_weight": self.keyword_weight,
            "semantic_weight": self.semantic_weight,
        }

        return ClassificationResult(
            task_id=task_id,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            factors=combined_factors,
            recommended_roles=keyword_result.recommended_roles,
            human_oversight_required=keyword_result.human_oversight_required,
            metadata={
                "engine_version": "2.0-hybrid",
                "classifier_type": "hybrid",
                "weights": {
                    "keyword": self.keyword_weight,
                    "semantic": self.semantic_weight,
                },
            },
        )

    def _determine_classification(
        self,
        human_score: float,
        ai_score: float,
        hybrid_score: float,
        keyword_result: ClassificationResult,
        semantic_scores: Dict[str, float],
    ) -> tuple[RoleType, float, str]:
        """Determine final classification from combined scores."""
        max_score = max(human_score, ai_score, hybrid_score)

        # Check for clear winner
        if human_score == max_score and human_score > ai_score + 0.15:
            confidence = min(0.95, 0.6 + (human_score - ai_score))
            reasoning = self._build_reasoning(
                RoleType.HUMAN_PRIMARY, keyword_result, semantic_scores
            )
            return RoleType.HUMAN_PRIMARY, confidence, reasoning

        if ai_score == max_score and ai_score > human_score + 0.15:
            confidence = min(0.95, 0.6 + (ai_score - human_score))
            reasoning = self._build_reasoning(
                RoleType.AI_PRIMARY, keyword_result, semantic_scores
            )
            return RoleType.AI_PRIMARY, confidence, reasoning

        # Default to hybrid for close scores
        confidence = max(0.5, hybrid_score)
        reasoning = self._build_reasoning(
            RoleType.HYBRID, keyword_result, semantic_scores
        )
        return RoleType.HYBRID, confidence, reasoning

    def _build_reasoning(
        self,
        classification: RoleType,
        keyword_result: ClassificationResult,
        semantic_scores: Dict[str, float],
    ) -> str:
        """Build explanation for the classification."""
        parts = [
            f"Hybrid classification: {classification.value}",
            f"Keyword signal: {keyword_result.classification.value} "
            f"(weight: {self.keyword_weight:.0%})",
        ]

        # Add semantic signal
        max_semantic = max(
            semantic_scores.get("human_similarity", 0),
            semantic_scores.get("ai_similarity", 0),
            semantic_scores.get("hybrid_similarity", 0),
        )
        if semantic_scores.get("human_similarity", 0) == max_semantic:
            semantic_signal = "human"
        elif semantic_scores.get("ai_similarity", 0) == max_semantic:
            semantic_signal = "ai"
        else:
            semantic_signal = "hybrid"

        parts.append(
            f"Semantic signal: {semantic_signal} "
            f"(weight: {self.semantic_weight:.0%}, "
            f"sim: {max_semantic:.2f})"
        )

        return " | ".join(parts)

    def update_weights(
        self, keyword_weight: float, semantic_weight: float
    ) -> None:
        """Update classification weights."""
        total = keyword_weight + semantic_weight
        self.keyword_weight = keyword_weight / total
        self.semantic_weight = semantic_weight / total
        logger.info(
            f"Updated weights: keyword={self.keyword_weight:.2f}, "
            f"semantic={self.semantic_weight:.2f}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier configuration and statistics."""
        return {
            "classifier_type": "hybrid",
            "keyword_weight": self.keyword_weight,
            "semantic_weight": self.semantic_weight,
            "keyword_stats": self.keyword_classifier.get_statistics(),
            "initialized": self._initialized,
        }
