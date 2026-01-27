# L11 Integration Layer - Bridge Service Integration

This document describes how the L11 Integration Layer services are wired to record operational data to the L01 Data Layer.

## Overview

The L11 Integration Layer consists of three core services that now automatically record their operational data to L01:

1. **SagaOrchestrator** - Records saga executions and steps
2. **CircuitBreaker** - Records circuit breaker state changes  
3. **ServiceRegistry** - Records service registration and health events

## Integration Points

### 1. SagaOrchestrator

**File**: `src/L11_integration/services/saga_orchestrator.py`

**Changes**:
- Added `l11_bridge` parameter to `__init__`
- Records saga execution when saga starts (line 95-103)
- Records saga step when step starts (line 193-201)
- Updates saga step on completion (line 236-242)
- Updates saga step on failure (line 263-270)
- Updates saga execution on completion (line 157-163)
- Records compensation mode when saga enters compensation (line 303-308)

**Recording Triggers**:
- Saga starts → `record_saga_execution()`
- Step starts → `record_saga_step()`
- Step completes → `update_saga_step(status="completed")`
- Step fails → `update_saga_step(status="failed")`
- Saga completes → `update_saga_execution(status="completed")`
- Saga enters compensation → `update_saga_execution(status="compensating")`

### 2. CircuitBreaker

**File**: `src/L11_integration/services/circuit_breaker.py`

**Changes**:
- Added `l11_bridge` parameter to `__init__`
- Records circuit breaker state changes on success (line 153-163)
- Records circuit breaker state changes on failure (line 185-196)

**Recording Triggers**:
- Circuit state changes (CLOSED → OPEN, OPEN → HALF_OPEN, HALF_OPEN → CLOSED)
- Records failure count, success count, thresholds, and timeout settings

### 3. ServiceRegistry

**File**: `src/L11_integration/services/service_registry.py`

**Changes**:
- Added `l11_bridge` parameter to `__init__`
- Records service registration (line 65-76)
- Records service deregistration (line 109-116)
- Records health status changes (line 198-206)

**Recording Triggers**:
- Service registered → `record_service_registry_event(event_type="registered")`
- Service deregistered → `record_service_registry_event(event_type="deregistered")`
- Health status changes → `record_service_registry_event(event_type="health_change")`

### 4. IntegrationLayer

**File**: `src/L11_integration/integration_layer.py`

**Changes**:
- Pass `l11_bridge` to ServiceRegistry (line 51)
- Pass `l11_bridge` to CircuitBreaker (line 53)
- Pass `l11_bridge` to SagaOrchestrator (line 63)

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  L11 Integration Layer                      │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────┐              │
│  │ SagaOrchestrator│───▶│    L11Bridge     │─┐            │
│  └─────────────────┘    └──────────────────┘ │            │
│                                                │            │
│  ┌─────────────────┐    ┌──────────────────┐ │            │
│  │ CircuitBreaker  │───▶│    L11Bridge     │─┤            │
│  └─────────────────┘    └──────────────────┘ │            │
│                                                │            │
│  ┌─────────────────┐    ┌──────────────────┐ │            │
│  │ ServiceRegistry │───▶│    L11Bridge     │─┤            │
│  └─────────────────┘    └──────────────────┘ │            │
│                                                │            │
└────────────────────────────────────────────────┼────────────┘
                                                 │
                                                 ▼
                              ┌─────────────────────────────┐
                              │      L01 Data Layer         │
                              │  - saga_executions table    │
                              │  - saga_steps table         │
                              │  - circuit_breaker_events   │
                              │  - service_registry_events  │
                              └─────────────────────────────┘
```

## Testing

All E2E tests pass (25/25):
- **L09 Bridge Tests**: 5/5 ✓
- **L10 Bridge Tests**: 8/8 ✓
- **L11 Bridge Tests**: 12/12 ✓

Test command:
```bash
python3 -m pytest tests/e2e/test_l09_l01_bridge.py \
                 tests/e2e/test_l10_l01_bridge.py \
                 tests/e2e/test_l11_l01_bridge.py -v
```

## Operational Data Captured

### Saga Executions
- Saga start/completion timestamps
- Total steps, completed steps, failed steps
- Saga status (running, completed, failed, compensating)
- Context and metadata
- Compensation mode tracking

### Saga Steps
- Step execution lifecycle (pending → executing → completed/failed)
- Request and response data
- Retry counts
- Compensation execution status
- Error messages

### Circuit Breaker Events
- State transitions (closed → open → half_open → closed)
- Failure and success counts
- Failure thresholds and timeout settings
- Timestamps for state changes

### Service Registry Events
- Service registration/deregistration
- Health status changes (healthy, unhealthy, degraded)
- Service metadata (layer, host, port, capabilities)
- Timestamps for all events

## Notes

- All bridge calls are non-blocking and fail gracefully
- Bridge can be disabled by passing `None` or setting `enabled=False`
- Recording errors are logged but don't affect service operation
- All timestamps are recorded in UTC with ISO format
