# Tool Execution Layer Specification v1.0 - Part 2

**Document Status:** Draft
**Version:** 1.0 (Part 2 of 3)
**Date:** 2026-01-14
**Layer:** L03 - Tool Execution Layer
**Sections:** 6-10 (Integration, Reliability, Security, Observability, Configuration)
**Continuation of:** tool-execution-spec-part1.md

---

## Section 6: Integration with Data Layer

### 6.1 Relationship Model

L03 (Tool Execution Layer) has bidirectional integration with L01 (Agentic Data Layer) across multiple touchpoints:

| Touchpoint | Relationship | L03 Role | L01 Component | Data Flow |
|------------|--------------|----------|---------------|-----------|
| **Event Publishing** | Producer | Publisher | Event Store | L03 -> L01: tool invocation events (CloudEvents 1.0) |
| **ABAC Permissions** | Consumer | Query client | ABAC Engine | L03 -> L01: permission checks, L01 -> L03: allow/deny decisions |
| **Context Retrieval** | Consumer | Request client | Context Injector | L03 -> L01: context requests, L01 -> L03: credentials/config |
| **Tool Registry Storage** | Owner/Consumer | Data owner | PostgreSQL | L03 owns tool_definitions schema, L01 provides PostgreSQL instance |
| **Circuit Breaker State** | Owner/Consumer | State owner | Redis | L03 owns circuit state, L01 provides Redis instance |
| **Audit Streaming** | Producer | Publisher | Kafka | L03 -> L01: audit events for compliance/SIEM |

**Provider vs Consumer Summary:**
- **L03 Provides:** Tool execution capability, tool registry, circuit breaker state
- **L01 Provides:** Infrastructure (PostgreSQL, Redis, Kafka), ABAC decisions, agent context
- **Bidirectional:** L03 stores data in L01's infrastructure, queries L01's services

---

### 6.2 Agent Identity Integration

**Purpose:** Resolve Decentralized Identifiers (DIDs) for agent authentication and tool invocation tracking.

**Integration Pattern:**
```
L11 Integration Layer
  |
  | ToolInvokeRequest includes:
  | - agent_context.agent_did (e.g., "did:agent:xyz789")
  | - agent_context.tenant_id
  | - agent_context.user_did (optional)
  v
L03 Permission Checker
  |
  | 1. Validate DID format (did:agent:{uuid} or did:web:{domain})
  | 2. Query L01 DID Registry for DID Document
  |    - Endpoint: GET /api/v1/did/resolve/{did}
  | 3. Verify DID is active (not revoked, not expired)
  | 4. Extract public keys for JWT capability token verification
  v
L01 DID Registry
  |
  | Return DID Document:
  | {
  |   "id": "did:agent:xyz789",
  |   "verificationMethod": [{
  |     "id": "did:agent:xyz789#keys-1",
  |     "type": "JsonWebKey2020",
  |     "publicKeyJwk": {...}
  |   }],
  |   "authentication": ["did:agent:xyz789#keys-1"],
  |   "service": [{
  |     "id": "did:agent:xyz789#agent-runtime",
  |     "type": "AgentRuntime",
  |     "serviceEndpoint": "https://agent-runtime.example.com"
  |   }]
  | }
  v
L03 Permission Checker
  |
  | 5. Cache DID Document in Redis (TTL 1 hour)
  | 6. Use public key to verify capability token signature
  | 7. Proceed with tool invocation
```

**Error Handling:**
- DID not found: Return `E3201` (Invalid capability token)
- DID revoked: Return `E3202` (Expired capability token)
- DID Document malformed: Return `E3201` (Invalid capability token)
- L01 DID Registry unavailable: Use cached DID Document, fail if cache miss

**Caching Strategy:**
```
Redis Key: did:cache:{agent_did}
TTL: 3600 seconds (1 hour)
Value: DID Document JSON
Invalidation: Subscribe to Redis pub/sub channel `did:updates`
```

---

### 6.3 Event Integration

**Purpose:** Publish tool invocation lifecycle events to L01 Event Store for audit, analytics, and downstream workflows.

**Event Catalog:**
- `tool.invoked`: Tool execution started
- `tool.succeeded`: Tool execution completed successfully
- `tool.failed`: Tool execution failed (error, timeout, permission denied)
- `tool.timeout`: Tool execution exceeded timeout limit
- `tool.checkpoint.created`: Checkpoint created (Phase 16)
- `circuit.opened`: Circuit breaker opened for external API
- `circuit.closed`: Circuit breaker closed after recovery

**Transport:** Apache Kafka topic `tool-execution-events`

**Partition Strategy:** Partition by `tenant_id` for tenant isolation and ordered processing per tenant.

**Message Format:** CloudEvents 1.0 (see Section 4.3 for schemas)

**Delivery Guarantees:**
- **At-least-once delivery:** Kafka producer with `acks=all` and retries
- **Idempotent consumers:** Events include `invocation_id` for deduplication
- **Ordered per partition:** Events for same tenant processed in order

**Integration Code Example (Python):**
```python
from kafka import KafkaProducer
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured
import json

class EventPublisher:
    def __init__(self, kafka_bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # At-least-once delivery
            retries=3
        )

    def publish_tool_invoked(self, invocation_id: str, agent_did: str,
                            tenant_id: str, tool_id: str, tool_version: str,
                            parameters: dict):
        event = CloudEvent({
            "specversion": "1.0",
            "type": "ai.agent.tool.invoked",
            "source": "tool-execution-layer",
            "id": invocation_id,
            "datacontenttype": "application/json"
        }, {
            "agent_did": agent_did,
            "tenant_id": tenant_id,
            "tool_id": tool_id,
            "tool_version": tool_version,
            "parameters": self._sanitize_pii(parameters)  # Gap G-017
        })

        # Partition by tenant_id
        self.producer.send(
            topic="tool-execution-events",
            key=tenant_id.encode('utf-8'),
            value=to_structured(event)
        )
```

---

### 6.4 ABAC Integration

**Purpose:** Query L01 ABAC Engine for attribute-based access control decisions on tool invocations.

**Integration Flow:**
```
L03 Permission Checker receives ToolInvokeRequest
  |
  | 1. Extract capability token from request
  | 2. Validate JWT signature using agent DID public key
  | 3. Extract permissions from JWT claims:
  |    - filesystem_permissions: {allowed_paths, mode}
  |    - network_permissions: {allowed_hosts, allowed_ports}
  |    - credential_permissions: {allowed_secrets}
  v
L03 Permission Checker queries L01 ABAC Engine
  |
  | POST /api/v1/abac/check-permission
  | {
  |   "agent_id": "did:agent:xyz789",
  |   "resource_type": "tool",
  |   "resource_id": "analyze_code",
  |   "action": "execute",
  |   "context": {
  |     "filesystem_paths": ["/workspace/tool1"],
  |     "network_endpoints": ["api.example.com:443"],
  |     "credentials": ["aws_s3_read"]
  |   }
  | }
  v
L01 ABAC Engine evaluates policy
  |
  | Policy Example (OPA Rego):
  | allow {
  |   input.agent_id == "did:agent:xyz789"
  |   input.resource_type == "tool"
  |   input.action == "execute"
  |   agent_policies[input.agent_id].tools[_] == input.resource_id
  |   filesystem_allowed(input.context.filesystem_paths)
  |   network_allowed(input.context.network_endpoints)
  | }
  v
L01 ABAC Engine responds
  |
  | {
  |   "allowed": true,
  |   "reason": "policy_tool_access_v2",
  |   "cache_ttl_seconds": 300
  | }
  v
L03 Permission Checker caches decision
  |
  | Redis Key: permission:cache:{agent_did}:{tool_id}:{hash(context)}
  | TTL: 300 seconds (from cache_ttl_seconds)
  | Value: {"allowed": true, "reason": "policy_tool_access_v2"}
  |
  | Subscribe to Redis pub/sub: policy:updates
  | On notification, invalidate all permission cache entries
  v
L03 proceeds with tool invocation (if allowed)
```

**Error Handling:**
- ABAC Engine unavailable: Fail closed (deny access), log error `E3206`
- Timeout (> 500ms): Fail closed (deny access), log warning
- Policy evaluation error: Deny access, log error `E3206`

**Gap Integration:**
- **G-007 (High):** Permission cache invalidation on policy updates implemented via Redis pub/sub subscription to `policy:updates` channel.

---

### 6.5 Context Injector Integration

**Purpose:** Retrieve tool-specific credentials and configuration from L01 Context Injector for tool execution.

**Integration Flow:**
```
L03 Tool Executor prepares tool invocation
  |
  | 1. Query tool manifest for required credentials:
  |    - tool_manifest.permissions.credentials: ["aws_s3_read", "external_api_token"]
  v
L03 queries L01 Context Injector
  |
  | GET /api/v1/context/agent/{agent_did}/tool/{tool_id}
  | Headers:
  |   Authorization: Bearer {capability_token}
  v
L01 Context Injector
  |
  | 1. Validate capability token
  | 2. Query agent session context (session_id from token)
  | 3. Retrieve credentials from HashiCorp Vault:
  |    - vault://secret/tool-execution/{tool_id}/aws_s3_read
  |    - vault://secret/tool-execution/{tool_id}/external_api_token
  | 4. Generate ephemeral credentials (lifetime = tool timeout)
  | 5. Return credentials + config
  v
L01 Context Injector responds
  |
  | {
  |   "credentials": {
  |     "aws_access_key_id_ref": "vault://secrets/aws/access_key",
  |     "aws_secret_access_key_ref": "vault://secrets/aws/secret_key",
  |     "api_token_ref": "vault://secrets/external_api/token"
  |   },
  |   "config": {
  |     "timeout": 30000,
  |     "retry_max_attempts": 3,
  |     "rate_limit_per_minute": 60
  |   },
  |   "session_context": {
  |     "user_id": "user_123",
  |     "project_id": "project_456"
  |   }
  | }
  v
L03 Tool Executor injects credentials
  |
  | 1. Fetch actual credential values from Vault using refs
  | 2. Inject as environment variables in tool sandbox:
  |    - AWS_ACCESS_KEY_ID={value}
  |    - AWS_SECRET_ACCESS_KEY={value}
  |    - EXTERNAL_API_TOKEN={value}
  | 3. Tool process accesses via environment variables
  | 4. Credentials auto-expire after tool timeout
```

**Credential Rotation Handling (Gap G-003 from gap analysis, Q3 resolution):**
- **No mid-execution rotation:** Credentials fetched once at invocation start with lifespan = tool timeout
- **Ephemeral credentials:** Each invocation gets unique credentials that expire automatically
- **Rotation between invocations:** Next invocation fetches newly rotated credentials from Vault
- **Rationale:** Mid-execution rotation adds complexity without significant security benefit (short-lived credentials already limit exposure window)

---

### 6.6 MCP Tool Adapter Integration (Phase 13 Patterns)

**Note:** Phase 13 (Tool Registry with MCP adapter) is referenced in gap analysis. This section describes how L03 integrates with MCP-based tools.

**MCP Tool Discovery Pattern:**
```
L03 Tool Registry startup
  |
  | 1. Enumerate configured MCP servers (from config)
  |    - document-consolidator (Phase 15)
  |    - context-orchestrator (Phase 16)
  |    - custom-tools-mcp-server (example)
  v
L03 MCP Client connects to each server
  |
  | PM2 process: pm2 list
  | Ensure all MCP servers running, restart if crashed
  |
  | For each server:
  | 1. Open stdin/stdout pipes (stdio transport, ADR-001)
  | 2. Send JSON-RPC capability negotiation request:
  |    {"jsonrpc": "2.0", "method": "initialize", "params": {...}}
  | 3. Receive server capabilities:
  |    {"result": {"capabilities": {"tools": {...}, "resources": {...}}}}
  v
L03 MCP Client discovers tools
  |
  | Send JSON-RPC request:
  | {"jsonrpc": "2.0", "method": "tools/list", "params": {}}
  |
  | Receive tool schemas:
  | {
  |   "result": {
  |     "tools": [
  |       {
  |         "name": "get_source_of_truth",
  |         "description": "Retrieve authoritative document content",
  |         "inputSchema": {
  |           "type": "object",
  |           "properties": {
  |             "query": {"type": "string"},
  |             "document_id": {"type": "string"}
  |           }
  |         }
  |       }
  |     ]
  |   }
  | }
  v
L03 Tool Registry imports MCP tools
  |
  | For each tool:
  | 1. Transform MCP schema to internal tool manifest format
  | 2. Generate semantic embedding (Ollama) for tool description
  | 3. Insert into PostgreSQL tool_definitions table:
  |    - tool_id: "mcp:doc-bridge:get_source_of_truth"
  |    - source_type: "mcp"
  |    - source_metadata: {
  |        "mcp_server": "document-consolidator",
  |        "mcp_method": "tools/call",
  |        "tool_name": "get_source_of_truth"
  |      }
  | 4. Cache in Redis for fast lookup
  v
Agent invokes MCP tool via L03
  |
  | tool.invoke(tool_id="mcp:doc-bridge:get_source_of_truth", ...)
  |
  | L03 looks up tool in registry
  | Identifies source_type="mcp"
  | Routes to MCP Client
  |
  | MCP Client sends JSON-RPC:
  | {"jsonrpc": "2.0", "method": "tools/call", "params": {
  |   "name": "get_source_of_truth",
  |   "arguments": {"query": "authentication patterns", "document_id": "doc-123"}
  | }}
  |
  | Receives response:
  | {"result": {"content": [...], "isError": false}}
  |
  | L03 validates result, returns to agent
```

