"""Integration tests for L06 Evaluation Service"""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC


@pytest.mark.asyncio
async def test_evaluation_service_initialization():
    """Test EvaluationService initialization"""
    from src.L06_evaluation.services.evaluation_service import EvaluationService

    service = EvaluationService()
    await service.initialize()

    assert service._initialized is True

    await service.cleanup()


@pytest.mark.asyncio
async def test_event_processing(mock_cloud_event):
    """Test end-to-end event processing"""
    from src.L06_evaluation.services.evaluation_service import EvaluationService

    service = EvaluationService()
    await service.initialize()

    # Process event
    result = await service.process_event(mock_cloud_event)

    assert result is True

    await service.cleanup()


@pytest.mark.asyncio
async def test_quality_score_computation():
    """Test quality score computation"""
    from src.L06_evaluation.services.evaluation_service import EvaluationService

    service = EvaluationService()
    await service.initialize()

    # Query quality scores
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)

    scores = await service.get_quality_scores(
        agent_id="agent-1",
        start=start,
        end=end,
    )

    assert isinstance(scores, list)

    await service.cleanup()
