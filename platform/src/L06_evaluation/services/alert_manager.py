"""Alert manager for routing alerts with retry logic"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import json

from ..models.alert import Alert, AlertChannel
from ..models.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Routes alerts to configured channels with retry logic.

    Per spec Section 3.2 (Component Responsibilities #7):
    - Slack webhook integration
    - PagerDuty integration (stub)
    - Email integration (stub)
    - Exponential backoff retry (100ms -> 60s)
    - Rate limiting (1 alert/5min per metric per severity)
    """

    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        pagerduty_api_key: Optional[str] = None,
        max_retries: int = 6,
    ):
        """
        Initialize alert manager.

        Args:
            slack_webhook_url: Slack webhook URL (optional)
            pagerduty_api_key: PagerDuty API key (optional)
            max_retries: Maximum retry attempts (default: 6)
        """
        self.slack_webhook = slack_webhook_url
        self.pagerduty_key = pagerduty_api_key
        self.max_retries = max_retries

        # Rate limiting: track last alert time per (metric, severity)
        self._last_alert_time: dict[tuple[str, str], datetime] = {}
        self._rate_limit_seconds = 300  # 5 minutes

        # Statistics
        self.alerts_sent = 0
        self.alerts_failed = 0
        self.alerts_rate_limited = 0

    async def send_alert(self, alert: Alert) -> bool:
        """
        Send alert to configured channels.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        # Check rate limiting
        if not self._check_rate_limit(alert):
            self.alerts_rate_limited += 1
            logger.info(f"Alert rate limited: {alert.metric}")
            return True  # Return True because it's not a failure

        # Try to send to each channel
        success = False
        for channel in alert.channels:
            try:
                if channel == AlertChannel.SLACK:
                    if await self._send_to_slack(alert):
                        success = True
                elif channel == AlertChannel.PAGERDUTY:
                    if await self._send_to_pagerduty(alert):
                        success = True
                elif channel == AlertChannel.EMAIL:
                    if await self._send_to_email(alert):
                        success = True
            except Exception as e:
                logger.error(f"Alert delivery to {channel} failed: {e}")

        if success:
            alert.mark_delivered()
            self.alerts_sent += 1
            self._update_rate_limit(alert)
        else:
            self.alerts_failed += 1

        return success

    async def _send_to_slack(self, alert: Alert) -> bool:
        """Send alert to Slack with retry logic"""
        if not self.slack_webhook:
            logger.debug("Slack webhook not configured, skipping")
            return False

        # Build Slack message
        payload = {
            "text": f":rotating_light: *{alert.severity.value.upper()} Alert*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.type}*: {alert.message}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Metric:*\n{alert.metric}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity.value}"},
                        {"type": "mrkdwn", "text": f"*Agent:*\n{alert.agent_id or 'N/A'}"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{alert.timestamp.isoformat()}"},
                    ],
                },
            ],
        }

        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                alert.increment_attempts()

                # Simulate HTTP POST (stub implementation)
                logger.info(f"Sending alert to Slack: {alert.alert_id}")
                # In real implementation: requests.post(self.slack_webhook, json=payload)

                return True

            except Exception as e:
                logger.warning(f"Slack delivery attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    delay = alert.calculate_backoff_delay()
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Slack delivery failed after {self.max_retries} attempts")
                    return False

        return False

    async def _send_to_pagerduty(self, alert: Alert) -> bool:
        """Send alert to PagerDuty (stub)"""
        if not self.pagerduty_key:
            return False

        logger.info(f"PagerDuty integration: {alert.alert_id} (stub)")
        return True

    async def _send_to_email(self, alert: Alert) -> bool:
        """Send alert via email (stub)"""
        logger.info(f"Email integration: {alert.alert_id} (stub)")
        return True

    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert is rate limited"""
        key = (alert.metric, alert.severity.value)
        now = datetime.utcnow()

        if key in self._last_alert_time:
            last_time = self._last_alert_time[key]
            elapsed = (now - last_time).total_seconds()

            if elapsed < self._rate_limit_seconds:
                return False  # Rate limited

        return True  # OK to send

    def _update_rate_limit(self, alert: Alert):
        """Update last alert time for rate limiting"""
        key = (alert.metric, alert.severity.value)
        self._last_alert_time[key] = datetime.utcnow()

    def get_statistics(self) -> dict:
        """Get alert manager statistics"""
        total_alerts = self.alerts_sent + self.alerts_failed + self.alerts_rate_limited
        success_rate = self.alerts_sent / total_alerts if total_alerts > 0 else 0.0

        return {
            "alerts_sent": self.alerts_sent,
            "alerts_failed": self.alerts_failed,
            "alerts_rate_limited": self.alerts_rate_limited,
            "success_rate": success_rate,
        }
