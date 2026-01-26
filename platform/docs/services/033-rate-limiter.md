# Service 33/44: RateLimiter

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.rate_limiter` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | Redis |
| **Category** | AI/ML / Request Throttling |

## Role in Development Environment

The **RateLimiter** provides distributed rate limiting using the token bucket algorithm with Redis backend. It provides:
- Requests per minute (RPM) limiting per agent/provider
- Tokens per minute (TPM) limiting per agent/provider
- Token bucket algorithm for smooth rate limiting
- Distributed state via Redis for multi-instance deployments
- Per-agent and per-provider usage tracking
- Fail-open behavior on Redis errors

This is **the request throttling layer for LLM inference** - preventing agents from exceeding provider rate limits and ensuring fair resource sharing across agents.

## Data Model

### Redis Key Structure
- `ratelimit:rpm:{agent_did}:{provider}` - RPM bucket
- `ratelimit:tpm:{agent_did}:{provider}` - TPM bucket

### Bucket State
- `tokens: float` - Available tokens
- `last_refill: float` - Timestamp of last refill

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `redis_url` | redis://localhost:6379 | Redis connection URL |
| `default_rpm` | 60 | Default requests per minute limit |
| `default_tpm` | 100000 | Default tokens per minute limit |

## API Methods

| Method | Description |
|--------|-------------|
| `check_rate_limit(agent_did, provider, tokens, ...)` | Check and consume rate limits |
| `check_limit(agent_id, tokens, ...)` | Alias with simplified parameters |
| `get_usage(agent_did, provider)` | Get current usage for agent/provider |
| `reset(agent_did, provider)` | Reset rate limits |
| `close()` | Close Redis connection |

## Use Cases in Your Workflow

### 1. Initialize Rate Limiter
```python
from L04_model_gateway.services.rate_limiter import RateLimiter

# Default initialization
limiter = RateLimiter()

# With custom limits
limiter = RateLimiter(
    redis_url="redis://localhost:6379",
    default_rpm=120,      # 120 requests per minute
    default_tpm=200000    # 200k tokens per minute
)
```

### 2. Check Rate Limit Before Inference
```python
from L04_model_gateway.models import RateLimitError

agent_did = "did:agent:abc123"
provider = "anthropic"
estimated_tokens = 500

try:
    # Check if request is allowed
    await limiter.check_rate_limit(
        agent_did=agent_did,
        provider=provider,
        tokens=estimated_tokens
    )
    # Proceed with inference
    response = await gateway.execute(request)

except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    print(f"Limit: {e.details.get('limit')}")
```

### 3. Check with Custom Limits
```python
# Override default limits for specific request
await limiter.check_rate_limit(
    agent_did="did:agent:premium",
    provider="openai",
    tokens=1000,
    rpm_limit=200,      # Higher RPM for premium agent
    tpm_limit=500000    # Higher TPM for premium agent
)
```

### 4. Use Simplified check_limit Method
```python
# Convenient alias
await limiter.check_limit(
    agent_id="did:agent:abc123",
    tokens=500,
    provider="anthropic"
)
```

### 5. Get Current Usage
```python
# Check how much of the limit has been consumed
usage = await limiter.get_usage(
    agent_did="did:agent:abc123",
    provider="anthropic"
)

print(f"RPM: {usage['rpm']['used']}/{usage['rpm']['capacity']}")
print(f"TPM: {usage['tpm']['used']}/{usage['tpm']['capacity']}")
print(f"RPM available: {usage['rpm']['available']}")
print(f"TPM available: {usage['tpm']['available']}")
```

### 6. Reset Rate Limits
```python
# Reset limits (e.g., for testing or after fixing issues)
await limiter.reset(
    agent_did="did:agent:abc123",
    provider="anthropic"
)
print("Rate limits reset")
```

### 7. Handle Rate Limit Errors
```python
from L04_model_gateway.models import RateLimitError, L04ErrorCode

try:
    await limiter.check_rate_limit(agent_did, provider, tokens)

except RateLimitError as e:
    if e.code == L04ErrorCode.E4404_RPM_LIMIT_EXCEEDED:
        print(f"Too many requests/minute")
        # Wait before retry
        await asyncio.sleep(60)

    elif e.code == L04ErrorCode.E4405_TPM_LIMIT_EXCEEDED:
        print(f"Too many tokens/minute")
        # Use smaller request or wait
        await asyncio.sleep(60)
```

### 8. Integration with ModelGateway
```python
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.services.rate_limiter import RateLimiter

# Create rate limiter
limiter = RateLimiter(
    default_rpm=60,
    default_tpm=100000
)

# Inject into gateway
gateway = ModelGateway(rate_limiter=limiter)

# Gateway uses limiter before every inference
response = await gateway.execute(request)
```

### 9. Cleanup
```python
# Close Redis connection
await limiter.close()
```

## Service Interactions

```
+------------------+
|   RateLimiter    | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Uses:
         |
+--------+--------+
|                 |
v                 v
Redis           ModelGateway
(State)         (Consumer)
```

**Integration Points:**
- **Redis**: Stores token bucket state for distributed limiting
- **ModelGateway (L04)**: Checks limits before every inference
- **InferenceRequest (L04)**: Provides agent_did and token count

## Token Bucket Algorithm

```
Token Bucket Flow:

1. Request arrives with N tokens

2. Calculate available tokens:
   - Time elapsed since last refill
   - Tokens refilled = (elapsed / 60) * capacity
   - Available = min(capacity, previous + refilled)

