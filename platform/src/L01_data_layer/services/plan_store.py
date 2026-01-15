"""Plan store service."""

import asyncpg
from typing import List, Optional
from uuid import UUID

from ..models import Plan, PlanCreate, PlanUpdate, Task, TaskCreate, TaskUpdate


class PlanStore:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def create_plan(self, plan_data: PlanCreate) -> Plan:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO plans (goal_id, agent_id, plan_type, steps) VALUES ($1, $2, $3, $4) RETURNING id, goal_id, agent_id, plan_type, steps, status, current_step, created_at, updated_at",
                plan_data.goal_id, plan_data.agent_id, plan_data.plan_type, plan_data.steps,
            )
        return Plan(**dict(row))

    async def get_plan(self, plan_id: UUID) -> Optional[Plan]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, goal_id, agent_id, plan_type, steps, status, current_step, created_at, updated_at FROM plans WHERE id = $1",
                plan_id,
            )
        return Plan(**dict(row)) if row else None

    async def update_plan(self, plan_id: UUID, plan_data: PlanUpdate) -> Optional[Plan]:
        update_fields = []
        params = []
        param_count = 1
        for field, value in plan_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value.value if hasattr(value, 'value') else value)
                param_count += 1
        if not update_fields:
            return await self.get_plan(plan_id)
        update_fields.append("updated_at = NOW()")
        query = f"UPDATE plans SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING id, goal_id, agent_id, plan_type, steps, status, current_step, created_at, updated_at"
        params.append(plan_id)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        return Plan(**dict(row)) if row else None

    async def create_task(self, task_data: TaskCreate) -> Task:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tasks (plan_id, agent_id, description, task_type, input_data, sequence_order) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at",
                task_data.plan_id, task_data.agent_id, task_data.description, task_data.task_type, task_data.input_data, task_data.sequence_order,
            )
        return Task(**dict(row))

    async def update_task(self, task_id: UUID, task_data: TaskUpdate) -> Optional[Task]:
        update_fields = []
        params = []
        param_count = 1
        for field, value in task_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value.value if hasattr(value, 'value') else value)
                param_count += 1
        if not update_fields:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at FROM tasks WHERE id = $1",
                    task_id,
                )
            return Task(**dict(row)) if row else None
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at"
        params.append(task_id)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        return Task(**dict(row)) if row else None

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at FROM tasks WHERE id = $1",
                task_id,
            )
        return Task(**dict(row)) if row else None

    async def list_tasks(self, plan_id: Optional[UUID] = None, limit: int = 100) -> List[Task]:
        if plan_id:
            query = "SELECT id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at FROM tasks WHERE plan_id = $1 ORDER BY sequence_order LIMIT $2"
            params = [plan_id, limit]
        else:
            query = "SELECT id, plan_id, agent_id, description, task_type, input_data, output_data, status, sequence_order, created_at, started_at, completed_at FROM tasks ORDER BY created_at DESC LIMIT $1"
            params = [limit]
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [Task(**dict(row)) for row in rows]
