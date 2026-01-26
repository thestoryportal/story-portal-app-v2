# Service 11/44: ToolRegistry

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.tool_registry` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Data & Storage |

## Role in Development Environment

The **ToolRegistry** is a comprehensive tool management and execution tracking service. It provides:
- Tool definition and schema registration
- Tool permission management
- Detailed execution logging with rich metadata
- Resource usage tracking (CPU, memory, network)
- Multi-tenant support with session/sandbox tracking
- Real-time events via Redis pub/sub

This is **critical for agent tool use** - when agents call tools like Bash, Read, or Edit, executions can be logged here for auditing, debugging, and performance analysis.

## Data Model

### Tool Fields
- `id: UUID` - Unique tool identifier
- `name: str` - Tool name (e.g., "Bash", "Read", "WebFetch")
- `description: str` - Human-readable description
- `tool_type: ToolType` - Type classification
- `schema_def: Dict` - JSON Schema for tool parameters
- `permissions: Dict` - Required permissions to use tool
- `enabled: bool` - Whether tool is active
- `created_at: datetime` - Registration timestamp
- `updated_at: datetime` - Last update timestamp

### ToolType Enum
- `FUNCTION` - Internal function tool
- `API` - External API tool
- `EXTERNAL` - External system integration

### ToolExecution Fields (Rich Metadata)
- `id: UUID` - Unique execution ID
- `invocation_id: UUID` - Client-provided invocation ID
- `tool_id: UUID` - Reference to registered tool
- `tool_name: str` - Tool name
- `tool_version: str` - Tool version
- **Agent Context:**
  - `agent_id: UUID` - Executing agent
  - `agent_did: str` - Decentralized ID
  - `tenant_id: str` - Multi-tenant ID
  - `session_id: str` - Session context
  - `parent_sandbox_id: str` - Sandbox context
- **Execution:**
  - `input_params: Dict` - Input parameters
  - `output_result: Dict` - Execution result
  - `status: ToolExecutionStatus` - Current status
- **Error Info:**
  - `error_code: str` - Error code
  - `error_message: str` - Error message
  - `error_details: Dict` - Detailed error info
  - `retryable: bool` - Can retry?
- **Resource Metrics:**
  - `duration_ms: int` - Execution time
  - `cpu_used_millicore_seconds: int` - CPU usage
  - `memory_peak_mb: int` - Peak memory
  - `network_bytes_sent/received: int` - Network I/O
- **Options:**
  - `async_mode: bool` - Async execution
  - `priority: int` - Execution priority (1-10)
  - `idempotency_key: str` - Dedup key
  - `require_approval: bool` - Needs human approval

### ToolExecutionStatus Enum
- `PENDING` - Waiting to execute
- `RUNNING` - Currently executing
- `SUCCESS` - Completed successfully
- `ERROR` - Execution error
- `FAILED` - Complete failure
- `TIMEOUT` - Execution timed out
- `CANCELLED` - Execution cancelled
- `PERMISSION_DENIED` - Not authorized
- `PENDING_APPROVAL` - Awaiting human approval

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tools/` | Register new tool |
| `GET` | `/tools/{id}` | Get tool by ID |
| `PATCH` | `/tools/{id}` | Update tool |
| `GET` | `/tools/` | List tools |
| `POST` | `/tool-executions/` | Record execution |
| `GET` | `/tool-executions/{id}` | Get execution |
| `PATCH` | `/tool-executions/{id}` | Update execution |
| `GET` | `/tool-executions/` | List executions |

## Use Cases in Your Workflow

### 1. Register a Custom Tool
```bash
curl -X POST http://localhost:8011/tools/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CodeAnalyzer",
    "description": "Analyzes code for patterns and issues",
    "tool_type": "function",
    "schema_def": {
      "type": "object",
      "properties": {
        "file_path": {"type": "string", "description": "Path to analyze"},
        "checks": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["file_path"]
    },
    "permissions": {
      "required": ["read_files"],
      "optional": ["write_files"]
    },
    "enabled": true
  }'
```

### 2. Record Tool Execution Start
```bash
curl -X POST http://localhost:8011/tool-executions/ \
  -H "Content-Type: application/json" \
  -d '{
    "invocation_id": "990e8400-e29b-41d4-a716-446655440004",
    "tool_name": "Bash",
    "tool_version": "1.0",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "session-123",
    "input_params": {
      "command": "npm test",
      "timeout": 60000
    },
    "status": "running",
    "priority": 7,
    "timeout_seconds": 120,
    "cpu_millicore_limit": 1000,
    "memory_mb_limit": 512
  }'
```

