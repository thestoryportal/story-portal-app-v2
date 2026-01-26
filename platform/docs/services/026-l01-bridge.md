# Service 26/44: L01Bridge (L03Bridge)

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.l01_bridge` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L01 Data Layer (HTTP API) |
| **Category** | Tool Management / Cross-Layer Bridge |

## Role in Development Environment

The **L01Bridge** (implemented as L03Bridge) connects L03 Tool Execution to L01 Data Layer for persistent tool execution tracking. It provides:
- Recording tool invocations when execution starts
- Updating execution records with results, errors, and metadata
- Tracking resource usage, documents accessed, and checkpoints
- Cross-layer access to tool execution history
- Audit trail and analytics foundation

This is **the persistence layer for tool executions** - when tools are invoked, L01Bridge ensures the execution is recorded in L01 for history, analytics, and cross-layer access.

## Data Model

Uses L03 models from `tool_result.py`:

### ToolInvokeRequest (key fields)
- `invocation_id: UUID` - Unique invocation identifier
- `tool_id: str` - Tool identifier
- `tool_version: str` - Tool version
- `agent_context: AgentContext` - Agent identity and sandbox
- `parameters: Dict` - Tool parameters
- `resource_limits: ResourceLimits` - CPU, memory, timeout
- `execution_options: ExecutionOptions` - Priority, async mode, idempotency

### ToolInvokeResponse (key fields)
- `invocation_id: UUID` - Matching invocation ID
- `status: ToolStatus` - SUCCESS, ERROR, TIMEOUT, etc.
- `result: ToolResult` - Execution result
- `error: ToolError` - Error details (if failed)
- `execution_metadata: ExecutionMetadata` - Duration, resource usage
- `checkpoint_ref: str` - Final checkpoint ID

### ToolStatus Enum
- `PENDING` - Queued for execution
- `RUNNING` - Currently executing
- `SUCCESS` - Completed successfully
- `ERROR` - Failed with error
- `TIMEOUT` - Exceeded timeout
- `CANCELLED` - Cancelled by client
- `PERMISSION_DENIED` - Insufficient permissions
- `PENDING_APPROVAL` - Waiting for approval

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `l01_base_url` | "http://localhost:8002" | L01 Data Layer API endpoint |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize bridge (async setup) |
| `record_invocation_start(request)` | Record execution start in L01 |
| `update_invocation_status(invocation_id, status)` | Update execution status |
| `record_invocation_result(response, started_at)` | Record execution result |
| `get_execution_history(invocation_id)` | Get execution record from L01 |
| `cleanup()` | Close connections |

## Use Cases in Your Workflow

### 1. Initialize L01 Bridge
```python
from L03_tool_execution.services.l01_bridge import L03Bridge

bridge = L03Bridge(
    l01_base_url="http://localhost:8002"
)

await bridge.initialize()
# L03Bridge initialized with base_url=http://localhost:8002
```

### 2. Record Tool Invocation Start
```python
from L03_tool_execution.models import (
    ToolInvokeRequest,
    AgentContext,
    ResourceLimits,
    ExecutionOptions
)
from uuid import uuid4

request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Read",
    tool_version="1.0.0",
    agent_context=AgentContext(
        agent_did="did:agent:abc123",
        tenant_id="tenant-001",
        session_id="session-456",
        parent_sandbox_id="sandbox-789"
    ),
    parameters={"file_path": "/project/src/modal.tsx"},
    resource_limits=ResourceLimits(
        cpu_millicore_limit=500,
        memory_mb_limit=1024,
        timeout_seconds=30
    ),
    execution_options=ExecutionOptions(
        async_mode=False,
        priority=5,
        idempotency_key="read-modal-v1"
    )
)

# Record start in L01
success = await bridge.record_invocation_start(request)
print(f"Recorded start: {success}")
# Creates record in L01 with status="pending"
```

### 3. Update Invocation Status
```python
from L03_tool_execution.models import ToolStatus

# Update status to running
await bridge.update_invocation_status(
    invocation_id=request.invocation_id,
    status=ToolStatus.RUNNING
)

# Later, update to success/error
await bridge.update_invocation_status(
    invocation_id=request.invocation_id,
    status=ToolStatus.SUCCESS
)
```

### 4. Record Invocation Result
```python
from L03_tool_execution.models import (
    ToolInvokeResponse,
    ToolResult,
    ExecutionMetadata,
    ToolStatus
)
from datetime import datetime

# After tool execution completes
response = ToolInvokeResponse(
    invocation_id=request.invocation_id,
    status=ToolStatus.SUCCESS,
    result=ToolResult(
        result={"content": "file contents...", "line_count": 150},
        result_type="object"
    ),
    execution_metadata=ExecutionMetadata(
        duration_ms=125,
        cpu_used_millicore_seconds=50,
        memory_peak_mb=128,
        documents_accessed=[
            {"document_id": "spec-v1", "version": "1.0.0"}
        ],
        checkpoints_created=[]
    ),
    completed_at=datetime.utcnow()
)

