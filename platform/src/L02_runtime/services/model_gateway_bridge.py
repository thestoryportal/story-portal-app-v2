"""
L02 Agent Runtime - Model Gateway Bridge

HTTP Bridge to integrate L04 Model Gateway with L02 Agent Runtime.
Allows agents to request LLM inference through the gateway via HTTP.

IMPORTANT: This bridge uses HTTP to communicate with L04.
Never import L04 modules directly - use the HTTP API endpoints.
"""

import os
import logging
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
import json

import httpx

logger = logging.getLogger(__name__)

# Default L04 configuration
DEFAULT_L04_BASE_URL = "http://localhost:8004"
DEFAULT_TIMEOUT = 300.0  # 5 minutes for LLM requests


class ModelGatewayBridgeError(Exception):
    """Base exception for ModelGatewayBridge errors"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ModelGatewayBridge:
    """
    HTTP Bridge between L02 Agent Runtime and L04 Model Gateway

    Provides agents with access to LLM inference capabilities
    through the L04 HTTP API. Does NOT import L04 modules directly.

    Pattern: HTTP Bridge (following CLAUDE.md requirements)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        Initialize HTTP bridge

        Args:
            base_url: L04 Model Gateway URL (default: http://localhost:8004)
            timeout: HTTP request timeout in seconds (default: 300)
        """
        self.base_url = base_url or os.getenv("L04_BASE_URL", DEFAULT_L04_BASE_URL)
        self.timeout = timeout or float(os.getenv("L04_TIMEOUT", DEFAULT_TIMEOUT))
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"ModelGatewayBridge initialized (url={self.base_url})")

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client

    async def request_inference(
        self,
        agent_did: str,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        capabilities: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        streaming: bool = False,
        enable_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Request LLM inference for an agent

        Args:
            agent_did: Agent DID making the request
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum output tokens
            capabilities: Required model capabilities (e.g., ["text", "tool_use"])
            model_id: Specific model to use (optional)
            streaming: Whether to use streaming mode
            enable_cache: Whether to enable semantic caching
            **kwargs: Additional parameters

        Returns:
            Dictionary with inference response:
            - streaming=False: Full response with content, token_usage, etc.
            - streaming=True: Dict with 'streaming' key and 'stream' async generator

        Raises:
            ModelGatewayBridgeError: On inference failure
        """
        client = await self._ensure_client()

        # Build request payload
        payload = {
            "agent_did": agent_did,
            "messages": messages,
            "temperature": temperature,
            "enable_cache": enable_cache
        }

        if system_prompt:
            payload["system_prompt"] = system_prompt
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if model_id:
            payload["model_id"] = model_id
        if capabilities:
            payload["capabilities"] = capabilities

        # Add any extra kwargs to metadata
        if kwargs:
            payload["metadata"] = kwargs

        try:
            if streaming:
                return await self._request_streaming(client, payload)
            else:
                return await self._request_sync(client, payload)

        except httpx.TimeoutException as e:
            logger.error(f"L04 request timeout for agent {agent_did}: {e}")
            raise ModelGatewayBridgeError(
                f"L04 request timed out after {self.timeout}s",
                error_code="E2050",
                details={"timeout": self.timeout, "agent_did": agent_did}
            )
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to L04 at {self.base_url}: {e}")
            raise ModelGatewayBridgeError(
                f"Cannot connect to L04 Model Gateway at {self.base_url}",
                error_code="E2051",
                details={"base_url": self.base_url}
            )
        except Exception as e:
            logger.error(f"Inference request failed for agent {agent_did}: {e}")
            raise ModelGatewayBridgeError(
                f"Inference request failed: {str(e)}",
                error_code="E2052",
                details={"error": str(e), "agent_did": agent_did}
            )

    async def _request_sync(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute synchronous inference request"""
        response = await client.post("/api/inference", json=payload)

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            raise ModelGatewayBridgeError(
                f"L04 inference failed: {response.status_code}",
                error_code=error_data.get("error_code", "E4999"),
                details=error_data
            )

        data = response.json()
        return {
            "streaming": False,
            "request_id": data.get("request_id"),
            "model_id": data.get("model_id"),
            "provider": data.get("provider"),
            "content": data.get("content"),
            "token_usage": data.get("token_usage", {}),
            "latency_ms": data.get("latency_ms"),
            "cached": data.get("cached", False),
            "finish_reason": data.get("finish_reason"),
            "metadata": data.get("metadata", {})
        }

    async def _request_streaming(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute streaming inference request"""

        async def stream_generator() -> AsyncIterator[Dict[str, Any]]:
            """Generate streaming chunks from SSE response"""
            async with client.stream("POST", "/api/inference/stream", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise ModelGatewayBridgeError(
                        f"L04 streaming failed: {response.status_code}",
                        error_code="E4604",
                        details={"response": error_text.decode()}
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse SSE format
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)

                            # Check for error in chunk
                            if "error" in chunk:
                                error = chunk["error"]
                                raise ModelGatewayBridgeError(
                                    error.get("message", "Streaming error"),
                                    error_code=error.get("error_code", "E4604"),
                                    details=error.get("details")
                                )

                            yield {
                                "request_id": chunk.get("request_id"),
                                "content_delta": chunk.get("content_delta", ""),
                                "is_final": chunk.get("is_final", False),
                                "token_count": chunk.get("token_count"),
                                "finish_reason": chunk.get("finish_reason")
                            }

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE chunk: {data_str}")
                            continue

        return {
            "streaming": True,
            "stream": stream_generator()
        }

    async def check_gateway_health(self) -> Dict[str, Any]:
        """
        Check Model Gateway health status

        Returns:
            Health status dictionary with provider info
        """
        try:
            client = await self._ensure_client()
            response = await client.get("/api/inference/health", timeout=5.0)

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Gateway health check failed: {e}")
            return {
                "status": "unavailable",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from L04 dynamically

        Returns:
            List of model dictionaries with capabilities
        """
        try:
            client = await self._ensure_client()
            response = await client.get("/api/models", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                logger.info(f"Fetched {len(models)} models from L04")
                return models

        except Exception as e:
            logger.warning(f"Failed to fetch models from L04, using static fallback: {e}")

        # Fallback to static list if L04 is unavailable
        return self._get_static_model_list()

    def _get_static_model_list(self) -> List[Dict[str, Any]]:
        """
        Get static fallback model list

        Returns:
            List of known Claude Code models
        """
        return [
            {
                "model_id": "claude-opus-4-5-20251101",
                "provider": "claude_code",
                "display_name": "Claude Opus 4.5",
                "capabilities": ["text", "code_generation", "reasoning", "tool_use", "vision"],
                "context_window": 200000,
                "max_output_tokens": 8192
            },
            {
                "model_id": "claude-sonnet-4-20250514",
                "provider": "claude_code",
                "display_name": "Claude Sonnet 4",
                "capabilities": ["text", "code_generation", "reasoning", "tool_use", "vision"],
                "context_window": 200000,
                "max_output_tokens": 8192
            }
        ]

    async def close(self):
        """Cleanup HTTP client resources"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("ModelGatewayBridge closed")

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
