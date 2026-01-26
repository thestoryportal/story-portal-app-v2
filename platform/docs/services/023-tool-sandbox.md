# Service 23/44: ToolSandbox

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_sandbox` |
| **Status** | Fully Implemented (Development Mode) |
| **Dependencies** | None (filesystem only) |
| **Category** | Tool Management / Isolation |

## Role in Development Environment

The **ToolSandbox** provides process-level isolation for tool execution. It provides:
- Sandbox creation and lifecycle management
- Filesystem isolation with workspace directories
- Timeout enforcement for tool execution
- BC-1 nested sandbox interface (tools within agent sandboxes)
- Support for multiple isolation technologies (gVisor, Firecracker, runc)
- Resource limit enforcement (development simulation)

This is **the isolation layer for tool execution** - when tools need to run in a sandboxed environment with resource constraints and security policies, ToolSandbox creates and manages those isolated execution contexts.

**Note:** Current implementation uses process/filesystem isolation for development. Production deployments should use Kubernetes Agent Sandbox CRD with gVisor/Firecracker.

## Data Model

### IsolationTechnology Enum
- `GVISOR` - Google gVisor (user-space kernel, cloud deployments)
- `FIRECRACKER` - AWS Firecracker (microVMs, on-prem deployments)
- `RUNC` - Standard OCI runtime (minimal isolation, trusted tools only)

### NetworkPolicy Enum
- `ISOLATED` - No network access
- `RESTRICTED` - Limited egress to approved hosts
- `ALLOW_EGRESS` - Full egress allowed

### ResourceLimits Dataclass
- `cpu_millicore_limit: int` - CPU limit in millicores (default: 500)
- `memory_mb_limit: int` - Memory limit in MB (default: 1024)
- `timeout_seconds: int` - Execution timeout (default: 30)
- `disk_mb_limit: int` - Ephemeral disk limit (optional)

### FilesystemPolicy Dataclass
- `mount_paths: List[Dict]` - Allowed mount paths [{path, mode}]
- `read_only_root: bool` - Read-only root filesystem
- `temp_dir_size_mb: int` - Temp directory size limit

### NetworkPolicyConfig Dataclass
- `policy: NetworkPolicy` - Network isolation level
- `allowed_hosts: List[str]` - Approved hostnames/IPs
- `allowed_ports: List[int]` - Allowed ports
- `dns_servers: List[str]` - Custom DNS servers

### SecurityContext Dataclass
- `run_as_non_root: bool` - Run as non-root (default: true)
- `run_as_user: int` - UID to run as (default: 65534/nobody)
- `run_as_group: int` - GID to run as (default: 65534)
- `fs_group: int` - Filesystem group
- `read_only_root_filesystem: bool` - Read-only root
- `allow_privilege_escalation: bool` - Block privilege escalation
- `capabilities_drop: List[str]` - Dropped capabilities (default: ["ALL"])

### SandboxConfig Dataclass
- `isolation_technology: IsolationTechnology` - Sandbox technology
- `resource_limits: ResourceLimits` - Resource constraints
- `filesystem_policy: FilesystemPolicy` - Filesystem access rules
- `network_policy: NetworkPolicyConfig` - Network access rules
- `security_context: SecurityContext` - Security settings
- `environment_variables: Dict[str, str]` - Environment vars

### ExecutionContext Dataclass
- `agent_did: str` - Agent decentralized identifier
- `tenant_id: str` - Multi-tenant isolation
- `session_id: str` - Agent session identifier
- `parent_sandbox_id: str` - L02 parent sandbox (BC-1)
- `sandbox_config: SandboxConfig` - Complete sandbox config
- `tool_sandbox_id: str` - Created sandbox ID
- `created_at: datetime` - Creation timestamp
- `started_at: datetime` - Execution start
- `completed_at: datetime` - Execution end

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `isolation_technology` | GVISOR | Sandbox technology |
| `sandbox_base_dir` | system temp | Base directory for sandboxes |

## API Methods

| Method | Description |
|--------|-------------|
| `create_sandbox(execution_context)` | Create isolated sandbox |
| `execute_in_sandbox(sandbox_id, tool_id, parameters, timeout)` | Execute tool in sandbox |
| `destroy_sandbox(sandbox_id)` | Cleanup sandbox |
| `get_sandbox_status(sandbox_id)` | Get sandbox status |

## Use Cases in Your Workflow

### 1. Initialize Tool Sandbox
```python
from L03_tool_execution.services.tool_sandbox import ToolSandbox
from L03_tool_execution.models import IsolationTechnology