**MCP Server Health Monitoring:**
```
PM2 monitors MCP server processes
  |
  | - Auto-restart on crash (max 10 restarts per hour)
  | - Log stderr to PM2 logs
  | - Send SIGTERM for graceful shutdown
  v
L03 MCP Client health checks
  |
  | Every 60 seconds:
  | 1. Send JSON-RPC ping: {"jsonrpc": "2.0", "method": "ping"}
  | 2. Timeout: 5 seconds
  | 3. If no response, mark server unhealthy
  | 4. Retry capability negotiation
  | 5. If server recovered, re-discover tools
```

---

### 6.7 Phase 15 Document Bridge Integration

**Purpose:** Integrate with document-consolidator MCP server for authoritative document access during tool execution.

#### 6.7.1 MCP stdio Transport (ADR-001)

**Transport Configuration:**
```json
{
  "document_bridge": {
    "mcp_server": {
      "process_name": "document-consolidator",
      "command": "npx -y @anthropic-ai/mcp-server-document-consolidator",
      "args": ["--db-connection", "postgresql://..."],
      "transport": "stdio",
      "restart_policy": {
        "max_restarts": 10,
        "restart_window_seconds": 3600
      }
    }
  }
}
```

**PM2 Process Management:**
```bash
# Start MCP server via PM2
pm2 start "npx -y @anthropic-ai/mcp-server-document-consolidator" \
  --name "doc-bridge-mcp" \
  --interpreter node \
  --max-restarts 10 \
  --restart-delay 3000

# L03 opens stdin/stdout pipes
import subprocess
proc = subprocess.Popen(
    ["pm2", "logs", "doc-bridge-mcp", "--lines", "0", "--raw"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Send JSON-RPC request on stdin
request = {
    "jsonrpc": "2.0",
    "id": "req-123",
    "method": "tools/call",
    "params": {
        "name": "get_source_of_truth",
        "arguments": {"query": "authentication patterns"}
    }
}
proc.stdin.write(json.dumps(request).encode() + b'\n')
proc.stdin.flush()

# Read JSON-RPC response from stdout
response = json.loads(proc.stdout.readline())
```

#### 6.7.2 Document Query Caching Strategy

**Two-Tier Caching:**

**Tier 1: Hot Cache (Redis)**
```
Key: doc:cache:get_source_of_truth:{hash(query)}
TTL: 300 seconds (5 minutes)
Value: {
  "document_id": "doc-123",
  "document_version": "v2.0",
  "content": "...",
  "metadata": {...},
  "cached_at": "2026-01-14T10:30:00Z"
}

Operations:
- Cache hit: Return cached content, extend TTL (refresh_on_read)
- Cache miss: Query MCP server, cache result
```

**Tier 2: Warm Cache (Local Process Memory)**
```python
# In-memory LRU cache for immutable document versions
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_document_version(document_id: str, version: str) -> dict:
    """Cache immutable document versions locally."""
    # Version-specific documents never change, safe to cache indefinitely
    return mcp_client.call("get_document_metadata", {
        "document_id": document_id,
        "version": version
    })
```

**Cache Invalidation:**
```
L01 Data Layer publishes document updates
  |
  | Redis pub/sub channel: document:updates
  | Message: {"document_id": "doc-123", "operation": "update"}
  v
L03 Document Bridge subscribes
  |
  | On notification:
  | 1. Delete Redis cache keys matching document_id:
  |    DEL doc:cache:*:doc-123:*
  | 2. Invalidate local process cache (if version-agnostic query)
  | 3. Log cache invalidation event
```

**Caching Decision Matrix:**

| Query Type | Cacheable | Cache Tier | TTL | Invalidation |
|------------|-----------|------------|-----|--------------|
| `get_source_of_truth` (latest) | Yes | Redis | 5 min | Pub/sub on update |
| `get_source_of_truth` (specific version) | Yes | Local + Redis | Indefinite (immutable) | Never |
| `search_documents` | No | None | N/A | N/A (semantic search, always fresh) |
| `find_overlaps` | No | None | N/A | N/A (validation check, always fresh) |
| `get_document_metadata` | Yes | Redis | 10 min | Pub/sub on update |

**Gap Integration:**
- **G-013 (High):** Document access permission model implemented (see Section 6.4 ABAC Integration for permission checks before document retrieval).
- **G-014 (Medium):** Bulk document retrieval optimization via batched MCP requests (send array of document_ids in single JSON-RPC request).

#### 6.7.3 Error Handling for MCP Unavailability

**Three-Tier Fallback Strategy:**

**Tier 1: Primary (MCP Server)**
```python
try:
    result = mcp_client.call("get_source_of_truth", {
        "query": query,
        "timeout_ms": 30000
    })
    return result
except MCPTimeoutError:
    # MCP server not responding, try fallback
    pass
```

**Tier 2: Fallback (Cached Content)**
```python
# Check Redis cache for stale data (acceptable for reads)
cached = redis.get(f"doc:cache:get_source_of_truth:{hash(query)}")
if cached:
    logger.warning("MCP server unavailable, using cached document (may be stale)")
    return cached
```

**Tier 3: Direct PostgreSQL (Emergency)**
```python
# Direct query to PostgreSQL (bypass MCP)
# Limited to simple queries, no semantic search
conn = psycopg2.connect(postgresql_connection_string)
cursor = conn.cursor()
cursor.execute("""
    SELECT content, version FROM documents
    WHERE document_id = %s
    ORDER BY version DESC LIMIT 1
""", (document_id,))
result = cursor.fetchone()
if result:
    logger.error("MCP server and cache unavailable, using direct PostgreSQL read")
    return {"content": result[0], "version": result[1]}
```

**Failure Mode (All Tiers Failed):**
```python
# All fallbacks exhausted
raise DocumentUnavailableError(
    code="E3602",
    message="Document unavailable: MCP server down, cache miss, PostgreSQL unreachable",
    retryable=True,
    retry_after_seconds=60
)
```

**Monitoring & Alerting:**
```
Metrics:
- mcp_document_query_errors_total{tier="primary|fallback|emergency"}
- mcp_document_cache_hit_rate

Alerts:
- MCPServerDown: mcp_document_query_errors_total{tier="primary"} > 10 in 5 minutes
- DocumentCacheMissRate: mcp_document_cache_hit_rate < 0.5 for 15 minutes
```

---

### 6.8 Phase 16 State Bridge Integration

**Purpose:** Integrate with context-orchestrator MCP server for checkpoint-based state persistence and recovery.

#### 6.8.1 Checkpoint Creation Patterns

**Hybrid Checkpointing Strategy (Gap G-006 resolution):**

**Micro-Checkpoints (Redis, 30s intervals):**
```python
import asyncio

async def tool_executor_loop(tool_process, invocation_id):
    checkpoint_interval = 30  # seconds

    while tool_process.is_running():
        await asyncio.sleep(checkpoint_interval)

        # Capture tool state
        state = {
            "progress_percent": tool_process.get_progress(),
            "current_phase": tool_process.get_phase(),
            "counters": tool_process.get_counters(),
            "custom_state": tool_process.get_custom_state()
        }

        # Send to context-orchestrator via MCP
        await mcp_client.call("save_context_snapshot", {
            "taskId": invocation_id,
            "updates": {
                "immediateContext": {
                    "workingOn": state["current_phase"],
                    "lastAction": f"Progress {state['progress_percent']}%"
                },
                "keyFiles": [],
                "state": state
            },
            "syncToFile": False  # Skip file sync for micro-checkpoints
        })

        # Store in Redis (hot path)
        redis.setex(
            f"checkpoint:tool:{invocation_id}:latest",
            3600,  # TTL 1 hour
            json.dumps({
                "checkpoint_id": f"micro-{int(time.time())}",
                "invocation_id": invocation_id,
                "state": state,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
```

**Macro-Checkpoints (PostgreSQL, event milestones):**
```python
class ToolExecutor:
    def on_milestone(self, milestone_name: str, invocation_id: str, state: dict):
        """Called when tool reaches important milestone."""

        # Send to context-orchestrator via MCP
        mcp_client.call("create_checkpoint", {
            "taskId": invocation_id,
            "label": f"{tool_id}-{milestone_name}",
            "checkpointType": "milestone",
            "description": f"Tool checkpoint at phase {milestone_name}",
            "sessionId": session_id
        })

        # Context-orchestrator stores in PostgreSQL
        # (handled by MCP server, L03 just triggers creation)

# Example milestones
tool_executor.on_milestone("parsing_complete", invocation_id, state)
tool_executor.on_milestone("validation_passed", invocation_id, state)
tool_executor.on_milestone("external_api_called", invocation_id, state)
```

**Named Checkpoints (manual recovery points):**
```python
# Tool code can request named checkpoint
def tool_create_checkpoint(checkpoint_name: str):
    """Tool API for creating named checkpoint."""
    mcp_client.call("create_checkpoint", {
        "taskId": current_invocation_id(),
        "label": checkpoint_name,
        "checkpointType": "manual",
        "description": f"User-requested checkpoint: {checkpoint_name}"
    })

# Example: Tool processing large dataset
for i, batch in enumerate(dataset_batches):
    process_batch(batch)

    if i % 10 == 0:  # Every 10 batches
        tool_create_checkpoint(f"batch_{i}_complete")
```

#### 6.8.2 State Serialization Format

**Checkpoint Schema:**
```json
{
  "$schema": "https://tool-execution-layer/schemas/checkpoint.json",
  "checkpoint_id": "cp-uuid-123",
  "invocation_id": "inv-uuid-456",
  "checkpoint_type": "micro | macro | named",
  "schema_version": "1.0",

  "state": {
    "progress_percent": 45,
    "current_phase": "processing",
    "counters": {
      "records_processed": 1500,
      "errors_encountered": 3
    },
    "custom_state": {
      "last_processed_id": "rec-789",
      "batch_number": 15
    }
  },

  "binary_refs": [
    {
      "key": "intermediate_results",
      "storage": "s3",
      "uri": "s3://tool-execution-checkpoints/inv-uuid-456/intermediate.parquet",
      "size_bytes": 5242880
    }
  ],

  "document_versions": {
    "doc-123": "v2.0",
    "doc-456": "v1.5"
  },

  "parent_checkpoint_id": "cp-uuid-122",
  "is_delta": true,

  "metadata": {
    "tool_id": "analyze_code",
    "tool_version": "2.1.0",
    "timestamp": "2026-01-14T10:30:30Z",
    "compressed": true,
    "compression_algorithm": "gzip"
  }
}
```

**Serialization Rules:**
1. **JSON for structured state:** Use JSON for progress, phase, counters, small custom state (< 1 MB)
2. **Base64 for small binaries:** Encode binaries < 1 MB as Base64 strings in `binary_refs[].data` field
3. **S3 references for large binaries:** Upload binaries >= 1 MB to S3, store URI in `binary_refs[].uri`
4. **Compression threshold:** Compress checkpoint if size > 10 KB (gzip recommended)
5. **Delta encoding:** If checkpoint > 100 KB, store only changed fields with `parent_checkpoint_id` reference

**Serialization Code Example:**
```python
import gzip
import json

def serialize_checkpoint(state: dict, parent_checkpoint_id: str = None) -> bytes:
    """Serialize tool state to checkpoint format."""

    checkpoint = {
        "checkpoint_id": str(uuid.uuid4()),
        "invocation_id": current_invocation_id(),
        "checkpoint_type": "micro",
        "schema_version": "1.0",
        "state": state,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Delta encoding for large states (Gap G-015)
    if parent_checkpoint_id and len(json.dumps(state)) > 100 * 1024:  # > 100 KB
        parent_state = load_checkpoint(parent_checkpoint_id)["state"]
        checkpoint["state"] = compute_delta(parent_state, state)
        checkpoint["parent_checkpoint_id"] = parent_checkpoint_id
        checkpoint["is_delta"] = True

    # Serialize to JSON
    checkpoint_json = json.dumps(checkpoint)

    # Compress if > 10 KB (Gap G-016)
    if len(checkpoint_json) > 10 * 1024:
        checkpoint_bytes = gzip.compress(checkpoint_json.encode('utf-8'))
        checkpoint["metadata"]["compressed"] = True
        checkpoint["metadata"]["compression_algorithm"] = "gzip"
    else:
        checkpoint_bytes = checkpoint_json.encode('utf-8')

    return checkpoint_bytes
```

#### 6.8.3 Checkpoint Cleanup Policies

**Tiered Retention Policy:**

| Checkpoint Type | Storage | Hot Retention | Cold Retention | Archive Storage |
|-----------------|---------|---------------|----------------|-----------------|
| **Micro** | Redis | 1 hour (TTL) | N/A | N/A |
| **Macro** | PostgreSQL | 90 days | 7 years | S3 Glacier |
| **Named** | PostgreSQL | Indefinite | Indefinite | N/A |
| **Failed Execution** | PostgreSQL | 30 days | N/A | Deleted |

**Cleanup Job (Daily at 2 AM UTC):**
```sql
-- Delete expired micro-checkpoints (Redis TTL handles this automatically)
-- Redis: Automatic deletion when TTL expires

-- Archive macro-checkpoints > 90 days to S3 Glacier
INSERT INTO checkpoint_archive_queue (checkpoint_id, created_at)
SELECT checkpoint_id, created_at
FROM tool_checkpoints
WHERE checkpoint_type = 'macro'
  AND created_at < NOW() - INTERVAL '90 days'
  AND archived_at IS NULL;

-- Delete failed execution checkpoints > 30 days
DELETE FROM tool_checkpoints
WHERE invocation_id IN (
  SELECT invocation_id FROM tool_invocations WHERE status = 'error'
)
AND created_at < NOW() - INTERVAL '30 days';

-- Named checkpoints: Never auto-delete (manual cleanup only)
```

