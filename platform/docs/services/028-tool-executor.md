# Service 28/44: ToolExecutor

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_executor` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ToolRegistry (L03), ToolSandbox (L03) |
| **Category** | Tool Management / Execution Engine |

## Role in Development Environment

The **ToolExecutor** is the core execution engine for tools within isolated sandboxes. It provides:
- BC-2 `tool.invoke()` interface for L11 Integration Layer
- Nested sandbox execution within agent sandboxes (BC-1)
- Resource sub-allocation and enforcement
- Concurrent execution limits per agent
- Sync and async execution patterns (Gap G-004)
- Priority scheduling (Gap G-005)
- Timeout enforcement

This is **the execution engine for all tool invocations** - when agents or users invoke tools, ToolExecutor manages the entire lifecycle from validation through sandboxed execution to result delivery.

## Data Model

### ToolInvokeRequest (key fields)
- `invocation_id: UUID` - Unique invocation identifier
- `tool_id: str` - Tool identifier
- `tool_version: str` - Version (or "latest")
- `parameters: Dict` - Tool parameters
- `agent_context: AgentContext` - Agent identity and sandbox
- `resource_limits: ResourceLimits` - CPU, memory, timeout overrides
- `execution_options: ExecutionOptions` - Async mode, priority

### ToolInvokeResponse (key fields)
- `invocation_id: UUID` - Matching invocation ID
- `status: ToolStatus` - SUCCESS, ERROR, TIMEOUT, etc.
- `result: ToolResult` - Execution result
- `error: ToolError` - Error details (if failed)
- `execution_metadata: ExecutionMetadata` - Duration, resource usage
- `completed_at: datetime` - Completion timestamp

### ToolStatus Enum
- `SUCCESS` - Completed successfully
- `ERROR` - Failed with error
- `TIMEOUT` - Exceeded timeout
- `CANCELLED` - Cancelled by client
- `PENDING` - Waiting for execution
- `RUNNING` - Currently executing

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_cpu_limit` | 500 | Default CPU limit (millicores) |
| `default_memory_limit` | 1024 | Default memory limit (MB) |
| `default_timeout` | 30 | Default timeout (seconds) |
| `max_concurrent_tools` | 4 | Max concurrent executions per agent |

## API Methods

| Method | Description |
|--------|-------------|
| `execute(request)` | Execute tool invocation (BC-2 interface) |
| `get_tool(tool_name)` | Get tool definition by name |
| `list_tools()` | List all available tools |

## Use Cases in Your Workflow

### 1. Initialize Tool Executor
```python
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.tool_registry import ToolRegistry
from L03_tool_execution.services.tool_sandbox import ToolSandbox

# Create dependencies
registry = ToolRegistry()
sandbox = ToolSandbox()

# Create executor
executor = ToolExecutor(
    tool_registry=registry,
    tool_sandbox=sandbox,
    default_cpu_limit=500,      # 0.5 CPU cores
    default_memory_limit=1024,  # 1 GB RAM
    default_timeout=30,         # 30 seconds
    max_concurrent_tools=4      # 4 concurrent per agent
)
```

### 2. Execute Tool (BC-2 Interface)
```python
from L03_tool_execution.models import (
    ToolInvokeRequest,
    AgentContext,
    ResourceLimits
)
from uuid import uuid4

# Create invocation request
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    parameters={"file_path": "/project/src/modal.tsx"},
    agent_context=AgentContext(
        agent_did="did:agent:abc123",
        tenant_id="tenant-001",
        session_id="session-456",
        parent_sandbox_id="agent-sandbox-789"
    )
)

# Execute
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
    tool_id="Analyze",
    parameters={"path": "/project/src"},
    agent_context=agent_context,
    resource_limits=ResourceLimits(
        cpu_millicore_limit=2000,  # 2 CPU cores
        memory_mb_limit=4096,      # 4 GB RAM
        timeout_seconds=300        # 5 minutes
    )
)

response = await executor.execute(request)
```

### 4. Async Execution (Gap G-004)
```python
from L03_tool_execution.models import ExecutionOptions

# Enable async mode for long-running tools
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Build",
    parameters={"project_path": "/project"},
    agent_context=agent_context,
    execution_options=ExecutionOptions(
        async_mode=True,  # Return immediately
        priority=7        # Higher priority (1-10)
    )
)

# Returns immediately with task info
response = await executor.execute(request)
task_id = f"task:{request.tool_id}:{request.invocation_id}"
# Poll for completion...
```

### 5. Get Tool Definition
```python
# Get tool for L02 integration
tool = await executor.get_tool("Read")

if tool:
    print(f"Tool: {tool.tool_id}")
    print(f"Category: {tool.category}")
    print(f"Parameters: {tool.parameter_schema}")
else:
    print("Tool not found")
```

