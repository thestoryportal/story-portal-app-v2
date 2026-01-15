# L10 Human Interface Layer

Real-time dashboard, control operations, and human-in-the-loop workflows for the AI Agent Platform.

## Overview

The L10 Human Interface Layer provides:

- **Dashboard Service**: Real-time agent state and metrics aggregation
- **Control Service**: Pause/resume agents, adjust quotas with distributed locking
- **WebSocket Gateway**: Push updates to clients (<500ms latency)
- **Event Viewer**: Query event history with filtering
- **Alert Manager**: Threshold alerts and notifications
- **Audit Service**: Comprehensive audit trail for all control actions
- **Cost Tracking**: Usage attribution and cost monitoring

## Architecture

```
L10 Human Interface Layer
├── Dashboard Service (L02 StateManager + L06 MetricsEngine)
├── Control Service (L02 Runtime + distributed locking)
├── WebSocket Gateway (Redis pub/sub + FastAPI)
├── Event Service (L06/L11 event history)
├── Alert Service (L06 metrics + alerting)
├── Audit Service (L06 AuditLogger)
└── Cost Service (L06 cost metrics)
```

### Key Features

- **Hybrid Pull + Push**: Query on-demand with Redis caching, WebSocket broadcasts for real-time updates
- **Distributed Locking**: Redis SET NX EX pattern prevents concurrent operations
- **Idempotency**: 24-hour idempotency cache for safe retries
- **Graceful Degradation**: Return partial data when dependencies fail
- **Multi-Tenant**: Tenant-scoped caching and filtering
- **Circuit Breaker**: Resilient cross-layer calls

## Installation

```bash
cd /path/to/platform/src/L10_human_interface
pip3 install -r requirements.txt --break-system-packages
```

## Configuration

Environment variables (see `config/settings.py`):

```bash
# Server
L10_HOST=0.0.0.0
L10_PORT=8010

# Redis
L10_REDIS_HOST=localhost
L10_REDIS_PORT=6379
L10_REDIS_DB=0

# PostgreSQL
L10_POSTGRES_HOST=localhost
L10_POSTGRES_PORT=5432
L10_POSTGRES_DB=agent_platform
L10_POSTGRES_USER=postgres
L10_POSTGRES_PASSWORD=postgres

# Cache TTLs (seconds)
L10_CACHE_TTL_AGENT_LIST=60
L10_CACHE_TTL_METRICS=300
L10_CACHE_TTL_DASHBOARD=120

# Control Operations
L10_CONTROL_LOCK_TTL=30
L10_CONTROL_IDEMPOTENCY_TTL=86400

# WebSocket
L10_WS_HEARTBEAT_INTERVAL=30
L10_WS_MAX_CONNECTIONS=1000
```

## Usage

### Dashboard Service

```python
from L10_human_interface.services import DashboardService
from L10_human_interface.config import L10Settings
import redis.asyncio as redis

# Initialize
settings = L10Settings()
redis_client = await redis.from_url(settings.redis_url)

dashboard = DashboardService(
    state_manager=state_manager,  # L02 StateManager
    metrics_engine=metrics_engine,  # L06 MetricsEngine
    event_bus=event_bus,  # L11 EventBusManager
    redis_client=redis_client,
    circuit_breaker=circuit_breaker,
)
await dashboard.initialize()

# Get dashboard overview
overview = await dashboard.get_dashboard_overview(tenant_id="tenant-1")
print(f"Total agents: {overview.agents_summary.total_count}")
print(f"Running: {overview.agents_summary.running_count}")
print(f"Paused: {overview.agents_summary.paused_count}")

# Get agent detail
agent = await dashboard.get_agent_detail(agent_id="agent-123")
print(f"Agent state: {agent.state}")
print(f"CPU usage: {agent.resource_utilization.cpu_percent}%")
```

### Control Service

