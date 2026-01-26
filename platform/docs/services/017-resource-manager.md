# Service 17/44: ResourceManager

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.resource_manager` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (in-memory) |
| **Category** | Agent Management / Resources |

## Role in Development Environment

The **ResourceManager** enforces CPU, memory, and token quotas for agent instances. It provides:
- Quota creation and management per agent
- Resource usage tracking (CPU, memory, tokens)
- Configurable enforcement modes (hard, soft, warn-only)
- Violation detection and action triggering
- Periodic usage reporting
- Kubernetes-style resource parsing

This is **essential for cost control and fairness** - it prevents agents from consuming unlimited resources and ensures token budgets are respected.

## Data Model

### EnforcementMode Enum
- `HARD` - Immediately suspend/terminate on breach
- `SOFT_THEN_HARD` - Warn first, then enforce on repeat
- `WARN_ONLY` - Only log warnings, no action

### QuotaAction Enum
- `WARN` - Log a warning
- `THROTTLE` - Slow down the agent
- `SUSPEND` - Suspend the agent
- `TERMINATE` - Terminate the agent

### QuotaScope Enum
- `AGENT` - Per-agent quota
- `SESSION` - Per-session quota
- `TENANT` - Per-tenant quota

### ResourceQuota Dataclass
- `scope: QuotaScope` - Quota scope (agent, session, tenant)
- `target_id: str` - Target identifier
- `limits: Dict` - Resource limits (cpu, memory, tokens_per_hour)
- `usage: QuotaUsage` - Current usage
- `reset_at: datetime` - When quota resets

### QuotaUsage Dataclass
- `cpu_seconds: float` - CPU seconds consumed
- `memory_peak_mb: float` - Peak memory usage
- `tokens_consumed: int` - Tokens consumed

### ResourceUsage Dataclass
- `cpu_seconds: float` - CPU seconds consumed
- `memory_peak_mb: float` - Peak memory in MB
- `tokens_consumed: int` - Tokens consumed

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_limits.cpu` | "2" | Default CPU limit |
| `default_limits.memory` | "2Gi" | Default memory limit |
| `default_limits.tokens_per_hour` | 100000 | Default token budget |
| `enforcement.cpu` | "hard" | CPU enforcement mode |
| `enforcement.memory` | "hard" | Memory enforcement mode |
| `enforcement.tokens` | "soft_then_hard" | Token enforcement mode |
| `token_budget_action` | "suspend" | Action when tokens exceeded |
| `usage_report_interval_seconds` | 60 | Reporting interval |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize and start background tasks |
| `create_quota(agent_id, limits)` | Create quota for agent |
| `get_quota(agent_id)` | Get agent's quota |
| `update_quota(agent_id, limits)` | Update quota limits |
| `report_usage(agent_id, cpu, memory, tokens)` | Report resource usage |
| `get_usage(agent_id)` | Get agent's usage |
| `reset_quota(agent_id)` | Reset quota usage |
| `cleanup_quota(agent_id)` | Remove quota tracking |
| `cleanup()` | Cleanup all resources |

## Use Cases in Your Workflow

### 1. Initialize Resource Manager
```python
from L02_runtime.services.resource_manager import ResourceManager

resource_mgr = ResourceManager(config={
    # Default limits
    "default_limits": {
        "cpu": "2",           # 2 CPU cores
        "memory": "2Gi",      # 2 GB RAM
        "tokens_per_hour": 100000
    },

    # Enforcement modes
    "enforcement": {
        "cpu": "hard",              # Immediate enforcement
        "memory": "hard",           # Immediate enforcement
        "tokens": "soft_then_hard"  # Warn first, then enforce
    },

    # Action for token budget exceeded
    "token_budget_action": "suspend",

    # Usage reporting interval
    "usage_report_interval_seconds": 60
})

await resource_mgr.initialize()
```

### 2. Create Quota for Agent
```python
from L02_runtime.models import ResourceLimits

# Create with custom limits
limits = ResourceLimits(
    cpu="4",              # 4 CPU cores
    memory="8Gi",         # 8 GB RAM
    tokens_per_hour=200000
)

quota = await resource_mgr.create_quota(
    agent_id="agent-001",
    limits=limits
)

print(f"Quota created for {quota.target_id}")
print(f"Limits: {quota.limits}")
print(f"Resets at: {quota.reset_at}")

# Create with defaults
quota = await resource_mgr.create_quota(agent_id="agent-002")
```

