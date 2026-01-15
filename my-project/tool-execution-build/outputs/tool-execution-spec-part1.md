# Tool Execution Layer Specification v1.0 - Part 1

**Document Status:** Draft
**Version:** 1.0 (Part 1 of 3)
**Date:** 2026-01-14
**Layer:** L03 - Tool Execution Layer
**Sections:** 1-5 (Executive Summary, Scope, Architecture, Interfaces, Data Model)

---

## Section 1: Executive Summary

### 1.1 Purpose

The Tool Execution Layer (L03) provides a secure, isolated environment for AI agent tool invocations, maintaining a registry of available tools with capability manifests and enforcing tool-level permissions. It acts as the critical boundary between agent intent and external system access, ensuring that tools execute safely within nested sandboxes, respect rate limits, handle failures gracefully through circuit breakers, and maintain state for long-running operations.

This layer addresses the emerging security challenge of AI agents as "the new insider threat" in 2026 enterprise environments. Research shows that 60% of production agent failures stem from tool versioning issues, while uncontrolled tool access represents a significant attack surface for agent misbehavior. L03 mitigates these risks through capability-based authorization, comprehensive audit logging, and fail-safe resilience patterns.

The Tool Execution Layer integrates two critical MCP (Model Context Protocol) bridges: the **Document Bridge (Phase 15)** provides tools with access to authoritative documentation during execution, ensuring consistency with organizational knowledge; the **State Bridge (Phase 16)** enables checkpoint-based recovery for long-running operations, allowing tools to resume after interruptions without reprocessing. These integrations position L03 as the operational nexus between agent reasoning (L02) and the agentic data ecosystem (L01, Phase 15/16).

### 1.2 Key Capabilities

| Capability | Description | Technology Foundation | Phase Integration |
|------------|-------------|----------------------|-------------------|
| **Protocol-Agnostic Tool Registry** | Unified interface for tools from MCP servers, OpenAPI specs, LangChain definitions, and native functions with semantic search via pgvector | PostgreSQL 16 + pgvector, ToolRegistry pattern | Phase 15: MCP tool discovery |
| **Nested Sandbox Execution (BC-1)** | Tool sandboxes isolated within agent sandboxes with resource sub-allocation, filesystem restrictions, and network policies | Kubernetes Agent Sandbox (gVisor for cloud, Firecracker for on-prem) | N/A |
| **Capability-Based Authorization** | Unforgeable capability tokens grant tool execution rights without central authorization service lookups | JWT (RS256) with OPA policy validation | N/A |
| **External API Management** | Rate limiting, circuit breaking, exponential backoff with jitter, and credential rotation for external service integrations | Redis 7 (state), Resilience4j (circuit breaker), Tenacity (retry), HashiCorp Vault (secrets) | N/A |
| **Fail-Safe Resilience** | Three-state circuit breakers (closed, open, half-open) with health-based triggers prevent cascading failures across tools | Redis 7 (distributed state), Resilience4j library | N/A |
| **Result Validation & Type Safety** | JSON Schema validation of tool outputs with type coercion and sanitization before returning to agents | AJV validator, custom sanitization rules | N/A |
| **Document Context Bridge (Phase 15)** | MCP client for document-consolidator service provides tools with authoritative document access, caching, and version pinning | MCP stdio transport (JSON-RPC 2.0), PM2 process management, Redis cache (5-min TTL) | **Phase 15: Full integration** |
| **State Checkpoint Bridge (Phase 16)** | MCP client for context-orchestrator service enables hybrid checkpointing (micro: Redis/30s, macro: PostgreSQL/events, named: manual) for resumable operations | MCP stdio transport (JSON-RPC 2.0), Redis (hot checkpoints), PostgreSQL (cold checkpoints) | **Phase 16: Full integration** |

### 1.3 Position in Stack

```
+========================================================================+
|                       L11: INTEGRATION LAYER                           |
|  (Workflow orchestration, multi-agent coordination)                    |
+========================================================================+
                               |
                               | BC-2: tool.invoke()
                               | (ToolInvokeRequest -> ToolInvokeResponse)
                               v
+========================================================================+
|                    L03: TOOL EXECUTION LAYER                           |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  | Tool Registry   | Tool Executor  | Permission    | Circuit       |  |
|  | (PostgreSQL +   | (Nested        | Checker       | Breaker       |  |
|  |  pgvector)      |  Sandbox)      | (OPA + JWT)   | (Resilience4j)|  |
|  +------------------------------------------------------------------+  |
|  | External API    | Result         | Document      | State         |  |
|  | Manager         | Validator      | Bridge        | Bridge        |  |
|  | (Redis +        | (AJV + Schema) | (Phase 15     | (Phase 16     |  |
|  |  Vault)         |                |  MCP)         |  MCP)         |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  MCP Bridges (stdio JSON-RPC):                                        |
|  +---------------------------+  +----------------------------------+   |
|  | document-consolidator     |  | context-orchestrator             |   |
|  | (Phase 15)                |  | (Phase 16)                       |   |
|  | - get_source_of_truth     |  | - save_context_snapshot          |   |
|  | - search_documents        |  | - create_checkpoint              |   |
|  | - find_overlaps           |  | - rollback_to                    |   |
|  | - get_document_metadata   |  | - get_unified_context            |   |
|  +---------------------------+  +----------------------------------+   |
+========================================================================+
                               ^
                               | BC-1: Nested sandbox context
                               | (agent_did, resource_limits, network_policy)
                               |
+========================================================================+
|                    L02: AGENT RUNTIME LAYER                            |
|  (Agent sandbox management, lifecycle control)                         |
+========================================================================+
                               ^
                               |
+========================================================================+
|                    L01: AGENTIC DATA LAYER                             |
|  (Event Store, ABAC Engine, Vector Store, Audit Log)                  |
+========================================================================+
```

**Key Interfaces:**
- **BC-1 (Boundary Condition 1):** Tool sandboxes are nested within agent sandboxes owned by L02 (Agent Runtime Layer). L03 inherits resource limits, network policies, and filesystem restrictions from L02, then applies additional tool-specific constraints.
- **BC-2 (Boundary Condition 2):** L03 exposes `tool.invoke()` interface consumed by L11 (Integration Layer) for workflow orchestration and multi-agent coordination.
- **Phase 15 Integration:** Document Bridge connects L03 to document-consolidator MCP server for authoritative document access during tool execution.
- **Phase 16 Integration:** State Bridge connects L03 to context-orchestrator MCP server for checkpoint-based state persistence and recovery.

### 1.4 Design Principles

1. **Nested Isolation (BC-1 Principle)**
   Tool sandboxes operate within agent sandboxes with strictly more restrictive permissions. Tool resource limits must be less than or equal to agent resource limits. Tool network access must be a subset of agent network access. Tool filesystem access must be within agent filesystem boundaries. This prevents privilege escalation while enabling fine-grained tool-level control.

2. **Fail-Safe Resilience**
   Circuit breakers default to open (blocking) on ambiguous states. Rate limiters use token bucket algorithm with burst tolerance. Retries use exponential backoff with full jitter to prevent thundering herd. External API failures never propagate to block agent progress—tools return structured errors with retry guidance.

3. **Capability-Based Authorization**
   Tool invocation tokens are unforgeable capabilities (JWT with RS256 signatures). Possessing a valid capability token grants tool execution rights without additional authorization service lookups. This decentralized pattern scales better than centralized RBAC/ABAC for distributed agent systems while maintaining security through cryptographic signatures.

4. **Checkpoint-Driven Recovery (Phase 16)**
   Long-running tools (> 30 seconds) automatically checkpoint progress at 30-second intervals (micro-checkpoints to Redis) and at key milestones (macro-checkpoints to PostgreSQL). Tools can resume from the last valid checkpoint after timeout, crash, or cancellation, minimizing reprocessing and enabling resilient operations.

5. **Document Version Pinning (Phase 15)**
   Tools requiring document context explicitly pin document versions at invocation start. Pinned versions remain immutable throughout tool execution, preventing "moving target" issues where documents change mid-execution. Checkpoints include document version maps to ensure consistent state on resume.

6. **Protocol Agnosticism**
   Tool registry abstracts tool sources (MCP servers, OpenAPI specs, LangChain tools, native functions) behind a unified interface. Tools are discovered via semantic search over capability descriptions using pgvector embeddings. This prevents vendor lock-in and enables gradual migration between tool ecosystems.

7. **Defense in Depth**
   Security layered across multiple boundaries: (1) Permission Checker validates capability tokens, (2) OPA enforces policy-based access control, (3) Sandbox Manager enforces resource limits and isolation, (4) Result Validator sanitizes outputs for XSS/injection, (5) Audit Logger records all invocations for forensic analysis. Compromise of any single layer does not compromise the system.

---

## Section 2: Scope Definition

### 2.1 In Scope

| Capability | Description | Components Involved | Gap References |
|------------|-------------|---------------------|----------------|
| **Tool Registry & Discovery** | Maintain catalog of available tools with capability manifests, semantic descriptions, version history, and dependency metadata. Support semantic search via pgvector embeddings. Manage tool lifecycle (active, deprecated, sunset, removed). Handle multiple concurrent versions per tool with SemVer conflict resolution. | Tool Registry, MCP Bridge (tool discovery from document-consolidator/context-orchestrator) | G-001, G-002, G-003 |
| **Nested Sandbox Execution** | Execute tools within isolated sandboxes nested inside agent sandboxes (BC-1). Inherit resource limits (CPU, memory, timeout) from agent context and sub-allocate to tools. Enforce filesystem restrictions (subset of agent mounts) and network policies (subset of agent allowed hosts). Support gVisor (cloud) and Firecracker (on-prem) isolation technologies. | Tool Executor, Sandbox Manager | BC-1 interface |
| **Permission Enforcement** | Validate capability tokens (JWT) for tool invocation authorization. Query OPA for policy-based access control (filesystem, network, credentials). Enforce least-privilege principle: tools only access explicitly allowed resources. Cache permissions in Redis with invalidation on policy updates. | Permission Checker | G-006, G-007 |
| **External API Management** | Manage connections to external services (APIs, databases, file systems). Handle authentication via runtime secret injection from HashiCorp Vault (ephemeral credentials). Enforce rate limits per tool/API (token bucket algorithm, Redis counters). Implement circuit breakers per API endpoint (Resilience4j, Redis state). Apply retry logic with exponential backoff and full jitter (Tenacity library). | External Adapter Manager, Circuit Breaker Controller | G-008, G-009 |
| **Result Validation** | Validate tool outputs against JSON Schema defined in tool manifest. Perform type coercion (e.g., string -> number, ISO 8601 -> Date) and sanitization (SQL injection, XSS, command injection patterns). Enforce structured output contracts for tools with schema definitions. Return validation errors to agent with specific field-level feedback. | Result Validator | G-010, G-011, G-012 |
| **Document Context Integration (Phase 15)** | Provide tools with access to authoritative documents via document-consolidator MCP server. Support semantic search (`search_documents`), content retrieval (`get_source_of_truth`), metadata access (`get_document_metadata`), and version pinning. Cache frequently accessed documents in Redis (5-min TTL) with pub/sub invalidation. Query ABAC engine for document access permissions. | Document Bridge, MCP Client | G-013, G-014, Phase 15 integration |
| **State Checkpoint Management (Phase 16)** | Persist tool execution state for resumability via context-orchestrator MCP server. Implement hybrid checkpointing: micro-checkpoints (Redis, 30s intervals), macro-checkpoints (PostgreSQL, event milestones), named checkpoints (manual recovery points). Support resume from checkpoint after timeout, crash, or cancellation. Store checkpoint diffs for large states using delta encoding. | State Bridge, MCP Client, State Checkpointer | G-015, G-016, Phase 16 integration |
| **Audit Logging & Compliance** | Stream tool invocation events to Kafka in CloudEvents 1.0 format. Record invocation parameters (PII-sanitized), results, duration, resource usage, errors, and document/state access patterns. Partition by tenant_id for multi-tenancy isolation. Retain 90 days in hot storage, 7 years in cold storage (S3 Glacier). Support SIEM integration (Splunk, Datadog, Elastic). | Audit Logger | G-017, G-018, G-019 |

### 2.2 Out of Scope

