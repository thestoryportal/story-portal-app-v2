"""
L10 Human Interface Layer - Alert Service

Query and manage alerts with integration to L06 Evaluation Layer.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta, UTC

from ..models import (
    Alert,
    AlertStatus,
    AcknowledgeRequest,
    SnoozeRequest,
    ErrorCode,
    InterfaceError,
)
from ..integration.l06_bridge import L06Bridge

logger = logging.getLogger(__name__)


class AlertService:
    """Alert service for managing alerts via L06 Evaluation Layer."""

    def __init__(
        self,
        l06_bridge: Optional[L06Bridge] = None,
        metrics_engine=None,
        audit_logger=None,
    ):
        """Initialize AlertService.

        Args:
            l06_bridge: Bridge to L06 Evaluation Layer
            metrics_engine: Optional legacy metrics engine (for backward compat)
            audit_logger: Optional audit logger for tracking operations
        """
        self.l06_bridge = l06_bridge
        self.metrics_engine = metrics_engine
        self.audit_logger = audit_logger
        self._alert_cache: dict[str, Alert] = {}  # Local cache for snooze tracking

    async def get_active_alerts(self, tenant_id: str) -> List[Alert]:
        """Get all active (triggered) alerts for tenant.

        Args:
            tenant_id: Tenant ID to filter alerts

        Returns:
            List of active Alert objects

        Raises:
            InterfaceError: If query fails (non-recoverable)
        """
        try:
            if not self.l06_bridge:
                logger.warning("L06 bridge not configured, returning empty alerts")
                return []

            # Query alerts with status=triggered from L06
            alerts = await self.l06_bridge.get_alerts(
                tenant_id=tenant_id,
                status="triggered",
            )

            # Filter out snoozed alerts that are still in snooze period
            now = datetime.now(UTC)
            active_alerts = []
            for alert in alerts:
                # Check if alert is snoozed
                if alert.snoozed_until and alert.snoozed_until > now:
                    continue
                # Check local cache for snooze status
                cached = self._alert_cache.get(alert.alert_id)
                if cached and cached.snoozed_until and cached.snoozed_until > now:
                    continue
                active_alerts.append(alert)

            logger.debug(f"Found {len(active_alerts)} active alerts for tenant {tenant_id}")
            return active_alerts

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            # Graceful degradation - return empty list instead of raising
            return []

    async def acknowledge_alert(self, request: AcknowledgeRequest) -> Alert:
        """Acknowledge an alert.

        Updates alert status to acknowledged and records the user who acknowledged it.

        Args:
            request: AcknowledgeRequest with alert_id and user_id

        Returns:
            Updated Alert object

        Raises:
            InterfaceError: E10703 if alert not found, E10704 if acknowledgment fails
        """
        try:
            if not self.l06_bridge:
                raise InterfaceError.from_code(
                    ErrorCode.E10902,
                    details={"reason": "L06 bridge not configured"},
                )

            # Get the alert first
            alert = await self.l06_bridge.get_alert_by_id(request.alert_id)
            if not alert:
                raise InterfaceError.from_code(
                    ErrorCode.E10703,
                    details={"alert_id": request.alert_id},
                )

            # Check if already acknowledged (idempotent)
            if alert.status == AlertStatus.ACKNOWLEDGED:
                logger.info(f"Alert {request.alert_id} already acknowledged (idempotent)")
                return alert

            # Update status via L06
            now = datetime.now(UTC)
            success = await self.l06_bridge.acknowledge_anomaly(
                anomaly_id=request.alert_id,
                status="acknowledged",
            )

            if not success:
                raise InterfaceError.from_code(
                    ErrorCode.E10704,
                    details={"alert_id": request.alert_id, "reason": "L06 update failed"},
                )

            # Update local state
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = now
            alert.acknowledged_by = request.user_id

            # Cache the updated alert
            self._alert_cache[alert.alert_id] = alert

            # Audit log
            if self.audit_logger:
                try:
                    await self.audit_logger.log(
                        event_type="alert.acknowledged",
                        data={
                            "alert_id": request.alert_id,
                            "user_id": request.user_id,
                            "comment": request.comment,
                            "timestamp": now.isoformat(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed: {e}")

            logger.info(f"Alert {request.alert_id} acknowledged by {request.user_id}")
            return alert

        except InterfaceError:
            raise
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10704,
                details={"alert_id": request.alert_id, "error": str(e)},
            )

    async def snooze_alert(self, request: SnoozeRequest) -> Alert:
        """Snooze an alert for a specified duration.

        The alert will be hidden from active alerts until the snooze period expires.

        Args:
            request: SnoozeRequest with alert_id, duration_minutes, and user_id

        Returns:
            Updated Alert object with snoozed_until set

        Raises:
            InterfaceError: E10703 if alert not found, E10704 if snooze fails
        """
        try:
            if not self.l06_bridge:
                raise InterfaceError.from_code(
                    ErrorCode.E10902,
                    details={"reason": "L06 bridge not configured"},
                )

            # Get the alert first
            alert = await self.l06_bridge.get_alert_by_id(request.alert_id)
            if not alert:
                raise InterfaceError.from_code(
                    ErrorCode.E10703,
                    details={"alert_id": request.alert_id},
                )

            # Calculate snooze until time
            now = datetime.now(UTC)
            snoozed_until = now + timedelta(minutes=request.duration_minutes)

            # Update local state (L06 may not have snooze support, so we track locally)
            alert.status = AlertStatus.SNOOZED
            alert.snoozed_until = snoozed_until

            # Cache the snoozed alert
            self._alert_cache[alert.alert_id] = alert

            # Audit log
            if self.audit_logger:
                try:
                    await self.audit_logger.log(
                        event_type="alert.snoozed",
                        data={
                            "alert_id": request.alert_id,
                            "user_id": request.user_id,
                            "duration_minutes": request.duration_minutes,
                            "snoozed_until": snoozed_until.isoformat(),
                            "reason": request.reason,
                            "timestamp": now.isoformat(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed: {e}")

            logger.info(
                f"Alert {request.alert_id} snoozed for {request.duration_minutes} minutes "
                f"by {request.user_id} (until {snoozed_until.isoformat()})"
            )
            return alert

        except InterfaceError:
            raise
        except Exception as e:
            logger.error(f"Failed to snooze alert: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10704,
                details={"alert_id": request.alert_id, "error": str(e)},
            )

    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert object or None if not found
        """
        # Check cache first
        if alert_id in self._alert_cache:
            return self._alert_cache[alert_id]

        if not self.l06_bridge:
            return None

        return await self.l06_bridge.get_alert_by_id(alert_id)

    async def clear_cache(self) -> None:
        """Clear the local alert cache."""
        self._alert_cache.clear()
        logger.debug("Alert cache cleared")