# Create sandbox manager
sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.GVISOR,
    sandbox_base_dir="/var/lib/sandboxes"
)
```

### 2. Create Sandbox for Tool Execution
```python
from L03_tool_execution.models import (
    ExecutionContext,
    SandboxConfig,
    ResourceLimits,
    FilesystemPolicy,
    NetworkPolicyConfig,
    NetworkPolicy,
    SecurityContext,
    IsolationTechnology
)

# Define resource limits
resource_limits = ResourceLimits(
    cpu_millicore_limit=500,   # 0.5 CPU cores
    memory_mb_limit=1024,      # 1 GB RAM
    timeout_seconds=30,         # 30 second timeout
    disk_mb_limit=100          # 100 MB ephemeral disk
)

# Define filesystem policy
filesystem_policy = FilesystemPolicy(
    mount_paths=[
        {"path": "/project", "mode": "ro"},
        {"path": "/tmp/work", "mode": "rw"}
    ],
    read_only_root=True,
    temp_dir_size_mb=50
)

# Define network policy
network_policy = NetworkPolicyConfig(
    policy=NetworkPolicy.RESTRICTED,
    allowed_hosts=["api.github.com", "pypi.org"],
    allowed_ports=[443],
    dns_servers=["8.8.8.8"]
)

# Define security context
security_context = SecurityContext(
    run_as_non_root=True,
    run_as_user=65534,      # nobody
    run_as_group=65534,
    read_only_root_filesystem=True,
    allow_privilege_escalation=False,
    capabilities_drop=["ALL"]
)

# Create sandbox config
sandbox_config = SandboxConfig(
    isolation_technology=IsolationTechnology.GVISOR,
    resource_limits=resource_limits,
    filesystem_policy=filesystem_policy,
    network_policy=network_policy,
    security_context=security_context,
    environment_variables={
        "HOME": "/tmp",
        "PATH": "/usr/bin:/bin"
    }
)

# Create execution context
execution_context = ExecutionContext(
    agent_did="did:agent:abc123",
    tenant_id="tenant-001",
    session_id="session-456",
    parent_sandbox_id="agent-sandbox-789",  # BC-1: Parent sandbox
    sandbox_config=sandbox_config
)

# Create sandbox
sandbox_id = await sandbox.create_sandbox(execution_context)
print(f"Created sandbox: {sandbox_id}")
```

### 3. Execute Tool in Sandbox
```python
# Execute a tool within the sandbox
result = await sandbox.execute_in_sandbox(
    sandbox_id=sandbox_id,
    tool_id="Read",
    parameters={
        "file_path": "/project/src/modal.tsx"
    },
    timeout=30
)

print(f"Status: {result['status']}")
print(f"Result: {result['result']}")
```

### 4. Get Sandbox Status
```python
# Check sandbox status
status = await sandbox.get_sandbox_status(sandbox_id)

print(f"Sandbox ID: {status['sandbox_id']}")
print(f"Status: {status['status']}")
print(f"Created: {status['created_at']}")
print(f"Agent: {status['agent_did']}")
```

### 5. Destroy Sandbox
```python
# Cleanup sandbox when done
await sandbox.destroy_sandbox(sandbox_id)
print(f"Destroyed sandbox: {sandbox_id}")

# Directory is removed, resources released
```

### 6. Use Different Isolation Technologies
```python
# gVisor for cloud deployments (default)
gvisor_sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.GVISOR
)

# Firecracker for on-prem with stronger isolation
firecracker_sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.FIRECRACKER
)

# runc for trusted tools with minimal overhead
runc_sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.RUNC
)
```

### 7. Validate BC-1 Resource Constraints
```python
from L03_tool_execution.models import ResourceLimits

# Parent agent limits (from L02)
agent_limits = ResourceLimits(
    cpu_millicore_limit=2000,
    memory_mb_limit=4096,
    timeout_seconds=300
)

