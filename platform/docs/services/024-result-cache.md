# Service 24/44: ResultCache

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.result_cache` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | Redis |
| **Category** | Tool Management / Caching |

## Role in Development Environment

The **ResultCache** caches tool execution results in Redis with TTL-based invalidation. It provides:
- Result caching with configurable TTL
- Cache key generation with idempotency support
- Cache invalidation strategies (per-request, per-tool, all)
- Metrics for cache hit/miss rates
- Deterministic key hashing for reproducibility

This is **the performance optimization layer for tool execution** - when tools are invoked with identical parameters, ResultCache returns cached results to avoid redundant execution.

## Data Model

### ToolResult Dataclass
- `result: Any` - Tool-specific result (validated against manifest schema)
- `result_type: str` - Type hint for deserialization (default: "object")

### ToolInvokeRequest Dataclass (key fields for caching)
- `invocation_id: UUID` - Unique invocation identifier
- `tool_id: str` - Tool identifier
- `tool_version: str` - Version (or "latest")
- `parameters: Dict` - Tool parameters
- `execution_options: ExecutionOptions` - May contain idempotency_key

### ExecutionOptions Dataclass
- `async_mode: bool` - Long-running tool mode
- `priority: int` - Execution priority (1-10)
- `idempotency_key: str` - For duplicate request detection
- `require_approval: bool` - Override approval setting

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `redis_url` | "redis://localhost:6379" | Redis connection URL |
| `default_ttl_seconds` | 300 | Default cache TTL (5 minutes) |
| `key_prefix` | "tool:result:" | Cache key prefix |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize Redis connection |
| `close()` | Close Redis connection |
| `get(request)` | Retrieve cached result |
| `set(request, result, ttl_seconds)` | Store result in cache |
| `invalidate(request)` | Invalidate specific cached result |
| `invalidate_tool(tool_id)` | Invalidate all results for a tool |
| `clear_all()` | Clear all cached results |
| `get_stats()` | Get cache statistics |

## Use Cases in Your Workflow

### 1. Initialize Result Cache
```python
from L03_tool_execution.services.result_cache import ResultCache

cache = ResultCache(
    redis_url="redis://localhost:6379",
    default_ttl_seconds=300,  # 5 minutes
    key_prefix="tool:result:"
)

await cache.initialize()
# Connects to Redis and verifies connection
```

### 2. Cache Tool Execution Result
```python
from L03_tool_execution.models import ToolInvokeRequest, ToolResult

# After executing a tool
request = ToolInvokeRequest(
    tool_id="Read",
    parameters={"file_path": "/project/src/modal.tsx"}
)

result = ToolResult(
    result={"content": "file contents here...", "line_count": 150},
    result_type="object"
)

# Cache the result
await cache.set(request, result)
# Stored with 5-minute TTL

# Or with custom TTL
await cache.set(request, result, ttl_seconds=3600)  # 1 hour
```

### 3. Check Cache Before Execution
```python
# Before executing a tool, check cache
request = ToolInvokeRequest(
    tool_id="Read",
    parameters={"file_path": "/project/src/modal.tsx"}
)

cached_result = await cache.get(request)

if cached_result:
    print("Cache HIT!")
    print(f"Result: {cached_result.result}")
else:
    print("Cache MISS - executing tool...")
    # Execute the tool
    result = await execute_tool(request)
    # Cache the result for next time
    await cache.set(request, result)
```

### 4. Use Idempotency Key
```python
from L03_tool_execution.models import ExecutionOptions

# Request with explicit idempotency key
request = ToolInvokeRequest(
    tool_id="Analyze",
    parameters={"path": "/project/src"},
    execution_options=ExecutionOptions(
        idempotency_key="analysis-modal-v1"  # Custom cache key
    )
)

# First call - executes and caches
result1 = await cache.get(request)  # MISS
# ... execute tool ...
await cache.set(request, result)

# Second call with same idempotency_key - cache hit
result2 = await cache.get(request)  # HIT
```

### 5. Invalidate Cached Result
```python
# Invalidate specific request
request = ToolInvokeRequest(
    tool_id="Read",
    parameters={"file_path": "/project/src/modal.tsx"}
)

