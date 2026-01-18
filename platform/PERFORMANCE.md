# Story Portal V2 - Performance Optimization Guide

## Overview

This document outlines performance optimization strategies and implementations for Story Portal V2.

## Current Performance Baseline

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API Response Time (p95) | < 500ms | TBD | Monitoring |
| Database Query Time (p95) | < 100ms | TBD | Monitoring |
| Redis Hit Rate | > 80% | TBD | Monitoring |
| Container Startup Time | < 30s | ~15s | ✓ |
| Memory Usage | < 12GB total | ~8GB | ✓ |

## 1. Database Performance

### Indexes

Critical indexes for query performance:

```sql
-- Events table (most queried)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_type_timestamp
  ON mcp_documents.events(type, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_agent_id
  ON mcp_documents.events(agent_id)
  WHERE agent_id IS NOT NULL;

-- Agents table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agents_status
  ON mcp_documents.agents(status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agents_created_at
  ON mcp_documents.agents(created_at DESC);

-- Sessions table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active
  ON mcp_documents.sessions(is_active, updated_at DESC)
  WHERE is_active = true;

-- API requests (L09)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_requests_timestamp
  ON mcp_documents.api_requests(timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_requests_status_code
  ON mcp_documents.api_requests(status_code, timestamp DESC);

-- Quality scores (L06)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quality_scores_component
  ON mcp_documents.quality_scores(component_type, component_id, calculated_at DESC);
```

### Connection Pooling

Optimize PostgreSQL connection pooling:

```yaml
# docker-compose.app.yml
postgres:
  command: >
    postgres
    -c max_connections=100
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=64MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c work_mem=2621kB
    -c min_wal_size=1GB
    -c max_wal_size=4GB
```

### Query Optimization

Common N+1 query patterns and fixes:

```python
# Before: N+1 queries
agents = get_all_agents()
for agent in agents:
    events = get_agent_events(agent.id)  # N queries

# After: Single query with JOIN
agents_with_events = db.query("""
    SELECT a.*,
           json_agg(e.*) as events
    FROM mcp_documents.agents a
    LEFT JOIN mcp_documents.events e ON e.agent_id = a.id
    GROUP BY a.id
""")
```

### Vacuum and Analyze

```sql
-- Automated maintenance
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05;

-- Manual vacuum (run during low traffic)
VACUUM ANALYZE mcp_documents.events;
VACUUM ANALYZE mcp_documents.api_requests;
```

## 2. Redis Performance

### Cache Strategy

```python
# Cache configuration
REDIS_CONFIG = {
    "default_ttl": 300,  # 5 minutes
    "max_memory": "512mb",
    "max_memory_policy": "allkeys-lru",
    "key_prefix": "sp_v2",
}

# Cache warming on startup
def warm_cache():
    """Pre-populate frequently accessed data"""
    # Load active agents
    agents = db.query("SELECT * FROM agents WHERE status = 'active'")
    for agent in agents:
        redis.setex(f"agent:{agent.id}", 300, json.dumps(agent))

    # Load service registry
    services = get_all_services()
    redis.setex("services:all", 600, json.dumps(services))
```

### Key Expiration Strategy

```python
# Tiered TTL based on access patterns
TTL_CONFIG = {
    "agent_metadata": 300,      # 5 min - frequently changing
    "service_registry": 600,    # 10 min - rarely changes
    "model_configs": 1800,      # 30 min - static
    "user_sessions": 3600,      # 1 hour - active sessions
    "api_responses": 60,        # 1 min - dynamic data
}
```

### Redis Pipeline for Bulk Operations

```python
# Before: Multiple round trips
for key in keys:
    value = redis.get(key)

# After: Single pipeline
pipeline = redis.pipeline()
for key in keys:
    pipeline.get(key)
results = pipeline.execute()
```

## 3. Application Performance

### Response Compression

```python
# FastAPI middleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Request Batching

```python
# Batch multiple API requests
@app.post("/api/v1/batch")
async def batch_requests(requests: List[BatchRequest]):
    """Execute multiple requests in a single API call"""
    results = await asyncio.gather(*[
        execute_request(req) for req in requests
    ])
    return {"results": results}
```

### Response Caching

```python
# Cache frequently accessed endpoints
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@app.get("/api/v1/services")
@cache(expire=60)  # Cache for 60 seconds
async def list_services():
    return get_all_services()
```

### Async I/O Optimization

```python
# Use async for all I/O operations
async def get_agent_with_events(agent_id: str):
    # Parallel fetch
    agent, events, metrics = await asyncio.gather(
        db.get_agent(agent_id),
        db.get_agent_events(agent_id),
        db.get_agent_metrics(agent_id)
    )
    return {
        "agent": agent,
        "events": events,
        "metrics": metrics
    }
