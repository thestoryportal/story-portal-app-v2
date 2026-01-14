"""
Checkpoint Data Models

Models for agent state checkpointing and recovery.
Based on Section 5.1.4 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class CheckpointType(Enum):
    """Type of checkpoint"""
    AUTO = "auto"                    # Automatic periodic checkpoint
    MANUAL = "manual"                # User-initiated checkpoint
    PRE_SUSPEND = "pre_suspend"      # Before suspending agent
    PRE_DRAIN = "pre_drain"          # Before draining instance


@dataclass
class Checkpoint:
    """
    Saved agent state for recovery.

    Checkpoints enable crash recovery and state migration.
    """
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    session_id: str = ""
    label: Optional[str] = None
    checkpoint_type: CheckpointType = CheckpointType.AUTO
    storage_location: str = ""       # URI to checkpoint data
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "label": self.label,
            "checkpoint_type": self.checkpoint_type.value,
            "storage_location": self.storage_location,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
