# Service 30/44: ModelGateway

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.model_gateway` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ModelRegistry, LLMRouter, SemanticCache, RateLimiter, CircuitBreaker, RequestQueue, Provider Adapters |
| **Category** | AI/ML / LLM Orchestration |

## Role in Development Environment

The **ModelGateway** is the central coordinator for all LLM inference operations. It provides:
- Unified inference API with caching and rate limiting
- Intelligent model routing with capability matching
- Automatic failover to fallback models
- Streaming inference support
- Circuit breaker protection against provider failures
- L01 integration for usage tracking
- Health monitoring across all providers

This is **the main entry point for all LLM requests** - when any layer needs LLM inference (agents, tools, analysis), ModelGateway coordinates the entire request lifecycle from rate limiting through execution to caching.

## Data Model

### InferenceRequest (key fields)
- `request_id: UUID` - Unique request identifier
- `agent_did: str` - Agent making request
- `messages: List[Message]` - Chat messages
- `system_prompt: Optional[str]` - System prompt
- `temperature: float` - Sampling temperature
- `max_tokens: int` - Maximum output tokens
- `capabilities: List[str]` - Required capabilities
- `enable_cache: bool` - Enable response caching
- `metadata: Dict` - Request metadata

### InferenceResponse (key fields)
- `request_id: UUID` - Matching request ID
- `content: str` - Generated content
- `model_id: str` - Model used
- `provider: str` - Provider used
- `token_usage: TokenUsage` - Token counts
- `latency_ms: float` - Response latency
- `cached: bool` - Whether from cache

### RoutingStrategy Enum
- `FASTEST` - Optimize for speed
- `CHEAPEST` - Optimize for cost
- `BEST_QUALITY` - Optimize for quality
- `BALANCED` - Balance all factors
- `CAPABILITY_MATCH` - Match required capabilities

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `registry` | None | ModelRegistry (creates default) |
| `router` | None | LLMRouter (creates default) |
| `cache` | None | SemanticCache (creates default) |
| `rate_limiter` | None | RateLimiter (creates default) |
| `circuit_breaker` | None | CircuitBreaker (creates default) |
| `request_queue` | None | RequestQueue (creates default) |
| `providers` | None | Provider adapters (creates defaults) |
| `l01_bridge` | None | Optional L01 integration |

## API Methods

| Method | Description |
|--------|-------------|
| `execute(request, routing_strategy)` | Execute inference request |
| `complete(request, routing_strategy)` | Alias for execute() |
| `stream(request, routing_strategy)` | Streaming inference |
| `health_check()` | Check health of all components |
| `close()` | Cleanup resources |

## Use Cases in Your Workflow

### 1. Initialize Model Gateway
```python
from L04_model_gateway.services.model_gateway import ModelGateway

# Default initialization (creates all components)
gateway = ModelGateway()

# Or with custom components
from L04_model_gateway.services.model_registry import ModelRegistry
from L04_model_gateway.services.semantic_cache import SemanticCache

registry = ModelRegistry()
registry.load_default_models()

cache = SemanticCache(redis_url="redis://localhost:6379")

gateway = ModelGateway(
    registry=registry,
    cache=cache
)
```

### 2. Execute Inference Request
```python
from L04_model_gateway.models import InferenceRequest, Message, MessageRole
from uuid import uuid4

# Create request
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[
        Message(role=MessageRole.USER, content="Explain async/await in Python")
    ],
    system_prompt="You are a helpful programming assistant.",
    temperature=0.7,
    max_tokens=500,
    capabilities=["text", "code"],
    enable_cache=True,
    metadata={"source": "tutorial"}
)

# Execute
response = await gateway.execute(request)

print(f"Model: {response.model_id}")
print(f"Content: {response.content}")
print(f"Tokens: {response.token_usage.total_tokens}")
print(f"Latency: {response.latency_ms}ms")
print(f"Cached: {response.cached}")
```

### 3. Execute with Routing Strategy
```python
from L04_model_gateway.models import RoutingStrategy

# Fastest response
response = await gateway.execute(request, RoutingStrategy.FASTEST)

# Lowest cost
response = await gateway.execute(request, RoutingStrategy.CHEAPEST)

# Highest quality
response = await gateway.execute(request, RoutingStrategy.BEST_QUALITY)

# Balanced approach
response = await gateway.execute(request, RoutingStrategy.BALANCED)

# Match capabilities
response = await gateway.execute(request, RoutingStrategy.CAPABILITY_MATCH)
```

### 4. Streaming Inference
```python
# Execute streaming request
async for chunk in gateway.stream(request):
    print(chunk.content, end="", flush=True)

    if chunk.is_final:
        print()
        print(f"Total tokens: {chunk.token_usage.total_tokens}")
