"""
L10 Human Interface Layer - L01 Event Bridge Tests

Tests for L01EventBridge HTTP client.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC
import httpx

from ..integration import L01EventBridge
from ..models import EventSummary, EventDetail, EventFilter


@pytest.mark.l10
class TestL01EventBridgeInit:
    """Tests for L01EventBridge initialization."""

    def test_bridge_creation(self):
        """Test L01 event bridge creates with default settings."""
        bridge = L01EventBridge()

        assert bridge.l01_base_url == "http://localhost:8001"
        assert bridge.timeout == 30.0
        assert bridge.enabled is True

    def test_bridge_custom_url(self):
        """Test L01 event bridge with custom URL."""
        bridge = L01EventBridge(l01_base_url="http://custom:9001")

        assert bridge.l01_base_url == "http://custom:9001"


@pytest.mark.l10
class TestL01EventBridgeQueryEvents:
    """Tests for L01EventBridge.query_events()."""

    @pytest.mark.asyncio
    async def test_query_events_l01_unavailable(self):
        """Test graceful degradation when L01 is unavailable."""
        bridge = L01EventBridge()
        bridge._client = AsyncMock()
        bridge._client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        filters = EventFilter()
        events, total = await bridge.query_events(filters)

        assert events == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_query_events_disabled_bridge(self):
        """Test disabled bridge returns empty results."""
        bridge = L01EventBridge()
        bridge.enabled = False

        filters = EventFilter()
        events, total = await bridge.query_events(filters)

        assert events == []
        assert total == 0


@pytest.mark.l10
class TestL01EventBridgeGetEvent:
    """Tests for L01EventBridge.get_event()."""

    @pytest.mark.asyncio
    async def test_get_event_not_found(self):
        """Test event not found returns None."""
        bridge = L01EventBridge()
        bridge._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        bridge._client.get = AsyncMock(return_value=mock_response)

        result = await bridge.get_event("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_event_disabled(self):
        """Test disabled bridge returns None."""
        bridge = L01EventBridge()
        bridge.enabled = False

        result = await bridge.get_event("event-1")

        assert result is None


@pytest.mark.l10
class TestL01EventBridgeRecordEvent:
    """Tests for L01EventBridge.record_event()."""

    @pytest.mark.asyncio
    async def test_record_event_disabled_bridge(self):
        """Test disabled bridge returns False."""
        bridge = L01EventBridge()
        bridge.enabled = False

        result = await bridge.record_event(
            event_type="agent.paused",
            payload={},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_record_event_failure(self):
        """Test event recording failure returns False."""
        bridge = L01EventBridge()
        bridge._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )
        bridge._client.post = AsyncMock(return_value=mock_response)

        result = await bridge.record_event(
            event_type="agent.paused",
            payload={},
        )

        assert result is False


@pytest.mark.l10
class TestL01EventBridgeCleanup:
    """Tests for L01EventBridge cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_when_no_client(self):
        """Test cleanup handles no client gracefully."""
        bridge = L01EventBridge()
        bridge._client = None

        # Should not raise
        await bridge.cleanup()

        assert bridge._client is None

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self):
        """Test cleanup closes HTTP client."""
        bridge = L01EventBridge()
        mock_client = AsyncMock()
        mock_client.is_closed = False
        bridge._client = mock_client

        await bridge.cleanup()

        mock_client.aclose.assert_called_once()
        assert bridge._client is None
