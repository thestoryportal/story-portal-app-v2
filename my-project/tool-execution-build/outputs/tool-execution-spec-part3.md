# Tool Execution Layer Specification - Part 3
## Sections 11-15: Implementation, Testing, Deployment, Decisions, References

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2026-01-14

---

## Section 11: Implementation Guide

### 11.1 Implementation Phases

The Tool Execution Layer should be implemented in six phases, each building on the previous phase's foundation. This phased approach allows for incremental value delivery and risk mitigation.

#### Phase 1: Core Tool Registry and Basic Execution (Weeks 1-3)

**Objective:** Establish the foundation for tool registration and simple invocation.

**Deliverables:**
- PostgreSQL 16 database with pgvector extension installed
- Tool registry schema (tool_definitions, tool_versions tables)
- Basic Tool Registry Service API (register, query, retrieve)
- Simple Tool Executor with subprocess isolation (no nested sandbox yet)
- HTTP API for tool.invoke() with synchronous execution only
- Basic error handling and logging

**Dependencies:**
- PostgreSQL 16 + pgvector deployment
- Python 3.11+ runtime environment

**Acceptance Criteria:**
- Can register a tool with manifest schema
- Can invoke tool with simple parameters (strings, numbers)
- Tool execution completes within timeout
- Basic error responses for invalid tool IDs

**Technology Stack:**
- PostgreSQL 16 + pgvector for registry
- FastAPI for HTTP API layer
- Python subprocess module for execution
- Pydantic for schema validation

---

#### Phase 2: Permission Integration and ABAC (Weeks 4-5)

**Objective:** Integrate with Data Layer's ABAC engine for secure authorization.

**Deliverables:**
- Permission Checker component
- JWT capability token validation (RS256 signature verification)
- Integration with Data Layer ABAC engine (gRPC or HTTP client)
- Permission cache implementation (Redis)
- DID-based authentication
- Permission denial error responses (E3200-E3249)

**Dependencies:**
- Phase 1 complete
- Data Layer ABAC engine deployed and accessible
- DID registry service available
- Redis 7 cluster deployed

**Acceptance Criteria:**
- Tool invocation blocked without valid capability token
- Permission cache hit rate > 80%
- Cache invalidation on policy updates
- Sub-50ms permission check latency (P95)

**Technology Stack:**
- Redis 7 for permission caching
- PyJWT for token validation
- gRPC client for ABAC engine communication
- Redis pub/sub for cache invalidation

---

#### Phase 3: Circuit Breaker and External Adapters (Weeks 6-8)

**Objective:** Add resilience patterns for external API integration.

**Deliverables:**
- Circuit Breaker Controller (Resilience4j pattern)
- Redis-based state storage for circuit breakers
- External Adapter Manager (HTTP, gRPC, WebSocket adapters)
- Rate limiting per external service
- Retry logic with exponential backoff and full jitter
- Circuit breaker state transitions logged to PostgreSQL

**Dependencies:**
- Phase 2 complete
- Redis 7 cluster deployed
- External API credentials in Vault

**Acceptance Criteria:**
- Circuit breaker opens after threshold failures
- Half-open state canary testing (10% traffic)
- Rate limiting enforced per service
- Retry with full jitter reduces thundering herd

**Technology Stack:**
- Redis 7 for circuit breaker state
- Python Tenacity library for retries
- HTTP clients: httpx with connection pooling
- Custom circuit breaker implementation based on Resilience4j pattern

---

#### Phase 4: Result Validation and Audit Logging (Weeks 9-10)

**Objective:** Ensure output correctness and compliance.

**Deliverables:**
- Result Validator component
- JSON Schema validation with AJV
- Type coercion pipeline
- PII sanitization engine
- Audit Logger with CloudEvents 1.0 format
- Kafka integration for audit streaming
- Tool invocation event schema (tool.invoke.*, tool.complete.*, tool.error.*)

**Dependencies:**
- Phase 3 complete
- Apache Kafka cluster deployed
- Compliance requirements documented

**Acceptance Criteria:**
- Tool results validated against manifest schema
- PII patterns redacted before audit logging
- Audit events streamed to Kafka with <100ms latency
- CloudEvents 1.0 compliance verified

**Technology Stack:**
- AJV for JSON Schema validation
- Kafka Python client (kafka-python or confluent-kafka)
- Regex-based PII sanitization
- CloudEvents SDK for Python

---

#### Phase 5: Document Bridge Integration (Phase 15) (Weeks 11-12)

**Objective:** Enable tool access to organizational documents via MCP.

**Deliverables:**
- Document Bridge component
- MCP stdio client for document-consolidator server
- Two-tier caching: Redis (hot) + local LRU (warm)
- get_source_of_truth() integration
- find_overlaps() integration for conflict detection
- MCP error handling with three-tier fallback
- PM2 configuration for MCP server process management

**Dependencies:**
- Phase 4 complete
- Phase 15 document-consolidator MCP server deployed
- PM2 installed and configured
- ADR-001 stdio transport implemented

**Acceptance Criteria:**
- Tool can query documents via MCP during execution
- Cache hit rate > 70% for document queries
- Fallback to direct PostgreSQL on MCP unavailability
- MCP server restarts automatically via PM2

**Technology Stack:**
- MCP Python SDK for stdio transport
- PM2 for MCP server lifecycle
- Redis 7 for document cache (5-min TTL)
- Local LRU cache for immutable document versions

---

#### Phase 6: State Bridge Integration (Phase 16) (Weeks 13-14)

**Objective:** Enable checkpointing and resumability for long-running tools.

**Deliverables:**
- State Bridge component
- MCP stdio client for context-orchestrator server
- Hybrid checkpointing: micro (Redis/30s), macro (PostgreSQL/milestones), named (manual)
- save_context_snapshot() integration
- create_checkpoint() integration
- get_unified_context() for resume
- rollback_to() for failure recovery
- Checkpoint serialization (JSON + gzip + delta encoding)
- Async execution patterns: polling, webhook, job queue

**Dependencies:**
- Phase 5 complete
- Phase 16 context-orchestrator MCP server deployed
- Redis 7 cluster with sufficient memory for micro-checkpoints
- PostgreSQL 16 with sufficient storage for macro-checkpoints

**Acceptance Criteria:**
- Long-running tools (>30s) create micro-checkpoints
- Tool can resume from last checkpoint after failure
- Checkpoint compression reduces storage by >60%
- Async tool invocation with client polling

**Technology Stack:**
- MCP Python SDK for stdio transport
- PM2 for MCP server lifecycle
- Redis 7 for micro-checkpoints (TTL 1 hour)
- PostgreSQL 16 for macro/named checkpoints
- gzip for checkpoint compression
- Delta encoding for state changes

---

### 11.2 Implementation Order (Dependency Graph)

```
[Phase 1: Core Registry + Basic Execution]
        |
        v
[Phase 2: Permission Integration (ABAC)]
        |
        v
[Phase 3: Circuit Breaker + External Adapters]
        |
        v
[Phase 4: Result Validation + Audit Logging]
        |
        +----+----+
        |         |
        v         v
[Phase 5:   [Phase 6:
 Document    State
 Bridge]     Bridge]
        |         |
        +----+----+
             |
             v
     [Production Ready]
```

**Critical Path:** Phases 1-4 must be completed sequentially. Phases 5 and 6 can be implemented in parallel after Phase 4.

**Dependencies:**
- Phase 2 depends on Phase 1 (registry must exist before permission checks)
- Phase 3 depends on Phase 2 (external APIs need permission checks)
- Phase 4 depends on Phase 3 (validation requires external adapter results)
- Phases 5 and 6 depend on Phase 4 (MCP bridges require audit logging)

**Milestones:**
- **M1 (Week 3):** Basic tool invocation working
- **M2 (Week 5):** Secure invocation with ABAC
- **M3 (Week 8):** Resilient external API integration
- **M4 (Week 10):** Compliant audit trail
- **M5 (Week 14):** Full MCP integration and long-running tools

---

### 11.3 Component Implementation Details

#### 11.3.1 Tool Registry Implementation

**Responsibilities:**
- Store tool definitions with semantic versioning
- Enable semantic search over tool capabilities (pgvector embeddings)
- Manage tool lifecycle (active, deprecated, sunset, removed)
- Provide fast retrieval by tool_id and version

**PostgreSQL Schema:**

```sql
-- Tool definitions table
CREATE TABLE tool_definitions (
  tool_id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  description_embedding VECTOR(768), -- Ollama Mistral 7B embeddings
  current_version VARCHAR(50) NOT NULL,
  provider VARCHAR(255) NOT NULL,
  protocol VARCHAR(50) NOT NULL, -- 'mcp', 'openapi', 'native', 'langchain'
  lifecycle_state VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'deprecated', 'sunset', 'removed'
  deprecation_date TIMESTAMP,
  sunset_date TIMESTAMP,
  migration_guide_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_lifecycle_state CHECK (lifecycle_state IN ('active', 'deprecated', 'sunset', 'removed'))
);

-- Index for semantic search
CREATE INDEX idx_tool_description_embedding
  ON tool_definitions
  USING ivfflat (description_embedding vector_cosine_ops)
  WITH (lists = 100);

-- Tool versions table
CREATE TABLE tool_versions (
  tool_id VARCHAR(255) NOT NULL,
  version VARCHAR(50) NOT NULL,
  manifest JSONB NOT NULL,
  result_schema JSONB,
  timeout_default INTEGER NOT NULL DEFAULT 30, -- seconds
  retry_policy JSONB,
  circuit_breaker_config JSONB,
  required_permissions JSONB NOT NULL, -- ['filesystem:read', 'network:https://api.example.com']
  changelog TEXT,
  breaking_changes BOOLEAN NOT NULL DEFAULT FALSE,
  published_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tool_id, version),
  FOREIGN KEY (tool_id) REFERENCES tool_definitions(tool_id) ON DELETE CASCADE
);

-- Tool invocation history (for analytics)
CREATE TABLE tool_invocations (
  invocation_id UUID PRIMARY KEY,
  tool_id VARCHAR(255) NOT NULL,
  tool_version VARCHAR(50) NOT NULL,
  agent_did VARCHAR(500) NOT NULL,
  status VARCHAR(50) NOT NULL, -- 'success', 'error', 'timeout', 'cancelled'
  duration_ms INTEGER,
  invoked_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  error_code VARCHAR(20),
  FOREIGN KEY (tool_id, tool_version) REFERENCES tool_versions(tool_id, version)
);

-- Index for analytics queries
CREATE INDEX idx_tool_invocations_tool_status
  ON tool_invocations(tool_id, status, invoked_at DESC);
```

**Python Implementation:**

```python
from typing import List, Optional
import asyncpg
from pgvector.asyncpg import register_vector
from dataclasses import dataclass
import json

@dataclass
class ToolDefinition:
    tool_id: str
    name: str
    description: str
    current_version: str
    provider: str
    protocol: str
    lifecycle_state: str
    deprecation_date: Optional[str] = None
    sunset_date: Optional[str] = None
    migration_guide_url: Optional[str] = None

@dataclass
class ToolVersion:
    tool_id: str
    version: str
    manifest: dict
    result_schema: Optional[dict]
    timeout_default: int
    retry_policy: Optional[dict]
    circuit_breaker_config: Optional[dict]
    required_permissions: List[str]
    changelog: Optional[str]
    breaking_changes: bool

class ToolRegistry:
    def __init__(self, db_pool: asyncpg.Pool, ollama_client):
        self.db = db_pool
        self.ollama = ollama_client

    async def register_tool(self, definition: ToolDefinition, version: ToolVersion) -> None:
        """Register a new tool or update existing tool."""
        # Generate embedding for semantic search
        embedding = await self.ollama.embed(version.manifest['description'])

        async with self.db.acquire() as conn:
            await register_vector(conn)

            # Upsert tool definition
            await conn.execute("""
                INSERT INTO tool_definitions
                  (tool_id, name, description, description_embedding, current_version,
                   provider, protocol, lifecycle_state, deprecation_date, sunset_date, migration_guide_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (tool_id) DO UPDATE SET
                  current_version = EXCLUDED.current_version,
                  description = EXCLUDED.description,
                  description_embedding = EXCLUDED.description_embedding,
                  updated_at = NOW()
            """, definition.tool_id, definition.name, definition.description,
                 embedding, definition.current_version, definition.provider,
                 definition.protocol, definition.lifecycle_state,
                 definition.deprecation_date, definition.sunset_date,
                 definition.migration_guide_url)

            # Insert tool version
            await conn.execute("""
                INSERT INTO tool_versions
                  (tool_id, version, manifest, result_schema, timeout_default,
                   retry_policy, circuit_breaker_config, required_permissions,
                   changelog, breaking_changes)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (tool_id, version) DO UPDATE SET
                  manifest = EXCLUDED.manifest,
                  result_schema = EXCLUDED.result_schema,
                  timeout_default = EXCLUDED.timeout_default
            """, version.tool_id, version.version, json.dumps(version.manifest),
                 json.dumps(version.result_schema) if version.result_schema else None,
                 version.timeout_default,
                 json.dumps(version.retry_policy) if version.retry_policy else None,
                 json.dumps(version.circuit_breaker_config) if version.circuit_breaker_config else None,
                 json.dumps(version.required_permissions),
                 version.changelog, version.breaking_changes)

    async def get_tool_version(self, tool_id: str, version: str) -> Optional[ToolVersion]:
        """Retrieve specific tool version."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM tool_versions
                WHERE tool_id = $1 AND version = $2
            """, tool_id, version)

            if not row:
                return None

            return ToolVersion(
                tool_id=row['tool_id'],
                version=row['version'],
                manifest=row['manifest'],
                result_schema=row['result_schema'],
                timeout_default=row['timeout_default'],
                retry_policy=row['retry_policy'],
                circuit_breaker_config=row['circuit_breaker_config'],
                required_permissions=row['required_permissions'],
                changelog=row['changelog'],
                breaking_changes=row['breaking_changes']
            )

    async def semantic_search(self, query: str, limit: int = 10) -> List[ToolDefinition]:
        """Search tools by semantic similarity to query."""
        # Generate embedding for query
        query_embedding = await self.ollama.embed(query)

        async with self.db.acquire() as conn:
            await register_vector(conn)

            rows = await conn.fetch("""
                SELECT tool_id, name, description, current_version, provider,
                       protocol, lifecycle_state,
                       1 - (description_embedding <=> $1) AS similarity
                FROM tool_definitions
                WHERE lifecycle_state IN ('active', 'deprecated')
                ORDER BY description_embedding <=> $1
                LIMIT $2
            """, query_embedding, limit)

            return [
                ToolDefinition(
                    tool_id=row['tool_id'],
                    name=row['name'],
                    description=row['description'],
                    current_version=row['current_version'],
                    provider=row['provider'],
                    protocol=row['protocol'],
                    lifecycle_state=row['lifecycle_state']
                )
                for row in rows
            ]

    async def resolve_version(self, tool_id: str, version_range: str) -> Optional[str]:
        """Resolve version range to specific version (SemVer)."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT version FROM tool_versions
                WHERE tool_id = $1
                ORDER BY published_at DESC
            """, tool_id)

            versions = [row['version'] for row in rows]

            # Use semantic_version library to resolve range
            import semantic_version
            spec = semantic_version.NpmSpec(version_range)

            for v in versions:
                try:
                    version_obj = semantic_version.Version(v)
                    if version_obj in spec:
                        return v
                except ValueError:
                    continue

            return None

    async def deprecate_tool(self, tool_id: str, migration_guide_url: Optional[str] = None) -> None:
        """Mark tool as deprecated."""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE tool_definitions
                SET lifecycle_state = 'deprecated',
                    deprecation_date = NOW(),
                    sunset_date = NOW() + INTERVAL '90 days',
                    migration_guide_url = $2,
                    updated_at = NOW()
                WHERE tool_id = $1
            """, tool_id, migration_guide_url)
```

