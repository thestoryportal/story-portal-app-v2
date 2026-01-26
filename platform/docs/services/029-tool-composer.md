# Service 29/44: ToolComposer

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_composer` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ToolExecutor (L03) |
| **Category** | Tool Management / Workflow Orchestration |

## Role in Development Environment

The **ToolComposer** enables tool chaining and parallel execution for complex workflows. It provides:
- Sequential tool chaining with data flow
- Parallel tool execution with result aggregation
- DAG workflow execution with dependencies
- Conditional branching with expression evaluation
- Result caching for repeated compositions
- Error handling and partial failure recovery
- Execution planning and optimization

This is **the workflow orchestration layer for tool execution** - when complex tasks require multiple tools working together (read file, analyze, transform, write), ToolComposer orchestrates the execution with proper dependencies and parallelism.

## Data Model

### CompositionResult Dataclass
- `composition_id: str` - Unique composition identifier
- `status: str` - success, partial_failure, failed
- `responses: List[ToolInvokeResponse]` - Tool responses
- `cached: bool` - Whether result came from cache
- `execution_time_ms: float` - Total execution time
- `error: Optional[str]` - Error message if failed

### ConditionalBranch Dataclass
- `condition: str` - Expression to evaluate
- `then_requests: List[ToolInvokeRequest]` - Requests if true
- `else_requests: Optional[List[ToolInvokeRequest]]` - Requests if false

### CacheEntry Dataclass
- `result: CompositionResult` - Cached composition result
- `created_at: datetime` - Cache creation time
- `ttl_seconds: int` - Time-to-live
- `hit_count: int` - Number of cache hits

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_enabled` | true | Enable result caching |
| `cache_ttl_seconds` | 300 | Default cache TTL (5 minutes) |
| `max_cache_entries` | 1000 | Maximum cache entries |

## API Methods

| Method | Description |
|--------|-------------|
| `execute_chain(requests, propagate_results)` | Execute tools sequentially |
| `execute_parallel(requests, fail_fast)` | Execute tools in parallel |
| `execute_dag(workflow)` | Execute DAG workflow |
| `validate_workflow(workflow)` | Validate DAG for cycles |
| `execute_conditional(branch, context)` | Execute conditional branch |
| `execute_cached(requests, ...)` | Execute with caching |
| `clear_cache()` | Clear all cached results |
| `get_cache_stats()` | Get cache statistics |
| `get_metrics()` | Get composer metrics |

## Use Cases in Your Workflow

### 1. Initialize Tool Composer
```python
from L03_tool_execution.services.tool_composer import ToolComposer
from L03_tool_execution.services.tool_executor import ToolExecutor

# Create executor first
executor = ToolExecutor(registry, sandbox)

# Create composer
composer = ToolComposer(
    tool_executor=executor,
    cache_enabled=True,
    cache_ttl_seconds=300,  # 5 minutes
    max_cache_entries=1000
)
```

### 2. Execute Tool Chain (Sequential)
```python
from L03_tool_execution.models import ToolInvokeRequest, AgentContext
from uuid import uuid4

agent_context = AgentContext(
    agent_did="did:agent:abc123",
    tenant_id="tenant-001",
    session_id="session-456"
)

# Create chain of requests
requests = [
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": "/project/src/modal.tsx"},
        agent_context=agent_context
    ),
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Analyze",
        parameters={"type": "lint"},
        agent_context=agent_context
    ),
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Write",
        parameters={"file_path": "/project/reports/lint.json"},
        agent_context=agent_context
    )
]

# Execute chain - results propagate between tools
responses = await composer.execute_chain(requests, propagate_results=True)

for i, response in enumerate(responses):
    print(f"Step {i+1}: {response.status}")
    if response.status != ToolStatus.SUCCESS:
        print(f"  Error: {response.error.message}")
        break  # Chain stops on failure
```

### 3. Execute Parallel Tools
```python
# Execute independent tools in parallel
parallel_requests = [
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": "/project/src/a.tsx"},
        agent_context=agent_context
    ),
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": "/project/src/b.tsx"},
        agent_context=agent_context
    ),
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": "/project/src/c.tsx"},
        agent_context=agent_context
    ),
]

# Execute all in parallel
responses = await composer.execute_parallel(parallel_requests, fail_fast=False)

# All responses returned in same order as requests
for i, response in enumerate(responses):
    print(f"File {i+1}: {response.status}")
```

