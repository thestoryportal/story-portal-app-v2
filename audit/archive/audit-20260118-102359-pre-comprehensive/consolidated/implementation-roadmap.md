# Implementation Roadmap - Story Portal Platform V2

**Generated:** 2026-01-18
**Current Health Score:** 79/100
**Target Health Score:** 90/100 (Production-Ready)
**Timeline:** 8 weeks to production readiness

---

## Roadmap Overview

This roadmap transforms the Story Portal Platform V2 from its current operational state (79/100) to production-ready status (90+/100) through 4 phased sprints.

### Milestone Timeline

```
Week 1-2: Critical Fixes         → 85/100 (Deployment-Ready)
Week 3-4: High Priority          → 88/100 (Production-Capable)
Week 5-6: Medium Priority        → 90/100 (Production-Ready)
Week 7-8: Optimization & Polish  → 92/100 (Production-Optimized)
```

---

## Phase 1: Critical Fixes (Week 1-2)

**Goal:** Address P1 issues to reach deployment-ready status
**Duration:** 2 weeks (80 hours, 2 engineers)
**Target Score:** 85/100

### Sprint 1.1: Infrastructure Stability (Week 1)

#### Task 1.1.1: Add Resource Limits to All Containers
- **Priority:** P1-002
- **Owner:** DevOps Team
- **Effort:** 4 hours
- **Dependencies:** None
- **Deliverables:**
  - Updated docker-compose.yml with resource limits for L01-L12
  - Documentation of resource allocation strategy
- **Acceptance Criteria:**
  - All containers have memory limits defined
  - All containers have CPU limits defined
  - No container can consume >90% of allocated resources
  - Containers restart if OOM occurs
- **Implementation:**
  ```yaml
  services:
    l01-data-layer:
      deploy:
        resources:
          limits:
            memory: 1G
            cpus: '1.0'
          reservations:
            memory: 512M
            cpus: '0.5'
  # Repeat for L02-L12
  ```
- **Testing:** Load test to verify limits enforced

#### Task 1.1.2: Tune PostgreSQL Configuration
- **Priority:** P1-004
- **Owner:** DBA / Infrastructure Team
- **Effort:** 2 hours
- **Dependencies:** None
- **Deliverables:**
  - Optimized postgresql.conf or Docker env vars
  - Baseline performance benchmarks
- **Acceptance Criteria:**
  - shared_buffers = 512MB
  - work_mem = 32MB
  - maintenance_work_mem = 256MB
  - Query performance improved by >20%
- **Implementation:**
  ```bash
  # Option A: Update postgresql.conf in container
  docker exec agentic-postgres psql -U postgres -c "ALTER SYSTEM SET shared_buffers = '512MB';"

  # Option B: Environment variables in docker-compose.yml
  environment:
    POSTGRES_INITDB_ARGS: "-c shared_buffers=512MB -c work_mem=32MB"
  ```
- **Testing:** Run pgbench before and after

#### Task 1.1.3: Resolve L08 Layer Status
- **Priority:** P1-001
- **Owner:** Platform Architecture Team
- **Effort:** 4 hours
- **Dependencies:** None
- **Deliverables:**
  - L08 deployed OR documentation explaining omission
  - Architecture diagram updated
- **Acceptance Criteria:**
  - Port 8008 responds with health check OR
  - ARCHITECTURE.md documents why L08 is skipped
  - No broken layer sequence
- **Implementation:**
  ```bash
  # Investigation
  find ./platform -name "*L08*" -o -name "*layer_08*"

  # If found, deploy
  docker-compose up -d l08-layer

  # If not found, document
  echo "L08 layer intentionally omitted - [reason]" >> ARCHITECTURE.md
  ```
- **Testing:** Verify port 8008 or verify documentation

### Sprint 1.2: Operational Excellence (Week 2)

