# Service 37/44: L04Bridge

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.l01_bridge` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L01 Data Layer (via L01Client) |
| **Category** | AI/ML / Usage Tracking |

## Role in Development Environment

The **L04Bridge** connects L04 Model Gateway to L01 Data Layer for persistent model usage tracking. It provides:
- Model inference usage recording
- Token usage tracking (input, output, cached)
- Latency and cost metrics
- Agent context preservation (DID, tenant, session)
- Cache hit tracking
- Error logging for failed requests

This is **the usage tracking layer for LLM inference** - when inference requests complete, L04Bridge records all metrics in L01 for analytics, cost tracking, and monitoring.

## Data Model

### Recorded Fields
- `request_id: str` - Unique request identifier
- `model_provider: str` - Provider name
- `model_name: str` - Model identifier
- `input_tokens: int` - Input token count
- `output_tokens: int` - Output token count
- `cached_tokens: int` - Cached token count
- `total_tokens: int` - Total token count
- `latency_ms: float` - Response latency
- `cached: bool` - Whether response was cached
- `cost_estimate: float` - Estimated cost in dollars
- `cost_input_cents: float` - Input cost in cents
- `cost_output_cents: float` - Output cost in cents
- `cost_cached_cents: float` - Cached cost in cents
- `finish_reason: str` - Why generation stopped
- `error_message: str` - Error if failed
- `response_status: str` - Response status
- `agent_did: str` - Agent identifier
- `tenant_id: str` - Tenant identifier
- `session_id: str` - Session identifier
- `metadata: Dict` - Additional metadata

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `l01_base_url` | http://localhost:8002 | L01 Data Layer URL |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize bridge (async setup) |
| `record_inference(request, response)` | Record inference usage |
| `cleanup()` | Cleanup resources |

## Use Cases in Your Workflow

### 1. Initialize L04 Bridge
```python
from L04_model_gateway.services.l01_bridge import L04Bridge

# Default initialization
bridge = L04Bridge()

# Or with custom L01 URL
bridge = L04Bridge(l01_base_url="http://l01-service:8002")

# Async initialization if needed
await bridge.initialize()
```

### 2. Record Inference Usage
```python
from L04_model_gateway.models import InferenceRequest, InferenceResponse

# After executing inference
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[...],
    metadata={
        "tenant_id": "tenant-001",
        "session_id": "session-456"
    }
)

response = await gateway.execute(request)

# Record usage in L01
success = await bridge.record_inference(request, response)

if success:
    print("Usage recorded in L01")
else:
    print("Failed to record usage")
```

### 3. Integration with ModelGateway
```python
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.services.l01_bridge import L04Bridge

# Create bridge
bridge = L04Bridge(l01_base_url="http://localhost:8002")

# Inject into gateway
gateway = ModelGateway(l01_bridge=bridge)

# Gateway automatically records usage after inference
response = await gateway.execute(request)
# Usage recorded automatically
```

### 4. Track Cost Breakdown
```python
# Response includes cost breakdown
response = await gateway.execute(request)

if response.cost_breakdown:
    print(f"Input cost: ${response.cost_breakdown.input_cost_cents/100:.4f}")
    print(f"Output cost: ${response.cost_breakdown.output_cost_cents/100:.4f}")
    print(f"Total cost: ${response.cost_breakdown.total_cost_cents/100:.4f}")

# Bridge records all cost details in L01
await bridge.record_inference(request, response)
```

### 5. Track Agent Context
```python
# Include agent context in request
request = InferenceRequest.create(
    agent_did="did:agent:abc123",  # Agent DID tracked
    messages=[...],
    metadata={
        "tenant_id": "tenant-001",    # Tenant tracked
        "session_id": "session-456"   # Session tracked
    }
)

# Bridge preserves context in L01 record
await bridge.record_inference(request, response)

# In L01, can query:
# - Usage by agent
# - Usage by tenant
# - Usage by session
```

### 6. Track Cache Hits
```python
# Response indicates if cached
response = await gateway.execute(request)

print(f"Cached: {response.cached}")
print(f"Latency: {response.latency_ms}ms")  # 0ms if cached

# Bridge records cache status
await bridge.record_inference(request, response)

# In L01, can analyze:
# - Cache hit rate
# - Latency improvement from caching
# - Cost savings from caching
```

### 7. Disable Recording
```python
# Disable usage recording (e.g., for testing)
bridge.enabled = False

# Recording will be skipped
success = await bridge.record_inference(request, response)
print(f"Recorded: {success}")  # False (disabled)

# Re-enable
bridge.enabled = True
```

### 8. Cleanup
```python
# Cleanup when done
await bridge.cleanup()
```

## Service Interactions

```
+------------------+
|    L04Bridge     | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Records to:
         |
+------------------+
|    L01Client     | <--- Shared client
+--------+---------+
         |
         v
+------------------+
|   L01 Data Layer | <--- L01 Data Layer
|      (L01)       |
+------------------+
```

**Integration Points:**
- **ModelGateway (L04)**: Calls bridge after inference
- **L01Client (shared)**: HTTP client for L01 API
- **L01 Data Layer**: Stores usage records

## Data Flow

```
1. ModelGateway executes inference

2. ModelGateway calls bridge.record_inference()

3. Bridge extracts:
   - Agent context (DID, tenant, session)
   - Token usage (input, output, cached)
   - Cost breakdown (input, output, cached)
   - Latency, cache status, finish reason

4. Bridge sends to L01 via L01Client

