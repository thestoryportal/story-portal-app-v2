# Service 18/44: StateManager

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.state_manager` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Agent Management / State |

## Role in Development Environment

The **StateManager** handles agent state persistence and recovery. It provides:
- Checkpoint creation and restoration (durable storage)
- Hot state caching for fast access (Redis with 1-hour TTL)
- Gzip compression for efficient checkpoint storage
- Automatic cleanup of old checkpoints
- State versioning with sequence numbers
- Transaction-safe checkpoint operations

This is **essential for agent reliability** - when agents suspend, crash, or need recovery, StateManager preserves their execution context. The dual-layer approach (PostgreSQL for durability, Redis for speed) enables both quick resumption and long-term recovery.

## Data Model

### StateSnapshot Dataclass
- `agent_id: str` - Agent identifier
- `session_id: str` - Session identifier
- `state: AgentState` - Current agent state (RUNNING, SUSPENDED, etc.)
- `context: Dict` - Execution context (messages, variables, etc.)
- `timestamp: datetime` - When snapshot was created
- `metadata: Dict` - Additional metadata (version, source, etc.)

### CheckpointInfo Dataclass
- `checkpoint_id: str` - Unique checkpoint identifier
- `agent_id: str` - Agent that owns this checkpoint
- `session_id: str` - Session identifier
- `created_at: datetime` - Creation timestamp
- `size_bytes: int` - Compressed size
- `version: int` - Sequence number

### HotState Dataclass
- `agent_id: str` - Agent identifier
- `state: AgentState` - Current state
- `context: Dict` - Current execution context
- `updated_at: datetime` - Last update time

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `postgres_dsn` | None | PostgreSQL connection string |
| `redis_url` | None | Redis connection URL |
| `hot_state_ttl_seconds` | 3600 | Hot state TTL (1 hour) |
| `checkpoint_retention_days` | 7 | Days to keep checkpoints |
| `compression_level` | 6 | Gzip compression (1-9) |
| `max_checkpoint_size_mb` | 100 | Maximum checkpoint size |
| `cleanup_interval_seconds` | 3600 | Cleanup check interval |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize PostgreSQL schema and Redis connection |
| `create_checkpoint(agent_id, session_id, snapshot)` | Create durable checkpoint |
| `restore_checkpoint(checkpoint_id)` | Restore from checkpoint |
| `list_checkpoints(agent_id)` | List agent's checkpoints |
| `delete_checkpoint(checkpoint_id)` | Delete specific checkpoint |
| `save_hot_state(agent_id, state)` | Save to Redis (fast) |
| `load_hot_state(agent_id)` | Load from Redis |
| `delete_hot_state(agent_id)` | Remove hot state |
| `get_latest_checkpoint(agent_id)` | Get most recent checkpoint |
| `cleanup_old_checkpoints()` | Remove expired checkpoints |
| `cleanup()` | Cleanup all resources |

## Use Cases in Your Workflow

### 1. Initialize State Manager
```python
from L02_runtime.services.state_manager import StateManager

state_mgr = StateManager(config={
    # PostgreSQL for durable checkpoints
    "postgres_dsn": "postgresql://user:pass@localhost:5432/platform",

    # Redis for hot state
    "redis_url": "redis://localhost:6379/0",

    # Hot state expires after 1 hour
    "hot_state_ttl_seconds": 3600,

    # Keep checkpoints for 7 days
    "checkpoint_retention_days": 7,

    # Compression level (1=fast, 9=small)
    "compression_level": 6
})

await state_mgr.initialize()
# Creates l02_runtime schema with checkpoints and agent_state tables
```

### 2. Create Checkpoint Before Suspend
```python
from L02_runtime.models import StateSnapshot, AgentState

# Capture current state
snapshot = StateSnapshot(
    agent_id="agent-001",
    session_id="session-456",
    state=AgentState.SUSPENDED,
    context={
        "messages": [...],
        "working_directory": "/project/src",
        "current_task": "Implement Steam Modal",
        "variables": {"file_count": 42}
    },
    metadata={
        "version": 1,
        "source": "suspend_operation",
        "tokens_used": 15000
    }
)

# Create durable checkpoint
checkpoint = await state_mgr.create_checkpoint(
    agent_id="agent-001",
    session_id="session-456",
    snapshot=snapshot
)

print(f"Checkpoint ID: {checkpoint.checkpoint_id}")
print(f"Size: {checkpoint.size_bytes} bytes")
print(f"Version: {checkpoint.version}")
```

### 3. Restore from Checkpoint
```python
# Restore agent state from checkpoint
snapshot = await state_mgr.restore_checkpoint(
    checkpoint_id="chk-abc123"
)

if snapshot:
    print(f"Agent: {snapshot.agent_id}")
    print(f"State: {snapshot.state}")
    print(f"Context keys: {list(snapshot.context.keys())}")
    print(f"Timestamp: {snapshot.timestamp}")
else:
    print("Checkpoint not found")
```

### 4. Save Hot State (Fast Access)
```python
from L02_runtime.models import HotState

# Save current state to Redis for fast access
hot_state = HotState(
    agent_id="agent-001",
    state=AgentState.RUNNING,
    context={
        "current_tool": "Edit",
        "file_path": "/project/src/Modal.tsx",
        "tokens_this_turn": 500
    }
)

await state_mgr.save_hot_state("agent-001", hot_state)
# Stored in Redis with 1-hour TTL
```

### 5. Load Hot State
```python
# Load from Redis (fast, < 1ms)
hot_state = await state_mgr.load_hot_state("agent-001")

if hot_state:
    print(f"State: {hot_state.state}")
    print(f"Context: {hot_state.context}")
    print(f"Updated: {hot_state.updated_at}")
else:
    print("Hot state expired or not found")
```

### 6. List Agent Checkpoints
```python
# List all checkpoints for an agent
checkpoints = await state_mgr.list_checkpoints("agent-001")

print(f"Found {len(checkpoints)} checkpoints:")
for cp in checkpoints:
    print(f"  {cp.checkpoint_id}: v{cp.version} ({cp.size_bytes} bytes)")
    print(f"    Created: {cp.created_at}")
```

### 7. Get Latest Checkpoint
```python
# Get most recent checkpoint for recovery
latest = await state_mgr.get_latest_checkpoint("agent-001")

if latest:
    print(f"Latest checkpoint: {latest.checkpoint_id}")
    print(f"Version: {latest.version}")
    print(f"Age: {datetime.now() - latest.created_at}")
```

### 8. Delete Checkpoint
```python
# Delete specific checkpoint
await state_mgr.delete_checkpoint("chk-abc123")

# Or delete hot state
await state_mgr.delete_hot_state("agent-001")
```

### 9. Cleanup Old Checkpoints
```python
# Manually trigger cleanup (also runs automatically)
deleted_count = await state_mgr.cleanup_old_checkpoints()
print(f"Deleted {deleted_count} expired checkpoints")
```

## Service Interactions

```
+------------------+
|  StateManager    | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+
|   PostgreSQL     |     |      Redis        |
| (Checkpoints)    |     |   (Hot State)     |
+------------------+     +-------------------+
         |
   Used by:
         |
+------------------+     +-------------------+     +------------------+
| LifecycleManager |     |   FleetManager    |     | AgentOrchestrator|
|     (L02)        |     |      (L02)        |     |      (L02)       |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **PostgreSQL**: Stores durable checkpoints with gzip compression
- **Redis**: Caches hot state for fast access (1-hour TTL)
- **LifecycleManager (L02)**: Creates checkpoints on suspend
- **FleetManager (L02)**: Checkpoints before graceful drain
- **AgentOrchestrator (L02)**: Recovers agents from checkpoints

## Database Schema

The StateManager creates a PostgreSQL schema:

```sql
-- Schema
CREATE SCHEMA IF NOT EXISTS l02_runtime;

-- Checkpoints table
CREATE TABLE l02_runtime.checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    state_data BYTEA NOT NULL,  -- Gzip compressed
    size_bytes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_agent_version UNIQUE (agent_id, version)
);

-- Agent state table
CREATE TABLE l02_runtime.agent_state (
    agent_id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    current_state VARCHAR(50) NOT NULL,
    last_checkpoint_id UUID REFERENCES l02_runtime.checkpoints(checkpoint_id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_checkpoints_agent ON l02_runtime.checkpoints(agent_id);
CREATE INDEX idx_checkpoints_expires ON l02_runtime.checkpoints(expires_at);
```

## Checkpoint Flow

```
1. Create Checkpoint
   ├── Serialize snapshot to JSON
   ├── Gzip compress data
   ├── Insert into PostgreSQL
   ├── Update agent_state table
   └── Return CheckpointInfo

2. Restore Checkpoint
   ├── Query PostgreSQL by checkpoint_id
   ├── Decompress gzip data
   ├── Deserialize JSON to StateSnapshot
   └── Return snapshot

3. Hot State (Redis)
   ├── Save: SET with TTL (1 hour)
   ├── Load: GET with deserialization
   └── Delete: DEL key
```

## Error Codes

| Code | Description |
|------|-------------|
| E2030 | Checkpoint not found |
| E2031 | Checkpoint creation failed (DB error) |
| E2032 | Checkpoint restoration failed (decompression/parse) |
| E2033 | Hot state operation failed (Redis error) |
| E2034 | Checkpoint size exceeds maximum |

## Execution Examples

