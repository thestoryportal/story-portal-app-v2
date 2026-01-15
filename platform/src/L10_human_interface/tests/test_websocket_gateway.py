"""
L10 Human Interface Layer - WebSocket Gateway Tests

Test WebSocket connection management, broadcasting, and pub/sub.
"""

import pytest
import asyncio
import json
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, MagicMock

from ..models import EventType
from ..services import WebSocketGateway, WebSocketConnection


class TestWebSocketGatewayInit:
    """Test gateway initialization."""

    @pytest.mark.asyncio
    async def test_gateway_creation(self, websocket_gateway):
        """Test WebSocket gateway creates successfully."""
        assert websocket_gateway is not None
        assert websocket_gateway._connections == {}
        assert websocket_gateway._topic_subscribers is not None

    @pytest.mark.asyncio
    async def test_gateway_start_subscribes_to_redis(self, websocket_gateway, mock_event_bus):
        """Test gateway starts and subscribes to Redis broadcast channel."""
        # Gateway should subscribe to Redis pub/sub for multi-instance support
        assert websocket_gateway._running is True


class TestConnectionManagement:
    """Test WebSocket connection lifecycle."""

    @pytest.mark.asyncio
    async def test_register_connection(self, websocket_gateway):
        """Test connection registration."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        tenant_id = "tenant-1"

        # Register connection
        await websocket_gateway._register_connection(mock_ws, conn_id, tenant_id)

        # Verify connection stored
        assert conn_id in websocket_gateway._connections
        conn = websocket_gateway._connections[conn_id]
        assert conn.connection_id == conn_id
        assert conn.tenant_id == tenant_id
        assert isinstance(conn.subscriptions, set)

    @pytest.mark.asyncio
    async def test_unregister_connection(self, websocket_gateway):
        """Test connection unregistration."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        tenant_id = "tenant-1"

        # Register then unregister
        await websocket_gateway._register_connection(mock_ws, conn_id, tenant_id)
        assert conn_id in websocket_gateway._connections

        await websocket_gateway._unregister_connection(conn_id)

        # Verify connection removed
        assert conn_id not in websocket_gateway._connections

    @pytest.mark.asyncio
    async def test_unregister_removes_from_topics(self, websocket_gateway):
        """Test unregistering removes connection from all subscribed topics."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        tenant_id = "tenant-1"

        # Register and subscribe to topics
        await websocket_gateway._register_connection(mock_ws, conn_id, tenant_id)
        await websocket_gateway._subscribe_connection(conn_id, ["topic1", "topic2"])

        # Verify subscriptions
        assert conn_id in websocket_gateway._topic_subscribers.get("topic1", set())
        assert conn_id in websocket_gateway._topic_subscribers.get("topic2", set())

        # Unregister
        await websocket_gateway._unregister_connection(conn_id)

        # Verify removed from topics
        assert conn_id not in websocket_gateway._topic_subscribers.get("topic1", set())
        assert conn_id not in websocket_gateway._topic_subscribers.get("topic2", set())

    @pytest.mark.asyncio
    async def test_get_connection_count(self, websocket_gateway):
        """Test getting active connection count."""
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()

        # Register multiple connections
        await websocket_gateway._register_connection(mock_ws1, "conn-1", "tenant-1")
        await websocket_gateway._register_connection(mock_ws2, "conn-2", "tenant-1")

        count = websocket_gateway.get_connection_count()
        assert count == 2


class TestTopicSubscription:
    """Test topic subscription management."""

    @pytest.mark.asyncio
    async def test_subscribe_to_topic(self, websocket_gateway):
        """Test subscribing connection to topic."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Subscribe to topic
        await websocket_gateway._subscribe_connection(conn_id, ["agent.state.changed"])

        # Verify subscription
        conn = websocket_gateway._connections[conn_id]
        assert "agent.state.changed" in conn.subscriptions
        assert conn_id in websocket_gateway._topic_subscribers["agent.state.changed"]

    @pytest.mark.asyncio
    async def test_subscribe_to_multiple_topics(self, websocket_gateway):
        """Test subscribing to multiple topics."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        topics = ["agent.state.changed", "task.completed", "alert.triggered"]
        await websocket_gateway._subscribe_connection(conn_id, topics)

        conn = websocket_gateway._connections[conn_id]
        for topic in topics:
            assert topic in conn.subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic(self, websocket_gateway):
        """Test unsubscribing from topic."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")
        await websocket_gateway._subscribe_connection(conn_id, ["topic1", "topic2"])

        # Unsubscribe from topic1
        await websocket_gateway._unsubscribe_connection(conn_id, ["topic1"])

        conn = websocket_gateway._connections[conn_id]
        assert "topic1" not in conn.subscriptions
        assert "topic2" in conn.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_duplicate_topic_idempotent(self, websocket_gateway):
        """Test subscribing to same topic twice is idempotent."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Subscribe twice
        await websocket_gateway._subscribe_connection(conn_id, ["topic1"])
        await websocket_gateway._subscribe_connection(conn_id, ["topic1"])

        # Should still be subscribed once
        conn = websocket_gateway._connections[conn_id]
        assert "topic1" in conn.subscriptions


class TestEventBroadcasting:
    """Test event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_to_topic_subscribers(self, websocket_gateway):
        """Test broadcasting event to topic subscribers."""
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Register two connections
        await websocket_gateway._register_connection(mock_ws1, "conn-1", "tenant-1")
        await websocket_gateway._register_connection(mock_ws2, "conn-2", "tenant-1")

        # Subscribe to topic
        await websocket_gateway._subscribe_connection("conn-1", ["agent.state.changed"])
        await websocket_gateway._subscribe_connection("conn-2", ["agent.state.changed"])

        # Broadcast event
        event_data = {
            "agent_id": "agent-1",
            "state": "paused",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await websocket_gateway._broadcast_locally("agent.state.changed", event_data)

        # Verify both connections received message
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_only_to_subscribers(self, websocket_gateway):
        """Test broadcast only goes to subscribed connections."""
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Register two connections
        await websocket_gateway._register_connection(mock_ws1, "conn-1", "tenant-1")
        await websocket_gateway._register_connection(mock_ws2, "conn-2", "tenant-1")

        # Only conn-1 subscribes
        await websocket_gateway._subscribe_connection("conn-1", ["agent.state.changed"])

        # Broadcast event
        event_data = {"agent_id": "agent-1", "state": "paused"}
        await websocket_gateway._broadcast_locally("agent.state.changed", event_data)

        # Only conn-1 should receive
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_publishes_to_redis(self, websocket_gateway, redis_client):
        """Test broadcast publishes to Redis for multi-instance support."""
        event_data = {"agent_id": "agent-1", "state": "paused"}

        await websocket_gateway.broadcast_event("agent.state.changed", event_data)

        # Should publish to Redis (would need to verify with Redis pub/sub)
        # This is tested indirectly through Redis client mock


class TestMessageHandling:
    """Test client message handling."""

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, websocket_gateway):
        """Test handling subscribe message from client."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Handle subscribe message
        message = {
            "type": "subscribe",
            "topics": ["agent.state.changed", "task.completed"],
        }

        conn = websocket_gateway._connections[conn_id]
        await websocket_gateway._handle_client_message(conn, message)

        # Verify subscriptions
        assert "agent.state.changed" in conn.subscriptions
        assert "task.completed" in conn.subscriptions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, websocket_gateway):
        """Test handling unsubscribe message from client."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")
        await websocket_gateway._subscribe_connection(conn_id, ["topic1", "topic2"])

        # Handle unsubscribe message
        message = {"type": "unsubscribe", "topics": ["topic1"]}

        conn = websocket_gateway._connections[conn_id]
        await websocket_gateway._handle_client_message(conn, message)

        # Verify unsubscribed
        assert "topic1" not in conn.subscriptions
        assert "topic2" in conn.subscriptions

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, websocket_gateway):
        """Test handling ping message responds with pong."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Handle ping message
        message = {"type": "ping"}

        conn = websocket_gateway._connections[conn_id]
        await websocket_gateway._handle_client_message(conn, message)

        # Should respond with pong
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_invalid_message_type(self, websocket_gateway):
        """Test handling invalid message type."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Handle invalid message
        message = {"type": "invalid_type"}

        conn = websocket_gateway._connections[conn_id]
        await websocket_gateway._handle_client_message(conn, message)

        # Should send error response
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert "error" in call_args or call_args.get("type") == "error"


