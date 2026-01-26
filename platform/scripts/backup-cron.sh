#!/bin/bash

# Story Portal Platform V2 - Automated Backup (Cron)
# This script is designed to run via cron for automated daily backups
# It adds logging and error handling for unattended execution

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"
LOG_DIR="/Volumes/Extreme SSD/projects/story-portal-app/logs"
LOG_FILE="$LOG_DIR/backup-cron.log"
MAX_LOG_SIZE=10485760  # 10MB

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Rotate log if too large
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]; then
    mv "$LOG_FILE" "$LOG_FILE.old"
fi

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handler
error_handler() {
    log "ERROR: Backup failed at line $1"
    log "Exit code: $2"
    exit 1
}

trap 'error_handler ${LINENO} $?' ERR

# Start backup
log "=========================================="
log "Starting automated backup"
log "=========================================="

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    log "ERROR: Backup script not found: $BACKUP_SCRIPT"
    exit 1
fi

# Make backup script executable
chmod +x "$BACKUP_SCRIPT"

# Run backup and capture output
log "Executing backup script: $BACKUP_SCRIPT"

if OUTPUT=$("$BACKUP_SCRIPT" 2>&1); then
    log "Backup completed successfully"
    log "Output:"
    echo "$OUTPUT" | while IFS= read -r line; do
        log "  $line"
    done
else
    log "ERROR: Backup script failed"
    log "Output:"
    echo "$OUTPUT" | while IFS= read -r line; do
        log "  $line"
    done
    exit 1
fi

log "=========================================="
log "Automated backup finished"
log "=========================================="

# Optional: Send notification (uncomment and configure)
# if command -v mail > /dev/null 2>&1; then
#     echo "Backup completed successfully at $(date)" | \
#         mail -s "Story Portal Backup - Success" admin@your-domain.com
# fi

exit 0
