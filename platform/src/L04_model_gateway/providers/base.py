"""
L04 Model Gateway Layer - Base Provider Adapter

Defines the protocol that all provider adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List
import logging

from ..models import (
    InferenceRequest,
    InferenceResponse,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk
)

logger = logging.getLogger(__name__)


class ProviderAdapter(ABC):
    """
    Abstract base class for provider adapters

    All provider adapters must implement this interface to ensure
    consistent behavior across different LLM providers.
    """

    def __init__(self, provider_id: str, base_url: str, **kwargs):
        """
        Initialize provider adapter

        Args:
            provider_id: Unique identifier for this provider
            base_url: Base URL for API requests
            **kwargs: Additional provider-specific configuration
        """
        self.provider_id = provider_id
        self.base_url = base_url
        self.config = kwargs
        self.logger = logging.getLogger(f"{__name__}.{provider_id}")

    @abstractmethod
    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute a completion request

        Args:
            request: InferenceRequest with prompt and parameters
            model_id: Model to use for completion

        Returns:
            InferenceResponse with generated content

        Raises:
            ProviderError: If request fails
        """
        pass

    @abstractmethod
    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute a streaming completion request

        Args:
            request: InferenceRequest with prompt and parameters
            model_id: Model to use for completion

        Yields:
            StreamChunk objects with incremental content

        Raises:
            ProviderError: If request fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Check provider health status

        Returns:
            ProviderHealth with current status

        Raises:
            ProviderError: If health check fails
        """
        pass

    @abstractmethod
    def supports_capability(self, capability: str) -> bool:
        """
        Check if provider supports a capability

        Args:
            capability: Capability name (e.g., "vision", "tool_use")

        Returns:
            True if capability is supported
        """
        pass

    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """
        Check if provider supports a specific model

        Args:
            model_id: Model identifier

        Returns:
            True if model is supported
        """
        pass

    def get_provider_id(self) -> str:
        """Get provider identifier"""
        return self.provider_id

    def get_base_url(self) -> str:
        """Get base URL"""
        return self.base_url

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass


class BaseProviderAdapter(ProviderAdapter):
    """
    Base implementation with common functionality

    Provides default implementations for common operations.
    """

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        **kwargs
    ):
        super().__init__(provider_id, base_url, **kwargs)
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    async def _create_client(self):
        """Create HTTP client - override in subclasses"""
        import httpx
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client

    async def _close_client(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_client()

    def _estimate_tokens(self, text: str, model_id: Optional[str] = None) -> int:
        """
        Estimate token count using appropriate tokenizer.

        Uses tiktoken for OpenAI models, approximation for others.

        Args:
            text: Text to count tokens for
            model_id: Optional model ID for model-specific counting

        Returns:
            Estimated token count
        """
        try:
            from .token_counter import get_token_counter

            # Use model_id if provided, otherwise try to infer from provider
            model = model_id or getattr(self, "default_model", None)
            if model:
                counter = get_token_counter(model)
                return counter.count(text)
        except ImportError:
            pass

        # Fallback to simple heuristic
        return max(1, len(text) // 4) if text else 0

    def _estimate_message_tokens(
        self, messages: List, model_id: Optional[str] = None
    ) -> int:
        """
        Estimate token count for a list of messages.

        Args:
            messages: List of Message objects
            model_id: Optional model ID for model-specific counting

        Returns:
            Estimated token count including message overhead
        """
        try:
            from .token_counter import get_token_counter
            from ..models import Message

            model = model_id or getattr(self, "default_model", None)
            if model:
                counter = get_token_counter(model)
                # Convert to Message objects if needed
                if messages and hasattr(messages[0], "content"):
                    return counter.count_messages(messages)

        except ImportError:
            pass

        # Fallback: sum content lengths with overhead
        total = 0
        for msg in messages:
            if hasattr(msg, "content") and msg.content:
                total += self._estimate_tokens(msg.content, model_id)
            total += 4  # Message overhead
        return total

    def _create_default_health(self, status: ProviderStatus) -> ProviderHealth:
        """Create a default ProviderHealth object"""
        from datetime import datetime
        return ProviderHealth(
            provider_id=self.provider_id,
            status=status,
            circuit_state=CircuitState.CLOSED,
            last_check=datetime.utcnow()
        )
