"""
L06 Evaluation Layer - Metrics Engine Tests

Tests for metrics aggregation and time-series processing.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
import statistics

from ..services.metrics_engine import MetricsEngine, StubStorageManager
from ..services.cache_manager import CacheManager
from ..models.metric import MetricPoint, MetricType, MetricAggregation
from ..models.cloud_event import CloudEvent


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager"""
    storage = MagicMock()
    storage.write_metric = AsyncMock(return_value=True)
    storage.read_metrics = AsyncMock(return_value=[])
    storage.cleanup = AsyncMock()
    return storage


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager"""
    cache = MagicMock(spec=CacheManager)
    cache.get_query_result = AsyncMock(return_value=None)
    cache.set_query_result = AsyncMock()
    return cache


@pytest.fixture
def metrics_engine(mock_storage_manager, mock_cache_manager):
    """Create MetricsEngine with mocked dependencies"""
    return MetricsEngine(
        storage_manager=mock_storage_manager,
        cache_manager=mock_cache_manager,
        window_seconds=60,
        max_cardinality_per_tenant=100,
    )


@pytest.fixture
def metrics_engine_no_deps():
    """Create MetricsEngine without dependencies"""
    return MetricsEngine(
        storage_manager=None,
        cache_manager=None,
        window_seconds=60,
    )


@pytest.fixture
def sample_metric():
    """Create a sample MetricPoint"""
    return MetricPoint(
        metric_name="test_metric",
        value=42.0,
        timestamp=datetime.now(UTC),
        labels={"agent_id": "agent-001", "tenant_id": "tenant-001"},
        metric_type=MetricType.GAUGE,
    )


@pytest.fixture
def sample_cloud_event():
    """Create a sample CloudEvent"""
    return CloudEvent(
        id="evt-001",
        source="test-source",
        type="task.completed",
        subject="task-001",
        time=datetime.now(UTC),
        data={
            "duration_ms": 500,
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
            "success": True,
        },
    )


@pytest.mark.l06
@pytest.mark.unit
class TestStubStorageManager:
    """Tests for StubStorageManager"""

    @pytest.mark.asyncio
    async def test_write_metric(self):
        """Test stub write_metric does nothing"""
        stub = StubStorageManager()
        metric = MetricPoint(
            metric_name="test",
            value=1.0,
            timestamp=datetime.now(UTC),
        )
        await stub.write_metric(metric)  # Should not raise

    @pytest.mark.asyncio
    async def test_query_metrics(self):
        """Test stub query_metrics returns empty list"""
        stub = StubStorageManager()
        result = await stub.query_metrics()
        assert result == []

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test stub cleanup does nothing"""
        stub = StubStorageManager()
        await stub.cleanup()  # Should not raise


@pytest.mark.l06
@pytest.mark.unit
class TestMetricsEngineInit:
    """Tests for MetricsEngine initialization"""

    def test_init_with_dependencies(self, metrics_engine, mock_storage_manager, mock_cache_manager):
        """Test initialization with dependencies"""
        assert metrics_engine.storage is mock_storage_manager
        assert metrics_engine.cache is mock_cache_manager
        assert metrics_engine.window_seconds == 60
        assert metrics_engine.max_cardinality == 100

    def test_init_without_dependencies(self, metrics_engine_no_deps):
        """Test initialization without dependencies"""
        assert metrics_engine_no_deps.storage is None
        assert metrics_engine_no_deps.cache is None

    def test_initial_statistics(self, metrics_engine):
        """Test initial statistics are zeroed"""
        assert metrics_engine.metrics_ingested == 0
        assert metrics_engine.metrics_dropped_cardinality == 0

    def test_initial_buffer_empty(self, metrics_engine):
        """Test initial buffer is empty"""
        assert len(metrics_engine._buffer) == 0


