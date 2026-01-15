"""Health check endpoints."""

from fastapi import APIRouter, Depends
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness():
    """Liveness probe."""
    return {"status": "alive"}

@router.get("/ready")
async def readiness():
    """Readiness probe."""
    db_ok = await db.health_check()
    redis_ok = await redis_client.health_check()
    
    status = "ready" if (db_ok and redis_ok) else "not_ready"
    return {
        "status": status,
        "database": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down",
    }
