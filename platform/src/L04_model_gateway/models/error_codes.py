"""
L04 Model Gateway Layer - Error Code Definitions

Error code range: E4000-E4999
Following pattern from L02 (E2xxx) and L03 (E3xxx)
"""

from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Error categories for the Model Gateway Layer"""
    CONFIGURATION = "configuration"
    ROUTING = "routing"
    PROVIDER = "provider"
    CACHE = "cache"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    RESPONSE = "response"
    CIRCUIT_BREAKER = "circuit_breaker"


class L04ErrorCode(Enum):
    """Error codes for L04 Model Gateway Layer (E4000-E4999)"""

    # Configuration errors (E4000-E4099)
    E4000_CONFIGURATION_INVALID = ("E4000", "Invalid configuration", ErrorCategory.CONFIGURATION)
    E4001_MODEL_NOT_FOUND = ("E4001", "Model not found in registry", ErrorCategory.CONFIGURATION)
    E4002_PROVIDER_NOT_CONFIGURED = ("E4002", "Provider not configured", ErrorCategory.CONFIGURATION)
    E4003_INVALID_MODEL_CONFIG = ("E4003", "Invalid model configuration", ErrorCategory.CONFIGURATION)
    E4004_REGISTRY_INITIALIZATION_FAILED = ("E4004", "Model registry initialization failed", ErrorCategory.CONFIGURATION)
    E4005_MISSING_REQUIRED_CONFIG = ("E4005", "Missing required configuration parameter", ErrorCategory.CONFIGURATION)

    # Routing errors (E4100-E4199)
    E4100_ROUTING_FAILED = ("E4100", "Routing failed", ErrorCategory.ROUTING)
    E4101_NO_CAPABLE_MODEL = ("E4101", "No model found matching requirements", ErrorCategory.ROUTING)
    E4102_ALL_MODELS_UNAVAILABLE = ("E4102", "All candidate models unavailable", ErrorCategory.ROUTING)
    E4103_CAPABILITY_MISMATCH = ("E4103", "Required capabilities not supported", ErrorCategory.ROUTING)
    E4104_CONTEXT_LENGTH_EXCEEDED = ("E4104", "Prompt exceeds model context length", ErrorCategory.ROUTING)
    E4105_INVALID_ROUTING_STRATEGY = ("E4105", "Invalid routing strategy specified", ErrorCategory.ROUTING)
    E4106_COST_LIMIT_EXCEEDED = ("E4106", "Request would exceed cost limit", ErrorCategory.ROUTING)
    E4107_DATA_RESIDENCY_VIOLATION = ("E4107", "No models available in required regions", ErrorCategory.ROUTING)

    # Provider errors (E4200-E4299)
    E4200_PROVIDER_ERROR = ("E4200", "Provider error", ErrorCategory.PROVIDER)
    E4201_PROVIDER_UNAVAILABLE = ("E4201", "Provider unavailable", ErrorCategory.PROVIDER)
    E4202_PROVIDER_TIMEOUT = ("E4202", "Provider request timed out", ErrorCategory.PROVIDER)
    E4203_PROVIDER_AUTH_FAILED = ("E4203", "Provider authentication failed", ErrorCategory.PROVIDER)
    E4204_PROVIDER_RATE_LIMITED = ("E4204", "Provider rate limit exceeded", ErrorCategory.PROVIDER)
    E4205_PROVIDER_INVALID_RESPONSE = ("E4205", "Provider returned invalid response", ErrorCategory.PROVIDER)
    E4206_PROVIDER_API_ERROR = ("E4206", "Provider API error", ErrorCategory.PROVIDER)
    E4207_MODEL_NOT_SUPPORTED = ("E4207", "Model not supported by provider", ErrorCategory.PROVIDER)
    E4208_STREAMING_NOT_SUPPORTED = ("E4208", "Streaming not supported", ErrorCategory.PROVIDER)

    # Cache errors (E4300-E4399)
    E4300_CACHE_ERROR = ("E4300", "Cache error", ErrorCategory.CACHE)
    E4301_CACHE_UNAVAILABLE = ("E4301", "Cache service unavailable", ErrorCategory.CACHE)
    E4302_CACHE_WRITE_FAILED = ("E4302", "Failed to write to cache", ErrorCategory.CACHE)
    E4303_CACHE_READ_FAILED = ("E4303", "Failed to read from cache", ErrorCategory.CACHE)
    E4304_EMBEDDING_GENERATION_FAILED = ("E4304", "Embedding generation failed", ErrorCategory.CACHE)
    E4305_SIMILARITY_SEARCH_FAILED = ("E4305", "Similarity search failed", ErrorCategory.CACHE)

    # Rate limit errors (E4400-E4499)
    E4400_RATE_LIMIT_EXCEEDED = ("E4400", "Rate limit exceeded", ErrorCategory.RATE_LIMIT)
    E4401_AGENT_RATE_LIMIT = ("E4401", "Agent rate limit exceeded", ErrorCategory.RATE_LIMIT)
    E4402_PROVIDER_RATE_LIMIT = ("E4402", "Provider rate limit exceeded", ErrorCategory.RATE_LIMIT)
    E4403_TOKEN_QUOTA_EXCEEDED = ("E4403", "Token quota exceeded", ErrorCategory.RATE_LIMIT)
    E4404_RPM_LIMIT_EXCEEDED = ("E4404", "Requests per minute limit exceeded", ErrorCategory.RATE_LIMIT)
    E4405_TPM_LIMIT_EXCEEDED = ("E4405", "Tokens per minute limit exceeded", ErrorCategory.RATE_LIMIT)

    # Request validation errors (E4500-E4599)
    E4500_INVALID_REQUEST = ("E4500", "Invalid request", ErrorCategory.VALIDATION)
    E4501_MISSING_REQUIRED_FIELD = ("E4501", "Missing required field", ErrorCategory.VALIDATION)
    E4502_INVALID_FIELD_VALUE = ("E4502", "Invalid field value", ErrorCategory.VALIDATION)
    E4503_PROMPT_TOO_LARGE = ("E4503", "Prompt exceeds maximum size", ErrorCategory.VALIDATION)
    E4504_INVALID_AGENT_DID = ("E4504", "Invalid agent DID", ErrorCategory.VALIDATION)
    E4505_AUTHORIZATION_FAILED = ("E4505", "Authorization failed", ErrorCategory.VALIDATION)
    E4506_INVALID_CAPABILITY = ("E4506", "Invalid capability specified", ErrorCategory.VALIDATION)

    # Response processing errors (E4600-E4699)
    E4600_RESPONSE_PROCESSING_FAILED = ("E4600", "Response processing failed", ErrorCategory.RESPONSE)
    E4601_TOKEN_COUNTING_FAILED = ("E4601", "Token counting failed", ErrorCategory.RESPONSE)
    E4602_RESPONSE_NORMALIZATION_FAILED = ("E4602", "Response normalization failed", ErrorCategory.RESPONSE)
    E4603_INVALID_RESPONSE_FORMAT = ("E4603", "Invalid response format", ErrorCategory.RESPONSE)
    E4604_STREAMING_ERROR = ("E4604", "Streaming error", ErrorCategory.RESPONSE)

    # Circuit breaker errors (E4700-E4799)
    E4700_CIRCUIT_BREAKER_OPEN = ("E4700", "Circuit breaker open", ErrorCategory.CIRCUIT_BREAKER)
    E4701_PROVIDER_CIRCUIT_OPEN = ("E4701", "Provider circuit breaker open", ErrorCategory.CIRCUIT_BREAKER)
    E4702_MODEL_CIRCUIT_OPEN = ("E4702", "Model circuit breaker open", ErrorCategory.CIRCUIT_BREAKER)
    E4703_HEALTH_CHECK_FAILED = ("E4703", "Health check failed", ErrorCategory.CIRCUIT_BREAKER)
    E4704_FAILURE_THRESHOLD_EXCEEDED = ("E4704", "Failure threshold exceeded", ErrorCategory.CIRCUIT_BREAKER)

    def __init__(self, code: str, message: str, category: ErrorCategory):
        self.code = code
        self.message = message
        self.category = category

    @property
    def code_value(self) -> str:
        """Get the error code string (e.g., 'E4000')"""
        return self.code

    @property
    def default_message(self) -> str:
        """Get the default error message"""
        return self.message

    @classmethod
    def from_code(cls, code: str) -> Optional['L04ErrorCode']:
        """Look up an error code by its code string"""
        for error in cls:
            if error.code == code:
                return error
        return None


class L04Error(Exception):
    """Base exception for L04 Model Gateway Layer"""

    def __init__(
        self,
        error_code: L04ErrorCode,
        message: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.message = message or error_code.default_message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization"""
        return {
            "error_code": self.error_code.code_value,
            "message": self.message,
            "category": self.error_code.category.value,
            "details": self.details
        }

    def __str__(self) -> str:
        details_str = f" - {self.details}" if self.details else ""
        return f"[{self.error_code.code_value}] {self.message}{details_str}"


# Convenience exception classes for each category
class ConfigurationError(L04Error):
    """Configuration-related errors"""
    pass


class RoutingError(L04Error):
    """Routing-related errors"""
    pass


class ProviderError(L04Error):
    """Provider-related errors"""
    pass


class CacheError(L04Error):
    """Cache-related errors"""
    pass


class RateLimitError(L04Error):
    """Rate limiting errors"""
    pass


class ValidationError(L04Error):
    """Validation errors"""
    pass


class ResponseError(L04Error):
    """Response processing errors"""
    pass


class CircuitBreakerError(L04Error):
    """Circuit breaker errors"""
    pass