@pytest.mark.l06
@pytest.mark.unit
class TestInitializeCleanup:
    """Tests for initialize and cleanup methods"""

    @pytest.mark.asyncio
    async def test_initialize_with_storage(self, metrics_engine):
        """Test initialization with storage manager"""
        await metrics_engine.initialize()
        assert metrics_engine._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, metrics_engine):
        """Test initialize is idempotent"""
        await metrics_engine.initialize()
        await metrics_engine.initialize()
        assert metrics_engine._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_creates_stub_storage(self):
        """Test initialization creates stub storage when module not available"""
        with patch('L06_evaluation.services.metrics_engine.StorageManager', None):
            engine = MetricsEngine()
            await engine.initialize()
            assert engine._initialized is True
            assert isinstance(engine.storage, StubStorageManager)

    @pytest.mark.asyncio
    async def test_cleanup(self, metrics_engine):
        """Test cleanup"""
        await metrics_engine.initialize()
        await metrics_engine.cleanup()
        assert metrics_engine._initialized is False


@pytest.mark.l06
@pytest.mark.unit
class TestIngest:
    """Tests for ingest method"""

    @pytest.mark.asyncio
    async def test_ingest_success(self, metrics_engine, sample_metric):
        """Test successful metric ingestion"""
        result = await metrics_engine.ingest(sample_metric)

        assert result is True
        assert metrics_engine.metrics_ingested == 1
        metrics_engine.storage.write_metric.assert_called_once_with(sample_metric)

    @pytest.mark.asyncio
    async def test_ingest_adds_to_buffer(self, metrics_engine, sample_metric):
        """Test ingestion adds to buffer"""
        await metrics_engine.ingest(sample_metric)

        series_key = sample_metric.series_key()
        assert series_key in metrics_engine._buffer
        assert len(metrics_engine._buffer[series_key]) == 1

    @pytest.mark.asyncio
    async def test_ingest_tracks_cardinality(self, metrics_engine, sample_metric):
        """Test ingestion tracks cardinality"""
        await metrics_engine.ingest(sample_metric)

        tenant_id = sample_metric.labels.get("tenant_id", "default")
        assert len(metrics_engine._cardinality[tenant_id]) == 1

    @pytest.mark.asyncio
    async def test_ingest_cardinality_limit(self, metrics_engine):
        """Test ingestion respects cardinality limit"""
        metrics_engine.max_cardinality = 2

        # First two should succeed
        for i in range(2):
            metric = MetricPoint(
                metric_name=f"metric_{i}",
                value=float(i),
                timestamp=datetime.now(UTC),
                labels={"tenant_id": "tenant-001"},
            )
            result = await metrics_engine.ingest(metric)
            assert result is True

        # Third should fail
        metric = MetricPoint(
            metric_name="metric_2",
            value=2.0,
            timestamp=datetime.now(UTC),
            labels={"tenant_id": "tenant-001"},
        )
        result = await metrics_engine.ingest(metric)

        assert result is False
        assert metrics_engine.metrics_dropped_cardinality == 1

    @pytest.mark.asyncio
    async def test_ingest_default_tenant(self, metrics_engine):
        """Test ingestion with default tenant"""
        metric = MetricPoint(
            metric_name="test",
            value=1.0,
            timestamp=datetime.now(UTC),
            labels={},  # No tenant_id
        )
        result = await metrics_engine.ingest(metric)

        assert result is True
        assert len(metrics_engine._cardinality["default"]) == 1

    @pytest.mark.asyncio
    async def test_ingest_exception_handled(self, metrics_engine, sample_metric):
        """Test ingestion handles exceptions"""
        metrics_engine.storage.write_metric = AsyncMock(side_effect=Exception("Storage error"))

        result = await metrics_engine.ingest(sample_metric)

        assert result is False


