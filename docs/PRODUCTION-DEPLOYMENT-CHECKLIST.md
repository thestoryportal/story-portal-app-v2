# Production Deployment Checklist

**Version:** 2.0
**Last Updated:** 2026-01-18
**Platform:** Story Portal V2 Platform

## Overview

This checklist ensures safe, reliable deployment of the V2 platform to production. Follow each section in order and verify all items before proceeding.

---

## Pre-Deployment Phase (T-7 Days)

### 1. Code Quality & Testing

- [ ] **All tests passing**
  ```bash
  # Run full test suite
  pytest -v
  pytest -m smoke
  pytest -m integration
  ```
  - Expected: 100% pass rate on critical paths
  - Acceptable: ≥95% overall pass rate

- [ ] **Code coverage meets threshold**
  ```bash
  pytest --cov --cov-report=html
  # Open htmlcov/index.html
  ```
  - Target: ≥80% coverage
  - Critical paths: ≥90% coverage

- [ ] **Static code analysis clean**
  ```bash
  sp-cli security bandit
  ```
  - Zero critical issues
  - Zero high severity issues

- [ ] **Security scan passed**
  ```bash
  sp-cli security scan
  ```
  - No critical vulnerabilities
  - All high severity issues addressed or documented

- [ ] **Performance benchmarks met**
  ```bash
  pytest -m performance
  ```
  - API response time: <500ms (p95)
  - Database query time: <100ms (p95)
  - UI load time: <3s (p95)

### 2. Documentation Review

- [ ] **API documentation up-to-date**
  - Verify: http://localhost:8099
  - All endpoints documented
  - Examples tested and working

- [ ] **README.md reflects current state**
  - Installation instructions accurate
  - Environment variables documented
  - Troubleshooting guide updated

- [ ] **Architecture diagrams current**
  - System architecture diagram
  - Database schema diagram
  - Network topology diagram

- [ ] **Runbook complete**
  - Deployment procedures documented
  - Common issues and solutions documented
  - Emergency contacts listed

### 3. Infrastructure Preparation

- [ ] **Production environment provisioned**
  - Compute resources allocated
  - Networking configured
  - Load balancers set up
  - SSL certificates obtained and installed

- [ ] **Database migration plan ready**
  - Migration scripts tested in staging
  - Rollback scripts prepared
  - Backup plan documented

- [ ] **High Availability configured**
  - PostgreSQL streaming replication (1 primary + 2 replicas)
  - Redis cluster (3 primaries + 3 replicas)
  - Multi-AZ deployment for critical services

- [ ] **Monitoring infrastructure ready**
  - Prometheus configured
  - Grafana dashboards created
  - Alert rules defined
  - PagerDuty/Slack integration configured

- [ ] **Backup systems operational**
  - Automated daily backups scheduled
  - Backup retention policy configured (30 days)
  - Restore procedures tested
  - Off-site backup replication enabled

### 4. Security Hardening

- [ ] **Secrets management configured**
  - No hardcoded secrets in code
  - Environment variables set in secure vault
  - API keys rotated
  - Database credentials unique per environment

- [ ] **Network security implemented**
  - Firewall rules configured
  - VPC/Security groups set up
  - Private subnets for databases
  - Bastion host for SSH access only

- [ ] **SSL/TLS configured**
  - Valid SSL certificates installed
  - TLS 1.2+ enforced
  - HTTP → HTTPS redirects enabled
  - Certificate auto-renewal configured

- [ ] **Authentication hardened**
  - JWT secret keys generated (production-specific)
  - Token expiration configured (15min access, 7day refresh)
  - Rate limiting enabled (100 req/min per IP)
  - CORS whitelist configured

- [ ] **Container security**
  - Base images scanned (Trivy)
  - Non-root users configured
  - Minimal runtime dependencies
  - Security updates applied

### 5. Configuration Management

