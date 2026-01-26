# Service 16/44: LifecycleManager

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.lifecycle_manager` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | RuntimeBackend, SandboxManager, L01Bridge |
| **Category** | Agent Management / Lifecycle |

## Role in Development Environment

The **LifecycleManager** handles the complete lifecycle of agent instances from spawn to termination. It provides:
- Agent spawning with sandbox configuration
- Graceful and forced termination
- Suspend/resume with checkpoint support
- State tracking and resource monitoring
- Restart with attempt limiting
- L01 Data Layer integration for event publishing

This is **the core agent lifecycle controller** - every agent spawn, terminate, suspend, resume, and restart operation flows through LifecycleManager.

## Data Model

### AgentState Enum
- `INITIALIZING` - Agent is starting up
- `RUNNING` - Agent is executing
- `SUSPENDED` - Agent is paused (can resume)
- `TERMINATED` - Agent has stopped
- `FAILED` - Agent encountered an error

### AgentInstance Dataclass
- `agent_id: str` - Agent identifier
- `config: AgentConfig` - Agent configuration
- `sandbox: SandboxConfiguration` - Sandbox settings
- `container_id: str` - Container/process ID
- `state: AgentState` - Current state
- `resource_usage: ResourceUsage` - CPU/memory usage
- `created_at: datetime` - Spawn time
- `updated_at: datetime` - Last update
- `terminated_at: datetime` - Termination time (if terminated)

### SpawnResult Dataclass
- `agent_id: str` - Agent identifier
- `container_id: str` - Container/process ID
- `state: AgentState` - Initial state
- `from_warm_pool: bool` - Whether from warm pool

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `spawn_timeout_seconds` | 60 | Timeout for spawn operations |
| `graceful_shutdown_seconds` | 30 | Graceful shutdown timeout |
| `max_restart_count` | 5 | Maximum automatic restarts |
| `enable_suspend` | true | Enable suspend/resume operations |
| `agent_image` | "agent-runtime:latest" | Default container image |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize manager and backend |
| `spawn(config, initial_context)` | Spawn new agent instance |
| `terminate(agent_id, reason, force)` | Terminate an agent |
| `suspend(agent_id, checkpoint)` | Suspend agent (optionally checkpoint) |
| `resume(agent_id, checkpoint_id)` | Resume suspended agent |
| `restart(agent_id, reason)` | Restart agent (terminate + spawn) |
| `get_state(agent_id)` | Get agent's current state |
| `get_instance(agent_id)` | Get full agent instance info |
| `list_instances()` | List all tracked instances |
| `cleanup()` | Terminate all and cleanup |

## Use Cases in Your Workflow

### 1. Initialize Lifecycle Manager
```python
from L02_runtime.services.lifecycle_manager import LifecycleManager
from L02_runtime.services.sandbox_manager import SandboxManager
from L02_runtime.backends.local_runtime import LocalRuntime
from L02_runtime.services.l01_bridge import L01Bridge

# Create dependencies
backend = LocalRuntime(config={"max_processes": 10})
sandbox_manager = SandboxManager(config={"available_runtimes": ["runc"]})
l01_bridge = L01Bridge(config={"l01_url": "http://localhost:8011"})

# Create lifecycle manager
lifecycle = LifecycleManager(
    backend=backend,
    sandbox_manager=sandbox_manager,
    config={
        "spawn_timeout_seconds": 60,
        "graceful_shutdown_seconds": 30,
        "max_restart_count": 5,
        "enable_suspend": True,
        "agent_image": "agent-runtime:latest"
    },
    l01_bridge=l01_bridge
)

await lifecycle.initialize()
```

### 2. Spawn an Agent
```python
from L02_runtime.models import AgentConfig, TrustLevel, ResourceLimits

# Create agent configuration
config = AgentConfig(
    agent_id="agent-001",
    trust_level=TrustLevel.STANDARD,
    resource_limits=ResourceLimits(
        cpu="2",
        memory="2Gi",
        tokens_per_hour=100000
    ),
    tools=["Read", "Edit", "Bash"],
    environment={
        "PROJECT_DIR": "/project",
        "LOG_LEVEL": "info"
    }
)

# Spawn with initial context
result = await lifecycle.spawn(
    config=config,
    initial_context={
        "task": "Implement Steam Modal",
        "working_directory": "/project/src"
    }
)

print(f"Agent spawned: {result.agent_id}")
print(f"Container ID: {result.container_id}")
print(f"State: {result.state}")
```

### 3. Terminate an Agent
```python
# Graceful termination (waits for in-flight work)
await lifecycle.terminate(
    agent_id="agent-001",
    reason="task_completed"
)

