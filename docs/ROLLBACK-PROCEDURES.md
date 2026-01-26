# Rollback Procedures - V2 Platform

**Version:** 2.0
**Last Updated:** 2026-01-18
**Emergency Contact:** oncall@example.com | PagerDuty: +1-xxx-xxx-xxxx

## Overview

This document provides detailed procedures for rolling back the V2 platform to a previous stable state in case of deployment failures, critical bugs, or production incidents.

---

## Table of Contents

1. [When to Rollback](#when-to-rollback)
2. [Rollback Decision Matrix](#rollback-decision-matrix)
3. [Pre-Rollback Checklist](#pre-rollback-checklist)
4. [Rollback Procedures](#rollback-procedures)
   - [Complete Platform Rollback](#complete-platform-rollback)
   - [Partial Service Rollback](#partial-service-rollback)
   - [Database Rollback](#database-rollback)
   - [Configuration Rollback](#configuration-rollback)
   - [UI Rollback](#ui-rollback)
5. [Post-Rollback Procedures](#post-rollback-procedures)
6. [Rollback Testing](#rollback-testing)
7. [Common Scenarios](#common-scenarios)
8. [Troubleshooting](#troubleshooting)

---

## When to Rollback

### Immediate Rollback Required

Execute rollback immediately (< 5 minutes decision time) if:

- **Critical functionality broken**: Core features (login, API, data access) completely non-functional
- **Data integrity issues**: Data loss, corruption, or inconsistency detected
- **Security vulnerability exposed**: Active exploit or breach detected
- **Error rate >5%**: Sustained error rate above acceptable threshold
- **Complete service outage**: Multiple critical services down
- **Performance degradation >10x**: Response times exceed 5 seconds
- **Database replication broken**: Primary-replica synchronization failed

### Rollback Consideration (< 30 minutes)

Evaluate rollback if:

- **Error rate 1-5%**: Elevated but not critical error rate
- **Performance degradation 2-10x**: Noticeably slower but functional
- **Partial functionality broken**: Non-critical features impaired
- **Unexpected behavior**: Issues not blocking but concerning
- **Customer complaints increasing**: User-reported issues escalating

### Monitor and Fix Forward

Continue monitoring (no rollback) if:

- **Error rate <1%**: Within acceptable bounds
- **Minor UI issues**: Visual glitches, non-blocking
- **Performance within SLA**: Response times acceptable
- **Known minor issues**: Documented and acceptable bugs
- **Workarounds available**: Users can complete tasks via alternate path

---

## Rollback Decision Matrix

| Issue Type | Error Rate | Response Time | Action | Timeline |
|-----------|------------|---------------|--------|----------|
| Complete Outage | Any | Any | **ROLLBACK** | Immediate |
| Data Corruption | Any | Any | **ROLLBACK** | Immediate |
| Security Breach | Any | Any | **ROLLBACK** | Immediate |
| Critical Feature Down | >5% | >5s | **ROLLBACK** | <5 min |
| Major Feature Down | >2% | >2s | **EVALUATE** | <15 min |
| Minor Feature Down | <1% | <1s | **MONITOR** | <30 min |
| Performance Degradation | <1% | >2s | **EVALUATE** | <15 min |
| UI Glitch | <0.1% | <500ms | **MONITOR** | Best effort |

---

## Pre-Rollback Checklist

### 1. Verify Rollback Readiness (2 minutes)

- [ ] **Confirm decision authority**
  - Deployment lead approval obtained
  - Stakeholders notified

- [ ] **Check backup availability**
  ```bash
  # List recent backups
  ls -lh ./backups/ | head -10

  # Verify backup integrity
  ./platform/scripts/backup.sh verify <backup-file>
  ```

- [ ] **Identify rollback scope**
  - [ ] Full platform rollback
  - [ ] Partial service rollback
  - [ ] Database only
  - [ ] Configuration only
  - [ ] UI only

- [ ] **Document current state**
  ```bash
  # Capture current state
  docker ps > rollback-pre-state-$(date +%Y%m%d-%H%M%S).txt
  kubectl get pods -n production > k8s-pre-state-$(date +%Y%m%d-%H%M%S).txt

  # Capture error logs
  docker logs agentic-l09-api-gateway --tail=1000 > api-gateway-errors.log
  ```

### 2. Communication (1 minute)

- [ ] **Update status page**
  ```bash
  # Update status page
  echo "Rolling back deployment due to [issue]" | ./scripts/update-status.sh
  ```

- [ ] **Notify teams**
  - [ ] Post in #incident-response Slack channel
  - [ ] Email to engineering@example.com
  - [ ] Update PagerDuty incident

- [ ] **Set maintenance mode** (if applicable)
  ```bash
  # Enable maintenance mode
  curl -X POST https://api.example.com/admin/maintenance/enable \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```

---

## Rollback Procedures

## Complete Platform Rollback

**Duration:** 15-30 minutes
**Downtime:** ~10-15 minutes

### Step 1: Stop Current Services (5 min)

```bash
# Set working directory
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform

# Stop all application services (keep infrastructure running)
docker-compose -f docker-compose.app.yml stop

# Verify services stopped
docker ps --filter "name=agentic-l" --format "table {{.Names}}\t{{.Status}}"
```

**Expected Output:**
```
All agentic-l* containers should show "Exited" status
Infrastructure (postgres, redis, consul, etcd) should remain running
```

### Step 2: Rollback to Previous Version (5 min)

```bash
# Get previous version tag
PREVIOUS_VERSION=$(git describe --tags HEAD~1)
echo "Rolling back to: $PREVIOUS_VERSION"

# Checkout previous version (service files only, keep infrastructure)
git checkout $PREVIOUS_VERSION -- docker-compose.app.yml platform/src

# Pull previous container images
docker-compose -f docker-compose.app.yml pull

# Alternative: Use previously tagged images
# docker pull registry.example.com/agentic-platform:$PREVIOUS_VERSION
```

### Step 3: Verify Configuration (2 min)

```bash
# Check environment variables
if [ ! -f .env.production ]; then
  echo "ERROR: .env.production not found!"
  exit 1
fi

# Verify database connection
docker exec agentic-postgres psql -U postgres -c "SELECT 1;" || {
  echo "ERROR: Database not accessible"
  exit 1
}

# Verify Redis connection
docker exec agentic-redis redis-cli PING || {
  echo "ERROR: Redis not accessible"
  exit 1
}
```

### Step 4: Restart Services (5 min)

```bash
# Start services in dependency order
echo "Starting L01 Data Layer..."
docker-compose -f docker-compose.app.yml up -d l01-data-layer
sleep 10
curl -sf http://localhost:8001/health/live || echo "L01 not ready yet"

echo "Starting L02-L07 Core Layers..."
docker-compose -f docker-compose.app.yml up -d \
  l02-runtime l03-tool-execution l04-model-gateway \
  l05-planning l06-evaluation l07-learning
sleep 10

echo "Starting L09 API Gateway..."
docker-compose -f docker-compose.app.yml up -d l09-api-gateway
sleep 10
curl -sf http://localhost:8009/health/live || echo "L09 not ready yet"

echo "Starting L10 Human Interface..."
docker-compose -f docker-compose.app.yml up -d l10-human-interface
sleep 10

echo "Starting L11 + L12..."
docker-compose -f docker-compose.app.yml up -d l11-integration l12-nl-interface
sleep 10

echo "All services started. Waiting for health checks..."
sleep 30
```

### Step 5: Verify Rollback (5 min)

```bash
# Run smoke tests
pytest -m smoke --env=production -v

# Check all service health
for port in 8001 8009 8010 8011 8012; do
  echo "Checking port $port..."
  curl -sf http://localhost:$port/health/live && echo "✅ Healthy" || echo "❌ Failed"
done

# Verify database
docker exec agentic-postgres psql -U postgres -d agentic_platform -c \
  "SELECT COUNT(*) FROM agents;"

# Check error rates
docker logs agentic-l09-api-gateway --tail=100 | grep -i error | wc -l
```

### Step 6: Disable Maintenance Mode (1 min)

```bash
# Disable maintenance mode
curl -X POST https://api.example.com/admin/maintenance/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Update status page
echo "Rollback complete. Platform operational." | ./scripts/update-status.sh
```

---

## Partial Service Rollback

**Duration:** 5-10 minutes
**Downtime:** ~2-3 minutes for affected service only

Use when only specific services are problematic.

### Identify Problematic Service

```bash
# Check recent logs for errors
for service in l01 l02 l03 l04 l05 l06 l07 l09 l10 l11 l12; do
  echo "=== $service ==="
  docker logs agentic-$service-* --tail=50 | grep -i error | head -5
done
```

### Rollback Single Service

```bash
# Example: Rollback L09 API Gateway only
SERVICE=l09-api-gateway

# Stop service
docker-compose -f docker-compose.app.yml stop $SERVICE

# Get previous service image
PREVIOUS_VERSION=$(git describe --tags HEAD~1)
docker pull registry.example.com/$SERVICE:$PREVIOUS_VERSION

# Update docker-compose to use previous version
docker-compose -f docker-compose.app.yml up -d $SERVICE

# Wait for health check
sleep 10
curl -sf http://localhost:8009/health/live

# Verify
docker logs agentic-$SERVICE --tail=50
```

---

## Database Rollback

**Duration:** 15-45 minutes (depends on database size)
**Downtime:** ~15-45 minutes (full platform stop required)

### ⚠️ CRITICAL WARNING
Database rollback causes **data loss**. All data changes since the backup will be lost.

### When to Rollback Database

Only rollback database if:
- Data corruption detected
- Schema migration failed
- Data integrity constraints violated
- No other recovery option available

### Pre-Database-Rollback Steps

```bash
# 1. Create emergency backup of current state
./platform/scripts/backup.sh emergency

# 2. Document data loss window
BACKUP_TIME=$(ls -t backups/ | head -1 | grep -oE '[0-9]{8}-[0-9]{6}')
echo "⚠️  All data after $BACKUP_TIME will be lost!"

# 3. Get stakeholder approval
read -p "Type 'CONFIRM DATA LOSS' to proceed: " confirmation
if [ "$confirmation" != "CONFIRM DATA LOSS" ]; then
  echo "Database rollback cancelled"
  exit 1
fi
```

### Database Rollback Procedure

```bash
# 1. Stop ALL application services
docker-compose -f docker-compose.app.yml down

# 2. Stop database connections
docker exec agentic-postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='agentic_platform';"

# 3. Restore from backup
BACKUP_FILE=$(ls -t backups/ | grep -E "backup-.*\.sql\.gz" | head -1)
echo "Restoring from: $BACKUP_FILE"

./platform/scripts/restore.sh backups/$BACKUP_FILE

# 4. Verify restore
docker exec agentic-postgres psql -U postgres -d agentic_platform -c \
  "SELECT COUNT(*) FROM agents;"

docker exec agentic-postgres psql -U postgres -d agentic_platform -c \
  "SELECT COUNT(*) FROM tasks;"

# 5. Run schema migrations (if needed)
alembic current
alembic stamp head  # Mark as up-to-date

# 6. Restart application services
docker-compose -f docker-compose.app.yml up -d

# 7. Wait and verify
sleep 60
pytest -m smoke --env=production
```

### Post-Database-Rollback

```bash
# Document data loss
cat > rollback-report-$(date +%Y%m%d-%H%M%S).txt << EOF
Database Rollback Report
========================
Rollback Date: $(date)
Backup Used: $BACKUP_FILE
Data Loss Window: From $BACKUP_TIME to $(date +%Y%m%d-%H%M%S)

Affected Data:
- Agents created/updated during loss window
- Tasks created/updated during loss window
- User sessions during loss window

Recovery Actions:
- [ ] Notify affected users
- [ ] Review lost transactions
- [ ] Identify if manual data recovery needed
EOF

cat rollback-report-*.txt
```

---

## Configuration Rollback

**Duration:** 2-5 minutes
**Downtime:** None (hot reload)

### Rollback etcd Configuration

```bash
# 1. Get current configuration snapshot
curl -s http://localhost:2379/v3/kv/range \
  -X POST \
  -d '{"key": "Y29uZmlnLw=="}' | jq > config-current.json

# 2. Restore from backup
BACKUP_CONFIG=$(ls -t backups/config-backup-*.json | head -1)

# 3. Apply previous configuration
cat $BACKUP_CONFIG | jq -r '.[] | "\(.key)=\(.value)"' | while IFS='=' read key value; do
  sp-cli config set "$key" "$value"
done

# 4. Verify configuration
sp-cli config get config/database/pool_size
sp-cli config get config/redis/max_connections
```

### Rollback Environment Variables

```bash
# 1. Backup current .env
cp .env.production .env.production.backup-$(date +%Y%m%d-%H%M%S)

# 2. Restore previous .env
PREV_ENV=$(ls -t .env.production.backup-* | head -2 | tail -1)
cp $PREV_ENV .env.production

# 3. Restart services to pick up new env
docker-compose -f docker-compose.app.yml restart

# 4. Verify
docker exec agentic-l09-api-gateway env | grep DATABASE_URL
```

---

## UI Rollback

**Duration:** 2-5 minutes
**Downtime:** None (CDN update)

### Rollback Frontend to Previous Version

```bash
# 1. Identify previous UI version
PREV_UI_VERSION=$(git describe --tags HEAD~1)

# 2. Checkout previous UI code
git checkout $PREV_UI_VERSION -- platform/ui

# 3. Rebuild UI
cd platform/ui
npm run build

# 4. Deploy to CDN
aws s3 sync dist/ s3://platform-ui-production --delete

# 5. Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id XXXXX \
  --paths "/*"

# 6. Verify
curl -I https://app.example.com/ | grep -i cache
```

---

## Post-Rollback Procedures

### 1. Immediate Verification (5 min)

```bash
# Run full smoke test suite
pytest -m smoke --env=production -v

# Check error rates
docker logs agentic-l09-api-gateway --since=5m | grep -i error | wc -l

# Verify key metrics
curl -s https://api.example.com/health/live | jq
```

### 2. Monitoring (30 min)

- [ ] **Monitor error rates** (target: <0.1%)
  ```bash
  # Real-time error monitoring
  docker logs -f agentic-l09-api-gateway | grep -i error
  ```

- [ ] **Monitor performance** (target: <500ms p95)
  ```bash
  # Check Grafana dashboard
  open https://grafana.example.com/d/api-performance
  ```

- [ ] **Monitor user reports**
  - Check #support channel
  - Review support tickets
  - Monitor social media

### 3. Communication (10 min)

- [ ] **Update status page**
  ```
  Status: Operational
  Message: "Rollback completed successfully. All systems operational."
  ```

- [ ] **Notify stakeholders**
  - Email to engineering@example.com
  - Post in #incident-response
  - Update PagerDuty incident (resolved)

- [ ] **Customer communication**
  - Email to affected users
  - Post-mortem blog post (if needed)
  - Support team briefing

### 4. Post-Mortem Preparation

Create post-mortem document:
```markdown
# Rollback Post-Mortem: [Date]

## Summary
- What was deployed that caused the rollback?
- What went wrong?
- How long was the impact?

## Timeline
- [Time] - Deployment started
- [Time] - Issue detected
- [Time] - Rollback decision made
- [Time] - Rollback completed
- [Time] - System verified

## Impact
- Users affected: X
- Downtime duration: Y minutes
- Data loss: Yes/No
- Revenue impact: $Z

## Root Cause
[Detailed analysis]

## Action Items
- [ ] Fix underlying issue
- [ ] Update deployment checklist
- [ ] Improve testing coverage
- [ ] Update monitoring alerts
- [ ] Review rollback procedures
```

---

## Rollback Testing

### Monthly Rollback Drill

Test rollback procedures in staging environment:

```bash
# 1. Deploy latest to staging
./scripts/deploy-staging.sh

# 2. Perform rollback
./scripts/rollback-staging.sh

# 3. Time the process
time ./scripts/rollback-staging.sh

# 4. Verify all systems
pytest -m smoke --env=staging

# 5. Document results
echo "Rollback drill completed in: X minutes" >> rollback-drill-log.txt
```

### Rollback Verification Checklist

After test rollback:
- [ ] All services healthy
- [ ] Database accessible
- [ ] Smoke tests passing
- [ ] No error spikes in logs
- [ ] Configuration correct
- [ ] UI accessible
- [ ] API responsive
- [ ] Users can login
- [ ] Core features working

---

## Common Scenarios

### Scenario 1: Database Migration Failed

```bash
# Symptoms
- Alembic migration fails
- Database schema inconsistent
- Application can't connect

# Solution
1. Don't rollback database (data loss risk)
2. Fix migration script forward
3. If unfixable, rollback database (last resort)

# Commands
alembic downgrade -1  # Rollback one migration
# Fix migration file
alembic upgrade head  # Re-apply
```

### Scenario 2: Memory Leak Causing OOM

```bash
# Symptoms
- Containers getting OOM killed
- Memory usage climbing
- Frequent restarts

# Solution
1. Rollback affected service only (not full platform)
2. Monitor memory usage

# Commands
docker-compose -f docker-compose.app.yml stop l09-api-gateway
docker-compose -f docker-compose.app.yml up -d l09-api-gateway
docker stats agentic-l09-api-gateway
```

### Scenario 3: Configuration Change Broke Service

```bash
# Symptoms
- Service crashes on startup
- Configuration errors in logs
- Can't connect to dependencies

# Solution
1. Rollback configuration only (fastest)
2. Restart affected services

# Commands
sp-cli config get config/ > config-current.json
sp-cli config set <key> <previous-value>
docker-compose -f docker-compose.app.yml restart
```

### Scenario 4: Third-Party API Changed

```bash
# Symptoms
- External API calls failing
- Integration broken
- Unexpected responses

# Solution
1. Rollback integration layer (L11)
2. Fix API client code
3. Deploy fix

# Commands
docker-compose -f docker-compose.app.yml stop l11-integration
# Deploy previous version of L11
docker-compose -f docker-compose.app.yml up -d l11-integration
```

---

## Troubleshooting

### Rollback Failed: Services Won't Start

```bash
# Check Docker resources
docker system df
docker system prune -a  # If disk full

# Check network connectivity
docker network inspect agentic-platform-network

# Check container logs
docker logs agentic-l09-api-gateway --tail=100

# Restart Docker daemon (last resort)
sudo systemctl restart docker
```

### Rollback Failed: Database Restore Hangs

```bash
# Check database connections
docker exec agentic-postgres psql -U postgres -c \
  "SELECT * FROM pg_stat_activity WHERE datname='agentic_platform';"

# Kill blocking connections
docker exec agentic-postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='agentic_platform';"

# Retry restore
./platform/scripts/restore.sh backups/$BACKUP_FILE
```

### Rollback Failed: Configuration Not Applied

```bash
# Verify etcd is accessible
curl http://localhost:2379/version

# Check configuration values
sp-cli config get config/

# Force reload services
docker-compose -f docker-compose.app.yml restart
```

---

## Emergency Contacts

### Escalation Path

**Level 1: On-Call Engineer** (Response: <5 min)
- Phone: +1-xxx-xxx-xxxx
- PagerDuty: Platform On-Call

**Level 2: Team Lead** (Response: <15 min)
- Phone: +1-xxx-xxx-xxxx
- Email: team-lead@example.com

**Level 3: CTO** (Response: <30 min)
- Phone: +1-xxx-xxx-xxxx
- Email: cto@example.com

### External Support

- **Cloud Provider:** support.aws.com | +1-xxx-xxx-xxxx
- **Database Vendor:** support.postgresql.org
- **CDN Provider:** support.cloudflare.com

---

## Document Maintenance

- **Review Frequency:** After each deployment or rollback
- **Test Frequency:** Monthly rollback drills in staging
- **Update Trigger:** Any change to infrastructure or deployment process

**Last Tested:** _______________
**Test Duration:** _______________
**Test Result:** Pass / Fail
**Notes:** _______________

---

**Document Version:** 2.0
**Last Review Date:** 2026-01-18
**Next Review Date:** 2026-02-18