- [ ] **Environment variables set**
  ```bash
  # Verify all required variables
  cat .env.production | grep -E "^[A-Z]" | wc -l
  ```
  - `DATABASE_URL` (production PostgreSQL)
  - `REDIS_URL` (production Redis)
  - `JWT_SECRET_KEY` (production secret)
  - `API_BASE_URL` (production domain)
  - `CORS_ORIGINS` (production frontends)
  - `LOG_LEVEL=INFO`
  - `ENVIRONMENT=production`

- [ ] **Feature flags reviewed**
  - All experimental features disabled
  - Beta features documented
  - Rollout percentages configured

- [ ] **Service discovery configured**
  - Consul cluster operational (3 nodes)
  - All services registered
  - Health checks configured

- [ ] **Configuration management ready**
  - etcd cluster operational (3 nodes)
  - Configuration values migrated
  - Backup of configuration taken

### 6. Stakeholder Communication

- [ ] **Deployment window scheduled**
  - Date and time announced (off-peak hours)
  - Duration estimated
  - Maintenance window communicated to users

- [ ] **Change request approved**
  - Change advisory board approval
  - Risk assessment completed
  - Rollback plan approved

- [ ] **Team assignments confirmed**
  - Deployment lead assigned
  - Support team on standby
  - Escalation path defined

- [ ] **Communication plan ready**
  - Status page URL: https://status.example.com
  - Email templates prepared
  - Social media posts drafted

---

## Deployment Phase (T-0)

### 7. Pre-Deployment Checks (T-30min)

- [ ] **Backup current production**
  ```bash
  # Database backup
  sp-cli db backup --production

  # Configuration backup
  kubectl get configmap -n production -o yaml > configs-backup.yaml

  # Service state snapshot
  docker ps > production-state.txt
  ```

- [ ] **Verify rollback readiness**
  - Previous version containers tagged
  - Database rollback script tested
  - DNS TTL reduced to 60s

- [ ] **Final smoke test in staging**
  ```bash
  pytest -m smoke --env=staging
  ```

- [ ] **Notify stakeholders: Deployment starting**
  - Status page updated: "Maintenance in progress"
  - Email sent to affected users
  - Internal team notified

### 8. Deployment Execution (T+0)

#### Step 1: Database Migration (T+0 to T+15)

- [ ] **Create production database backup**
  ```bash
  ./platform/scripts/backup.sh production
  ```

- [ ] **Run database migrations**
  ```bash
  # Connect to production
  export DATABASE_URL=<production-url>

  # Run migrations
  alembic upgrade head

  # Verify migrations
  alembic current
  ```

- [ ] **Validate data integrity**
  ```sql
  -- Check row counts
  SELECT 'agents' AS table_name, COUNT(*) FROM agents
  UNION ALL
  SELECT 'tasks', COUNT(*) FROM tasks
  UNION ALL
  SELECT 'sessions', COUNT(*) FROM sessions;

  -- Verify foreign key constraints
  SELECT * FROM pg_constraint WHERE contype = 'f';
  ```

#### Step 2: Container Deployment (T+15 to T+30)

- [ ] **Build production images**
  ```bash
  # Set production tag
  export VERSION=$(git describe --tags)

  # Build all service images
  docker-compose -f docker-compose.v2.yml build

  # Tag for production registry
  docker tag agentic-platform:latest registry.example.com/agentic-platform:$VERSION
  ```

- [ ] **Push images to registry**
  ```bash
  # Push to production registry
  docker push registry.example.com/agentic-platform:$VERSION
  ```

- [ ] **Deploy infrastructure services**
  ```bash
  # Deploy PostgreSQL HA
  docker-compose -f docker-compose.postgres-ha.yml up -d

  # Deploy Redis cluster
  docker-compose -f docker-compose.redis-ha.yml up -d

  # Deploy Consul
  docker-compose -f docker-compose.consul.yml up -d

  # Deploy etcd
  docker-compose -f docker-compose.etcd.yml up -d

  # Wait for readiness
  sleep 30
  ```