### 3. Update Execution with Results
```bash
# Success case
curl -X PATCH http://localhost:8011/tool-executions/990e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "success",
    "output_result": {
      "stdout": "All tests passed",
      "exit_code": 0,
      "test_count": 42
    },
    "duration_ms": 15000,
    "cpu_used_millicore_seconds": 8500,
    "memory_peak_mb": 256,
    "completed_at": "2026-01-24T10:15:00Z"
  }'

# Error case
curl -X PATCH http://localhost:8011/tool-executions/990e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "error",
    "error_code": "TIMEOUT",
    "error_message": "Command timed out after 120 seconds",
    "error_details": {
      "command": "npm test",
      "timeout_seconds": 120
    },
    "retryable": true,
    "duration_ms": 120000
  }'
```

### 4. Query Execution History
```bash
# By agent
curl "http://localhost:8011/tool-executions/?agent_id=550e8400-e29b-41d4-a716-446655440000&limit=20"

# By tool
curl "http://localhost:8011/tool-executions/?tool_name=Bash&status=success"

# By session
curl "http://localhost:8011/tool-executions/?session_id=session-123"

# By tenant (multi-tenant)
curl "http://localhost:8011/tool-executions/?tenant_id=tenant-abc"
```

### 5. List Available Tools
```bash
# All tools
curl http://localhost:8011/tools/

# Only enabled tools
curl "http://localhost:8011/tools/?enabled_only=true"
```

### 6. Disable a Tool
```bash
curl -X PATCH http://localhost:8011/tools/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Service Interactions

```
+------------------+
|  ToolRegistry    | <--- L01 Data Layer (PostgreSQL)
|     (L01)        | ---> Redis (pub/sub events)
+--------+---------+
         |
   Provides tool definitions for:
         |
+------------------+     +-------------------+     +------------------+
| ExecutionEngine  |     |  SandboxManager   |     | PermissionSystem |
|     (L05)        |     |      (L02)        |     |      (L03)       |
+------------------+     +-------------------+     +------------------+
         |
   Logs executions for:
         |
+------------------+     +-------------------+     +------------------+
| MetricsEngine    |     |   AuditService    |     |  AlertManager    |
|     (L06)        |     |      (L01)        |     |      (L06)       |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **ExecutionEngine (L05)**: Fetches tool definitions, logs executions
- **SandboxManager (L02)**: Tool executions run in sandboxes
- **PermissionSystem (L03)**: Checks tool permissions
- **MetricsEngine (L06)**: Aggregates execution metrics
- **AuditService**: Execution logs for compliance

## Redis Events

ToolRegistry publishes events on tool and execution lifecycle:

```python
# Tool registered
{
    "event_type": "tool.registered",
    "aggregate_type": "tool",
    "aggregate_id": "tool-uuid",
    "payload": {"name": "CodeAnalyzer", "tool_type": "function"}
}

# Execution created
{
    "event_type": "tool.execution.created",
    "aggregate_type": "tool_execution",
    "aggregate_id": "invocation-uuid",
    "payload": {
        "tool_name": "Bash",
        "agent_id": "agent-uuid",
        "status": "running",
        "session_id": "session-123"
    }
}

# Execution updated
{
    "event_type": "tool.execution.updated",
    "aggregate_type": "tool_execution",
    "aggregate_id": "invocation-uuid",
    "payload": {
        "tool_name": "Bash",
        "status": "success",
        "duration_ms": 15000
    }
}
```

## Execution Examples

