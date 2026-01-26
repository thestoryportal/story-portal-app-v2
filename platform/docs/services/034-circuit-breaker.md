# Service 34/44: CircuitBreaker

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.circuit_breaker` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (in-memory state) |
| **Category** | AI/ML / Fault Tolerance |

## Role in Development Environment

The **CircuitBreaker** implements the circuit breaker pattern for provider health management and automatic failover. It provides:
- Three-state circuit (CLOSED, OPEN, HALF_OPEN)
- Automatic circuit opening after consecutive failures
- Timed recovery attempts with half-open state
- Per-provider health tracking
- Error rate and failure statistics
- Manual reset capability

This is **the fault tolerance layer for LLM providers** - preventing cascading failures by stopping requests to unhealthy providers and automatically testing recovery.

## Data Model

### CircuitState Enum
- `CLOSED` - Normal operation, requests pass through
- `OPEN` - Too many failures, reject requests immediately
- `HALF_OPEN` - Testing recovery, allow limited requests

### ProviderStatus Enum
- `HEALTHY` - Provider operational (circuit CLOSED)
- `DEGRADED` - Provider recovering (circuit HALF_OPEN)
- `UNAVAILABLE` - Provider down (circuit OPEN)

### ProviderHealth Dataclass
- `provider_id: str` - Provider identifier
- `status: ProviderStatus` - Current status
- `circuit_state: CircuitState` - Circuit breaker state
- `last_check: datetime` - Last health check time
- `consecutive_failures: int` - Current failure streak
- `last_failure_time: datetime` - Most recent failure
- `error_rate: float` - Historical error rate
- `metadata: Dict` - Additional metrics

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Failures before opening circuit |
| `recovery_timeout` | 60 | Seconds before attempting recovery |
| `half_open_max_requests` | 3 | Max requests in half-open state |

## API Methods

| Method | Description |
|--------|-------------|
| `get_state(provider)` | Get current circuit state |
| `call(provider, operation)` | Execute operation through circuit |
| `record_success(provider)` | Record successful request |
| `record_failure(provider)` | Record failed request |
| `get_health(provider)` | Get provider health status |
| `reset(provider)` | Reset circuit to CLOSED |
| `get_stats()` | Get all circuit statistics |

## Use Cases in Your Workflow

### 1. Initialize Circuit Breaker
```python
from L04_model_gateway.services.circuit_breaker import CircuitBreaker

# Default initialization
breaker = CircuitBreaker()

# With custom configuration
breaker = CircuitBreaker(
    failure_threshold=5,         # 5 failures to open
    recovery_timeout=60,         # 60 seconds before retry
    half_open_max_requests=3     # 3 test requests
)
```

### 2. Execute Through Circuit Breaker
```python
from L04_model_gateway.models import CircuitBreakerError

async def call_provider(prompt: str) -> str:
    # Your actual provider call
    return await anthropic.complete(prompt)

try:
    result = await breaker.call(
        provider="anthropic",
        operation=lambda: call_provider("Hello")
    )
    print(f"Result: {result}")

except CircuitBreakerError as e:
    print(f"Circuit open: {e.message}")
    # Use fallback provider
```

### 3. Check Circuit State
```python
from L04_model_gateway.models import CircuitState

state = breaker.get_state("anthropic")

if state == CircuitState.CLOSED:
    print("Provider healthy, proceed normally")
elif state == CircuitState.HALF_OPEN:
    print("Provider recovering, limited requests allowed")
elif state == CircuitState.OPEN:
    print("Provider down, requests will be rejected")
```

### 4. Get Provider Health
```python
health = breaker.get_health("anthropic")

print(f"Provider: {health.provider_id}")
print(f"Status: {health.status.value}")
print(f"Circuit: {health.circuit_state.value}")
print(f"Consecutive failures: {health.consecutive_failures}")
print(f"Error rate: {health.error_rate:.2%}")
print(f"Last failure: {health.last_failure_time}")
```

### 5. Manual Success/Failure Recording
```python
# Record success after external health check
breaker.record_success("anthropic")

# Record failure after detecting issue
breaker.record_failure("anthropic")
```

### 6. Reset Circuit
```python
# Manually reset circuit (e.g., after known recovery)
breaker.reset("anthropic")
print("Circuit reset to CLOSED")
```

### 7. Get All Statistics
```python
stats = breaker.get_stats()

