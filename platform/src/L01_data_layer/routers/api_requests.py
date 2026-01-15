"""API requests router for L09 API Gateway integration."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/api-requests", tags=["api-gateway"])


class APIRequestCreate(BaseModel):
    """API request creation model."""
    request_id: str
    trace_id: str
    span_id: str
    timestamp: str
    method: str
    path: str
    status_code: int
    latency_ms: float
    consumer_id: Optional[str] = None
    tenant_id: Optional[str] = None
    authenticated: bool = False
    auth_method: Optional[str] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    rate_limit_tier: Optional[str] = None
    idempotency_key: Optional[str] = None
    idempotent_cache_hit: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    headers: Optional[dict] = None
    query_params: Optional[dict] = None
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_api_request(request_data: APIRequestCreate):
    """Create a new API request record."""
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(request_data.timestamp.replace('Z', '+00:00'))

        # Serialize JSONB fields
        headers_json = json.dumps(request_data.headers or {})
        query_params_json = json.dumps(request_data.query_params or {})
        metadata_json = json.dumps(request_data.metadata or {})

        # Insert record
        query = """
            INSERT INTO api_requests (
                request_id, trace_id, span_id, timestamp, method, path,
                consumer_id, tenant_id, authenticated, auth_method,
                status_code, latency_ms, request_size_bytes, response_size_bytes,
                rate_limit_tier, idempotency_key, idempotent_cache_hit,
                error_code, error_message, client_ip, user_agent,
                headers, query_params, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24
            ) RETURNING id, request_id, trace_id, span_id, timestamp, method, path,
                        status_code, latency_ms, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                request_data.request_id,
                request_data.trace_id,
                request_data.span_id,
                timestamp,
                request_data.method,
                request_data.path,
                request_data.consumer_id,
                request_data.tenant_id,
                request_data.authenticated,
                request_data.auth_method,
                request_data.status_code,
                request_data.latency_ms,
                request_data.request_size_bytes,
                request_data.response_size_bytes,
                request_data.rate_limit_tier,
                request_data.idempotency_key,
                request_data.idempotent_cache_hit,
                request_data.error_code,
                request_data.error_message,
                request_data.client_ip,
                request_data.user_agent,
                headers_json,
                query_params_json,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API request: {str(e)}")


@router.get("/{request_id}")
async def get_api_request(request_id: str):
    """Get API request by request_id."""
    try:
        query = """
            SELECT * FROM api_requests WHERE request_id = $1
        """
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, request_id)

            if not record:
                raise HTTPException(status_code=404, detail="API request not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_api_requests(
    consumer_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    path_prefix: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List API requests with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if consumer_id:
            conditions.append(f"consumer_id = ${param_index}")
            params.append(consumer_id)
            param_index += 1

        if tenant_id:
            conditions.append(f"tenant_id = ${param_index}")
            params.append(tenant_id)
            param_index += 1

        if method:
            conditions.append(f"method = ${param_index}")
            params.append(method)
            param_index += 1

        if status_code:
            conditions.append(f"status_code = ${param_index}")
            params.append(status_code)
            param_index += 1

        if path_prefix:
            conditions.append(f"path LIKE ${param_index}")
            params.append(f"{path_prefix}%")
            param_index += 1

        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            conditions.append(f"timestamp >= ${param_index}")
            params.append(start_dt)
            param_index += 1

        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            conditions.append(f"timestamp <= ${param_index}")
            params.append(end_dt)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM api_requests
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([limit, offset])

        async with db.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(record) for record in records]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
