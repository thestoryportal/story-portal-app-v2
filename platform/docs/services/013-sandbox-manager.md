# Service 13/44: SandboxManager

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.sandbox_manager` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (Configuration-based) |
| **Category** | Agent Management / Runtime |

## Role in Development Environment

The **SandboxManager** configures agent isolation and runtime security. It provides:
- Trust level to runtime class mapping
- Security context generation
- Network policy selection
- Resource limit validation
- Kubernetes-style resource parsing

This is **critical for agent security** - it determines how much isolation an agent gets based on its trust level. In production, this maps to different container runtimes (runc, gVisor, Kata). In local development, it simulates these with configuration.

## Trust Level → Runtime Mapping

The core function maps trust levels to container runtimes:

| Trust Level | Runtime Class | Isolation Level | Use Case |
|-------------|---------------|-----------------|----------|
| `TRUSTED` | `runc` | Minimal | First-party, verified code |
| `STANDARD` | `gvisor` | Moderate | Normal agent workloads |
| `UNTRUSTED` | `kata` | Strong | Third-party or unknown code |
| `CONFIDENTIAL` | `kata-cc` | Maximum | Sensitive data processing |

## Data Model

### TrustLevel Enum
- `TRUSTED` - First-party verified code (minimal sandbox)
- `STANDARD` - Normal agent workloads (moderate sandbox)
- `UNTRUSTED` - Third-party/unknown code (strong sandbox)
- `CONFIDENTIAL` - Sensitive data (maximum isolation with CC)

### RuntimeClass Enum
- `RUNC` - Standard OCI runtime (minimal isolation)
- `GVISOR` - User-space kernel (application-level sandbox)
- `KATA` - Lightweight VM (strong isolation)
- `KATA_CC` - Kata with Confidential Computing (encrypted memory)

### NetworkPolicy Enum
- `ISOLATED` - No network access
- `RESTRICTED` - Limited egress to approved services
- `ALLOW_EGRESS` - Full outbound network access

### ResourceLimits Dataclass
- `cpu: str` - CPU limit (Kubernetes format: "2", "500m")
- `memory: str` - Memory limit (Kubernetes format: "2Gi", "512Mi")
- `tokens_per_hour: int` - Token budget for LLM calls

### SandboxConfiguration Dataclass
- `runtime_class: RuntimeClass` - Container runtime
- `trust_level: TrustLevel` - Trust classification
- `security_context: Dict` - Kubernetes security context
- `network_policy: NetworkPolicy` - Network isolation
- `resource_limits: ResourceLimits` - Resource constraints

## API Methods

| Method | Description |
|--------|-------------|
| `get_sandbox_config(trust_level, custom_limits)` | Generate sandbox config |
| `validate_sandbox_config(sandbox)` | Validate config settings |
| `get_network_policy(trust_level)` | Get network policy for trust level |
| `get_available_runtimes()` | List available runtime classes |
| `initialize()` | Initialize manager (query k8s in prod) |

## Use Cases in Your Workflow

### 1. Get Sandbox Config for Trusted Agent
```python
from L02_runtime.services.sandbox_manager import SandboxManager
from L02_runtime.models import TrustLevel

manager = SandboxManager(config={
    "default_runtime_class": "runc",
    "available_runtimes": ["runc", "gvisor"]
})

# Get config for trusted agent (minimal isolation)
sandbox = manager.get_sandbox_config(TrustLevel.TRUSTED)
# sandbox.runtime_class = RuntimeClass.RUNC
# sandbox.network_policy = NetworkPolicy.ALLOW_EGRESS
```

### 2. Get Sandbox Config for Untrusted Code
```python
# Get config for untrusted agent (strong isolation)
sandbox = manager.get_sandbox_config(TrustLevel.UNTRUSTED)
# sandbox.runtime_class = RuntimeClass.KATA (or fallback to runc if unavailable)
# sandbox.network_policy = NetworkPolicy.ISOLATED
```

### 3. Custom Resource Limits
```python
from L02_runtime.models import ResourceLimits

custom_limits = ResourceLimits(
    cpu="4",           # 4 CPU cores
    memory="8Gi",      # 8GB RAM
    tokens_per_hour=200000  # Higher token budget
)

sandbox = manager.get_sandbox_config(
    TrustLevel.STANDARD,
    custom_limits=custom_limits
)
```

### 4. Validate Sandbox Configuration
```python
try:
    manager.validate_sandbox_config(sandbox)
    print("Configuration valid")
except SandboxError as e:
    print(f"Invalid: {e.code} - {e.message}")
```

### 5. Check Available Runtimes
```python
available = manager.get_available_runtimes()
# {"runc"} in local dev
# {"runc", "gvisor", "kata", "kata-cc"} in production k8s
```

### 6. Get Network Policy
```python
policy = manager.get_network_policy(TrustLevel.STANDARD)
# NetworkPolicy.RESTRICTED
```

## Service Interactions

```
+------------------+
| SandboxManager   | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Configures sandboxes for:
         |
+------------------+     +-------------------+
| LocalRuntime     |     | KubernetesRuntime |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
         |
   Used by:
         |
