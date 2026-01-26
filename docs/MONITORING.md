# Monitoring Guide - Story Portal Platform V2

**Version:** 2.0.0
**Last Updated:** 2026-01-18

---

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Stack](#monitoring-stack)
3. [Prometheus Configuration](#prometheus-configuration)
4. [Grafana Dashboards](#grafana-dashboards)
5. [Metrics Reference](#metrics-reference)
6. [Alerting](#alerting)
7. [Health Checks](#health-checks)
8. [Performance Monitoring](#performance-monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

The Story Portal Platform V2 includes a comprehensive monitoring stack based on Prometheus and Grafana, providing real-time visibility into system health, performance, and resource utilization.

### Monitoring Components

- **Prometheus:** Time-series database and monitoring system
- **Grafana:** Visualization and dashboarding platform
- **PostgreSQL Exporter:** Database metrics collection
- **Redis Exporter:** Cache metrics collection
- **cAdvisor:** Container metrics (optional)

### Quick Start

```bash
# Access monitoring interfaces
make prometheus    # http://localhost:9090
make grafana       # http://localhost:3000 (admin/admin)

# Check service health
make health

# View metrics
curl http://localhost:9090/metrics
```

---

## Monitoring Stack

### Architecture

```
┌─────────────────┐
│  Application    │
│  Services       │──┐
│  (L01-L12)      │  │
└─────────────────┘  │
                     │ /metrics
┌─────────────────┐  │
│  PostgreSQL     │──┤
│  + Exporter     │  │
└─────────────────┘  │
                     │
┌─────────────────┐  │
│  Redis          │──┤
│  + Exporter     │  │
└─────────────────┘  │
                     │
                     ▼
              ┌─────────────┐
              │ Prometheus  │
              │ :9090       │
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │  Grafana    │
              │  :3000      │
              └─────────────┘
```

### Access Information

| Service | Port | URL | Default Credentials |
|---------|------|-----|---------------------|
| Prometheus | 9090 | http://localhost:9090 | None |
| Grafana | 3000 | http://localhost:3000 | admin/admin |
| PostgreSQL Exporter | 9187 | http://localhost:9187/metrics | None |
| Redis Exporter | 9121 | http://localhost:9121/metrics | None |

---

## Prometheus Configuration

### Configuration File

Prometheus configuration is located at: `/platform/monitoring/prometheus/prometheus.yml`

### Scrape Targets

Prometheus scrapes metrics from the following targets every 15 seconds:

```yaml
scrape_configs:
  # Application Services (L01-L12)
  - job_name: 'agentic-services'
    static_configs:
      - targets:
          - 'agentic-l01-data-layer:8001'
          - 'agentic-l02-runtime:8002'
          - 'agentic-l03-tool-execution:8003'
          - 'agentic-l04-model-gateway:8004'
          - 'agentic-l05-planning:8005'
          - 'agentic-l06-evaluation:8006'
          - 'agentic-l07-learning:8007'
          - 'agentic-l09-api-gateway:8009'
          - 'agentic-l10-human-interface:8010'
          - 'agentic-l11-integration:8011'
          - 'agentic-l12-nl-interface:8012'

  # PostgreSQL Database
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis Cache
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Viewing Targets

Navigate to **Prometheus UI → Status → Targets** to see all scrape targets and their health status.

```bash
# Check target status via CLI
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

### Adding Custom Metrics

To add custom metrics to your application:

1. **Instrument your code** (FastAPI example):

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_connections = Gauge('active_connections', 'Number of active connections')

# Use in endpoints
@app.get("/api/data")
async def get_data():
    request_count.labels(method='GET', endpoint='/api/data').inc()
    with request_duration.time():
        # Your logic here
        return {"data": "value"}
```

2. **Expose /metrics endpoint**:

```python
from prometheus_client import make_asgi_app

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

3. **Verify metrics**:

```bash
curl http://localhost:8001/metrics | grep http_requests_total
```

---

## Grafana Dashboards

### Initial Setup

1. **Access Grafana**: http://localhost:3000
2. **Login**: admin / admin (change on first login)
3. **Add Prometheus data source**:
   - Configuration → Data Sources → Add data source
   - Select Prometheus
   - URL: `http://prometheus:9090`
   - Click "Save & Test"

### Pre-built Dashboards

#### 1. Platform Overview Dashboard

Create a new dashboard with the following panels:

**Service Health Status**
```promql
up{job="agentic-services"}
```

**Request Rate (requests/sec)**
```promql
rate(http_requests_total[5m])
```

**Error Rate**
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

**Response Time (p95)**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### 2. Database Dashboard

**PostgreSQL Connection Count**
```promql
pg_stat_database_numbackends{datname="agentic_platform"}
```

**Query Performance**
```promql
rate(pg_stat_statements_calls_total[5m])
```

**Database Size**
```promql
pg_database_size_bytes{datname="agentic_platform"}
```

**Active Transactions**
```promql
pg_stat_activity_count{state="active"}
```

#### 3. Redis Dashboard

**Redis Memory Usage**
```promql
redis_memory_used_bytes
```

**Cache Hit Rate**
```promql
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

**Connected Clients**
```promql
redis_connected_clients
```

#### 4. Container Resources Dashboard

**CPU Usage by Container**
```promql
rate(container_cpu_usage_seconds_total{name=~"agentic-.*"}[5m])
```

**Memory Usage by Container**
```promql
container_memory_usage_bytes{name=~"agentic-.*"}
```

**Network I/O**
```promql
rate(container_network_receive_bytes_total{name=~"agentic-.*"}[5m])
```

### Importing Dashboards

Grafana provides community dashboards that can be imported:

1. **PostgreSQL Dashboard**: https://grafana.com/grafana/dashboards/9628
2. **Redis Dashboard**: https://grafana.com/grafana/dashboards/11835
3. **Docker Container Dashboard**: https://grafana.com/grafana/dashboards/193

**To import:**
- Grafana UI → Dashboards → Import
- Enter dashboard ID or upload JSON
- Select Prometheus data source

---

## Metrics Reference

### Application Metrics

All application services (L01-L12) expose the following standard metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request duration distribution |
| `http_requests_in_progress` | Gauge | Current requests being processed |
| `app_info` | Info | Application version and metadata |

### PostgreSQL Metrics

Collected via `postgres_exporter`:

| Metric | Description |
|--------|-------------|
| `pg_up` | Database reachability (1=up, 0=down) |
| `pg_stat_database_numbackends` | Active connections |
| `pg_stat_database_xact_commit` | Committed transactions |
| `pg_stat_database_xact_rollback` | Rolled back transactions |
| `pg_stat_database_blks_read` | Disk blocks read |
| `pg_stat_database_blks_hit` | Buffer cache hits |
| `pg_database_size_bytes` | Database size in bytes |
| `pg_stat_activity_count` | Active queries by state |

### Redis Metrics

Collected via `redis_exporter`:

| Metric | Description |
|--------|-------------|
| `redis_up` | Redis reachability (1=up, 0=down) |
| `redis_connected_clients` | Number of connected clients |
| `redis_memory_used_bytes` | Memory consumption |
| `redis_memory_max_bytes` | Maximum memory limit |
| `redis_keyspace_hits_total` | Cache hits |
| `redis_keyspace_misses_total` | Cache misses |
| `redis_db_keys` | Number of keys per database |
| `redis_evicted_keys_total` | Evicted keys (memory pressure) |

### Custom Business Metrics

Define business-specific metrics for your use case:

```python
from prometheus_client import Counter, Histogram

# Agent execution metrics
agent_executions = Counter('agent_executions_total', 'Total agent executions', ['agent_type', 'status'])
agent_duration = Histogram('agent_execution_duration_seconds', 'Agent execution time', ['agent_type'])

# Task metrics
tasks_created = Counter('tasks_created_total', 'Total tasks created')
tasks_completed = Counter('tasks_completed_total', 'Total tasks completed', ['status'])
```

---

## Alerting

### Prometheus Alert Rules

Alert rules are defined in `/platform/monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: platform_alerts
    interval: 30s
    rules:
      # Service Health Alerts
      - alert: ServiceDown
        expr: up{job="agentic-services"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.job }} instance {{ $labels.instance }} has been down for more than 1 minute."

      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes."

      # Database Alerts
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"

      - alert: HighDatabaseConnections
        expr: pg_stat_database_numbackends{datname="agentic_platform"} > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High number of database connections"
          description: "Current connections: {{ $value }}"

      # Redis Alerts
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"

      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage is high"
          description: "Memory usage: {{ $value | humanizePercentage }}"

      # Resource Alerts
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{name=~"agentic-.*"}[5m]) > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.name }}"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{name=~"agentic-.*"} / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.name }}"
```

### Viewing Active Alerts

**Prometheus UI:**
- Navigate to **Prometheus UI → Alerts**
- View active, pending, and firing alerts

**API:**
```bash
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name: .labels.alertname, state: .state}'
```

### Alert Notification Channels

Configure Alertmanager for alert notifications:

**Alertmanager Configuration** (`/platform/monitoring/alertmanager/alertmanager.yml`):

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#platform-alerts'
        title: 'Platform Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## Health Checks

### Standardized Health Endpoints

All services expose standardized health check endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health` | Basic health check | `{"status": "healthy", "service": "...", "version": "2.0.0"}` |
| `/health/live` | Liveness probe | Returns 200 if service is alive |
| `/health/ready` | Readiness probe | Returns 200 if service is ready to accept traffic |
| `/health/detailed` | Comprehensive diagnostics | Detailed health info (may require auth) |

### Health Check Script

Use the Makefile health check:

```bash
# Quick health check
make health

# Detailed health check with JSON responses
make health-detailed

# Continuous monitoring
watch -n 5 'make health'
```

### Kubernetes/Docker Health Probes

Configure health probes in `docker-compose.v2.yml`:

```yaml
services:
  l01-data-layer:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Performance Monitoring

### Query Performance (PostgreSQL)

Monitor slow queries using `pg_stat_statements`:

```sql
-- Top 10 slowest queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Most frequently executed queries
SELECT
    query,
    calls,
    total_exec_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

**Via Prometheus:**
```promql
topk(10, rate(pg_stat_statements_mean_exec_time_seconds[5m]))
```

### Cache Performance (Redis)

Monitor cache hit ratio:

```bash
# Via Redis CLI
docker exec agentic-redis redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"

# Calculate hit ratio
hits=$(docker exec agentic-redis redis-cli INFO stats | grep keyspace_hits | cut -d: -f2 | tr -d '\r')
misses=$(docker exec agentic-redis redis-cli INFO stats | grep keyspace_misses | cut -d: -f2 | tr -d '\r')
echo "Hit ratio: $(echo "scale=2; 100*$hits/($hits+$misses)" | bc)%"
```

**Via Prometheus:**
```promql
# Cache hit rate
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

### Application Performance

**Request latency percentiles:**
```promql
# p50 (median)
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Throughput (requests per second):**
```promql
rate(http_requests_total[5m])
```

---

## Troubleshooting

### Common Issues

#### 1. Prometheus Not Scraping Targets

**Symptoms:** Targets showing as "DOWN" in Prometheus UI

**Diagnosis:**
```bash
# Check Prometheus logs
docker logs agentic-prometheus

# Verify target is accessible
curl http://localhost:8001/metrics

# Check network connectivity
docker exec agentic-prometheus wget -O- http://agentic-l01-data-layer:8001/metrics
```

**Solutions:**
- Verify service is running: `make ps`
- Check service health: `make health`
- Verify metrics endpoint: `curl http://localhost:8001/metrics`
- Check Prometheus config: `/platform/monitoring/prometheus/prometheus.yml`

#### 2. Missing Metrics in Grafana

**Diagnosis:**
```bash
# Query Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=up'

# Check data source connection in Grafana
# Configuration → Data Sources → Prometheus → Test
```

**Solutions:**
- Verify Prometheus data source URL: `http://prometheus:9090`
- Check metric names: Prometheus UI → Graph → "Metrics Explorer"
- Verify time range in Grafana dashboard

#### 3. High Memory Usage

**Diagnosis:**
```bash
# Check container stats
docker stats --no-stream | grep agentic

# Check Prometheus retention
docker exec agentic-prometheus cat /etc/prometheus/prometheus.yml | grep retention
```

**Solutions:**
- Adjust Prometheus retention: `--storage.tsdb.retention.time=15d`
- Reduce scrape frequency in `prometheus.yml`
- Increase container memory limits in `docker-compose.v2.yml`

#### 4. Alerts Not Firing

**Diagnosis:**
```bash
# Check alert rules are loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {alert: .name, state: .state}'

# Manually evaluate alert expression
curl 'http://localhost:9090/api/v1/query?query=up{job="agentic-services"}==0'
```

**Solutions:**
- Verify alert rules syntax: `/platform/monitoring/prometheus/alerts.yml`
- Check Alertmanager is running: `docker ps | grep alertmanager`
- Review Alertmanager config: `/platform/monitoring/alertmanager/alertmanager.yml`

---

## Best Practices

### 1. Metric Naming Conventions

Follow Prometheus naming conventions:

```
<namespace>_<subsystem>_<name>_<unit>

Examples:
- http_requests_total (counter)
- http_request_duration_seconds (histogram)
- database_connections_active (gauge)
```

### 2. Label Usage

- Use labels for dimensions (method, endpoint, status)
- Avoid high-cardinality labels (user IDs, UUIDs)
- Keep label count reasonable (< 10 labels per metric)

**Good:**
```promql
http_requests_total{method="GET", endpoint="/api/users", status="200"}
```

**Bad:**
```promql
http_requests_total{method="GET", endpoint="/api/users/12345", user_id="67890"}
```

### 3. Alert Fatigue Prevention

- Set appropriate thresholds (don't alert on minor issues)
- Use `for` duration to avoid flapping alerts
- Group related alerts
- Implement severity levels (critical, warning, info)

### 4. Dashboard Organization

- Create role-specific dashboards (ops, dev, business)
- Use variables for dynamic filtering
- Include links to related dashboards
- Document dashboard purpose and metrics

### 5. Regular Review

- Review alert rules quarterly
- Clean up unused metrics
- Optimize slow queries
- Update retention policies based on needs

### 6. Capacity Planning

Monitor trends for:
- Database growth rate
- Request rate trends
- Resource utilization patterns
- Cache effectiveness

Use trend data to predict when scaling is needed.

---

## Additional Resources

- **Prometheus Documentation:** https://prometheus.io/docs/
- **Grafana Documentation:** https://grafana.com/docs/
- **PromQL Basics:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Community Dashboards:** https://grafana.com/grafana/dashboards/

---

## Quick Reference Commands

```bash
# Start monitoring stack
make up

# Access dashboards
make prometheus
make grafana

# Health checks
make health
make health-detailed
make status

# View metrics
curl http://localhost:9090/metrics          # Prometheus metrics
curl http://localhost:8001/metrics          # L01 service metrics
curl http://localhost:9187/metrics          # PostgreSQL exporter
curl http://localhost:9121/metrics          # Redis exporter

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'
curl 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])'

# View logs
make logs
make logs | grep -i error

# Container stats
make stats
docker stats --no-stream

# Database monitoring
make db-shell
# Then run: SELECT * FROM pg_stat_activity;

# Redis monitoring
make redis-shell
# Then run: INFO, DBSIZE, SLOWLOG GET 10
```

---

**Document Version:** 1.0.0
**Last Review:** 2026-01-18
**Next Review:** 2026-04-18
