# Service 31/44: LLMRouter

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.llm_router` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ModelRegistry (L04) |
| **Category** | AI/ML / Request Routing |

## Role in Development Environment

The **LLMRouter** provides intelligent model selection based on requirements, cost, and availability. It provides:
- Multi-criteria model selection (capabilities, cost, latency, quality)
- Multiple routing strategies for different use cases
- Provider health-aware routing with circuit breaker integration
- Data residency compliance checking
- Context length validation
- Fallback model selection for resilience

This is **the decision engine for model selection** - when a request comes in, LLMRouter determines which model(s) to use based on requirements, constraints, and current provider health.

## Data Model

### RoutingStrategy Enum
- `CAPABILITY_FIRST` - Match capabilities, then optimize cost
- `COST_OPTIMIZED` - Minimize cost
- `LATENCY_OPTIMIZED` - Minimize latency
- `QUALITY_OPTIMIZED` - Maximize quality scores
- `PROVIDER_PINNED` - Prefer specific providers

### RoutingDecision Dataclass
- `primary_model_id: str` - Selected primary model
- `primary_provider: str` - Primary model's provider
- `fallback_models: List[str]` - Up to 2 fallback model IDs
- `routing_strategy: RoutingStrategy` - Strategy used
- `estimated_cost_cents: float` - Estimated request cost
- `estimated_latency_ms: int` - Expected latency
- `reason: str` - Human-readable decision reason
- `metadata: Dict` - Additional routing info

### ProviderHealth Dataclass
- `provider_id: str` - Provider identifier
- `status: HealthStatus` - Current status
- `circuit_state: CircuitState` - Circuit breaker state
- `error_rate: float` - Recent error rate
- `avg_latency_ms: float` - Average latency

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `registry` | Required | ModelRegistry instance |
| `default_strategy` | CAPABILITY_FIRST | Default routing strategy |

## API Methods

| Method | Description |
|--------|-------------|
| `route(request, strategy)` | Route request to model |
| `update_provider_health(health)` | Update provider health status |

## Use Cases in Your Workflow

### 1. Initialize LLM Router
```python
from L04_model_gateway.services.llm_router import LLMRouter
from L04_model_gateway.services.model_registry import ModelRegistry
from L04_model_gateway.models import RoutingStrategy

# Create registry and load models
registry = ModelRegistry()
registry.load_default_models()

# Create router with default strategy
router = LLMRouter(
    registry=registry,
    default_strategy=RoutingStrategy.CAPABILITY_FIRST
)
```

### 2. Route Request to Model
```python
from L04_model_gateway.models import InferenceRequest, Message, MessageRole

# Create request
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[
        Message(role=MessageRole.USER, content="Analyze this code")
    ],
    capabilities=["text", "code"],
    max_tokens=1000
)

# Route to model
decision = router.route(request)

print(f"Primary: {decision.primary_model_id}")
print(f"Provider: {decision.primary_provider}")
print(f"Fallbacks: {decision.fallback_models}")
print(f"Cost: ${decision.estimated_cost_cents:.4f}")
print(f"Latency: {decision.estimated_latency_ms}ms")
print(f"Reason: {decision.reason}")
```

### 3. Use Different Routing Strategies
```python
from L04_model_gateway.models import RoutingStrategy

# Cost optimized - cheapest model
decision = router.route(request, RoutingStrategy.COST_OPTIMIZED)
print(f"Cheapest: {decision.primary_model_id}")

# Latency optimized - fastest model
decision = router.route(request, RoutingStrategy.LATENCY_OPTIMIZED)
print(f"Fastest: {decision.primary_model_id}")

# Quality optimized - best quality
decision = router.route(request, RoutingStrategy.QUALITY_OPTIMIZED)
print(f"Best quality: {decision.primary_model_id}")

# Provider pinned - specific provider
decision = router.route(request, RoutingStrategy.PROVIDER_PINNED)
print(f"Preferred provider: {decision.primary_model_id}")

# Capability first (default) - match capabilities, then optimize
decision = router.route(request, RoutingStrategy.CAPABILITY_FIRST)
print(f"Best match: {decision.primary_model_id}")
```

### 4. Update Provider Health
```python
from L04_model_gateway.models import ProviderHealth, HealthStatus, CircuitState

# Update health after checking provider
health = ProviderHealth(
    provider_id="ollama",
    status=HealthStatus.HEALTHY,
    circuit_state=CircuitState.CLOSED,
    error_rate=0.01,
    avg_latency_ms=150
)

router.update_provider_health(health)

# Unhealthy provider
unhealthy = ProviderHealth(
    provider_id="failing-provider",
    status=HealthStatus.DEGRADED,
    circuit_state=CircuitState.OPEN,  # Circuit breaker open
    error_rate=0.8,
    avg_latency_ms=5000
)

