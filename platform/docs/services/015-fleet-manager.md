# Service 15/44: FleetManager

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.fleet_manager` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | LifecycleManager, StateManager, ResourceManager |
| **Category** | Agent Management / Scaling |

## Role in Development Environment

The **FleetManager** handles horizontal scaling and warm pool management for agent fleets. It provides:
- Autoscaling based on CPU/memory utilization
- Warm pool for instant agent provisioning
- Graceful drain operations before termination
- Scaling stabilization to prevent thrashing
- Fleet metrics and scaling history

This is **essential for production agent fleets** - when load increases, FleetManager automatically scales up agents; when load decreases, it gracefully scales down. The warm pool enables sub-second agent startup.

## Data Model

### ScalingDecision Dataclass
- `action: str` - "scale_up", "scale_down", or "no_action"
- `target_replicas: int` - Desired replica count
- `current_replicas: int` - Current replica count
- `reason: str` - Human-readable reason for decision

### ScalingMetrics Dataclass
- `current_replicas: int` - Current instance count
- `desired_replicas: int` - Target instance count
- `avg_cpu_utilization: float` - Average CPU usage (%)
- `avg_memory_utilization: float` - Average memory usage (%)
- `pending_requests: int` - Queued requests

### WarmInstance Dataclass
- `agent_id: str` - Agent identifier
- `created_at: datetime` - When instance was created
- `state: AgentState` - Current state (SUSPENDED)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_replicas` | 1 | Minimum agent instances |
| `max_replicas` | 100 | Maximum agent instances |
| `target_cpu_utilization` | 70% | Target CPU for scaling |
| `scale_up_stabilization_seconds` | 60 | Scale up cooldown |
| `scale_down_stabilization_seconds` | 300 | Scale down cooldown |
| `autoscaling_interval_seconds` | 30 | Autoscaling check interval |

### Warm Pool Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `warm_pool.enabled` | true | Enable warm pool |
| `warm_pool.size` | 5 | Target pool size |
| `warm_pool.refresh_interval_seconds` | 3600 | Instance refresh interval |

### Graceful Drain Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `graceful_drain.timeout_seconds` | 30 | Drain timeout |
| `graceful_drain.checkpoint_before_drain` | true | Save checkpoint before drain |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize(lifecycle, state, resource)` | Initialize with dependencies |
| `evaluate_scaling(metrics)` | Evaluate scaling decision |
| `scale_up(target, config)` | Scale up to target replicas |
| `scale_down(target)` | Scale down to target replicas |
| `get_fleet_metrics()` | Get current fleet metrics |
| `start_autoscaling(config)` | Start autoscaling loop |
| `stop_autoscaling()` | Stop autoscaling loop |
| `acquire_from_warm_pool(config)` | Get warm instance |
| `get_warm_pool_stats()` | Get warm pool statistics |
| `get_autoscaling_status()` | Get autoscaling status |
| `get_scaling_history(limit)` | Get recent scaling decisions |
| `get_health_status()` | Get fleet health status |
| `cleanup()` | Cleanup all resources |

## Use Cases in Your Workflow

### 1. Initialize Fleet Manager
```python
from L02_runtime.services.fleet_manager import FleetManager

fleet = FleetManager(config={
    # Scaling bounds
    "min_replicas": 2,
    "max_replicas": 50,
    "target_cpu_utilization": 70,

    # Stabilization
    "scale_up_stabilization_seconds": 60,
    "scale_down_stabilization_seconds": 300,

    # Warm pool
    "warm_pool": {
        "enabled": True,
        "size": 5,
        "refresh_interval_seconds": 3600
    },

    # Graceful drain
    "graceful_drain": {
        "timeout_seconds": 30,
        "checkpoint_before_drain": True
    }
})

# Initialize with dependencies
await fleet.initialize(
    lifecycle_manager=lifecycle_mgr,
    state_manager=state_mgr,
    resource_manager=resource_mgr
)
```

### 2. Evaluate Scaling Decision
```python
from L02_runtime.models.fleet_models import ScalingMetrics

# Get current metrics
metrics = ScalingMetrics(
    current_replicas=5,
    desired_replicas=5,
    avg_cpu_utilization=85.0,  # High CPU
    avg_memory_utilization=60.0,
    pending_requests=0
)

# Evaluate what scaling action to take
decision = await fleet.evaluate_scaling(metrics)

print(f"Action: {decision.action}")
print(f"Current: {decision.current_replicas}")
print(f"Target: {decision.target_replicas}")
print(f"Reason: {decision.reason}")

# Output:
# Action: scale_up
# Current: 5
# Target: 6
# Reason: CPU utilization 85.0% > target 70%
```

### 3. Manual Scale Up
```python
from L02_runtime.models import AgentConfig

