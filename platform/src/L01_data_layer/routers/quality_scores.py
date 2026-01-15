"""Quality Scores API router for L06 Evaluation integration."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/quality-scores", tags=["quality_scores"])


@router.post("/", status_code=201)
async def create_quality_score(score_data: dict):
    """Create a new quality score record."""
    query = """
        INSERT INTO quality_scores (
            score_id, agent_id, agent_did, tenant_id, timestamp,
            overall_score, assessment, data_completeness, cached,
            dimensions, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert timestamp string to datetime if needed
        timestamp = score_data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Convert complex objects to JSON strings for JSONB columns
        dimensions_json = json.dumps(score_data.get("dimensions", {}))
        metadata_json = json.dumps(score_data.get("metadata", {}))

        row = await conn.fetchrow(
            query,
            score_data["score_id"],
            score_data.get("agent_id"),
            score_data["agent_did"],
            score_data["tenant_id"],
            timestamp,
            score_data["overall_score"],
            score_data["assessment"],
            score_data.get("data_completeness", 1.0),
            score_data.get("cached", False),
            dimensions_json,
            metadata_json
        )

        return dict(row)


@router.get("/{score_id}")
async def get_quality_score(score_id: str):
    """Get quality score by score_id."""
    query = "SELECT * FROM quality_scores WHERE score_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, score_id)
        if not row:
            raise HTTPException(status_code=404, detail="Quality score not found")
        return dict(row)


@router.get("/")
async def list_quality_scores(
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    assessment: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List quality scores with filters."""
    conditions = []
    params = []
    param_count = 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if tenant_id:
        conditions.append(f"tenant_id = ${param_count}")
        params.append(tenant_id)
        param_count += 1

    if assessment:
        conditions.append(f"assessment = ${param_count}")
        params.append(assessment)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM quality_scores
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
