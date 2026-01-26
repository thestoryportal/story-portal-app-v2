"""
L10 Human Interface FastAPI Application

Provides dashboard interface, WebSocket updates, and control operations.
Integrates with L01 Data Layer for agent state and subscribes to Redis events.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set, Optional
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from shared.clients import L01Client
from .config import get_settings
from .services.l01_bridge import L10Bridge

logger = logging.getLogger(__name__)
settings = get_settings()

# Global state
redis_client: Optional[aioredis.Redis] = None
l01_client: Optional[L01Client] = None
l10_bridge: Optional[L10Bridge] = None
active_websockets: Set[WebSocket] = set()
event_subscription_task: Optional[asyncio.Task] = None


async def subscribe_to_redis_events():
    """
    Subscribe to L01 events from Redis and broadcast to WebSocket clients.
    """
    global redis_client, active_websockets

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("l01:events")

    logger.info("Subscribed to l01:events Redis channel")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                event_data = json.loads(message["data"])

                # Broadcast to all connected WebSocket clients
                disconnected = set()
                for websocket in active_websockets:
                    try:
                        await websocket.send_json(event_data)
                    except Exception as e:
                        logger.warning(f"Failed to send to WebSocket: {e}")
                        disconnected.add(websocket)

                # Remove disconnected clients
                active_websockets.difference_update(disconnected)
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
    logger.info("Starting L10 Human Interface...")

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
    version="1.0.0",
    description="Dashboard and control interface for AI Agent Platform",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML page."""
    return DASHBOARD_HTML


@app.get("/health/live")
async def liveness():
    """Liveness probe."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe."""
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
        # Simple health check via L01 client
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.

    Clients connect here to receive real-time events from L01 via Redis.
    """
    await websocket.accept()
    active_websockets.add(websocket)

    logger.info(f"WebSocket client connected. Total clients: {len(active_websockets)}")

    # Record WebSocket connection in L01
    if l10_bridge:
        await l10_bridge.record_user_interaction(
            timestamp=datetime.utcnow(),
            interaction_type="websocket",
            action="connect",
            client_ip=websocket.client.host if websocket.client else "unknown",
            result="success",
        )

    try:
        # Send initial connection success message
        await websocket.send_json({
            "event_type": "connection.established",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to L10 event stream"
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back for now (could be used for heartbeat)
                await websocket.send_json({
                    "event_type": "echo",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        active_websockets.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(active_websockets)}")


# Dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Platform Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            color: white;
            text-align: center;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: #10b981;
            color: white;
            font-size: 0.9em;
            font-weight: 600;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .card h2 {
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }

        .agent-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .agent-item {
            padding: 15px;
            margin-bottom: 10px;
            background: #f9fafb;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }

        .agent-name {
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }

        .agent-did {
            font-size: 0.85em;
            color: #6b7280;
            font-family: monospace;
        }

        .agent-status {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            margin-top: 5px;
            background: #dbeafe;
            color: #1e40af;
            font-weight: 600;
        }

        .event-log {
            max-height: 400px;
            overflow-y: auto;
            background: #1f2937;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }

        .event-item {
            padding: 8px;
            margin-bottom: 8px;
            background: #374151;
            border-radius: 4px;
            color: #f3f4f6;
            border-left: 3px solid #10b981;
        }

        .event-type {
            color: #10b981;
            font-weight: 600;
        }

        .event-time {
            color: #9ca3af;
            font-size: 0.9em;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat-box {
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: 700;
            color: #3b82f6;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #6b7280;
            font-size: 0.9em;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6b7280;
        }

        .error {
            background: #fee2e2;
            color: #991b1b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Agent Platform</h1>
            <p>Real-time Dashboard</p>
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

            <div class="card">
                <h2>🤖 Agents</h2>
                <div class="agent-list" id="agentList">
                    <div class="loading">Loading agents...</div>
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
        let ws;
        let eventCount = 0;

        // Connect to WebSocket
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').style.background = '#10b981';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('Event received:', data);

                // Update event log
                addEventToLog(data);

                // Update stats
                eventCount++;
                document.getElementById('totalEvents').textContent = eventCount;

                // If agent event, refresh agent list
                if (data.aggregate_type === 'agent' || data.event_type?.startsWith('agent.')) {
                    loadAgents();
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                document.getElementById('connectionStatus').textContent = 'Error';
                document.getElementById('connectionStatus').style.background = '#ef4444';
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').style.background = '#f59e0b';

                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }

        // Add event to log
        function addEventToLog(event) {
            const eventLog = document.getElementById('eventLog');
            const eventItem = document.createElement('div');
            eventItem.className = 'event-item';

            const eventType = event.event_type || event.aggregate_type || 'unknown';
            const timestamp = event.timestamp || new Date().toISOString();

            eventItem.innerHTML = `
                <div><span class="event-type">${eventType}</span></div>
                <div class="event-time">${new Date(timestamp).toLocaleTimeString()}</div>
                <div style="color: #d1d5db; margin-top: 5px; font-size: 0.9em;">${JSON.stringify(event.payload || {})}</div>
            `;

            eventLog.insertBefore(eventItem, eventLog.firstChild);

            // Keep only last 50 events
            while (eventLog.children.length > 50) {
                eventLog.removeChild(eventLog.lastChild);
            }
        }

        // Load agents
        async function loadAgents() {
            try {
                const response = await fetch('/api/agents');
                const data = await response.json();

                const agentList = document.getElementById('agentList');

                if (data.agents.length === 0) {
                    agentList.innerHTML = '<div class="loading">No agents found</div>';
                    return;
                }

                agentList.innerHTML = data.agents.map(agent => `
                    <div class="agent-item">
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-did">${agent.did}</div>
                        <span class="agent-status">${agent.status}</span>
                    </div>
                `).join('');

                // Update stats
                document.getElementById('totalAgents').textContent = data.total;
                document.getElementById('activeAgents').textContent =
                    data.agents.filter(a => a.status === 'active' || a.status === 'created').length;
            } catch (error) {
                console.error('Failed to load agents:', error);
                document.getElementById('agentList').innerHTML =
                    '<div class="error">Failed to load agents</div>';
            }
        }

        // Load goals
        async function loadGoals() {
            try {
                const response = await fetch('/api/goals');
                const data = await response.json();
                document.getElementById('totalGoals').textContent = data.total;
            } catch (error) {
                console.error('Failed to load goals:', error);
            }
        }

        // Initialize
        connectWebSocket();
        loadAgents();
        loadGoals();

        // Refresh data every 30 seconds
        setInterval(() => {
            loadAgents();
            loadGoals();
        }, 30000);
    </script>
</body>
</html>
"""
