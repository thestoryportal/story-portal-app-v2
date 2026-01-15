"""Reusable test fixtures."""
from uuid import uuid4
from datetime import datetime

def create_test_goal(goal_text: str = "Test task"):
    """Create a test goal."""
    from src.L05_planning.models.goal import Goal
    return Goal(
        goal_id=str(uuid4()),
        agent_did="did:agent:test",
        goal_text=goal_text
    )

def create_test_cloud_event(event_type: str = "task.completed", data: dict = None):
    """Create a test CloudEvent."""
    from src.L06_evaluation.models.cloud_event import CloudEvent
    return CloudEvent(
        id=str(uuid4()),
        source="test",
        type=event_type,
        subject=f"test-{uuid4()}",
        time=datetime.now(),
        data=data or {"success": True}
    )

def create_test_inference_request(prompt: str = "Test prompt"):
    """Create a test inference request."""
    from src.L04_model_gateway.models.inference_request import (
        InferenceRequest, LogicalPrompt, ModelRequirements, RequestConstraints
    )
    return InferenceRequest(
        request_id=str(uuid4()),
        agent_did="did:agent:test",
        logical_prompt=LogicalPrompt(
            system="You are a test assistant.",
            user=prompt
        ),
        requirements=ModelRequirements(capabilities=[]),
        constraints=RequestConstraints()
    )
