"""
L04 Model Gateway Layer - OpenAI Provider Adapter

Adapter for OpenAI GPT models via the OpenAI Chat Completions API.

OpenAI API Documentation:
- Endpoint: https://api.openai.com/v1/chat/completions
- Auth: Authorization: Bearer {api_key}
- Streaming: SSE with delta format
"""

import httpx
import json
from typing import AsyncIterator, Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import BaseProviderAdapter
from ..models import (
    InferenceRequest,
    InferenceResponse,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk,
    TokenUsage,
    ResponseStatus,
    MessageRole,
    ProviderError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)

# Model capabilities mapping
MODEL_CAPABILITIES = {
    "gpt-4o": {
        "vision": True,
        "function_calling": True,
        "streaming": True,
        "max_tokens": 16384,
        "context_length": 128000,
    },
    "gpt-4o-mini": {
        "vision": True,
        "function_calling": True,
        "streaming": True,
        "max_tokens": 16384,
        "context_length": 128000,
    },
    "gpt-4-turbo-2024-04-09": {
        "vision": True,
        "function_calling": True,
        "streaming": True,
        "max_tokens": 4096,
        "context_length": 128000,
    },
    "gpt-4-0125-preview": {
        "vision": False,
        "function_calling": True,
        "streaming": True,
        "max_tokens": 4096,
        "context_length": 128000,
    },
    "gpt-3.5-turbo": {
        "vision": False,
        "function_calling": True,
        "streaming": True,
        "max_tokens": 4096,
        "context_length": 16385,
    },
}