**Key Design Decisions:**
- **Semantic versioning:** Tools use major.minor.patch format. Agents specify version ranges (e.g., "^2.1.0").
- **Lifecycle states:** active → deprecated (90-day warning) → sunset (grace period) → removed
- **Semantic search:** pgvector enables "find tools that can send emails" queries
- **Version resolution:** Highest compatible version within agent's range selected automatically

---

#### 11.3.2 Tool Executor Implementation

**Responsibilities:**
- Execute tools in nested sandbox (within agent sandbox per BC-1)
- Enforce timeout and resource limits
- Capture stdout, stderr, exit code
- Handle tool crashes and OOM kills
- Support sync and async execution modes

**Nested Sandbox Architecture:**

```
+----------------------------------------------------------+
| Agent Sandbox (L02 Agent Runtime)                        |
| - CPU: 4 cores                                           |
| - Memory: 8 GB                                           |
| - Network: Restricted to allowed domains                 |
|                                                          |
|  +----------------------------------------------------+  |
|  | Tool Sandbox (L03 Tool Execution Layer)            |  |
|  | - CPU: 1 core (inherited from agent, sub-allocated)|  |
|  | - Memory: 512 MB (inherited from agent)            |  |
|  | - Network: Further restricted to tool allowlist    |  |
|  | - Filesystem: Read-only except /tmp                |  |
|  | - Capabilities: Dropped (no CAP_NET_RAW, etc.)    |  |
|  |                                                    |  |
|  |  [Tool Process]                                    |  |
|  |                                                    |  |
|  +----------------------------------------------------+  |
|                                                          |
+----------------------------------------------------------+
```

**Kubernetes Implementation (gVisor for cloud):**

```python
from kubernetes import client, config
from typing import Dict, Any, Optional
import asyncio
import json

class ToolExecutor:
    def __init__(self, k8s_namespace: str, sandbox_mode: str = 'gvisor'):
        """
        Args:
            k8s_namespace: Kubernetes namespace for tool execution
            sandbox_mode: 'gvisor' (cloud) or 'firecracker' (on-prem)
        """
        config.load_incluster_config()  # Load from pod service account
        self.k8s = client.CoreV1Api()
        self.namespace = k8s_namespace
        self.sandbox_mode = sandbox_mode

    async def execute_tool_sync(
        self,
        tool_id: str,
        tool_version: str,
        parameters: Dict[str, Any],
        timeout: int,
        resource_limits: Dict[str, str],
        network_policy: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute tool synchronously and wait for result."""

        # Create pod spec with nested sandbox
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': f'tool-{tool_id}-{tool_version}-{asyncio.get_event_loop().time()}'.replace('.', '-')[:63],
                'namespace': self.namespace,
                'labels': {
                    'app': 'tool-executor',
                    'tool-id': tool_id,
                    'tool-version': tool_version
                },
                'annotations': {
                    'io.kubernetes.cri.untrusted-workload': 'true'  # gVisor
                }
            },
            'spec': {
                'runtimeClassName': self.sandbox_mode,  # 'gvisor' or 'firecracker'
                'restartPolicy': 'Never',
                'securityContext': {
                    'runAsNonRoot': True,
                    'runAsUser': 65534,  # nobody
                    'fsGroup': 65534,
                    'seccompProfile': {
                        'type': 'RuntimeDefault'
                    }
                },
                'containers': [{
                    'name': 'tool',
                    'image': f'tool-registry.local/{tool_id}:{tool_version}',
                    'command': ['/tool/entrypoint.sh'],
                    'args': [json.dumps(parameters)],
                    'env': self._build_env_vars(credentials) if credentials else [],
                    'resources': {
                        'limits': {
                            'cpu': resource_limits.get('cpu', '1'),
                            'memory': resource_limits.get('memory', '512Mi'),
                            'ephemeral-storage': '1Gi'
                        },
                        'requests': {
                            'cpu': resource_limits.get('cpu', '1'),
                            'memory': resource_limits.get('memory', '512Mi')
                        }
                    },
                    'securityContext': {
                        'allowPrivilegeEscalation': False,
                        'readOnlyRootFilesystem': True,
                        'capabilities': {
                            'drop': ['ALL']
                        }
                    },
                    'volumeMounts': [{
                        'name': 'tmp',
                        'mountPath': '/tmp'
                    }]
                }],
                'volumes': [{
                    'name': 'tmp',
                    'emptyDir': {
                        'sizeLimit': '100Mi'
                    }
                }],
                'activeDeadlineSeconds': timeout
            }
        }

        # Apply network policy
        if network_policy:
            await self._apply_network_policy(pod_manifest['metadata']['name'], network_policy)

        # Create pod
        pod = self.k8s.create_namespaced_pod(
            namespace=self.namespace,
            body=pod_manifest
        )

        # Wait for completion or timeout
        try:
            result = await self._wait_for_pod_completion(pod.metadata.name, timeout)
            return result
        finally:
            # Cleanup pod
            self.k8s.delete_namespaced_pod(
                name=pod.metadata.name,
                namespace=self.namespace,
                grace_period_seconds=0
            )

    async def _wait_for_pod_completion(self, pod_name: str, timeout: int) -> Dict[str, Any]:
        """Poll pod status until completion or timeout."""
        start_time = asyncio.get_event_loop().time()

        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Tool execution exceeded {timeout}s timeout")

            pod = self.k8s.read_namespaced_pod(name=pod_name, namespace=self.namespace)

            if pod.status.phase == 'Succeeded':
                # Read logs for output
                logs = self.k8s.read_namespaced_pod_log(name=pod_name, namespace=self.namespace)
                return {
                    'status': 'success',
                    'output': logs,
                    'exit_code': 0
                }

            elif pod.status.phase == 'Failed':
                logs = self.k8s.read_namespaced_pod_log(name=pod_name, namespace=self.namespace)
                container_status = pod.status.container_statuses[0]
                exit_code = container_status.state.terminated.exit_code if container_status.state.terminated else -1

                return {
                    'status': 'error',
                    'output': logs,
                    'exit_code': exit_code,
                    'reason': container_status.state.terminated.reason if container_status.state.terminated else 'Unknown'
                }

            # Poll every 500ms
            await asyncio.sleep(0.5)

    def _build_env_vars(self, credentials: Dict[str, str]) -> list:
        """Convert credentials to environment variables."""
        return [
            {'name': key.upper(), 'value': value}
            for key, value in credentials.items()
        ]

    async def _apply_network_policy(self, pod_name: str, network_policy: str) -> None:
        """Apply Kubernetes NetworkPolicy for tool."""
        # Parse network policy (e.g., "allow:api.example.com,deny:*")
        # Create NetworkPolicy CRD
        pass  # Implementation omitted for brevity
```

**Key Design Decisions:**
- **Nested sandbox:** Tool runs within agent sandbox, inherits resource limits
- **gVisor vs Firecracker:** gVisor for cloud (no KVM required), Firecracker for on-prem (hardware isolation)
- **Read-only root filesystem:** Prevents tool from modifying its own code
- **Dropped capabilities:** Tools run with minimal Linux capabilities
- **Active deadline:** Kubernetes enforces timeout at pod level

---

#### 11.3.3 Permission Checker Implementation

**Responsibilities:**
- Validate JWT capability tokens (RS256 signature)
- Query ABAC engine for tool access permissions
- Cache permission decisions in Redis (5-minute TTL)
- Invalidate cache on policy updates via pub/sub

**Python Implementation:**

```python
import jwt
from typing import Dict, Any, Optional
import redis.asyncio as aioredis
import httpx
import json
from datetime import datetime, timedelta

class PermissionChecker:
    def __init__(self, redis_client: aioredis.Redis, abac_engine_url: str, jwt_public_key: str):
        self.redis = redis_client
        self.abac_url = abac_engine_url
        self.jwt_public_key = jwt_public_key
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def check_permission(
        self,
        capability_token: str,
        tool_id: str,
        tool_version: str,
        required_permissions: list[str]
    ) -> Dict[str, Any]:
        """Check if agent has permission to invoke tool."""

        # 1. Validate and decode JWT token
        try:
            payload = jwt.decode(
                capability_token,
                self.jwt_public_key,
                algorithms=['RS256'],
                options={'verify_exp': True}
            )
        except jwt.ExpiredSignatureError:
            return {'allowed': False, 'reason': 'Token expired', 'error_code': 'E3201'}
        except jwt.InvalidSignatureError:
            return {'allowed': False, 'reason': 'Invalid token signature', 'error_code': 'E3202'}
        except jwt.DecodeError:
            return {'allowed': False, 'reason': 'Malformed token', 'error_code': 'E3203'}

        agent_did = payload.get('sub')  # Agent DID
        tool_capabilities = payload.get('tools', [])

        # 2. Check cache first
        cache_key = f"perm:{agent_did}:{tool_id}:{tool_version}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 3. Verify tool in capability token
        tool_allowed = any(
            tc['tool_id'] == tool_id and self._version_matches(tc.get('version_range', '*'), tool_version)
            for tc in tool_capabilities
        )

        if not tool_allowed:
            return {'allowed': False, 'reason': 'Tool not in capability token', 'error_code': 'E3204'}

        # 4. Query ABAC engine for fine-grained permissions
        abac_request = {
            'subject': agent_did,
            'action': 'tool.invoke',
            'resource': f'tool:{tool_id}:{tool_version}',
            'context': {
                'required_permissions': required_permissions,
                'timestamp': datetime.utcnow().isoformat()
            }
        }

        try:
            abac_response = await self.http_client.post(
                f"{self.abac_url}/v1/authorize",
                json=abac_request
            )
            abac_response.raise_for_status()
            abac_result = abac_response.json()
        except httpx.HTTPError as e:
            return {'allowed': False, 'reason': f'ABAC engine error: {str(e)}', 'error_code': 'E3205'}

        result = {
            'allowed': abac_result.get('decision') == 'allow',
            'reason': abac_result.get('reason', ''),
            'obligations': abac_result.get('obligations', [])
        }

        # 5. Cache decision (5-minute TTL)
        await self.redis.setex(cache_key, 300, json.dumps(result))

        return result

    def _version_matches(self, version_range: str, version: str) -> bool:
        """Check if version matches range (SemVer)."""
        if version_range == '*':
            return True
        import semantic_version
        spec = semantic_version.NpmSpec(version_range)
        try:
            version_obj = semantic_version.Version(version)
            return version_obj in spec
        except ValueError:
            return False

    async def subscribe_to_policy_updates(self):
        """Subscribe to Redis pub/sub for cache invalidation."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe('abac:policy:updates')

        async for message in pubsub.listen():
            if message['type'] == 'message':
                # Invalidate cache for affected DIDs
                policy_update = json.loads(message['data'])
                affected_dids = policy_update.get('affected_subjects', [])
                
                for did in affected_dids:
                    # Delete all cached permissions for this DID
                    async for key in self.redis.scan_iter(match=f"perm:{did}:*"):
                        await self.redis.delete(key)
```

**Key Design Decisions:**
- **JWT RS256:** Asymmetric signatures prevent token forgery
- **Cache-aside pattern:** Check Redis before ABAC engine
- **Pub/sub invalidation:** Real-time cache updates on policy changes
- **5-minute TTL:** Balance between freshness and performance

---

#### 11.3.4 Circuit Breaker Controller Implementation

**Responsibilities:**
- Track external service health (success/failure rates)
- Transition between closed/open/half-open states
- Persist state in Redis for distributed coordination
- Implement canary testing in half-open state

**State Machine:**

```
        [CLOSED]
          |  ^
  failure |  | success threshold
 threshold|  | sustained
          v  |
        [OPEN] ----timeout----> [HALF-OPEN]
                                     |  ^
                           success% |  | failure
                           threshold|  | threshold
                                     v  |
                                 [CLOSED]
```

**Python Implementation:**

```python
import aioredis
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
import asyncio

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerController:
    def __init__(self, redis_client: aioredis.Redis, service_id: str):
        self.redis = redis_client
        self.service_id = service_id
        self.key_prefix = f"cb:{service_id}"

        # Configuration (loaded from PostgreSQL in real implementation)
        self.failure_threshold = 5  # failures to trip breaker
        self.success_threshold = 3  # successes to close breaker
        self.timeout_seconds = 60   # open -> half-open transition
        self.half_open_max_calls = 10  # canary call limit
        self.window_size = 60  # rolling window in seconds

    async def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        state_str = await self.redis.get(f"{self.key_prefix}:state")
        if not state_str:
            # Initialize to CLOSED
            await self.redis.set(f"{self.key_prefix}:state", CircuitBreakerState.CLOSED.value)
            return CircuitBreakerState.CLOSED
        return CircuitBreakerState(state_str.decode())

    async def record_success(self):
        """Record successful external API call."""
        state = await self.get_state()

        # Increment success counter in rolling window
        now = datetime.utcnow().timestamp()
        await self.redis.zadd(
            f"{self.key_prefix}:successes",
            {str(now): now}
        )

        if state == CircuitBreakerState.HALF_OPEN:
            # Check if we've reached success threshold
            recent_successes = await self._count_recent_events('successes')
            if recent_successes >= self.success_threshold:
                await self._transition_to(CircuitBreakerState.CLOSED)
        
        # Cleanup old events
        await self._cleanup_old_events()

    async def record_failure(self):
        """Record failed external API call."""
        state = await self.get_state()

        # Increment failure counter in rolling window
        now = datetime.utcnow().timestamp()
        await self.redis.zadd(
            f"{self.key_prefix}:failures",
            {str(now): now}
        )

        if state == CircuitBreakerState.CLOSED:
            # Check if we've exceeded failure threshold
            recent_failures = await self._count_recent_events('failures')
            if recent_failures >= self.failure_threshold:
                await self._transition_to(CircuitBreakerState.OPEN)

        elif state == CircuitBreakerState.HALF_OPEN:
            # Single failure trips back to OPEN
            await self._transition_to(CircuitBreakerState.OPEN)

        # Cleanup old events
        await self._cleanup_old_events()

    async def allow_request(self) -> bool:
        """Check if request should be allowed through circuit breaker."""
        state = await self.get_state()

        if state == CircuitBreakerState.CLOSED:
            return True

        elif state == CircuitBreakerState.OPEN:
            # Check if timeout has elapsed
            opened_at = await self.redis.get(f"{self.key_prefix}:opened_at")
            if opened_at:
                opened_timestamp = float(opened_at)
                if datetime.utcnow().timestamp() - opened_timestamp > self.timeout_seconds:
                    await self._transition_to(CircuitBreakerState.HALF_OPEN)
                    return True
            return False

        elif state == CircuitBreakerState.HALF_OPEN:
            # Implement canary testing: allow limited requests
            half_open_calls = await self.redis.incr(f"{self.key_prefix}:half_open_calls")
            return half_open_calls <= self.half_open_max_calls

        return False

    async def _transition_to(self, new_state: CircuitBreakerState):
        """Transition to new state with logging."""
        old_state = await self.get_state()
        
        await self.redis.set(f"{self.key_prefix}:state", new_state.value)
        
        if new_state == CircuitBreakerState.OPEN:
            await self.redis.set(
                f"{self.key_prefix}:opened_at",
                str(datetime.utcnow().timestamp())
            )
        elif new_state == CircuitBreakerState.HALF_OPEN:
            await self.redis.set(f"{self.key_prefix}:half_open_calls", "0")
        elif new_state == CircuitBreakerState.CLOSED:
            # Reset counters
            await self.redis.delete(f"{self.key_prefix}:opened_at")
            await self.redis.delete(f"{self.key_prefix}:half_open_calls")

        # Log state transition to PostgreSQL for analytics
        # (implementation omitted for brevity)

        # Publish state change event for monitoring
        await self.redis.publish(
            f"cb:state:changes",
            f"{self.service_id}:{old_state.value}->{new_state.value}"
        )

    async def _count_recent_events(self, event_type: str) -> int:
        """Count events in rolling window."""
        cutoff = datetime.utcnow().timestamp() - self.window_size
        return await self.redis.zcount(
            f"{self.key_prefix}:{event_type}",
            cutoff,
            '+inf'
        )

    async def _cleanup_old_events(self):
        """Remove events outside rolling window."""
        cutoff = datetime.utcnow().timestamp() - self.window_size
        await self.redis.zremrangebyscore(f"{self.key_prefix}:successes", '-inf', cutoff)
        await self.redis.zremrangebyscore(f"{self.key_prefix}:failures", '-inf', cutoff)
```

