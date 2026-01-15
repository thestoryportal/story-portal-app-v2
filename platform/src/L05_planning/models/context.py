"""
L05 Planning Layer - Execution Context Models.

Represents the execution context injected into tasks at runtime.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List


class ContextScope(str, Enum):
    """Scope of execution context determining access permissions."""

    GLOBAL = "global"  # Access to all resources
    WORKSPACE = "workspace"  # Access to workspace resources only
    TASK = "task"  # Access to task-specific resources only
    RESTRICTED = "restricted"  # Minimal access (sandboxed)


@dataclass
class ExecutionContext:
    """
    Execution context provided to a task at runtime.

    Contains all inputs, secrets, permissions, and metadata needed for task execution.
    """

    task_id: str  # Task being executed
    plan_id: str  # Parent plan
    agent_did: str  # Executing agent DID
    scope: ContextScope = ContextScope.TASK  # Access scope
    inputs: Dict[str, Any] = field(default_factory=dict)  # Input values
    secrets: Dict[str, str] = field(default_factory=dict)  # Secret references (masked)
    environment: Dict[str, str] = field(default_factory=dict)  # Environment variables
    permissions: List[str] = field(default_factory=list)  # Granted permissions
    parent_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Outputs from dependencies
    workspace_path: Optional[str] = None  # Workspace directory
    timeout_seconds: int = 300  # Execution timeout
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def get_input(self, key: str, default: Any = None) -> Any:
        """Get input value by key."""
        return self.inputs.get(key, default)

    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions

    def resolve_input_reference(self, reference: str) -> Optional[Any]:
        """
        Resolve input reference to parent task output.

        Reference format: "task_id.output_key"
        """
        if "." not in reference:
            return None

        task_id, output_key = reference.split(".", 1)
        if task_id in self.parent_outputs:
            return self.parent_outputs[task_id].get(output_key)

        return None

    def add_secret(self, key: str, reference: str) -> None:
        """Add secret reference (masked)."""
        self.secrets[key] = reference

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "agent_did": self.agent_did,
            "scope": self.scope.value,
            "inputs": self.inputs,
            "secrets": self.secrets,
            "environment": self.environment,
            "permissions": self.permissions,
            "parent_outputs": self.parent_outputs,
            "workspace_path": self.workspace_path,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary representation."""
        return cls(
            task_id=data["task_id"],
            plan_id=data["plan_id"],
            agent_did=data["agent_did"],
            scope=ContextScope(data.get("scope", "task")),
            inputs=data.get("inputs", {}),
            secrets=data.get("secrets", {}),
            environment=data.get("environment", {}),
            permissions=data.get("permissions", []),
            parent_outputs=data.get("parent_outputs", {}),
            workspace_path=data.get("workspace_path"),
            timeout_seconds=data.get("timeout_seconds", 300),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create_for_task(
        cls,
        task_id: str,
        plan_id: str,
        agent_did: str,
        inputs: Optional[Dict[str, Any]] = None,
        scope: ContextScope = ContextScope.TASK,
        timeout_seconds: int = 300,
    ) -> "ExecutionContext":
        """Factory method to create execution context for a task."""
        return cls(
            task_id=task_id,
            plan_id=plan_id,
            agent_did=agent_did,
            scope=scope,
            inputs=inputs or {},
            timeout_seconds=timeout_seconds,
        )
