"""
L06 Evaluation Layer - Anomaly Detector Tests

Tests for z-score based statistical anomaly detection.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock

from ..services.anomaly_detector import AnomalyDetector
from ..services.cache_manager import CacheManager
from ..models.anomaly import Anomaly, AnomalySeverity, Baseline
from ..models.quality_score import QualityScore, Assessment


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager"""
    cache = MagicMock(spec=CacheManager)
    cache.get_baseline = AsyncMock(return_value=None)
    cache.set_baseline = AsyncMock(return_value=None)
    cache.delete = AsyncMock(return_value=None)
    cache.clear = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def anomaly_detector(mock_cache_manager):
    """Create AnomalyDetector with mocked cache"""
    return AnomalyDetector(
        cache_manager=mock_cache_manager,
        deviation_threshold=3.0,
        baseline_window_hours=24,
        cold_start_samples=10,  # Lower for testing
    )


@pytest.fixture
def anomaly_detector_no_cache():
    """Create AnomalyDetector without cache"""
    return AnomalyDetector(
        cache_manager=None,
        deviation_threshold=3.0,
        baseline_window_hours=24,
        cold_start_samples=10,
    )


@pytest.fixture
def sample_quality_score():
    """Create a sample quality score"""
    return QualityScore(
        score_id="qs-001",
        agent_id="agent-001",
        tenant_id="tenant-001",
        timestamp=datetime.now(UTC),
        overall_score=85.0,
        assessment=Assessment.GOOD,
        dimensions={},
    )


@pytest.fixture
def established_baseline():
    """Create an established baseline"""
    return Baseline(
        metric_name="quality_score:agent-001",
        mean=80.0,
        stddev=5.0,
        sample_count=100,  # Above cold_start threshold
        last_updated=datetime.now(UTC),
        window_hours=24,
    )


@pytest.mark.l06
@pytest.mark.unit
class TestAnomalyDetectorInit:
    """Tests for AnomalyDetector initialization"""

    def test_init_with_cache(self, anomaly_detector, mock_cache_manager):
        """Test initialization with cache manager"""
        assert anomaly_detector.cache is mock_cache_manager
        assert anomaly_detector.threshold == 3.0
        assert anomaly_detector.baseline_window_hours == 24
        assert anomaly_detector.cold_start_samples == 10

    def test_init_without_cache(self, anomaly_detector_no_cache):
        """Test initialization without cache"""
        assert anomaly_detector_no_cache.cache is None

    def test_init_custom_threshold(self, mock_cache_manager):
        """Test initialization with custom threshold"""
        detector = AnomalyDetector(
            cache_manager=mock_cache_manager,
            deviation_threshold=2.0,
        )
        assert detector.threshold == 2.0

    def test_initial_statistics(self, anomaly_detector):
        """Test initial statistics are zeroed"""
        assert anomaly_detector.anomalies_detected == 0
        assert anomaly_detector.baselines_trained == 0


@pytest.mark.l06
@pytest.mark.unit
class TestInitializeCleanup:
    """Tests for initialize and cleanup methods"""

    @pytest.mark.asyncio
    async def test_initialize(self, anomaly_detector):
        """Test detector initialization"""
        await anomaly_detector.initialize()
        assert anomaly_detector._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, anomaly_detector):
        """Test initialize is idempotent"""
        await anomaly_detector.initialize()
        await anomaly_detector.initialize()
        assert anomaly_detector._initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self, anomaly_detector):
        """Test detector cleanup"""
        await anomaly_detector.initialize()
        await anomaly_detector.cleanup()

        assert anomaly_detector._initialized is False
        assert len(anomaly_detector._baselines) == 0