### 3. Report Resource Usage
```python
# Report CPU usage (seconds consumed)
await resource_mgr.report_usage(
    agent_id="agent-001",
    cpu_seconds=5.5
)

# Report memory usage (current MB)
await resource_mgr.report_usage(
    agent_id="agent-001",
    memory_mb=1024.0
)

# Report token consumption
await resource_mgr.report_usage(
    agent_id="agent-001",
    tokens=1500
)

# Report all at once
await resource_mgr.report_usage(
    agent_id="agent-001",
    cpu_seconds=2.0,
    memory_mb=2048.0,
    tokens=500
)
```

### 4. Check Usage
```python
# Get current usage
usage = await resource_mgr.get_usage("agent-001")

print(f"CPU: {usage.cpu_seconds:.2f} seconds")
print(f"Memory: {usage.memory_peak_mb:.2f} MB (peak)")
print(f"Tokens: {usage.tokens_consumed}")
```

### 5. Check Quota
```python
# Get quota with limits and usage
quota = await resource_mgr.get_quota("agent-001")

print(f"Limits:")
print(f"  CPU: {quota.limits['cpu']}")
print(f"  Memory: {quota.limits['memory']}")
print(f"  Tokens/hour: {quota.limits['tokens_per_hour']}")

print(f"Current Usage:")
print(f"  CPU: {quota.usage.cpu_seconds:.2f}s")
print(f"  Memory: {quota.usage.memory_peak_mb:.2f}MB")
print(f"  Tokens: {quota.usage.tokens_consumed}")

print(f"Resets at: {quota.reset_at}")
```

### 6. Update Quota Limits
```python
# Increase limits for a heavy workload
new_limits = ResourceLimits(
    cpu="8",
    memory="16Gi",
    tokens_per_hour=500000
)

quota = await resource_mgr.update_quota(
    agent_id="agent-001",
    limits=new_limits
)

print(f"Updated limits: {quota.limits}")
```

### 7. Reset Quota
```python
# Reset quota usage (e.g., at hour boundary)
await resource_mgr.reset_quota("agent-001")

# Usage counters reset to 0
# Warning flags cleared
# Reset time extended by 1 hour
```

### 8. Cleanup Agent Quota
```python
# Remove tracking when agent terminates
await resource_mgr.cleanup_quota("agent-001")

# Quota, usage, and warning state removed
```

## Service Interactions

```
+------------------+
| ResourceManager  | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Tracks usage for:
         |
+------------------+     +-------------------+
| LifecycleManager |     |  AgentExecutor    |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
         |
   Provides metrics to:
         |
+------------------+     +-------------------+
|  FleetManager    |     |   MetricsEngine   |
|     (L02)        |     |      (L06)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **LifecycleManager (L02)**: Creates quotas on spawn, cleans up on terminate
- **AgentExecutor (L02)**: Reports usage during execution
- **FleetManager (L02)**: Uses metrics for scaling decisions
- **MetricsEngine (L06)**: Aggregates resource statistics

## Enforcement Flow

```
Usage Reported
      │
      v
Check Against Quota
      │
      ├── Within Limits ─────> Continue
      │
      └── Exceeded ──────────> Check Enforcement Mode
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            v                         v                         v
       WARN_ONLY               SOFT_THEN_HARD                 HARD
            │                         │                         │
       Log Warning            First Time?                  Enforce
            │                    │    │                   Immediately
            v                    v    v
          Done               Warn   Enforce
```

## Enforcement Actions

| Resource | Default Mode | Default Action |
|----------|--------------|----------------|
| CPU | HARD | SUSPEND |
| Memory | HARD | SUSPEND |
| Tokens | SOFT_THEN_HARD | SUSPEND |

## Resource Parsing

The manager parses Kubernetes-style resource specifications:

```python
# CPU parsing
"2"      → 2.0 cores
"500m"   → 0.5 cores
"1500m"  → 1.5 cores