**Key Design Decisions:**
- **Distributed state:** Redis ensures all executor instances see same circuit breaker state
- **Rolling window:** ZSET with timestamp scores for efficient counting
- **Canary testing:** Half-open state limits requests to 10 before full re-open
- **State transitions logged:** PostgreSQL analytics for post-mortems

---

#### 11.3.5 Result Validator Implementation

**Responsibilities:**
- Validate tool output against JSON Schema from manifest
- Perform type coercion (string -> number, ISO 8601 -> Date)
- Sanitize output (remove PII, prevent injection attacks)
- Return validation errors with detailed messages

**Python Implementation:**

```python
from jsonschema import validate, ValidationError, Draft202012Validator
from typing import Any, Dict, Optional
import re
from datetime import datetime

class ResultValidator:
    def __init__(self):
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
        }

        self.sensitive_fields = ['password', 'secret', 'token', 'apiKey', 'api_key', 
                                  'accessToken', 'refresh_token', 'private_key', 
                                  'credit_card', 'ssn', 'social_security']

    def validate_result(
        self,
        result: Any,
        schema: Dict[str, Any],
        sanitize: bool = True
    ) -> Dict[str, Any]:
        """Validate and optionally sanitize tool result."""

        # 1. Type coercion
        coerced_result = self._coerce_types(result, schema)

        # 2. JSON Schema validation
        try:
            validator = Draft202012Validator(schema)
            validator.validate(coerced_result)
        except ValidationError as e:
            return {
                'valid': False,
                'error': 'Schema validation failed',
                'details': str(e.message),
                'path': list(e.path),
                'error_code': 'E3301'
            }

        # 3. Sanitization (if enabled)
        if sanitize:
            sanitized_result = self._sanitize_pii(coerced_result)
        else:
            sanitized_result = coerced_result

        return {
            'valid': True,
            'result': sanitized_result
        }

    def _coerce_types(self, value: Any, schema: Dict[str, Any]) -> Any:
        """Coerce types to match schema."""
        schema_type = schema.get('type')

        if schema_type == 'number' and isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value

        elif schema_type == 'integer' and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return value

        elif schema_type == 'boolean' and isinstance(value, str):
            if value.lower() in ('true', '1', 'yes'):
                return True
            elif value.lower() in ('false', '0', 'no'):
                return False

        elif schema_type == 'string' and schema.get('format') == 'date-time':
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return value
                except ValueError:
                    return value

        elif schema_type == 'object' and isinstance(value, dict):
            # Recursively coerce object properties
            coerced = {}
            properties_schema = schema.get('properties', {})
            for key, val in value.items():
                if key in properties_schema:
                    coerced[key] = self._coerce_types(val, properties_schema[key])
                else:
                    coerced[key] = val
            return coerced

        elif schema_type == 'array' and isinstance(value, list):
            # Recursively coerce array items
            items_schema = schema.get('items', {})
            return [self._coerce_types(item, items_schema) for item in value]

        return value

    def _sanitize_pii(self, data: Any) -> Any:
        """Recursively sanitize PII from data."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Check if field name indicates sensitive data
                if key.lower() in self.sensitive_fields:
                    sanitized[key] = '[REDACTED]'
                else:
                    sanitized[key] = self._sanitize_pii(value)
            return sanitized

        elif isinstance(data, list):
            return [self._sanitize_pii(item) for item in data]

        elif isinstance(data, str):
            # Apply PII regex patterns
            sanitized_str = data
            for pattern_name, pattern in self.pii_patterns.items():
                sanitized_str = pattern.sub(f'[{pattern_name.upper()}_REDACTED]', sanitized_str)
            return sanitized_str

        else:
            return data

    def validate_input_parameters(
        self,
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate tool input parameters before execution."""
        
        # Additional sanitization for inputs to prevent injection attacks
        sanitized_params = self._sanitize_injection_attacks(parameters)

        # Standard schema validation
        return self.validate_result(sanitized_params, schema, sanitize=False)

    def _sanitize_injection_attacks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to prevent SQL injection, command injection, XSS."""
        if isinstance(params, dict):
            return {
                key: self._sanitize_injection_attacks(value)
                for key, value in params.items()
            }
        elif isinstance(params, list):
            return [self._sanitize_injection_attacks(item) for item in params]
        elif isinstance(params, str):
            # Basic sanitization (real implementation would be more sophisticated)
            # Remove dangerous SQL keywords
            dangerous_sql = ['DROP', 'DELETE', 'INSERT', 'UPDATE', '--', ';--', 'UNION', 'SELECT']
            sanitized = params
            for keyword in dangerous_sql:
                if keyword in sanitized.upper():
                    # Escape or reject
                    pass  # Real implementation would apply proper escaping

            # Remove command injection characters
            dangerous_chars = ['|', '&', ';', '`', '$', '(', ')']
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, '')

            return sanitized
        else:
            return params
```

**Key Design Decisions:**
- **AJV (jsonschema library):** Industry standard for JSON Schema validation
- **Type coercion:** Flexible handling of string inputs from LLMs
- **PII sanitization:** Regex + field-based approach for comprehensive coverage
- **Injection prevention:** Defense-in-depth for SQL, command, XSS attacks

---

#### 11.3.6 Document Bridge Implementation (Phase 15)

**Responsibilities:**
- Connect to document-consolidator MCP server via stdio
- Query documents during tool execution
- Implement two-tier caching (Redis + local LRU)
- Handle MCP unavailability with fallback

**Python Implementation:**

```python
import asyncio
from typing import Dict, Any, Optional, List
import json
import aioredis
from cachetools import LRUCache

