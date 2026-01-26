# Service 35/44: RequestQueue

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.request_queue` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (asyncio-based) |
| **Category** | AI/ML / Request Buffering |

## Role in Development Environment

The **RequestQueue** provides priority-based request buffering for handling load spikes. It provides:
- Priority queue with HIGH, NORMAL, LOW levels
- Deadline-aware processing with automatic expiration
- Maximum queue size limits with rejection handling
- FIFO ordering within priority levels
- Request timeout enforcement
- Queue statistics and monitoring

This is **the request buffering layer for LLM inference** - smoothing out load spikes by queuing requests when the system is under pressure and processing them in priority order.

## Data Model

### Priority Enum
- `HIGH` (0) - Highest priority, processed first
- `NORMAL` (1) - Default priority
- `LOW` (2) - Lowest priority, processed last

### QueuedRequest Dataclass
- `request: InferenceRequest` - The queued request
- `priority: Priority` - Priority level
- `enqueued_at: datetime` - When request was queued
- `deadline: Optional[datetime]` - Processing deadline

### Queue Statistics
- `enqueued: int` - Total requests enqueued
- `dequeued: int` - Total requests dequeued
- `expired: int` - Requests that exceeded deadline
- `rejected: int` - Requests rejected (queue full)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_size` | 1000 | Maximum queue size |
| `default_timeout_seconds` | 300 | Default request timeout (5 min) |

## API Methods

| Method | Description |
|--------|-------------|
| `enqueue(request, priority, deadline, timeout)` | Add request to queue |
| `dequeue(timeout)` | Get next request from queue |
| `size()` | Get current queue size |
| `is_empty()` | Check if queue is empty |
| `is_full()` | Check if queue is full |
| `clear()` | Clear all requests |
| `get_stats()` | Get queue statistics |

## Use Cases in Your Workflow

### 1. Initialize Request Queue
```python
from L04_model_gateway.services.request_queue import RequestQueue

# Default initialization
queue = RequestQueue()

# With custom configuration
queue = RequestQueue(
    max_size=500,               # Max 500 pending requests
    default_timeout_seconds=120  # 2 minute timeout
)
```

### 2. Enqueue Request
```python
from L04_model_gateway.services.request_queue import RequestQueue, Priority
from L04_model_gateway.models import InferenceRequest

# Create request
request = InferenceRequest.create(
    agent_did="did:agent:abc123",
    messages=[...],
    max_tokens=500
)

# Enqueue with default priority
success = await queue.enqueue(request)

if success:
    print(f"Request queued, queue size: {queue.size()}")
else:
    print("Queue full, request rejected")
```

### 3. Enqueue with Priority
```python
# High priority request
await queue.enqueue(request, priority=Priority.HIGH)

# Normal priority (default)
await queue.enqueue(request, priority=Priority.NORMAL)

# Low priority (background tasks)
await queue.enqueue(request, priority=Priority.LOW)
```

### 4. Enqueue with Deadline
```python
from datetime import datetime, timedelta

# Explicit deadline
deadline = datetime.utcnow() + timedelta(seconds=30)
await queue.enqueue(request, deadline=deadline)

# Using timeout_seconds
await queue.enqueue(request, timeout_seconds=60)  # 60 second deadline
```

### 5. Dequeue Next Request
```python
# Blocking dequeue (waits for request)
next_request = await queue.dequeue()

if next_request:
    # Process request
    response = await gateway.execute(next_request)
else:
    # Request expired before processing
    print("Request expired")
```

### 6. Dequeue with Timeout
```python
# Non-blocking with timeout
next_request = await queue.dequeue(timeout=5.0)

if next_request:
    print("Got request to process")
else:
    print("No request within 5 seconds")
```

### 7. Check Queue Status
```python
# Get current size
size = queue.size()
print(f"Queue size: {size}")

# Check if empty
if queue.is_empty():
    print("Queue is empty")

# Check if full
if queue.is_full():
    print("Queue is full, new requests will be rejected")
```

### 8. Get Queue Statistics
```python
stats = queue.get_stats()

print(f"Current size: {stats['current_size']}")
print(f"Max size: {stats['max_size']}")
print(f"Utilization: {stats['utilization']:.1%}")
print(f"Total enqueued: {stats['enqueued']}")
print(f"Total dequeued: {stats['dequeued']}")
print(f"Expired: {stats['expired']}")
print(f"Rejected: {stats['rejected']}")
```

