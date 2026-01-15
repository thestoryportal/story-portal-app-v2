"""Goal store service."""

import asyncpg
import json
from typing import List, Optional
from uuid import UUID

from ..models import Goal, GoalCreate, GoalUpdate


class GoalStore:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    def _row_to_goal(self, row) -> Goal:
        """Convert database row to Goal model, parsing JSON fields."""
        goal_dict = dict(row)
        # Parse success_criteria if it's a string
        if 'success_criteria' in goal_dict and isinstance(goal_dict['success_criteria'], str):
            goal_dict['success_criteria'] = json.loads(goal_dict['success_criteria'])
        return Goal(**goal_dict)

    async def create_goal(self, goal_data: GoalCreate) -> Goal:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO goals (agent_id, description, success_criteria, priority, parent_goal_id)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING id, agent_id, description, success_criteria, status, priority, parent_goal_id, created_at, updated_at, completed_at
                """,
                goal_data.agent_id, goal_data.description, json.dumps(goal_data.success_criteria),
                goal_data.priority, goal_data.parent_goal_id,
            )
        return self._row_to_goal(row)

    async def get_goal(self, goal_id: UUID) -> Optional[Goal]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, agent_id, description, success_criteria, status, priority, parent_goal_id, created_at, updated_at, completed_at FROM goals WHERE id = $1",
                goal_id,
            )
        return self._row_to_goal(row) if row else None

    async def update_goal(self, goal_id: UUID, goal_data: GoalUpdate) -> Optional[Goal]:
        update_fields = []
        params = []
        param_count = 1
        for field, value in goal_data.model_dump(exclude_unset=True).items():
            if value is not None:
                # Handle JSON fields
                if field == 'success_criteria':
                    update_fields.append(f"{field} = ${param_count}::jsonb")
                    params.append(json.dumps(value))
                else:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value.value if hasattr(value, 'value') else value)
                param_count += 1
        if not update_fields:
            return await self.get_goal(goal_id)
        update_fields.append("updated_at = NOW()")
        query = f"UPDATE goals SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING id, agent_id, description, success_criteria, status, priority, parent_goal_id, created_at, updated_at, completed_at"
        params.append(goal_id)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        return self._row_to_goal(row) if row else None

    async def list_goals(self, agent_id: Optional[UUID] = None, limit: int = 100) -> List[Goal]:
        if agent_id:
            query = "SELECT id, agent_id, description, success_criteria, status, priority, parent_goal_id, created_at, updated_at, completed_at FROM goals WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2"
            params = [agent_id, limit]
        else:
            query = "SELECT id, agent_id, description, success_criteria, status, priority, parent_goal_id, created_at, updated_at, completed_at FROM goals ORDER BY created_at DESC LIMIT $1"
            params = [limit]
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [self._row_to_goal(row) for row in rows]