router.update_provider_health(unhealthy)
# Models from this provider will be excluded from routing
```

### 5. Route with Data Residency
```python
# Request with data residency requirements
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[Message(role=MessageRole.USER, content="Sensitive data")],
    constraints={
        "allowed_regions": ["us", "eu"]  # Only US/EU models
    }
)

decision = router.route(request)
# Only selects models in US or EU regions
```

### 6. Route with Latency Constraint
```python
# Request with max latency
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[Message(role=MessageRole.USER, content="Quick question")],
    constraints={
        "max_latency_ms": 1000  # Must respond within 1 second
    }
)

decision = router.route(request)
# Only selects models with p99 latency <= 1000ms
```

### 7. Route with Quality Preference
```python
# Request optimized for coding quality
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[Message(role=MessageRole.USER, content="Write a function")],
    capabilities=["text", "code"],
    requirements={
        "preferred_quality": "coding"  # Optimize for code quality
    }
)

decision = router.route(request, RoutingStrategy.QUALITY_OPTIMIZED)
# Selects model with highest coding quality score
```

### 8. Route with Preferred Providers
```python
# Request pinned to specific providers
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[Message(role=MessageRole.USER, content="Hello")],
    constraints={
        "preferred_providers": ["ollama", "anthropic"]
    }
)

decision = router.route(request, RoutingStrategy.PROVIDER_PINNED)
# Only considers models from Ollama or Anthropic
```

### 9. Handle Routing Errors
```python
from L04_model_gateway.models import RoutingError, L04ErrorCode

try:
    decision = router.route(request)
except RoutingError as e:
    if e.code == L04ErrorCode.E4101_NO_CAPABLE_MODEL:
        print("No models support required capabilities")
        print(f"Required: {e.details['required']}")

    elif e.code == L04ErrorCode.E4102_ALL_MODELS_UNAVAILABLE:
        print("All matching models are unavailable")

    elif e.code == L04ErrorCode.E4104_CONTEXT_LENGTH_EXCEEDED:
        print("Prompt too long for any model")
        print(f"Tokens: {e.details['estimated_tokens']}")

    elif e.code == L04ErrorCode.E4107_DATA_RESIDENCY_VIOLATION:
        print("No models in allowed regions")
        print(f"Allowed: {e.details['allowed_regions']}")
```

## Service Interactions

```
+------------------+
|    LLMRouter     | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Uses:
         |
+------------------+
|  ModelRegistry   | <--- Model configurations
|      (L04)       |
+------------------+
         |
   Receives health from:
         |
+------------------+
|  CircuitBreaker  | <--- Provider health
|      (L04)       |
+------------------+
```

**Integration Points:**
- **ModelRegistry (L04)**: Provides model configurations and capabilities
- **CircuitBreaker (L04)**: Provides provider health status
- **ModelGateway (L04)**: Uses router for request routing

## Routing Pipeline

```
1. route(request)
   │
   ├── Filter by capabilities
   │   └── Match required capabilities
   │
   ├── Filter by context length
   │   └── Check token limits
   │
   ├── Filter by data residency
   │   └── Match allowed regions
   │
   ├── Filter by provider health
   │   └── Exclude circuit-open providers
   │
   ├── Filter by latency
   │   └── Check max latency constraint
   │
   ├── Apply routing strategy
   │   ├── COST_OPTIMIZED → rank by cost
   │   ├── LATENCY_OPTIMIZED → rank by latency
   │   ├── QUALITY_OPTIMIZED → rank by quality
   │   ├── PROVIDER_PINNED → filter preferred
   │   └── CAPABILITY_FIRST → rank by cost
   │
   └── Return RoutingDecision
       ├── primary_model_id
       ├── fallback_models (up to 2)
       ├── estimated_cost
       └── estimated_latency
```

## Filtering Steps

### 1. Capability Filter
```
Required: ["text", "code", "reasoning"]
Available models:
  - model-a: ["text", "code"] → Excluded
  - model-b: ["text", "code", "reasoning"] → Included
  - model-c: ["text", "code", "reasoning", "vision"] → Included
```

### 2. Context Length Filter
```
Estimated tokens: 5000
Max output: 2000
Required context: 7000

Available:
  - model-a: 4096 context → Excluded
  - model-b: 8192 context → Included
  - model-c: 32768 context → Included
```

### 3. Health Filter
```
Provider health:
  - ollama: CLOSED → Include models
  - openai: HALF_OPEN → Include (with caution)
  - failing: OPEN → Exclude all models
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4100 | Routing failed | No |
| E4101 | No capable model | No |
| E4102 | All models unavailable | Yes |
| E4104 | Context length exceeded | No |
| E4107 | Data residency violation | No |

## Execution Examples