# Tool limits (must be <= agent)
tool_limits = ResourceLimits(
    cpu_millicore_limit=500,
    memory_mb_limit=1024,
    timeout_seconds=30
)

# Validate nested constraint
is_valid = tool_limits.validate_against_parent(agent_limits)
print(f"Tool limits valid: {is_valid}")  # True

# Invalid tool limits
excessive_limits = ResourceLimits(
    cpu_millicore_limit=4000,  # Exceeds agent's 2000
    memory_mb_limit=8192,      # Exceeds agent's 4096
    timeout_seconds=600        # Exceeds agent's 300
)

is_valid = excessive_limits.validate_against_parent(agent_limits)
print(f"Excessive limits valid: {is_valid}")  # False
```

### 8. Handle Sandbox Errors
```python
from L03_tool_execution.models import ErrorCode, ToolExecutionError

try:
    result = await sandbox.execute_in_sandbox(
        sandbox_id="invalid-id",
        tool_id="Read",
        parameters={"file_path": "/test"},
        timeout=30
    )
except ToolExecutionError as e:
    if e.code == ErrorCode.E3101:
        print("Sandbox not found")
    elif e.code == ErrorCode.E3103:
        print("Execution timeout")
    elif e.code == ErrorCode.E3108:
        print("Tool execution failed")
```

## Service Interactions

```
+------------------+
|   ToolSandbox    | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Used by:
         |
+------------------+
|  ToolExecutor    |
|     (L03)        |
+------------------+
         |
   BC-1 Interface:
         |
+------------------+
| SandboxManager   | <--- L02 Runtime Layer (Parent)
|     (L02)        |
+------------------+
```

**Integration Points:**
- **ToolExecutor (L03)**: Uses for sandboxed tool execution
- **SandboxManager (L02)**: Parent sandbox (BC-1 nested interface)
- **AgentExecutor (L02)**: Provides agent context for sandboxes

## Sandbox Lifecycle

```
1. Create Sandbox
   ├── Generate UUID sandbox_id
   ├── Create workspace directory
   ├── Store execution context
   └── Return sandbox_id

2. Execute in Sandbox
   ├── Validate sandbox exists
   ├── Write parameters to input.json
   ├── Execute tool (simulated/real)
   ├── Enforce timeout
   └── Return result

3. Destroy Sandbox
   ├── Remove workspace directory
   ├── Delete from active_sandboxes
   └── Log cleanup
```

## BC-1 Nested Sandbox Interface

Tool sandboxes are nested within agent sandboxes:

```
Agent Sandbox (L02)
├── CPU: 2000m
├── Memory: 4Gi
├── Timeout: 300s
│
└── Tool Sandbox (L03)
    ├── CPU: 500m (max = parent)
    ├── Memory: 1Gi (max = parent)
    ├── Timeout: 30s (max = parent)
    └── Execution isolated
```

Resource validation:
```python
# Tool limits must not exceed agent limits
tool_limits.cpu_millicore_limit <= agent_limits.cpu_millicore_limit
tool_limits.memory_mb_limit <= agent_limits.memory_mb_limit
tool_limits.timeout_seconds <= agent_limits.timeout_seconds
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E3101 | Sandbox creation failed / not found | No |
| E3103 | Timeout exceeded | Yes |
| E3108 | Tool execution failed | No |

## Execution Examples

