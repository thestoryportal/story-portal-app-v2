# Service 32/44: SemanticCache

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.semantic_cache` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | Redis, Ollama (embeddings) |
| **Category** | AI/ML / Response Caching |

## Role in Development Environment

The **SemanticCache** provides intelligent caching of LLM responses using embeddings and cosine similarity. It provides:
- Exact match caching with SHA-256 hashed cache keys
- Semantic similarity matching using vector embeddings
- Configurable similarity threshold for cache hits
- TTL-based cache expiration
- Selective invalidation by pattern, model, or age
- Cache warming for known request/response pairs
- Hit rate statistics and health monitoring

This is **the intelligent caching layer for LLM responses** - when similar prompts are submitted, SemanticCache can return cached responses without re-executing the LLM inference, dramatically reducing latency and cost.

## Data Model

### Cache Key Structure
- `cache:exact:{hash}` - Serialized response for exact match
- `cache:embedding:{hash}` - Embedding vector + metadata
- `cache:meta:{hash}` - Metadata for quick lookups

### Cache Statistics
- `hits: int` - Number of cache hits
- `misses: int` - Number of cache misses
- `writes: int` - Number of cache writes
- `errors: int` - Number of cache errors

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `redis_url` | redis://localhost:6379 | Redis connection URL |
| `ttl_seconds` | 3600 | Cache TTL (1 hour) |
| `similarity_threshold` | 0.85 | Minimum similarity for semantic hit |
| `embedding_model` | nomic-embed-text | Ollama model for embeddings |
| `ollama_base_url` | http://localhost:11434 | Ollama API URL |
| `enable_embeddings` | True | Enable semantic matching |

## API Methods

| Method | Description |
|--------|-------------|
| `get(request)` | Get cached response for request |
| `set(request, response)` | Cache a response |
| `clear()` | Clear all cache entries |
| `invalidate(pattern, model_id, older_than)` | Selective invalidation |
| `warm_cache(requests, responses)` | Pre-warm cache |
| `get_stats()` | Get cache statistics |
| `get_health_status()` | Get health status |
| `close()` | Close Redis connection |

## Use Cases in Your Workflow

### 1. Initialize Semantic Cache
```python
from L04_model_gateway.services.semantic_cache import SemanticCache

# Default initialization
cache = SemanticCache()

# With custom configuration
cache = SemanticCache(
    redis_url="redis://localhost:6379",
    ttl_seconds=7200,           # 2 hours
    similarity_threshold=0.90,   # Higher threshold = more exact
    embedding_model="nomic-embed-text",
    ollama_base_url="http://localhost:11434",
    enable_embeddings=True
)
```

### 2. Check Cache Before Inference
```python
from L04_model_gateway.models import InferenceRequest, Message, MessageRole

# Create request
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[
        Message(role=MessageRole.USER, content="What is Python?")
    ],
    temperature=0.7,
    max_tokens=500
)

# Check cache first
cached_response = await cache.get(request)

if cached_response:
    print(f"Cache hit! Latency: {cached_response.latency_ms}ms")  # 0ms
    print(f"Content: {cached_response.content}")
else:
    print("Cache miss - executing inference")
    response = await gateway.execute(request)
    # Cache the response
    await cache.set(request, response)
```

### 3. Semantic Similarity Matching
```python
# First request
request1 = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[
        Message(role=MessageRole.USER, content="What is Python programming?")
    ]
)
response = await gateway.execute(request1)
await cache.set(request1, response)

# Similar request - will hit cache if similarity >= threshold
request2 = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[
        Message(role=MessageRole.USER, content="Tell me about Python programming")
    ]
)

# This may return cached response due to semantic similarity
cached = await cache.get(request2)
if cached:
    print("Semantic cache hit!")
    print(f"Response: {cached.content}")
```

### 4. Cache Statistics
```python
# Get cache statistics
stats = cache.get_stats()

print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Writes: {stats['writes']}")
print(f"Errors: {stats['errors']}")
print(f"Hit Rate: {stats['hit_rate']:.2%}")
print(f"Total Requests: {stats['total_requests']}")
```

### 5. Selective Invalidation
```python
from datetime import datetime, timedelta

# Invalidate by pattern
count = await cache.invalidate(pattern="*modal*")
print(f"Invalidated {count} entries matching *modal*")

# Invalidate by model
count = await cache.invalidate(model_id="gpt-4")
print(f"Invalidated {count} GPT-4 entries")

# Invalidate old entries
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
count = await cache.invalidate(older_than=one_hour_ago)
print(f"Invalidated {count} entries older than 1 hour")

