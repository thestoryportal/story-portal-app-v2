"""Model usage API router."""

import json
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/usage", status_code=201)
async def record_model_usage(usage_data: dict):
    """Record model usage."""
    query = """
        INSERT INTO model_usage (
            request_id, agent_id, agent_did, tenant_id, session_id,
            model_provider, model_name, model_id,
            input_tokens, output_tokens, cached_tokens, total_tokens,
            latency_ms, cached,
            cost_estimate, cost_input_cents, cost_output_cents, cost_cached_cents,
            finish_reason, error_message, response_status, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
            $15, $16, $17, $18, $19, $20, $21, $22
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert metadata dict to JSON string for JSONB
        metadata = usage_data.get("metadata", {})
        metadata_json = json.dumps(metadata) if metadata else "{}"

        row = await conn.fetchrow(
            query,
            usage_data["request_id"],
            usage_data.get("agent_id"),
            usage_data.get("agent_did"),
            usage_data.get("tenant_id"),
            usage_data.get("session_id"),
            usage_data["model_provider"],
            usage_data["model_name"],
            usage_data.get("model_id"),
            usage_data["input_tokens"],
            usage_data["output_tokens"],
            usage_data.get("cached_tokens", 0),
            usage_data.get("total_tokens"),
            usage_data.get("latency_ms"),
            usage_data.get("cached", False),
            usage_data.get("cost_estimate"),
            usage_data.get("cost_input_cents"),
            usage_data.get("cost_output_cents"),
            usage_data.get("cost_cached_cents"),
            usage_data.get("finish_reason"),
            usage_data.get("error_message"),
            usage_data.get("response_status", "success"),
            metadata_json
        )

        return dict(row)


@router.get("/usage")
async def list_model_usage(
    agent_id: Optional[UUID] = None,
    agent_did: Optional[str] = None,
    model_provider: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List model usage records with filters."""
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

    if model_provider:
        conditions.append(f"model_provider = ${param_count}")
        params.append(model_provider)
        param_count += 1

    if tenant_id:
        conditions.append(f"tenant_id = ${param_count}")
        params.append(tenant_id)
        param_count += 1

    if session_id:
        conditions.append(f"session_id = ${param_count}")
        params.append(session_id)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM model_usage
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


@router.get("/usage/{request_id}")
async def get_model_usage(request_id: str):
    """Get model usage by request ID."""
    query = "SELECT * FROM model_usage WHERE request_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, request_id)
        if not row:
            raise HTTPException(status_code=404, detail="Model usage not found")
        return dict(row)
