"""Goals API router for L05 Planning integration."""

import json
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("/", status_code=201)
async def create_goal(goal_data: dict):
    """Create a new goal."""
    query = """
        INSERT INTO goals (
            goal_id, agent_id, agent_did, goal_text, goal_type, status,
            constraints_max_token_budget, constraints_max_execution_time_sec,
            constraints_max_parallelism, constraints_deadline_unix_ms,
            constraints_priority, constraints_require_approval,
            constraints_allowed_agent_types, constraints_forbidden_tools,
            constraints_cost_limit_usd, metadata, parent_goal_id,
            decomposition_strategy
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Extract constraints
        constraints = goal_data.get("constraints", {})

        # Convert metadata dict to JSON string for JSONB
        metadata = goal_data.get("metadata", {})
        metadata_json = json.dumps(metadata) if metadata else "{}"

        row = await conn.fetchrow(
            query,
            goal_data["goal_id"],
            goal_data.get("agent_id"),
            goal_data["agent_did"],
            goal_data["goal_text"],
            goal_data.get("goal_type", "compound"),
            goal_data.get("status", "pending"),
            constraints.get("max_token_budget"),
            constraints.get("max_execution_time_sec"),
            constraints.get("max_parallelism", 10),
            constraints.get("deadline_unix_ms"),
            constraints.get("priority", 5),
            constraints.get("require_approval", False),
            constraints.get("allowed_agent_types"),
            constraints.get("forbidden_tools"),
            constraints.get("cost_limit_usd"),
            metadata_json,
            goal_data.get("parent_goal_id"),
            goal_data.get("decomposition_strategy")
        )

        return dict(row)


@router.get("/{goal_id}")
async def get_goal(goal_id: str):
    """Get goal by goal_id."""
    query = "SELECT * FROM goals WHERE goal_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, goal_id)
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        return dict(row)


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, update_data: dict):
    """Update goal status and fields."""
    updates = []
    params = [goal_id]
    param_count = 2

    if "status" in update_data:
        updates.append(f"status = ${param_count}")
        params.append(update_data["status"])
        param_count += 1

    if "decomposition_strategy" in update_data:
        updates.append(f"decomposition_strategy = ${param_count}")
        params.append(update_data["decomposition_strategy"])
        param_count += 1

    updates.append(f"updated_at = NOW()")

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"""
        UPDATE goals
        SET {", ".join(updates)}
        WHERE goal_id = $1
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        return dict(row)


@router.get("/")
async def list_goals(
    agent_id: Optional[UUID] = None,
    agent_did: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List goals with filters."""
    conditions = []
    params = []
    param_count = 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if agent_did:
        conditions.append(f"agent_did = ${param_count}")
        params.append(agent_did)
        param_count += 1

    if status:
        conditions.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM goals
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