```python
from L10_human_interface.services import ControlService

control = ControlService(
    state_manager=state_manager,
    event_bus=event_bus,
    audit_logger=audit_logger,
    redis_client=redis_client,
)

# Pause agent
response = await control.pause_agent(
    agent_id="agent-123",
    tenant_id="tenant-1",
    user_id="user-456",
    reason="Scheduled maintenance",
    idempotency_key="pause-2024-01-15-001",
)

if response.status == ControlStatus.SUCCESS:
    print(f"Agent paused: {response.agent_id}")
    print(f"Previous state: {response.previous_state}")
    print(f"New state: {response.new_state}")

# Resume agent
response = await control.resume_agent(
    agent_id="agent-123",
    tenant_id="tenant-1",
    user_id="user-456",
)

# Emergency stop
response = await control.emergency_stop_agent(
    agent_id="agent-123",
    tenant_id="tenant-1",
    user_id="admin-001",
    reason="Security incident detected",
)

# Adjust quota
response = await control.adjust_quota(
    agent_id="agent-123",
    tenant_id="tenant-1",
    user_id="user-456",
    quota_type="api_calls",
    new_limit=10000,
)
```

### WebSocket Gateway

```python
from L10_human_interface.services import WebSocketGateway

gateway = WebSocketGateway(
    event_bus=event_bus,
    redis_client=redis_client,
)
await gateway.start()

# In your WebSocket endpoint (FastAPI example):
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str = Query(...)):
    connection_id = str(uuid.uuid4())

    await gateway.handle_connection(
        websocket=websocket,
        connection_id=connection_id,
        tenant_id=tenant_id,
    )

# Broadcast event to all subscribers
await gateway.broadcast_event(
    topic="agent.state.changed",
    event_data={
        "agent_id": "agent-123",
        "state": "paused",
        "timestamp": datetime.now(UTC).isoformat(),
    },
)
```

### Client WebSocket Usage

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8010/ws/events?tenant_id=tenant-1");

