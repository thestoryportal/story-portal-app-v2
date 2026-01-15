"""Custom test assertions."""
from typing import Any

def assert_valid_plan(plan: Any) -> None:
    """Assert plan is valid."""
    assert plan is not None, "Plan is None"
    assert plan.plan_id is not None, "Plan ID is None"
    assert plan.tasks is not None, "Plan tasks is None"
    assert len(plan.tasks) >= 1, "Plan has no tasks"

def assert_valid_response(response: Any) -> None:
    """Assert inference response is valid."""
    assert response is not None, "Response is None"
    assert response.content is not None, "Response content is None"
    assert len(response.content) > 0, "Response content is empty"

def assert_valid_quality_score(score: Any) -> None:
    """Assert quality score is valid."""
    assert score is not None, "Score is None"
    assert 0 <= score.overall_score <= 100, f"Score {score.overall_score} out of range"
    assert len(score.dimensions) >= 1, "Score has no dimensions"
