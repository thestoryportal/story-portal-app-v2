"""
L11 Integration Layer FastAPI Application

Provides cross-layer event routing and service coordination.
Subscribes to L01 events and routes them to appropriate layers.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from .integration_layer import IntegrationLayer
from .services.event_router import EventRouter


# ============================================================================
# Logging Configuration
# ============================================================================

def configure_logging():
    """Configure logging based on LOG_FORMAT environment variable."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()

    if log_format == "json":
        try:
            import structlog

            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
            # Configure standard logging to use structlog
            logging.basicConfig(
                format="%(message)s",
                stream=sys.stdout,
                level=getattr(logging, log_level),
            )
            return structlog.get_logger(__name__)
        except ImportError:
            pass  # Fall back to standard logging

    # Standard logging format
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level),
    )
    return logging.getLogger(__name__)


logger = configure_logging()

# Global integration layer instance
integration_layer: Optional[IntegrationLayer] = None
event_router: Optional[EventRouter] = None
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

        # Route event to target layer
        if event_router:
            routed = await event_router.route_l01_event(event)
            if routed:
                logger.debug(f"Event routed successfully: {event_type}")
            else:
                logger.debug(f"Event not routed (no matching route): {event_type}")

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
    global integration_layer, event_router, redis_client, l01_subscription_task

    # Startup
    logger.info("Starting L11 Integration Layer...")

    try:
        # Create and start integration layer
        integration_layer = IntegrationLayer(
            redis_url="redis://localhost:6379/0",
            observability_output_file="l11_observability.log"
        )
        await integration_layer.start()

        # Create and start event router
        event_router = EventRouter()
        await event_router.start()
        logger.info("Event router started")

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

    # Stop event router
    if event_router:
        await event_router.stop()

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


@app.get("/")
async def root():
    """
    Root endpoint with service metadata.

    Returns service info, available endpoints, and version.
    """
    return {
        "service": "L11 Integration Layer",
        "version": "1.0.0",
        "description": "Cross-layer orchestration and event routing",
        "layer": "L11",
        "port": 8011,
        "endpoints": {
            "health": {
                "/health/live": "Liveness probe",
                "/health/ready": "Readiness probe",
                "/health/detailed": "Detailed health check",
            },
            "services": {
                "/services": "List registered services",
            },
            "circuits": {
                "/circuits": "List circuit breaker states",
                "/circuits/{name}/reset": "Reset a circuit breaker",
            },
            "sagas": {
                "/sagas": "List saga executions",
                "/sagas/{execution_id}": "Get saga execution details",
            },
            "events": {
                "/events": "Event routing statistics",
            },
            "traces": {
                "/traces/{trace_id}": "Get distributed trace spans",
            },
            "metrics": {
                "/metrics": "Integration layer metrics",
            },
        },
        "status": "running" if integration_layer and integration_layer.is_running() else "starting",
    }


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
    services = await integration_layer.service_registry.get_all_services()

    return {
        "services": services,
        "total": len(services)
    }


@app.get("/metrics")
async def get_metrics():
    """Get integration layer metrics."""
    global integration_layer, event_router

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    metrics = {
        "circuit_breaker": integration_layer.circuit_breaker.get_metrics(),
        "saga_orchestrator": integration_layer.saga_orchestrator.get_metrics(),
    }

    if event_router:
        metrics["event_router"] = event_router.get_metrics()

    return metrics


@app.get("/events")
async def get_event_stats():
    """Get event routing statistics."""
    global event_router

    if not event_router:
        return JSONResponse(
            status_code=503,
            content={"error": "Event router not initialized"}
        )

    metrics = event_router.get_metrics()
    health = await event_router.get_health()

    return {
        "routing": {
            "events_received": metrics["events_received"],
            "events_routed": metrics["events_routed"],
            "success_rate_percent": health["success_rate_percent"],
        },
        "by_aggregate_type": metrics["events_by_type"],
        "errors_by_layer": metrics["route_errors"],
        "dlq": {
            "sizes": metrics["dlq_sizes"],
            "total": sum(metrics["dlq_sizes"].values()),
        },
        "routing_table": metrics["routing_table"],
        "health": health,
    }