@pytest.mark.l06
@pytest.mark.unit
class TestIngestFromEvent:
    """Tests for ingest_from_event method"""

    @pytest.mark.asyncio
    async def test_ingest_task_completed_event(self, metrics_engine, sample_cloud_event):
        """Test ingestion from task.completed event"""
        metrics = await metrics_engine.ingest_from_event(sample_cloud_event)

        # Should create duration and completion counter metrics
        assert len(metrics) == 2
        metric_names = [m.metric_name for m in metrics]
        assert "task_duration_seconds" in metric_names
        assert "task_completed_total" in metric_names

    @pytest.mark.asyncio
    async def test_ingest_task_completed_no_duration(self, metrics_engine):
        """Test task.completed event without duration"""
        event = CloudEvent(
            id="evt-001",
            source="test",
            type="task.completed",
            subject="task-001",
            time=datetime.now(UTC),
            data={"success": True},
        )
        metrics = await metrics_engine.ingest_from_event(event)

        # Should only create completion counter (no duration)
        assert len(metrics) == 1
        assert metrics[0].metric_name == "task_completed_total"

    @pytest.mark.asyncio
    async def test_ingest_model_inference_event(self, metrics_engine):
        """Test ingestion from model.inference.used event"""
        event = CloudEvent(
            id="evt-001",
            source="test",
            type="model.inference.used",
            subject="inference-001",
            time=datetime.now(UTC),
            data={
                "tokens": 1000,
                "cost": 0.05,
                "model": "claude-3",
                "agent_id": "agent-001",
            },
        )
        metrics = await metrics_engine.ingest_from_event(event)

        # Should create tokens and cost metrics
        assert len(metrics) == 2
        metric_names = [m.metric_name for m in metrics]
        assert "model_tokens_used" in metric_names
        assert "model_cost_dollars" in metric_names

    @pytest.mark.asyncio
    async def test_ingest_error_occurred_event(self, metrics_engine):
        """Test ingestion from error.occurred event"""
        event = CloudEvent(
            id="evt-001",
            source="test",
            type="error.occurred",
            subject="error-001",
            time=datetime.now(UTC),
            data={
                "error_code": "E5001",
                "agent_id": "agent-001",
            },
        )
        metrics = await metrics_engine.ingest_from_event(event)

        # Should create error counter
        assert len(metrics) == 1
        assert metrics[0].metric_name == "errors_total"

    @pytest.mark.asyncio
    async def test_ingest_unknown_event_type(self, metrics_engine):
        """Test ingestion from unknown event type"""
        event = CloudEvent(
            id="evt-001",
            source="test",
            type="unknown.type",
            subject="unknown-001",
            time=datetime.now(UTC),
            data={},
        )
        metrics = await metrics_engine.ingest_from_event(event)

        # Should return empty list for unknown types
        assert len(metrics) == 0


