"""
L04 Model Gateway Layer - Anthropic Provider Adapter

Adapter for Anthropic Claude models via the Anthropic API.

Supports both API key and environment variable configuration.
"""

from typing import AsyncIterator, Optional
from datetime import datetime
import os
import logging
import json

from .base import BaseProviderAdapter
from ..models import (
    InferenceRequest,
    InferenceResponse,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk,
    ProviderError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseProviderAdapter):
    """
    Adapter for Anthropic Claude models

    Supports API key from parameter or ANTHROPIC_API_KEY environment variable.
    Falls back to graceful degradation if no API key is provided.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 30,
        **kwargs
    ):
        super().__init__(
            provider_id="anthropic",
            base_url=base_url,
            timeout=timeout,
            **kwargs
        )
        # Try API key from parameter, then environment variable
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.api_version = "2023-06-01"  # Anthropic API version

        if not self.api_key:
            logger.warning(
                "Anthropic adapter initialized without API key. "
                "Set ANTHROPIC_API_KEY environment variable to enable Claude models."
            )
        else:
            logger.info("Anthropic adapter initialized successfully")

        self.supported_models = {
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307"
        }

    def supports_capability(self, capability: str) -> bool:
        """Check if Anthropic supports a capability"""
        supported = {
            "text", "vision", "tool_use", "streaming",
            "function_calling", "json_mode"
        }
        return capability.lower() in supported

    def supports_model(self, model_id: str) -> bool:
        """Check if this is an Anthropic model"""
        return model_id in self.supported_models

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute completion via Anthropic API

        Args:
            request: Inference request with prompt and parameters
            model_id: Anthropic model identifier

        Returns:
            InferenceResponse with generated text

        Raises:
            ProviderError: If API key is missing or API call fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.",
                {"provider": "anthropic", "model_id": model_id}
            )

        try:
            import httpx

            # Build messages for Anthropic API
            messages = [{"role": "user", "content": request.prompt}]

            # Build request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": request.max_tokens or 1024,
                "temperature": request.temperature or 0.7,
            }

            # Add system prompt if provided
            if request.system_prompt:
                payload["system"] = request.system_prompt

            # Add optional parameters
            if request.top_p is not None:
                payload["top_p"] = request.top_p
            if request.stop_sequences:
                payload["stop_sequences"] = request.stop_sequences

            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start_time = datetime.utcnow()
                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.api_version,
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code != 200:
                    error_detail = response.json() if response.text else {}
                    raise ProviderError(
                        L04ErrorCode.E4202_PROVIDER_API_ERROR,
                        f"Anthropic API error: {response.status_code}",
                        {"status_code": response.status_code, "detail": error_detail}
                    )

                result = response.json()
                end_time = datetime.utcnow()

                # Extract completion from Anthropic's response format
                generated_text = result["content"][0]["text"]
                usage = result.get("usage", {})

                return InferenceResponse(
                    generated_text=generated_text,
                    model_id=model_id,
                    provider_id=self.provider_id,
                    latency_ms=int((end_time - start_time).total_seconds() * 1000),
                    tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    finish_reason=result.get("stop_reason", "end_turn"),
                    metadata={
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "model": result.get("model", model_id),
                        "stop_reason": result.get("stop_reason"),
                    },
                )

        except httpx.HTTPError as e:
            logger.error(f"Anthropic HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_API_ERROR,
                f"Anthropic HTTP error: {str(e)}",
                {"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Anthropic completion error: {e}")
            raise ProviderError(
                L04ErrorCode.E4299_PROVIDER_UNKNOWN_ERROR,
                f"Anthropic error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming completion via Anthropic API

        Args:
            request: Inference request with prompt and parameters
            model_id: Anthropic model identifier

        Yields:
            StreamChunk: Individual chunks of generated text

        Raises:
            ProviderError: If API key is missing or API call fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.",
                {"provider": "anthropic", "model_id": model_id}
            )

        try:
            import httpx

            # Build messages for Anthropic API
            messages = [{"role": "user", "content": request.prompt}]

            # Build request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": request.max_tokens or 1024,
                "temperature": request.temperature or 0.7,
                "stream": True,  # Enable streaming
            }

            # Add system prompt if provided
            if request.system_prompt:
                payload["system"] = request.system_prompt

            # Add optional parameters
            if request.top_p is not None:
                payload["top_p"] = request.top_p
            if request.stop_sequences:
                payload["stop_sequences"] = request.stop_sequences

            # Make streaming API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.api_version,
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise ProviderError(
                            L04ErrorCode.E4202_PROVIDER_API_ERROR,
                            f"Anthropic streaming API error: {response.status_code}",
                            {"status_code": response.status_code, "detail": error_text.decode()}
                        )

                    # Process SSE stream
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            try:
                                chunk_data = json.loads(data_str)

                                # Handle different event types
                                event_type = chunk_data.get("type")

                                if event_type == "content_block_delta":
                                    # Extract text from delta
                                    delta = chunk_data.get("delta", {})
                                    content = delta.get("text")

                                    if content:
                                        yield StreamChunk(
                                            text=content,
                                            finish_reason=None,
                                            model_id=model_id,
                                            provider_id=self.provider_id,
                                        )

                                elif event_type == "message_stop":
                                    # Stream finished
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue

        except httpx.HTTPError as e:
            logger.error(f"Anthropic streaming HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_API_ERROR,
                f"Anthropic streaming HTTP error: {str(e)}",
                {"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4299_PROVIDER_UNKNOWN_ERROR,
                f"Anthropic streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check Anthropic API health

        Returns UNAVAILABLE if no API key is configured.
        """
        if not self.api_key:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=0,
                metadata={"reason": "API key not configured"}
            )

        try:
            import httpx

            # Test API connectivity with a minimal request
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Make a small test request
                test_payload = {
                    "model": "claude-3-haiku-20240307",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1,
                }

                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=test_payload,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.api_version,
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    return ProviderHealth(
                        provider_id=self.provider_id,
                        status=ProviderStatus.HEALTHY,
                        circuit_state=CircuitState.CLOSED,
                        last_check=datetime.utcnow(),
                        consecutive_failures=0,
                        metadata={"api_version": self.api_version}
                    )
                else:
                    return ProviderHealth(
                        provider_id=self.provider_id,
                        status=ProviderStatus.DEGRADED,
                        circuit_state=CircuitState.HALF_OPEN,
                        last_check=datetime.utcnow(),
                        consecutive_failures=1,
                        metadata={"status_code": response.status_code}
                    )

        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNHEALTHY,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )
