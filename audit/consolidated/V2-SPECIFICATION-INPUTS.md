# Story Portal Platform V2 - Specification Inputs

**Document Purpose:** Technical requirements and architectural inputs derived from comprehensive V2 platform audit
**Audit Date:** January 17, 2026
**Target Audience:** System architects, platform engineers, product managers
**Baseline Comparison:** V1 Platform (Health Score: 65/100) → V2 Platform (Health Score: 52/100)

---

## 1. Infrastructure Requirements

### 1.1 Container Orchestration [Source: AUD-019]

**Current State:**
- 14 Docker containers running
- 13/14 containers healthy (93%)
- No resource limits configured (Memory=0, CPU=0)
- Multiple duplicate networks detected
- No docker-compose.yml found

**Requirements for V2.1:**

```yaml
# Required Resource Limits (per container type)
resources:
  small_services:  # L01, L02, L11
    limits:
      memory: "512Mi"
      cpu: "0.5"
    reservations:
      memory: "256Mi"
      cpu: "0.25"

  medium_services:  # L03-L07, L09, L10, L12
    limits:
      memory: "1Gi"
      cpu: "1.0"
    reservations:
      memory: "512Mi"
      cpu: "0.5"

  large_services:  # Ollama (if containerized)
    limits:
      memory: "4Gi"
      cpu: "2.0"
    reservations:
      memory: "2Gi"
      cpu: "1.0"

  infrastructure:  # PostgreSQL, Redis
    limits:
      memory: "2Gi"
      cpu: "1.0"
    reservations:
      memory: "1Gi"
      cpu: "0.5"
```

**Action Items:**
1. Create unified `docker-compose.yml` with all service definitions
2. Apply resource limits to prevent resource exhaustion
3. Consolidate to single `platform_network`
4. Add restart policies: `unless-stopped`
5. Configure log rotation: max-size=10m, max-file=3

**Priority:** P1 (High)

### 1.2 Volume Management [Source: AUD-019]

**Current State:**
- PostgreSQL volume: ✅ Persistent
- Redis volume: ✅ Persistent
- Application layers: Stateless (no volumes)

**Requirements:**
- Maintain current volume strategy (infrastructure only)
- Add backup volumes for:
  - PostgreSQL dumps: `/backups/postgres`
  - Redis RDB snapshots: `/backups/redis`
  - Application logs: `/var/log/platform`

**Priority:** P2 (Medium)

### 1.3 LLM Infrastructure [Source: AUD-020]

**Current State:**
- Ollama version: 0.14.2
- Models loaded: 0 (none available)
- GPU: Not detected (CPU-only mode)
- PM2 restarts: 266+ in 7 hours (CRITICAL)

**Requirements:**

```yaml
ollama:
  deployment: "docker"  # NOT PM2
  models_required:
    - name: "llama2:7b"
      size: "3.8GB"
      use_case: "General chat, L10 interface"
    - name: "mistral:7b"
      size: "4.1GB"
      use_case: "Code generation, L03 tools"
    - name: "codellama:7b"
      size: "3.8GB"
      use_case: "L02 runtime, L03 execution"

  resource_requirements:
    cpu_only:
      memory: "8GB"
      cpu: "4 cores"
    with_gpu:
      memory: "16GB"
      gpu: "NVIDIA with 8GB+ VRAM"

  healthcheck:
    endpoint: "/api/tags"
    interval: "30s"
    timeout: "10s"
    retries: 3
```

**Action Items:**
1. Stop PM2-managed Ollama immediately
2. Deploy Ollama via Docker with proper resource limits
3. Pull required models during deployment
4. Add model download script to initialization
5. Document GPU requirements for production

**Priority:** P0 (Critical) - Ollama instability blocking LLM features

### 1.4 Database Configuration [Source: AUD-021, AUD-004]

**Current State:**
- PostgreSQL: pgvector/pgvector:pg16 (healthy)
- Connection test: Failed (client tools not on audit host)
- Database size: Unknown
- Extensions: pgvector enabled

**Requirements:**

```sql
-- Required Extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy search

-- Connection Pool Settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '1536MB';
ALTER SYSTEM SET work_mem = '16MB';

-- Replication (for production)
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
```

**Action Items:**
1. Document all required PostgreSQL extensions
2. Configure connection pooling (pgBouncer recommended)
3. Set up automated backups (pg_dump daily)
4. Implement replication for production
5. Add schema migration tool (Alembic/Flyway)

**Priority:** P2 (Medium) - Database stable but needs hardening

### 1.5 Redis Configuration [Source: AUD-015, AUD-024]

