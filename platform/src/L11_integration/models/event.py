"""
L11 Integration Layer - Event Bus Models.

Models for event-driven integration across layers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, Callable, Awaitable
from uuid import uuid4
import json


class EventPriority(str, Enum):
    """Priority level for event delivery."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EventMetadata:
    """Metadata for event tracking and correlation."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: Optional[str] = None  # Distributed tracing ID
    correlation_id: Optional[str] = None  # Request correlation ID
    source_service: Optional[str] = None  # Service that published the event
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0  # Number of delivery attempts
    max_retries: int = 3  # Maximum retry attempts
    tags: Dict[str, str] = field(default_factory=dict)  # Custom tags


@dataclass
class EventMessage:
    """
    Event message for async communication between layers.

    Events enable loose coupling and eventual consistency across the system.
    """

    topic: str  # Event topic (e.g., "agent.created", "task.completed")
    event_type: str  # Event type within topic
    payload: Dict[str, Any]  # Event data
    metadata: EventMetadata = field(default_factory=EventMetadata)
    schema_version: str = "1.0"  # Schema version for compatibility

    @classmethod
    def create(
        cls,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        source_service: Optional[str] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        tags: Optional[Dict[str, str]] = None,
    ) -> "EventMessage":
        """Factory method to create a new event."""
        metadata = EventMetadata(
            trace_id=trace_id,
            correlation_id=correlation_id,
            source_service=source_service,
            priority=priority,
            tags=tags or {},
        )
        return cls(
            topic=topic,
            event_type=event_type,
            payload=payload,
            metadata=metadata,
        )

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps({
            "topic": self.topic,
            "event_type": self.event_type,
            "payload": self.payload,
            "metadata": {
                "event_id": self.metadata.event_id,
                "trace_id": self.metadata.trace_id,
                "correlation_id": self.metadata.correlation_id,
                "source_service": self.metadata.source_service,
                "timestamp": self.metadata.timestamp.isoformat(),
                "priority": self.metadata.priority.value,
                "retry_count": self.metadata.retry_count,
                "max_retries": self.metadata.max_retries,
                "tags": self.metadata.tags,
            },
            "schema_version": self.schema_version,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "EventMessage":
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        metadata_dict = data.get("metadata", {})
        metadata = EventMetadata(
            event_id=metadata_dict.get("event_id", str(uuid4())),
            trace_id=metadata_dict.get("trace_id"),
            correlation_id=metadata_dict.get("correlation_id"),
            source_service=metadata_dict.get("source_service"),
            timestamp=datetime.fromisoformat(metadata_dict["timestamp"])
                if "timestamp" in metadata_dict else datetime.now(timezone.utc),
            priority=EventPriority(metadata_dict.get("priority", "normal")),
            retry_count=metadata_dict.get("retry_count", 0),
            max_retries=metadata_dict.get("max_retries", 3),
            tags=metadata_dict.get("tags", {}),
        )
        return cls(
            topic=data["topic"],
            event_type=data["event_type"],
            payload=data["payload"],
            metadata=metadata,
            schema_version=data.get("schema_version", "1.0"),
        )

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.metadata.retry_count += 1

    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.metadata.retry_count < self.metadata.max_retries


# Type alias for event handler functions
EventHandler = Callable[[EventMessage], Awaitable[None]]


@dataclass
class EventSubscription:
    """Subscription to an event topic."""

    subscription_id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""  # Topic pattern (supports wildcards like "agent.*")
    handler: Optional[EventHandler] = None  # Async handler function
    service_name: Optional[str] = None  # Service that created this subscription
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True  # Whether subscription is active

    def matches_topic(self, topic: str) -> bool:
        """Check if subscription matches given topic."""
        # Simple wildcard matching
        if self.topic == topic:
            return True
        if "*" in self.topic:
            pattern = self.topic.replace("*", ".*")
            import re
            return bool(re.match(f"^{pattern}$", topic))
        return False