```

## 4. Infrastructure Performance

### Docker Image Optimization

#### Multi-stage Builds

```dockerfile
# Before: 1.2GB image
FROM python:3.11
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]

# After: 200MB image
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

#### BuildKit Caching

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with cache
docker build \
  --cache-from=type=registry,ref=myregistry/l01-data-layer:latest \
  --cache-to=type=inline \
  -t l01-data-layer:latest .
```

### Container Resource Tuning

Current allocations are conservative. Monitor actual usage and adjust:

```bash
# Monitor resource usage
docker stats --no-stream

# Adjust based on actual usage
# If a service uses 200MB but allocated 1GB, reduce to 512MB
```

## 5. Network Performance

### HTTP/2 Support

```nginx
# nginx.conf for Platform UI
server {
    listen 443 ssl http2;
    server_name _;

    # HTTP/2 push for critical resources
    http2_push /static/main.js;
    http2_push /static/main.css;
}
```

### Connection Keep-Alive

```python
# FastAPI Uvicorn configuration
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,
    workers=4,
    loop="uvloop",  # Faster event loop
    http="httptools",  # Faster HTTP parser
    limit_concurrency=1000,
    backlog=2048,
    timeout_keep_alive=5
)
```

## 6. Monitoring & Profiling

### Prometheus Metrics

```python
# Add custom metrics
from prometheus_client import Counter, Histogram

request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

@app.middleware("http")
async def track_metrics(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    return response
```

### Performance Profiling

```python
# cProfile for Python profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... code to profile ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest functions
```

## 7. Load Testing

### k6 Performance Tests

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 100 },  // Sustained load
    { duration: '2m', target: 200 },  // Peak load
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // Test L09 API Gateway
  let res = http.get('http://localhost:8009/health/live');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });

  // Test L12 Service Hub
  res = http.get('http://localhost:8012/v1/services');
  check(res, {
    'returns services': (r) => JSON.parse(r.body).length > 0,
  });

  sleep(1);
}
```

### Running Load Tests

```bash
# Install k6
brew install k6  # macOS

# Run load test
k6 run load-test.js

# Run with custom parameters
k6 run --vus 100 --duration 5m load-test.js

# Save results
k6 run --out json=results.json load-test.js
```

## 8. Performance Checklist

### Database
- [ ] Indexes created for all frequently queried columns
- [ ] Connection pooling configured (max_connections=100)
- [ ] Query plans analyzed for slow queries
- [ ] Autovacuum enabled and tuned
- [ ] N+1 queries eliminated

### Redis
- [ ] Cache TTL configured for all keys
- [ ] Max memory and eviction policy set
- [ ] Pipeline used for bulk operations
- [ ] Cache hit rate monitored (target > 80%)
- [ ] Cache warming implemented

### Application
- [ ] Response compression enabled
- [ ] Async I/O used throughout
- [ ] Database connections pooled
- [ ] Response caching for read-heavy endpoints
- [ ] Request batching implemented

### Infrastructure
- [ ] Multi-stage Docker builds
- [ ] Docker BuildKit caching enabled
- [ ] Container resources tuned based on actual usage
- [ ] HTTP/2 enabled
- [ ] Connection keep-alive configured

### Monitoring
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Load tests passing with p95 < 500ms
- [ ] Resource usage monitored
- [ ] Slow query logging enabled

## 9. Performance Targets

### API Response Times (p95)
- Health checks: < 50ms
- List endpoints: < 200ms
- Detail endpoints: < 300ms
- Write operations: < 500ms

### Database Query Times (p95)
- Simple selects: < 10ms
- Joins (2-3 tables): < 50ms
- Complex aggregations: < 100ms

### Cache Hit Rates
- Service registry: > 95%
- Agent metadata: > 80%
- Session data: > 90%

### Resource Usage
- Total memory: < 12GB
- Total CPU: < 10 cores average
- Database connections: < 50 active
- Redis memory: < 512MB

## 10. Continuous Optimization

### Weekly Tasks
- Review Grafana dashboards for performance regressions
- Analyze slow query logs
- Check cache hit rates
- Review resource usage trends

### Monthly Tasks
- Run full load test suite
- Update performance baselines
- Optimize identified bottlenecks
- Review and tune database indexes

### Quarterly Tasks
- Comprehensive performance audit
- Upgrade dependencies for performance improvements
- Benchmark against similar platforms
- Plan architectural improvements

## References

- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/runtime-config.html)
- [Redis Performance Best Practices](https://redis.io/docs/manual/optimization/)
- [FastAPI Performance Guide](https://fastapi.tiangolo.com/deployment/concepts/)
- [Docker BuildKit](https://docs.docker.com/build/buildkit/)
- [k6 Load Testing](https://k6.io/docs/)