**Current State:**
- Redis: 7-alpine (healthy)
- PONG response: ✅ Working
- Persistence: Configured (RDB snapshots)
- Memory usage: Unknown

**Requirements:**

```redis
# Required Redis Configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1        # Save after 900s if 1 key changed
save 300 10       # Save after 300s if 10 keys changed
save 60 10000     # Save after 60s if 10000 keys changed
appendonly yes    # Enable AOF for better durability
appendfsync everysec
```

**Priority:** P3 (Low) - Redis working well

---

## 2. Security Requirements

### 2.1 Authentication & Authorization [Source: AUD-002, AUD-014]

**Current State:**
- L01 Data Layer: API key required (401 on health endpoint)
- Other layers: No authentication detected
- JWT patterns: Found in codebase
- Session management: Present but not validated

**Requirements:**

```yaml
authentication:
  strategy: "JWT with API keys"

  jwt:
    algorithm: "RS256"  # Use asymmetric signing
    expiry: "1h"
    refresh_expiry: "7d"
    issuer: "story-portal-platform"

  api_keys:
    format: "sp_live_[32_random_chars]"
    scopes:
      - read:services
      - write:services
      - admin:platform

  health_endpoints:
    authentication: false  # MUST BE UNAUTHENTICATED
    paths:
      - "/health"
      - "/health/live"
      - "/health/ready"

  rate_limiting:
    authenticated: "1000/hour"
    unauthenticated: "100/hour"
    health_checks: "unlimited"
```

**Action Items:**
1. Remove authentication from all `/health*` endpoints
2. Implement JWT-based auth for all API endpoints
3. Add API key management interface
4. Configure rate limiting at L09 API Gateway
5. Add RBAC for admin operations

**Priority:** P1 (High) - Critical for production

### 2.2 Network Security [Source: AUD-023]

**Current State:**
- TLS certificates: Not found
- HTTPS: Not configured (all HTTP)
- Port exposure: All ports publicly accessible
- Network segmentation: Partial (dedicated network exists)

**Requirements:**

```yaml
network_security:
  public_exposure:
    - port: 3000
      service: "Platform UI"
      tls: true
      certificate: "Let's Encrypt"
    - port: 8009
      service: "API Gateway"
      tls: true
      certificate: "Let's Encrypt"

  internal_only:
    - ports: [8001-8008, 8010-8012]
      services: "All backend layers"
      access: "via API Gateway only"
    - port: 5432
      service: "PostgreSQL"
      access: "backend layers only"
    - port: 6379
      service: "Redis"
      access: "backend layers only"

  network_policies:
    - name: "frontend-to-gateway"
      from: "platform-ui"
      to: "l09-api-gateway"
      ports: [8009]
    - name: "gateway-to-services"
      from: "l09-api-gateway"
      to: "l01-l12"
      ports: [8001-8012]
    - name: "services-to-db"
      from: "l01-l12"
      to: ["postgres", "redis"]
      ports: [5432, 6379]
```

**Action Items:**
1. Generate TLS certificates for platform-ui and l09-api-gateway
2. Configure nginx with HTTPS termination
3. Close direct access to ports 8001-8008, 8010-8012 from public
4. Implement network policies (firewall rules or Kubernetes NetworkPolicy)
5. Add certificate renewal automation

**Priority:** P1 (High) - Required for production

### 2.3 Input Validation [Source: AUD-002]

**Current State:**
- Pydantic usage: Detected (good)
- Validation patterns: Found in code
- SQL injection risk: Raw SQL patterns detected

**Requirements:**
- All API inputs must use Pydantic models
- No raw SQL queries (use ORM or parameterized queries)
- Sanitize all user-generated content
- Validate file uploads (type, size, content)
- Implement request body size limits (10MB max)

**Priority:** P2 (Medium)

---

## 3. Data Layer Requirements

### 3.1 Database Schema [Source: AUD-004]

**Current State:**
- Tables: Unable to audit (psql not available)
- Indexes: Unknown
- Foreign keys: Unknown
- Schema files: Found in codebase

**Requirements:**

```python
# Required Tables (minimum viable schema)
tables_required = [
    "agents",           # Agent registry
    "services",         # Service registry (for L12)
    "workflows",        # Workflow definitions
    "goals",            # User goals
    "sessions",         # User sessions
    "events",           # Event sourcing
    "tool_executions",  # Tool execution logs
    "llm_requests",     # LLM request/response logs
    "api_keys",         # API key management
    "users"             # User accounts
]

# Required Indexes
indexes_required = {
    "agents": ["created_at", "status", "layer"],
    "services": ["name", "layer"],
    "events": ["aggregate_id", "timestamp"],
    "sessions": ["user_id", "created_at"],
    "api_keys": ["key_hash", "user_id"]
}
```