### 9. Clear Queue
```python
# Clear all pending requests
cleared = await queue.clear()
print(f"Cleared {cleared} requests from queue")
```

### 10. Worker Pattern
```python
async def request_worker(queue: RequestQueue, gateway: ModelGateway):
    """Worker that processes queued requests"""
    while True:
        # Wait for next request
        request = await queue.dequeue(timeout=1.0)

        if request is None:
            # No request or expired
            continue

        try:
            response = await gateway.execute(request)
            print(f"Processed {request.request_id}")
        except Exception as e:
            print(f"Error processing {request.request_id}: {e}")
```

### 11. Integration with ModelGateway
```python
from L04_model_gateway.services.model_gateway import ModelGateway
from L04_model_gateway.services.request_queue import RequestQueue

# Create queue
queue = RequestQueue(max_size=1000)

# Inject into gateway
gateway = ModelGateway(request_queue=queue)

# Gateway can buffer requests when under load
response = await gateway.execute(request)
```

## Service Interactions

```
+------------------+
|   RequestQueue   | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Buffers:
         |
+--------+--------+
|                 |
v                 v
InferenceRequest ModelGateway
(Incoming)       (Consumer)
```

**Integration Points:**
- **InferenceRequest (L04)**: Queued request model
- **ModelGateway (L04)**: Uses queue for request buffering
- **Workers**: Consume requests from queue

## Priority Ordering

```
Queue Processing Order:

Priority HIGH   → First
Priority NORMAL → Second
Priority LOW    → Third

Within same priority:
  - Earlier deadline → First
  - Earlier enqueue time → Second (FIFO)

Example Queue:
  [HIGH,  enqueued T=0,  deadline T=30]  → Position 1
  [HIGH,  enqueued T=5,  deadline T=25]  → Position 2 (earlier deadline)
  [NORMAL, enqueued T=1, deadline T=60]  → Position 3
  [NORMAL, enqueued T=2, deadline T=60]  → Position 4
  [LOW,   enqueued T=0,  deadline T=120] → Position 5
```

## Deadline Expiration

```
Expiration Flow:

1. Request enqueued with deadline

2. Request waits in queue

3. On dequeue:
   - If current_time > deadline:
     - Return None (expired)
     - Increment expired counter
   - Else:
     - Return request for processing
     - Increment dequeued counter
```

## Error Codes

| Condition | Behavior |
|-----------|----------|
| Queue full | enqueue() returns False |
| Timeout | dequeue() returns None |
| Expired | dequeue() returns None |

## Execution Examples