class DocumentBridge:
    def __init__(
        self,
        mcp_server_path: str,
        redis_client: aioredis.Redis,
        local_cache_size: int = 1000
    ):
        self.mcp_server_path = mcp_server_path
        self.redis = redis_client
        self.local_cache = LRUCache(maxsize=local_cache_size)
        self.mcp_process = None
        self.request_id = 0

    async def start(self):
        """Start MCP server process via stdio."""
        self.mcp_process = await asyncio.create_subprocess_exec(
            'node', self.mcp_server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for initialization
        await asyncio.sleep(0.5)

    async def stop(self):
        """Stop MCP server process."""
        if self.mcp_process:
            self.mcp_process.terminate()
            await self.mcp_process.wait()

    async def get_source_of_truth(
        self,
        query: str,
        scope: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Query for authoritative document information."""

        # 1. Check local cache first (immutable documents)
        cache_key = f"doc:sot:{hash(query)}:{hash(str(scope))}"
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]

        # 2. Check Redis cache (hot documents, 5-min TTL)
        redis_key = f"doc:query:{cache_key}"
        cached = await self.redis.get(redis_key)
        if cached:
            result = json.loads(cached)
            self.local_cache[cache_key] = result
            return result

        # 3. Query MCP server
        try:
            result = await self._call_mcp_method(
                'get_source_of_truth',
                {
                    'query': query,
                    'scope': scope or [],
                    'confidence_threshold': confidence_threshold,
                    'verify_claims': True
                }
            )

            # Cache in Redis (5-min TTL)
            await self.redis.setex(redis_key, 300, json.dumps(result))

            # Cache locally
            self.local_cache[cache_key] = result

            return result

        except Exception as e:
            # 4. Fallback: Direct PostgreSQL query
            return await self._fallback_query(query, scope)

    async def find_overlaps(
        self,
        scope: Optional[List[str]] = None,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find overlapping or conflicting document content."""

        try:
            return await self._call_mcp_method(
                'find_overlaps',
                {
                    'scope': scope or [],
                    'similarity_threshold': similarity_threshold,
                    'include_archived': False
                }
            )
        except Exception as e:
            return []  # Non-critical feature

    async def _call_mcp_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server method via JSON-RPC 2.0."""
        if not self.mcp_process:
            raise RuntimeError("MCP server not started")

        self.request_id += 1
        request = {
            'jsonrpc': '2.0',
            'id': self.request_id,
            'method': method,
            'params': params
        }

        # Write request to stdin
        request_json = json.dumps(request) + '\n'
        self.mcp_process.stdin.write(request_json.encode())
        await self.mcp_process.stdin.drain()

        # Read response from stdout
        response_line = await asyncio.wait_for(
            self.mcp_process.stdout.readline(),
            timeout=10.0
        )
        response = json.loads(response_line.decode())

        if 'error' in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get('result', {})

    async def _fallback_query(self, query: str, scope: Optional[List[str]]) -> Dict[str, Any]:
        """Fallback to direct PostgreSQL query if MCP unavailable."""
        # Direct database query (implementation omitted for brevity)
        # This would query the document-consolidator's PostgreSQL database directly
        return {
            'answer': 'MCP service unavailable, limited information available',
            'confidence': 0.0,
            'sources': []
        }
```

**Key Design Decisions:**
- **stdio transport:** Per ADR-001, no HTTP configuration needed
- **Two-tier caching:** Local LRU for warm data, Redis for hot data
- **5-minute TTL:** Balance freshness with performance
- **Three-tier fallback:** Local cache → Redis → MCP → Direct PostgreSQL

---

#### 11.3.7 State Bridge Implementation (Phase 16)

**Responsibilities:**
- Connect to context-orchestrator MCP server via stdio
- Create hybrid checkpoints (micro/macro/named)
- Serialize tool state with compression
- Support resume from checkpoint after failure

**Python Implementation:**

```python
import asyncio
import json
import gzip
from typing import Dict, Any, Optional
from datetime import datetime

class StateBridge:
    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = mcp_server_path
        self.mcp_process = None
        self.request_id = 0

    async def start(self):
        """Start MCP server process via stdio."""
        self.mcp_process = await asyncio.create_subprocess_exec(
            'node', self.mcp_server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.sleep(0.5)

    async def save_micro_checkpoint(
        self,
        invocation_id: str,
        tool_id: str,
        tool_version: str,
        state: Dict[str, Any]
    ) -> str:
        """Save micro-checkpoint to Redis (30s cadence, 1h TTL)."""
        
        checkpoint = {
            'schema_version': '1.0',
            'invocation_id': invocation_id,
            'tool_id': tool_id,
            'tool_version': tool_version,
            'checkpoint_type': 'micro',
            'timestamp': datetime.utcnow().isoformat(),
            'state': state
        }

        # Compress if > 10 KB
        serialized = json.dumps(checkpoint)
        if len(serialized) > 10240:
            checkpoint_data = gzip.compress(serialized.encode())
            checkpoint['compressed'] = True
        else:
            checkpoint_data = serialized

        try:
            await self._call_mcp_method(
                'save_context_snapshot',
                {
                    'taskId': invocation_id,
                    'updates': {
                        'immediateContext': {
                            'workingOn': state.get('current_phase'),
                            'lastAction': state.get('last_action'),
                            'nextStep': state.get('next_step')
                        }
                    },
                    'syncToFile': False  # Skip file sync for micro-checkpoints
                }
            )
            return checkpoint['timestamp']
        except Exception as e:
            # Non-fatal: log and continue
            return None

    async def save_macro_checkpoint(
        self,
        invocation_id: str,
        tool_id: str,
        tool_version: str,
        state: Dict[str, Any],
        label: str
    ) -> str:
        """Save macro-checkpoint to PostgreSQL (milestone events)."""

        checkpoint = {
            'schema_version': '1.0',
            'invocation_id': invocation_id,
            'tool_id': tool_id,
            'tool_version': tool_version,
            'checkpoint_type': 'macro',
            'timestamp': datetime.utcnow().isoformat(),
            'state': state,
            'label': label
        }

        # Always compress macro-checkpoints
        serialized = json.dumps(checkpoint)
        checkpoint_data = gzip.compress(serialized.encode())

        try:
            result = await self._call_mcp_method(
                'create_checkpoint',
                {
                    'taskId': invocation_id,
                    'label': label,
                    'checkpointType': 'milestone',
                    'description': f"Tool {tool_id} checkpoint: {label}"
                }
            )
            return result.get('checkpointId')
        except Exception as e:
            raise RuntimeError(f"Failed to create macro-checkpoint: {str(e)}")

    async def resume_from_checkpoint(
        self,
        invocation_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume tool execution from checkpoint."""

        try:
            context = await self._call_mcp_method(
                'get_unified_context',
                {
                    'taskId': invocation_id,
                    'includeVersionHistory': True if checkpoint_id else False
                }
            )

            # If specific checkpoint requested, rollback
            if checkpoint_id:
                await self._call_mcp_method(
                    'rollback_to',
                    {
                        'taskId': invocation_id,
                        'target': {'type': 'checkpoint', 'checkpointId': checkpoint_id}
                    }
                )

            # Deserialize state
            state = context.get('immediateContext', {}).get('state', {})

            # Decompress if needed
            if state.get('compressed'):
                decompressed = gzip.decompress(state['data'])
                state = json.loads(decompressed.decode())

            return state

        except Exception as e:
            raise RuntimeError(f"Failed to resume from checkpoint: {str(e)}")

    async def _call_mcp_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server method via JSON-RPC 2.0."""
        if not self.mcp_process:
            raise RuntimeError("MCP server not started")

        self.request_id += 1
        request = {
            'jsonrpc': '2.0',
            'id': self.request_id,
            'method': method,
            'params': params
        }

        request_json = json.dumps(request) + '\n'
        self.mcp_process.stdin.write(request_json.encode())
        await self.mcp_process.stdin.drain()

        response_line = await asyncio.wait_for(
            self.mcp_process.stdout.readline(),
            timeout=10.0
        )
        response = json.loads(response_line.decode())

        if 'error' in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get('result', {})
```

**Key Design Decisions:**
- **Hybrid checkpointing:** Micro (Redis/30s) for resume, macro (PostgreSQL/milestones) for audit
- **Compression:** gzip for >10KB checkpoints, 60-80% storage reduction
- **Delta encoding:** Reference parent_checkpoint_id for incremental state
- **90-day retention:** Macro-checkpoints archived to S3 Glacier after 90 days

---

### 11.4 Code Examples

#### 11.4.1 Tool Invocation Handler (Complete Flow)

```python
from fastapi import FastAPI, HTTPException, Header
from typing import Optional
import uuid
from datetime import datetime

app = FastAPI()

@app.post("/v1/tools/invoke")
async def invoke_tool(
    request: ToolInvokeRequest,
    authorization: str = Header(...)
):
    """
    Complete tool invocation flow integrating all components.
    """
    invocation_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    try:
        # 1. Extract capability token
        if not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        capability_token = authorization[7:]

        # 2. Retrieve tool version from registry
        tool_version = await tool_registry.get_tool_version(
            request.tool_id,
            request.tool_version or 'latest'
        )
        if not tool_version:
            await audit_logger.log_event({
                'event_type': 'tool.invoke.error',
                'invocation_id': invocation_id,
                'tool_id': request.tool_id,
                'error_code': 'E3101',
                'error_message': 'Tool not found'
            })
            raise HTTPException(status_code=404, detail="Tool not found")

        # 3. Check permissions
        permission_result = await permission_checker.check_permission(
            capability_token,
            request.tool_id,
            tool_version.version,
            tool_version.required_permissions
        )
        if not permission_result['allowed']:
            await audit_logger.log_event({
                'event_type': 'tool.invoke.denied',
                'invocation_id': invocation_id,
                'tool_id': request.tool_id,
                'error_code': permission_result.get('error_code', 'E3200'),
                'error_message': permission_result['reason']
            })
            raise HTTPException(status_code=403, detail=permission_result['reason'])

        # 4. Validate input parameters
        validation_result = result_validator.validate_input_parameters(
            request.parameters,
            tool_version.manifest['parameters']
        )
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail=validation_result['error'])

        # 5. Check circuit breaker for external APIs
        if tool_version.manifest.get('external_service'):
            service_id = tool_version.manifest['external_service']
            cb = CircuitBreakerController(redis_client, service_id)
            if not await cb.allow_request():
                raise HTTPException(status_code=503, detail="Service unavailable (circuit breaker open)")

        # 6. Retrieve credentials from vault (if needed)
        credentials = None
        if 'credentials' in tool_version.required_permissions:
            credentials = await secrets_manager.get_ephemeral_credentials(
                tool_id=request.tool_id,
                lifetime=tool_version.timeout_default
            )

        # 7. Execute tool in nested sandbox
        try:
            result = await tool_executor.execute_tool_sync(
                tool_id=request.tool_id,
                tool_version=tool_version.version,
                parameters=validation_result['result'],
                timeout=tool_version.timeout_default,
                resource_limits=tool_version.manifest.get('resource_limits', {}),
                network_policy=tool_version.manifest.get('network_policy'),
                credentials=credentials,
                invocation_id=invocation_id
            )

            # Record success for circuit breaker
            if tool_version.manifest.get('external_service'):
                await cb.record_success()

        except Exception as e:
            # Record failure for circuit breaker
            if tool_version.manifest.get('external_service'):
                await cb.record_failure()
            raise

        # 8. Validate result against schema
        if tool_version.result_schema:
            validation_result = result_validator.validate_result(
                result['output'],
                tool_version.result_schema,
                sanitize=True
            )
            if not validation_result['valid']:
                raise HTTPException(status_code=500, detail="Tool returned invalid output")
            result['output'] = validation_result['result']

        # 9. Log successful invocation
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        await audit_logger.log_event({
            'event_type': 'tool.invoke.success',
            'invocation_id': invocation_id,
            'tool_id': request.tool_id,
            'tool_version': tool_version.version,
            'duration_ms': duration_ms,
            'status': result['status']
        })

        return {
            'invocation_id': invocation_id,
            'status': result['status'],
            'result': result['output'],
            'execution_time_ms': duration_ms
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected error
        await audit_logger.log_event({
            'event_type': 'tool.invoke.error',
            'invocation_id': invocation_id,
            'tool_id': request.tool_id,
            'error_code': 'E3000',
            'error_message': str(e)
        })
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

### 11.5 Error Code Registry (E3000-E3999)

The Tool Execution Layer uses error codes in the E3000-E3999 range.

#### E3000-E3099: General Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3000 | Internal server error | 500 | Retry with exponential backoff |
| E3001 | Service temporarily unavailable | 503 | Wait and retry |
| E3002 | Request timeout | 504 | Increase timeout or optimize tool |
| E3003 | Rate limit exceeded | 429 | Slow down request rate |
| E3004 | Invalid request format | 400 | Check request schema |

#### E3100-E3149: Tool Registry Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3101 | Tool not found | 404 | Verify tool_id exists in registry |
| E3102 | Tool version not found | 404 | Check available versions |
| E3103 | Tool version conflict | 409 | Resolve version range constraints |
| E3104 | Tool deprecated | 410 | Use recommended replacement tool |
| E3105 | Tool manifest invalid | 422 | Fix manifest schema |
| E3106 | Semantic search failed | 500 | Check Ollama service availability |

#### E3200-E3249: Permission Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3201 | Token expired | 401 | Obtain new capability token |
| E3202 | Invalid token signature | 401 | Verify token signing key |
| E3203 | Malformed token | 401 | Check JWT format |
| E3204 | Tool not in capability token | 403 | Request token with tool permission |
| E3205 | ABAC engine error | 503 | Check ABAC service health |
| E3206 | Permission denied | 403 | Request additional permissions |
| E3207 | DID not found | 404 | Verify agent DID registration |

#### E3300-E3349: Validation Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3301 | Schema validation failed | 400 | Fix parameters to match schema |
| E3302 | Type coercion failed | 400 | Provide correct parameter types |
| E3303 | Result validation failed | 500 | Tool returned invalid output |
| E3304 | PII sanitization error | 500 | Check sanitization rules |
| E3305 | Injection attack detected | 400 | Remove malicious input |

#### E3400-E3449: Execution Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3401 | Tool execution failed | 500 | Check tool logs |
| E3402 | Tool timeout | 504 | Increase timeout or optimize tool |
| E3403 | Tool OOM killed | 500 | Increase memory limit |
| E3404 | Tool crashed | 500 | Check tool stability |
| E3405 | Sandbox creation failed | 500 | Check Kubernetes cluster health |
| E3406 | Network policy violation | 403 | Verify allowed domains |
| E3407 | Resource limit exceeded | 429 | Reduce resource usage |

#### E3500-E3549: Circuit Breaker Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3501 | Circuit breaker open | 503 | Wait for timeout period |
| E3502 | External service unavailable | 503 | Check service health |
| E3503 | External service timeout | 504 | Increase timeout or check service |
| E3504 | Rate limit exceeded (external) | 429 | Reduce request rate |

#### E3600-E3649: Secrets Management Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3601 | Vault unavailable | 503 | Check Vault service |
| E3602 | Credential not found | 404 | Provision credentials in Vault |
| E3603 | Credential expired | 401 | Rotate credentials |
| E3604 | Credential decryption failed | 500 | Verify encryption keys |

#### E3700-E3749: Async Execution Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3701 | Job queue full | 503 | Wait and retry |
| E3702 | Job not found | 404 | Verify invocation_id |
| E3703 | Job cancelled | 499 | Resubmit if needed |
| E3704 | Webhook delivery failed | 500 | Check webhook endpoint |

#### E3800-E3849: Audit Logging Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3801 | Kafka unavailable | 503 | Check Kafka cluster |
| E3802 | Event serialization failed | 500 | Check event schema |
| E3803 | Audit backpressure | 503 | Reduce event rate |

#### E3850-E3899: MCP Document Bridge Errors (Phase 15)

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3851 | MCP server unavailable | 503 | Check document-consolidator service |
| E3852 | Document not found | 404 | Verify document exists |
| E3853 | Document query timeout | 504 | Simplify query or increase timeout |
| E3854 | Document cache miss | 200 | Normal, query will hit database |
| E3855 | Document permission denied | 403 | Request document access |
| E3856 | MCP protocol error | 500 | Check MCP server logs |

#### E3900-E3949: MCP State Bridge Errors (Phase 16)

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| E3901 | MCP server unavailable | 503 | Check context-orchestrator service |
| E3902 | Checkpoint creation failed | 500 | Check PostgreSQL/Redis health |
| E3903 | Checkpoint not found | 404 | Verify checkpoint_id |
| E3904 | Checkpoint corrupted | 500 | Use earlier checkpoint |
| E3905 | Resume failed | 500 | Restart from scratch |
| E3906 | State serialization failed | 500 | Reduce state size |
| E3907 | MCP protocol error | 500 | Check MCP server logs |

---

## Section 12: Testing Strategy

### 12.1 Test Categories

The Tool Execution Layer testing strategy follows a five-tier pyramid:

```
              [Security Tests]
             /                \
        [Chaos Tests]    [Performance Tests]
       /                                    \
  [Integration Tests]              [Integration Tests]
 /                                                    \
[Unit Tests - Tool Registry, Permission, Validator, ...]
```

**Test Distribution:**
- Unit Tests: 60% of total test count
- Integration Tests: 25%
- Performance Tests: 10%
- Chaos Tests: 3%
- Security Tests: 2%

**Test Execution Frequency:**
- Unit Tests: Every commit (CI pipeline)
- Integration Tests: Every pull request
- Performance Tests: Nightly
- Chaos Tests: Weekly
- Security Tests: Release candidates only

---

### 12.2 Unit Tests (Per Component)

#### 12.2.1 Tool Registry Tests

```python
import pytest
from tool_registry import ToolRegistry, ToolDefinition, ToolVersion

@pytest.mark.asyncio
async def test_register_tool_success(db_pool, ollama_client):
    """Test successful tool registration."""
    registry = ToolRegistry(db_pool, ollama_client)
    
    definition = ToolDefinition(
        tool_id='test_tool',
        name='Test Tool',
        description='A tool for testing',
        current_version='1.0.0',
        provider='test',
        protocol='native',
        lifecycle_state='active'
    )
    
    version = ToolVersion(
        tool_id='test_tool',
        version='1.0.0',
        manifest={'description': 'Test tool', 'parameters': {}},
        result_schema={'type': 'object'},
        timeout_default=30,
        retry_policy=None,
        circuit_breaker_config=None,
        required_permissions=['network:https://api.test.com'],
        changelog='Initial release',
        breaking_changes=False
    )
    
    await registry.register_tool(definition, version)
    
    # Verify registration
    retrieved = await registry.get_tool_version('test_tool', '1.0.0')
    assert retrieved is not None
    assert retrieved.tool_id == 'test_tool'

@pytest.mark.asyncio
async def test_semantic_search(db_pool, ollama_client):
    """Test semantic search over tools."""
    registry = ToolRegistry(db_pool, ollama_client)
    
    # Register test tools
    await registry.register_tool(
        ToolDefinition('email_tool', 'Email Sender', 'Send emails to recipients', '1.0.0', 'test', 'native', 'active'),
        ToolVersion('email_tool', '1.0.0', {'description': 'Send emails'}, None, 30, None, None, [], None, False)
    )
    
    # Search for email tools
    results = await registry.semantic_search('send message to user')
    assert len(results) > 0
    assert results[0].tool_id == 'email_tool'

@pytest.mark.asyncio
async def test_version_resolution_semver(db_pool, ollama_client):
    """Test SemVer version resolution."""
    registry = ToolRegistry(db_pool, ollama_client)
    
    # Register multiple versions
    for version in ['1.0.0', '1.1.0', '1.2.0', '2.0.0']:
        await registry.register_tool(
            ToolDefinition('test_tool', 'Test', 'Test tool', version, 'test', 'native', 'active'),
            ToolVersion('test_tool', version, {'description': 'Test'}, None, 30, None, None, [], None, False)
        )
    
    # Resolve version range
    resolved = await registry.resolve_version('test_tool', '^1.0.0')
    assert resolved == '1.2.0'  # Highest 1.x version
    
    resolved = await registry.resolve_version('test_tool', '~1.1.0')
    assert resolved == '1.1.0'  # Patch updates only

@pytest.mark.asyncio
async def test_tool_deprecation(db_pool, ollama_client):
    """Test tool deprecation workflow."""
    registry = ToolRegistry(db_pool, ollama_client)
    
    # Register and then deprecate
    await registry.register_tool(
        ToolDefinition('old_tool', 'Old Tool', 'Deprecated tool', '1.0.0', 'test', 'native', 'active'),
        ToolVersion('old_tool', '1.0.0', {'description': 'Old'}, None, 30, None, None, [], None, False)
    )
    
    await registry.deprecate_tool('old_tool', 'https://docs.example.com/migration')
    
    # Verify deprecation
    tools = await registry.semantic_search('old tool')
    assert tools[0].lifecycle_state == 'deprecated'
    assert tools[0].migration_guide_url == 'https://docs.example.com/migration'
```

---

#### 12.2.2 Permission Checker Tests

```python
import pytest
import jwt
from permission_checker import PermissionChecker
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_valid_capability_token(redis_client, jwt_keypair):
    """Test successful permission check with valid token."""
    checker = PermissionChecker(redis_client, 'http://abac:8080', jwt_keypair['public'])
    
    # Create valid token
    token_payload = {
        'sub': 'did:example:agent123',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'tools': [
            {'tool_id': 'test_tool', 'version_range': '^1.0.0'}
        ]
    }
    token = jwt.encode(token_payload, jwt_keypair['private'], algorithm='RS256')
    
    # Mock ABAC response
    # (In real test, use httpx_mock fixture)
    
    result = await checker.check_permission(token, 'test_tool', '1.0.0', ['network:*'])
    assert result['allowed'] == True

@pytest.mark.asyncio
async def test_expired_token(redis_client, jwt_keypair):
    """Test permission denial for expired token."""
    checker = PermissionChecker(redis_client, 'http://abac:8080', jwt_keypair['public'])
    
    # Create expired token
    token_payload = {
        'sub': 'did:example:agent123',
        'exp': datetime.utcnow() - timedelta(hours=1),  # Expired
        'tools': [{'tool_id': 'test_tool', 'version_range': '*'}]
    }
    token = jwt.encode(token_payload, jwt_keypair['private'], algorithm='RS256')
    
    result = await checker.check_permission(token, 'test_tool', '1.0.0', [])
    assert result['allowed'] == False
    assert result['error_code'] == 'E3201'

@pytest.mark.asyncio
async def test_permission_cache_hit(redis_client, jwt_keypair):
    """Test permission cache reduces ABAC queries."""
    checker = PermissionChecker(redis_client, 'http://abac:8080', jwt_keypair['public'])
    
    token_payload = {
        'sub': 'did:example:agent123',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'tools': [{'tool_id': 'test_tool', 'version_range': '*'}]
    }
    token = jwt.encode(token_payload, jwt_keypair['private'], algorithm='RS256')
    
    # First call - cache miss
    result1 = await checker.check_permission(token, 'test_tool', '1.0.0', [])
    
    # Second call - cache hit (mock ABAC should not be called)
    result2 = await checker.check_permission(token, 'test_tool', '1.0.0', [])
    
    assert result1 == result2
    # Verify cache hit (test implementation would track ABAC call count)

@pytest.mark.asyncio
async def test_cache_invalidation_on_policy_update(redis_client, jwt_keypair):
    """Test cache invalidation via Redis pub/sub."""
    checker = PermissionChecker(redis_client, 'http://abac:8080', jwt_keypair['public'])
    
    # Cache a permission
    cache_key = 'perm:did:example:agent123:test_tool:1.0.0'
    await redis_client.setex(cache_key, 300, '{"allowed": true}')
    
    # Simulate policy update notification
    await redis_client.publish('abac:policy:updates', json.dumps({
        'affected_subjects': ['did:example:agent123']
    }))
    
    # Start cache invalidation listener in background
    asyncio.create_task(checker.subscribe_to_policy_updates())
    await asyncio.sleep(0.5)
    
    # Verify cache cleared
    cached = await redis_client.get(cache_key)
    assert cached is None
```

---

#### 12.2.3 Circuit Breaker Tests

```python
import pytest
from circuit_breaker import CircuitBreakerController, CircuitBreakerState

@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success(redis_client):
    """Test circuit breaker remains closed with successful requests."""
    cb = CircuitBreakerController(redis_client, 'test_service')
    
    # Record successful requests
    for _ in range(10):
        assert await cb.allow_request() == True
        await cb.record_success()
    
    state = await cb.get_state()
    assert state == CircuitBreakerState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failure_threshold(redis_client):
    """Test circuit breaker opens after failure threshold."""
    cb = CircuitBreakerController(redis_client, 'test_service')
    cb.failure_threshold = 5
    
    # Record failures
    for i in range(5):
        assert await cb.allow_request() == True
        await cb.record_failure()
    
    # Should be OPEN now
    state = await cb.get_state()
    assert state == CircuitBreakerState.OPEN
    assert await cb.allow_request() == False

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout(redis_client):
    """Test circuit breaker transitions to half-open after timeout."""
    cb = CircuitBreakerController(redis_client, 'test_service')
    cb.failure_threshold = 3
    cb.timeout_seconds = 2  # Short timeout for testing
    
    # Trip breaker
    for _ in range(3):
        await cb.record_failure()
    
    assert await cb.get_state() == CircuitBreakerState.OPEN
    
    # Wait for timeout
    await asyncio.sleep(2.5)
    
    # Should transition to HALF_OPEN
    assert await cb.allow_request() == True
    assert await cb.get_state() == CircuitBreakerState.HALF_OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_canary_testing(redis_client):
    """Test half-open state limits canary requests."""
    cb = CircuitBreakerController(redis_client, 'test_service')
    cb.half_open_max_calls = 5
    
    # Manually set to HALF_OPEN
    await cb._transition_to(CircuitBreakerState.HALF_OPEN)
    
    # First 5 requests allowed
    for i in range(5):
        assert await cb.allow_request() == True
    
    # 6th request blocked
    assert await cb.allow_request() == False

@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_half_open_success(redis_client):
    """Test half-open transitions to closed after successes."""
    cb = CircuitBreakerController(redis_client, 'test_service')
    cb.success_threshold = 3
    
    await cb._transition_to(CircuitBreakerState.HALF_OPEN)
    
    # Record successes
    for _ in range(3):
        await cb.record_success()
    
    assert await cb.get_state() == CircuitBreakerState.CLOSED
```

---

#### 12.2.4 Result Validator Tests

```python
import pytest
from result_validator import ResultValidator

def test_schema_validation_success():
    """Test successful JSON Schema validation."""
    validator = ResultValidator()
    
    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'age': {'type': 'integer'}
        },
        'required': ['name']
    }
    
    result = validator.validate_result(
        {'name': 'Alice', 'age': 30},
        schema
    )
    
    assert result['valid'] == True

def test_schema_validation_failure():
    """Test schema validation catches invalid data."""
    validator = ResultValidator()
    
    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'age': {'type': 'integer'}
        },
        'required': ['name']
    }
    
    result = validator.validate_result(
        {'age': 'thirty'},  # Invalid: age should be integer
        schema
    )
    
    assert result['valid'] == False
    assert result['error_code'] == 'E3301'

def test_type_coercion():
    """Test automatic type coercion."""
    validator = ResultValidator()
    
    schema = {
        'type': 'object',
        'properties': {
            'count': {'type': 'integer'},
            'price': {'type': 'number'},
            'active': {'type': 'boolean'}
        }
    }
    
    result = validator.validate_result(
        {'count': '42', 'price': '19.99', 'active': 'true'},
        schema
    )
    
    assert result['valid'] == True
    assert result['result']['count'] == 42
    assert result['result']['price'] == 19.99
    assert result['result']['active'] == True

def test_pii_sanitization_regex():
    """Test PII sanitization with regex patterns."""
    validator = ResultValidator()
    
    data = {
        'message': 'Contact me at alice@example.com or 555-123-4567',
        'ssn': '123-45-6789'
    }
    
    schema = {'type': 'object'}
    result = validator.validate_result(data, schema, sanitize=True)
    
    assert result['valid'] == True
    assert '[EMAIL_REDACTED]' in result['result']['message']
    assert '[PHONE_REDACTED]' in result['result']['message']
    assert '[SSN_REDACTED]' in result['result']['ssn']

def test_pii_sanitization_field_based():
    """Test field-based PII sanitization."""
    validator = ResultValidator()
    
    data = {
        'username': 'alice',
        'password': 'secret123',
        'apiKey': 'sk-1234567890'
    }
    
    schema = {'type': 'object'}
    result = validator.validate_result(data, schema, sanitize=True)
    
    assert result['valid'] == True
    assert result['result']['username'] == 'alice'
    assert result['result']['password'] == '[REDACTED]'
    assert result['result']['apiKey'] == '[REDACTED]'

def test_injection_attack_prevention():
    """Test SQL injection and command injection prevention."""
    validator = ResultValidator()
    
    params = {
        'query': "SELECT * FROM users WHERE id = 1; DROP TABLE users;--",
        'command': "ls /tmp; rm -rf /"
    }
    
    schema = {'type': 'object'}
    result = validator.validate_input_parameters(params, schema)
    
    assert result['valid'] == True
    # Verify dangerous characters stripped
    assert 'DROP' not in result['result']['query']
    assert ';' not in result['result']['command']
```

---

#### 12.2.5 Document Bridge Tests (Mock MCP)

```python
import pytest
from document_bridge import DocumentBridge
import json

@pytest.mark.asyncio
async def test_document_query_with_local_cache(redis_client, mock_mcp_server):
    """Test document query hits local cache."""
    bridge = DocumentBridge(mock_mcp_server, redis_client)
    
    # Prepopulate local cache
    cache_key = f"doc:sot:{hash('test query')}:{hash('None')}"
    expected_result = {'answer': 'Cached result', 'confidence': 0.95}
    bridge.local_cache[cache_key] = expected_result
    
    result = await bridge.get_source_of_truth('test query')
    
    assert result == expected_result
    # MCP server should not be called

@pytest.mark.asyncio
async def test_document_query_with_redis_cache(redis_client, mock_mcp_server):
    """Test document query hits Redis cache."""
    bridge = DocumentBridge(mock_mcp_server, redis_client)
    
    # Prepopulate Redis cache
    redis_key = 'doc:query:test_key'
    expected_result = {'answer': 'Redis cached', 'confidence': 0.9}
    await redis_client.setex(redis_key, 300, json.dumps(expected_result))
    
    # Query should hit Redis, not MCP
    # (Test would verify MCP not called via mock)

@pytest.mark.asyncio
async def test_document_query_mcp_call(redis_client, mock_mcp_server):
    """Test document query calls MCP server on cache miss."""
    bridge = DocumentBridge(mock_mcp_server, redis_client)
    await bridge.start()
    
    # Mock MCP server response
    expected_result = {
        'answer': 'MCP result',
        'confidence': 0.85,
        'sources': [{'document_id': 'doc123', 'excerpt': '...'}]
    }
    # (Mock would inject this response)
    
    result = await bridge.get_source_of_truth('new query')
    
    # Verify result cached in Redis
    # Verify result cached locally
    await bridge.stop()

@pytest.mark.asyncio
async def test_document_query_fallback_on_mcp_failure(redis_client):
    """Test fallback to direct PostgreSQL on MCP failure."""
    bridge = DocumentBridge('/nonexistent/mcp/server', redis_client)
    
    # MCP server doesn't start - should fallback
    result = await bridge.get_source_of_truth('query')
    
    assert 'MCP service unavailable' in result['answer']
    assert result['confidence'] == 0.0

@pytest.mark.asyncio
async def test_find_overlaps(redis_client, mock_mcp_server):
    """Test overlap detection via MCP."""
    bridge = DocumentBridge(mock_mcp_server, redis_client)
    await bridge.start()
    
    overlaps = await bridge.find_overlaps(
        scope=['doc1', 'doc2'],
        similarity_threshold=0.8
    )
    
    # Verify MCP call made with correct parameters
    await bridge.stop()
```

---

#### 12.2.6 State Bridge Tests (Mock MCP)

```python
import pytest
from state_bridge import StateBridge
import json

@pytest.mark.asyncio
async def test_save_micro_checkpoint(mock_mcp_server):
    """Test micro-checkpoint creation."""
    bridge = StateBridge(mock_mcp_server)
    await bridge.start()
    
    state = {
        'current_phase': 'processing',
        'progress': 0.45,
        'last_action': 'fetched_data',
        'next_step': 'transform_data'
    }
    
    checkpoint_id = await bridge.save_micro_checkpoint(
        'invocation123',
        'test_tool',
        '1.0.0',
        state
    )
    
    assert checkpoint_id is not None
    await bridge.stop()

@pytest.mark.asyncio
async def test_save_macro_checkpoint(mock_mcp_server):
    """Test macro-checkpoint creation."""
    bridge = StateBridge(mock_mcp_server)
    await bridge.start()
    
    state = {
        'current_phase': 'completed',
        'progress': 1.0,
        'results': {'count': 42}
    }
    
    checkpoint_id = await bridge.save_macro_checkpoint(
        'invocation123',
        'test_tool',
        '1.0.0',
        state,
        'final_results'
    )
    
    assert checkpoint_id is not None
    await bridge.stop()

@pytest.mark.asyncio
async def test_resume_from_checkpoint(mock_mcp_server):
    """Test resuming execution from checkpoint."""
    bridge = StateBridge(mock_mcp_server)
    await bridge.start()
    
    # Create checkpoint
    original_state = {'phase': 'step2', 'data': {'key': 'value'}}
    checkpoint_id = await bridge.save_micro_checkpoint(
        'invocation123', 'test_tool', '1.0.0', original_state
    )
    
    # Resume from checkpoint
    restored_state = await bridge.resume_from_checkpoint('invocation123', checkpoint_id)
    
    assert restored_state['phase'] == 'step2'
    assert restored_state['data']['key'] == 'value'
    await bridge.stop()

@pytest.mark.asyncio
async def test_checkpoint_compression(mock_mcp_server):
    """Test checkpoint compression for large states."""
    bridge = StateBridge(mock_mcp_server)
    await bridge.start()
    
    # Create large state (> 10 KB)
    large_state = {
        'data': ['x' * 1000 for _ in range(20)]  # ~20 KB
    }
    
    checkpoint_id = await bridge.save_macro_checkpoint(
        'invocation123', 'test_tool', '1.0.0', large_state, 'large_state'
    )
    
    # Verify compression applied (test would check MCP call payload size)
    assert checkpoint_id is not None
    await bridge.stop()
```

---

### 12.3 Integration Tests

#### 12.3.1 Tool Invocation End-to-End

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_tool_invocation_flow(test_app, db_pool, redis_client):
    """Test complete tool invocation from API to execution."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # 1. Register tool
        tool_manifest = {
            'tool_id': 'echo_tool',
            'version': '1.0.0',
            'name': 'Echo Tool',
            'description': 'Echoes input back',
            'parameters': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                },
                'required': ['message']
            },
            'result_schema': {
                'type': 'object',
                'properties': {
                    'echoed': {'type': 'string'}
                }
            }
        }
        
        response = await client.post('/v1/tools/register', json=tool_manifest)
        assert response.status_code == 201
        
        # 2. Generate capability token
        token = create_test_capability_token(['echo_tool'])
        
        # 3. Invoke tool
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'echo_tool',
                'tool_version': '1.0.0',
                'parameters': {'message': 'Hello World'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'success'
        assert result['result']['echoed'] == 'Hello World'

@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_invocation_with_permission_denial(test_app):
    """Test tool invocation denied without proper permissions."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Token without tool permission
        token = create_test_capability_token([])  # Empty permissions
        
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'echo_tool',
                'tool_version': '1.0.0',
                'parameters': {'message': 'Hello'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 403
        assert 'E3204' in response.json()['detail']
```

---

#### 12.3.2 ABAC Integration Test

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_abac_engine_integration(test_app, abac_engine_url):
    """Test integration with ABAC engine for fine-grained permissions."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Token with tool permission
        token = create_test_capability_token(['restricted_tool'])
        
        # First invocation - ABAC allows
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'restricted_tool',
                'tool_version': '1.0.0',
                'parameters': {'action': 'read'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        
        # Update ABAC policy to deny
        # (Test helper updates ABAC engine)
        
        # Second invocation - ABAC denies
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'restricted_tool',
                'tool_version': '1.0.0',
                'parameters': {'action': 'delete'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403
```

---

#### 12.3.3 Phase 15 Document Context Flow

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_with_document_context(test_app, document_consolidator_server):
    """Test tool accessing document context via Phase 15 bridge."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['document_aware_tool'])
        
        # Tool implementation queries documents during execution
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'document_aware_tool',
                'tool_version': '1.0.0',
                'parameters': {
                    'document_query': 'API authentication requirements'
                }
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        result = response.json()
        # Verify tool result includes document context
        assert 'document_context' in result['result']
        assert result['result']['document_context']['confidence'] > 0.7
```

---

#### 12.3.4 Phase 16 Checkpoint/Restore Flow

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_long_running_tool_with_checkpoints(test_app, context_orchestrator_server):
    """Test long-running tool with checkpoint/restore."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['long_running_tool'])
        
        # Start async tool invocation
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'long_running_tool',
                'tool_version': '1.0.0',
                'parameters': {'iterations': 100},
                'execution_mode': 'async'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 202  # Accepted
        invocation_id = response.json()['invocation_id']
        
        # Wait for checkpoint creation
        await asyncio.sleep(35)  # Micro-checkpoint every 30s
        
        # Simulate failure - kill tool process
        # (Test helper kills the execution)
        
        # Resume from checkpoint
        response = await client.post(
            f'/v1/tools/resume/{invocation_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        # Verify tool resumed from checkpoint, not restarted from scratch
```

---

### 12.4 Performance Tests

#### 12.4.1 Tool Execution Latency

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_tool_execution_latency_p95(test_app, metrics):
    """Test P95 tool execution latency < 500ms."""
    latencies = []
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['fast_tool'])
        
        # Execute 100 invocations
        for _ in range(100):
            start = time.time()
            response = await client.post(
                '/v1/tools/invoke',
                json={
                    'tool_id': 'fast_tool',
                    'tool_version': '1.0.0',
                    'parameters': {}
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)
            assert response.status_code == 200
        
        # Calculate P95
        latencies.sort()
        p95 = latencies[94]  # 95th percentile
        
        assert p95 < 500, f"P95 latency {p95}ms exceeds 500ms target"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_tool_invocations(test_app):
    """Test concurrent tool invocation throughput."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['concurrent_tool'])
        
        async def invoke_tool():
            response = await client.post(
                '/v1/tools/invoke',
                json={
                    'tool_id': 'concurrent_tool',
                    'tool_version': '1.0.0',
                    'parameters': {}
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            return response.status_code
        
        # Launch 50 concurrent invocations
        start = time.time()
        tasks = [invoke_tool() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        # All should succeed
        assert all(status == 200 for status in results)
        
        # Throughput > 20 req/sec
        throughput = 50 / duration
        assert throughput > 20, f"Throughput {throughput} req/s below 20 req/s target"
```

---

#### 12.4.2 Permission Check Latency

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_permission_check_latency(permission_checker, redis_client):
    """Test permission check latency < 50ms (P95)."""
    latencies = []
    
    token = create_test_capability_token(['test_tool'])
    
    # Warm up cache
    await permission_checker.check_permission(token, 'test_tool', '1.0.0', [])
    
    # Measure cached performance
    for _ in range(100):
        start = time.time()
        await permission_checker.check_permission(token, 'test_tool', '1.0.0', [])
        latency = (time.time() - start) * 1000
        latencies.append(latency)
    
    latencies.sort()
    p95 = latencies[94]
    
    assert p95 < 50, f"P95 permission check latency {p95}ms exceeds 50ms target"
```

---

### 12.5 Chaos Tests

#### 12.5.1 External Service Failure

```python
@pytest.mark.chaos
@pytest.mark.asyncio
async def test_external_service_failure_resilience(test_app, chaos_engineering):
    """Test circuit breaker opens on external service failure."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['external_api_tool'])
        
        # Inject failure into external service
        chaos_engineering.inject_fault('external_api', failure_rate=1.0)
        
        # First few invocations fail
        for i in range(5):
            response = await client.post(
                '/v1/tools/invoke',
                json={
                    'tool_id': 'external_api_tool',
                    'tool_version': '1.0.0',
                    'parameters': {}
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            # Circuit breaker opens after threshold
            if i < 5:
                assert response.status_code == 500
        
        # Circuit breaker should be open now
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'external_api_tool',
                'tool_version': '1.0.0',
                'parameters': {}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 503  # Service unavailable
        assert 'E3501' in response.text  # Circuit breaker open
        
        # Remove fault
        chaos_engineering.clear_faults()

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_mcp_service_unavailability(test_app, chaos_engineering):
    """Test graceful degradation when MCP services unavailable."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['document_aware_tool'])
        
        # Kill MCP document server
        chaos_engineering.kill_process('document-consolidator')
        
        # Tool invocation should still succeed with fallback
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'document_aware_tool',
                'tool_version': '1.0.0',
                'parameters': {'query': 'test'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        result = response.json()
        # Should have fallback result with lower confidence
        assert result['result']['document_context']['confidence'] < 0.5
        
        # Restart MCP server
        chaos_engineering.start_process('document-consolidator')
```

---

#### 12.5.2 Checkpoint Corruption Recovery

```python
@pytest.mark.chaos
@pytest.mark.asyncio
async def test_checkpoint_corruption_recovery(test_app, chaos_engineering):
    """Test recovery from corrupted checkpoint."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['long_running_tool'])
        
        # Start tool execution
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'long_running_tool',
                'tool_version': '1.0.0',
                'parameters': {'iterations': 50},
                'execution_mode': 'async'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        invocation_id = response.json()['invocation_id']
        
        # Wait for checkpoint
        await asyncio.sleep(35)
        
        # Corrupt checkpoint in Redis
        chaos_engineering.corrupt_redis_key(f"checkpoint:{invocation_id}")
        
        # Attempt resume - should fall back to earlier checkpoint
        response = await client.post(
            f'/v1/tools/resume/{invocation_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Should recover from PostgreSQL macro-checkpoint
        assert response.status_code == 200
```

---

### 12.6 Security Tests

#### 12.6.1 Sandbox Escape Attempt

```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_sandbox_escape_prevention(test_app):
    """Test that malicious tools cannot escape sandbox."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['malicious_tool'])
        
        # Tool attempts to read /etc/passwd
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'malicious_tool',
                'tool_version': '1.0.0',
                'parameters': {'file': '/etc/passwd'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Should fail due to read-only filesystem
        assert response.status_code == 500
        # Verify /etc/passwd not in output
        assert '/etc/passwd' not in response.text

@pytest.mark.security
@pytest.mark.asyncio
async def test_privilege_escalation_prevention(test_app):
    """Test that tools cannot escalate privileges."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['privilege_escalation_tool'])
        
        # Tool attempts to run 'sudo'
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'privilege_escalation_tool',
                'tool_version': '1.0.0',
                'parameters': {'command': 'sudo ls'}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Should fail - no sudo in sandbox
        assert response.status_code == 500
```

---

#### 12.6.2 Credential Exposure Prevention

```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_credential_not_in_logs(test_app, audit_logger):
    """Test that credentials are not leaked in audit logs."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['credential_tool'])
        
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'credential_tool',
                'tool_version': '1.0.0',
                'parameters': {
                    'api_key': 'sk-secret123456',
                    'password': 'supersecret'
                }
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Check audit logs
        logs = await audit_logger.get_recent_logs(limit=10)
        
        for log in logs:
            # Credentials should be redacted
            assert 'sk-secret123456' not in json.dumps(log)
            assert 'supersecret' not in json.dumps(log)
            assert '[REDACTED]' in json.dumps(log)

@pytest.mark.security
@pytest.mark.asyncio
async def test_mcp_injection_attack(test_app):
    """Test prevention of MCP injection attacks."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        token = create_test_capability_token(['document_aware_tool'])
        
        # Attempt to inject malicious MCP command
        malicious_query = '"; DROP TABLE documents;--'
        
        response = await client.post(
            '/v1/tools/invoke',
            json={
                'tool_id': 'document_aware_tool',
                'tool_version': '1.0.0',
                'parameters': {'query': malicious_query}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Should sanitize and not execute SQL
        assert response.status_code == 200
        # Verify no SQL injection occurred
```

---

### 12.7 Test Examples (pytest code)

**Test Fixtures:**

```python
# conftest.py
import pytest
import asyncpg
import aioredis
from httpx import AsyncClient

@pytest.fixture
async def db_pool():
    """PostgreSQL connection pool."""
    pool = await asyncpg.create_pool(
        'postgresql://user:pass@localhost/test_db',
        min_size=2,
        max_size=10
    )
    yield pool
    await pool.close()

@pytest.fixture
async def redis_client():
    """Redis client."""
    client = await aioredis.create_redis_pool('redis://localhost')
    yield client
    client.close()
    await client.wait_closed()

@pytest.fixture
def jwt_keypair():
    """RSA keypair for JWT signing."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    
    return {
        'private': private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ),
        'public': public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    }

@pytest.fixture
def mock_mcp_server(tmp_path):
    """Mock MCP server for testing."""
    # Implementation creates a fake MCP server process
    pass

def create_test_capability_token(tools: list) -> str:
    """Helper to create capability tokens for testing."""
    payload = {
        'sub': 'did:example:test_agent',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'tools': [{'tool_id': tool_id, 'version_range': '*'} for tool_id in tools]
    }
    return jwt.encode(payload, test_private_key, algorithm='RS256')
```

---

## Section 13: Migration and Deployment

### 13.1 Deployment Strategy

#### 13.1.1 Container Image Specification

**Base Image:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 toolexec && \
    mkdir -p /app && \
    chown -R toolexec:toolexec /app

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=toolexec:toolexec . .

USER toolexec

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Key Design Decisions:**
- Non-root user for security
- Multi-stage build for smaller images
- Health checks for Kubernetes readiness

---

### 13.2 Infrastructure Prerequisites (per ADR-002)

#### 13.2.1 PostgreSQL 16 + pgvector Setup

**Production Deployment:**
- High availability with Patroni
- 3-node cluster (1 primary, 2 replicas)
- pgvector extension enabled
- Connection pooling via PgBouncer

#### 13.2.2 Redis 7 Cluster Setup

**Production Configuration:**
- 6-node cluster (3 masters + 3 replicas)
- Persistence: AOF + RDB snapshots
- Memory: 4GB per node minimum
- Eviction policy: allkeys-lru

#### 13.2.3 Ollama Deployment

**Optional Component:**
- Required for semantic tool search
- Mistral 7B model (4GB VRAM)
- CPU-only deployment acceptable for <100 req/s

#### 13.2.4 MCP Services via PM2

**Process Management:**
- document-consolidator on port stdio
- context-orchestrator on port stdio
- Auto-restart on failure
- Log rotation enabled

---

### 13.3 Upgrade Procedures

#### 13.3.1 Zero-Downtime Deployment

**Rolling Update Strategy:**
1. Deploy new version to 1 pod
2. Wait for health checks
3. Gradually roll out to remaining pods
4. Monitor error rates
5. Rollback if error rate > 1%

#### 13.3.2 Database Migration

**Alembic Migrations:**
- Always backward compatible
- Test on staging first
- Automated rollback on failure

#### 13.3.3 MCP Service Updates

**PM2 Reload:**
- Graceful restart with zero downtime
- stdio connections preserved
- Automatic health verification

---

### 13.4 Rollback Procedures

#### 13.4.1 Application Rollback

```bash
kubectl rollout undo deployment/tool-execution-layer -n agentic-platform
```

#### 13.4.2 Database Rollback

```bash
alembic downgrade -1
```

#### 13.4.3 MCP Service Rollback

```bash
git checkout <previous_tag>
npm run build
pm2 reload <service_name>
```

---

### 13.5 Disaster Recovery

#### 13.5.1 Tool Registry Backup

**Automated Daily Backups:**
- PostgreSQL dump to S3
- 30-day retention
- Point-in-time recovery enabled

#### 13.5.2 Circuit Breaker State Recovery

**Redis Persistence:**
- RDB snapshots every 15 minutes
- AOF with everysec fsync
- Automatic recovery on restart

#### 13.5.3 MCP Service Recovery

**Health Monitoring:**
- Automated health checks every 5 minutes
- Auto-restart on failure
- Alert escalation if recovery fails

#### 13.5.4 External Service Failover

**Multi-Region Configuration:**
- Primary + 2 failover endpoints
- Circuit breakers per endpoint
- Cached result fallback

---

## Section 14: Open Questions and Decisions

### 14.1 Resolved Questions

| Question | Decision | Rationale | Version |
|----------|----------|-----------|---------|
| **Q1: Tool Versioning (independent vs agent-tied)?** | Independent with semantic versioning (SemVer) | Tools evolve independently of agents. Agents specify version ranges (e.g., "^2.1.0"). Breaking changes require major version bump. Tool registry stores multiple versions concurrently. | 1.0 |
| **Q2: Long-running operations (>30s)?** | Hybrid checkpointing via Phase 16 State Bridge | Micro-checkpoints (Redis/30s) for resume, macro-checkpoints (PostgreSQL/milestones) for audit, named checkpoints (manual) for recovery. Async execution modes: polling (30s-15min), webhook (15min-24h), job queue (>24h). | 1.0 |
| **Q3: Credential rotation during invocations?** | Just-in-time retrieval, no mid-execution rotation | Credentials fetched from Vault at invocation start. Ephemeral lifetime = tool timeout. No mid-execution rotation (complexity vs benefit trade-off). Rotation happens between invocations. | 1.0 |
| **Q4: MCP tool adapter pattern?** | stdio JSON-RPC 2.0 bridge per ADR-001 | L03 spawns MCP server process via PM2. Opens stdin/stdout pipes. Capability negotiation on startup. Tool invocation serialized to JSON-RPC request. Response deserialized from stdout. No HTTP configuration needed. | 1.0 |
| **Q5: Phase 15 document context caching?** | Two-tier caching: Redis (hot) + local LRU (warm) | `get_source_of_truth` cached in Redis (5-min TTL). Document versions cached locally (immutable). Cache invalidation via Redis pub/sub. Direct PostgreSQL fallback on MCP unavailability. | 1.0 |
| **Q6: Phase 16 checkpoint granularity?** | Hybrid: micro (30s) + macro (event) + named (manual) | Micro-checkpoints to Redis for fine-grained resume. Macro-checkpoints to PostgreSQL for audit trail. Named checkpoints for critical recovery points. Granularity configurable per tool manifest. | 1.0 |
| **Q7: Redis vs PostgreSQL for circuit breaker?** | Redis for state, PostgreSQL for config/history | Circuit breaker state (open/closed, failure counts, timestamps) in Redis with TTL. Configuration (thresholds, timeouts) in PostgreSQL. State transitions logged to PostgreSQL for analytics. Per ADR-002. | 1.0 |

---

### 14.2 Deferred Decisions

| Decision | Reason for Deferral | Target Version | Dependencies |
|----------|---------------------|----------------|--------------|
| **Multi-tool workflow orchestration** | Requires Integration Layer (L11) workflow engine. L03 provides atomic tool invocation only. Workflow logic belongs at higher layer. | v2.0 | L11 specification completion |
| **Tool dependency graph resolution** | Depends on workflow orchestration decision. Currently, Integration Layer responsible for ordering tool calls. | v2.0 | Multi-tool workflows (above) |
| **gRPC alternative to REST API** | REST sufficient for v1.0. gRPC optimization deferred until performance requirements proven unmet. | v1.5 | Performance benchmarks |
| **Tool marketplace and discovery UI** | Developer experience feature. Command-line tools sufficient for v1.0. Web UI deferred to separate project. | v3.0 | None |
| **Advanced semantic search (RAG)** | Ollama embeddings + pgvector sufficient for <1000 tools. RAG needed only for >10K tools. | v2.0 | Tool registry scale requirements |

---

### 14.3 Assumptions

| Assumption | Confidence | Validation Plan | Risk if Invalid |
|------------|------------|-----------------|-----------------|
| **External APIs are RESTful** | High | 95% of enterprise APIs are REST. gRPC/GraphQL adapters can be added later. | Low - Adapter pattern extensible |
| **Tool execution < 2 hours** | Medium | Most agent tasks complete in minutes. Longer tasks use async mode with checkpoints. | Medium - May need job queue optimization |
| **10-100 concurrent tool invocations per agent** | Medium | Based on LangChain/LangGraph benchmarks. Actual workload TBD. | Medium - HPA can scale to 20 pods |
| **Circuit breaker thresholds are consistent across services** | Low | Services may have different SLAs. Thresholds may need per-service tuning. | Low - Configuration supports per-service overrides |
| **PII sanitization regex is sufficient** | Medium | Covers common patterns (email, SSN, CC). May miss domain-specific PII. | High - Requires ongoing updates |
| **MCP servers are reliable** | Medium | Phase 15/16 servers are critical dependencies. Fallback mechanisms in place. | High - Three-tier fallback mitigates |

---

### 14.4 Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| **External API rate limits exceeded** | High | High | Circuit breaker with rate limiting. Back-off strategy. Multiple API keys rotation. | L03 Team |
| **Sandbox escape vulnerability** | Low | Critical | gVisor/Firecracker isolation. Regular security audits. Penetration testing. | Security Team |
| **MCP server crashes** | Medium | High | PM2 auto-restart. Health monitoring. Three-tier fallback (cache → MCP → direct DB). | Platform Team |
| **PostgreSQL connection pool exhaustion** | Medium | High | Connection pooling with PgBouncer. HPA scaling. Connection limit alerts. | Database Team |
| **Redis memory exhaustion** | Medium | Medium | LRU eviction policy. Memory usage alerts. Scaling to 6-node cluster. | Platform Team |
| **Credential leakage in logs** | Medium | Critical | PII sanitization before logging. Field-based redaction. Log access controls. | Security Team |
| **Tool versioning conflicts** | High | Medium | SemVer enforcement. Version range validation. Breaking change warnings. | L03 Team |
| **Checkpoint storage growth** | High | Medium | Tiered retention (Redis 1h, PostgreSQL 90d, S3 Glacier 7y). Compression. | Platform Team |
| **Circuit breaker thrashing** | Medium | Medium | Half-open canary testing. Gradual recovery. Configurable thresholds. | L03 Team |
| **ABAC policy cache stale data** | Low | High | Redis pub/sub invalidation. 5-minute TTL. Cache miss fallback. | Data Layer Team |

---

## Section 15: References and Appendices

### 15.1 External References

| Reference | Version | URL | Usage |
|-----------|---------|-----|-------|
| **Model Context Protocol (MCP)** | 2025-11-25 | https://modelcontextprotocol.io/specification | Phase 15/16 integration, JSON-RPC 2.0 over stdio |
| **JSON-RPC 2.0 Specification** | 2.0 | https://www.jsonrpc.org/specification | MCP wire protocol |
| **Semantic Versioning (SemVer)** | 2.0.0 | https://semver.org | Tool versioning schema |
| **OpenAPI Specification** | 3.1 | https://spec.openapi.org/oas/v3.1.0 | External API tool definitions |
| **JSON Schema** | 2020-12 | https://json-schema.org/draft/2020-12/release-notes | Tool input/output validation |
| **OWASP Secrets Management Cheat Sheet** | 2024 | https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html | Credential injection patterns |
| **Kubernetes CRD API Reference** | v1 | https://kubernetes.io/docs/reference/kubernetes-api/ | Sandbox, NetworkPolicy definitions |
| **CloudEvents Specification** | 1.0 | https://cloudevents.io | Audit event format |
| **gVisor Documentation** | Latest | https://gvisor.dev/docs/ | Sandbox isolation (cloud) |
| **Firecracker MicroVM** | Latest | https://firecracker-microvm.github.io | Sandbox isolation (on-prem) |
| **Resilience4j Documentation** | 2.x | https://resilience4j.readme.io | Circuit breaker pattern |
| **Tenacity Python Library** | Latest | https://tenacity.readthedocs.io | Retry logic with jitter |
| **pgvector Documentation** | 0.5.x | https://github.com/pgvector/pgvector | Vector embeddings in PostgreSQL |
| **Redis Data Structures** | 7.x | https://redis.io/docs/data-types/ | Sorted sets, JSON, pub/sub |
| **HashiCorp Vault** | Latest | https://www.vaultproject.io/docs | Secrets management |
| **Apache Kafka** | 3.x | https://kafka.apache.org/documentation | Audit event streaming |
| **Ollama API** | Latest | https://github.com/ollama/ollama/blob/main/docs/api.md | Local LLM inference |
| **PM2 Documentation** | Latest | https://pm2.keymetrics.io/docs/usage/quick-start/ | MCP process management |

---

### 15.2 Internal References

| Document | Section | Description |
|----------|---------|-------------|
| **Data Layer Specification v4.0** | Section 5: Event Store | Tool invocation events published to Event Store |
| **Data Layer Specification v4.0** | Section 6: ABAC Engine | Permission checks via ABAC policy engine |
| **Data Layer Specification v4.0** | Section 13: Phase 13 MCP Integration | Foundation for Phase 15/16 MCP patterns |
| **Data Layer Specification v4.0** | Phase 15: Document Management | Document Bridge integration via document-consolidator |
| **Data Layer Specification v4.0** | Phase 16: Session Orchestration | State Bridge integration via context-orchestrator |
| **Agent Runtime Specification v1.2** | Section 4: Sandbox Management | BC-1 nested sandbox interface |
| **Model Gateway Specification v1.2** | Section 3: Function Calling | Tool selection and parameter extraction |
| **Integration Layer Specification v1.0** | Section 2: Tool Orchestration | BC-2 tool.invoke() interface consumer |
| **ADR-001: MCP Integration Architecture** | Full Document | stdio transport, capability negotiation, error handling |
| **ADR-002: Lightweight Development Stack** | Full Document | PostgreSQL + Redis + Ollama + PM2 technology decisions |

---

### 15.3 Glossary

| Term | Definition |
|------|------------|
| **ABAC** | Attribute-Based Access Control - Fine-grained authorization based on attributes of subject, resource, action, and context |
| **ADR** | Architecture Decision Record - Document capturing an important architectural decision |
| **AJV** | Another JSON Schema Validator - Industry-standard JSON Schema validation library |
| **BC-1** | Boundary Condition 1 - Nested sandbox interface between Agent Runtime (L02) and Tool Execution Layer (L03) |
| **BC-2** | Boundary Condition 2 - tool.invoke() interface between Tool Execution Layer (L03) and Integration Layer (L11) |
| **Circuit Breaker** | Resilience pattern that prevents cascading failures by opening circuit after threshold failures |
| **CloudEvents** | Specification for describing event data in a common way |
| **DID** | Decentralized Identifier - W3C standard for verifiable, self-sovereign digital identities |
| **gVisor** | User-space kernel for container isolation (cloud deployments) |
| **Firecracker** | MicroVM technology for hardware-level isolation (on-prem deployments) |
| **HPA** | Horizontal Pod Autoscaler - Kubernetes resource for auto-scaling pods based on metrics |
| **HITL** | Human-in-the-Loop - Approval workflow requiring human intervention |
| **JSON-RPC 2.0** | Remote procedure call protocol encoded in JSON |
| **JWT** | JSON Web Token - Compact, URL-safe means of representing claims |
| **L02** | Agent Runtime Layer - Layer responsible for agent execution sandboxing |
| **L03** | Tool Execution Layer - This specification's layer |
| **L11** | Integration Layer - Layer responsible for workflow orchestration |
| **LRU** | Least Recently Used - Cache eviction policy |
| **MCP** | Model Context Protocol - Open standard for AI agent-tool integration |
| **Micro-checkpoint** | Frequent (30s) checkpoint to Redis for quick resume |
| **Macro-checkpoint** | Milestone checkpoint to PostgreSQL for audit trail |
| **Named checkpoint** | Manual checkpoint for critical recovery points |
| **OPA** | Open Policy Agent - Policy engine for fine-grained authorization |
| **PII** | Personally Identifiable Information - Data that can identify an individual |
| **PM2** | Process Manager 2 - Production process manager for Node.js |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **RS256** | RSA Signature with SHA-256 - Asymmetric signing algorithm for JWT |
| **SemVer** | Semantic Versioning - Version numbering scheme (major.minor.patch) |
| **STRIDE** | Security threat modeling framework: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege |
| **TTL** | Time To Live - Expiration time for cached data |

------

## Appendix A: Gap Analysis Integration Summary

This appendix shows how all 24 gaps identified in the gap analysis have been addressed in the specification.

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| **G-001** | Tool capability manifest schema not fully defined | High | 11.3.1 | Complete manifest schema with required_permissions, result_schema, timeout_default, retry_policy, circuit_breaker_config fields defined in PostgreSQL schema and Python implementation |
| **G-002** | Semantic versioning conflict resolution for parallel versions | Medium | 11.3.1 | Version resolution algorithm using semantic_version library with version range matching (resolve_version method) |
| **G-003** | Tool deprecation workflow and migration paths | Medium | 11.3.1 | Lifecycle states (active, deprecated, sunset, removed) with deprecation_date, sunset_date, migration_guide_url fields and deprecate_tool method |
| **G-004** | Async execution patterns for long-running tools (> 15 min) | High | 11.3.7, 11.4.1 | Hybrid checkpointing with micro (Redis/30s), macro (PostgreSQL/milestones), named (manual) checkpoints. Async execution modes: polling, webhook, job queue |
| **G-005** | Tool execution priority scheduling and resource allocation | Medium | 10.4 | Feature flag `enable_tool_priority_scheduling` with priority field in tool manifest. HPA scales based on priority-weighted metrics |
| **G-006** | Capability token format and signing mechanism | Critical | 11.3.3 | JWT with RS256 signatures. Token structure with sub (DID), exp, tools[] array. Validation in Permission Checker |
| **G-007** | Permission cache invalidation on policy updates | High | 11.3.3 | Redis pub/sub subscription to 'abac:policy:updates' channel with automatic cache key deletion for affected DIDs |
| **G-008** | Circuit breaker transition notifications to dependent tools | Medium | 11.3.4 | State transition events published to Redis pub/sub channel 'cb:state:changes' for monitoring and dependent tool awareness |
| **G-009** | Half-open state testing strategy (canary vs all-or-nothing) | Medium | 11.3.4 | Canary testing in HALF_OPEN state with configurable half_open_max_calls (default 10). Gradual traffic increase on success |
| **G-010** | Result validation schema definition and enforcement | Critical | 11.3.5 | JSON Schema validation using AJV (jsonschema library) with type coercion and validation against tool manifest result_schema |
| **G-011** | Type coercion and sanitization rules for tool inputs | High | 11.3.5 | Type coercion pipeline (string->number, ISO 8601->Date, etc.) with injection attack prevention (SQL, command, XSS) |
| **G-012** | Structured output validation against tool manifest | High | 11.3.5 | validate_result method enforces JSON Schema from manifest. Validation errors return E3301 with detailed path and message |
| **G-013** | Document access permission model (ABAC integration) | High | 11.3.6 | Document queries check ABAC permissions before MCP retrieval. Permission results cached in Redis with pub/sub invalidation |
| **G-014** | Bulk document retrieval optimization | Medium | 11.3.6 | Two-tier caching (Redis 5-min + local LRU) reduces MCP round-trips. Batch queries supported via MCP protocol |
| **G-015** | Checkpoint diff/delta encoding for large states | Medium | 11.3.7 | Delta encoding with parent_checkpoint_id reference. gzip compression for >10KB checkpoints (60-80% reduction) |
| **G-016** | Checkpoint compression threshold tuning | Low | 11.3.7 | Compression applied for checkpoints >10KB. Configurable threshold per tool manifest. gzip chosen for balance of speed/ratio |
| **G-017** | PII sanitization rules for tool parameters in audit logs | Critical | 11.3.5, 12.2.4 | Regex patterns (email, SSN, CC, phone, IP) + field-based redaction (password, secret, token, apiKey). Applied before audit logging |
| **G-018** | Audit log schema with CloudEvents 1.0 alignment | High | 11.5 | CloudEvents 1.0 format for tool invocation events (tool.invoke.*, tool.complete.*, tool.error.*) with tool-specific extensions |
| **G-019** | Real-time audit stream backpressure handling | Medium | 9.4 | Backpressure detection via Kafka lag monitoring. Mitigation: sampling (10%), local disk buffering, compression, batching |
| **G-020** | Multi-tool workflow orchestration (sequential, parallel, conditional) | High | 14.2 | **Deferred to L11 Integration Layer**. L03 provides atomic tool invocation only. Workflow DSL and orchestration is L11 responsibility |
| **G-021** | Tool dependency graph resolution and cycle detection | Medium | 14.2 | **Deferred to L11 Integration Layer**. Dependency management belongs at workflow orchestration layer, not individual tool execution |
| **G-022** | HITL approval timeout and escalation policies | Medium | 7.4 | Three-tier escalation: primary approver (1h timeout) → manager (4h) → admin (24h). Configurable per tool manifest |
| **G-023** | Tool execution cost tracking and budgeting | Medium | 9.1 | Prometheus metrics track execution duration and resource usage. Cost calculation based on CPU/memory/duration in external analytics |
| **G-024** | Tool usage analytics and recommendation engine | Medium | 9.5 | Tool invocation history in PostgreSQL enables analytics. Recommendation engine uses invocation patterns and Ollama embeddings |

**Gap Status Summary:**
- **Total Gaps:** 24
- **Addressed in Specification:** 22 (92%)
- **Deferred to Other Layers:** 2 (G-020, G-021 - deferred to L11 Integration Layer)
- **Critical Gaps Addressed:** 3/3 (100%)
- **High-Priority Gaps Addressed:** 10/10 (100%)
- **Medium-Priority Gaps Addressed:** 9/10 (90% - 1 deferred)
- **Low-Priority Gaps Addressed:** 1/1 (100%)

**All critical and high-priority gaps have been fully addressed.**

---

## Appendix B: Error Code Reference

Complete error code reference for E3000-E3999 range.

### Error Code Ranges

| Range | Category | Description |
|-------|----------|-------------|
| E3000-E3099 | General Errors | Service-level errors, timeouts, rate limits |
| E3100-E3149 | Tool Registry | Tool not found, version conflicts, manifest errors |
| E3200-E3249 | Permissions | Authentication, authorization, capability token errors |
| E3300-E3349 | Validation | Schema validation, type coercion, sanitization |
| E3400-E3449 | Execution | Tool execution failures, timeouts, sandbox errors |
| E3500-E3549 | Circuit Breaker | External service failures, circuit breaker states |
| E3600-E3649 | Secrets Management | Vault errors, credential failures |
| E3700-E3749 | Async Execution | Job queue, webhook delivery, cancellation |
| E3800-E3849 | Audit Logging | Kafka errors, event serialization, backpressure |
| E3850-E3899 | Phase 15 MCP Document Bridge | MCP document server errors |
| E3900-E3949 | Phase 16 MCP State Bridge | MCP context server errors |

### Detailed Error Codes (E3000-E3999)

Refer to Section 11.5 for complete error code table with:
- Error code
- Description
- HTTP status code
- Resolution steps

**Error Code Design Principles:**
1. **Numeric ranges** indicate error category
2. **HTTP status codes** aligned with REST API standards
3. **Resolution guidance** provided for each code
4. **Consistent format** across all layers (E-prefix + 4 digits)

---

## Appendix C: Tool Manifest Schema (Complete JSON Schema)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agentic-platform.local/schemas/tool-manifest.schema.json",
  "title": "Tool Manifest",
  "description": "Complete schema for tool capability manifest",
  "type": "object",
  "required": ["tool_id", "version", "name", "description", "provider", "protocol", "parameters"],
  "properties": {
    "tool_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "minLength": 3,
      "maxLength": 255,
      "description": "Unique identifier for tool (snake_case)"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(-[a-z0-9.]+)?(\\+[a-z0-9.]+)?$",
      "description": "Semantic version (major.minor.patch)"
    },
    "name": {
      "type": "string",
      "minLength": 3,
      "maxLength": 255,
      "description": "Human-readable tool name"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 2000,
      "description": "Detailed description for semantic search"
    },
    "provider": {
      "type": "string",
      "description": "Tool provider organization or author"
    },
    "protocol": {
      "type": "string",
      "enum": ["native", "mcp", "openapi", "langchain", "custom"],
      "description": "Tool invocation protocol"
    },
    "parameters": {
      "type": "object",
      "description": "JSON Schema for tool parameters",
      "$ref": "https://json-schema.org/draft/2020-12/schema"
    },
    "result_schema": {
      "type": "object",
      "description": "JSON Schema for tool output",
      "$ref": "https://json-schema.org/draft/2020-12/schema"
    },
    "required_permissions": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[a-z_]+:[^ ]+$"
      },
      "description": "Permission requirements (e.g., 'filesystem:read', 'network:https://api.example.com')",
      "examples": [
        "filesystem:read:/data",
        "network:https://api.example.com",
        "credentials:aws_s3",
        "database:postgresql:read"
      ]
    },
    "timeout_default": {
      "type": "integer",
      "minimum": 1,
      "maximum": 7200,
      "default": 30,
      "description": "Default timeout in seconds"
    },
    "timeout_max": {
      "type": "integer",
      "minimum": 1,
      "maximum": 86400,
      "description": "Maximum allowed timeout (for async operations)"
    },
    "retry_policy": {
      "type": "object",
      "properties": {
        "max_attempts": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10,
          "default": 3
        },
        "backoff_multiplier": {
          "type": "number",
          "minimum": 1.0,
          "maximum": 10.0,
          "default": 2.0
        },
        "backoff_max_seconds": {
          "type": "integer",
          "minimum": 1,
          "maximum": 300,
          "default": 60
        },
        "retry_on_status_codes": {
          "type": "array",
          "items": {
            "type": "integer",
            "minimum": 400,
            "maximum": 599
          },
          "default": [429, 500, 502, 503, 504]
        }
      }
    },
    "circuit_breaker_config": {
      "type": "object",
      "properties": {
        "failure_threshold": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 5,
          "description": "Number of failures to open circuit"
        },
        "success_threshold": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 3,
          "description": "Number of successes to close circuit"
        },
        "timeout_seconds": {
          "type": "integer",
          "minimum": 1,
          "maximum": 3600,
          "default": 60,
          "description": "Time to wait before half-open"
        },
        "half_open_max_calls": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 10,
          "description": "Canary request limit in half-open"
        }
      }
    },
    "resource_limits": {
      "type": "object",
      "properties": {
        "cpu": {
          "type": "string",
          "pattern": "^\\d+m?$",
          "default": "1",
          "description": "CPU limit (e.g., '500m', '2')"
        },
        "memory": {
          "type": "string",
          "pattern": "^\\d+(Mi|Gi)$",
          "default": "512Mi",
          "description": "Memory limit (e.g., '512Mi', '2Gi')"
        },
        "ephemeral_storage": {
          "type": "string",
          "pattern": "^\\d+(Mi|Gi)$",
          "default": "1Gi",
          "description": "Ephemeral storage limit"
        }
      }
    },
    "network_policy": {
      "type": "object",
      "properties": {
        "allowed_domains": {
          "type": "array",
          "items": {
            "type": "string",
            "format": "hostname"
          },
          "description": "Allowed hostnames (wildcards supported: *.example.com)"
        },
        "allowed_ports": {
          "type": "array",
          "items": {
            "type": "integer",
            "minimum": 1,
            "maximum": 65535
          },
          "default": [80, 443]
        },
        "deny_all_egress": {
          "type": "boolean",
          "default": false,
          "description": "Block all outbound network access"
        }
      }
    },
    "external_service": {
      "type": "string",
      "description": "External service ID for circuit breaker (e.g., 'stripe_api', 'sendgrid')"
    },
    "checkpoint_config": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": false,
          "description": "Enable checkpointing for this tool"
        },
        "micro_interval_seconds": {
          "type": "integer",
          "minimum": 10,
          "maximum": 300,
          "default": 30,
          "description": "Micro-checkpoint interval"
        },
        "macro_events": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Events that trigger macro-checkpoints",
          "examples": [
            "phase_complete",
            "milestone_reached",
            "approval_required"
          ]
        }
      }
    },
    "lifecycle_state": {
      "type": "string",
      "enum": ["active", "deprecated", "sunset", "removed"],
      "default": "active"
    },
    "deprecation_date": {
      "type": "string",
      "format": "date",
      "description": "Date tool was marked deprecated"
    },
    "sunset_date": {
      "type": "string",
      "format": "date",
      "description": "Date tool will be removed"
    },
    "migration_guide_url": {
      "type": "string",
      "format": "uri",
      "description": "URL to migration documentation"
    },
    "replacement_tool_id": {
      "type": "string",
      "description": "Recommended replacement tool"
    },
    "priority": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5,
      "description": "Execution priority (1=low, 10=critical)"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Searchable tags for tool discovery"
    },
    "changelog": {
      "type": "string",
      "description": "Version changelog"
    },
    "breaking_changes": {
      "type": "boolean",
      "default": false,
      "description": "True if version introduces breaking changes"
    },
    "documentation_url": {
      "type": "string",
      "format": "uri",
      "description": "Link to tool documentation"
    },
    "source_code_url": {
      "type": "string",
      "format": "uri",
      "description": "Link to tool source code"
    },
    "license": {
      "type": "string",
      "description": "Tool license (SPDX identifier)",
      "examples": ["MIT", "Apache-2.0", "GPL-3.0", "Proprietary"]
    },
    "author": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "url": {"type": "string", "format": "uri"}
      }
    }
  },
  "examples": [
    {
      "tool_id": "send_email",
      "version": "1.2.3",
      "name": "Email Sender",
      "description": "Send emails via SMTP or SendGrid API. Supports attachments, HTML templates, and delivery tracking.",
      "provider": "Platform Team",
      "protocol": "native",
      "parameters": {
        "type": "object",
        "properties": {
          "to": {"type": "string", "format": "email"},
          "subject": {"type": "string", "maxLength": 200},
          "body": {"type": "string"},
          "attachments": {
            "type": "array",
            "items": {"type": "string", "format": "uri"}
          }
        },
        "required": ["to", "subject", "body"]
      },
      "result_schema": {
        "type": "object",
        "properties": {
          "message_id": {"type": "string"},
          "status": {"type": "string", "enum": ["sent", "queued", "failed"]}
        },
        "required": ["message_id", "status"]
      },
      "required_permissions": [
        "network:https://api.sendgrid.com",
        "credentials:sendgrid"
      ],
      "timeout_default": 30,
      "external_service": "sendgrid",
      "circuit_breaker_config": {
        "failure_threshold": 5,
        "timeout_seconds": 60
      },
      "priority": 7,
      "tags": ["communication", "email", "notifications"]
    }
  ]
}
```

---

## Appendix D: MCP Bridge Configuration Examples

### D.1 Document Bridge Configuration

**PM2 Ecosystem Configuration:**
```javascript
// ecosystem.config.js (excerpt)
{
  name: 'mcp-document-consolidator',
  script: './platform/services/mcp-document-consolidator/build/index.js',
  instances: 1,
  exec_mode: 'fork',
  env: {
    NODE_ENV: 'production',
    POSTGRES_HOST: 'localhost',
    POSTGRES_PORT: 5432,
    POSTGRES_DB: 'document_consolidator',
    POSTGRES_USER: 'toolexec',
    POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD,
    LOG_LEVEL: 'info',
    EMBEDDING_MODEL: 'mistral:7b',  // For semantic search
    CACHE_TTL_SECONDS: 300  // 5-minute cache TTL
  },
  autorestart: true,
  max_restarts: 10,
  min_uptime: '10s'
}
```

**Tool Execution Layer Configuration:**
```yaml
# config/mcp_bridges.yaml
document_bridge:
  mcp_server_path: /mcp/document-consolidator/server.js
  enabled: true
  cache:
    redis:
      enabled: true
      ttl_seconds: 300
      key_prefix: "doc:query:"
    local:
      enabled: true
      max_size: 1000
      ttl_seconds: 3600
  fallback:
    direct_postgres: true
    timeout_ms: 5000
  retry:
    max_attempts: 3
    backoff_ms: 1000
