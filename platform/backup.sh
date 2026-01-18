#!/bin/bash
set -e

# Story Portal Platform V2 - Backup Script
# Backs up PostgreSQL database and Redis data

# Configuration
BACKUP_ROOT="${BACKUP_ROOT:-/tmp/story-portal-backups}"
BACKUP_DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_DATE"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

echo "==========================================="
echo "Story Portal V2 - Backup Script"
echo "==========================================="
echo "Backup directory: $BACKUP_DIR"
echo "Retention: $RETENTION_DAYS days"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
echo "[1/3] Backing up PostgreSQL..."
docker exec agentic-postgres pg_dump -U postgres agentic_platform | \
  gzip > "$BACKUP_DIR/postgres.sql.gz"
echo "  ✓ PostgreSQL backup: $(du -h "$BACKUP_DIR/postgres.sql.gz" | cut -f1)"

# Backup Redis
echo "[2/3] Backing up Redis..."
docker exec agentic-redis redis-cli BGSAVE > /dev/null
sleep 2  # Wait for background save
docker cp agentic-redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb" 2>/dev/null || true
if [ -f "$BACKUP_DIR/redis.rdb" ]; then
  echo "  ✓ Redis backup: $(du -h "$BACKUP_DIR/redis.rdb" | cut -f1)"
else
  echo "  ⚠ Redis backup skipped (no data to backup)"
fi

# Backup Prometheus metrics
echo "[3/3] Backing up Prometheus metrics..."
if docker ps | grep -q agentic-prometheus; then
  docker exec agentic-prometheus tar czf /tmp/prometheus-data.tar.gz -C /prometheus . 2>/dev/null
  docker cp agentic-prometheus:/tmp/prometheus-data.tar.gz "$BACKUP_DIR/prometheus-data.tar.gz" 2>/dev/null
  docker exec agentic-prometheus rm /tmp/prometheus-data.tar.gz
  echo "  ✓ Prometheus backup: $(du -h "$BACKUP_DIR/prometheus-data.tar.gz" | cut -f1)"
else
  echo "  ⚠ Prometheus not running, skipped"
fi

# Create backup metadata
cat > "$BACKUP_DIR/metadata.txt" <<EOF
Backup Date: $BACKUP_DATE
Platform: Story Portal V2
Components:
  - PostgreSQL (agentic_platform database)
  - Redis (session/cache data)
  - Prometheus (metrics data)

Container Status:
$(docker ps --format "  {{.Names}}: {{.Status}}" | grep agentic)

Backup Size:
$(du -sh "$BACKUP_DIR" | cut -f1)
EOF

echo ""
echo "Backup complete: $BACKUP_DIR"
cat "$BACKUP_DIR/metadata.txt"

# Cleanup old backups
echo ""
echo "Cleaning up backups older than $RETENTION_DAYS days..."
if [ -d "$BACKUP_ROOT" ]; then
  OLD_BACKUPS=$(find "$BACKUP_ROOT" -type d -mindepth 1 -maxdepth 1 -mtime +$RETENTION_DAYS 2>/dev/null || true)
  if [ -n "$OLD_BACKUPS" ]; then
    echo "$OLD_BACKUPS" | while read -r old_backup; do
      echo "  Removing: $(basename "$old_backup")"
      rm -rf "$old_backup"
    done
    echo "  ✓ Cleanup complete"
  else
    echo "  No old backups to remove"
  fi
fi

echo ""
echo "==========================================="
echo "✓ Backup completed successfully"
echo "==========================================="
