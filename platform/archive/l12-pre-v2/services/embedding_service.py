"""Embedding service for L12 semantic matching.

This module provides embedding generation for semantic similarity matching
using Ollama's embedding API.
"""

import asyncio
import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Simple embedding service for semantic matching in L12."""

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        timeout: float = 10.0,
    ):
        """Initialize embedding service.

        Args:
            ollama_base_url: Base URL for Ollama API
            embedding_model: Model name for embeddings
            timeout: Request timeout in seconds
        """
        self.ollama_base_url = ollama_base_url
        self.embedding_model = embedding_model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"EmbeddingService initialized: model={embedding_model}, "
            f"url={ollama_base_url}"
        )

    async def start(self):
        """Start the embedding service."""
        if not self._client:
            self._client = httpx.AsyncClient()
            logger.info("EmbeddingService started")

    async def stop(self):
        """Stop the embedding service."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("EmbeddingService stopped")

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats) or None if failed
        """
        if not self._client:
            await self.start()

        try:
            response = await self._client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text,
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding:
                    logger.debug(f"Generated embedding: dim={len(embedding)}")
                    return embedding
                else:
                    logger.warning("No embedding in response")
                    return None
            else:
                logger.warning(
                    f"Embedding generation failed: status={response.status_code}"
                )
                return None

        except httpx.TimeoutException:
            logger.warning("Embedding generation timeout")
            return None
        except httpx.ConnectError:
            logger.warning(f"Cannot connect to Ollama at {self.ollama_base_url}")
            return None
        except Exception as e:
            logger.error(f"Embedding generation error: {e}", exc_info=True)
            return None

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0.0-1.0)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (mag1 * mag2)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))
