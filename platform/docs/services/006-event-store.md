# Service 6/44: EventStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.event_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Data & Storage |

## Role in Development Environment

The **EventStore** implements event sourcing for audit trails and state replay. It:
- Persists immutable events to PostgreSQL
- Publishes events to Redis for real-time subscribers
- Enables querying by aggregate, type, or time

This is the foundation for **event-driven architecture** across the platform.

## Data Model

### Event Fields
- `id: UUID` - Unique event identifier
- `event_type: str` - Event type (e.g., "agent.created", "task.completed")
- `aggregate_type: str` - Entity type (e.g., "agent", "task", "plan")
- `aggregate_id: UUID` - Entity ID the event relates to
- `payload: Dict` - Event-specific data
- `metadata: Dict` - Context (user, session, correlation ID)
- `version: int` - Event version for schema evolution
- `created_at: datetime` - Event timestamp

### Event Types Convention
Use dot-notation: `{aggregate}.{action}`
- `agent.created`, `agent.updated`, `agent.deleted`
- `task.started`, `task.completed`, `task.failed`
- `plan.generated`, `plan.approved`, `plan.executed`

## API Methods

| Method | Description |
|--------|-------------|
| `create_event(event_data)` | Create and persist event, publish to Redis |
| `get_event(event_id)` | Retrieve single event by ID |
| `query_events(aggregate_id, aggregate_type, event_type, limit, offset)` | Query with filters |

## Use Cases in Your Workflow

### 1. Track Agent Lifecycle
```bash
curl -X POST http://localhost:8011/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent.created",
    "aggregate_type": "agent",
    "aggregate_id": "550e8400-e29b-41d4-a716-446655440000",
    "payload": {
      "name": "explore-agent",
      "agent_type": "exploration"
    },
    "metadata": {
      "session_id": "session-123",
      "correlation_id": "corr-456"
    },
    "version": 1
  }'
```

### 2. Audit Task Execution
```bash
curl -X POST http://localhost:8011/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "task.completed",
    "aggregate_type": "task",
    "aggregate_id": "660e8400-e29b-41d4-a716-446655440001",
    "payload": {
      "status": "success",
      "duration_ms": 1250,
      "output_lines": 42
    },
    "metadata": {
      "agent_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "version": 1
  }'
```

### 3. Query Entity History
```bash
# Get all events for a specific agent
curl "http://localhost:8011/events/?aggregate_type=agent&aggregate_id=550e8400-e29b-41d4-a716-446655440000"

# Get all task completion events
curl "http://localhost:8011/events/?event_type=task.completed&limit=50"
```

## Service Interactions

```
+------------------+
|   EventStore     | <--- PostgreSQL (persistence)
|     (L01)        | ---> Redis (pub/sub)
+--------+---------+
         |
   Published events consumed by:
         |
+------------------+     +-------------------+     +------------------+
| WebSocketGateway |     |  SagaOrchestrator |     |   AlertManager   |
|     (L10)        |     |      (L11)        |     |      (L06)       |
+------------------+     +-------------------+     +------------------+
         |
         v
+------------------+     +-------------------+
| MetricsEngine    |     |  LearningService  |
|     (L06)        |     |      (L07)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **WebSocketGateway (L10)**: Pushes events to UI in real-time
- **SagaOrchestrator (L11)**: Triggers saga steps based on events
- **AlertManager (L06)**: Triggers alerts on specific events
- **MetricsEngine (L06)**: Aggregates metrics from events
- **All L01 services**: Publish events for their CRUD operations

## Redis Publishing

Every event created is automatically published to Redis:
- Channel: `events:{aggregate_type}`
- Payload: Full event JSON

Subscribers can listen for specific aggregate types:
```python
await redis.subscribe("events:agent")  # All agent events
await redis.subscribe("events:task")   # All task events
```

## Execution Examples

```bash
# Create an event
curl -X POST http://localhost:8011/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "plan.executed",
    "aggregate_type": "plan",
    "aggregate_id": "770e8400-e29b-41d4-a716-446655440002",
    "payload": {
      "steps_completed": 5,
      "steps_total": 5,
      "success": true
    },
    "metadata": {"executor": "orchestrator-1"},
    "version": 1
  }'

# Get specific event
curl http://localhost:8011/events/880e8400-e29b-41d4-a716-446655440003

# Query events by aggregate
curl "http://localhost:8011/events/?aggregate_id=550e8400-e29b-41d4-a716-446655440000"

# Query events by type
curl "http://localhost:8011/events/?aggregate_type=agent"

# Query specific event type
curl "http://localhost:8011/events/?event_type=agent.created"

# Paginate results
curl "http://localhost:8011/events/?limit=10&offset=20"
```

## Event Sourcing Patterns

### State Reconstruction
Replay events to rebuild entity state:
```python
events = await event_store.query_events(
    aggregate_id=agent_id,
    aggregate_type="agent"
)
# Apply events in order to rebuild state
state = {}
for event in events:
    state = apply_event(state, event)
```

### Audit Trail
Query complete history for compliance:
```python
events = await event_store.query_events(
    aggregate_id=task_id,
    aggregate_type="task"
)
# Returns: task.created -> task.started -> task.completed
```

### Correlation Tracking
Use metadata for request tracing:
```json
{
  "metadata": {
    "correlation_id": "req-abc123",
    "session_id": "sess-456",
    "user_id": "user-789"
  }
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Event | Complete |
| Get Event | Complete |
| Query Events | Complete |
| Redis Publishing | Complete |
| Aggregate Filtering | Complete |
| Type Filtering | Complete |
| Pagination | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Time-Range Query | Medium | Filter by created_at range |
| Event Replay | Medium | Replay events from offset |
| Snapshot Support | Low | Create snapshots for fast state rebuild |
| Event Archival | Low | Move old events to cold storage |
| Schema Validation | Low | Validate payload against schema |
| Batch Insert | Low | Insert multiple events at once |

## Strengths

- **Immutable audit trail** - Events never modified, only appended
- **Real-time pub/sub** - Immediate notification via Redis
- **Flexible querying** - Filter by aggregate, type, pagination
- **Version support** - Handle schema evolution
- **Metadata tracking** - Correlation IDs for tracing

## Weaknesses

- **No time-range query** - Cannot filter by date range
- **No replay utility** - Must manually iterate events
- **No snapshots** - Replaying long event streams is slow
- **No archival** - Events grow indefinitely
- **No schema enforcement** - Payload can be anything

## Best Practices

### Event Naming
Use consistent naming:
- `{aggregate}.{past_tense_verb}`: `agent.created`, `task.failed`
- Keep events small and focused
- Include only changed data in payload

### Metadata Usage
Always include tracing info:
```json
{
  "metadata": {
    "correlation_id": "...",
    "session_id": "...",
    "source_service": "...",
    "timestamp_ms": 1706123456789
  }
}
```

### Versioning
Increment version for breaking changes:
- v1: `{"agent_name": "foo"}`
- v2: `{"name": "foo", "type": "general"}` (field renamed)

## Source Files

- Service: `platform/src/L01_data_layer/services/event_store.py`
- Models: `platform/src/L01_data_layer/models/event.py`
- Routes: (likely in `routers/events.py`)

## Related Services

- EventBusManager (L11) - Redis pub/sub management
- SagaOrchestrator (L11) - Event-driven workflows
- WebSocketGateway (L10) - Real-time UI updates
- All L01 services - Publish events on CRUD operations

---
*Generated: 2026-01-24 | Platform Services Documentation*
