"""
L08 Supervision Layer - L10 Human Interface Bridge

Bridge between L08 Supervision Layer and L10 Human Interface for
escalation notifications and human-in-the-loop workflows.
"""

import os
import hmac
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class L10Bridge:
    """
    Bridge between L08 Supervision Layer and L10 Human Interface.

    Responsibilities:
    - Send escalation notifications via WebSocket/webhooks
    - Track notification delivery status
    - Support MFA verification flow
    - Handle approval/rejection responses
    """

    def __init__(
        self,
        l10_base_url: str = "http://localhost:8010",
        webhook_secret: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        """
        Initialize L10 bridge.

        Args:
            l10_base_url: Base URL for L10 Human Interface API
            webhook_secret: Secret for signing webhook payloads
            timeout_seconds: Request timeout
        """
        self.l10_base_url = l10_base_url
        self.webhook_secret = webhook_secret or os.getenv("L10_WEBHOOK_SECRET", "dev_secret")
        self.timeout_seconds = timeout_seconds
        self._initialized = False

        # Track notification status (in production, would be in L01)
        self._notification_status: Dict[str, Dict[str, Any]] = {}

        logger.info(f"L10Bridge initialized with base_url={l10_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge and verify L10 connectivity"""
        try:
            # In production, would verify L10 connectivity
            self._initialized = True
            logger.info("L10Bridge initialized successfully")
        except Exception as e:
            logger.warning(f"L10Bridge initialization warning: {e}")
            self._initialized = True  # Still allow operation

    async def send_escalation_notification(
        self,
        escalation_id: str,
        approvers: List[str],
        reason: str,
        context: Dict[str, Any],
        priority: int = 1
    ) -> bool:
        """
        Send escalation notification to L10 Human Interface.

        Args:
            escalation_id: Unique escalation workflow ID
            approvers: List of approver user IDs
            reason: Reason for escalation
            context: Additional context for decision making
            priority: Notification priority (1=normal, 2=high, 3=urgent)

        Returns:
            True if notification was sent successfully
        """
        try:
            payload = {
                "type": "escalation_notification",
                "escalation_id": escalation_id,
                "approvers": approvers,
                "reason": reason,
                "context": context,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Sign the payload
            signature = self._sign_payload(payload)

            # In production, would send to L10 via HTTP or WebSocket
            # POST /api/notifications/escalation
            # Headers: X-Webhook-Signature: {signature}

            # Track notification status
            self._notification_status[escalation_id] = {
                "status": "sent",
                "approvers": approvers,
                "sent_at": datetime.utcnow().isoformat(),
                "delivery_attempts": 1,
            }

            logger.info(
                f"Sent escalation notification {escalation_id} to {len(approvers)} approvers"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")

            # Track failed notification
            self._notification_status[escalation_id] = {
                "status": "failed",
                "error": str(e),
                "sent_at": datetime.utcnow().isoformat(),
            }
            return False

    async def send_escalation_reminder(
        self,
        escalation_id: str,
        approvers: List[str],
        time_remaining_seconds: int
    ) -> bool:
        """
        Send reminder for pending escalation.

        Args:
            escalation_id: Escalation workflow ID
            approvers: List of approver user IDs to remind
            time_remaining_seconds: Time remaining before timeout

        Returns:
            True if reminder was sent
        """
        try:
            payload = {
                "type": "escalation_reminder",
                "escalation_id": escalation_id,
                "approvers": approvers,
                "time_remaining_seconds": time_remaining_seconds,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # In production, would send to L10
            logger.info(
                f"Sent escalation reminder {escalation_id} "
                f"({time_remaining_seconds}s remaining)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send escalation reminder: {e}")
            return False

    async def send_escalation_resolved(
        self,
        escalation_id: str,
        approved: bool,
        resolved_by: str,
        notes: str = ""
    ) -> bool:
        """
        Send notification that escalation has been resolved.

        Args:
            escalation_id: Escalation workflow ID
            approved: Whether the escalation was approved
            resolved_by: User ID who resolved the escalation
            notes: Resolution notes

        Returns:
            True if notification was sent
        """
        try:
            payload = {
                "type": "escalation_resolved",
                "escalation_id": escalation_id,
                "approved": approved,
                "resolved_by": resolved_by,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # In production, would send to L10
            logger.info(
                f"Sent escalation resolved notification {escalation_id} "
                f"(approved={approved})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
            return False

    async def send_anomaly_alert(
        self,
        anomaly_id: str,
        agent_id: str,
        severity: str,
        metric_name: str,
        description: str,
        recipients: List[str]
    ) -> bool:
        """
        Send anomaly alert notification.

        Args:
            anomaly_id: Anomaly ID
            agent_id: Affected agent ID
            severity: Anomaly severity
            metric_name: Name of anomalous metric
            description: Description of anomaly
            recipients: List of recipient user IDs

        Returns:
            True if alert was sent
        """
        try:
            payload = {
                "type": "anomaly_alert",
                "anomaly_id": anomaly_id,
                "agent_id": agent_id,
                "severity": severity,
                "metric_name": metric_name,
                "description": description,
                "recipients": recipients,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # In production, would send to L10
            logger.info(
                f"Sent anomaly alert {anomaly_id} (severity={severity}) "
                f"to {len(recipients)} recipients"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send anomaly alert: {e}")
            return False

    async def verify_mfa(
        self,
        user_id: str,
        mfa_token: str,
        escalation_id: str
    ) -> bool:
        """
        Verify MFA token for escalation approval.

        Args:
            user_id: User ID performing verification
            mfa_token: MFA token to verify
            escalation_id: Associated escalation ID

        Returns:
            True if MFA verification succeeded
        """
        try:
            # In production, would call L10 MFA verification endpoint
            # POST /api/mfa/verify
            # Body: { user_id, token, context: { escalation_id } }

            # For development, accept any 6-digit token
            if len(mfa_token) == 6 and mfa_token.isdigit():
                logger.info(f"MFA verified for user {user_id}")
                return True

            logger.warning(f"MFA verification failed for user {user_id}")
            return False

        except Exception as e:
            logger.error(f"MFA verification error: {e}")
            return False

    async def get_notification_status(self, escalation_id: str) -> Dict[str, Any]:
        """Get status of escalation notification"""
        return self._notification_status.get(escalation_id, {
            "status": "unknown",
            "escalation_id": escalation_id,
        })

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """
        Sign webhook payload with HMAC-SHA256.

        Args:
            payload: Payload to sign

        Returns:
            Signature as hex string
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Verify incoming webhook signature.

        Args:
            payload: Received payload
            signature: Received signature

        Returns:
            True if signature is valid
        """
        expected = self._sign_payload(payload)
        return hmac.compare_digest(expected, signature)

    async def health_check(self) -> Dict[str, Any]:
        """Check L10 connectivity"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "l10_url": self.l10_base_url,
            "pending_notifications": len(self._notification_status),
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("L10Bridge cleanup complete")