**Action Items:**
1. Document complete schema in migration files
2. Add indexes for frequently queried fields
3. Implement foreign key constraints
4. Add created_at/updated_at to all tables
5. Create schema validation tests

**Priority:** P2 (Medium)

### 3.2 Event Sourcing [Source: AUD-017]

**Current State:**
- Event store patterns: Detected in code
- CQRS patterns: Found
- Event table: Not confirmed

**Requirements:**

```python
# Event Sourcing Schema
class Event:
    id: UUID
    aggregate_id: UUID
    aggregate_type: str  # "Agent", "Workflow", "Goal"
    event_type: str
    payload: JSONB
    metadata: JSONB
    timestamp: datetime
    sequence_number: int

# Event Types Required
event_types = [
    "AgentCreated",
    "AgentUpdated",
    "ServiceRegistered",
    "ServiceInvoked",
    "WorkflowStarted",
    "WorkflowCompleted",
    "GoalCreated",
    "GoalAchieved",
    "ToolExecuted"
]
```

**Priority:** P3 (Low) - Advanced feature

### 3.3 Redis Patterns [Source: AUD-015]

**Current State:**
- Key patterns: Unknown (no keys found or empty)
- Pub/sub channels: None detected
- Memory usage: Unknown

**Requirements:**

```python
# Redis Key Patterns
key_patterns = {
    "session": "session:{session_id}",
    "user_cache": "user:{user_id}",
    "service_cache": "service:{service_name}",
    "rate_limit": "ratelimit:{ip}:{endpoint}",
    "lock": "lock:{resource_name}",
    "queue": "queue:{queue_name}"
}

# Pub/Sub Channels
pubsub_channels = [
    "events:agent",
    "events:service",
    "events:workflow",
    "notifications:user",
    "system:health"
]

# TTL Policies
ttl_policies = {
    "session": 3600,        # 1 hour
    "user_cache": 300,      # 5 minutes
    "service_cache": 60,    # 1 minute
    "rate_limit": 3600      # 1 hour
}
```

**Priority:** P2 (Medium)

---

## 4. API & Integration Requirements

### 4.1 Service Discovery & Health [Source: AUD-010, AUD-016]

**Current State:**
- Health endpoint coverage: 2/12 (17%)
- L09 API Gateway: HTTP 500 (FAILED)
- L12 Service Hub: Reports 44 services, returns 0
- Standard health path: Inconsistent

**Requirements:**

```yaml
health_endpoints:
  standard_paths:
    liveness: "/health/live"
    readiness: "/health/ready"
    startup: "/health/startup"

  response_format:
    success:
      status: "healthy"
      version: "1.0.0"
      uptime_seconds: 12345
      dependencies:
        - name: "postgres"
          status: "healthy"
        - name: "redis"
          status: "healthy"

    failure:
      status: "unhealthy"
      version: "1.0.0"
      errors:
        - "Database connection failed"
        - "Redis timeout"

  requirements:
    - Unauthenticated (no API key required)
    - Response time <100ms
    - Return 200 for healthy, 503 for unhealthy
    - Include dependency checks in readiness probe
```

**ALL 12 LAYERS MUST IMPLEMENT:**
1. `/health/live` - Is the service running?
2. `/health/ready` - Is the service ready to accept traffic?
3. `/health/startup` - Has the service completed initialization?

**Action Items:**
1. Create shared health check library
2. Implement health endpoints on all 12 layers
3. Fix L09 API Gateway critical failure
4. Fix L12 Service Hub discovery API
5. Add health endpoint tests to CI/CD

**Priority:** P0 (Critical) for L09, P1 (High) for others

### 4.2 L09 API Gateway Specification [Source: AUD-025]

**Current State:**
- Status: HTTP 500 Internal Server Error (CRITICAL)
- Health: Container healthy, service failing
- CORS: Unable to test (service down)
- Rate limiting: Unable to test

**Requirements:**