# Define agent template
config_template = AgentConfig(
    agent_id="template",
    trust_level="standard",
    resource_limits={"cpu_limit": 2.0, "memory_limit_mb": 2048},
    tools=["Read", "Edit", "Bash"],
    environment={"ENV": "production"}
)

# Scale up to 10 replicas
results = await fleet.scale_up(
    target_replicas=10,
    config_template=config_template
)

print(f"Spawned {len(results)} new instances")
for result in results:
    print(f"  - {result.agent_id}: {result.state}")
```

### 4. Manual Scale Down
```python
# Scale down to 5 replicas
# FleetManager will:
# 1. Select oldest instances
# 2. Gracefully drain each
# 3. Checkpoint state
# 4. Terminate instances

terminated = await fleet.scale_down(target_replicas=5)

print(f"Terminated {len(terminated)} instances:")
for agent_id in terminated:
    print(f"  - {agent_id}")
```

### 5. Start Autoscaling
```python
# Start autoscaling with config template
await fleet.start_autoscaling(config_template)

# Autoscaling loop will:
# - Check metrics every 30 seconds
# - Evaluate scaling decision
# - Try warm pool first for scale up
# - Execute scale up/down as needed
# - Respect stabilization periods

# Check status
status = fleet.get_autoscaling_status()
print(f"Autoscaling: {'enabled' if status['enabled'] else 'disabled'}")
print(f"Current replicas: {status['current_replicas']}")
print(f"Scale ups: {status['scale_up_count']}")
print(f"Scale downs: {status['scale_down_count']}")
```

### 6. Stop Autoscaling
```python
# Stop autoscaling loop
await fleet.stop_autoscaling()

# Fleet will maintain current replica count
# Manual scaling still available
```

### 7. Use Warm Pool for Fast Startup
```python
# Check warm pool stats first
stats = fleet.get_warm_pool_stats()
print(f"Warm pool size: {stats['current_size']}/{stats['target_size']}")
print(f"Hit rate: {stats['hit_rate_percent']}%")

# Acquire from warm pool (instant startup)
result = await fleet.acquire_from_warm_pool(config_template)

if result:
    print(f"Got warm instance: {result.agent_id}")
    print(f"From warm pool: {result.from_warm_pool}")  # True
else:
    print("Warm pool empty, need cold start")
```

### 8. Get Fleet Metrics
```python
# Get current fleet metrics
metrics = await fleet.get_fleet_metrics()

print(f"Replicas: {metrics.current_replicas}")
print(f"CPU: {metrics.avg_cpu_utilization:.1f}%")
print(f"Memory: {metrics.avg_memory_utilization:.1f}%")
print(f"Pending: {metrics.pending_requests}")
```

### 9. View Scaling History
```python
# Get recent scaling decisions
history = await fleet.get_scaling_history(limit=10)

for decision in history:
    print(f"{decision.action}: {decision.current_replicas} -> {decision.target_replicas}")
    print(f"  Reason: {decision.reason}")
```

### 10. Health Check
```python
# Get comprehensive health status
health = fleet.get_health_status()

print(f"Healthy: {health['healthy']}")
print(f"Replicas: {health['current_replicas']} (min={health['min_replicas']}, max={health['max_replicas']})")
print(f"Active instances: {health['active_instances']}")
print(f"Autoscaling: {health['autoscaling']['enabled']}")
print(f"Warm pool: {health['warm_pool']['current_size']}/{health['warm_pool']['target_size']}")
```

## Service Interactions

```
+------------------+
|  FleetManager    | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+     +------------------+
| LifecycleManager |     |   StateManager    |     | ResourceManager  |
|     (L02)        |     |      (L02)        |     |      (L02)       |
+------------------+     +-------------------+     +------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
| AgentOrchestrator|     | KubernetesRuntime |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **LifecycleManager (L02)**: Spawns/terminates agent instances
- **StateManager (L02)**: Creates checkpoints before drain
- **ResourceManager (L02)**: Collects CPU/memory metrics
- **AgentOrchestrator (L02)**: Uses fleet for multi-agent work
- **KubernetesRuntime (L02)**: K8s HPA integration (future)

## Scaling Algorithm

```
1. Collect Metrics
   └── CPU, Memory, Pending Requests

2. Calculate Desired Replicas
   └── desired = current * (avg_cpu / target_cpu)

3. Apply Constraints
   ├── max(min_replicas, desired)
   └── min(max_replicas, desired)

4. Check Stabilization
   ├── Scale up: 60s cooldown
   └── Scale down: 300s cooldown

5. Execute Action
   ├── Scale up: Try warm pool, then spawn
   └── Scale down: Drain, checkpoint, terminate
```

## Warm Pool Flow