### 6. List Available Tools
```python
# List all tools
tools = await executor.list_tools()

for tool in tools:
    print(f"- {tool.tool_id}: {tool.description}")
```

### 7. Handle Execution Errors
```python
from L03_tool_execution.models import ErrorCode, ToolStatus

response = await executor.execute(request)

if response.status == ToolStatus.ERROR:
    error = response.error

    if error.code == ErrorCode.E3001.value:
        print("Tool not found")
    elif error.code == ErrorCode.E3103.value:
        print("Execution timeout - try increasing timeout")
    elif error.code == ErrorCode.E3106.value:
        print("Too many concurrent tools - wait and retry")
    elif error.code == ErrorCode.E3108.value:
        print(f"Execution failed: {error.message}")

    if error.retryable:
        # Retry logic
        pass
```

### 8. Concurrent Execution Limits
```python
# Executor tracks per-agent concurrency
# Default: max 4 concurrent tools per agent

# This will work (4 concurrent)
tasks = [
    executor.execute(create_request("Read", {"file": "/a.txt"})),
    executor.execute(create_request("Read", {"file": "/b.txt"})),
    executor.execute(create_request("Read", {"file": "/c.txt"})),
    executor.execute(create_request("Read", {"file": "/d.txt"})),
]
results = await asyncio.gather(*tasks)

# 5th concurrent tool would raise E3106
```

## Service Interactions

```
+------------------+
|   ToolExecutor   | <--- L03 Tool Execution Layer
|      (L03)       |
+--------+---------+
         |
   Uses:
         |
+------------------+     +------------------+
|   ToolRegistry   |     |   ToolSandbox    |
|      (L03)       |     |      (L03)       |
+------------------+     +------------------+
         |                        |
   Tool definitions          Sandbox execution
         |                        |
+------------------+     +------------------+
| L11 Integration  |     |  L02 Runtime     |
|     Layer        |     | (Parent Sandbox) |
+------------------+     +------------------+
```

**Integration Points:**
- **ToolRegistry (L03)**: Retrieves tool definitions
- **ToolSandbox (L03)**: Creates sandboxes and executes tools
- **L11 Integration Layer**: Consumes BC-2 `tool.invoke()` interface
- **L02 Runtime Layer**: Parent sandbox (BC-1 nested sandboxes)

## Execution Flow

```
1. execute(request)
   ├── Check concurrent limit (per agent)
   ├── Get tool definition from registry
   ├── Resolve resource limits (BC-1)
   └── Build execution context

2. Resource Limit Resolution (Priority)
   ├── 1. Request overrides (highest)
   ├── 2. Tool manifest defaults
   └── 3. Executor defaults (lowest)

3. Execution Mode Selection
   ├── async_mode=True → _execute_async()
   └── async_mode=False → _execute_sync()

4. _execute_sync()
   ├── Create sandbox
   ├── Execute in sandbox (with timeout)
   ├── Build response with metadata
   ├── Destroy sandbox (finally)
   └── Release concurrent slot (finally)

5. _execute_async() (Gap G-004)
   ├── Generate task ID
   ├── Create MCP Task (TODO)
   └── Return immediately with task info
```

## BC-1 Nested Sandbox Interface

Tool sandboxes are nested within agent sandboxes:

```
Agent Sandbox (L02)
├── CPU: 2000m (parent limit)
├── Memory: 4Gi (parent limit)
│
└── Tool Sandbox (L03)
    ├── CPU: min(request, manifest, default, parent)
    ├── Memory: min(request, manifest, default, parent)
    └── Execution isolated
```

Resource limit validation:
```python
# Resolved limits must not exceed parent sandbox
tool_limits.cpu <= parent_limits.cpu
tool_limits.memory <= parent_limits.memory
tool_limits.timeout <= parent_limits.timeout
```

## BC-2 Tool.invoke() Interface

The `execute()` method implements BC-2:

```python
# L11 Integration Layer uses this interface
response = await tool_executor.execute(ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    parameters={...},
    agent_context=AgentContext(...)
))
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E3001 | Tool not found | No |
| E3101 | Agent context required | No |
| E3103 | Execution timeout | Yes |
| E3106 | Concurrent limit exceeded | Yes |
| E3108 | Tool execution failed | Depends |

## Execution Examples

```python
# Complete tool execution workflow
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.tool_registry import ToolRegistry
from L03_tool_execution.services.tool_sandbox import ToolSandbox
from L03_tool_execution.models import (
    ToolInvokeRequest,
    AgentContext,
    ResourceLimits,
    ExecutionOptions,
    ToolStatus
)
from uuid import uuid4

# Initialize
registry = ToolRegistry()
sandbox = ToolSandbox()
executor = ToolExecutor(
    tool_registry=registry,
    tool_sandbox=sandbox,
    default_cpu_limit=500,
    default_memory_limit=1024,
    default_timeout=30,
    max_concurrent_tools=4
)