#### Task 1.2.1: Standardize Health Check Endpoints
- **Priority:** P1-003
- **Owner:** API Team + Layer Owners
- **Effort:** 8 hours (distributed)
- **Dependencies:** Task 1.1.3 (L08 resolution)
- **Deliverables:**
  - Public /health endpoint on all services
  - API standards documentation
- **Acceptance Criteria:**
  - All L01-L12 services have /health endpoint
  - /health returns 200 OK without authentication
  - Response format standardized: `{"status":"healthy","version":"X.X.X"}`
  - Monitoring can access all health endpoints
- **Implementation:**
  ```python
  # Add to each layer's main.py
  @app.get("/health", tags=["health"])
  async def health_check():
      return {
          "status": "healthy",
          "version": "1.0.0",
          "timestamp": int(time.time())
      }
  # No authentication required!
  ```
- **Testing:** `curl http://localhost:800X/health` for X in 1-12

#### Task 1.2.2: CLI Tooling Decision & Implementation
- **Priority:** P1-005
- **Owner:** Platform Team
- **Effort:** 1 hour (documentation) OR 16 hours (implementation)
- **Dependencies:** None
- **Deliverables:**
  - Decision documented OR CLI tools implemented
- **Acceptance Criteria:**
  - **Option A:** ARCHITECTURE.md documents HTTP-only design rationale
  - **Option B:** Priority layers have working CLI: `python -m L01_data_layer --health`
- **Implementation Option B:**
  ```python
  # Add to each layer: __main__.py
  if __name__ == "__main__":
      import click

      @click.group()
      def cli():
          pass

      @cli.command()
      def health():
          """Check service health"""
          click.echo("Service healthy")

      cli()
  ```
- **Testing:** Execute `python -m L01_data_layer --help`

#### Task 1.2.3: Quick Wins Implementation
- **Priority:** Multiple P2/P3 items
- **Owner:** DevOps Team
- **Effort:** 4 hours
- **Dependencies:** None
- **Deliverables:**
  - Duplicate model removed
  - Legacy database dropped
  - Stopped containers cleaned up
- **Acceptance Criteria:**
  - llama3.2:3b removed, 2GB saved
  - "agentic" database dropped (if unused)
  - No stopped containers in `docker ps -a`
- **Implementation:**
  ```bash
  ollama rm llama3.2:3b
  docker exec agentic-postgres psql -U postgres -c "DROP DATABASE agentic;"
  docker rm practical_chebyshev awesome_hypatia
  docker image prune -f
  ```
- **Testing:** Verify space reclaimed, services unaffected

### Phase 1 Deliverables Checklist
- [ ] Resource limits on all containers
- [ ] PostgreSQL tuned for performance
- [ ] L08 deployed or documented
- [ ] Health checks standardized
- [ ] CLI decision made and implemented
- [ ] Quick wins completed
- [ ] Docker-compose.yml centralized (bonus)
- [ ] Phase 1 documentation updated

### Phase 1 Success Metrics
- **Health Score:** 85/100 (↑6 points)
- **Operational Readiness:** Deployment-ready for staging
- **Monitoring Coverage:** 100% health check accessibility
- **Resource Stability:** No OOM kills, predictable performance

---

## Phase 2: High Priority Improvements (Week 3-4)

**Goal:** Address P2 issues for production capability
**Duration:** 2 weeks (48 hours, 1 engineer)
**Target Score:** 88/100

### Sprint 2.1: Service Health & Discovery (Week 3)

#### Task 2.1.1: Investigate Redis Integration
- **Priority:** P2-005
- **Owner:** Backend Team
- **Effort:** 4 hours
- **Deliverables:**
  - Redis usage audit
  - Integration fixes OR removal plan
- **Acceptance Criteria:**
  - Redis DBSIZE > 0 (if integrated) OR Redis removed (if unused)
- **Implementation:**
  ```bash
  # Check code for Redis usage
  grep -r "redis" --include="*.py" ./platform

  # If unused, remove from docker-compose
  # If used, fix integration
  ```