# Combine filters
count = await cache.invalidate(
    model_id="claude-3-opus",
    older_than=one_hour_ago
)
```

### 6. Warm Cache
```python
# Pre-warm cache with known good responses
known_requests = [request1, request2, request3]
known_responses = [response1, response2, response3]

added = await cache.warm_cache(known_requests, known_responses)
print(f"Warmed cache with {added} entries")
```

### 7. Clear Cache
```python
# Clear all cache entries
await cache.clear()
print("Cache cleared")
```

### 8. Health Check
```python
# Get cache health status
health = cache.get_health_status()

print(f"Healthy: {health['healthy']}")
print(f"Redis Connected: {health['redis_connected']}")
print(f"Embeddings Enabled: {health['embeddings_enabled']}")
print(f"TTL: {health['config']['ttl_seconds']}s")
print(f"Similarity Threshold: {health['config']['similarity_threshold']}")
```

### 9. Disable Embeddings (Exact Match Only)
```python
# For faster but less flexible caching
cache = SemanticCache(
    enable_embeddings=False  # Only exact match
)

# Only exact same requests will hit cache
```

### 10. Handle Cache Errors
```python
from L04_model_gateway.models import CacheError, L04ErrorCode

try:
    await cache.clear()
except CacheError as e:
    if e.code == L04ErrorCode.E4301_CACHE_UNAVAILABLE:
        print("Redis not available")
    elif e.code == L04ErrorCode.E4300_CACHE_ERROR:
        print(f"Cache error: {e.message}")
```

## Service Interactions

```
+------------------+
|  SemanticCache   | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Uses:
         |
+--------+--------+--------+
|                 |        |
v                 v        v
Redis           Ollama   InferenceRequest/
(Storage)       (Embed)  Response (L04)
```

**Integration Points:**
- **Redis**: Stores cached responses and embeddings
- **Ollama**: Generates embeddings for semantic matching
- **ModelGateway (L04)**: Uses cache before/after inference
- **InferenceRequest/Response (L04)**: Request/response models

## Cache Lookup Flow

```
1. get(request)
   │
   ├── Generate cache key (SHA-256 hash)
   │   └── Hash: messages + system_prompt + temp + tokens + capabilities
   │
   ├── Try exact match
   │   └── Redis GET cache:exact:{hash}
   │   └── Found → Return (cache hit)
   │
   ├── Try semantic match (if enabled)
   │   ├── Generate embedding for request
   │   ├── Scan all cache:embedding:* keys
   │   ├── Compute cosine similarity
   │   ├── Find best match >= threshold
   │   └── Return cached response if found
   │
   └── Return None (cache miss)
```

## Cache Storage Flow

```
1. set(request, response)
   │
   ├── Generate cache key
   │
   ├── Store exact match
   │   └── Redis SETEX cache:exact:{hash} {TTL} {response}
   │
   └── Store embedding (if enabled)
       ├── Generate embedding via Ollama
       ├── Store in cache:embedding:{hash}
       │   ├── embedding: vector
       │   ├── cache_key: hash
       │   ├── request_id: id
       │   ├── model_id: model
       │   └── timestamp: now
       └── Store metadata in cache:meta:{hash}
```

## Similarity Matching

### Cosine Similarity
```python
similarity = dot_product(vec1, vec2) / (norm(vec1) * norm(vec2))

# Examples:
# similarity = 1.0  → Identical
# similarity = 0.9  → Very similar (likely same intent)
# similarity = 0.85 → Similar (default threshold)
# similarity = 0.7  → Somewhat related
# similarity = 0.0  → Unrelated
```

### Threshold Selection
```python
# Higher threshold (0.90-0.95) - More conservative
# - Fewer false positives
# - Lower hit rate
# - Use for precise matching

# Default threshold (0.85)
# - Good balance of hits vs accuracy
# - Suitable for most use cases

# Lower threshold (0.75-0.80) - More aggressive
# - More cache hits
# - May return less relevant responses
# - Use for cost optimization
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4300 | Cache error | Depends |
| E4301 | Cache unavailable | Yes |

## Execution Examples

