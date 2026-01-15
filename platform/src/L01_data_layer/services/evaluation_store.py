"""Evaluation store service."""

import asyncpg
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models import Evaluation, EvaluationCreate


class EvaluationStore:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def record_evaluation(self, eval_data: EvaluationCreate) -> Evaluation:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO evaluations (agent_id, task_id, evaluation_type, score, metrics, feedback) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, agent_id, task_id, evaluation_type, score, metrics, feedback, created_at",
                eval_data.agent_id, eval_data.task_id, eval_data.evaluation_type, eval_data.score, eval_data.metrics, eval_data.feedback,
            )
        return Evaluation(**dict(row))

    async def get_evaluation(self, evaluation_id: UUID) -> Optional[Evaluation]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, agent_id, task_id, evaluation_type, score, metrics, feedback, created_at FROM evaluations WHERE id = $1",
                evaluation_id,
            )
        return Evaluation(**dict(row)) if row else None

    async def list_evaluations(self, agent_id: Optional[UUID] = None, limit: int = 100) -> List[Evaluation]:
        if agent_id:
            query = "SELECT id, agent_id, task_id, evaluation_type, score, metrics, feedback, created_at FROM evaluations WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2"
            params = [agent_id, limit]
        else:
            query = "SELECT id, agent_id, task_id, evaluation_type, score, metrics, feedback, created_at FROM evaluations ORDER BY created_at DESC LIMIT $1"
            params = [limit]
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [Evaluation(**dict(row)) for row in rows]

    async def get_agent_stats(self, agent_id: UUID) -> Dict[str, Any]:
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                "SELECT COUNT(*) as total_evaluations, AVG(score) as avg_score, MIN(score) as min_score, MAX(score) as max_score FROM evaluations WHERE agent_id = $1",
                agent_id,
            )
        return dict(stats) if stats else {"total_evaluations": 0, "avg_score": None, "min_score": None, "max_score": None}
