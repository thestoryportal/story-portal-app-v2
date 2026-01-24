"""
Semantic Classifier for L13 Role Management Layer.

Uses Ollama embeddings for semantic task classification, comparing task
descriptions against reference embeddings for HUMAN/AI/HYBRID categories.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Tuple
import httpx
import asyncio

from ..models import (
    RoleType,
    TaskRequirements,
)

logger = logging.getLogger(__name__)


class SemanticClassifier:
    """
    Semantic classifier using Ollama embeddings.

    Compares task description embeddings against reference embeddings
    for each role type to determine semantic similarity.
    """

    # Reference descriptions for each classification category
    HUMAN_REFERENCE_TEXTS: List[str] = [
        "This task requires strategic decision making and approval authority.",
        "Sensitive confidential information handling with legal and compliance oversight.",
        "Creative design work requiring human innovation and brainstorming.",
        "Interpersonal communication, negotiation, and stakeholder management.",
        "Ethical judgment and risk assessment with potential consequences.",
        "Personnel management, interviews, mentoring, and counseling.",
        "Strategic planning, vision setting, and organizational leadership.",
    ]

    AI_REFERENCE_TEXTS: List[str] = [
        "Data processing, analysis, and transformation with statistical computation.",
        "Automated content generation, synthesis, and document drafting.",
        "Repetitive batch processing and scheduled automation tasks.",
        "Classification, categorization, tagging, and sorting operations.",
        "Text summarization, condensation, and information extraction.",
        "Search, query, retrieval, and lookup operations across databases.",
        "Monitoring, tracking, alerting, and anomaly detection.",
        "Format conversion, translation, and standardization tasks.",
    ]

    HYBRID_REFERENCE_TEXTS: List[str] = [
        "Analysis requiring both automated processing and human interpretation.",
        "Content creation with AI assistance reviewed by human experts.",
        "Complex problem solving combining AI insights with human judgment.",
        "Quality assurance with automated checks and manual verification.",
        "Research tasks with AI-powered search and human synthesis.",
    ]

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        cache_embeddings: bool = True,
    ):
        """
        Initialize the semantic classifier.

        Args:
            ollama_base_url: Ollama API endpoint
            embedding_model: Model name for embeddings
            cache_embeddings: Whether to cache reference embeddings
        """
        self.ollama_base_url = ollama_base_url or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.embedding_model = embedding_model or os.environ.get(
            "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
        )
        self.cache_embeddings = cache_embeddings
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Cached reference embeddings
        self._human_embeddings: Optional[List[List[float]]] = None
        self._ai_embeddings: Optional[List[List[float]]] = None
        self._hybrid_embeddings: Optional[List[List[float]]] = None
        self._initialized: bool = False

        logger.info(
            f"SemanticClassifier initialized: "
            f"model={self.embedding_model}, base_url={self.ollama_base_url}"
        )

    async def initialize(self) -> None:
        """Initialize by pre-computing reference embeddings."""
        if self._initialized:
            return

        try:
            # Compute reference embeddings in parallel
            human_task = self._batch_embed(self.HUMAN_REFERENCE_TEXTS)
            ai_task = self._batch_embed(self.AI_REFERENCE_TEXTS)
            hybrid_task = self._batch_embed(self.HYBRID_REFERENCE_TEXTS)

            self._human_embeddings, self._ai_embeddings, self._hybrid_embeddings = (
                await asyncio.gather(human_task, ai_task, hybrid_task)
            )

            self._initialized = True
            logger.info("SemanticClassifier reference embeddings computed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SemanticClassifier: {e}")
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            response = await self.http_client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self._generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _average_similarity(
        self, embedding: List[float], reference_embeddings: List[List[float]]
    ) -> float:
        """Compute average similarity to reference embeddings."""
        if not reference_embeddings:
            return 0.0

        similarities = [
            self._cosine_similarity(embedding, ref) for ref in reference_embeddings
        ]
        return sum(similarities) / len(similarities)

    async def classify(
        self, requirements: TaskRequirements
    ) -> Tuple[RoleType, float, Dict[str, float]]:
        """
        Classify a task using semantic similarity.

        Args:
            requirements: Task requirements with description

        Returns:
            Tuple of (classification, confidence, similarity_scores)
        """
        if not self._initialized:
            await self.initialize()

        # Generate embedding for task description
        task_embedding = await self._generate_embedding(requirements.task_description)

        # Compute similarity to each category
        human_sim = self._average_similarity(task_embedding, self._human_embeddings or [])
        ai_sim = self._average_similarity(task_embedding, self._ai_embeddings or [])
        hybrid_sim = self._average_similarity(task_embedding, self._hybrid_embeddings or [])

        scores = {
            "human_similarity": human_sim,
            "ai_similarity": ai_sim,
            "hybrid_similarity": hybrid_sim,
        }

        # Determine classification based on highest similarity
        max_sim = max(human_sim, ai_sim, hybrid_sim)

        if max_sim < 0.3:
            # Low similarity to all - default to hybrid
            return RoleType.HYBRID, 0.5, scores

        if human_sim == max_sim:
            confidence = min(0.95, 0.5 + (human_sim - max(ai_sim, hybrid_sim)))
            return RoleType.HUMAN_PRIMARY, confidence, scores

        if ai_sim == max_sim:
            confidence = min(0.95, 0.5 + (ai_sim - max(human_sim, hybrid_sim)))
            return RoleType.AI_PRIMARY, confidence, scores

        # Hybrid is highest
        confidence = min(0.95, 0.5 + (hybrid_sim - max(human_sim, ai_sim)))
        return RoleType.HYBRID, confidence, scores

    async def get_semantic_scores(
        self, requirements: TaskRequirements
    ) -> Dict[str, float]:
        """
        Get semantic similarity scores without classification.

        Useful for hybrid classifiers that combine multiple signals.
        """
        if not self._initialized:
            await self.initialize()

        task_embedding = await self._generate_embedding(requirements.task_description)

        return {
            "human_similarity": self._average_similarity(
                task_embedding, self._human_embeddings or []
            ),
            "ai_similarity": self._average_similarity(
                task_embedding, self._ai_embeddings or []
            ),
            "hybrid_similarity": self._average_similarity(
                task_embedding, self._hybrid_embeddings or []
            ),
        }
