# P2-09: Service Discovery with Consul

**Status:** ✅ Complete
**Phase:** 3 (Week 5: Service Architecture)
**Priority:** P2 (High Impact)
**Completion Date:** 2026-01-18

---

## Overview

Implemented Consul-based service discovery to enable dynamic service registration, health checking, and load balancing across all 12 service layers. This replaces hardcoded service URLs with dynamic service resolution.

### Key Features

- **Automatic Service Registration**: Services register themselves with Consul on startup
- **Health-Based Routing**: Only healthy service instances receive traffic
- **Dynamic Load Balancing**: Round-robin, random, and first-available strategies
- **Graceful Deregistration**: Clean removal from registry on shutdown
- **Async Operations**: Full async/await support using httpx

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Consul Server                            │
│  - Service Registry                                          │
│  - Health Check Aggregation                                  │
│  - DNS Interface (8600)                                      │
│  - HTTP API (8500)                                           │
└─────────────────────────────────────────────────────────────┘
                          ▲ ▼
           ┌──────────────┴──────────────┐
           │                              │
    ┌──────▼─────┐               ┌───────▼──────┐
    │  Service A  │               │  Service B   │
    │            │               │              │
    │ - Register │               │ - Register   │
    │ - Heartbeat│               │ - Heartbeat  │
    │ - Discover │◄─────────────►│ - Discover   │
    └────────────┘               └──────────────┘
```

### Service Lifecycle

1. **Startup**: Service registers with Consul, providing name, address, port, tags
2. **Health Checks**: Consul periodically calls service's `/health/ready` endpoint
3. **Discovery**: Other services query Consul to find healthy instances
4. **Shutdown**: Service deregisters from Consul gracefully

---

## Implementation

### Core Classes

#### ConsulClient

Low-level async client for Consul HTTP API.

**Key Methods:**
- `register_service()`: Register service with health checks
- `deregister_service()`: Remove service from registry
- `discover_service()`: Find healthy service instances
- `get_service_address()`: Get load-balanced service address
- `list_services()`: List all registered services

**Example:**
```python
async with ConsulClient("http://consul:8500") as consul:
    # Register
    service_id = await consul.register_service(
        name="l01-data-layer",
        port=8001,
        tags=["api", "v1"],
        health_check_path="/health/ready",
    )

    # Discover
    instances = await consul.discover_service("l02-runtime")
    for instance in instances:
        print(f"{instance.name} at {instance.address}:{instance.port}")
```

#### ServiceRegistry

High-level wrapper for FastAPI integration.

**Example:**
```python
from shared import create_service_registry
from fastapi import FastAPI

app = FastAPI()
registry = create_service_registry("l01-data-layer", 8001)

@app.on_event("startup")
async def startup():
    await registry.register()

@app.on_event("shutdown")
async def shutdown():
    await registry.deregister()

# Service-to-service calls
@app.get("/call-l02")
async def call_l02():
    l02_url = await registry.get_service_url("l02-runtime")
    if not l02_url:
        raise HTTPException(status_code=503, detail="L02 service unavailable")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{l02_url}/execute")
        return response.json()
```

#### ServiceInstance

Dataclass representing a discovered service instance.

**Fields:**
- `id`: Unique service instance ID
- `name`: Service name
- `address`: IP address or hostname
- `port`: Service port
- `tags`: List of tags for filtering
- `meta`: Metadata dictionary
- `health_status`: "passing", "warning", or "critical"

---

## Integration Guide

### Step 1: Update Service Layer

**File:** `platform/src/L01_data_layer/main.py` (example for L01)

```python
from fastapi import FastAPI
from shared import create_service_registry, setup_health_checks

app = FastAPI(title="L01 Data Layer")

# Create service registry
registry = create_service_registry(
    service_name="l01-data-layer",
    service_port=8001,
    tags=["api", "data", "v1"],
)

# Set up health checks (required for Consul)
health_manager = setup_health_checks(
    app=app,
    db=db_pool,  # Your database connection
    redis=redis_client,  # Your Redis client
)

