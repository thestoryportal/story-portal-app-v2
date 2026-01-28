"""
L02 Agent Runtime - Agent DTOs

Pydantic models for agent lifecycle HTTP endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ResourceLimitsDTO(BaseModel):
    """Resource allocation limits"""
    cpu: str = Field("2", description="CPU cores (e.g., '2', '500m')")
    memory: str = Field("2Gi", description="Memory limit (e.g., '2Gi', '512Mi')")
    tokens_per_hour: int = Field(100000, description="Token budget per hour")

    model_config = {"extra": "ignore"}


class ToolDefinitionDTO(BaseModel):
    """Tool available to the agent"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")

    model_config = {"extra": "ignore"}


class SpawnRequestDTO(BaseModel):
    """Request to spawn a new agent"""
    agent_id: str = Field(..., description="Unique agent identifier")
    trust_level: str = Field(
        "standard",
        description="Trust level: trusted, standard, untrusted, confidential"
    )
    resource_limits: Optional[ResourceLimitsDTO] = Field(
        None,
        description="Resource allocation limits"
    )
    tools: List[ToolDefinitionDTO] = Field(
        default_factory=list,
        description="Tools available to the agent"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    initial_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Initial execution context"
    )
    recovery_checkpoint_id: Optional[str] = Field(
        None,
        description="Checkpoint ID for recovery"
    )

    model_config = {"extra": "ignore"}


class SpawnResponseDTO(BaseModel):
    """Response from spawning an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    session_id: str = Field(..., description="Session identifier")
    state: str = Field(..., description="Agent state")
    sandbox_type: str = Field(..., description="Sandbox type used")
    container_id: Optional[str] = Field(None, description="Container ID if applicable")
    pod_name: Optional[str] = Field(None, description="Pod name if using Kubernetes")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"extra": "ignore"}


class TerminateRequestDTO(BaseModel):
    """Request to terminate an agent"""
    reason: str = Field(..., description="Termination reason")
    force: bool = Field(False, description="Force kill without graceful shutdown")

    model_config = {"extra": "ignore"}


class SuspendRequestDTO(BaseModel):
    """Request to suspend an agent"""
    checkpoint: bool = Field(True, description="Whether to create a checkpoint")

    model_config = {"extra": "ignore"}


class SuspendResponseDTO(BaseModel):
    """Response from suspending an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    checkpoint_id: Optional[str] = Field(None, description="Checkpoint ID if created")
    state: str = Field(..., description="Agent state after suspension")

    model_config = {"extra": "ignore"}


class ResumeRequestDTO(BaseModel):
    """Request to resume a suspended agent"""
    checkpoint_id: Optional[str] = Field(
        None,
        description="Optional checkpoint to restore from"
    )

    model_config = {"extra": "ignore"}


class ResumeResponseDTO(BaseModel):
    """Response from resuming an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    state: str = Field(..., description="Agent state after resume")
    restored_from_checkpoint: bool = Field(..., description="Whether restored from checkpoint")

    model_config = {"extra": "ignore"}


class AgentStateDTO(BaseModel):
    """Agent state information"""
    state: str = Field(..., description="Current agent state")
    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"extra": "ignore"}


class AgentStateResponseDTO(BaseModel):
    """Response for agent state query"""
    agent_id: str = Field(..., description="Agent identifier")
    state: str = Field(..., description="Current agent state")
    session_id: str = Field(..., description="Session identifier")
    sandbox_type: str = Field(..., description="Sandbox type")
    resource_usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current resource usage"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    terminated_at: Optional[datetime] = Field(
        None,
        description="Termination timestamp if applicable"
    )

    model_config = {"extra": "ignore"}
