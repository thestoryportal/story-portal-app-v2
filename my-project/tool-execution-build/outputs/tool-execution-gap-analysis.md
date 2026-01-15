# Tool Execution Layer - Gap Analysis

**Version:** 1.0
**Date:** 2026-01-14
**Session:** 02 - Gap Analysis
**Status:** Complete

---

## Executive Summary

This gap analysis evaluates the Tool Execution Layer research findings against the architectural requirements for nested sandboxing (BC-1), integration interface (BC-2), Phase 15 Document Bridge, and Phase 16 State Bridge integrations.

**Key Findings:**
- **26 research findings** from Session 01 assessed for applicability
- **Critical gaps identified:** 7
- **High-priority gaps:** 9
- **Medium-priority gaps:** 5
- **All gaps will be integrated** into specification (prioritization for ordering only)

**Integration Readiness:**
- BC-1 (Nested Sandbox): **READY** - Kubernetes Agent Sandbox provides standard
- BC-2 (tool.invoke() Interface): **READY** - Patterns identified
- Phase 15 (Document Bridge): **PARTIAL** - MCP patterns ready, caching strategy needed
- Phase 16 (State Bridge): **PARTIAL** - Checkpoint patterns ready, granularity decision needed

---

## Task 1: Classification of Research Findings

| Finding ID | Finding Name | Classification | Target Component | Notes |
|------------|--------------|----------------|------------------|-------|
| R-01 | Protocol-Agnostic Tool Registry | APPLICABLE | Tool Registry | Core capability, direct application |
| R-02 | LangGraph BigTool - Large-Scale Tool Management | APPLICABLE | Tool Registry | Scaling pattern for 1000+ tools |
| R-03 | MCP Tool Discovery via JSON-RPC | APPLICABLE | Tool Registry, MCP Bridge | Critical for Phase 15/16 |
| R-04 | OpenAI vs Anthropic Tool Schema Patterns | OTHER LAYER | N/A | Integration Layer (L11) responsibility |
| R-05 | Kubernetes Agent Sandbox Standard | APPLICABLE | Execution Sandbox | BC-1 implementation standard |
| R-06 | gVisor vs Firecracker Trade-offs | APPLICABLE | Execution Sandbox | Technology choice guidance |
| R-07 | Filesystem and Network Isolation Requirements | APPLICABLE | Execution Sandbox | Security requirements |
| R-08 | Lambda Tenant Isolation Mode | APPLICABLE | Execution Sandbox | Multi-tenancy pattern |
| R-09 | Automated Credential Rotation with JWKS | APPLICABLE | Credential Manager | Runtime security |
| R-10 | Centralized Rate Limiting with Redis | APPLICABLE | External API Manager | ADR-002 aligned |
| R-11 | Exponential Backoff with Jitter | APPLICABLE | External API Manager | Resilience pattern |
| R-12 | Runtime Secret Injection | APPLICABLE | Credential Manager | Zero-trust security |
| R-13 | Resilience4j State Machine | APPLICABLE | Circuit Breaker Controller | Technology choice |
| R-14 | Health-Based vs Count-Based Circuit Decisions | APPLICABLE | Circuit Breaker Controller | Pattern guidance |
| R-15 | AI Agents as New Insider Threat | APPLICABLE | Permission Checker | Security model driver |
| R-16 | Capability-Based Security for Distributed Systems | APPLICABLE | Permission Checker | Authorization pattern |
| R-17 | Tool Invocation Audit Logging for Compliance | APPLICABLE | Audit Logger | Regulatory requirement |
| R-18 | MCP Donation to Linux Foundation | APPLICABLE | MCP Bridge | Standard validation |
| R-19 | Tool Versioning - 60% of Production Failures | APPLICABLE | Tool Registry | Critical requirement |
| R-20 | Human-in-the-Loop Workflows | APPLICABLE | Tool Orchestrator | Approval flow pattern |
| R-21 | MCP stdio Transport with JSON-RPC 2.0 | APPLICABLE | MCP Bridge | ADR-001 aligned |
| R-22 | MCP Capability Negotiation | APPLICABLE | MCP Bridge | Discovery protocol |
| R-23 | MCP Tool State Persistence | APPLICABLE | MCP Bridge, State Bridge | Phase 16 integration |
| R-24 | LangGraph Redis Checkpoint 0.1.0 Redesign | APPLICABLE | State Checkpointer | Phase 16 implementation |
| R-25 | PostgreSQL for Durable Checkpoints | APPLICABLE | State Checkpointer | ADR-002 aligned |
| R-26 | Stream Processing Checkpoint Pattern | APPLICABLE | State Checkpointer | Long-running tool pattern |

**Classification Summary:**
- APPLICABLE: 25 findings (96%)
- OTHER LAYER: 1 finding (4%)
- OUT OF SCOPE: 0 findings
- DEFER: 0 findings

**Conclusion:** Research findings have excellent alignment with Tool Execution Layer responsibilities.

---

## Task 2: Data Layer Integration Requirements

| Integration Point | Direction | Data Layer Component | Tool Execution Usage | Interface Type | Priority |
|-------------------|-----------|---------------------|----------------------|----------------|----------|
| Event Publishing | L03 -> L01 | Event Store | Publish tool.invoked, tool.succeeded, tool.failed, tool.timeout events | Async Event Bus | Critical |
| Permission Query | L03 -> L01 | ABAC Engine | Validate agent capabilities for tool access (filesystem, network, credentials) | Sync API Call | Critical |
| Context Retrieval | L03 <- L01 | Context Injector | Retrieve tool-specific credentials, config, and context from agent session | Sync API Call | Critical |
| Audit Logging | L03 -> L01 | Audit Log | Compliance records for all tool invocations (parameters sanitized for PII) | Async Stream (Kafka) | Critical |
| Semantic Tool Search | L03 -> L01 | Vector Search (pgvector) | Query tool registry by semantic similarity of capability descriptions | Sync API Call | High |
| Tool Capability Storage | L03 -> L01 | PostgreSQL | Persist tool registry entries with capability manifests | Direct DB Access | High |
| Circuit Breaker State | L03 <-> L01 | Redis | Read/write circuit breaker state for distributed coordination | Direct Cache Access | High |
| Rate Limit Counters | L03 <-> L01 | Redis | Increment/decrement rate limit tokens for external APIs | Direct Cache Access | High |
| Hot Checkpoint Storage | L03 -> L01 | Redis | Store active tool execution checkpoints for fast retrieval | Direct Cache Access | High |
| Cold Checkpoint Storage | L03 -> L01 | PostgreSQL | Store completed tool execution checkpoints for audit/recovery | Direct DB Access | Medium |
| MCP Server Registry | L03 <-> L01 | PostgreSQL | Track active MCP servers, capabilities, lifecycle state | Direct DB Access | High |

### Integration Pattern Details

