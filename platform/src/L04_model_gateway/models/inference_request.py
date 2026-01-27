"""
L04 Model Gateway Layer - Inference Request Models

Defines the request structure for model inference operations.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class MessageRole(Enum):
    """Role of a message in the conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in a conversation"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class LogicalPrompt:
    """
    Logical prompt representation - abstraction over provider-specific formats
    """
    messages: Optional[List[Message]] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None

    # Convenience parameters for simple prompts
    system: Optional[str] = None
    user: Optional[str] = None

    def __post_init__(self):
        """Convert convenience parameters to messages if provided"""
        if self.messages is None:
            self.messages = []

        # If system and user convenience parameters are provided, convert them
        if self.system is not None or self.user is not None:
            new_messages = []
            if self.system is not None:
                self.system_prompt = self.system
                new_messages.append(Message(role=MessageRole.SYSTEM, content=self.system))
            if self.user is not None:
                new_messages.append(Message(role=MessageRole.USER, content=self.user))

            # Only set messages if they weren't already provided
            if not self.messages:
                self.messages = new_messages

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "messages": [m.to_dict() for m in self.messages],
            "temperature": self.temperature
        }
        if self.system_prompt:
            result["system_prompt"] = self.system_prompt
        if self.max_tokens:
            result["max_tokens"] = self.max_tokens
        if self.stop_sequences:
            result["stop_sequences"] = self.stop_sequences
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.presence_penalty is not None:
            result["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            result["frequency_penalty"] = self.frequency_penalty
        return result

    def estimate_tokens(self) -> int:
        """Rough estimate of token count (4 chars per token heuristic)"""
        total_chars = len(self.system_prompt or "")
        for message in self.messages:
            total_chars += len(message.content)
        return total_chars // 4


@dataclass
class ModelRequirements:
    """Requirements for model selection"""
    capabilities: List[str] = field(default_factory=list)  # e.g., ["vision", "tool_use", "long_context"]
    min_context_length: int = 4096
    max_output_tokens: int = 4096
    preferred_quality: Optional[str] = None  # "reasoning", "coding", "creative", "summarization"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "capabilities": self.capabilities,
            "min_context_length": self.min_context_length,
            "max_output_tokens": self.max_output_tokens
        }
        if self.preferred_quality:
            result["preferred_quality"] = self.preferred_quality
        return result


@dataclass
class RequestConstraints:
    """Constraints for request execution"""
    max_latency_ms: int = 30000
    max_cost_cents: int = 100
    preferred_providers: Optional[List[str]] = None
    allowed_regions: Optional[List[str]] = None  # For data residency
    require_streaming: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        result = {
            "max_latency_ms": self.max_latency_ms,
            "max_cost_cents": self.max_cost_cents,
            "require_streaming": self.require_streaming
        }
        if self.preferred_providers:
            result["preferred_providers"] = self.preferred_providers
        if self.allowed_regions:
            result["allowed_regions"] = self.allowed_regions
        return result


@dataclass
class InferenceRequest:
    """
    Model inference request

    This is the primary request object for the Model Gateway Layer.
    It abstracts away provider-specific details and focuses on logical requirements.
    """
    request_id: str
    agent_did: str
    logical_prompt: LogicalPrompt
    requirements: ModelRequirements = field(default_factory=ModelRequirements)
    constraints: RequestConstraints = field(default_factory=RequestConstraints)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    enable_cache: bool = True
    enable_streaming: bool = False

    @classmethod
    def create(
        cls,
        agent_did: str,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        capabilities: Optional[List[str]] = None,
        **kwargs
    ) -> 'InferenceRequest':
        """
        Convenience factory method for creating inference requests
        """
        logical_prompt = LogicalPrompt(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        requirements = ModelRequirements(
            capabilities=capabilities or [],
            max_output_tokens=max_tokens or 4096
        )

        return cls(
            request_id=str(uuid.uuid4()),
            agent_did=agent_did,
            logical_prompt=logical_prompt,
            requirements=requirements,
            **kwargs
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "request_id": self.request_id,
            "agent_did": self.agent_did,
            "logical_prompt": self.logical_prompt.to_dict(),
            "requirements": self.requirements.to_dict(),
            "constraints": self.constraints.to_dict(),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "enable_cache": self.enable_cache,
            "enable_streaming": self.enable_streaming
        }

    def estimate_input_tokens(self) -> int:
        """Estimate input token count"""
        return self.logical_prompt.estimate_tokens()