```yaml
l09_api_gateway:
  routes:
    # Backend service proxying
    - path: "/api/l01/*"
      target: "http://l01-data-layer:8001"
      strip_prefix: "/api/l01"

    - path: "/api/l02/*"
      target: "http://l02-runtime:8002"
      strip_prefix: "/api/l02"

    # ... (L03-L12)

    - path: "/api/services/*"
      target: "http://l12-service-hub:8012"
      strip_prefix: "/api"

  cors:
    allowed_origins:
      - "http://localhost:3000"
      - "https://platform.example.com"
    allowed_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allowed_headers: ["Content-Type", "Authorization", "X-API-Key"]
    expose_headers: ["X-Request-ID", "X-Rate-Limit-Remaining"]
    max_age: 3600

  rate_limiting:
    default: "100/minute"
    authenticated: "1000/minute"
    admin: "unlimited"
    per_endpoint:
      "/api/llm/generate": "10/minute"
      "/api/search": "50/minute"

  middleware:
    - request_id_injection
    - logging
    - authentication
    - authorization
    - rate_limiting
    - cors
    - error_handling
    - metrics_collection

  monitoring:
    metrics:
      - request_count
      - request_duration
      - error_rate
      - backend_availability
    alerts:
      - error_rate > 5%
      - p99_latency > 1000ms
      - backend_down
```

**Action Items (URGENT):**
1. Investigate L09 logs: `docker logs l09-api-gateway --tail 500`
2. Check backend connectivity from within container
3. Verify route configuration
4. Test without middleware to isolate issue
5. Restart container if necessary
6. Add comprehensive logging
7. Implement health checks for all backends

**Priority:** P0 (Critical) - BLOCKING ENTIRE PLATFORM

### 4.3 L12 Service Hub Specification [Source: AUD-026]

**Current State:**
- Health: Reports 44 services loaded
- Discovery API: Returns 0 services (FAILED)
- All `/api/v1/*` endpoints: 404
- Source code: Not found in expected location

**Requirements:**

```yaml
l12_service_hub:
  service_registry:
    discovery:
      endpoint: "/api/v1/services"
      response:
        total: 44
        services:
          - name: "AgentRegistry"
            layer: "L01"
            description: "Manage agent lifecycle"
            methods: ["create", "update", "list", "delete"]
            health: "healthy"

    search:
      endpoint: "/api/v1/services/search"
      parameters:
        - name: "q"
          required: true
          description: "Fuzzy search query"
      algorithm: "Levenshtein distance"
      max_results: 20

    invocation:
      endpoint: "/api/v1/services/invoke"
      method: "POST"
      body:
        service_name: "AgentRegistry"
        method: "list_agents"
        params: {}
      timeout: "30s"

  workflows:
    endpoint: "/api/v1/workflows"
    operations: ["list", "create", "execute", "status"]

  sessions:
    endpoint: "/api/v1/sessions"
    operations: ["create", "get", "update", "delete"]
    ttl: "1h"
```

**Action Items (URGENT):**
1. Verify API router is mounted in FastAPI app
2. Check source code location in container
3. Test service registration on startup
4. Add debug logging to registration process
5. Verify database connectivity for service metadata
6. Fix route definitions
7. Test all 9 endpoints

**Priority:** P0 (Critical) - Core V2 feature non-functional

### 4.4 FastAPI Standards [Source: AUD-016]

**Current State:**
- Route definitions: Found (@app, @router decorators)
- GET routes: Detected in code
- POST routes: Detected in code
- Health endpoints: Inconsistent paths

**Requirements:**

```python
# Standard FastAPI Application Structure
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Layer XX Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Health Check (REQUIRED)
@app.get("/health/live")
async def liveness():
    return {"status": "healthy"}

@app.get("/health/ready")
async def readiness():
    # Check dependencies
    db_healthy = await check_database()
    cache_healthy = await check_redis()

    if not (db_healthy and cache_healthy):
        raise HTTPException(status_code=503, detail="Not ready")

    return {"status": "ready", "dependencies": {
        "database": "healthy",
        "cache": "healthy"
    }}

# API Endpoints (use router)
from .routers import agents, services, workflows

app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(services.router, prefix="/api/v1/services", tags=["services"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])

# Error Handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )
```

**Priority:** P1 (High)

---

## 5. Quality & Testing Requirements

### 5.1 Test Coverage [Source: AUD-003]

**Current State:**
- Test files: Found in codebase
- Test functions: Count detected
- pytest config: Not found or incomplete
- Coverage: Unknown

**Requirements:**

```yaml
testing:
  minimum_coverage: 80%

  test_types:
    unit:
      framework: "pytest"
      coverage_target: 90%
      location: "tests/unit/"

    integration:
      framework: "pytest"
      coverage_target: 70%
      location: "tests/integration/"
      requires: ["docker", "postgres", "redis"]

    e2e:
      framework: "playwright"
      coverage_target: 50%
      location: "tests/e2e/"
      requires: ["full platform deployment"]

    performance:
      framework: "locust"
      location: "tests/performance/"
      requirements:
        - "50 concurrent users"
        - "p95 latency <500ms"
        - "error rate <1%"

  ci_requirements:
    - All unit tests must pass
    - Integration tests must pass
    - Coverage must not decrease
    - No critical security vulnerabilities
```

