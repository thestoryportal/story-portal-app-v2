"""Pytest configuration and fixtures"""

import pytest
import asyncio
from datetime import datetime, UTC

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_cloud_event():
    """Mock CloudEvent fixture"""
    from src.L06_evaluation.models.cloud_event import CloudEvent

    return CloudEvent(
        id="test-event-1",
        source="l02.agent-runtime",
        type="task.completed",
        subject="task-123",
        data={
            "agent_id": "agent-1",
            "tenant_id": "tenant-1",
            "duration_ms": 150,
            "success": True,
        },
    )

@pytest.fixture
def mock_metric_point():
    """Mock MetricPoint fixture"""
    from src.L06_evaluation.models.metric import MetricPoint, MetricType

    return MetricPoint(
        metric_name="task_duration_seconds",
        value=0.15,
        timestamp=datetime.now(UTC),
        labels={"agent_id": "agent-1", "tenant_id": "tenant-1"},
        metric_type=MetricType.GAUGE,
    )
