#!/bin/bash
# Full Platform Backup
echo "=== Story Portal Platform Backup ==="
echo "Started: $(date)"

./scripts/backup/backup-postgres.sh
./scripts/backup/backup-redis.sh

echo ""
echo "=== Backup Complete ==="
echo "Finished: $(date)"