```python
# Complete routing workflow
from L04_model_gateway.services.llm_router import LLMRouter
from L04_model_gateway.services.model_registry import ModelRegistry
from L04_model_gateway.models import (
    InferenceRequest,
    Message,
    MessageRole,
    RoutingStrategy,
    ProviderHealth,
    HealthStatus,
    CircuitState
)

# Initialize
registry = ModelRegistry()
registry.load_default_models()
router = LLMRouter(registry, RoutingStrategy.CAPABILITY_FIRST)

# Update provider health
router.update_provider_health(ProviderHealth(
    provider_id="ollama",
    status=HealthStatus.HEALTHY,
    circuit_state=CircuitState.CLOSED,
    error_rate=0.01,
    avg_latency_ms=100
))

# 1. Simple routing
simple_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Hello")
    ],
    max_tokens=100
)

decision = router.route(simple_request)
print(f"Model: {decision.primary_model_id}")
print(f"Provider: {decision.primary_provider}")

# 2. Capability-specific routing
code_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Write Python code")
    ],
    capabilities=["text", "code"],
    max_tokens=500
)

decision = router.route(code_request, RoutingStrategy.QUALITY_OPTIMIZED)
print(f"Best for code: {decision.primary_model_id}")
print(f"Fallbacks: {decision.fallback_models}")

# 3. Cost-optimized routing
cheap_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Quick task")
    ],
    max_tokens=100
)

decision = router.route(cheap_request, RoutingStrategy.COST_OPTIMIZED)
print(f"Cheapest: {decision.primary_model_id}")
print(f"Estimated cost: ${decision.estimated_cost_cents:.4f}")

# 4. Latency-optimized routing
fast_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="Fast response needed")
    ],
    constraints={"max_latency_ms": 500},
    max_tokens=50
)

decision = router.route(fast_request, RoutingStrategy.LATENCY_OPTIMIZED)
print(f"Fastest: {decision.primary_model_id}")
print(f"Expected latency: {decision.estimated_latency_ms}ms")

# 5. Region-constrained routing
eu_request = InferenceRequest.create(
    agent_did="did:agent:test",
    messages=[
        Message(role=MessageRole.USER, content="EU data")
    ],
    constraints={"allowed_regions": ["eu"]},
    max_tokens=200
)

try:
    decision = router.route(eu_request)
    print(f"EU model: {decision.primary_model_id}")
except RoutingError as e:
    print(f"No EU models: {e.message}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| route() | Complete |
| update_provider_health() | Complete |
| Capability filtering | Complete |
| Context length filtering | Complete |
| Data residency filtering | Complete |
| Health filtering | Complete |
| Latency filtering | Complete |
| Cost optimization | Complete |
| Latency optimization | Complete |
| Quality optimization | Complete |
| Provider pinning | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Load Balancing | Medium | Distribute across equal models |
| Cost Budgets | Medium | Per-request cost limits |
| Custom Strategies | Low | User-defined routing logic |
| A/B Testing | Low | Route percentage to different models |
| Prometheus Metrics | Low | Export routing metrics |
| Learning Router | Low | ML-based routing optimization |

## Strengths

- **Multi-criteria** - Considers capabilities, cost, latency, quality
- **Health-aware** - Integrates with circuit breaker
- **Fallback support** - Provides backup models
- **Data residency** - Compliance checking
- **Cost estimation** - Predicts request cost
- **Clear reasons** - Human-readable decisions

## Weaknesses

- **No load balancing** - Picks single primary
- **No cost budgets** - Can't limit request cost
- **Static strategies** - No custom logic
- **No A/B testing** - All requests same path
- **No learning** - Doesn't optimize over time
- **Synchronous** - Blocking route decision

## Best Practices

### Strategy Selection
Match strategy to use case:
```python
# User-facing, real-time → latency
RoutingStrategy.LATENCY_OPTIMIZED

# Background processing → cost
RoutingStrategy.COST_OPTIMIZED

# Critical decisions → quality
RoutingStrategy.QUALITY_OPTIMIZED

# Specific requirements → capability
RoutingStrategy.CAPABILITY_FIRST

# Compliance requirements → pinned
RoutingStrategy.PROVIDER_PINNED
```

### Health Updates
Keep health current:
```python
# Update health regularly (e.g., every 30 seconds)
async def update_health_periodically():
    while True:
        for provider in providers:
            health = await provider.health_check()
            router.update_provider_health(health)
        await asyncio.sleep(30)
```

### Error Handling
Handle routing failures gracefully:
```python
try:
    decision = router.route(request)
except RoutingError as e:
    if e.code == L04ErrorCode.E4102_ALL_MODELS_UNAVAILABLE:
        # Wait and retry
        await asyncio.sleep(5)
        decision = router.route(request)
    else:
        # Use fallback behavior
        handle_routing_failure(e)
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/llm_router.py`
- Models: `platform/src/L04_model_gateway/models/routing_config.py`
- Error Codes: `platform/src/L04_model_gateway/models/error_codes.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelRegistry (L04) - Model configurations
- ModelGateway (L04) - Uses router for decisions
- CircuitBreaker (L04) - Provider health source
- RateLimiter (L04) - Complementary limiting
- SemanticCache (L04) - Cache before routing

---
*Generated: 2026-01-24 | Platform Services Documentation*
