"""Plans API router for L05 Planning integration."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/", status_code=201)
async def create_plan(plan_data: dict):
    """Create a new execution plan."""
    query = """
        INSERT INTO plans (
            plan_id, goal_id, agent_id, tasks, dependency_graph, status,
            resource_budget, decomposition_strategy, decomposition_latency_ms,
            cache_hit, llm_provider, llm_model, total_tokens_used,
            validation_time_ms, tags, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert complex objects to JSON strings for JSONB columns
        tasks_json = json.dumps(plan_data.get("tasks", []))
        dependency_graph_json = json.dumps(plan_data.get("dependency_graph", {}))
        resource_budget_json = json.dumps(plan_data.get("resource_budget")) if plan_data.get("resource_budget") else None
        metadata_json = json.dumps(plan_data.get("metadata", {}))

        row = await conn.fetchrow(
            query,
            plan_data["plan_id"],
            plan_data["goal_id"],
            plan_data.get("agent_id"),
            tasks_json,
            dependency_graph_json,
            plan_data.get("status", "draft"),
            resource_budget_json,
            plan_data.get("decomposition_strategy", "hybrid"),
            plan_data.get("decomposition_latency_ms"),
            plan_data.get("cache_hit", False),
            plan_data.get("llm_provider"),
            plan_data.get("llm_model"),
            plan_data.get("total_tokens_used", 0),
            plan_data.get("validation_time_ms"),
            plan_data.get("tags", []),
            metadata_json
        )

        return dict(row)


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get plan by plan_id."""
    query = "SELECT * FROM plans WHERE plan_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, plan_id)
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        return dict(row)


@router.patch("/{plan_id}")
async def update_plan(plan_id: str, update_data: dict):
    """Update plan status and execution details."""
    updates = []
    params = [plan_id]
    param_count = 2

    if "status" in update_data:
        updates.append(f"status = ${param_count}")
        params.append(update_data["status"])
        param_count += 1

    if "validated_at" in update_data:
        updates.append(f"validated_at = ${param_count}")
        # Parse ISO timestamp string to datetime
        validated_at = update_data["validated_at"]
        if isinstance(validated_at, str):
            validated_at = datetime.fromisoformat(validated_at)
        params.append(validated_at)
        param_count += 1

    if "execution_started_at" in update_data:
        updates.append(f"execution_started_at = ${param_count}")
        # Parse ISO timestamp string to datetime
        execution_started_at = update_data["execution_started_at"]
        if isinstance(execution_started_at, str):
            execution_started_at = datetime.fromisoformat(execution_started_at)
        params.append(execution_started_at)
        param_count += 1

    if "execution_completed_at" in update_data:
        updates.append(f"execution_completed_at = ${param_count}")
        # Parse ISO timestamp string to datetime
        execution_completed_at = update_data["execution_completed_at"]
        if isinstance(execution_completed_at, str):
            execution_completed_at = datetime.fromisoformat(execution_completed_at)
        params.append(execution_completed_at)
        param_count += 1

    if "execution_time_ms" in update_data:
        updates.append(f"execution_time_ms = ${param_count}")
        params.append(update_data["execution_time_ms"])
        param_count += 1

    if "parallelism_achieved" in update_data:
        updates.append(f"parallelism_achieved = ${param_count}")
        params.append(update_data["parallelism_achieved"])
        param_count += 1

    if "error" in update_data:
        updates.append(f"error = ${param_count}")
        params.append(update_data["error"])
        param_count += 1

    if "completed_task_count" in update_data:
        updates.append(f"completed_task_count = ${param_count}")
        params.append(update_data["completed_task_count"])
        param_count += 1

    if "failed_task_count" in update_data:
        updates.append(f"failed_task_count = ${param_count}")
        params.append(update_data["failed_task_count"])
        param_count += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"""
        UPDATE plans
        SET {", ".join(updates)}
        WHERE plan_id = $1
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        return dict(row)


@router.get("/")
async def list_plans(
    goal_id: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List plans with filters."""
    conditions = []
    params = []
    param_count = 1

    if goal_id:
        conditions.append(f"goal_id = ${param_count}")
        params.append(goal_id)
        param_count += 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if status:
        conditions.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM plans
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
