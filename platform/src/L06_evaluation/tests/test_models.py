"""Tests for L06 models"""

import pytest
from datetime import datetime, UTC

def test_cloud_event_creation():
    """Test CloudEvent model creation"""
    from src.L06_evaluation.models.cloud_event import CloudEvent

    event = CloudEvent(
        id="test-1",
        source="l02.agent-runtime",
        type="task.completed",
        subject="task-1",
        data={"test": "data"},
    )

    assert event.id == "test-1"
    assert event.source == "l02.agent-runtime"
    assert event.type == "task.completed"

def test_metric_point_validation():
    """Test MetricPoint validation"""
    from src.L06_evaluation.models.metric import MetricPoint, MetricType

    metric = MetricPoint(
        metric_name="test_metric",
        value=100.0,
        timestamp=datetime.now(UTC),
        metric_type=MetricType.GAUGE,
    )

    assert metric.metric_name == "test_metric"
    assert metric.value == 100.0

def test_quality_score_weights():
    """Test QualityScore weight validation"""
    from src.L06_evaluation.models.quality_score import QualityScore, DimensionScore, Assessment

    dimensions = {
        "accuracy": DimensionScore("accuracy", 90.0, 0.5, {}),
        "latency": DimensionScore("latency", 80.0, 0.5, {}),
    }

    score = QualityScore(
        score_id="test-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        timestamp=datetime.now(UTC),
        overall_score=85.0,
        dimensions=dimensions,
        assessment=Assessment.GOOD,
    )

    assert score.overall_score == 85.0