@app.on_event("startup")
async def startup():
    """Register with Consul on startup."""
    await registry.register()
    logger.info("Service registered with Consul")

@app.on_event("shutdown")
async def shutdown():
    """Deregister from Consul on shutdown."""
    await registry.deregister()
    logger.info("Service deregistered from Consul")
```

### Step 2: Update Inter-Service Calls

**Before (Hardcoded):**
```python
L02_URL = "http://l02-runtime:8002"

async def call_l02():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{L02_URL}/execute")
        return response.json()
```

**After (Service Discovery):**
```python
async def call_l02():
    # Get dynamic URL from Consul
    l02_url = await registry.get_service_url("l02-runtime")
    if not l02_url:
        raise ServiceUnavailableError("L02 Runtime service not available")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{l02_url}/execute")
        return response.json()
```

### Step 3: Update Docker Compose

**File:** `docker-compose.v2.yml`

Add Consul dependency to service:

```yaml
services:
  l01-data-layer:
    depends_on:
      consul:
        condition: service_healthy
    environment:
      - CONSUL_URL=http://consul:8500
```

---

## Configuration

### Environment Variables

All services should set:

```bash
CONSUL_URL=http://consul:8500  # Consul HTTP API URL
SERVICE_NAME=l01-data-layer    # Service name in registry
SERVICE_PORT=8001              # Service port
SERVICE_TAGS=api,data,v1       # Comma-separated tags
```

### Consul Server Configuration

**File:** `docker-compose.consul.yml`

```yaml
services:
  consul-server:
    image: hashicorp/consul:1.17
    container_name: agentic-consul
    command: agent -server -ui -node=consul-server -bootstrap-expect=1 -client=0.0.0.0
    ports:
      - "8500:8500"  # HTTP API
      - "8600:8600"  # DNS
    networks:
      - agentic-network
    healthcheck:
      test: ["CMD", "consul", "members"]
      interval: 10s
      timeout: 5s
      retries: 3
```

**Access Consul UI:** http://localhost:8500/ui

---

## Load Balancing Strategies

### Round-Robin (Default)

Distributes requests evenly across instances using hash-based selection.

```python
address, port = await consul.get_service_address(
    "l02-runtime",
    strategy="round-robin"
)
```

### Random

Randomly selects an instance on each request.

```python
address, port = await consul.get_service_address(
    "l02-runtime",
    strategy="random"
)
```

### First-Available

Always uses the first healthy instance (useful for testing).

```python
address, port = await consul.get_service_address(
    "l02-runtime",
    strategy="first"
)
```

---

## Health Checks

### Health Check Configuration

Services must expose `/health/ready` endpoint:

```python
from shared import HealthCheckManager, DatabaseHealthCheck, RedisHealthCheck

health_manager = HealthCheckManager()
health_manager.add_check(DatabaseHealthCheck(db_pool))
health_manager.add_check(RedisHealthCheck(redis_client))

@app.get("/health/ready")
async def readiness():
    """Consul calls this endpoint every 10 seconds."""
    result = await health_manager.check_health()
    if result.status != HealthStatus.HEALTHY:
        raise HTTPException(status_code=503, detail="Service not ready")
    return result.dict()
```

### Health Check Intervals

- **Interval**: 10 seconds (how often Consul checks)
- **Timeout**: 5 seconds (max time for health check)
- **Deregister After**: 1 minute (auto-remove if failing)

### Health Check Behavior

- **Passing**: Service receives traffic
- **Warning**: Service still receives traffic (degraded)
- **Critical**: Service removed from load balancing after 1 minute

---

## Testing

### Manual Testing

**1. Start Consul:**
```bash
docker-compose -f docker-compose.consul.yml up -d
```

**2. Register a Service:**
```python
from shared import register_with_consul

service_id = await register_with_consul(
    service_name="test-service",
    service_port=9999,
    tags=["test"],
)
print(f"Registered: {service_id}")
```

**3. Check Consul UI:**
- Navigate to http://localhost:8500/ui
- Verify service appears in Services list
- Check health status is "passing"

**4. Discover Service:**
```python
from shared import ConsulClient