#### 1. Event Publishing (Async Event Bus)
**Pattern:** Publish-Subscribe via Apache Kafka or equivalent
**Payload:** CloudEvents 1.0 format with tool invocation metadata
**Schema:**
```
{
  "specversion": "1.0",
  "type": "ai.agent.tool.invoked",
  "source": "tool-execution-layer",
  "id": "<invocation_id>",
  "time": "2026-01-14T10:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "agent_id": "<agent_did>",
    "tenant_id": "<tenant_id>",
    "tool_id": "<tool_id>",
    "tool_version": "1.2.0",
    "parameters": {/* sanitized */}
  }
}
```
**Reliability:** At-least-once delivery, idempotent consumers

#### 2. Permission Query (Sync API)
**Pattern:** REST API with capability tokens
**Endpoint:** `POST /api/v1/abac/check-permission`
**Request:**
```
{
  "agent_id": "<agent_did>",
  "resource_type": "tool",
  "resource_id": "<tool_id>",
  "action": "execute",
  "context": {
    "filesystem_paths": ["/tmp/workspace"],
    "network_endpoints": ["https://api.example.com"],
    "credentials": ["aws_s3_read"]
  }
}
```
**Response:** `{"allowed": true, "reason": "policy_xyz"}`
**Timeout:** 500ms (fast fail for real-time tool invocation)

#### 3. Context Retrieval (Sync API)
**Pattern:** REST API with agent session context
**Endpoint:** `GET /api/v1/context/agent/{agent_id}/tool/{tool_id}`
**Response:**
```
{
  "credentials": {
    "aws_access_key_id_ref": "vault://secrets/aws/access_key",
    "api_token_ref": "vault://secrets/external_api/token"
  },
  "config": {
    "timeout": 30000,
    "retry_max_attempts": 3,
    "rate_limit_per_minute": 60
  },
  "session_context": {
    "user_id": "user_123",
    "project_id": "project_456"
  }
}
```
**Caching:** Redis cache with 5-minute TTL

#### 4. Audit Logging (Async Stream)
**Pattern:** Kafka stream to audit data lake
**Topic:** `tool-execution-audit`
**Partition Key:** `tenant_id` (tenant isolation)
**Retention:** 90 days in Kafka, 7 years in cold storage (S3 Glacier)
**Schema:** See Event Publishing, plus `result`, `duration_ms`, `error`

---

## Task 3: Agent Runtime Integration Requirements (BC-1 Nested Sandbox)

| Interface | L02 Provides | L03 Consumes | Data Type | Validation |
|-----------|--------------|--------------|-----------|------------|
| Sandbox Context | Agent DID, tenant ID, parent sandbox ID | Parent sandbox for tool isolation | String IDs | L03 validates agent DID exists |
| Resource Bounds | CPU limit (millicores), memory limit (MB), time limit (seconds) | Inherited limits for tool execution | Integers | L03 enforces tool limits <= agent limits |
| Network Policy | Allowed CIDR ranges, DNS resolution policy | Base network restrictions for tools | NetworkPolicy CRD | L03 adds tool-specific restrictions (stricter) |
| Filesystem Policy | Allowed mount paths, read-only vs read-write | Base filesystem access for tools | Volume mounts | L03 adds tool-specific paths (subset) |
| Tool Invocation API | `tool.invoke()` method | Execute tool on agent's behalf | JSON-RPC call | L03 validates call signature |
| Identity Propagation | Agent DID, user DID, session ID | Track identity across tool boundary | JWT token | L03 validates token signature |

### BC-1 Nested Sandbox Design

```
+--------------------------------------------------+
|  L02: Agent Runtime Layer                        |
|  +--------------------------------------------+  |
|  | Agent Sandbox (Kubernetes Sandbox CRD)     |  |
|  | - Network Policy: Allow api.example.com    |  |
|  | - CPU Limit: 2000m, Memory: 4096MB         |  |
|  | - Filesystem: /workspace (RW), /data (RO)  |  |
|  |                                            |  |
|  |  +--------------------------------------+  |  |
|  |  | L03: Tool Execution Layer            |  |
|  |  | +----------------------------------+ |  |
|  |  | | Tool Sandbox (nested)            | |  |
|  |  | | - Network: api.example.com:443   | |  |
|  |  | |   (subset of parent)             | |  |
|  |  | | - CPU: 500m, Memory: 1024MB      | |  |
|  |  | |   (< parent limits)              | |  |
|  |  | | - Filesystem: /workspace/tool1   | |  |
|  |  | |   (subdirectory of parent)       | |  |
|  |  | +----------------------------------+ |  |
|  |  +--------------------------------------+  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
```

### BC-1 Interface Contract

**L02 -> L03 Invocation:**
```typescript
interface ToolInvokeRequest {
  agent_context: {
    agent_did: string;
    tenant_id: string;
    user_did: string;
    session_id: string;
    parent_sandbox_id: string;
  };
  resource_limits: {
    cpu_millicore_limit: number;
    memory_mb_limit: number;
    timeout_seconds: number;
  };
  network_policy: {
    allowed_hosts: string[];
    allowed_ports: number[];
    dns_servers: string[];
  };
  filesystem_policy: {
    mounts: Array<{
      path: string;
      mode: "ro" | "rw";
    }>;
  };
  tool_request: {
    tool_id: string;
    tool_version: string;
    parameters: Record<string, any>;
    invocation_id: string;
  };
}
```

**L03 -> L02 Response:**
```typescript
interface ToolInvokeResponse {
  invocation_id: string;
  status: "success" | "error" | "timeout" | "permission_denied";
  result?: any;
  error?: {
    code: string;
    message: string;
    details: Record<string, any>;
  };
  execution_metadata: {
    duration_ms: number;
    cpu_used_millicore_seconds: number;
    memory_peak_mb: number;
    network_bytes_sent: number;
    network_bytes_received: number;
  };
  checkpoint_ref?: string; // For long-running tools
}
```

### Resource Limit Enforcement

| Limit Type | L02 Allocation | L03 Sub-Allocation | Enforcement |
|------------|----------------|-------------------|-------------|
| CPU | 2000 millicores | 500m per tool (max 4 concurrent tools) | cgroup CPU quota |
| Memory | 4096 MB | 1024 MB per tool (max 4 concurrent tools) | cgroup memory limit |
| Timeout | 900 seconds (15 min) | Tool-specific (default 30s, max 900s) | Process kill after timeout |
| Network | 100 Mbps | Per-tool bandwidth shaping | tc qdisc |
| Filesystem | 10 GB | Tool-specific sub-directories | Disk quota |

---

## Task 4: Phase 15 Document Management Integration

| Integration Point | Direction | MCP Tool | L03 Usage | Latency SLA | Caching Strategy |
|-------------------|-----------|----------|-----------|-------------|------------------|
| Document Query | L03 -> MCP | `get_source_of_truth` | Retrieve authoritative content during tool execution | < 200ms | Redis cache (5-min TTL) |
| Document Search | L03 -> MCP | `search_documents` | Find relevant docs for tool context | < 500ms | No cache (semantic search) |
| Overlap Detection | L03 -> MCP | `find_overlaps` | Validate tool inputs against corpus | < 1s | No cache (validation check) |
| Document Metadata | L03 -> MCP | `get_document_metadata` | Audit trail for document-dependent outputs | < 100ms | Redis cache (10-min TTL) |
| Document Version | L03 -> MCP | `get_document_version` | Pin specific document version during long-running tool | N/A | Immutable (no cache needed) |
| Document Ingest | L03 -> MCP | `ingest_document` | Tools can create documents as output | < 2s | Invalidate cache on write |