| Excluded Capability | Rationale | Owning Layer |
|---------------------|-----------|--------------|
| **LLM Function Calling** | Transforming tool manifests into provider-specific function calling formats (OpenAI functions, Anthropic tools, Google function declarations) is L11 responsibility. L03 maintains vendor-neutral tool definitions. | L11: Integration Layer |
| **Agent Sandbox Management** | Creating, managing, and destroying agent-level sandboxes is L02 responsibility. L03 operates within sandboxes provided by L02 (BC-1 nested isolation). | L02: Agent Runtime Layer |
| **Multi-Agent Coordination** | Orchestrating tool invocations across multiple agents, resolving inter-agent dependencies, and managing distributed workflows is L11 responsibility. L03 executes single-agent tool invocations. | L11: Integration Layer |
| **Policy Authoring** | Defining ABAC policies for tool access control is L01 responsibility (ABAC Engine). L03 enforces policies but does not author them. | L01: Agentic Data Layer |
| **Document Content Management** | Storing, versioning, consolidating, and searching document content is Phase 15 responsibility. L03 consumes documents via MCP bridge but does not manage document lifecycle. | Phase 15: Document Management (MCP Server) |
| **Session State Management** | Tracking agent session lifecycle, managing session context, and coordinating state across session phases is Phase 16 responsibility. L03 checkpoints tool-specific state but does not manage session-level state. | Phase 16: Session Orchestration (MCP Server) |

### 2.3 Boundary Decisions

#### BC-1: Nested Sandbox Interface (L02 -> L03)

**Decision:** Tool sandboxes are nested within agent sandboxes owned by L02 (Agent Runtime Layer).

**Rationale:** Agent-level sandboxes provide coarse-grained isolation (agent from agent). Tool-level sandboxes provide fine-grained isolation (tool from tool within same agent). Nesting ensures tools cannot escape agent security boundaries while allowing per-tool restrictions.

**Interface Contract:**
```
L02 provides:
- agent_did (identity)
- parent_sandbox_id (Kubernetes Sandbox CRD)
- resource_limits (CPU: millicores, memory: MB, timeout: seconds)
- network_policy (allowed_hosts, allowed_ports, DNS servers)
- filesystem_policy (mount paths, read-only vs read-write)

L03 consumes:
- Validates tool resource requests <= agent limits
- Creates nested sandbox (SandboxClaim referencing parent_sandbox_id)
- Adds tool-specific network restrictions (subset of allowed_hosts)
- Adds tool-specific filesystem restrictions (subdirectories of agent mounts)
- Enforces timeout <= agent timeout
```

**Technology:** Kubernetes Agent Sandbox CRD with gVisor runtime (cloud deployments) or Firecracker runtime (on-prem deployments).

**Gap Addressed:** None directly, but foundation for G-004 (async execution patterns) and G-005 (priority scheduling).

---

#### BC-2: Tool Invocation Interface (L03 -> L11)

**Decision:** L03 exposes `tool.invoke()` method consumed by L11 (Integration Layer) for workflow orchestration.

**Rationale:** L11 orchestrates multi-agent workflows and coordinates tool invocations across agents. L11 needs a synchronous interface for immediate tool execution and an asynchronous interface for long-running tools (> 30s). L03 provides both via a single `tool.invoke()` method with `async_mode` parameter.

**Interface Contract:**
```
L11 invokes:
- tool.invoke(request: ToolInvokeRequest) -> ToolInvokeResponse

Request includes:
- tool_id, tool_version (semantic version)
- agent_context (agent_did, tenant_id, session_id)
- parameters (validated against tool manifest schema)
- resource_limits (optional, defaults from manifest)
- document_context (Phase 15: document_refs, version_pinning, query)
- checkpoint_config (Phase 16: enable_checkpointing, interval, resume_from)
- execution_options (async_mode, priority, idempotency_key, require_approval)

Response includes:
- status (pending, running, success, error, timeout, cancelled, permission_denied, pending_approval)
- result (tool-specific, validated against manifest schema)
- error (code, message, details, retryable flag)
- execution_metadata (duration, resource usage, documents_accessed, checkpoints_created)
- checkpoint_ref (for resumable operations)
- polling_info (for async mode)
```

**Technology:** REST API (JSON over HTTP) or gRPC (protobuf) for performance-critical deployments.

**Gap Addressed:** G-006 (capability token in agent_context), G-020 (multi-tool workflow orchestration from L11).

---

#### ADR-001: MCP Integration Architecture

**Decision:** MCP servers (document-consolidator, context-orchestrator) communicate with L03 via stdio transport (JSON-RPC 2.0), not HTTP.

**Rationale:** stdio transport provides process-level isolation, no network configuration overhead, guaranteed message delivery within same host, and inherent security through OS-level process boundaries. PM2 manages MCP server lifecycle (auto-restart on crash, log aggregation, clustering).

**Implementation:**
```
PM2 starts MCP server process:
  pm2 start mcp-document-consolidator --name "doc-bridge"

L03 MCP Client:
  - Opens stdin/stdout pipes to MCP server process
  - Sends JSON-RPC requests on stdin
  - Reads JSON-RPC responses from stdout
  - Enforces timeout (30s default, kills process if no response)
  - Captures stderr for error logging
```

**Gap Addressed:** None directly, but foundation for Phase 15/16 integrations (G-013, G-014, G-015).

---

#### ADR-002: Lightweight Development Stack

**Decision:** PostgreSQL 16 + pgvector (tool registry), Redis 7 (hot state), Ollama (local LLM inference), PM2 (MCP process management).

**Rationale:** Avoid heavy infrastructure dependencies (Kubernetes-only, cloud-specific services). Enable local development and on-prem deployments. PostgreSQL provides relational storage + vector search in single database. Redis provides fast cache/state with JSON data type. Ollama enables local semantic search without API costs.

**Technology Mapping:**
- **PostgreSQL 16 + pgvector:** Tool registry, tool versions, tool manifests, cold checkpoints, audit logs (90-day retention)
- **Redis 7 (JSON data type):** Circuit breaker state, rate limit counters, hot checkpoints (TTL 1 hour), permission cache, document cache
- **Ollama (Mistral 7B):** Semantic embeddings for tool descriptions, tool selection from natural language queries
- **PM2:** MCP server process lifecycle, auto-restart, log rotation, clustering for high availability

**Gap Addressed:** Technology foundation for G-001 (manifest schema in PostgreSQL), G-008 (circuit breaker notifications via Redis pub/sub), G-010 (result validation schema storage).

---

## Section 3: Architecture

### 3.1 Component Diagram

```
+======================================================================+
|                    L03: TOOL EXECUTION LAYER                         |
+======================================================================+
|                                                                      |
|  +----------------+  +----------------+  +------------------+        |
|  | Tool Registry  |  | Tool Executor  |  | Permission       |        |
|  |                |  |                |  | Checker          |        |
|  | - Tool catalog |  | - Sandbox mgmt |  | - JWT validation |        |
|  | - Semantic     |  | - Resource     |  | - OPA query      |        |
|  |   search       |  |   allocation   |  | - Capability     |        |
|  | - Versioning   |  | - Isolation    |  |   tokens         |        |
|  | - Deprecation  |  |   (gVisor/FC)  |  | - Cache mgmt     |        |
|  +-------+--------+  +-------+--------+  +--------+---------+        |
|          |                   |                    |                  |
|          |                   v                    v                  |
|          |          +------------------+  +------------------+       |
|          |          | External Adapter |  | Circuit Breaker  |       |
|          |          | Manager          |  | Controller       |       |
|          |          |                  |  |                  |       |
|          |          | - API clients    |  | - State machine  |       |
|          |          | - Credential     |  | - Health checks  |       |
|          |          |   injection      |  | - Transitions    |       |
|          |          | - Rate limiting  |  | - Notifications  |       |
|          |          | - Retry logic    |  | - Redis state    |       |
|          |          +------------------+  +--------+---------+       |
|          |                   |                    |                  |
|          v                   v                    v                  |
|  +------------------+  +------------------+                          |
|  | Result Validator |  | Audit Logger     |                          |
|  |                  |  |                  |                          |
|  | - Schema check   |  | - CloudEvents    |                          |
|  | - Type coercion  |  | - Kafka stream   |                          |
|  | - Sanitization   |  | - PII redaction  |                          |
|  | - Error handling |  | - Tenant partition|                         |
|  +------------------+  +------------------+                          |
|                                                                      |
|  +------------------------------------------------------------------+|
|  | MCP BRIDGES (stdio JSON-RPC)                                     ||
|  +------------------------------------------------------------------+|
|  |                                                                  ||
|  |  +--------------------------+  +------------------------------+ ||
|  |  | Document Bridge          |  | State Bridge                 | ||
|  |  | (Phase 15)               |  | (Phase 16)                   | ||
|  |  |                          |  |                              | ||
|  |  | - MCP client             |  | - MCP client                 | ||
|  |  | - Document query         |  | - Checkpoint creation        | ||
|  |  | - Cache management       |  | - State restoration          | ||
|  |  | - Version pinning        |  | - Delta encoding             | ||
|  |  | - Permission check       |  | - TTL management             | ||
|  |  +------------+-------------+  +-------------+----------------+ ||
|  |               |                              |                  ||
|  |               v stdin/stdout                 v stdin/stdout     ||
|  |  +--------------------------+  +------------------------------+ ||
|  |  | document-consolidator    |  | context-orchestrator         | ||
|  |  | (MCP Server, Phase 15)   |  | (MCP Server, Phase 16)       | ||
|  |  +--------------------------+  +------------------------------+ ||
|  +------------------------------------------------------------------+|
|                                                                      |
+======================================================================+
                           ^                    ^
                           |                    |
                    BC-1: Nested sandbox  BC-2: tool.invoke()
                    (from L02)            (to L11)
                           |                    |
+==========================+====================+=======================+
|          L02: Agent Runtime        |    L11: Integration Layer       |
+====================================+==================================+
```

### 3.2 Component Inventory

| Component | Purpose | Technology (ADR-002) | Dependencies | Status |
|-----------|---------|---------------------|--------------|--------|
| **Tool Registry** | Catalog of available tools with capability manifests, semantic search, versioning, deprecation lifecycle | PostgreSQL 16 + pgvector (storage), Ollama (embeddings), ToolRegistry library (protocol-agnostic interface) | Data Layer (PostgreSQL), Ollama (embedding generation) | Core |
| **Tool Executor** | Execute tools in nested sandboxes with resource limits, isolation, and timeout enforcement | Kubernetes Agent Sandbox CRD (gVisor for cloud, Firecracker for on-prem) | Agent Runtime Layer (parent sandbox context via BC-1) | Core |
| **Permission Checker** | Validate capability tokens, query OPA for policy decisions, cache permissions, handle invalidation | JWT (RS256), Open Policy Agent (OPA), Redis 7 (permission cache) | Data Layer (ABAC Engine), Redis (cache) | Core |
| **External Adapter Manager** | Manage external API connections, credential injection, rate limiting, retry logic | HashiCorp Vault (secrets), Redis 7 (rate limit counters), Tenacity (retry library) | HashiCorp Vault (credential storage), Redis (state) | Core |
| **Circuit Breaker Controller** | Prevent cascading failures via circuit breaker state machine, health checks, notifications | Resilience4j (circuit breaker library), Redis 7 (distributed state), Redis pub/sub (notifications) | Redis (state + pub/sub) | Core |
| **Result Validator** | Validate tool outputs against JSON Schema, type coercion, sanitization, error handling | AJV (JSON Schema validator), custom sanitization rules | Tool Registry (schema definitions) | Core |
| **Document Bridge (Phase 15)** | MCP client for document-consolidator, document query/cache/version pinning, permission checks | MCP Client (JSON-RPC 2.0), PM2 (process management), Redis 7 (document cache), Python asyncio (stdio pipes) | MCP Server (document-consolidator), Redis (cache), ABAC Engine (permissions) | Phase 15 |
| **State Bridge (Phase 16)** | MCP client for context-orchestrator, checkpoint creation/restoration, delta encoding, TTL management | MCP Client (JSON-RPC 2.0), PM2 (process management), Redis 7 (hot checkpoints), PostgreSQL 16 (cold checkpoints) | MCP Server (context-orchestrator), Redis (hot state), PostgreSQL (cold state) | Phase 16 |
| **Audit Logger** | Stream tool invocation events to Kafka in CloudEvents 1.0 format, PII redaction, tenant partitioning | Apache Kafka (event stream), CloudEvents SDK, custom PII sanitization rules | Kafka cluster (event ingestion) | Core |