# Record result in L01
success = await bridge.record_invocation_result(
    response=response,
    started_at=request.created_at
)
print(f"Recorded result: {success}")
```

### 5. Record Error Result
```python
from L03_tool_execution.models import ToolError

# Record failed execution
error_response = ToolInvokeResponse(
    invocation_id=request.invocation_id,
    status=ToolStatus.ERROR,
    error=ToolError(
        code="E3001",
        message="Tool not found",
        details={"tool_id": "InvalidTool"},
        retryable=False
    ),
    execution_metadata=ExecutionMetadata(
        duration_ms=10
    ),
    completed_at=datetime.utcnow()
)

await bridge.record_invocation_result(error_response)
# Records error_code, error_message, error_details, retryable in L01
```

### 6. Get Execution History
```python
# Retrieve execution record from L01
history = await bridge.get_execution_history(request.invocation_id)

if history:
    print(f"Tool: {history['tool_name']}")
    print(f"Status: {history['status']}")
    print(f"Duration: {history.get('duration_ms')}ms")
    print(f"Error: {history.get('error_message')}")
else:
    print("Execution record not found")
```

### 7. Integration with ToolExecutor
```python
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.l01_bridge import L03Bridge

class TrackedToolExecutor:
    def __init__(self, executor: ToolExecutor, bridge: L03Bridge):
        self.executor = executor
        self.bridge = bridge

    async def execute(self, request: ToolInvokeRequest):
        started_at = datetime.utcnow()

        # Record start
        await self.bridge.record_invocation_start(request)

        # Update to running
        await self.bridge.update_invocation_status(
            request.invocation_id,
            ToolStatus.RUNNING
        )

        try:
            # Execute tool
            response = await self.executor.execute(request)

            # Record result
            await self.bridge.record_invocation_result(
                response,
                started_at=started_at
            )

            return response

        except Exception as e:
            # Record error
            error_response = ToolInvokeResponse(
                invocation_id=request.invocation_id,
                status=ToolStatus.ERROR,
                error=ToolError(
                    code="E3999",
                    message=str(e),
                    retryable=False
                ),
                completed_at=datetime.utcnow()
            )
            await self.bridge.record_invocation_result(
                error_response,
                started_at=started_at
            )
            raise
```

### 8. Disable Bridge (for testing)
```python
# Disable L01 recording (useful for unit tests)
bridge.enabled = False

# All operations return False but don't fail
await bridge.record_invocation_start(request)  # Returns False
await bridge.record_invocation_result(response)  # Returns False
```

## Service Interactions

```
+------------------+
|   L03Bridge      | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   HTTP API calls:
         |
+------------------+
|   L01 Data Layer |
|   (PostgreSQL)   |
+------------------+
         |
   Uses shared client:
         |
+------------------+
|   L01Client      |
| (shared/clients) |
+------------------+
```

**Integration Points:**
- **L01 Data Layer**: Stores tool execution records
- **L01Client**: Shared HTTP client for L01 API
- **ToolExecutor (L03)**: Records executions via bridge
- **ToolComposer (L03)**: Records composition results

## Data Flow

```
1. Tool Invocation Start
   ├── Extract agent_context, resource_limits, execution_options
   ├── Call L01Client.record_tool_execution()
   └── Store with status="pending"

2. Status Updates
   ├── Call L01Client.update_tool_execution()
   └── Update status to "running", "success", "error", etc.

3. Result Recording
   ├── Extract result, error, execution_metadata
   ├── Convert documents_accessed to list of IDs
   ├── Convert checkpoints_created to list of IDs
   ├── Call L01Client.update_tool_execution()
   └── Store complete execution record

4. History Retrieval
   ├── Call L01Client.get_tool_execution_by_invocation()
   └── Return execution record dict
```

## L01 Record Fields

Fields stored in L01 tool_executions table:

| Field | Source | Description |
|-------|--------|-------------|
| `invocation_id` | request | Unique invocation UUID |
| `tool_name` | request.tool_id | Tool identifier |
| `tool_version` | request | Version string |
| `agent_did` | agent_context | Agent DID |
| `tenant_id` | agent_context | Tenant ID |
| `session_id` | agent_context | Session ID |
| `parent_sandbox_id` | agent_context | Parent sandbox |
| `input_params` | request.parameters | Tool parameters |
| `status` | response.status | Execution status |
| `output_result` | response.result | Tool result |
| `error_code` | response.error | Error code |
| `error_message` | response.error | Error message |
| `error_details` | response.error | Error details |
| `retryable` | response.error | Retry flag |
| `duration_ms` | execution_metadata | Duration |
| `cpu_used_millicore_seconds` | execution_metadata | CPU usage |
| `memory_peak_mb` | execution_metadata | Memory usage |
| `network_bytes_sent` | execution_metadata | Network TX |
| `network_bytes_received` | execution_metadata | Network RX |
| `documents_accessed` | execution_metadata | Document IDs |
| `checkpoints_created` | execution_metadata | Checkpoint IDs |
| `checkpoint_ref` | response | Final checkpoint |
| `started_at` | provided | Start timestamp |
| `completed_at` | response | End timestamp |

## Error Handling

All bridge operations are fault-tolerant:
- On failure, operations log error and return `False`
- Tool execution continues even if recording fails
- Bridge can be disabled via `enabled = False`

```python
try:
    await self.l01_client.record_tool_execution(...)
    return True
