"""
Test Semantic Classifier

Tests for the Ollama-based semantic classification engine.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ..services import SemanticClassifier
from ..models import RoleType, TaskRequirements


class TestSemanticClassifierInit:
    """Test SemanticClassifier initialization."""

    def test_default_configuration(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OLLAMA_BASE_URL", None)
            os.environ.pop("OLLAMA_EMBEDDING_MODEL", None)

            classifier = SemanticClassifier()

            assert classifier.ollama_base_url == "http://localhost:11434"
            assert classifier.embedding_model == "nomic-embed-text"
            assert classifier.cache_embeddings is True

    def test_env_configuration(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            "OLLAMA_BASE_URL": "http://custom:11434",
            "OLLAMA_EMBEDDING_MODEL": "custom-model"
        }):
            classifier = SemanticClassifier()

            assert classifier.ollama_base_url == "http://custom:11434"
            assert classifier.embedding_model == "custom-model"

    def test_constructor_overrides_env(self):
        """Test that constructor params override env vars."""
        with patch.dict(os.environ, {
            "OLLAMA_BASE_URL": "http://env:11434",
            "OLLAMA_EMBEDDING_MODEL": "env-model"
        }):
            classifier = SemanticClassifier(
                ollama_base_url="http://param:11434",
                embedding_model="param-model"
            )

            assert classifier.ollama_base_url == "http://param:11434"
            assert classifier.embedding_model == "param-model"

    def test_reference_texts_defined(self):
        """Test that reference texts are properly defined."""
        assert len(SemanticClassifier.HUMAN_REFERENCE_TEXTS) > 0
        assert len(SemanticClassifier.AI_REFERENCE_TEXTS) > 0
        assert len(SemanticClassifier.HYBRID_REFERENCE_TEXTS) > 0


class TestSemanticClassifierCosine:
    """Test cosine similarity calculation."""

    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical vectors."""
        classifier = SemanticClassifier()

        vec = [1.0, 0.0, 0.0, 1.0]
        similarity = classifier._cosine_similarity(vec, vec)

        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors."""
        classifier = SemanticClassifier()

        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0, 0.0]
        similarity = classifier._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0, abs=0.001)

    def test_cosine_similarity_opposite(self):
        """Test cosine similarity of opposite vectors."""
        classifier = SemanticClassifier()

        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = classifier._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0, abs=0.001)

    def test_cosine_similarity_empty(self):
        """Test cosine similarity with empty vectors."""
        classifier = SemanticClassifier()

        similarity = classifier._cosine_similarity([], [])
        assert similarity == 0.0

    def test_cosine_similarity_zero_norm(self):
        """Test cosine similarity with zero vector."""
        classifier = SemanticClassifier()

        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = classifier._cosine_similarity(vec1, vec2)

        assert similarity == 0.0


class TestSemanticClassifierAverage:
    """Test average similarity calculation."""

    def test_average_similarity(self):
        """Test average similarity across reference embeddings."""
        classifier = SemanticClassifier()

        query_embedding = [1.0, 0.0, 0.0, 0.0]
        reference_embeddings = [
            [1.0, 0.0, 0.0, 0.0],  # sim = 1.0
            [0.0, 1.0, 0.0, 0.0],  # sim = 0.0
        ]

        avg_sim = classifier._average_similarity(query_embedding, reference_embeddings)

        assert avg_sim == pytest.approx(0.5, abs=0.001)

    def test_average_similarity_empty_refs(self):
        """Test average similarity with no references."""
        classifier = SemanticClassifier()

        query_embedding = [1.0, 0.0, 0.0, 0.0]
        avg_sim = classifier._average_similarity(query_embedding, [])

        assert avg_sim == 0.0


@pytest.mark.asyncio
class TestSemanticClassifierClassification:
    """Test semantic classification functionality."""

    async def test_classify_returns_role_type(self, simple_task_requirements):
        """Test that classify returns a valid RoleType."""
        classifier = SemanticClassifier()

        # Mock the embedding generation and initialization
        classifier._initialized = True
        classifier._human_embeddings = [[0.1] * 768] * 3
        classifier._ai_embeddings = [[0.2] * 768] * 3
        classifier._hybrid_embeddings = [[0.15] * 768] * 3

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = MagicMock()

        classifier.http_client = AsyncMock()
        classifier.http_client.post = AsyncMock(return_value=mock_response)

        role_type, confidence, scores = await classifier.classify(simple_task_requirements)

        assert isinstance(role_type, RoleType)
        assert 0 <= confidence <= 1
        assert "human_similarity" in scores
        assert "ai_similarity" in scores
        assert "hybrid_similarity" in scores

    async def test_get_semantic_scores(self, simple_task_requirements):
        """Test getting semantic scores without classification."""
        classifier = SemanticClassifier()

        # Mock initialization
        classifier._initialized = True
        classifier._human_embeddings = [[0.1] * 768] * 3
        classifier._ai_embeddings = [[0.2] * 768] * 3
        classifier._hybrid_embeddings = [[0.15] * 768] * 3

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = MagicMock()

        classifier.http_client = AsyncMock()
        classifier.http_client.post = AsyncMock(return_value=mock_response)

        scores = await classifier.get_semantic_scores(simple_task_requirements)

        assert "human_similarity" in scores
        assert "ai_similarity" in scores
        assert "hybrid_similarity" in scores
        assert all(0 <= v <= 1 for v in scores.values())

    async def test_low_similarity_defaults_to_hybrid(self):
        """Test that low similarity to all categories defaults to HYBRID."""
        classifier = SemanticClassifier()

        # Mock with very different embeddings (low similarity)
        classifier._initialized = True
        classifier._human_embeddings = [[1.0, 0.0, 0.0] + [0.0] * 765]
        classifier._ai_embeddings = [[0.0, 1.0, 0.0] + [0.0] * 765]
        classifier._hybrid_embeddings = [[0.0, 0.0, 1.0] + [0.0] * 765]

        # Mock with orthogonal query embedding
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.0, 0.0, 0.0, 1.0] + [0.0] * 764}
        mock_response.raise_for_status = MagicMock()

        classifier.http_client = AsyncMock()
        classifier.http_client.post = AsyncMock(return_value=mock_response)

        requirements = TaskRequirements(
            task_description="Something completely unrelated",
            required_skills=[],
            keywords=[],
            complexity="medium",
            urgency="normal",
        )

        role_type, confidence, _ = await classifier.classify(requirements)

        # Low similarity should default to HYBRID with low confidence
        assert role_type == RoleType.HYBRID
        assert confidence <= 0.5


@pytest.mark.asyncio
class TestSemanticClassifierLifecycle:
    """Test classifier lifecycle (init/close)."""

    async def test_close(self):
        """Test closing the classifier."""
        classifier = SemanticClassifier()
        classifier.http_client = AsyncMock()

        await classifier.close()

        classifier.http_client.aclose.assert_called_once()