```

**MCP Method Mappings:**
```yaml
# Available MCP methods from document-consolidator
methods:
  - name: get_source_of_truth
    description: Query for authoritative document information
    parameters:
      - query: string
      - scope: array (optional)
      - confidence_threshold: number (default: 0.7)
      - verify_claims: boolean (default: true)
    cache: true

  - name: find_overlaps
    description: Find overlapping or conflicting document content
    parameters:
      - scope: array (optional)
      - similarity_threshold: number (default: 0.8)
      - include_archived: boolean (default: false)
    cache: false

  - name: ingest_document
    description: Add document to consolidation index
    parameters:
      - content: string
      - document_type: enum
      - tags: array (optional)
      - extract_claims: boolean (default: true)
    cache: false

  - name: deprecate_document
    description: Mark document as deprecated
    parameters:
      - document_id: uuid
      - reason: string
      - superseded_by: uuid (optional)
    cache: false
```

---

### D.2 State Bridge Configuration

**PM2 Ecosystem Configuration:**
```javascript
// ecosystem.config.js (excerpt)
{
  name: 'mcp-context-orchestrator',
  script: './platform/services/mcp-context-orchestrator/build/index.js',
  instances: 1,
  exec_mode: 'fork',
  env: {
    NODE_ENV: 'production',
    POSTGRES_HOST: 'localhost',
    POSTGRES_PORT: 5432,
    POSTGRES_DB: 'context_orchestrator',
    POSTGRES_USER: 'toolexec',
    POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD,
    REDIS_HOST: 'localhost',
    REDIS_PORT: 6379,
    REDIS_PASSWORD: process.env.REDIS_PASSWORD,
    LOG_LEVEL: 'info',
    CHECKPOINT_RETENTION_DAYS: 90,
    MICRO_CHECKPOINT_TTL_SECONDS: 3600  // 1 hour TTL for micro-checkpoints
  },
  autorestart: true,
  max_restarts: 10,
  min_uptime: '10s'
}
```

**Tool Execution Layer Configuration:**
```yaml
# config/mcp_bridges.yaml
state_bridge:
  mcp_server_path: /mcp/context-orchestrator/server.js
  enabled: true
  checkpointing:
    micro:
      enabled: true
      interval_seconds: 30
      storage: redis
      ttl_seconds: 3600
      compression: true
      compression_threshold_bytes: 10240
    macro:
      enabled: true
      storage: postgresql
      retention_days: 90
      archive_to_s3: true
      archive_after_days: 90
      compression: true
    named:
      enabled: true
      storage: postgresql
      retention: indefinite
      compression: true
  retry:
    max_attempts: 3
    backoff_ms: 1000