**Action Items:**
1. Create pytest.ini with coverage config
2. Implement unit tests for all services (80%+ coverage)
3. Create integration test suite
4. Add tests to CI/CD pipeline
5. Generate coverage reports

**Priority:** P2 (Medium)

### 5.2 Code Quality [Source: AUD-007]

**Current State:**
- Type hints: Partial coverage detected
- Docstrings: Some coverage
- TODO/FIXME: 30+ found
- Large files: Several >500 lines

**Requirements:**

```yaml
code_quality:
  linting:
    tools:
      - ruff        # Fast Python linter
      - mypy        # Type checking
      - black       # Code formatting

    rules:
      max_line_length: 100
      max_function_lines: 50
      max_file_lines: 500
      max_complexity: 10

  type_coverage:
    target: 100%
    strict: true
    ignore_missing_imports: false

  documentation:
    docstring_coverage: 100%
    format: "Google"  # or "NumPy", "Sphinx"
```

**Action Items:**
1. Add ruff, mypy, black to pre-commit hooks
2. Add type hints to all functions
3. Add docstrings to all public functions/classes
4. Refactor files >500 lines
5. Address all TODO/FIXME comments

**Priority:** P3 (Low)

### 5.3 Performance [Source: AUD-006]

**Current State:**
- Async patterns: Detected in code
- Connection pooling: Found
- Caching: Some patterns detected
- N+1 queries: Potential risks found

**Requirements:**

```yaml
performance:
  latency_targets:
    p50: <100ms
    p95: <500ms
    p99: <1000ms

  throughput_targets:
    api_gateway: "1000 req/s"
    database_queries: "5000 req/s"
    llm_requests: "10 req/s"  # GPU dependent

  optimization_patterns:
    - Use async/await everywhere
    - Implement connection pooling (DB, Redis, HTTP)
    - Add caching layers (Redis, in-memory)
    - Prevent N+1 queries (use eager loading)
    - Implement request coalescing for LLM calls
    - Add CDN for static assets
```

**Priority:** P3 (Low) - After fixing critical issues

---

## 6. UX & DevEx Requirements

### 6.1 Platform Control Center UI [Source: AUD-027, AUD-029]

**Current State:**
- HTTP status: 200 OK (UI serving properly)
- Response time: 11.8ms (excellent)
- All routes: Working (/, /dashboard, /agents, /services, /workflows, /goals, /monitoring)
- Container status: Unhealthy (health check misconfigured)
- Backend integration: Blocked by L09 failure

**Requirements:**

```yaml
platform_ui:
  framework: "React + TypeScript"
  build_tool: "Vite"

  pages_required:
    - path: "/"
      component: "Dashboard"
      features: ["system health", "recent activity"]

    - path: "/agents"
      component: "AgentManager"
      features: ["list", "create", "update", "delete", "logs"]

    - path: "/services"
      component: "ServiceBrowser"
      features: ["search", "invoke", "documentation"]

    - path: "/workflows"
      component: "WorkflowDesigner"
      features: ["create", "execute", "monitor", "history"]

    - path: "/goals"
      component: "GoalTracker"
      features: ["set goals", "track progress", "analytics"]

    - path: "/monitoring"
      component: "MonitoringDashboard"
      features: ["metrics", "logs", "traces", "alerts"]

  api_integration:
    base_url: "/api"  # Proxied through nginx to L09
    endpoints:
      agents: "/api/l01/agents"
      services: "/api/services"  # L12
      workflows: "/api/workflows"
      health: "/api/health"

  real_time:
    protocol: "WebSocket"
    url: "ws://localhost:8009/ws"
    features:
      - "Live service status updates"
      - "Real-time log streaming"
      - "Workflow execution progress"
      - "System alerts"

  performance:
    initial_load: <2s
    bundle_size: <500KB (gzipped)
    lighthouse_score: >90
```

**Action Items:**
1. Fix health check configuration in platform-ui container
2. Verify WebSocket proxy through nginx
3. Add error handling for L09 failures
4. Implement loading states for all API calls
5. Add offline mode/retry logic
6. Document API client configuration

**Priority:** P1 (High) - UI working but blocked by backend

### 6.2 nginx Configuration [Source: AUD-028]

