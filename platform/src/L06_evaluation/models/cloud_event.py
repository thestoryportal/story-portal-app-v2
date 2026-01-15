"""CloudEvent model per CloudEvents specification"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict
import uuid


class EventSource(str, Enum):
    """Event source identifiers"""
    L01_DATA_LAYER = "l01.data-layer"
    L02_AGENT_RUNTIME = "l02.agent-runtime"
    L03_TOOL_EXECUTION = "l03.tool-execution"
    L04_MODEL_GATEWAY = "l04.model-gateway"
    L05_PLANNING = "l05.planning"
    L06_EVALUATION = "l06.evaluation"


class EventType(str, Enum):
    """Event type identifiers"""
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    AGENT_EXECUTION_STARTED = "agent.execution.started"
    AGENT_EXECUTION_FINISHED = "agent.execution.finished"
    MODEL_INFERENCE_USED = "model.inference.used"
    ERROR_OCCURRED = "error.occurred"
    CONSTRAINT_CHECKED = "constraint.checked"
    TOOL_INVOKED = "tool.invoked"
    PLAN_CREATED = "plan.created"


@dataclass
class CloudEvent:
    """
    CloudEvent per CloudEvents 1.0 specification.

    Used for event-driven communication between layers.
    All events consumed by L06 must follow this schema.
    """
    id: str
    source: str
    type: str
    subject: str
    data: Dict[str, Any]
    time: datetime = field(default_factory=lambda: datetime.now(UTC))
    datacontenttype: str = "application/json"
    specversion: str = "1.0"

    def __post_init__(self):
        """Generate UUID if not provided"""
        if not self.id:
            self.id = str(uuid.uuid4())

        # Ensure time is datetime object
        if isinstance(self.time, str):
            self.time = datetime.fromisoformat(self.time.replace('Z', '+00:00'))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "subject": self.subject,
            "time": self.time.isoformat() + "Z" if isinstance(self.time, datetime) else self.time,
            "data": self.data,
            "datacontenttype": self.datacontenttype,
            "specversion": self.specversion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent":
        """Create CloudEvent from dictionary"""
        return cls(
            id=data["id"],
            source=data["source"],
            type=data["type"],
            subject=data["subject"],
            time=data["time"],
            data=data["data"],
            datacontenttype=data.get("datacontenttype", "application/json"),
            specversion=data.get("specversion", "1.0"),
        )

    def is_valid_source(self, whitelist: list[str]) -> bool:
        """Check if event source is in whitelist"""
        return self.source in whitelist

    def age_seconds(self) -> float:
        """Return age of event in seconds"""
        return (datetime.now(UTC) - self.time).total_seconds()
