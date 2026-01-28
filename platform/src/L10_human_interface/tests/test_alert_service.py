"""
L10 Human Interface Layer - Alert Service Tests

Tests for AlertService including L06 bridge integration.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, UTC

from ..models import (
    Alert,
    AlertStatus,
    AlertSeverity,
    AcknowledgeRequest,
    SnoozeRequest,
    ErrorCode,
    InterfaceError,
)
from ..services import AlertService


@pytest.mark.l10
class TestAlertServiceGetActiveAlerts:
    """Tests for AlertService.get_active_alerts()."""

    @pytest.mark.asyncio
    async def test_get_active_alerts_success(self, alert_service, mock_l06_bridge):
        """Test successful retrieval of active alerts."""
        result = await alert_service.get_active_alerts("tenant-1")

        assert len(result) == 1
        assert result[0].alert_id == "alert-1"
        assert result[0].status == AlertStatus.TRIGGERED
        mock_l06_bridge.get_alerts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_alerts_empty(self, mock_l06_bridge, mock_audit_logger):
        """Test when no active alerts exist."""
        mock_l06_bridge.get_alerts.return_value = []
        service = AlertService(l06_bridge=mock_l06_bridge, audit_logger=mock_audit_logger)

        result = await service.get_active_alerts("tenant-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_active_alerts_l06_unavailable(self, mock_audit_logger):
        """Test graceful degradation when L06 is unavailable."""
        service = AlertService(l06_bridge=None, audit_logger=mock_audit_logger)

        result = await service.get_active_alerts("tenant-1")

        # Should return empty list, not raise
        assert result == []

    @pytest.mark.asyncio
    async def test_get_active_alerts_filters_by_tenant(self, mock_l06_bridge, mock_audit_logger):
        """Test that get_alerts is called with correct tenant_id."""
        alert_tenant1 = Alert(
            alert_id="alert-1",
            rule_name="test",
            severity=AlertSeverity.WARNING,
            message="Test",
            metric="test",
            current_value=1.0,
            threshold=0.5,
            triggered_at=datetime.now(UTC),
            tenant_id="tenant-1",
        )
        # L06 bridge filters by tenant_id, so only tenant-1 alerts are returned
        mock_l06_bridge.get_alerts.return_value = [alert_tenant1]
        service = AlertService(l06_bridge=mock_l06_bridge)

        result = await service.get_active_alerts("tenant-1")

        # Verify bridge was called with tenant_id filter
        mock_l06_bridge.get_alerts.assert_called_once_with(
            tenant_id="tenant-1",
            status="triggered",
        )
        assert len(result) == 1
        assert result[0].tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_get_active_alerts_excludes_snoozed(self, mock_l06_bridge, mock_audit_logger):
        """Test that snoozed alerts are excluded from active alerts."""
        snoozed_alert = Alert(
            alert_id="alert-snoozed",
            rule_name="test",
            severity=AlertSeverity.WARNING,
            message="Test",
            metric="test",
            current_value=1.0,
            threshold=0.5,
            triggered_at=datetime.now(UTC),
            status=AlertStatus.SNOOZED,
            snoozed_until=datetime.now(UTC) + timedelta(hours=1),
            tenant_id="tenant-1",
        )
        mock_l06_bridge.get_alerts.return_value = [snoozed_alert]
        service = AlertService(l06_bridge=mock_l06_bridge)

        result = await service.get_active_alerts("tenant-1")

        assert len(result) == 0


@pytest.mark.l10
class TestAlertServiceAcknowledge:
    """Tests for AlertService.acknowledge_alert()."""

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, alert_service, mock_l06_bridge, mock_audit_logger):
        """Test successful alert acknowledgment."""
        request = AcknowledgeRequest(
            alert_id="alert-1",
            user_id="user-1",
            comment="Investigating",
        )

        result = await alert_service.acknowledge_alert(request)

        assert result.status == AlertStatus.ACKNOWLEDGED
        assert result.acknowledged_by == "user-1"
        mock_l06_bridge.acknowledge_anomaly.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, mock_l06_bridge, mock_audit_logger):
        """Test acknowledgment of non-existent alert raises E10703."""
        mock_l06_bridge.get_alert_by_id.return_value = None
        service = AlertService(l06_bridge=mock_l06_bridge, audit_logger=mock_audit_logger)
        request = AcknowledgeRequest(alert_id="nonexistent", user_id="user-1")

        with pytest.raises(InterfaceError) as exc_info:
            await service.acknowledge_alert(request)

        assert exc_info.value.code == ErrorCode.E10703

    @pytest.mark.asyncio
    async def test_acknowledge_alert_already_acknowledged(self, mock_l06_bridge, mock_audit_logger):
        """Test idempotent acknowledgment of already acknowledged alert."""
        acknowledged_alert = Alert(
            alert_id="alert-1",
            rule_name="test",
            severity=AlertSeverity.WARNING,
            message="Test",
            metric="test",
            current_value=1.0,
            threshold=0.5,
            triggered_at=datetime.now(UTC),
            status=AlertStatus.ACKNOWLEDGED,
            acknowledged_at=datetime.now(UTC),
            acknowledged_by="other-user",
        )
        mock_l06_bridge.get_alert_by_id.return_value = acknowledged_alert
        service = AlertService(l06_bridge=mock_l06_bridge, audit_logger=mock_audit_logger)
        request = AcknowledgeRequest(alert_id="alert-1", user_id="user-1")

        result = await service.acknowledge_alert(request)

        # Should return the already acknowledged alert (idempotent)
        assert result.status == AlertStatus.ACKNOWLEDGED
        # Should not call L06 to update
        mock_l06_bridge.acknowledge_anomaly.assert_not_called()

    @pytest.mark.asyncio
    async def test_acknowledge_alert_l06_update_fails(self, mock_l06_bridge, mock_audit_logger):
        """Test acknowledgment failure when L06 update fails."""
        mock_l06_bridge.acknowledge_anomaly.return_value = False
        service = AlertService(l06_bridge=mock_l06_bridge, audit_logger=mock_audit_logger)
        request = AcknowledgeRequest(alert_id="alert-1", user_id="user-1")

        with pytest.raises(InterfaceError) as exc_info:
            await service.acknowledge_alert(request)

        assert exc_info.value.code == ErrorCode.E10704


@pytest.mark.l10
class TestAlertServiceSnooze:
    """Tests for AlertService.snooze_alert()."""

    @pytest.mark.asyncio
    async def test_snooze_alert_success(self, alert_service, mock_l06_bridge, mock_audit_logger):
        """Test successful alert snooze."""
        request = SnoozeRequest(
            alert_id="alert-1",
            duration_minutes=30,
            user_id="user-1",
            reason="Scheduled maintenance",
        )

        result = await alert_service.snooze_alert(request)

        assert result.status == AlertStatus.SNOOZED
        assert result.snoozed_until is not None
        mock_audit_logger.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_snooze_alert_calculates_until_correctly(self, alert_service, mock_l06_bridge):
        """Test that snoozed_until is calculated correctly."""
        before = datetime.now(UTC)
        request = SnoozeRequest(
            alert_id="alert-1",
            duration_minutes=60,
            user_id="user-1",
        )

        result = await alert_service.snooze_alert(request)
        after = datetime.now(UTC)

        # snoozed_until should be ~60 minutes from now
        expected_min = before + timedelta(minutes=60)
        expected_max = after + timedelta(minutes=60)
        assert expected_min <= result.snoozed_until <= expected_max

    @pytest.mark.asyncio
    async def test_snooze_alert_not_found(self, mock_l06_bridge, mock_audit_logger):
        """Test snooze of non-existent alert raises E10703."""
        mock_l06_bridge.get_alert_by_id.return_value = None
        service = AlertService(l06_bridge=mock_l06_bridge, audit_logger=mock_audit_logger)
        request = SnoozeRequest(
            alert_id="nonexistent",
            duration_minutes=30,
            user_id="user-1",
        )

        with pytest.raises(InterfaceError) as exc_info:
            await service.snooze_alert(request)

        assert exc_info.value.code == ErrorCode.E10703

    @pytest.mark.asyncio
    async def test_snooze_alert_l06_unavailable(self, mock_audit_logger):
        """Test snooze fails gracefully when L06 is unavailable."""
        service = AlertService(l06_bridge=None, audit_logger=mock_audit_logger)
        request = SnoozeRequest(
            alert_id="alert-1",
            duration_minutes=30,
            user_id="user-1",
        )

        with pytest.raises(InterfaceError) as exc_info:
            await service.snooze_alert(request)

        assert exc_info.value.code == ErrorCode.E10902


@pytest.mark.l10
class TestAlertServiceCache:
    """Tests for AlertService caching behavior."""

    @pytest.mark.asyncio
    async def test_get_alert_by_id_uses_cache(self, alert_service, mock_l06_bridge):
        """Test that get_alert_by_id uses cache after acknowledge."""
        request = AcknowledgeRequest(alert_id="alert-1", user_id="user-1")

        # First acknowledge to cache
        await alert_service.acknowledge_alert(request)

        # Then get - should use cache
        result = await alert_service.get_alert_by_id("alert-1")

        assert result is not None
        assert result.status == AlertStatus.ACKNOWLEDGED

    @pytest.mark.asyncio
    async def test_clear_cache(self, alert_service, mock_l06_bridge):
        """Test cache clearing."""
        request = AcknowledgeRequest(alert_id="alert-1", user_id="user-1")
        await alert_service.acknowledge_alert(request)

        await alert_service.clear_cache()

        # Cache should be empty, next get should call L06
        mock_l06_bridge.get_alert_by_id.reset_mock()
        await alert_service.get_alert_by_id("alert-1")
        mock_l06_bridge.get_alert_by_id.assert_called_once()