```python
# Complete caching workflow
from L04_model_gateway.services.semantic_cache import SemanticCache
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.models import (
    InferenceRequest,
    Message,
    MessageRole
)

# Initialize with custom settings
cache = SemanticCache(
    redis_url="redis://localhost:6379",
    ttl_seconds=3600,
    similarity_threshold=0.85,
    enable_embeddings=True
)

# Initialize gateway with cache
gateway = ModelGateway(cache=cache)

# 1. First request (cache miss)
request1 = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Explain async/await in Python")
    ],
    temperature=0.7,
    max_tokens=500,
    enable_cache=True
)

cached = await cache.get(request1)
print(f"First request cached: {cached is not None}")  # False

response1 = await gateway.execute(request1)
await cache.set(request1, response1)
print(f"Response cached, latency: {response1.latency_ms}ms")

# 2. Exact same request (cache hit)
cached = await cache.get(request1)
print(f"Exact match cached: {cached is not None}")  # True
print(f"Cached latency: {cached.latency_ms}ms")  # 0ms

# 3. Similar request (semantic cache hit)
request2 = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="How does async/await work in Python?")
    ],
    temperature=0.7,
    max_tokens=500,
    enable_cache=True
)

cached = await cache.get(request2)
if cached:
    print("Semantic cache hit!")
    print(f"Content: {cached.content[:100]}...")
else:
    print("Cache miss - different enough to warrant new inference")

# 4. Check statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Total: {stats['total_requests']} requests")

# 5. Health status
health = cache.get_health_status()
print(f"Cache healthy: {health['healthy']}")
print(f"Redis connected: {health['redis_connected']}")

# 6. Selective invalidation
invalidated = await cache.invalidate(model_id="gpt-4")
print(f"Invalidated {invalidated} GPT-4 entries")

# 7. Warm cache with known pairs
common_requests = [...]
common_responses = [...]
warmed = await cache.warm_cache(common_requests, common_responses)
print(f"Warmed {warmed} entries")

# 8. Cleanup
await cache.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Exact Match Caching | Complete |
| Semantic Similarity | Complete |
| Embedding Generation | Complete |
| Cosine Similarity | Complete |
| TTL Expiration | Complete |
| Selective Invalidation | Complete |
| Cache Warming | Complete |
| Statistics | Complete |
| Health Status | Complete |
| close() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Vector Search Index | High | Use Redis Vector Search instead of scan |
| Embedding Caching | Medium | Cache embeddings themselves |
| Batch Embedding | Medium | Generate multiple embeddings in one call |
| Prometheus Metrics | Low | Export cache metrics |
| Multiple Redis Nodes | Low | Redis cluster support |
| Alternative Embeddings | Low | Support non-Ollama embedding providers |

## Strengths

- **Semantic matching** - Finds similar prompts, not just exact
- **Two-tier caching** - Exact + semantic for best hit rate
- **Configurable threshold** - Balance precision vs recall
- **Selective invalidation** - Granular cache control
- **Cache warming** - Pre-populate for known patterns
- **Graceful degradation** - Falls back to exact match if embeddings fail
- **Statistics tracking** - Monitor cache effectiveness

## Weaknesses

- **Scan-based similarity** - O(n) scan of all embeddings
- **No vector index** - Redis Vector Search not used
- **Single embedding model** - Fixed to Ollama only
- **Memory usage** - Embeddings take space
- **Embedding latency** - Generation adds to cache set time
- **No batching** - Single embedding at a time
- **Redis dependency** - Requires Redis to be available

## Best Practices

### Threshold Tuning
Match threshold to use case:
```python
# Precise matching (code, technical)
SemanticCache(similarity_threshold=0.92)

# General matching (conversation)
SemanticCache(similarity_threshold=0.85)

# Aggressive caching (cost optimization)
SemanticCache(similarity_threshold=0.78)
```

### TTL Configuration
Set TTL based on content freshness:
```python
# Static content (documentation, tutorials)
SemanticCache(ttl_seconds=86400)  # 24 hours

# Dynamic content (news, real-time data)
SemanticCache(ttl_seconds=300)  # 5 minutes

# Standard usage
SemanticCache(ttl_seconds=3600)  # 1 hour
```

### Cache Bypass
Know when to bypass cache:
```python
# Dynamic/time-sensitive requests
request = InferenceRequest.create(
    messages=[...],
    enable_cache=False  # Bypass cache
)

# Or invalidate before request
await cache.invalidate(pattern="time-sensitive-*")
```

### Monitoring
Track cache effectiveness:
```python
# Log cache stats periodically
import asyncio

async def monitor_cache(cache, interval=60):
    while True:
        stats = cache.get_stats()
        logger.info(f"Cache hit rate: {stats['hit_rate']:.2%}")
        await asyncio.sleep(interval)
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/semantic_cache.py`
- Models: `platform/src/L04_model_gateway/models/errors.py`
- Error Codes: `platform/src/L04_model_gateway/models/__init__.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelGateway (L04) - Uses cache for inference
- LLMRouter (L04) - Routes after cache miss
- RateLimiter (L04) - Applied before cache check
- CircuitBreaker (L04) - Protects cache backend
- Redis - Cache storage backend
- Ollama - Embedding generation

---
*Generated: 2026-01-24 | Platform Services Documentation*
