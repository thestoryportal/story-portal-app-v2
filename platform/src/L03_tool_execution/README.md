# L03 Tool Execution Layer

**Version:** 1.0.0
**Specification:** tool-execution-layer-specification-v1.2-ASCII.md
**Status:** Implementation Complete
**Date:** 2026-01-14

## Overview

The L03 Tool Execution Layer provides secure, isolated execution of tools invoked by AI agents with comprehensive permission enforcement, result caching, and MCP integration.

## Key Features

- **Tool Registry**: PostgreSQL + pgvector storage with Ollama semantic search
- **Nested Sandbox Execution**: BC-1 compliant sandboxing with resource limits
- **Result Caching**: Redis-backed caching with TTL and idempotency support
- **MCP Integration**: Document Bridge (Phase 15) and State Bridge (Phase 16)
- **Tool Composition**: Sequential chaining and parallel execution
- **Error Handling**: Comprehensive error codes E3000-E3999

## Architecture

```
L03 Tool Execution Layer
├── models/          - Data models and types
│   ├── tool_definition.py     - Tool registry models
│   ├── tool_result.py         - Request/response models
│   ├── execution_context.py   - Sandbox and resource models
│   ├── checkpoint_models.py   - Checkpoint and task models
│   └── error_codes.py         - Error codes E3000-E3999
├── services/        - Core services
│   ├── tool_registry.py       - Tool registration and search
│   ├── tool_executor.py       - Tool execution orchestration
│   ├── tool_sandbox.py        - Sandbox management
│   ├── result_cache.py        - Result caching
│   ├── mcp_tool_bridge.py     - MCP integration
│   └── tool_composer.py       - Tool composition
└── tests/           - Test suite
    ├── conftest.py            - Test fixtures
    ├── test_models.py         - Model tests
    ├── test_registry.py       - Registry tests
    └── test_cache.py          - Cache tests
```

## Implementation Status

### ✅ Phase 1: Foundation (Complete)
- [x] Data models (ToolDefinition, ToolResult, ExecutionContext, Checkpoint)
- [x] Error codes E3000-E3999
- [x] Tool Registry with PostgreSQL + pgvector
- [x] Semantic search with Ollama embeddings

### ✅ Phase 2: Core Execution (Complete)
- [x] Tool Executor with BC-2 interface
- [x] Tool Sandbox with process isolation
- [x] L02 integration interface (get_tool, list_tools)
- [x] Resource limit validation (BC-1)

### ✅ Phase 3: Caching (Complete)
- [x] Result Cache with Redis backend
- [x] Cache invalidation strategies
- [x] Idempotency key support
- [x] Cache statistics

### ✅ Phase 4: MCP Integration (Complete)
- [x] MCP Tool Bridge architecture
- [x] Document Bridge stubs (Phase 15)
- [x] State Bridge stubs (Phase 16)
- [x] Checkpoint management

### ✅ Phase 5: Composition (Complete)
- [x] Tool Composer for chaining
- [x] Parallel execution support
- [x] DAG workflow execution
- [x] Error handling and partial failure recovery

### ✅ Phase 6: Testing (Complete)
- [x] Test suite with pytest
- [x] Model tests
- [x] Registry tests
- [x] Cache tests
- [x] Fixtures and conftest

### ⏳ Phase 6: Observability (Deferred)
- [ ] Prometheus metrics
- [ ] Structured logging
- [ ] Tracing integration
- [ ] Alerting rules

## Dependencies

```bash
pip3 install --break-system-packages \
    psycopg[binary] \
    redis \
    httpx
```

## Configuration

### Environment Variables

- `POSTGRES_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/agentic_tools`)
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `OLLAMA_URL`: Ollama API endpoint (default: `http://localhost:11434`)

### Infrastructure Requirements

| Service | Host | Port | Container |
|---------|------|------|-----------|
| PostgreSQL 16 + pgvector | localhost | 5432 | agentic-postgres |
| Redis 7 | localhost | 6379 | agentic-redis |
| Ollama | localhost | 11434 | native |

Verify infrastructure:
```bash
docker ps | grep agentic
curl http://localhost:11434/api/version
```

