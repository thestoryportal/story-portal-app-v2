"""
Async Handler - 202 Responses and Webhook Delivery
"""

import hmac
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
from ..models import (
    RequestContext,
    AsyncOperation,
    OperationStatus,
    WebhookConfig,
    WebhookDeliveryStatus,
    AsyncOperationResponse,
)
from ..errors import ErrorCode, ValidationError


class AsyncHandler:
    """
    Manages long-running async operations

    Features:
    - 202 Accepted responses
    - Webhook delivery with HMAC signatures
    - SSRF prevention
    - Exponential backoff retries
    - Dead-letter queue for failed webhooks
    """

    def __init__(self, operation_store, redis_client):
        """
        Args:
            operation_store: Storage for operation records (L01)
            redis_client: Redis for webhook queue
        """
        self.operation_store = operation_store
        self.redis = redis_client
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    async def create_async_operation(
        self,
        context: RequestContext,
        route_id: str,
        request_payload: Optional[Dict[str, Any]] = None,
        webhook_config: Optional[WebhookConfig] = None,
    ) -> AsyncOperation:
        """
        Create async operation record

        Args:
            context: Request context
            route_id: Route that handled request
            request_payload: Original request data
            webhook_config: Webhook configuration

        Returns:
            AsyncOperation with operation_id
        """
        operation = AsyncOperation(
            operation_id=str(uuid4()),
            consumer_id=context.consumer_id or "unknown",
            tenant_id=context.tenant_id or "unknown",
            status=OperationStatus.QUEUED,
            request_id=context.request_id,
            route_id=route_id,
            request_payload=request_payload,
            webhook_config=webhook_config,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

        # Store in L01
        await self.operation_store.create_operation(operation)

        return operation

    async def get_operation(self, operation_id: str) -> Optional[AsyncOperation]:
        """Get operation by ID"""
        return await self.operation_store.get_operation(operation_id)

    async def update_operation_status(
        self,
        operation_id: str,
        status: OperationStatus,
        progress_pct: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update operation status"""
        await self.operation_store.update_operation(
            operation_id=operation_id,
            status=status,
            progress_pct=progress_pct,
            result=result,
            error=error,
            completed_at=datetime.utcnow() if status in [OperationStatus.COMPLETED, OperationStatus.FAILED] else None,
        )

    async def deliver_webhook(
        self, operation: AsyncOperation
    ) -> bool:
        """
        Deliver webhook with result

        Args:
            operation: Completed operation

        Returns:
            True if delivered successfully
        """
        if not operation.webhook_config:
            return False

        # Validate webhook URL (SSRF prevention)
        try:
            self._validate_webhook_url(operation.webhook_config.url)
        except ValidationError as e:
            # Mark as failed
            await self._mark_webhook_failed(operation, str(e))
            return False

        # Prepare webhook payload
        payload = {
            "operation_id": operation.operation_id,
            "status": operation.status.value,
            "result": operation.result,
            "error": operation.error,
            "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        }

        # Calculate HMAC signature
        timestamp = int(datetime.utcnow().timestamp())
        signature = self._calculate_signature(
            payload,
            timestamp,
            operation.webhook_config.secret,
        )

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": str(timestamp),
            "X-Operation-ID": operation.operation_id,
        }

        # Execute with retries
        max_retries = operation.webhook_config.max_retries
        retry_count = 0

        while retry_count <= max_retries:
            try:
                response = await self._http_client.post(
                    operation.webhook_config.url,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code >= 200 and response.status_code < 300:
                    # Success
                    await self._mark_webhook_delivered(operation)
                    return True

                # Non-2xx response, retry
                retry_count += 1

                if retry_count <= max_retries:
                    # Exponential backoff
                    backoff = self._calculate_backoff(
                        retry_count,
                        operation.webhook_config.retry_backoff_base_ms,
                    )
                    await self._sleep(backoff)

            except Exception as e:
                retry_count += 1

                if retry_count <= max_retries:
                    backoff = self._calculate_backoff(
                        retry_count,
                        operation.webhook_config.retry_backoff_base_ms,
                    )
                    await self._sleep(backoff)

        # All retries exhausted - move to dead-letter queue
        await self._mark_webhook_dead_letter(operation)
        return False

    def _validate_webhook_url(self, url: str) -> None:
        """
        Validate webhook URL for SSRF prevention

        Raises:
            ValidationError: If URL is invalid or blocked
        """
        import re

        # Must be HTTPS
        if not url.startswith("https://"):
            raise ValidationError(
                ErrorCode.E9701,
                "Webhook URL must use HTTPS",
            )

        # Block private IP ranges
        private_patterns = [
            r"^https?://127\.",
            r"^https?://10\.",
            r"^https?://172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^https?://192\.168\.",
            r"^https?://169\.254\.",
            r"^https?://\[::1\]",
            r"^https?://\[fc[0-9a-f]{2}:",
            r"^https?://localhost",
        ]

        for pattern in private_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                raise ValidationError(
                    ErrorCode.E9704,
                    f"Webhook URL blocked (SSRF prevention): {url}",
                )

    def _calculate_signature(
        self,
        payload: Dict[str, Any],
        timestamp: int,
        secret: str,
    ) -> str:
        """
        Calculate HMAC-SHA256 signature for webhook

        Format: HMAC-SHA256("{timestamp}.{json_body}", secret)
        """
        import json

        message = f"{timestamp}.{json.dumps(payload, sort_keys=True)}"
        signature = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _calculate_backoff(self, retry_count: int, base_ms: int) -> float:
        """Calculate exponential backoff"""
        # 1s → 10s → 100s → 1000s → 10000s
        backoff_ms = base_ms * (10 ** (retry_count - 1))
        return backoff_ms / 1000.0

    async def _sleep(self, seconds: float) -> None:
        """Sleep for specified seconds"""
        import asyncio
        await asyncio.sleep(seconds)

    async def _mark_webhook_delivered(self, operation: AsyncOperation) -> None:
        """Mark webhook as delivered"""
        await self.operation_store.update_operation(
            operation_id=operation.operation_id,
            webhook_delivery_status=WebhookDeliveryStatus.DELIVERED,
            webhook_last_attempt=datetime.utcnow(),
        )

    async def _mark_webhook_failed(self, operation: AsyncOperation, error: str) -> None:
        """Mark webhook as failed"""
        await self.operation_store.update_operation(
            operation_id=operation.operation_id,
            webhook_delivery_status=WebhookDeliveryStatus.FAILED,
            webhook_last_attempt=datetime.utcnow(),
        )

    async def _mark_webhook_dead_letter(self, operation: AsyncOperation) -> None:
        """Move webhook to dead-letter queue"""
        await self.operation_store.update_operation(
            operation_id=operation.operation_id,
            webhook_delivery_status=WebhookDeliveryStatus.DEAD_LETTER,
            webhook_last_attempt=datetime.utcnow(),
        )

        # Add to dead-letter queue in Redis
        await self.redis.lpush(
            "webhook:dlq",
            operation.operation_id,
        )

    async def close(self) -> None:
        """Close HTTP client"""
        await self._http_client.aclose()
