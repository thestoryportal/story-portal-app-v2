# Service 43/44: PlanCache

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.plan_cache` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | Redis (optional for L2 cache) |
| **Category** | Planning / Caching |

## Role in Development Environment

The **PlanCache** provides a two-level caching system for execution plans to avoid redundant goal decomposition. It provides:
- L1 in-memory cache with LRU eviction
- L2 Redis cache with TTL-based expiration
- SHA-256 based cache key generation
- Automatic L2→L1 promotion on cache hits
- Cache statistics and hit rate tracking
- Graceful degradation if Redis unavailable

This is **the performance optimization layer for planning** - when agents submit goals that have been processed before, PlanCache returns cached plans instantly without LLM calls.

## Data Model

### Cache Architecture
```
Goal Text → SHA-256 Hash → Cache Key
                            ↓
            ┌───────────────┴───────────────┐
            │                               │
        L1 Cache                        L2 Cache
    (In-Memory LRU)                    (Redis TTL)
        ↓                                   ↓
    Fast access                      Persistent storage
    Process-local                    Shared across instances
```

### Cache Entry
- `key: str` - SHA-256 hash of normalized goal text
- `value: ExecutionPlan` - Cached execution plan
- `timestamp: datetime` - When entry was cached

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `l1_max_size` | 100 | Maximum L1 cache entries |
| `l2_ttl_seconds` | 3600 | TTL for Redis cache (1 hour) |
| `enable_l2` | True | Enable Redis L2 cache |

## API Methods

| Method | Description |
|--------|-------------|
| `get(goal_text)` | Get cached plan (L1 then L2) |
| `set(goal_text, plan, ttl)` | Store plan in both caches |
| `invalidate(goal_text)` | Remove plan from caches |
| `clear()` | Clear all caches |
| `get_stats()` | Get cache statistics |

## Use Cases in Your Workflow

### 1. Initialize Plan Cache
```python
from L05_planning.services.plan_cache import PlanCache

# Default configuration
cache = PlanCache()

# Custom configuration
cache = PlanCache(
    l1_max_size=200,
    l2_ttl_seconds=7200,  # 2 hours
    enable_l2=True
)

# In-memory only mode
cache = PlanCache(enable_l2=False)
```

### 2. Get Cached Plan
```python
# Look up cached plan
plan = await cache.get("Create a REST API for user management")

if plan:
    print(f"Cache hit! Plan ID: {plan.plan_id}")
    print(f"Tasks: {len(plan.tasks)}")
else:
    print("Cache miss - need to decompose goal")
```

### 3. Store Plan in Cache
```python
# Cache a newly decomposed plan
await cache.set(
    goal_text="Create a REST API for user management",
    plan=plan,
)

# With custom TTL
await cache.set(
    goal_text="Deploy application",
    plan=plan,
    ttl_seconds=1800,  # 30 minutes
)
```

### 4. Invalidate Cached Plan
```python
# Invalidate specific goal's plan
await cache.invalidate("Create a REST API for user management")

# Plan will be recomputed on next access
```

### 5. Clear All Caches
```python
# Clear both L1 and L2 caches
await cache.clear()

print("All cached plans removed")
```

### 6. Get Cache Statistics
```python
stats = cache.get_stats()

print(f"L1 cache size: {stats['l1_size']}/{stats['l1_max_size']}")
print(f"L1 hit rate: {stats['l1_hit_rate']:.1%}")
print(f"L2 connected: {stats['l2_connected']}")
print(f"L2 hit rate: {stats['l2_hit_rate']:.1%}")
```

### 7. Integration with GoalDecomposer
```python
from L05_planning.services.goal_decomposer import GoalDecomposer
from L05_planning.services.plan_cache import PlanCache

# Create cache
cache = PlanCache()

# Inject into decomposer
decomposer = GoalDecomposer(cache=cache)

# Cache is automatically used during decomposition
plan = await decomposer.decompose(goal)  # Uses cache internally
```

### 8. Monitor Cache Performance
```python
# Periodic monitoring
stats = cache.get_stats()

# Check L1 hit rate
if stats['l1_hit_rate'] < 0.5:
    print("Warning: Low L1 hit rate, consider increasing size")

# Check L2 status
if not stats['l2_connected'] and cache.enable_l2:
    print("Warning: Redis L2 cache not connected")