```

### 5. Request with Multi-Turn Conversation
```python
# Multi-turn conversation
messages = [
    Message(role=MessageRole.USER, content="What is a closure?"),
    Message(role=MessageRole.ASSISTANT, content="A closure is a function..."),
    Message(role=MessageRole.USER, content="Can you give an example?")
]

request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=messages,
    system_prompt="You are a programming tutor.",
    temperature=0.5,
    max_tokens=1000
)

response = await gateway.execute(request)
```

### 6. Disable Caching
```python
# For dynamic or sensitive requests
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[Message(role=MessageRole.USER, content="What time is it?")],
    enable_cache=False  # Bypass cache
)

response = await gateway.execute(request)
print(f"Cached: {response.cached}")  # Always False
```

### 7. Health Check
```python
# Check all components
health = await gateway.health_check()

print(f"Gateway: {health['gateway']}")
print(f"Timestamp: {health['timestamp']}")
print(f"Registry models: {health['registry']['total_models']}")
print(f"Cache entries: {health['cache']['entries']}")
print(f"Queue pending: {health['queue']['pending_requests']}")

# Check each provider
for provider_id, status in health['providers'].items():
    print(f"  {provider_id}: {status['status']}")
```

### 8. Handle Errors
```python
from L04_model_gateway.models import L04Error, RateLimitError, ProviderError

try:
    response = await gateway.execute(request)
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    print(f"Retry after: {e.details.get('retry_after')}")
except ProviderError as e:
    print(f"Provider failed: {e.code} - {e.message}")
except L04Error as e:
    print(f"Gateway error: {e.code} - {e.message}")
```

### 9. Cleanup
```python
# Close all resources
await gateway.close()
# Closes cache, rate limiter, L01 bridge, providers
```

## Service Interactions

```
+------------------+
|   ModelGateway   | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Coordinates:
         |
+--------+--------+--------+--------+--------+
|        |        |        |        |        |
v        v        v        v        v        v
Registry Router  Cache  RateLimiter Circuit  Queue
   |                                 Breaker
   |
   +-- Providers (Ollama, OpenAI, Anthropic, Mock)
```

**Integration Points:**
- **ModelRegistry (L04)**: Model configurations and capabilities
- **LLMRouter (L04)**: Request routing and model selection
- **SemanticCache (L04)**: Response caching
- **RateLimiter (L04)**: Request rate limiting
- **CircuitBreaker (L04)**: Fault tolerance
- **RequestQueue (L04)**: Priority queuing
- **Provider Adapters**: LLM provider integrations
- **L01Bridge (L04)**: Usage tracking to L01

## Request Pipeline

```
1. execute(request)
   │
   ├── Check rate limits (RateLimiter)
   │   └── RateLimitError if exceeded
   │
   ├── Check cache (SemanticCache)
   │   └── Return cached if hit
   │
   ├── Route request (LLMRouter)
   │   ├── Select primary model
   │   └── Identify fallbacks
   │
   ├── Execute with failover
   │   ├── Try primary model (CircuitBreaker protected)
   │   └── Try fallbacks on failure
   │
   ├── Cache response (SemanticCache)
   │   └── Only cache successful responses
   │
   ├── Record usage (L01Bridge)
   │   └── Optional tracking
   │
   └── Return InferenceResponse
```

## Failover Mechanism

```
1. Try primary model
   └── Success → Return response

2. On failure, try fallback models in order
   ├── Fallback 1 → Success → Return
   ├── Fallback 2 → Success → Return
   └── ...

3. All failed
   └── Raise ProviderError(E4102_ALL_MODELS_UNAVAILABLE)
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4002 | Provider not configured | No |
| E4102 | All models unavailable | Yes |
| E4200 | Provider error | Depends |
| E4604 | Streaming error | Yes |

## Execution Examples