### Document Bridge Design

#### Architecture Pattern
```
+--------------------+
| L03 Tool Execution |
+--------------------+
         |
         | stdio (JSON-RPC)
         v
+--------------------+
| MCP Client         |
| (Document Bridge)  |
+--------------------+
         |
         | stdin/stdout pipes
         v
+--------------------+
| MCP Server         |
| (document-         |
|  consolidator)     |
+--------------------+
         |
         | SQL queries
         v
+--------------------+
| PostgreSQL         |
| (document store)   |
+--------------------+
```

#### Design Questions - Answered

**Q1: Caching strategy for repeated queries?**
**Answer:** Two-tier caching:
- **Tier 1 (Hot):** Redis cache for `get_source_of_truth` and `get_document_metadata` with 5-10 minute TTL
- **Tier 2 (Warm):** Local process cache for document versions (immutable, cache until process restart)
- **Cache Invalidation:** Write operations (`ingest_document`, `deprecate_document`) send invalidation events via Redis pub/sub
- **Cache Key Structure:** `doc:cache:{operation}:{doc_id}:{version}` for deterministic invalidation

**Q2: Error handling for MCP service unavailability?**
**Answer:** Three-tier fallback:
1. **Primary:** MCP server via stdio
2. **Fallback 1:** Cached document content from Redis (stale data acceptable for reads)
3. **Fallback 2:** Direct PostgreSQL read (bypass MCP, limited to simple queries)
4. **Failure Mode:** If all fail, tool execution returns error with `document_unavailable` code, agent retries or escalates

**Q3: Document version pinning during long-running tools?**
**Answer:** Explicit version pinning:
- Tool invocation specifies `document_version` parameter (optional, defaults to `latest`)
- Checkpoint includes `document_versions_map` (doc_id -> version used)
- On tool resume, same document versions restored from checkpoint
- If pinned version deprecated, tool receives warning but continues with pinned version
- Prevents "moving target" problem where doc changes mid-execution

### MCP Bridge - Document Context Injection Pattern

```typescript
// Tool declares document dependency in manifest
{
  "tool_id": "analyze_requirements",
  "document_dependencies": [
    {
      "document_pattern": "spec:requirements-*",
      "access_mode": "read",
      "version_pinning": true
    }
  ]
}

// L03 injects document context before tool execution
async function injectDocumentContext(toolRequest: ToolRequest): Promise<EnrichedContext> {
  const documents = [];
  for (const dep of tool.manifest.document_dependencies) {
    // Query MCP server
    const result = await mcpBridge.call("get_source_of_truth", {
      query: dep.document_pattern,
      version: dep.version_pinning ? "pin_latest" : "latest"
    });

    // Cache for duration of tool execution
    if (dep.version_pinning) {
      checkpoint.document_versions[dep.document_pattern] = result.version;
    }

    documents.push(result);
  }

  // Make available to tool via environment
  return {
    ...toolRequest,
    context: {
      documents: documents,
      document_refs: documents.map(d => d.uri)
    }
  };
}
```

---

## Task 5: Phase 16 Session Orchestration Integration

| Integration Point | Direction | MCP Tool | L03 Usage | Granularity | Storage |
|-------------------|-----------|----------|-----------|-------------|---------|
| Checkpoint Creation | L03 -> MCP | `save_context_snapshot` | Persist tool progress during execution | Continuous (30s intervals) | Redis (hot) |
| Named Checkpoints | L03 -> MCP | `create_checkpoint` | Named recovery points at key milestones | Event-based (tool milestones) | PostgreSQL (cold) |
| State Restoration | L03 <- MCP | `rollback_to` | Resume interrupted tool execution | Load from checkpoint | Redis or PostgreSQL |
| Session Context | L03 <- MCP | `get_unified_context` | Access agent session state for tool context | On-demand | Redis (cached) |
| Task Switch | L03 -> MCP | `switch_task` | Save current tool state, load new tool context | Per-tool invocation | PostgreSQL |
| Conflict Detection | L03 -> MCP | `detect_conflicts` | Identify state conflicts in concurrent tools | Pre-execution validation | PostgreSQL (metadata) |

### State Bridge Design

#### Architecture Pattern
```
+--------------------+
| L03 Tool Execution |
| - Tool Orchestrator|
| - Checkpointer     |
+--------------------+
         |
         | stdio (JSON-RPC)
         v
+--------------------+
| MCP Client         |
| (State Bridge)     |
+--------------------+
         |
         | stdin/stdout pipes
         v
+--------------------+
| MCP Server         |
| (context-          |
|  orchestrator)     |
+--------------------+
         |
         | SQL + Redis
         v
+--------------------+     +--------------------+
| PostgreSQL         | <-> | Redis              |
| (cold checkpoints) |     | (hot checkpoints)  |
+--------------------+     +--------------------+
```

#### Design Questions - Answered

**Q1: Checkpoint granularity (per-phase vs continuous)?**
**Answer:** Hybrid approach with three granularities:
1. **Micro-checkpoints (continuous):** Every 30 seconds for long-running tools (> 1 min), stored in Redis, TTL 1 hour
2. **Macro-checkpoints (event-based):** At tool milestones (e.g., "file parsed", "API call succeeded"), stored in PostgreSQL, retained 90 days
3. **Named checkpoints (manual):** Explicit checkpoints created by tool code for critical recovery points, stored in PostgreSQL, retained indefinitely

**Rationale:**
- Micro-checkpoints enable fine-grained resume (minimize reprocessing)
- Macro-checkpoints provide audit trail (compliance, debugging)
- Named checkpoints support A/B testing, rollback scenarios

**Q2: State serialization format?**
**Answer:** JSON with binary blob support:
- **Primary Format:** JSON for structured state (tool parameters, progress counters, metadata)
- **Binary Blobs:** Base64-encoded for small binaries (< 1 MB), S3 references for large binaries (>= 1 MB)
- **Schema Versioning:** Each checkpoint includes `schema_version` field for forward/backward compatibility
- **Compression:** gzip compression for checkpoints > 10 KB

```typescript
interface ToolCheckpoint {
  schema_version: "1.0";
  invocation_id: string;
  tool_id: string;
  tool_version: string;
  checkpoint_type: "micro" | "macro" | "named";
  timestamp: string; // ISO 8601
  state: {
    progress_percent: number;
    phase: string;
    counters: Record<string, number>;
    custom_state: Record<string, any>;
  };
  binary_refs?: Array<{
    key: string;
    storage: "inline" | "s3";
    uri: string;
  }>;
  document_versions?: Record<string, string>; // Phase 15 integration
  parent_checkpoint_id?: string; // For delta encoding
}
```