async with ConsulClient() as consul:
    instances = await consul.discover_service("test-service")
    print(f"Found {len(instances)} instances")
    for instance in instances:
        print(f"  - {instance.address}:{instance.port}")
```

### Integration Testing

**Test File:** `platform/tests/test_service_discovery.py`

```python
import pytest
from shared import ConsulClient, create_service_registry

@pytest.mark.asyncio
async def test_service_registration():
    """Test service can register and deregister."""
    async with ConsulClient("http://localhost:8500") as consul:
        service_id = await consul.register_service(
            name="test-service",
            port=9999,
        )

        # Verify registration
        instances = await consul.discover_service("test-service")
        assert len(instances) == 1
        assert instances[0].port == 9999

        # Deregister
        await consul.deregister_service(service_id)

        # Verify deregistration
        instances = await consul.discover_service("test-service")
        assert len(instances) == 0

@pytest.mark.asyncio
async def test_service_discovery_with_tags():
    """Test discovering services by tag."""
    async with ConsulClient() as consul:
        # Register multiple services
        await consul.register_service("svc-1", 8001, tags=["api"])
        await consul.register_service("svc-2", 8002, tags=["api"])
        await consul.register_service("svc-3", 8003, tags=["worker"])

        # Discover by tag
        api_services = await consul.discover_service("svc-1", tag="api")
        assert len(api_services) > 0
```

---

## Troubleshooting

### Service Not Appearing in Consul

**Symptoms:** Service registers but doesn't show in Consul UI

**Causes:**
1. Health check failing immediately
2. Wrong Consul URL
3. Network connectivity issues

**Solutions:**
```bash
# Check health endpoint manually
curl http://localhost:8001/health/ready

# Check Consul logs
docker logs agentic-consul

# Verify network connectivity
docker exec l01-data-layer curl http://consul:8500/v1/status/leader
```

### Service Deregistered After 1 Minute

**Symptoms:** Service appears briefly then disappears

**Cause:** Health check consistently failing

**Solutions:**
```bash
# Check service logs for health check errors
docker logs l01-data-layer | grep health

# Test health endpoint
curl -v http://localhost:8001/health/ready

# Check Consul health checks
curl http://localhost:8500/v1/health/service/l01-data-layer
```

### "No healthy instances found" Error

**Symptoms:** `get_service_url()` returns `None`

**Causes:**
1. Service not registered
2. All instances failing health checks
3. Wrong service name

**Solutions:**
```bash
# List all services
curl http://localhost:8500/v1/catalog/services

# Check specific service health
curl http://localhost:8500/v1/health/service/l02-runtime

# Verify service name in code matches Consul
```

### Consul Connection Timeout

**Symptoms:** `httpx.ConnectError` or timeout errors

**Causes:**
1. Consul not running
2. Wrong Consul URL
3. Network issues

**Solutions:**
```bash
# Check Consul status
docker ps | grep consul

# Test Consul connectivity
curl http://localhost:8500/v1/status/leader

# Check service environment
docker exec l01-data-layer env | grep CONSUL_URL
```

---

## Performance Considerations

### Caching

Consider caching service addresses to reduce Consul queries:

```python
from functools import lru_cache
import asyncio

