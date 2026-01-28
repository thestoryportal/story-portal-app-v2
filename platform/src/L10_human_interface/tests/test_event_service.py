"""
L10 Human Interface Layer - Event Service Tests

Tests for EventService including L01 bridge integration.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, UTC

from ..models import (
    EventQuery,
    EventFilter,
    EventSummary,
    EventDetail,
    EventResponse,
    ErrorCode,
    InterfaceError,
)
from ..services import EventService


@pytest.mark.l10
class TestEventServiceQuery:
    """Tests for EventService.query_events()."""

    @pytest.mark.asyncio
    async def test_query_events_success(self, event_service, mock_l01_event_bridge):
        """Test successful event query."""
        query = EventQuery(
            filters=EventFilter(tenant_id="tenant-1"),
            limit=100,
            offset=0,
        )

        result = await event_service.query_events(query)

        assert isinstance(result, EventResponse)
        assert len(result.events) == 1
        assert result.total == 1
        assert result.limit == 100
        assert result.offset == 0
        mock_l01_event_bridge.query_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_events_with_all_filters(self, event_service, mock_l01_event_bridge):
        """Test query with all filter options."""
        now = datetime.now(UTC)
        query = EventQuery(
            filters=EventFilter(
                event_types=["agent.state.changed", "agent.created"],
                agent_id="agent-1",
                tenant_id="tenant-1",
                start_time=now - timedelta(hours=1),
                end_time=now,
                severity="warning",
                search_text="error",
            ),
            limit=50,
            offset=10,
            sort_by="timestamp",
            sort_order="desc",
        )

        result = await event_service.query_events(query)

        assert isinstance(result, EventResponse)
        mock_l01_event_bridge.query_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_events_pagination(self, mock_l01_event_bridge):
        """Test query pagination with has_more."""
        # Return 50 events but total is 100
        events = [
            EventSummary(
                event_id=f"event-{i}",
                event_type="agent.state.changed",
                aggregate_id="agent-1",
                aggregate_type="agent",
                timestamp=datetime.now(UTC),
                tenant_id="tenant-1",
            )
            for i in range(50)
        ]
        mock_l01_event_bridge.query_events.return_value = (events, 100)
        service = EventService(l01_event_bridge=mock_l01_event_bridge)

        query = EventQuery(
            filters=EventFilter(),
            limit=50,
            offset=0,
        )
        result = await service.query_events(query)

        assert result.has_more is True
        assert result.total == 100

    @pytest.mark.asyncio
    async def test_query_events_no_more_pages(self, mock_l01_event_bridge):
        """Test pagination when on last page."""
        events = [
            EventSummary(
                event_id="event-1",
                event_type="agent.state.changed",
                aggregate_id="agent-1",
                aggregate_type="agent",
                timestamp=datetime.now(UTC),
                tenant_id="tenant-1",
            )
        ]
        mock_l01_event_bridge.query_events.return_value = (events, 1)
        service = EventService(l01_event_bridge=mock_l01_event_bridge)

        query = EventQuery(
            filters=EventFilter(),
            limit=50,
            offset=0,
        )
        result = await service.query_events(query)

        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_query_events_l01_unavailable(self):
        """Test graceful degradation when L01 is unavailable."""
        service = EventService(l01_event_bridge=None)

        query = EventQuery(
            filters=EventFilter(tenant_id="tenant-1"),
            limit=100,
            offset=0,
        )
        result = await service.query_events(query)

        assert result.events == []
        assert result.total == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_query_events_invalid_limit(self, event_service):
        """Test validation of limit parameter."""
        query = EventQuery(
            filters=EventFilter(),
            limit=5000,  # Too high
            offset=0,
        )

        with pytest.raises(InterfaceError) as exc_info:
            await event_service.query_events(query)

        assert exc_info.value.code == ErrorCode.E10403

    @pytest.mark.asyncio
    async def test_query_events_invalid_offset(self, event_service):
        """Test validation of negative offset."""
        query = EventQuery(
            filters=EventFilter(),
            limit=100,
            offset=-1,
        )

        with pytest.raises(InterfaceError) as exc_info:
            await event_service.query_events(query)

        assert exc_info.value.code == ErrorCode.E10403

    @pytest.mark.asyncio
    async def test_query_events_invalid_time_range(self, event_service):
        """Test validation of start_time after end_time."""
        now = datetime.now(UTC)
        query = EventQuery(
            filters=EventFilter(
                start_time=now,
                end_time=now - timedelta(hours=1),  # End before start
            ),
            limit=100,
            offset=0,
        )

        with pytest.raises(InterfaceError) as exc_info:
            await event_service.query_events(query)

        assert exc_info.value.code == ErrorCode.E10403


@pytest.mark.l10
class TestEventServiceGetDetails:
    """Tests for EventService.get_event_details()."""

    @pytest.mark.asyncio
    async def test_get_event_details_success(self, event_service, mock_l01_event_bridge):
        """Test successful event detail retrieval."""
        result = await event_service.get_event_details("event-1")

        assert isinstance(result, EventDetail)
        assert result.event_id == "event-1"
        assert result.payload is not None
        mock_l01_event_bridge.get_event.assert_called_once_with("event-1")

    @pytest.mark.asyncio
    async def test_get_event_details_not_found(self, mock_l01_event_bridge):
        """Test retrieval of non-existent event raises E10402."""
        mock_l01_event_bridge.get_event.return_value = None
        service = EventService(l01_event_bridge=mock_l01_event_bridge)

        with pytest.raises(InterfaceError) as exc_info:
            await service.get_event_details("nonexistent")

        assert exc_info.value.code == ErrorCode.E10402

    @pytest.mark.asyncio
    async def test_get_event_details_empty_id(self, event_service):
        """Test retrieval with empty event_id raises E10403."""
        with pytest.raises(InterfaceError) as exc_info:
            await event_service.get_event_details("")

        assert exc_info.value.code == ErrorCode.E10403

    @pytest.mark.asyncio
    async def test_get_event_details_l01_unavailable(self):
        """Test failure when L01 is unavailable."""
        service = EventService(l01_event_bridge=None)

        with pytest.raises(InterfaceError) as exc_info:
            await service.get_event_details("event-1")

        assert exc_info.value.code == ErrorCode.E10902


@pytest.mark.l10
class TestEventServiceRecordEvent:
    """Tests for EventService.record_control_event()."""

    @pytest.mark.asyncio
    async def test_record_control_event_success(self, event_service, mock_l01_event_bridge):
        """Test successful control event recording."""
        result = await event_service.record_control_event(
            event_type="agent.paused",
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            payload={"reason": "maintenance"},
        )

        assert result is True
        mock_l01_event_bridge.record_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_control_event_l01_unavailable(self):
        """Test recording returns False when L01 unavailable."""
        service = EventService(l01_event_bridge=None)

        result = await service.record_control_event(
            event_type="agent.paused",
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            payload={},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_record_control_event_failure(self, mock_l01_event_bridge):
        """Test recording handles failures gracefully."""
        mock_l01_event_bridge.record_event.return_value = False
        service = EventService(l01_event_bridge=mock_l01_event_bridge)

        result = await service.record_control_event(
            event_type="agent.paused",
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            payload={},
        )

        assert result is False
