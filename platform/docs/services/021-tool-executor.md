# Service 21/44: ToolExecutor

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_executor` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ToolRegistry, ToolSandbox |
| **Category** | Tool Management / Execution |

## Role in Development Environment

The **ToolExecutor** executes tools within isolated sandboxes with resource limits and timeout enforcement. It provides:
- Nested sandbox execution within agent sandboxes (BC-1 interface)
- Resource sub-allocation and enforcement (CPU, memory, timeout)
- Concurrent execution limiting per agent
- Async execution patterns for long-running tools
- Integration with ToolRegistry for tool resolution
- Sandbox lifecycle management

This is **the core tool execution engine** - when agents invoke tools like Read, Edit, or Bash, ToolExecutor manages the sandboxed execution with proper isolation and resource constraints.

## Data Model

### ToolInvokeRequest Dataclass
- `invocation_id: UUID` - Unique invocation identifier
- `tool_id: str` - Tool to invoke
- `parameters: Dict` - Tool parameters
- `agent_context: AgentContext` - Agent context (agent_did, tenant_id, session_id)
- `resource_limits: ResourceLimits` - Optional resource overrides
- `execution_options: ExecutionOptions` - Execution options (async_mode, etc.)

### ToolInvokeResponse Dataclass
- `invocation_id: UUID` - Matching invocation ID
- `status: ToolStatus` - SUCCESS, ERROR, CANCELLED, TIMEOUT
- `result: ToolResult` - Execution result (if success)
- `error: ToolError` - Error details (if failed)
- `execution_metadata: ExecutionMetadata` - Duration, resource usage
- `completed_at: datetime` - Completion timestamp

### ExecutionContext Dataclass
- `agent_did: str` - Agent decentralized identifier
- `tenant_id: str` - Tenant identifier
- `session_id: str` - Session identifier
- `parent_sandbox_id: str` - Parent agent sandbox (BC-1)
- `tool_sandbox_id: str` - Nested tool sandbox
- `sandbox_config: SandboxConfig` - Resource limits and config

### IsolationTechnology Enum
- `GVISOR` - Google gVisor (user-space kernel)
- `FIRECRACKER` - AWS Firecracker (microVMs)
- `RUNC` - Standard OCI runtime

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_cpu_limit` | 500 | Default CPU limit (millicores) |
| `default_memory_limit` | 1024 | Default memory limit (MB) |
| `default_timeout` | 30 | Default timeout (seconds) |
| `max_concurrent_tools` | 4 | Max concurrent tools per agent |
| `isolation_technology` | gvisor | Sandbox technology |
| `sandbox_base_dir` | /tmp | Base directory for sandboxes |

## API Methods

| Method | Description |
|--------|-------------|
| `execute(request)` | Execute tool invocation (BC-2 interface) |
| `get_tool(tool_name)` | Get tool definition by name |
| `list_tools()` | List all available tools |

### ToolSandbox Methods

| Method | Description |
|--------|-------------|
| `create_sandbox(execution_context)` | Create isolated sandbox |
| `execute_in_sandbox(sandbox_id, tool_id, parameters, timeout)` | Execute in sandbox |
| `destroy_sandbox(sandbox_id)` | Cleanup sandbox |
| `get_sandbox_status(sandbox_id)` | Get sandbox status |

## Use Cases in Your Workflow

### 1. Initialize Tool Executor
```python
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.tool_registry import ToolRegistry
from L03_tool_execution.services.tool_sandbox import ToolSandbox
from L03_tool_execution.models import IsolationTechnology

# Create dependencies
registry = ToolRegistry()
sandbox = ToolSandbox(
    isolation_technology=IsolationTechnology.GVISOR,
    sandbox_base_dir="/var/lib/sandboxes"
)

# Create executor
executor = ToolExecutor(
    tool_registry=registry,
    tool_sandbox=sandbox,
    default_cpu_limit=500,      # 500 millicores (0.5 CPU)
    default_memory_limit=1024,  # 1 GB
    default_timeout=30,         # 30 seconds
    max_concurrent_tools=4      # Max 4 tools per agent
)
```

### 2. Execute a Tool
```python
from L03_tool_execution.models import (
    ToolInvokeRequest,
    AgentContext,
    ResourceLimits
)
from uuid import uuid4

# Create agent context
agent_context = AgentContext(
    agent_did="did:agent:abc123",
    tenant_id="tenant-001",
    session_id="session-456",
    parent_sandbox_id="sandbox-parent-789"
)

# Create invocation request
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    parameters={
        "file_path": "/project/src/modal.tsx"
    },
    agent_context=agent_context
)

# Execute tool
response = await executor.execute(request)

if response.status == ToolStatus.SUCCESS:
    print(f"Result: {response.result.result}")
    print(f"Duration: {response.execution_metadata.duration_ms}ms")
else:
    print(f"Error: {response.error.message}")
```