@pytest.mark.l06
@pytest.mark.unit
class TestDetect:
    """Tests for anomaly detection"""

    @pytest.mark.asyncio
    async def test_detect_cold_start(
        self, anomaly_detector, sample_quality_score
    ):
        """Test detection during cold-start period"""
        # No baseline exists, should return None and update baseline
        anomaly = await anomaly_detector.detect(sample_quality_score)

        assert anomaly is None
        assert anomaly_detector.baselines_trained == 1

    @pytest.mark.asyncio
    async def test_detect_no_anomaly(
        self, anomaly_detector, sample_quality_score, established_baseline
    ):
        """Test detection when score is within normal range"""
        # Pre-populate baseline
        metric_name = f"quality_score:{sample_quality_score.agent_id}"
        anomaly_detector._baselines[metric_name] = established_baseline

        # Score of 85 is within 3 stddev of mean 80 (threshold = 80 ± 15)
        anomaly = await anomaly_detector.detect(sample_quality_score)

        assert anomaly is None

    @pytest.mark.asyncio
    async def test_detect_anomaly(
        self, anomaly_detector, established_baseline
    ):
        """Test detection of actual anomaly"""
        # Pre-populate baseline
        metric_name = "quality_score:agent-001"
        anomaly_detector._baselines[metric_name] = established_baseline

        # Create score far outside normal range
        anomalous_score = QualityScore(
            score_id="qs-anomaly",
            agent_id="agent-001",
            tenant_id="tenant-001",
            timestamp=datetime.now(UTC),
            overall_score=10.0,  # Way below mean of 80
            assessment=Assessment.CRITICAL,
            dimensions={},
        )

        anomaly = await anomaly_detector.detect(anomalous_score)

        assert anomaly is not None
        assert anomaly.current_value == 10.0
        assert anomaly.baseline_value == 80.0
        assert anomaly_detector.anomalies_detected == 1


@pytest.mark.l06
@pytest.mark.unit
class TestBaselineManagement:
    """Tests for baseline management"""

    @pytest.mark.asyncio
    async def test_get_baseline_from_memory(
        self, anomaly_detector, established_baseline
    ):
        """Test getting baseline from memory"""
        metric_name = "quality_score:agent-001"
        anomaly_detector._baselines[metric_name] = established_baseline

        baseline = await anomaly_detector._get_baseline(metric_name)

        assert baseline is established_baseline

    @pytest.mark.asyncio
    async def test_get_baseline_from_cache(
        self, anomaly_detector, mock_cache_manager, established_baseline
    ):
        """Test getting baseline from cache"""
        metric_name = "quality_score:agent-001"
        # Create a proper dict with ISO format timestamp (no Z suffix issue)
        cached_dict = {
            "metric_name": established_baseline.metric_name,
            "mean": established_baseline.mean,
            "stddev": established_baseline.stddev,
            "sample_count": established_baseline.sample_count,
            "last_updated": established_baseline.last_updated.isoformat(),  # No Z suffix
            "window_hours": established_baseline.window_hours,
        }
        mock_cache_manager.get_baseline.return_value = cached_dict

        baseline = await anomaly_detector._get_baseline(metric_name)

        assert baseline is not None
        assert baseline.mean == established_baseline.mean

    @pytest.mark.asyncio
    async def test_get_baseline_not_found(self, anomaly_detector):
        """Test getting non-existent baseline"""
        baseline = await anomaly_detector._get_baseline("nonexistent")

        assert baseline is None

    @pytest.mark.asyncio
    async def test_update_baseline_new(self, anomaly_detector):
        """Test creating new baseline"""
        await anomaly_detector._update_baseline("new_metric", 50.0)

        assert "new_metric" in anomaly_detector._baselines
        baseline = anomaly_detector._baselines["new_metric"]
        assert baseline.mean == 50.0
        assert baseline.sample_count == 1

    @pytest.mark.asyncio
    async def test_update_baseline_existing(
        self, anomaly_detector, established_baseline
    ):
        """Test updating existing baseline"""
        metric_name = "quality_score:agent-001"
        anomaly_detector._baselines[metric_name] = established_baseline
        old_mean = established_baseline.mean
        old_count = established_baseline.sample_count

        await anomaly_detector._update_baseline(metric_name, 85.0)

        baseline = anomaly_detector._baselines[metric_name]
        assert baseline.sample_count == old_count + 1
        # Mean should shift slightly toward 85
        assert baseline.mean != old_mean

    @pytest.mark.asyncio
    async def test_get_baseline_public(
        self, anomaly_detector, established_baseline
    ):
        """Test public get_baseline method"""
        metric_name = "quality_score:agent-001"
        anomaly_detector._baselines[metric_name] = established_baseline

        baseline = await anomaly_detector.get_baseline(metric_name)

        assert baseline is established_baseline

    @pytest.mark.asyncio
    async def test_clear_baseline(
        self, anomaly_detector, mock_cache_manager, established_baseline
    ):
        """Test clearing specific baseline"""
        metric_name = "quality_score:agent-001"
        anomaly_detector._baselines[metric_name] = established_baseline

        await anomaly_detector.clear_baseline(metric_name)

        assert metric_name not in anomaly_detector._baselines
        mock_cache_manager.delete.assert_called()

    @pytest.mark.asyncio
    async def test_clear_all_baselines(
        self, anomaly_detector, mock_cache_manager, established_baseline
    ):
        """Test clearing all baselines"""
        anomaly_detector._baselines["metric1"] = established_baseline
        anomaly_detector._baselines["metric2"] = established_baseline

        await anomaly_detector.clear_all_baselines()

        assert len(anomaly_detector._baselines) == 0
        mock_cache_manager.clear.assert_called()