### 4. Execute Parallel with Fail-Fast
```python
# Stop on first failure
responses = await composer.execute_parallel(
    parallel_requests,
    fail_fast=True  # Cancel remaining on first error
)

# Some may be cancelled
for response in responses:
    if response.status == ToolStatus.CANCELLED:
        print("Cancelled due to other failure")
```

### 5. Execute DAG Workflow
```python
# Define DAG workflow with dependencies
workflow = {
    "nodes": {
        "read_config": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Read",
                parameters={"file_path": "/project/config.json"},
                agent_context=agent_context
            ),
            "depends_on": []  # No dependencies - runs first
        },
        "read_source": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Read",
                parameters={"file_path": "/project/src/app.tsx"},
                agent_context=agent_context
            ),
            "depends_on": []  # No dependencies - parallel with read_config
        },
        "analyze": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Analyze",
                parameters={"type": "full"},
                agent_context=agent_context
            ),
            "depends_on": ["read_config", "read_source"]  # Wait for both
        },
        "generate_report": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Write",
                parameters={"file_path": "/project/report.md"},
                agent_context=agent_context
            ),
            "depends_on": ["analyze"]  # Wait for analysis
        }
    }
}

# Validate before execution
if composer.validate_workflow(workflow):
    results = await composer.execute_dag(workflow)

    for node_id, response in results.items():
        print(f"{node_id}: {response.status}")
else:
    print("Invalid workflow - check for cycles or missing deps")
```

### 6. Validate Workflow DAG
```python
# Check for cycles and missing dependencies
valid = composer.validate_workflow(workflow)

if not valid:
    print("Workflow has issues:")
    # Logs will show: "Cycle detected" or "Missing dependency"
```

### 7. Execute Conditional Branch
```python
from L03_tool_execution.services.tool_composer import ConditionalBranch

# Define conditional branch
branch = ConditionalBranch(
    condition="has_errors == true",
    then_requests=[
        ToolInvokeRequest(
            invocation_id=uuid4(),
            tool_id="Write",
            parameters={"file_path": "/project/errors.log"},
            agent_context=agent_context
        ),
        ToolInvokeRequest(
            invocation_id=uuid4(),
            tool_id="Notify",
            parameters={"message": "Errors found"},
            agent_context=agent_context
        )
    ],
    else_requests=[
        ToolInvokeRequest(
            invocation_id=uuid4(),
            tool_id="Deploy",
            parameters={"target": "production"},
            agent_context=agent_context
        )
    ]
)

# Context for condition evaluation
context = {
    "has_errors": True,
    "error_count": 5,
    "status": "failed"
}

# Execute - will run then_requests since has_errors == true
result = await composer.execute_conditional(branch, context)
print(f"Status: {result.status}")
print(f"Responses: {len(result.responses)}")
```

### 8. Condition Expressions
```python
# Supported condition expressions:

# Equality
ConditionalBranch(condition="status == 'success'", ...)

# Comparison
ConditionalBranch(condition="count > 10", ...)

# Boolean
ConditionalBranch(condition="enabled == true", ...)

# None checks
ConditionalBranch(condition="error is None", ...)
ConditionalBranch(condition="result is not None", ...)
```

### 9. Execute with Caching
```python
# Execute with automatic caching
result = await composer.execute_cached(
    requests=requests,
    cache_key=None,  # Auto-generate key
    ttl_seconds=600,  # 10 minutes
    execution_mode="chain"  # or "parallel"
)

print(f"Cached: {result.cached}")  # False on first run
print(f"Status: {result.status}")

# Second call with same requests - cache hit
result2 = await composer.execute_cached(requests, execution_mode="chain")
print(f"Cached: {result2.cached}")  # True - from cache
print(f"Execution time: {result2.execution_time_ms}ms")  # Near-zero
```

### 10. Custom Cache Key
```python
# Use custom cache key for semantic caching
result = await composer.execute_cached(
    requests=requests,
    cache_key="analyze-modal-component-v2",  # Custom key
    ttl_seconds=3600,  # 1 hour
    execution_mode="parallel"
)
```

### 11. Get Cache Statistics
```python
stats = composer.get_cache_stats()

print(f"Cache enabled: {stats['enabled']}")
print(f"Entries: {stats['entries']}/{stats['max_entries']}")
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate_percent']}%")
```

