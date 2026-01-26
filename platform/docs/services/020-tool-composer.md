# Service 20/44: ToolComposer

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_composer` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ToolExecutor |
| **Category** | Tool Management / Composition |

## Role in Development Environment

The **ToolComposer** enables multi-tool workflow composition and chaining. It provides:
- Sequential tool chaining with data flow between steps
- Parallel tool execution with result aggregation
- DAG-based workflow execution with dependencies
- Conditional branching with expression evaluation
- Result caching for repeated compositions
- Cycle detection and workflow validation

This is **the orchestration layer for tool workflows** - when agents need to execute multiple tools in sequence, parallel, or complex DAG patterns, ToolComposer manages the execution flow and data passing.

## Data Model

### CompositionResult Dataclass
- `composition_id: str` - Unique composition identifier
- `status: str` - "success", "partial_failure", or "failed"
- `responses: List[ToolInvokeResponse]` - Tool responses
- `cached: bool` - Whether result was from cache
- `execution_time_ms: float` - Total execution time
- `error: str` - Error message (if failed)

### ConditionalBranch Dataclass
- `condition: str` - Expression to evaluate
- `then_requests: List[ToolInvokeRequest]` - Requests if condition is true
- `else_requests: List[ToolInvokeRequest]` - Requests if condition is false

### CacheEntry Dataclass
- `result: CompositionResult` - Cached result
- `created_at: datetime` - When cached
- `ttl_seconds: int` - Time to live
- `hit_count: int` - Number of cache hits

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_enabled` | true | Enable result caching |
| `cache_ttl_seconds` | 300 | Default cache TTL (5 min) |
| `max_cache_entries` | 1000 | Maximum cache entries |

## API Methods

| Method | Description |
|--------|-------------|
| `execute_chain(requests, propagate_results)` | Execute tools sequentially |
| `execute_parallel(requests, fail_fast)` | Execute tools concurrently |
| `execute_dag(workflow)` | Execute DAG workflow |
| `execute_conditional(branch, context)` | Execute conditional branch |
| `execute_cached(requests, cache_key, ttl, mode)` | Execute with caching |
| `validate_workflow(workflow)` | Validate DAG for cycles |
| `clear_cache()` | Clear all cached results |
| `get_cache_stats()` | Get cache statistics |
| `get_metrics()` | Get composer metrics |

## Use Cases in Your Workflow

### 1. Initialize Tool Composer
```python
from L03_tool_execution.services.tool_composer import ToolComposer
from L03_tool_execution.services.tool_executor import ToolExecutor

# Create executor first
executor = ToolExecutor(config={...})

# Create composer with caching
composer = ToolComposer(
    tool_executor=executor,
    cache_enabled=True,
    cache_ttl_seconds=300,
    max_cache_entries=1000
)
```

### 2. Execute Sequential Tool Chain
```python
from L03_tool_execution.models import ToolInvokeRequest

# Define sequential requests
requests = [
    ToolInvokeRequest(
        tool_id="Read",
        parameters={"file_path": "/project/src/modal.tsx"}
    ),
    ToolInvokeRequest(
        tool_id="Analyze",
        parameters={"type": "code_review"}
        # Will receive _previous_result from Read
    ),
    ToolInvokeRequest(
        tool_id="Report",
        parameters={"format": "markdown"}
        # Will receive _previous_result from Analyze
    )
]

# Execute chain - each tool receives previous result
responses = await composer.execute_chain(
    requests=requests,
    propagate_results=True  # Pass results between tools
)

for i, response in enumerate(responses):
    print(f"Step {i+1}: {response.status}")
    if response.result:
        print(f"  Result: {response.result.result}")
```

### 3. Execute Parallel Tools
```python
# Define parallel requests
requests = [
    ToolInvokeRequest(
        tool_id="Lint",
        parameters={"path": "/project/src"}
    ),
    ToolInvokeRequest(
        tool_id="TypeCheck",
        parameters={"path": "/project/src"}
    ),
    ToolInvokeRequest(
        tool_id="Test",
        parameters={"path": "/project/tests"}
    )
]

# Execute all in parallel
responses = await composer.execute_parallel(
    requests=requests,
    fail_fast=False  # Continue even if one fails
)

# With fail_fast=True, stops on first failure
responses = await composer.execute_parallel(
    requests=requests,
    fail_fast=True
)
```