@pytest.mark.l06
@pytest.mark.unit
class TestQuery:
    """Tests for query method"""

    @pytest.mark.asyncio
    async def test_query_empty(self, metrics_engine):
        """Test query with no results"""
        result = await metrics_engine.query(
            metric_name="test_metric",
            start=datetime.now(UTC) - timedelta(hours=1),
            end=datetime.now(UTC),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_query_with_cache_hit(self, metrics_engine, mock_cache_manager):
        """Test query with cache hit"""
        cached_data = [
            {
                "metric_name": "test_metric",
                "value": 42.0,
                "timestamp": datetime.now(UTC).isoformat(),
                "labels": {},
                "metric_type": "gauge",
            }
        ]
        mock_cache_manager.get_query_result.return_value = cached_data

        result = await metrics_engine.query(
            metric_name="test_metric",
            start=datetime.now(UTC) - timedelta(hours=1),
            end=datetime.now(UTC),
        )

        assert len(result) == 1
        assert result[0].metric_name == "test_metric"

    @pytest.mark.asyncio
    async def test_query_caches_result(self, metrics_engine, mock_cache_manager, mock_storage_manager):
        """Test query caches result"""
        mock_storage_manager.read_metrics.return_value = []

        await metrics_engine.query(
            metric_name="test_metric",
            start=datetime.now(UTC) - timedelta(hours=1),
            end=datetime.now(UTC),
        )

        mock_cache_manager.set_query_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_exception_handled(self, metrics_engine, mock_storage_manager):
        """Test query handles exceptions"""
        mock_storage_manager.read_metrics = AsyncMock(side_effect=Exception("Storage error"))

        result = await metrics_engine.query(
            metric_name="test_metric",
            start=datetime.now(UTC) - timedelta(hours=1),
            end=datetime.now(UTC),
        )

        assert result == []


@pytest.mark.l06
@pytest.mark.unit
class TestAggregateMetrics:
    """Tests for _aggregate_metrics method"""

    def test_aggregate_empty(self, metrics_engine):
        """Test aggregation of empty list"""
        result = metrics_engine._aggregate_metrics([], MetricAggregation.AVG)
        assert result == []

    def test_aggregate_avg(self, metrics_engine):
        """Test AVG aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.AVG)

        assert len(result) == 1
        assert result[0].value == 20.0

    def test_aggregate_sum(self, metrics_engine):
        """Test SUM aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.SUM)

        assert len(result) == 1
        assert result[0].value == 60.0

    def test_aggregate_min(self, metrics_engine):
        """Test MIN aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.MIN)

        assert len(result) == 1
        assert result[0].value == 10.0

    def test_aggregate_max(self, metrics_engine):
        """Test MAX aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.MAX)

        assert len(result) == 1
        assert result[0].value == 30.0

    def test_aggregate_stddev(self, metrics_engine):
        """Test STDDEV aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.STDDEV)

        assert len(result) == 1
        assert result[0].value == pytest.approx(statistics.stdev([10.0, 20.0, 30.0]))

    def test_aggregate_stddev_single_value(self, metrics_engine):
        """Test STDDEV with single value returns 0"""
        now = datetime.now(UTC)
        metrics = [MetricPoint("test", 10.0, now, {})]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.STDDEV)

        assert len(result) == 1
        assert result[0].value == 0.0

    def test_aggregate_p50(self, metrics_engine):
        """Test P50 (median) aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.P50)

        assert len(result) == 1
        assert result[0].value == 20.0

    def test_aggregate_p95(self, metrics_engine):
        """Test P95 aggregation"""
        now = datetime.now(UTC)
        # Create 100 values
        metrics = [MetricPoint("test", float(i), now, {}) for i in range(100)]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.P95)

        assert len(result) == 1
        assert result[0].value >= 94.0  # 95th percentile

    def test_aggregate_p99(self, metrics_engine):
        """Test P99 aggregation"""
        now = datetime.now(UTC)
        # Create 100 values
        metrics = [MetricPoint("test", float(i), now, {}) for i in range(100)]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.P99)

        assert len(result) == 1
        assert result[0].value >= 98.0  # 99th percentile

    def test_aggregate_count(self, metrics_engine):
        """Test COUNT aggregation"""
        now = datetime.now(UTC)
        metrics = [
            MetricPoint("test", 10.0, now, {}),
            MetricPoint("test", 20.0, now, {}),
            MetricPoint("test", 30.0, now, {}),
        ]
        result = metrics_engine._aggregate_metrics(metrics, MetricAggregation.COUNT)

        assert len(result) == 1
        assert result[0].value == 3.0


@pytest.mark.l06
@pytest.mark.unit
class TestPercentile:
    """Tests for _percentile method"""

    def test_percentile_empty(self, metrics_engine):
        """Test percentile of empty list"""
        result = metrics_engine._percentile([], 0.95)
        assert result == 0.0

    def test_percentile_single_value(self, metrics_engine):
        """Test percentile of single value"""
        result = metrics_engine._percentile([42.0], 0.95)
        assert result == 42.0

    def test_percentile_95(self, metrics_engine):
        """Test 95th percentile"""
        values = list(range(100))
        result = metrics_engine._percentile(values, 0.95)
        assert result == 95

    def test_percentile_99(self, metrics_engine):
        """Test 99th percentile"""
        values = list(range(100))
        result = metrics_engine._percentile(values, 0.99)
        assert result == 99