### 12. Clear Cache
```python
# Clear all cached results
cleared = composer.clear_cache()
print(f"Cleared {cleared} entries")
```

### 13. Get Composer Metrics
```python
metrics = composer.get_metrics()

print(f"Total compositions: {metrics['total_compositions']}")
print(f"Successful: {metrics['successful_compositions']}")
print(f"Failed: {metrics['failed_compositions']}")
print(f"Success rate: {metrics['success_rate_percent']}%")

# Cache metrics included
print(f"Cache hit rate: {metrics['cache']['hit_rate_percent']}%")
```

## Service Interactions

```
+------------------+
|   ToolComposer   | <--- L03 Tool Execution Layer
|      (L03)       |
+--------+---------+
         |
   Uses:
         |
+------------------+
|   ToolExecutor   |
|      (L03)       |
+------------------+
         |
   Executes tools:
         |
+------------------+
|   ToolSandbox    |
|      (L03)       |
+------------------+
```

**Integration Points:**
- **ToolExecutor (L03)**: Executes individual tools
- **ToolRegistry (L03)**: Tool definitions (via executor)
- **ToolSandbox (L03)**: Sandboxed execution (via executor)
- **ResultCache (L03)**: Complementary caching layer

## Execution Patterns

### Chain Execution
```
Request 1 → Execute → Result 1
                         ↓
Request 2 ← Result 1 injected → Execute → Result 2
                                              ↓
Request 3 ← Result 2 injected → Execute → Result 3
```

### Parallel Execution
```
Request 1 → Execute ──┐
Request 2 → Execute ──┼→ Aggregate → Results
Request 3 → Execute ──┘
```

### DAG Execution
```
read_config ─────┐
                 ├→ analyze → generate_report
read_source ─────┘
```

### Conditional Branching
```
Evaluate condition
       │
       ├─ True → Execute then_requests (chain)
       │
       └─ False → Execute else_requests (chain)
```

## Cache Key Generation

```
1. Collect: execution_mode + tool_ids + parameters
2. Serialize: JSON with sorted keys
3. Hash: SHA256
4. Result: 64-character hex string

Example:
   Mode: "chain"
   Tools: ["Read", "Analyze"]
   Params: [{"file": "/a.txt"}, {"type": "lint"}]

   Key: "a3b8c9d2e1f0..."
```

## Error Handling

### Chain Errors
- Chain stops on first error
- All remaining requests skipped
- Returns partial responses

### Parallel Errors
- `fail_fast=False`: All complete, errors captured
- `fail_fast=True`: Cancel remaining on first error

### DAG Errors
- Dependent nodes not executed
- Independent nodes continue

## Execution Examples