### 4. Execute DAG Workflow
```python
# Define DAG with dependencies
workflow = {
    "nodes": {
        "fetch_data": {
            "request": ToolInvokeRequest(
                tool_id="Fetch",
                parameters={"url": "https://api.example.com/data"}
            ),
            "depends_on": []  # No dependencies
        },
        "parse_data": {
            "request": ToolInvokeRequest(
                tool_id="Parse",
                parameters={"format": "json"}
                # Receives _dep_fetch_data automatically
            ),
            "depends_on": ["fetch_data"]
        },
        "validate": {
            "request": ToolInvokeRequest(
                tool_id="Validate",
                parameters={"schema": "user_schema"}
            ),
            "depends_on": ["parse_data"]
        },
        "transform_a": {
            "request": ToolInvokeRequest(
                tool_id="Transform",
                parameters={"type": "normalize"}
            ),
            "depends_on": ["validate"]
        },
        "transform_b": {
            "request": ToolInvokeRequest(
                tool_id="Transform",
                parameters={"type": "enrich"}
            ),
            "depends_on": ["validate"]
        },
        "merge": {
            "request": ToolInvokeRequest(
                tool_id="Merge",
                parameters={}
            ),
            "depends_on": ["transform_a", "transform_b"]
        }
    }
}

# Validate first
if composer.validate_workflow(workflow):
    # Execute DAG
    results = await composer.execute_dag(workflow)

    for node_id, response in results.items():
        print(f"{node_id}: {response.status}")
```

### 5. Conditional Branching
```python
from L03_tool_execution.services.tool_composer import ConditionalBranch

# Define conditional branch
branch = ConditionalBranch(
    condition="status == 'success' and count > 10",
    then_requests=[
        ToolInvokeRequest(
            tool_id="ProcessLarge",
            parameters={"batch_size": 100}
        )
    ],
    else_requests=[
        ToolInvokeRequest(
            tool_id="ProcessSmall",
            parameters={"batch_size": 10}
        )
    ]
)

# Execute with context
context = {
    "status": "success",
    "count": 42
}

result = await composer.execute_conditional(
    branch=branch,
    context=context
)

print(f"Branch executed: {result.status}")
# Executes ProcessLarge because count > 10
```

### 6. Cached Execution
```python
# Execute with caching
result = await composer.execute_cached(
    requests=requests,
    cache_key="my-workflow-v1",  # Optional custom key
    ttl_seconds=600,             # 10 minute TTL
    execution_mode="chain"       # or "parallel"
)

if result.cached:
    print("Result from cache!")
else:
    print(f"Fresh execution: {result.execution_time_ms}ms")

# Second call with same key returns cached result
result2 = await composer.execute_cached(
    requests=requests,
    cache_key="my-workflow-v1",
    execution_mode="chain"
)
# result2.cached == True
```

### 7. Check Cache Statistics
```python
stats = composer.get_cache_stats()

print(f"Cache enabled: {stats['enabled']}")
print(f"Entries: {stats['entries']}/{stats['max_entries']}")
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate_percent']}%")
```

### 8. Get Composer Metrics
```python
metrics = composer.get_metrics()

print(f"Total compositions: {metrics['total_compositions']}")
print(f"Successful: {metrics['successful_compositions']}")
print(f"Failed: {metrics['failed_compositions']}")
print(f"Success rate: {metrics['success_rate_percent']}%")
print(f"Cache stats: {metrics['cache']}")
```

### 9. Clear Cache
```python
# Clear all cached results
cleared = composer.clear_cache()
print(f"Cleared {cleared} entries")
```

## Service Interactions

```
+------------------+
|  ToolComposer    | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+
|  ToolExecutor    |
|     (L03)        |
+------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
| AgentExecutor    |     | WorkflowEngine    |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **ToolExecutor (L03)**: Executes individual tools
- **AgentExecutor (L02)**: Uses for multi-tool agent operations
- **WorkflowEngine (L02)**: Integrates for workflow tool nodes

## Execution Patterns

### Chain Execution Flow
```
Request 1 ──execute──> Response 1
     │
     └── _previous_result ──>
                              │
Request 2 ──execute──> Response 2
     │
     └── _previous_result ──>
                              │
Request 3 ──execute──> Response 3
```

### Parallel Execution Flow
```
                 ┌── Request 1 ──> Response 1
                 │
Parallel ────────┼── Request 2 ──> Response 2
                 │
                 └── Request 3 ──> Response 3
                          │
                 gather() │
                          v
                 [Response 1, 2, 3]
```

### DAG Execution Flow
```
fetch_data (no deps)
      │
      v
  parse_data
      │
      v
   validate
    /    \
   v      v
transform_a  transform_b
    \    /
     \  /
      v
    merge
```

## Condition Expression Syntax

The composer supports safe expression evaluation:

```python
# Equality comparisons
"status == 'success'"
"count == 10"

# Inequality
"status != 'error'"
"count > 0"
"count >= 10"
"count < 100"
"count <= 50"

# Boolean values
"enabled == true"
"disabled == false"

# None checks
"error is None"
"result is not None"