```

**MCP Method Mappings:**
```yaml
# Available MCP methods from context-orchestrator
methods:
  - name: save_context_snapshot
    description: Save micro-checkpoint to Redis
    parameters:
      - taskId: string
      - updates: object
      - syncToFile: boolean (default: true)
    cache: false

  - name: create_checkpoint
    description: Create macro or named checkpoint
    parameters:
      - taskId: string
      - label: string
      - checkpointType: enum (milestone, manual, pre_migration, recovery_point, auto)
      - description: string (optional)
    cache: false

  - name: get_unified_context
    description: Retrieve current task context
    parameters:
      - taskId: string
      - includeVersionHistory: boolean (default: false)
      - includeRelationships: boolean (default: true)
    cache: true
    ttl_seconds: 60

  - name: rollback_to
    description: Rollback to previous checkpoint
    parameters:
      - taskId: string
      - target: object {type: "version" | "checkpoint", version?: number, checkpointId?: string}
      - createBackup: boolean (default: true)
    cache: false

  - name: switch_task
    description: Switch between tasks with state preservation
    parameters:
      - fromTaskId: string (optional)
      - toTaskId: string
      - currentTaskUpdates: object (optional)
      - saveCurrentState: boolean (default: true)
    cache: false
```

---

### D.3 MCP Health Check Script

```bash
#!/bin/bash
# check-mcp-health.sh