# Forced termination (immediate kill)
await lifecycle.terminate(
    agent_id="agent-001",
    reason="timeout",
    force=True
)
```

### 4. Suspend and Resume Agent
```python
# Suspend with checkpoint
checkpoint_id = await lifecycle.suspend(
    agent_id="agent-001",
    checkpoint=True
)
print(f"Agent suspended, checkpoint: {checkpoint_id}")

# Later: Resume from checkpoint
state = await lifecycle.resume(
    agent_id="agent-001",
    checkpoint_id=checkpoint_id
)
print(f"Agent resumed, state: {state}")
```

### 5. Restart an Agent
```python
# Restart preserves original config
result = await lifecycle.restart(
    agent_id="agent-001",
    reason="memory_leak"
)

print(f"Agent restarted: {result.agent_id}")
print(f"New container: {result.container_id}")

# Note: Tracks restart count, fails after max_restart_count (5)
```

### 6. Check Agent State
```python
# Get current state
state = await lifecycle.get_state("agent-001")
print(f"State: {state}")  # AgentState.RUNNING

# Get full instance details
instance = await lifecycle.get_instance("agent-001")
print(f"Agent ID: {instance.agent_id}")
print(f"State: {instance.state}")
print(f"Container: {instance.container_id}")
print(f"CPU Usage: {instance.resource_usage.cpu_percent}%")
print(f"Memory: {instance.resource_usage.memory_mb}MB")
print(f"Created: {instance.created_at}")
```

### 7. List All Instances
```python
# Get all tracked instances
instances = await lifecycle.list_instances()

for agent_id, instance in instances.items():
    print(f"{agent_id}: {instance.state.value}")

# Filter by state
running = [i for i in instances.values() if i.state == AgentState.RUNNING]
print(f"Running agents: {len(running)}")
```

### 8. Cleanup on Shutdown
```python
# Terminate all agents and cleanup
await lifecycle.cleanup()

# This will:
# 1. Force terminate all running agents
# 2. Cleanup backend resources
# 3. Clear internal state
```

## Service Interactions

```
+------------------+
| LifecycleManager | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+     +------------------+
| RuntimeBackend   |     |  SandboxManager   |     |    L01Bridge     |
| (Local/K8s)      |     |      (L02)        |     |      (L02)       |
+------------------+     +-------------------+     +------------------+
         |                                                   |
         |                                                   v
         |                                        +------------------+
         |                                        |  L01 Data Layer  |
         |                                        |  (SessionService)|
         |                                        +------------------+
   Used by:
         |
+------------------+     +-------------------+     +------------------+
|  FleetManager    |     |   StateManager    |     | AgentOrchestrator|
|     (L02)        |     |      (L02)        |     |      (L02)       |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **RuntimeBackend**: LocalRuntime or KubernetesRuntime for container operations
- **SandboxManager (L02)**: Generates sandbox configuration based on trust level
- **L01Bridge (L02)**: Publishes lifecycle events to L01 Data Layer
- **FleetManager (L02)**: Uses for scale up/down operations
- **StateManager (L02)**: Checkpoints during suspend
- **AgentOrchestrator (L02)**: Manages multi-agent workflows

## Lifecycle State Machine

```
                    ┌─────────────┐
                    │ INITIALIZING│
                    └──────┬──────┘
                           │ spawn success
                           v
    ┌───────────┐    ┌─────────────┐    ┌───────────┐
    │ SUSPENDED │◄───│   RUNNING   │───►│   FAILED  │
    └─────┬─────┘    └──────┬──────┘    └───────────┘
          │                 │
          │   resume        │ terminate
          │                 │
          └────────►────────┼────────────────►┌───────────┐
                           │                  │ TERMINATED│
                           └─────────────────►└───────────┘
```

## L01 Integration Events

When L01Bridge is configured, LifecycleManager publishes these events:

```python
# On spawn
await l01_bridge.on_agent_spawned(spawn_result, agent_instance)
# Creates L01 session, returns session_id

# On state change
await l01_bridge.on_agent_state_changed(
    l01_session_id=session_id,
    agent_id=agent_id,
    old_state=AgentState.RUNNING,
    new_state=AgentState.SUSPENDED
)

# On terminate
await l01_bridge.on_agent_terminated(
    l01_session_id=session_id,
    agent_id=agent_id,
    termination_reason="task_completed",
    resource_usage={"cpu_seconds": 120, "memory_mb_peak": 512}
)
```