```bash
# Register a tool
curl -X POST http://localhost:8011/tools/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DatabaseQuery",
    "description": "Execute database queries",
    "tool_type": "api",
    "schema_def": {
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "database": {"type": "string"}
      }
    },
    "permissions": {"required": ["db_read"]},
    "enabled": true
  }'

# Get tool
curl http://localhost:8011/tools/660e8400-e29b-41d4-a716-446655440001

# Update tool schema
curl -X PATCH http://localhost:8011/tools/660e8400-e29b-41d4-a716-446655440001 \
  -d '{"schema_def": {...}}'

# Record execution
curl -X POST http://localhost:8011/tool-executions/ \
  -d '{
    "invocation_id": "...",
    "tool_name": "DatabaseQuery",
    "agent_id": "...",
    "input_params": {"query": "SELECT * FROM users"}
  }'

# Update execution status
curl -X PATCH http://localhost:8011/tool-executions/990e8400-e29b-41d4-a716-446655440004 \
  -d '{"status": "success", "output_result": {...}}'

# List executions with filters
curl "http://localhost:8011/tool-executions/?tool_name=Bash&status=error&limit=10"
```

## Tool Schema Examples

### File Operation Tool
```json
{
  "name": "FileWriter",
  "schema_def": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "File path"},
      "content": {"type": "string", "description": "Content to write"},
      "mode": {"type": "string", "enum": ["overwrite", "append"]}
    },
    "required": ["path", "content"]
  },
  "permissions": {"required": ["write_files"]}
}
```

### API Integration Tool
```json
{
  "name": "GitHubAPI",
  "tool_type": "api",
  "schema_def": {
    "type": "object",
    "properties": {
      "endpoint": {"type": "string"},
      "method": {"type": "string", "enum": ["GET", "POST", "PUT"]},
      "body": {"type": "object"}
    },
    "required": ["endpoint"]
  },
  "permissions": {"required": ["network_access", "github_token"]}
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Register Tool | Complete |
| Get Tool | Complete |
| Update Tool | Complete |
| List Tools | Complete |
| Enabled Filter | Complete |
| Record Execution | Complete |
| Get Execution | Complete |
| Update Execution | Complete |
| List Executions | Complete |
| Multi-Filter Query | Complete |
| Redis Events | Complete |
| Resource Tracking | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Delete Tool | Medium | Remove tools (soft delete?) |
| Tool Versioning | Medium | Track schema versions |
| Execution Stats | Medium | Aggregate execution metrics |
| Tool Categories | Low | Group tools by category |
| Dependency Graph | Low | Track tool dependencies |
| Rate Limiting | Low | Per-tool rate limits |
| Approval Workflow | Low | Human approval flow |

## Strengths

- **Rich execution metadata** - Full context for debugging
- **Resource tracking** - CPU, memory, network metrics
- **Multi-tenant support** - tenant_id, session_id tracking
- **Redis events** - Real-time execution notifications
- **Flexible filtering** - Query by agent, tool, session, status
- **Schema storage** - Tool definitions with JSON Schema
- **Permission model** - Required/optional permissions

## Weaknesses

- **No tool deletion** - Cannot remove deprecated tools
- **No versioning** - Schema changes overwrite
- **No aggregations** - Must compute stats manually
- **No rate limiting** - No built-in throttling
- **No approval workflow** - require_approval flag not enforced

## Best Practices

### Tool Registration
Include complete schemas:
```json
{
  "schema_def": {
    "type": "object",
    "properties": {...},
    "required": [...],
    "additionalProperties": false
  }
}
```

### Execution Logging
Always record start and completion:
```python
# Start
execution = await tool_registry.record_execution(
    ToolExecutionCreate(
        invocation_id=uuid4(),
        tool_name="Bash",
        agent_id=agent_id,
        status=ToolExecutionStatus.RUNNING,
        input_params=params
    )
)

# Complete
await tool_registry.update_execution(
    execution.invocation_id,
    ToolExecutionUpdate(
        status=ToolExecutionStatus.SUCCESS,
        output_result=result,
        duration_ms=elapsed_ms
    )
)
```

### Error Handling
Include retry information:
```json
{
  "status": "error",
  "error_code": "RATE_LIMITED",
  "error_message": "Too many requests",
  "retryable": true,
  "error_details": {"retry_after_seconds": 60}
}
```

## Source Files

- Service: `platform/src/L01_data_layer/services/tool_registry.py`
- Models: `platform/src/L01_data_layer/models/tool.py`
- Routes: (likely in `routers/tools.py`)

## Related Services

- ExecutionEngine (L05) - Runs tools, logs executions
- SandboxManager (L02) - Isolated tool execution
- PermissionSystem (L03) - Permission enforcement
- MetricsEngine (L06) - Execution analytics
- EventStore (L01) - Execution events persisted

---
*Generated: 2026-01-24 | Platform Services Documentation*