### 3. Execute with Custom Resource Limits
```python
# Override default limits
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Bash",
    parameters={
        "command": "npm run build"
    },
    agent_context=agent_context,
    resource_limits=ResourceLimits(
        cpu_millicore_limit=1000,   # 1 CPU core
        memory_mb_limit=2048,       # 2 GB
        timeout_seconds=300         # 5 minutes
    )
)

response = await executor.execute(request)
```

### 4. Execute Long-Running Tool (Async Mode)
```python
from L03_tool_execution.models import ExecutionOptions

# Enable async execution for long-running tools
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Build",
    parameters={"target": "production"},
    agent_context=agent_context,
    execution_options=ExecutionOptions(
        async_mode=True  # Returns immediately with task ID
    )
)

response = await executor.execute(request)
# response contains task_id for polling
# (Note: Full async not yet implemented, falls back to sync)
```

### 5. Get Tool Definition
```python
# Retrieve tool definition
tool_def = await executor.get_tool("Read")

if tool_def:
    print(f"Tool: {tool_def.name}")
    print(f"Description: {tool_def.description}")
    print(f"Default timeout: {tool_def.default_timeout_seconds}s")
else:
    print("Tool not found")
```

### 6. Handle Execution Errors
```python
from L03_tool_execution.models import ToolStatus, ErrorCode

response = await executor.execute(request)

if response.status == ToolStatus.ERROR:
    error = response.error

    if error.code == ErrorCode.E3103.value:
        print("Timeout - tool took too long")
    elif error.code == ErrorCode.E3106.value:
        print("Concurrent limit - too many tools running")
    elif error.code == ErrorCode.E3101.value:
        print("Sandbox error - isolation failed")
    else:
        print(f"Error: {error.message}")

    # Check if retryable
    if error.retryable:
        print("This error is retryable")
```

## Service Interactions

```
+------------------+
|  ToolExecutor    | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+
|  ToolRegistry    |     |   ToolSandbox     |
|     (L03)        |     |      (L03)        |
+------------------+     +-------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
|  ToolComposer    |     |  AgentExecutor    |
|     (L03)        |     |      (L02)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **ToolRegistry (L03)**: Resolves tool definitions
- **ToolSandbox (L03)**: Creates and manages sandboxes
- **ToolComposer (L03)**: Uses for multi-tool workflows
- **AgentExecutor (L02)**: Invokes tools during agent execution
- **L11 Integration**: Provides BC-2 tool.invoke() interface

## Execution Flow

```
1. Receive Request
   ├── Validate agent context
   ├── Check concurrent limit
   └── Resolve tool definition

2. Resolve Resource Limits
   ├── Start with defaults
   ├── Apply tool manifest defaults
   ├── Apply request overrides
   └── Validate against parent (BC-1)

3. Create Sandbox
   ├── Generate sandbox ID
   ├── Create isolated workspace
   └── Apply resource limits

4. Execute in Sandbox
   ├── Write parameters to sandbox
   ├── Execute tool process
   ├── Capture result/error
   └── Enforce timeout

5. Cleanup
   ├── Destroy sandbox
   ├── Release concurrent slot
   └── Return response
```

## BC-1 Nested Sandbox Interface

Tool sandboxes are nested within agent sandboxes:

```
Agent Sandbox (L02)
├── CPU: 2000m
├── Memory: 4Gi
└── Tool Sandbox (L03)
    ├── CPU: 500m (max = parent)
    ├── Memory: 1Gi (max = parent)
    └── Execution isolated
```

Resource limits must not exceed parent sandbox limits.

## Error Codes (E3100-E3199)

| Code | Description | Retryable |
|------|-------------|-----------|
| E3101 | Sandbox creation failed | No |
| E3102 | Resource limit exceeded | No |
| E3103 | Timeout exceeded | Yes |
| E3104 | Network policy violation | No |
| E3105 | Filesystem policy violation | No |
| E3106 | Concurrent tool limit exceeded | Yes |
| E3107 | Sandbox crashed | No |
| E3108 | Tool process exit non-zero | No |

## Execution Examples

```python
# Complete tool execution workflow
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.tool_registry import ToolRegistry
from L03_tool_execution.services.tool_sandbox import ToolSandbox
from L03_tool_execution.models import *

# Setup
registry = ToolRegistry()
sandbox = ToolSandbox(isolation_technology=IsolationTechnology.GVISOR)
executor = ToolExecutor(
    tool_registry=registry,
    tool_sandbox=sandbox,
    default_timeout=30,
    max_concurrent_tools=4
)

