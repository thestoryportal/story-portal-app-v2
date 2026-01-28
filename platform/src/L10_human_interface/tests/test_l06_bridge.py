"""
L10 Human Interface Layer - L06 Bridge Tests

Tests for L06Bridge HTTP client.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC
import httpx

from ..integration import L06Bridge
from ..models import Alert, AlertStatus, AlertSeverity


@pytest.mark.l10
class TestL06BridgeInit:
    """Tests for L06Bridge initialization."""

    def test_bridge_creation(self):
        """Test L06 bridge creates with default settings."""
        bridge = L06Bridge()

        assert bridge.l06_base_url == "http://localhost:8006"
        assert bridge.timeout == 30.0
        assert bridge.enabled is True

    def test_bridge_custom_url(self):
        """Test L06 bridge with custom URL."""
        bridge = L06Bridge(l06_base_url="http://custom:9000")

        assert bridge.l06_base_url == "http://custom:9000"

    def test_bridge_trailing_slash_stripped(self):
        """Test trailing slash is stripped from URL."""
        bridge = L06Bridge(l06_base_url="http://custom:9000/")

        assert bridge.l06_base_url == "http://custom:9000"


@pytest.mark.l10
class TestL06BridgeGetAlerts:
    """Tests for L06Bridge.get_alerts()."""

    @pytest.mark.asyncio
    async def test_get_alerts_l06_unavailable(self):
        """Test graceful degradation when L06 is unavailable."""
        bridge = L06Bridge()
        bridge._client = AsyncMock()
        bridge._client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await bridge.get_alerts(tenant_id="tenant-1")

        # Should return empty list, not raise
        assert result == []

    @pytest.mark.asyncio
    async def test_get_alerts_disabled_bridge(self):
        """Test disabled bridge returns empty list."""
        bridge = L06Bridge()
        bridge.enabled = False

        result = await bridge.get_alerts(tenant_id="tenant-1")

        assert result == []


@pytest.mark.l10
class TestL06BridgeGetAlertById:
    """Tests for L06Bridge.get_alert_by_id()."""

    @pytest.mark.asyncio
    async def test_get_alert_by_id_not_found(self):
        """Test alert not found returns None."""
        bridge = L06Bridge()
        bridge._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        bridge._client.get = AsyncMock(return_value=mock_response)

        result = await bridge.get_alert_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_alert_by_id_disabled(self):
        """Test disabled bridge returns None."""
        bridge = L06Bridge()
        bridge.enabled = False

        result = await bridge.get_alert_by_id("alert-1")

        assert result is None


@pytest.mark.l10
class TestL06BridgeAcknowledge:
    """Tests for L06Bridge.acknowledge_anomaly()."""

    @pytest.mark.asyncio
    async def test_acknowledge_anomaly_disabled(self):
        """Test disabled bridge returns False."""
        bridge = L06Bridge()
        bridge.enabled = False

        result = await bridge.acknowledge_anomaly("anomaly-1", "acknowledged")

        assert result is False

    @pytest.mark.asyncio
    async def test_acknowledge_anomaly_failure(self):
        """Test acknowledgment failure returns False."""
        bridge = L06Bridge()
        bridge._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )
        bridge._client.patch = AsyncMock(return_value=mock_response)

        result = await bridge.acknowledge_anomaly("anomaly-1", "acknowledged")

        assert result is False


@pytest.mark.l10
class TestL06BridgeMetrics:
    """Tests for L06Bridge.query_metrics()."""

    @pytest.mark.asyncio
    async def test_query_metrics_disabled(self):
        """Test disabled bridge returns empty list."""
        bridge = L06Bridge()
        bridge.enabled = False

        now = datetime.now(UTC)
        result = await bridge.query_metrics(
            metric_name="model_cost_dollars",
            start_time=now,
            end_time=now,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_query_metrics_connection_failure(self):
        """Test query returns empty list on failure."""
        bridge = L06Bridge()
        bridge._client = AsyncMock()
        bridge._client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        now = datetime.now(UTC)
        result = await bridge.query_metrics(
            metric_name="model_cost_dollars",
            start_time=now,
            end_time=now,
        )

        assert result == []


@pytest.mark.l10
class TestL06BridgeAlertStats:
    """Tests for L06Bridge.get_alert_stats()."""

    @pytest.mark.asyncio
    async def test_get_alert_stats_disabled(self):
        """Test disabled bridge returns defaults."""
        bridge = L06Bridge()
        bridge.enabled = False

        result = await bridge.get_alert_stats()

        assert result["alerts_sent"] == 0
        assert result["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_alert_stats_failure(self):
        """Test alert stats returns defaults on failure."""
        bridge = L06Bridge()
        bridge._client = AsyncMock()
        bridge._client.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await bridge.get_alert_stats()

        assert result["alerts_sent"] == 0
        assert result["success_rate"] == 0.0


@pytest.mark.l10
class TestL06BridgeCleanup:
    """Tests for L06Bridge cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_when_no_client(self):
        """Test cleanup handles no client gracefully."""
        bridge = L06Bridge()
        bridge._client = None

        # Should not raise
        await bridge.cleanup()

        assert bridge._client is None

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self):
        """Test cleanup closes HTTP client."""
        bridge = L06Bridge()
        mock_client = AsyncMock()
        mock_client.is_closed = False
        bridge._client = mock_client

        await bridge.cleanup()

        mock_client.aclose.assert_called_once()
        assert bridge._client is None