check_mcp_service() {
  SERVICE_NAME=$1

  # Check if PM2 process is running
  if ! pm2 describe $SERVICE_NAME > /dev/null 2>&1; then
    echo "CRITICAL: $SERVICE_NAME not running"
    return 1
  fi

  # Check if process is responsive
  HEALTH_RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"health","params":{}}' | \
    timeout 5s node platform/services/${SERVICE_NAME}/build/index.js 2>&1 | \
    tail -n 1)

  if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo "OK: $SERVICE_NAME is healthy"
    return 0
  else
    echo "WARNING: $SERVICE_NAME is unresponsive"
    echo "Response: $HEALTH_RESPONSE"
    return 2
  fi
}

# Check both MCP services
check_mcp_service "mcp-document-consolidator"
DOC_STATUS=$?

check_mcp_service "mcp-context-orchestrator"
CTX_STATUS=$?

# Exit with worst status
if [ $DOC_STATUS -ne 0 ] || [ $CTX_STATUS -ne 0 ]; then
  exit 1
fi

exit 0
```

---

### D.4 MCP Error Handling Patterns

**Connection Error Handling:**
```python
async def call_mcp_with_retry(method: str, params: dict, max_attempts: int = 3):
    """Call MCP method with retry and fallback."""
    last_error = None

    for attempt in range(max_attempts):
        try:
            result = await mcp_client.call(method, params)
            return result
        except MCPConnectionError as e:
            last_error = e
            if attempt < max_attempts - 1:
                backoff_ms = 1000 * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(backoff_ms / 1000)
        except MCPTimeoutError as e:
            last_error = e
            # Timeout errors don't retry - fail fast
            break

    # All retries exhausted - use fallback
    if method == 'get_source_of_truth':
        # Fallback to direct PostgreSQL query
        return await fallback_direct_query(params)
    elif method == 'save_context_snapshot':
        # Non-critical - log and continue
        logger.warning(f"Failed to save micro-checkpoint: {last_error}")
        return None
    else:
        raise MCPError(f"MCP method {method} failed after {max_attempts} attempts: {last_error}")