@app.post("/events/dlq/retry")
async def retry_dlq(route: Optional[str] = None):
    """Retry events in dead letter queue."""
    global event_router

    if not event_router:
        return JSONResponse(
            status_code=503,
            content={"error": "Event router not initialized"}
        )

    results = await event_router.retry_dlq(route)
    return {"results": results}


@app.get("/events/dlq")
async def get_dlq_events(route: Optional[str] = None, limit: int = 100):
    """Get events from dead letter queue."""
    global event_router

    if not event_router:
        return JSONResponse(
            status_code=503,
            content={"error": "Event router not initialized"}
        )

    events = await event_router.get_dlq_events(route, limit)
    return {"events": events, "total": len(events)}


# ============================================================================
# Circuit Breaker Endpoints
# ============================================================================


@app.get("/circuits")
async def list_circuits():
    """List all circuit breaker states."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    metrics = integration_layer.circuit_breaker.get_metrics()
    return {
        "summary": {
            "total": metrics["total_circuits"],
            "open": metrics["open"],
            "half_open": metrics["half_open"],
            "closed": metrics["closed"],
        },
        "circuits": metrics["circuits"],
    }


@app.post("/circuits/{name}/reset")
async def reset_circuit(name: str):
    """Manually reset a circuit breaker to closed state."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    # Check if circuit exists
    circuit = await integration_layer.circuit_breaker.get_state(name)
    if not circuit:
        return JSONResponse(
            status_code=404,
            content={"error": f"Circuit breaker '{name}' not found"}
        )

    await integration_layer.circuit_breaker.reset_circuit(name)
    return {
        "message": f"Circuit breaker '{name}' reset to closed state",
        "circuit": name,
    }


# ============================================================================
# Saga Endpoints
# ============================================================================


@app.get("/sagas")
async def list_sagas(
    status: Optional[str] = None,
    saga_name: Optional[str] = None,
    limit: int = 100,
):
    """List saga executions with optional filters."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    # Convert status string to enum if provided
    status_filter = None
    if status:
        from .models import SagaStatus
        try:
            status_filter = SagaStatus(status)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Invalid status: {status}",
                    "valid_values": [s.value for s in SagaStatus],
                }
            )

    executions = await integration_layer.saga_orchestrator.list_executions(
        status_filter=status_filter,
        saga_name_filter=saga_name,
        limit=limit,
    )

    metrics = integration_layer.saga_orchestrator.get_metrics()

    return {
        "summary": {
            "total": metrics["total_executions"],
            "running": metrics["running"],
            "completed": metrics["completed"],
            "failed": metrics["failed"],
            "timeout": metrics["timeout"],
            "compensating": metrics["compensating"],
        },
        "executions": executions,
    }


@app.get("/sagas/{execution_id}")
async def get_saga(execution_id: str):
    """Get saga execution details with trace."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    trace = await integration_layer.saga_orchestrator.get_execution_trace(execution_id)
    if not trace:
        return JSONResponse(
            status_code=404,
            content={"error": f"Saga execution '{execution_id}' not found"}
        )

    return trace


# ============================================================================
# Trace Endpoints
# ============================================================================