```
1. Background Maintenance
   ├── Every refresh_interval (1 hour)
   ├── Remove stale instances (> 2x refresh interval)
   └── Create new instances to reach target size

2. Acquire from Pool
   ├── Pop oldest instance
   ├── Reconfigure with new config
   ├── Resume from suspended state
   └── Return SpawnResult (from_warm_pool=True)

3. Pool Miss
   ├── Record miss statistic
   └── Fall back to cold start
```

## Graceful Drain Flow

```
1. Agent selected for termination

2. Checkpoint state (if enabled)
   └── Save to StateManager

3. Wait for drain timeout
   └── Allow in-flight work to complete

4. Terminate agent
   └── Via LifecycleManager
```

## Error Codes

| Code | Description |
|------|-------------|
| E2090 | Scale up failed (lifecycle manager not available) |
| E2091 | Scale down failed (lifecycle manager not available) |
| E2093 | Graceful drain timeout exceeded |

## Execution Examples

```python
# Full fleet management workflow
fleet = FleetManager(config={
    "min_replicas": 2,
    "max_replicas": 20,
    "target_cpu_utilization": 70,
    "warm_pool": {"enabled": True, "size": 3}
})

await fleet.initialize(
    lifecycle_manager=lifecycle,
    state_manager=state,
    resource_manager=resources
)

# Start with minimum replicas
await fleet.scale_up(2, config_template)

# Start autoscaling
await fleet.start_autoscaling(config_template)

# Monitor
while True:
    metrics = await fleet.get_fleet_metrics()
    status = fleet.get_autoscaling_status()

    print(f"Replicas: {status['current_replicas']}")
    print(f"CPU: {metrics.avg_cpu_utilization:.1f}%")
    print(f"Scale ups: {status['scale_up_count']}")
    print(f"Scale downs: {status['scale_down_count']}")

    await asyncio.sleep(60)

# Cleanup on shutdown
await fleet.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Fleet Initialization | Complete |
| Scaling Evaluation | Complete |
| Scale Up | Complete |
| Scale Down | Complete |
| Graceful Drain | Complete |
| Checkpoint on Drain | Complete |
| Stabilization Period | Complete |
| Warm Pool Creation | Complete |
| Warm Pool Acquisition | Complete |
| Warm Pool Maintenance | Complete |
| Autoscaling Loop | Complete |
| Fleet Metrics | Complete |
| Scaling History | Complete |
| Health Status | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| K8s HPA Integration | Medium | Use K8s HPA for scaling |
| Custom Metrics | Medium | Scale on custom metrics |
| Predictive Scaling | Low | Predict load and pre-scale |
| Pod Disruption Budget | Low | K8s PDB support |
| Redis Events | Low | Publish scaling events |
| Scaling Policies | Low | Different policies by time/load |

## Strengths

- **Complete autoscaling** - CPU-based scaling with stabilization
- **Warm pool** - Near-instant agent provisioning
- **Graceful drain** - Checkpoints before termination
- **Metrics collection** - Real or estimated metrics
- **Scaling history** - Track decisions for debugging
- **Health monitoring** - Comprehensive status

## Weaknesses

- **No K8s HPA** - Local process pool only
- **CPU only** - No memory/custom metric scaling
- **No predictive** - Reactive only
- **No events** - Scaling not published to Redis
- **Single metric** - Cannot combine metrics

## Best Practices

### Stabilization Periods
Prevent scaling thrashing:
```python
FleetManager(config={
    "scale_up_stabilization_seconds": 60,   # Quick scale up
    "scale_down_stabilization_seconds": 300  # Slow scale down
})
```

### Warm Pool Sizing
Match to burst patterns:
```python
FleetManager(config={
    "warm_pool": {
        "size": 5,  # Enough for typical bursts
        "refresh_interval_seconds": 3600  # Refresh hourly
    }
})
```

### Resource Limits
Set appropriate bounds:
```python
FleetManager(config={
    "min_replicas": 2,   # Always available
    "max_replicas": 50,  # Cost control
    "target_cpu_utilization": 70  # Headroom for spikes
})
```

### Checkpoint on Drain
Always enable for stateful agents:
```python
FleetManager(config={
    "graceful_drain": {
        "checkpoint_before_drain": True,
        "timeout_seconds": 30
    }
})
```

## Source Files

- Service: `platform/src/L02_runtime/services/fleet_manager.py`
- Models: `platform/src/L02_runtime/models/fleet_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.10)

## Related Services

- LifecycleManager (L02) - Agent spawn/terminate
- StateManager (L02) - Checkpoint management
- ResourceManager (L02) - Resource metrics
- SandboxManager (L02) - Sandbox for new agents
- AgentOrchestrator (L02) - Uses fleet for workloads

---
*Generated: 2026-01-24 | Platform Services Documentation*