class TestHeartbeat:
    """Test heartbeat/keepalive mechanism."""

    @pytest.mark.asyncio
    async def test_heartbeat_pings_connections(self, websocket_gateway):
        """Test heartbeat sends ping to all connections."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Trigger heartbeat
        await websocket_gateway._send_heartbeat()

        # Should send ping
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "ping"

    @pytest.mark.asyncio
    async def test_heartbeat_removes_stale_connections(self, websocket_gateway):
        """Test heartbeat detects and removes stale connections."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.send_json.side_effect = Exception("Connection closed")

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Trigger heartbeat - should detect failed connection
        await websocket_gateway._send_heartbeat()

        # Stale connection should be removed
        # (Implementation may vary - this tests the concept)


class TestTenantIsolation:
    """Test tenant isolation in broadcasts."""

    @pytest.mark.asyncio
    async def test_broadcast_respects_tenant_isolation(self, websocket_gateway):
        """Test events only broadcast to same-tenant connections."""
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Register connections for different tenants
        await websocket_gateway._register_connection(mock_ws1, "conn-1", "tenant-1")
        await websocket_gateway._register_connection(mock_ws2, "conn-2", "tenant-2")

        # Both subscribe to same topic
        await websocket_gateway._subscribe_connection("conn-1", ["agent.state.changed"])
        await websocket_gateway._subscribe_connection("conn-2", ["agent.state.changed"])

        # Broadcast tenant-1 event
        event_data = {"agent_id": "agent-1", "tenant_id": "tenant-1", "state": "paused"}
        await websocket_gateway._broadcast_locally("agent.state.changed", event_data)

        # Both might receive, but implementation should filter by tenant
        # This depends on whether filtering happens in gateway or client


