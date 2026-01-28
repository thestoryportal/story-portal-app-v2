"""
L06 Evaluation Layer - Quality Scorer Tests

Tests for multi-dimensional quality scoring service.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from ..services.quality_scorer import QualityScorer
from ..services.cache_manager import CacheManager
from ..models.quality_score import QualityScore, DimensionScore, Assessment


@pytest.fixture
def mock_metrics_engine():
    """Create a mock metrics engine"""
    engine = MagicMock()
    engine.initialize = AsyncMock()
    engine.cleanup = AsyncMock()
    engine.query = AsyncMock(return_value=[])
    return engine


@pytest.fixture
def mock_compliance_validator():
    """Create a mock compliance validator"""
    validator = MagicMock()
    validator.validate_compliance = AsyncMock(return_value=MagicMock(compliant=True))
    return validator


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager"""
    cache = MagicMock(spec=CacheManager)
    cache.get_quality_score = AsyncMock(return_value=None)
    cache.set_quality_score = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def quality_scorer(mock_metrics_engine, mock_compliance_validator, mock_cache_manager):
    """Create QualityScorer with mocked dependencies"""
    return QualityScorer(
        metrics_engine=mock_metrics_engine,
        compliance_validator=mock_compliance_validator,
        cache_manager=mock_cache_manager,
    )


@pytest.fixture
def quality_scorer_no_cache(mock_metrics_engine, mock_compliance_validator):
    """Create QualityScorer without cache"""
    return QualityScorer(
        metrics_engine=mock_metrics_engine,
        compliance_validator=mock_compliance_validator,
        cache_manager=None,
    )


@pytest.fixture
def sample_time_window():
    """Create a sample time window"""
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    return (start, end)


@pytest.fixture
def sample_dimension_score():
    """Create a sample dimension score"""
    return DimensionScore(
        dimension="accuracy",
        score=85.0,
        weight=0.3,
        raw_metrics={"task_success_rate": 0.95},
    )


@pytest.mark.l06
@pytest.mark.unit
class TestQualityScorerInit:
    """Tests for QualityScorer initialization"""

    def test_init_with_defaults(self, mock_metrics_engine, mock_compliance_validator):
        """Test initialization with default weights"""
        scorer = QualityScorer(
            metrics_engine=mock_metrics_engine,
            compliance_validator=mock_compliance_validator,
        )
        assert scorer.weights is not None
        assert abs(sum(scorer.weights.values()) - 1.0) < 0.001
        assert scorer._initialized is False

    def test_init_with_custom_weights(self, mock_metrics_engine, mock_compliance_validator):
        """Test initialization with custom weights"""
        weights = {
            "accuracy": 0.4,
            "latency": 0.2,
            "cost": 0.1,
            "reliability": 0.2,
            "compliance": 0.1,
        }
        scorer = QualityScorer(
            metrics_engine=mock_metrics_engine,
            compliance_validator=mock_compliance_validator,
            weights=weights,
        )
        assert scorer.weights == weights

    def test_init_invalid_weights(self, mock_metrics_engine, mock_compliance_validator):
        """Test initialization with invalid weights raises error"""
        weights = {
            "accuracy": 0.5,
            "latency": 0.3,
            "cost": 0.3,  # Sum > 1.0
            "reliability": 0.2,
            "compliance": 0.1,
        }
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            QualityScorer(
                metrics_engine=mock_metrics_engine,
                compliance_validator=mock_compliance_validator,
                weights=weights,
            )

    def test_init_dimensions_list(self, quality_scorer):
        """Test dimensions list is populated"""
        assert len(quality_scorer.dimensions) == 5
        assert "accuracy" in quality_scorer.dimensions
        assert "latency" in quality_scorer.dimensions

    def test_init_statistics_zeroed(self, quality_scorer):
        """Test initial statistics are zeroed"""
        assert quality_scorer.scores_computed == 0
        assert quality_scorer.cache_hits == 0


@pytest.mark.l06
@pytest.mark.unit
class TestInitializeCleanup:
    """Tests for initialize and cleanup methods"""

    @pytest.mark.asyncio
    async def test_initialize(self, quality_scorer):
        """Test initialization"""
        await quality_scorer.initialize()
        assert quality_scorer._initialized is True
        assert len(quality_scorer.scorers) == 5

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, quality_scorer):
        """Test initialize is idempotent"""
        await quality_scorer.initialize()
        await quality_scorer.initialize()
        assert quality_scorer._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_without_metrics_engine(
        self, mock_compliance_validator, mock_cache_manager
    ):
        """Test initialization creates metrics engine if not provided"""
        scorer = QualityScorer(
            metrics_engine=None,
            compliance_validator=mock_compliance_validator,
            cache_manager=mock_cache_manager,
        )

        with patch("L06_evaluation.services.metrics_engine.MetricsEngine") as MockEngine:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock()
            MockEngine.return_value = mock_instance

            await scorer.initialize()

            assert scorer._initialized is True
            # Note: MetricsEngine is created via local import in initialize()

    @pytest.mark.asyncio
    async def test_cleanup(self, quality_scorer):
        """Test cleanup"""
        await quality_scorer.initialize()
        await quality_scorer.cleanup()
        assert quality_scorer._initialized is False