- [ ] **Deploy application services (rolling update)**
  ```bash
  # Deploy in dependency order
  # L01 Data Layer
  docker-compose -f docker-compose.app.yml up -d l01-data-layer
  sleep 10

  # L02-L07 Core Layers
  docker-compose -f docker-compose.app.yml up -d \
    l02-runtime l03-tool-execution l04-model-gateway \
    l05-planning l06-evaluation l07-learning
  sleep 10

  # L09 API Gateway
  docker-compose -f docker-compose.app.yml up -d l09-api-gateway
  sleep 10

  # L10 Human Interface
  docker-compose -f docker-compose.app.yml up -d l10-human-interface
  sleep 10

  # L11 Integration + L12 NL Interface
  docker-compose -f docker-compose.app.yml up -d l11-integration l12-nl-interface
  sleep 10
  ```

- [ ] **Deploy UI**
  ```bash
  # Build production UI
  cd platform/ui
  npm run build

  # Deploy to CDN/hosting
  aws s3 sync dist/ s3://platform-ui-production --delete
  aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*"
  ```

#### Step 3: Service Verification (T+30 to T+45)

- [ ] **Verify all containers running**
  ```bash
  docker ps --filter "name=agentic-" --format "table {{.Names}}\t{{.Status}}"
  ```
  - Expected: 23+ containers in "healthy" state

- [ ] **Check service health endpoints**
  ```bash
  # L01 Data Layer
  curl -f https://api.example.com/l01/health/live

  # L09 API Gateway
  curl -f https://api.example.com/health/live

  # L10 Human Interface
  curl -f https://api.example.com/l10/health/live

  # L12 NL Interface
  curl -f https://api.example.com/l12/health/live
  ```

- [ ] **Verify database connections**
  ```bash
  # Check active connections
  docker exec agentic-postgres psql -U postgres -c \
    "SELECT count(*) FROM pg_stat_activity WHERE datname='agentic_platform';"

  # Verify replication status
  docker exec agentic-postgres psql -U postgres -c \
    "SELECT * FROM pg_stat_replication;"
  ```

- [ ] **Verify Redis cluster**
  ```bash
  docker exec agentic-redis-1 redis-cli CLUSTER INFO
  docker exec agentic-redis-1 redis-cli CLUSTER NODES
  ```

- [ ] **Verify Consul service discovery**
  ```bash
  curl -s http://consul.example.com:8500/v1/catalog/services | jq
  ```

- [ ] **Check application logs**
  ```bash
  # Check for errors
  docker logs agentic-l09-api-gateway --tail=100 | grep -i error
  docker logs agentic-l10-human-interface --tail=100 | grep -i error
  ```

### 9. Post-Deployment Verification (T+45 to T+60)

- [ ] **Run smoke tests against production**
  ```bash
  # Set production URL
  export API_GATEWAY_URL=https://api.example.com

  # Run smoke tests
  pytest -m smoke --env=production
  ```

- [ ] **Verify critical user flows**
  - [ ] User registration and login
  - [ ] Agent creation and task execution
  - [ ] API key generation
  - [ ] Session management
  - [ ] File upload/download

- [ ] **Performance validation**
  ```bash
  # API latency check
  curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com/health/live
  ```
  - Target: <500ms response time

- [ ] **Security validation**
  - [ ] HTTPS enforced
  - [ ] CORS headers present
  - [ ] Rate limiting active
  - [ ] Authentication required for protected endpoints

- [ ] **Monitoring dashboards operational**
  - [ ] Grafana showing metrics
  - [ ] Prometheus scraping all targets
  - [ ] No critical alerts firing
  - [ ] Log aggregation working

- [ ] **Verify data consistency**
  ```sql
  -- Check critical tables
  SELECT COUNT(*) FROM agents;
  SELECT COUNT(*) FROM tasks;
  SELECT COUNT(*) FROM users;
  ```
  - Data counts match pre-deployment

### 10. User Acceptance (T+60 to T+120)

- [ ] **Internal team testing** (30 minutes)
  - Dev team: API testing
  - QA team: End-to-end testing
  - Product team: Feature verification

