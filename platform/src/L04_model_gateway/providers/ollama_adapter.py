"""
L04 Model Gateway Layer - Ollama Provider Adapter

Adapter for local Ollama models.
"""

import httpx
import json
from typing import AsyncIterator, Dict, Any, List
from datetime import datetime, timezone
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


class OllamaAdapter(BaseProviderAdapter):
    """
    Adapter for Ollama local models

    Ollama provides a local API compatible with OpenAI's format.
    Default endpoint: http://localhost:11434
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 180,  # Increased from 60 for slower local hardware
        **kwargs
    ):
        super().__init__(
            provider_id="ollama",
            base_url=base_url,
            timeout=timeout,
            **kwargs
        )
        self.supported_models = {
            "llama3.1:8b",
            "llama3.2:3b",
            "llama3.2:1b",
            "llava-llama3:latest"
        }

    def supports_capability(self, capability: str) -> bool:
        """Check if Ollama supports a capability"""
        supported = {
            "text", "streaming", "json_mode"
        }
        # llava models support vision
        return capability.lower() in supported

    def supports_model(self, model_id: str) -> bool:
        """Check if Ollama has this model"""
        return model_id in self.supported_models

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute completion request via Ollama

        Args:
            request: InferenceRequest with prompt
            model_id: Model to use

        Returns:
            InferenceResponse with result
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Create client if needed
            await self._create_client()

            # Build Ollama request
            ollama_request = self._build_ollama_request(request, model_id)

            # Execute request
            response = await self._client.post(
                "/api/chat",
                json=ollama_request,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            result = response.json()

            # Calculate latency
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            # Build InferenceResponse
            content = result.get("message", {}).get("content", "")

            # Extract token usage if available
            input_tokens = self._estimate_tokens(
                self._format_messages_for_estimation(request)
            )
            output_tokens = self._estimate_tokens(content)

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
                latency_ms=latency_ms,
                cached=False,
                status=ResponseStatus.SUCCESS,
                finish_reason=result.get("done_reason", "stop"),
                metadata={
                    "total_duration": result.get("total_duration"),
                    "load_duration": result.get("load_duration"),
                    "prompt_eval_count": result.get("prompt_eval_count"),
                    "eval_count": result.get("eval_count")
                }
            )

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4206_PROVIDER_API_ERROR,
                f"Ollama API error: {e.response.status_code}",
                {"status_code": e.response.status_code, "detail": str(e)}
            )
        except httpx.TimeoutException as e:
            self.logger.error(f"Ollama timeout: {e}")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                "Ollama request timed out",
                {"timeout": self.timeout}
            )
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"Ollama error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming completion via Ollama

        Args:
            request: InferenceRequest with prompt
            model_id: Model to use

        Yields:
            StreamChunk objects with incremental content
        """
        try:
            # Create client if needed
            await self._create_client()

            # Build Ollama request with streaming enabled
            ollama_request = self._build_ollama_request(request, model_id)
            ollama_request["stream"] = True

            # Execute streaming request
            async with self._client.stream(
                "POST",
                "/api/chat",
                json=ollama_request,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()

                # Process streaming chunks
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)

                        # Extract content delta
                        content_delta = chunk_data.get("message", {}).get("content", "")
                        is_final = chunk_data.get("done", False)

                        yield StreamChunk(
                            request_id=request.request_id,
                            content_delta=content_delta,
                            is_final=is_final,
                            finish_reason=chunk_data.get("done_reason") if is_final else None
                        )

                        if is_final:
                            break

                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse streaming chunk: {line}")
                        continue

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama streaming HTTP error: {e}")
            raise ProviderError(
                L04ErrorCode.E4206_PROVIDER_API_ERROR,
                f"Ollama streaming API error: {e.response.status_code}",
                {"status_code": e.response.status_code}
            )
        except Exception as e:
            self.logger.error(f"Ollama streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4604_STREAMING_ERROR,
                f"Ollama streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check Ollama health status

        Returns:
            ProviderHealth with current status
        """
        try:
            # Create client if needed
            await self._create_client()

            # Try to list models as a health check
            response = await self._client.get(
                "/api/tags",
                timeout=5
            )
            response.raise_for_status()

            # If we get here, Ollama is healthy
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.HEALTHY,
                circuit_state=CircuitState.CLOSED,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                average_latency_ms=None,
                error_rate=0.0,
                metadata={"models_available": len(response.json().get("models", []))}
            )

        except httpx.TimeoutException:
            self.logger.warning("Ollama health check timed out")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=1,
                metadata={"error": "timeout"}
            )
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )

    def _build_ollama_request(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Build Ollama API request from InferenceRequest

        Args:
            request: InferenceRequest
            model_id: Model to use

        Returns:
            Dictionary for Ollama API
        """
        # Convert messages to Ollama format
        messages = []

        # Add system prompt if present
        if request.logical_prompt.system_prompt:
            messages.append({
                "role": "system",
                "content": request.logical_prompt.system_prompt
            })

        # Add conversation messages
        for msg in request.logical_prompt.messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        # Build request
        ollama_request = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.logical_prompt.temperature
            }
        }

        # Add optional parameters
        if request.logical_prompt.max_tokens:
            ollama_request["options"]["num_predict"] = request.logical_prompt.max_tokens

        if request.logical_prompt.top_p is not None:
            ollama_request["options"]["top_p"] = request.logical_prompt.top_p

        if request.logical_prompt.stop_sequences:
            ollama_request["options"]["stop"] = request.logical_prompt.stop_sequences

        return ollama_request

    def _format_messages_for_estimation(self, request: InferenceRequest) -> str:
        """Format messages for token estimation"""
        text = request.logical_prompt.system_prompt or ""
        for msg in request.logical_prompt.messages:
            text += f"\n{msg.role.value}: {msg.content}"
        return text