# Agent context (from L02)
agent_context = AgentContext(
    agent_did="did:agent:test",
    tenant_id="tenant-1",
    session_id="session-1",
    parent_sandbox_id="parent-sandbox-1"
)

# 1. Simple execution
simple_request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    parameters={"file_path": "/project/README.md"},
    agent_context=agent_context
)

response = await executor.execute(simple_request)
print(f"Status: {response.status}")
print(f"Duration: {response.execution_metadata.duration_ms}ms")

# 2. Execution with custom limits
heavy_request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Build",
    parameters={"target": "all"},
    agent_context=agent_context,
    resource_limits=ResourceLimits(
        cpu_millicore_limit=2000,
        memory_mb_limit=4096,
        timeout_seconds=600
    ),
    execution_options=ExecutionOptions(
        priority=8  # High priority
    )
)

response = await executor.execute(heavy_request)

# 3. Parallel execution (within limits)
import asyncio

parallel_requests = [
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": f"/project/file{i}.txt"},
        agent_context=agent_context
    )
    for i in range(4)  # Max concurrent is 4
]

responses = await asyncio.gather(*[
    executor.execute(req) for req in parallel_requests
])

for i, resp in enumerate(responses):
    print(f"Request {i}: {resp.status}")

# 4. Error handling
try:
    response = await executor.execute(request)
    if response.status == ToolStatus.ERROR:
        print(f"Error: {response.error.code} - {response.error.message}")
        if response.error.retryable:
            print("Retryable - try again")
except ToolExecutionError as e:
    print(f"Critical error: {e.code} - {e.message}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| execute() (BC-2) | Complete |
| Concurrent Limits | Complete |
| Resource Resolution | Complete |
| Execution Context | Complete |
| Sync Execution | Complete |
| Async Execution | Partial (fallback to sync) |
| get_tool() | Complete |
| list_tools() | Partial |
| Timeout Enforcement | Complete |
| Error Handling | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Async Execution | High | Full MCP Task implementation (G-004) |
| Priority Scheduling | High | Priority queue (G-005) |
| BC-1 Validation | Medium | Validate against parent limits |
| Result Schema Validation | Medium | Validate against manifest (G-010) |
| list_tools() | Medium | Full implementation |
| Metrics Export | Low | Prometheus metrics |
| Retry Logic | Low | Automatic retry for retryable errors |

## Strengths

- **BC-2 compliant** - Full tool.invoke() interface
- **Sandboxed execution** - All tools run isolated
- **Concurrent limits** - Per-agent protection
- **Resource management** - Priority-based limit resolution
- **Clean lifecycle** - Create, execute, destroy pattern
- **Comprehensive errors** - Detailed error codes and messages

## Weaknesses

- **Async incomplete** - Falls back to sync
- **No priority queue** - Priority not enforced yet
- **No BC-1 validation** - Parent limits not checked
- **No result validation** - Schema validation missing
- **No retry logic** - Manual retry required
- **No metrics** - Execution stats not exported

## Best Practices

### Resource Limit Configuration
Set limits based on tool type:
```python
# Quick reads - minimal resources
ResourceLimits(cpu_millicore_limit=100, memory_mb_limit=256, timeout_seconds=10)

# Analysis tools - moderate resources
ResourceLimits(cpu_millicore_limit=500, memory_mb_limit=1024, timeout_seconds=60)

# Build tools - heavy resources
ResourceLimits(cpu_millicore_limit=2000, memory_mb_limit=4096, timeout_seconds=600)
```

### Error Handling
Always check response status:
```python
response = await executor.execute(request)

if response.status == ToolStatus.SUCCESS:
    handle_success(response.result)
elif response.status == ToolStatus.TIMEOUT:
    handle_timeout(request)
elif response.error.retryable:
    await retry_execution(request)
else:
    handle_permanent_failure(response.error)
```

### Concurrent Execution
Stay within limits:
```python
# Batch execution respecting limits
MAX_CONCURRENT = 4
for batch in chunks(requests, MAX_CONCURRENT):
    responses = await asyncio.gather(*[
        executor.execute(req) for req in batch
    ])
    process_responses(responses)
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_executor.py`
- Models: `platform/src/L03_tool_execution/models/tool_result.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3.3.2, BC-1, BC-2 interface specifications

## Related Services

- ToolRegistry (L03) - Tool definitions and discovery
- ToolSandbox (L03) - Sandbox creation and execution
- ToolComposer (L03) - Multi-tool workflows
- ResultCache (L03) - Caches execution results
- L01Bridge (L03) - Records execution history
- SandboxManager (L02) - Parent agent sandbox (BC-1)
- L11 Integration Layer - Consumes BC-2 interface

---
*Generated: 2026-01-24 | Platform Services Documentation*