@pytest.mark.l06
@pytest.mark.unit
class TestComputeScore:
    """Tests for compute_score method"""

    @pytest.mark.asyncio
    async def test_compute_score_success(
        self, quality_scorer, sample_time_window, sample_dimension_score
    ):
        """Test successful score computation"""
        await quality_scorer.initialize()

        # Mock all scorers to return sample scores
        for name, scorer in quality_scorer.scorers.items():
            mock_score = DimensionScore(
                dimension=name,
                score=80.0,
                weight=quality_scorer.weights[name],
                raw_metrics={},
            )
            scorer.compute_score = AsyncMock(return_value=mock_score)

        result = await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert isinstance(result, QualityScore)
        assert result.agent_id == "agent-001"
        assert result.overall_score == 80.0  # All dimensions at 80
        assert quality_scorer.scores_computed == 1

    @pytest.mark.asyncio
    async def test_compute_score_cache_hit(
        self, quality_scorer, mock_cache_manager, sample_time_window
    ):
        """Test score computation with cache hit"""
        await quality_scorer.initialize()

        cached_score = {
            "score_id": "qs-cached",
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
            "timestamp": sample_time_window[0].isoformat(),
            "overall_score": 90.0,
            "assessment": "Good",  # Must match Assessment enum values
            "dimensions": {},
            "data_completeness": 1.0,
            "cached": False,
        }
        mock_cache_manager.get_quality_score.return_value = cached_score

        result = await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert result.cached is True
        assert quality_scorer.cache_hits == 1

    @pytest.mark.asyncio
    async def test_compute_score_dimension_failure(
        self, quality_scorer, sample_time_window
    ):
        """Test score computation handles dimension failures"""
        await quality_scorer.initialize()

        # Make one scorer fail, others succeed
        for i, (name, scorer) in enumerate(quality_scorer.scorers.items()):
            if i == 0:
                scorer.compute_score = AsyncMock(side_effect=Exception("Scorer error"))
            else:
                mock_score = DimensionScore(
                    dimension=name,
                    score=80.0,
                    weight=quality_scorer.weights[name],
                    raw_metrics={},
                )
                scorer.compute_score = AsyncMock(return_value=mock_score)

        result = await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        # Should still return a score, with default for failed dimension
        assert isinstance(result, QualityScore)
        assert result.data_completeness < 1.0

    @pytest.mark.asyncio
    async def test_compute_score_no_cache(
        self, quality_scorer_no_cache, sample_time_window, sample_dimension_score
    ):
        """Test score computation without cache"""
        await quality_scorer_no_cache.initialize()

        for name, scorer in quality_scorer_no_cache.scorers.items():
            mock_score = DimensionScore(
                dimension=name,
                score=85.0,
                weight=quality_scorer_no_cache.weights[name],
                raw_metrics={},
            )
            scorer.compute_score = AsyncMock(return_value=mock_score)

        result = await quality_scorer_no_cache.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert isinstance(result, QualityScore)
        assert result.cached is False


