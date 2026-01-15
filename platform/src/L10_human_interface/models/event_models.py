"""
L10 Human Interface Layer - Event Models

Models for event querying and viewing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class EventType(str, Enum):
    """Event types."""
    AGENT_STATE_CHANGED = "agent.state.changed"
    AGENT_CREATED = "agent.created"
    AGENT_TERMINATED = "agent.terminated"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    COST_UPDATE = "cost.update"
    ALERT_TRIGGERED = "alert.triggered"
    CONTROL_OPERATION = "control.operation"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class EventFilter:
    """Filter for event queries."""
    event_types: Optional[List[str]] = None
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    severity: Optional[str] = None
    search_text: Optional[str] = None


@dataclass
class EventQuery:
    """Query for events."""
    filters: EventFilter
    limit: int = 100
    offset: int = 0
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # desc or asc


@dataclass
class EventSummary:
    """Event summary for list view."""
    event_id: str
    event_type: str
    aggregate_id: str  # agent_id, workflow_id, etc.
    aggregate_type: str  # "agent", "workflow", "task"
    timestamp: datetime
    tenant_id: str
    severity: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "severity": self.severity,
            "summary": self.summary,
        }


@dataclass
class EventDetail:
    """Full event details."""
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    timestamp: datetime
    tenant_id: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "payload": self.payload,
            "metadata": self.metadata,
            "version": self.version,
        }


@dataclass
class EventResponse:
    """Response with list of events."""
    events: List[EventSummary]
    total: int
    limit: int
    offset: int
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "events": [event.to_dict() for event in self.events],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "has_more": self.has_more,
        }