#### Task 2.1.2: Fix L12 Service Registry
- **Priority:** P2-006
- **Owner:** L12 Team
- **Effort:** 4 hours
- **Deliverables:**
  - Service registry bug fixed
  - 44 services visible via API
- **Acceptance Criteria:**
  - `curl http://localhost:8012/api/v1/services` returns 44 services
  - Health check "services_loaded" matches API count
- **Implementation:**
  ```python
  # Debug service loading in L12
  # Verify registry initialization
  # Check service discovery mechanism
  ```

#### Task 2.1.3: Ollama Deployment Clarification
- **Priority:** P2-001
- **Owner:** Infrastructure Team
- **Effort:** 2 hours
- **Deliverables:**
  - Ollama deployment documented
  - Container vs host service clarified
- **Acceptance Criteria:**
  - DEPLOYMENT.md explains Ollama setup
  - Docker container properly tracked (if containerized)
  - Service monitoring configured

#### Task 2.1.4: PM2 Memory Reporting Fix
- **Priority:** P2-010
- **Owner:** MCP Team
- **Effort:** 2 hours
- **Deliverables:**
  - PM2 metrics collection fixed
  - Memory usage visible
- **Acceptance Criteria:**
  - `pm2 list` shows non-zero memory values
  - Resource monitoring dashboard updated

### Sprint 2.2: Database Optimization (Week 4)

#### Task 2.2.1: PostgreSQL Index Audit
- **Priority:** P2-008
- **Owner:** DBA
- **Effort:** 4 hours
- **Deliverables:**
  - Index coverage report
  - Missing indexes added
- **Acceptance Criteria:**
  - All foreign keys have indexes
  - Frequently queried columns indexed
  - Query performance improved
- **Implementation:**
  ```sql
  -- Find missing indexes on foreign keys
  SELECT ...

  -- Add indexes
  CREATE INDEX idx_documents_entity_id ON mcp_documents.documents(entity_id);
  ```

#### Task 2.2.2: Connection Pooling Implementation
- **Priority:** P2-009
- **Owner:** Backend Team
- **Effort:** 8 hours
- **Deliverables:**
  - pgBouncer deployed OR app-level pooling
  - Connection limits configured
- **Acceptance Criteria:**
  - Connection count remains stable under load
  - Max connections not exceeded
  - Latency <10ms for connection acquisition
- **Implementation:**
  ```yaml
  # Option: Add pgBouncer container
  pgbouncer:
    image: pgbouncer/pgbouncer
    environment:
      DATABASE_URL: postgres://postgres@agentic-postgres/agentic_platform
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
  ```

#### Task 2.2.3: Add pg_stat_statements Extension
- **Priority:** P2-014
- **Owner:** DBA
- **Effort:** 1 hour
- **Deliverables:**
  - Extension installed
  - Query monitoring enabled
- **Acceptance Criteria:**
  - Slow queries identified
  - Top 10 queries by execution time visible