**Dependency Graph:**
```
Tool Registry -----> PostgreSQL 16 (storage)
              \----> Ollama (embeddings)

Tool Executor -----> L02 Agent Runtime (BC-1 parent sandbox)
              \----> Kubernetes Sandbox CRD

Permission Checker -> Redis 7 (cache)
                   \-> OPA (policy engine)
                   \-> L01 Data Layer (ABAC Engine)

External Adapter ---> HashiCorp Vault (secrets)
                 \--> Redis 7 (rate limits)

Circuit Breaker ----> Redis 7 (state + pub/sub)

Result Validator ---> Tool Registry (schemas)

Document Bridge ----> document-consolidator (MCP)
                \---> Redis 7 (cache)
                \---> L01 Data Layer (ABAC Engine)

State Bridge -------> context-orchestrator (MCP)
             \------> Redis 7 (hot checkpoints)
             \------> PostgreSQL 16 (cold checkpoints)

Audit Logger -------> Kafka (event stream)
```

### 3.3 Component Specifications

#### 3.3.1 Tool Registry

**Purpose:**
Maintain a catalog of available tools with capability manifests, semantic descriptions, version history, and deprecation lifecycle. Support semantic search via pgvector embeddings for agent queries like "find a tool to parse CSV files". Handle multiple concurrent versions per tool with SemVer-based conflict resolution.

**Technology Choice & Rationale:**
- **PostgreSQL 16 + pgvector:** Relational storage for structured tool metadata with vector search for semantic queries. Single database reduces operational complexity compared to separate vector DB.
- **Ollama (Mistral 7B):** Generate embeddings for tool descriptions locally without API costs. Mistral 7B provides good quality embeddings (768-dim) at reasonable inference speed (~50ms per description).
- **ToolRegistry Library:** Protocol-agnostic abstraction layer supports tools from MCP servers, OpenAPI specs, LangChain definitions, and native Python functions.

**Configuration Schema (JSON Schema 2020-12):**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "registry": {
      "type": "object",
      "properties": {
        "postgresql_connection_string": {
          "type": "string",
          "description": "PostgreSQL connection URL with pgvector extension enabled"
        },
        "ollama_base_url": {
          "type": "string",
          "default": "http://localhost:11434",
          "description": "Ollama API endpoint for embedding generation"
        },
        "embedding_model": {
          "type": "string",
          "default": "mistral:7b",
          "description": "Ollama model for tool description embeddings"
        },
        "embedding_dimensions": {
          "type": "integer",
          "default": 768,
          "description": "Vector dimensions (must match Ollama model output)"
        },
        "semantic_search_threshold": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "default": 0.7,
          "description": "Cosine similarity threshold for semantic search results"
        },
        "version_retention_policy": {
          "type": "object",
          "properties": {
            "max_versions_per_tool": {
              "type": "integer",
              "default": 5,
              "description": "Maximum concurrent versions to retain"
            },
            "deprecation_warning_days": {
              "type": "integer",
              "default": 90,
              "description": "Days to warn before removing deprecated version"
            }
          }
        }
      },
      "required": ["postgresql_connection_string"]
    }
  }
}
```

**Dependencies:**
- PostgreSQL 16 (Data Layer L01)
- Ollama service (local or remote)
- MCP servers (for tool discovery via Phase 15/16 bridges)

**Error Codes (E3000-E3099):**
- `E3001`: Tool not found (tool_id does not exist in registry)
- `E3002`: Tool version not found (tool_version does not exist for tool_id)
- `E3003`: Tool deprecated (version in sunset phase, warnings issued)
- `E3004`: Tool removed (version deleted, no longer available)
- `E3005`: Semantic search failed (Ollama embedding generation error)
- `E3006`: Version conflict (requested version range has no compatible versions)
- `E3007`: Duplicate tool registration (tool_id already exists with same version)
- `E3008`: Invalid tool manifest (schema validation failed)

**Gap Integration:**
- **G-001 (High):** Tool capability manifest schema fully defined in Section 5.1.1 with all fields (permissions, result_schema, timeout, retry policy, circuit breaker config).
- **G-002 (Medium):** Semantic versioning conflict resolution implemented via `max_versions_per_tool` retention policy and agent-specified version ranges (e.g., "^2.1.0").
- **G-003 (Medium):** Tool deprecation workflow defined with lifecycle states (active, deprecated, sunset, removed) and `deprecation_warning_days` configuration.

---

#### 3.3.2 Tool Executor

**Purpose:**
Execute tools within isolated sandboxes nested inside agent sandboxes (BC-1). Inherit resource limits (CPU, memory, timeout) from agent context and sub-allocate to tools. Enforce filesystem restrictions (subset of agent mounts) and network policies (subset of agent allowed hosts). Support both gVisor (cloud) and Firecracker (on-prem) isolation technologies.

**Technology Choice & Rationale:**
- **Kubernetes Agent Sandbox CRD:** Industry standard for agent workload isolation (Google, Kubernetes SIG Apps). Provides Sandbox, SandboxTemplate, and SandboxClaim resources for declarative sandbox management.
- **gVisor (cloud):** Intercepts syscalls in user-space Go program. No KVM required, works in standard Kubernetes (GKE, EKS, AKS). Adequate isolation for most tools. Anthropic-validated in production (Claude web). Recommended for cloud deployments.
- **Firecracker (on-prem):** Boots real microVMs in ~125ms with ~5MB overhead. Hardware-level isolation via KVM. Stronger security for high-risk tools (arbitrary code execution, untrusted plugins). Vercel-validated in production. Recommended for on-prem/bare-metal deployments.

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "executor": {
      "type": "object",
      "properties": {
        "isolation_technology": {
          "type": "string",
          "enum": ["gvisor", "firecracker"],
          "default": "gvisor",
          "description": "Sandbox isolation technology (gvisor for cloud, firecracker for on-prem)"
        },
        "default_resource_limits": {
          "type": "object",
          "properties": {
            "cpu_millicore_limit": {
              "type": "integer",
              "default": 500,
              "description": "Default CPU limit per tool (millicores)"
            },
            "memory_mb_limit": {
              "type": "integer",
              "default": 1024,
              "description": "Default memory limit per tool (MB)"
            },
            "timeout_seconds": {
              "type": "integer",
              "default": 30,
              "description": "Default execution timeout per tool (seconds)"
            }
          }
        },
        "concurrent_tools_per_agent": {
          "type": "integer",
          "default": 4,
          "description": "Maximum concurrent tool executions per agent"
        },
        "sandbox_warm_pool": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": false,
              "description": "Pre-warm sandboxes for reduced cold start latency"
            },
            "pool_size": {
              "type": "integer",
              "default": 10,
              "description": "Number of pre-warmed sandboxes per agent"
            }
          }
        }
      }
    }
  }
}
```

**Dependencies:**
- Agent Runtime Layer L02 (parent sandbox context via BC-1)
- Kubernetes cluster with Agent Sandbox CRD installed
- gVisor runtime or Firecracker/KVM for VM isolation

**Error Codes (E3100-E3199):**
- `E3101`: Sandbox creation failed (Kubernetes API error, resource exhaustion)
- `E3102`: Resource limit exceeded (tool requested more CPU/memory than agent allows)
- `E3103`: Timeout exceeded (tool execution exceeded timeout limit, process killed)
- `E3104`: Network policy violation (tool attempted connection to disallowed host)
- `E3105`: Filesystem policy violation (tool attempted access outside allowed paths)
- `E3106`: Concurrent tool limit exceeded (agent already running max concurrent tools)
- `E3107`: Sandbox crashed (microVM or gVisor process terminated unexpectedly)
- `E3108`: Tool process exit non-zero (tool binary returned error exit code)

**Gap Integration:**
- **G-004 (High):** Async execution patterns for long-running tools (> 15 min) supported via `async_mode` parameter in `tool.invoke()` request (Section 4.1).
- **G-005 (Medium):** Tool execution priority scheduling implemented via `priority` field in `execution_options` (Section 4.1).

---

#### 3.3.3 Permission Checker

**Purpose:**
Validate capability tokens (JWT with RS256 signatures) for tool invocation authorization. Query Open Policy Agent (OPA) for policy-based access control decisions (filesystem, network, credentials). Enforce least-privilege principle: tools only access explicitly allowed resources. Cache permissions in Redis with pub/sub invalidation on policy updates.

**Technology Choice & Rationale:**
- **JWT (RS256):** Industry-standard token format for capability-based authorization. RS256 (RSA signatures) enables distributed validation without shared secrets (only public key needed). Token structure: `{tool_id, allowed_operations, expiration, agent_did, signature}`.
- **Open Policy Agent (OPA):** Policy engine for attribute-based access control (ABAC). Policies written in Rego language, evaluated locally without network calls. Integrates with Data Layer's ABAC Engine for centralized policy management.
- **Redis 7 (permission cache):** Cache OPA decisions for repeated invocations (same tool + agent + resources). TTL 5 minutes. Invalidate via Redis pub/sub on policy updates from Data Layer.

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "permission_checker": {
      "type": "object",
      "properties": {
        "jwt_public_key_path": {
          "type": "string",
          "description": "Path to RSA public key (PEM format) for JWT signature verification"
        },
        "jwt_algorithm": {
          "type": "string",
          "default": "RS256",
          "description": "JWT signature algorithm (RS256 recommended)"
        },
        "opa_endpoint": {
          "type": "string",
          "default": "http://localhost:8181/v1/data/tool_execution/allow",
          "description": "OPA REST API endpoint for policy evaluation"
        },
        "permission_cache": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true
            },
            "redis_connection_string": {
              "type": "string"
            },
            "ttl_seconds": {
              "type": "integer",
              "default": 300,
              "description": "Cache TTL (5 minutes default)"
            },
            "invalidation_channel": {
              "type": "string",
              "default": "policy:updates",
              "description": "Redis pub/sub channel for cache invalidation"
            }
          }
        }
      },
      "required": ["jwt_public_key_path"]
    }
  }
}
```

**Dependencies:**
- Data Layer L01 (ABAC Engine for policy definitions, Redis for cache)
- Open Policy Agent (OPA) service
- JWT signing service (issues capability tokens)

**Error Codes (E3200-E3299):**
- `E3201`: Invalid capability token (JWT signature verification failed)
- `E3202`: Expired capability token (token expiration timestamp < current time)
- `E3203`: Permission denied - filesystem (OPA denied access to requested filesystem paths)
- `E3204`: Permission denied - network (OPA denied access to requested network hosts)
- `E3205`: Permission denied - credentials (OPA denied access to requested credentials)
- `E3206`: OPA query failed (OPA service unreachable or returned error)
- `E3207`: Missing required claims (JWT missing tool_id, agent_did, or expiration)
- `E3208`: Token revoked (token in revocation list, stored in Redis)

**Gap Integration:**
- **G-006 (Critical):** Capability token format fully specified in Section 4.1.1 with JWT structure (claims, signature algorithm, expiration).
- **G-007 (High):** Permission cache invalidation on policy updates implemented via Redis pub/sub subscription to `policy:updates` channel.

---

#### 3.3.4 External Adapter Manager

**Purpose:**
Manage connections to external services (APIs, databases, file systems). Handle authentication via runtime secret injection from HashiCorp Vault (ephemeral credentials with lifespan = tool timeout). Enforce rate limits per tool/API using token bucket algorithm with Redis counters. Implement retry logic with exponential backoff and full jitter using Tenacity library.

**Technology Choice & Rationale:**
- **HashiCorp Vault:** Industry-standard secrets management with dynamic secrets (ephemeral credentials), automatic rotation, audit trail, and FIPS 140-2 compliance. Integrates with AWS IAM, GCP Service Accounts, Azure AD for cloud provider credentials.
- **Redis 7 (rate limit counters):** Token bucket algorithm state stored in Redis with atomic increment/decrement operations. Distributed rate limiting across multiple L03 instances.
- **Tenacity (Python):** Retry library with exponential backoff, full jitter, and configurable stop conditions. 97% success rate on flakes in 2025 benchmarks, 3.5x better than baseline implementations.

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "external_adapter": {
      "type": "object",
      "properties": {
        "vault": {
          "type": "object",
          "properties": {
            "address": {
              "type": "string",
              "description": "HashiCorp Vault server address"
            },
            "auth_method": {
              "type": "string",
              "enum": ["token", "kubernetes", "aws-iam", "gcp-iam", "azure"],
              "description": "Vault authentication method"
            },
            "secret_path_prefix": {
              "type": "string",
              "default": "secret/tool-execution",
              "description": "Vault path prefix for tool credentials"
            }
          },
          "required": ["address", "auth_method"]
        },
        "rate_limiting": {
          "type": "object",
          "properties": {
            "algorithm": {
              "type": "string",
              "enum": ["token_bucket", "leaky_bucket", "fixed_window", "sliding_window"],
              "default": "token_bucket",
              "description": "Rate limiting algorithm"
            },
            "redis_connection_string": {
              "type": "string"
            },
            "default_requests_per_minute": {
              "type": "integer",
              "default": 60
            },
            "burst_size": {
              "type": "integer",
              "default": 10,
              "description": "Burst tolerance above rate limit"
            }
          }
        },
        "retry": {
          "type": "object",
          "properties": {
            "max_attempts": {
              "type": "integer",
              "default": 3
            },
            "base_delay_ms": {
              "type": "integer",
              "default": 1000,
              "description": "Initial backoff delay (milliseconds)"
            },
            "max_delay_ms": {
              "type": "integer",
              "default": 60000,
              "description": "Maximum backoff delay (milliseconds)"
            },
            "jitter": {
              "type": "string",
              "enum": ["none", "full", "equal", "decorrelated"],
              "default": "full",
              "description": "Jitter strategy (full recommended to prevent thundering herd)"
            },
            "retryable_status_codes": {
              "type": "array",
              "items": {"type": "integer"},
              "default": [429, 500, 502, 503, 504],
              "description": "HTTP status codes to retry"
            }
          }
        }
      }
    }
  }
}
```