**Q3: Cleanup policy for completed tool checkpoints?**
**Answer:** Tiered retention policy:
- **Micro-checkpoints (Redis):** TTL 1 hour, deleted on tool completion or timeout
- **Macro-checkpoints (PostgreSQL):** Retained 90 days, then archived to S3 Glacier (7 years)
- **Named checkpoints (PostgreSQL):** Retained indefinitely unless explicitly deleted
- **Failed execution checkpoints:** Retained 30 days for debugging, then deleted
- **Cleanup Job:** Daily background job runs at 2 AM UTC, archives/deletes expired checkpoints

### MCP Bridge - State Persistence Pattern

```typescript
// Tool checkpoint during execution
async function checkpointToolProgress(
  invocationId: string,
  state: ToolState,
  type: "micro" | "macro" | "named"
): Promise<string> {
  // Serialize state to checkpoint format
  const checkpoint: ToolCheckpoint = {
    schema_version: "1.0",
    invocation_id: invocationId,
    tool_id: state.tool_id,
    tool_version: state.tool_version,
    checkpoint_type: type,
    timestamp: new Date().toISOString(),
    state: {
      progress_percent: state.progress,
      phase: state.current_phase,
      counters: state.counters,
      custom_state: state.custom
    }
  };

  // Call MCP server based on checkpoint type
  if (type === "micro") {
    // Hot path: Redis via context-orchestrator
    await mcpBridge.call("save_context_snapshot", {
      taskId: invocationId,
      updates: checkpoint,
      syncToFile: false // Skip file sync for micro-checkpoints
    });
  } else {
    // Cold path: PostgreSQL via context-orchestrator
    await mcpBridge.call("create_checkpoint", {
      taskId: invocationId,
      label: `${state.tool_id}-${state.current_phase}`,
      checkpointType: type,
      description: `Tool checkpoint at phase ${state.current_phase}`
    });
  }

  return checkpoint.timestamp; // checkpoint ID
}

// Tool resume from checkpoint
async function resumeToolFromCheckpoint(
  invocationId: string,
  checkpointId?: string
): Promise<ToolState> {
  // Retrieve checkpoint from MCP server
  const context = await mcpBridge.call("get_unified_context", {
    taskId: invocationId,
    includeVersionHistory: true
  });

  // If specific checkpoint requested, rollback
  if (checkpointId) {
    await mcpBridge.call("rollback_to", {
      taskId: invocationId,
      target: { type: "checkpoint", checkpointId }
    });
  }

  // Deserialize state
  return {
    tool_id: context.immediateContext.tool_id,
    progress: context.immediateContext.state.progress_percent,
    current_phase: context.immediateContext.state.phase,
    counters: context.immediateContext.state.counters,
    custom: context.immediateContext.state.custom_state
  };
}
```

---

## Task 6: Dependent Layer Requirements (BC-2 Interface)

| Consuming Layer | Required Interface | Direction | Data Exchanged | SLA | Error Handling |
|-----------------|-------------------|-----------|----------------|-----|----------------|
| L11 Integration | `tool.invoke()` | L11 -> L03 | ToolInvokeRequest -> ToolInvokeResponse | < 100ms overhead | Structured errors with codes |
| L11 Integration | `tool.list()` | L11 -> L03 | Query params -> Tool manifest list | < 50ms | Empty list on error |
| L11 Integration | `tool.status()` | L11 -> L03 | invocation_id -> Execution status | < 10ms | Status unknown on error |
| L11 Integration | `tool.cancel()` | L11 -> L03 | invocation_id -> Cancellation ack | < 50ms | Idempotent (no-op if already done) |

### BC-2 Interface Contract (Complete with Phase 15/16 Fields)

```typescript
// ============================================
// PRIMARY INTERFACE: tool.invoke()
// ============================================

interface ToolInvokeRequest {
  // Core tool identification
  tool_id: string;
  tool_version: string; // Semantic version (e.g., "1.2.0")
  invocation_id: string; // Unique invocation ID (UUID)

  // Agent context (from L02)
  agent_context: {
    agent_did: string; // Decentralized Identifier
    tenant_id: string; // Multi-tenancy isolation
    user_did?: string; // End user (if applicable)
    session_id: string; // Session for context tracking
  };

  // Tool parameters (validated against tool manifest schema)
  parameters: Record<string, any>;

  // Resource limits (inherited from L02, sub-allocated by L03)
  resource_limits?: {
    cpu_millicore_limit?: number; // Default: tool manifest default
    memory_mb_limit?: number; // Default: tool manifest default
    timeout_seconds?: number; // Default: tool manifest default
    network_bandwidth_mbps?: number; // Optional bandwidth shaping
  };

  // **NEW: Phase 15 - Document Context**
  document_context?: {
    document_refs?: string[]; // URIs to documents (e.g., "doc://spec-v1.0")
    version_pinning?: boolean; // Pin document versions for consistency
    query?: string; // Semantic search query for document retrieval
  };

  // **NEW: Phase 16 - State Checkpoint**
  checkpoint_config?: {
    enable_checkpointing?: boolean; // Default: true for long-running tools
    checkpoint_interval_seconds?: number; // Default: 30
    resume_from_checkpoint_id?: string; // Resume previous invocation
  };

  // Execution options
  execution_options?: {
    async_mode?: boolean; // Default: false (synchronous)
    priority?: "low" | "normal" | "high"; // Default: "normal"
    idempotency_key?: string; // Prevent duplicate invocations
    require_approval?: boolean; // Human-in-the-loop approval
  };
}

interface ToolInvokeResponse {
  invocation_id: string;
  status: ToolInvocationStatus;

  // Success response
  result?: any; // Tool-specific result (validated against manifest schema)

  // Error response
  error?: {
    code: ToolErrorCode;
    message: string;
    details?: Record<string, any>;
    retryable: boolean;
  };

  // Execution metadata
  execution_metadata: {
    duration_ms: number;
    started_at: string; // ISO 8601
    completed_at?: string; // ISO 8601

    // Resource usage
    cpu_used_millicore_seconds: number;
    memory_peak_mb: number;
    network_bytes_sent: number;
    network_bytes_received: number;

    // **NEW: Phase 15 - Document Access**
    documents_accessed?: Array<{
      document_id: string;
      document_version: string;
      access_count: number;
    }>;

    // **NEW: Phase 16 - Checkpoints Created**
    checkpoints_created?: Array<{
      checkpoint_id: string;
      checkpoint_type: "micro" | "macro" | "named";
      timestamp: string;
    }>;
  };

  // **NEW: Phase 16 - Checkpoint Reference (for async/long-running)**
  checkpoint_ref?: string; // ID to resume this invocation

  // Async mode tracking
  polling_info?: {
    status_url: string; // URL to poll for status
    estimated_completion_seconds?: number;
  };
}

enum ToolInvocationStatus {
  PENDING = "pending", // Queued, not yet started
  RUNNING = "running", // Currently executing
  SUCCESS = "success", // Completed successfully
  ERROR = "error", // Failed with error
  TIMEOUT = "timeout", // Exceeded time limit
  CANCELLED = "cancelled", // Cancelled by user/system
  PERMISSION_DENIED = "permission_denied", // ABAC check failed
  PENDING_APPROVAL = "pending_approval", // Awaiting HITL approval
}

enum ToolErrorCode {
  // Client errors (4xx-style)
  INVALID_PARAMETERS = "invalid_parameters",
  TOOL_NOT_FOUND = "tool_not_found",
  TOOL_VERSION_NOT_FOUND = "tool_version_not_found",
  PERMISSION_DENIED = "permission_denied",
  RATE_LIMIT_EXCEEDED = "rate_limit_exceeded",
  IDEMPOTENCY_CONFLICT = "idempotency_conflict",

  // Server errors (5xx-style)
  TOOL_EXECUTION_ERROR = "tool_execution_error",
  SANDBOX_FAILURE = "sandbox_failure",
  EXTERNAL_API_ERROR = "external_api_error",
  CIRCUIT_BREAKER_OPEN = "circuit_breaker_open",
  TIMEOUT = "timeout",
  RESOURCE_EXHAUSTED = "resource_exhausted",

  // **NEW: Phase 15 Errors**
  DOCUMENT_NOT_FOUND = "document_not_found",
  DOCUMENT_UNAVAILABLE = "document_unavailable",
  DOCUMENT_VERSION_CONFLICT = "document_version_conflict",

  // **NEW: Phase 16 Errors**
  CHECKPOINT_FAILED = "checkpoint_failed",
  RESUME_FAILED = "resume_failed",
  STATE_CONFLICT = "state_conflict",

  // Generic fallback
  INTERNAL_ERROR = "internal_error",
}

// ============================================
// SECONDARY INTERFACES
// ============================================

interface ToolListRequest {
  agent_context: {
    agent_did: string;
    tenant_id: string;
  };
  filters?: {
    category?: string; // e.g., "data_access", "computation", "external_api"
    capability_query?: string; // Semantic search query
    tags?: string[];
  };
  pagination?: {
    page: number;
    page_size: number; // Default: 50, max: 200
  };
}

interface ToolListResponse {
  tools: Array<{
    tool_id: string;
    tool_name: string;
    description: string;
    category: string;
    versions: string[]; // Available versions
    latest_version: string;
    tags: string[];
    requires_approval: boolean; // HITL flag
  }>;
  pagination: {
    total_count: number;
    page: number;
    page_size: number;
  };
}

interface ToolStatusRequest {
  invocation_id: string;
  agent_context: {
    agent_did: string;
    tenant_id: string;
  };
}

interface ToolStatusResponse {
  invocation_id: string;
  status: ToolInvocationStatus;
  progress_percent?: number; // For long-running tools
  current_phase?: string; // E.g., "parsing", "processing", "finalizing"
  error?: ToolInvokeResponse["error"];

  // **NEW: Phase 16 - Latest Checkpoint**
  latest_checkpoint?: {
    checkpoint_id: string;
    timestamp: string;
  };
}

interface ToolCancelRequest {
  invocation_id: string;
  agent_context: {
    agent_did: string;
    tenant_id: string;
  };
  reason?: string; // Optional cancellation reason
}

interface ToolCancelResponse {
  invocation_id: string;
  cancelled: boolean;
  message: string; // E.g., "Cancellation in progress" or "Already completed"
}
```

