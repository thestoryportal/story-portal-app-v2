"""
Health Check Routes

Enhanced health endpoints with dependency status reporting.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> Dict[str, Any]:
    """
    Health check with dependency status.

    Returns overall service health and status of dependencies
    (PostgreSQL, Redis, Ollama).
    """
    dependencies = {}
    overall_healthy = True

    # Check tool registry (PostgreSQL)
    registry = getattr(request.app.state, "tool_registry", None)
    if registry:
        try:
            # Check if we can connect to the database
            if hasattr(registry, "db_pool") and registry.db_pool:
                async with registry.db_pool.connection() as conn:
                    await conn.execute("SELECT 1")
                dependencies["postgresql"] = "up"
            else:
                dependencies["postgresql"] = "not_initialized"
                overall_healthy = False
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            dependencies["postgresql"] = "down"
            overall_healthy = False
    else:
        dependencies["postgresql"] = "not_configured"
        overall_healthy = False

    # Check result cache (Redis)
    cache = getattr(request.app.state, "result_cache", None)
    if cache:
        try:
            if hasattr(cache, "redis") and cache.redis:
                await cache.redis.ping()
                dependencies["redis"] = "up"
            else:
                dependencies["redis"] = "not_initialized"
                overall_healthy = False
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            dependencies["redis"] = "down"
            overall_healthy = False
    else:
        dependencies["redis"] = "not_configured"

    status = "healthy" if overall_healthy else "degraded"

    return {
        "status": status,
        "service": "l03-tool-execution",
        "version": "2.0.0",
        "dependencies": dependencies,
    }


@router.get("/health/live")
async def liveness() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes.

    Returns alive if the service process is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    """
    Readiness probe for Kubernetes.

    Returns ready only if critical dependencies are available.
    """
    registry = getattr(request.app.state, "tool_registry", None)

    if not registry:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Tool registry not initialized"}
        )

    try:
        if hasattr(registry, "db_pool") and registry.db_pool:
            async with registry.db_pool.connection() as conn:
                await conn.execute("SELECT 1")
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "Database pool not initialized"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": f"Database not available: {str(e)}"}
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ready"}
    )