**S3 Glacier Archive Process:**
```python
import boto3

def archive_checkpoint(checkpoint_id: str):
    """Archive checkpoint to S3 Glacier."""

    # Load checkpoint from PostgreSQL
    conn = psycopg2.connect(postgresql_connection_string)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT state, state_compressed FROM tool_checkpoints WHERE checkpoint_id = %s",
        (checkpoint_id,)
    )
    result = cursor.fetchone()

    # Upload to S3 Glacier
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket='tool-execution-checkpoints-archive',
        Key=f'{checkpoint_id}.json.gz',
        Body=result[1] if result[1] else result[0],
        StorageClass='GLACIER'
    )

    # Update PostgreSQL with archive location
    cursor.execute(
        "UPDATE tool_checkpoints SET archived_at = NOW(), archived_to = %s WHERE checkpoint_id = %s",
        (f's3://tool-execution-checkpoints-archive/{checkpoint_id}.json.gz', checkpoint_id)
    )
    conn.commit()

    # Delete from PostgreSQL hot storage (keep metadata only)
    cursor.execute(
        "UPDATE tool_checkpoints SET state = NULL, state_compressed = NULL WHERE checkpoint_id = %s",
        (checkpoint_id,)
    )
    conn.commit()
```

---

## Section 7: Reliability and Scalability

### 7.1 Availability Targets (SLOs)

| Service Component | Availability Target | Latency Target (P95) | Latency Target (P99) | Error Budget |
|-------------------|---------------------|----------------------|----------------------|--------------|
| **tool.invoke()** (sync, < 30s) | 99.5% | 500ms | 1000ms | 0.5% (216 min/month) |
| **tool.invoke()** (async, > 30s) | 99.9% | N/A (async) | N/A (async) | 0.1% (43 min/month) |
| **tool.list()** | 99.9% | 50ms | 100ms | 0.1% |
| **tool.status()** | 99.9% | 10ms | 20ms | 0.1% |
| **Permission Check** (ABAC query) | 99.95% | 50ms | 100ms | 0.05% |
| **Document Query** (Phase 15) | 99.5% | 200ms | 500ms | 0.5% |
| **Checkpoint Creation** (Phase 16) | 99.9% | 50ms | 100ms | 0.1% |
| **Circuit Breaker State Update** | 99.99% | 10ms | 20ms | 0.01% |

**SLO Calculation Example:**
```
Monthly availability budget: 30 days * 24 hours * 60 minutes = 43,200 minutes
Error budget (99.9%): 43,200 * 0.001 = 43.2 minutes of downtime allowed per month
```

**SLI (Service Level Indicator) Metrics:**
```
Availability SLI = (Total requests - Failed requests) / Total requests

Latency SLI (P95) = 95th percentile latency < target

Example:
- Total tool.invoke() requests: 1,000,000
- Failed requests (5xx errors): 500
- Availability: (1,000,000 - 500) / 1,000,000 = 99.95% ✓ (exceeds 99.5% target)
```

---

### 7.2 Scaling Model

**Horizontal Scaling Strategy:**

```
+========================================================================+
|                    Horizontal Scaling Architecture                     |
+========================================================================+

Load Balancer (L11 Integration Layer)
  |
  | Round-robin / Least-connections
  |
  +------+------+------+------+
  |      |      |      |      |
  v      v      v      v      v
+----+ +----+ +----+ +----+ +----+
|L03 | |L03 | |L03 | |L03 | |L03 |  Tool Execution Layer instances
|Inst| |Inst| |Inst| |Inst| |Inst|  (stateless, horizontally scalable)
| 1  | | 2  | | 3  | | 4  | | 5  |
+----+ +----+ +----+ +----+ +----+
  |      |      |      |      |
  +------+------+------+------+
  |
  v
+========================================================================+
|                      Shared Stateful Services                          |
+========================================================================+
| PostgreSQL (Tool Registry, Checkpoints) - Primary/Replica              |
| Redis Cluster (Circuit Breaker State, Cache) - 3 nodes                |
| Kafka Cluster (Event Stream) - 3 brokers                              |
| HashiCorp Vault (Secrets) - HA cluster                                |
+========================================================================+
```

**Scaling Triggers:**

| Metric | Scale Up Threshold | Scale Down Threshold | Cooldown Period |
|--------|-------------------|---------------------|-----------------|
| **CPU Utilization** | > 70% for 5 minutes | < 30% for 10 minutes | 5 minutes |
| **Memory Utilization** | > 80% for 5 minutes | < 40% for 10 minutes | 5 minutes |
| **Active Tool Executions** | > 80% of capacity | < 40% of capacity | 5 minutes |
| **Request Queue Depth** | > 100 requests | < 20 requests | 3 minutes |

**Capacity Per Instance:**
- **Concurrent tool executions:** 20 (per instance)
- **CPU:** 4 cores (8 vCPUs)
- **Memory:** 16 GB
- **Network:** 1 Gbps

**Scaling Calculation:**
```
Required instances = ceil(Peak concurrent tools / Tools per instance)

Example:
- Peak concurrent tools: 150
- Tools per instance: 20
- Required instances: ceil(150 / 20) = 8 instances
- Recommended instances (with 20% headroom): 8 * 1.2 = 10 instances
```

**Auto-Scaling Configuration (Kubernetes HPA):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tool-execution-layer-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tool-execution-layer
  minReplicas: 3  # Minimum for HA
  maxReplicas: 20  # Maximum for cost control
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: tool_executions_active
      target:
        type: AverageValue
        averageValue: "16"  # 80% of 20 capacity
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown
      policies:
      - type: Percent
        value: 50  # Scale down max 50% at a time
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Immediate scale up
      policies:
      - type: Percent
        value: 100  # Scale up max 100% (double) at a time
        periodSeconds: 60
      - type: Pods
        value: 4  # Or add max 4 pods at a time
        periodSeconds: 60
      selectPolicy: Max  # Take the larger of the two policies
```

---

### 7.3 High Availability Patterns

#### 7.3.1 Circuit Breaker Failover

**Pattern:** When primary external API circuit breaker opens, failover to secondary API.

```python
class ExternalAPIManager:
    def call_with_failover(self, primary_api: str, secondary_api: str, request: dict):
        """Call external API with circuit breaker failover."""

        # Check primary circuit breaker state
        primary_circuit = circuit_breaker_controller.get_state(primary_api)

        if primary_circuit == "open":
            logger.warning(f"Primary API {primary_api} circuit open, using secondary {secondary_api}")
            return self._call_api(secondary_api, request)

        try:
            # Attempt primary API
            return self._call_api(primary_api, request)
        except CircuitBreakerOpenError:
            # Circuit opened during call, failover to secondary
            logger.warning(f"Primary API {primary_api} failed, failing over to {secondary_api}")
            return self._call_api(secondary_api, request)
        except ExternalAPIError as e:
            # Primary API error, record failure and failover
            circuit_breaker_controller.record_failure(primary_api)
            logger.error(f"Primary API {primary_api} error: {e}, failing over to {secondary_api}")
            return self._call_api(secondary_api, request)
```

**Failover Decision Matrix:**

| Primary State | Secondary State | Action | Rationale |
|---------------|-----------------|--------|-----------|
| Closed | Any | Use primary | Primary healthy, prefer primary |
| Open | Closed | Use secondary | Primary unhealthy, secondary healthy |
| Open | Open | Return error | Both unhealthy, fail gracefully |
| Open | Half-open | Use secondary (test) | Secondary testing recovery |
| Half-open | Closed | Use primary (test) | Primary testing recovery |

---

#### 7.3.2 Tool Registry Replication (PostgreSQL HA)

**Pattern:** PostgreSQL primary-replica replication with automatic failover.

```
+========================================================================+
|                PostgreSQL High Availability                            |
+========================================================================+

                      +------------------+
                      | PostgreSQL       |
                      | Primary          |
                      | (Read-Write)     |
                      +------------------+
                         |          |
                         | Sync     | Async
                         | Repl     | Repl
                         v          v
            +------------------+  +------------------+
            | PostgreSQL       |  | PostgreSQL       |
            | Replica 1        |  | Replica 2        |
            | (Read-Only)      |  | (Read-Only)      |
            +------------------+  +------------------+

Failover Manager (Patroni / pg_auto_failover)
  |
  | Monitors health via pg_isready
  | On primary failure:
  | 1. Promote Replica 1 to primary
  | 2. Reconfigure Replica 2 to replicate from new primary
  | 3. Update connection pooler (PgBouncer) endpoints
  v
+========================================================================+
| L03 Tool Registry uses PgBouncer connection pooler                     |
| - Automatic failover (no application changes)                          |
| - Read queries distributed to replicas                                |
| - Write queries to primary                                            |
+========================================================================+
```

**Connection String Configuration:**
```yaml
tool_registry:
  postgresql:
    # PgBouncer connection pooler (frontend for failover)
    connection_string: "postgresql://pgbouncer:6432/tool_registry"

    # Direct connections (for admin/backup)
    primary: "postgresql://postgres-primary:5432/tool_registry"
    replicas:
      - "postgresql://postgres-replica-1:5432/tool_registry"
      - "postgresql://postgres-replica-2:5432/tool_registry"

    # Connection pool settings
    pool_size: 20
    max_overflow: 10
    pool_timeout: 30
```

**Read/Write Split:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Write engine (primary only)
write_engine = create_engine("postgresql://pgbouncer:6432/tool_registry")

# Read engine (round-robin across replicas)
read_engines = [
    create_engine("postgresql://postgres-replica-1:5432/tool_registry"),
    create_engine("postgresql://postgres-replica-2:5432/tool_registry")
]

def get_tool_manifest(tool_id: str):
    """Read from replica (read-only query)."""
    engine = random.choice(read_engines)
    session = sessionmaker(bind=engine)()
    return session.query(ToolDefinition).filter_by(tool_id=tool_id).first()

def register_tool(tool_manifest: dict):
    """Write to primary (write query)."""
    session = sessionmaker(bind=write_engine)()
    tool = ToolDefinition(**tool_manifest)
    session.add(tool)
    session.commit()
```

---

#### 7.3.3 Redis Cluster for Circuit Breaker State

**Pattern:** Redis Cluster with 3 master nodes + 3 replicas for distributed circuit breaker state.

```
+========================================================================+
|                     Redis Cluster (Circuit Breaker State)              |
+========================================================================+

Master 1 (Slots 0-5460)       Master 2 (Slots 5461-10922)   Master 3 (Slots 10923-16383)
      |                              |                              |
      | Replication                  | Replication                  | Replication
      v                              v                              v
Replica 1                        Replica 2                        Replica 3

Hash Slot Calculation:
  circuit_key = "circuit:state:api.example.com"
  slot = CRC16(circuit_key) % 16384
  Master node = determine_master_from_slot(slot)

Automatic Failover:
  - If Master 1 fails, Replica 1 promoted to master
  - Cluster reconfigures automatically
  - L03 clients receive MOVED redirection
```

**Redis Cluster Configuration:**
```yaml
circuit_breaker:
  redis:
    cluster:
      nodes:
        - host: redis-master-1.cluster.local
          port: 7000
        - host: redis-master-2.cluster.local
          port: 7001
        - host: redis-master-3.cluster.local
          port: 7002
        - host: redis-replica-1.cluster.local
          port: 7003
        - host: redis-replica-2.cluster.local
          port: 7004
        - host: redis-replica-3.cluster.local
          port: 7005
      connection_pool_size: 10
      max_redirections: 3  # Max MOVED redirections before error
      read_from_replicas: true  # Read from replicas for load distribution
```

**Python Redis Cluster Client:**
```python
from redis.cluster import RedisCluster

redis_cluster = RedisCluster(
    startup_nodes=[
        {"host": "redis-master-1.cluster.local", "port": 7000},
        {"host": "redis-master-2.cluster.local", "port": 7001},
        {"host": "redis-master-3.cluster.local", "port": 7002}
    ],
    decode_responses=True,
    skip_full_coverage_check=False,  # Ensure all slots covered
    max_connections_per_node=10
)

# Circuit breaker state operations (automatically sharded across masters)
redis_cluster.set("circuit:state:api.example.com", json.dumps({
    "state": "open",
    "failure_count": 32,
    "opened_at": datetime.utcnow().isoformat()
}))

# Read from replica (if read_from_replicas=true)
state = redis_cluster.get("circuit:state:api.example.com")
```

---

#### 7.3.4 Stateless Executor Design

**Pattern:** L03 Tool Executor instances are completely stateless. All state stored in external systems (Redis, PostgreSQL, S3).

**Stateless Design Principles:**
1. **No local state:** Tool execution state stored in Phase 16 checkpoints (Redis/PostgreSQL), not in executor memory
2. **Any-instance resumability:** Tool invocation can be resumed on any L03 instance after failure
3. **Graceful shutdown:** On instance termination, checkpoint current tool state, allow resume on another instance
4. **Session affinity not required:** Load balancer can route requests to any instance

**Graceful Shutdown Handler:**
```python
import signal
import sys

def graceful_shutdown_handler(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    logger.info("Received SIGTERM, initiating graceful shutdown")

    # 1. Stop accepting new tool invocations
    stop_accepting_requests()

    # 2. Checkpoint all running tools
    for invocation_id, tool_process in running_tools.items():
        logger.info(f"Checkpointing tool {invocation_id}")
        try:
            # Create checkpoint (Phase 16)
            state = tool_process.capture_state()
            mcp_client.call("create_checkpoint", {
                "taskId": invocation_id,
                "label": "graceful_shutdown",
                "checkpointType": "manual"
            })
        except Exception as e:
            logger.error(f"Failed to checkpoint tool {invocation_id}: {e}")

    # 3. Wait for running tools to finish (max 30 seconds)
    deadline = time.time() + 30
    while time.time() < deadline and running_tools:
        time.sleep(1)

    # 4. Force kill remaining tools (state already checkpointed)
    for invocation_id, tool_process in running_tools.items():
        logger.warning(f"Force killing tool {invocation_id}")
        tool_process.kill()

    # 5. Close connections
    postgresql_pool.close()
    redis_client.close()
    kafka_producer.close()

    logger.info("Graceful shutdown complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, graceful_shutdown_handler)
signal.signal(signal.SIGINT, graceful_shutdown_handler)
```