```python
# Complete composition workflow
from L03_tool_execution.services.tool_composer import (
    ToolComposer,
    ConditionalBranch
)
from L03_tool_execution.models import ToolInvokeRequest, AgentContext
from uuid import uuid4

# Initialize
composer = ToolComposer(
    tool_executor=executor,
    cache_enabled=True,
    cache_ttl_seconds=300,
    max_cache_entries=1000
)

agent_context = AgentContext(
    agent_did="did:agent:test",
    tenant_id="tenant-1",
    session_id="session-1"
)

# 1. Simple chain
chain_requests = [
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Glob",
        parameters={"pattern": "**/*.tsx"},
        agent_context=agent_context
    ),
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Analyze",
        parameters={"type": "components"},
        agent_context=agent_context
    )
]

result = await composer.execute_cached(
    requests=chain_requests,
    execution_mode="chain"
)
print(f"Chain result: {result.status}")

# 2. Parallel reads
parallel_requests = [
    ToolInvokeRequest(
        invocation_id=uuid4(),
        tool_id="Read",
        parameters={"file_path": f"/src/{f}"},
        agent_context=agent_context
    )
    for f in ["app.tsx", "index.tsx", "modal.tsx"]
]

responses = await composer.execute_parallel(parallel_requests)
print(f"Read {len(responses)} files in parallel")

# 3. Conditional deployment
deploy_branch = ConditionalBranch(
    condition="tests_passed == true and coverage > 80",
    then_requests=[
        ToolInvokeRequest(
            invocation_id=uuid4(),
            tool_id="Deploy",
            parameters={"env": "production"},
            agent_context=agent_context
        )
    ],
    else_requests=[
        ToolInvokeRequest(
            invocation_id=uuid4(),
            tool_id="Notify",
            parameters={"message": "Deployment blocked"},
            agent_context=agent_context
        )
    ]
)

context = {"tests_passed": True, "coverage": 85}
result = await composer.execute_conditional(deploy_branch, context)
# Deploys to production (condition met)

# 4. DAG workflow
workflow = {
    "nodes": {
        "lint": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Lint",
                parameters={},
                agent_context=agent_context
            ),
            "depends_on": []
        },
        "test": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Test",
                parameters={},
                agent_context=agent_context
            ),
            "depends_on": []
        },
        "build": {
            "request": ToolInvokeRequest(
                invocation_id=uuid4(),
                tool_id="Build",
                parameters={},
                agent_context=agent_context
            ),
            "depends_on": ["lint", "test"]
        }
    }
}

if composer.validate_workflow(workflow):
    dag_results = await composer.execute_dag(workflow)
    print(f"Build: {dag_results['build'].status}")

# 5. Check metrics
metrics = composer.get_metrics()
print(f"Success rate: {metrics['success_rate_percent']}%")
print(f"Cache hit rate: {metrics['cache']['hit_rate_percent']}%")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| execute_chain | Complete |
| execute_parallel | Complete |
| execute_dag | Complete |
| validate_workflow | Complete |
| execute_conditional | Complete |
| execute_cached | Complete |
| Cache Management | Complete |
| Metrics Tracking | Complete |
| Error Handling | Complete |
| Condition Evaluation | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Execution Planning | Medium | Optimize execution order |
| Retry Policies | Medium | Per-step retry configuration |
| Timeout Aggregation | Medium | Total workflow timeout |
| Streaming Results | Low | Stream responses as available |
| Workflow Templates | Low | Predefined workflow patterns |
| Prometheus Metrics | Low | Export metrics |

## Strengths

- **Multiple patterns** - Chain, parallel, DAG, conditional
- **Result propagation** - Data flows between tools
- **Built-in caching** - Avoid redundant compositions
- **DAG validation** - Cycle detection, dependency checking
- **Partial failure** - Continue despite errors (parallel)
- **Metrics tracking** - Success rates, cache stats

## Weaknesses

- **No workflow timeout** - Only per-tool timeouts
- **No retry policies** - Manual retry required
- **Simple conditions** - Limited expression support
- **No streaming** - Wait for all responses
- **In-memory cache** - Not shared across instances
- **No optimization** - Executes as defined

## Best Practices

### Execution Mode Selection
Choose the right mode:
```python
# Independent tools - parallel
composer.execute_parallel(independent_requests)

# Dependent tools - chain
composer.execute_chain(dependent_requests, propagate_results=True)

# Complex dependencies - DAG
composer.execute_dag(workflow_with_deps)

# Decision points - conditional
composer.execute_conditional(branch, context)
```

### Cache Configuration
Set appropriate TTL:
```python
# Volatile data (file contents) - short TTL
execute_cached(requests, ttl_seconds=60)

# Stable analysis - medium TTL
execute_cached(requests, ttl_seconds=300)

# Expensive computations - long TTL
execute_cached(requests, ttl_seconds=3600)
```

### Error Handling
Handle partial failures:
```python
result = await composer.execute_cached(requests, execution_mode="parallel")

if result.status == "partial_failure":
    # Some succeeded, some failed
    for response in result.responses:
        if response.status != ToolStatus.SUCCESS:
            handle_failure(response)
elif result.status == "failed":
    # All failed
    log_error(result.error)
```

### DAG Design
Keep workflows manageable:
```python
# Good: Clear dependencies
workflow = {
    "nodes": {
        "a": {"request": ..., "depends_on": []},
        "b": {"request": ..., "depends_on": ["a"]},
        "c": {"request": ..., "depends_on": ["b"]}
    }
}

# Avoid: Too many dependencies
# Creates bottlenecks and complexity
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_composer.py`
- Models: `platform/src/L03_tool_execution/models/tool_result.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3 architecture, Gap G-020

## Related Services

- ToolExecutor (L03) - Executes individual tools
- ResultCache (L03) - Complementary caching
- ToolRegistry (L03) - Tool definitions
- MCPToolBridge (L03) - MCP integration
- ModelGatewayBridge (L03) - LLM composition support

---
*Generated: 2026-01-24 | Platform Services Documentation*
