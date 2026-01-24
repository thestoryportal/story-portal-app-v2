"""
Test Hybrid Classifier

Tests for the combined keyword + semantic classification engine.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ..services import HybridClassifier
from ..models import RoleType, TaskRequirements


class TestHybridClassifierInit:
    """Test HybridClassifier initialization."""

    def test_default_weights(self):
        """Test default weight values."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("L13_KEYWORD_WEIGHT", None)
            os.environ.pop("L13_SEMANTIC_WEIGHT", None)

            classifier = HybridClassifier()

            assert classifier.keyword_weight == pytest.approx(0.8, abs=0.01)
            assert classifier.semantic_weight == pytest.approx(0.2, abs=0.01)

    def test_env_weights(self):
        """Test weights from environment variables."""
        with patch.dict(os.environ, {
            "L13_KEYWORD_WEIGHT": "0.7",
            "L13_SEMANTIC_WEIGHT": "0.3"
        }):
            classifier = HybridClassifier()

            assert classifier.keyword_weight == pytest.approx(0.7, abs=0.01)
            assert classifier.semantic_weight == pytest.approx(0.3, abs=0.01)

    def test_constructor_weights(self):
        """Test weights from constructor parameters."""
        classifier = HybridClassifier(
            keyword_weight=0.6,
            semantic_weight=0.4
        )

        assert classifier.keyword_weight == pytest.approx(0.6, abs=0.01)
        assert classifier.semantic_weight == pytest.approx(0.4, abs=0.01)

    def test_weight_normalization(self):
        """Test that weights are normalized to sum to 1.0."""
        classifier = HybridClassifier(
            keyword_weight=3.0,
            semantic_weight=1.0
        )

        # 3.0 + 1.0 = 4.0, so 3/4 = 0.75 and 1/4 = 0.25
        assert classifier.keyword_weight == pytest.approx(0.75, abs=0.01)
        assert classifier.semantic_weight == pytest.approx(0.25, abs=0.01)
        assert classifier.keyword_weight + classifier.semantic_weight == pytest.approx(1.0, abs=0.01)

    def test_thresholds_passed_to_keyword_classifier(self):
        """Test that thresholds are passed to keyword classifier."""
        classifier = HybridClassifier(
            human_threshold=0.7,
            ai_threshold=0.5
        )

        assert classifier.keyword_classifier.human_threshold == 0.7
        assert classifier.keyword_classifier.ai_threshold == 0.5