**Dependencies:**
- HashiCorp Vault (credential storage)
- Redis 7 (rate limit counters)
- External APIs/services (HTTP clients, database drivers, file system access)

**Error Codes (E3300-E3399):**
- `E3301`: Vault connection failed (unable to reach Vault server)
- `E3302`: Credential retrieval failed (secret not found in Vault)
- `E3303`: Rate limit exceeded (tool exhausted API quota, 429 response)
- `E3304`: External API error (5xx response from external service)
- `E3305`: Max retries exhausted (all retry attempts failed)
- `E3306`: Connection timeout (external service did not respond within timeout)
- `E3307`: Authentication failed (401/403 from external service, credential invalid)
- `E3308`: Invalid response format (external service returned malformed response)

**Gap Integration:**
- None directly addressed in this component (gaps related to circuit breaker handled in next component).

---

#### 3.3.5 Circuit Breaker Controller

**Purpose:**
Prevent cascading failures via three-state circuit breaker state machine (closed, open, half-open). Monitor external API health and trigger state transitions based on failure rates or consecutive failure counts. Send notifications to dependent tools on state changes via Redis pub/sub. Store distributed circuit breaker state in Redis for coordination across multiple L03 instances.

**Technology Choice & Rationale:**
- **Resilience4j:** Industry-standard circuit breaker library for Java/JVM languages. Hystrix (Netflix) is in maintenance mode; Resilience4j is the recommended alternative. Configurable state machine with sliding window failure tracking.
- **Redis 7 (circuit state + pub/sub):** Distributed state storage for circuit breaker status (open/closed, failure count, timestamps). Pub/sub for real-time notifications to subscribed tools. Atomic operations for state transitions.

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "circuit_breaker": {
      "type": "object",
      "properties": {
        "redis_connection_string": {
          "type": "string"
        },
        "notification_channel": {
          "type": "string",
          "default": "circuit:state:changes",
          "description": "Redis pub/sub channel for circuit breaker notifications"
        },
        "default_config": {
          "type": "object",
          "properties": {
            "failure_rate_threshold": {
              "type": "number",
              "minimum": 0,
              "maximum": 100,
              "default": 50,
              "description": "Failure rate percentage to trigger open state"
            },
            "slow_call_rate_threshold": {
              "type": "number",
              "minimum": 0,
              "maximum": 100,
              "default": 100,
              "description": "Slow call rate percentage to trigger open state"
            },
            "slow_call_duration_threshold_ms": {
              "type": "integer",
              "default": 5000,
              "description": "Call duration to consider slow (milliseconds)"
            },
            "sliding_window_type": {
              "type": "string",
              "enum": ["count_based", "time_based"],
              "default": "count_based"
            },
            "sliding_window_size": {
              "type": "integer",
              "default": 100,
              "description": "Number of calls (count_based) or seconds (time_based) in window"
            },
            "minimum_number_of_calls": {
              "type": "integer",
              "default": 10,
              "description": "Minimum calls before calculating failure rate"
            },
            "wait_duration_in_open_state_seconds": {
              "type": "integer",
              "default": 60,
              "description": "Duration to wait before transitioning to half-open"
            },
            "permitted_number_of_calls_in_half_open_state": {
              "type": "integer",
              "default": 10,
              "description": "Test calls in half-open state before closing"
            }
          }
        },
        "half_open_strategy": {
          "type": "string",
          "enum": ["canary", "all_or_nothing"],
          "default": "canary",
          "description": "Canary: gradually increase traffic; All-or-nothing: send all or none"
        }
      },
      "required": ["redis_connection_string"]
    }
  }
}
```

**Dependencies:**
- Redis 7 (state storage + pub/sub)
- External Adapter Manager (for external API call metrics)

**Error Codes (E3400-E3499):**
- `E3401`: Circuit breaker open (too many failures, requests blocked)
- `E3402`: Circuit breaker state transition failed (Redis update error)
- `E3403`: Invalid circuit configuration (threshold > 100, window size < 1)
- `E3404`: Circuit health check failed (unable to probe endpoint)
- `E3405`: Half-open test failed (test calls in half-open state still failing)

**Gap Integration:**
- **G-008 (Medium):** Circuit breaker transition notifications implemented via Redis pub/sub on `circuit:state:changes` channel. Dependent tools subscribe and adjust behavior (e.g., skip fallback API if also open).
- **G-009 (Medium):** Half-open state testing strategy configurable via `half_open_strategy` parameter (canary vs all-or-nothing). Canary gradually increases traffic percentage if successful.

---

#### 3.3.6 Result Validator

**Purpose:**
Validate tool outputs against JSON Schema defined in tool manifest. Perform type coercion (e.g., string -> number, ISO 8601 -> Date) and sanitization (SQL injection, XSS, command injection patterns). Enforce structured output contracts for tools with schema definitions. Return validation errors to agent with specific field-level feedback.

**Technology Choice & Rationale:**
- **AJV (Another JSON Schema Validator):** Fastest JSON Schema validator for JavaScript/TypeScript. Supports JSON Schema 2020-12, custom keywords, and async validation. Used by major projects (Webpack, ESLint, VS Code).
- **Custom Sanitization Rules:** Regex patterns and field-based sanitization for security threats. Redact patterns for SQL injection (`'; DROP TABLE`, `1' OR '1'='1`), XSS (`<script>`, `javascript:`), command injection (``; rm -rf`, `| cat /etc/passwd`).

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "result_validator": {
      "type": "object",
      "properties": {
        "strict_mode": {
          "type": "boolean",
          "default": true,
          "description": "Reject outputs that fail schema validation (false: log warning and allow)"
        },
        "type_coercion": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true
            },
            "rules": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "from_type": {"type": "string"},
                  "to_type": {"type": "string"},
                  "coercion_function": {"type": "string"}
                }
              },
              "default": [
                {"from_type": "string", "to_type": "number", "coercion_function": "parseFloat"},
                {"from_type": "string", "to_type": "integer", "coercion_function": "parseInt"},
                {"from_type": "string", "to_type": "boolean", "coercion_function": "Boolean"},
                {"from_type": "string", "to_type": "date", "coercion_function": "new Date"}
              ]
            }
          }
        },
        "sanitization": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true
            },
            "patterns": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "threat_type": {"type": "string"},
                  "regex_pattern": {"type": "string"},
                  "action": {"type": "string", "enum": ["reject", "redact", "escape"]}
                }
              },
              "default": [
                {"threat_type": "sql_injection", "regex_pattern": "('|(\\-\\-)|(;)|(\\|\\|)|(\\*))", "action": "reject"},
                {"threat_type": "xss", "regex_pattern": "(<script|javascript:|onerror=)", "action": "escape"},
                {"threat_type": "command_injection", "regex_pattern": "(;|\\||`|\\$\\()", "action": "reject"}
              ]
            }
          }
        }
      }
    }
  }
}
```

**Dependencies:**
- Tool Registry (for schema definitions from tool manifests)
- AJV library (JSON Schema validation)

**Error Codes (E3500-E3599):**
- `E3501`: Schema validation failed (output does not match tool manifest schema)
- `E3502`: Type coercion failed (unable to coerce value to expected type)
- `E3503`: Sanitization rejected (output contains SQL injection pattern)
- `E3504`: Sanitization rejected (output contains XSS pattern)
- `E3505`: Sanitization rejected (output contains command injection pattern)
- `E3506`: Missing required field (output missing required schema field)
- `E3507`: Invalid field type (output field type does not match schema)
- `E3508`: Schema not found (tool manifest does not define result_schema)

**Gap Integration:**
- **G-010 (Critical):** Result validation schema definition enforced via AJV validator with JSON Schema 2020-12 from tool manifest `result_schema` field.
- **G-011 (High):** Type coercion rules defined in `type_coercion.rules` configuration with support for string -> number/integer/boolean/date conversions.
- **G-012 (High):** Structured output validation implemented via `strict_mode` flag. When enabled, tools must return outputs matching `result_schema` or invocation fails with `E3501`.

---

#### 3.3.7 Document Bridge (Phase 15)

**Purpose:**
MCP client for document-consolidator service. Provides tools with access to authoritative documents via `get_source_of_truth`, `search_documents`, `find_overlaps`, and `get_document_metadata`. Cache frequently accessed documents in Redis (5-min TTL) with pub/sub invalidation on writes. Query ABAC engine for document access permissions. Support version pinning for long-running tools.

**Technology Choice & Rationale:**
- **MCP Client (JSON-RPC 2.0):** Implements MCP specification 2025-11-25 for tool discovery, resource access, and capability negotiation. Communicates with document-consolidator MCP server via stdin/stdout pipes (ADR-001).
- **PM2 (process management):** Manages document-consolidator MCP server lifecycle (auto-restart on crash, log rotation, clustering for HA).
- **Redis 7 (document cache):** Two-tier caching: (1) Hot: `get_source_of_truth` results cached with 5-min TTL, (2) Warm: Immutable document versions cached locally until process restart. Cache invalidation via Redis pub/sub on `document:updates` channel.
- **Python asyncio (stdio pipes):** Non-blocking I/O for stdin/stdout communication with MCP server process.

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "document_bridge": {
      "type": "object",
      "properties": {
        "mcp_server": {
          "type": "object",
          "properties": {
            "pm2_process_name": {
              "type": "string",
              "default": "doc-bridge-mcp",
              "description": "PM2 process name for document-consolidator MCP server"
            },
            "startup_timeout_ms": {
              "type": "integer",
              "default": 5000,
              "description": "Timeout for MCP server startup and capability negotiation"
            },
            "request_timeout_ms": {
              "type": "integer",
              "default": 30000,
              "description": "Timeout for individual MCP requests"
            },
            "max_retries": {
              "type": "integer",
              "default": 3,
              "description": "Max retries for failed MCP requests"
            }
          }
        },
        "cache": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true
            },
            "redis_connection_string": {
              "type": "string"
            },
            "hot_cache_ttl_seconds": {
              "type": "integer",
              "default": 300,
              "description": "TTL for get_source_of_truth results (5 minutes)"
            },
            "metadata_cache_ttl_seconds": {
              "type": "integer",
              "default": 600,
              "description": "TTL for document metadata (10 minutes)"
            },
            "invalidation_channel": {
              "type": "string",
              "default": "document:updates",
              "description": "Redis pub/sub channel for cache invalidation"
            }
          }
        },
        "version_pinning": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true,
              "description": "Support version pinning for long-running tools"
            },
            "pin_storage": {
              "type": "string",
              "enum": ["checkpoint", "redis", "local"],
              "default": "checkpoint",
              "description": "Where to store version pins (checkpoint: Phase 16 integration)"
            }
          }
        },
        "permissions": {
          "type": "object",
          "properties": {
            "check_enabled": {
              "type": "boolean",
              "default": true,
              "description": "Query ABAC engine for document access permissions"
            },
            "abac_endpoint": {
              "type": "string",
              "description": "Data Layer ABAC Engine endpoint for permission checks"
            }
          }
        }
      },
      "required": ["mcp_server"]
    }
  }
}
```

