# Priority Matrix - Story Portal Platform V2 Audit

**Generated:** 2026-01-18
**Total Findings:** 47
**Critical Issues:** 0
**High Priority:** 5
**Medium Priority:** 15
**Low Priority:** 27

---

## Priority Classification

| Priority | Definition | Timeline | Impact |
|----------|------------|----------|--------|
| **P0** | Critical - Blocking production | Immediate (24h) | System down/data loss |
| **P1** | High - Required for production | Week 1-2 | Major functionality gap |
| **P2** | Medium - Strongly recommended | Week 3-6 | Performance/stability |
| **P3** | Low - Nice to have | Month 2+ | Quality of life |

---

## P0 - CRITICAL (0 findings)

**None identified - No showstopper issues**

---

## P1 - HIGH PRIORITY (5 findings)

### P1-001: Layer L08 Not Deployed
- **Category:** Service Discovery
- **Source:** AUD-010
- **Finding:** Port 8008 not responding; breaks layer sequence (L01-L07, L09-L12)
- **Impact:** Unknown functionality missing; architectural gap
- **Risk:** Medium (if L08 is essential) / Low (if intentional)
- **Effort:** 2-4 hours (deploy) or 1 hour (document omission)
- **Dependencies:** None
- **Recommended Action:**
  1. Verify if L08 exists in codebase
  2. Deploy if present, or document why L08 is skipped
  3. Update architecture diagrams
- **Owner:** Platform Architecture Team

### P1-002: Missing Resource Limits on Platform Layers
- **Category:** Infrastructure
- **Source:** AUD-019
- **Finding:** All L01-L12 services have Memory=0 CPU=0 (unlimited resources)
- **Impact:** Risk of resource contention, OOM kills, noisy neighbor issues
- **Risk:** High under load
- **Effort:** 4 hours
- **Dependencies:** None
- **Recommended Action:**
  ```yaml
  # Add to docker-compose.yml
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
  ```
- **Owner:** DevOps Team

### P1-003: Inconsistent Health Check Endpoints
- **Category:** Service Discovery
- **Source:** AUD-010
- **Finding:**
  - L12: /health returns 200 (public)
  - L09, L01: /health requires authentication (401)
  - L02-L07, L10-L11: /health returns 404
- **Impact:** Monitoring systems cannot check service health; inconsistent observability
- **Risk:** High (operational blindness)
- **Effort:** 8 hours (standardize across 10 layers)
- **Dependencies:** None
- **Recommended Action:**
  1. Add public `/health` endpoint to all services (returns 200 OK without auth)
  2. Add `/ready` endpoint for startup checks
  3. Move authentication check to `/auth/verify` or similar
  4. Document standard in API guidelines
- **Owner:** API Team + Each Layer Owner

### P1-004: PostgreSQL Not Tuned for Container Resources
- **Category:** Infrastructure - Database
- **Source:** AUD-021
- **Finding:**
  - shared_buffers: 128MB (should be 512MB for 2GB container = 25% rule)
  - work_mem: 4MB (should be 16-32MB for complex queries)
  - maintenance_work_mem: 64MB (should be 256MB for faster vacuuming)
- **Impact:** Suboptimal query performance; slow bulk operations
- **Risk:** Medium (performance degradation under load)
- **Effort:** 2 hours
- **Dependencies:** None
- **Recommended Action:**
  ```ini
  # Add to postgresql.conf or Docker environment variables
  shared_buffers = 512MB
  effective_cache_size = 4GB
  work_mem = 32MB
  maintenance_work_mem = 256MB
  ```
- **Owner:** DBA / Infrastructure Team

### P1-005: No CLI Entry Points
- **Category:** Developer Experience
- **Source:** AUD-011
- **Finding:** Zero layers have `__main__.py` or `cli.py` CLI interfaces
- **Impact:** Cannot interact with layers directly; limited debugging; HTTP-only workflow
- **Risk:** Low (if intentional) / Medium (if oversight)
- **Effort:** 16 hours (to implement) or 1 hour (to document)
- **Dependencies:** Architecture decision
- **Recommended Action:**
  - **Option A:** Add CLI entry points for debugging (`python -m L01_data_layer --help`)
  - **Option B:** Document that platform is HTTP-only by design
  - If Option A, prioritize: L01, L04, L09, L12 (most critical layers)
- **Owner:** Platform Team + Each Layer Owner

---

## P2 - MEDIUM PRIORITY (15 findings)

