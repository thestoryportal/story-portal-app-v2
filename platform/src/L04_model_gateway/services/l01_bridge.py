"""
L04 Model Gateway - L01 Data Layer Bridge

Bridge between L04 Model Gateway and L01 Data Layer for persistent model usage tracking.

This bridge records model inference requests and responses in L01 for analytics,
cost tracking, and usage monitoring across the platform.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import httpx

from ..models import InferenceRequest, InferenceResponse


logger = logging.getLogger(__name__)


class L01Bridge:
    """
    Bridge between L04 Model Gateway Layer and L01 Data Layer.

    Responsibilities:
    - Record model inference usage in L01 when requests complete
    - Track token usage, latency, cost, and cache hits
    - Support agent context (DID, tenant, session) for analytics
    - Publish model usage events via L01 event stream
    - Graceful degradation when L01 is unavailable
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        """
        Initialize L01 bridge.

        Args:
            base_url: Base URL for L01 Data Layer API (default: http://localhost:8001)
            api_key: API key for L01 authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = (
            base_url
            or os.environ.get("L01_BASE_URL", "http://localhost:8001")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("L01_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.enabled = True
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"L01Bridge initialized with base_url={self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication headers."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L01Bridge initialized")

    async def record_inference(
        self,
        request: InferenceRequest,
        response: InferenceResponse,
    ) -> bool:
        """
        Record model inference usage in L01.

        Args:
            request: InferenceRequest instance
            response: InferenceResponse instance

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            client = await self._get_client()

            # Extract agent context from request
            agent_did = request.agent_did
            tenant_id = (
                request.metadata.get("tenant_id") if request.metadata else None
            )
            session_id = (
                request.metadata.get("session_id") if request.metadata else None
            )

            # Extract cost breakdown if available
            cost_input_cents = None
            cost_output_cents = None
            cost_cached_cents = None
            cost_estimate = None

            if response.cost_breakdown:
                cost_input_cents = response.cost_breakdown.input_cost_cents
                cost_output_cents = response.cost_breakdown.output_cost_cents
                cost_cached_cents = response.cost_breakdown.cached_cost_cents
                # Total cost in dollars
                cost_estimate = response.cost_breakdown.total_cost_cents / 100.0

            # Build payload
            payload = {
                "request_id": response.request_id,
                "model_provider": response.provider,
                "model_name": response.model_id,
                "input_tokens": response.token_usage.input_tokens,
                "output_tokens": response.token_usage.output_tokens,
                "cached_tokens": response.token_usage.cached_tokens,
                "total_tokens": response.token_usage.total_tokens,
                "cached": response.cached,
                "response_status": response.status.value if response.status else "success",
                "metadata": response.metadata or {},
            }

            # Add optional fields
            if agent_did:
                payload["agent_did"] = agent_did
            if tenant_id:
                payload["tenant_id"] = tenant_id
            if session_id:
                payload["session_id"] = session_id
            if response.model_id:
                payload["model_id"] = response.model_id
            if response.latency_ms is not None:
                payload["latency_ms"] = response.latency_ms
            if cost_estimate is not None:
                payload["cost_estimate"] = cost_estimate
            if cost_input_cents is not None:
                payload["cost_input_cents"] = cost_input_cents
            if cost_output_cents is not None:
                payload["cost_output_cents"] = cost_output_cents
            if cost_cached_cents is not None:
                payload["cost_cached_cents"] = cost_cached_cents
            if response.finish_reason:
                payload["finish_reason"] = response.finish_reason
            if response.error_message:
                payload["error_message"] = response.error_message

            # Make request with retry logic
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    http_response = await client.post(
                        "/api/models/usage", json=payload
                    )
                    http_response.raise_for_status()

                    logger.info(
                        f"Recorded model usage {response.request_id} in L01 "
                        f"({response.model_id}, {response.token_usage.total_tokens} tokens, "
                        f"{response.latency_ms}ms, cached={response.cached})"
                    )
                    return True

                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code >= 500:
                        logger.warning(
                            f"L01 server error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                        )
                        continue
                    # Don't retry client errors
                    logger.error(f"L01 client error: {e}")
                    break

                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning(
                        f"L01 timeout (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    continue

                except httpx.ConnectError as e:
                    last_error = e
                    logger.warning(
                        f"L01 connection error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    continue

            logger.error(f"Failed to record model usage in L01 after retries: {last_error}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error recording model usage in L01: {e}")
            return False

    async def record_inference_simple(
        self,
        agent_did: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        provider: str = "unknown",
        cached: bool = False,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Record model inference with simple parameters.

        Convenience method for recording without full request/response objects.

        Args:
            agent_did: Agent DID
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Latency in milliseconds
            provider: Provider name
            cached: Whether response was cached
            session_id: Optional session ID
            tenant_id: Optional tenant ID
            request_id: Optional request ID

        Returns:
            True if recorded successfully
        """
        if not self.enabled:
            return False

        try:
            client = await self._get_client()

            # Generate request ID if not provided
            if not request_id:
                import uuid
                request_id = str(uuid.uuid4())

            payload = {
                "request_id": request_id,
                "agent_did": agent_did,
                "model_provider": provider,
                "model_name": model_id,
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cached_tokens": 0,
                "latency_ms": latency_ms,
                "cached": cached,
                "response_status": "success",
                "metadata": {},
            }

            if session_id:
                payload["session_id"] = session_id
            if tenant_id:
                payload["tenant_id"] = tenant_id

            http_response = await client.post("/api/models/usage", json=payload)
            http_response.raise_for_status()

            logger.info(
                f"Recorded model usage {request_id} in L01 "
                f"({model_id}, {input_tokens + output_tokens} tokens, {latency_ms}ms)"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to record model usage in L01: {e}")
            return False

    async def get_agent_usage(
        self,
        agent_did: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get usage statistics for an agent.

        Args:
            agent_did: Agent DID
            start_time: Optional start time for query range
            end_time: Optional end time for query range

        Returns:
            Usage statistics dictionary
        """
        try:
            client = await self._get_client()

            params = {"agent_did": agent_did}
            if start_time:
                params["start_time"] = start_time.isoformat()
            if end_time:
                params["end_time"] = end_time.isoformat()

            response = await client.get("/api/models/usage/stats", params=params)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.warning(f"Failed to get agent usage from L01: {e}")
            return {
                "error": str(e),
                "total_requests": 0,
                "total_tokens": 0,
            }

    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        aggregate_type: str = "model_usage",
        aggregate_id: Optional[str] = None,
    ) -> bool:
        """
        Publish an event to L01 event stream.

        Args:
            event_type: Type of event (e.g., "inference_completed")
            payload: Event payload
            aggregate_type: Aggregate type for event sourcing
            aggregate_id: Optional aggregate ID

        Returns:
            True if published successfully
        """
        try:
            client = await self._get_client()

            import uuid
            event_data = {
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id or str(uuid.uuid4()),
                "payload": payload,
                "metadata": {
                    "source": "l04_model_gateway",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

            response = await client.post("/api/events/", json=event_data)
            response.raise_for_status()

            logger.debug(f"Published event {event_type} to L01")
            return True

        except Exception as e:
            logger.warning(f"Failed to publish event to L01: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check L01 connectivity and health.

        Returns:
            Health status dictionary
        """
        try:
            client = await self._get_client()
            response = await client.get("/health/live")

            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "reachable": True,
                "latency_ms": response.elapsed.total_seconds() * 1000,
            }

        except httpx.TimeoutException:
            return {
                "status": "unavailable",
                "reachable": False,
                "error": "timeout",
            }
        except httpx.ConnectError as e:
            return {
                "status": "unavailable",
                "reachable": False,
                "error": f"connection_failed: {e}",
            }
        except Exception as e:
            return {
                "status": "unknown",
                "reachable": False,
                "error": str(e),
            }

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            logger.info("L01Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L01Bridge cleanup failed: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