### BC-2 Interface Usage Example

```typescript
// L11 invokes tool on L03
const request: ToolInvokeRequest = {
  tool_id: "analyze_code",
  tool_version: "2.1.0",
  invocation_id: "inv_abc123",
  agent_context: {
    agent_did: "did:agent:xyz789",
    tenant_id: "tenant_acme",
    session_id: "sess_456"
  },
  parameters: {
    repository_url: "https://github.com/example/repo",
    analysis_type: "security"
  },
  document_context: {
    document_refs: ["doc://security-standards-v2.0"],
    version_pinning: true
  },
  checkpoint_config: {
    enable_checkpointing: true,
    checkpoint_interval_seconds: 60
  }
};

const response = await l03.tool.invoke(request);

if (response.status === "success") {
  console.log("Analysis results:", response.result);
  console.log("Documents accessed:", response.execution_metadata.documents_accessed);
} else if (response.status === "error") {
  console.error("Tool failed:", response.error.message);
  if (response.error.retryable) {
    // Retry logic
  }
}
```

---

## Task 7: Component Coverage Analysis

| Component | Research Coverage | Gaps Identified | Gap Severity |
|-----------|------------------|-----------------|--------------|
| **Tool Registry** | ⭐⭐⭐⭐⭐ EXCELLENT | G-001: Tool capability manifest schema not fully defined | High |
| | R-01: Protocol-agnostic registry | G-002: Semantic versioning conflict resolution for parallel versions | Medium |
| | R-02: LangGraph BigTool scaling | G-003: Tool deprecation workflow and migration paths | Medium |
| | R-03: MCP tool discovery | |
| | R-19: Tool versioning patterns | |
| **Tool Executor** | ⭐⭐⭐⭐ GOOD | G-004: Async execution patterns for long-running tools (> 15 min) | High |
| | R-05: Kubernetes Agent Sandbox | G-005: Tool execution priority scheduling and resource allocation | Medium |
| | R-06: gVisor vs Firecracker | |
| | R-07: Filesystem/network isolation | |
| | R-08: Tenant isolation | |
| **Permission Checker** | ⭐⭐⭐⭐ GOOD | G-006: Capability token format and signing mechanism | Critical |
| | R-15: AI agents as insider threat | G-007: Permission cache invalidation on policy updates | High |
| | R-16: Capability-based security | |
| **External Adapter Manager** | ⭐⭐⭐⭐⭐ EXCELLENT | None identified | N/A |
| | R-09: Automated credential rotation | |
| | R-10: Rate limiting with Redis | |
| | R-11: Exponential backoff with jitter | |
| | R-12: Runtime secret injection | |
| **Circuit Breaker Controller** | ⭐⭐⭐⭐ GOOD | G-008: Circuit breaker transition notifications to dependent tools | Medium |
| | R-13: Resilience4j state machine | G-009: Half-open state testing strategy (canary vs all-or-nothing) | Medium |
| | R-14: Health-based vs count-based | |
| **Result Validator** | ⭐⭐ MINIMAL | G-010: Result validation schema definition and enforcement | Critical |
| | No dedicated findings | G-011: Type coercion and sanitization rules | High |
| | | G-012: Structured output validation against tool manifest | High |
| **Document Bridge (Phase 15)** | ⭐⭐⭐⭐ GOOD | G-013: Document access permission model (ABAC integration) | High |
| | R-03: MCP tool discovery | G-014: Bulk document retrieval optimization | Medium |
| | R-21: MCP stdio transport | |
| | R-22: MCP capability negotiation | |
| | R-23: MCP state persistence | |
| **State Bridge (Phase 16)** | ⭐⭐⭐⭐⭐ EXCELLENT | G-015: Checkpoint diff/delta encoding for large states | Medium |
| | R-23: MCP state persistence | G-016: Checkpoint compression threshold tuning | Low |
| | R-24: LangGraph Redis checkpoint | |
| | R-25: PostgreSQL durable checkpoints | |
| | R-26: Stream processing checkpoint | |
| **Audit Logger** | ⭐⭐⭐ ADEQUATE | G-017: PII sanitization rules for tool parameters | Critical |
| | R-17: Audit logging compliance | G-018: Audit log schema with CloudEvents 1.0 alignment | High |
| | | G-019: Real-time audit stream backpressure handling | Medium |
| **Tool Orchestrator** | ⭐⭐⭐ ADEQUATE | G-020: Multi-tool workflow orchestration (sequential, parallel, conditional) | High |
| | R-20: Human-in-the-loop workflows | G-021: Tool dependency graph resolution and cycle detection | Medium |
| | | G-022: HITL approval timeout and escalation policies | Medium |