### P2-001: Ollama Container Status Unclear
- **Category:** Infrastructure
- **Source:** AUD-019, AUD-020
- **Finding:** API accessible at localhost:11434 but Docker shows `awesome_hypatia` stopped
- **Impact:** Confusion about service deployment; potential for accidental shutdown
- **Effort:** 2 hours
- **Action:** Clarify if Ollama runs as host service or different container; update docs

### P2-002: Duplicate llama3.2 Model Tags
- **Category:** LLM Infrastructure
- **Source:** AUD-020
- **Finding:** Both `llama3.2:latest` and `llama3.2:3b` are identical (2.02GB each)
- **Impact:** 2GB wasted storage
- **Effort:** 30 minutes
- **Action:** `ollama rm llama3.2:3b` (keep :latest)

### P2-003: No docker-compose.yml in Root
- **Category:** Infrastructure
- **Source:** AUD-019
- **Finding:** `docker-compose config` failed - no compose file detected
- **Impact:** Difficult to manage multi-container deployment
- **Effort:** 4 hours
- **Action:** Create/centralize docker-compose.yml with all services

### P2-004: Legacy "agentic" Database Present
- **Category:** Database
- **Source:** AUD-021
- **Finding:** Database "agentic" exists but appears unused (active is "agentic_platform")
- **Impact:** Resource waste; potential confusion
- **Effort:** 1 hour
- **Action:** Verify if unused, then `DROP DATABASE agentic;`

### P2-005: Redis Completely Empty
- **Category:** Infrastructure - Cache
- **Source:** AUD-015
- **Finding:** DBSIZE returns 0 keys despite 10h uptime
- **Impact:** Redis may be unused; wasted resources if true
- **Effort:** 4 hours
- **Action:** Verify Redis integration in application layers; remove if unused

### P2-006: L12 Service Hub API Inconsistency
- **Category:** V2 Components
- **Source:** AUD-026
- **Finding:** Health check claims 44 services loaded, but `/api/v1/services` returns 0
- **Impact:** Service discovery broken; misleading health status
- **Effort:** 4 hours
- **Action:** Debug service registry loading issue

### P2-007: LLaVA Model Outdated
- **Category:** LLM Infrastructure
- **Source:** AUD-020
- **Finding:** LLaVA last modified 2025-12-26 (23 days ago)
- **Impact:** Missing latest improvements
- **Effort:** 1 hour
- **Action:** `ollama pull llava-llama3:latest`

### P2-008: No Index Analysis Performed
- **Category:** Database
- **Source:** AUD-021
- **Finding:** Cannot verify if appropriate indexes exist on frequently queried columns
- **Impact:** Potential slow queries
- **Effort:** 4 hours
- **Action:** Audit indexes on mcp_documents schema; add where needed

### P2-009: No Connection Pooling Configuration
- **Category:** Database
- **Source:** AUD-021
- **Finding:** Direct connections from application layers
- **Impact:** Risk of connection exhaustion under load
- **Effort:** 8 hours
- **Action:** Implement pgBouncer or connection pooling in app code

### P2-010: PM2 Memory Reporting Issue
- **Category:** MCP Services
- **Source:** AUD-010
- **Finding:** Both MCP services show 0b memory usage
- **Impact:** Cannot monitor resource usage
- **Effort:** 2 hours
- **Action:** Fix PM2 metrics collection

### P2-011: Stopped Containers Present
- **Category:** Infrastructure
- **Source:** AUD-019
- **Finding:** `practical_chebyshev` (postgres) and `awesome_hypatia` (ollama) are stopped
- **Impact:** Clutter; potential confusion
- **Effort:** 30 minutes
- **Action:** `docker rm practical_chebyshev awesome_hypatia`

### P2-012: Image Cleanup Needed
- **Category:** Infrastructure
- **Source:** AUD-019
- **Finding:** Multiple tag versions (latest, test, prefixed), 8.97GB Ollama image unused
- **Impact:** Wasted disk space
- **Effort:** 1 hour
- **Action:** `docker image prune -a` (after backing up needed images)

### P2-013: No Code-Specialized LLM Models
- **Category:** LLM Infrastructure
- **Source:** AUD-020
- **Finding:** No CodeLlama or similar models for code generation
- **Impact:** Suboptimal for code-related tasks
- **Effort:** 2 hours
- **Action:** Consider `ollama pull codellama:13b` if needed

