"""Session service."""

import asyncpg
import json
import logging
from typing import List, Optional
from uuid import UUID

from ..models import Session, SessionCreate, SessionUpdate
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, db_pool: asyncpg.Pool, redis_client: Optional[RedisClient] = None):
        self.db_pool = db_pool
        self.redis_client = redis_client

    def _row_to_session(self, row) -> Session:
        """Convert database row to Session model, parsing JSON fields."""
        session_dict = dict(row)
        # Parse JSON fields that might be returned as strings
        for field in ['context', 'checkpoint', 'runtime_metadata']:
            if field in session_dict and isinstance(session_dict[field], str):
                session_dict[field] = json.loads(session_dict[field])
        return Session(**session_dict)

    async def create_session(self, session_data: SessionCreate) -> Session:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sessions (agent_id, session_type, context, runtime_backend, runtime_metadata)
                VALUES ($1, $2, $3::jsonb, $4, $5::jsonb)
                RETURNING id, agent_id, session_type, status, context, checkpoint,
                          runtime_backend, runtime_metadata, created_at, updated_at
                """,
                session_data.agent_id,
                session_data.session_type,
                json.dumps(session_data.context),
                session_data.runtime_backend.value if session_data.runtime_backend else None,
                json.dumps(session_data.runtime_metadata),
            )

        session = self._row_to_session(row)

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="session.created",
                aggregate_type="session",
                aggregate_id=str(session.id),
                payload={
                    "agent_id": str(session.agent_id),
                    "session_type": session.session_type,
                    "runtime_backend": session.runtime_backend.value if session.runtime_backend else None,
                },
            )

        logger.info(f"Created session {session.id} for agent {session.agent_id}")
        return session

    async def get_session(self, session_id: UUID) -> Optional[Session]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, agent_id, session_type, status, context, checkpoint,
                       runtime_backend, runtime_metadata, created_at, updated_at
                FROM sessions WHERE id = $1
                """,
                session_id,
            )
        return self._row_to_session(row) if row else None

    async def update_session(self, session_id: UUID, session_data: SessionUpdate) -> Optional[Session]:
        update_fields = []
        params = []
        param_count = 1

        for field, value in session_data.model_dump(exclude_unset=True).items():
            if value is not None:
                # Handle JSON fields
                if field in ['context', 'checkpoint', 'runtime_metadata']:
                    update_fields.append(f"{field} = ${param_count}::jsonb")
                    params.append(json.dumps(value))
                # Handle enum fields
                elif hasattr(value, 'value'):
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value.value)
                else:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                param_count += 1

        if not update_fields:
            return await self.get_session(session_id)

        update_fields.append("updated_at = NOW()")
        query = f"""
            UPDATE sessions SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, agent_id, session_type, status, context, checkpoint,
                      runtime_backend, runtime_metadata, created_at, updated_at
        """
        params.append(session_id)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        session = self._row_to_session(row) if row else None

        # Publish event
        if session and self.redis_client:
            await self.redis_client.publish_event(
                event_type="session.updated",
                aggregate_type="session",
                aggregate_id=str(session.id),
                payload={
                    "agent_id": str(session.agent_id),
                    "status": session.status.value,
                    "updates": list(session_data.model_dump(exclude_unset=True).keys()),
                },
            )

        return session

    async def list_sessions(self, agent_id: Optional[UUID] = None, limit: int = 100) -> List[Session]:
        if agent_id:
            query = """
                SELECT id, agent_id, session_type, status, context, checkpoint,
                       runtime_backend, runtime_metadata, created_at, updated_at
                FROM sessions WHERE agent_id = $1
                ORDER BY created_at DESC LIMIT $2
            """
            params = [agent_id, limit]
        else:
            query = """
                SELECT id, agent_id, session_type, status, context, checkpoint,
                       runtime_backend, runtime_metadata, created_at, updated_at
                FROM sessions
                ORDER BY created_at DESC LIMIT $1
            """
            params = [limit]

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_session(row) for row in rows]