**Current State:**
- nginx version: 1.29.4
- Configuration test: Passed
- API Gateway proxy: Unable to test (L09 down)
- Service Hub proxy: Unable to test
- WebSocket support: Not confirmed
- Security headers: Not confirmed

**Requirements:**

```nginx
# /etc/nginx/conf.d/default.conf

upstream api_gateway {
    server l09-api-gateway:8009;
    keepalive 32;
}

upstream service_hub {
    server l12-service-hub:8012;
    keepalive 32;
}

server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Frontend static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }

    # API Gateway proxy
    location /api/ {
        proxy_pass http://api_gateway/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://api_gateway/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Service Hub direct access
    location /services/ {
        proxy_pass http://service_hub/api/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Health check endpoint
    location /health {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "healthy\n";
    }
}
```

**Action Items:**
1. Add security headers
2. Enable gzip compression
3. Configure WebSocket proxying
4. Add connection pooling (keepalive)
5. Implement request buffering limits
6. Add custom error pages

**Priority:** P1 (High)

### 6.3 Documentation [Source: AUD-030]

**Current State:**
- USER_GUIDE.md: Found, links present
- API_REFERENCE.md: Found, endpoints documented
- DEPLOYMENT_COMPLETE.md: Found, layer references present
- Link validation: Some endpoints tested
- README files: Multiple found

**Requirements:**

```yaml
documentation:
  required_docs:
    - name: "README.md"
      location: "/"
      content: ["Quick start", "Architecture overview", "Links to docs"]

    - name: "ARCHITECTURE.md"
      location: "/docs/"
      content: ["Layer descriptions", "Data flow", "Dependencies"]

    - name: "API_REFERENCE.md"
      location: "/docs/"
      content: ["All endpoints", "Request/response schemas", "Examples"]

    - name: "DEPLOYMENT.md"
      location: "/docs/"
      content: ["Prerequisites", "Installation", "Configuration", "Troubleshooting"]

    - name: "DEVELOPMENT.md"
      location: "/docs/"
      content: ["Setup", "Testing", "Contributing", "Code standards"]

    - name: "OPERATIONS.md"
      location: "/docs/"
      content: ["Monitoring", "Backup/restore", "Disaster recovery", "Scaling"]

  auto_generation:
    - OpenAPI specs from FastAPI (all layers)
    - Database schema from migrations
    - Architecture diagrams from code

  maintenance:
    - Validate all links monthly
    - Update version numbers on release
    - Test all commands in docs
```

**Action Items:**
1. Validate and fix all broken links
2. Update docs to reflect V2 reality
3. Add troubleshooting section (based on this audit)
4. Generate OpenAPI specs for all layers
5. Create architecture diagrams
6. Add runbooks for common operations

**Priority:** P2 (Medium)

---

## 7. Service Discovery Findings [Source: AUD-010, AUD-011, AUD-012, AUD-013]

### 7.1 Service Health Matrix

| Service | Container | HTTP Test | Functional | Priority |
|---------|-----------|-----------|------------|----------|
| L01 Data Layer | ✅ Healthy | ⚠️ 401 Auth | Unknown | P1 |
| L02 Runtime | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L03 Tool Exec | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L04 Model Gateway | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L05 Planning | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L06 Evaluation | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L07 Learning | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L09 API Gateway | ✅ Healthy | 🔥 500 | Failed | P0 |
| L10 Human Interface | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L11 Integration | ✅ Healthy | ❌ 404 | Unknown | P1 |
| L12 Service Hub | ✅ Healthy | ⚠️ Partial | Failed | P0 |

### 7.2 CLI Tooling [Source: AUD-011]

**Requirements:**
```bash
# Each layer should support:
python -m L01_data_layer --help
python -m L01_data_layer health    # Check health
python -m L01_data_layer version   # Show version
python -m L01_data_layer config    # Show configuration
python -m L01_data_layer migrate   # Run migrations (if applicable)

# Example layer CLI structure
commands:
  - health: "Check service health and dependencies"
  - version: "Display service version and build info"
  - config: "Display current configuration (sanitized)"
  - test: "Run service self-tests"
  - migrate: "Run database migrations (data layers only)"
  - seed: "Seed test data (development only)"
```

**Priority:** P3 (Low) - Nice to have

### 7.3 MCP Services [Source: AUD-012]

**Current State:**
- mcp-document-consolidator: ✅ Stable (0 restarts)
- mcp-context-orchestrator: ✅ Stable (0 restarts)
- ollama: ⚠️ Unstable (266+ restarts)