### P2-014: Missing pg_stat_statements Extension
- **Category:** Database
- **Source:** AUD-021
- **Finding:** Extension not detected for query performance monitoring
- **Impact:** Cannot identify slow queries
- **Effort:** 1 hour
- **Action:** `CREATE EXTENSION pg_stat_statements;`

### P2-015: MCP Configuration Files Minimal
- **Category:** MCP Services
- **Source:** AUD-012
- **Finding:** Only 2 .mcp.json files found
- **Impact:** Limited MCP service configuration
- **Effort:** 4 hours
- **Action:** Document MCP architecture and expand configuration if needed

---

## P3 - LOW PRIORITY (27 findings)

### Infrastructure & Operations

#### P3-001: No GPU Acceleration for Ollama
- **Source:** AUD-020
- **Impact:** Slower LLM inference (CPU-only)
- **Effort:** Hardware dependent
- **Action:** Document performance expectations; plan GPU for production

#### P3-002: Container Resource Usage Monitoring
- **Source:** AUD-019
- **Impact:** Cannot track resource trends
- **Effort:** 4 hours
- **Action:** Add Grafana dashboards for container resources

#### P3-003: No Monitoring Documentation
- **Source:** AUD-019
- **Impact:** Unclear monitoring ownership
- **Effort:** 2 hours
- **Action:** Document monitoring architecture

#### P3-004: Image Tagging Strategy Unstandardized
- **Source:** AUD-019
- **Impact:** Inconsistent versioning
- **Effort:** 4 hours
- **Action:** Define and implement tagging standard (semantic versioning)

#### P3-005: No Automated Image Pruning
- **Source:** AUD-019
- **Impact:** Disk space accumulation
- **Effort:** 2 hours
- **Action:** Add cron job for `docker image prune`

### Database & Data Layer

#### P3-006: maintenance_work_mem Low
- **Source:** AUD-021
- **Impact:** Slow VACUUM and CREATE INDEX operations
- **Effort:** 30 minutes
- **Action:** Set to 256MB in postgresql.conf

#### P3-007: No Automated VACUUM Scheduling
- **Source:** AUD-021
- **Impact:** Potential table bloat over time
- **Effort:** 2 hours
- **Action:** Configure autovacuum or schedule manual vacuums

#### P3-008: No Database Growth Planning
- **Source:** AUD-021
- **Impact:** Unprepared for scale
- **Effort:** 4 hours
- **Action:** Model growth, plan partitioning strategy

#### P3-009: No Backup Verification Process
- **Source:** AUD-024, AUD-035
- **Impact:** Backups may be corrupt/incomplete
- **Effort:** 4 hours
- **Action:** Implement automated backup testing

### Security & Compliance

#### P3-010: No SSL/TLS Certificates Detected
- **Source:** AUD-023, AUD-033
- **Impact:** No encryption in transit
- **Effort:** 8 hours
- **Action:** Generate and configure SSL certificates

#### P3-011: Security Documentation Missing
- **Source:** AUD-033
- **Impact:** No reference for security procedures
- **Effort:** 8 hours
- **Action:** Create SECURITY.md with hardening guide

#### P3-012: No Internal HTTPS Usage
- **Source:** AUD-023
- **Impact:** Unencrypted internal communication
- **Effort:** 16 hours
- **Action:** Implement mTLS for service-to-service

#### P3-013: Backup/Recovery Scripts Missing
- **Source:** AUD-024, AUD-035
- **Impact:** No disaster recovery procedure
- **Effort:** 8 hours
- **Action:** Create backup.sh and restore.sh with testing

### API & Integration

#### P3-014: Inconsistent Error Response Formats
- **Source:** AUD-010
- **Impact:** Difficult client error handling
- **Effort:** 8 hours
- **Action:** Standardize error format (RFC 7807 Problem Details)

#### P3-015: No Service Registry Detected
- **Source:** AUD-010
- **Impact:** Manual service discovery
- **Effort:** 16 hours
- **Action:** Implement Consul or etcd

#### P3-016: No OpenAPI Specifications Found
- **Source:** AUD-016
- **Impact:** No API documentation generation
- **Effort:** 8 hours per layer
- **Action:** Add OpenAPI/Swagger to each layer

#### P3-017: No Circuit Breakers
- **Source:** AUD-010
- **Impact:** Cascading failures possible
- **Effort:** 16 hours
- **Action:** Implement circuit breaker pattern (resilience4j, Hystrix)

### Quality & Testing

#### P3-018: Test File Count Unknown
- **Source:** AUD-003
- **Impact:** Cannot assess test coverage
- **Effort:** 2 hours
- **Action:** Generate test coverage report

