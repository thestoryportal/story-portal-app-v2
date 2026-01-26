# Service 10/44: SessionService

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.session_service` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Data & Storage |

## Role in Development Environment

The **SessionService** manages agent execution sessions - the runtime context for agent work. It provides:
- Session lifecycle management (create, pause, resume, complete)
- Context persistence across session boundaries
- Checkpoint storage for crash recovery
- Runtime backend tracking (local vs. kubernetes)
- Real-time session events via Redis pub/sub

This is **essential for stateful agent workflows** - when Claude Code runs a long task, the session tracks state, context, and checkpoints.

## Data Model

### Session Fields
- `id: UUID` - Unique session identifier
- `agent_id: UUID` - Agent running in this session
- `session_type: str` - Type of session (e.g., "conversation", "task", "batch")
- `status: SessionStatus` - Current session status
- `context: Dict` - Session context data (conversation history, working state)
- `checkpoint: Dict` - Recovery checkpoint data
- `runtime_backend: RuntimeBackend` - Where session runs (local/kubernetes)
- `runtime_metadata: Dict` - Runtime-specific data (container_id, pod_name, etc.)
- `created_at: datetime` - Session start time
- `updated_at: datetime` - Last activity time

### SessionStatus Enum
- `ACTIVE` - Session is running
- `PAUSED` - Session is paused (can resume)
- `COMPLETED` - Session finished normally
- `CRASHED` - Session failed unexpectedly

### RuntimeBackend Enum
- `LOCAL` - Running on local machine
- `KUBERNETES` - Running in Kubernetes pod
- `UNKNOWN` - Backend not specified

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions/` | Create new session |
| `GET` | `/sessions/{id}` | Get session by ID |
| `PATCH` | `/sessions/{id}` | Update session |
| `GET` | `/sessions/` | List sessions (filter by agent) |

## Use Cases in Your Workflow

### 1. Start a Development Session
```bash
curl -X POST http://localhost:8011/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_type": "development",
    "context": {
      "working_directory": "/project",
      "current_task": "Implement Steam Modal",
      "files_open": ["SteamModal.tsx", "animations.ts"]
    },
    "runtime_backend": "local",
    "runtime_metadata": {
      "terminal_id": "term-123",
      "pid": 12345
    }
  }'
```

### 2. Track Conversation Session
```bash
curl -X POST http://localhost:8011/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_type": "conversation",
    "context": {
      "user_id": "user-456",
      "topic": "code review",
      "message_count": 0
    }
  }'
```

### 3. Save Checkpoint for Recovery
```bash
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{
    "checkpoint": {
      "last_completed_step": 3,
      "files_modified": ["a.ts", "b.ts"],
      "pending_actions": ["run tests", "commit"],
      "recovery_prompt": "Continue implementing modal from step 4"
    }
  }'
```

### 4. Update Session Context
```bash
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "working_directory": "/project",
      "current_task": "Testing Steam Modal",
      "files_open": ["SteamModal.test.tsx"],
      "progress": 0.75
    }
  }'
```

### 5. End Session
```bash
# Complete normally
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'

# Mark as crashed (for recovery)
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"status": "crashed"}'
```

### 6. List Agent Sessions
```bash
# Recent sessions for an agent
curl "http://localhost:8011/sessions/?agent_id=550e8400-e29b-41d4-a716-446655440000&limit=10"

# All recent sessions
curl "http://localhost:8011/sessions/?limit=20"
```

## Service Interactions

```
+------------------+
| SessionService   | <--- L01 Data Layer (PostgreSQL)
|     (L01)        | ---> Redis (pub/sub events)
+--------+---------+
         |
   Provides session tracking for:
         |
+------------------+     +-------------------+     +------------------+
|  AgentRegistry   |     |  SandboxManager   |     |   L02 Session    |
|     (L01)        |     |      (L02)        |     |    Runtime       |
+------------------+     +-------------------+     +------------------+
         |
         v
+------------------+     +-------------------+
| ContextOrchest-  |     | WebSocketGateway  |
|   rator (MCP)    |     |      (L10)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **AgentRegistry (L01)**: Sessions linked to registered agents
- **SandboxManager (L02)**: Sessions may run in sandboxed environments
- **L02 Session Runtime**: Actual execution environment
- **ContextOrchestrator (MCP)**: Uses session for context persistence
- **WebSocketGateway (L10)**: Real-time session status updates

## Redis Events

SessionService publishes events to Redis on lifecycle changes:

```python
# On session create
{
    "event_type": "session.created",
    "aggregate_type": "session",
    "aggregate_id": "session-uuid",
    "payload": {
        "agent_id": "agent-uuid",
        "session_type": "development",
        "runtime_backend": "local"
    }
}