**Coverage Summary:**
- **Excellent (5⭐):** 3 components (25%)
- **Good (4⭐):** 4 components (33%)
- **Adequate (3⭐):** 2 components (17%)
- **Minimal (2⭐):** 1 component (8%)
- **Total Gaps:** 22 identified

---

## Task 8: Open Question Resolution

| Question | Research Answer | Confidence | Section Target | Supporting Findings |
|----------|-----------------|------------|----------------|---------------------|
| Q1: Tool versioning (independent vs agent-tied)? | **Independent with agent compatibility matrix**. Tools use semantic versioning (major.minor.patch). Registry stores multiple versions concurrently. Agents specify required version range (e.g., "^2.1.0"). Breaking changes require new major version. | ⭐⭐⭐⭐⭐ High | Section 3: Tool Registry | R-19: Tool versioning causes 60% of failures, strict SemVer required |
| Q2: Long-running operations (>30s)? | **Checkpointing with async polling**. Tools > 30s use async mode. Micro-checkpoints every 30s to Redis. Macro-checkpoints at milestones to PostgreSQL. Client polls via `tool.status()`. Resume from checkpoint on failure. | ⭐⭐⭐⭐⭐ High | Section 7: Execution Management | R-24, R-25, R-26: LangGraph Redis + PostgreSQL checkpointing patterns |
| Q3: Credential rotation during invocations? | **Just-in-time retrieval, no rotation mid-execution**. Credentials fetched from vault at invocation start. Ephemeral credentials with lifespan = tool timeout. No mid-execution rotation (complexity vs benefit trade-off). Rotation happens between invocations. | ⭐⭐⭐⭐ Medium | Section 8: Security | R-09, R-12: Runtime secret injection, ephemeral credentials |
| Q4: MCP tool adapter pattern? | **stdio JSON-RPC bridge with capability negotiation**. L03 spawns MCP server process via PM2. Opens stdin/stdout pipes. Capability negotiation on startup. Tool invocation serialized to JSON-RPC request. Response deserialized from stdout. | ⭐⭐⭐⭐⭐ High | Section 6: MCP Integration | R-03, R-21, R-22: MCP specification, stdio transport, capability negotiation |
| Q5: Phase 15 document context caching? | **Two-tier caching: Redis (hot) + local (warm)**. `get_source_of_truth` cached in Redis (5-min TTL). Document versions cached locally (immutable). Cache invalidation via Redis pub/sub on writes. Direct PostgreSQL fallback on MCP unavailability. | ⭐⭐⭐⭐⭐ High | Section 6: MCP Integration | Task 4 design question answers |
| Q6: Phase 16 checkpoint granularity? | **Hybrid: micro (30s) + macro (event) + named (manual)**. Micro-checkpoints to Redis for fine-grained resume. Macro-checkpoints to PostgreSQL for audit trail. Named checkpoints for critical recovery points. Granularity configurable per tool manifest. | ⭐⭐⭐⭐⭐ High | Section 7: Execution Management | R-24, R-25, R-26 + Task 5 design question answers |
| Q7: Redis vs PostgreSQL for circuit breaker? | **Redis for state, PostgreSQL for config/history**. Circuit breaker state (open/closed, failure counts, timestamps) stored in Redis with TTL. Configuration (thresholds, timeouts) stored in PostgreSQL. State transitions logged to PostgreSQL for analytics. | ⭐⭐⭐⭐⭐ High | Section 3: Tool Registry & Section 5: Resilience | R-10, R-13: Redis for distributed state, ADR-002 alignment |

**Confidence Legend:**
- ⭐⭐⭐⭐⭐ High: Definitive answer from multiple research sources
- ⭐⭐⭐⭐ Medium: Strong answer with some assumptions
- ⭐⭐⭐ Low: Partial answer, gaps remain

**All questions resolved with high or medium confidence.** Specification writing can proceed with these decisions.

---

## Task 9: Gap Summary and Prioritization

### Critical Gaps (Security & Correctness)

| Gap ID | Description | Target Section | Remediation |
|--------|-------------|----------------|-------------|
| **G-006** | Capability token format and signing mechanism not specified | Section 8: Security | Define JWT structure with tool permissions, expiration, signature algorithm (RS256). Integrate with Data Layer's ABAC engine for token issuance. |
| **G-010** | Result validation schema definition and enforcement | Section 4: Tool Execution | Define JSON Schema validation for tool outputs. Enforce schema checks before returning results to agent. Type safety for structured outputs. |
| **G-017** | PII sanitization rules for tool parameters in audit logs | Section 9: Observability | Define regex patterns and field-based sanitization rules (e.g., redact email, SSN, credit card). Apply before audit log write. |

### High-Priority Gaps (Functionality & Integration)

| Gap ID | Description | Target Section | Remediation |
|--------|-------------|----------------|-------------|
| **G-001** | Tool capability manifest schema not fully defined | Section 3: Tool Registry | Extend manifest schema with fields: required_permissions (filesystem, network, credentials), result_schema (JSON Schema), timeout_default, retry_policy, circuit_breaker_config. |
| **G-004** | Async execution patterns for long-running tools (> 15 min) | Section 7: Execution Management | Define async invocation flow with polling. Specify job queue (Redis + Bull), worker pool architecture, timeout extension mechanism. |
| **G-007** | Permission cache invalidation on policy updates | Section 8: Security | Implement Redis pub/sub for policy change notifications. Subscribe to Data Layer's policy update events. Invalidate cached permissions on notification. |
| **G-011** | Type coercion and sanitization rules for tool inputs | Section 4: Tool Execution | Define type coercion rules (e.g., string -> number, ISO 8601 -> Date). Sanitization for SQL injection, XSS, command injection. |
| **G-012** | Structured output validation against tool manifest | Section 4: Tool Execution | Implement JSON Schema validator using AJV library. Validate tool output before returning. Return validation errors to agent. |
| **G-013** | Document access permission model (ABAC integration) | Section 6: MCP Integration | Define document permission schema: (agent_did, document_id, access_mode). Query Data Layer ABAC before MCP document retrieval. Cache permissions in Redis. |
| **G-018** | Audit log schema with CloudEvents 1.0 alignment | Section 9: Observability | Define CloudEvents-compliant schema for tool invocation events. Include extensions for tool-specific metadata. |
| **G-020** | Multi-tool workflow orchestration (sequential, parallel, conditional) | Section 7: Execution Management | Define workflow DSL (DAG-based). Implement workflow executor with task dependencies. Support parallel execution with resource limits. |

