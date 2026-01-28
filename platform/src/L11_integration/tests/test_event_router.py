"""
L11 Integration Layer - Event Router Tests.

Tests for the EventRouter service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from L11_integration.services.event_router import EventRouter, ROUTING_TABLE
from .fixtures.mock_http import MockHTTPClient
from .fixtures.event_data import (
    sample_agent_event,
    sample_tool_event,
    sample_plan_event,
    sample_session_event,
    sample_dataset_event,
    sample_unknown_event,
)


@pytest.mark.l11
@pytest.mark.unit
class TestEventRouterUnit:
    """Unit tests for EventRouter."""

    @pytest_asyncio.fixture
    async def router(self, mock_http_client):
        """Create router with mock HTTP client."""
        router = EventRouter()
        await router.start()
        router._http_client = mock_http_client
        yield router
        await router.stop()

    @pytest.mark.asyncio
    async def test_route_agent_event_success(self, router, mock_http_client):
        """Test routing agent event to L02."""
        mock_http_client.add_response("POST", "/events/agent", {"status": "ok"})

        event = sample_agent_event()
        result = await router.route_l01_event(event)

        assert result is True
        assert mock_http_client.request_count() == 1
        request = mock_http_client.get_requests()[0]
        assert request["method"] == "POST"
        assert "/events/agent" in request["url"]

    @pytest.mark.asyncio
    async def test_route_tool_event_success(self, router, mock_http_client):
        """Test routing tool event to L03."""
        mock_http_client.add_response("POST", "/events/tool", {"status": "ok"})

        event = sample_tool_event()
        result = await router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "/events/tool" in request["url"]

    @pytest.mark.asyncio
    async def test_route_plan_event_success(self, router, mock_http_client):
        """Test routing plan event to L05."""
        mock_http_client.add_response("POST", "/events/plan", {"status": "ok"})

        event = sample_plan_event()
        result = await router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "/events/plan" in request["url"]

    @pytest.mark.asyncio
    async def test_route_session_event_success(self, router, mock_http_client):
        """Test routing session event to L10."""
        mock_http_client.add_response("POST", "/events/session", {"status": "ok"})

        event = sample_session_event()
        result = await router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "/events/session" in request["url"]

    @pytest.mark.asyncio
    async def test_route_dataset_event_success(self, router, mock_http_client):
        """Test routing dataset event to L07."""
        mock_http_client.add_response("POST", "/events/training", {"status": "ok"})

        event = sample_dataset_event()
        result = await router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "/events/training" in request["url"]

    @pytest.mark.asyncio
    async def test_unknown_event_not_routed(self, router, mock_http_client):
        """Test that unknown events are not routed."""
        event = sample_unknown_event()
        result = await router.route_l01_event(event)

        assert result is False
        assert mock_http_client.request_count() == 0

    @pytest.mark.asyncio
    async def test_route_failure_adds_to_dlq(self, router, mock_http_client):
        """Test that failed routes add events to DLQ."""
        mock_http_client.set_connect_error_for("POST", "/events/agent")

        event = sample_agent_event()
        result = await router.route_l01_event(event)

        assert result is False
        metrics = router.get_metrics()
        assert sum(metrics["dlq_sizes"].values()) > 0

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, router, mock_http_client):
        """Test that metrics are tracked correctly."""
        mock_http_client.add_response("POST", "/events/agent", {"status": "ok"})
        mock_http_client.add_response("POST", "/events/tool", {"status": "ok"})

        await router.route_l01_event(sample_agent_event())
        await router.route_l01_event(sample_tool_event())
        await router.route_l01_event(sample_unknown_event())

        metrics = router.get_metrics()
        assert metrics["events_received"] == 3
        assert metrics["events_routed"] == 2
        assert metrics["events_by_type"]["agent"] == 1
        assert metrics["events_by_type"]["tool"] == 1
        assert metrics["events_by_type"]["unknown_type"] == 1

    @pytest.mark.asyncio
    async def test_dlq_retry(self, router, mock_http_client):
        """Test DLQ retry functionality."""
        # First request fails
        mock_http_client.set_connect_error_for("POST", "/events/agent")
        event = sample_agent_event()
        await router.route_l01_event(event)

        # Clear mock and set success response
        mock_http_client.clear_requests()
        mock_http_client._responses.clear()
        mock_http_client.add_response("POST", "/events/agent", {"status": "ok"})

        # Retry DLQ
        results = await router.retry_dlq()

        assert "L02_runtime" in results
        assert results["L02_runtime"]["total"] == 1

    @pytest.mark.asyncio
    async def test_health_status(self, router, mock_http_client):
        """Test health status reporting."""
        mock_http_client.add_response("POST", "/events/agent", {"status": "ok"})

        # Route some events
        for _ in range(5):
            await router.route_l01_event(sample_agent_event())

        health = await router.get_health()
        assert health["healthy"] is True
        assert health["success_rate_percent"] == 100.0
        assert health["events_received"] == 5
        assert health["events_routed"] == 5

    @pytest.mark.asyncio
    async def test_routing_table_completeness(self):
        """Test that routing table has expected entries."""
        expected_aggregates = ["agent", "tool", "tool_execution", "plan", "dataset", "training_example", "session"]
        for agg_type in expected_aggregates:
            assert agg_type in ROUTING_TABLE, f"Missing route for {agg_type}"


@pytest.mark.l11
@pytest.mark.unit
class TestEventRouterStartStop:
    """Tests for EventRouter lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_http_client(self):
        """Test that start creates HTTP client."""
        router = EventRouter()
        assert router._http_client is None

        await router.start()
        assert router._http_client is not None

        await router.stop()
        assert router._http_client is None

    @pytest.mark.asyncio
    async def test_route_without_start_fails(self):
        """Test that routing without starting fails gracefully."""
        router = EventRouter()
        event = sample_agent_event()

        result = await router.route_l01_event(event)
        assert result is False