@pytest.mark.asyncio
class TestHybridClassifierClassification:
    """Test hybrid classification functionality."""

    @pytest.fixture
    def mock_hybrid_classifier(self):
        """Create a hybrid classifier with mocked semantic classifier."""
        classifier = HybridClassifier()

        # Mock semantic classifier
        classifier.semantic_classifier._initialized = True
        classifier.semantic_classifier._human_embeddings = [[0.1] * 768] * 3
        classifier.semantic_classifier._ai_embeddings = [[0.2] * 768] * 3
        classifier.semantic_classifier._hybrid_embeddings = [[0.15] * 768] * 3

        # Mock HTTP client for semantic classifier
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = MagicMock()

        classifier.semantic_classifier.http_client = AsyncMock()
        classifier.semantic_classifier.http_client.post = AsyncMock(return_value=mock_response)

        classifier._initialized = True

        return classifier

    async def test_classify_returns_classification_result(
        self, mock_hybrid_classifier, simple_task_requirements
    ):
        """Test that classify_task returns a ClassificationResult."""
        result = await mock_hybrid_classifier.classify_task(
            task_id="test-task",
            requirements=simple_task_requirements
        )

        assert result.task_id == "test-task"
        assert isinstance(result.classification, RoleType)
        assert 0 <= result.confidence <= 1
        assert result.metadata.get("classifier_type") == "hybrid"

    async def test_combined_factors_in_result(
        self, mock_hybrid_classifier, simple_task_requirements
    ):
        """Test that combined factors are included in result."""
        result = await mock_hybrid_classifier.classify_task(
            task_id="test-task",
            requirements=simple_task_requirements
        )

        # Should have both keyword and semantic factors
        assert "semantic_human" in result.factors
        assert "semantic_ai" in result.factors
        assert "semantic_hybrid" in result.factors
        assert "final_human" in result.factors
        assert "final_ai" in result.factors
        assert "keyword_weight" in result.factors
        assert "semantic_weight" in result.factors

    async def test_human_task_weighted_classification(
        self, mock_hybrid_classifier, human_task_requirements
    ):
        """Test that human-oriented tasks favor human classification."""
        # Override semantic scores to favor human
        async def mock_get_scores(*args, **kwargs):
            return {
                "human_similarity": 0.9,
                "ai_similarity": 0.3,
                "hybrid_similarity": 0.5,
            }

        mock_hybrid_classifier.semantic_classifier.get_semantic_scores = mock_get_scores

        result = await mock_hybrid_classifier.classify_task(
            task_id="test-task",
            requirements=human_task_requirements
        )

        # With both keyword and semantic favoring human, final_human should be highest
        assert result.factors.get("final_human", 0) >= result.factors.get("final_ai", 0)
        # Should be either HUMAN_PRIMARY or HYBRID
        assert result.classification in [RoleType.HUMAN_PRIMARY, RoleType.HYBRID]

    async def test_ai_task_weighted_classification(
        self, mock_hybrid_classifier, ai_task_requirements
    ):
        """Test that AI-oriented tasks favor AI classification."""
        # Override semantic scores to favor AI
        async def mock_get_scores(*args, **kwargs):
            return {
                "human_similarity": 0.2,
                "ai_similarity": 0.9,
                "hybrid_similarity": 0.4,
            }

        mock_hybrid_classifier.semantic_classifier.get_semantic_scores = mock_get_scores

        result = await mock_hybrid_classifier.classify_task(
            task_id="test-task",
            requirements=ai_task_requirements
        )

        # With both keyword and semantic favoring AI, final_ai should be highest
        assert result.factors.get("final_ai", 0) >= result.factors.get("final_human", 0)
        # Should be either AI_PRIMARY or HYBRID
        assert result.classification in [RoleType.AI_PRIMARY, RoleType.HYBRID]

    async def test_metadata_includes_weights(
        self, mock_hybrid_classifier, simple_task_requirements
    ):
        """Test that result metadata includes weight information."""
        result = await mock_hybrid_classifier.classify_task(
            task_id="test-task",
            requirements=simple_task_requirements
        )

        assert "weights" in result.metadata
        assert result.metadata["weights"]["keyword"] == pytest.approx(0.8, abs=0.01)
        assert result.metadata["weights"]["semantic"] == pytest.approx(0.2, abs=0.01)


class TestHybridClassifierWeightUpdate:
    """Test weight update functionality."""

    def test_update_weights(self):
        """Test updating classification weights."""
        classifier = HybridClassifier(
            keyword_weight=0.8,
            semantic_weight=0.2
        )

        classifier.update_weights(0.5, 0.5)

        assert classifier.keyword_weight == pytest.approx(0.5, abs=0.01)
        assert classifier.semantic_weight == pytest.approx(0.5, abs=0.01)

    def test_update_weights_normalizes(self):
        """Test that weight updates are normalized."""
        classifier = HybridClassifier()

        classifier.update_weights(2.0, 2.0)

        assert classifier.keyword_weight == pytest.approx(0.5, abs=0.01)
        assert classifier.semantic_weight == pytest.approx(0.5, abs=0.01)


class TestHybridClassifierStatistics:
    """Test statistics reporting."""

    def test_get_statistics(self):
        """Test statistics retrieval."""
        classifier = HybridClassifier(
            keyword_weight=0.75,
            semantic_weight=0.25
        )

        stats = classifier.get_statistics()

        assert stats["classifier_type"] == "hybrid"
        assert stats["keyword_weight"] == pytest.approx(0.75, abs=0.01)
        assert stats["semantic_weight"] == pytest.approx(0.25, abs=0.01)
        assert "keyword_stats" in stats
        assert stats["initialized"] is False  # Not initialized yet


@pytest.mark.asyncio
class TestHybridClassifierLifecycle:
    """Test classifier lifecycle."""

    async def test_initialize_initializes_semantic(self):
        """Test that initialize sets up semantic classifier."""
        classifier = HybridClassifier()

        # Mock semantic classifier initialize
        classifier.semantic_classifier.initialize = AsyncMock()

        await classifier.initialize()

        classifier.semantic_classifier.initialize.assert_called_once()
        assert classifier._initialized is True

    async def test_close_closes_semantic(self):
        """Test that close cleans up semantic classifier."""
        classifier = HybridClassifier()
        classifier.semantic_classifier.close = AsyncMock()

        await classifier.close()

        classifier.semantic_classifier.close.assert_called_once()
