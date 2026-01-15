"""Metrics API router for L06 Evaluation integration."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/", status_code=201)
async def create_metric(metric_data: dict):
    """Create a new metric point."""
    query = """
        INSERT INTO metrics (
            metric_name, metric_type, value, timestamp,
            labels, agent_id, tenant_id
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert timestamp string to datetime if needed
        timestamp = metric_data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Convert labels dict to JSON string for JSONB
        labels_json = json.dumps(metric_data.get("labels", {}))

        row = await conn.fetchrow(
            query,
            metric_data["metric_name"],
            metric_data.get("metric_type", "gauge"),
            metric_data["value"],
            timestamp,
            labels_json,
            metric_data.get("agent_id"),
            metric_data.get("tenant_id")
        )

        return dict(row)


@router.get("/")
async def query_metrics(
    metric_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    limit: int = Query(1000, le=10000)
):
    """Query metrics with time range and filters."""
    conditions = [f"metric_name = $1"]
    params = [metric_name]
    param_count = 2

    if start_time:
        conditions.append(f"timestamp >= ${param_count}")
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        params.append(start_dt)
        param_count += 1

    if end_time:
        conditions.append(f"timestamp <= ${param_count}")
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        params.append(end_dt)
        param_count += 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if tenant_id:
        conditions.append(f"tenant_id = ${param_count}")
        params.append(tenant_id)
        param_count += 1

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT * FROM metrics
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count}
    """
    params.append(limit)

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


@router.get("/aggregates/{metric_name}")
async def get_metric_aggregates(
    metric_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    agent_id: Optional[UUID] = None
):
    """Get aggregated statistics for a metric."""
    conditions = [f"metric_name = $1"]
    params = [metric_name]
    param_count = 2

    if start_time:
        conditions.append(f"timestamp >= ${param_count}")
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        params.append(start_dt)
        param_count += 1

    if end_time:
        conditions.append(f"timestamp <= ${param_count}")
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        params.append(end_dt)
        param_count += 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            COUNT(*) as count,
            AVG(value) as avg,
            MIN(value) as min,
            MAX(value) as max,
            STDDEV(value) as stddev,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as p50,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) as p99
        FROM metrics
        WHERE {where_clause}
    """

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row or row["count"] == 0:
            raise HTTPException(status_code=404, detail="No metrics found")
        return dict(row)
