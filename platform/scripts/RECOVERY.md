# PostgreSQL Disaster Recovery Procedures

**Last Updated:** 2026-01-18
**PostgreSQL Version:** 16 (pgvector/pgvector:pg16)
**WAL Archiving:** ✅ ENABLED

## Overview

This document describes the disaster recovery procedures for the Story Portal Platform PostgreSQL database. WAL (Write-Ahead Logging) archiving is enabled to support Point-in-Time Recovery (PITR).

## WAL Archiving Configuration

### Current Configuration

```sql
archive_mode = on
wal_level = replica
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
```

### Archive Location

- **Container Path:** `/var/lib/postgresql/wal_archive/`
- **Archive Status:** Active (checked via `pg_stat_archiver`)
- **Archive Frequency:** Continuous (every 16MB or checkpoint)

### Verification

```bash
# Check archiver status
docker exec agentic-postgres psql -U postgres -c \
  "SELECT archived_count, failed_count, last_archived_wal, last_archived_time FROM pg_stat_archiver;"

# View archived WAL files
docker exec agentic-postgres ls -lh /var/lib/postgresql/wal_archive/

# Force WAL switch (for testing)
docker exec agentic-postgres psql -U postgres -c "SELECT pg_switch_wal();"
```

## Backup Types

### 1. Logical Backup (pg_dump)

**Best For:** Small to medium databases, schema exports, selective restoration

```bash
# Full database backup
docker exec agentic-postgres pg_dump -U postgres -Fc agentic_platform > backup_$(date +%Y%m%d_%H%M%S).dump

# Schema only
docker exec agentic-postgres pg_dump -U postgres -s agentic_platform > schema_$(date +%Y%m%d_%H%M%S).sql

# Specific tables
docker exec agentic-postgres pg_dump -U postgres -t agents -t goals agentic_platform > tables_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Physical Backup (pg_basebackup)

**Best For:** Large databases, fast restoration, Point-in-Time Recovery

```bash
# Create base backup
docker exec agentic-postgres pg_basebackup -U postgres -D /tmp/backup_base -Ft -z -P

# Copy backup from container
docker cp agentic-postgres:/tmp/backup_base ./backups/base_$(date +%Y%m%d_%H%M%S)/
```

### 3. Continuous Archiving (WAL Files)

**Best For:** Point-in-Time Recovery, minimal data loss

WAL files are automatically archived to `/var/lib/postgresql/wal_archive/` as configured.

## Recovery Scenarios

### Scenario 1: Restore from Logical Backup (pg_dump)

**Recovery Time:** Minutes to hours (depends on database size)
**Data Loss:** Since last backup

```bash
# 1. Stop all services that connect to database
docker stop l01-data-layer l02-runtime l03-tool-execution l04-model-gateway \
  l05-planning l06-evaluation l07-learning l09-api-gateway \
  l10-human-interface l11-integration l12-service-hub

# 2. Drop and recreate database
docker exec agentic-postgres psql -U postgres -c "DROP DATABASE IF EXISTS agentic_platform;"
docker exec agentic-postgres psql -U postgres -c "CREATE DATABASE agentic_platform;"

# 3. Restore backup
docker exec -i agentic-postgres pg_restore -U postgres -d agentic_platform -v < backup_20260118_120000.dump

# 4. Verify restoration
docker exec agentic-postgres psql -U postgres -d agentic_platform -c "\dt"
docker exec agentic-postgres psql -U postgres -d agentic_platform -c "SELECT COUNT(*) FROM agents;"

# 5. Restart services
docker start l01-data-layer l02-runtime l03-tool-execution l04-model-gateway \
  l05-planning l06-evaluation l07-learning l09-api-gateway \
  l10-human-interface l11-integration l12-service-hub
```

### Scenario 2: Restore from Physical Backup (pg_basebackup)

**Recovery Time:** Minutes (fast restore)
**Data Loss:** Since last base backup + WAL files

```bash
# 1. Stop PostgreSQL container
docker stop agentic-postgres