@pytest.mark.l06
@pytest.mark.unit
class TestGetWindowStart:
    """Tests for _get_window_start method"""

    def test_window_start_rounds_down(self, metrics_engine):
        """Test window start rounds down to window boundary"""
        # Create timestamp at :30 seconds
        timestamp = datetime(2026, 1, 28, 12, 0, 30, tzinfo=UTC)
        result = metrics_engine._get_window_start(timestamp)

        # Should round down to :00
        assert result.second == 0

    def test_window_start_exact_boundary(self, metrics_engine):
        """Test window start at exact boundary"""
        timestamp = datetime(2026, 1, 28, 12, 0, 0, tzinfo=UTC)
        result = metrics_engine._get_window_start(timestamp)

        # Result is naive datetime from fromtimestamp() (local time)
        # Verify it's at exact boundary (seconds = 0) and matches input epoch
        assert result.second == 0
        assert result.timestamp() == timestamp.timestamp()


@pytest.mark.l06
@pytest.mark.unit
class TestCheckCardinality:
    """Tests for _check_cardinality method"""

    def test_cardinality_new_series(self, metrics_engine):
        """Test adding new series"""
        result = metrics_engine._check_cardinality("tenant-001", "series-1")

        assert result is True
        assert "series-1" in metrics_engine._cardinality["tenant-001"]

    def test_cardinality_existing_series(self, metrics_engine):
        """Test existing series"""
        metrics_engine._cardinality["tenant-001"].add("series-1")

        result = metrics_engine._check_cardinality("tenant-001", "series-1")

        assert result is True

    def test_cardinality_limit_reached(self, metrics_engine):
        """Test cardinality limit"""
        metrics_engine.max_cardinality = 2
        metrics_engine._cardinality["tenant-001"].add("series-1")
        metrics_engine._cardinality["tenant-001"].add("series-2")

        result = metrics_engine._check_cardinality("tenant-001", "series-3")

        assert result is False


@pytest.mark.l06
@pytest.mark.unit
class TestFlushBuffer:
    """Tests for _flush_buffer method"""

    @pytest.mark.asyncio
    async def test_flush_empty_buffer(self, metrics_engine):
        """Test flushing empty buffer"""
        await metrics_engine._flush_buffer()
        # Should not raise

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self, metrics_engine, sample_metric):
        """Test flush clears buffer"""
        await metrics_engine.ingest(sample_metric)
        assert len(metrics_engine._buffer) > 0

        await metrics_engine._flush_buffer()

        assert len(metrics_engine._buffer) == 0


@pytest.mark.l06
@pytest.mark.unit
class TestCheckAndFlush:
    """Tests for _check_and_flush method"""

    @pytest.mark.asyncio
    async def test_check_no_flush_needed(self, metrics_engine):
        """Test check when flush not needed"""
        metrics_engine._last_flush = datetime.now(UTC)
        await metrics_engine._check_and_flush()
        # Should not flush (recent)

    @pytest.mark.asyncio
    async def test_check_flush_needed(self, metrics_engine, sample_metric):
        """Test check when flush is needed"""
        await metrics_engine.ingest(sample_metric)
        metrics_engine._last_flush = datetime.now(UTC) - timedelta(seconds=120)

        await metrics_engine._check_and_flush()

        # Buffer should be cleared
        assert len(metrics_engine._buffer) == 0


