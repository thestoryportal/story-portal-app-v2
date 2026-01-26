#!/bin/bash

# Story Portal Platform V2 - Restore Script
# Restores PostgreSQL database and Redis data from backup

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Volumes/Extreme SSD/projects/story-portal-app/backups"
POSTGRES_CONTAINER="agentic-postgres"
REDIS_CONTAINER="agentic-redis"
POSTGRES_USER="postgres"
POSTGRES_DB="agentic_platform"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage function
usage() {
    echo "Usage: $0 [TIMESTAMP]"
    echo ""
    echo "Restores PostgreSQL and Redis from backup files"
    echo ""
    echo "Arguments:"
    echo "  TIMESTAMP    Backup timestamp (e.g., 20260118-143022)"
    echo "               If omitted, lists available backups"
    echo ""
    echo "Examples:"
    echo "  $0                    # List available backups"
    echo "  $0 20260118-143022    # Restore specific backup"
    echo ""
    exit 1
}

# List available backups
list_backups() {
    echo -e "${BLUE}=== Available Backups ===${NC}"
    echo ""

    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/postgres-*.sql.gz 2>/dev/null)" ]; then
        echo -e "${YELLOW}No backups found in $BACKUP_DIR${NC}"
        exit 0
    fi

    for backup in "$BACKUP_DIR"/postgres-*.sql.gz; do
        TIMESTAMP=$(basename "$backup" .sql.gz | sed 's/postgres-//')
        MANIFEST="$BACKUP_DIR/backup-$TIMESTAMP.manifest"

        echo -e "${GREEN}Timestamp: $TIMESTAMP${NC}"

        if [ -f "$MANIFEST" ]; then
            echo "  PostgreSQL: $(basename "$backup") ($(du -h "$backup" | cut -f1))"
            [ -f "$BACKUP_DIR/redis-$TIMESTAMP.rdb" ] && \
                echo "  Redis: redis-$TIMESTAMP.rdb ($(du -h "$BACKUP_DIR/redis-$TIMESTAMP.rdb" | cut -f1))"
            echo "  Date: $(grep "^Date:" "$MANIFEST" | cut -d: -f2-)"
        else
            echo "  PostgreSQL: $(basename "$backup") ($(du -h "$backup" | cut -f1))"
        fi
        echo ""
    done

    echo "To restore a backup, run: $0 <TIMESTAMP>"
}

# Check arguments
if [ $# -eq 0 ]; then
    list_backups
    exit 0
fi

TIMESTAMP=$1

# Validate timestamp format
if ! [[ "$TIMESTAMP" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
    echo -e "${RED}ERROR: Invalid timestamp format. Expected: YYYYMMDD-HHMMSS${NC}"
    echo ""
    usage
fi

# Check if backup files exist
POSTGRES_BACKUP="$BACKUP_DIR/postgres-$TIMESTAMP.sql.gz"
REDIS_BACKUP="$BACKUP_DIR/redis-$TIMESTAMP.rdb"
MANIFEST="$BACKUP_DIR/backup-$TIMESTAMP.manifest"

if [ ! -f "$POSTGRES_BACKUP" ]; then
    echo -e "${RED}ERROR: PostgreSQL backup not found: $POSTGRES_BACKUP${NC}"
    echo ""
    list_backups
    exit 1
fi

# Confirmation prompt
echo -e "${RED}⚠ WARNING: This will REPLACE the current database!${NC}"
echo ""
echo "Restore details:"
echo "  Timestamp: $TIMESTAMP"
echo "  PostgreSQL: $POSTGRES_BACKUP"
[ -f "$REDIS_BACKUP" ] && echo "  Redis: $REDIS_BACKUP"
echo ""
echo "Current database will be DROPPED and replaced with backup data."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo -e "${GREEN}=== Starting Restore Process ===${NC}"
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

# Restore PostgreSQL
echo -e "${YELLOW}[1/2] Restoring PostgreSQL database...${NC}"
echo "  - Terminating active connections..."
docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$POSTGRES_DB' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

echo "  - Dropping existing database..."
docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" > /dev/null

echo "  - Creating fresh database..."
docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;" > /dev/null

echo "  - Restoring data from backup..."
gunzip -c "$POSTGRES_BACKUP" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null

echo -e "${GREEN}✓ PostgreSQL restore completed${NC}"

# Restore Redis
if [ -f "$REDIS_BACKUP" ]; then
    echo -e "${YELLOW}[2/2] Restoring Redis data...${NC}"

    echo "  - Flushing current Redis data..."
    docker exec "$REDIS_CONTAINER" redis-cli FLUSHALL > /dev/null 2>&1 || true

    echo "  - Stopping Redis to replace dump.rdb..."
    docker stop "$REDIS_CONTAINER" > /dev/null

    echo "  - Copying backup file..."
    docker cp "$REDIS_BACKUP" "$REDIS_CONTAINER:/data/dump.rdb"

    echo "  - Starting Redis..."
    docker start "$REDIS_CONTAINER" > /dev/null

    # Wait for Redis to be ready
    sleep 3
    until docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; do
        echo "  - Waiting for Redis to be ready..."
        sleep 1
    done

    echo -e "${GREEN}✓ Redis restore completed${NC}"
else
    echo -e "${YELLOW}[2/2] Redis backup not found, skipping...${NC}"
fi

# Verify restore
echo ""
echo -e "${YELLOW}Verifying restore...${NC}"

# Check PostgreSQL
TABLE_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')
echo "  PostgreSQL tables: $TABLE_COUNT"

# Check Redis
if docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
    KEY_COUNT=$(docker exec "$REDIS_CONTAINER" redis-cli DBSIZE | cut -d: -f2 | tr -d ' ' || echo "0")
    echo "  Redis keys: $KEY_COUNT"
fi

echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
echo ""
echo "The database has been restored from backup: $TIMESTAMP"
echo ""
echo "Next steps:"
echo "  1. Verify application functionality"
echo "  2. Check service health: curl http://localhost:8009/health"
echo "  3. Review application logs for any errors"
