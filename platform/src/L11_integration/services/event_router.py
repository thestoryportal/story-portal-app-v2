"""
L11 Integration Layer - Event Router.

Routes L01 events to appropriate target layers based on aggregate_type.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import defaultdict

import httpx

from ..models import IntegrationError, ErrorCode


logger = logging.getLogger(__name__)


# Routing table: aggregate_type -> (layer_name, endpoint, port)
ROUTING_TABLE: Dict[str, tuple] = {
    "agent": ("L02_runtime", "/events/agent", 8002),
    "tool": ("L03_tool_execution", "/events/tool", 8003),
    "tool_execution": ("L03_tool_execution", "/events/tool", 8003),
    "plan": ("L05_planning", "/events/plan", 8005),
    "dataset": ("L07_learning", "/events/training", 8007),
    "training_example": ("L07_learning", "/events/training", 8007),
    "session": ("L10_human_interface", "/events/session", 8010),
}


class EventRouter:
    """
    Routes L01 events to target layers based on aggregate_type.

    Maintains a dead letter queue (DLQ) for failed deliveries and
    provides metrics on routing success/failure.
    """

    def __init__(
        self,
        base_urls: Optional[Dict[str, str]] = None,
        timeout: float = 5.0,
        max_dlq_size: int = 1000,
    ):
        """
        Initialize event router.

        Args:
            base_urls: Optional mapping of layer names to base URLs.
                       If not provided, uses localhost with default ports.
            timeout: HTTP request timeout in seconds
            max_dlq_size: Maximum size of dead letter queue per route
        """
        self._base_urls = base_urls or {}
        self._timeout = timeout
        self._max_dlq_size = max_dlq_size
        self._http_client: Optional[httpx.AsyncClient] = None

        # Metrics
        self._events_received = 0
        self._events_routed = 0
        self._route_errors: Dict[str, int] = defaultdict(int)
        self._events_by_type: Dict[str, int] = defaultdict(int)

        # Dead letter queue (per route)
        self._dlq: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the event router."""
        self._http_client = httpx.AsyncClient(timeout=self._timeout)
        logger.info("Event router started")

    async def stop(self) -> None:
        """Stop the event router."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Event router stopped")

    def _get_base_url(self, layer_name: str, port: int) -> str:
        """Get base URL for a layer."""
        if layer_name in self._base_urls:
            return self._base_urls[layer_name]
        return f"http://localhost:{port}"

    async def route_l01_event(self, event: Dict[str, Any]) -> bool:
        """
        Route an L01 event to the appropriate target layer.

        Args:
            event: L01 event dictionary containing:
                - event_type: Type of event (e.g., "agent.created")
                - aggregate_type: Type of aggregate (e.g., "agent")
                - aggregate_id: ID of the aggregate
                - payload: Event payload

        Returns:
            True if event was routed successfully, False otherwise
        """
        async with self._lock:
            self._events_received += 1

        aggregate_type = event.get("aggregate_type", "unknown")
        event_type = event.get("event_type", "unknown")
        aggregate_id = event.get("aggregate_id", "unknown")

        async with self._lock:
            self._events_by_type[aggregate_type] += 1

        # Find route
        route = ROUTING_TABLE.get(aggregate_type)
        if not route:
            logger.debug(
                f"No route for aggregate_type={aggregate_type}, "
                f"event will not be forwarded"
            )
            return False

        layer_name, endpoint, port = route
        base_url = self._get_base_url(layer_name, port)
        url = f"{base_url}{endpoint}"

        logger.debug(
            f"Routing event: {event_type} -> {layer_name} "
            f"(aggregate={aggregate_type}/{aggregate_id})"
        )

        # Send event to target layer
        success = await self._send_event(url, event, layer_name)

        if success:
            async with self._lock:
                self._events_routed += 1
            logger.info(
                f"Event routed: {event_type} -> {layer_name} "
                f"(aggregate={aggregate_type}/{aggregate_id})"
            )
        else:
            # Add to DLQ
            await self._add_to_dlq(layer_name, event)
            async with self._lock:
                self._route_errors[layer_name] += 1
            logger.warning(
                f"Failed to route event: {event_type} -> {layer_name} "
                f"(aggregate={aggregate_type}/{aggregate_id})"
            )

        return success

    async def _send_event(
        self,
        url: str,
        event: Dict[str, Any],
        layer_name: str,
    ) -> bool:
        """
        Send event to target URL.

        Args:
            url: Target URL
            event: Event data
            layer_name: Target layer name (for logging)

        Returns:
            True if successful, False otherwise
        """
        if not self._http_client:
            logger.error("Event router not started")
            return False

        try:
            response = await self._http_client.post(
                url,
                json=event,
                headers={
                    "Content-Type": "application/json",
                    "X-Source-Layer": "L11",
                    "X-Event-Type": event.get("event_type", "unknown"),
                },
            )

            if response.status_code in (200, 201, 202, 204):
                return True
            else:
                logger.warning(
                    f"Event delivery failed: {layer_name} returned {response.status_code}"
                )
                return False

        except httpx.TimeoutException:
            logger.warning(f"Event delivery timeout: {layer_name}")
            return False
        except httpx.ConnectError:
            logger.warning(f"Event delivery connection error: {layer_name} not reachable")
            return False
        except Exception as e:
            logger.error(f"Event delivery error: {layer_name} - {e}")
            return False

    async def _add_to_dlq(self, route: str, event: Dict[str, Any]) -> None:
        """Add event to dead letter queue."""
        async with self._lock:
            dlq = self._dlq[route]
            dlq.append({
                "event": event,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "route": route,
            })
            # Trim if over max size
            if len(dlq) > self._max_dlq_size:
                self._dlq[route] = dlq[-self._max_dlq_size:]

    async def retry_dlq(self, route: Optional[str] = None) -> Dict[str, int]:
        """
        Retry events in dead letter queue.

        Args:
            route: Specific route to retry, or None for all routes

        Returns:
            Dictionary with retry results per route
        """
        results = {}
        routes_to_retry = [route] if route else list(self._dlq.keys())

        for r in routes_to_retry:
            async with self._lock:
                events = self._dlq.get(r, []).copy()
                self._dlq[r] = []

            success_count = 0
            for item in events:
                event = item["event"]
                if await self.route_l01_event(event):
                    success_count += 1

            results[r] = {
                "total": len(events),
                "success": success_count,
                "failed": len(events) - success_count,
            }

        return results

    async def get_dlq_events(
        self,
        route: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get events from dead letter queue.

        Args:
            route: Specific route, or None for all routes
            limit: Maximum events to return

        Returns:
            List of DLQ entries
        """
        async with self._lock:
            if route:
                return self._dlq.get(route, [])[:limit]
            else:
                all_events = []
                for dlq_events in self._dlq.values():
                    all_events.extend(dlq_events)
                return sorted(
                    all_events,
                    key=lambda x: x.get("failed_at", ""),
                    reverse=True,
                )[:limit]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get event router metrics.

        Returns:
            Dictionary with metrics
        """
        return {
            "events_received": self._events_received,
            "events_routed": self._events_routed,
            "success_rate": (
                self._events_routed / self._events_received * 100
                if self._events_received > 0 else 100.0
            ),
            "route_errors": dict(self._route_errors),
            "events_by_type": dict(self._events_by_type),
            "dlq_sizes": {
                route: len(events)
                for route, events in self._dlq.items()
            },
            "routing_table": {
                agg_type: {
                    "layer": layer,
                    "endpoint": endpoint,
                    "port": port,
                }
                for agg_type, (layer, endpoint, port) in ROUTING_TABLE.items()
            },
        }

    async def get_health(self) -> Dict[str, Any]:
        """
        Get event router health status.

        Returns:
            Health status dictionary
        """
        total_dlq_size = sum(len(events) for events in self._dlq.values())
        success_rate = (
            self._events_routed / self._events_received * 100
            if self._events_received > 0 else 100.0
        )

        return {
            "healthy": success_rate >= 90.0 and total_dlq_size < 100,
            "success_rate_percent": round(success_rate, 2),
            "events_received": self._events_received,
            "events_routed": self._events_routed,
            "total_dlq_size": total_dlq_size,
            "http_client_active": self._http_client is not None,
        }