@pytest.mark.l06
@pytest.mark.unit
class TestGetQueryCacheKey:
    """Tests for _get_query_cache_key method"""

    def test_cache_key_generated(self, metrics_engine):
        """Test cache key is generated"""
        key = metrics_engine._get_query_cache_key(
            metric_name="test",
            start=datetime.now(UTC),
            end=datetime.now(UTC),
            labels=None,
            aggregation=MetricAggregation.AVG,
        )

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest length

    def test_cache_key_different_for_different_queries(self, metrics_engine):
        """Test different queries produce different keys"""
        now = datetime.now(UTC)
        key1 = metrics_engine._get_query_cache_key(
            metric_name="test1",
            start=now,
            end=now,
            labels=None,
            aggregation=MetricAggregation.AVG,
        )
        key2 = metrics_engine._get_query_cache_key(
            metric_name="test2",
            start=now,
            end=now,
            labels=None,
            aggregation=MetricAggregation.AVG,
        )

        assert key1 != key2


@pytest.mark.l06
@pytest.mark.unit
class TestStatistics:
    """Tests for statistics methods"""

    def test_get_statistics(self, metrics_engine):
        """Test getting statistics"""
        metrics_engine.metrics_ingested = 100
        metrics_engine.metrics_dropped_cardinality = 5
        metrics_engine._buffer["series-1"] = [MagicMock()]
        metrics_engine._cardinality["tenant-001"].add("series-1")

        stats = metrics_engine.get_statistics()

        assert stats["metrics_ingested"] == 100
        assert stats["metrics_dropped_cardinality"] == 5
        assert stats["buffer_size"] == 1
        assert stats["cardinality_by_tenant"]["tenant-001"] == 1

    def test_reset_statistics(self, metrics_engine):
        """Test resetting statistics"""
        metrics_engine.metrics_ingested = 100
        metrics_engine.metrics_dropped_cardinality = 5

        metrics_engine.reset_statistics()

        assert metrics_engine.metrics_ingested == 0
        assert metrics_engine.metrics_dropped_cardinality == 0


@pytest.mark.l06
@pytest.mark.unit
class TestIngestFromEventException:
    """Tests for ingest_from_event exception handling"""

    @pytest.mark.asyncio
    async def test_ingest_from_event_exception(self, metrics_engine, sample_cloud_event):
        """Test ingest_from_event handles exceptions (lines 253-254)"""
        await metrics_engine.initialize()

        # Make ingest fail to trigger exception handling
        async def raise_exception(*args, **kwargs):
            raise RuntimeError("Ingestion failed unexpectedly")

        metrics_engine.ingest = raise_exception

        # Should not raise - returns empty list on exception
        result = await metrics_engine.ingest_from_event(sample_cloud_event)

        # Should return empty list when exception occurs
        assert result == []


@pytest.mark.l06
@pytest.mark.unit
class TestInitializeWithStorageCreation:
    """Tests for initialize with storage creation (lines 92-94)"""

    @pytest.mark.asyncio
    async def test_initialize_creates_storage_manager(self, mock_cache_manager):
        """Test initialize creates StorageManager when none provided (lines 92-94)"""
        import L06_evaluation.services.metrics_engine as metrics_module

        # Create mock storage manager
        mock_storage = MagicMock()
        mock_storage.initialize = AsyncMock()
        mock_storage.cleanup = AsyncMock()

        # Store original and replace
        original_storage_manager = metrics_module.StorageManager

        # Create a mock class that returns our mock instance
        mock_storage_class = MagicMock(return_value=mock_storage)
        metrics_module.StorageManager = mock_storage_class

        try:
            # Create engine WITHOUT storage manager
            engine = MetricsEngine(
                storage_manager=None,
                cache_manager=mock_cache_manager,
            )

            # Initialize - should create storage manager
            await engine.initialize()

            # Verify storage was created and initialized
            assert engine._initialized is True
            mock_storage_class.assert_called_once()
            mock_storage.initialize.assert_called_once()

            await engine.cleanup()
        finally:
            # Restore original
            metrics_module.StorageManager = original_storage_manager