+------------------+     +-------------------+     +------------------+
| AgentOrchestrator|     |  SessionService   |     | ExecutionEngine  |
|     (L02)        |     |      (L01)        |     |      (L05)       |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **LocalRuntime (L02)**: Applies sandbox config for local execution
- **KubernetesRuntime (L02)**: Generates pod specs with sandbox settings
- **AgentOrchestrator (L02)**: Requests sandbox configs for agents
- **SessionService (L01)**: Sessions track which sandbox is active
- **ExecutionEngine (L05)**: Tasks run within sandbox constraints

## Security Context Generation

The manager builds Kubernetes-compatible security contexts:

```python
# For TRUSTED level
{
    "run_as_non_root": True,
    "allow_privilege_escalation": False,
    "read_only_root_filesystem": False,
    "capabilities": {
        "drop": ["ALL"]
    }
}

# For UNTRUSTED level
{
    "run_as_non_root": True,
    "run_as_user": 65534,  # nobody
    "run_as_group": 65534,
    "allow_privilege_escalation": False,
    "read_only_root_filesystem": True,
    "capabilities": {
        "drop": ["ALL"]
    },
    "seccomp_profile": {"type": "RuntimeDefault"}
}
```

## Network Policy Mapping

| Trust Level | Network Policy | Description |
|-------------|----------------|-------------|
| TRUSTED | ALLOW_EGRESS | Full outbound access |
| STANDARD | RESTRICTED | Limited to approved services |
| UNTRUSTED | ISOLATED | No network access |
| CONFIDENTIAL | ISOLATED | No network access |

## Execution Examples

```python
# Initialize manager
manager = SandboxManager(config={
    "default_runtime_class": "runc",
    "default_cpu": "2",
    "default_memory": "2Gi",
    "default_tokens_per_hour": 100000,
    "available_runtimes": ["runc"]
})

await manager.initialize()

# Get sandbox for different trust levels
trusted_sandbox = manager.get_sandbox_config(TrustLevel.TRUSTED)
standard_sandbox = manager.get_sandbox_config(TrustLevel.STANDARD)
untrusted_sandbox = manager.get_sandbox_config(TrustLevel.UNTRUSTED)

# Validate
manager.validate_sandbox_config(trusted_sandbox)

# Get serializable dict
config_dict = trusted_sandbox.to_dict()
```

## Resource Parsing

The manager parses Kubernetes-style resource specifications:

```python
# CPU parsing
"2"     → 2.0 cores
"500m"  → 0.5 cores
"1500m" → 1.5 cores

# Memory parsing
"2Gi"   → 2048 MB
"512Mi" → 512 MB
"4G"    → 4000 MB
"1024M" → 1024 MB
```

## Error Codes

| Code | Description |
|------|-------------|
| E2040 | RuntimeClass not available |
| E2041 | CPU limit out of range (0-32 cores) |
| E2042 | Memory limit out of range (0-64Gi) |
| E2043 | Token limit must be non-negative |
| E2044 | Privilege escalation must be disabled |

## Implementation Status

| Component | Status |
|-----------|--------|
| Trust Level Mapping | Complete |
| Sandbox Config Generation | Complete |
| Security Context Building | Complete |
| Network Policy Selection | Complete |
| Resource Limit Validation | Complete |
| Resource Parsing (k8s style) | Complete |
| Runtime Availability Check | Complete |
| Fallback to Default Runtime | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| K8s RuntimeClass Query | Medium | Query actual k8s cluster |
| Dynamic Policy Updates | Low | Update policies at runtime |
| Sandbox Metrics | Low | Track sandbox resource usage |
| Custom Seccomp Profiles | Low | Per-trust-level seccomp |
| Namespace Isolation | Low | K8s namespace per trust level |

## Strengths

- **Trust-based isolation** - Automatic runtime selection
- **Kubernetes-ready** - Compatible security contexts
- **Resource validation** - Prevents invalid configs
- **Graceful fallback** - Falls back if runtime unavailable
- **Local dev friendly** - Works with just runc

## Weaknesses

- **No persistence** - Config is ephemeral
- **No metrics** - Doesn't track actual resource usage
- **Static policies** - Cannot update at runtime
- **No audit** - Sandbox decisions not logged to L01
- **K8s dependency** - Full features need Kubernetes

## Best Practices

### Trust Level Selection
Choose appropriate trust levels:
- `TRUSTED`: Only for your own verified code
- `STANDARD`: Default for most agent workloads
- `UNTRUSTED`: For third-party or user-provided code
- `CONFIDENTIAL`: For PII or sensitive data processing

### Resource Limits
Set reasonable limits:
```python
# Development
ResourceLimits(cpu="2", memory="2Gi", tokens_per_hour=100000)

# Production - standard
ResourceLimits(cpu="4", memory="4Gi", tokens_per_hour=200000)

# Production - heavy workload
ResourceLimits(cpu="8", memory="16Gi", tokens_per_hour=500000)
```

### Local Development
Use minimal config:
```python
manager = SandboxManager(config={
    "available_runtimes": ["runc"],
    "default_runtime_class": "runc"
})
```

## Source Files

- Service: `platform/src/L02_runtime/services/sandbox_manager.py`
- Models: `platform/src/L02_runtime/models/agent_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.5)

## Related Services

- LocalRuntime (L02) - Local execution with sandbox
- KubernetesRuntime (L02) - K8s execution with pod specs
- AgentOrchestrator (L02) - Orchestrates agent lifecycle
- SessionService (L01) - Tracks session sandbox
- ToolRegistry (L01) - Tools run in sandbox context

---
*Generated: 2026-01-24 | Platform Services Documentation*