await cache.invalidate(request)
print("Cache entry invalidated")

# Next get() will return None
```

### 6. Invalidate All Results for a Tool
```python
# When a tool is updated, invalidate all its cached results
await cache.invalidate_tool("Read")
print("All Read tool cache entries invalidated")

# Also useful when file system changes
await cache.invalidate_tool("Glob")
await cache.invalidate_tool("Grep")
```

### 7. Clear All Cache
```python
# Clear entire cache (e.g., after deployment)
await cache.clear_all()
print("All cache entries cleared")
```

### 8. Get Cache Statistics
```python
stats = await cache.get_stats()

print(f"Cached entries: {stats['cached_entries']}")
print(f"Redis hits: {stats['redis_hits']}")
print(f"Redis misses: {stats['redis_misses']}")

# Calculate hit rate
total = stats['redis_hits'] + stats['redis_misses']
if total > 0:
    hit_rate = (stats['redis_hits'] / total) * 100
    print(f"Hit rate: {hit_rate:.1f}%")
```

### 9. Cache Integration with ToolExecutor
```python
from L03_tool_execution.services.tool_executor import ToolExecutor
from L03_tool_execution.services.result_cache import ResultCache

class CachedToolExecutor:
    def __init__(self, executor: ToolExecutor, cache: ResultCache):
        self.executor = executor
        self.cache = cache

    async def execute(self, request: ToolInvokeRequest):
        # Check cache first
        cached = await self.cache.get(request)
        if cached:
            return ToolInvokeResponse(
                invocation_id=request.invocation_id,
                status=ToolStatus.SUCCESS,
                result=cached,
                execution_metadata=ExecutionMetadata(
                    duration_ms=0  # Instant from cache
                )
            )

        # Execute tool
        response = await self.executor.execute(request)

        # Cache successful results
        if response.status == ToolStatus.SUCCESS and response.result:
            await self.cache.set(request, response.result)

        return response
```

## Service Interactions

```
+------------------+
|  ResultCache     | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+
|      Redis       |
|   (Key-Value)    |
+------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
|  ToolExecutor    |     |  ToolComposer     |
|     (L03)        |     |      (L03)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **Redis**: Stores cached results with TTL expiration
- **ToolExecutor (L03)**: Caches tool execution results
- **ToolComposer (L03)**: Uses cache for composition results

## Cache Key Generation

```
1. With Idempotency Key:
   └── tool:result:{idempotency_key}

2. Without Idempotency Key:
   ├── Combine: tool_id + tool_version + parameters
   ├── JSON serialize (sorted keys)
   ├── SHA256 hash (first 16 chars)
   └── tool:result:{tool_id}:{hash}

Example:
   Request:
     tool_id: "Read"
     tool_version: "1.0.0"
     parameters: {"file_path": "/src/app.tsx"}

   Key: tool:result:Read:a3b8c9d2e1f0g4h5
```

## Redis Data Structure

```
KEY: tool:result:Read:a3b8c9d2e1f0g4h5
VALUE: {
  "result": {"content": "...", "line_count": 100},
  "result_type": "object",
  "cached_at": "2026-01-24T10:30:00Z"
}
TTL: 300 seconds
```

## Error Handling

The cache is designed to fail gracefully:
- Cache errors don't fail tool execution
- On `get()` error: returns `None` (cache miss)
- On `set()` error: logs warning, continues execution
- On `invalidate()` error: logs warning, continues

```python
# Cache errors are logged but don't raise exceptions
try:
    cached = await cache.get(request)
except Exception as e:
    # Internal handling - never propagates
    logger.error(f"Cache retrieval error: {e}")
    return None  # Treat as cache miss
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E3503 | Failed to initialize result cache | Yes |

## Execution Examples

```python
# Complete caching workflow
cache = ResultCache(
    redis_url="redis://localhost:6379",
    default_ttl_seconds=300
)

await cache.initialize()

# Tool execution requests
requests = [
    ToolInvokeRequest(tool_id="Read", parameters={"file_path": "/a.txt"}),
    ToolInvokeRequest(tool_id="Read", parameters={"file_path": "/b.txt"}),
    ToolInvokeRequest(tool_id="Read", parameters={"file_path": "/a.txt"}),  # Duplicate
]