### Medium-Priority Gaps (Optimization & UX)

| Gap ID | Description | Target Section | Remediation |
|--------|-------------|----------------|-------------|
| **G-002** | Semantic versioning conflict resolution for parallel versions | Section 3: Tool Registry | Define conflict resolution strategy: pick highest compatible version within agent's version range. Log warnings for version constraints. |
| **G-003** | Tool deprecation workflow and migration paths | Section 3: Tool Registry | Define deprecation states: active, deprecated, sunset, removed. Provide migration guides in tool manifest. Warn agents using deprecated tools. |
| **G-005** | Tool execution priority scheduling and resource allocation | Section 7: Execution Management | Implement priority queue for tool invocations. Allocate resources based on priority (high-priority tools get more CPU/memory). Preemption for low-priority tools. |
| **G-008** | Circuit breaker transition notifications to dependent tools | Section 5: Resilience | Publish circuit breaker state change events to Redis pub/sub. Dependent tools subscribe and adjust behavior (e.g., skip fallback API if also open). |
| **G-009** | Half-open state testing strategy (canary vs all-or-nothing) | Section 5: Resilience | Implement canary testing: send N% of requests through half-open circuit. Gradually increase percentage if successful. Configurable per tool. |
| **G-014** | Bulk document retrieval optimization | Section 6: MCP Integration | Implement batch MCP requests for multiple documents. Reduce round-trips. Cache batch results in Redis. |
| **G-015** | Checkpoint diff/delta encoding for large states | Section 7: Execution Management | Implement delta encoding: checkpoint only stores state changes since last checkpoint. Reference parent_checkpoint_id. Reduces storage and I/O. |
| **G-019** | Real-time audit stream backpressure handling | Section 9: Observability | Implement backpressure detection: monitor Kafka lag, buffer sizes. Apply sampling (1% of logs) or buffering (in-memory queue) during overload. |
| **G-021** | Tool dependency graph resolution and cycle detection | Section 7: Execution Management | Build dependency graph from tool manifests. Detect cycles using DFS. Reject workflows with cycles. |
| **G-022** | HITL approval timeout and escalation policies | Section 7: Execution Management | Define timeout hierarchy: primary approver (1 hour), escalation to manager (4 hours), fallback to admin (24 hours). Configurable per tool. |

### Low-Priority Gaps (Nice-to-Have)

| Gap ID | Description | Target Section | Remediation |
|--------|-------------|----------------|-------------|
| **G-016** | Checkpoint compression threshold tuning | Section 7: Execution Management | Auto-tune compression: measure checkpoint size distribution, compress if > 10 KB. Benchmark gzip vs zstd. Document recommended threshold. |

**Gap Summary:**
- **Critical:** 3 gaps
- **High-Priority:** 10 gaps
- **Medium-Priority:** 10 gaps
- **Low-Priority:** 1 gap
- **Total:** 24 gaps (all will be remediated in specification)

---

## Specification Preparation

### Technology Decisions (ADR-002 Aligned)

| Decision | Choice | Rationale | ADR Reference |
|----------|--------|-----------|---------------|
| **Tool Registry Storage** | PostgreSQL 16 + pgvector | Structured tool manifests with semantic search over capability descriptions. pgvector enables similarity search for tool discovery. | ADR-002: PostgreSQL 16 primary datastore |
| **Hot State & Caching** | Redis 7 (JSON data type) | Circuit breaker state, rate limit counters, hot checkpoints, permission cache. JSON type enables complex state storage with single-operation retrieval. | ADR-002: Redis 7 for state/caching |
| **Cold Checkpoint Storage** | PostgreSQL 16 | Durable audit trail for compliance (90-day retention, 7-year archive). Queryable for debugging, rollback, analytics. | ADR-002: PostgreSQL 16 primary datastore |
| **Sandbox Isolation (Cloud)** | gVisor | No KVM required, works in standard Kubernetes (GKE, EKS, AKS). Adequate isolation for most tools. Anthropic-validated in production. | Kubernetes compatibility, industry validation |
| **Sandbox Isolation (On-Prem)** | Firecracker MicroVM | Hardware-level isolation for high-risk tools (arbitrary code execution). 125ms cold start, 5MB overhead. Vercel-validated. | Security-critical tools, bare-metal deployment |
| **Circuit Breaker Library** | Resilience4j | Industry standard, Hystrix deprecated. Configurable state machine (closed, open, half-open). Battle-tested in microservices. | Research finding R-13 |
| **Retry Logic Library** | Tenacity (Python) | 97% success on flakes, 3.5x better than baselines (2025 benchmarks). Full jitter support. Decorator-based API. | Research finding R-11 |
| **Secrets Management** | HashiCorp Vault | Ephemeral credentials, runtime injection, automatic rotation. Industry standard, audit trail, FIPS 140-2 compliance. | Research finding R-09, R-12 |
| **Audit Streaming** | Apache Kafka | Real-time compliance monitoring, high-throughput, durable. Retention policies for regulatory compliance. SIEM integration. | Research finding R-17 |
| **MCP Process Manager** | PM2 | Process lifecycle for MCP servers, stdio supervision, auto-restart, clustering. Node.js ecosystem standard. | ADR-002: PM2 for MCP services |
| **MCP Transport** | stdio (JSON-RPC 2.0) | No network config, process isolation, minimal overhead. Per ADR-001. OpenAI, Anthropic, Google adopted standard. | ADR-001: MCP stdio transport |
| **Checkpoint Serialization** | JSON + gzip | Human-readable (debugging), schema-versioned (compatibility), compressed (storage efficiency). Binary blobs via S3 refs. | Operability vs performance balance |
| **Local LLM Inference** | Ollama | Tool selection, semantic search, parameter extraction. Local inference (no API costs). Mistral 7B recommended model. | ADR-002: Ollama for local inference |

### Patterns to Specify