# Memory parsing
"2Gi"    → 2048 MB
"512Mi"  → 512 MB
"4G"     → 4000 MB
"1024M"  → 1024 MB
```

## Error Codes

| Code | Description |
|------|-------------|
| E2070 | Quota/usage not found for agent |
| E2073 | Quota update failed |

## Execution Examples

```python
# Complete resource management workflow
resource_mgr = ResourceManager(config={
    "default_limits": {
        "cpu": "2",
        "memory": "4Gi",
        "tokens_per_hour": 100000
    },
    "enforcement": {
        "cpu": "hard",
        "memory": "hard",
        "tokens": "soft_then_hard"
    }
})

await resource_mgr.initialize()

# Create quota for agent
quota = await resource_mgr.create_quota("agent-1")

# Simulate usage reporting during execution
for i in range(10):
    await resource_mgr.report_usage(
        agent_id="agent-1",
        cpu_seconds=0.5,
        memory_mb=512 + i * 100,
        tokens=1000
    )

# Check usage
usage = await resource_mgr.get_usage("agent-1")
print(f"Total CPU: {usage.cpu_seconds}s")
print(f"Peak Memory: {usage.memory_peak_mb}MB")
print(f"Tokens Used: {usage.tokens_consumed}")

# Reset at hour boundary
await resource_mgr.reset_quota("agent-1")

# Cleanup on agent terminate
await resource_mgr.cleanup_quota("agent-1")

# Shutdown
await resource_mgr.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize | Complete |
| Create Quota | Complete |
| Get Quota | Complete |
| Update Quota | Complete |
| Report Usage | Complete |
| Get Usage | Complete |
| Reset Quota | Complete |
| Cleanup Quota | Complete |
| Violation Detection | Complete |
| Enforcement Modes | Complete |
| Background Reporting | Complete |
| Resource Parsing | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| LifecycleManager Integration | High | Actually suspend/terminate on violation |
| Tenant Quotas | Medium | Multi-tenant quota aggregation |
| Session Quotas | Medium | Per-session limits |
| Redis Events | Low | Publish usage events |
| Prometheus Metrics | Low | Export metrics |
| Rate Limiting | Low | Request-based throttling |

## Strengths

- **Flexible enforcement** - Hard, soft, or warn-only modes
- **Kubernetes-style parsing** - Familiar resource notation
- **Hourly token budgets** - Prevents runaway costs
- **Background reporting** - Periodic usage logging
- **Per-agent tracking** - Individual quotas and usage

## Weaknesses

- **Stub enforcement** - Doesn't actually suspend/terminate
- **No persistence** - Usage lost on restart
- **No aggregation** - No tenant/session totals
- **No Redis events** - Usage not published
- **CPU as seconds** - Not real-time CPU monitoring

## Best Practices

### Token Budget Planning
Set realistic hourly limits:
```python
# Light usage (chat, simple queries)
ResourceLimits(tokens_per_hour=50000)

# Medium usage (code generation)
ResourceLimits(tokens_per_hour=100000)

# Heavy usage (complex reasoning)
ResourceLimits(tokens_per_hour=250000)
```

### Enforcement Mode Selection
Match to workload criticality:
```python
# Production: strict enforcement
ResourceManager(config={
    "enforcement": {
        "cpu": "hard",
        "memory": "hard",
        "tokens": "hard"
    }
})

# Development: lenient
ResourceManager(config={
    "enforcement": {
        "cpu": "warn_only",
        "memory": "warn_only",
        "tokens": "soft_then_hard"
    }
})
```

### Memory Tracking
Report memory frequently:
```python
# Report current memory usage periodically
import psutil

process = psutil.Process()
memory_mb = process.memory_info().rss / (1024 * 1024)

await resource_mgr.report_usage(
    agent_id=agent_id,
    memory_mb=memory_mb
)
```

### Token Tracking
Report tokens after each LLM call:
```python
# After LLM inference
response = await llm.generate(prompt)

await resource_mgr.report_usage(
    agent_id=agent_id,
    tokens=response.usage.total_tokens
)
```

## Source Files

- Service: `platform/src/L02_runtime/services/resource_manager.py`
- Models: `platform/src/L02_runtime/models/resource_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.8)

## Related Services

- LifecycleManager (L02) - Agent lifecycle control
- AgentExecutor (L02) - Reports usage during execution
- FleetManager (L02) - Uses metrics for scaling
- SandboxManager (L02) - Sets initial resource limits
- MetricsEngine (L06) - Aggregates statistics

---
*Generated: 2026-01-24 | Platform Services Documentation*
