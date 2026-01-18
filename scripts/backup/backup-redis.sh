#!/bin/bash
# Redis Backup Script
BACKUP_DIR="${BACKUP_DIR:-./backups/redis}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "Starting Redis backup..."
redis-cli BGSAVE
sleep 2

# Copy the dump file
if docker cp agentic-redis:/data/dump.rdb "$BACKUP_DIR/dump_$TIMESTAMP.rdb" 2>/dev/null; then
    echo "✓ Backup complete: $BACKUP_DIR/dump_$TIMESTAMP.rdb"
elif [ -f /var/lib/redis/dump.rdb ]; then
    cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$TIMESTAMP.rdb"
    echo "✓ Backup complete: $BACKUP_DIR/dump_$TIMESTAMP.rdb"
else
    echo "✗ Could not locate Redis dump file"
fi