print(f"Total providers: {stats['total_providers']}")
print(f"Circuits OPEN: {stats['circuits_open']}")
print(f"Circuits HALF_OPEN: {stats['circuits_half_open']}")
print(f"Circuits CLOSED: {stats['circuits_closed']}")

for provider, info in stats['providers'].items():
    print(f"  {provider}:")
    print(f"    State: {info['state']}")
    print(f"    Failures: {info['total_failures']}")
    print(f"    Requests: {info['total_requests']}")
```

### 8. Handle Circuit Open Errors
```python
from L04_model_gateway.models import CircuitBreakerError, L04ErrorCode

try:
    result = await breaker.call("anthropic", operation)

except CircuitBreakerError as e:
    if e.code == L04ErrorCode.E4701_PROVIDER_CIRCUIT_OPEN:
        # Circuit is open, use fallback
        result = await fallback_provider(request)
```

### 9. Integration with ModelGateway
```python
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.services.circuit_breaker import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)

# Inject into gateway
gateway = ModelGateway(circuit_breaker=breaker)

# Gateway automatically uses circuit breaker for all provider calls
response = await gateway.execute(request)
```

## Service Interactions

```
+------------------+
|  CircuitBreaker  | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Protects:
         |
+--------+--------+--------+
|                 |        |
v                 v        v
Anthropic       OpenAI   Ollama
Provider        Provider Provider
```

**Integration Points:**
- **ModelGateway (L04)**: Uses circuit breaker for all provider calls
- **LLMRouter (L04)**: Considers circuit state when routing
- **Provider Adapters**: Protected by circuit breaker

## State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────┐     failure_threshold     ┌──────────┐       │
│  │ CLOSED  │ ─────── exceeded ───────► │   OPEN   │       │
│  │         │                           │          │       │
│  └────┬────┘                           └────┬─────┘       │
│       │                                     │             │
│       │                          recovery_timeout         │
│  success                               elapsed            │
│       │                                     │             │
│       │    ┌───────────────────────────┐    │             │
│       │    │                           │    │             │
│       ▼    ▼                           │    ▼             │
│  ┌─────────────┐   success × 3    ┌────┴──────┐          │
│  │   CLOSED    │ ◄─────────────── │ HALF_OPEN │          │
│  │             │                  │           │          │
│  └─────────────┘  ◄── failure ─── └───────────┘          │
│                    (back to OPEN)                         │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## State Transitions

### CLOSED → OPEN
```
Trigger: consecutive_failures >= failure_threshold

Example:
  Request 1: Failure (1 failure)
  Request 2: Failure (2 failures)
  Request 3: Failure (3 failures)
  Request 4: Failure (4 failures)
  Request 5: Failure (5 failures) → OPEN
```

### OPEN → HALF_OPEN
```
Trigger: current_time - open_timestamp >= recovery_timeout

Example:
  Circuit opened at T=0
  T=30: Still OPEN (< 60s)
  T=60: Transition to HALF_OPEN
```

### HALF_OPEN → CLOSED
```
Trigger: half_open_requests >= half_open_max_requests AND all successful

Example:
  Request 1: Success (1/3)
  Request 2: Success (2/3)
  Request 3: Success (3/3) → CLOSED
```

### HALF_OPEN → OPEN
```
Trigger: Any failure during half-open state

Example:
  Request 1: Success
  Request 2: Failure → Back to OPEN
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4701 | Provider circuit open | Yes (after timeout) |

## Execution Examples