#### P3-019: No pytest Configuration
- **Source:** AUD-003
- **Impact:** Inconsistent test execution
- **Effort:** 2 hours
- **Action:** Create pytest.ini with standards

#### P3-020: Type Hint Coverage Unknown
- **Source:** AUD-007
- **Impact:** Reduced IDE support, more runtime errors
- **Effort:** 40 hours (to add comprehensively)
- **Action:** Run mypy audit, add type hints incrementally

#### P3-021: Large Files Detected (>500 lines)
- **Source:** AUD-007
- **Impact:** Reduced maintainability
- **Effort:** Variable
- **Action:** Refactor large files into smaller modules

#### P3-022: TODO/FIXME Comments Present
- **Source:** AUD-007
- **Impact:** Technical debt markers
- **Effort:** Variable
- **Action:** Address or convert to tracked issues

### Developer Experience

#### P3-023: No Setup Scripts
- **Source:** AUD-009
- **Impact:** Manual setup process
- **Effort:** 4 hours
- **Action:** Create setup.sh and install.sh

#### P3-024: No Makefile
- **Source:** AUD-009
- **Impact:** No command shortcuts
- **Effort:** 2 hours
- **Action:** Create Makefile with common tasks

#### P3-025: Examples/Samples Missing
- **Source:** AUD-009
- **Impact:** Harder to onboard developers
- **Effort:** 8 hours
- **Action:** Add example code and usage samples

### Production Readiness

#### P3-026: CI/CD Pipeline Not Detected
- **Source:** AUD-036
- **Impact:** Manual deployment process
- **Effort:** 16 hours
- **Action:** Create GitHub Actions workflow

#### P3-027: High Availability Not Configured
- **Source:** AUD-037
- **Impact:** Single point of failure
- **Effort:** 40 hours
- **Action:** Plan and implement HA architecture

---

## Effort Summary

| Priority | Count | Total Effort (hours) | Average Effort |
|----------|-------|----------------------|----------------|
| P0 | 0 | 0 | N/A |
| P1 | 5 | 32-40 | 6-8 hours |
| P2 | 15 | 48 | 3.2 hours |
| P3 | 27 | 214+ | 7.9 hours |
| **TOTAL** | **47** | **294-302** | **6.3 hours** |

### Resource Allocation Recommendation
- **Week 1-2:** Focus on P1 (32-40 hours, 2 engineers)
- **Week 3-6:** Address P2 (48 hours, 1 engineer)
- **Month 2-3:** Select P3 items based on priority (214+ hours, multiple engineers)

---

## Risk Matrix

| Finding | Likelihood | Impact | Risk Score | Priority |
|---------|------------|--------|------------|----------|
| Missing resource limits | High | High | **9** | P1 |
| Inconsistent health checks | High | Medium | **6** | P1 |
| PostgreSQL not tuned | Medium | Medium | **4** | P1 |
| L08 not deployed | Low | High | **3** | P1 |
| No CLI entry points | Low | Low | **1** | P1 |
| Redis empty | Medium | Low | **2** | P2 |
| No SSL/TLS | Low | High | **3** | P3 |
| No backups | Low | High | **3** | P3 |

**Risk Score = Likelihood (1-3) × Impact (1-3)**
- 7-9: Critical
- 4-6: High
- 1-3: Medium/Low

---

## Dependencies & Sequencing

```
Week 1:
  P1-001 (L08) → No dependencies
  P1-002 (Resource limits) → No dependencies
  P1-004 (PostgreSQL tune) → No dependencies

Week 2:
  P1-003 (Health checks) → Depends on P1-001 (L08 must exist first)
  P1-005 (CLI) → Architecture decision first

Week 3-4:
  P2 items → Can proceed independently

Month 2+:
  P3 items → Some depend on P1/P2 completion
```

---

## Quick Wins (Highest Value, Lowest Effort)

1. **P1-004:** PostgreSQL tuning (2 hours, immediate performance gain)
2. **P2-002:** Remove duplicate model (30 minutes, save 2GB)
3. **P2-004:** Drop unused database (1 hour, clean up)
4. **P2-011:** Remove stopped containers (30 minutes, clean up)
5. **P3-006:** Increase maintenance_work_mem (30 minutes, faster operations)

**Total Quick Wins:** 4.5 hours, multiple immediate improvements

---

**End of Priority Matrix**
**For implementation details, see:** `./audit/consolidated/implementation-roadmap.md`