3. If available >= N:
   - Consume N tokens
   - Update bucket state
   - Allow request

4. If available < N:
   - Reject request
   - Raise RateLimitError
```

### Token Bucket Visualization
```
Capacity: 60 tokens (60 RPM)
Refill rate: 1 token per second

Time 0:   [████████████████████████] 60/60 tokens
Request:  [Consume 1]
Time 0:   [███████████████████████ ] 59/60 tokens

Time 1:   [████████████████████████] 60/60 tokens (refilled)
Request:  [Consume 1]
Time 1:   [███████████████████████ ] 59/60 tokens

...burst of 50 requests...

Time 5:   [██████                  ] 14/60 tokens
Request:  [Consume 1]
Time 5:   [█████                   ] 13/60 tokens

...wait 47 seconds for refill...

Time 52:  [████████████████████████] 60/60 tokens
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4400 | Rate limit exceeded (general) | Yes |
| E4404 | RPM limit exceeded | Yes |
| E4405 | TPM limit exceeded | Yes |

## Execution Examples

```python
# Complete rate limiting workflow
from L04_model_gateway.services.rate_limiter import RateLimiter
from L04_model_gateway.models import RateLimitError, L04ErrorCode
import asyncio

# Initialize
limiter = RateLimiter(
    redis_url="redis://localhost:6379",
    default_rpm=60,
    default_tpm=100000
)

agent_did = "did:agent:test"
provider = "anthropic"

# 1. Check and consume rate limit
try:
    await limiter.check_rate_limit(
        agent_did=agent_did,
        provider=provider,
        tokens=500
    )
    print("Request allowed")

except RateLimitError as e:
    print(f"Rate limited: {e.message}")

# 2. Get current usage
usage = await limiter.get_usage(agent_did, provider)
print(f"RPM: {usage['rpm']['used']}/{usage['rpm']['capacity']}")
print(f"TPM: {usage['tpm']['used']}/{usage['tpm']['capacity']}")

# 3. Simulate burst of requests
for i in range(10):
    try:
        await limiter.check_rate_limit(agent_did, provider, tokens=100)
        print(f"Request {i+1} allowed")
    except RateLimitError as e:
        print(f"Request {i+1} rejected: {e.message}")
        break

# 4. Check usage after burst
usage = await limiter.get_usage(agent_did, provider)
print(f"After burst - RPM used: {usage['rpm']['used']}")

# 5. Reset and verify
await limiter.reset(agent_did, provider)
usage = await limiter.get_usage(agent_did, provider)
print(f"After reset - RPM used: {usage['rpm']['used']}")  # 0

# 6. Cleanup
await limiter.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| check_rate_limit() | Complete |
| check_limit() | Complete |
| Token Bucket Algorithm | Complete |
| RPM Limiting | Complete |
| TPM Limiting | Complete |
| get_usage() | Complete |
| reset() | Complete |
| Redis Backend | Complete |
| close() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Per-Model Limits | High | Different limits per model |
| Sliding Window | Medium | Alternative algorithm |
| Quota Management | Medium | Daily/monthly quotas |
| Rate Limit Headers | Low | Return X-RateLimit headers |
| Prometheus Metrics | Low | Export rate limit metrics |
| Local Cache | Low | Reduce Redis calls |

## Strengths

- **Distributed** - Redis backend for multi-instance
- **Token bucket** - Smooth rate limiting, allows bursts
- **Dual limits** - Both RPM and TPM enforced
- **Fail-open** - Allows requests on Redis errors
- **Per-agent tracking** - Fair sharing across agents
- **Reset capability** - Manual override when needed

## Weaknesses

- **Redis dependency** - Requires Redis to be available
- **No per-model limits** - Same limits for all models
- **No quotas** - Only rate limits, not usage quotas
- **No local cache** - Every check hits Redis
- **Single algorithm** - Only token bucket
- **No priority** - All agents treated equally

## Best Practices

### Limit Configuration
Set limits based on provider constraints:
```python
# Anthropic limits (example)
RateLimiter(default_rpm=60, default_tpm=100000)

# OpenAI limits (example)
RateLimiter(default_rpm=500, default_tpm=90000)

# Conservative shared limits
RateLimiter(default_rpm=30, default_tpm=50000)
```

### Error Handling
Always handle rate limit errors:
```python
async def execute_with_retry(request, max_retries=3):
    for attempt in range(max_retries):
        try:
            await limiter.check_rate_limit(...)
            return await gateway.execute(request)
        except RateLimitError:
            if attempt < max_retries - 1:
                await asyncio.sleep(60)  # Wait for refill
            else:
                raise
```

### Monitoring
Track rate limit usage:
```python
async def monitor_usage(limiter, agents, providers):
    for agent in agents:
        for provider in providers:
            usage = await limiter.get_usage(agent, provider)
            logger.info(
                f"{agent}@{provider}: "
                f"RPM {usage['rpm']['used']}/{usage['rpm']['capacity']}, "
                f"TPM {usage['tpm']['used']}/{usage['tpm']['capacity']}"
            )
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/rate_limiter.py`
- Models: `platform/src/L04_model_gateway/models/errors.py`
- Error Codes: `platform/src/L04_model_gateway/models/__init__.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelGateway (L04) - Uses rate limiter before inference
- CircuitBreaker (L04) - Complementary fault tolerance
- RequestQueue (L04) - Buffers requests when rate limited
- SemanticCache (L04) - Cached responses bypass limits
- Redis - Rate limit state storage

---
*Generated: 2026-01-24 | Platform Services Documentation*
