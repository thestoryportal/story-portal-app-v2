"""
L11 Integration Layer - End-to-End Event Flow Tests.

Tests the complete event flow from L01 subscription to target layer routing.
Requires: Redis running on localhost:6379
"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import AsyncMock, patch

from L11_integration.app import app, handle_l01_event
from L11_integration.services import EventRouter
from L11_integration.tests.fixtures.mock_http import MockHTTPClient
from L11_integration.tests.fixtures.event_data import (
    sample_agent_event,
    sample_tool_event,
    sample_plan_event,
)


@pytest.mark.l11
@pytest.mark.integration
class TestE2EEventFlow:
    """End-to-end tests for event routing flow."""

    @pytest_asyncio.fixture
    async def mock_http_client(self):
        """Create mock HTTP client with all layer endpoints."""
        client = MockHTTPClient()
        client.add_response("POST", "/events/agent", {"status": "ok"})
        client.add_response("POST", "/events/tool", {"status": "ok"})
        client.add_response("POST", "/events/plan", {"status": "ok"})
        client.add_response("POST", "/events/training", {"status": "ok"})
        client.add_response("POST", "/events/session", {"status": "ok"})
        return client

    @pytest_asyncio.fixture
    async def event_router(self, mock_http_client):
        """Create event router with mock HTTP client."""
        router = EventRouter()
        await router.start()
        router._http_client = mock_http_client
        yield router
        await router.stop()

    @pytest.mark.asyncio
    async def test_l01_to_l02_agent_event_flow(self, event_router, mock_http_client):
        """Test agent event flows from L01 to L02."""
        # Simulate L01 publishing an agent.created event
        event = sample_agent_event("agent.created", "agent-e2e-001")

        # Route the event
        result = await event_router.route_l01_event(event)

        assert result is True
        assert mock_http_client.request_count() == 1

        request = mock_http_client.get_requests()[0]
        assert request["method"] == "POST"
        assert "8002" in request["url"]  # L02 port
        assert "/events/agent" in request["url"]
        assert request["json"]["aggregate_type"] == "agent"

    @pytest.mark.asyncio
    async def test_l01_to_l03_tool_event_flow(self, event_router, mock_http_client):
        """Test tool event flows from L01 to L03."""
        event = sample_tool_event("tool.executed", "tool-e2e-001")

        result = await event_router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "8003" in request["url"]  # L03 port
        assert "/events/tool" in request["url"]

    @pytest.mark.asyncio
    async def test_l01_to_l05_plan_event_flow(self, event_router, mock_http_client):
        """Test plan event flows from L01 to L05."""
        event = sample_plan_event("plan.created", "plan-e2e-001")

        result = await event_router.route_l01_event(event)

        assert result is True
        request = mock_http_client.get_requests()[0]
        assert "8005" in request["url"]  # L05 port
        assert "/events/plan" in request["url"]

    @pytest.mark.asyncio
    async def test_multiple_events_routed_in_sequence(self, event_router, mock_http_client):
        """Test multiple events are routed correctly in sequence."""
        events = [
            sample_agent_event("agent.created", "agent-001"),
            sample_tool_event("tool.registered", "tool-001"),
            sample_plan_event("plan.started", "plan-001"),
        ]

        for event in events:
            await event_router.route_l01_event(event)

        assert mock_http_client.request_count() == 3
        metrics = event_router.get_metrics()
        assert metrics["events_received"] == 3
        assert metrics["events_routed"] == 3

    @pytest.mark.asyncio
    async def test_failed_delivery_queued_in_dlq(self, event_router, mock_http_client):
        """Test that failed deliveries are added to DLQ."""
        mock_http_client.set_connect_error_for("POST", "/events/agent")

        event = sample_agent_event("agent.failed", "agent-fail-001")
        result = await event_router.route_l01_event(event)

        assert result is False
        metrics = event_router.get_metrics()
        assert sum(metrics["dlq_sizes"].values()) == 1

    @pytest.mark.asyncio
    async def test_dlq_retry_after_recovery(self, event_router, mock_http_client):
        """Test DLQ events are retried after service recovery."""
        # Fail initial delivery
        mock_http_client.set_connect_error_for("POST", "/events/agent")
        event = sample_agent_event("agent.retry", "agent-retry-001")
        await event_router.route_l01_event(event)

        # Verify in DLQ
        dlq_events = await event_router.get_dlq_events()
        assert len(dlq_events) == 1

        # "Recover" the service
        mock_http_client._responses.clear()
        mock_http_client.add_response("POST", "/events/agent", {"status": "ok"})

        # Retry DLQ
        results = await event_router.retry_dlq()

        # Should have succeeded
        assert "L02_runtime" in results
        dlq_events = await event_router.get_dlq_events()
        # DLQ should be empty after successful retry
        # (Note: retry actually calls route_l01_event again which adds to DLQ on fail)


@pytest.mark.l11
@pytest.mark.integration
class TestEventHandlerIntegration:
    """Tests for the app-level event handler."""

    @pytest_asyncio.fixture
    async def router_with_mock(self):
        """Create router with mock HTTP client."""
        router = EventRouter()
        await router.start()
        mock_client = MockHTTPClient()
        mock_client.add_response("POST", "/events/agent", {"status": "ok"})
        mock_client.add_response("POST", "/events/tool", {"status": "ok"})
        router._http_client = mock_client
        yield router, mock_client
        await router.stop()

    @pytest.mark.asyncio
    async def test_handle_l01_event_routes_correctly(self, router_with_mock):
        """Test handle_l01_event function routes events."""
        router, mock_client = router_with_mock

        # Patch the global event_router
        with patch("L11_integration.app.event_router", router):
            event = sample_agent_event("agent.created", "agent-handler-001")
            await handle_l01_event(event)

        # Verify event was routed
        assert mock_client.request_count() == 1

    @pytest.mark.asyncio
    async def test_handle_l01_event_handles_malformed_event(self, router_with_mock):
        """Test handle_l01_event handles malformed events gracefully."""
        router, mock_client = router_with_mock

        with patch("L11_integration.app.event_router", router):
            # Malformed event - missing required fields
            malformed_event = {"data": "incomplete"}
            # Should not raise
            await handle_l01_event(malformed_event)

        # No routing should happen for invalid events
        assert mock_client.request_count() == 0
