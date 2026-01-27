"""
L04 Model Gateway Layer - Inference Response Models

Defines the response structure for model inference operations.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class ResponseStatus(Enum):
    """Status of an inference response"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"  # For streaming responses


@dataclass
class TokenUsage:
    """Token usage information"""
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used"""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class CostBreakdown:
    """Cost breakdown for the inference"""
    input_cost_cents: float
    output_cost_cents: float
    cached_cost_cents: float = 0.0

    @property
    def total_cost_cents(self) -> float:
        """Total cost in cents"""
        return self.input_cost_cents + self.output_cost_cents + self.cached_cost_cents

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "input_cost_cents": self.input_cost_cents,
            "output_cost_cents": self.output_cost_cents,
            "cached_cost_cents": self.cached_cost_cents,
            "total_cost_cents": self.total_cost_cents
        }


@dataclass
class ToolCall:
    """Represents a tool call in the response"""
    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments
        }


@dataclass
class InferenceResponse:
    """
    Model inference response

    This is the normalized response format returned by the Model Gateway Layer,
    regardless of which provider was used.
    """
    request_id: str
    model_id: str
    provider: str
    content: str
    token_usage: TokenUsage
    latency_ms: int
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ResponseStatus = ResponseStatus.SUCCESS
    error_message: Optional[str] = None
    finish_reason: Optional[str] = None  # "stop", "length", "tool_calls", etc.
    tool_calls: Optional[List[ToolCall]] = None
    cost_breakdown: Optional[CostBreakdown] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "provider": self.provider,
            "content": self.content,
            "token_usage": self.token_usage.to_dict(),
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value
        }

        if self.error_message:
            result["error_message"] = self.error_message
        if self.finish_reason:
            result["finish_reason"] = self.finish_reason
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.cost_breakdown:
            result["cost_breakdown"] = self.cost_breakdown.to_dict()

        return result

    def is_success(self) -> bool:
        """Check if response was successful"""
        return self.status == ResponseStatus.SUCCESS

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls"""
        return self.tool_calls is not None and len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """A chunk in a streaming response"""
    request_id: str
    content_delta: str
    is_final: bool = False
    token_count: Optional[int] = None
    finish_reason: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "request_id": self.request_id,
            "content_delta": self.content_delta,
            "is_final": self.is_final
        }
        if self.token_count is not None:
            result["token_count"] = self.token_count
        if self.finish_reason:
            result["finish_reason"] = self.finish_reason
        return result