**Requirements:**
- Move Ollama out of PM2 (use Docker)
- Keep other MCP services in PM2 if stable
- Add health checks to PM2 processes
- Configure max_restarts limit (e.g., 10)

**Priority:** P0 (Critical) for Ollama

### 7.4 Configuration Management [Source: AUD-013]

**Current State:**
- .env files: Found
- Config YAML/JSON: Found
- Sensitive patterns: Detected

**Requirements:**

```yaml
configuration:
  hierarchy:
    1. Environment variables (highest priority)
    2. .env files (per-environment)
    3. config.yaml (defaults)
    4. Hardcoded defaults (lowest priority)

  environments:
    - development: ".env.dev"
    - staging: ".env.staging"
    - production: ".env.prod"

  secrets_management:
    tool: "Docker Secrets" # or HashiCorp Vault
    never_commit:
      - ".env.prod"
      - ".env.staging"
      - "*.key"
      - "*.pem"

  required_vars:
    - DATABASE_URL
    - REDIS_URL
    - OLLAMA_URL
    - JWT_SECRET_KEY
    - API_KEY_SALT
```

**Priority:** P2 (Medium)

---

## 8. V2 Platform Components (NEW) [Source: AUD-025, AUD-026, AUD-027, AUD-028, AUD-029]

### 8.1 New Components Summary

| Component | Version | Status | Functionality | Priority |
|-----------|---------|--------|---------------|----------|
| L09 API Gateway | 1.0.0 | 🔥 Failed | 0% | P0 |
| L12 Service Hub | 1.0.0 | ⚠️ Partial | 10% | P0 |
| Platform UI | 1.0.0 | ⚠️ Unhealthy | 80% | P1 |
| nginx Proxy | 1.29.4 | ✅ Working | 90% | P2 |

### 8.2 Integration Status

```yaml
integration_matrix:
  ui_to_gateway:
    status: "blocked"
    reason: "L09 returning 500"
    workaround: "none"

  gateway_to_services:
    status: "unknown"
    reason: "L09 not operational"
    workaround: "direct service access for testing"

  ui_to_service_hub:
    status: "blocked"
    reason: "L12 APIs returning 404"
    workaround: "none"

  nginx_proxying:
    status: "untested"
    reason: "backend services not responding"
    workaround: "test after fixing L09"
```

---

## 9. External Dependencies [Source: AUD-031]

**Current State:**
- Python dependencies: Unable to find requirements.txt
- External APIs: Some references found
- CI/CD: No GitHub Actions found
- Lock files: Not found

**Requirements:**

```txt
# requirements.txt (example minimum)
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
redis==5.0.1
httpx==0.25.1
pyjwt==2.8.0
python-multipart==0.0.6
prometheus-client==0.19.0
structlog==23.2.0
```

**Action Items:**
1. Create requirements.txt for each layer
2. Add requirements-dev.txt for development dependencies
3. Create requirements-test.txt for testing dependencies
4. Use pip-tools to generate locked requirements
5. Document all external APIs and their rate limits

**Priority:** P2 (Medium)

---

## 10. Priority Matrix

| Priority | Category | Finding | Impact | Effort | Risk |
|----------|----------|---------|--------|--------|------|
| **P0** | API | L09 Gateway Failure | Blocking | 4h | High |
| **P0** | API | L12 Service Hub APIs | Blocking | 8h | High |
| **P0** | LLM | Ollama PM2 Instability | High | 2h | Medium |
| **P1** | Container | No Resource Limits | High | 4h | High |
| **P1** | Monitoring | Missing Health Endpoints | Medium | 16h | Medium |
| **P1** | UI | platform-ui Health Check | Medium | 1h | Low |
| **P1** | Security | Auth on Health Endpoints | Medium | 2h | Low |
| **P1** | Network | No TLS/HTTPS | High | 8h | High |
| **P2** | Config | Missing docker-compose.yml | Medium | 4h | Medium |
| **P2** | Database | Connection Pooling | Medium | 4h | Low |
| **P2** | Docs | Outdated Documentation | Low | 8h | Low |
| **P2** | Testing | No Test Suite | Medium | 40h | Medium |
| **P3** | Code | Quality Issues | Low | 16h | Low |
| **P3** | Performance | Optimization | Low | 24h | Low |

---

## 11. Implementation Roadmap

### Phase 1: Emergency Fixes (Week 1 - Days 1-2)
**Goal:** Restore basic platform functionality
**Duration:** 2 days
**Team Size:** 2-3 engineers

**Day 1 Morning:**
- [ ] Fix L09 API Gateway (4h)
  - Investigate logs
  - Identify root cause
  - Apply fix
  - Test all endpoints

