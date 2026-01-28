"""Sample event data for testing."""

from datetime import datetime, timezone
from typing import Dict, Any


def sample_agent_event(
    event_type: str = "agent.created",
    agent_id: str = "agent-123",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample agent event."""
    return {
        "event_id": f"evt-{agent_id}-001",
        "event_type": event_type,
        "aggregate_type": "agent",
        "aggregate_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "agent_id": agent_id,
            "name": "Test Agent",
            "status": "created",
            **payload_extras,
        },
    }


def sample_tool_event(
    event_type: str = "tool.registered",
    tool_id: str = "tool-456",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample tool event."""
    return {
        "event_id": f"evt-{tool_id}-001",
        "event_type": event_type,
        "aggregate_type": "tool",
        "aggregate_id": tool_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "tool_id": tool_id,
            "name": "Test Tool",
            "version": "1.0.0",
            **payload_extras,
        },
    }


def sample_tool_execution_event(
    event_type: str = "tool_execution.started",
    execution_id: str = "exec-789",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample tool execution event."""
    return {
        "event_id": f"evt-{execution_id}-001",
        "event_type": event_type,
        "aggregate_type": "tool_execution",
        "aggregate_id": execution_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "execution_id": execution_id,
            "tool_id": "tool-456",
            "status": "started",
            **payload_extras,
        },
    }


def sample_plan_event(
    event_type: str = "plan.created",
    plan_id: str = "plan-abc",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample plan event."""
    return {
        "event_id": f"evt-{plan_id}-001",
        "event_type": event_type,
        "aggregate_type": "plan",
        "aggregate_id": plan_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "plan_id": plan_id,
            "goal": "Test Goal",
            "status": "created",
            **payload_extras,
        },
    }


def sample_session_event(
    event_type: str = "session.started",
    session_id: str = "session-xyz",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample session event."""
    return {
        "event_id": f"evt-{session_id}-001",
        "event_type": event_type,
        "aggregate_type": "session",
        "aggregate_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "session_id": session_id,
            "user_id": "user-001",
            "status": "started",
            **payload_extras,
        },
    }


def sample_dataset_event(
    event_type: str = "dataset.created",
    dataset_id: str = "dataset-001",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample dataset event."""
    return {
        "event_id": f"evt-{dataset_id}-001",
        "event_type": event_type,
        "aggregate_type": "dataset",
        "aggregate_id": dataset_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "dataset_id": dataset_id,
            "name": "Test Dataset",
            "status": "created",
            **payload_extras,
        },
    }


def sample_unknown_event(
    event_type: str = "unknown.event",
    aggregate_id: str = "unknown-001",
    **payload_extras,
) -> Dict[str, Any]:
    """Create a sample event with unknown aggregate type."""
    return {
        "event_id": f"evt-{aggregate_id}-001",
        "event_type": event_type,
        "aggregate_type": "unknown_type",
        "aggregate_id": aggregate_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "data": "test",
            **payload_extras,
        },
    }