@pytest.mark.l06
@pytest.mark.unit
class TestStatistics:
    """Tests for statistics tracking"""

    def test_get_statistics(self, anomaly_detector, established_baseline):
        """Test getting statistics"""
        anomaly_detector._baselines["metric1"] = established_baseline
        anomaly_detector.anomalies_detected = 5
        anomaly_detector.baselines_trained = 3

        stats = anomaly_detector.get_statistics()

        assert stats["anomalies_detected"] == 5
        assert stats["baselines_trained"] == 3
        assert stats["baselines_in_memory"] == 1
        assert stats["deviation_threshold"] == 3.0

    def test_reset_statistics(self, anomaly_detector):
        """Test resetting statistics"""
        anomaly_detector.anomalies_detected = 10
        anomaly_detector.baselines_trained = 5

        anomaly_detector.reset_statistics()

        assert anomaly_detector.anomalies_detected == 0
        assert anomaly_detector.baselines_trained == 0


@pytest.mark.l06
@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_detect_handles_exception(self, anomaly_detector):
        """Test detection handles exceptions gracefully"""
        # Create score that will cause exception
        bad_score = MagicMock()
        bad_score.overall_score = None
        bad_score.agent_id = "agent-001"
        bad_score.tenant_id = "tenant-001"
        bad_score.timestamp = datetime.now(UTC)

        # Should return None on error
        result = await anomaly_detector.detect(bad_score)
        assert result is None


@pytest.mark.l06
@pytest.mark.unit
class TestColdStartBehavior:
    """Tests for cold-start period behavior"""

    @pytest.mark.asyncio
    async def test_cold_start_builds_baseline(self, anomaly_detector):
        """Test cold-start period builds baseline without detecting"""
        scores = []
        for i in range(15):  # More than cold_start_samples (10)
            score = QualityScore(
                score_id=f"qs-{i}",
                agent_id="agent-001",
                tenant_id="tenant-001",
                timestamp=datetime.now(UTC),
                overall_score=80.0 + i,  # Varying scores
                assessment=Assessment.GOOD,
                dimensions={},
            )
            scores.append(score)

        # Process all scores
        anomalies = []
        for score in scores:
            anomaly = await anomaly_detector.detect(score)
            if anomaly:
                anomalies.append(anomaly)

        # First 10 scores should not detect anomalies (cold-start)
        # After that, detection is active
        metric_name = "quality_score:agent-001"
        baseline = anomaly_detector._baselines.get(metric_name)
        assert baseline is not None
        assert baseline.sample_count >= 10


@pytest.mark.l06
@pytest.mark.unit
class TestDetectExceptionHandling:
    """Tests for exception handling in detect method (lines 135-137)"""

    @pytest.mark.asyncio
    async def test_detect_exception_returns_none(self, mock_cache_manager):
        """Test that exception during detect returns None (lines 135-137)"""
        detector = AnomalyDetector(
            cache_manager=mock_cache_manager,
            deviation_threshold=3.0,
            baseline_window_hours=24,
            cold_start_samples=5,
        )

        score = QualityScore(
            score_id="score-001",
            agent_id="agent-001",
            tenant_id="tenant-001",
            timestamp=datetime.now(UTC),
            overall_score=85.0,
            assessment=Assessment.GOOD,
            dimensions={},
        )

        # Make _get_baseline raise an exception to trigger lines 135-137
        async def raise_exception(*args, **kwargs):
            raise RuntimeError("Simulated error in _get_baseline")

        detector._get_baseline = raise_exception

        result = await detector.detect(score)

        # Should return None on exception (fail open)
        assert result is None
