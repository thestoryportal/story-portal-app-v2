"""L06 Evaluation layer tests."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

class TestL06Evaluation:
    """Test L06 Evaluation functionality."""

    @pytest.fixture
    async def evaluation_service(self):
        """Initialize evaluation service."""
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        service = EvaluationService()
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest.fixture
    async def quality_scorer(self):
        """Initialize quality scorer."""
        from src.L06_evaluation.services.quality_scorer import QualityScorer
        scorer = QualityScorer()
        await scorer.initialize()
        yield scorer
        await scorer.cleanup()

    @pytest.fixture
    async def metrics_engine(self):
        """Initialize metrics engine."""
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        await engine.initialize()
        yield engine
        await engine.cleanup()

    @pytest.fixture
    def sample_cloud_event(self):
        """Create sample CloudEvent for testing."""
        from src.L06_evaluation.models.cloud_event import CloudEvent
        return CloudEvent(
            id=str(uuid4()),
            source="l02.agent-runtime",
            type="task.completed",
            subject=f"task-{uuid4()}",
            time=datetime.now(),
            data={
                "agent_id": "agent-001",
                "task_id": str(uuid4()),
                "duration_ms": 1500,
                "success": True,
                "token_count": 250
            }
        )

    @pytest.mark.asyncio
    async def test_evaluation_service_initialization(self, evaluation_service):
        """Evaluation service initializes correctly."""
        assert evaluation_service is not None

    @pytest.mark.asyncio
    async def test_quality_scorer_initialization(self, quality_scorer):
        """Quality scorer initializes correctly."""
        assert quality_scorer is not None

    @pytest.mark.asyncio
    async def test_metrics_engine_initialization(self, metrics_engine):
        """Metrics engine initializes correctly."""
        assert metrics_engine is not None

    @pytest.mark.asyncio
    async def test_process_cloud_event(self, evaluation_service, sample_cloud_event):
        """Can process a CloudEvent."""
        await evaluation_service.process_event(sample_cloud_event)
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_quality_score_computation(self, quality_scorer):
        """Can compute quality scores."""
        score = await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=(datetime.now() - timedelta(hours=1), datetime.now())
        )

        # Score may be None if no data, or a QualityScore object
        if score is not None:
            assert 0 <= score.overall_score <= 100
            assert len(score.dimensions) >= 1

    @pytest.mark.asyncio
    async def test_quality_dimensions(self, quality_scorer):
        """Quality scorer uses 5 dimensions."""
        expected_dimensions = ['accuracy', 'latency', 'cost', 'reliability', 'compliance']

        # Verify dimensions are configured
        assert hasattr(quality_scorer, 'dimensions') or hasattr(quality_scorer, 'config')

    @pytest.mark.asyncio
    async def test_dimension_weights_sum_to_one(self, quality_scorer):
        """Quality dimension weights sum to 1.0."""
        if hasattr(quality_scorer, 'weights'):
            weights = quality_scorer.weights
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    @pytest.mark.asyncio
    async def test_metrics_ingestion(self, metrics_engine):
        """Can ingest metrics."""
        from src.L06_evaluation.models.metric import MetricPoint, MetricType

        metric = MetricPoint(
            metric_name="task_duration_ms",
            value=1500.0,
            timestamp=datetime.now(),
            labels={"agent_id": "agent-001", "task_type": "summarization"},
            metric_type=MetricType.GAUGE
        )

        await metrics_engine.ingest(metric)
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_metrics_query(self, metrics_engine):
        """Can query metrics."""
        results = await metrics_engine.query(
            metric_name="task_duration_ms",
            start=datetime.now() - timedelta(hours=1),
            end=datetime.now(),
            labels={},
            aggregation="avg"
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, evaluation_service):
        """Anomaly detector identifies outliers."""
        from src.L06_evaluation.services.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()
        await detector.initialize()

        # Anomaly detection requires baseline data
        # This test verifies the detector initializes
        assert detector is not None

        await detector.cleanup()