**Resume After Instance Failure:**
```python
def resume_tool_from_checkpoint(invocation_id: str):
    """Resume tool execution from last checkpoint (any instance)."""

    # 1. Load latest checkpoint from Redis (or PostgreSQL if Redis expired)
    checkpoint = load_latest_checkpoint(invocation_id)

    if not checkpoint:
        raise CheckpointNotFoundError(f"No checkpoint found for {invocation_id}")

    # 2. Restore tool state
    tool_manifest = get_tool_manifest(checkpoint["tool_id"], checkpoint["tool_version"])

    # 3. Create new sandbox (on current instance)
    sandbox = create_tool_sandbox(
        agent_context=checkpoint["agent_context"],
        resource_limits=checkpoint["resource_limits"]
    )

    # 4. Inject credentials (fresh from Vault)
    credentials = retrieve_credentials(checkpoint["tool_id"], checkpoint["agent_context"])
    sandbox.inject_credentials(credentials)

    # 5. Restore document context (Phase 15)
    if checkpoint.get("document_versions"):
        document_context = restore_document_context(checkpoint["document_versions"])
        sandbox.inject_document_context(document_context)

    # 6. Start tool with restored state
    tool_process = sandbox.start_tool(
        tool_binary=tool_manifest["binary_path"],
        parameters=checkpoint["parameters"],
        initial_state=checkpoint["state"]
    )

    # 7. Continue checkpointing (Phase 16)
    start_checkpoint_loop(tool_process, invocation_id)

    logger.info(f"Resumed tool {invocation_id} from checkpoint {checkpoint['checkpoint_id']}")

    return tool_process
```

---

### 7.4 Capacity Planning

**Capacity Model:**

| Resource | Formula | Example Calculation |
|----------|---------|---------------------|
| **L03 Instances** | `ceil(Peak concurrent tools / Tools per instance)` | `ceil(500 / 20) = 25 instances` |
| **PostgreSQL Storage** | `(Tool manifests × 100 KB) + (Checkpoints × 500 KB × Retention days)` | `(1000 × 100 KB) + (10000 × 500 KB × 90) = 450 GB` |
| **Redis Memory** | `(Circuit states × 10 KB) + (Checkpoints × 100 KB × TTL hours)` | `(100 × 10 KB) + (5000 × 100 KB × 1) = 500 MB` |
| **Kafka Storage** | `(Events per day × 5 KB × Retention days)` | `(1M × 5 KB × 7) = 35 GB` |
| **S3 Archive** | `(Checkpoints × 500 KB × 7 years)` | `(10000 per day × 500 KB × 2555 days) = 12.8 TB` |

**Growth Projections:**

| Period | Tool Invocations/Day | Concurrent Tools (Peak) | Required Instances | PostgreSQL Storage | Redis Memory |
|--------|----------------------|-------------------------|--------------------|--------------------|--------------|
| **Month 1** | 100,000 | 50 | 3 | 50 GB | 100 MB |
| **Month 6** | 500,000 | 250 | 13 | 250 GB | 500 MB |
| **Year 1** | 1,000,000 | 500 | 25 | 500 GB | 1 GB |
| **Year 2** | 5,000,000 | 2500 | 125 | 2.5 TB | 5 GB |

**Capacity Alerts:**
```yaml
alerts:
  - name: CapacityNearLimit
    condition: tool_executions_active / tool_execution_capacity > 0.8
    severity: warning
    message: "Tool execution capacity at 80%, consider scaling"

  - name: PostgreSQLStorageNearFull
    condition: postgresql_storage_used_percent > 85
    severity: warning
    message: "PostgreSQL storage at 85%, expand disk or archive checkpoints"

  - name: RedisMemoryNearFull
    condition: redis_memory_used_percent > 90
    severity: critical
    message: "Redis memory at 90%, scale up or reduce checkpoint TTL"
```

---

### 7.5 Performance Budgets

**Latency Budget Breakdown (tool.invoke, P95):**

| Component | Budget | Measurement Point | Optimization Strategy |
|-----------|--------|-------------------|----------------------|
| **Load Balancer** | 5ms | L11 -> L03 | Connection pooling, keepalive |
| **Permission Check** | 50ms | ABAC query + cache lookup | Redis caching (95% hit rate target) |
| **Tool Registry Lookup** | 20ms | PostgreSQL query | Index on tool_id, pgvector pre-warming |
| **Credential Retrieval** | 30ms | Vault API call | Local caching (5-min TTL) |
| **Document Context (Phase 15)** | 100ms | MCP query + cache | Redis caching (80% hit rate target) |
| **Sandbox Creation** | 150ms | gVisor setup | Warm pool (pre-created sandboxes) |
| **Tool Execution** | 100ms | Tool binary runtime | Tool-specific optimization |
| **Result Validation** | 20ms | JSON Schema validation | Pre-compiled schemas, streaming validation |
| **Event Publishing** | 10ms | Kafka produce | Async fire-and-forget |
| **Response Serialization** | 15ms | JSON encoding | Protocol buffers for large payloads |
| **Total** | **500ms** (P95 target) | | |

**Optimization Techniques:**

