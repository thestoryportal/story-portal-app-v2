#!/bin/bash
# PostgreSQL Backup Script
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "Starting PostgreSQL backup..."
docker exec agentic-postgres pg_dump -U postgres -d agentic -F c -f /tmp/agentic_$TIMESTAMP.dump
docker cp agentic-postgres:/tmp/agentic_$TIMESTAMP.dump "$BACKUP_DIR/"

if [ $? -eq 0 ]; then
    echo "✓ Backup complete: $BACKUP_DIR/agentic_$TIMESTAMP.dump"
    # Keep only last 7 backups
    ls -t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n +8 | xargs -r rm
else
    echo "✗ Backup failed"
    exit 1
fi
