"""Compliance Results API router for L06 Evaluation integration."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/compliance-results", tags=["compliance_results"])


@router.post("/", status_code=201)
async def create_compliance_result(result_data: dict):
    """Create a new compliance result record."""
    query = """
        INSERT INTO compliance_results (
            result_id, execution_id, agent_id, agent_did, tenant_id,
            timestamp, compliant, violations, constraints_checked
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert timestamp string to datetime if needed
        timestamp = result_data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Convert arrays to JSON strings for JSONB columns
        violations_json = json.dumps(result_data.get("violations", []))
        constraints_json = json.dumps(result_data.get("constraints_checked", []))

        row = await conn.fetchrow(
            query,
            result_data["result_id"],
            result_data["execution_id"],
            result_data.get("agent_id"),
            result_data["agent_did"],
            result_data["tenant_id"],
            timestamp,
            result_data["compliant"],
            violations_json,
            constraints_json
        )

        return dict(row)


@router.get("/{result_id}")
async def get_compliance_result(result_id: str):
    """Get compliance result by result_id."""
    query = "SELECT * FROM compliance_results WHERE result_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, result_id)
        if not row:
            raise HTTPException(status_code=404, detail="Compliance result not found")
        return dict(row)


@router.get("/")
async def list_compliance_results(
    execution_id: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    compliant: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """List compliance results with filters."""
    conditions = []
    params = []
    param_count = 1

    if execution_id:
        conditions.append(f"execution_id = ${param_count}")
        params.append(execution_id)
        param_count += 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if tenant_id:
        conditions.append(f"tenant_id = ${param_count}")
        params.append(tenant_id)
        param_count += 1

    if compliant is not None:
        conditions.append(f"compliant = ${param_count}")
        params.append(compliant)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM compliance_results
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