ws.onopen = () => {
    // Subscribe to topics
    ws.send(JSON.stringify({
        type: "subscribe",
        topics: ["agent.state.changed", "task.completed", "alert.triggered"]
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "event") {
        console.log("Received event:", message.topic, message.data);
        // Update UI based on event
    } else if (message.type === "ping") {
        // Respond to heartbeat
        ws.send(JSON.stringify({ type: "pong" }));
    }
};

// Unsubscribe from topics
ws.send(JSON.stringify({
    type: "unsubscribe",
    topics: ["task.completed"]
}));
```

### Event Service

```python
from L10_human_interface.services import EventService
from L10_human_interface.models import EventQuery

event_service = EventService(event_bus=event_bus)

# Query events
response = await event_service.query_events(
    filters={
        "event_type": "agent.state.changed",
        "agent_id": "agent-123",
        "start_time": "2024-01-15T00:00:00Z",
        "end_time": "2024-01-15T23:59:59Z",
    },
    limit=50,
    offset=0,
)

print(f"Total events: {response.total}")
for event in response.events:
    print(f"{event.timestamp}: {event.event_type} - {event.data}")
```

### Alert Service

```python
from L10_human_interface.services import AlertService

alert_service = AlertService(metrics_engine=metrics_engine)

# Get active alerts
alerts = await alert_service.get_active_alerts()
for alert in alerts:
    print(f"{alert.severity}: {alert.message}")

# Acknowledge alert
await alert_service.acknowledge_alert(
    alert_id="alert-123",
    user="user-456",
)

# Snooze alert
from datetime import timedelta
await alert_service.snooze_alert(
    alert_id="alert-456",
    duration=timedelta(hours=1),
)
```

### Audit Service

```python
from L10_human_interface.services import AuditService
from L10_human_interface.models import AuditQuery

audit_service = AuditService(audit_logger=audit_logger)

# Log action (automatically done by ControlService)
entry = await audit_service.log_action(
    actor="user-456",
    action="pause_agent",
    resource_type="agent",
    resource_id="agent-123",
    tenant_id="tenant-1",
    actor_ip="192.168.1.100",
    reason="Manual pause for maintenance",
    change_delta={"state": {"from": "running", "to": "paused"}},
)

# Query audit trail
query = AuditQuery(
    resource_id="agent-123",
    start_time=datetime.now(UTC) - timedelta(days=7),
    limit=100,
    offset=0,
)
response = await audit_service.query_audit_trail(query)

for entry in response.entries:
    print(f"{entry.timestamp}: {entry.actor} performed {entry.action} on {entry.resource_id}")
```

### Cost Service

```python
from L10_human_interface.services import CostService

cost_service = CostService(metrics_engine=metrics_engine)

# Get cost summary for tenant
summary = await cost_service.get_cost_summary(tenant_id="tenant-1")
print(f"Total cost: ${summary.total_cost_usd:.2f}")
print(f"Costs by model: {summary.cost_by_model}")

# Get agent-specific cost
from datetime import timedelta
end = datetime.now(UTC)
start = end - timedelta(days=30)

cost = await cost_service.get_agent_cost(
    agent_id="agent-123",
    start=start,
    end=end,
)
print(f"Agent cost (30 days): ${cost['total_cost']:.2f}")
```

## Error Handling

All services use structured error codes (E10000-E10999):

```python
from L10_human_interface.models import ErrorCode, InterfaceError

try:
    response = await control.pause_agent(
        agent_id="nonexistent",
        tenant_id="tenant-1",
        user_id="user-456",
    )
except InterfaceError as e:
    print(f"Error {e.code}: {e.message}")
    print(f"HTTP Status: {e.http_status}")
    print(f"Recoverable: {e.is_recoverable}")
    if e.recovery_suggestion:
        print(f"Suggestion: {e.recovery_suggestion}")
```

### Error Code Ranges

- **E10000-E10099**: Authentication & Authorization
- **E10100-E10199**: Dashboard Operations
- **E10200-E10299**: WebSocket Operations
- **E10300-E10399**: Control Operations
- **E10400-E10499**: Event Viewer
- **E10500-E10599**: Audit Operations
- **E10600-E10699**: Cost API
- **E10700-E10799**: Alert Manager
- **E10900-E10999**: Server Errors

## Testing

```bash
# Run all tests
pytest src/L10_human_interface/tests/ -v

# Run specific test suite
pytest src/L10_human_interface/tests/test_dashboard_service.py -v
pytest src/L10_human_interface/tests/test_control_service.py -v
pytest src/L10_human_interface/tests/test_websocket_gateway.py -v

# Run integration tests (requires Redis & PostgreSQL)
pytest src/L10_human_interface/tests/test_integration.py -v

# Run with coverage
pytest src/L10_human_interface/tests/ --cov=src/L10_human_interface --cov-report=html
```

## Performance SLAs

- **Dashboard queries**: <500ms (with caching: <50ms)
- **Control operations**: <100ms
- **WebSocket latency**: <100ms for broadcasts
- **Cache TTLs**:
  - Agent list: 60s
  - Metrics: 300s (5min)
  - Dashboard overview: 120s (2min)
  - Agent detail: 30s

## Integration with Other Layers

- **L02 Runtime Layer**: Agent state management, control operations
- **L06 Evaluation Layer**: Metrics, audit logging, cost tracking
- **L11 Integration Layer**: Event bus for real-time updates

## Development

```bash
# Install dependencies
pip3 install -r requirements.txt --break-system-packages

# Run linting
black src/L10_human_interface/
flake8 src/L10_human_interface/
mypy src/L10_human_interface/

# Run tests with auto-reload
pytest-watch src/L10_human_interface/tests/
```

## Architecture Decisions

1. **Direct Imports vs Service Registry**: Using direct imports for local dev simplicity
2. **Redis for Caching & Locking**: Fast, distributed, well-suited for real-time ops
3. **Event-Driven Cache Invalidation**: Subscribe to L11 events to invalidate stale cache
4. **Graceful Degradation**: Return partial data when sources fail
5. **Idempotency**: 24h cache for safe operation retries
6. **Circuit Breaker**: Protect against cascading failures

## License

Proprietary - AI Agent Platform