**Dependencies:**
- document-consolidator MCP server (Phase 15)
- PM2 (process management)
- Redis 7 (cache + pub/sub)
- Data Layer L01 (ABAC Engine for document permissions)

**Error Codes (E3600-E3699):**
- `E3601`: Document not found (document_id does not exist in consolidator)
- `E3602`: Document unavailable (MCP server down, all retries failed, no cache)
- `E3603`: Document permission denied (ABAC check failed for agent)
- `E3604`: Document version conflict (requested version deprecated/removed)
- `E3605`: MCP server timeout (no response within request_timeout_ms)
- `E3606`: MCP protocol error (invalid JSON-RPC response from server)
- `E3607`: Cache unavailable (Redis connection failed, MCP fallback used)
- `E3608`: Version pinning failed (unable to store pinned versions)

**Gap Integration:**
- **G-013 (High):** Document access permission model implemented via ABAC integration. Before MCP document retrieval, query Data Layer ABAC Engine with `(agent_did, document_id, access_mode)` tuple.
- **G-014 (Medium):** Bulk document retrieval optimization implemented via batched MCP requests. Send array of document_ids in single `tools/call` request, reduce round-trips, cache batch results.

---

#### 3.3.8 State Bridge (Phase 16)

**Purpose:**
MCP client for context-orchestrator service. Enables hybrid checkpointing: micro-checkpoints (Redis, 30s intervals), macro-checkpoints (PostgreSQL, event milestones), named checkpoints (manual recovery points). Supports resume from checkpoint after timeout, crash, or cancellation. Stores checkpoint diffs for large states using delta encoding. Implements TTL management for hot checkpoints (Redis) and retention policies for cold checkpoints (PostgreSQL).

**Technology Choice & Rationale:**
- **MCP Client (JSON-RPC 2.0):** Implements MCP specification 2025-11-25 for checkpoint operations (`save_context_snapshot`, `create_checkpoint`, `rollback_to`, `get_unified_context`).
- **Redis 7 (hot checkpoints):** LangGraph Redis Checkpoint 0.1.0 pattern with inline JSON storage for single-operation retrieval. TTL 1 hour for micro-checkpoints. Automatic expiration via Redis TTL with `refresh_on_read`.
- **PostgreSQL 16 (cold checkpoints):** Durable storage for macro-checkpoints and named checkpoints. Delta encoding: store only changed state since parent checkpoint. Retention 90 days hot, 7 years cold (archived to S3 Glacier).

**Configuration Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "state_bridge": {
      "type": "object",
      "properties": {
        "mcp_server": {
          "type": "object",
          "properties": {
            "pm2_process_name": {
              "type": "string",
              "default": "state-bridge-mcp",
              "description": "PM2 process name for context-orchestrator MCP server"
            },
            "startup_timeout_ms": {
              "type": "integer",
              "default": 5000
            },
            "request_timeout_ms": {
              "type": "integer",
              "default": 10000,
              "description": "Checkpoint operations are fast, 10s timeout sufficient"
            }
          }
        },
        "checkpointing": {
          "type": "object",
          "properties": {
            "micro_checkpoints": {
              "type": "object",
              "properties": {
                "enabled": {
                  "type": "boolean",
                  "default": true
                },
                "interval_seconds": {
                  "type": "integer",
                  "default": 30,
                  "description": "Frequency of micro-checkpoints for long-running tools"
                },
                "storage": {
                  "type": "string",
                  "enum": ["redis"],
                  "default": "redis"
                },
                "ttl_seconds": {
                  "type": "integer",
                  "default": 3600,
                  "description": "TTL for micro-checkpoints (1 hour)"
                }
              }
            },
            "macro_checkpoints": {
              "type": "object",
              "properties": {
                "enabled": {
                  "type": "boolean",
                  "default": true
                },
                "storage": {
                  "type": "string",
                  "enum": ["postgresql"],
                  "default": "postgresql"
                },
                "retention_days": {
                  "type": "integer",
                  "default": 90,
                  "description": "Hot retention in PostgreSQL (90 days)"
                },
                "archive_storage": {
                  "type": "string",
                  "default": "s3",
                  "description": "Cold storage for archived checkpoints (S3 Glacier)"
                },
                "archive_retention_years": {
                  "type": "integer",
                  "default": 7,
                  "description": "Compliance retention in cold storage"
                }
              }
            },
            "named_checkpoints": {
              "type": "object",
              "properties": {
                "enabled": {
                  "type": "boolean",
                  "default": true
                },
                "storage": {
                  "type": "string",
                  "enum": ["postgresql"],
                  "default": "postgresql"
                },
                "retention": {
                  "type": "string",
                  "enum": ["indefinite", "days", "manual"],
                  "default": "indefinite",
                  "description": "Named checkpoints retained indefinitely unless explicitly deleted"
                }
              }
            }
          }
        },
        "delta_encoding": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true,
              "description": "Store only state changes since parent checkpoint"
            },
            "threshold_kb": {
              "type": "integer",
              "default": 100,
              "description": "Use delta encoding if checkpoint > 100 KB"
            }
          }
        },
        "compression": {
          "type": "object",
          "properties": {
            "enabled": {
              "type": "boolean",
              "default": true
            },
            "algorithm": {
              "type": "string",
              "enum": ["gzip", "zstd"],
              "default": "gzip"
            },
            "threshold_kb": {
              "type": "integer",
              "default": 10,
              "description": "Compress if checkpoint > 10 KB"
            }
          }
        }
      }
    }
  }
}
```

**Dependencies:**
- context-orchestrator MCP server (Phase 16)
- PM2 (process management)
- Redis 7 (hot checkpoints)
- PostgreSQL 16 (cold checkpoints)
- S3 or compatible object storage (cold archive)

**Error Codes (E3700-E3799):**
- `E3701`: Checkpoint creation failed (MCP server error, Redis/PostgreSQL write failed)
- `E3702`: Checkpoint not found (checkpoint_id does not exist)
- `E3703`: Checkpoint restoration failed (corrupted checkpoint data, deserialization error)
- `E3704`: State conflict detected (concurrent tool executions modified same state)
- `E3705`: Delta encoding failed (unable to compute diff from parent checkpoint)
- `E3706`: Compression failed (gzip/zstd compression error)
- `E3707`: TTL expired (micro-checkpoint deleted, unable to resume)
- `E3708`: Archive retrieval failed (S3 Glacier restore in progress, ETA hours)

**Gap Integration:**
- **G-015 (Medium):** Checkpoint diff/delta encoding implemented via `delta_encoding.enabled` flag. When enabled and checkpoint > 100 KB, store only changed state fields with `parent_checkpoint_id` reference.
- **G-016 (Low):** Checkpoint compression threshold tuning via `compression.threshold_kb` parameter. Auto-tune by measuring checkpoint size distribution, compress if > 10 KB (gzip recommended, benchmarked vs zstd).

---

## Section 4: Interfaces

### 4.1 Provided Interfaces

#### 4.1.1 tool.invoke() - Primary Tool Execution Interface (BC-2)

**Interface Type:** Synchronous/Asynchronous REST API (JSON over HTTP) or gRPC (protobuf)

**Purpose:** Primary interface for L11 (Integration Layer) to invoke tools on behalf of agents. Supports synchronous execution for short-running tools (< 30s) and asynchronous execution for long-running tools (> 30s) with polling.

**Python Protocol Definition:**

```python
from typing import Protocol, Optional, Dict, List, Any, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# ========== Enums ==========

class ToolInvocationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"
    PENDING_APPROVAL = "pending_approval"

class ToolErrorCode(str, Enum):
    # Client errors
    INVALID_PARAMETERS = "invalid_parameters"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_VERSION_NOT_FOUND = "tool_version_not_found"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"

    # Server errors
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    SANDBOX_FAILURE = "sandbox_failure"
    EXTERNAL_API_ERROR = "external_api_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"

    # Phase 15 errors
    DOCUMENT_NOT_FOUND = "document_not_found"
    DOCUMENT_UNAVAILABLE = "document_unavailable"
    DOCUMENT_VERSION_CONFLICT = "document_version_conflict"

    # Phase 16 errors
    CHECKPOINT_FAILED = "checkpoint_failed"
    RESUME_FAILED = "resume_failed"
    STATE_CONFLICT = "state_conflict"

    # Generic
    INTERNAL_ERROR = "internal_error"

# ========== Request Data Classes ==========

@dataclass
class AgentContext:
    """Agent identity and session context from L02 (BC-1)."""
    agent_did: str  # Decentralized Identifier for agent
    tenant_id: str  # Multi-tenancy isolation
    user_did: Optional[str] = None  # End user (if applicable)
    session_id: str = ""  # Session for context tracking

@dataclass
class ResourceLimits:
    """Resource limits inherited from agent and sub-allocated to tool."""
    cpu_millicore_limit: Optional[int] = None
    memory_mb_limit: Optional[int] = None
    timeout_seconds: Optional[int] = None
    network_bandwidth_mbps: Optional[int] = None

@dataclass
class DocumentContext:
    """Phase 15 - Document context for tool execution."""
    document_refs: Optional[List[str]] = None  # URIs (e.g., "doc://spec-v1.0")
    version_pinning: bool = False  # Pin document versions for consistency
    query: Optional[str] = None  # Semantic search query

@dataclass
class CheckpointConfig:
    """Phase 16 - Checkpoint configuration for resumable operations."""
    enable_checkpointing: bool = True
    checkpoint_interval_seconds: int = 30
    resume_from_checkpoint_id: Optional[str] = None

@dataclass
class ExecutionOptions:
    """Execution behavior options."""
    async_mode: bool = False  # Synchronous by default
    priority: Literal["low", "normal", "high"] = "normal"
    idempotency_key: Optional[str] = None  # Prevent duplicate invocations
    require_approval: bool = False  # Human-in-the-loop approval

@dataclass
class ToolInvokeRequest:
    """Request to invoke a tool on behalf of an agent."""
    # Core tool identification
    tool_id: str
    tool_version: str  # Semantic version (e.g., "1.2.0")
    invocation_id: str  # Unique invocation ID (UUID)

    # Agent context (from L02 via BC-1)
    agent_context: AgentContext

    # Tool parameters (validated against tool manifest schema)
    parameters: Dict[str, Any]

    # Optional overrides and configurations
    resource_limits: Optional[ResourceLimits] = None
    document_context: Optional[DocumentContext] = None
    checkpoint_config: Optional[CheckpointConfig] = None
    execution_options: Optional[ExecutionOptions] = None

    # **NEW: Capability Token (Gap G-006)**
    capability_token: str  # JWT (RS256) with tool permissions

# ========== Response Data Classes ==========

@dataclass
class ToolError:
    """Structured error information."""
    code: ToolErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False

@dataclass
class DocumentAccess:
    """Phase 15 - Document access metadata."""
    document_id: str
    document_version: str
    access_count: int

@dataclass
class CheckpointMetadata:
    """Phase 16 - Checkpoint metadata."""
    checkpoint_id: str
    checkpoint_type: Literal["micro", "macro", "named"]
    timestamp: str  # ISO 8601

@dataclass
class ExecutionMetadata:
    """Execution metrics and resource usage."""
    duration_ms: int
    started_at: str  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601

    # Resource usage
    cpu_used_millicore_seconds: int = 0
    memory_peak_mb: int = 0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0

    # Phase 15 - Document access
    documents_accessed: Optional[List[DocumentAccess]] = None

    # Phase 16 - Checkpoints created
    checkpoints_created: Optional[List[CheckpointMetadata]] = None

@dataclass
class PollingInfo:
    """Async mode polling information."""
    status_url: str  # URL to poll for status
    estimated_completion_seconds: Optional[int] = None