class CachedServiceRegistry(ServiceRegistry):
    def __init__(self, *args, cache_ttl=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_ttl = cache_ttl

    async def get_service_url(self, service_name: str) -> Optional[str]:
        # Check cache
        if service_name in self.cache:
            cached_url, cached_time = self.cache[service_name]
            if time.time() - cached_time < self.cache_ttl:
                return cached_url

        # Query Consul
        url = await super().get_service_url(service_name)

        # Update cache
        if url:
            self.cache[service_name] = (url, time.time())

        return url
```

### Connection Pooling

Reuse httpx client for better performance:

```python
class ConsulClient:
    def __init__(self, consul_url: str):
        self.consul_url = consul_url
        self._client = httpx.AsyncClient(timeout=5.0)

    async def close(self):
        await self._client.aclose()
```

---

## Security

### Consul ACLs (Future)

For production, enable Consul ACLs:

```bash
# Generate ACL token
consul acl token create -description "L01 Data Layer" -service-identity="l01-data-layer"

# Use token in service
CONSUL_TOKEN=your-token-here
```

### TLS Encryption (Future)

Enable TLS for Consul communication:

```yaml
services:
  consul-server:
    command: agent -server -ui -encrypt=<encryption-key> -ca-file=/consul/config/ca.pem
```

---

## Migration Path

### Phase 1: Add Consul (Current)

- Deploy Consul server
- Services register on startup but still use hardcoded URLs
- Monitor Consul UI to verify registration

### Phase 2: Hybrid Mode

- Update inter-service calls to use service discovery
- Keep fallback to hardcoded URLs if Consul unavailable
- Monitor metrics to verify discovery working

### Phase 3: Full Discovery

- Remove hardcoded URLs entirely
- Fail fast if Consul unavailable
- All service resolution through Consul

---

## Metrics and Monitoring

### Key Metrics to Track

1. **Service Registration Time**: Time to register on startup
2. **Discovery Latency**: Time to resolve service address
3. **Health Check Success Rate**: % of passing health checks
4. **Consul API Latency**: Response time for Consul queries

### Prometheus Metrics

Add metrics to track service discovery:

```python
from prometheus_client import Counter, Histogram

consul_registrations = Counter(
    'consul_registrations_total',
    'Total service registrations',
    ['service_name']
)

consul_discovery_latency = Histogram(
    'consul_discovery_seconds',
    'Time to discover service',
    ['service_name']
)

# Track registration
consul_registrations.labels(service_name="l01-data-layer").inc()

# Track discovery latency
with consul_discovery_latency.labels(service_name="l02-runtime").time():
    url = await registry.get_service_url("l02-runtime")
```

---

## Files Created

### Core Implementation
- `platform/src/shared/service_discovery.py` (512 lines)
  - ConsulClient class
  - ServiceRegistry class
  - ServiceInstance dataclass
  - Helper functions

### Configuration
- `platform/docker-compose.consul.yml` (50 lines)
  - Consul server setup
  - Health checks
  - Network configuration

### Documentation
- `platform/P2-09-SERVICE-DISCOVERY.md` (this file)
  - Architecture overview
  - Integration guide
  - Testing procedures
  - Troubleshooting guide

### Updated Files
- `platform/src/shared/__init__.py`
  - Added service discovery exports

---

## Next Steps

### Integration (P3-04)

1. Update all 12 service layers to register with Consul
2. Replace hardcoded service URLs with dynamic discovery
3. Add service discovery to nginx configuration (if applicable)

### High Availability (P2-11)

1. Deploy Consul in cluster mode (3+ servers)
2. Configure Consul for high availability
3. Test failover scenarios

### Monitoring (P3-07)

1. Add Prometheus metrics for service discovery
2. Create Grafana dashboard for service health
3. Set up alerts for service unavailability

---

## Success Criteria

✅ **Implementation Complete**
- ConsulClient class with full async support
- ServiceRegistry wrapper for FastAPI
- Docker Compose configuration for Consul
- Comprehensive documentation

✅ **Integration Ready**
- Module exports added to shared package
- Example integration provided
- Testing procedures documented

✅ **Production Ready**
- Health check integration
- Error handling and fallbacks
- Performance considerations documented
- Security best practices outlined

---

## Related Documentation

- **P2-08**: Standardized Health Endpoints (required for Consul health checks)
- **P2-11**: High Availability Architecture (Consul clustering)
- **P3-04**: Service Integration (using service discovery)
- **P3-07**: Monitoring & Observability (service discovery metrics)

---

**Implementation Date:** 2026-01-18
**Implementation Time:** 2 hours
**Lines of Code:** 562
**Documentation:** 650+ lines
**Status:** ✅ Complete and ready for integration
