"""
L04 Model Gateway Layer - Mock Provider Adapter

Mock adapter for testing purposes.
"""

import asyncio
from typing import AsyncIterator
from datetime import datetime, timezone

from .base import ProviderAdapter
from ..models import (
    InferenceRequest,
    InferenceResponse,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk,
    TokenUsage,
    ResponseStatus
)


class MockAdapter(ProviderAdapter):
    """
    Mock provider adapter for testing

    Returns canned responses and allows simulating various scenarios.
    """

    def __init__(
        self,
        provider_id: str = "mock",
        base_url: str = "http://localhost:9999",
        latency_ms: int = 100,
        should_fail: bool = False,
        **kwargs
    ):
        super().__init__(provider_id, base_url, **kwargs)
        self.latency_ms = latency_ms
        self.should_fail = should_fail
        self.call_count = 0
        self.supported_models = {"mock-model", "mock-vision", "mock-tools"}

    def supports_capability(self, capability: str) -> bool:
        """Mock adapter supports all capabilities"""
        return True

    def supports_model(self, model_id: str) -> bool:
        """Check if model is supported"""
        return model_id in self.supported_models

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Return a mock completion response

        Args:
            request: InferenceRequest
            model_id: Model ID

        Returns:
            Mock InferenceResponse
        """
        self.call_count += 1

        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)

        # Simulate failure if configured
        if self.should_fail:
            from ..models import ProviderError, L04ErrorCode
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                "Mock provider configured to fail"
            )

        # Generate mock response
        last_message = request.logical_prompt.messages[-1] if request.logical_prompt.messages else None
        user_content = last_message.content if last_message else "Hello"

        content = f"Mock response to: {user_content[:50]}..."

        # Mock token usage
        input_tokens = len(user_content.split())
        output_tokens = len(content.split())

        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=0
        )

        return InferenceResponse(
            request_id=request.request_id,
            model_id=model_id,
            provider=self.provider_id,
            content=content,
            token_usage=token_usage,
            latency_ms=self.latency_ms,
            cached=False,
            status=ResponseStatus.SUCCESS,
            finish_reason="stop",
            metadata={"call_count": self.call_count, "mock": True}
        )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Return a mock streaming response

        Args:
            request: InferenceRequest
            model_id: Model ID

        Yields:
            Mock StreamChunk objects
        """
        self.call_count += 1

        # Simulate streaming with chunks
        chunks = [
            "Mock ",
            "streaming ",
            "response ",
            "to ",
            "your ",
            "request."
        ]

        for i, chunk_text in enumerate(chunks):
            await asyncio.sleep(0.05)  # Small delay between chunks

            yield StreamChunk(
                request_id=request.request_id,
                content_delta=chunk_text,
                is_final=(i == len(chunks) - 1),
                finish_reason="stop" if i == len(chunks) - 1 else None
            )

    async def health_check(self) -> ProviderHealth:
        """
        Return mock health status

        Returns:
            ProviderHealth with mock status
        """
        status = ProviderStatus.UNAVAILABLE if self.should_fail else ProviderStatus.HEALTHY
        circuit_state = CircuitState.OPEN if self.should_fail else CircuitState.CLOSED

        return ProviderHealth(
            provider_id=self.provider_id,
            status=status,
            circuit_state=circuit_state,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=1 if self.should_fail else 0,
            average_latency_ms=self.latency_ms,
            error_rate=1.0 if self.should_fail else 0.0,
            metadata={"mock": True, "call_count": self.call_count}
        )

    def set_should_fail(self, should_fail: bool):
        """Configure whether adapter should fail"""
        self.should_fail = should_fail

    def set_latency_ms(self, latency_ms: int):
        """Configure mock latency"""
        self.latency_ms = latency_ms

    def get_call_count(self) -> int:
        """Get number of times adapter was called"""
        return self.call_count

    def reset(self):
        """Reset adapter state"""
        self.call_count = 0
        self.should_fail = False