# Total hit rate
total_hits = stats['l1_hits'] + stats['l2_hits']
total_attempts = total_hits + stats['l1_misses']
hit_rate = total_hits / max(1, total_attempts)
print(f"Overall hit rate: {hit_rate:.1%}")
```

### 9. Distributed Caching
```python
# Multiple instances share Redis L2 cache
#
# Instance A:
cache_a = PlanCache(enable_l2=True)
await cache_a.set("goal-1", plan)  # Stored in Redis

# Instance B:
cache_b = PlanCache(enable_l2=True)
plan = await cache_b.get("goal-1")  # Retrieved from Redis
# Also promoted to Instance B's L1 cache
```

### 10. Graceful Degradation
```python
# If Redis is unavailable, L2 is automatically disabled
cache = PlanCache(enable_l2=True)

# First L2 access will attempt connection
plan = await cache.get("some goal")

# Check if L2 was disabled
stats = cache.get_stats()
if not stats['l2_connected']:
    print("Running in L1-only mode")
```

## Service Interactions

```
+-------------------+
|    PlanCache      | <--- L05 Planning Layer
|       (L05)       |
+--------+----------+
         |
   Provides:
         |
+--------+--------+
|                 |
v                 v
L1 Cache       L2 Cache
(In-Memory)    (Redis)
    ↓              ↓
LRU Eviction   TTL Expiration
```

**Integration Points:**
- **GoalDecomposer (L05)**: Primary user of cache
- **PlanningService (L05)**: Uses decomposer with cache
- **Redis (External)**: L2 persistent cache

## Cache Workflow

```
Cache Lookup Flow:
                     GET(goal_text)
                           │
                     ┌─────▼─────┐
                     │ Hash Key  │
                     │ (SHA-256) │
                     └─────┬─────┘
                           │
                     ┌─────▼─────┐
              ┌──Yes─┤ L1 Hit?  │
              │      └─────┬─────┘
              │            │ No
         Return Plan       │
              │      ┌─────▼─────┐
              │  ┌───┤ L2 Enabled│
              │  │   └─────┬─────┘
              │  │ No      │ Yes
              │  │   ┌─────▼─────┐
              │  │   │ L2 Hit?   │
              │  │   └─────┬─────┘
              │  │    Yes  │ No
              │  │    ↓    │
              │  │ Promote │
              │  │ to L1   │
              │  │    ↓    │
              │  └─>Return │──> Return None
              │      Plan  │
              │            ↓
              └────────────────────> Return Plan


Cache Store Flow:
                     SET(goal_text, plan)
                           │
                     ┌─────▼─────┐
                     │ Hash Key  │
                     │ (SHA-256) │
                     └─────┬─────┘
                           │
                     ┌─────▼─────┐
                     │ L1 at max?│
                     └─────┬─────┘
                      Yes  │ No
                       ↓   │
                  LRU Evict│
                       ↓   │
                     Store in L1
                           │
                     ┌─────▼─────┐
                     │ L2 Enabled│
                     └─────┬─────┘
                           │ Yes
                     Store in L2
                     (with TTL)
```

## Cache Key Generation

```python
# Goal text normalization
normalized = " ".join(goal_text[:1000].split())
# SHA-256 hash
cache_key = hashlib.sha256(normalized.encode()).hexdigest()

# Example:
# Goal: "Create  a  REST  API"
# Normalized: "Create a REST API"
# Key: "e3b0c44298fc1c..."
```

## Execution Examples

```python
# Complete plan caching workflow
from L05_planning.services.plan_cache import PlanCache
from L05_planning.models import ExecutionPlan, Task, TaskType

# Initialize cache
cache = PlanCache(
    l1_max_size=50,
    l2_ttl_seconds=3600,
    enable_l2=True
)