@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get distributed trace spans for a trace ID."""
    global integration_layer

    if not integration_layer:
        return JSONResponse(
            status_code=503,
            content={"error": "Integration layer not initialized"}
        )

    # Get spans from observability collector
    spans = await integration_layer.observability.get_trace(trace_id)

    if not spans:
        return JSONResponse(
            status_code=404,
            content={"error": f"Trace '{trace_id}' not found"}
        )

    # Format spans for response
    formatted_spans = []
    for span in spans:
        formatted_spans.append({
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "span_name": span.span_name,
            "span_kind": span.span_kind.value if hasattr(span.span_kind, "value") else str(span.span_kind),
            "service_name": span.service_name,
            "start_time": span.start_time.isoformat() if span.start_time else None,
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "duration_ms": span.duration_ms,
            "status": span.status.value if hasattr(span.status, "value") else str(span.status),
            "attributes": span.attributes,
        })

    return {
        "trace_id": trace_id,
        "span_count": len(formatted_spans),
        "spans": formatted_spans,
    }


# ============================================================================
# Prometheus Metrics Endpoint
# ============================================================================


def format_prometheus_metrics() -> str:
    """Format metrics in Prometheus text format."""
    lines = []

    # Helper to add metric
    def add_metric(name: str, value: float, help_text: str, metric_type: str = "gauge", labels: dict = None):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {metric_type}")
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
            lines.append(f"{name}{{{label_str}}} {value}")
        else:
            lines.append(f"{name} {value}")

    # Service health
    if integration_layer and integration_layer.is_running():
        add_metric("l11_up", 1, "L11 Integration Layer is up", "gauge")
    else:
        add_metric("l11_up", 0, "L11 Integration Layer is up", "gauge")

    # Event router metrics
    if event_router:
        metrics = event_router.get_metrics()
        add_metric(
            "l11_events_received_total",
            metrics["events_received"],
            "Total events received from L01",
            "counter",
        )
        add_metric(
            "l11_events_routed_total",
            metrics["events_routed"],
            "Total events successfully routed",
            "counter",
        )

        # Events by type
        for agg_type, count in metrics["events_by_type"].items():
            add_metric(
                "l11_events_by_type_total",
                count,
                "Events received by aggregate type",
                "counter",
                {"aggregate_type": agg_type},
            )

        # Route errors
        for layer, count in metrics["route_errors"].items():
            add_metric(
                "l11_route_errors_total",
                count,
                "Event routing errors by target layer",
                "counter",
                {"layer": layer},
            )

        # DLQ sizes
        for route, size in metrics["dlq_sizes"].items():
            add_metric(
                "l11_dlq_size",
                size,
                "Dead letter queue size by route",
                "gauge",
                {"route": route},
            )

    # Circuit breaker metrics
    if integration_layer:
        cb_metrics = integration_layer.circuit_breaker.get_metrics()
        add_metric(
            "l11_circuits_total",
            cb_metrics["total_circuits"],
            "Total circuit breakers",
            "gauge",
        )
        add_metric(
            "l11_circuits_open",
            cb_metrics["open"],
            "Open circuit breakers",
            "gauge",
        )
        add_metric(
            "l11_circuits_half_open",
            cb_metrics["half_open"],
            "Half-open circuit breakers",
            "gauge",
        )
        add_metric(
            "l11_circuits_closed",
            cb_metrics["closed"],
            "Closed circuit breakers",
            "gauge",
        )

        # Per-circuit metrics
        for circuit_name, circuit_data in cb_metrics["circuits"].items():
            add_metric(
                "l11_circuit_failure_count",
                circuit_data["failure_count"],
                "Circuit breaker failure count",
                "gauge",
                {"circuit": circuit_name},
            )
            add_metric(
                "l11_circuit_error_rate",
                circuit_data["error_rate"],
                "Circuit breaker error rate",
                "gauge",
                {"circuit": circuit_name},
            )

        # Saga metrics
        saga_metrics = integration_layer.saga_orchestrator.get_metrics()
        add_metric(
            "l11_sagas_total",
            saga_metrics["total_executions"],
            "Total saga executions",
            "counter",
        )
        add_metric(
            "l11_sagas_running",
            saga_metrics["running"],
            "Currently running sagas",
            "gauge",
        )
        add_metric(
            "l11_sagas_completed",
            saga_metrics["completed"],
            "Completed sagas",
            "counter",
        )
        add_metric(
            "l11_sagas_failed",
            saga_metrics["failed"],
            "Failed sagas",
            "counter",
        )
        add_metric(
            "l11_sagas_timeout",
            saga_metrics["timeout"],
            "Timed out sagas",
            "counter",
        )

    return "\n".join(lines)


@app.get("/metrics/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Get metrics in Prometheus text format."""
    return format_prometheus_metrics()