## Error Codes

| Code | Description |
|------|-------------|
| E2000 | Agent not found |
| E2020 | Spawn failed (sandbox error or other) |
| E2021 | Spawn timeout exceeded |
| E2022 | Terminate failed or agent not found |
| E2023 | Suspend failed (disabled, not found, or wrong state) |
| E2024 | Resume failed (disabled, not found, or wrong state) |
| E2025 | Max restart count exceeded |

## Execution Examples

```python
# Complete lifecycle workflow
lifecycle = LifecycleManager(
    backend=LocalRuntime(),
    sandbox_manager=SandboxManager()
)

await lifecycle.initialize()

# Spawn
config = AgentConfig(
    agent_id="agent-1",
    trust_level=TrustLevel.STANDARD,
    tools=["Read", "Edit"]
)
result = await lifecycle.spawn(config)
print(f"Spawned: {result.agent_id}")

# Check state
state = await lifecycle.get_state("agent-1")
print(f"State: {state}")  # RUNNING

# Suspend
checkpoint = await lifecycle.suspend("agent-1")
print(f"Suspended with checkpoint: {checkpoint}")

# Resume
await lifecycle.resume("agent-1", checkpoint)
print("Resumed")

# Restart
await lifecycle.restart("agent-1", reason="refresh")
print("Restarted")

# Terminate
await lifecycle.terminate("agent-1", reason="done")
print("Terminated")

# Cleanup
await lifecycle.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize | Complete |
| Spawn | Complete |
| Terminate (graceful/force) | Complete |
| Suspend | Complete |
| Resume | Complete |
| Restart | Complete |
| Get State | Complete |
| Get Instance | Complete |
| List Instances | Complete |
| Restart Count Limiting | Complete |
| L01 Bridge Integration | Complete |
| Resource Usage Tracking | Complete |
| Cleanup | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Health Checks | Medium | Periodic agent health probes |
| Automatic Restart | Medium | Restart on crash detection |
| Preemption | Low | Preempt low-priority agents |
| Migration | Low | Move agent between backends |
| Resource Quotas | Low | Enforce per-agent quotas |
| Metrics Export | Low | Prometheus metrics |

## Strengths

- **Complete lifecycle** - Spawn, terminate, suspend, resume, restart
- **State tracking** - Accurate state machine
- **L01 integration** - Events published to data layer
- **Restart limiting** - Prevents restart loops
- **Resource monitoring** - CPU/memory tracking
- **Timeout handling** - Spawn and shutdown timeouts

## Weaknesses

- **No health checks** - Cannot detect hung agents
- **No auto-restart** - Manual restart only
- **No preemption** - Cannot preempt running agents
- **No migration** - Cannot move between backends
- **Single backend** - One backend per manager

## Best Practices

### Trust Level Selection
Match trust to workload:
```python
# Trusted: Your verified code
AgentConfig(trust_level=TrustLevel.TRUSTED)

# Standard: Normal workloads
AgentConfig(trust_level=TrustLevel.STANDARD)

# Untrusted: Third-party code
AgentConfig(trust_level=TrustLevel.UNTRUSTED)
```

### Graceful vs Force Terminate
Use graceful when possible:
```python
# Prefer graceful (allows cleanup)
await lifecycle.terminate(agent_id, reason="done", force=False)

# Use force only when necessary
await lifecycle.terminate(agent_id, reason="hung", force=True)
```

### Restart Handling
Monitor restart counts:
```python
try:
    await lifecycle.restart(agent_id, reason="error")
except LifecycleError as e:
    if e.code == "E2025":
        # Max restarts exceeded - investigate root cause
        logger.error(f"Agent {agent_id} keeps failing")
```

### Suspend for Long Pauses
Use suspend instead of keeping idle:
```python
# Suspend when not needed
checkpoint = await lifecycle.suspend(agent_id)

# Resume when needed again
await lifecycle.resume(agent_id, checkpoint)
```

## Source Files

- Service: `platform/src/L02_runtime/services/lifecycle_manager.py`
- Models: `platform/src/L02_runtime/models/agent_models.py`
- L01 Bridge: `platform/src/L02_runtime/services/l01_bridge.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.3, 11.3)

## Related Services

- RuntimeBackend (L02) - Container operations
- SandboxManager (L02) - Sandbox configuration
- FleetManager (L02) - Fleet scaling
- StateManager (L02) - State persistence
- SessionService (L01) - Session tracking
- AgentRegistry (L01) - Agent registration

---
*Generated: 2026-01-24 | Platform Services Documentation*
