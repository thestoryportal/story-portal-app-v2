"""
L11 Integration Layer FastAPI Application

Provides cross-layer event routing and service coordination.
Subscribes to L01 events and routes them to appropriate layers.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .integration_layer import IntegrationLayer

logger = logging.getLogger(__name__)

# Global integration layer instance
integration_layer: Optional[IntegrationLayer] = None
redis_client: Optional[aioredis.Redis] = None
l01_subscription_task: Optional[asyncio.Task] = None


async def handle_l01_event(message: dict):
    """
    Handle raw Redis messages from L01 Data Layer.

    L01 publishes events in its own format (not L11 EventMessage format).
    This handler processes the raw message data.
    """
    # Redis pubsub sends messages as: {"type": "message", "data": "{...}"}
    # We need to parse the JSON data
    try:
        # If message is already parsed as dict, use it directly
        event = message if isinstance(message, dict) and "event_type" in message else message

        event_type = event.get("event_type", "unknown")
        aggregate_type = event.get("aggregate_type", "unknown")
        aggregate_id = event.get("aggregate_id", "unknown")

        logger.info(
            f"Received L01 event: {event_type} | "
            f"aggregate: {aggregate_type}/{aggregate_id}"
        )

        # Log payload for debugging
        payload = event.get("payload", {})
        logger.debug(f"Event payload: {payload}")

        # TODO: Route events to specific layers based on event type
        # For example:
        # - agent.* events -> L02 Runtime
        # - tool.* events -> L03 Tool Execution
        # - metrics.* events -> L06 Metrics
        # For now, just log the event

    except Exception as e:
        logger.error(f"Error handling L01 event: {e}", exc_info=True)


async def subscribe_to_l01_events():
    """
    Subscribe to L01 events directly from Redis.

    L01 publishes events in its own format to the "l01:events" channel.
    """
    global redis_client

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("l01:events")

    logger.info("Subscribed to l01:events Redis channel")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Parse JSON event data
                    event_data = json.loads(message["data"])
                    await handle_l01_event(event_data)
                except Exception as e:
                    logger.error(f"Error processing L01 event: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("L01 event subscription cancelled")
        await pubsub.unsubscribe("l01:events")
        await pubsub.aclose()
    except Exception as e:
        logger.error(f"Error in L01 subscription: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    """
    global integration_layer, redis_client, l01_subscription_task

    # Startup
    logger.info("Starting L11 Integration Layer...")

    try:
        # Create and start integration layer
        integration_layer = IntegrationLayer(
            redis_url="redis://localhost:6379/0",
            observability_output_file="l11_observability.log"
        )
        await integration_layer.start()

        # Create separate Redis client for L01 events
        redis_client = await aioredis.from_url(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis client connected for L01 events")

        # Start L01 event subscription task
        l01_subscription_task = asyncio.create_task(subscribe_to_l01_events())
        logger.info("L01 event subscription started")

        logger.info("L11 Integration Layer started successfully")

    except Exception as e:
        logger.error(f"Failed to start L11: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down L11 Integration Layer...")

    # Cancel L01 subscription
    if l01_subscription_task:
        l01_subscription_task.cancel()
        try:
            await l01_subscription_task
        except asyncio.CancelledError:
            pass

    # Close Redis client
    if redis_client:
        await redis_client.close()

    # Stop integration layer
    if integration_layer:
        await integration_layer.stop()

    logger.info("L11 Integration Layer shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="L11 Integration Layer",
    version="1.0.0",
    description="Cross-layer orchestration and event routing for AI Agent Platform",
    lifespan=lifespan
)


@app.get("/health/live")
async def liveness():
    """Liveness probe."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe."""
    global integration_layer

    if not integration_layer or not integration_layer.is_running():
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "reason": "Integration layer not running"
            }
        )

    # Get health status from integration layer
    health = await integration_layer.health_check()

    if health["status"] != "healthy":
        return JSONResponse(
            status_code=503,
            content=health
        )

    return health


@app.get("/health/detailed")
async def detailed_health():
    """Detailed health check."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "reason": "Integration layer not initialized"
            }
        )

    health = await integration_layer.health_check()

    # Add additional metrics
    health["layer_info"] = {
        "running": integration_layer.is_running(),
        "services": [
            "service_registry",
            "event_bus",
            "circuit_breaker",
            "request_orchestrator",
            "saga_orchestrator",
            "observability"
        ]
    }

    return health


@app.get("/services")
async def list_services():
    """List all registered services."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    # Get registered services
    services = await integration_layer.service_registry.list_services()

    return {
        "services": services,
        "total": len(services)
    }


@app.get("/metrics")
async def get_metrics():
    """Get integration layer metrics."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    return {
        "circuit_breaker": integration_layer.circuit_breaker.get_metrics(),
        "saga_orchestrator": integration_layer.saga_orchestrator.get_metrics(),
    }
