#!/bin/bash
set -e

# Story Portal V2 - Performance Optimization Script
# Implements performance optimizations for database and services

echo "==========================================="
echo "Story Portal V2 - Performance Optimization"
echo "==========================================="
echo ""

# Check prerequisites
if ! docker ps | grep -q agentic-postgres; then
  echo "Error: PostgreSQL container not running"
  exit 1
fi

# 1. Create database indexes
echo "[1/6] Creating database indexes..."
docker exec agentic-postgres psql -U postgres agentic_platform <<'SQL'
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

SELECT 'Indexes created successfully' as status;
SQL

if [ $? -eq 0 ]; then
  echo "  ✓ Database indexes created"
else
  echo "  ⚠️  Some indexes may already exist"
fi

# 2. Optimize PostgreSQL configuration
echo ""
echo "[2/6] Optimizing PostgreSQL configuration..."
docker exec agentic-postgres psql -U postgres <<'SQL'
-- Connection and memory settings
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET work_mem = '2621kB';

-- WAL settings
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET default_statistics_target = 100;

-- Autovacuum
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05;

SELECT pg_reload_conf();
SELECT 'PostgreSQL configuration optimized' as status;
SQL

if [ $? -eq 0 ]; then
  echo "  ✓ PostgreSQL configuration optimized"
  echo "  Note: Some settings require PostgreSQL restart to take effect"
else
  echo "  ⚠️  Configuration optimization failed"
fi

# 3. Run VACUUM ANALYZE
echo ""
echo "[3/6] Running VACUUM ANALYZE..."
docker exec agentic-postgres psql -U postgres agentic_platform <<'SQL'
VACUUM ANALYZE mcp_documents.events;
VACUUM ANALYZE mcp_documents.agents;
VACUUM ANALYZE mcp_documents.api_requests;
VACUUM ANALYZE mcp_documents.sessions;
SELECT 'VACUUM ANALYZE complete' as status;
SQL

if [ $? -eq 0 ]; then
  echo "  ✓ VACUUM ANALYZE complete"
else
  echo "  ⚠️  VACUUM ANALYZE failed"
fi

# 4. Analyze query performance
echo ""
echo "[4/6] Analyzing slow queries..."
docker exec agentic-postgres psql -U postgres agentic_platform <<'SQL'
-- Enable query logging temporarily
ALTER SYSTEM SET log_min_duration_statement = 100;
SELECT pg_reload_conf();

-- Show table statistics
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes
FROM pg_stat_user_tables
WHERE schemaname = 'mcp_documents'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
SQL

echo "  ✓ Query analysis complete"

# 5. Check Redis performance
echo ""
echo "[5/6] Checking Redis performance..."
if docker ps | grep -q agentic-redis; then
  REDIS_INFO=$(docker exec agentic-redis redis-cli INFO stats)

  TOTAL_COMMANDS=$(echo "$REDIS_INFO" | grep 'total_commands_processed' | cut -d: -f2 | tr -d '\r')
  KEYSPACE_HITS=$(echo "$REDIS_INFO" | grep 'keyspace_hits' | cut -d: -f2 | tr -d '\r')
  KEYSPACE_MISSES=$(echo "$REDIS_INFO" | grep 'keyspace_misses' | cut -d: -f2 | tr -d '\r')

  if [ -n "$KEYSPACE_HITS" ] && [ -n "$KEYSPACE_MISSES" ] && [ "$((KEYSPACE_HITS + KEYSPACE_MISSES))" -gt 0 ]; then
    HIT_RATE=$((100 * KEYSPACE_HITS / (KEYSPACE_HITS + KEYSPACE_MISSES)))
    echo "  ✓ Redis hit rate: ${HIT_RATE}%"

    if [ "$HIT_RATE" -lt 80 ]; then
      echo "  ⚠️  Low cache hit rate (target: >80%)"
    fi
  else
    echo "  ✓ Redis operational (no cache stats yet)"
  fi

  # Set Redis max memory
  docker exec agentic-redis redis-cli CONFIG SET maxmemory 512mb
  docker exec agentic-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
  echo "  ✓ Redis memory limit set to 512MB with LRU eviction"
else
  echo "  ⚠️  Redis not running"
fi

# 6. Check container resource usage
echo ""
echo "[6/6] Analyzing container resource usage..."
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | \
  grep agentic | head -n 15

echo ""
echo "==========================================="
echo "✓ Performance optimization complete"
echo "==========================================="
echo ""
echo "Next steps:"
echo "  1. Monitor Grafana dashboards for performance metrics"
echo "  2. Run load tests: k6 run load-test.js"
echo "  3. Review slow query logs in PostgreSQL"
echo "  4. Adjust container resource limits based on actual usage"
echo "  5. Consider restarting PostgreSQL to apply all configuration changes:"
echo "     docker-compose -f docker-compose.app.yml restart postgres"
echo ""
