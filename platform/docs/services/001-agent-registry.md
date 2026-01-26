# Service 1/44: AgentRegistry

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.agent_registry` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Data & Storage |

## Role in Development Environment

The **AgentRegistry** is the foundational data persistence service for agent metadata. It serves as the **single source of truth** for all agent definitions, configurations, and lifecycle states in your platform.

**What it stores:**
- Agent identity (UUID, DID - Decentralized Identifier)
- Agent type (general, reasoning, execution, coordination)
- Status (created, active, idle, busy, suspended, terminated, error)
- Configuration (JSON blob for agent-specific settings)
- Metadata (arbitrary key-value data)
- Resource limits (CPU, memory, concurrency constraints)

## Data Model

### AgentStatus Enum
- `CREATED` - Initial state after registration
- `ACTIVE` - Running and available
- `IDLE` - Available but not currently working
- `BUSY` - Currently executing a task
- `SUSPENDED` - Temporarily paused
- `TERMINATED` - Permanently stopped
- `ERROR` - In error state

### Agent Fields
- `id: UUID` - Unique identifier
- `did: str` - Decentralized identifier (format: `did:agent:{name}:{hash}`)
- `name: str` - Human-readable name
- `agent_type: str` - Type classification
- `status: AgentStatus` - Current lifecycle status
- `configuration: Dict` - Agent-specific settings
- `metadata: Dict` - Arbitrary key-value data
- `resource_limits: Dict` - CPU, memory, concurrency limits
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agents/` | Create a new agent |
| `GET` | `/agents/` | List agents (with optional status filter) |
| `GET` | `/agents/{id}` | Get agent by UUID |
| `PATCH` | `/agents/{id}` | Update agent fields |
| `DELETE` | `/agents/{id}` | Delete an agent |

## Use Cases in Your Workflow

### 1. Registering Claude Code Sub-agents
When you spawn Task agents (Explore, Plan, Bash, etc.), they could be registered here for tracking:
```bash
curl -X POST http://localhost:8011/agents/ \
  -H "Content-Type: application/json" \
  -d '{"name": "explore-agent", "agent_type": "exploration", "configuration": {"thoroughness": "medium"}}'
```

### 2. Tracking Agent State Across Sessions
Use for persistent tracking of long-running agents or background tasks.

### 3. Fleet Management Dashboard
The L10 Dashboard queries this registry to display all agents and their statuses.

## Service Interactions

```
+------------------+
|  AgentRegistry   | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
         v
+------------------+     +-------------------+
|  AgentAssigner   |---->|  TaskOrchestrator |
|     (L05)        |     |      (L05)        |
+------------------+     +-------------------+
         |
         v
+------------------+
|  FleetManager    |
|     (L02)        |
+------------------+
```

- **AgentAssigner (L05)**: Queries registry to find capable agents for task assignment
- **FleetManager (L02)**: Uses registry for scaling decisions
- **LifecycleManager (L02)**: Updates agent status during spawn/terminate
- **DashboardService (L10)**: Reads registry for UI display

## Event Publishing

Every CRUD operation publishes to Redis:
- `agent.created` - New agent registered
- `agent.updated` - Agent modified
- `agent.deleted` - Agent removed

These events allow other services to react to agent lifecycle changes.

## Execution Examples

```bash
# List all active agents
curl http://localhost:8011/agents/?status=active

# Get specific agent
curl http://localhost:8011/agents/550e8400-e29b-41d4-a716-446655440000

# Update agent status
curl -X PATCH http://localhost:8011/agents/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"status": "busy"}'

# Create new agent
curl -X POST http://localhost:8011/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "agent_type": "general",
    "configuration": {"model": "claude-3"},
    "metadata": {"project": "story-portal"},
    "resource_limits": {"max_concurrent": 5}
  }'

# Delete agent
curl -X DELETE http://localhost:8011/agents/550e8400-e29b-41d4-a716-446655440000
```

## Implementation Status

| Component | Status |
|-----------|--------|
| CRUD Operations | Complete |
| PostgreSQL Integration | Complete |
| Redis Event Publishing | Complete |
| API Routes | Complete |
| JSON Field Parsing | Complete |
| Status Filtering | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Capability Indexing | Medium | Add searchable capability tags |
| Health Check Ping | Low | Periodic liveness check for registered agents |
| Audit Trail | Low | Full event sourcing for compliance |

## Strengths

- **Simple, focused CRUD** - Does one thing well
- **Event-driven** - Other services react to changes via Redis pub/sub
- **Flexible schema** - JSON fields allow extensibility without migrations
- **DID support** - Decentralized identifiers for future cross-platform agent identity

## Weaknesses

- **No caching layer** - Every request hits PostgreSQL
- **Mock agents in L05** - AgentAssigner still uses mock data instead of querying registry
- **No bulk operations** - Creating/updating multiple agents requires multiple API calls
- **No search** - Can only filter by status, not by capabilities or metadata

## Source Files

- Service: `platform/src/L01_data_layer/services/agent_registry.py`
- Models: `platform/src/L01_data_layer/models/agent.py`
- Routes: `platform/src/L01_data_layer/routers/agents.py`

## Related Services

- ConfigStore (L01) - Configuration storage
- FleetManager (L02) - Agent fleet management
- LifecycleManager (L02) - Agent lifecycle control
- AgentAssigner (L05) - Task-to-agent assignment

---
*Generated: 2026-01-24 | Platform Services Documentation*