- [ ] **Beta user testing** (30 minutes)
  - 5-10 beta users invited
  - Critical path testing
  - Feedback collected

- [ ] **Monitor error rates**
  ```bash
  # Check error logs
  kubectl logs -n production -l app=api-gateway --since=1h | grep ERROR | wc -l
  ```
  - Target: <0.1% error rate

- [ ] **Monitor performance metrics**
  - Response time: <500ms (p95)
  - CPU usage: <70%
  - Memory usage: <80%
  - Database connections: <80% of max

---

## Post-Deployment Phase (T+120)

### 11. Communication & Handoff

- [ ] **Notify stakeholders: Deployment complete**
  - Status page updated: "All systems operational"
  - Email sent: "Platform upgraded successfully"
  - Internal team notified

- [ ] **Update documentation**
  - Deployment notes added to runbook
  - Known issues documented
  - Lessons learned captured

- [ ] **Handoff to operations team**
  - Deployment summary shared
  - Monitoring dashboard URLs provided
  - On-call schedule confirmed

### 12. Monitoring & Observation (T+120 to T+720)

- [ ] **Monitor for 6 hours minimum**
  - [ ] Hour 1: Active monitoring (every 5 minutes)
  - [ ] Hour 2-3: Regular monitoring (every 15 minutes)
  - [ ] Hour 4-6: Periodic monitoring (every 30 minutes)

- [ ] **Key metrics to watch**
  - Error rate: Should remain <0.1%
  - Response time: Should remain <500ms
  - CPU/Memory: Should be stable
  - Database connections: Should be normal
  - User sessions: Should be growing normally

- [ ] **Alert thresholds configured**
  - Critical: Error rate >1%, Response time >2s
  - Warning: Error rate >0.5%, Response time >1s
  - Info: Unusual traffic patterns

### 13. Success Criteria Validation

- [ ] **Platform health score ≥95/100**
  ```bash
  # Generate health report
  sp-cli health check --detailed
  ```

- [ ] **Zero critical incidents**
  - No service outages
  - No data loss
  - No security breaches

- [ ] **Performance targets met**
  - API response time: <500ms (p95) ✅
  - UI load time: <3s (p95) ✅
  - Database query time: <100ms (p95) ✅

- [ ] **User satisfaction**
  - No major user complaints
  - Beta user feedback positive
  - Internal team approval

---

## Rollback Procedures

### When to Rollback

Immediately rollback if:
- Critical functionality broken
- Data integrity issues detected
- Security vulnerability exposed
- Error rate >5%
- Response time >5s sustained

### Rollback Steps (15-30 minutes)

#### 1. Initiate Rollback (0-5 min)

- [ ] **Notify stakeholders**
  ```bash
  # Update status page
  echo "Rolling back to previous version" | update-status.sh
  ```

- [ ] **Stop new deployments**
  ```bash
  # Prevent auto-scaling
  kubectl scale deployment --replicas=0 -n production
  ```

#### 2. Revert Application Services (5-15 min)

- [ ] **Rollback containers to previous version**
  ```bash
  # Get previous version
  PREVIOUS_VERSION=$(git describe --tags HEAD~1)

  # Rollback services
  docker-compose -f docker-compose.app.yml down
  docker-compose -f docker-compose.app.yml pull $PREVIOUS_VERSION
  docker-compose -f docker-compose.app.yml up -d
  ```

- [ ] **Verify services running**
  ```bash
  docker ps --filter "name=agentic-" --format "table {{.Names}}\t{{.Status}}"
  ```

#### 3. Revert Database (if needed) (10-25 min)

- [ ] **Stop all application services**
  ```bash
  docker-compose -f docker-compose.app.yml stop
  ```

- [ ] **Restore database from backup**
  ```bash
  # Restore from pre-deployment backup
  ./platform/scripts/restore.sh <backup-timestamp>
  ```

- [ ] **Verify data integrity**
  ```sql
  SELECT COUNT(*) FROM agents;
  SELECT COUNT(*) FROM tasks;
  ```

#### 4. Restart Services (25-30 min)

