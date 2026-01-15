"""
L04 Model Gateway Layer - Models Package

Exports all model classes for convenient imports.
"""

from .error_codes import (
    ErrorCategory,
    L04ErrorCode,
    L04Error,
    ConfigurationError,
    RoutingError,
    ProviderError,
    CacheError,
    RateLimitError,
    ValidationError,
    ResponseError,
    CircuitBreakerError
)

from .inference_request import (
    MessageRole,
    Message,
    LogicalPrompt,
    ModelRequirements,
    RequestConstraints,
    InferenceRequest
)

from .inference_response import (
    ResponseStatus,
    TokenUsage,
    CostBreakdown,
    ToolCall,
    InferenceResponse,
    StreamChunk
)

from .model_config import (
    ModelStatus,
    ModelCapability,
    ProvisionedThroughput,
    QualityScores,
    ModelCapabilities,
    ModelConfig
)

from .provider_config import (
    ProviderStatus,
    CircuitState,
    ProviderHealth,
    ProviderConfig
)

from .routing_config import (
    RoutingStrategy,
    LatencyClass,
    RoutingDecision,
    RoutingRules
)

__all__ = [
    # Error codes
    "ErrorCategory",
    "L04ErrorCode",
    "L04Error",
    "ConfigurationError",
    "RoutingError",
    "ProviderError",
    "CacheError",
    "RateLimitError",
    "ValidationError",
    "ResponseError",
    "CircuitBreakerError",

    # Inference request
    "MessageRole",
    "Message",
    "LogicalPrompt",
    "ModelRequirements",
    "RequestConstraints",
    "InferenceRequest",

    # Inference response
    "ResponseStatus",
    "TokenUsage",
    "CostBreakdown",
    "ToolCall",
    "InferenceResponse",
    "StreamChunk",

    # Model config
    "ModelStatus",
    "ModelCapability",
    "ProvisionedThroughput",
    "QualityScores",
    "ModelCapabilities",
    "ModelConfig",

    # Provider config
    "ProviderStatus",
    "CircuitState",
    "ProviderHealth",
    "ProviderConfig",

    # Routing config
    "RoutingStrategy",
    "LatencyClass",
    "RoutingDecision",
    "RoutingRules"
]