```python
# Complete circuit breaker workflow
from L04_model_gateway.services.circuit_breaker import CircuitBreaker
from L04_model_gateway.models import (
    CircuitState,
    CircuitBreakerError,
    ProviderStatus
)
import asyncio

# Initialize
breaker = CircuitBreaker(
    failure_threshold=3,      # Open after 3 failures
    recovery_timeout=30,      # Try recovery after 30s
    half_open_max_requests=2  # 2 test requests
)

provider = "anthropic"

# 1. Normal operation (CLOSED)
print(f"Initial state: {breaker.get_state(provider).value}")

async def mock_success():
    return "success"

async def mock_failure():
    raise Exception("Provider error")

# 2. Successful requests
for i in range(3):
    result = await breaker.call(provider, mock_success)
    print(f"Request {i+1}: {result}")

health = breaker.get_health(provider)
print(f"Status: {health.status.value}")  # HEALTHY

# 3. Failures leading to OPEN
for i in range(3):
    try:
        await breaker.call(provider, mock_failure)
    except CircuitBreakerError:
        print(f"Circuit now OPEN")
        break
    except Exception:
        print(f"Failure {i+1} recorded")

print(f"State after failures: {breaker.get_state(provider).value}")  # OPEN

# 4. Requests rejected when OPEN
try:
    await breaker.call(provider, mock_success)
except CircuitBreakerError as e:
    print(f"Request rejected: {e.message}")

# 5. Wait for recovery timeout
print("Waiting for recovery timeout...")
await asyncio.sleep(30)

# 6. Half-open state - test requests
print(f"State after timeout: {breaker.get_state(provider).value}")  # HALF_OPEN

for i in range(2):
    result = await breaker.call(provider, mock_success)
    print(f"Recovery test {i+1}: {result}")

print(f"Final state: {breaker.get_state(provider).value}")  # CLOSED

# 7. Get statistics
stats = breaker.get_stats()
print(f"Total requests: {stats['providers'][provider]['total_requests']}")
print(f"Total failures: {stats['providers'][provider]['total_failures']}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Three-state circuit | Complete |
| get_state() | Complete |
| call() | Complete |
| record_success() | Complete |
| record_failure() | Complete |
| get_health() | Complete |
| reset() | Complete |
| get_stats() | Complete |
| State transitions | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Persistent State | Medium | Store circuit state in Redis |
| Time-based Reset | Medium | Auto-reset after extended healthy period |
| Configurable per Provider | Medium | Different thresholds per provider |
| Prometheus Metrics | Low | Export circuit metrics |
| Event Hooks | Low | Callbacks on state changes |
| Sliding Window | Low | Count failures in time window |

## Strengths

- **Three-state design** - Clear CLOSED/OPEN/HALF_OPEN states
- **Automatic recovery** - Tests recovery after timeout
- **Per-provider tracking** - Independent circuits per provider
- **Health reporting** - Detailed health status
- **In-memory** - No external dependencies
- **Statistics** - Comprehensive failure tracking

## Weaknesses

- **In-memory only** - State lost on restart
- **Single instance** - Not distributed
- **Fixed thresholds** - Same config for all providers
- **No time window** - Counts consecutive failures only
- **No event hooks** - Can't trigger alerts
- **No backoff** - Fixed recovery timeout

## Best Practices

### Threshold Configuration
Tune thresholds based on provider reliability:
```python
# Stable providers - higher threshold
CircuitBreaker(failure_threshold=10, recovery_timeout=120)

# Flaky providers - lower threshold
CircuitBreaker(failure_threshold=3, recovery_timeout=30)

# Critical providers - quick recovery
CircuitBreaker(failure_threshold=5, recovery_timeout=15)
```

### Fallback Handling
Always provide fallbacks:
```python
async def inference_with_fallback(request):
    providers = ["anthropic", "openai", "ollama"]

    for provider in providers:
        state = breaker.get_state(provider)
        if state == CircuitState.OPEN:
            continue

        try:
            return await breaker.call(
                provider,
                lambda: call_provider(provider, request)
            )
        except CircuitBreakerError:
            continue
        except Exception:
            continue

    raise Exception("All providers unavailable")
```

### Health Monitoring
Monitor circuit states:
```python
async def health_check_task(breaker, interval=30):
    while True:
        stats = breaker.get_stats()
        if stats["circuits_open"] > 0:
            logger.warning(f"{stats['circuits_open']} circuits OPEN!")
            for provider, info in stats["providers"].items():
                if info["state"] == "OPEN":
                    logger.warning(f"  {provider} is OPEN")
        await asyncio.sleep(interval)
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/circuit_breaker.py`
- Models: `platform/src/L04_model_gateway/models/circuit.py`
- Error Codes: `platform/src/L04_model_gateway/models/__init__.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelGateway (L04) - Uses circuit breaker for failover
- LLMRouter (L04) - Considers circuit state when routing
- RateLimiter (L04) - Complementary request limiting
- Provider Adapters - Protected by circuit breaker

---
*Generated: 2026-01-24 | Platform Services Documentation*