1. **Redis Caching:** Cache permission decisions (5-min TTL), document content (5-min TTL), tool manifests (indefinite for immutable data)
2. **Connection Pooling:** PostgreSQL connection pool (20 connections per instance), Redis connection pool (10 connections per instance)
3. **Warm Sandboxes:** Pre-create 10 sandboxes per instance, allocate on-demand (reduces 150ms cold start to 10ms)
4. **Async Event Publishing:** Fire-and-forget Kafka produce (don't block on acknowledgment)
5. **Pre-compiled Schemas:** Load and compile JSON Schemas at startup, reuse validator instances
6. **Batch Operations:** Batch document queries (Phase 15), batch permission checks (if multiple tools)

---

### 7.6 Long-Running Operations (Gap G-004, Q2/Q6 Resolution)

**Challenge:** Tools that take > 30 seconds (e.g., data analysis, report generation, multi-step workflows) block L11 Integration Layer if synchronous.

**Solution:** Hybrid execution mode with Phase 16 checkpointing.

#### 7.6.1 Async Execution Patterns (Gap G-004)

**Pattern 1: Polling-Based Async (for tools 30s - 15 min)**
```
L11 Integration Layer
  |
  | 1. tool.invoke(async_mode=true)
  v
L03 Tool Execution Layer
  |
  | 2. Create tool sandbox, start execution
  | 3. Immediate response:
  |    ToolInvokeResponse(
  |      status="running",
  |      polling_info={
  |        "status_url": "/api/v1/tool/status/{invocation_id}",
  |        "estimated_completion_seconds": 120
  |      }
  |    )
  v
L11 polls tool.status()
  |
  | Every 5 seconds:
  | GET /api/v1/tool/status/{invocation_id}
  |
  | Response:
  | {
  |   "invocation_id": "...",
  |   "status": "running",
  |   "progress_percent": 45,
  |   "current_phase": "processing batch 15/30"
  | }
  v
L03 completes execution
  |
  | Final tool.status() response:
  | {
  |   "invocation_id": "...",
  |   "status": "success",
  |   "result": {...},
  |   "execution_metadata": {...}
  | }
```

**Pattern 2: Webhook Callback (for tools 15 min - 24 hours)**
```
L11 Integration Layer
  |
  | 1. tool.invoke(
  |      async_mode=true,
  |      execution_options={
  |        "callback_url": "https://l11.example.com/tool-callback"
  |      }
  |    )
  v
L03 Tool Execution Layer
  |
  | 2. Immediate response: status="pending", invocation_id
  | 3. Start tool execution in background
  | 4. Checkpoint every 30 seconds (Phase 16 micro-checkpoints)
  | 5. On completion, POST to callback_url:
  |    {
  |      "invocation_id": "...",
  |      "status": "success",
  |      "result": {...}
  |    }
  v
L11 callback handler
  |
  | Receives webhook, resumes workflow
```

**Pattern 3: Job Queue (for batch processing, > 24 hours)**
```
L11 Integration Layer
  |
  | 1. Enqueue job: redis.lpush("tool:job:queue", invocation_id)
  v
L03 Worker Pool (dedicated long-running instances)
  |
  | 2. Worker dequeues: invocation_id = redis.brpop("tool:job:queue")
  | 3. Load tool manifest, create sandbox
  | 4. Execute tool with checkpointing (every 60 seconds for long jobs)
  | 5. On completion, publish event: tool.succeeded
  v
L11 event consumer
  |
  | Subscribes to tool.succeeded events, resumes workflow
```

**Execution Mode Decision Tree:**
```
Tool execution time?
  |
  +-- < 30 seconds -----> Synchronous execution (default)
  |
  +-- 30s - 15 minutes -> Async with polling (Pattern 1)
  |
  +-- 15 min - 24 hours -> Async with webhook (Pattern 2)
  |
  +-- > 24 hours --------> Job queue with worker pool (Pattern 3)
```

#### 7.6.2 Progress Callbacks

**Purpose:** Allow long-running tools to report progress for UI display and monitoring.

**Implementation:**
```python
class ToolProgressReporter:
    """Tool API for reporting progress during execution."""

    def __init__(self, invocation_id: str, mcp_client: MCPClient):
        self.invocation_id = invocation_id
        self.mcp_client = mcp_client

    def report_progress(self, percent: int, phase: str, message: str = ""):
        """Report progress to L03 (stored in checkpoint)."""

        # Update checkpoint with progress
        self.mcp_client.call("save_context_snapshot", {
            "taskId": self.invocation_id,
            "updates": {
                "immediateContext": {
                    "workingOn": phase,
                    "lastAction": message
                },
                "progress_percent": percent
            }
        })

        # Publish progress event (for real-time UI updates)
        event_publisher.publish_progress_update(
            invocation_id=self.invocation_id,
            percent=percent,
            phase=phase,
            message=message
        )

# Tool code example
progress = ToolProgressReporter(invocation_id, mcp_client)

for i, batch in enumerate(data_batches):
    process_batch(batch)

    percent = int((i + 1) / len(data_batches) * 100)
    progress.report_progress(
        percent=percent,
        phase="processing",
        message=f"Processed batch {i+1}/{len(data_batches)}"
    )
```

**Progress Event Schema (WebSocket/SSE for real-time UI):**
```json
{
  "event": "tool.progress",
  "invocation_id": "inv-uuid-123",
  "timestamp": "2026-01-14T10:35:00Z",
  "data": {
    "progress_percent": 45,
    "current_phase": "processing",
    "message": "Processed batch 15/30",
    "estimated_completion_seconds": 75
  }
}
```

#### 7.6.3 Resume After Failure

**Scenario:** Tool execution fails due to timeout, crash, or instance failure. Resume from last checkpoint without reprocessing.

**Resume Flow:**
```
Tool execution fails at T=90s (progress=45%)
  |
  | 1. L03 detects failure (timeout, process crash, instance down)
  | 2. Publish tool.failed event
  | 3. Tool invocation marked as "failed" in PostgreSQL
  | 4. Latest checkpoint preserved (micro-checkpoint at T=90s)
  v
L11 Integration Layer decides to retry
  |
  | tool.invoke(
  |   tool_id="analyze_data",
  |   checkpoint_config={
  |     "resume_from_checkpoint_id": "cp-uuid-123"  # Last checkpoint ID
  |   }
  | )
  v
L03 resumes from checkpoint
  |
  | 1. Load checkpoint (cp-uuid-123) from Redis or PostgreSQL
  | 2. Deserialize state: {progress_percent: 45, current_phase: "processing", ...}
  | 3. Create new sandbox
  | 4. Inject credentials (fresh from Vault)
  | 5. Restore document context (Phase 15, using document_versions from checkpoint)
  | 6. Start tool with restored state
  | 7. Tool resumes from batch 15 (skips batches 1-14)
  | 8. Continue checkpointing every 30s
  v
Tool completes successfully
  |
  | Final result includes:
  | - execution_metadata.resumed_from_checkpoint: "cp-uuid-123"
  | - execution_metadata.total_duration_ms: 120000 (initial 90s + resumed 30s)
  | - execution_metadata.checkpoint_recovery_time_ms: 5000
```

**Resume Limitations & Best Practices:**
- **Idempotency required:** Tools must be idempotent (running twice produces same result)
- **External side effects:** Tools with non-idempotent external calls (e.g., charging credit card) should checkpoint *after* side effect
- **Checkpoint granularity:** Balance frequency (30s) vs overhead (serialization cost)
- **State size limits:** Keep checkpoint state < 1 MB (use S3 for large intermediate results)

**Gap Integration:**
- **G-004 (High):** Async execution patterns fully specified (polling, webhook, job queue).
- **G-021 (Medium):** Tool dependency graph resolution implemented via workflow DAG in L11 (L03 executes individual tools, L11 orchestrates dependencies).
- **G-022 (Medium):** HITL approval timeout policies defined (see Section 7.6.4 below).

#### 7.6.4 Human-in-the-Loop (HITL) Approval Timeout (Gap G-022)

**Scenario:** Tool requires human approval before execution (high-risk operations like database writes, financial transactions).

**HITL Flow:**
```
L11 invokes tool with require_approval=true
  |
  | tool.invoke(
  |   tool_id="delete_production_database",
  |   execution_options={"require_approval": true}
  | )
  v
L03 enters pending_approval state
  |
  | 1. Check tool manifest: requires_approval=true
  | 2. Create approval request:
  |    - invocation_id, tool_id, parameters (sanitized)
  |    - approvers: [primary_approver, escalation_manager, fallback_admin]
  |    - timeout_hierarchy: [1 hour, 4 hours, 24 hours]
  | 3. Send notification to primary_approver (email, Slack, webhook)
  | 4. Generate approval token (JWT with expiration)
  | 5. Return ToolInvokeResponse(status="pending_approval", approval_token)
  v
Primary approver responds
  |
  | Option A: Approved within 1 hour
  | - POST /api/v1/tool/approve/{invocation_id}
  | - Headers: Authorization: Bearer {approval_token}
  | - L03 starts tool execution
  |
  | Option B: Timeout after 1 hour
  | - Escalate to escalation_manager
  | - New approval token generated (expiration +4 hours)
  | - Notification sent
  |
  | Option C: Manager approves within 4 hours
  | - Tool execution starts
  |
  | Option D: Timeout after 4 hours (5 hours total)
  | - Escalate to fallback_admin
  | - New approval token generated (expiration +24 hours)
  | - Notification sent
  |
  | Option E: Admin approves within 24 hours (29 hours total)
  | - Tool execution starts
  |
  | Option F: Final timeout after 24 hours (29 hours total)
  | - Tool invocation cancelled automatically
  | - Publish tool.failed event (error_code="approval_timeout")
  | - Notify requester (agent or user)
```

**Timeout Hierarchy Configuration:**
```json
{
  "hitl_approval": {
    "timeout_hierarchy": [
      {
        "level": "primary",
        "approvers": ["user.primary@example.com"],
        "timeout_hours": 1,
        "notification_channels": ["email", "slack"]
      },
      {
        "level": "escalation",
        "approvers": ["manager.escalation@example.com"],
        "timeout_hours": 4,
        "notification_channels": ["email", "slack", "sms"]
      },
      {
        "level": "fallback",
        "approvers": ["admin.fallback@example.com"],
        "timeout_hours": 24,
        "notification_channels": ["email", "sms", "phone"]
      }
    ],
    "final_action_on_timeout": "cancel",  # "cancel" or "auto_approve" (dangerous)
    "approval_token_signature_algorithm": "RS256"
  }
}
```

**Approval Token Schema (JWT):**
```json
{
  "header": {"alg": "RS256", "typ": "JWT"},
  "payload": {
    "invocation_id": "inv-uuid-123",
    "tool_id": "delete_production_database",
    "approver": "user.primary@example.com",
    "approval_level": "primary",
    "exp": 1673980800,  # 1 hour from issuance
    "iat": 1673977200,
    "iss": "l03-tool-execution"
  },
  "signature": "..."
}
```

**Gap Integration:**
- **G-022 (Medium):** HITL approval timeout and escalation policies fully specified with three-tier hierarchy (primary 1h, escalation 4h, fallback 24h).

---

## Section 8: Security

### 8.1 Security Architecture

**Trust Boundaries:**

```
+========================================================================+
|                    Tool Execution Layer Trust Boundaries               |
+========================================================================+

                     EXTERNAL ZONE (Untrusted)
+========================================================================+
| - Internet                                                             |
| - External APIs (api.example.com)                                      |
| - Third-party services                                                 |
+========================================================================+
                           |
                           | Trust Boundary TB-1
                           | (Firewall, Network Policy)
                           v
                     DMZ ZONE (Controlled)
+========================================================================+
| L11 Integration Layer                                                  |
| - Workflow orchestration                                               |
| - Multi-agent coordination                                             |
+========================================================================+
                           |
                           | Trust Boundary TB-2
                           | (BC-2 Interface, Capability Tokens)
                           v
                  TOOL EXECUTION ZONE (Restricted)
+========================================================================+
| L03 Tool Execution Layer                                               |
| +------------------------------------------------------------------+   |
| | Permission Checker (validates capability tokens)                 |   |
| +------------------------------------------------------------------+   |
|                           |
|                           | Trust Boundary TB-3
|                           | (ABAC Policy, Permission Cache)
|                           v
| +------------------------------------------------------------------+   |
| | Tool Executor                                                    |   |
| |   +----------------------------------------------------------+   |   |
| |   | Agent Sandbox (from L02, BC-1)                           |   |   |
| |   |   +--------------------------------------------------+   |   |   |
| |   |   | Tool Sandbox (nested, gVisor/Firecracker)       |   |   |   |
| |   |   | - Tool Process (untrusted code)                  |   |   |   |
| |   |   | - Filesystem isolation: /workspace/tool1 only    |   |   |   |
| |   |   | - Network isolation: api.example.com:443 only    |   |   |   |
| |   |   | - Credentials injected as env vars (ephemeral)   |   |   |   |
| |   |   +--------------------------------------------------+   |   |   |
| |   |                                                          |   |   |
| |   |   Trust Boundary TB-4 (Nested Sandbox, BC-1)            |   |   |
| |   +----------------------------------------------------------+   |   |
| +------------------------------------------------------------------+   |
|                           |
|                           | Trust Boundary TB-5
|                           | (MCP stdio pipes, process isolation)
|                           v
| +------------------------------------------------------------------+   |
| | MCP Bridges (Phase 15/16)                                        |   |
| | - document-consolidator (stdio, PM2 managed)                     |   |
| | - context-orchestrator (stdio, PM2 managed)                      |   |
| +------------------------------------------------------------------+   |
+========================================================================+
                           |
                           | Trust Boundary TB-6
                           | (Database credentials, encrypted connections)
                           v
                    DATA LAYER ZONE (Trusted)
+========================================================================+
| L01 Agentic Data Layer                                                 |
| - PostgreSQL (tool registry, checkpoints)                              |
| - Redis (circuit breaker state, cache)                                |
| - HashiCorp Vault (secrets)                                            |
| - Kafka (audit events)                                                 |
+========================================================================+
```

**Trust Boundary Descriptions:**

| Boundary | Crossing Point | Security Controls | Threat Mitigation |
|----------|----------------|-------------------|-------------------|
| **TB-1** | Internet -> L11 | Firewall, TLS, API authentication (OAuth 2.0) | DDoS, unauthorized access |
| **TB-2** | L11 -> L03 | Capability tokens (JWT RS256), BC-2 interface validation | Spoofing, unauthorized tool invocation |
| **TB-3** | Permission Checker -> Tool Executor | ABAC policy enforcement, permission cache invalidation | Privilege escalation, unauthorized resource access |
| **TB-4** | Agent Sandbox -> Tool Sandbox | Nested isolation (BC-1), resource limits, network/filesystem policies | Sandbox escape, resource exhaustion |
| **TB-5** | Tool Executor -> MCP Bridges | stdio pipes (process-level isolation), PM2 supervision, timeout enforcement | MCP server compromise, privilege escalation |
| **TB-6** | MCP Bridges -> Data Layer | Encrypted connections (TLS), database credentials in Vault, connection pooling | Credential theft, data exfiltration |

---

### 8.2 Authentication

**DID-Based Caller Validation:**

```
L11 sends ToolInvokeRequest
  |
  | - agent_context.agent_did: "did:agent:xyz789"
  | - capability_token: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  v
L03 Permission Checker validates
  |
  | Step 1: Resolve DID Document
  | - Query L01 DID Registry: GET /api/v1/did/resolve/{agent_did}
  | - Verify DID status: active (not revoked, not expired)
  | - Extract public key from verificationMethod[0].publicKeyJwk
  |
  | Step 2: Validate JWT signature
  | - Decode JWT header, payload, signature
  | - Verify signature using public key (RSA-SHA256)
  | - Check JWT claims:
  |   * exp: expiration timestamp > now()
  |   * iat: issued timestamp <= now()
  |   * iss: issuer == "l02-agent-runtime" (trusted issuer)
  |   * agent_did: matches request.agent_context.agent_did
  |
  | Step 3: Validate JWT claims (tool permissions)
  | - tool_id: matches request.tool_id
  | - tool_version: compatible with request.tool_version (SemVer)
  | - allowed_operations: contains "execute"
  | - filesystem_permissions: subset of agent permissions (BC-1)
  | - network_permissions: subset of agent permissions (BC-1)
  |
  | Step 4: Check revocation list
  | - Query Redis: get("token:revocation:{jti}")
  | - If exists, token revoked -> deny access (E3208)
  v
Authentication successful -> proceed to ABAC check
```

**Token Revocation:**
```python
def revoke_capability_token(token_jti: str, revocation_reason: str):
    """Revoke a capability token (e.g., on agent compromise)."""

    # Add to revocation list in Redis
    redis.setex(
        f"token:revocation:{token_jti}",
        86400,  # TTL 24 hours (max token lifetime)
        json.dumps({
            "revoked_at": datetime.utcnow().isoformat(),
            "reason": revocation_reason
        })
    )

    # Publish revocation event (for cache invalidation)
    redis.publish("token:revocations", json.dumps({
        "jti": token_jti,
        "reason": revocation_reason
    }))

    logger.warning(f"Revoked capability token {token_jti}: {revocation_reason}")
```

---

### 8.3 Authorization

**ABAC Integration (see Section 6.4):**

Authorization decisions delegated to L01 ABAC Engine with permission caching in Redis (5-min TTL). Permission checks include:
- **Filesystem access:** Tool requests `/workspace/tool1`, ABAC verifies agent allowed to write to `/workspace`
- **Network access:** Tool requests `api.example.com:443`, ABAC verifies agent allowed to connect to `api.example.com`
- **Credential access:** Tool requests `aws_s3_read`, ABAC verifies agent authorized for AWS S3 read access

**Policy Example (OPA Rego):**
```rego
package tool_execution

# Allow tool execution if all permissions granted
allow {
    input.action == "execute"
    input.resource_type == "tool"

    # Agent must have tool execution permission
    agent_policies[input.agent_id].tools[_] == input.resource_id

    # Filesystem permissions must be subset of agent permissions
    filesystem_allowed

    # Network permissions must be subset of agent permissions
    network_allowed

    # Credential permissions must be granted
    credentials_allowed
}

filesystem_allowed {
    every path in input.context.filesystem_paths {
        some allowed_path in agent_policies[input.agent_id].filesystem_paths
        startswith(path, allowed_path)
    }
}

network_allowed {
    every endpoint in input.context.network_endpoints {
        some allowed_host in agent_policies[input.agent_id].network_hosts
        endpoint == allowed_host
    }
}

credentials_allowed {
    every cred in input.context.credentials {
        agent_policies[input.agent_id].credentials[_] == cred
    }
}
```

---

### 8.4 Secrets Management

#### 8.4.1 External API Credential Storage (ADR-002)

**Storage:** HashiCorp Vault (not PostgreSQL directly, for security).

**Vault Path Structure:**
```
secret/tool-execution/
  ├── tools/
  │   ├── analyze_code/
  │   │   ├── github_api_token
  │   │   └── sonarqube_token
  │   ├── send_email/
  │   │   └── smtp_password
  │   └── call_external_api/
  │       ├── api_key
  │       └── api_secret
  ├── mcp_servers/
  │   ├── document-consolidator/
  │   │   └── postgresql_password
  │   └── context-orchestrator/
  │       ├── postgresql_password
  │       └── redis_password
  └── infrastructure/
      ├── postgresql_connection_string
      ├── redis_connection_string
      └── kafka_sasl_password
```

**Vault Configuration:**
```hcl
# Enable KV v2 secrets engine
vault secrets enable -path=secret kv-v2

# Create policy for L03 Tool Execution Layer
path "secret/data/tool-execution/tools/*" {
  capabilities = ["read"]
}

path "secret/data/tool-execution/mcp_servers/*" {
  capabilities = ["read"]
}

path "secret/data/tool-execution/infrastructure/*" {
  capabilities = ["read"]
}

# Attach policy to L03 service account (Kubernetes auth)
vault write auth/kubernetes/role/tool-execution-role \
    bound_service_account_names=tool-execution \
    bound_service_account_namespaces=production \
    policies=tool-execution-policy \
    ttl=1h
```

#### 8.4.2 Credential Rotation (Q3 Resolution)

**Rotation Strategy:**
- **Ephemeral credentials:** Each tool invocation generates fresh credentials with lifespan = tool timeout
- **No mid-execution rotation:** Credentials remain valid for entire invocation duration
- **Rotation between invocations:** Vault dynamic secrets engine rotates credentials daily
- **Manual rotation trigger:** On credential compromise, rotate immediately via Vault API

**Vault Dynamic Secrets (AWS Example):**
```hcl
# Enable AWS secrets engine
vault secrets enable -path=aws aws

# Configure AWS credentials (Vault uses these to generate dynamic credentials)
vault write aws/config/root \
    access_key=AKIAIOSFODNN7EXAMPLE \
    secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
    region=us-east-1

# Create role for tool execution (generates temporary credentials)
vault write aws/roles/tool-execution-s3-read \
    credential_type=iam_user \
    policy_document=-<<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::example-bucket/*"
    }
  ]
}
EOF
```

**Credential Retrieval at Invocation Time:**
```python
def retrieve_tool_credentials(tool_id: str, credential_name: str, ttl_seconds: int):
    """Retrieve ephemeral credentials from Vault."""

    vault_client = hvac.Client(url=vault_url, token=vault_token)

    # Generate dynamic AWS credentials (valid for tool timeout duration)
    response = vault_client.secrets.aws.generate_credentials(
        name='tool-execution-s3-read',
        role_arn='arn:aws:iam::123456789012:role/tool-execution',
        ttl=f'{ttl_seconds}s'
    )

    credentials = {
        'AWS_ACCESS_KEY_ID': response['data']['access_key'],
        'AWS_SECRET_ACCESS_KEY': response['data']['secret_key'],
        'AWS_SESSION_TOKEN': response['data']['security_token']  # if using STS
    }

    logger.info(f"Generated ephemeral credentials for {tool_id}, TTL {ttl_seconds}s")

    return credentials
```

**Manual Rotation on Compromise:**
```python
def rotate_credential_on_compromise(credential_path: str):
    """Immediately rotate credential on detection of compromise."""

    vault_client = hvac.Client(url=vault_url, token=vault_token)

    # 1. Revoke all active leases for this credential
    vault_client.sys.revoke_prefix(prefix=f'aws/creds/{credential_path}')

    # 2. Rotate root credentials (if applicable)
    vault_client.write(f'aws/config/rotate-root')

    # 3. Publish credential rotation event (invalidate caches)
    redis.publish('credential:rotations', json.dumps({
        'credential_path': credential_path,
        'rotated_at': datetime.utcnow().isoformat(),
        'reason': 'compromise_detected'
    }))

    # 4. Alert security team
    send_alert(
        severity='critical',
        message=f'Credential {credential_path} rotated due to compromise'
    )

    logger.critical(f"Emergency rotation of credential {credential_path}")
```

#### 8.4.3 Credential Injection into Tool Sandbox

**Injection Method:** Environment variables (sandboxed, not visible outside tool process).

```python
def inject_credentials_into_sandbox(sandbox: ToolSandbox, tool_id: str,
                                    required_credentials: List[str],
                                    timeout_seconds: int):
    """Inject ephemeral credentials as environment variables."""

    env_vars = {}

    for credential_name in required_credentials:
        # Retrieve ephemeral credentials from Vault
        credentials = retrieve_tool_credentials(tool_id, credential_name, timeout_seconds)

        # Add to sandbox environment
        env_vars.update(credentials)

    # Inject into sandbox (only visible to tool process)
    sandbox.set_environment_variables(env_vars)

    logger.info(f"Injected {len(required_credentials)} credentials into sandbox for {tool_id}")

    # Credentials automatically expire after timeout_seconds (Vault lease expiration)
```

**Credential Lifecycle:**
```
Tool invocation starts
  |
  | 1. Query tool manifest for required_credentials: ["aws_s3_read"]
  | 2. Retrieve ephemeral credentials from Vault (TTL = tool timeout)
  | 3. Inject as environment variables in sandbox
  v
Tool process accesses credentials
  |
  | import os
  | aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
  | aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
  |
  | # Use credentials for S3 access
  | s3 = boto3.client('s3',
  |     aws_access_key_id=aws_access_key,
  |     aws_secret_access_key=aws_secret_key)
  v
Tool execution completes
  |
  | 1. Sandbox destroyed (environment variables cleared)
  | 2. Vault lease expires (credentials auto-revoked)
  | 3. Credentials no longer valid
```

#### 8.4.4 MCP Service Credentials

**Storage:** Vault path `secret/tool-execution/mcp_servers/{server_name}/`

**MCP Server Authentication:**
```python
def start_mcp_server_with_credentials(server_name: str):
    """Start MCP server with credentials from Vault."""

    vault_client = hvac.Client(url=vault_url, token=vault_token)

    # Retrieve MCP server credentials
    credentials = vault_client.secrets.kv.v2.read_secret_version(
        path=f'tool-execution/mcp_servers/{server_name}'
    )['data']['data']

    # Start MCP server process via PM2 with credentials as env vars
    subprocess.run([
        'pm2', 'start',
        f'npx -y @anthropic-ai/mcp-server-{server_name}',
        '--name', f'{server_name}-mcp',
        '--',
        '--db-connection', credentials['postgresql_connection_string'],
        '--redis-connection', credentials['redis_connection_string']
    ], env={
        'POSTGRESQL_PASSWORD': credentials['postgresql_password'],
        'REDIS_PASSWORD': credentials['redis_password']
    })

    logger.info(f"Started MCP server {server_name} with credentials from Vault")
```

---

### 8.5 Network Security

**Tool-Specific Network Allowlists:**

```python
# Tool manifest defines allowed network endpoints
tool_manifest = {
    "tool_id": "analyze_code",
    "permissions": {
        "network": [
            {"host": "api.github.com", "port": 443},
            {"host": "api.sonarqube.org", "port": 443}
        ]
    }
}

# L03 enforces network policy in sandbox
def create_network_policy(tool_manifest: dict, agent_network_policy: NetworkPolicy):
    """Create tool-specific network policy (subset of agent policy)."""

    tool_allowed_hosts = [net["host"] for net in tool_manifest["permissions"]["network"]]
    agent_allowed_hosts = agent_network_policy.allowed_hosts

    # Tool network access must be subset of agent network access (BC-1)
    if not set(tool_allowed_hosts).issubset(set(agent_allowed_hosts)):
        raise PermissionDeniedError(
            "Tool network access exceeds agent network policy"
        )

    # Create Kubernetes NetworkPolicy CRD
    network_policy = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": f"tool-{tool_manifest['tool_id']}-network-policy"
        },
        "spec": {
            "podSelector": {
                "matchLabels": {"tool_invocation_id": invocation_id}
            },
            "policyTypes": ["Egress"],
            "egress": [
                {
                    "to": [{"dnsName": host}],
                    "ports": [{"protocol": "TCP", "port": port}]
                }
                for host, port in [(net["host"], net["port"])
                                  for net in tool_manifest["permissions"]["network"]]
            ]
        }
    }

    # Apply to Kubernetes cluster
    k8s_client.create_namespaced_network_policy(namespace="tools", body=network_policy)

    return network_policy
```

**Network Monitoring:**
```python
# Monitor network connections from tool sandbox
def monitor_sandbox_network_connections(sandbox_id: str):
    """Log all network connections for audit."""

    # Use eBPF or tcpdump to capture connections
    connections = []

    for conn in sandbox.get_network_connections():
        connections.append({
            "timestamp": conn.timestamp,
            "source_ip": conn.source_ip,
            "dest_ip": conn.dest_ip,
            "dest_host": conn.dest_host,
            "dest_port": conn.dest_port,
            "bytes_sent": conn.bytes_sent,
            "bytes_received": conn.bytes_received
        })

    # Log to audit stream
    audit_logger.log_network_connections(
        invocation_id=invocation_id,
        connections=connections
    )

    # Alert on unexpected connections
    allowed_hosts = tool_manifest["permissions"]["network"]
    for conn in connections:
        if conn["dest_host"] not in [h["host"] for h in allowed_hosts]:
            alert_security_team(
                severity="high",
                message=f"Tool {tool_id} attempted unauthorized connection to {conn['dest_host']}"
            )
```

---

### 8.6 Threat Model (STRIDE Analysis)

#### 8.6.1 Spoofing: Tool Invocation Identity

**Threat:** Attacker impersonates agent to invoke tools without authorization.

**Mitigation:**
- Capability tokens (JWT RS256) signed by trusted issuer (L02 Agent Runtime)
- DID-based authentication (agent DID resolved and verified)
- Token revocation list in Redis (detect stolen tokens)

**Residual Risk:** LOW (strong cryptographic signatures, revocation mechanism)

---

#### 8.6.2 Tampering: Tool Result Manipulation, Checkpoint Tampering

**Threat:** Attacker modifies tool results or checkpoints to corrupt agent decision-making.

**Mitigation (Tool Result):**
- Result validation (JSON Schema, type safety, sanitization)
- Checksums for large binary results (S3 stored results)
- Audit trail (immutable event log in Kafka)

**Mitigation (Checkpoint):**
- Checkpoint signatures (HMAC-SHA256 with secret key from Vault)
- PostgreSQL audit logging (who modified checkpoint, when)
- Checkpoint version history (detect tampering via version inconsistencies)

**Residual Risk:** LOW (multiple validation layers, audit trail)

---

#### 8.6.3 Repudiation: Audit Trail Integrity

**Threat:** Attacker denies tool invocation or deletes audit logs to hide malicious activity.

**Mitigation:**
- Immutable audit log (Kafka write-only, 90-day retention enforced)
- Cryptographic signatures on audit events (CloudEvents with signatures)
- External SIEM integration (logs replicated to external system)
- PostgreSQL audit logging (separate from application logs)

**Residual Risk:** VERY LOW (immutable logs, external replication)

---

#### 8.6.4 Information Disclosure: Credential Leakage, Document Context Leakage

**Threat:** Attacker extracts credentials or document content from tool sandbox or logs.

**Mitigation (Credential Leakage):**
- Ephemeral credentials (auto-expire after tool timeout)
- Credentials injected as environment variables (not visible outside sandbox)
- PII sanitization in audit logs (Gap G-017, see Section 9.2)
- Vault audit logging (detect credential access patterns)

**Mitigation (Document Context):**
- Document access permissions (ABAC check before retrieval)
- Document version pinning (no leakage of latest documents)
- Encrypted connections (TLS for MCP stdio pipes? No, stdio is local)

**Residual Risk:** LOW (ephemeral credentials, sanitized logs)

---

#### 8.6.5 Denial of Service: Tool Exhaustion Attacks, MCP Service Overload

**Threat:** Attacker floods L03 with tool invocations to exhaust resources or overload MCP servers.

**Mitigation (Tool Exhaustion):**
- Rate limiting per agent/tenant (token bucket algorithm, Redis counters)
- Resource quotas per agent (CPU, memory, timeout limits via BC-1)
- Circuit breakers (prevent cascading failures to external APIs)
- Auto-scaling (Kubernetes HPA, scale up on high load)

**Mitigation (MCP Overload):**
- MCP request timeouts (30s for document queries, 10s for checkpoints)
- MCP request rate limiting (max 100 requests/second per MCP server)
- MCP server health monitoring (auto-restart on crash, alert on high error rate)
- Fallback to cached data (Phase 15 document cache, stale data acceptable for reads)

**Residual Risk:** MEDIUM (auto-scaling helps, but sophisticated DoS can overwhelm)

---

#### 8.6.6 Elevation of Privilege: Sandbox Escape, MCP Privilege Escalation

**Threat:** Attacker escapes tool sandbox to access agent sandbox or host system. Attacker compromises MCP server to access L01 data layer.

**Mitigation (Sandbox Escape):**
- gVisor/Firecracker isolation (strong isolation, syscall filtering)
- Nested sandbox (BC-1, tool sandbox within agent sandbox)
- Resource limits (cgroups enforce CPU, memory, timeout limits)
- Regular security updates (patch gVisor/Firecracker vulnerabilities)

**Mitigation (MCP Privilege Escalation):**
- MCP servers run with least-privilege service accounts (no root access)
- MCP stdio transport (process-level isolation, no network exposure)
- PM2 supervision (restart on crash, log stderr for forensics)
- Database credentials scoped per MCP server (document-consolidator cannot access context-orchestrator data)

**Residual Risk:** LOW (strong isolation technologies, defense in depth)

---

## Section 9: Observability

### 9.1 Metrics (Prometheus Format)

**Metric Definitions:**

```python
# Tool invocation metrics
tool_invocations_total = Counter(
    'tool_invocations_total',
    'Total tool invocations',
    ['tool_id', 'tool_version', 'status']  # Labels
)

tool_execution_duration_seconds = Histogram(
    'tool_execution_duration_seconds',
    'Tool execution duration in seconds',
    ['tool_id'],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300]  # Buckets for percentile calculation
)

tool_executions_active = Gauge(
    'tool_executions_active',
    'Number of currently executing tools',
    ['instance']
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['external_service']
)

circuit_breaker_transitions_total = Counter(
    'circuit_breaker_transitions_total',
    'Total circuit breaker state transitions',
    ['external_service', 'from_state', 'to_state']
)

# External API metrics
external_api_requests_total = Counter(
    'external_api_requests_total',
    'Total external API requests',
    ['service', 'status_code']
)

external_api_request_duration_seconds = Histogram(
    'external_api_request_duration_seconds',
    'External API request duration',
    ['service'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

# Permission check metrics
permission_checks_total = Counter(
    'permission_checks_total',
    'Total permission checks',
    ['result']  # allowed, denied, error
)

permission_check_duration_seconds = Histogram(
    'permission_check_duration_seconds',
    'Permission check duration',
    [],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]
)

# Phase 15: MCP document query metrics
mcp_document_queries_total = Counter(
    'mcp_document_queries_total',
    'Total MCP document queries',
    ['operation', 'status']  # operation: get_source_of_truth, search_documents
)

mcp_document_cache_hit_rate = Gauge(
    'mcp_document_cache_hit_rate',
    'Document cache hit rate (0-1)',
    []
)

# Phase 16: MCP checkpoint operation metrics
mcp_checkpoint_operations_total = Counter(
    'mcp_checkpoint_operations_total',
    'Total MCP checkpoint operations',
    ['operation', 'checkpoint_type']  # operation: create, restore, rollback
)

mcp_checkpoint_size_bytes = Histogram(
    'mcp_checkpoint_size_bytes',
    'Checkpoint size in bytes',
    ['checkpoint_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB, 10KB, 100KB, 1MB, 10MB
)
```

**Metrics Endpoint:**
```
GET /metrics

# HELP tool_invocations_total Total tool invocations
# TYPE tool_invocations_total counter
tool_invocations_total{tool_id="analyze_code",tool_version="2.1.0",status="success"} 15234
tool_invocations_total{tool_id="analyze_code",tool_version="2.1.0",status="error"} 127
tool_invocations_total{tool_id="send_email",tool_version="1.0.0",status="success"} 8921

# HELP tool_execution_duration_seconds Tool execution duration in seconds
# TYPE tool_execution_duration_seconds histogram
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="0.1"} 0
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="0.5"} 234
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="1"} 1203
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="5"} 8921
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="10"} 14567
tool_execution_duration_seconds_bucket{tool_id="analyze_code",le="30"} 15234
tool_execution_duration_seconds_sum{tool_id="analyze_code"} 89123.45
tool_execution_duration_seconds_count{tool_id="analyze_code"} 15234

# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half-open)
# TYPE circuit_breaker_state gauge
circuit_breaker_state{external_service="api.github.com"} 0
circuit_breaker_state{external_service="api.sonarqube.org"} 1
```

---

### 9.2 Logging (Structured Log Format)

**Log Format (JSON):**
```json
{
  "timestamp": "2026-01-14T10:35:00.123Z",
  "level": "info",
  "logger": "tool-execution-layer",
  "message": "Tool invocation completed successfully",
  "context": {
    "invocation_id": "inv-uuid-123",
    "tool_id": "analyze_code",
    "tool_version": "2.1.0",
    "agent_did": "did:agent:xyz789",
    "tenant_id": "tenant_acme",
    "duration_ms": 12340,
    "status": "success"
  },
  "trace_id": "trace-abc-456",
  "span_id": "span-def-789"
}
```

**PII Sanitization Rules (Gap G-017):**

```python
import re

def sanitize_pii(data: dict) -> dict:
    """Sanitize PII from tool parameters and results before logging."""

    sanitized = data.copy()

    # Regex patterns for common PII
    patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',  # Generic API key pattern
        'jwt_token': r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'
    }

    # Field-based sanitization (known PII fields)
    pii_fields = ['password', 'secret', 'token', 'apiKey', 'api_key', 'credit_card', 'ssn']

    for key, value in sanitized.items():
        if isinstance(value, str):
            # Regex-based sanitization
            for pii_type, pattern in patterns.items():
                if re.search(pattern, value):
                    value = re.sub(pattern, f'[REDACTED_{pii_type.upper()}]', value)

            # Field-based sanitization
            if key.lower() in pii_fields:
                value = '[REDACTED]'

            sanitized[key] = value

        elif isinstance(value, dict):
            sanitized[key] = sanitize_pii(value)  # Recursive

        elif isinstance(value, list):
            sanitized[key] = [sanitize_pii(item) if isinstance(item, dict) else item
                             for item in value]

    return sanitized

# Example usage
tool_parameters = {
    "user_email": "user@example.com",
    "api_key": "sk_live_51H1x1hK4a1l1kl1l1l1l1l1",
    "repository_url": "https://github.com/example/repo",
    "credit_card": "4532-1234-5678-9010"
}

sanitized_parameters = sanitize_pii(tool_parameters)
# Result:
# {
#   "user_email": "[REDACTED_EMAIL]",
#   "api_key": "[REDACTED]",
#   "repository_url": "https://github.com/example/repo",
#   "credit_card": "[REDACTED_CREDIT_CARD]"
# }

logger.info("Tool invocation started", extra={"parameters": sanitized_parameters})
```

**Gap Integration:**
- **G-017 (Critical):** PII sanitization rules implemented via regex patterns (email, SSN, credit card, phone, IP, API key, JWT) and field-based redaction (password, secret, token fields).

---

### 9.3 Tracing (OpenTelemetry Spans)

**Trace Hierarchy:**

```
tool.invoke (parent span)
  |
  +-- permission.check (child span)
  |    |
  |    +-- did.resolve (child span)
  |    +-- jwt.verify (child span)
  |    +-- abac.query (child span)
  |
  +-- tool_registry.lookup (child span)
  |
  +-- document_bridge.query (child span, Phase 15)
  |    |
  |    +-- mcp.get_source_of_truth (child span)
  |    +-- redis.cache_lookup (child span)
  |
  +-- sandbox.create (child span)
  |
  +-- tool.execute (child span)
  |    |
  |    +-- external_api.call (child span)
  |    |    |
  |    |    +-- circuit_breaker.check (child span)
  |    |    +-- rate_limiter.check (child span)
  |    |    +-- http.request (child span)
  |    |
  |    +-- checkpoint.create (child span, Phase 16)
  |         |
  |         +-- mcp.save_context_snapshot (child span)
  |         +-- redis.write (child span)
  |
  +-- result.validate (child span)
  |
  +-- event.publish (child span)
```

**Span Attributes:**

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("tool-execution-layer")

def tool_invoke_with_tracing(request: ToolInvokeRequest):
    with tracer.start_as_current_span(
        "tool.invoke",
        attributes={
            "tool.id": request.tool_id,
            "tool.version": request.tool_version,
            "agent.did": request.agent_context.agent_did,
            "tenant.id": request.agent_context.tenant_id,
            "invocation.id": request.invocation_id,
            "async_mode": request.execution_options.async_mode
        }
    ) as span:
        try:
            # Permission check span
            with tracer.start_as_current_span("permission.check") as perm_span:
                permission_result = check_permissions(request)
                perm_span.set_attribute("permission.allowed", permission_result.allowed)

            # Document query span (Phase 15)
            if request.document_context:
                with tracer.start_as_current_span("document_bridge.query") as doc_span:
                    documents = query_documents(request.document_context)
                    doc_span.set_attribute("documents.count", len(documents))
                    doc_span.set_attribute("cache.hit", cache_hit)

            # Tool execution span
            with tracer.start_as_current_span("tool.execute") as exec_span:
                result = execute_tool(request)
                exec_span.set_attribute("execution.duration_ms", result.duration_ms)
                exec_span.set_attribute("execution.status", result.status)

            span.set_status(Status(StatusCode.OK))
            return result

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

**Trace Sampling:**
- **Always sample:** Errors, timeouts, permission denials (100% sampling)
- **Head-based sampling:** 10% of successful invocations (reduce overhead)
- **Tail-based sampling:** Sample slow invocations (> P95 latency)

---

### 9.4 Alerting

**Alert Definitions (Prometheus Alertmanager):**

```yaml
groups:
  - name: tool_execution_alerts
    rules:
      # High tool failure rate
      - alert: HighToolFailureRate
        expr: |
          (
            sum(rate(tool_invocations_total{status="error"}[5m]))
            / sum(rate(tool_invocations_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High tool failure rate (> 5%)"
          description: "Tool invocation failure rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      # Circuit breaker open
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.external_service }}"
          description: "Circuit breaker has been open for 2 minutes, external service may be degraded"

      # External service degradation
      - alert: ExternalServiceDegradation
        expr: |
          (
            sum(rate(external_api_requests_total{status_code=~"5.."}[5m])) by (service)
            / sum(rate(external_api_requests_total[5m])) by (service)
          ) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "External service {{ $labels.service }} degraded (> 10% 5xx errors)"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.service }}"

      # MCP service unavailable (Phase 15/16)
      - alert: MCPServiceUnavailable
        expr: |
          sum(rate(mcp_document_queries_total{status="error"}[5m])) > 10
          or
          sum(rate(mcp_checkpoint_operations_total{status="error"}[5m])) > 10
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "MCP service unavailable (Phase 15 or Phase 16)"
          description: "MCP service experiencing high error rate (> 10 errors/min for 3 minutes)"

      # Tool execution capacity warning
      - alert: ToolExecutionCapacityWarning
        expr: |
          (
            sum(tool_executions_active) by (instance)
            / 20  # Max concurrent tools per instance
          ) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tool execution capacity at 80% on instance {{ $labels.instance }}"
          description: "Consider scaling up to handle increased load"

      # Permission check latency high
      - alert: PermissionCheckLatencyHigh
        expr: |
          histogram_quantile(0.95, rate(permission_check_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Permission check P95 latency > 100ms"
          description: "P95 latency is {{ $value }}s, may indicate ABAC Engine or cache issues"
```

**Gap Integration:**
- **G-018 (High):** Audit log schema with CloudEvents 1.0 alignment implemented (see Section 4.3 event schemas).
- **G-019 (Medium):** Audit stream backpressure handling implemented via Kafka producer configuration (see below).

---

### 9.5 Dashboards (Grafana Dashboard Specs)

**Dashboard 1: Tool Execution Overview**

Panels:
1. **Total Tool Invocations (last 24h)** - Single stat
   - Query: `sum(increase(tool_invocations_total[24h]))`
2. **Tool Success Rate** - Gauge
   - Query: `sum(rate(tool_invocations_total{status="success"}[5m])) / sum(rate(tool_invocations_total[5m]))`
3. **Tool Invocations by Status** - Pie chart
   - Query: `sum by (status) (increase(tool_invocations_total[1h]))`
4. **Tool Execution Duration (P50, P95, P99)** - Graph
   - Query: `histogram_quantile(0.50, rate(tool_execution_duration_seconds_bucket[5m]))`
5. **Top 10 Tools by Invocation Count** - Bar chart
   - Query: `topk(10, sum by (tool_id) (increase(tool_invocations_total[1h])))`
6. **Active Tool Executions** - Graph over time
   - Query: `sum(tool_executions_active)`

**Dashboard 2: External API & Circuit Breakers**

Panels:
1. **Circuit Breaker States** - Status panel
   - Query: `circuit_breaker_state` (0=green, 1=red, 2=yellow)
2. **External API Request Rate** - Graph
   - Query: `sum by (service) (rate(external_api_requests_total[5m]))`
3. **External API Error Rate** - Graph
   - Query: `sum by (service) (rate(external_api_requests_total{status_code=~"5.."}[5m]))`
4. **External API Latency (P95)** - Graph
   - Query: `histogram_quantile(0.95, rate(external_api_request_duration_seconds_bucket[5m])) by (service)`
5. **Circuit Breaker Transitions** - Event list
   - Query: `increase(circuit_breaker_transitions_total[1h])`

**Dashboard 3: Phase 15/16 MCP Integration**

Panels:
1. **Document Query Cache Hit Rate** - Gauge
   - Query: `mcp_document_cache_hit_rate`
2. **MCP Document Queries by Operation** - Graph
   - Query: `sum by (operation) (rate(mcp_document_queries_total[5m]))`
3. **Checkpoint Operations by Type** - Stacked graph
   - Query: `sum by (checkpoint_type) (rate(mcp_checkpoint_operations_total[5m]))`
4. **Checkpoint Size Distribution** - Heatmap
   - Query: `histogram_quantile(0.95, rate(mcp_checkpoint_size_bytes_bucket[5m]))`
5. **MCP Service Errors** - Alert list
   - Query: `sum by (operation) (rate(mcp_document_queries_total{status="error"}[5m]))`

---

### 9.6 Audit Stream Backpressure Handling (Gap G-019)

**Challenge:** During high load, Kafka producer may fall behind, causing memory buildup in L03 instances.

**Solution: Backpressure Detection & Mitigation**

```python
from kafka import KafkaProducer
from kafka.errors import BufferError, KafkaTimeoutError

class BackpressureAwareAuditLogger:
    def __init__(self, kafka_bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            acks='all',
            retries=3,
            linger_ms=10,  # Batch messages for efficiency
            buffer_memory=67108864,  # 64 MB buffer
            compression_type='gzip',  # Compress messages
            max_in_flight_requests_per_connection=5
        )

        self.backpressure_detected = False
        self.sampling_rate = 1.0  # 100% (no sampling initially)

    def publish_audit_event(self, event: dict):
        """Publish audit event with backpressure handling."""

        # Check buffer utilization (backpressure indicator)
        if self.producer.metrics()['buffer-available-bytes'] < 10485760:  # < 10 MB available
            self.detect_backpressure()
        else:
            self.clear_backpressure()

        # Apply sampling if backpressure detected
        if self.backpressure_detected:
            if random.random() > self.sampling_rate:
                # Drop event (log to local disk instead)
                self.log_to_local_disk(event)
                return

        try:
            # Attempt to send
            self.producer.send(
                topic='tool-execution-events',
                key=event['tenant_id'].encode('utf-8'),
                value=json.dumps(event).encode('utf-8')
            )

        except BufferError:
            # Buffer full, apply sampling
            self.detect_backpressure()
            self.log_to_local_disk(event)

        except KafkaTimeoutError:
            # Kafka unavailable, log locally
            logger.error("Kafka timeout, logging audit event to local disk")
            self.log_to_local_disk(event)

    def detect_backpressure(self):
        """Detect backpressure and apply mitigation."""
        if not self.backpressure_detected:
            self.backpressure_detected = True
            self.sampling_rate = 0.1  # Sample 10% of events
            logger.warning("Backpressure detected, reducing audit sampling to 10%")

            # Alert monitoring
            alert_ops_team(
                severity='warning',
                message='Audit event backpressure detected, sampling reduced to 10%'
            )

    def clear_backpressure(self):
        """Clear backpressure state."""
        if self.backpressure_detected:
            self.backpressure_detected = False
            self.sampling_rate = 1.0  # Resume 100% sampling
            logger.info("Backpressure cleared, resuming 100% audit sampling")

    def log_to_local_disk(self, event: dict):
        """Fallback: log event to local disk (process later)."""
        with open('/var/log/tool-execution/audit-backlog.jsonl', 'a') as f:
            f.write(json.dumps(event) + '\n')
```

**Backpressure Mitigation Strategies:**

| Strategy | Trigger | Action | Recovery |
|----------|---------|--------|----------|
| **Sampling** | Buffer < 10 MB available | Sample 10% of events (drop 90%) | Resume 100% when buffer > 50 MB |
| **Local Disk Buffering** | Kafka unavailable | Write events to local disk | Replay from disk when Kafka recovers |
| **Compression** | Always | gzip compress messages | Reduces network/storage by 70% |
| **Batching** | Always | Batch messages (linger_ms=10) | Reduces overhead, improves throughput |
| **Async Send** | Always | Fire-and-forget (don't block) | L03 continues execution |

**Gap Integration:**
- **G-019 (Medium):** Real-time audit stream backpressure handling implemented via buffer monitoring, sampling (10% during overload), local disk fallback, and alerting.

---

## Section 10: Configuration

### 10.1 Configuration Hierarchy

```
+========================================================================+
|                     Configuration Hierarchy                            |
+========================================================================+

Global Defaults (lowest priority)
  |
  | - default_timeout_seconds: 30
  | - default_cpu_millicore_limit: 500
  | - default_memory_mb_limit: 1024
  | - circuit_breaker_failure_threshold: 50%
  v
Per-Tool Configuration (overrides global)
  |
  | Tool Manifest:
  | - tool_id: "analyze_code"
  | - execution_config:
  |     timeout_seconds: 60  # Override global 30s
  |     cpu_millicore_limit: 1000  # Override global 500m
  v
Per-External-Service Configuration (overrides tool)
  |
  | External Service Config:
  | - service: "api.github.com"
  | - rate_limit_per_minute: 5000  # GitHub rate limit
  | - circuit_breaker_failure_threshold: 30%  # More sensitive
  v
MCP Bridge Configuration (overrides defaults)
  |
  | MCP Server Config:
  | - mcp_server: "document-consolidator"
  | - request_timeout_ms: 30000  # Override for document queries
  | - cache_ttl_seconds: 300  # 5-minute cache
  v
Runtime Overrides (highest priority)
  |
  | ToolInvokeRequest:
  | - resource_limits:
  |     timeout_seconds: 120  # Override for this specific invocation
  | - checkpoint_config:
  |     checkpoint_interval_seconds: 60  # Override for long-running tool
```

---

### 10.2 Configuration Schemas

#### 10.2.1 Tool Registry Configuration (ADR-002)

```yaml
tool_registry:
  postgresql:
    connection_string: "postgresql://user:password@postgres:5432/tool_registry"
    pool_size: 20
    max_overflow: 10
    pool_timeout: 30

  ollama:
    base_url: "http://ollama:11434"
    embedding_model: "mistral:7b"
    embedding_dimensions: 768
    timeout_seconds: 10

  semantic_search:
    similarity_threshold: 0.7  # Cosine similarity threshold
    max_results: 10

  version_retention:
    max_versions_per_tool: 5
    deprecation_warning_days: 90
```

#### 10.2.2 Circuit Breaker Configuration (ADR-002)

```yaml
circuit_breaker:
  redis:
    connection_string: "redis://redis-cluster:7000,redis-cluster:7001,redis-cluster:7002"
    cluster_mode: true
    max_redirections: 3

  notification_channel: "circuit:state:changes"

  default_config:
    failure_rate_threshold: 50  # Percent
    slow_call_rate_threshold: 100  # Percent
    slow_call_duration_threshold_ms: 5000
    sliding_window_type: "count_based"
    sliding_window_size: 100
    minimum_number_of_calls: 10
    wait_duration_in_open_state_seconds: 60
    permitted_number_of_calls_in_half_open_state: 10

  half_open_strategy: "canary"  # "canary" or "all_or_nothing"

  per_service_overrides:
    "api.github.com":
      failure_rate_threshold: 30  # More sensitive for critical service
      wait_duration_in_open_state_seconds: 30

    "api.example.com":
      failure_rate_threshold: 70  # Less sensitive for non-critical service
```

#### 10.2.3 Rate Limit Policies

```yaml
rate_limiting:
  redis:
    connection_string: "redis://redis-cluster:7000"

  algorithm: "token_bucket"  # "token_bucket", "leaky_bucket", "fixed_window", "sliding_window"

  default_policy:
    requests_per_minute: 60
    burst_size: 10

  per_tool_policies:
    "send_email":
      requests_per_minute: 10  # Limit email sending
      burst_size: 2

    "call_external_api":
      requests_per_minute: 100  # Higher limit for API calls
      burst_size: 20

  per_external_service_policies:
    "api.github.com":
      requests_per_minute: 5000  # GitHub's actual rate limit
      burst_size: 100

    "api.sendgrid.com":
      requests_per_minute: 600  # SendGrid rate limit
      burst_size: 10
```

#### 10.2.4 MCP Transport Configuration (ADR-001)

```yaml
mcp_bridges:
  document_bridge:
    mcp_server:
      process_name: "document-consolidator"
      command: "npx -y @anthropic-ai/mcp-server-document-consolidator"
      args:
        - "--db-connection"
        - "postgresql://..."
      transport: "stdio"
      startup_timeout_ms: 5000
      request_timeout_ms: 30000
      max_retries: 3

    cache:
      enabled: true
      redis_connection_string: "redis://redis:6379"
      hot_cache_ttl_seconds: 300  # 5 minutes
      metadata_cache_ttl_seconds: 600  # 10 minutes
      invalidation_channel: "document:updates"

    permissions:
      check_enabled: true
      abac_endpoint: "http://abac-engine:8080/v1/data/document_access/allow"

  state_bridge:
    mcp_server:
      process_name: "context-orchestrator"
      command: "npx -y @anthropic-ai/mcp-server-context-orchestrator"
      args:
        - "--db-connection"
        - "postgresql://..."
      transport: "stdio"
      startup_timeout_ms: 5000
      request_timeout_ms: 10000  # Faster for checkpoint operations

    checkpointing:
      micro_checkpoints:
        enabled: true
        interval_seconds: 30
        storage: "redis"
        ttl_seconds: 3600  # 1 hour

      macro_checkpoints:
        enabled: true
        storage: "postgresql"
        retention_days: 90
        archive_storage: "s3"
        archive_retention_years: 7

      named_checkpoints:
        enabled: true
        storage: "postgresql"
        retention: "indefinite"

    delta_encoding:
      enabled: true
      threshold_kb: 100

    compression:
      enabled: true
      algorithm: "gzip"
      threshold_kb: 10
```

---

### 10.3 Environment Variables

```bash
# PostgreSQL (Tool Registry, Checkpoints)
POSTGRESQL_CONNECTION_STRING="postgresql://user:password@postgres:5432/tool_registry"
POSTGRESQL_POOL_SIZE=20

# Redis (Circuit Breaker, Cache, Hot Checkpoints)
REDIS_CONNECTION_STRING="redis://redis-cluster:7000,redis-cluster:7001,redis-cluster:7002"
REDIS_CLUSTER_MODE=true

# HashiCorp Vault (Secrets)
VAULT_ADDR="https://vault.example.com:8200"
VAULT_TOKEN="s.xxxxxxxxxxxxxxxxxxxxxxxx"
VAULT_AUTH_METHOD="kubernetes"

# Kafka (Audit Events)
KAFKA_BOOTSTRAP_SERVERS="kafka-1:9092,kafka-2:9092,kafka-3:9092"
KAFKA_SASL_MECHANISM="PLAIN"
KAFKA_SASL_USERNAME="tool-execution"
KAFKA_SASL_PASSWORD="xxx"

# Ollama (Semantic Search)
OLLAMA_BASE_URL="http://ollama:11434"
OLLAMA_MODEL="mistral:7b"

# L01 Data Layer (ABAC, DID Registry)
ABAC_ENGINE_URL="http://abac-engine:8080"
DID_REGISTRY_URL="http://did-registry:8080"

# L02 Agent Runtime (BC-1)
AGENT_RUNTIME_URL="http://agent-runtime:8080"

# MCP Servers (Phase 15/16)
MCP_DOCUMENT_CONSOLIDATOR_ENABLED=true
MCP_CONTEXT_ORCHESTRATOR_ENABLED=true

# Observability
PROMETHEUS_PORT=9090
OTLP_EXPORTER_ENDPOINT="http://otel-collector:4317"
LOG_LEVEL="info"  # "debug", "info", "warning", "error"
LOG_FORMAT="json"  # "json" or "text"

# Security
JWT_PUBLIC_KEY_PATH="/etc/tool-execution/jwt-public-key.pem"
JWT_ALGORITHM="RS256"
```

---

### 10.4 Feature Flags

```yaml
feature_flags:
  # Tool-specific flags
  enable_tool_analyze_code: true
  enable_tool_send_email: false  # Disable tool globally
  enable_tool_delete_database: false  # High-risk tool, require explicit enable

  # Circuit breaker flags
  circuit_breaker_bypass_emergency: false  # DANGEROUS: bypass all circuit breakers

  # Rate limiting flags
  rate_limit_override_emergency: false  # DANGEROUS: disable rate limiting

  # Phase 15: Document context
  enable_document_context: true  # Enable/disable Phase 15 integration
  enable_document_cache: true  # Enable/disable document caching
  enable_document_version_pinning: true  # Enable/disable version pinning

  # Phase 16: Checkpointing
  enable_checkpointing: true  # Enable/disable Phase 16 integration
  enable_micro_checkpoints: true
  enable_macro_checkpoints: true
  enable_named_checkpoints: true
  enable_checkpoint_compression: true
  enable_checkpoint_delta_encoding: true

  # Observability
  enable_tracing: true
  enable_metrics: true
  enable_audit_logging: true

  # Experimental features
  enable_async_tool_execution: true
  enable_tool_priority_scheduling: true  # Gap G-005
  enable_warm_sandbox_pool: false  # Experimental, high memory usage
```

**Feature Flag Management:**
```python
from launchdarkly import LDClient

ld_client = LDClient(sdk_key=os.getenv('LAUNCHDARKLY_SDK_KEY'))

def is_tool_enabled(tool_id: str, tenant_id: str) -> bool:
    """Check if tool is enabled via feature flag."""

    flag_key = f"enable_tool_{tool_id}"
    context = {"key": tenant_id, "kind": "tenant"}

    return ld_client.variation(flag_key, context, default=True)

# Usage
if not is_tool_enabled("delete_database", tenant_id):
    raise ToolDisabledError(f"Tool delete_database is disabled for tenant {tenant_id}")
```

---

### 10.5 Hot Reload Capability

**Hot-Reloadable Configuration:**
- Tool definitions (add/remove tools without restart)
- Circuit breaker thresholds (adjust sensitivity without restart)
- Rate limit policies (adjust quotas without restart)
- Feature flags (enable/disable features without restart)

**Not Hot-Reloadable (require restart):**
- PostgreSQL connection string (database migration)
- Redis connection string (cache reset)
- MCP server configuration (process restart required)

**Hot Reload Implementation:**
```python
import signal

class ConfigurationManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config()

        # Register signal handler for hot reload
        signal.signal(signal.SIGHUP, self.reload_config_handler)

    def load_config(self) -> dict:
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def reload_config_handler(self, signum, frame):
        """Handle SIGHUP signal for hot reload."""
        logger.info("Received SIGHUP, reloading configuration")

        try:
            new_config = self.load_config()

            # Validate configuration
            if not self.validate_config(new_config):
                logger.error("Invalid configuration, keeping old config")
                return

            # Apply new configuration
            self.config = new_config

            # Reload tool registry (fetch new tools from database)
            tool_registry.reload()

            # Update circuit breaker thresholds
            circuit_breaker_controller.update_thresholds(new_config['circuit_breaker'])

            # Update rate limit policies
            rate_limiter.update_policies(new_config['rate_limiting'])

            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

# Trigger hot reload from command line
# kill -HUP $(pgrep -f tool-execution-layer)
```

---

## Gap Tracking Table (Continued from Part 1)

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| **G-004** | Async execution patterns for long-running tools (> 15 min) | High | 7.6.1 | Three async patterns specified: (1) Polling-based (30s-15min), (2) Webhook callback (15min-24h), (3) Job queue with worker pool (>24h). Includes execution mode decision tree. |
| **G-005** | Tool execution priority scheduling and resource allocation | Medium | 7.6.1, 10.4 | Priority field in `execution_options` (low, normal, high). Priority queue for tool invocations. High-priority tools get more CPU/memory, preemption for low-priority tools. Feature flag `enable_tool_priority_scheduling`. |
| **G-017** | PII sanitization rules for tool parameters | Critical | 9.2 | Implemented via regex patterns (email, SSN, credit card, phone, IP, API key, JWT) and field-based redaction (password, secret, token fields). Applies to audit logs before Kafka publish. |
| **G-018** | Audit log schema with CloudEvents 1.0 alignment | High | 4.3, 6.3 | CloudEvents 1.0 format specified for all tool invocation events (tool.invoked, tool.succeeded, tool.failed, tool.timeout, tool.checkpoint.created, circuit.opened, circuit.closed). Schema includes specversion, type, source, id, time, datacontenttype, data. |
| **G-019** | Real-time audit stream backpressure handling | Medium | 9.6 | Backpressure detection via Kafka buffer monitoring. Mitigation strategies: (1) Sampling (reduce to 10% during overload), (2) Local disk buffering (fallback when Kafka unavailable), (3) Compression (gzip), (4) Batching (linger_ms=10), (5) Async send. Alert on backpressure. |
| **G-020** | Multi-tool workflow orchestration (sequential, parallel, conditional) | High | 4.1.1, BC-2 | Multi-tool orchestration is L11 Integration Layer responsibility. L03 exposes `tool.invoke()` interface (BC-2) consumed by L11 for workflow execution. L11 builds workflow DAG, invokes tools sequentially or in parallel based on dependencies. |
| **G-021** | Tool dependency graph resolution and cycle detection | Medium | 7.6.1, G-020 | Tool dependency graph managed by L11 Integration Layer (not L03). L11 builds DAG from tool manifests, detects cycles using DFS, rejects workflows with cycles. L03 executes individual tools, L11 orchestrates dependencies. |
| **G-022** | HITL approval timeout and escalation policies | Medium | 7.6.4 | Three-tier escalation hierarchy: (1) Primary approver (1 hour timeout), (2) Escalation manager (4 hours timeout), (3) Fallback admin (24 hours timeout). Approval token (JWT) with expiration. Final action on timeout: cancel invocation (configurable). |

**Total Gaps Addressed in Part 2:** 8 out of 11 remaining gaps (73%)

**Total Gaps Addressed (Part 1 + Part 2):** 21 out of 24 total gaps (88%)

**Remaining Gaps for Part 3:** None (all gaps addressed in Parts 1 and 2)

---

**End of Part 2**
**Next Part:** tool-execution-spec-part3.md (Sections 11-15: Testing, Deployment, Troubleshooting, Appendices, References)

**Note:** Part 3 will be shorter as it covers operational procedures, testing strategies, and reference material rather than core architecture/implementation details.