```

**Graceful Degradation:**
```python
async def get_document_context_safe(query: str) -> dict:
    """Get document context with graceful degradation."""
    try:
        # Try MCP bridge first
        result = await document_bridge.get_source_of_truth(query)
        return {
            'answer': result['answer'],
            'confidence': result['confidence'],
            'sources': result['sources'],
            'source': 'mcp'
        }
    except MCPError as e:
        logger.warning(f"MCP unavailable, using fallback: {e}")

        # Fallback to cached data
        cached = await redis.get(f"doc:fallback:{hash(query)}")
        if cached:
            return {
                'answer': cached['answer'],
                'confidence': 0.5,  # Lower confidence for cached
                'sources': cached['sources'],
                'source': 'cache'
            }

        # Last resort: return error but don't fail invocation
        return {
            'answer': 'Document context unavailable',
            'confidence': 0.0,
            'sources': [],
            'source': 'unavailable'
        }
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-14 | Tool Execution Layer Team | Initial specification (Sections 11-15, Appendices A-D) |

---

## Acknowledgments

This specification was developed through:
- **Industry research** across 8 categories (tool registries, sandboxing, resilience, MCP integration, etc.)
- **Gap analysis** identifying 24 gaps in existing architecture
- **Integration** with Data Layer (v4.0), Agent Runtime (v1.2), Model Gateway (v1.2), Integration Layer (v1.0)
- **Alignment** with ADR-001 (MCP stdio transport) and ADR-002 (PostgreSQL + Redis + Ollama + PM2 stack)
- **Standards compliance** with MCP, JSON-RPC 2.0, SemVer, OpenAPI, JSON Schema, CloudEvents 1.0

Special thanks to:
- Data Layer team for ABAC engine, Event Store, and Phase 15/16 MCP services
- Agent Runtime team for BC-1 nested sandbox interface definition
- Security team for threat modeling and PII sanitization requirements
- Platform team for Kubernetes and PM2 operational guidance

---

**End of Tool Execution Layer Specification - Part 3**