results = {}

for req in requests:
    # Check cache
    cached = await cache.get(req)

    if cached:
        print(f"HIT: {req.tool_id} {req.parameters}")
        results[str(req.invocation_id)] = cached
    else:
        print(f"MISS: {req.tool_id} {req.parameters}")
        # Simulate execution
        result = ToolResult(
            result={"content": f"Contents of {req.parameters['file_path']}"},
            result_type="object"
        )
        await cache.set(req, result)
        results[str(req.invocation_id)] = result

# Output:
# MISS: Read {'file_path': '/a.txt'}
# MISS: Read {'file_path': '/b.txt'}
# HIT: Read {'file_path': '/a.txt'}

# Check stats
stats = await cache.get_stats()
print(f"Cache entries: {stats['cached_entries']}")

# Cleanup
await cache.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize | Complete |
| Close | Complete |
| Get (cache lookup) | Complete |
| Set (cache storage) | Complete |
| Invalidate (single) | Complete |
| Invalidate Tool (bulk) | Complete |
| Clear All | Complete |
| Get Stats | Complete |
| Cache Key Generation | Complete |
| Idempotency Key Support | Complete |
| TTL Expiration | Complete |
| Error Handling | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Cache Warming | Medium | Pre-populate cache for common requests |
| Cache Compression | Medium | Compress large results |
| Hit/Miss Metrics | Medium | Prometheus metrics export |
| Cluster Support | Low | Redis Cluster support |
| Cache Regions | Low | Separate caches by tool category |
| Eviction Policy | Low | LRU when cache is full |

## Strengths

- **Simple API** - Get, set, invalidate pattern
- **TTL-based expiration** - Automatic cleanup
- **Idempotency support** - Custom cache keys
- **Graceful failures** - Cache errors don't break execution
- **Bulk invalidation** - Clear all results for a tool
- **Statistics** - Monitor cache effectiveness

## Weaknesses

- **No compression** - Large results stored as-is
- **No warming** - Cold cache after restart
- **Single Redis** - No cluster support
- **No eviction policy** - Relies on TTL only
- **No hit/miss tracking** - Only Redis-level stats
- **No cache regions** - Flat key space

## Best Practices

### TTL Configuration
Match TTL to data freshness needs:
```python
# Static analysis results (long TTL)
ResultCache(default_ttl_seconds=3600)  # 1 hour

# File contents (medium TTL)
ResultCache(default_ttl_seconds=300)  # 5 minutes

# Dynamic data (short TTL)
ResultCache(default_ttl_seconds=60)  # 1 minute
```

### Idempotency Keys
Use for deterministic caching:
```python
# Good: Semantic idempotency key
ExecutionOptions(idempotency_key="lint-src-v1.2.3")

# Good: Content-based key
content_hash = hashlib.sha256(file_content.encode()).hexdigest()[:16]
ExecutionOptions(idempotency_key=f"analyze-{content_hash}")
```

### Invalidation Strategy
Invalidate on file changes:
```python
# File modified - invalidate related cache
async def on_file_change(file_path: str):
    # Invalidate Read results for this file
    await cache.invalidate(ToolInvokeRequest(
        tool_id="Read",
        parameters={"file_path": file_path}
    ))

    # Invalidate Glob/Grep that might include this file
    await cache.invalidate_tool("Glob")
    await cache.invalidate_tool("Grep")
```

### Cache Key Prefix
Use meaningful prefixes for debugging:
```python
# Development
ResultCache(key_prefix="dev:tool:result:")

# Production
ResultCache(key_prefix="prod:tool:result:")

# Per-tenant
ResultCache(key_prefix=f"tenant:{tenant_id}:tool:result:")
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/result_cache.py`
- Models: `platform/src/L03_tool_execution/models/tool_result.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3 architecture with Redis 7 backend

## Related Services

- ToolExecutor (L03) - Caches execution results
- ToolComposer (L03) - Uses cache for compositions
- ToolRegistry (L03) - Tool metadata (not cached here)
- StateManager (L02) - Different caching (agent state)
- SemanticCache (L04) - LLM response caching

---
*Generated: 2026-01-24 | Platform Services Documentation*
