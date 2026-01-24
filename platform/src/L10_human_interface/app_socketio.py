"""
L10 Human Interface with Socket.IO Support

Provides real-time event streaming from L01 via Redis to connected UI clients.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from shared.clients import L01Client
from .config import get_settings
from .services.l01_bridge import L10Bridge

logger = logging.getLogger(__name__)
settings = get_settings()

# Global state
redis_client: Optional[aioredis.Redis] = None
l01_client: Optional[L01Client] = None
l10_bridge: Optional[L10Bridge] = None
event_subscription_task: Optional[asyncio.Task] = None

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # In production, specify actual origins
    logger=True,
    engineio_logger=False
)


async def subscribe_to_redis_events():
    """
    Subscribe to L01 events from Redis and broadcast to Socket.IO clients.
    """
    global redis_client

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("l01:events")

    logger.info("Subscribed to l01:events Redis channel")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])

                    # Broadcast to all connected Socket.IO clients
                    await sio.emit('event', event_data)

                    # Also emit specific event types for targeted listeners
                    event_type = event_data.get('event_type', '').replace('.', '_')
                    if event_type:
                        await sio.emit(event_type, event_data)

                    logger.debug(f"Broadcasted event: {event_data.get('event_type')}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Redis message: {e}")
                except Exception as e:
                    logger.error(f"Error broadcasting event: {e}")

    except asyncio.CancelledError:
        logger.info("Redis subscription cancelled")
        await pubsub.unsubscribe("l01:events")
        await pubsub.close()
    except Exception as e:
        logger.error(f"Error in Redis subscription: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    """
    global redis_client, l01_client, l10_bridge, event_subscription_task

    # Startup
    logger.info("Starting L10 Human Interface with Socket.IO...")

    # Initialize Redis
    redis_client = await aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
        encoding="utf-8",
        decode_responses=True
    )
    logger.info("Redis connected")

    # Initialize L01 Client with API key from environment
    import os
    l01_api_key = os.getenv("L01_API_KEY", "dev_key_local_ONLY")
    if l01_api_key == "dev_key_local_ONLY":
        logger.warning("Using default L01_API_KEY. Set environment variable for production.")

    l01_client = L01Client(
        base_url=f"http://{settings.l01_host}:{settings.l01_port}",
        api_key=l01_api_key
    )
    logger.info("L01 client initialized")

    # Initialize L10 Bridge with API key
    l10_bridge = L10Bridge(
        l01_base_url=f"http://{settings.l01_host}:{settings.l01_port}",
        api_key=l01_api_key
    )
    await l10_bridge.initialize()
    logger.info("L10 bridge initialized")

    # Start Redis event subscription
    event_subscription_task = asyncio.create_task(subscribe_to_redis_events())
    logger.info("Redis event subscription started")

    logger.info("L10 Human Interface started successfully")
    logger.info(f"Socket.IO server ready at ws://{settings.host}:{settings.port}/socket.io/")

    yield

    # Shutdown
    logger.info("Shutting down L10 Human Interface...")

    # Cancel Redis subscription
    if event_subscription_task:
        event_subscription_task.cancel()
        try:
            await event_subscription_task
        except asyncio.CancelledError:
            pass

    # Close connections
    if l10_bridge:
        await l10_bridge.cleanup()

    if l01_client:
        await l01_client.close()

    if redis_client:
        await redis_client.close()

    logger.info("L10 Human Interface shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="L10 Human Interface",
    version="2.0.0",
    description="Dashboard and control interface with real-time Socket.IO events",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory for React frontend
STATIC_DIR = Path("/app/static")

# Mount static assets if directory exists (for production)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

# Mount Socket.IO app
socket_app = socketio.ASGIApp(sio, app)


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle Socket.IO client connection."""
    logger.info(f"Socket.IO client connected: {sid}")

    # Record connection in L01
    if l10_bridge:
        try:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="socketio",
                action="connect",
                client_ip=environ.get('REMOTE_ADDR', 'unknown'),
                result="success",
            )
        except Exception as e:
            logger.warning(f"Failed to record connection: {e}")

    # Send connection confirmation
    await sio.emit('connection.established', {
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Connected to L10 event stream',
        'sid': sid
    }, room=sid)


@sio.event
async def disconnect(sid):
    """Handle Socket.IO client disconnection."""
    logger.info(f"Socket.IO client disconnected: {sid}")

    # Record disconnection in L01
    if l10_bridge:
        try:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="socketio",
                action="disconnect",
                result="success",
            )
        except Exception as e:
            logger.warning(f"Failed to record disconnection: {e}")


@sio.event
async def subscribe(sid, data):
    """Handle subscription to specific event topics."""
    topics = data.get('topics', [])
    logger.info(f"Client {sid} subscribing to topics: {topics}")

    # Join Socket.IO rooms for each topic
    for topic in topics:
        await sio.enter_room(sid, topic)

    await sio.emit('subscribed', {'topics': topics}, room=sid)


@sio.event
async def unsubscribe(sid, data):
    """Handle unsubscription from event topics."""
    topics = data.get('topics', [])
    logger.info(f"Client {sid} unsubscribing from topics: {topics}")

    # Leave Socket.IO rooms
    for topic in topics:
        await sio.leave_room(sid, topic)

    await sio.emit('unsubscribed', {'topics': topics}, room=sid)


@sio.event
async def ping(sid, data):
    """Handle ping/pong for connection health check."""
    await sio.emit('pong', {'timestamp': datetime.utcnow().isoformat()}, room=sid)


# REST API endpoints
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the React frontend or fallback dashboard."""
    # Try to serve React frontend if available
    react_index = STATIC_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    # Fallback to embedded dashboard
    return DASHBOARD_HTML


@app.get("/health/live")
async def liveness():
    """Liveness probe."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe with dependency checks."""
    dependencies = {}

    # Check Redis
    try:
        await redis_client.ping()
        dependencies["redis"] = "healthy"
    except Exception as e:
        dependencies["redis"] = f"unhealthy: {e}"
        return {"status": "unhealthy", "dependencies": dependencies}, 503

    # Check L01
    try:
        await l01_client.list_agents(limit=1)
        dependencies["l01"] = "healthy"
    except Exception as e:
        dependencies["l01"] = f"unhealthy: {e}"
        return {"status": "unhealthy", "dependencies": dependencies}, 503

    return {"status": "healthy", "dependencies": dependencies}


@app.get("/api/agents")
async def list_agents(status: Optional[str] = None, limit: int = 100):
    """List all agents."""
    try:
        agents = await l01_client.list_agents(status=status, limit=limit)

        # Record user interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="list_agents",
                target_type="agent",
                parameters={"status": status, "limit": limit},
                result="success",
            )

        return {"agents": agents, "total": len(agents)}
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")

        # Record failed interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="list_agents",
                target_type="agent",
                result="failure",
                error_message=str(e),
            )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: UUID):
    """Get agent by ID."""
    try:
        agent = await l01_client.get_agent(agent_id)

        # Record user interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="get_agent",
                target_type="agent",
                target_id=str(agent_id),
                result="success",
            )

        return agent
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")

        # Record failed interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="get_agent",
                target_type="agent",
                target_id=str(agent_id),
                result="failure",
                error_message=str(e),
            )

        raise HTTPException(status_code=404, detail="Agent not found")


