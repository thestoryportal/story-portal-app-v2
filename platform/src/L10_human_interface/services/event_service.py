"""
L10 Human Interface Layer - Event Service

Query event history with filtering and pagination via L01 Data Layer.
"""

import logging
from typing import Optional

from ..models import (
    EventQuery,
    EventSummary,
    EventDetail,
    EventResponse,
    ErrorCode,
    InterfaceError,
)
from ..integration.l01_event_bridge import L01EventBridge

logger = logging.getLogger(__name__)


class EventService:
    """Event service for querying event history via L01 Data Layer."""

    def __init__(
        self,
        l01_event_bridge: Optional[L01EventBridge] = None,
        event_bus=None,
        audit_logger=None,
    ):
        """Initialize EventService.

        Args:
            l01_event_bridge: Bridge to L01 Data Layer for event queries
            event_bus: Optional legacy event bus (for backward compat)
            audit_logger: Optional audit logger
        """
        self.l01_bridge = l01_event_bridge
        self.event_bus = event_bus
        self.audit_logger = audit_logger

    async def query_events(self, query: EventQuery) -> EventResponse:
        """Query events with filtering and pagination.

        Args:
            query: EventQuery with filters, limit, offset

        Returns:
            EventResponse with events and pagination info

        Raises:
            InterfaceError: E10401 if query fails, E10403 for invalid filters
        """
        try:
            # Validate query
            if query.limit < 1 or query.limit > 1000:
                raise InterfaceError.from_code(
                    ErrorCode.E10403,
                    details={"limit": query.limit, "reason": "Limit must be between 1 and 1000"},
                )

            if query.offset < 0:
                raise InterfaceError.from_code(
                    ErrorCode.E10403,
                    details={"offset": query.offset, "reason": "Offset must be non-negative"},
                )

            # Check if start_time is after end_time
            if query.filters.start_time and query.filters.end_time:
                if query.filters.start_time > query.filters.end_time:
                    raise InterfaceError.from_code(
                        ErrorCode.E10403,
                        details={
                            "start_time": query.filters.start_time.isoformat(),
                            "end_time": query.filters.end_time.isoformat(),
                            "reason": "start_time must be before end_time",
                        },
                    )

            if not self.l01_bridge:
                logger.warning("L01 event bridge not configured, returning empty response")
                return EventResponse(
                    events=[],
                    total=0,
                    limit=query.limit,
                    offset=query.offset,
                    has_more=False,
                )

            # Query events from L01
            events, total = await self.l01_bridge.query_events(
                filters=query.filters,
                limit=query.limit,
                offset=query.offset,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
            )

            # Calculate has_more
            has_more = (query.offset + len(events)) < total

            logger.debug(
                f"Query returned {len(events)} events (total={total}, "
                f"offset={query.offset}, limit={query.limit})"
            )

            return EventResponse(
                events=events,
                total=total,
                limit=query.limit,
                offset=query.offset,
                has_more=has_more,
            )

        except InterfaceError:
            raise
        except Exception as e:
            logger.error(f"Event query failed: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10401,
                details={"error": str(e)},
            )

    async def get_event_details(self, event_id: str) -> EventDetail:
        """Get full event details by ID.

        Args:
            event_id: Event ID

        Returns:
            EventDetail with full payload

        Raises:
            InterfaceError: E10402 if event not found, E10401 if query fails
        """
        try:
            if not event_id:
                raise InterfaceError.from_code(
                    ErrorCode.E10403,
                    details={"event_id": event_id, "reason": "Event ID is required"},
                )

            if not self.l01_bridge:
                raise InterfaceError.from_code(
                    ErrorCode.E10902,
                    details={"reason": "L01 event bridge not configured"},
                )

            # Get event from L01
            event = await self.l01_bridge.get_event(event_id)

            if not event:
                raise InterfaceError.from_code(
                    ErrorCode.E10402,
                    details={"event_id": event_id},
                )

            logger.debug(f"Retrieved event details for {event_id}")
            return event

        except InterfaceError:
            raise
        except Exception as e:
            logger.error(f"Failed to get event details: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10401,
                details={"event_id": event_id, "error": str(e)},
            )

    async def record_control_event(
        self,
        event_type: str,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> bool:
        """Record a control operation event.

        Args:
            event_type: Type of control event (e.g., agent.paused, agent.stopped)
            agent_id: Agent ID
            tenant_id: Tenant ID
            user_id: User who triggered the operation
            payload: Event payload with operation details

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.l01_bridge:
            logger.warning("L01 event bridge not configured, skipping event recording")
            return False

        try:
            return await self.l01_bridge.record_event(
                event_type=event_type,
                payload={
                    **payload,
                    "user_id": user_id,
                },
                source="l10",
                aggregate_id=agent_id,
                aggregate_type="agent",
                tenant_id=tenant_id,
            )
        except Exception as e:
            logger.error(f"Failed to record control event: {e}")
            return False
