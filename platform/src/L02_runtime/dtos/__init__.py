"""
L02 Agent Runtime - Data Transfer Objects (DTOs)

Pydantic models for HTTP API request/response serialization.
"""

from .agent_dtos import (
    SpawnRequestDTO,
    SpawnResponseDTO,
    TerminateRequestDTO,
    SuspendRequestDTO,
    SuspendResponseDTO,
    ResumeRequestDTO,
    ResumeResponseDTO,
    AgentStateDTO,
    AgentStateResponseDTO,
    ResourceLimitsDTO,
    ToolDefinitionDTO,
)

from .execution_dtos import (
    ExecuteRequestDTO,
    ExecuteResponseDTO,
    StreamChunkDTO,
    ToolCallDTO,
    ToolResultDTO,
    TokenUsageDTO,
    ErrorResponseDTO,
)

__all__ = [
    # Agent DTOs
    "SpawnRequestDTO",
    "SpawnResponseDTO",
    "TerminateRequestDTO",
    "SuspendRequestDTO",
    "SuspendResponseDTO",
    "ResumeRequestDTO",
    "ResumeResponseDTO",
    "AgentStateDTO",
    "AgentStateResponseDTO",
    "ResourceLimitsDTO",
    "ToolDefinitionDTO",
    # Execution DTOs
    "ExecuteRequestDTO",
    "ExecuteResponseDTO",
    "StreamChunkDTO",
    "ToolCallDTO",
    "ToolResultDTO",
    "TokenUsageDTO",
    "ErrorResponseDTO",
]