- [ ] **Start services in order**
  ```bash
  # Restart infrastructure
  docker-compose -f docker-compose.v2.yml up -d postgres redis

  # Restart application
  docker-compose -f docker-compose.app.yml up -d
  ```

- [ ] **Run smoke tests**
  ```bash
  pytest -m smoke --env=production
  ```

#### 5. Post-Rollback Validation

- [ ] **All services healthy**
- [ ] **Smoke tests passing**
- [ ] **No data loss**
- [ ] **Users can access platform**

- [ ] **Notify stakeholders: Rollback complete**
  - Status page updated
  - Incident report drafted
  - Post-mortem scheduled

---

## Emergency Contacts

### Deployment Team

- **Deployment Lead:** [Name] - [Phone] - [Email]
- **Database Admin:** [Name] - [Phone] - [Email]
- **Infrastructure Lead:** [Name] - [Phone] - [Email]
- **Security Lead:** [Name] - [Phone] - [Email]

### Escalation Path

1. **Level 1:** On-call engineer (response: 5 minutes)
2. **Level 2:** Team lead (response: 15 minutes)
3. **Level 3:** CTO (response: 30 minutes)

### External Contacts

- **Cloud Provider Support:** [Support Number]
- **Database Vendor Support:** [Support Number]
- **SSL Certificate Provider:** [Support Number]

---

## Post-Deployment Review

### Within 24 Hours

- [ ] **Post-mortem meeting scheduled** (if issues occurred)
- [ ] **Deployment metrics analyzed**
  - Deployment duration
  - Downtime duration (if any)
  - Issue count and severity

- [ ] **Lessons learned documented**
  - What went well
  - What went wrong
  - What to improve

### Within 1 Week

- [ ] **Update deployment procedures**
  - Incorporate lessons learned
  - Update scripts and automation
  - Update documentation

- [ ] **Review monitoring and alerts**
  - Were alerts timely and actionable?
  - Were there false positives?
  - Are there gaps in coverage?

- [ ] **Plan for next deployment**
  - Schedule next release
  - Identify risk areas
  - Plan for improvements

---

## Appendix

### A. Useful Commands

```bash
# Check platform health
sp-cli platform status

# View service logs
sp-cli service logs <service-name>

# Database backup
sp-cli db backup

# Database restore
sp-cli db restore <backup-file>

# Security scan
sp-cli security scan

# Run smoke tests
pytest -m smoke

# Check API health
curl https://api.example.com/health/live

# Monitor logs in real-time
docker logs -f agentic-l09-api-gateway
```

### B. Health Check Endpoints

- **L01 Data Layer:** https://api.example.com/l01/health/{live,ready,startup}
- **L09 API Gateway:** https://api.example.com/health/{live,ready,startup}
- **L10 Human Interface:** https://api.example.com/l10/health/{live,ready,startup}
- **L12 NL Interface:** https://api.example.com/l12/health/{live,ready,startup}

### C. Monitoring Dashboards

- **Grafana:** https://grafana.example.com
- **Prometheus:** https://prometheus.example.com
- **Consul UI:** https://consul.example.com:8500
- **API Documentation:** https://docs.example.com

### D. Configuration Files

- **Production Environment:** `.env.production`
- **Docker Compose (Main):** `docker-compose.v2.yml`
- **Docker Compose (HA):** `docker-compose.postgres-ha.yml`, `docker-compose.redis-ha.yml`
- **Kubernetes Configs:** `k8s/production/`

---

## Checklist Completion

**Deployment Date:** _______________
**Deployment Lead:** _______________
**Deployment Duration:** _______________
**Issues Encountered:** _______________
**Rollback Performed:** Yes / No
**Overall Success:** Yes / No

**Signatures:**

- **Deployment Lead:** _______________ Date: _______________
- **QA Lead:** _______________ Date: _______________
- **Operations Lead:** _______________ Date: _______________

---

**Document Version:** 2.0
**Last Review Date:** 2026-01-18
**Next Review Date:** 2026-04-18 (or after next deployment)