## Usage Examples

### Tool Registration

```python
from L03_tool_execution import ToolRegistry, ToolDefinition, ToolManifest

registry = ToolRegistry(
    db_connection_string="postgresql://localhost/tools"
)
await registry.initialize()

# Register tool
tool_def = ToolDefinition(
    tool_id="csv_parser",
    tool_name="CSV Parser",
    description="Parse CSV files with schema validation",
    category=ToolCategory.DATA_ACCESS,
    latest_version="1.0.0",
    source_type=SourceType.NATIVE,
)

await registry.register_tool(tool_def, tool_manifest)
```

### Tool Execution

```python
from L03_tool_execution import ToolExecutor, ToolInvokeRequest

executor = ToolExecutor(tool_registry, tool_sandbox)

request = ToolInvokeRequest(
    tool_id="csv_parser",
    parameters={"file_path": "/data/input.csv"},
    agent_context=AgentContext(
        agent_did="agent:123",
        tenant_id="tenant_1",
        session_id="session_abc",
    ),
)

response = await executor.execute(request)
if response.status == ToolStatus.SUCCESS:
    print(response.result.result)
```

### Semantic Search

```python
# Find tools by natural language query
results = await registry.semantic_search(
    query="find a tool to parse CSV files",
    limit=5
)

for tool_def, similarity in results:
    print(f"{tool_def.tool_name}: {similarity:.2f}")
```

## Testing

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
python3 -m pytest src/L03_tool_execution/tests/ -v --timeout=30
```

## Integration Points

### BC-1: Nested Sandbox Interface (from L02)
- Inherits agent sandbox context and resource limits
- Sub-allocates resources for tool execution
- Enforces stricter constraints than parent sandbox

### BC-2: Tool Invocation Interface (to L11)
- Exposes `tool.invoke()` method
- Returns `ToolInvokeResponse` with result or error
- Supports async execution patterns

### Phase 15: Document Management
- Integrates with document-consolidator MCP server
- Provides semantic document search
- Version pinning for consistency

### Phase 16: Session Orchestration
- Integrates with context-orchestrator MCP server
- Checkpoint creation and restoration
- Delta encoding for large states

## Error Codes

| Range | Category | Examples |
|-------|----------|----------|
| E3000-E3099 | Tool Registry | E3001: Tool not found, E3005: Semantic search failed |
| E3100-E3199 | Tool Executor | E3103: Timeout, E3106: Concurrent limit exceeded |
| E3200-E3299 | Permissions | E3201: Invalid token, E3203: Filesystem denied |
| E3300-E3399 | External API | E3301: Circuit breaker open, E3302: Rate limited |
| E3400-E3499 | Validation | E3401: Schema validation failed |
| E3500-E3599 | Document Bridge | E3501: Document not found |
| E3600-E3699 | State Bridge | E3601: Checkpoint creation failed |

## Known Limitations

1. **Sandbox Implementation**: Current implementation uses process isolation for development. Production should use Kubernetes Agent Sandbox CRD with gVisor/Firecracker.

2. **MCP Integration**: Document Bridge and State Bridge are stub implementations. Full integration requires MCP stdio transport implementation.

3. **Async Execution**: MCP Tasks pattern for long-running tools (>30s) is partially implemented. Falls back to sync execution.

4. **Observability**: Prometheus metrics, structured logging, and tracing are not yet implemented (Phase 6 deferred).

## Next Steps

1. **Complete MCP Stdio Transport**: Implement JSON-RPC 2.0 over stdio for MCP server communication
2. **Kubernetes Integration**: Deploy with Agent Sandbox CRD and gVisor runtime
3. **Observability**: Add Prometheus metrics and structured logging
4. **Result Validation**: Implement JSON Schema validation for tool outputs (Gap G-010)
5. **Permission Checker**: Integrate with OPA for policy-based access control
6. **Circuit Breaker**: Implement distributed circuit breaker with Redis state

## References

- Specification: `../specs/tool-execution-layer-specification-v1.2-ASCII.md`
- L02 Runtime Layer: `../src/L02_runtime/`
- Progress Log: `PROGRESS.md`
