"""
L04 Model Gateway - L01 Data Layer Bridge

Bridge between L04 Model Gateway and L01 Data Layer for persistent model usage tracking.

This bridge records model inference requests and responses in L01 for analytics,
cost tracking, and usage monitoring across the platform.
"""

import logging
from typing import Optional

from L01_data_layer.client import L01Client
from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse


logger = logging.getLogger(__name__)


class L04Bridge:
    """
    Bridge between L04 Model Gateway Layer and L01 Data Layer.

    Responsibilities:
    - Record model inference usage in L01 when requests complete
    - Track token usage, latency, cost, and cache hits
    - Support agent context (DID, tenant, session) for analytics
    - Publish model usage events via L01 event stream
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """Initialize L04 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L04Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L04Bridge initialized")

    async def record_inference(
        self,
        request: InferenceRequest,
        response: InferenceResponse
    ) -> bool:
        """Record model inference usage in L01.

        Args:
            request: InferenceRequest instance
            response: InferenceResponse instance

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Extract agent context from request
            agent_did = request.agent_did
            tenant_id = request.metadata.get("tenant_id") if request.metadata else None
            session_id = request.metadata.get("session_id") if request.metadata else None

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

            # Record in L01
            await self.l01_client.record_model_usage(
                request_id=response.request_id,
                model_provider=response.provider,
                model_name=response.model_id,
                input_tokens=response.token_usage.input_tokens,
                output_tokens=response.token_usage.output_tokens,
                agent_did=agent_did,
                tenant_id=tenant_id,
                session_id=session_id,
                model_id=response.model_id,
                cached_tokens=response.token_usage.cached_tokens,
                total_tokens=response.token_usage.total_tokens,
                latency_ms=response.latency_ms,
                cached=response.cached,
                cost_estimate=cost_estimate,
                cost_input_cents=cost_input_cents,
                cost_output_cents=cost_output_cents,
                cost_cached_cents=cost_cached_cents,
                finish_reason=response.finish_reason,
                error_message=response.error_message,
                response_status=response.status.value,
                metadata=response.metadata
            )

            logger.info(
                f"Recorded model usage {response.request_id} in L01 "
                f"({response.model_id}, {response.token_usage.total_tokens} tokens, "
                f"{response.latency_ms}ms, cached={response.cached})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record model usage in L01: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L04Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L04Bridge cleanup failed: {e}")
