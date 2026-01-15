# L11 Integration Layer

Cross-layer orchestration and service mesh coordination for the Agentic AI Workforce platform.

## Overview

The Integration Layer (L11) provides the communication backbone for all vertical layers (L02-L10), enabling:

- **Service Discovery**: Layer registration and health tracking
- **Event-Driven Integration**: Redis Pub/Sub for async messaging
- **Circuit Breaker**: Failure isolation and fast-fail behavior
- **Request Orchestration**: Cross-layer routing with tracing
- **Saga Orchestration**: Multi-step workflows with automatic compensation
- **Observability**: Distributed tracing and metrics collection

## Architecture

```
┌─────────────────────────────────────────────────┐
│          L11 INTEGRATION LAYER                  │
│                                                 │
│  ┌─ Service Registry                           │
│  │  • Layer discovery                           │
│  │  • Health tracking                           │
│  │                                              │
│  ├─ Event Bus (Redis Pub/Sub)                  │
│  │  • Async event distribution                  │
│  │  • Topic routing                             │
│  │  • Dead letter queue                         │
│  │                                              │
│  ├─ Circuit Breaker                             │
│  │  • Per-service failure isolation             │
│  │  • Fast-fail behavior                        │
│  │                                              │
│  ├─ Request Orchestrator                        │
│  │  • Cross-layer routing                       │
│  │  • Request correlation                       │
│  │  • Timeout management                        │
│  │                                              │
│  ├─ Saga Orchestrator                           │
│  │  • Multi-step workflows                      │
│  │  • Automatic compensation                    │
│  │                                              │
│  └─ Observability Collector                     │
│     • Distributed tracing                       │
│     • Metrics aggregation                       │
└─────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
pip3 install -r requirements.txt --break-system-packages
```

### Basic Usage

```python
from L11_integration import IntegrationLayer, ServiceInfo, HealthCheck, HealthCheckType

# Create integration layer
integration = IntegrationLayer(
    redis_url="redis://localhost:6379",
    observability_output_file="observability.log",
)

# Start integration layer
await integration.start()

# Register a service
service = ServiceInfo.create(
    service_name="L02_runtime",
    service_version="0.1.0",
    endpoint="http://localhost:8002",
    health_check=HealthCheck(
        check_type=HealthCheckType.HTTP,
        endpoint="http://localhost:8002/health",
    ),
)
await integration.service_registry.register_service(service)

# Use request orchestrator
response = await integration.request_orchestrator.route_request(
    service_name="L02_runtime",
    method="POST",
    path="/execute",
    data={"task": "example"},
)

# Stop integration layer
await integration.stop()
```

## Components

### Service Registry

Maintains a registry of all layer services with health monitoring.

```python
# Register service
service = ServiceInfo.create(
    service_name="L03_tool_execution",
    service_version="0.1.0",
    endpoint="http://localhost:8003",
)
await service_registry.register_service(service)

# Get service by name
service = await service_registry.get_service_by_name("L03_tool_execution")

# Health summary
summary = await service_registry.get_health_summary()
```

### Event Bus

Redis Pub/Sub based event bus for async communication.

```python
# Subscribe to events
async def handle_event(event: EventMessage):
    print(f"Received: {event.topic} - {event.payload}")

sub_id = await event_bus.subscribe(
    topic="agent.created",
    handler=handle_event,
)

# Publish event
event = EventMessage.create(
    topic="agent.created",
    event_type="created",
    payload={"agent_id": "agent-123"},
)
await event_bus.publish(event)

# Wildcard subscriptions
sub_id = await event_bus.subscribe(topic="agent.*", handler=handle_event)
```

### Circuit Breaker

Protects against cascading failures.

```python
# Execute with circuit breaker protection
async def call_service():
    # Service call
    return await some_service_call()

result = await circuit_breaker.execute(
    "L04_model_gateway",
    call_service,
)

# Get circuit state
state = await circuit_breaker.get_state("L04_model_gateway")
print(f"Circuit state: {state.state.value}")
```

### Request Orchestrator

Cross-layer request routing with tracing.

```python
# Route request
response = await request_orchestrator.route_request(
    service_name="L05_planning",
    method="POST",
    path="/create_plan",
    data={"goal": "Deploy application"},
)

# Broadcast to multiple services
responses = await request_orchestrator.broadcast_request(
    service_names=["L02_runtime", "L03_tool_execution"],
    method="GET",
    path="/health",
)
```

### Saga Orchestrator

Multi-step workflows with automatic compensation.

```python
# Define saga steps
async def step1_action(context):
    return {"result": "step1_done"}

async def step1_compensation(context):
    # Rollback step 1
    pass

# Create saga
saga = SagaDefinition.create(
    saga_name="deploy_application",
    steps=[
        SagaStep(
            step_id="build",
            step_name="Build application",
            action=step1_action,
            compensation=step1_compensation,
        ),
    ],
)

# Execute saga
execution = await saga_orchestrator.execute_saga(saga)
print(f"Saga status: {execution.status.value}")
```

### Observability

Distributed tracing and metrics.

```python
# Record trace span
span = TraceSpan(
    span_name="execute_task",
    service_name="L11_integration",
)
await observability.record_span(span)

# Record metric
metric = Metric(
    metric_name="l11_request_duration_seconds",
    metric_type="histogram",
    value=0.123,
    labels={"service": "L02_runtime"},
)
await observability.record_metric(metric)

# Get trace
spans = await observability.get_trace(trace_id="abc-123")
```

## Configuration

Default configuration in `config/default_config.py`:

```python
DEFAULT_CONFIG = {
    "redis": {
        "url": "redis://localhost:6379",
    },
    "circuit_breaker": {
        "failure_threshold": 5,
        "timeout_sec": 60,
    },
    "saga": {
        "default_timeout_sec": 300,
        "auto_compensate": True,
    },
}
```

## Testing

Run integration tests:

```bash
pytest tests/test_integration.py -v
```

Tests require Redis running on localhost:6379.

## Error Codes

L11 uses error codes E11000-E11999:

- **E11000-E11099**: Service registry and discovery
- **E11100-E11199**: Event bus operations
- **E11200-E11299**: Circuit breaker
- **E11300-E11399**: Request orchestration
- **E11400-E11499**: Saga orchestration
- **E11500-E11599**: Observability and tracing
- **E11800-E11899**: Health checking
- **E11900-E11999**: Generic integration errors

## Local Development Adaptations

This implementation is adapted for local development:

- **Event bus**: Redis Pub/Sub instead of Kafka/NATS
- **Service mesh**: Direct HTTP instead of Istio/Linkerd
- **Tracing**: Console/file output instead of Jaeger
- **Service discovery**: Config-based instead of K8s DNS

## Dependencies

- `httpx>=0.27.0` - HTTP client for request orchestration
- `redis>=5.0.0` - Redis client for event bus
- `pytest>=8.0.0` - Testing framework
- `pytest-asyncio>=0.23.0` - Async test support

## License

Part of the Agentic AI Workforce platform.