**Day 1 Afternoon:**
- [ ] Stabilize Ollama (2h)
  - Stop PM2 process
  - Verify Docker container
  - Pull required models
  - Test LLM functionality

**Day 2 Morning:**
- [ ] Fix L12 Service Hub (4h)
  - Mount API routes properly
  - Fix service registration
  - Test all 9 endpoints
  - Verify 44 services discoverable

**Day 2 Afternoon:**
- [ ] Validation & Testing (4h)
  - Test UI → Gateway → Services flow
  - Verify all critical paths
  - Document fixes
  - Update team

### Phase 2: Critical Infrastructure (Week 1 - Days 3-5)
**Goal:** Prevent resource exhaustion and enable monitoring
**Duration:** 3 days

- [ ] Add container resource limits (4h)
- [ ] Implement health endpoints on all layers (16h)
- [ ] Fix platform-ui health check (1h)
- [ ] Remove auth from health endpoints (2h)
- [ ] Create basic monitoring dashboard (8h)

### Phase 3: Production Readiness (Week 2-3)
**Goal:** Make platform production-ready
**Duration:** 2 weeks

- [ ] Implement TLS/HTTPS (8h)
- [ ] Configure network policies (4h)
- [ ] Add API authentication/authorization (16h)
- [ ] Implement rate limiting (4h)
- [ ] Create docker-compose.yml (4h)
- [ ] Set up automated backups (8h)
- [ ] Write operations runbook (8h)
- [ ] Create integration test suite (24h)

### Phase 4: Quality & Optimization (Week 4-6)
**Goal:** Improve quality and performance
**Duration:** 3 weeks

- [ ] Add unit tests (80%+ coverage) (40h)
- [ ] Implement code quality checks (16h)
- [ ] Performance optimization (24h)
- [ ] Update all documentation (16h)
- [ ] Add CI/CD pipeline (16h)
- [ ] Conduct security audit (16h)
- [ ] Load testing (16h)

---

## 12. Success Metrics

### Immediate Success (Week 1)
- [ ] L09 API Gateway: 0 errors, HTTP 200 on all endpoints
- [ ] L12 Service Hub: 44/44 services discoverable
- [ ] Ollama: 0 restarts in 24 hours
- [ ] Health endpoints: 12/12 layers responding
- [ ] Platform UI: Healthy status, all features working

### Production Readiness (Month 1)
- [ ] All containers with resource limits
- [ ] TLS enabled on public endpoints
- [ ] Authentication working on all APIs
- [ ] Automated backups running daily
- [ ] Monitoring dashboard operational
- [ ] Integration tests passing (>90%)
- [ ] Documentation updated and validated

### Quality Targets (Month 2)
- [ ] Test coverage: >80%
- [ ] Code quality score: >85/100
- [ ] API availability: >99.9%
- [ ] P95 latency: <500ms
- [ ] Error rate: <1%
- [ ] Security vulnerabilities: 0 critical, 0 high

---

## 13. Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| L09/L12 fixes fail | Medium | High | Allocate backup engineers, prepare rollback plan |
| Resource limits cause OOM | Low | High | Test limits in staging, monitor closely, have quick rollback |
| Data loss during changes | Low | Critical | Backup all data before changes, test restore procedures |
| Breaking changes to API | Medium | High | Maintain backwards compatibility, version APIs |
| Performance degradation | Low | Medium | Load test before production, gradual rollout |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Extended downtime | Low | High | Implement in staging first, have rollback plan ready |
| Team bandwidth | High | Medium | Prioritize ruthlessly, defer P3 items |
| Knowledge gaps | Medium | Medium | Pair programming, documentation, knowledge sharing |
| Scope creep | Medium | Medium | Strict adherence to roadmap, defer new features |

---

## Conclusion

This specification document provides comprehensive technical requirements derived from the V2 platform audit. The platform is currently **not production-ready** due to critical failures in L09 API Gateway and L12 Service Hub.

**Immediate focus must be:**
1. Restoring L09 API Gateway functionality
2. Fixing L12 Service Hub service discovery
3. Stabilizing Ollama LLM service

With focused effort over 1-2 weeks, the platform can achieve operational status and meet basic production readiness criteria.

---

**Document Version:** 1.0
**Last Updated:** January 17, 2026
**Next Review:** January 24, 2026 (post-fixes)
**Owner:** Platform Team
**Approvers:** Technical Lead, Product Manager, DevOps Lead

---

*This document synthesizes findings from 31 audit agents and provides actionable technical requirements for V2.1 planning.*