except Exception as e:
    logger.error(f"Failed to record tool invocation in L01: {e}")
    return False  # Don't fail execution
```

## Execution Examples

```python
# Complete L01 bridge workflow
bridge = L03Bridge(l01_base_url="http://localhost:8002")
await bridge.initialize()

# Create request
request = ToolInvokeRequest(
    invocation_id=uuid4(),
    tool_id="Analyze",
    tool_version="2.0.0",
    agent_context=AgentContext(
        agent_did="did:agent:test",
        tenant_id="tenant-1",
        session_id="session-1"
    ),
    parameters={"path": "/project/src"},
    execution_options=ExecutionOptions(priority=7)
)

# Record start
await bridge.record_invocation_start(request)

# Update to running
await bridge.update_invocation_status(
    request.invocation_id,
    ToolStatus.RUNNING
)

# Simulate execution
result = {"files_analyzed": 42, "issues_found": 3}

# Record result
response = ToolInvokeResponse(
    invocation_id=request.invocation_id,
    status=ToolStatus.SUCCESS,
    result=ToolResult(result=result),
    execution_metadata=ExecutionMetadata(
        duration_ms=5000,
        cpu_used_millicore_seconds=2500,
        memory_peak_mb=512
    ),
    completed_at=datetime.utcnow()
)

await bridge.record_invocation_result(response)

# Query history
history = await bridge.get_execution_history(request.invocation_id)
print(f"Execution: {history['tool_name']} - {history['status']}")
print(f"Duration: {history['duration_ms']}ms")

# Cleanup
await bridge.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize | Complete |
| Record Invocation Start | Complete |
| Update Invocation Status | Complete |
| Record Invocation Result | Complete |
| Get Execution History | Complete |
| Cleanup | Complete |
| Error Handling | Complete |
| Disable Flag | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Event Publishing | Medium | Publish tool execution events |
| Batch Recording | Low | Record multiple invocations at once |
| Metrics Export | Low | Prometheus metrics for L01 calls |
| Retry Logic | Low | Retry failed L01 API calls |
| Circuit Breaker | Low | Protect against L01 outages |

## Strengths

- **Fault-tolerant** - Failures don't break execution
- **Complete tracking** - All execution metadata captured
- **Cross-layer access** - L01 stores for all layers
- **Audit trail** - Complete history of tool usage
- **Simple API** - Start, update, result, get

## Weaknesses

- **No retries** - Failed recordings not retried
- **No batching** - One API call per operation
- **No events** - Not publishing to event stream
- **Synchronous** - Waits for L01 response
- **No circuit breaker** - May slow execution if L01 is slow

## Best Practices

### Integration Pattern
Wrap executor with bridge:
```python
# Create tracked executor
tracked = TrackedToolExecutor(executor, bridge)

# All executions automatically recorded
response = await tracked.execute(request)
```

### Error Recording
Always record errors with full context:
```python
error_response = ToolInvokeResponse(
    invocation_id=request.invocation_id,
    status=ToolStatus.ERROR,
    error=ToolError(
        code="E3103",  # Specific error code
        message="Timeout exceeded",
        details={
            "timeout": 30,
            "elapsed": 45,
            "tool_id": request.tool_id
        },
        retryable=True
    ),
    completed_at=datetime.utcnow()
)
```

### Testing Without L01
Disable bridge for unit tests:
```python
bridge = L03Bridge()
bridge.enabled = False  # All calls return False but don't fail
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/l01_bridge.py`
- Models: `platform/src/L03_tool_execution/models/tool_result.py`
- Client: `platform/shared/clients/l01_client.py`
- Spec: Cross-layer communication patterns

## Related Services

- ToolExecutor (L03) - Uses bridge for execution tracking
- ToolComposer (L03) - Uses for composition tracking
- L01 Data Layer - Stores execution records
- MetricsEngine (L06) - Aggregates execution metrics
- AuditLog (L07) - Uses execution records for audit

---
*Generated: 2026-01-24 | Platform Services Documentation*