class OpenAIAdapter(BaseProviderAdapter):
    """
    Adapter for OpenAI GPT models via the Chat Completions API.

    Features:
    - Full Chat Completions API support
    - Streaming via Server-Sent Events
    - Function/tool calling support
    - Vision capabilities (for supported models)
    - Proper error code mapping
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        max_retries: int = 3,
        organization: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key (required for API calls)
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            organization: Optional organization ID
            **kwargs: Additional configuration
        """
        super().__init__(
            provider_id="openai",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs
        )
        self.api_key = api_key
        self.organization = organization
        self.supported_models = set(MODEL_CAPABILITIES.keys())

    def supports_capability(self, capability: str) -> bool:
        """
        Check if OpenAI supports a capability.

        Args:
            capability: Capability name (e.g., "vision", "tool_use")

        Returns:
            True if capability is supported
        """
        supported = {
            "text", "vision", "tool_use", "streaming",
            "function_calling", "json_mode"
        }
        return capability.lower() in supported

    def supports_model(self, model_id: str) -> bool:
        """
        Check if this is an OpenAI model.

        Args:
            model_id: Model identifier

        Returns:
            True if model is supported
        """
        return model_id in self.supported_models

    async def _create_client(self):
        """Create HTTP client with OpenAI-specific headers"""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            if self.organization:
                headers["OpenAI-Organization"] = self.organization

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers
            )
        return self._client

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute chat completion via OpenAI API.

        Args:
            request: InferenceRequest with prompt and parameters
            model_id: Model to use for completion

        Returns:
            InferenceResponse with generated content

        Raises:
            ProviderError: If request fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "OpenAI API key not configured",
                {"provider": "openai"}
            )

        start_time = datetime.utcnow()

        try:
            await self._create_client()

            # Build OpenAI request
            openai_request = self._build_openai_request(request, model_id)

            # Execute request
            response = await self._client.post(
                "/chat/completions",
                json=openai_request,
                timeout=self.timeout
            )

            # Handle errors
            if response.status_code != 200:
                self._handle_error_response(response)

            # Parse response
            result = response.json()

            # Calculate latency
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Extract content from response
            content = self._extract_content(result)

            # Extract token usage
            usage = result.get("usage", {})
            token_usage = TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cached_tokens=0
            )

            # Get finish reason
            choices = result.get("choices", [])
            finish_reason = choices[0].get("finish_reason", "stop") if choices else "stop"

            return InferenceResponse(
                request_id=request.request_id,
                model_id=result.get("model", model_id),
                provider=self.provider_id,
                content=content,
                token_usage=token_usage,
                latency_ms=latency_ms,
                cached=False,
                status=ResponseStatus.SUCCESS,
                finish_reason=finish_reason,
                metadata={
                    "openai_id": result.get("id"),
                    "system_fingerprint": result.get("system_fingerprint"),
                }
            )

        except ProviderError:
            raise
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            logger.error(f"OpenAI timeout: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                "OpenAI request timed out",
                {"timeout": self.timeout}
            )
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"OpenAI error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming chat completion via OpenAI SSE.

        Args:
            request: InferenceRequest with prompt and parameters
            model_id: Model to use for completion

        Yields:
            StreamChunk objects with incremental content

        Raises:
            ProviderError: If request fails
        """
        if not self.api_key:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                "OpenAI API key not configured",
                {"provider": "openai"}
            )

        try:
            await self._create_client()

            # Build OpenAI request with streaming enabled
            openai_request = self._build_openai_request(request, model_id)
            openai_request["stream"] = True

            # Execute streaming request
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=openai_request,
                timeout=self.timeout
            ) as response:
                # Handle error status codes
                if response.status_code != 200:
                    error_body = await response.aread()
                    self._handle_error_response_from_bytes(
                        response.status_code, error_body
                    )

                # Process SSE stream
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE event
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        # Handle [DONE] signal
                        if data_str == "[DONE]":
                            yield StreamChunk(
                                request_id=request.request_id,
                                content_delta="",
                                is_final=True,
                                finish_reason="stop"
                            )
                            return

                        if not data_str.strip():
                            continue

                        try:
                            chunk_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data_str}")
                            continue

                        # Extract delta content
                        choices = chunk_data.get("choices", [])
                        if not choices:
                            continue

                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = choice.get("finish_reason")

                        if content or finish_reason:
                            yield StreamChunk(
                                request_id=request.request_id,
                                content_delta=content or "",
                                is_final=finish_reason is not None,
                                finish_reason=finish_reason
                            )

                            if finish_reason:
                                return

                # If we reach here without [DONE], emit final chunk
                yield StreamChunk(
                    request_id=request.request_id,
                    content_delta="",
                    is_final=True,
                    finish_reason="stop"
                )

        except ProviderError:
            raise
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            logger.error(f"OpenAI streaming timeout: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                "OpenAI streaming request timed out",
                {"timeout": self.timeout}
            )
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4604_STREAMING_ERROR,
                f"OpenAI streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check OpenAI API health.

        Returns:
            ProviderHealth with current status
        """
        try:
            if not self.api_key:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.UNAVAILABLE,
                    circuit_state=CircuitState.OPEN,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    metadata={"status": "unconfigured", "reason": "API key not set"}
                )

            await self._create_client()

            # Check models endpoint to verify API key
            response = await self._client.get(
                "/models",
                timeout=10
            )

            if response.status_code == 200:
                models_data = response.json()
                model_count = len(models_data.get("data", []))
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.HEALTHY,
                    circuit_state=CircuitState.CLOSED,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    metadata={"models_available": model_count}
                )
            elif response.status_code == 401:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.UNAVAILABLE,
                    circuit_state=CircuitState.OPEN,
                    last_check=datetime.utcnow(),
                    consecutive_failures=1,
                    metadata={"error": "authentication_failed"}
                )
            elif response.status_code == 429:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.DEGRADED,
                    circuit_state=CircuitState.HALF_OPEN,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    metadata={"error": "rate_limited"}
                )
            else:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.DEGRADED,
                    circuit_state=CircuitState.HALF_OPEN,
                    last_check=datetime.utcnow(),
                    consecutive_failures=1,
                    metadata={"error": f"status_{response.status_code}"}
                )

        except httpx.TimeoutException:
            logger.warning("OpenAI health check timed out")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": "timeout"}
            )
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )

    def _build_openai_request(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Build OpenAI API request from InferenceRequest.

        Args:
            request: InferenceRequest
            model_id: Model to use

        Returns:
            Dictionary for OpenAI API
        """
        # Convert messages to OpenAI format
        messages = []

        # Add system prompt as first message if present
        if request.logical_prompt.system_prompt:
            messages.append({
                "role": "system",
                "content": request.logical_prompt.system_prompt
            })

        # Add conversation messages
        for msg in request.logical_prompt.messages:
            # Skip system messages if already added system prompt
            if msg.role == MessageRole.SYSTEM and request.logical_prompt.system_prompt:
                continue

            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            messages.append(openai_msg)

        # Build request
        openai_request: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
        }

        # Add optional parameters
        if request.logical_prompt.max_tokens is not None:
            openai_request["max_tokens"] = request.logical_prompt.max_tokens

        if request.logical_prompt.temperature is not None:
            openai_request["temperature"] = request.logical_prompt.temperature

        if request.logical_prompt.top_p is not None:
            openai_request["top_p"] = request.logical_prompt.top_p

        if request.logical_prompt.presence_penalty is not None:
            openai_request["presence_penalty"] = request.logical_prompt.presence_penalty

        if request.logical_prompt.frequency_penalty is not None:
            openai_request["frequency_penalty"] = request.logical_prompt.frequency_penalty

        if request.logical_prompt.stop_sequences:
            openai_request["stop"] = request.logical_prompt.stop_sequences

        return openai_request

    def _extract_content(self, result: Dict[str, Any]) -> str:
        """
        Extract text content from OpenAI response.

        Args:
            result: OpenAI API response

        Returns:
            Extracted text content
        """
        choices = result.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})
        return message.get("content", "") or ""

    def _handle_error_response(self, response: httpx.Response):
        """
        Handle error response from OpenAI API.

        Args:
            response: HTTP response

        Raises:
            ProviderError: With appropriate error code
        """
        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            error_type = error_info.get("type", "unknown")
            error_message = error_info.get("message", "Unknown error")
            error_code = error_info.get("code")
        except Exception:
            error_type = "unknown"
            error_message = f"HTTP {response.status_code}"
            error_code = None

        self._raise_provider_error(
            response.status_code, error_type, error_message, error_code
        )

    def _handle_error_response_from_bytes(
        self, status_code: int, error_body: bytes
    ):
        """
        Handle error response from streaming request.

        Args:
            status_code: HTTP status code
            error_body: Raw error body

        Raises:
            ProviderError: With appropriate error code
        """
        try:
            error_data = json.loads(error_body)
            error_info = error_data.get("error", {})
            error_type = error_info.get("type", "unknown")
            error_message = error_info.get("message", "Unknown error")
            error_code = error_info.get("code")
        except Exception:
            error_type = "unknown"
            error_message = f"HTTP {status_code}"
            error_code = None

        self._raise_provider_error(status_code, error_type, error_message, error_code)

    def _handle_http_error(self, e: httpx.HTTPStatusError):
        """
        Handle HTTP status error.

        Args:
            e: HTTP status error

        Raises:
            ProviderError: With appropriate error code
        """
        self._handle_error_response(e.response)

    def _raise_provider_error(
        self,
        status_code: int,
        error_type: str,
        error_message: str,
        error_code: Optional[str] = None
    ):
        """
        Raise appropriate ProviderError based on error info.

        Args:
            status_code: HTTP status code
            error_type: OpenAI error type
            error_message: Error message
            error_code: OpenAI error code

        Raises:
            ProviderError: With appropriate error code
        """
        logger.error(
            f"OpenAI API error: {status_code} - {error_type}: {error_message}"
        )

        # Map HTTP status codes to L04 error codes
        if status_code == 401:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                f"OpenAI authentication failed: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 429:
            raise ProviderError(
                L04ErrorCode.E4402_PROVIDER_RATE_LIMIT,
                f"OpenAI rate limit exceeded: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 400:
            # Check for model not found error
            if error_code == "model_not_found":
                raise ProviderError(
                    L04ErrorCode.E4207_MODEL_NOT_SUPPORTED,
                    f"Model not found: {error_message}",
                    {"status_code": status_code, "error_type": error_type}
                )
            raise ProviderError(
                L04ErrorCode.E4500_INVALID_REQUEST,
                f"Invalid request to OpenAI: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 404:
            raise ProviderError(
                L04ErrorCode.E4207_MODEL_NOT_SUPPORTED,
                f"Model or endpoint not found: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code >= 500:
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"OpenAI server error: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        else:
            raise ProviderError(
                L04ErrorCode.E4206_PROVIDER_API_ERROR,
                f"OpenAI API error: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