@dataclass
class ToolInvokeResponse:
    """Response from tool invocation."""
    invocation_id: str
    status: ToolInvocationStatus

    # Success response
    result: Optional[Any] = None  # Tool-specific result (validated)

    # Error response
    error: Optional[ToolError] = None

    # Execution metadata
    execution_metadata: ExecutionMetadata = None

    # Phase 16 - Checkpoint reference (for async/long-running)
    checkpoint_ref: Optional[str] = None

    # Async mode tracking
    polling_info: Optional[PollingInfo] = None

# ========== Protocol ==========

class ToolExecutionService(Protocol):
    """Tool Execution Layer service interface (BC-2)."""

    def invoke(self, request: ToolInvokeRequest) -> ToolInvokeResponse:
        """
        Invoke a tool on behalf of an agent.

        Args:
            request: Tool invocation request with parameters and context.

        Returns:
            Tool invocation response with result or error.

        Raises:
            PermissionDenied: If capability token invalid or ABAC check fails.
            ToolNotFound: If tool_id or tool_version does not exist.
            RateLimitExceeded: If tool exhausted API quota.
            CircuitBreakerOpen: If external API circuit breaker is open.
            Timeout: If tool execution exceeds timeout limit.
        """
        ...
```

**Capability Token Format (Gap G-006):**

JWT (RS256) structure for capability-based authorization:
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "tool_id": "analyze_code",
    "tool_version": "^2.0.0",
    "agent_did": "did:agent:xyz789",
    "tenant_id": "tenant_acme",
    "allowed_operations": ["execute"],
    "filesystem_permissions": {
      "allowed_paths": ["/workspace/tool1"],
      "mode": "rw"
    },
    "network_permissions": {
      "allowed_hosts": ["api.example.com"],
      "allowed_ports": [443]
    },
    "credential_permissions": {
      "allowed_secrets": ["aws_s3_read", "external_api_token"]
    },
    "exp": 1673980800,
    "iat": 1673977200,
    "iss": "l02-agent-runtime"
  },
  "signature": "..."
}
```

**Gap Integration:**
- **G-006 (Critical):** Capability token format fully specified as JWT (RS256) with claims for tool permissions, expiration, agent identity.
- **G-020 (High):** Multi-tool workflow orchestration supported via L11 calling `tool.invoke()` sequentially or in parallel based on workflow DAG.

---

#### 4.1.2 tool.list() - Tool Discovery Interface

**Purpose:** Query available tools with filtering and semantic search.

**Python Protocol Definition:**
```python
@dataclass
class ToolListRequest:
    """Request to list available tools."""
    agent_context: AgentContext
    filters: Optional[Dict[str, Any]] = None  # category, tags
    capability_query: Optional[str] = None  # Semantic search query
    pagination: Optional[Dict[str, int]] = None  # page, page_size

@dataclass
class ToolSummary:
    """Tool summary for listing."""
    tool_id: str
    tool_name: str
    description: str
    category: str
    versions: List[str]  # Available versions
    latest_version: str
    tags: List[str]
    requires_approval: bool  # HITL flag

@dataclass
class ToolListResponse:
    """Response with list of available tools."""
    tools: List[ToolSummary]
    total_count: int
    page: int
    page_size: int
```

---

#### 4.1.3 tool.status() - Execution Status Query

**Purpose:** Query status of tool invocation (for async mode).

**Python Protocol Definition:**
```python
@dataclass
class ToolStatusRequest:
    """Request to query tool invocation status."""
    invocation_id: str
    agent_context: AgentContext

@dataclass
class ToolStatusResponse:
    """Response with tool invocation status."""
    invocation_id: str
    status: ToolInvocationStatus
    progress_percent: Optional[int] = None  # For long-running tools
    current_phase: Optional[str] = None  # E.g., "parsing", "processing"
    error: Optional[ToolError] = None
    latest_checkpoint: Optional[CheckpointMetadata] = None  # Phase 16
```

---

#### 4.1.4 tool.cancel() - Execution Cancellation

**Purpose:** Cancel running tool invocation.

**Python Protocol Definition:**
```python
@dataclass
class ToolCancelRequest:
    """Request to cancel tool invocation."""
    invocation_id: str
    agent_context: AgentContext
    reason: Optional[str] = None  # Cancellation reason

@dataclass
class ToolCancelResponse:
    """Response to cancellation request."""
    invocation_id: str
    cancelled: bool
    message: str  # E.g., "Cancellation in progress" or "Already completed"
```

---

### 4.2 Required Interfaces

#### 4.2.1 Agent Sandbox Context (from L02, BC-1)

**Provider:** L02 (Agent Runtime Layer)
**Direction:** L02 -> L03
**Purpose:** Provide parent sandbox context for nested tool sandbox creation.

**Interface Contract:**
```python
@dataclass
class AgentSandboxContext:
    """Parent sandbox context from Agent Runtime Layer."""
    agent_did: str
    tenant_id: str
    parent_sandbox_id: str  # Kubernetes Sandbox CRD ID

    resource_limits: ResourceLimits  # CPU, memory, timeout
    network_policy: NetworkPolicy  # Allowed hosts, ports, DNS
    filesystem_policy: FilesystemPolicy  # Mount paths, permissions

@dataclass
class NetworkPolicy:
    """Network policy for tool execution."""
    allowed_hosts: List[str]  # Hostnames or IP addresses
    allowed_ports: List[int]  # TCP/UDP ports
    dns_servers: List[str]  # DNS resolver IPs

@dataclass
class FilesystemPolicy:
    """Filesystem policy for tool execution."""
    mounts: List[Mount]

@dataclass
class Mount:
    """Filesystem mount."""
    path: str  # Mount path (e.g., "/workspace")
    mode: Literal["ro", "rw"]  # Read-only or read-write
```

---

#### 4.2.2 ABAC Policy Engine (from L01)

**Provider:** L01 (Agentic Data Layer - ABAC Engine)
**Direction:** L03 -> L01 (request), L01 -> L03 (response)
**Purpose:** Query attribute-based access control policies for tool permissions.

**Interface Contract:**
```python
@dataclass
class ABACCheckRequest:
    """Request to check ABAC policy."""
    agent_id: str  # Agent DID
    resource_type: str  # "tool"
    resource_id: str  # Tool ID
    action: str  # "execute"
    context: Dict[str, Any]  # Filesystem paths, network endpoints, credentials

@dataclass
class ABACCheckResponse:
    """Response from ABAC policy check."""
    allowed: bool
    reason: Optional[str] = None  # Policy ID or denial reason
    cache_ttl_seconds: int = 300  # Cache TTL for this decision
```

**Endpoint:** `POST /api/v1/abac/check-permission`
**Timeout:** 500ms (fast fail for real-time invocation)

---

#### 4.2.3 Event Store (from L01)

**Provider:** L01 (Agentic Data Layer - Event Store)
**Direction:** L03 -> L01 (publish events)
**Purpose:** Publish tool invocation events for audit, analytics, and downstream processing.

**Interface Contract:** Apache Kafka topic: `tool-execution-events`
**Format:** CloudEvents 1.0 (see Section 4.3)

---

#### 4.2.4 Document Bridge (from Phase 15 MCP)

**Provider:** document-consolidator MCP server (Phase 15)
**Direction:** L03 <-> MCP (bidirectional JSON-RPC)
**Purpose:** Access authoritative documents during tool execution.

**Interface Contract:**
- MCP JSON-RPC methods: `get_source_of_truth`, `search_documents`, `find_overlaps`, `get_document_metadata`, `ingest_document`
- Transport: stdio (stdin/stdout pipes)
- Timeout: 30s per request

---

#### 4.2.5 State Bridge (from Phase 16 MCP)

**Provider:** context-orchestrator MCP server (Phase 16)
**Direction:** L03 <-> MCP (bidirectional JSON-RPC)
**Purpose:** Checkpoint and restore tool execution state.

**Interface Contract:**
- MCP JSON-RPC methods: `save_context_snapshot`, `create_checkpoint`, `rollback_to`, `get_unified_context`, `switch_task`
- Transport: stdio (stdin/stdout pipes)
- Timeout: 10s per request

---

### 4.3 Events Published

All events published in **CloudEvents 1.0** format to Kafka topic `tool-execution-events`. Partition key: `tenant_id` (tenant isolation).

#### 4.3.1 tool.invoked

**Published:** When tool invocation starts (after permission checks pass).

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.tool.invoked",
  "source": "tool-execution-layer",
  "id": "<invocation_id>",
  "time": "2026-01-14T10:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "agent_did": "did:agent:xyz789",
    "tenant_id": "tenant_acme",
    "tool_id": "analyze_code",
    "tool_version": "2.1.0",
    "parameters": {/* PII-sanitized */},
    "async_mode": false,
    "priority": "normal"
  }
}
```

---

#### 4.3.2 tool.succeeded

**Published:** When tool invocation completes successfully.

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.tool.succeeded",
  "source": "tool-execution-layer",
  "id": "<event_id>",
  "time": "2026-01-14T10:35:00Z",
  "datacontenttype": "application/json",
  "data": {
    "invocation_id": "<invocation_id>",
    "agent_did": "did:agent:xyz789",
    "tenant_id": "tenant_acme",
    "tool_id": "analyze_code",
    "tool_version": "2.1.0",
    "result_summary": "Analysis complete: 15 issues found",
    "execution_metadata": {
      "duration_ms": 12340,
      "cpu_used_millicore_seconds": 6170,
      "memory_peak_mb": 512,
      "documents_accessed": [
        {"document_id": "doc-123", "document_version": "v2.0", "access_count": 3}
      ],
      "checkpoints_created": [
        {"checkpoint_id": "cp-456", "checkpoint_type": "macro", "timestamp": "2026-01-14T10:34:00Z"}
      ]
    }
  }
}
```

---

#### 4.3.3 tool.failed

**Published:** When tool invocation fails (error, timeout, permission denied).

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.tool.failed",
  "source": "tool-execution-layer",
  "id": "<event_id>",
  "time": "2026-01-14T10:31:00Z",
  "datacontenttype": "application/json",
  "data": {
    "invocation_id": "<invocation_id>",
    "agent_did": "did:agent:xyz789",
    "tenant_id": "tenant_acme",
    "tool_id": "analyze_code",
    "tool_version": "2.1.0",
    "error": {
      "code": "timeout",
      "message": "Tool execution exceeded 30s timeout",
      "retryable": true
    },
    "execution_metadata": {
      "duration_ms": 30100,
      "checkpoints_created": [
        {"checkpoint_id": "cp-789", "checkpoint_type": "micro", "timestamp": "2026-01-14T10:30:30Z"}
      ]
    }
  }
}
```

---

#### 4.3.4 tool.timeout

**Published:** When tool invocation times out (subset of tool.failed, for specific monitoring).

**Schema:** Same as `tool.failed` with `error.code: "timeout"`.

---

#### 4.3.5 tool.checkpoint.created (Phase 16)

**Published:** When checkpoint created during long-running tool execution.

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.tool.checkpoint.created",
  "source": "tool-execution-layer",
  "id": "<event_id>",
  "time": "2026-01-14T10:30:30Z",
  "datacontenttype": "application/json",
  "data": {
    "invocation_id": "<invocation_id>",
    "checkpoint_id": "cp-789",
    "checkpoint_type": "micro",
    "progress_percent": 25,
    "current_phase": "parsing"
  }
}
```

---

#### 4.3.6 circuit.opened