```python
# Complete queue workflow
from L04_model_gateway.services.request_queue import RequestQueue, Priority
from L04_model_gateway.models import InferenceRequest, Message, MessageRole
from datetime import datetime, timedelta
import asyncio

# Initialize
queue = RequestQueue(
    max_size=100,
    default_timeout_seconds=60
)

# 1. Enqueue requests with different priorities
requests = []
for i, priority in enumerate([Priority.LOW, Priority.NORMAL, Priority.HIGH]):
    request = InferenceRequest.create(
        agent_did=f"did:agent:test{i}",
        messages=[Message(role=MessageRole.USER, content=f"Request {i}")]
    )
    requests.append(request)
    await queue.enqueue(request, priority=priority)

print(f"Queue size: {queue.size()}")  # 3

# 2. Dequeue in priority order
order = []
while not queue.is_empty():
    req = await queue.dequeue(timeout=0.1)
    if req:
        order.append(req.agent_did)

print(f"Processing order: {order}")
# ['did:agent:test2', 'did:agent:test1', 'did:agent:test0']
# HIGH, then NORMAL, then LOW

# 3. Test deadline expiration
request = InferenceRequest.create(
    agent_did="did:agent:expiring",
    messages=[Message(role=MessageRole.USER, content="Urgent")]
)

# Short deadline - 0.1 seconds
deadline = datetime.utcnow() + timedelta(seconds=0.1)
await queue.enqueue(request, deadline=deadline)

# Wait for expiration
await asyncio.sleep(0.2)

# Should return None (expired)
expired_req = await queue.dequeue(timeout=0.1)
print(f"Expired request: {expired_req}")  # None

# 4. Test queue full rejection
full_queue = RequestQueue(max_size=2)

await full_queue.enqueue(requests[0])  # Success
await full_queue.enqueue(requests[1])  # Success
success = await full_queue.enqueue(requests[2])  # Rejected
print(f"Third request accepted: {success}")  # False

# 5. Get statistics
stats = queue.get_stats()
print(f"Stats: {stats}")

# 6. Worker pattern
async def worker():
    while True:
        request = await queue.dequeue(timeout=5.0)
        if request:
            print(f"Processing: {request.agent_did}")
        else:
            print("No requests, idle...")
            break

# Add some work
for i in range(3):
    request = InferenceRequest.create(
        agent_did=f"did:agent:worker{i}",
        messages=[Message(role=MessageRole.USER, content="Work")]
    )
    await queue.enqueue(request)

# Start worker
await worker()

# 7. Clear queue
await queue.clear()
print(f"Queue cleared, size: {queue.size()}")  # 0
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Priority Queue | Complete |
| enqueue() | Complete |
| dequeue() | Complete |
| Priority Ordering | Complete |
| Deadline Expiration | Complete |
| Queue Size Limits | Complete |
| size()/is_empty()/is_full() | Complete |
| clear() | Complete |
| get_stats() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Persistent Queue | High | Redis-backed queue for durability |
| Multiple Workers | Medium | Worker pool management |
| Fair Queuing | Medium | Per-agent fairness |
| Dead Letter Queue | Medium | Failed request handling |
| Priority Boosting | Low | Boost priority of aging requests |
| Prometheus Metrics | Low | Export queue metrics |

## Strengths

- **Priority-based** - Three priority levels for ordering
- **Deadline-aware** - Automatic expiration of stale requests
- **Size limited** - Prevents unbounded memory growth
- **Statistics** - Tracks enqueue/dequeue/expired/rejected
- **Asyncio native** - Non-blocking queue operations
- **In-memory** - Fast, no external dependencies

## Weaknesses

- **In-memory only** - Requests lost on restart
- **Single instance** - Not distributed
- **No persistence** - No durability guarantee
- **No fair queuing** - No per-agent limits
- **No dead letter** - Failed requests not saved
- **No priority boosting** - Stale LOW requests may never run

## Best Practices

### Queue Sizing
Size queue based on load characteristics:
```python
# High-throughput, low-latency
RequestQueue(max_size=100, default_timeout_seconds=30)

# Batch processing, high durability
RequestQueue(max_size=10000, default_timeout_seconds=3600)

# Interactive, fast rejection
RequestQueue(max_size=50, default_timeout_seconds=10)
```

### Priority Assignment
Use priorities appropriately:
```python
# User-facing, interactive
await queue.enqueue(request, priority=Priority.HIGH)

# Background processing
await queue.enqueue(request, priority=Priority.LOW)

# Standard requests
await queue.enqueue(request, priority=Priority.NORMAL)
```

### Monitoring
Track queue health:
```python
async def monitor_queue(queue, interval=30):
    while True:
        stats = queue.get_stats()
        utilization = stats['utilization']

        if utilization > 0.8:
            logger.warning(f"Queue at {utilization:.0%} capacity!")

        if stats['expired'] > stats['dequeued'] * 0.1:
            logger.warning("High expiration rate!")

        await asyncio.sleep(interval)
```

### Graceful Shutdown
Drain queue before shutdown:
```python
async def graceful_shutdown(queue, gateway, timeout=30):
    """Drain queue before shutdown"""
    deadline = datetime.utcnow() + timedelta(seconds=timeout)

    while not queue.is_empty():
        if datetime.utcnow() > deadline:
            remaining = await queue.clear()
            logger.warning(f"Shutdown timeout, discarded {remaining} requests")
            break

        request = await queue.dequeue(timeout=1.0)
        if request:
            await gateway.execute(request)
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/request_queue.py`
- Models: `platform/src/L04_model_gateway/models/inference.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- ModelGateway (L04) - Uses queue for request buffering
- RateLimiter (L04) - Rate limiting may cause queuing
- CircuitBreaker (L04) - Circuit open may cause queuing
- InferenceRequest (L04) - Queued request model

---
*Generated: 2026-01-24 | Platform Services Documentation*
