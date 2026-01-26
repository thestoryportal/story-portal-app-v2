# Platform Scripts

Utility scripts for Story Portal Platform V2 backup, restore, and maintenance.

## Backup Scripts

### backup.sh

Manual backup script for PostgreSQL and Redis data.

**Usage:**
```bash
./platform/scripts/backup.sh
```

**What it does:**
- Backs up PostgreSQL database (`agentic_platform`) to compressed SQL file
- Backs up Redis data (dump.rdb) to timestamped file
- Creates backup manifest with metadata
- Cleans up backups older than 30 days (configurable)
- Outputs backup files to `/backups/` directory

**Backup files created:**
- `postgres-YYYYMMDD-HHMMSS.sql.gz` - Compressed PostgreSQL dump
- `redis-YYYYMMDD-HHMMSS.rdb` - Redis snapshot
- `backup-YYYYMMDD-HHMMSS.manifest` - Backup metadata

**Example:**
```bash
$ ./platform/scripts/backup.sh

=== Story Portal Platform V2 Backup ===
Timestamp: 20260118-143022
Backup directory: /Volumes/Extreme SSD/projects/story-portal-app/backups

[1/3] Backing up PostgreSQL database...
✓ PostgreSQL backup completed: postgres-20260118-143022.sql.gz (45M)

[2/3] Backing up Redis data...
✓ Redis backup completed: redis-20260118-143022.rdb (2.1M)

[3/3] Creating backup manifest...
✓ Backup manifest created: backup-20260118-143022.manifest

=== Backup Complete ===
```

---

### restore.sh

Restore script for PostgreSQL and Redis from backup files.

**Usage:**
```bash
# List available backups
./platform/scripts/restore.sh

# Restore specific backup
./platform/scripts/restore.sh TIMESTAMP
```

**What it does:**
- Lists all available backups when run without arguments
- Restores PostgreSQL database from compressed SQL backup
- Restores Redis data from snapshot file
- Validates restore operation
- Requires confirmation before proceeding (destructive operation)

**⚠️ WARNING:** This will **DROP** the existing database and replace it with backup data.

**Example:**
```bash
# List backups
$ ./platform/scripts/restore.sh

=== Available Backups ===

Timestamp: 20260118-143022
  PostgreSQL: postgres-20260118-143022.sql.gz (45M)
  Redis: redis-20260118-143022.rdb (2.1M)
  Date: Sat Jan 18 14:30:22 PST 2026

To restore a backup, run: ./platform/scripts/restore.sh <TIMESTAMP>

# Restore specific backup
$ ./platform/scripts/restore.sh 20260118-143022

⚠ WARNING: This will REPLACE the current database!

Restore details:
  Timestamp: 20260118-143022
  PostgreSQL: /backups/postgres-20260118-143022.sql.gz
  Redis: /backups/redis-20260118-143022.rdb

Are you sure you want to continue? (yes/no): yes

=== Starting Restore Process ===

[1/2] Restoring PostgreSQL database...
✓ PostgreSQL restore completed

[2/2] Restoring Redis data...
✓ Redis restore completed

=== Restore Complete ===
```

---

### backup-cron.sh

Automated backup script designed for cron execution.

**Usage:**
```bash
# Run manually
./platform/scripts/backup-cron.sh

# Add to crontab for daily backups at 2 AM
0 2 * * * /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup-cron.sh
```

**What it does:**
- Wraps `backup.sh` with logging for unattended execution
- Writes logs to `/logs/backup-cron.log`
- Rotates logs when they exceed 10MB
- Handles errors and provides exit codes
- Suitable for cron scheduling

**Log file location:**
```
/Volumes/Extreme SSD/projects/story-portal-app/logs/backup-cron.log
```

**Example crontab entry:**
```bash
# Daily backup at 2:00 AM
0 2 * * * /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup-cron.sh

# Weekly backup on Sunday at 3:00 AM
0 3 * * 0 /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup-cron.sh

# Hourly backup during business hours (9 AM - 5 PM)
0 9-17 * * * /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup-cron.sh
```

**Setting up cron:**
```bash
# Edit crontab
crontab -e

# Add the following line for daily backups at 2 AM:
0 2 * * * /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup-cron.sh

# Save and exit
# Verify crontab
crontab -l
```

---

## Other Scripts

### start-dev.sh

Starts the development environment (already existing).

### stop-dev.sh

Stops the development environment (already existing).

---

## Configuration

All scripts use the following default configuration:

**Paths:**
- Backup directory: `/Volumes/Extreme SSD/projects/story-portal-app/backups`
- Log directory: `/Volumes/Extreme SSD/projects/story-portal-app/logs`

**Containers:**
- PostgreSQL: `agentic-postgres`
- Redis: `agentic-redis`

**Database:**
- PostgreSQL user: `postgres`
- PostgreSQL database: `agentic_platform`

**Retention:**
- Backup retention: 30 days (configurable in `backup.sh`)

To modify these settings, edit the configuration section at the top of each script.

---

## Troubleshooting

### Backup fails with "container not running"

**Solution:** Ensure containers are running:
```bash
docker ps | grep agentic
```

Start containers if needed:
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app
docker-compose -f platform/docker-compose.app.yml up -d
```

### Restore fails with "permission denied"

**Solution:** Ensure scripts are executable:
```bash
chmod +x platform/scripts/*.sh
```

### Backups consuming too much disk space

**Solution:** Adjust retention period in `backup.sh`:
```bash
RETENTION_DAYS=7  # Keep only 7 days instead of 30
```

Or manually clean old backups:
```bash
find backups/ -name "*.sql.gz" -mtime +7 -delete
find backups/ -name "*.rdb" -mtime +7 -delete
```

### Cron job not running

**Solution:** Check cron logs:
```bash
# macOS
log show --predicate 'process == "cron"' --last 1h

# Linux
grep CRON /var/log/syslog
```

Verify crontab entry:
```bash
crontab -l
```

Ensure script has absolute path in crontab (not relative).

---

## Security Considerations

- Backup files contain sensitive data - restrict access:
  ```bash
  chmod 700 backups/
  chmod 600 backups/*
  ```

- Consider encrypting backups for long-term storage:
  ```bash
  gpg --encrypt --recipient backup@your-org.com postgres-*.sql.gz
  ```

- Store backups on separate physical media or remote location for disaster recovery

- Rotate backup encryption keys regularly

- Test restore procedures regularly to ensure backups are valid

---

## Best Practices

1. **Test restores regularly** - Verify backups are valid by testing restore in development environment

2. **Monitor backup logs** - Check `/logs/backup-cron.log` for errors

3. **Offsite backups** - Copy backups to remote storage (S3, NAS, etc.)

4. **Document recovery procedures** - Maintain runbook for disaster recovery

5. **Backup before upgrades** - Always backup before major platform changes

6. **Verify disk space** - Ensure sufficient space for backups (estimate 2-3x database size)

---

## See Also

- [SECURITY.md](../../SECURITY.md) - Security best practices
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) - Platform architecture
- [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md) - Development guide
