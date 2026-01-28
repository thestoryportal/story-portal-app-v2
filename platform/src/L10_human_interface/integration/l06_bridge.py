"""
L10 Human Interface Layer - L06 Evaluation Layer Bridge

Bridge between L10 Human Interface and L06 Evaluation Layer for:
- Alert queries and acknowledgment
- Metric queries for cost aggregation
- Alert statistics
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from ..models import Alert, AlertStatus, AlertSeverity

logger = logging.getLogger(__name__)


class L06Bridge:
    """
    Bridge between L10 Human Interface and L06 Evaluation Layer.

    Responsibilities:
    - Query alerts from L06
    - Acknowledge/snooze alerts
    - Get alert statistics
    - Query metrics for cost aggregation
    """

    def __init__(
        self,
        l06_base_url: str = "http://localhost:8006",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize L06 bridge.

        Args:
            l06_base_url: Base URL for L06 Evaluation Layer API
            api_key: API key for L06 authentication (defaults to L01_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("L01_API_KEY", "dev_key_local_ONLY")
        self.l06_base_url = l06_base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self.enabled = True
        logger.info(f"L06Bridge initialized with base_url={l06_base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            self._client = httpx.AsyncClient(
                base_url=self.l06_base_url,
                timeout=self.timeout,
                headers=headers
            )
        return self._client

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L06Bridge initialized")

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("L06Bridge cleanup complete")

    async def get_alerts(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts from L06.

        Args:
            tenant_id: Filter by tenant ID
            status: Filter by status (triggered, acknowledged, resolved, snoozed)
            severity: Filter by severity (critical, warning, info)
            start: Start timestamp
            end: End timestamp
            limit: Maximum results

        Returns:
            List of Alert objects
        """
        if not self.enabled:
            return []

        try:
            client = await self._get_client()

            params: Dict[str, Any] = {"limit": limit}
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            if severity:
                params["severity"] = severity

            response = await client.get("/api/alerts", params=params)
            response.raise_for_status()

            alerts: List[Alert] = []
            for data in response.json():
                try:
                    alert = self._parse_alert(data)
                    # Filter by tenant_id if specified
                    if tenant_id and alert.tenant_id != tenant_id:
                        continue
                    # Filter by status if specified
                    if status and alert.status.value != status:
                        continue
                    alerts.append(alert)
                except Exception as e:
                    logger.warning(f"Failed to parse alert: {e}")

            logger.debug(f"Retrieved {len(alerts)} alerts from L06")
            return alerts

        except httpx.HTTPStatusError as e:
            logger.error(f"L06 HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.ConnectError as e:
            logger.error(f"L06 connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get alerts from L06: {e}")
            return []

    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert object or None if not found
        """
        if not self.enabled:
            return None

        try:
            client = await self._get_client()

            response = await client.get(f"/api/alerts/{alert_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()

            data = response.json()
            return self._parse_alert(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"L06 HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to get alert {alert_id} from L06: {e}")
            return None

    async def acknowledge_anomaly(
        self,
        anomaly_id: str,
        status: str,
        resolved_at: Optional[datetime] = None,
    ) -> bool:
        """Acknowledge an anomaly (update status) in L06.

        Args:
            anomaly_id: Anomaly ID to update
            status: New status value (acknowledged, resolved)
            resolved_at: Resolution timestamp if resolving

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            client = await self._get_client()

            payload: Dict[str, Any] = {"status": status}
            if resolved_at:
                payload["resolved_at"] = resolved_at.isoformat()

            response = await client.patch(
                f"/api/anomalies/{anomaly_id}",
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Updated anomaly {anomaly_id} status to {status}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"L06 HTTP error updating anomaly: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Failed to acknowledge anomaly {anomaly_id}: {e}")
            return False

    async def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics from L06.

        Returns:
            Dictionary with alert stats (alerts_sent, alerts_failed, etc.)
        """
        if not self.enabled:
            return {
                "alerts_sent": 0,
                "alerts_failed": 0,
                "alerts_rate_limited": 0,
                "success_rate": 0.0,
            }

        try:
            client = await self._get_client()

            response = await client.get("/api/alerts/stats/summary")
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get alert stats from L06: {e}")
            return {
                "alerts_sent": 0,
                "alerts_failed": 0,
                "alerts_rate_limited": 0,
                "success_rate": 0.0,
            }

    async def query_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict[str, str]] = None,
        aggregation: str = "sum",
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query metrics from L06.

        Args:
            metric_name: Name of the metric to query
            start_time: Start timestamp
            end_time: End timestamp
            labels: Optional label filters (e.g., {"agent_id": "..."})
            aggregation: Aggregation type (sum, avg, min, max)
            limit: Maximum results

        Returns:
            List of metric points with timestamps and values
        """
        if not self.enabled:
            return []

        try:
            client = await self._get_client()

            params: Dict[str, Any] = {
                "metric_name": metric_name,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "limit": limit,
            }
            if labels:
                # L06 expects labels as query params
                for k, v in labels.items():
                    params[f"label_{k}"] = v

            response = await client.get("/api/metrics", params=params)
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"L06 metrics query failed: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to query metrics from L06: {e}")
            return []

    def _parse_alert(self, data: Dict[str, Any]) -> Alert:
        """Parse alert data from L06 response to L10 Alert model.

        Args:
            data: Raw alert data from L06

        Returns:
            Alert object
        """
        # Parse timestamp
        timestamp_str = data.get("timestamp", "")
        if timestamp_str:
            triggered_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            triggered_at = datetime.utcnow()

        # Parse severity
        severity_str = data.get("severity", "info")
        try:
            severity = AlertSeverity(severity_str)
        except ValueError:
            severity = AlertSeverity.INFO

        # Parse status - L06 may not have full status, default to triggered
        status_str = data.get("status", "triggered")
        try:
            status = AlertStatus(status_str)
        except ValueError:
            status = AlertStatus.TRIGGERED

        # Parse acknowledged_at if present
        ack_at_str = data.get("acknowledged_at")
        acknowledged_at = None
        if ack_at_str:
            acknowledged_at = datetime.fromisoformat(ack_at_str.replace("Z", "+00:00"))

        # Parse snoozed_until if present
        snoozed_str = data.get("snoozed_until")
        snoozed_until = None
        if snoozed_str:
            snoozed_until = datetime.fromisoformat(snoozed_str.replace("Z", "+00:00"))

        return Alert(
            alert_id=data.get("alert_id", ""),
            rule_name=data.get("type", "unknown"),
            severity=severity,
            message=data.get("message", ""),
            metric=data.get("metric", ""),
            current_value=data.get("current_value", 0.0),
            threshold=data.get("threshold", 0.0),
            triggered_at=triggered_at,
            status=status,
            acknowledged_at=acknowledged_at,
            acknowledged_by=data.get("acknowledged_by"),
            snoozed_until=snoozed_until,
            channels_notified=data.get("channels", []),
            tenant_id=data.get("tenant_id"),
            metadata=data.get("metadata", {}),
        )