5. L01 stores record for:
   - Analytics dashboards
   - Cost tracking
   - Usage monitoring
   - Billing
```

## Recorded Metrics

### Token Metrics
```python
response.token_usage.input_tokens    # Prompt tokens
response.token_usage.output_tokens   # Generated tokens
response.token_usage.cached_tokens   # Tokens from cache
response.token_usage.total_tokens    # Total tokens
```

### Cost Metrics
```python
response.cost_breakdown.input_cost_cents    # Input cost
response.cost_breakdown.output_cost_cents   # Output cost
response.cost_breakdown.cached_cost_cents   # Cached cost
response.cost_breakdown.total_cost_cents    # Total cost
```

### Performance Metrics
```python
response.latency_ms    # Response latency
response.cached        # Whether cached
response.status        # Response status
response.finish_reason # Why generation stopped
```

## Error Handling

```python
# Bridge handles errors gracefully
try:
    await bridge.record_inference(request, response)
except Exception as e:
    # Logged but not raised
    logger.error(f"Failed to record: {e}")
    # Returns False instead of raising
    return False

# Callers can check success
if not await bridge.record_inference(request, response):
    logger.warning("Usage not recorded")
    # Continue anyway - recording failure shouldn't break inference
```

## Execution Examples

```python
# Complete L04 Bridge workflow
from L04_model_gateway.services.l01_bridge import L04Bridge
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.models import (
    InferenceRequest,
    Message,
    MessageRole
)

# Initialize
bridge = L04Bridge(l01_base_url="http://localhost:8002")
await bridge.initialize()

# Create gateway with bridge
gateway = ModelGateway(l01_bridge=bridge)

# 1. Create request with full context
request = InferenceRequest.create(
    agent_did="did:agent:demo",
    messages=[
        Message(role=MessageRole.USER, content="What is Python?")
    ],
    temperature=0.7,
    max_tokens=500,
    metadata={
        "tenant_id": "tenant-demo",
        "session_id": "session-123"
    }
)

# 2. Execute inference
response = await gateway.execute(request)

print(f"Model: {response.model_id}")
print(f"Tokens: {response.token_usage.total_tokens}")
print(f"Latency: {response.latency_ms}ms")
print(f"Cached: {response.cached}")

# 3. Manual recording (if not using gateway integration)
success = await bridge.record_inference(request, response)
print(f"Recorded: {success}")

# 4. Check what was recorded
print(f"\nRecorded in L01:")
print(f"  Request ID: {response.request_id}")
print(f"  Agent: {request.agent_did}")
print(f"  Model: {response.model_id}")
print(f"  Provider: {response.provider}")
print(f"  Input tokens: {response.token_usage.input_tokens}")
print(f"  Output tokens: {response.token_usage.output_tokens}")
print(f"  Latency: {response.latency_ms}ms")
print(f"  Cached: {response.cached}")

if response.cost_breakdown:
    print(f"  Cost: ${response.cost_breakdown.total_cost_cents/100:.4f}")

# 5. Disable for testing
bridge.enabled = False
success = await bridge.record_inference(request, response)
print(f"\nRecording disabled: {not success}")

# 6. Re-enable
bridge.enabled = True

# 7. Cleanup
await bridge.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| L04Bridge class | Complete |
| initialize() | Complete |
| record_inference() | Complete |
| Token tracking | Complete |
| Cost tracking | Complete |
| Agent context | Complete |
| Cache tracking | Complete |
| Error handling | Complete |
| cleanup() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Batch Recording | Medium | Record multiple at once |
| Async Queue | Medium | Non-blocking recording |
| Retry Logic | Medium | Retry on L01 failures |
| Local Buffer | Low | Buffer if L01 unavailable |
| Prometheus Metrics | Low | Export recording metrics |
| Event Publishing | Low | Publish to event stream |

## Strengths

- **Complete tracking** - All usage metrics recorded
- **Agent context** - Full audit trail
- **Cost tracking** - Detailed cost breakdown
- **Non-blocking** - Failures don't break inference
- **Simple API** - Single record method
- **Clean abstraction** - Hides L01 complexity

## Weaknesses

- **Synchronous** - Blocks until L01 responds
- **No batching** - One record per request
- **No retry** - Single attempt to record
- **No buffering** - Lost if L01 unavailable
- **No events** - Only stores, no pub/sub
- **L01 dependent** - Requires L01 to be up

## Best Practices

### Include Full Context
Always include agent context:
```python
request = InferenceRequest.create(
    agent_did="did:agent:xxx",  # Required
    metadata={
        "tenant_id": "tenant-xxx",   # For multi-tenant
        "session_id": "session-xxx"  # For session tracking
    }
)
```

### Handle Recording Failures
Check recording success:
```python
success = await bridge.record_inference(request, response)
if not success:
    logger.warning(f"Failed to record {response.request_id}")
    # Consider: queue for retry, log locally, etc.
```

### Use Gateway Integration
Let gateway handle recording:
```python
# Instead of:
response = await provider.execute(request)
await bridge.record_inference(request, response)

# Use:
gateway = ModelGateway(l01_bridge=bridge)
response = await gateway.execute(request)  # Auto-records
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/l01_bridge.py`
- Client: `platform/src/shared/clients/l01_client.py`
- Models: `platform/src/L04_model_gateway/models/`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelGateway (L04) - Uses bridge for recording
- L01Client (shared) - HTTP client for L01
- L01 Data Layer - Stores usage records
- InferenceRequest/Response (L04) - Recorded data

---
*Generated: 2026-01-24 | Platform Services Documentation*