```python
# Complete sandbox workflow
from L03_tool_execution.services.tool_sandbox import ToolSandbox
from L03_tool_execution.models import (
    IsolationTechnology,
    ExecutionContext,
    SandboxConfig,
    ResourceLimits
)

# Initialize sandbox manager
sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.GVISOR,
    sandbox_base_dir="/tmp/sandboxes"
)

# Create execution context
context = ExecutionContext(
    agent_did="did:agent:test",
    tenant_id="tenant-1",
    session_id="session-1",
    parent_sandbox_id="parent-sandbox-1",
    sandbox_config=SandboxConfig(
        resource_limits=ResourceLimits(
            cpu_millicore_limit=500,
            memory_mb_limit=1024,
            timeout_seconds=60
        )
    )
)

# Create sandbox
sandbox_id = await sandbox.create_sandbox(context)
print(f"Created: {sandbox_id}")

# Execute multiple tools
tools = [
    ("Read", {"file_path": "/project/src/app.tsx"}),
    ("Analyze", {"type": "lint"}),
    ("Bash", {"command": "npm test"})
]

for tool_id, params in tools:
    result = await sandbox.execute_in_sandbox(
        sandbox_id=sandbox_id,
        tool_id=tool_id,
        parameters=params,
        timeout=30
    )
    print(f"{tool_id}: {result['status']}")

# Check status
status = await sandbox.get_sandbox_status(sandbox_id)
print(f"Active: {status['status']}")

# Cleanup
await sandbox.destroy_sandbox(sandbox_id)
print("Sandbox destroyed")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Sandbox | Complete |
| Execute in Sandbox | Complete (simulated) |
| Destroy Sandbox | Complete |
| Get Sandbox Status | Complete |
| Filesystem Isolation | Complete |
| Timeout Enforcement | Complete |
| Resource Limits Model | Complete |
| Security Context Model | Complete |
| Network Policy Model | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| gVisor Integration | High | Real gVisor container execution |
| Firecracker Integration | High | MicroVM execution support |
| runc Integration | Medium | OCI runtime execution |
| BC-1 Limit Validation | Medium | Enforce parent limits |
| Resource Metering | Medium | Actual CPU/memory tracking |
| Network Isolation | Low | Implement network policies |
| Filesystem Mounts | Low | Implement mount policies |
| Kubernetes CRD | Low | Agent Sandbox CRD integration |

## Strengths

- **Clear isolation model** - Nested sandbox architecture
- **BC-1 compliance** - Resource limit inheritance
- **Multiple technologies** - gVisor, Firecracker, runc support
- **Comprehensive config** - Resource, network, filesystem, security
- **Clean lifecycle** - Create, execute, destroy pattern
- **Development friendly** - Works without container runtime

## Weaknesses

- **Simulated execution** - Not using real isolation
- **No metering** - Resource usage not tracked
- **No network isolation** - Policies defined but not enforced
- **No filesystem mounts** - Mount policies not enforced
- **Single process** - No container runtime integration
- **No Kubernetes** - CRD not implemented

## Best Practices

### Isolation Technology Selection
Match to deployment environment:
```python
# Cloud (GKE, EKS, AKS) - gVisor
ToolSandbox(isolation_technology=IsolationTechnology.GVISOR)

# On-prem with strong isolation needs - Firecracker
ToolSandbox(isolation_technology=IsolationTechnology.FIRECRACKER)

# Trusted tools, minimal overhead - runc
ToolSandbox(isolation_technology=IsolationTechnology.RUNC)
```

### Resource Limit Configuration
Set appropriate limits per tool type:
```python
# Quick read operations
ResourceLimits(cpu_millicore_limit=100, memory_mb_limit=256, timeout_seconds=10)

# Code analysis
ResourceLimits(cpu_millicore_limit=500, memory_mb_limit=1024, timeout_seconds=60)

# Build operations
ResourceLimits(cpu_millicore_limit=2000, memory_mb_limit=4096, timeout_seconds=600)
```

### Network Policy Selection
Match to tool requirements:
```python
# File-only tools - no network
NetworkPolicyConfig(policy=NetworkPolicy.ISOLATED)

# API tools - restricted egress
NetworkPolicyConfig(
    policy=NetworkPolicy.RESTRICTED,
    allowed_hosts=["api.github.com"],
    allowed_ports=[443]
)

# Browser tools - full egress
NetworkPolicyConfig(policy=NetworkPolicy.ALLOW_EGRESS)
```

### Security Context
Use secure defaults:
```python
SecurityContext(
    run_as_non_root=True,
    run_as_user=65534,  # nobody
    read_only_root_filesystem=True,
    allow_privilege_escalation=False,
    capabilities_drop=["ALL"]
)
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_sandbox.py`
- Models: `platform/src/L03_tool_execution/models/execution_context.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3.3.2 and BC-1 interface specification

## Related Services

- ToolExecutor (L03) - Uses sandbox for tool execution
- ToolRegistry (L03) - Tool definitions with sandbox requirements
- ToolComposer (L03) - Multi-tool workflows in sandboxes
- SandboxManager (L02) - Parent agent sandbox (BC-1)
- AgentExecutor (L02) - Agent context provider

---
*Generated: 2026-01-24 | Platform Services Documentation*
