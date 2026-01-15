"""
L05 Planning Layer - Goal Data Model.

Represents high-level objectives that need to be decomposed into executable tasks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class GoalType(str, Enum):
    """Type of goal indicating decomposition complexity."""

    SIMPLE = "simple"  # Single-task goal, no decomposition needed
    COMPOUND = "compound"  # Multi-task goal, straightforward decomposition
    RECURSIVE = "recursive"  # Complex goal requiring recursive decomposition


class GoalStatus(str, Enum):
    """Status of goal in the planning lifecycle."""

    PENDING = "pending"  # Goal received, not yet processed
    DECOMPOSING = "decomposing"  # Goal is being decomposed into tasks
    READY = "ready"  # Goal decomposed, plan ready for execution
    FAILED = "failed"  # Goal decomposition failed


@dataclass
class GoalConstraints:
    """Constraints and requirements for goal execution."""

    max_token_budget: Optional[int] = None  # Maximum tokens allowed
    max_execution_time_sec: Optional[int] = None  # Maximum execution time
    max_parallelism: int = 10  # Maximum parallel tasks
    deadline_unix_ms: Optional[int] = None  # Hard deadline
    priority: int = 5  # Priority 1-10 (10 highest)
    require_approval: bool = False  # Requires human approval before execution
    allowed_agent_types: Optional[list[str]] = None  # Restrict to agent types
    forbidden_tools: Optional[list[str]] = None  # Tools not allowed
    cost_limit_usd: Optional[float] = None  # Maximum cost in USD


@dataclass
class Goal:
    """
    Represents a high-level goal to be decomposed into executable tasks.

    A Goal is the input to the Planning Layer. It contains natural language or
    structured description of what needs to be accomplished, along with metadata
    and constraints.
    """

    goal_id: str  # Unique identifier (UUID)
    agent_did: str  # DID of requesting agent
    goal_text: str  # Natural language or structured goal description
    goal_type: GoalType = GoalType.COMPOUND  # Type of goal
    status: GoalStatus = GoalStatus.PENDING  # Current status
    constraints: GoalConstraints = field(default_factory=GoalConstraints)  # Constraints
    created_at: datetime = field(default_factory=datetime.utcnow)  # Creation timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    parent_goal_id: Optional[str] = None  # For recursive decomposition
    decomposition_strategy: Optional[str] = None  # "llm", "template", "hybrid"

    @classmethod
    def create(
        cls,
        agent_did: str,
        goal_text: str,
        goal_type: GoalType = GoalType.COMPOUND,
        constraints: Optional[GoalConstraints] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_goal_id: Optional[str] = None,
    ) -> "Goal":
        """Factory method to create a new Goal with generated UUID."""
        return cls(
            goal_id=str(uuid4()),
            agent_did=agent_did,
            goal_text=goal_text,
            goal_type=goal_type,
            status=GoalStatus.PENDING,
            constraints=constraints or GoalConstraints(),
            created_at=datetime.utcnow(),
            metadata=metadata or {},
            parent_goal_id=parent_goal_id,
        )

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate goal input per security requirements.

        Returns:
            (is_valid, error_message)
        """
        import re

        # Check length
        if len(self.goal_text) > 100_000:
            return False, "Goal text exceeds 100,000 character limit (E5001)"

        # Check for shell metacharacters
        shell_metacharacters = r'[<>|&;$`]'
        if re.search(shell_metacharacters, self.goal_text):
            return False, "Goal text contains shell metacharacters (E5004)"

        # Check for SQL keywords (case-insensitive)
        sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE']
        goal_upper = self.goal_text.upper()
        for keyword in sql_keywords:
            # Look for keyword as whole word
            if re.search(r'\b' + keyword + r'\b', goal_upper):
                return False, f"Goal text contains SQL keyword: {keyword} (E5004)"

        # Check for code patterns
        code_patterns = [
            r'eval\s*\(',
            r'__import__\s*\(',
            r'exec\s*\(',
            r'<script\s*>',
        ]
        for pattern in code_patterns:
            if re.search(pattern, self.goal_text, re.IGNORECASE):
                return False, f"Goal text contains code injection pattern (E5004)"

        # Character whitelist check (alphanumeric, spaces, basic punctuation, filenames)
        # Allow: letters, numbers, spaces, basic punctuation, underscores, slashes, quotes
        allowed_chars = r'^[a-zA-Z0-9\s\-.,!?:;()_/\'"@#]+$'
        if not re.match(allowed_chars, self.goal_text):
            return False, "Goal text contains invalid characters (E5004)"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert Goal to dictionary representation."""
        return {
            "goal_id": self.goal_id,
            "agent_did": self.agent_did,
            "goal_text": self.goal_text,
            "goal_type": self.goal_type.value,
            "status": self.status.value,
            "constraints": {
                "max_token_budget": self.constraints.max_token_budget,
                "max_execution_time_sec": self.constraints.max_execution_time_sec,
                "max_parallelism": self.constraints.max_parallelism,
                "deadline_unix_ms": self.constraints.deadline_unix_ms,
                "priority": self.constraints.priority,
                "require_approval": self.constraints.require_approval,
                "allowed_agent_types": self.constraints.allowed_agent_types,
                "forbidden_tools": self.constraints.forbidden_tools,
                "cost_limit_usd": self.constraints.cost_limit_usd,
            },
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "parent_goal_id": self.parent_goal_id,
            "decomposition_strategy": self.decomposition_strategy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Create Goal from dictionary representation."""
        constraints_data = data.get("constraints", {})
        constraints = GoalConstraints(
            max_token_budget=constraints_data.get("max_token_budget"),
            max_execution_time_sec=constraints_data.get("max_execution_time_sec"),
            max_parallelism=constraints_data.get("max_parallelism", 10),
            deadline_unix_ms=constraints_data.get("deadline_unix_ms"),
            priority=constraints_data.get("priority", 5),
            require_approval=constraints_data.get("require_approval", False),
            allowed_agent_types=constraints_data.get("allowed_agent_types"),
            forbidden_tools=constraints_data.get("forbidden_tools"),
            cost_limit_usd=constraints_data.get("cost_limit_usd"),
        )

        return cls(
            goal_id=data["goal_id"],
            agent_did=data["agent_did"],
            goal_text=data["goal_text"],
            goal_type=GoalType(data.get("goal_type", "compound")),
            status=GoalStatus(data.get("status", "pending")),
            constraints=constraints,
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
            parent_goal_id=data.get("parent_goal_id"),
            decomposition_strategy=data.get("decomposition_strategy"),
        )
