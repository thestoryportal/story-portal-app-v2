#!/bin/bash
set -e

# Story Portal Platform V2 - Restore Script
# Restores PostgreSQL database and Redis data from backup

# Configuration
BACKUP_ROOT="${BACKUP_ROOT:-/tmp/story-portal-backups}"

echo "==========================================="
echo "Story Portal V2 - Restore Script"
echo "==========================================="
echo ""

# Check if backup date provided
if [ -z "$1" ]; then
  echo "Usage: $0 <backup-date>"
  echo ""
  echo "Available backups:"
  if [ -d "$BACKUP_ROOT" ]; then
    ls -1t "$BACKUP_ROOT" | head -n 10
  else
    echo "  No backups found in $BACKUP_ROOT"
  fi
  exit 1
fi

BACKUP_DATE="$1"
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_DATE"

# Verify backup exists
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Error: Backup not found: $BACKUP_DIR"
  exit 1
fi

echo "Backup directory: $BACKUP_DIR"
echo ""

# Show backup metadata
if [ -f "$BACKUP_DIR/metadata.txt" ]; then
  echo "Backup metadata:"
  cat "$BACKUP_DIR/metadata.txt"
  echo ""
fi

# Confirmation prompt
read -p "⚠️  WARNING: This will overwrite current data. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Stop all services except infrastructure
echo ""
echo "[1/5] Stopping application services..."
cd "$(dirname "$0")"
docker-compose -f docker-compose.app.yml stop \
  l01-data-layer l02-runtime l03-tool-execution l04-model-gateway \
  l05-planning l06-evaluation l07-learning l09-api-gateway \
  l10-human-interface l11-integration l12-service-hub platform-ui 2>/dev/null || true
echo "  ✓ Application services stopped"

# Restore PostgreSQL
echo ""
echo "[2/5] Restoring PostgreSQL..."
if [ -f "$BACKUP_DIR/postgres.sql.gz" ]; then
  # Drop and recreate database
  docker exec agentic-postgres psql -U postgres -c "DROP DATABASE IF EXISTS agentic_platform;" 2>/dev/null || true
  docker exec agentic-postgres psql -U postgres -c "CREATE DATABASE agentic_platform;"

  # Restore from backup
  gunzip < "$BACKUP_DIR/postgres.sql.gz" | \
    docker exec -i agentic-postgres psql -U postgres agentic_platform

  echo "  ✓ PostgreSQL restored"
else
  echo "  ⚠ PostgreSQL backup not found, skipped"
fi

# Restore Redis
echo ""
echo "[3/5] Restoring Redis..."
if [ -f "$BACKUP_DIR/redis.rdb" ]; then
  # Stop Redis, copy backup, restart
  docker-compose -f docker-compose.app.yml stop redis
  docker cp "$BACKUP_DIR/redis.rdb" agentic-redis:/data/dump.rdb
  docker-compose -f docker-compose.app.yml start redis
  sleep 2
  echo "  ✓ Redis restored"
else
  echo "  ⚠ Redis backup not found, skipped"
fi

# Restore Prometheus
echo ""
echo "[4/5] Restoring Prometheus metrics..."
if [ -f "$BACKUP_DIR/prometheus-data.tar.gz" ] && docker ps | grep -q agentic-prometheus; then
  docker-compose -f docker-compose.app.yml stop prometheus
  docker cp "$BACKUP_DIR/prometheus-data.tar.gz" agentic-prometheus:/tmp/
  docker exec agentic-prometheus sh -c "cd /prometheus && tar xzf /tmp/prometheus-data.tar.gz && rm /tmp/prometheus-data.tar.gz"
  docker-compose -f docker-compose.app.yml start prometheus
  echo "  ✓ Prometheus metrics restored"
else
  echo "  ⚠ Prometheus backup not found or service not running, skipped"
fi

# Restart all services
echo ""
echo "[5/5] Restarting application services..."
docker-compose -f docker-compose.app.yml up -d
echo "  ✓ All services restarted"

# Wait for services to be healthy
echo ""
echo "Waiting for services to be healthy (30s)..."
sleep 30

# Verify restoration
echo ""
echo "Verifying restoration..."

# Check PostgreSQL
if docker exec agentic-postgres psql -U postgres agentic_platform -c "SELECT COUNT(*) FROM mcp_documents.events;" > /dev/null 2>&1; then
  EVENT_COUNT=$(docker exec agentic-postgres psql -U postgres agentic_platform -t -c "SELECT COUNT(*) FROM mcp_documents.events;" | tr -d ' ')
  echo "  ✓ PostgreSQL: $EVENT_COUNT events in database"
else
  echo "  ⚠ PostgreSQL: Unable to verify"
fi

# Check Redis
if docker exec agentic-redis redis-cli PING | grep -q PONG; then
  echo "  ✓ Redis: Service responding"
else
  echo "  ⚠ Redis: Unable to verify"
fi

# Check container health
HEALTHY=$(docker ps --filter "status=running" --filter "health=healthy" | grep -c agentic || true)
TOTAL=$(docker ps --filter "status=running" | grep -c agentic || true)
echo "  ✓ Containers: $HEALTHY/$TOTAL healthy"

echo ""
echo "==========================================="
echo "✓ Restore completed"
echo "==========================================="
echo ""
echo "Next steps:"
echo "  1. Verify application functionality"
echo "  2. Check logs: docker-compose -f docker-compose.app.yml logs -f"
echo "  3. Run integration tests: ./integration-test.sh"
