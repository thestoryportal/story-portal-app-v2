"""
L04 Model Gateway Layer - Anthropic Provider Adapter

Adapter for Anthropic Claude models via the Anthropic Messages API.

Anthropic API Documentation:
- Endpoint: https://api.anthropic.com/v1/messages
- Auth: x-api-key header
- Streaming: SSE with content_block_delta events
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

# Anthropic API version - pinned for stability
ANTHROPIC_API_VERSION = "2023-06-01"

# Model capabilities mapping
MODEL_CAPABILITIES = {
    "claude-opus-4-5-20251101": {
        "vision": True,
        "tool_use": True,
        "streaming": True,
        "max_tokens": 8192,
        "context_length": 200000,
    },
    "claude-sonnet-4-20250514": {
        "vision": True,
        "tool_use": True,
        "streaming": True,
        "max_tokens": 8192,
        "context_length": 200000,
    },
    "claude-3-5-sonnet-20241022": {
        "vision": True,
        "tool_use": True,
        "streaming": True,
        "max_tokens": 8192,
        "context_length": 200000,
    },
    "claude-3-opus-20240229": {
        "vision": True,
        "tool_use": True,
        "streaming": True,
        "max_tokens": 4096,
        "context_length": 200000,
    },
    "claude-3-haiku-20240307": {
        "vision": False,
        "tool_use": True,
        "streaming": True,
        "max_tokens": 4096,
        "context_length": 200000,
    },
}


class AnthropicAdapter(BaseProviderAdapter):
    """
    Adapter for Anthropic Claude models via the Messages API.

    Features:
    - Full Messages API support with system prompts
    - Streaming via Server-Sent Events
    - Tool/function calling support
    - Vision capabilities (for supported models)
    - Proper error code mapping
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize Anthropic adapter.

        Args:
            api_key: Anthropic API key (required for API calls)
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Additional configuration
        """
        super().__init__(
            provider_id="anthropic",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs
        )
        self.api_key = api_key
        self.supported_models = set(MODEL_CAPABILITIES.keys())

    def supports_capability(self, capability: str) -> bool:
        """
        Check if Anthropic supports a capability.

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
        Check if this is an Anthropic model.

        Args:
            model_id: Model identifier

        Returns:
            True if model is supported
        """
        return model_id in self.supported_models

    async def _create_client(self):
        """Create HTTP client with Anthropic-specific headers"""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "anthropic-version": ANTHROPIC_API_VERSION,
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key

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
        Execute completion via Anthropic Messages API.

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
                "Anthropic API key not configured",
                {"provider": "anthropic"}
            )

        start_time = datetime.utcnow()

        try:
            await self._create_client()

            # Build Anthropic request
            anthropic_request = self._build_anthropic_request(request, model_id)

            # Execute request
            response = await self._client.post(
                "/v1/messages",
                json=anthropic_request,
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
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cached_tokens=usage.get("cache_read_input_tokens", 0)
            )

            # Map stop reason
            finish_reason = self._map_stop_reason(result.get("stop_reason"))

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
                    "anthropic_id": result.get("id"),
                    "stop_sequence": result.get("stop_sequence"),
                }
            )

        except ProviderError:
            raise
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            logger.error(f"Anthropic timeout: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                "Anthropic request timed out",
                {"timeout": self.timeout}
            )
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"Anthropic error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming completion via Anthropic SSE.

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
                "Anthropic API key not configured",
                {"provider": "anthropic"}
            )

        try:
            await self._create_client()

            # Build Anthropic request with streaming enabled
            anthropic_request = self._build_anthropic_request(request, model_id)
            anthropic_request["stream"] = True

            # Execute streaming request
            async with self._client.stream(
                "POST",
                "/v1/messages",
                json=anthropic_request,
                timeout=self.timeout
            ) as response:
                # Handle error status codes
                if response.status_code != 200:
                    error_body = await response.aread()
                    self._handle_error_response_from_bytes(
                        response.status_code, error_body
                    )

                # Process SSE stream
                accumulated_text = ""
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE event
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        # Handle [DONE] or empty data
                        if data_str == "[DONE]" or not data_str.strip():
                            continue

                        try:
                            event_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data_str}")
                            continue

                        # Process different event types
                        event_type = event_data.get("type")

                        if event_type == "content_block_delta":
                            delta = event_data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                accumulated_text += text
                                yield StreamChunk(
                                    request_id=request.request_id,
                                    content_delta=text,
                                    is_final=False
                                )

                        elif event_type == "message_stop":
                            yield StreamChunk(
                                request_id=request.request_id,
                                content_delta="",
                                is_final=True,
                                finish_reason="stop"
                            )
                            return

                        elif event_type == "message_delta":
                            # Final message delta with stop reason
                            delta = event_data.get("delta", {})
                            stop_reason = delta.get("stop_reason")
                            if stop_reason:
                                yield StreamChunk(
                                    request_id=request.request_id,
                                    content_delta="",
                                    is_final=True,
                                    finish_reason=self._map_stop_reason(stop_reason)
                                )
                                return

                # If we reach here without message_stop, emit final chunk
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
            logger.error(f"Anthropic streaming timeout: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                "Anthropic streaming request timed out",
                {"timeout": self.timeout}
            )
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4604_STREAMING_ERROR,
                f"Anthropic streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check Anthropic API health.

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

            # Make a minimal API call to verify credentials
            # Using a simple messages request with minimal tokens
            test_request = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }

            response = await self._client.post(
                "/v1/messages",
                json=test_request,
                timeout=10
            )

            if response.status_code == 200:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.HEALTHY,
                    circuit_state=CircuitState.CLOSED,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    metadata={"models_available": len(self.supported_models)}
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
            logger.warning("Anthropic health check timed out")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": "timeout"}
            )
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )

    def _build_anthropic_request(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Build Anthropic API request from InferenceRequest.

        Args:
            request: InferenceRequest
            model_id: Model to use

        Returns:
            Dictionary for Anthropic API
        """
        # Convert messages to Anthropic format
        messages = []

        for msg in request.logical_prompt.messages:
            # Skip system messages - they go in the system field
            if msg.role == MessageRole.SYSTEM:
                continue

            anthropic_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            messages.append(anthropic_msg)

        # Build request
        anthropic_request: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "max_tokens": request.logical_prompt.max_tokens or 4096,
        }

        # Add system prompt if present
        if request.logical_prompt.system_prompt:
            anthropic_request["system"] = request.logical_prompt.system_prompt

        # Add optional parameters
        if request.logical_prompt.temperature is not None:
            anthropic_request["temperature"] = request.logical_prompt.temperature

        if request.logical_prompt.top_p is not None:
            anthropic_request["top_p"] = request.logical_prompt.top_p

        if request.logical_prompt.stop_sequences:
            anthropic_request["stop_sequences"] = request.logical_prompt.stop_sequences

        return anthropic_request

    def _extract_content(self, result: Dict[str, Any]) -> str:
        """
        Extract text content from Anthropic response.

        Args:
            result: Anthropic API response

        Returns:
            Extracted text content
        """
        content_blocks = result.get("content", [])
        text_parts = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "".join(text_parts)

    def _map_stop_reason(self, stop_reason: Optional[str]) -> str:
        """
        Map Anthropic stop reason to standard format.

        Args:
            stop_reason: Anthropic stop reason

        Returns:
            Standardized stop reason
        """
        if not stop_reason:
            return "stop"

        mapping = {
            "end_turn": "stop",
            "stop_sequence": "stop",
            "max_tokens": "length",
            "tool_use": "tool_calls",
        }
        return mapping.get(stop_reason, stop_reason)

    def _handle_error_response(self, response: httpx.Response):
        """
        Handle error response from Anthropic API.

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
        except Exception:
            error_type = "unknown"
            error_message = f"HTTP {response.status_code}"

        self._raise_provider_error(
            response.status_code, error_type, error_message
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
        except Exception:
            error_type = "unknown"
            error_message = f"HTTP {status_code}"

        self._raise_provider_error(status_code, error_type, error_message)

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
        self, status_code: int, error_type: str, error_message: str
    ):
        """
        Raise appropriate ProviderError based on error info.

        Args:
            status_code: HTTP status code
            error_type: Anthropic error type
            error_message: Error message

        Raises:
            ProviderError: With appropriate error code
        """
        logger.error(
            f"Anthropic API error: {status_code} - {error_type}: {error_message}"
        )

        # Map HTTP status codes to L04 error codes
        if status_code == 401:
            raise ProviderError(
                L04ErrorCode.E4203_PROVIDER_AUTH_FAILED,
                f"Anthropic authentication failed: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 429:
            raise ProviderError(
                L04ErrorCode.E4402_PROVIDER_RATE_LIMIT,
                f"Anthropic rate limit exceeded: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 400:
            raise ProviderError(
                L04ErrorCode.E4500_INVALID_REQUEST,
                f"Invalid request to Anthropic: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code == 404:
            raise ProviderError(
                L04ErrorCode.E4207_MODEL_NOT_SUPPORTED,
                f"Model not found: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        elif status_code >= 500:
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"Anthropic server error: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
        else:
            raise ProviderError(
                L04ErrorCode.E4206_PROVIDER_API_ERROR,
                f"Anthropic API error: {error_message}",
                {"status_code": status_code, "error_type": error_type}
            )