# Create context
agent_ctx = AgentContext(
    agent_did="did:agent:test",
    tenant_id="tenant-1",
    session_id="session-1",
    parent_sandbox_id="parent-sandbox-1"
)

# Execute Read tool
read_request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    parameters={"file_path": "/project/README.md"},
    agent_context=agent_ctx
)

read_response = await executor.execute(read_request)
print(f"Read: {read_response.status}")

# Execute Edit tool
edit_request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Edit",
    parameters={
        "file_path": "/project/src/app.tsx",
        "old_string": "old code",
        "new_string": "new code"
    },
    agent_context=agent_ctx
)

edit_response = await executor.execute(edit_request)
print(f"Edit: {edit_response.status}")

# Execute Bash with higher limits
bash_request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Bash",
    parameters={"command": "npm test"},
    agent_context=agent_ctx,
    resource_limits=ResourceLimits(
        cpu_millicore_limit=1000,
        memory_mb_limit=2048,
        timeout_seconds=120
    )
)

bash_response = await executor.execute(bash_request)
print(f"Bash: {bash_response.status}")
if bash_response.result:
    print(f"Duration: {bash_response.execution_metadata.duration_ms}ms")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Request Validation | Complete |
| Concurrent Limit Check | Complete |
| Resource Limit Resolution | Complete |
| Sandbox Creation | Complete |
| Sandbox Execution | Complete (simulated) |
| Sandbox Cleanup | Complete |
| Timeout Enforcement | Complete |
| Error Handling | Complete |
| Async Execution | Partial (fallback to sync) |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| gVisor Integration | High | Real gVisor container execution |
| Firecracker Integration | Medium | MicroVM support |
| Parent Limit Validation | Medium | BC-1 constraint enforcement |
| Async Task Polling | Medium | MCP Task integration |
| Resource Metering | Low | Actual CPU/memory tracking |
| Priority Scheduling | Low | Gap G-005 implementation |

## Strengths

- **Isolation** - Nested sandbox architecture
- **Resource limits** - CPU, memory, timeout enforcement
- **Concurrent control** - Per-agent tool limits
- **Clean interface** - BC-2 tool.invoke() API
- **Error handling** - Structured error codes
- **Retryable errors** - Clear retry guidance

## Weaknesses

- **Simulated execution** - Not using real gVisor/Firecracker
- **No parent validation** - BC-1 limits not enforced
- **Async incomplete** - Falls back to sync
- **No metering** - Resource usage estimated
- **No priority** - FIFO execution only
- **Single node** - No distributed execution

## Best Practices

### Resource Limits
Set appropriate limits per tool type:
```python
# Quick read operations
ResourceLimits(cpu_millicore_limit=100, memory_mb_limit=256, timeout_seconds=10)

# Code analysis
ResourceLimits(cpu_millicore_limit=500, memory_mb_limit=1024, timeout_seconds=60)

# Build operations
ResourceLimits(cpu_millicore_limit=2000, memory_mb_limit=4096, timeout_seconds=600)
```

### Concurrent Limits
Match to system capacity:
```python
# Development (limited resources)
ToolExecutor(max_concurrent_tools=2)

# Production (more resources)
ToolExecutor(max_concurrent_tools=8)
```

### Error Handling
Handle retryable vs non-retryable:
```python
response = await executor.execute(request)

if response.status == ToolStatus.ERROR:
    if response.error.retryable:
        # Wait and retry
        await asyncio.sleep(1)
        response = await executor.execute(request)
    else:
        # Non-retryable, report error
        raise ToolExecutionError(response.error)
```

### Timeout Configuration
Match timeout to expected duration:
```python
# File read: short timeout
ToolInvokeRequest(tool_id="Read", resource_limits=ResourceLimits(timeout_seconds=10))

# npm install: long timeout
ToolInvokeRequest(tool_id="Bash", parameters={"command": "npm install"},
                  resource_limits=ResourceLimits(timeout_seconds=300))
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_executor.py`
- Sandbox: `platform/src/L03_tool_execution/services/tool_sandbox.py`
- Models: `platform/src/L03_tool_execution/models/`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3.3.2 and BC-1/BC-2 interfaces

## Related Services

- ToolRegistry (L03) - Tool definition storage
- ToolSandbox (L03) - Sandbox management
- ToolComposer (L03) - Multi-tool composition
- ResultCache (L03) - Result caching
- AgentExecutor (L02) - Agent execution
- SandboxManager (L02) - Parent sandbox

---
*Generated: 2026-01-24 | Platform Services Documentation*