- **Implementation:**
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

  -- View slow queries
  SELECT query, mean_exec_time FROM pg_stat_statements
  ORDER BY mean_exec_time DESC LIMIT 10;
  ```

### Sprint 2.3: Infrastructure Cleanup

#### Task 2.3.1: Model Management
- **Priority:** P2-007, P2-013
- **Owner:** ML Team
- **Effort:** 3 hours
- **Deliverables:**
  - LLaVA updated
  - CodeLlama evaluated/added
- **Implementation:**
  ```bash
  ollama pull llava-llama3:latest
  ollama pull codellama:13b  # if needed
  ```

#### Task 2.3.2: Docker Cleanup
- **Priority:** P2-003, P2-011, P2-012
- **Owner:** DevOps
- **Effort:** 2 hours
- **Deliverables:**
  - Centralized docker-compose.yml
  - Images pruned
  - Containers cleaned
- **Implementation:**
  ```bash
  # Create root docker-compose.yml
  # Consolidate all services
  docker image prune -a
  docker system df  # verify space reclaimed
  ```

### Phase 2 Deliverables Checklist
- [ ] Redis integration verified
- [ ] L12 service registry operational
- [ ] Ollama deployment documented
- [ ] PM2 monitoring working
- [ ] PostgreSQL indexes optimized
- [ ] Connection pooling deployed
- [ ] Query monitoring enabled
- [ ] Models updated
- [ ] Docker cleanup completed

### Phase 2 Success Metrics
- **Health Score:** 88/100 (↑3 points)
- **Operational Readiness:** Production-capable
- **Database Performance:** Query time <100ms p99
- **Service Discovery:** 100% services visible

---

## Phase 3: Medium Priority & Polish (Week 5-6)

**Goal:** Address selected P3 items for production readiness
**Duration:** 2 weeks (40 hours, 1 engineer)
**Target Score:** 90/100

### Sprint 3.1: Security Foundations

#### Task 3.1.1: Generate SSL/TLS Certificates
- **Priority:** P3-010
- **Effort:** 4 hours
- **Deliverables:**
  - Self-signed certs for development
  - Let's Encrypt for production (if applicable)
- **Implementation:**
  ```bash
  # Generate self-signed cert
  openssl req -x509 -newkey rsa:4096 \
    -keyout platform/ssl/key.pem \
    -out platform/ssl/cert.pem \
    -days 365 -nodes
  ```

#### Task 3.1.2: Create Security Documentation
- **Priority:** P3-011
- **Effort:** 8 hours
- **Deliverables:**
  - SECURITY.md with hardening guide
  - Security runbook
- **Content:**
  - Authentication setup
  - API key management
  - SSL/TLS configuration
  - Security best practices

### Sprint 3.2: Backup & Recovery

#### Task 3.2.1: Implement Backup Scripts
- **Priority:** P3-013
- **Effort:** 8 hours
- **Deliverables:**
  - backup.sh (PostgreSQL, Redis, configs)
  - restore.sh with verification
  - Automated scheduling
- **Implementation:**
  ```bash
  #!/bin/bash
  # backup.sh
  BACKUP_DIR="/tmp/story-portal-backups/$(date +%Y%m%d_%H%M%S)"
  mkdir -p $BACKUP_DIR

  # Backup PostgreSQL
  docker exec agentic-postgres pg_dump -U postgres agentic_platform | \
    gzip > $BACKUP_DIR/postgres.sql.gz

  # Backup Redis
  docker exec agentic-redis redis-cli SAVE
  docker cp agentic-redis:/data/dump.rdb $BACKUP_DIR/

  # Backup configs
  tar -czf $BACKUP_DIR/configs.tar.gz ./platform/{.env,docker-compose.yml}
  ```

#### Task 3.2.2: WAL Archiving & PITR
- **Priority:** P3-007, P3-009
- **Effort:** 4 hours
- **Deliverables:**
  - WAL archiving configured
  - Point-in-time recovery tested
- **Implementation:**
  ```ini
  # postgresql.conf
  wal_level = replica
  archive_mode = on
  archive_command = 'cp %p /backup/wal/%f'
  ```

### Sprint 3.3: Developer Experience

#### Task 3.3.1: Create Setup Scripts
- **Priority:** P3-023
- **Effort:** 4 hours
- **Deliverables:**
  - setup.sh for first-time setup
  - Makefile for common tasks
- **Implementation:**
  ```bash
  # setup.sh
  #!/bin/bash
  set -e
  echo "Setting up Story Portal Platform..."
  cp .env.example .env
  docker-compose up -d
  ./wait-for-services.sh
  echo "Setup complete!"
  ```

#### Task 3.3.2: Add Examples & Documentation
- **Priority:** P3-025
- **Effort:** 4 hours
- **Deliverables:**
  - Example API calls
  - Sample workflows
  - Quickstart guide

### Sprint 3.4: Monitoring Enhancements

#### Task 3.4.1: Resource Monitoring Dashboards
- **Priority:** P3-002
- **Effort:** 4 hours
- **Deliverables:**
  - Grafana dashboards for container resources
  - Alerts for resource thresholds
- **Implementation:**
  - Import pre-built dashboards
  - Configure alerting rules

#### Task 3.4.2: Automated Health Checks
- **Priority:** P3-003
- **Effort:** 2 hours
- **Deliverables:**
  - Health check monitoring script
  - Alert on service degradation
- **Implementation:**
  ```bash
  #!/bin/bash
  # health-monitor.sh
  for port in 8001 8002 8003 8004 8005 8006 8007 8009 8010 8011 8012; do
    curl -sf http://localhost:$port/health || echo "L$(($port-8000)) UNHEALTHY"
  done
  ```

### Phase 3 Deliverables Checklist
- [ ] SSL/TLS certificates generated
- [ ] SECURITY.md created
- [ ] Backup/restore scripts tested
- [ ] WAL archiving configured
- [ ] Setup scripts available
- [ ] Examples and quickstart added
- [ ] Grafana dashboards deployed
- [ ] Automated health monitoring

### Phase 3 Success Metrics
- **Health Score:** 90/100 (↑2 points)
- **Operational Readiness:** Production-ready
- **Security Posture:** Basic hardening complete
- **Recovery Time:** <15 minutes from backup

---

## Phase 4: Optimization & Advanced Features (Week 7-8)

**Goal:** Optimize performance and add advanced capabilities
**Duration:** 2 weeks (40 hours, 1 engineer)
**Target Score:** 92/100

### Sprint 4.1: CI/CD & Automation

#### Task 4.1.1: GitHub Actions Workflow
- **Priority:** P3-026
- **Effort:** 16 hours
- **Deliverables:**
  - .github/workflows/platform-ci.yml
  - Automated testing
  - Docker image builds
- **Stages:**
  1. Lint & type check
  2. Unit tests
  3. Integration tests
  4. Build Docker images
  5. Deploy to staging

#### Task 4.1.2: Automated Testing
- **Priority:** P3-018, P3-019
- **Effort:** 8 hours
- **Deliverables:**
  - pytest configuration
  - Coverage reporting
  - Integration test suite
- **Target:** >70% code coverage

### Sprint 4.2: High Availability Planning

#### Task 4.2.1: HA Architecture Design
- **Priority:** P3-027
- **Effort:** 8 hours
- **Deliverables:**
  - HIGH-AVAILABILITY.md
  - HAProxy configuration
  - Scaling strategy
- **Components:**
  - Load balancer (HAProxy/nginx)
  - Service replicas (2-3x for critical services)
  - Database replication
  - Shared state management

#### Task 4.2.2: Performance Optimization
- **Priority:** P3-020, P3-021, P3-022
- **Effort:** 8 hours
- **Deliverables:**
  - Code refactoring (large files)
  - Type hint improvements
  - Performance benchmarks
- **Targets:**
  - Response time <100ms p99
  - Throughput >1000 req/s

### Phase 4 Deliverables Checklist
- [ ] CI/CD pipeline operational
- [ ] Automated tests passing
- [ ] HA architecture documented
- [ ] Performance optimizations applied
- [ ] Load testing completed
- [ ] Final documentation review

### Phase 4 Success Metrics
- **Health Score:** 92/100 (↑2 points)
- **Operational Readiness:** Production-optimized
- **Automation:** 100% deployments automated
- **Scalability:** HA architecture planned

---

## Resource Requirements

### Team Composition
- **1x DevOps Engineer** (Weeks 1-2, 5-6)
- **1x Backend Engineer** (Weeks 3-4, 5-6)
- **0.5x DBA** (Weeks 1-2, 3-4)
- **0.5x Security Engineer** (Weeks 5-6)
- **1x Platform Architect** (Advisory throughout)

### Total Effort
- **Phase 1:** 80 hours (2 engineers × 2 weeks)
- **Phase 2:** 48 hours (1 engineer × 2 weeks + DBA)
- **Phase 3:** 40 hours (1 engineer × 2 weeks)
- **Phase 4:** 40 hours (1 engineer × 2 weeks)
- **TOTAL:** 208 hours (≈5 person-weeks)

### Budget Estimate (if contractors)
- DevOps: 160 hours × $150/hr = $24,000
- Backend: 48 hours × $130/hr = $6,240
- DBA: 40 hours × $140/hr = $5,600
- Security: 20 hours × $160/hr = $3,200
- **TOTAL:** $39,040

---

## Risk Management

### High Risks
1. **L08 Layer Missing**
   - Mitigation: Investigate in Week 1, Day 1
   - Contingency: Document omission if not found

2. **Resource Limits Cause Instability**
   - Mitigation: Conservative initial limits
   - Contingency: Rollback mechanism ready

3. **Database Tuning Degrades Performance**
   - Mitigation: Benchmark before/after
   - Contingency: Keep original config as backup

### Medium Risks
4. **Health Check Changes Break Monitoring**
   - Mitigation: Phased rollout, one layer at a time
   - Contingency: Keep auth-based endpoints alongside

5. **Redis Integration Unclear**
   - Mitigation: Early investigation (Week 3)
   - Contingency: Remove if unused, minimal impact

### Low Risks
6. **Timeline Slippage**
   - Mitigation: Buffer built into each phase
   - Contingency: Prioritize P1/P2, defer P3

---

## Success Criteria

### Phase 1 Success (Week 2)
- ✅ All containers have resource limits
- ✅ PostgreSQL performance improved
- ✅ All health checks accessible
- ✅ Score ≥85/100

### Phase 2 Success (Week 4)
- ✅ Service discovery operational
- ✅ Database optimized (indexes, pooling)
- ✅ Infrastructure cleaned up
- ✅ Score ≥88/100

### Phase 3 Success (Week 6)
- ✅ Basic security hardening complete
- ✅ Backup/restore tested
- ✅ Developer experience improved
- ✅ Score ≥90/100 (PRODUCTION-READY)

### Phase 4 Success (Week 8)
- ✅ CI/CD pipeline operational
- ✅ HA architecture planned
- ✅ Performance optimized
- ✅ Score ≥92/100 (PRODUCTION-OPTIMIZED)

---

## Maintenance & Ongoing Operations

### After Week 8
1. **Weekly:** Monitor health scores, address degradation
2. **Bi-weekly:** Review and address new P3 items
3. **Monthly:** Capacity planning, performance review
4. **Quarterly:** Security audit, dependency updates

### Continuous Improvement
- Implement service mesh (Month 3-4)
- Add distributed tracing (Month 4-5)
- Expand test coverage to 90% (Month 5-6)
- Implement chaos engineering (Month 6+)

---

## Appendices

### A. Rollback Procedures
For each phase, document rollback steps in case of issues:
- Phase 1: Revert docker-compose, restart containers
- Phase 2: Restore database config, remove pooler
- Phase 3: Disable SSL, remove monitoring
- Phase 4: Rollback CI/CD changes

### B. Testing Checklists
Detailed test plans for each phase available in:
- `./audit/testing/phase1-tests.md`
- `./audit/testing/phase2-tests.md`
- etc.

### C. Communication Plan
- Week 1: Kickoff meeting
- Weekly: Status updates to stakeholders
- Phase end: Demo & review
- Week 8: Final review & handoff

---

**End of Implementation Roadmap**
**For detailed findings, see:** `./audit/consolidated/FULL-AUDIT-REPORT.md`
**For priority details, see:** `./audit/consolidated/priority-matrix.md`
