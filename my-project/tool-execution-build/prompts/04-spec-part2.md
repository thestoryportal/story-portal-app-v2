# Session: Tool Execution Layer -- Specification Part 2

## Objective
Write specification Sections 6-10: Integration, Reliability, Security, Observability, Configuration.

Continue integrating ALL gap analysis findings.

## Source Files in Project Knowledge
1. `tool-execution-spec-part1.md`
2. `tool-execution-research-findings.md`
3. `tool-execution-gap-analysis.md`
4. `agentic-data-layer-master-specification-v4.0-final-ASCII.md`
5. `phase-15-document-management-specification-v1.0-ASCII.md`
6. `phase-16-session-orchestration-specification-v1.0-ASCII.md`

## Checkpoint Protocol

**Exchange limit:** 8 exchanges for this session

**Checkpoint triggers:**
- After each section (5 sections total)
- When context estimate exceeds 60%

**At each checkpoint:**
1. Save completed sections to file
2. Report: Section [X] complete, [Y] remaining
3. PAUSE - wait for "Continue"

## Gap Integration Tracking
Continue the gap tracking table from Part 1:
| Gap ID | Description | Priority | Section | How Addressed |

## Sections to Write

### Section 6: Integration with Data Layer
- 6.1 Relationship Model (provider vs consumer for each touchpoint)
- 6.2 Agent Identity Integration (DID resolution for tool invocations)
- 6.3 Event Integration (tool.* events -> Event Store)
- 6.4 ABAC Integration (Permission Checker -> ABAC Engine)
- 6.5 Context Injector Integration (credential and config retrieval)
- 6.6 MCP Tool Adapter Integration (Phase 13 patterns)
- 6.7 Phase 15 Document Bridge Integration
  - MCP stdio transport (per ADR-001)
  - Document query caching strategy
  - Error handling for MCP unavailability
- 6.8 Phase 16 State Bridge Integration
  - Checkpoint creation patterns
  - State serialization format
  - Checkpoint cleanup policies


---

### Section 7: Reliability and Scalability
- 7.1 Availability Targets (SLOs for tool invocation latency)
- 7.2 Scaling Model (horizontal scaling for Tool Executor instances)
- 7.3 High Availability Patterns
  - Circuit breaker failover
  - Tool registry replication (PostgreSQL HA)
  - Redis cluster for circuit breaker state
  - Stateless executor design
- 7.4 Capacity Planning (concurrent tool invocations, external API limits)
- 7.5 Performance Budgets (latency targets per component)
- 7.6 Long-Running Operations (Q2/Q6 resolution)
  - Phase 16 checkpoint integration
  - Async execution patterns
  - Progress callbacks
  - Resume after failure


---

### Section 8: Security
- 8.1 Security Architecture (trust boundaries diagram including nested sandbox, MCP bridges)
- 8.2 Authentication (DID-based caller validation)
- 8.3 Authorization (ABAC integration for tool access)
- 8.4 Secrets Management
  - External API credential storage (per ADR-002: PostgreSQL encrypted)
  - Credential rotation (Q3 resolution)
  - Credential injection into tool sandbox
  - MCP service credentials
- 8.5 Network Security (tool-specific network allowlists)
- 8.6 Threat Model (STRIDE analysis for tool execution)
  - Spoofing: Tool invocation identity
  - Tampering: Tool result manipulation, checkpoint tampering
  - Repudiation: Audit trail integrity
  - Information Disclosure: Credential leakage, document context leakage
  - Denial of Service: Tool exhaustion attacks, MCP service overload
  - Elevation of Privilege: Sandbox escape, MCP privilege escalation


---

### Section 9: Observability
- 9.1 Metrics (Prometheus format)
  - tool_invocations_total (by tool_id, status)
  - tool_execution_duration_seconds (histogram)
  - circuit_breaker_state (by external_service)
  - external_api_requests_total (by service, status)
  - permission_checks_total (by result)
  - mcp_document_queries_total (Phase 15)
  - mcp_checkpoint_operations_total (Phase 16)
- 9.2 Logging (structured log format for tool invocations)
- 9.3 Tracing (OpenTelemetry spans)
  - tool.invoke span with attributes
  - external_api.call child span
  - permission.check child span
  - mcp.document_query child span (Phase 15)
  - mcp.checkpoint child span (Phase 16)
- 9.4 Alerting (alert definitions)
  - High tool failure rate
  - Circuit breaker open
  - External service degradation
  - MCP service unavailable
- 9.5 Dashboards (Grafana dashboard specs)


---

### Section 10: Configuration
- 10.1 Configuration Hierarchy
  - Global tool defaults
  - Per-tool configuration
  - Per-external-service configuration
  - MCP bridge configuration
- 10.2 Configuration Schemas
  - Tool registry configuration (PostgreSQL connection per ADR-002)
  - Circuit breaker thresholds (Redis connection per ADR-002)
  - Rate limit policies
  - MCP transport configuration (stdio per ADR-001)
- 10.3 Environment Variables
- 10.4 Feature Flags
  - Enable/disable individual tools
  - Circuit breaker bypass (emergency)
  - Rate limit override
  - Phase 15 document context (enable/disable)
  - Phase 16 checkpointing (enable/disable)
- 10.5 Hot Reload Capability (tool definitions, circuit breaker config)

## Gap Tracking Table
Update with gaps addressed in this part:
| Gap ID | Description | Priority | Section | How Addressed |

## Output
Save as: `tool-execution-spec-part2.md`

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-spec-part2.md` | Sections 6-10 for merge |

### Verification
- [ ] All 5 sections complete
- [ ] Phase 15/16 integration fully specified
- [ ] ADR-001/002 reflected in configuration
- [ ] Gap tracking table updated
- [ ] File added to KB before C.3