@app.get("/api/goals")
async def list_goals(agent_id: Optional[UUID] = None, limit: int = 100):
    """List goals."""
    try:
        goals = await l01_client.list_goals(agent_id=agent_id, limit=limit)

        # Record user interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="list_goals",
                target_type="goal",
                parameters={"agent_id": str(agent_id) if agent_id else None, "limit": limit},
                result="success",
            )

        return {"goals": goals, "total": len(goals)}
    except Exception as e:
        logger.error(f"Failed to list goals: {e}")

        # Record failed interaction in L01
        if l10_bridge:
            await l10_bridge.record_user_interaction(
                timestamp=datetime.utcnow(),
                interaction_type="api_call",
                action="list_goals",
                target_type="goal",
                result="failure",
                error_message=str(e),
            )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/services/health")
async def get_services_health():
    """
    Aggregate real health data from all services.
    Returns actual status and latency for each service.
    """
    import time
    import httpx

    services = [
        {"name": "L01 Data Layer", "url": "http://l01-data-layer:8001", "port": 8001},
        {"name": "L02 Runtime", "url": "http://l02-runtime:8002", "port": 8002},
        {"name": "L03 Tool Execution", "url": "http://l03-tool-execution:8003", "port": 8003},
        {"name": "L04 Model Gateway", "url": "http://l04-model-gateway:8004", "port": 8004},
        {"name": "L05 Planning", "url": "http://l05-planning:8005", "port": 8005},
        {"name": "L06 Evaluation", "url": "http://l06-evaluation:8006", "port": 8006},
        {"name": "L07 Learning", "url": "http://l07-learning:8007", "port": 8007},
        {"name": "L09 API Gateway", "url": "http://l09-api-gateway:8009", "port": 8009},
        {"name": "L10 Human Interface", "url": "http://localhost:8010", "port": 8010},
        {"name": "L11 Integration", "url": "http://l11-integration:8011", "port": 8011},
        {"name": "L12 Service Hub", "url": "http://l12-service-hub:8012", "port": 8012},
    ]

    async def check_service_health(service):
        """Check health of a single service."""
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service['url']}/health/live")
                latency = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    return {
                        "name": service["name"],
                        "status": "healthy",
                        "latency": latency
                    }
                else:
                    return {
                        "name": service["name"],
                        "status": "unhealthy",
                        "latency": latency
                    }
        except Exception as e:
            logger.debug(f"Failed to check health for {service['name']}: {e}")
            return {
                "name": service["name"],
                "status": "unhealthy",
                "latency": 0
            }

    # Check all services in parallel
    results = await asyncio.gather(*[check_service_health(s) for s in services])

    return {"services": results, "timestamp": datetime.utcnow().isoformat()}


