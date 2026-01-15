# Session: Tool Execution Layer -- Specification Part 3

## Objective
Write specification Sections 11-15: Implementation, Testing, Migration, Open Questions, References.

Ensure ALL gap analysis findings are addressed.

## Source Files in Project Knowledge
1. `tool-execution-spec-part1.md`
2. `tool-execution-spec-part2.md`
3. `tool-execution-research-findings.md`
4. `tool-execution-gap-analysis.md`

## Checkpoint Protocol

**Exchange limit:** 8 exchanges for this session

**Checkpoint triggers:**
- After each section (5 sections total)
- After Gap Integration Summary appendix
- When context estimate exceeds 60%

**At each checkpoint:**
1. Save completed sections to file
2. Report: Section [X] complete, [Y] remaining
3. PAUSE - wait for "Continue"

## Gap Integration Verification
Before writing, verify all gaps from analysis have been assigned to sections:
| Gap ID | Status | Section | Notes |

If any gaps are unassigned, assign them now.

## Sections to Write

### Section 11: Implementation Guide
- 11.1 Implementation Phases
  - Phase 1: Tool Registry (PostgreSQL) and basic execution
  - Phase 2: Permission integration and ABAC
  - Phase 3: Circuit breaker (Redis) and external adapters
  - Phase 4: Result validation and MCP integration
  - Phase 5: Document Bridge (Phase 15) integration
  - Phase 6: State Bridge (Phase 16) integration
- 11.2 Implementation Order (dependency graph, ASCII)
- 11.3 Component Implementation Details
  - Tool Registry implementation (PostgreSQL + pgvector per ADR-002)
  - Tool Executor implementation (nested sandbox)
  - Permission Checker implementation
  - External Adapter Manager implementation
  - Circuit Breaker Controller implementation (Redis per ADR-002)
  - Result Validator implementation
  - Document Bridge implementation (MCP stdio per ADR-001)
  - State Bridge implementation (MCP stdio per ADR-001)
- 11.4 Code Examples (Python with type hints)
  - Tool invocation handler
  - Circuit breaker state machine
  - Result validation pipeline
  - MCP document query client
  - MCP checkpoint client
- 11.5 Error Codes Registry (E3000-E3999 complete list including E3850-E3949 for MCP)


---

### Section 12: Testing Strategy
- 12.1 Test Categories
- 12.2 Unit Tests (per component)
  - Tool Registry tests
  - Permission Checker tests
  - Circuit Breaker tests
  - Result Validator tests
  - Document Bridge tests (mock MCP)
  - State Bridge tests (mock MCP)
- 12.3 Integration Tests
  - Tool invocation end-to-end
  - ABAC integration
  - Event Store integration
  - Phase 15 document context flow
  - Phase 16 checkpoint/restore flow
- 12.4 Performance Tests
  - Tool execution latency
  - Concurrent invocation throughput
  - Circuit breaker response time
  - MCP query latency
- 12.5 Chaos Tests
  - External service failure
  - Network partition
  - Credential rotation during execution
  - MCP service unavailability
  - Checkpoint corruption recovery
- 12.6 Security Tests
  - Sandbox escape attempts
  - Privilege escalation
  - Credential exposure
  - MCP injection attacks
- 12.7 Test Examples (pytest code)


---

### Section 13: Migration and Deployment
- 13.1 Deployment Strategy
  - Container image specification
  - Kubernetes deployment manifest
  - Service mesh integration
  - PM2 configuration for MCP services
- 13.2 Infrastructure Prerequisites (per ADR-002)
  - PostgreSQL 16 + pgvector setup
  - Redis 7 cluster setup
  - Ollama deployment (optional)
  - MCP service deployment via PM2
- 13.3 Upgrade Procedures
  - Tool registry migration
  - Circuit breaker state preservation
  - MCP service updates
- 13.4 Rollback Procedures
- 13.5 Disaster Recovery
  - Tool registry backup/restore (PostgreSQL)
  - Circuit breaker state recovery (Redis)
  - MCP service recovery
  - External service failover


---

### Section 14: Open Questions and Decisions
- 14.1 Resolved Questions
  - Q1: Tool versioning decision and rationale
  - Q2: Long-running operations pattern (Phase 16 checkpoints)
  - Q3: Credential rotation strategy
  - Q4: MCP tool adapter pattern (ADR-001 stdio)
  - Q5: Phase 15 document context caching
  - Q6: Phase 16 checkpoint granularity
  - Q7: Redis vs PostgreSQL for circuit breaker (Redis per ADR-002)
- 14.2 Deferred Decisions (with rationale and target version)
- 14.3 Assumptions
- 14.4 Risks and Mitigations


---

### Section 15: References and Appendices
- 15.1 External References
  - MCP Specification
  - Circuit Breaker Pattern (Martin Fowler)
  - OpenTelemetry Semantic Conventions
  - PostgreSQL pgvector documentation
  - Redis data structures
- 15.2 Internal References
  - Data Layer v4.0 Sections (Event Store, ABAC, Phase 13, 15, 16)
  - Agent Runtime v1.2 Sections (BC-1 sandbox interface)
  - Model Gateway v1.2 Sections (function calling)
  - ADR-001 MCP Integration Architecture
  - ADR-002 Lightweight Development Stack
- 15.3 Glossary

### Appendix A: Gap Analysis Integration Summary
**REQUIRED:** Include complete table showing ALL gaps and how addressed:
| Gap ID | Description | Priority | Section | How Addressed |

All gaps must show "Addressed" status. NO gaps may be deferred.

### Appendix B: Error Code Reference
Complete E3000-E3999 error code listing including:
- E3850-E3899: MCP Document Bridge errors (Phase 15)
- E3900-E3949: MCP State Bridge errors (Phase 16)

### Appendix C: Tool Manifest Schema (Complete JSON Schema)

### Appendix D: MCP Bridge Configuration Examples

## Output
Save as: `tool-execution-spec-part3.md`

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-spec-part3.md` | Sections 11-15 for merge |

### Verification
- [ ] All 5 sections complete
- [ ] Gap Integration Summary shows 100% addressed
- [ ] Phase 15/16 implementation guidance complete
- [ ] ADR-001/002 infrastructure prerequisites documented
- [ ] File added to KB before C.4
