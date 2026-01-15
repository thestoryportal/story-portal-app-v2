"""Feedback store service."""

import asyncpg
from typing import List, Optional
from uuid import UUID

from ..models import FeedbackEntry, FeedbackCreate, FeedbackUpdate


class FeedbackStore:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def record_feedback(self, feedback_data: FeedbackCreate) -> FeedbackEntry:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO feedback_entries (agent_id, task_id, feedback_type, rating, content, metadata) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at",
                feedback_data.agent_id, feedback_data.task_id, feedback_data.feedback_type, feedback_data.rating, feedback_data.content, feedback_data.metadata,
            )
        return FeedbackEntry(**dict(row))

    async def get_feedback(self, feedback_id: UUID) -> Optional[FeedbackEntry]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at FROM feedback_entries WHERE id = $1",
                feedback_id,
            )
        return FeedbackEntry(**dict(row)) if row else None

    async def list_feedback(self, agent_id: Optional[UUID] = None, limit: int = 100) -> List[FeedbackEntry]:
        if agent_id:
            query = "SELECT id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at FROM feedback_entries WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2"
            params = [agent_id, limit]
        else:
            query = "SELECT id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at FROM feedback_entries ORDER BY created_at DESC LIMIT $1"
            params = [limit]
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [FeedbackEntry(**dict(row)) for row in rows]

    async def get_unprocessed_feedback(self, limit: int = 100) -> List[FeedbackEntry]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at FROM feedback_entries WHERE processed = FALSE ORDER BY created_at LIMIT $1",
                limit,
            )
        return [FeedbackEntry(**dict(row)) for row in rows]

    async def update_feedback(self, feedback_id: UUID, feedback_data: FeedbackUpdate) -> Optional[FeedbackEntry]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE feedback_entries SET processed = $1 WHERE id = $2 RETURNING id, agent_id, task_id, feedback_type, rating, content, metadata, processed, created_at",
                feedback_data.processed, feedback_id,
            )
        return FeedbackEntry(**dict(row)) if row else None