# 1. Create a plan
plan = ExecutionPlan.create(goal_id="goal-123")
task = Task.create(
    plan_id=plan.plan_id,
    name="Setup environment",
    description="Initialize project",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
plan.add_task(task)

goal_text = "Create a REST API for user management"

# 2. Cache miss (first access)
cached = await cache.get(goal_text)
print(f"First access: {cached}")  # None

# 3. Store plan
await cache.set(goal_text, plan)
print(f"Plan cached: {plan.plan_id}")

# 4. Cache hit (L1)
cached = await cache.get(goal_text)
print(f"Second access: {cached.plan_id}")  # Same plan ID

# 5. Check statistics
stats = cache.get_stats()
print(f"\nCache stats:")
print(f"  L1 size: {stats['l1_size']}/{stats['l1_max_size']}")
print(f"  L1 hits: {stats['l1_hits']}")
print(f"  L1 misses: {stats['l1_misses']}")
print(f"  L1 hit rate: {stats['l1_hit_rate']:.1%}")
print(f"  L2 connected: {stats['l2_connected']}")

# 6. Invalidate
await cache.invalidate(goal_text)
print(f"\nPlan invalidated")

# 7. Cache miss again
cached = await cache.get(goal_text)
print(f"After invalidation: {cached}")  # None

# 8. Test LRU eviction
print(f"\nTesting LRU eviction...")
for i in range(60):  # More than max_size (50)
    test_plan = ExecutionPlan.create(goal_id=f"goal-{i}")
    await cache.set(f"Goal {i}", test_plan)

stats = cache.get_stats()
print(f"L1 size after 60 inserts: {stats['l1_size']}")  # 50 (max)

# 9. Clear caches
await cache.clear()
stats = cache.get_stats()
print(f"\nL1 size after clear: {stats['l1_size']}")  # 0
```

## Implementation Status

| Component | Status |
|-----------|--------|
| PlanCache class | Complete |
| L1 in-memory cache | Complete |
| LRU eviction | Complete |
| L2 Redis cache | Complete |
| TTL expiration | Complete |
| Cache key generation | Complete |
| get() | Complete |
| set() | Complete |
| invalidate() | Complete |
| clear() | Complete |
| get_stats() | Complete |
| Redis connection pooling | Partial |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Connection pooling | Medium | Use connection pool for Redis |
| Semantic similarity | Medium | Cache based on goal similarity |
| Cache warming | Low | Preload common plans |
| Cluster support | Low | Redis cluster mode |
| Metrics export | Low | Prometheus cache metrics |
| L1 size auto-tuning | Low | Dynamic sizing based on memory |

## Strengths

- **Two-level architecture** - Fast L1 + persistent L2
- **LRU eviction** - Keeps hot plans in memory
- **Graceful degradation** - Works without Redis
- **Simple key generation** - Consistent SHA-256 hashing
- **Automatic promotion** - L2 hits cached in L1
- **Configurable TTL** - Control cache freshness

## Weaknesses

- **Exact match only** - No semantic similarity
- **No cache warming** - Cold start on restart
- **Basic Redis connection** - No connection pooling
- **Single Redis instance** - No cluster support
- **Process-local L1** - Not shared across instances
- **No eviction callbacks** - Can't notify on eviction

## Best Practices

### Size Configuration
Choose L1 size based on memory:
```python
# Rule of thumb: 1MB per cached plan
# 100 plans ≈ 100MB memory usage
cache = PlanCache(l1_max_size=100)

# For memory-constrained environments
cache = PlanCache(l1_max_size=25)

# For large memory systems
cache = PlanCache(l1_max_size=500)
```

### TTL Configuration
Choose TTL based on goal volatility:
```python
# Stable goals (infrastructure, deployment)
cache = PlanCache(l2_ttl_seconds=86400)  # 24 hours

# Dynamic goals (development, testing)
cache = PlanCache(l2_ttl_seconds=3600)  # 1 hour

# Frequently changing goals
cache = PlanCache(l2_ttl_seconds=300)  # 5 minutes
```

### Monitoring
Track cache performance:
```python
stats = cache.get_stats()

# Alert on low hit rate
if stats['l1_hit_rate'] < 0.3:
    logger.warning("Low L1 cache hit rate")

# Alert on Redis disconnect
if cache.enable_l2 and not stats['l2_connected']:
    logger.error("Redis L2 cache disconnected")
```

## Source Files

- Service: `platform/src/L05_planning/services/plan_cache.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- GoalDecomposer (L05) - Primary cache user
- PlanningService (L05) - Uses decomposer with cache
- TemplateRegistry (L05) - Complementary caching
- Redis (External) - L2 backing store

---
*Generated: 2026-01-24 | Platform Services Documentation*