**Published:** When circuit breaker transitions to open state for external API.

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.circuit.opened",
  "source": "tool-execution-layer",
  "id": "<event_id>",
  "time": "2026-01-14T10:32:00Z",
  "datacontenttype": "application/json",
  "data": {
    "circuit_name": "external-api-example-com",
    "tool_id": "analyze_code",
    "failure_rate": 65.4,
    "failure_count": 32,
    "window_size": 100,
    "reason": "Failure rate 65.4% exceeded threshold 50%"
  }
}
```

---

#### 4.3.7 circuit.closed

**Published:** When circuit breaker transitions from half-open to closed state.

**Schema:**
```json
{
  "specversion": "1.0",
  "type": "ai.agent.circuit.closed",
  "source": "tool-execution-layer",
  "id": "<event_id>",
  "time": "2026-01-14T10:35:00Z",
  "datacontenttype": "application/json",
  "data": {
    "circuit_name": "external-api-example-com",
    "tool_id": "analyze_code",
    "test_success_count": 10,
    "reason": "Half-open test calls succeeded"
  }
}
```

---

### 4.4 Events Consumed

*None.* L03 is an event producer only. Event consumption handled by downstream layers (L01 Event Store, L11 Integration Layer, external SIEM systems).

---

## Section 5: Data Model

### 5.1 Owned Entities

#### 5.1.1 ToolDefinition (PostgreSQL)

**Purpose:** Registry entry for a tool with capability manifest and semantic embedding.

**Schema:**
```sql
CREATE TABLE tool_definitions (
  tool_id VARCHAR(255) PRIMARY KEY,
  tool_name VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  category VARCHAR(100) NOT NULL,  -- e.g., "data_access", "computation", "external_api"
  tags TEXT[],  -- Array of tags
  latest_version VARCHAR(50) NOT NULL,  -- Semantic version
  source_type VARCHAR(50) NOT NULL,  -- "mcp", "openapi", "langchain", "native"
  source_metadata JSONB,  -- Source-specific metadata (MCP server ID, OpenAPI spec URL)
  deprecation_state VARCHAR(20) DEFAULT 'active',  -- "active", "deprecated", "sunset", "removed"
  deprecation_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Gap G-001: Tool capability manifest fields
  requires_approval BOOLEAN DEFAULT FALSE,  -- HITL approval required
  default_timeout_seconds INTEGER DEFAULT 30,
  default_cpu_millicore_limit INTEGER DEFAULT 500,
  default_memory_mb_limit INTEGER DEFAULT 1024,

  -- Permissions (Gap G-001)
  required_permissions JSONB,  -- {filesystem: [...], network: [...], credentials: [...]}

  -- Result schema (Gap G-010)
  result_schema JSONB,  -- JSON Schema 2020-12 for output validation

  -- Retry policy (Gap G-001)
  retry_policy JSONB,  -- {max_attempts, base_delay_ms, max_delay_ms, retryable_errors}

  -- Circuit breaker config (Gap G-001)
  circuit_breaker_config JSONB,  -- {failure_rate_threshold, window_size, wait_duration_seconds}

  -- Semantic search (pgvector)
  description_embedding VECTOR(768)  -- Ollama Mistral 7B embeddings
);

CREATE INDEX idx_tool_category ON tool_definitions(category);
CREATE INDEX idx_tool_deprecation_state ON tool_definitions(deprecation_state);
CREATE INDEX idx_tool_description_embedding ON tool_definitions USING ivfflat (description_embedding vector_cosine_ops);
```

**Gap Integration:**
- **G-001 (High):** Tool capability manifest schema fully defined with all required fields (permissions, result_schema, timeout, retry policy, circuit breaker config).
- **G-010 (Critical):** Result validation schema stored in `result_schema` field as JSON Schema 2020-12.

---

#### 5.1.2 ToolVersion (PostgreSQL)

**Purpose:** Version history for tools supporting multiple concurrent versions.

**Schema:**
```sql
CREATE TABLE tool_versions (
  version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id VARCHAR(255) REFERENCES tool_definitions(tool_id) ON DELETE CASCADE,
  version VARCHAR(50) NOT NULL,  -- Semantic version (e.g., "2.1.0")
  manifest JSONB NOT NULL,  -- Full tool manifest (parameters schema, return schema)
  compatibility_range VARCHAR(100),  -- Compatible agent versions (e.g., "^1.0.0")
  release_notes TEXT,
  deprecated_in_favor_of VARCHAR(50),  -- Version to migrate to
  created_at TIMESTAMP DEFAULT NOW(),
  removed_at TIMESTAMP,  -- Set when version removed (Gap G-003)

  UNIQUE(tool_id, version)
);