```python
# Complete state management workflow
state_mgr = StateManager(config={
    "postgres_dsn": "postgresql://localhost/platform",
    "redis_url": "redis://localhost:6379/0",
    "hot_state_ttl_seconds": 3600,
    "checkpoint_retention_days": 7
})

await state_mgr.initialize()

# During execution: save hot state frequently
await state_mgr.save_hot_state("agent-1", HotState(
    agent_id="agent-1",
    state=AgentState.RUNNING,
    context={"current_step": 5}
))

# On suspend: create durable checkpoint
snapshot = StateSnapshot(
    agent_id="agent-1",
    session_id="session-1",
    state=AgentState.SUSPENDED,
    context={"full": "context", "messages": [...]}
)
checkpoint = await state_mgr.create_checkpoint(
    "agent-1", "session-1", snapshot
)

# On resume: restore from checkpoint
restored = await state_mgr.restore_checkpoint(checkpoint.checkpoint_id)

# Or try hot state first (faster)
hot = await state_mgr.load_hot_state("agent-1")
if not hot:
    # Fall back to checkpoint
    latest = await state_mgr.get_latest_checkpoint("agent-1")
    restored = await state_mgr.restore_checkpoint(latest.checkpoint_id)

# Cleanup on shutdown
await state_mgr.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize (schema creation) | Complete |
| Create Checkpoint | Complete |
| Restore Checkpoint | Complete |
| List Checkpoints | Complete |
| Delete Checkpoint | Complete |
| Get Latest Checkpoint | Complete |
| Save Hot State | Complete |
| Load Hot State | Complete |
| Delete Hot State | Complete |
| Gzip Compression | Complete |
| Background Cleanup | Complete |
| Version Tracking | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Checkpoint Encryption | Medium | Encrypt sensitive state data |
| Incremental Checkpoints | Medium | Delta-based checkpoints |
| Checkpoint Streaming | Low | Stream large checkpoints |
| Cross-Region Replication | Low | Replicate checkpoints |
| Metrics Export | Low | Prometheus metrics |
| S3 Backend | Low | Alternative to PostgreSQL |

## Strengths

- **Dual-layer persistence** - Redis for speed, PostgreSQL for durability
- **Compression** - Gzip reduces storage by 60-80%
- **Version tracking** - Sequence numbers for ordering
- **Auto-cleanup** - Background removal of expired checkpoints
- **Transaction safety** - PostgreSQL ACID guarantees
- **TTL-based hot state** - Automatic expiration in Redis

## Weaknesses

- **No encryption** - State stored in plaintext
- **Full snapshots only** - No incremental/delta support
- **Single region** - No cross-region replication
- **Memory pressure** - Large contexts loaded fully
- **No streaming** - Cannot stream large checkpoints
- **PostgreSQL dependency** - Requires database for checkpoints

## Best Practices

### Checkpoint Frequency
Balance durability vs. performance:
```python
# Checkpoint on significant events
await state_mgr.create_checkpoint(...)  # On suspend
await state_mgr.create_checkpoint(...)  # After major task completion
await state_mgr.create_checkpoint(...)  # Before risky operations

# Use hot state for frequent updates
await state_mgr.save_hot_state(...)  # Every few seconds during execution
```

### Context Size Management
Keep contexts reasonably sized:
```python
# Good: Summarize long message histories
context = {
    "recent_messages": messages[-10:],  # Last 10 messages
    "summary": "Previously discussed X, Y, Z",
    "key_variables": {...}
}

# Bad: Include entire history
context = {
    "all_messages": messages  # Could be thousands
}
```

### Recovery Strategy
Try hot state first, then checkpoints:
```python
async def recover_agent(agent_id: str):
    # Try hot state (fast, < 1ms)
    hot = await state_mgr.load_hot_state(agent_id)
    if hot:
        return hot

    # Fall back to checkpoint (slower, but durable)
    latest = await state_mgr.get_latest_checkpoint(agent_id)
    if latest:
        return await state_mgr.restore_checkpoint(latest.checkpoint_id)

    # No state found
    return None
```

### Retention Configuration
Match retention to use case:
```python
# Development: Short retention
StateManager(config={"checkpoint_retention_days": 1})

# Production: Longer retention
StateManager(config={"checkpoint_retention_days": 30})

# Compliance: Extended retention
StateManager(config={"checkpoint_retention_days": 365})
```

## Source Files

- Service: `platform/src/L02_runtime/services/state_manager.py`
- Models: `platform/src/L02_runtime/models/state_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.9)

## Related Services

- LifecycleManager (L02) - Creates checkpoints on suspend
- FleetManager (L02) - Checkpoints before drain
- AgentOrchestrator (L02) - Recovery coordination
- ResourceManager (L02) - Tracks usage in state
- SessionService (L01) - Session context
- ContextOrchestrator (MCP) - Higher-level context management

---
*Generated: 2026-01-24 | Platform Services Documentation*
