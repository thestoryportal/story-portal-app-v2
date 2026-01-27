"""
L04 Model Gateway Layer - OpenAI Provider Adapter

Adapter for OpenAI GPT models via the OpenAI API.

Supports both API key and environment variable configuration.
"""

from typing import AsyncIterator, List, Dict, Any, Optional
from datetime import datetime, timezone
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


class OpenAIAdapter(BaseProviderAdapter):
    """
    Adapter for OpenAI GPT models

    Supports API key from parameter or OPENAI_API_KEY environment variable.
    Falls back to graceful degradation if no API key is provided.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        **kwargs
    ):
        super().__init__(
            provider_id="openai",
            base_url=base_url,
            timeout=timeout,
            **kwargs
        )
        # Try API key from parameter, then environment variable
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning(
                "OpenAI adapter initialized without API key. "
                "Set OPENAI_API_KEY environment variable to enable OpenAI models."
            )
        else:
            logger.info("OpenAI adapter initialized successfully")

        self.supported_models = {
            "gpt-4-turbo-2024-04-09",
            "gpt-4-0125-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo"
        }

    def supports_capability(self, capability: str) -> bool:
        """Check if OpenAI supports a capability"""
        supported = {
            "text", "vision", "tool_use", "streaming",
            "function_calling", "json_mode"
        }
        return capability.lower() in supported

    def supports_model(self, model_id: str) -> bool:
        """Check if this is an OpenAI model"""
        return model_id in self.supported_models

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute completion via OpenAI API

        Args:
            request: Inference request with prompt and parameters
            model_id: OpenAI model identifier

        Returns:
            InferenceResponse with generated text

        Raises:
            ProviderError: If API key is missing or API call fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
                {"provider": "openai", "model_id": model_id}
            )

        try:
            import httpx

            # Build messages from prompt
            messages = [{"role": "user", "content": request.prompt}]
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})

            # Build request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": request.temperature or 0.7,
                "max_tokens": request.max_tokens or 1024,
                "stream": False,
            }

            # Add optional parameters
            if request.top_p is not None:
                payload["top_p"] = request.top_p
            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start_time = datetime.now(timezone.utc)
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code != 200:
                    error_detail = response.json() if response.text else {}
                    raise ProviderError(
                        L04ErrorCode.E4202_PROVIDER_API_ERROR,
                        f"OpenAI API error: {response.status_code}",
                        {"status_code": response.status_code, "detail": error_detail}
                    )

                result = response.json()
                end_time = datetime.now(timezone.utc)

                # Extract completion
                generated_text = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})

                return InferenceResponse(
                    generated_text=generated_text,
                    model_id=model_id,
                    provider_id=self.provider_id,
                    latency_ms=int((end_time - start_time).total_seconds() * 1000),
                    tokens_used=usage.get("total_tokens", 0),
                    finish_reason=result["choices"][0].get("finish_reason", "stop"),
                    metadata={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "model": result.get("model", model_id),
                    },
                )

        except httpx.HTTPError as e:
            logger.error(f"OpenAI HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_API_ERROR,
                f"OpenAI HTTP error: {str(e)}",
                {"error": str(e)}
            )
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise ProviderError(
                L04ErrorCode.E4299_PROVIDER_UNKNOWN_ERROR,
                f"OpenAI error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming completion via OpenAI API

        Args:
            request: Inference request with prompt and parameters
            model_id: OpenAI model identifier

        Yields:
            StreamChunk: Individual chunks of generated text

        Raises:
            ProviderError: If API key is missing or API call fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
                {"provider": "openai", "model_id": model_id}
            )

        try:
            import httpx

            # Build messages from prompt
            messages = [{"role": "user", "content": request.prompt}]
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})

            # Build request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": request.temperature or 0.7,
                "max_tokens": request.max_tokens or 1024,
                "stream": True,  # Enable streaming
            }

            # Add optional parameters
            if request.top_p is not None:
                payload["top_p"] = request.top_p
            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            # Make streaming API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise ProviderError(
                            L04ErrorCode.E4202_PROVIDER_API_ERROR,
                            f"OpenAI streaming API error: {response.status_code}",
                            {"status_code": response.status_code, "detail": error_text.decode()}
                        )

                    # Process SSE stream
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            if data_str == "[DONE]":
                                break

                            try:
                                chunk_data = json.loads(data_str)
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content")

                                if content:
                                    yield StreamChunk(
                                        text=content,
                                        finish_reason=chunk_data["choices"][0].get("finish_reason"),
                                        model_id=model_id,
                                        provider_id=self.provider_id,
                                    )
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue

        except httpx.HTTPError as e:
            logger.error(f"OpenAI streaming HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_API_ERROR,
                f"OpenAI streaming HTTP error: {str(e)}",
                {"error": str(e)}
            )
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4299_PROVIDER_UNKNOWN_ERROR,
                f"OpenAI streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check OpenAI API health

        Tests API connectivity by calling the models endpoint.
        Returns UNAVAILABLE if no API key is configured.
        """
        if not self.api_key:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                metadata={"reason": "API key not configured"}
            )

        try:
            import httpx

            # Test API connectivity by listing models
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )

                if response.status_code == 200:
                    return ProviderHealth(
                        provider_id=self.provider_id,
                        status=ProviderStatus.HEALTHY,
                        circuit_state=CircuitState.CLOSED,
                        last_check=datetime.now(timezone.utc),
                        consecutive_failures=0,
                        metadata={"api_version": "v1"}
                    )
                else:
                    return ProviderHealth(
                        provider_id=self.provider_id,
                        status=ProviderStatus.DEGRADED,
                        circuit_state=CircuitState.HALF_OPEN,
                        last_check=datetime.now(timezone.utc),
                        consecutive_failures=1,
                        metadata={"status_code": response.status_code}
                    )

        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNHEALTHY,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )
