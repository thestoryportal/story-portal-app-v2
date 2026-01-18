# Story Portal V2 - High Availability Guide

## Overview

This document outlines the high availability (HA) architecture for Story Portal V2, ensuring zero-downtime operations and fault tolerance.

## Architecture Overview

```
┌─────────────────┐
│   HAProxy LB    │  (Load Balancer)
│   :8009/:3000   │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    │         │        │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ L09-1 │ │ L09-2 │ │ L09-3 │  (API Gateway replicas)
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └─────────┼─────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────────┐  ┌───────▼──────┐
│ PostgreSQL │  │ Redis Cluster │
│ Primary+   │  │ + Sentinel    │
│ Replica    │  │               │
└────────────┘  └───────────────┘
```

## 1. Load Balancing

### HAProxy Configuration

Create `haproxy.cfg`:

```haproxy
global
    maxconn 4096
    log stdout format raw local0

defaults
    mode http
    log global
    option httplog
    option dontlognull
    option forwardfor
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend http-in
    bind *:8009
    default_backend l09-api-gateway

frontend ui-in
    bind *:3000
    default_backend platform-ui

backend l09-api-gateway
    balance roundrobin
    option httpchk GET /health/live
    http-check expect status 200
    server l09-1 l09-api-gateway-1:8009 check inter 2000 rise 2 fall 3
    server l09-2 l09-api-gateway-2:8009 check inter 2000 rise 2 fall 3
    server l09-3 l09-api-gateway-3:8009 check inter 2000 rise 2 fall 3

backend platform-ui
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    server ui-1 platform-ui-1:80 check inter 2000 rise 2 fall 3
    server ui-2 platform-ui-2:80 check inter 2000 rise 2 fall 3

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    stats admin if TRUE
```

### Docker Compose HA Configuration

Create `docker-compose.ha.yml`:

```yaml
version: '3.8'

services:
  # HAProxy Load Balancer
  haproxy:
    image: haproxy:2.8-alpine
    container_name: agentic-haproxy
    ports:
      - "8009:8009"
      - "3000:3000"
      - "8404:8404"  # HAProxy stats
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - l09-api-gateway-1
      - l09-api-gateway-2
      - l09-api-gateway-3
    networks:
      - agentic-network
    restart: unless-stopped

  # L09 API Gateway - 3 replicas
  l09-api-gateway-1:
    extends:
      file: docker-compose.app.yml
      service: l09-api-gateway
    container_name: l09-api-gateway-1
    ports: []  # Remove direct port exposure

  l09-api-gateway-2:
    extends:
      file: docker-compose.app.yml
      service: l09-api-gateway
    container_name: l09-api-gateway-2
    ports: []

  l09-api-gateway-3:
    extends:
      file: docker-compose.app.yml
      service: l09-api-gateway
    container_name: l09-api-gateway-3
    ports: []

  # Platform UI - 2 replicas
  platform-ui-1:
    extends:
      file: docker-compose.app.yml
      service: platform-ui
    container_name: platform-ui-1
    ports: []

  platform-ui-2:
    extends:
      file: docker-compose.app.yml
      service: platform-ui
    container_name: platform-ui-2
    ports: []

  # Core services - 2 replicas each
  l01-data-layer-1:
    extends:
      file: docker-compose.app.yml
      service: l01-data-layer
    container_name: l01-data-layer-1

  l01-data-layer-2:
    extends:
      file: docker-compose.app.yml
      service: l01-data-layer
    container_name: l01-data-layer-2

networks:
  agentic-network:
    external: true
```

## 2. PostgreSQL High Availability

### PostgreSQL Replication

#### Primary Configuration

```sql
-- On primary server
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET max_replication_slots = 3;
ALTER SYSTEM SET hot_standby = on;

-- Create replication user
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'repl_password';
```

#### Replica Configuration

```yaml
# docker-compose.ha.yml
postgres-replica:
  image: pgvector/pgvector:pg16
  container_name: agentic-postgres-replica
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - PGDATA=/var/lib/postgresql/data/pgdata
  command: >
    bash -c "
    if [ ! -f /var/lib/postgresql/data/pgdata/PG_VERSION ]; then
      pg_basebackup -h postgres -D /var/lib/postgresql/data/pgdata -U replicator -v -P -W;
      echo 'primary_conninfo = ''host=postgres port=5432 user=replicator password=repl_password''' >> /var/lib/postgresql/data/pgdata/postgresql.auto.conf;
      echo 'hot_standby = on' >> /var/lib/postgresql/data/pgdata/postgresql.auto.conf;
      touch /var/lib/postgresql/data/pgdata/standby.signal;
    fi;
    postgres
    "
  volumes:
    - postgres_replica_data:/var/lib/postgresql/data
  networks:
    - agentic-network
  restart: unless-stopped
```

### PostgreSQL Failover

Use `pg_auto_failover` or `Patroni` for automatic failover:

```yaml
# Using Patroni for automatic failover
patroni:
  image: patroni/patroni:latest
  container_name: agentic-patroni
  environment:
    - PATRONI_NAME=postgres-1
    - PATRONI_POSTGRESQL_CONNECT_ADDRESS=postgres:5432
    - PATRONI_POSTGRESQL_DATA_DIR=/var/lib/postgresql/data
    - PATRONI_RESTAPI_CONNECT_ADDRESS=patroni:8008
    - PATRONI_ETCD_HOST=etcd:2379
  volumes:
    - postgres_data:/var/lib/postgresql/data
  networks:
    - agentic-network
```

## 3. Redis High Availability

### Redis Sentinel Mode

```yaml
# Redis master
redis-master:
  image: redis:7-alpine
  container_name: agentic-redis-master
  command: redis-server --requirepass redis_password --masterauth redis_password
  volumes:
    - redis_master_data:/data
  networks:
    - agentic-network
  restart: unless-stopped

# Redis replica 1
redis-replica-1:
  image: redis:7-alpine
  container_name: agentic-redis-replica-1
  command: redis-server --replicaof redis-master 6379 --requirepass redis_password --masterauth redis_password
  volumes:
    - redis_replica1_data:/data
  networks:
    - agentic-network
  restart: unless-stopped

# Redis replica 2
redis-replica-2:
  image: redis:7-alpine
  container_name: agentic-redis-replica-2
  command: redis-server --replicaof redis-master 6379 --requirepass redis_password --masterauth redis_password
  volumes:
    - redis_replica2_data:/data
  networks:
    - agentic-network
  restart: unless-stopped

# Redis Sentinel (3 instances for quorum)
redis-sentinel-1:
  image: redis:7-alpine
  container_name: agentic-sentinel-1
  command: redis-sentinel /etc/redis/sentinel.conf
  volumes:
    - ./redis-sentinel.conf:/etc/redis/sentinel.conf
  networks:
    - agentic-network
  restart: unless-stopped

redis-sentinel-2:
  image: redis:7-alpine
  container_name: agentic-sentinel-2
  command: redis-sentinel /etc/redis/sentinel.conf
  volumes:
    - ./redis-sentinel.conf:/etc/redis/sentinel.conf
  networks:
    - agentic-network
  restart: unless-stopped

redis-sentinel-3:
  image: redis:7-alpine
  container_name: agentic-sentinel-3
  command: redis-sentinel /etc/redis/sentinel.conf
  volumes:
    - ./redis-sentinel.conf:/etc/redis/sentinel.conf
  networks:
    - agentic-network
  restart: unless-stopped
```

### Sentinel Configuration

Create `redis-sentinel.conf`:

```
port 26379
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
sentinel auth-pass mymaster redis_password
```

## 4. Service Replication

### L12 Service Hub Discovery

With HA setup, L12 needs to discover all service replicas:

```python
# L12 service registry configuration
SERVICE_DISCOVERY_CONFIG = {
    "L09_API_GATEWAY": [
        "http://l09-api-gateway-1:8009",
        "http://l09-api-gateway-2:8009",
        "http://l09-api-gateway-3:8009"
    ],
    "L01_DATA_LAYER": [
        "http://l01-data-layer-1:8001",
        "http://l01-data-layer-2:8001"
    ],
    # ... other services
}
```

## 5. Health Checks & Monitoring

### Service Health Checks

All services must implement:
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

```python
@app.get("/health/live")
async def liveness():
    """Quick check if service is alive"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """Check if service is ready to accept traffic"""
    # Check dependencies
    db_ok = await check_database()
    redis_ok = await check_redis()

    if db_ok and redis_ok:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Not ready")
```

### Prometheus Monitoring

```yaml
# prometheus/alerts.yml
groups:
  - name: high-availability
    rules:
      - alert: ServiceInstanceDown
        expr: up{job=~"l.*"} == 0
        for: 2m
        annotations:
          summary: "Service instance {{ $labels.instance }} is down"

      - alert: LoadBalancerUnhealthy
        expr: haproxy_backend_up{backend="l09-api-gateway"} < 2
        annotations:
          summary: "Less than 2 L09 instances healthy"

      - alert: DatabaseReplicationLag
        expr: pg_replication_lag > 60
        annotations:
          summary: "PostgreSQL replication lag > 60 seconds"
```

## 6. Zero-Downtime Deployments

### Rolling Updates

```bash
#!/bin/bash
# rolling-update.sh

SERVICES="l09-api-gateway-1 l09-api-gateway-2 l09-api-gateway-3"

for SERVICE in $SERVICES; do
  echo "Updating $SERVICE..."

  # Pull new image
  docker-compose -f docker-compose.ha.yml pull $SERVICE

  # Update one instance
  docker-compose -f docker-compose.ha.yml up -d $SERVICE

  # Wait for health check
  echo "Waiting for $SERVICE to be healthy..."
  for i in {1..30}; do
    if docker inspect $SERVICE | grep -q "healthy"; then
      echo "$SERVICE is healthy"
      break
    fi
    sleep 2
  done

  # Brief pause between updates
  sleep 5
done

echo "Rolling update complete"
```

## 7. Disaster Recovery

### Backup Strategy

1. **Continuous**: WAL archiving (PostgreSQL)
2. **Hourly**: Redis snapshots
3. **Daily**: Full database backup
4. **Weekly**: Application state backup

### Recovery Procedures

```bash
# PostgreSQL Point-in-Time Recovery (PITR)
pg_basebackup -h postgres -D /var/lib/postgresql/data/restore -U replicator -P
# Apply WAL logs to desired point

# Redis recovery
redis-cli --rdb /backup/redis.rdb
```

## 8. Capacity Planning

### Resource Requirements (HA Setup)

| Component | Instances | CPU/Instance | Memory/Instance | Total CPU | Total Memory |
|-----------|-----------|--------------|-----------------|-----------|--------------|
| HAProxy | 1 | 0.5 | 256MB | 0.5 | 256MB |
| L09 Gateway | 3 | 2.0 | 1GB | 6.0 | 3GB |
| L01 Data | 2 | 1.0 | 1GB | 2.0 | 2GB |
| PostgreSQL | 2 | 2.0 | 2GB | 4.0 | 4GB |
| Redis | 3+3 | 0.5 | 512MB | 3.0 | 3GB |
| Other Services | 2 each | 1.0 | 1GB | 20.0 | 20GB |
| **Total** | - | - | - | **35.5** | **32.2GB** |

## 9. Testing HA Setup

### Chaos Testing

```bash
# Test service failure
docker stop l09-api-gateway-1
# Verify traffic continues through other instances

# Test database failover
docker stop agentic-postgres
# Verify replica promotion

# Test Redis failover
docker stop redis-master
# Verify sentinel promotes replica
```

### Load Testing with HA

```javascript
// k6 HA load test
export let options = {
  stages: [
    { duration: '5m', target: 500 },  // Ramp to 500 users
    { duration: '10m', target: 500 }, // Sustain
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<1000'],
    http_req_failed: ['rate<0.001'],  // < 0.1% errors
  },
};
```

## 10. HA Checklist

### Pre-Production
- [ ] HAProxy configured with health checks
- [ ] 3+ L09 API Gateway instances
- [ ] PostgreSQL replication configured
- [ ] Redis Sentinel mode enabled
- [ ] All services have health check endpoints
- [ ] Prometheus alerts configured
- [ ] Rolling update script tested
- [ ] Backup and recovery tested
- [ ] Chaos testing completed
- [ ] Load testing passed with HA

### Operational
- [ ] Monitor HAProxy stats (port 8404)
- [ ] Check replication lag daily
- [ ] Test failover monthly
- [ ] Review capacity quarterly
- [ ] Update disaster recovery plan

## References

- [HAProxy Documentation](http://www.haproxy.org/doc/)
- [PostgreSQL Replication](https://www.postgresql.org/docs/current/high-availability.html)
- [Redis Sentinel](https://redis.io/docs/manual/sentinel/)
- [Patroni (PostgreSQL HA)](https://patroni.readthedocs.io/)