@pytest.mark.l06
@pytest.mark.unit
class TestGetDimensionScore:
    """Tests for get_dimension_score method"""

    @pytest.mark.asyncio
    async def test_get_dimension_score_success(
        self, quality_scorer, sample_time_window, sample_dimension_score
    ):
        """Test getting single dimension score"""
        await quality_scorer.initialize()

        quality_scorer.scorers["accuracy"].compute_score = AsyncMock(
            return_value=sample_dimension_score
        )

        result = await quality_scorer.get_dimension_score(
            dimension="accuracy",
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert result is not None
        assert result.dimension == "accuracy"
        assert result.score == 85.0

    @pytest.mark.asyncio
    async def test_get_dimension_score_invalid_dimension(
        self, quality_scorer, sample_time_window
    ):
        """Test getting score for invalid dimension"""
        await quality_scorer.initialize()

        result = await quality_scorer.get_dimension_score(
            dimension="invalid_dimension",
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_dimension_score_exception(
        self, quality_scorer, sample_time_window
    ):
        """Test get dimension score handles exceptions"""
        await quality_scorer.initialize()

        quality_scorer.scorers["accuracy"].compute_score = AsyncMock(
            side_effect=Exception("Scorer error")
        )

        result = await quality_scorer.get_dimension_score(
            dimension="accuracy",
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        assert result is None


@pytest.mark.l06
@pytest.mark.unit
class TestUpdateWeights:
    """Tests for update_weights method"""

    @pytest.mark.asyncio
    async def test_update_weights_valid(self, quality_scorer):
        """Test updating weights with valid values"""
        await quality_scorer.initialize()

        new_weights = {
            "accuracy": 0.4,
            "latency": 0.2,
            "cost": 0.1,
            "reliability": 0.2,
            "compliance": 0.1,
        }

        quality_scorer.update_weights(new_weights)

        assert quality_scorer.weights["accuracy"] == 0.4
        assert quality_scorer.scorers["accuracy"].weight == 0.4

    def test_update_weights_invalid(self, quality_scorer):
        """Test updating weights with invalid values"""
        invalid_weights = {
            "accuracy": 0.5,
            "latency": 0.5,
            "cost": 0.5,  # Sum > 1.0
            "reliability": 0.2,
            "compliance": 0.1,
        }

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            quality_scorer.update_weights(invalid_weights)


@pytest.mark.l06
@pytest.mark.unit
class TestGetWeights:
    """Tests for get_weights method"""

    def test_get_weights(self, quality_scorer):
        """Test getting current weights"""
        weights = quality_scorer.get_weights()

        assert isinstance(weights, dict)
        assert abs(sum(weights.values()) - 1.0) < 0.001
        # Verify it's a copy
        weights["accuracy"] = 0.99
        assert quality_scorer.weights["accuracy"] != 0.99


@pytest.mark.l06
@pytest.mark.unit
class TestStatistics:
    """Tests for statistics methods"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, quality_scorer, sample_time_window, sample_dimension_score):
        """Test getting statistics"""
        await quality_scorer.initialize()

        # Mock scorers
        for name, scorer in quality_scorer.scorers.items():
            mock_score = DimensionScore(
                dimension=name,
                score=80.0,
                weight=quality_scorer.weights[name],
                raw_metrics={},
            )
            scorer.compute_score = AsyncMock(return_value=mock_score)

        # Compute some scores
        await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        stats = quality_scorer.get_statistics()

        assert stats["scores_computed"] == 1
        assert stats["cache_hits"] == 0
        assert stats["cache_hit_rate"] == 0.0
        assert "weights" in stats

    @pytest.mark.asyncio
    async def test_statistics_with_cache_hits(
        self, quality_scorer, mock_cache_manager, sample_time_window
    ):
        """Test statistics include cache hits"""
        await quality_scorer.initialize()

        cached_score = {
            "score_id": "qs-cached",
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
            "timestamp": sample_time_window[0].isoformat(),
            "overall_score": 90.0,
            "assessment": "Good",  # Must match Assessment enum values
            "dimensions": {},
            "data_completeness": 1.0,
            "cached": False,
        }
        mock_cache_manager.get_quality_score.return_value = cached_score

        await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=sample_time_window,
        )

        stats = quality_scorer.get_statistics()
        assert stats["cache_hits"] == 1
        assert stats["cache_hit_rate"] == 1.0

    def test_reset_statistics(self, quality_scorer):
        """Test resetting statistics"""
        quality_scorer.scores_computed = 10
        quality_scorer.cache_hits = 5

        quality_scorer.reset_statistics()

        assert quality_scorer.scores_computed == 0
        assert quality_scorer.cache_hits == 0


@pytest.mark.l06
@pytest.mark.unit
class TestCleanupEdgeCases:
    """Tests for cleanup edge cases"""

    @pytest.mark.asyncio
    async def test_cleanup_with_metrics_engine_when_not_initialized(
        self, mock_metrics_engine, mock_cache_manager
    ):
        """Test cleanup calls metrics_engine.cleanup when not initialized (lines 102-103)"""
        # Create scorer with metrics engine but DON'T initialize it
        scorer = QualityScorer(
            metrics_engine=mock_metrics_engine,
            cache_manager=mock_cache_manager,
        )

        # Verify not initialized
        assert scorer._initialized is False

        # Call cleanup - should call metrics_engine.cleanup since not initialized
        await scorer.cleanup()

        # The cleanup method checks: if self.metrics_engine and not self._initialized
        # Since _initialized is False and metrics_engine exists, it should call cleanup
        mock_metrics_engine.cleanup.assert_called_once()


@pytest.mark.l06
@pytest.mark.unit
class TestComputeScoreExceptionHandling:
    """Tests for exception handling in compute_score"""

    @pytest.mark.asyncio
    async def test_compute_score_exception(
        self, quality_scorer, sample_time_window
    ):
        """Test compute_score exception handling (lines 194-196)"""
        await quality_scorer.initialize()

        # Mock all scorers to return valid scores first
        for name, scorer in quality_scorer.scorers.items():
            mock_score = DimensionScore(
                dimension=name,
                score=80.0,
                weight=quality_scorer.weights[name],
                raw_metrics={},
            )
            scorer.compute_score = AsyncMock(return_value=mock_score)

        # Make cache.set_quality_score raise an exception OUTSIDE the dimension loop
        # This will trigger the outer exception handler at lines 194-196
        quality_scorer.cache.set_quality_score = AsyncMock(
            side_effect=RuntimeError("Cache write failed unexpectedly")
        )

        # Should raise Exception with wrapped error
        with pytest.raises(Exception, match="Quality score calculation error"):
            await quality_scorer.compute_score(
                agent_id="agent-001",
                tenant_id="tenant-001",
                time_window=sample_time_window,
            )