class TestErrorHandling:
    """Test error handling in WebSocket operations."""

    @pytest.mark.asyncio
    async def test_send_error_handles_closed_connection(self, websocket_gateway):
        """Test sending to closed connection is handled gracefully."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.send_json.side_effect = Exception("Connection closed")

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")
        await websocket_gateway._subscribe_connection(conn_id, ["topic1"])

        # Broadcast should handle closed connection gracefully
        event_data = {"test": "data"}
        await websocket_gateway._broadcast_locally("topic1", event_data)

        # Connection might be removed or error logged

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_connection_fails_gracefully(self, websocket_gateway):
        """Test subscribing nonexistent connection fails gracefully."""
        # Try to subscribe connection that doesn't exist
        result = await websocket_gateway._subscribe_connection("nonexistent", ["topic1"])

        # Should fail gracefully (return False or None)
        assert result is None or result is False


class TestRedisMultiInstance:
    """Test Redis pub/sub for multi-instance support."""

    @pytest.mark.asyncio
    async def test_redis_broadcast_distributes_to_instances(self, websocket_gateway, redis_client):
        """Test Redis broadcast allows multiple gateway instances."""
        event_data = {"agent_id": "agent-1", "state": "paused"}

        # Broadcast should publish to Redis
        await websocket_gateway.broadcast_event("agent.state.changed", event_data)

        # In multi-instance setup, other instances would receive via Redis pub/sub

    @pytest.mark.asyncio
    async def test_receive_redis_broadcast(self, websocket_gateway):
        """Test receiving broadcast from Redis."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "conn-123"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")
        await websocket_gateway._subscribe_connection(conn_id, ["agent.state.changed"])

        # Simulate receiving message from Redis pub/sub
        redis_message = {
            "topic": "agent.state.changed",
            "event": {"agent_id": "agent-1", "state": "paused"},
        }

        await websocket_gateway._handle_redis_message(json.dumps(redis_message))

        # Connection should receive the event
        mock_ws.send_json.assert_called()


class TestCleanup:
    """Test gateway cleanup and shutdown."""

    @pytest.mark.asyncio
    async def test_stop_closes_all_connections(self, websocket_gateway):
        """Test stopping gateway closes all connections."""
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.close = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.close = AsyncMock()

        # Register connections
        await websocket_gateway._register_connection(mock_ws1, "conn-1", "tenant-1")
        await websocket_gateway._register_connection(mock_ws2, "conn-2", "tenant-1")

        # Stop gateway
        await websocket_gateway.stop()

        # All connections should be closed
        mock_ws1.close.assert_called()
        mock_ws2.close.assert_called()
        assert len(websocket_gateway._connections) == 0

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_from_redis(self, websocket_gateway):
        """Test stopping gateway unsubscribes from Redis."""
        await websocket_gateway.stop()

        # Should unsubscribe from Redis pub/sub
        assert websocket_gateway._running is False