# On session update
{
    "event_type": "session.updated",
    "aggregate_type": "session",
    "aggregate_id": "session-uuid",
    "payload": {
        "agent_id": "agent-uuid",
        "status": "paused",
        "updates": ["status", "checkpoint"]
    }
}
```

Subscribe to session events:
```python
await redis.subscribe("events:session")  # All session events
```

## Execution Examples

```bash
# Create a session
curl -X POST http://localhost:8011/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_type": "task",
    "context": {"task_id": "implement-modal"},
    "runtime_backend": "local"
  }'

# Get session
curl http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001

# Pause session
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -d '{"status": "paused"}'

# Resume session
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -d '{"status": "active"}'

# Save checkpoint
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -d '{
    "checkpoint": {
      "step": 5,
      "state": {"files": ["a.ts"]},
      "resume_prompt": "Continue from step 5"
    }
  }'

# List sessions by agent
curl "http://localhost:8011/sessions/?agent_id=550e8400-e29b-41d4-a716-446655440000"

# Complete session
curl -X PATCH http://localhost:8011/sessions/660e8400-e29b-41d4-a716-446655440001 \
  -d '{"status": "completed"}'
```

## Context Structure Examples

### Development Session Context
```json
{
  "context": {
    "working_directory": "/project/src",
    "current_task": "Implement animation system",
    "files_open": ["animations.ts", "SteamModal.tsx"],
    "git_branch": "feature/steam-modal",
    "uncommitted_changes": 3,
    "last_command": "npm test"
  }
}
```

### Conversation Session Context
```json
{
  "context": {
    "user_id": "user-123",
    "topic": "code review",
    "messages": [
      {"role": "user", "content": "Review this PR"},
      {"role": "assistant", "content": "I'll review..."}
    ],
    "files_discussed": ["api.ts"]
  }
}
```

### Checkpoint Structure
```json
{
  "checkpoint": {
    "step": 3,
    "completed_actions": ["analyze", "design", "implement"],
    "pending_actions": ["test", "review"],
    "state_snapshot": {
      "files_modified": ["a.ts", "b.ts"],
      "test_results": null
    },
    "resume_prompt": "Run tests and complete code review"
  }
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Session | Complete |
| Get Session | Complete |
| Update Session | Complete |
| List Sessions | Complete |
| Agent Filter | Complete |
| JSON Context | Complete |
| Checkpoint Storage | Complete |
| Runtime Backend | Complete |
| Redis Events | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Delete Session | Medium | Remove old sessions |
| Status Filter | Medium | List by status (active, crashed) |
| Session Recovery | Medium | Auto-resume crashed sessions |
| Time-Range Query | Low | Filter by date range |
| Session Metrics | Low | Duration, activity stats |
| Bulk Cleanup | Low | Delete old completed sessions |

## Strengths

- **Redis events** - Real-time session lifecycle notifications
- **Checkpoint support** - Save state for crash recovery
- **Flexible context** - Store any session state as JSON
- **Runtime tracking** - Know where sessions run
- **Agent linking** - Sessions tied to registered agents

## Weaknesses

- **No deletion** - Cannot remove sessions
- **No status filtering** - Must filter client-side
- **No auto-recovery** - Must manually resume crashed sessions
- **No session metrics** - No built-in duration tracking
- **Context replacement** - Updates replace context, no merge

## Best Practices

### Session Types
Use consistent types:
- `conversation` - Interactive chat sessions
- `development` - Code development work
- `task` - Single task execution
- `batch` - Batch processing jobs

### Context Management
Keep context focused:
```json
{
  "context": {
    "essential_state": "...",
    "last_action": "...",
    "next_step": "..."
  }
}
```

### Checkpoint Discipline
Save checkpoints at key milestones:
```python
# After completing each major step
await session_service.update_session(session_id, SessionUpdate(
    checkpoint={
        "completed_step": 3,
        "resume_prompt": "Continue with step 4: testing"
    }
))
```

### Crash Recovery
Check for crashed sessions on startup:
```python
# Find crashed sessions for this agent
sessions = await session_service.list_sessions(agent_id=agent_id)
crashed = [s for s in sessions if s.status == SessionStatus.CRASHED]
for session in crashed:
    # Resume from checkpoint
    resume_from(session.checkpoint)
```

## Source Files

- Service: `platform/src/L01_data_layer/services/session_service.py`
- Models: `platform/src/L01_data_layer/models/session.py`
- Routes: (likely in `routers/sessions.py`)

## Related Services

- AgentRegistry (L01) - Agents that run sessions
- SandboxManager (L02) - Isolated execution environments
- EventStore (L01) - Session events persisted here too
- ContextOrchestrator (MCP) - Session context management
- WebSocketGateway (L10) - Real-time session updates

---
*Generated: 2026-01-24 | Platform Services Documentation*
