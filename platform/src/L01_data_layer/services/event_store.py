"""Event store service for event sourcing."""

import asyncpg
from typing import List, Optional
from uuid import UUID
import logging

from ..models import Event, EventCreate
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class EventStore:
    """Event store for event sourcing."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: RedisClient):
        self.db_pool = db_pool
        self.redis_client = redis_client

    async def create_event(self, event_data: EventCreate) -> Event:
        """Create a new event."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO events (event_type, aggregate_type, aggregate_id, payload, metadata, version)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, event_type, aggregate_type, aggregate_id, payload, metadata, created_at, version
                """,
                event_data.event_type,
                event_data.aggregate_type,
                event_data.aggregate_id,
                event_data.payload,
                event_data.metadata,
                event_data.version,
            )

        event = Event(
            id=row["id"],
            event_type=row["event_type"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            payload=row["payload"],
            metadata=row["metadata"],
            created_at=row["created_at"],
            version=row["version"],
        )

        # Publish to Redis
        await self.redis_client.publish_event(
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=str(event.aggregate_id),
            payload=event.payload,
            metadata=event.metadata,
        )

        logger.info(f"Created event {event.id} of type {event.event_type}")
        return event

    async def get_event(self, event_id: UUID) -> Optional[Event]:
        """Get event by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, event_type, aggregate_type, aggregate_id, payload, metadata, created_at, version FROM events WHERE id = $1",
                event_id,
            )

        if not row:
            return None

        return Event(**dict(row))

    async def query_events(
        self,
        aggregate_id: Optional[UUID] = None,
        aggregate_type: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        """Query events with filters."""
        conditions = []
        params = []
        param_count = 1

        if aggregate_id:
            conditions.append(f"aggregate_id = ${param_count}")
            params.append(aggregate_id)
            param_count += 1

        if aggregate_type:
            conditions.append(f"aggregate_type = ${param_count}")
            params.append(aggregate_type)
            param_count += 1

        if event_type:
            conditions.append(f"event_type = ${param_count}")
            params.append(event_type)
            param_count += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT id, event_type, aggregate_type, aggregate_id, payload, metadata, created_at, version
            FROM events
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [Event(**dict(row)) for row in rows]
