"""
L02 Agent Runtime - Execution DTOs

Pydantic models for agent execution HTTP endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ToolCallDTO(BaseModel):
    """Tool call from LLM response"""
    id: str = Field(..., description="Tool call identifier")
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments"
    )

    model_config = {"extra": "ignore"}


class ToolResultDTO(BaseModel):
    """Result of a tool invocation"""
    invocation_id: str = Field(..., description="Tool invocation identifier")
    tool_name: str = Field(..., description="Tool name")
    success: bool = Field(..., description="Whether tool execution succeeded")
    result: Optional[Any] = Field(None, description="Tool result if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(0.0, description="Execution time in milliseconds")

    model_config = {"extra": "ignore"}


class ExecuteRequestDTO(BaseModel):
    """Request to execute an agent"""
    content: str = Field(..., description="Input message content")
    system_prompt: Optional[str] = Field(
        None,
        description="Optional system prompt override"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum tokens to generate"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata"
    )

    model_config = {"extra": "ignore"}


class TokenUsageDTO(BaseModel):
    """Token usage information"""
    input_tokens: int = Field(0, description="Input tokens used")
    output_tokens: int = Field(0, description="Output tokens generated")
    cached_tokens: int = Field(0, description="Tokens from cache")
    total_tokens: int = Field(0, description="Total tokens")

    model_config = {"extra": "ignore"}


class ExecuteResponseDTO(BaseModel):
    """Response from executing an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    session_id: str = Field(..., description="Session identifier")
    request_id: Optional[str] = Field(None, description="LLM request identifier")
    model_id: Optional[str] = Field(None, description="Model used for inference")
    provider: Optional[str] = Field(None, description="Provider used")
    response: str = Field(..., description="Agent response content")
    tool_calls: List[ToolCallDTO] = Field(
        default_factory=list,
        description="Tool calls requested by the agent"
    )
    token_usage: TokenUsageDTO = Field(
        default_factory=TokenUsageDTO,
        description="Token usage information"
    )
    latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
    cached: bool = Field(False, description="Whether response was cached")

    model_config = {"extra": "ignore"}


class StreamChunkDTO(BaseModel):
    """SSE chunk for streaming responses"""
    type: str = Field(
        ...,
        description="Chunk type: start, content, tool_call, end, error"
    )
    agent_id: str = Field(..., description="Agent identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    request_id: Optional[str] = Field(None, description="LLM request identifier")
    delta: Optional[str] = Field(None, description="Content delta for 'content' type")
    tool_call: Optional[ToolCallDTO] = Field(
        None,
        description="Tool call for 'tool_call' type"
    )
    tokens_used: Optional[int] = Field(
        None,
        description="Total tokens used (on 'end' type)"
    )
    content_length: Optional[int] = Field(
        None,
        description="Total content length (on 'end' type)"
    )
    error_code: Optional[str] = Field(
        None,
        description="Error code for 'error' type"
    )
    message: Optional[str] = Field(
        None,
        description="Error message for 'error' type"
    )

    model_config = {"extra": "ignore"}


class ErrorResponseDTO(BaseModel):
    """Error response DTO"""
    error_code: str = Field(..., description="Error code (e.g., E2001)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )

    model_config = {"extra": "ignore"}