# 2. Remove old data directory
docker exec agentic-postgres rm -rf /var/lib/postgresql/data/*

# 3. Copy base backup to data directory
docker cp ./backups/base_20260118_120000/base.tar.gz agentic-postgres:/tmp/
docker exec agentic-postgres tar -xzf /tmp/base.tar.gz -C /var/lib/postgresql/data/

# 4. Create recovery signal file
docker exec agentic-postgres touch /var/lib/postgresql/data/recovery.signal

# 5. Configure recovery
docker exec agentic-postgres bash -c "cat > /var/lib/postgresql/data/recovery.conf <<EOF
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-01-18 12:00:00'
recovery_target_action = 'promote'
EOF"

# 6. Start PostgreSQL
docker start agentic-postgres

# 7. Monitor recovery
docker logs -f agentic-postgres

# 8. Verify database
docker exec agentic-postgres psql -U postgres -c "\l"
```

### Scenario 3: Point-in-Time Recovery (PITR)

**Recovery Time:** Minutes to hours
**Data Loss:** Minimal (up to specific timestamp)

```bash
# 1. Stop PostgreSQL
docker stop agentic-postgres

# 2. Restore base backup (see Scenario 2 steps 2-3)

# 3. Configure PITR recovery
docker exec agentic-postgres bash -c "cat > /var/lib/postgresql/data/postgresql.auto.conf <<EOF
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-01-18 11:45:00'  # Set to desired recovery point
recovery_target_action = 'promote'
EOF"

# 4. Create recovery signal
docker exec agentic-postgres touch /var/lib/postgresql/data/recovery.signal

# 5. Start PostgreSQL
docker start agentic-postgres

# 6. Monitor recovery logs
docker logs -f agentic-postgres | grep -i recovery

# 7. Once recovered, verify data
docker exec agentic-postgres psql -U postgres -c "SELECT now();"
docker exec agentic-postgres psql -U postgres -d agentic_platform -c "SELECT COUNT(*) FROM agents;"
```

### Scenario 4: Complete System Rebuild

**Recovery Time:** 30-60 minutes
**Data Loss:** Depends on backup age + WAL files

```bash
# 1. Backup current WAL archive (if accessible)
docker cp agentic-postgres:/var/lib/postgresql/wal_archive ./backups/wal_archive_$(date +%Y%m%d)

# 2. Remove old container and volume
docker stop agentic-postgres
docker rm agentic-postgres
docker volume rm story-portal-app_postgres_data

# 3. Recreate PostgreSQL service
cd /Volumes/Extreme\ SSD/projects/story-portal-app
docker-compose -f platform/docker-compose.app.yml up -d postgres

# 4. Wait for PostgreSQL to initialize
sleep 30

# 5. Restore base backup + WAL files (see Scenario 2)

# 6. Restore WAL archive
docker cp ./backups/wal_archive_20260118 agentic-postgres:/var/lib/postgresql/wal_archive

# 7. Perform PITR recovery (see Scenario 3)

# 8. Restart all dependent services
docker-compose -f platform/docker-compose.app.yml restart
```

## Recovery Verification Checklist

After any recovery operation, verify:

### Database Integrity

```sql
-- Check database exists and is accessible
\l

-- Verify tables exist
\dt

-- Check table row counts
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  (SELECT COUNT(*) FROM pg_class WHERE relname = tablename) as tables
FROM pg_tables
WHERE schemaname = 'public';

-- Verify data consistency
SELECT COUNT(*) FROM agents;
SELECT COUNT(*) FROM goals;
SELECT COUNT(*) FROM tasks;

-- Check for any corruption
SELECT datname, pg_database_size(datname) as size FROM pg_database;
```

### Application Connectivity

```bash
# Test L01 connection
docker exec l01-data-layer python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:postgres@postgres:5432/agentic_platform')
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('L01 connection:', result.scalar())
"

# Check service health
curl http://localhost:8001/health
curl http://localhost:8009/health
curl http://localhost:8010/health
```

### WAL Archiving

```sql
-- Verify archiving is active
SELECT * FROM pg_stat_archiver;

-- Check archive status
SHOW archive_mode;
SHOW archive_command;

-- Test WAL switch
SELECT pg_switch_wal();
```

## Backup Automation

### Using platform/scripts/backup.sh

The automated backup script is available at `platform/scripts/backup.sh`:

```bash
# Run manual backup
cd /Volumes/Extreme\ SSD/projects/story-portal-app
./platform/scripts/backup.sh

# Backups are stored in /tmp/story-portal-backups/
```

### Scheduled Backups (Recommended)

```bash
# Add to crontab for daily backups at 2 AM
crontab -e

# Add this line:
0 2 * * * /Volumes/Extreme\ SSD/projects/story-portal-app/platform/scripts/backup.sh
```

## Backup Retention Policy

**Recommended Retention:**

- **Daily backups:** 7 days
- **Weekly backups:** 4 weeks
- **Monthly backups:** 12 months
- **WAL archives:** 7 days minimum (or until next base backup)

**Cleanup Script:**

```bash
# Remove backups older than 7 days
find /tmp/story-portal-backups/ -name "*.dump" -mtime +7 -delete
find /tmp/story-portal-backups/ -name "*.sql" -mtime +7 -delete

# Archive monthly backups
find /tmp/story-portal-backups/ -name "*_01.dump" -exec cp {} /backups/monthly/ \;
```

## Recovery Time Objectives (RTO)

| Scenario | RTO Target | Actual Time | Notes |
|----------|-----------|-------------|-------|
| Logical Backup Restore | 30 minutes | 15-45 min | Depends on database size |
| Physical Backup Restore | 15 minutes | 10-20 min | Faster for large databases |
| Point-in-Time Recovery | 30 minutes | 20-40 min | Includes WAL replay |
| Complete System Rebuild | 60 minutes | 45-90 min | Includes container recreation |

## Recovery Point Objectives (RPO)

| Backup Type | RPO | Data Loss |
|-------------|-----|-----------|
| Daily Logical Backup | 24 hours | Up to 24 hours |
| Physical Backup + WAL | 15 minutes | Minimal (last checkpoint) |
| Continuous WAL Archiving | < 5 minutes | Minimal (unflushed writes) |

## Disaster Recovery Testing

**Test Schedule:**

- **Monthly:** Restore from latest backup to test environment
- **Quarterly:** Full disaster recovery drill (complete rebuild)
- **Annually:** Verify off-site backup integrity

**Test Procedure:**

```bash
# 1. Create test environment
docker-compose -f platform/docker-compose.test.yml up -d postgres-test

# 2. Restore latest backup
./platform/scripts/restore.sh --target postgres-test --backup latest

# 3. Verify data integrity
docker exec postgres-test psql -U postgres -d agentic_platform -c "SELECT COUNT(*) FROM agents;"

# 4. Run application tests
pytest platform/tests/integration/

# 5. Cleanup
docker-compose -f platform/docker-compose.test.yml down -v
```

## Troubleshooting

### Issue: Archive Command Failing

```sql
-- Check archiver status
SELECT * FROM pg_stat_archiver;

-- Common causes:
-- 1. Insufficient disk space
-- 2. Permission issues on archive directory
-- 3. Incorrect archive_command syntax

-- Fix permissions
```

```bash
docker exec agentic-postgres chmod 700 /var/lib/postgresql/wal_archive
docker exec agentic-postgres chown -R postgres:postgres /var/lib/postgresql/wal_archive
```

### Issue: Recovery Stuck

```bash
# Check recovery progress
docker exec agentic-postgres tail -f /var/lib/postgresql/data/log/postgresql.log

# Common causes:
# 1. Missing WAL files
# 2. Incorrect recovery target time
# 3. WAL file corruption

# Skip to latest available WAL
docker exec agentic-postgres psql -U postgres -c "SELECT pg_wal_replay_resume();"
```

### Issue: Slow Recovery

```sql
-- Monitor recovery progress
SELECT pg_last_wal_replay_lsn(), pg_current_wal_lsn();

-- Tune recovery settings
ALTER SYSTEM SET max_wal_size = '10GB';
ALTER SYSTEM SET checkpoint_timeout = '30min';
SELECT pg_reload_conf();
```

## Emergency Contacts

- **Database Administrator:** [Contact Info]
- **Platform Team:** [Contact Info]
- **On-Call Engineer:** [Contact Info]

## Related Documentation

- Backup script: `platform/scripts/backup.sh`
- Restore script: `platform/scripts/restore.sh`
- PostgreSQL configuration: `platform/docker-compose.app.yml`
- Monitoring: Grafana dashboard at http://localhost:3001

## References

- [PostgreSQL Backup and Restore](https://www.postgresql.org/docs/16/backup.html)
- [WAL Archiving](https://www.postgresql.org/docs/16/continuous-archiving.html)
- [Point-in-Time Recovery](https://www.postgresql.org/docs/16/continuous-archiving.html#BACKUP-PITR-RECOVERY)
- [pg_basebackup](https://www.postgresql.org/docs/16/app-pgbasebackup.html)
