#!/bin/bash

# Story Portal Platform V2 - Backup Script
# Backs up PostgreSQL database and Redis data

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Volumes/Extreme SSD/projects/story-portal-app/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
POSTGRES_CONTAINER="agentic-postgres"
REDIS_CONTAINER="agentic-redis"
POSTGRES_USER="postgres"
POSTGRES_DB="agentic_platform"
RETENTION_DAYS=30

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}=== Story Portal Platform V2 Backup ===${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Backup directory: $BACKUP_DIR"
echo ""

# Check if containers are running
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo -e "${RED}ERROR: PostgreSQL container ($POSTGRES_CONTAINER) is not running${NC}"
    exit 1
fi

if ! docker ps | grep -q "$REDIS_CONTAINER"; then
    echo -e "${RED}ERROR: Redis container ($REDIS_CONTAINER) is not running${NC}"
    exit 1
fi

# Backup PostgreSQL
echo -e "${YELLOW}[1/3] Backing up PostgreSQL database...${NC}"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | \
    gzip > "$BACKUP_DIR/postgres-$TIMESTAMP.sql.gz"

POSTGRES_SIZE=$(du -h "$BACKUP_DIR/postgres-$TIMESTAMP.sql.gz" | cut -f1)
echo -e "${GREEN}✓ PostgreSQL backup completed: postgres-$TIMESTAMP.sql.gz ($POSTGRES_SIZE)${NC}"

# Backup Redis
echo -e "${YELLOW}[2/3] Backing up Redis data...${NC}"
docker exec "$REDIS_CONTAINER" redis-cli BGSAVE > /dev/null 2>&1 || true
sleep 2  # Wait for BGSAVE to complete

docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_DIR/redis-$TIMESTAMP.rdb" 2>/dev/null || \
    echo -e "${YELLOW}⚠ Redis backup skipped (no dump.rdb found - Redis may be empty)${NC}"

if [ -f "$BACKUP_DIR/redis-$TIMESTAMP.rdb" ]; then
    REDIS_SIZE=$(du -h "$BACKUP_DIR/redis-$TIMESTAMP.rdb" | cut -f1)
    echo -e "${GREEN}✓ Redis backup completed: redis-$TIMESTAMP.rdb ($REDIS_SIZE)${NC}"
fi

# Create backup manifest
echo -e "${YELLOW}[3/3] Creating backup manifest...${NC}"
cat > "$BACKUP_DIR/backup-$TIMESTAMP.manifest" <<EOF
Backup Manifest
===============
Timestamp: $TIMESTAMP
Date: $(date)
Platform Version: 2.0.0

PostgreSQL:
  Container: $POSTGRES_CONTAINER
  Database: $POSTGRES_DB
  File: postgres-$TIMESTAMP.sql.gz
  Size: $POSTGRES_SIZE

Redis:
  Container: $REDIS_CONTAINER
  File: redis-$TIMESTAMP.rdb
  Size: ${REDIS_SIZE:-N/A}

Status: Complete
EOF

echo -e "${GREEN}✓ Backup manifest created: backup-$TIMESTAMP.manifest${NC}"

# Clean up old backups (older than RETENTION_DAYS)
echo ""
echo -e "${YELLOW}Cleaning up backups older than $RETENTION_DAYS days...${NC}"
find "$BACKUP_DIR" -name "postgres-*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "redis-*.rdb" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "backup-*.manifest" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Summary
echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo "Backup files:"
echo "  - $BACKUP_DIR/postgres-$TIMESTAMP.sql.gz"
[ -f "$BACKUP_DIR/redis-$TIMESTAMP.rdb" ] && echo "  - $BACKUP_DIR/redis-$TIMESTAMP.rdb"
echo "  - $BACKUP_DIR/backup-$TIMESTAMP.manifest"
echo ""
echo "Total backups in directory: $(ls -1 "$BACKUP_DIR"/postgres-*.sql.gz 2>/dev/null | wc -l)"
echo "Disk usage: $(du -sh "$BACKUP_DIR" | cut -f1)"