```python
# Complete gateway workflow
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.models import (
    InferenceRequest,
    Message,
    MessageRole,
    RoutingStrategy
)
from uuid import uuid4

# Initialize
gateway = ModelGateway()

# 1. Simple completion
simple_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Hello, how are you?")
    ],
    temperature=0.7,
    max_tokens=100
)

response = await gateway.execute(simple_request)
print(f"Response: {response.content}")

# 2. Code generation with capability matching
code_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Write a Python function to sort a list")
    ],
    system_prompt="You are an expert Python programmer.",
    capabilities=["text", "code"],
    max_tokens=500
)

response = await gateway.execute(code_request, RoutingStrategy.CAPABILITY_MATCH)
print(f"Model: {response.model_id}")  # Model with code capability
print(f"Code:\n{response.content}")

# 3. Streaming response
stream_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Explain machine learning")
    ],
    max_tokens=1000
)

print("Streaming: ", end="")
async for chunk in gateway.stream(stream_request):
    print(chunk.content, end="", flush=True)
print()

# 4. Cached request
cached_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="What is 2+2?")
    ],
    enable_cache=True
)

# First call - not cached
response1 = await gateway.execute(cached_request)
print(f"First call cached: {response1.cached}")  # False

# Second call - cached
response2 = await gateway.execute(cached_request)
print(f"Second call cached: {response2.cached}")  # True
print(f"Latency: {response2.latency_ms}ms")  # Near-zero

# 5. Health check
health = await gateway.health_check()
print(f"Gateway status: {health['gateway']}")
for provider, status in health['providers'].items():
    print(f"  {provider}: {status['status']}")

# 6. Error handling
try:
    response = await gateway.execute(invalid_request)
except RateLimitError as e:
    print(f"Rate limited - retry after {e.details.get('retry_after')}s")
except ProviderError as e:
    print(f"Provider error: {e.message}")

# 7. Cleanup
await gateway.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| execute() | Complete |
| complete() | Complete |
| stream() | Complete |
| Rate Limiting | Complete |
| Cache Integration | Complete |
| Routing | Complete |
| Failover | Complete |
| Circuit Breaker | Complete |
| Health Check | Complete |
| L01 Integration | Complete |
| close() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Request Prioritization | Medium | Use RequestQueue priority |
| Batch Inference | Medium | Multiple requests in one call |
| Cost Tracking | Medium | Track inference costs |
| Prometheus Metrics | Low | Export gateway metrics |
| Additional Providers | Low | More LLM provider adapters |
| Load Balancing | Low | Distribute across providers |

## Strengths

- **Unified API** - Single entry point for all LLM requests
- **Automatic failover** - Resilient to provider failures
- **Full pipeline** - Caching, rate limiting, routing integrated
- **Streaming support** - Real-time response streaming
- **Health monitoring** - Track all component health
- **Clean abstraction** - Hides provider complexity

## Weaknesses

- **No batch inference** - One request at a time
- **No cost optimization** - Routing doesn't consider cost yet
- **Limited providers** - Ollama and Mock only by default
- **No load balancing** - Single provider per request
- **No request priority** - Queue not fully utilized
- **Streaming bypasses cache** - Can't cache streams

## Best Practices

### Request Configuration
Set appropriate parameters:
```python
# Creative tasks - higher temperature
InferenceRequest.create(temperature=0.9, max_tokens=2000)

# Factual tasks - lower temperature
InferenceRequest.create(temperature=0.1, max_tokens=500)

# Code generation - specific capabilities
InferenceRequest.create(capabilities=["text", "code"], temperature=0.3)
```

### Routing Strategy Selection
Choose based on needs:
```python
# User-facing - prioritize speed
gateway.execute(request, RoutingStrategy.FASTEST)

# Background processing - save costs
gateway.execute(request, RoutingStrategy.CHEAPEST)

# Critical decisions - prioritize quality
gateway.execute(request, RoutingStrategy.BEST_QUALITY)
```

### Caching
Enable for repeatable requests:
```python
# Good for caching (same input = same output)
InferenceRequest.create(
    messages=[...static...],
    enable_cache=True
)

# Bad for caching (dynamic content)
InferenceRequest.create(
    messages=[...dynamic...],
    enable_cache=False
)
```

### Error Handling
Always handle L04 errors:
```python
try:
    response = await gateway.execute(request)
except RateLimitError:
    await asyncio.sleep(retry_after)
    response = await gateway.execute(request)
except ProviderError as e:
    if e.details.get("retryable"):
        # Retry logic
        pass
    else:
        # Fallback logic
        pass
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/model_gateway.py`
- Models: `platform/src/L04_model_gateway/models/`
- Providers: `platform/src/L04_model_gateway/providers/`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelRegistry (L04) - Model configuration
- LLMRouter (L04) - Request routing
- SemanticCache (L04) - Response caching
- RateLimiter (L04) - Rate limiting
- CircuitBreaker (L04) - Fault tolerance
- RequestQueue (L04) - Priority queuing
- L04Bridge (L04) - L01 integration
- ToolModelBridge (L03) - Tool execution bridge

---
*Generated: 2026-01-24 | Platform Services Documentation*