@app.get("/dashboard/metrics")
async def get_dashboard_metrics():
    """
    Get aggregated system metrics for the dashboard.
    Returns agent counts, resource usage, and request statistics.
    """
    import psutil

    try:
        # Get agent statistics from L01
        agent_stats = {
            "total": 0,
            "active": 0,
            "idle": 0,
            "failed": 0
        }

        if l01_client:
            try:
                agents = await l01_client.list_agents()
                agent_stats["total"] = len(agents)
                agent_stats["active"] = len([a for a in agents if a.get("status") in ["active", "busy"]])
                agent_stats["idle"] = len([a for a in agents if a.get("status") == "idle"])
                agent_stats["failed"] = len([a for a in agents if a.get("status") in ["error", "terminated"]])
            except Exception as e:
                logger.warning(f"Failed to get agent stats: {e}")

        # Get system resource usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        total_memory_gb = memory.total / (1024 ** 3)

        # Get request statistics (placeholder - would come from L09 API Gateway)
        request_stats = {
            "total": 0,
            "success_rate": 0.0,
            "avg_response_time_ms": 0.0
        }

        return {
            "agents": agent_stats,
            "resources": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "total_memory": total_memory_gb
            },
            "requests": request_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/overview")
async def get_dashboard_overview():
    """
    Get dashboard overview with key system indicators.
    """
    try:
        metrics = await get_dashboard_metrics()
        services_health = await get_services_health()

        healthy_services = len([s for s in services_health["services"] if s["status"] == "healthy"])
        total_services = len(services_health["services"])

        return {
            "agents": metrics["agents"],
            "services": {
                "healthy": healthy_services,
                "total": total_services
            },
            "system_health": "healthy" if healthy_services >= total_services * 0.8 else "degraded",
            "resources": metrics["resources"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Catch-all route for SPA client-side routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React frontend for client-side routing."""
    # Skip API routes and health endpoints
    if full_path.startswith(("api/", "health", "dashboard/", "socket.io")):
        raise HTTPException(status_code=404, detail="Not found")

    # Try to serve static file first
    static_file = STATIC_DIR / full_path
    if static_file.exists() and static_file.is_file():
        return FileResponse(static_file)

    # Serve index.html for SPA routing
    react_index = STATIC_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index)

    # Fallback to embedded dashboard
    return HTMLResponse(DASHBOARD_HTML)


# Dashboard HTML with Socket.IO client
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Platform Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { color: white; text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .status-badge {
            display: inline-block; padding: 5px 15px; border-radius: 20px;
            background: #10b981; color: white; font-size: 0.9em; font-weight: 600;
        }
        .status-connecting { background: #f59e0b; }
        .status-error { background: #ef4444; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .card h2 { font-size: 1.3em; margin-bottom: 20px; color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }
        .event-log {
            max-height: 400px; overflow-y: auto; background: #1f2937; border-radius: 8px;
            padding: 15px; font-family: 'Courier New', monospace; font-size: 0.85em;
        }
        .event-item {
            padding: 8px; margin-bottom: 8px; background: #374151; border-radius: 4px;
            color: #f3f4f6; border-left: 3px solid #10b981;
        }
        .event-type { color: #10b981; font-weight: 600; }
        .event-time { color: #9ca3af; font-size: 0.9em; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .stat-box { padding: 15px; background: #f9fafb; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 2em; font-weight: 700; color: #3b82f6; margin-bottom: 5px; }
        .stat-label { color: #6b7280; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Agent Platform</h1>
            <p>Real-time Dashboard with Socket.IO</p>
            <div class="status-badge" id="connectionStatus">Connecting...</div>
        </div>
        <div class="grid">
            <div class="card">
                <h2>📊 System Overview</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value" id="totalAgents">-</div>
                        <div class="stat-label">Total Agents</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="activeAgents">-</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="totalGoals">-</div>
                        <div class="stat-label">Total Goals</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="totalEvents">0</div>
                        <div class="stat-label">Events Received</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card">
            <h2>📡 Real-time Event Stream</h2>
            <div class="event-log" id="eventLog">
                <div style="color: #9ca3af;">Waiting for events...</div>
            </div>
        </div>
    </div>
    <script>
        let socket;
        let eventCount = 0;

        function connectSocket() {
            socket = io();

            socket.on('connect', () => {
                console.log('Socket.IO connected');
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').className = 'status-badge';
            });

            socket.on('disconnect', () => {
                console.log('Socket.IO disconnected');
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').className = 'status-badge status-error';
            });

            socket.on('connection.established', (data) => {
                console.log('Connection established:', data);
                addEventToLog({event_type: 'connection.established', payload: data, timestamp: data.timestamp});
            });

            socket.on('event', (data) => {
                console.log('Event received:', data);
                addEventToLog(data);
                eventCount++;
                document.getElementById('totalEvents').textContent = eventCount;

                if (data.event_type?.startsWith('agent.')) {
                    loadAgents();
                }
            });

            socket.on('connect_error', (error) => {
                console.error('Socket.IO connection error:', error);
                document.getElementById('connectionStatus').textContent = 'Connection Error';
                document.getElementById('connectionStatus').className = 'status-badge status-error';
            });
        }

        function addEventToLog(event) {
            const eventLog = document.getElementById('eventLog');
            const eventItem = document.createElement('div');
            eventItem.className = 'event-item';
            const eventType = event.event_type || 'unknown';
            const timestamp = event.timestamp || new Date().toISOString();
            eventItem.innerHTML = `
                <div><span class="event-type">${eventType}</span></div>
                <div class="event-time">${new Date(timestamp).toLocaleTimeString()}</div>
                <div style="color: #d1d5db; margin-top: 5px; font-size: 0.9em;">${JSON.stringify(event.payload || event).substring(0, 200)}</div>
            `;
            eventLog.insertBefore(eventItem, eventLog.firstChild);
            while (eventLog.children.length > 50) {
                eventLog.removeChild(eventLog.lastChild);
            }
        }

        async function loadAgents() {
            try {
                const response = await fetch('/api/agents');
                const data = await response.json();
                document.getElementById('totalAgents').textContent = data.total;
                document.getElementById('activeAgents').textContent =
                    data.agents.filter(a => a.status === 'active' || a.status === 'created').length;
            } catch (error) {
                console.error('Failed to load agents:', error);
            }
        }

        async function loadGoals() {
            try {
                const response = await fetch('/api/goals');
                const data = await response.json();
                document.getElementById('totalGoals').textContent = data.total;
            } catch (error) {
                console.error('Failed to load goals:', error);
            }
        }

        connectSocket();
        loadAgents();
        loadGoals();
        setInterval(() => { loadAgents(); loadGoals(); }, 30000);
    </script>
</body>
</html>
"""
