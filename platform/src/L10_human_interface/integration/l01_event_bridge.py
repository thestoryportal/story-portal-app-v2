"""
L10 Human Interface Layer - L01 Event Bridge

Bridge between L10 Human Interface and L01 Data Layer for event queries.
Uses L01's event store API to query and retrieve event history.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from ..models import EventSummary, EventDetail, EventFilter

logger = logging.getLogger(__name__)


class L01EventBridge:
    """
    Bridge between L10 Human Interface and L01 Data Layer for events.

    Responsibilities:
    - Query events with filtering and pagination
    - Get event details by ID
    - Record control events
    """

    def __init__(
        self,
        l01_base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize L01 Event Bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
            api_key: API key for L01 authentication
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("L01_API_KEY", "dev_key_local_ONLY")
        self.l01_base_url = l01_base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self.enabled = True
        logger.info(f"L01EventBridge initialized with base_url={l01_base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            self._client = httpx.AsyncClient(
                base_url=self.l01_base_url,
                timeout=self.timeout,
                headers=headers
            )
        return self._client

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L01EventBridge initialized")

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("L01EventBridge cleanup complete")

    async def query_events(
        self,
        filters: EventFilter,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[List[EventSummary], int]:
        """Query events with filtering and pagination.

        Args:
            filters: EventFilter with query parameters
            limit: Maximum results to return
            offset: Number of results to skip
            sort_by: Field to sort by
            sort_order: Sort direction (asc or desc)

        Returns:
            Tuple of (list of EventSummary objects, total count)
        """
        if not self.enabled:
            return [], 0

        try:
            client = await self._get_client()

            params: Dict[str, Any] = {
                "limit": limit,
                "offset": offset,
            }

            # Add filter parameters
            if filters.event_types:
                params["event_type"] = ",".join(filters.event_types)
            if filters.agent_id:
                params["aggregate_id"] = filters.agent_id
            if filters.tenant_id:
                params["tenant_id"] = filters.tenant_id
            if filters.start_time:
                params["start"] = filters.start_time.isoformat()
            if filters.end_time:
                params["end"] = filters.end_time.isoformat()
            if filters.search_text:
                params["search"] = filters.search_text

            response = await client.get("/events/", params=params)
            response.raise_for_status()

            data = response.json()

            # L01 may return a list or a paginated response
            events_data = data if isinstance(data, list) else data.get("events", data)
            total = len(events_data) if isinstance(data, list) else data.get("total", len(events_data))

            events: List[EventSummary] = []
            for event_data in events_data:
                try:
                    event = self._parse_event_summary(event_data)
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")

            logger.debug(f"Retrieved {len(events)} events from L01 (total={total})")
            return events, total

        except httpx.HTTPStatusError as e:
            logger.error(f"L01 HTTP error: {e.response.status_code} - {e.response.text}")
            return [], 0
        except httpx.ConnectError as e:
            logger.error(f"L01 connection error: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"Failed to query events from L01: {e}")
            return [], 0

    async def get_event(self, event_id: str) -> Optional[EventDetail]:
        """Get a specific event by ID.

        Args:
            event_id: Event ID

        Returns:
            EventDetail object or None if not found
        """
        if not self.enabled:
            return None

        try:
            client = await self._get_client()

            response = await client.get(f"/events/{event_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()

            data = response.json()
            return self._parse_event_detail(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"L01 HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to get event {event_id} from L01: {e}")
            return None

    async def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "l10",
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record an event in L01.

        Args:
            event_type: Type of event
            payload: Event payload
            source: Event source (default: l10)
            aggregate_id: Aggregate ID (e.g., agent_id)
            aggregate_type: Aggregate type (e.g., agent, workflow)
            tenant_id: Tenant ID
            correlation_id: Correlation ID for tracing
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            client = await self._get_client()

            event_data: Dict[str, Any] = {
                "event_type": event_type,
                "payload": payload,
                "source": source,
            }
            if aggregate_id:
                event_data["aggregate_id"] = aggregate_id
            if aggregate_type:
                event_data["aggregate_type"] = aggregate_type
            if tenant_id:
                event_data["tenant_id"] = tenant_id
            if correlation_id:
                event_data["correlation_id"] = correlation_id
            if metadata:
                event_data["metadata"] = metadata

            response = await client.post("/events/", json=event_data)
            response.raise_for_status()

            logger.info(f"Recorded event {event_type} in L01")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"L01 HTTP error recording event: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Failed to record event in L01: {e}")
            return False

    def _parse_event_summary(self, data: Dict[str, Any]) -> EventSummary:
        """Parse event data to EventSummary.

        Args:
            data: Raw event data from L01

        Returns:
            EventSummary object
        """
        # Parse timestamp
        timestamp_str = data.get("timestamp") or data.get("created_at", "")
        if timestamp_str:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = timestamp_str
        else:
            timestamp = datetime.utcnow()

        # Extract severity from payload if present
        payload = data.get("payload", {})
        severity = payload.get("severity") or data.get("severity")

        # Generate summary from payload or event type
        summary = payload.get("summary") or payload.get("message") or data.get("event_type", "")

        return EventSummary(
            event_id=data.get("event_id") or data.get("id", ""),
            event_type=data.get("event_type", ""),
            aggregate_id=data.get("aggregate_id", ""),
            aggregate_type=data.get("aggregate_type", "unknown"),
            timestamp=timestamp,
            tenant_id=data.get("tenant_id", ""),
            severity=severity,
            summary=summary[:200] if summary else None,  # Truncate long summaries
        )

    def _parse_event_detail(self, data: Dict[str, Any]) -> EventDetail:
        """Parse event data to EventDetail.

        Args:
            data: Raw event data from L01

        Returns:
            EventDetail object
        """
        # Parse timestamp
        timestamp_str = data.get("timestamp") or data.get("created_at", "")
        if timestamp_str:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = timestamp_str
        else:
            timestamp = datetime.utcnow()

        return EventDetail(
            event_id=data.get("event_id") or data.get("id", ""),
            event_type=data.get("event_type", ""),
            aggregate_id=data.get("aggregate_id", ""),
            aggregate_type=data.get("aggregate_type", "unknown"),
            timestamp=timestamp,
            tenant_id=data.get("tenant_id", ""),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            version=data.get("version", 1),
        )