CREATE INDEX idx_tool_version_tool_id ON tool_versions(tool_id);
CREATE INDEX idx_tool_version_version ON tool_versions(version);
```

**Gap Integration:**
- **G-002 (Medium):** Semantic versioning conflict resolution supported via `compatibility_range` field and query logic to find highest compatible version.
- **G-003 (Medium):** Tool deprecation workflow implemented via `deprecated_in_favor_of` and `removed_at` fields.

---

#### 5.1.3 ToolInvocation (PostgreSQL)

**Purpose:** Execution record for tool invocations (audit trail, analytics).

**Schema:**
```sql
CREATE TABLE tool_invocations (
  invocation_id UUID PRIMARY KEY,
  tool_id VARCHAR(255) NOT NULL,
  tool_version VARCHAR(50) NOT NULL,
  agent_did VARCHAR(255) NOT NULL,
  tenant_id VARCHAR(255) NOT NULL,
  session_id VARCHAR(255),

  parameters JSONB,  -- PII-sanitized
  result JSONB,  -- Tool output

  status VARCHAR(50) NOT NULL,  -- "success", "error", "timeout", etc.
  error_code VARCHAR(100),
  error_message TEXT,

  -- Execution metadata
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  duration_ms INTEGER,
  cpu_used_millicore_seconds INTEGER,
  memory_peak_mb INTEGER,
  network_bytes_sent BIGINT,
  network_bytes_received BIGINT,

  -- Phase 15 integration
  documents_accessed JSONB,  -- [{document_id, version, access_count}]

  -- Phase 16 integration
  checkpoints_created JSONB,  -- [{checkpoint_id, type, timestamp}]
  checkpoint_ref VARCHAR(255),  -- Final checkpoint ID for resumable operations

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invocation_agent ON tool_invocations(agent_did);
CREATE INDEX idx_invocation_tenant ON tool_invocations(tenant_id);
CREATE INDEX idx_invocation_tool ON tool_invocations(tool_id);
CREATE INDEX idx_invocation_status ON tool_invocations(status);
CREATE INDEX idx_invocation_started_at ON tool_invocations(started_at);
```

---

#### 5.1.4 ToolCheckpoint (Phase 16, PostgreSQL + Redis)

**Purpose:** Checkpoint state for resumable tool operations.

**PostgreSQL Schema (cold checkpoints):**
```sql
CREATE TABLE tool_checkpoints (
  checkpoint_id UUID PRIMARY KEY,
  invocation_id UUID REFERENCES tool_invocations(invocation_id) ON DELETE CASCADE,
  checkpoint_type VARCHAR(20) NOT NULL,  -- "micro", "macro", "named"
  checkpoint_label VARCHAR(255),  -- For named checkpoints

  parent_checkpoint_id UUID,  -- For delta encoding (Gap G-015)
  is_delta BOOLEAN DEFAULT FALSE,

  state JSONB NOT NULL,  -- Tool execution state
  state_compressed BYTEA,  -- gzip/zstd compressed state (if > 10 KB, Gap G-016)
  state_size_bytes INTEGER,

  progress_percent INTEGER,
  current_phase VARCHAR(100),

  -- Phase 15 integration
  document_versions JSONB,  -- {document_id: version} for version pinning

  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,  -- TTL for micro-checkpoints
  archived_at TIMESTAMP  -- When moved to S3 Glacier
);

CREATE INDEX idx_checkpoint_invocation ON tool_checkpoints(invocation_id);
CREATE INDEX idx_checkpoint_type ON tool_checkpoints(checkpoint_type);
CREATE INDEX idx_checkpoint_expires_at ON tool_checkpoints(expires_at) WHERE expires_at IS NOT NULL;
```

**Redis Schema (hot checkpoints):**
```
Key: checkpoint:tool:{invocation_id}:latest
Value: JSON {
  checkpoint_id: "...",
  invocation_id: "...",
  state: {...},
  progress_percent: 25,
  current_phase: "parsing",
  timestamp: "2026-01-14T10:30:30Z"
}
TTL: 3600 seconds (1 hour)
```

**Gap Integration:**
- **G-015 (Medium):** Checkpoint diff/delta encoding via `parent_checkpoint_id` and `is_delta` fields. When enabled, only changed state stored with reference to parent.
- **G-016 (Low):** Checkpoint compression threshold via `state_compressed` field. State compressed with gzip if > 10 KB, stored in BYTEA column.

---

#### 5.1.5 CircuitState (Redis)

**Purpose:** Distributed circuit breaker state for external APIs.

**Redis Schema:**
```
Key: circuit:state:{circuit_name}
Value: JSON {
  state: "closed" | "open" | "half_open",
  failure_count: 32,
  success_count: 5,
  slow_call_count: 3,
  sliding_window: [
    {timestamp: "2026-01-14T10:31:00Z", result: "failure", duration_ms: 5200},
    ...
  ],
  last_failure_time: "2026-01-14T10:32:00Z",
  opened_at: "2026-01-14T10:32:00Z",
  last_state_transition: "2026-01-14T10:32:00Z",
  half_open_test_calls_permitted: 10,
  half_open_test_calls_completed: 0
}
TTL: None (persistent until circuit removed)
```

---

#### 5.1.6 ExternalServiceCredential (HashiCorp Vault)

**Purpose:** Ephemeral credentials for external service access.

**Vault Path:** `secret/tool-execution/{tool_id}/{credential_name}`

**Schema:**
```json
{
  "credential_type": "api_key" | "oauth_token" | "aws_iam" | "gcp_sa" | "azure_ad",
  "credential_value": "...",  -- Encrypted by Vault
  "expires_at": "2026-01-14T11:00:00Z",  -- Ephemeral lifetime
  "rotation_schedule": "daily" | "weekly" | "on_demand",
  "metadata": {
    "service_name": "external-api-example-com",
    "scopes": ["read", "write"]
  }
}
```

---

### 5.2 Configuration Schemas (JSON Schema 2020-12)

#### 5.2.1 Tool Manifest Schema

**Purpose:** Define tool parameters, return schema, permissions, and execution config.

**JSON Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://tool-execution-layer/schemas/tool-manifest.json",
  "title": "Tool Manifest",
  "type": "object",
  "properties": {
    "tool_id": {"type": "string"},
    "tool_name": {"type": "string"},
    "description": {"type": "string"},
    "category": {
      "type": "string",
      "enum": ["data_access", "computation", "external_api", "file_system", "llm_interaction"]
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },

    "parameters_schema": {
      "type": "object",
      "description": "JSON Schema 2020-12 for input parameters"
    },

    "result_schema": {
      "type": "object",
      "description": "JSON Schema 2020-12 for output validation (Gap G-010)"
    },

    "permissions": {
      "type": "object",
      "properties": {
        "filesystem": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "path": {"type": "string"},
              "mode": {"type": "string", "enum": ["ro", "rw"]}
            }
          }
        },
        "network": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "host": {"type": "string"},
              "port": {"type": "integer"}
            }
          }
        },
        "credentials": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },

    "execution_config": {
      "type": "object",
      "properties": {
        "default_timeout_seconds": {"type": "integer", "default": 30},
        "default_cpu_millicore_limit": {"type": "integer", "default": 500},
        "default_memory_mb_limit": {"type": "integer", "default": 1024},
        "requires_approval": {"type": "boolean", "default": false},
        "retry_policy": {
          "type": "object",
          "properties": {
            "max_attempts": {"type": "integer", "default": 3},
            "base_delay_ms": {"type": "integer", "default": 1000},
            "max_delay_ms": {"type": "integer", "default": 60000},
            "retryable_errors": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        },
        "circuit_breaker_config": {
          "type": "object",
          "properties": {
            "failure_rate_threshold": {"type": "number", "minimum": 0, "maximum": 100},
            "sliding_window_size": {"type": "integer"},
            "wait_duration_seconds": {"type": "integer"}
          }
        }
      }
    }
  },
  "required": ["tool_id", "tool_name", "version", "parameters_schema"]
}
```

**Gap Integration:**
- **G-001 (High):** Complete tool manifest schema with all required fields (permissions, result_schema, execution_config).

---

### 5.3 Data Flows (ASCII Diagrams)

#### 5.3.1 Tool Invocation Flow with Phase 15 Document Context

```
+========================================================================+
|                 Tool Invocation with Document Context                  |
+========================================================================+

L11 Integration Layer
  |
  | 1. tool.invoke(request)
  |    - tool_id, parameters
  |    - document_context: {document_refs, version_pinning}
  v
+------------------------+
| L03 Permission Checker |
+------------------------+
  |
  | 2. Validate capability token (JWT RS256)
  | 3. Query ABAC Engine (permission check)
  v
+------------------------+
| L03 Tool Registry      |
+------------------------+
  |
  | 4. Lookup tool manifest (PostgreSQL)
  | 5. Resolve version (SemVer conflict resolution, Gap G-002)
  v
+------------------------+
| L03 Document Bridge    |
| (Phase 15)             |
+------------------------+
  |
  | 6. Check document permissions (ABAC, Gap G-013)
  | 7. Query document cache (Redis, 5-min TTL)
  |    - Cache miss -> MCP call to document-consolidator
  | 8. Pin document versions (if version_pinning=true)
  v
+--------------------------+
| document-consolidator    |
| (MCP Server, Phase 15)   |
+--------------------------+
  |
  | 9. get_source_of_truth(document_refs)
  | 10. Return document content + version
  v
+------------------------+
| L03 Document Bridge    |
+------------------------+
  |
  | 11. Cache documents in Redis
  | 12. Build document context for tool
  v
+------------------------+
| L03 Tool Executor      |
+------------------------+
  |
  | 13. Create nested sandbox (BC-1)
  |     - Inherit agent resource limits
  |     - Enforce tool filesystem/network restrictions
  | 14. Inject credentials from Vault (ephemeral)
  | 15. Inject document context as environment variables
  | 16. Execute tool binary in sandbox
  v
+------------------------+
| Tool Process           |
| (gVisor/Firecracker)   |
+------------------------+
  |
  | 17. Process parameters
  | 18. Access documents from environment
  | 19. Call external APIs (via External Adapter Manager)
  | 20. Return result
  v
+------------------------+
| L03 Result Validator   |
+------------------------+
  |
  | 21. Validate result against result_schema (Gap G-010)
  | 22. Type coercion (Gap G-011)
  | 23. Sanitization (SQL injection, XSS, Gap G-011)
  v
+------------------------+
| L03 Audit Logger       |
+------------------------+
  |
  | 24. Publish tool.succeeded event (CloudEvents, Gap G-018)
  |     - Include documents_accessed metadata
  v
L11 Integration Layer
  |
  | 25. ToolInvokeResponse(status=success, result=...)
```

---

#### 5.3.2 Long-Running Tool Flow with Phase 16 Checkpoints

```
+========================================================================+
|            Long-Running Tool with Hybrid Checkpointing                 |
+========================================================================+

L11 Integration Layer
  |
  | 1. tool.invoke(request)
  |    - async_mode=true
  |    - checkpoint_config: {enable_checkpointing=true, interval=30s}
  v
+------------------------+
| L03 Tool Executor      |
+------------------------+
  |
  | 2. Create nested sandbox
  | 3. Start tool execution (async)
  | 4. Return ToolInvokeResponse(status=running, polling_info)
  v
+------------------------+
| Tool Process           |
| (Long-running, 5 min)  |
+------------------------+
  |
  | ... processing ...
  | T=30s
  v
+------------------------+
| L03 State Bridge       |
| (Phase 16)             |
+------------------------+
  |
  | 5. Micro-checkpoint timer triggers (30s interval)
  | 6. Serialize tool state (progress, phase, counters)
  | 7. Store in Redis (hot checkpoint, TTL 1 hour)
  v
+--------------------------+
| context-orchestrator     |
| (MCP Server, Phase 16)   |
+--------------------------+
  |
  | 8. save_context_snapshot(taskId, updates, syncToFile=false)
  | 9. Redis: checkpoint:tool:{invocation_id}:latest
  v
+------------------------+
| Tool Process           |
+------------------------+
  |
  | ... processing continues ...
  | T=60s (milestone: "parsing complete")
  v
+------------------------+
| L03 State Bridge       |
+------------------------+
  |
  | 10. Macro-checkpoint event triggered (milestone)
  | 11. Serialize tool state + document versions
  | 12. Store in PostgreSQL (cold checkpoint, 90-day retention)
  | 13. Delta encoding if state > 100 KB (Gap G-015)
  v
+--------------------------+
| context-orchestrator     |
| (MCP Server, Phase 16)   |
+--------------------------+
  |
  | 14. create_checkpoint(taskId, label="parsing-complete")
  | 15. PostgreSQL: tool_checkpoints table
  v
+------------------------+
| Tool Process           |
+------------------------+
  |
  | ... processing continues ...
  | T=150s (timeout or crash)
  v
+------------------------+
| L03 Tool Executor      |
+------------------------+
  |
  | 16. Detect timeout/crash
  | 17. Kill tool process
  | 18. Publish tool.failed event
  v
L11 Integration Layer
  |
  | 19. Retry with resume_from_checkpoint_id
  v
+------------------------+
| L03 State Bridge       |
+------------------------+
  |
  | 20. Retrieve latest checkpoint from Redis
  | 21. If Redis expired, fallback to PostgreSQL macro-checkpoint
  | 22. Deserialize state
  v
+------------------------+
| L03 Tool Executor      |
+------------------------+
  |
  | 23. Create new sandbox
  | 24. Restore tool state from checkpoint
  | 25. Resume execution from last phase
  v
+------------------------+
| Tool Process           |
| (Resumed)              |
+------------------------+
  |
  | ... processing from checkpoint ...
  | T=300s (completion)
  v
+------------------------+
| L03 Audit Logger       |
+------------------------+
  |
  | 26. Publish tool.succeeded event
  |     - Include checkpoints_created metadata
  v
L11 Integration Layer
  |
  | 27. ToolInvokeResponse(status=success, result=...)
```

---

#### 5.3.3 Circuit Breaker State Flow

```
+========================================================================+
|                  Circuit Breaker State Transitions                     |
+========================================================================+

INITIAL STATE: CLOSED
+------------------------+
| Tool calls external    |
| API via External       |
| Adapter Manager        |
+------------------------+
  |
  | Success/Failure tracked in Redis
  | Key: circuit:state:{circuit_name}
  v
+------------------------+
| Circuit Breaker        |
| Controller             |
+------------------------+
  |
  | Failure rate calculated (sliding window)
  | failure_rate = failures / (failures + successes)
  |
  | IF failure_rate > threshold (e.g., 50%)
  v
STATE TRANSITION: CLOSED -> OPEN
+------------------------+
| Circuit Breaker        |
| State: OPEN            |
+------------------------+
  |
  | 1. Block all requests to external API
  | 2. Publish circuit.opened event (Gap G-008)
  |    - Redis pub/sub: circuit:state:changes
  | 3. Dependent tools notified (subscribe to channel)
  | 4. Start wait_duration timer (e.g., 60s)
  v
  ... wait_duration elapses ...
  |
STATE TRANSITION: OPEN -> HALF-OPEN
+------------------------+
| Circuit Breaker        |
| State: HALF-OPEN       |
+------------------------+
  |
  | 5. Allow limited test requests (e.g., 10)
  | 6. Canary strategy: gradually increase traffic (Gap G-009)
  |    - Start with 1% of requests
  |    - Increase to 10%, 50%, 100% if successful
  |
  | IF test requests succeed
  v
STATE TRANSITION: HALF-OPEN -> CLOSED
+------------------------+
| Circuit Breaker        |
| State: CLOSED          |
+------------------------+
  |
  | 7. Resume normal operations
  | 8. Publish circuit.closed event
  | 9. Reset failure counters
  |
  | IF test requests fail
  v
STATE TRANSITION: HALF-OPEN -> OPEN
+------------------------+
| Circuit Breaker        |
| State: OPEN            |
+------------------------+
  |
  | 10. Re-open circuit
  | 11. Restart wait_duration timer
  | 12. Publish circuit.opened event
```

---

## Gap Tracking Table

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| **G-001** | Tool capability manifest schema not fully defined | High | 5.1.1, 5.2.1 | Complete manifest schema defined in ToolDefinition PostgreSQL table and JSON Schema with all fields: permissions (filesystem, network, credentials), result_schema, timeout, retry_policy, circuit_breaker_config. |
| **G-002** | Semantic versioning conflict resolution for parallel versions | Medium | 3.3.1, 5.1.2 | Implemented via `compatibility_range` field in ToolVersion table and `max_versions_per_tool` retention policy in Tool Registry configuration. Query logic finds highest compatible version within agent's version range. |
| **G-003** | Tool deprecation workflow and migration paths | Medium | 3.3.1, 5.1.2 | Lifecycle states (active, deprecated, sunset, removed) defined in ToolDefinition.deprecation_state field. ToolVersion includes `deprecated_in_favor_of` and `removed_at` fields for migration guidance. `deprecation_warning_days` configuration triggers agent warnings. |
| **G-006** | Capability token format and signing mechanism | Critical | 4.1.1 | JWT (RS256) structure fully specified with claims for tool_id, tool_version, agent_did, tenant_id, allowed_operations, filesystem_permissions, network_permissions, credential_permissions, exp, iat, iss. Public key path configured in Permission Checker. |
| **G-007** | Permission cache invalidation on policy updates | High | 3.3.3 | Redis pub/sub subscription to `policy:updates` channel from Data Layer ABAC Engine. On notification, invalidate cached permissions in Redis (key pattern: `permission:cache:{agent_did}:{tool_id}:*`). |
| **G-008** | Circuit breaker transition notifications to dependent tools | Medium | 3.3.5, 5.3.3 | Redis pub/sub channel `circuit:state:changes` for circuit breaker state transitions. Dependent tools subscribe and adjust behavior (e.g., skip fallback API if also open). Events published on open, half-open, closed transitions. |
| **G-009** | Half-open state testing strategy (canary vs all-or-nothing) | Medium | 3.3.5, 5.3.3 | Configurable via `half_open_strategy` parameter in Circuit Breaker Controller config. Canary strategy: gradually increase traffic percentage (1% -> 10% -> 50% -> 100%) if test calls successful. All-or-nothing strategy: send all permitted test calls immediately. |
| **G-010** | Result validation schema definition and enforcement | Critical | 3.3.6, 5.1.1, 5.2.1 | JSON Schema 2020-12 stored in ToolDefinition.result_schema field and tool manifest. AJV validator enforces schema checks before returning results to agent. `strict_mode` flag rejects outputs that fail validation (E3501 error). |
| **G-011** | Type coercion and sanitization rules | High | 3.3.6 | Type coercion rules defined in Result Validator configuration: string -> number/integer/boolean/date. Sanitization patterns for SQL injection, XSS, command injection with configurable actions (reject, redact, escape). |
| **G-012** | Structured output validation against tool manifest | High | 3.3.6 | Implemented via AJV validator with JSON Schema 2020-12 from tool manifest `result_schema` field. `strict_mode` enforces validation, returns field-level errors (E3501-E3507). |
| **G-013** | Document access permission model (ABAC integration) | High | 3.3.7, 5.3.1 | ABAC permission check before MCP document retrieval. Query Data Layer ABAC Engine with `(agent_did, document_id, access_mode)` tuple. Cache permissions in Redis (5-min TTL). Document Bridge enforces permissions before returning documents to tools. |
| **G-014** | Bulk document retrieval optimization | Medium | 3.3.7 | Batched MCP requests for multiple documents. Send array of document_ids in single `tools/call` JSON-RPC request to document-consolidator. Reduce round-trips from N to 1. Cache batch results in Redis. |
| **G-015** | Checkpoint diff/delta encoding for large states | Medium | 3.3.8, 5.1.4 | Delta encoding enabled via State Bridge configuration `delta_encoding.enabled` flag. When checkpoint > 100 KB, store only changed state fields with `parent_checkpoint_id` reference in PostgreSQL tool_checkpoints table. `is_delta` flag indicates delta checkpoint. |
| **G-016** | Checkpoint compression threshold tuning | Low | 3.3.8, 5.1.4 | Compression threshold configurable via `compression.threshold_kb` parameter (default 10 KB). gzip compression recommended (benchmarked vs zstd). Compressed state stored in BYTEA column `state_compressed` in tool_checkpoints table. |

**Total Gaps Addressed in Part 1:** 13 out of 24 total gaps (54%)

**Remaining Gaps for Part 2 (Sections 6-10):** G-004, G-005, G-017, G-018, G-019, G-020, G-021, G-022

**Status:** All gaps targeted at Sections 1-5 have been fully addressed in this specification part.

---

**End of Part 1**
**Next Part:** tool-execution-spec-part2.md (Sections 6-10)