| Pattern | Source | Application | Section |
|---------|--------|-------------|---------|
| **Protocol-Agnostic Tool Registry** | ToolRegistry library (R-01) | Unified interface for MCP, OpenAPI, LangChain, native tools | Section 3: Tool Registry |
| **Nested Sandbox Isolation (BC-1)** | Kubernetes Agent Sandbox (R-05) | Tool sandboxes within agent sandboxes. Resource limits inherited and sub-allocated. | Section 4: Tool Execution |
| **Exponential Backoff with Full Jitter** | AWS, Tenacity (R-11) | External API retries. Randomized delays to prevent thundering herd. | Section 5: Resilience |
| **Circuit Breaker State Machine** | Resilience4j (R-13) | Three states: closed, open, half-open. Failure threshold triggers open. Timeout triggers half-open. | Section 5: Resilience |
| **Runtime Secret Injection** | StrongDM, 1Password (R-12) | Credentials fetched from vault at invocation time. Ephemeral lifetime = tool timeout. No storage in configs. | Section 8: Security |
| **Capability-Based Authorization** | Capability-based security (R-16) | Tool invocation tokens as capabilities. Token possession = authorization. Decentralized validation. | Section 8: Security |
| **MCP stdio Bridge** | MCP specification (R-21) | JSON-RPC 2.0 over stdin/stdout pipes. PM2 process management. Capability negotiation on startup. | Section 6: MCP Integration |
| **Hybrid Checkpointing** | LangGraph Redis + PostgreSQL (R-24, R-25) | Micro-checkpoints (Redis, 30s), macro-checkpoints (PostgreSQL, milestones), named checkpoints (manual recovery points). | Section 7: Execution Management |
| **Two-Tier Document Caching** | Phase 15 integration (Task 4) | Redis cache (5-min TTL) for hot documents. Local cache for immutable versions. Invalidation via pub/sub. | Section 6: MCP Integration |
| **Human-in-the-Loop Approval** | n8n, Temporal (R-20) | Tool enters pending_approval state. Notification sent. Approval token with expiration. Resume on approval. | Section 7: Execution Management |
| **Audit Streaming with CloudEvents** | Confluent, CloudEvents 1.0 (R-17) | Real-time audit events to Kafka. CloudEvents 1.0 format. Partitioned by tenant_id. 90-day retention. | Section 9: Observability |
| **Semantic Tool Discovery** | LangGraph BigTool (R-02) | pgvector embeddings of tool descriptions. Semantic search query from agent. Meta-tool pattern for large registries. | Section 3: Tool Registry |

### Standards to Reference

| Standard | Version | Sections | How Used |
|----------|---------|----------|----------|
| **Model Context Protocol (MCP)** | 2025-11-25 | Section 6: MCP Integration | Tool discovery, invocation, resource access via JSON-RPC. Official Linux Foundation standard. |
| **JSON-RPC 2.0** | 2.0 | Section 6: MCP Integration | Wire protocol for MCP communication over stdio. Request/response/notification messages. |
| **Semantic Versioning (SemVer)** | 2.0.0 | Section 3: Tool Registry | Tool versioning, backward compatibility rules. Major.minor.patch format. |
| **OpenAPI** | 3.1 | Section 3: Tool Registry | External API tool definitions. REST endpoint schemas, authentication, rate limits. |
| **JSON Schema** | 2020-12 | Section 3: Tool Registry, Section 4: Tool Execution | Tool input/output schema validation. Parameter type checking, constraints. |
| **OWASP Secrets Management Cheat Sheet** | Current | Section 8: Security | Credential injection, rotation, audit. Vault integration patterns. |
| **Kubernetes CRD** | v1 | Section 4: Tool Execution | Sandbox, SandboxTemplate, SandboxClaim definitions. Resource limits, network policies. |
| **OAuth 2.1** | Draft | Section 8: Security | MCP authorization (per June 2025 MCP update). Token-based access control. |
| **CloudEvents** | 1.0 | Section 9: Observability | Tool invocation event format. Standardized envelope for audit logs. |
| **ISO 8601** | Current | All sections | Timestamp format for all temporal data. Timezone-aware (UTC). |
| **JWT (RFC 7519)** | RFC 7519 | Section 8: Security | Capability token format. RS256 signing algorithm. Claims for tool permissions. |
| **gRPC** | Optional | Section 11: Integration | Alternative to REST for L03 <-> L11 communication. Performance optimization. |

---

## Verification Checklist

- [x] All research findings classified (25 applicable, 1 other layer)
- [x] Data Layer integration points mapped (11 integration points)
- [x] Agent Runtime interface documented (BC-1 nested sandbox with 6 interfaces)
- [x] Phase 15 Document Bridge integration mapped (6 integration points, 3 design questions answered)
- [x] Phase 16 State Bridge integration mapped (6 integration points, 3 design questions answered)
- [x] Integration Layer interface documented (BC-2 with 4 methods, complete TypeScript contracts)
- [x] Component coverage analysis completed (10 components assessed, 22 gaps identified)
- [x] Open questions resolved (7 questions answered with high/medium confidence)
- [x] All gaps have target sections assigned (24 gaps prioritized: 3 critical, 10 high, 10 medium, 1 low)
- [x] Technology decisions aligned with ADR-002 (14 decisions documented)
- [x] Patterns identified for specification (12 patterns mapped to sections)
- [x] Standards documented for reference (12 standards with usage guidance)

---

## Next Steps for Session 03-05 (Specification Writing)

### Session 03: Spec Part 1 - Architecture & Registry
**Focus:**
- Section 1: Executive Summary
- Section 2: System Overview & Context
- Section 3: Architecture Components (Tool Registry, Tool Discovery, Tool Versioning)
- Section 4: Data Model (Tool Manifest Schema, Capability Schema, Permission Schema)

**Key Gaps to Address:** G-001, G-002, G-003, G-006

**Research Findings to Leverage:** R-01, R-02, R-03, R-19

---

### Session 04: Spec Part 2 - Execution & Security
**Focus:**
- Section 5: Component Specifications (Tool Executor, Sandbox Manager, Permission Checker)
- Section 6: Security & Compliance (Capability Tokens, Credential Injection, Audit Logging)
- Section 7: Resilience Patterns (Circuit Breaker, Rate Limiting, Retry Logic)

**Key Gaps to Address:** G-004, G-005, G-007, G-010, G-011, G-012, G-017, G-018

**Research Findings to Leverage:** R-05, R-06, R-07, R-08, R-09, R-10, R-11, R-12, R-13, R-14, R-15, R-16, R-17

---

### Session 05: Spec Part 3 - Integration & Operations
**Focus:**
- Section 8: Integration Patterns (BC-1 Nested Sandbox, BC-2 tool.invoke(), Phase 15/16 MCP Bridges)
- Section 9: Operational Procedures (Deployment, Monitoring, Troubleshooting)
- Section 10: Testing Strategy (Unit, Integration, Security, Performance Tests)
- Section 11: Future Considerations (Multi-tool Workflows, Advanced Orchestration)

**Key Gaps to Address:** G-008, G-009, G-013, G-014, G-015, G-019, G-020, G-021, G-022

**Research Findings to Leverage:** R-03, R-18, R-20, R-21, R-22, R-23, R-24, R-25, R-26

---

## Summary for Specification Authors

**What This Gap Analysis Provides:**
1. **Validated research alignment:** 96% of findings directly applicable to L03
2. **Complete integration contracts:** BC-1 (nested sandbox), BC-2 (tool.invoke()), Phase 15/16 (MCP bridges)
3. **Technology stack locked in:** PostgreSQL + Redis + gVisor/Firecracker + Vault + Kafka + PM2
4. **24 gaps identified and prioritized:** All will be remediated, prioritization for section ordering
5. **12 industry patterns ready to specify:** From LangGraph, Kubernetes, Resilience4j, MCP, etc.
6. **7 open questions resolved:** High-confidence answers for versioning, checkpointing, credentials, caching

**Specification Writing Can Proceed with Confidence.**

---

**Gap Analysis Complete**
**Next Session:** 03-spec-part1.md (Architecture & Registry Components)