# Combined (implicit AND)
"status == 'success' and count > 10"
```

## Error Codes

| Code | Description |
|------|-------------|
| E3108 | Tool execution failed during composition |

## Execution Examples

```python
# Complete composition workflow
composer = ToolComposer(
    tool_executor=executor,
    cache_enabled=True,
    cache_ttl_seconds=300
)

# Sequential: Read -> Analyze -> Transform
chain_requests = [
    ToolInvokeRequest(tool_id="Read", parameters={"file": "data.json"}),
    ToolInvokeRequest(tool_id="Analyze", parameters={"type": "stats"}),
    ToolInvokeRequest(tool_id="Transform", parameters={"output": "csv"})
]

chain_result = await composer.execute_chain(chain_requests)
print(f"Chain: {len(chain_result)} steps, last status: {chain_result[-1].status}")

# Parallel: Run independent checks
parallel_requests = [
    ToolInvokeRequest(tool_id="CheckA", parameters={}),
    ToolInvokeRequest(tool_id="CheckB", parameters={}),
    ToolInvokeRequest(tool_id="CheckC", parameters={})
]

parallel_result = await composer.execute_parallel(parallel_requests)
all_passed = all(r.status == ToolStatus.SUCCESS for r in parallel_result)
print(f"All checks passed: {all_passed}")

# Cached execution
cached_result = await composer.execute_cached(
    chain_requests,
    execution_mode="chain"
)
print(f"From cache: {cached_result.cached}")

# View metrics
print(composer.get_metrics())
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Chain Execution | Complete |
| Parallel Execution | Complete |
| DAG Execution | Complete |
| Result Propagation | Complete |
| Conditional Branching | Complete |
| Expression Evaluation | Complete |
| Result Caching | Complete |
| Cache TTL | Complete |
| Cache Eviction | Complete |
| Workflow Validation | Complete |
| Cycle Detection | Complete |
| Metrics Collection | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Redis Cache Backend | Medium | Distributed caching |
| Retry Logic | Medium | Retry failed compositions |
| Timeout Handling | Medium | Per-composition timeouts |
| Error Recovery | Low | Partial recovery strategies |
| Composition Templates | Low | Reusable workflow templates |
| Visualization | Low | Workflow graph visualization |

## Strengths

- **Flexible execution** - Chain, parallel, DAG patterns
- **Data flow** - Automatic result propagation between tools
- **Caching** - Avoid redundant executions
- **Validation** - Cycle detection in DAGs
- **Conditional logic** - Safe expression evaluation
- **Metrics** - Track success/failure rates

## Weaknesses

- **In-memory cache** - Not distributed
- **No retries** - Failed compositions not retried
- **No timeouts** - Individual tool timeouts only
- **Simple conditions** - Limited expression language
- **No templates** - Workflows defined inline
- **No persistence** - Workflow state not persisted

## Best Practices

### Chain Design
Use chains for dependent operations:
```python
# Good: Each step needs previous result
requests = [
    ToolInvokeRequest(tool_id="Fetch", parameters={"url": "..."}),
    ToolInvokeRequest(tool_id="Parse", parameters={}),  # Uses _previous_result
    ToolInvokeRequest(tool_id="Validate", parameters={})
]
await composer.execute_chain(requests, propagate_results=True)
```

### Parallel Design
Use parallel for independent operations:
```python
# Good: Independent operations
requests = [
    ToolInvokeRequest(tool_id="LintJS", parameters={}),
    ToolInvokeRequest(tool_id="LintCSS", parameters={}),
    ToolInvokeRequest(tool_id="LintPython", parameters={})
]
await composer.execute_parallel(requests)
```

### DAG Design
Use DAGs for complex dependencies:
```python
# Good: Multiple dependency paths
workflow = {
    "nodes": {
        "a": {"request": ..., "depends_on": []},
        "b": {"request": ..., "depends_on": ["a"]},
        "c": {"request": ..., "depends_on": ["a"]},
        "d": {"request": ..., "depends_on": ["b", "c"]}
    }
}
# b and c run in parallel after a, d waits for both
```

### Cache Configuration
Match TTL to data freshness needs:
```python
# Short TTL for dynamic data
await composer.execute_cached(requests, ttl_seconds=60)

# Longer TTL for static data
await composer.execute_cached(requests, ttl_seconds=3600)

# Disable for unique operations
composer.cache_enabled = False
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_composer.py`
- Models: `platform/src/L03_tool_execution/models/`
- Spec: Platform architecture Section 3 (Gap G-020)

## Related Services

- ToolExecutor (L03) - Individual tool execution
- ToolRegistry (L03) - Tool registration
- ResultCache (L03) - Result caching
- AgentExecutor (L02) - Agent tool execution
- WorkflowEngine (L02) - Workflow orchestration

---
*Generated: 2026-01-24 | Platform Services Documentation*
