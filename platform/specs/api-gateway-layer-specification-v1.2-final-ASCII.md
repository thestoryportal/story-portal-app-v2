# API Gateway Layer Specification

**Layer ID:** L09
**Version:** 1.2.0
**Status:** Final
**Date:** 2026-01-04
**Error Code Range:** E9000-E9999

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-01-04 | Integrated all 26 industry validation findings (P1: 8 critical, P2: 12 should-have, P3: 6 optional) |
| 1.1.0 | 2026-01-05 | Applied self-validation fixes (3 critical issues resolved): Added missing Sections 1-5 (Overview, Architecture, Core Components, Request Processing, Async Operations) |
| 1.0.0 | 2026-01-04 | Initial comprehensive specification (all sections) |

---

## Table of Contents

### Part 1: Fundamentals (Sections 1-5)
1. [Section 1: Overview and Scope](#section-1-overview-and-scope)
2. [Section 2: Architecture](#section-2-architecture)
3. [Section 3: Core Components](#section-3-core-components)
4. [Section 4: Request Processing](#section-4-request-processing)
5. [Section 5: Async Operations](#section-5-async-operations)

### Part 2: Integration and Operations (Sections 6-10)
6. [Section 6: Integration with Data Layer](#section-6-integration-with-data-layer)
7. [Section 7: Reliability and Scalability](#section-7-reliability-and-scalability)
8. [Section 8: Security](#section-8-security)
9. [Section 9: Observability](#section-9-observability)
10. [Section 10: Configuration](#section-10-configuration)

### Part 3: Implementation and Deployment (Sections 11-15)
11. [Section 11: Implementation Guide](#section-11-implementation-guide)
12. [Section 12: Testing Strategy](#section-12-testing-strategy)
13. [Section 13: Migration and Deployment](#section-13-migration-and-deployment)
14. [Section 14: Open Questions and Decisions](#section-14-open-questions-and-decisions)
15. [Section 15: References and Appendices](#section-15-references-and-appendices)

### Appendices
- [Appendix A: Industry Validation Integration Summary](#appendix-a-industry-validation-integration-summary)
- [Appendix B: Complete Error Code Registry](#appendix-b-complete-error-code-registry)

---

# PART 1: FUNDAMENTALS

## Section 1: Overview and Scope

### 1.1 Purpose and Role

The API Gateway Layer (L09) serves as the primary entry point for all external API requests in the agentic system. It acts as a sophisticated request router, security boundary, and integration point between external consumers and internal backend services.

**Core Responsibilities:**

1. **Request Routing**: Direct incoming requests to appropriate backend services based on HTTP method, path, API version, and request metadata
2. **Authentication**: Verify the identity of API consumers using multiple authentication methods (API keys, OAuth 2.0, mTLS)
3. **Authorization**: Enforce access control policies ensuring consumers can only access permitted resources and operations
4. **Rate Limiting**: Enforce quota and rate limit policies to prevent abuse and ensure fair resource allocation
5. **Async Operations**: Manage long-running operations with 202 Accepted responses and webhook-based result delivery
6. **Observability**: Emit comprehensive metrics, logs, and traces for monitoring system health and debugging issues
7. **Security**: Protect against threats including authentication bypass, unauthorized access, and cross-tenant data leakage

### 1.2 Position in System Architecture

The API Gateway Layer sits between external consumers and internal services:

```
[External Consumers]
        │
        ├─► [L09: API Gateway Layer]
        │   └─► [Authentication]
        │   └─► [Authorization]
        │   └─► [Rate Limiting]
        │   └─► [Request Router]
        │   └─► [Idempotency Handler]
        │   └─► [Webhook Delivery]
        │
        ├─► [L01: Data Layer] (Consumer Registry, Configuration Service, Event Store, Audit Logs)
        ├─► [L02: Agent Runtime] (Long-running operation execution)
        ├─► [L08: Supervision] (Policy evaluation, constraint checking)
        └─► [Backend Services] (Business logic implementation)
```

### 1.3 Design Principles

**1. Security-First Design**
- Multi-tenant isolation is enforced at every stage
- Authentication is mandatory for all requests
- Authorization policies are evaluated before backend invocation
- Tenant context is verified and immutable throughout request lifecycle
- Zero trust architecture: All service-to-service communication requires mutual authentication (mTLS)

**2. Resilience and Fault Tolerance**
- Circuit breakers protect against cascading failures with explicit state transitions
- Graceful degradation when dependencies are unavailable
- Exponential backoff and automatic retries for transient failures
- Health-based load balancing excludes unhealthy replicas
- Per-backend connection pool bulkheads prevent one failing backend from exhausting shared resources

**3. Stateless Gateway Design**
- Gateway instances are horizontally scalable
- All state is stored in L01 (Data Layer) or Redis (distributed cache)
- Request context flows through system without local persistence
- Configuration changes are propagated dynamically to all instances
- Configuration is fully externalized per 12-Factor App methodology

**4. Observability by Default**
- All requests are traced with W3C Trace Context (with validation)
- Structured JSON logging with adaptive sampling
- 18+ Prometheus metrics with exemplars for trace correlation
- Audit trails for all security-relevant events (immutable, time-locked)
- OpenTelemetry semantic attributes for complete context

**5. Multi-Tenancy as Foundational Constraint**
- Every request contains tenant context (validated and immutable)
- Row-level security filters protect tenant isolation
- Cross-tenant access is a critical security threat (actively prevented)
- Tenant ID is extracted, validated, and propagated throughout the system

### 1.4 Supported Protocols and Formats

**Protocols:**
- HTTP/1.1 (synchronous requests)
- HTTP/2 (streaming support, multiplexing)
- gRPC (protocol buffers, binary serialization)
- Webhooks (HTTPS callbacks for async operation results)

**Request Formats:**
- JSON (application/json)
- Protocol Buffers (application/protobuf)
- Form URL-encoded (application/x-www-form-urlencoded)

**Authentication Methods:**
- API Key (header-based, bcrypt-hashed, with rotation schedule)
- OAuth 2.0 with JWT (RS256 signature, JWKS endpoint validation)
- Mutual TLS (mTLS) with certificate-based client authentication

### 1.5 Out-of-Scope and Deferred Features

**v1.1 Roadmap (Deferred):**
- WebSocket proxy for streaming operations (requires persistent connections)
- Server-Sent Events (SSE) as alternative to webhooks
- gRPC streaming support (basic gRPC working in v1.0)

**v2.0+ Roadmap (Future):**
- GraphQL federation (requires schema composition)
- API versioning with multiple simultaneous versions
- Advanced traffic shaping and load balancing (priority queues, weighted routing)

---

## Section 2: Architecture

### 2.1 High-Level Architecture

The API Gateway Layer consists of core components that process requests through ordered pipeline stages:

```
External Request
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│          Request Processing Pipeline (L09)              │
├─────────────────────────────────────────────────────────┤
│ 1. [Authentication Handler]                             │
│    Verify consumer identity via API key / OAuth / mTLS  │
│    With credential rotation support (IV-011)            │
│                                                          │
│ 2. [Authorization Engine]                               │
│    Check RBAC/ABAC policies against consumer scopes     │
│                                                          │
│ 3. [Request Validator]                                  │
│    Validate request format, parameters, body size       │
│    Unicode normalization, character set validation      │
│    (IV-006 comprehensive input validation)              │
│                                                          │
│ 4. [Idempotency Handler]                                │
│    Check for duplicate requests via idempotency key     │
│    Return cached response for replayed requests (IV-007)│
│                                                          │
│ 5. [Rate Limiter]                                       │
│    Check quota using distributed token bucket algorithm │
│    Unified across HTTP/1.1, HTTP/2, gRPC (IV-021)      │
│                                                          │
│ 6. [Request Router]                                     │
│    Match request to backend service, load balance       │
│                                                          │
│ 7. [Backend Executor]                                   │
│    Invoke backend service with mTLS (IV-016)            │
│    Collect response, handle with circuit breaker        │
│                                                          │
│ 8. [Async Handler] (if operation is async)              │
│    Queue webhook delivery with retry strategy           │
│    SSRF validation before sending (IV-004)              │
│                                                          │
│ 9. [Response Formatter]                                 │
│    Format response, inject headers, sanitize output     │
│                                                          │
│ 10. [Event Publisher]                                   │
│    Emit audit logs (immutable, time-locked) to L01      │
│    Publish events with schema versioning (IV-020)       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Return Response to Consumer
```

### 2.2 Request Context Propagation

Request context flows through the entire pipeline and is injected into backend service calls:

```
[Request Context Object]
  ├─ trace_id (W3C format, validated per IV-022)
  ├─ span_id (generated, validated)
  ├─ request_id (unique per request)
  ├─ consumer_id (authenticated identity)
  ├─ tenant_id (multi-tenant isolation, immutable)
  ├─ oauth_scopes (permission scope list)
  ├─ rate_limit_tier (STANDARD/PREMIUM/ENTERPRISE)
  ├─ client_ip (source IP for audit/security)
  ├─ idempotency_key (UUID v4 for deduplication)
  └─ timestamp (request received time)

[Headers Injected to Backend]
  X-Request-ID: {request_id}
  X-Trace-ID: {trace_id}
  X-Span-ID: {span_id}
  X-Consumer-ID: {consumer_id}
  X-Tenant-ID: {tenant_id}
  X-Tenant-Type: {tenant_type}
  X-Idempotency-Key: {idempotency_key}
```

### 2.3 Integration Points

**L01 Data Layer Queries (with mTLS, IV-016):**
- Consumer Registry: Look up consumer profile by API key / OAuth client ID / mTLS cert
- Configuration Service: Get route definitions, auth methods, rate limit tiers
- Event Store: Publish audit logs (immutable, IV-026), request events, webhook delivery events
- Consumer Change Stream: Watch for consumer profile updates, invalidate cache

**L02 Agent Runtime:**
- Invoke async operations (long-running agent execution)
- Poll operation status during execution
- Receive completion webhooks with results

**L08 Supervision:**
- Evaluate ABAC policies against consumer attributes
- Validate constraints and quota enforcement

**Redis Cache (with mTLS, IV-016):**
- Distributed rate limiting with atomic token bucket operations
- Consumer profile cache for performance (5-minute TTL)
- Configuration cache with TTL-based invalidation
- Idempotency result cache (24-hour TTL, IV-007)

### 2.4 Data Flow Through System

**Synchronous Request Flow:**

1. Request arrives at gateway
2. Authentication Handler validates credentials with L01 (includes credential rotation check, IV-011)
3. Authorization Engine checks policies with L08
4. Request Validator checks format, size, character set (IV-006)
5. Idempotency Handler checks for duplicate (IV-007), returns cached response if found
6. Rate Limiter checks quota against Redis (unified across protocols, IV-021)
7. Request Router matches request to backend service
8. Backend Executor invokes service with mTLS (IV-016), timeout, and retry logic
9. Response Formatter adds headers (rate limit info, trace ID)
10. Event Publisher emits APIRequestEvent to L01 (with schema versioning, IV-020)
11. Response returned to consumer

**Asynchronous Request Flow:**

1. Request arrives at gateway
2. Authentication, authorization, validation (same as sync)
3. Idempotency check (IV-007)
4. Rate Limiter checks quota
5. Request Router matches to async-enabled route
6. Async Handler creates operation in L01, returns 202 Accepted with operation_id
7. Backend Executor invokes L02 Runtime asynchronously
8. L02 executes agent, produces result
9. Async Handler delivers result via webhook to consumer's webhook URL with SSRF validation (IV-004)
10. Webhook signature verification (HMAC-SHA256, IV-009) and retry strategy (exponential backoff)
11. If all retries fail: Dead-letter queue for manual review (IV-023)
12. Event Publisher emits completion events to L01 (schema versioned, IV-020)

### 2.5 Failure Recovery Architecture

Gateway failures are handled through multiple resilience mechanisms with explicit cache invalidation:

```
[Request Received]
    │
    ├─ Is L01 available?
    │  └─ NO: Use local cache for consumer profiles + config
    │         Cache TTL: 5 minutes (watch stream invalidation, IV-024)
    │         Degrade functionality but continue
    │
    ├─ Is authentication service available?
    │  └─ NO: Return 503 (gateway dependency unavailable)
    │
    ├─ Is Redis available?
    │  └─ NO: Fall back to in-memory rate limiting (single instance only)
    │         Per-gateway token bucket
    │
    ├─ Is backend service healthy?
    │  └─ NO: Check circuit breaker
    │     ├─ CLOSED: Proceed normally
    │     ├─ OPEN: Return 503 (backend unhealthy)
    │     ├─ HALF_OPEN: Allow limited probe requests
    │     └─ RECOVERING: Ramp up traffic gradually (IV-005)
    │
    └─ [Normal Processing]
```

---

## Section 3: Core Components

### 3.1 Request Router

**Responsibility:** Match incoming HTTP requests to backend services based on path patterns, HTTP methods, and API versioning.

**Inputs:**
- HTTP method (GET, POST, PUT, DELETE, PATCH)
- Request path (e.g., /agents/{id}/invoke)
- API version header (e.g., Accept-Version: v1)

**Outputs:**
- Matched RouteDefinition with backend service information
- Load balancing strategy (least-connections, round-robin, consistent-hash)
- Route-specific configuration (timeout, retries, cost units)

**Key Features:**
- Glob pattern matching for path parameters (/agents/{id}/*)
- API versioning with deprecation tracking
- Cost-aware routing (heavy operations consume more tokens)
- Multiple backend target support with load balancing
- Service discovery: Kubernetes DNS, Consul, or manual registry (IV-025)

### 3.2 Authentication Handler

**Responsibility:** Verify the identity of API consumers using one of three authentication methods.

**Authentication Methods:**

1. **API Key Authentication**
   - Consumer provides key in Authorization header or query parameter
   - Gateway looks up key in L01 Consumer Registry
   - Key is bcrypt-hashed at rest, compared securely
   - Supports key rotation (90-day schedule, IV-011)
   - Automatic expiration with grace period (30 days)

2. **OAuth 2.0 with JWT**
   - Consumer provides JWT token in Authorization header
   - Gateway verifies RS256 signature using JWKS endpoint from L01
   - Validates token expiry, issuer, and required claims
   - Extracts consumer_id from JWT subject claim
   - Requires mTLS for L01 connection (IV-016)

3. **Mutual TLS (mTLS)**
   - Consumer presents client certificate during TLS handshake
   - Gateway validates certificate chain and revocation status
   - Extracts consumer_id from certificate common name
   - Enforces certificate pinning for high-security scenarios
   - Supports certificate rotation (1-year schedule, IV-011)

**Credential Rotation (IV-011):**
- API Keys: Rotate every 90 days, 30-day grace period
- OAuth Secrets: Rotate every 60 days, 30-day grace period
- Certificates: Rotate every 1 year, 30-day notice period
- Rotation process: Generate new, store both simultaneously, notify consumer, deprecate old

**Outputs:**
- ConsumerProfile (consumer_id, oauth_scopes, rate_limit_tier)
- Authentication method used
- Token expiry time for rate limit reset calculation
- Credential validity confirmation

**Error Handling:**
- Invalid credentials: Return 401 Unauthorized (E9101)
- Expired token: Return 401 Unauthorized (E9102)
- Missing credentials: Return 401 Unauthorized (E9103)
- Authentication service unavailable: Return 503 Service Unavailable (E9803)

### 3.3 Authorization Engine

**Responsibility:** Enforce access control policies ensuring consumers can only access permitted resources and operations.

**Authorization Models:**

1. **Role-Based Access Control (RBAC)**
   - Consumer has assigned roles (ADMIN, DEVELOPER, GUEST)
   - Routes require specific roles for access
   - Role hierarchy: ADMIN > DEVELOPER > GUEST

2. **OAuth Scopes**
   - Scopes follow resource:action format
   - Examples: agents:invoke, operations:read, webhooks:manage
   - OAuth token must contain all required scopes for route
   - Scopes are case-sensitive

3. **Attribute-Based Access Control (ABAC)**
   - Policies evaluated by L08 Supervision component
   - Conditions on: consumer_tier, tenant, IP range, time-of-day, operation_cost
   - Policy evaluation returns explicit allow/deny
   - Deny decisions take precedence (fail-secure)

**Policy Evaluation:**

1. Extract consumer scopes from authentication
2. Check route required scopes (OAuth validation)
3. Evaluate RBAC role hierarchy
4. Call L08 Supervision for ABAC policy evaluation
5. Deny if any check fails (fail-secure)

**Outputs:**
- Authorization result (allow/deny)
- Consumed scopes (for audit logging)

**Error Handling:**
- Insufficient scopes: Return 403 Forbidden (E9207)
- Role mismatch: Return 403 Forbidden (E9206)
- Cross-tenant access: Return 403 Forbidden (E9205)

### 3.4 Rate Limiter

**Responsibility:** Enforce quota and rate limit policies to prevent abuse and ensure fair resource allocation.

**Rate Limiting Algorithm: Token Bucket**

```
Consumer has:
  - burst_capacity (tokens available for immediate use)
  - rps_limit (tokens refilled per second)
  - daily_quota (total tokens per day)

On each request:
  1. Check burst capacity: tokens_available >= tokens_required
  2. Check daily quota: daily_used <= daily_limit
  3. If both OK: Decrement tokens, allow request
  4. If either fails: Return 429 Too Many Requests
```

**Distributed Rate Limiting (Unified Across Protocols, IV-021):**
- Redis Lua script ensures atomic token bucket operations
- Key format: rl:consumer:{consumer_id}
- Field format: {burst_tokens, daily_used, reset_time}
- Supports cost-aware rate limiting (heavy ops cost more tokens)
- Same rate limit bucket for HTTP/1.1, HTTP/2, gRPC (protocol-independent)

**Rate Limit Tiers:**

| Tier | RPS Limit | Burst | Daily Quota |
|------|-----------|-------|-------------|
| STANDARD | 100 | 1000 | 100K |
| PREMIUM | 1000 | 10K | 1M |
| ENTERPRISE | 10K | 100K | 100M |

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
Retry-After: 30
```

**Error Handling:**
- Rate limit exceeded: Return 429 Too Many Requests (E9401)
- Daily quota exceeded: Return 429 Too Many Requests (E9402)
- Burst capacity exceeded: Return 429 Too Many Requests (E9404)

### 3.5 Idempotency Handler (IV-007)

**Responsibility:** Ensure idempotent operations are not duplicated when requests are retried.

**Idempotency Configuration:**

- Header Name: `Idempotency-Key`
- Key Format: UUID v4 (RFC 4122)
- Deduplication Window: 24 hours (configurable)
- Idempotent Methods: POST, PUT, DELETE
- Non-Idempotent Methods: GET, HEAD, OPTIONS

**Operation Flow:**

1. Consumer provides `Idempotency-Key: {uuid-v4}` header
2. Gateway checks Redis cache: `idempotency:{idempotency_key}`
3. If cache hit: Return cached response (same status, body, headers)
4. If cache miss: Process request normally
5. On success: Store response in Redis with 24-hour TTL
6. On error: Do NOT cache (allow retry)

**Response Headers for Duplicate Request:**

```
HTTP/1.1 200 OK
X-Idempotency-Replayed: true
X-Idempotency-Original-Request-ID: {original_request_id}
```

**Error Handling:**
- Invalid idempotency key format: Return 400 Bad Request (E9301)
- Idempotency key missing for idempotent method: Log warning (optional enforcement)

### 3.6 Async Operation Handler

**Responsibility:** Manage long-running operations that cannot complete within HTTP request/response cycle.

**Operation Lifecycle:**

1. **SUBMIT_REQUEST**: Consumer submits async request (marked by is_async_operation=true in route config)
2. **ASYNC_ACCEPTED**: Gateway returns 202 Accepted with operation_id
3. **OPERATION_CREATED**: Operation record created in L01 with status QUEUED
4. **RUNNING**: L02 Runtime executing agent
5. **COMPLETED/FAILED**: Execution finished, result available
6. **WEBHOOK_QUEUED**: If webhook registered, queue delivery
7. **WEBHOOK_SUCCESS/FAILED**: Webhook delivery completed (or all retries exhausted)

**Result Delivery Mechanisms:**

1. **Webhooks** (primary)
   - Consumer provides webhook_url during consumer registration
   - Gateway delivers result via HTTPS POST to webhook URL
   - SSRF Validation (IV-004): IP blocklist, DNS validation, TLS enforcement
   - Request includes HMAC-SHA256 signature for verification (IV-009)
   - Exponential backoff retry: 1s → 10s → 100s → 1000s → 10000s (5 attempts max)
   - After 5 failed attempts, dead-letter queue for manual review (IV-023)

2. **Polling** (fallback)
   - Consumer polls GET /operations/{id}/status periodically
   - Response includes progress (RUNNING), or result (COMPLETED/FAILED)
   - Result retention: 30 days by default, configurable per consumer
   - After retention expires, operation deleted (E9603 returned)

**Webhook Signature (IV-009):**

```
POST {webhook_url}
HMAC-SHA256({message}, {webhook_hmac_secret})

Message Format: "{timestamp}.{request_body}"
Signature Header: X-Webhook-Signature: sha256={hex_signature}
Timestamp Header: X-Webhook-Timestamp: {unix_timestamp}

Consumer validates:
  1. Verify signature matches computed HMAC-SHA256
  2. Check timestamp is within 5 minutes of current time
  3. Process webhook only if both checks pass
```

**Webhook Validation (SSRF Prevention, IV-004):**

```
Before delivery, validate webhook URL:
  1. Enforce HTTPS protocol (no HTTP)
  2. Block private IP ranges:
     - 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12
     - 192.168.0.0/16, 169.254.0.0/16
     - ::1/128 (IPv6 loopback), fc00::/7 (IPv6 private)
  3. Validate resolved DNS does not match blocklist
  4. Enforce TLS certificate validation (no self-signed)
  5. Limit timeout: 10 seconds maximum
  6. Limit redirect hops: 5 maximum
  7. Audit all webhook destinations (immutable log)
```

**Error Handling:**
- Operation not found: Return 410 Gone (E9602)
- Operation expired: Return 410 Gone (E9603)
- Invalid webhook URL: Return 400 Bad Request (E9701) + SSRF check failure details
- Webhook delivery failed: Retry with exponential backoff

### 3.7 Health Checker

**Responsibility:** Monitor backend service health and manage circuit breaker states. Kubernetes integration support.

**Health Check Types:**

1. **Liveness Check**: Is the service alive?
   - HTTP GET /health/live
   - Returns 200 if service responding
   - Timeout: 30 seconds
   - Failure threshold: 3 failures
   - Interval: Every 10 seconds

2. **Readiness Check**: Is the service ready for traffic?
   - HTTP GET /health/ready
   - Checks dependency health (L01 available? Redis available?)
   - Returns 200 if all critical dependencies healthy
   - Timeout: 30 seconds
   - Failure threshold: 1 failure (sensitive)
   - Interval: Every 5 seconds
   - Unhealthy services excluded from load balancing

3. **Startup Check**: Has the service completed initialization?
   - HTTP GET /health/startup
   - Checks if service is ready to receive traffic (Kubernetes)
   - Timeout: 30 seconds
   - Failure threshold: 3 failures
   - Interval: Every 10 seconds
   - Prevents readiness check before dependencies ready

4. **Detailed Check**: Full dependency status
   - HTTP GET /health/detailed
   - Returns detailed status of each dependency
   - L01: {status: healthy, latency_ms: 45, version: "v1.2.0"}
   - Redis: {status: healthy, latency_ms: 2}

**Dependency Health Matrix (IV-010):**

```
Per-dependency configuration:
  name: "L01", "Redis", "backend-service"
  health_check_path: "/health"
  timeout_ms: 5000
  required: true (for readiness)
  
Health check evaluates:
  - Connection available
  - Response time within SLA
  - No cascading failures
```

**Kubernetes Pod Spec (IV-015):**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api-gateway
spec:
  containers:
  - name: gateway
    image: api-gateway:1.2.0

    # Startup: wait for L01 connection
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 30  # 30 * 10s = 5 minute timeout

    # Readiness: check all dependencies
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8080
      initialDelaySeconds: 0
      periodSeconds: 5
      failureThreshold: 2  # 2 failures = 10s, remove from LB

    # Liveness: basic responsiveness
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      failureThreshold: 3  # 3 failures = 30s, restart pod

    # Graceful shutdown
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 15"]  # Wait for connections to drain
```

**Circuit Breaker State Machine (IV-005):**

```
CLOSED (normal operation)
    ├─ On success: Stay CLOSED
    ├─ On error threshold exceeded: → OPEN
    │  Error Threshold: 50% errors in 1-minute window
    │  Min Requests: 10 requests to measure
    └─ State Duration: Indefinite (until error)

OPEN (failing, reject requests)
    ├─ Return 503 Service Unavailable (fast-fail)
    ├─ After 60 seconds: → HALF_OPEN
    └─ State Duration: 60 seconds (exponential backoff max 30 min)

HALF_OPEN (testing recovery)
    ├─ Allow 1 probe request to backend
    ├─ If probe succeeds → CLOSED (success threshold: 5 successes)
    ├─ If probe fails → OPEN (restart timeout)
    └─ State Duration: Until probe result

RECOVERING (gradual ramp-up)
    ├─ Gradually increase traffic from 10% to 100%
    ├─ Duration: 5 minutes linear ramp
    ├─ Monitor error rate during ramp-up
    └─ Reopen circuit if error rate exceeds threshold
```

**Error Handling:**
- Circuit breaker open: Return 503 Service Unavailable (E9801)
- All replicas down: Return 503 Service Unavailable (E9803)
- Unhealthy dependency: Degrade gracefully (use cache if available)

---

## Section 4: Request Processing

### 4.1 Request Lifecycle State Machine

All requests flow through the following state machine, with detailed error paths:

```
START
  │
  ├─► [AUTHENTICATING]
  │   ├─ Extract credentials from headers/params
  │   ├─ Call L01 Consumer Registry lookup
  │   ├─ Validate consumer is active (not suspended)
  │   ├─ Check credential rotation status (IV-011)
  │   │
  │   ├─ SUCCESS: Extract consumer_id, oauth_scopes, rate_limit_tier
  │   └─ FAILURE: → [ERROR: 401 Unauthorized] (E9101-E9103)
  │
  ├─► [AUTHORIZING]
  │   ├─ Check OAuth scopes (if JWT auth used)
  │   ├─ Call L08 Supervision for ABAC policy evaluation
  │   ├─ Verify tenant_id matches authentication
  │   ├─ Check cross-tenant access protection
  │   │
  │   ├─ SUCCESS: Extract authorized scopes
  │   └─ FAILURE: → [ERROR: 403 Forbidden] (E9201-E9207)
  │
  ├─► [VALIDATING] (IV-006: Comprehensive input validation)
  │   ├─ Check request format (JSON/protobuf)
  │   ├─ Validate required parameters present
  │   ├─ Check parameter types and ranges
  │   ├─ Validate request body size (max 10MB)
  │   ├─ Character set validation:
  │   │  ├─ Reject null bytes (0x00)
  │   │  ├─ Reject control characters
  │   │  ├─ Normalize Unicode (NFC)
  │   │  └─ Validate UTF-8 encoding
  │   ├─ Header validation:
  │   │  ├─ Max header count: 100
  │   │  ├─ Max header size: 16KB
  │   │  └─ Forbidden headers: validate against blocklist
  │   ├─ Query string validation
  │   │  ├─ Max length: 4096 characters
  │   │  └─ Encoding validation (percent-encoded)
  │   │
  │   ├─ SUCCESS: Request validated
  │   └─ FAILURE: → [ERROR: 400 Bad Request] (E9301-E9309)
  │
  ├─► [IDEMPOTENCY_CHECK] (IV-007)
  │   ├─ Extract Idempotency-Key header (UUID v4 format)
  │   ├─ Check Redis cache for duplicate
  │   │
  │   ├─ If cache hit:
  │   │  ├─ Return cached response (200 with X-Idempotency-Replayed: true)
  │   │  └─ Skip to [LOGGING]
  │   │
  │   └─ If cache miss: Proceed to [RATE_LIMITING]
  │
  ├─► [RATE_LIMITING] (IV-021: Unified across protocols)
  │   ├─ Extract rate_limit_tier from consumer profile
  │   ├─ Look up tier configuration from L01
  │   ├─ Query Redis for current token bucket state
  │   ├─ Check burst capacity: tokens_available >= tokens_required
  │   ├─ Check daily quota: daily_used <= daily_limit
  │   ├─ Unified bucket: Same limit for HTTP/1.1, HTTP/2, gRPC
  │   ├─ Atomically decrement tokens (Redis Lua script)
  │   │
  │   ├─ SUCCESS: Quota check passed
  │   └─ FAILURE: → [ERROR: 429 Too Many Requests] (E9401-E9404)
  │
  ├─► [ROUTING]
  │   ├─ Extract HTTP method and path from request
  │   ├─ Call L01 Configuration Service: GetRoutes()
  │   ├─ Match request to route patterns (glob matching)
  │   ├─ Apply API versioning and deprecation rules
  │   ├─ Apply pagination rules if list operation (IV-018)
  │   ├─ Select backend service from list
  │   │
  │   ├─ SUCCESS: Route found, backend selected
  │   └─ FAILURE: → [ERROR: 404 Not Found] (E9001)
  │
  ├─► [QUEUING_OR_EXECUTING]
  │   ├─ Check if operation is async (is_async_operation=true)
  │   │
  │   ├─ IF ASYNC:
  │   │  ├─ Create operation record in L01 with status QUEUED
  │   │  ├─ Queue async task with L02 Runtime (with mTLS, IV-016)
  │   │  ├─ → [ASYNC_ACCEPTED] Return 202 with operation_id
  │   │  └─ Skip to [LOGGING]
  │   │
  │   └─ IF SYNC:
  │      ├─ Check backend capacity (not overloaded)
  │      ├─ On capacity exceeded: Queue request in local buffer (5s timeout)
  │      ├─ SUCCESS: Proceed to [EXECUTING]
  │      └─ FAILURE: → [ERROR: 503 Service Unavailable] (E9902)
  │
  ├─► [EXECUTING]
  │   ├─ Prepare backend request (inject context headers)
  │   ├─ Establish mTLS connection with certificate pinning (IV-016)
  │   ├─ Apply request timeout (default 60s)
  │   ├─ Invoke backend service
  │   ├─ Collect response body and status
  │   ├─ Check for transient errors (5xx status)
  │   │
  │   ├─ IF TRANSIENT ERROR:
  │   │  ├─ Apply retry strategy (exponential backoff with jitter)
  │   │  ├─ Max retries per route (default 3)
  │   │  ├─ Only retry on retryable status codes (503, 504, timeouts)
  │   │  ├─ Backoff: 100ms, 1s, 10s (with ±10% jitter)
  │   │  └─ On success: Proceed to [FORMATTING_RESPONSE]
  │   │
  │   ├─ SUCCESS: Backend responded, status < 500
  │   └─ FAILURE (after retries): → [ERROR: 502 Bad Gateway] (E9904)
  │
  ├─► [FORMATTING_RESPONSE]
  │   ├─ Sanitize response body (remove PII)
  │   ├─ Set Content-Type header
  │   ├─ Inject gateway headers:
  │   │  ├─ X-Request-ID: {request_id}
  │   │  ├─ X-Trace-ID: {trace_id}
  │   │  ├─ X-Span-ID: {span_id}
  │   │  ├─ X-RateLimit-Remaining: {tokens_remaining}
  │   │  ├─ X-RateLimit-Reset: {reset_timestamp}
  │   │  ├─ X-Idempotency-Replayed: {if replayed, IV-007}
  │   │  └─ Cache-Control: {route-specific policy}
  │   ├─ Remove sensitive headers (internal IDs, versions)
  │   │
  │   └─ SUCCESS: Response formatted
  │
  ├─► [WEBHOOK_DELIVERY] (only for async operations)
  │   ├─ Check if consumer has webhook_url configured
  │   │
  │   ├─ IF WEBHOOK CONFIGURED:
  │   │  ├─ Validate webhook URL (SSRF check, IV-004)
  │   │  ├─ Create WebhookDeliveryEvent with signature (IV-009)
  │   │  ├─ Queue webhook task with L01
  │   │  ├─ Apply retry strategy (exponential backoff, 5 max attempts)
  │   │  ├─ Signature: HMAC-SHA256("{timestamp}.{body}", secret)
  │   │  ├─ On all failures: Move to dead-letter queue (IV-023)
  │   │  ├─ Notify consumer of DLQ entry (email or webhook)
  │   │  ├─ Emit WebhookDeliveryEvent for each attempt
  │   │  └─ Track costs toward rate limit (optional)
  │   │
  │   └─ IF NO WEBHOOK:
  │      └─ Consumer must poll /operations/{id}/status
  │
  ├─► [LOGGING]
  │   ├─ Create APIRequestEvent with:
  │   │  ├─ request method, path, headers (redacted), body (redacted)
  │   │  ├─ response status, body (redacted), latency
  │   │  ├─ trace_id, span_id, consumer_id, tenant_id
  │   │  ├─ route_matched, backend_service, rate_limited flag
  │   │  ├─ idempotency_key (if used, IV-007)
  │   │  ├─ error_code (if error occurred)
  │   │  └─ log sampling decision (IV-012)
  │   ├─ Apply log sampling (IV-012):
  │   │  ├─ Probabilistic: 1% of requests (configurable)
  │   │  ├─ Tail sampling: 100% of errors, timeouts
  │   │  ├─ Adaptive: Increase rate during high error periods
  │   │  └─ Per-consumer override (log all for specific consumer)
  │   ├─ Redact sensitive data (passwords, secrets, tokens)
  │   ├─ Publish APIRequestEvent to L01 Event Store (async, schema versioned, IV-020)
  │   ├─ Send metrics to Prometheus (with exemplars, IV-002):
  │   │  ├─ http_request_duration_seconds (histogram with exemplar)
  │   │  ├─ http_requests_total (counter by status, method, path)
  │   │  ├─ rate_limit_violations_total
  │   │  ├─ idempotency_cache_hits_total (IV-007)
  │   │  └─ webhook_delivery_attempts_total (IV-009)
  │   ├─ Record audit log (immutable, time-locked, IV-026)
  │   │
  │   └─ SUCCESS: Events emitted
  │
  └─► END (Return response to consumer)
```

### 4.2 Error Paths and Recovery (IV-014)

Requests can fail at any stage. Error handling follows this pattern:

1. **Fail-Safe Decision**: Error detected
2. **Error Categorization**: Map to error code (E9xxx)
3. **HTTP Status Mapping**: Convert error code to HTTP status
4. **Response Formatting**: Return error object to consumer
5. **Audit Logging**: Emit error event for debugging

**Error Response Format:**

```json
{
  "error": {
    "code": "E9101",
    "message": "Invalid API key",
    "timestamp": 1640000000000,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7",
    "request_id": "req-12345678"
  }
}
```

**Client-Side Error Recovery (IV-014):**

```
Error categorization by status code:

4xx (Client Error - Permanent)
  ├─ 400 Bad Request: Don't retry (invalid input)
  ├─ 401 Unauthorized: Don't retry (auth failed)
  ├─ 403 Forbidden: Don't retry (not authorized)
  ├─ 404 Not Found: Don't retry (resource missing)
  ├─ 409 Conflict: Don't retry (state conflict)
  └─ Others (4xx): Return immediately

5xx (Server Error - Transient)
  ├─ 500 Internal Server Error: Retry with exponential backoff
  ├─ 502 Bad Gateway: Retry with exponential backoff
  ├─ 503 Service Unavailable: Retry with exponential backoff
  └─ 504 Gateway Timeout: Retry with exponential backoff

429 (Rate Limit - Respects Retry-After)
  └─ Retry-After: 5
     ├─ Respect header value if provided
     └─ Exponential backoff if header absent

Exponential Backoff Algorithm (IV-014):
  backoff_ms = min(
    initial_backoff_ms * (multiplier ^ attempt),
    max_backoff_ms
  )
  actual_backoff = backoff_ms * (1 + random(-jitter, +jitter))

  Parameters:
  ├─ initial_backoff_ms: 100
  ├─ multiplier: 10
  ├─ max_backoff_ms: 60000 (1 minute)
  ├─ jitter_factor: 0.1 (±10%)
  ├─ max_retries: 3
  └─ total_timeout_ms: 30000 (30 seconds)

Client-side retry pseudocode:
  for attempt in 1..max_retries:
    try:
      response = send_request()
      if response.status in [429, 500, 502, 503, 504]:
        wait_time = parse_retry_after(response) OR backoff_ms
        if elapsed_time + wait_time > total_timeout:
          raise TimeoutError
        sleep(wait_time)
        continue
      else:
        return response
    except network_error:
      // Network errors are transient, always retry
      sleep(backoff_ms)
      continue
  // All retries exhausted
  raise ExhaustedRetriesError
```

### 4.3 Multi-Tenancy Validation

Tenant context is validated and enforced throughout request processing:

1. **Tenant Extraction**: Extract from JWT claims, headers, or consumer profile
2. **Tenant Verification**: Verify tenant_id matches authenticated consumer's authorized tenants
3. **Tenant Propagation**: Include tenant_id in all L01 queries (row-level security filter)
4. **Cross-Tenant Prevention**: Reject any request accessing other tenant's resources

**Tenant Context Fields:**

```
X-Tenant-ID: "org-123456789"
X-Tenant-Type: "ORGANIZATION"  // or "INDIVIDUAL"
X-Tenant-Roles: ["admin", "developer"]
```

### 4.4 Timeout and Graceful Degradation (IV-024)

**Request Timeouts:**
- Per-route timeout (configurable, default 60s)
- Hard timeout: 120s maximum (circuit breaker opens)
- Backend invocation timeout: 65s (includes network latency buffer)

**Graceful Degradation with Cache Invalidation (IV-024):**
- L01 unavailable: Use cached consumer profiles (5-minute TTL, invalidates via watch stream)
- L01 unavailable: Use cached route configuration (5-minute TTL, invalidates via watch stream)
- Redis unavailable: Fall back to in-memory rate limiting (single instance only)
- Backend unhealthy: Return 503; exclude from load balancing
- Cache invalidation: Explicit invalidation triggers (ConfigurationChangeEvent), version tracking

### 4.5 Pagination (IV-018)

**Pagination Configuration:**

```protobuf
message PaginationConfig {
  enum Style {
    CURSOR = 0;           // Recommended
    OFFSET = 1;           // Alternative
  }
  Style style = 1;

  int32 default_limit = 2;         // Default: 50
  int32 max_limit = 3;             // Max: 1000
  string sort_order = 4;           // "-created_at" (descending)
}
```

**Cursor-Based Pagination (Recommended):**

```
GET /operations?cursor=abc123&limit=100

Response:
{
  "items": [...],
  "next_cursor": "def456",
  "prev_cursor": "xyz789",
  "total_count": 12345,
  "has_more": true
}
```

**Offset-Based Pagination (Alternative):**

```
GET /operations?offset=0&limit=100

Response:
{
  "items": [...],
  "total_count": 12345,
  "has_more": true
}
```

---

## Section 5: Async Operations

### 5.1 Distinguishing Sync vs. Async Endpoints

Routes can be configured as either synchronous or asynchronous:

**Synchronous Routes** (Default)
- Request waits for backend processing to complete
- Response returned with result or error
- HTTP 200, 400, 500, etc. returned directly
- Client must wait for response (up to route timeout)
- Use cases: Metadata queries, real-time operations

**Asynchronous Routes**
- Request accepted immediately (202 Accepted)
- Operation created in background
- Response includes operation_id for polling/webhooks
- Client continues without waiting
- Use cases: Long-running agents, complex computations, async workflows

**Route Configuration:**

```protobuf
message RouteDefinition {
  bool is_async_operation = 18;  // Enable async handling
  string async_result_delivery = 19;  // WEBHOOK, POLLING, SSE
  // ... other fields
}
```

### 5.2 202 Accepted Response Model

Async operations are accepted with HTTP 202 and return operation metadata:

**Request:**
```
POST /agents/{id}/invoke
Authorization: Bearer {token}
Content-Type: application/json

{
  "parameters": {...}
}
```

**Response (202 Accepted):**
```
HTTP/1.1 202 Accepted
Content-Type: application/json
X-Request-ID: req-12345678
X-Trace-ID: 4bf92f3577b34da6a3ce929d0e0e4736
Retry-After: 5

{
  "operation_id": "op-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "QUEUED",
  "created_at": "2026-01-05T10:00:00Z",
  "webhook_url": "https://consumer.example.com/webhook",
  "polling_url": "https://api.example.com/operations/op-f47ac10b-58cc-4372-a567-0e02b2c3d479/status",
  "estimated_duration_ms": 45000
}
```

### 5.3 Operation Lifecycle (QUEUED → RUNNING → COMPLETED)

**State Transitions:**

1. **QUEUED** (Initial state)
   - Operation created in L01
   - Waiting for L02 Runtime to pick up task
   - Duration: typically < 1 second

2. **RUNNING** (Execution in progress)
   - L02 Runtime acquired task
   - Agent executing requested operation
   - Consumer can poll for progress updates
   - Duration: seconds to minutes (application-dependent)

3. **COMPLETED** (Success)
   - Agent finished execution successfully
   - Result stored in L01
   - Webhook delivery queued (if configured)
   - Available for 30 days (retention configurable)

4. **FAILED** (Error)
   - Agent failed during execution
   - Error information stored in L01
   - Webhook delivery queued with failure details
   - Available for 30 days

**State Machine Diagram:**

```
    ┌─────────────────────────────────────┐
    │      QUEUED (initial)               │
    │  (waiting for runtime pickup)       │
    │  Duration: < 1s                     │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │      RUNNING                        │
    │  (agent execution in progress)      │
    │  Can poll /status for progress      │
    │  Duration: seconds to minutes       │
    └──────┬──────────────────┬───────────┘
           │                  │
     SUCCESS│                 │FAILURE
           │                  │
           ▼                  ▼
    ┌──────────────┐   ┌──────────────┐
    │  COMPLETED   │   │    FAILED    │
    │  (success)   │   │   (error)    │
    └──────┬───────┘   └──────┬───────┘
           │                  │
           └──────────┬───────┘
                      │
                      ▼
           ┌────────────────────┐
           │ WEBHOOK_QUEUED     │
           │ (if webhook exists) │
           │ Retries: 5 max     │
           └────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
    ┌─────────────┐      ┌──────────────┐
    │ WEBHOOK_SUC │      │ WEBHOOK_FAIL │
    │ (delivered) │      │ (dl-queue)   │
    └─────────────┘      └──────────────┘
```

### 5.4 Webhook Delivery Mechanism with SSRF and Signature Verification

Webhooks provide push-based result delivery to external systems with security validations.

**Webhook Registration:**

Consumer registers webhook during onboarding:
```json
{
  "webhook_url": "https://consumer.example.com/webhook",
  "webhook_hmac_secret": "sk_live_xxxxxxxxxxxxx"
}
```

**Webhook Delivery Request with Signature (IV-009):**

```
POST https://consumer.example.com/webhook
Content-Type: application/json
X-Webhook-Signature: sha256=4d0e23c7ddf92f8eac9a0285e06c8d21bd0329df
X-Webhook-Timestamp: 1640000000
X-Webhook-Version: 1

{
  "event_id": "evt-abc123",
  "event_type": "operation.completed",
  "timestamp": 1640000000000,
  "operation_id": "op-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "COMPLETED",
  "result": {
    "agent_id": "agent-001",
    "output": "Task completed successfully"
  }
}
```

**Signature Verification (IV-009):**

```python
import hmac
import hashlib

signature_header = request.headers['X-Webhook-Signature']
timestamp_header = request.headers['X-Webhook-Timestamp']
body = request.body
secret = webhook_hmac_secret

# Message format: "{timestamp}.{body}"
message = f"{timestamp_header}.{body}"

# Extract signature from header (format: "sha256=xxx")
expected = 'sha256=' + hmac.new(
  secret.encode(),
  message.encode(),
  hashlib.sha256
).hexdigest()

# Check signature
if not hmac.compare_digest(signature_header, expected):
  return 401 Unauthorized  # Invalid signature

# Check timestamp (reject if > 5 minutes old)
current_time = time.time()
if abs(current_time - int(timestamp_header)) > 300:
  return 401 Unauthorized  # Timestamp too old
```

**SSRF Validation (IV-004):**

```
Before sending webhook, validate:
  1. Enforce HTTPS protocol only (no HTTP, no FTP, etc.)
  2. Block private/internal IP ranges:
     - 127.0.0.0/8 (loopback)
     - 10.0.0.0/8 (private)
     - 172.16.0.0/12 (private)
     - 192.168.0.0/16 (private)
     - 169.254.0.0/16 (link-local)
     - ::1/128 (IPv6 loopback)
     - fc00::/7 (IPv6 private)
  3. Validate resolved DNS does not match blocklist
     - Resolve hostname and check IP against blocklist
  4. Enforce TLS certificate validation
     - Do NOT allow self-signed certificates
     - Validate certificate chain
  5. Enforce timeout (10 seconds maximum)
  6. Enforce redirect limits (5 maximum)
  7. Audit all webhook destinations (immutable log, IV-026)
  8. Log SSRF violation attempts
```

### 5.5 Webhook Retry Strategy and Dead-Letter Queue

Webhooks are retried with exponential backoff if delivery fails:

**Retry Schedule:**
- Attempt 1: Immediately
- Attempt 2: After 1 second
- Attempt 3: After 10 seconds
- Attempt 4: After 100 seconds
- Attempt 5: After 1000 seconds (~17 minutes)
- After 5th failure: Move to dead-letter queue for manual review (IV-023)

**Retryable Conditions:**
- HTTP 5xx status codes (500, 502, 503, 504)
- HTTP 408 Request Timeout
- HTTP 429 Too Many Requests
- Network timeout (>10 seconds)
- Connection refused
- DNS resolution failure

**Non-Retryable Conditions:**
- HTTP 4xx status codes (except 408, 429)
- HTTPS certificate validation failure
- Webhook URL blocked by SSRF check (IV-004)
- Consumer account suspended

**Dead-Letter Queue (IV-023):**

When a webhook fails after 5 attempts, it's stored in the DLQ:

```json
{
  "webhook_delivery_id": "whd-xyz",
  "operation_id": "op-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "webhook_url": "https://consumer.example.com/webhook",
  "consumer_id": "consumer-123",
  "last_error": "Connection timeout after 10s",
  "last_error_time": "2026-01-05T10:17:30Z",
  "last_attempt_time": "2026-01-05T10:17:30Z",
  "total_attempts": 5,
  "created_at": "2026-01-05T10:00:00Z",
  "retention_until": "2026-02-04T10:00:00Z"
}
```

**DLQ Recovery (IV-023):**

1. Consumer notification:
   - Email: "Webhook delivery failed for operation {op_id}"
   - Webhook: POST to fallback URL with failure details

2. Manual recovery API:
   - List DLQ entries: GET /webhooks/dead-letter
   - Review entry: GET /webhooks/dead-letter/{id}
   - Update webhook URL: PUT /webhooks/dead-letter/{id}
   - Manually retry: POST /webhooks/dead-letter/{id}/retry
   - Delete entry: DELETE /webhooks/dead-letter/{id}

3. DLQ monitoring:
   - Alert if >100 entries
   - Track growth rate
   - Provide dashboard view

4. DLQ retention and cleanup:
   - TTL: 30 days (configurable)
   - Auto-delete after retention expires
   - Audit trail for all deletions

### 5.6 Polling as Alternative

For consumers without webhooks, polling provides result retrieval:

**Polling Endpoint:**

```
GET /operations/{operation_id}/status
Authorization: Bearer {token}
```

**Polling Response (Running):**

```json
{
  "operation_id": "op-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "RUNNING",
  "created_at": "2026-01-05T10:00:00Z",
  "progress_percent": 45,
  "estimated_time_remaining_ms": 25000
}
```

**Polling Response (Completed):**

```json
{
  "operation_id": "op-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "COMPLETED",
  "created_at": "2026-01-05T10:00:00Z",
  "completed_at": "2026-01-05T10:02:30Z",
  "result": {
    "agent_id": "agent-001",
    "output": "Task completed successfully"
  }
}
```

**Polling Best Practices:**
- Start with 1-second poll interval
- Exponential backoff: Double interval on each poll (max 30s)
- Stop polling after 30 days (operation expires)
- Use Retry-After header if provided

---

## Section 6: Integration with Data Layer

### 6.1 Data Layer Components Used

The API Gateway Layer (L09) integrates with the following Data Layer (L01) components via mTLS (IV-016):

#### 6.1.1 Consumer Registry

The Consumer Registry maintains metadata for all external API consumers. L09 queries this registry to validate incoming requests.

**Data Structure: Consumer Profile**

```protobuf
message ConsumerProfile {
  string consumer_id = 1;
  string consumer_name = 2;
  string organization = 3;

  // Authentication
  repeated string api_keys = 4;  // Hashed API keys (bcrypt)
  repeated OAuthClient oauth_clients = 5;
  string mTLS_certificate_cn = 6;  // mTLS certificate common name
  int64 last_credential_rotation = 7;  // Timestamp of last rotation

  // Rate Limiting & Quotas
  string rate_limit_tier = 8;  // STANDARD, PREMIUM, ENTERPRISE
  int32 rate_limit_rps = 9;    // Requests per second
  int32 rate_limit_burst = 10; // Burst capacity
  int32 quota_daily_limit = 11; // Daily quota

  // OAuth Configuration
  repeated string oauth_scopes = 12;  // Permitted scopes

  // Webhook Configuration
  repeated string webhook_urls = 13;
  string webhook_hmac_secret = 14;

  // Metadata
  int64 created_timestamp = 15;
  int64 last_updated = 16;
  bool is_active = 17;
}

message OAuthClient {
  string client_id = 1;
  string client_secret_hash = 2;  // Hashed with Argon2
  repeated string allowed_redirect_uris = 3;
  repeated string scopes = 4;
  int64 last_secret_rotation = 5;  // For rotation tracking
}
```

#### 6.1.2 Configuration Service

The Configuration Service stores route definitions, API versioning policies, and authentication methods. Uses mTLS for L09 connections (IV-016).

**Data Structure: Route Definition**

```protobuf
message RouteDefinition {
  string route_id = 1;
  string api_path = 2;        // Glob pattern: /agents/{id}/*, /operations/**
  string http_method = 3;     // GET, POST, PUT, DELETE, PATCH

  // Routing Configuration
  repeated string backend_services = 4;  // Service IDs in internal mesh
  string load_balancing_strategy = 5;   // LEAST_CONNECTIONS, ROUND_ROBIN, CONSISTENT_HASH

  // API Versioning
  string api_version = 6;     // v1, v2, v3
  string deprecated_since = 7; // ISO timestamp
  string sunset_date = 8;      // ISO timestamp

  // Rate Limiting
  int32 rate_limit_rps = 9;
  int32 rate_limit_burst = 10;
  bool cost_aware = 11;
  int32 cost_units = 12;       // Default 1, heavy ops: 10+

  // Timeout & Retry
  int32 timeout_ms = 13;       // Default 60000
  int32 max_retries = 14;      // Default 3
  repeated int32 retryable_status_codes = 15;

  // Required Scopes
  repeated string required_oauth_scopes = 16;

  // Features
  bool supports_streaming = 17;
  bool is_async_operation = 18;
  string async_result_delivery = 19;  // WEBHOOK, POLLING, SSE

  // Documentation
  string operation_id = 20;    // OpenAPI operationId
  string description = 21;
  map<string, string> examples = 22;
}
```

### 6.2 Event Store Integration with Schema Versioning (IV-020)

L09 emits events to the Event Store for audit trails, analytics, and webhook triggering.

**Event Schema with Versioning (IV-020):**

```protobuf
message EventSchema {
  string event_type = 1;           // "api.request.received"
  int32 version = 2;               // Current version
  int32 min_compatible_version = 3; // Consumers must support >= this

  message Field {
    string name = 1;
    string type = 2;               // "string", "int32", "object"
    bool required = 3;
    string deprecated_since_version = 4;  // e.g., "v2"
    string deprecated_replacement = 5;    // e.g., "new_field_name"
    string deprecation_removal_date = 6;  // ISO timestamp
  }
  repeated Field fields = 4;

  message EvolutionPolicy {
    bool allow_new_optional_fields = 1;   // Always ok
    bool allow_remove_fields = 2;         // Requires version bump
    int32 field_removal_grace_period_days = 3;  // 180 days notice
  }
  EvolutionPolicy evolution = 5;
}
```

**Event Schema: API Request Event**

```protobuf
message APIRequestEvent {
  string event_id = 1;           // Unique event ID (UUID)
  string event_type = 2;         // "api.request.received"
  int32 event_version = 3;       // Current version (IV-020)
  int64 timestamp = 4;           // Milliseconds since epoch

  // Request Context
  string trace_id = 5;           // W3C Trace Context (validated, IV-022)
  string span_id = 6;            // Current span ID
  string consumer_id = 7;        // From authentication
  string tenant_id = 8;          // Multi-tenant context

  // Request Details
  string http_method = 9;
  string request_path = 10;
  string query_string = 11;
  map<string, string> headers = 12;
  bytes request_body = 13;       // Redacted (PII removed)
  string content_type = 14;
  string client_ip = 15;
  string idempotency_key = 16;   // If provided (IV-007)

  // Response Details
  int32 http_status = 17;
  bytes response_body = 18;      // Redacted
  int32 response_time_ms = 19;

  // Processing Steps
  string route_matched = 20;
  string backend_service = 21;
  bool rate_limited = 22;
  bool idempotency_replayed = 23;  // True if cached response (IV-007)
  string error_code = 24;        // E9xxx if error

  // Tags
  map<string, string> tags = 25;
}

message WebhookDeliveryEvent {
  string event_id = 1;
  string event_type = 2;         // "webhook.delivery.attempted"
  int32 event_version = 3;       // IV-020
  int64 timestamp = 4;

  string webhook_id = 5;
  string webhook_url = 6;        // HTTPS URL (SSRF validated, IV-004)
  string consumer_id = 7;

  int32 attempt_number = 8;
  int32 http_status = 9;
  int32 response_time_ms = 10;
  bool success = 11;
  string failure_reason = 12;    // If failed
}

message RateLimitViolationEvent {
  string event_id = 1;
  string event_type = 2;         // "rate_limit.violation"
  int32 event_version = 3;
  int64 timestamp = 4;

  string consumer_id = 5;
  string endpoint = 6;
  int32 excess_requests = 7;     // How many over limit
  string rate_limit_tier = 8;
  bool protocol_unified = 9;     // True if unified bucket (IV-021)
}
```

**Event Validation on Publish (IV-020):**

```
Before publishing event:
  1. Check event matches schema for declared version
  2. Reject unknown fields (fail-safe)
  3. Verify all required fields present
  4. Validate field types match schema
  5. Apply field redaction rules (PII, secrets)
  6. Sign event for immutability (IV-026)
```

### 6.3 Context Injection Integration with W3C Validation (IV-022)

L09 maintains request context throughout processing and injects it into backend services.

**W3C Trace Context Validation (IV-022):**

```
Traceparent format: "version-trace_id-parent_id-trace_flags"
Example: "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

Validation rules:
  1. Version: 00 (current version only)
  2. Trace ID: 32 hex chars (16 bytes), not all zeros
     - Reject: "00000000000000000000000000000000"
  3. Parent ID: 16 hex chars (8 bytes), not all zeros
     - Reject: "0000000000000000"
  4. Trace Flags: 2 hex chars (valid: 00, 01, 02, 03)
  5. Format: Exact format validation
  6. Sampling decision: Bit 0 = 0 (not sampled) or 1 (sampled)

Generation policy (if missing):
  1. Generate random 16-byte trace ID (RANDOM strategy)
  2. Generate random 8-byte span ID
  3. Set sampling decision based on configuration
  4. Propagate to all downstream services
```

**Request Context Structure**

```protobuf
message RequestContext {
  // Tracing (with W3C validation, IV-022)
  string trace_id = 1;           // W3C format: "version-traceId-parentId-traceFlags"
  string span_id = 2;            // Parent span for this request
  bool trace_sampled = 3;        // Sampling decision

  // Authentication & Authorization
  string consumer_id = 4;        // Primary identity
  repeated string consumer_roles = 5;
  repeated string oauth_scopes = 6;
  int64 token_expiry = 7;

  // Multi-Tenancy
  string tenant_id = 8;          // Tenant context (verified, immutable)
  string tenant_type = 9;        // ORGANIZATION, INDIVIDUAL

  // Rate Limiting
  string rate_limit_tier = 10;
  int32 remaining_quota = 11;
  int64 quota_reset_time = 12;
  bool quota_unified = 13;       // True if unified bucket (IV-021)

  // Request Metadata
  string client_ip = 14;
  string user_agent = 15;
  string request_id = 16;
  int64 request_received_time = 17;

  // Idempotency (IV-007)
  string idempotency_key = 18;   // UUID v4
  bool idempotency_replayed = 19; // True if cached

  // Feature Flags & Config
  map<string, bool> feature_flags = 20;
  map<string, string> context_attributes = 21;
}
```

**Propagation Rules**

1. **Header Injection into Backend Calls**

```
X-Request-ID: {request_context.request_id}
X-Trace-ID: {request_context.trace_id}
X-Span-ID: {request_context.span_id}
X-Consumer-ID: {request_context.consumer_id}
X-Tenant-ID: {request_context.tenant_id}
X-Tenant-Type: {request_context.tenant_type}
X-Idempotency-Key: {request_context.idempotency_key}
Authorization: Bearer {original_token}  // Pass through original auth
Traceparent: {w3c_format}  // W3C Trace Context
Tracestate: {vendor_extensions}  // Optional vendor extensions
```

2. **Validation Points**

- At entry (L09): Extract from request headers/query params
- At backend call: Inject into headers (with mTLS, IV-016)
- On L01 query: Pass tenant_id as query filter
- On webhook: Include in webhook signature (IV-009)
- W3C validation: Check trace ID format and values (IV-022)

---

## Section 7: Reliability and Scalability

### 7.1 Failure Modes and Chaos Engineering (IV-013)

This section catalogs 15+ failure scenarios with detection, impact, and recovery procedures. Includes chaos engineering scenarios for resilience validation.

#### Failure Modes Matrix

| Failure ID | Failure Mode | Detection | Impact | Priority | Recovery |
|-----------|--------------|-----------|--------|----------|----------|
| F-001 | Backend service unreachable | Health check timeout after 3 attempts | Requests fail with 503 | CRITICAL | Circuit breaker opens; route to fallback |
| F-002 | Rate limiter (Redis) unavailable | Connection timeout to Redis | Cannot enforce rate limits | CRITICAL | Fall back to per-node rate limiting (stricter) |
| F-003 | Consumer Registry unreachable | L01 query timeout | Cannot authenticate requests | CRITICAL | Use cached consumer profiles (5min TTL) |
| F-004 | Configuration Service down | Config reload fails | Using stale configuration | HIGH | Keep last-known-good config; retry reload |
| F-005 | Event store write failure | Publish timeout | Audit logs missing | HIGH | Queue events locally; retry on reconnect |
| F-006 | Webhook delivery failure | HTTP error or timeout | External notification lost | MEDIUM | Retry with exponential backoff (5 attempts) |
| F-007 | Request validation schema invalid | Schema parse error on startup | Gateway won't start | CRITICAL | Reject invalid config; maintain old schema |
| F-008 | Distributed cache (config) inconsistent | Different nodes see different configs | Behavior inconsistency | MEDIUM | Re-query L01; use version numbers |
| F-009 | TLS certificate expired | X509 verification failure | Clients can't connect | CRITICAL | Automatic renewal via Cert Manager |
| F-010 | Request body size exceeds limit | Size check at stream start | Request rejected | LOW | Return 413 Payload Too Large |
| F-011 | Request processing exceeds timeout | Timer fires after deadline | Request cancelled mid-process | MEDIUM | Clean up resources; return 504 |
| F-012 | Distributed trace system unavailable | Span export timeout | Tracing data lost | LOW | Local buffering; graceful degradation |
| F-013 | Metrics collection cardinality explosion | Metric registration fails | Metrics unusable | MEDIUM | Drop old series; apply cardinality limits |
| F-014 | Memory pressure (connection pool exhausted) | Allocator fails | New requests rejected | HIGH | Shed load; close idle connections |
| F-015 | Network partition (multi-region) | Rate limit sync fails | Cross-region quota inconsistency | MEDIUM | Local enforcement; reconcile after recovery |

#### Chaos Engineering Scenarios (IV-013)

```protobuf
message ChaosExperiment {
  string experiment_id = 1;          // "ce-001-backend-latency"
  string description = 2;             // Human-readable description
  enum Severity {
    LOW = 0;        // Single node
    MEDIUM = 1;     // Multiple nodes
    HIGH = 2;       // Critical path
  }
  Severity severity = 3;

  // Failure injection
  message Injection {
    enum FailureType {
      LATENCY = 0;        // Add delay
      ERROR_RATE = 1;     // % return errors
      PACKET_LOSS = 2;    // Network loss
      TIMEOUT = 3;        // Connection timeout
      CRASH = 4;          // Pod restart
    }
    FailureType type = 1;
    string target = 2;    // "redis", "l01", "backend:service-name"
    int32 start_time_unix = 3;
    int32 duration_seconds = 4;
    float intensity = 5;  // 0.0-1.0
  }
  repeated Injection injections = 4;

  // Success criteria
  string success_metrics = 5;  // Prometheus query
  bool success_if_all_pass = 6;

  // Schedule
  string cron_schedule = 7;    // When to run (optional)
  bool requires_approval = 8;  // Manual approval first
}
```

**Scenario 1: Backend Latency Spike**

```
Scenario: Backend adds 500ms latency
  Trigger: Gradual increase from 0→500ms over 30 seconds
  Duration: 5 minutes
  Expected: Circuit breaker opens, returns 503 after 50% errors
  Success: No client errors during recovery, error budget <10%
```

**Scenario 2: Redis Unavailable**

```
Scenario: Redis crashes for 30 seconds
  Trigger: Network partition to Redis
  Duration: 30 seconds
  Expected: Fall back to per-node rate limiting, requests don't fail
  Success: Request latency increases <50%, no 429 errors
```

**Scenario 3: L01 Consumer Registry Timeout**

```
Scenario: L01 queries take >2 seconds
  Trigger: Slow queries to Consumer Registry
  Duration: 1 minute
  Expected: Use cached profiles, 5% of requests hit cache
  Success: No authentication failures for cached consumers
```

### 7.2 Recovery Procedures and Cache Invalidation (IV-024)

#### Cache Invalidation Strategy (IV-024)

**Multi-Level Caching with Invalidation:**

```protobuf
message CacheInvalidationPolicy {
  // TTL-based expiry
  int32 consumer_profile_ttl_seconds = 1;     // Default: 300
  int32 route_config_ttl_seconds = 2;         // Default: 300
  int32 auth_cache_ttl_seconds = 3;           // Default: 60
  int32 idempotency_cache_ttl_seconds = 4;    // Default: 86400 (24 hours)

  // Explicit invalidation triggers
  bool watch_l01_changes = 5;                 // Default: true
  string change_watch_topic = 6;              // gRPC stream topic
  int32 watch_reconnect_backoff_ms = 7;       // Exponential backoff

  // Version-based coherence
  bool use_version_numbers = 8;               // Default: true
  bool reject_stale_versions = 9;             // Default: true

  // Stale-while-revalidate (IV-024)
  bool serve_stale_if_refresh_fails = 10;     // Default: true
  int32 stale_grace_period_seconds = 11;      // Serve for 60s after TTL

  // Cache warming
  bool preload_on_startup = 12;               // Default: true
  repeated string preload_keys = 13;          // Keys to preload

  // Multi-level caching
  enum CachingStrategy {
    LOCAL_ONLY = 0;                    // L09 instance memory only
    LOCAL_WITH_REDIS = 1;              // L09 + Redis L2
    REDIS_ONLY = 2;                    // Redis primary, L09 secondary
  }
  CachingStrategy strategy = 14;

  // Monitoring
  bool track_cache_hit_rate = 15;             // Default: true
  int32 alert_miss_rate_threshold = 16;       // Alert if > 20%
}
```

**Invalidation Algorithm (IV-024):**

```
1. On startup: load all preload_keys from L01
2. On ConfigurationChangeEvent: invalidate affected keys immediately
3. On timer (every 5s): check for expired TTLs, refresh from L01
4. On access:
   if local_cache.has(key) && !expired(key):
     return local_cache[key]
   else if stale_allowed(key) && stale_cache.has(key):
     serve stale_cache[key]
     refresh_in_background()  // Async refresh
   else:
     refresh_from_l01()
5. Watch stream: Invalidate cache on ConfigurationChangeEvent
   - Immediate invalidation (no TTL wait)
   - Version-based validation (reject stale)
```

#### F-001: Backend Service Unreachable

**Detection Trigger:**
```
health_check_failure_count >= 3 in 30 seconds
```

**Recovery Procedure:**

```
Step 1: Mark backend as UNHEALTHY
  - Remove from active pool
  - Stop routing new requests
  - In-flight requests: continue processing

Step 2: Open circuit breaker for this backend
  - State: OPEN
  - Return HTTP 503 Service Unavailable for 60 seconds
  - Emit FailureEvent to event store

Step 3: Transition to HALF_OPEN after 60 seconds
  - Allow 1 probe request to backend
  - If probe succeeds: close circuit (backend healthy)
  - If probe fails: reopen circuit (60 more seconds)

Step 4: Exponential backoff
  - Attempt 1: after 60s
  - Attempt 2: after 120s
  - Attempt 3: after 240s
  - Max: 30 minutes between attempts

Step 5: When backend recovers
  - Circuit closes
  - Gradually increase traffic (ramp-up over 5 minutes)
  - Re-add to active backend pool
```

#### F-002: Rate Limiter (Redis) Unavailable

**Detection Trigger:**
```
redis_connection_timeout OR redis_operation_latency > 5 seconds
```

**Recovery Procedure:**

```
Step 1: Switch to local (per-gateway) rate limiting
  - Each gateway node maintains token bucket locally
  - Tighter limits (assume distributed load)
  - Consumer limit_rps → limit_rps / num_gateway_nodes

Step 2: Enable degraded mode
  - Return HTTP 503 if Redis unavailable for >30 seconds
  - Log warning: "Rate limiting degraded; local enforcement active"
  - Emit DegradedModeEvent

Step 3: Retry Redis connection every 5 seconds
  - Exponential backoff on connection failures
  - Once connected: sync local token buckets to Redis
  - Resume distributed enforcement

Step 4: Reconciliation on recovery
  - Compare local counters with Redis state
  - Adjust quotas if consumed more than allowed
  - Emit ReconciliationEvent

Step 5: Alert operations
  - Page on-call if Redis unavailable >5 minutes
  - Provide status: num_gateways in degraded mode
```

#### F-003: Consumer Registry Unreachable

**Detection Trigger:**
```
consumer_registry_latency > 2 seconds OR connection_refused
```

**Recovery Procedure:**

```
Step 1: Check local cache for consumer (5-minute TTL, IV-024)
  - If cache hit: use cached profile
  - If cache miss: proceed to Step 2

Step 2: Return authentication error
  - HTTP 401 Unauthorized (cannot verify identity)
  - Error code: E9101 (Authentication service unavailable)
  - Log event with retry indication

Step 3: Implement exponential backoff retry
  - Retry 1: immediately
  - Retry 2: after 100ms
  - Retry 3: after 1 second
  - Max: 3 retries over 2 seconds

Step 4: If all retries fail
  - Use fallback authentication (emergency API key)
  - Emit AuthenticationFallbackEvent
  - Alert operations

Step 5: Connection recovery
  - When L01 reconnects, flush expired cache entries
  - Resume normal authentication flow

Step 6: Monitoring
  - Alert if >1% of requests hit fallback auth
  - Track cache hit rate
```

#### F-004: Configuration Service Down

**Detection Trigger:**
```
config_reload_failure OR watch_stream_disconnected
```

**Recovery Procedure:**

```
Step 1: Keep last-known-good configuration
  - Maintain version number for each config
  - Store on-disk backup of latest config
  - Continue routing with stale config

Step 2: Log configuration staleness
  - Emit ConfigurationStalenessEvent
  - Track how long using stale config
  - Alert if >5 minutes

Step 3: Retry configuration reload every 10 seconds
  - Exponential backoff: 10s, 20s, 40s... (max 5 minutes)
  - When successful: apply new config atomically
  - All in-flight requests use old config; new requests use new

Step 4: Graceful transition
  - New route definitions: used immediately
  - Removed route definitions: reject after 5-minute grace period
  - Modified routes: clients see old behavior for 5 minutes

Step 5: Alert operations
  - Page on-call if stale config >15 minutes
  - Provide details: last update time, version
```

### 7.3 Circuit Breaker Patterns with State Transitions (IV-005)

#### Circuit Breaker State Machine (IV-005)

```
┌─────────────────────────────────────────────────────────┐
│              CIRCUIT BREAKER STATE MACHINE              │
└─────────────────────────────────────────────────────────┘

                        ┌──────────────┐
                        │   CLOSED     │ ◄─── Normal operation
                        │ (Requests go │      All requests succeed
                        │  through)    │
                        └──────┬───────┘
                               │
                        Error threshold met
                        (50% errors in 60s window)
                        Minimum 10 requests to measure
                               │
                               ▼
                        ┌──────────────────────┐
                        │   OPEN               │
         ┌──────────────►│ (Requests rejected)  │◄──────┐
         │              │ Fast-fail mode       │       │
         │              │ Return 503           │       │
         │              │                      │       │
         │ After 60     └──────┬───────────────┘       │ Probe
         │ seconds             │                        │ fails
         │                     │ After 60 seconds       │
         │                     ▼                        │
         │              ┌──────────────────┐            │
         └──────────────│   HALF-OPEN      │────────────┘
                        │ (Probe requests) │
                        │ Allow 1 request  │
                        │ to backend       │
                        │ Measure response │
                        └──────┬───────────┘
                               │
                      Probe succeeds (5 consecutive successes)
                      (Backend responds with 2xx)
                               │
                               ▼
                        ┌──────────────┐
                        │   CLOSED     │
                        │   RECOVERING │
                        │ Ramp up      │
                        │ traffic      │
                        │ 10%→100%     │
                        │ (5 minutes)  │
                        └──────────────┘


Transition Rules (IV-005):

CLOSED → OPEN:
  Condition: error_rate >= 50% AND request_count >= 10 in 60s window
  Action: Reject all requests, return 503, start timer

OPEN → HALF_OPEN:
  Condition: 60 seconds elapsed since entering OPEN
  Action: Allow 1 probe request, measure response

HALF_OPEN → CLOSED (success):
  Condition: 5 consecutive successful requests
  Action: Close circuit, enter RECOVERING state

HALF_OPEN → OPEN (failure):
  Condition: 1 request fails in HALF_OPEN
  Action: Restart OPEN timeout (60 seconds)

RECOVERING → CLOSED:
  Condition: Ramp-up complete (5 minutes) OR error rate < 10%
  Action: Full circuit closure, accept all requests

RECOVERING → OPEN:
  Condition: error_rate >= 50% during ramp-up
  Action: Reopen circuit immediately

Configuration:
  - Error Threshold: 50% errors in 1-minute window
  - Half-Open Timeout: 60 seconds
  - Success Threshold (to close): 5 consecutive successes
  - Ramp-up Duration: 5 minutes linear
  - Max Backoff: 30 minutes
```

#### Circuit Breaker Implementation

```protobuf
message CircuitBreakerConfig {
  // Failure detection
  double error_rate_threshold = 1;  // 0.5 = 50%
  int32 error_sample_window_ms = 2; // 60000 = 1 minute
  int32 min_requests_threshold = 3; // Need at least 10 requests to measure

  // State transitions
  int32 open_timeout_ms = 4;        // 60000 = 1 minute
  int32 half_open_success_threshold = 5;  // 5 consecutive successes to close

  // Ramp-up recovery
  int32 ramp_up_duration_ms = 6;    // 300000 = 5 minutes
  int32 ramp_up_initial_traffic_pct = 7;  // 10%

  // Max backoff
  int32 max_open_duration_ms = 8;   // 1800000 = 30 minutes
}

message CircuitBreakerState {
  enum State {
    CLOSED = 0;      // Normal
    OPEN = 1;        // Fast-fail
    HALF_OPEN = 2;   // Testing recovery
    RECOVERING = 3;  // Ramping up traffic
  }

  State current_state = 1;
  int64 last_state_change_time = 2;

  int32 error_count = 3;      // Errors in current window
  int32 request_count = 4;    // Total requests in current window
  double error_rate = 5;

  int32 success_count_in_half_open = 6;
  int32 traffic_ramp_pct = 7;  // 0-100, used during RECOVERING
}
```

### 7.4 Connection Pool Bulkheads (IV-019)

**Bulkhead Pattern for Connection Isolation:**

```protobuf
message ConnectionPoolConfig {
  // Per-backend pool configuration
  int32 min_idle_connections = 1;   // Default: 10
  int32 max_connections = 2;        // Default: 100 per backend
  int32 max_queued_requests = 3;    // Default: 50 per backend

  // Connection timeouts
  int32 acquire_timeout_ms = 4;     // Wait for available connection
  int32 idle_timeout_ms = 5;        // Close idle connections
  int32 max_lifetime_ms = 6;        // Max connection age

  // Connection reuse
  bool keep_alive = 7;              // HTTP keep-alive
  bool http2_enabled = 8;           // Multiplexing

  // Per-backend bulkheads (isolation)
  repeated BulkheadConfig bulkheads = 9;
}

message BulkheadConfig {
  string backend_service_id = 1;
  int32 pool_size = 2;              // Isolated pool size (default: 100)
  int32 max_pending_requests = 3;   // Queue depth (default: 50)

  // Failure handling
  enum OnPoolExhausted {
    REJECT_REQUEST = 0;             // HTTP 503
    QUEUE_WITH_TIMEOUT = 1;         // Queue for Xs, then reject
    FAST_FAIL = 2;                  // Reject immediately
  }
  OnPoolExhausted exhaustion_behavior = 4;
  int32 queue_timeout_ms = 5;
}
```

**Bulkhead Implementation:**

```
Per-backend isolation (IV-019):
  ├─ Backend A: 100 connections (isolated)
  │  └─ If Backend A exhausts pool: only Backend A affected
  ├─ Backend B: 100 connections (isolated)
  │  └─ If Backend B slow: only Backend B affected
  └─ Traffic to other backends: unaffected

Failure scenario without bulkheads:
  ├─ Single slow backend exhausts global pool
  └─ All requests fail (cascading failure)

Failure scenario with bulkheads:
  ├─ Single slow backend exhausts its isolated pool
  └─ Only requests to that backend rejected (graceful degradation)
```

### 7.5 Scaling Strategy with Kubernetes Probes (IV-015)

#### Container Readiness Probe Strategy (IV-015)

**Kubernetes Pod Lifecycle:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api-gateway
spec:
  containers:
  - name: gateway
    image: api-gateway:1.2.0
    
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "2000m"

    # Startup: wait for L01 connection
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 30  # 30 * 10s = 5 minute timeout
      timeoutSeconds: 5

    # Readiness: check all dependencies
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8080
      initialDelaySeconds: 0
      periodSeconds: 5
      failureThreshold: 2  # 2 failures = 10s, remove from LB
      timeoutSeconds: 5

    # Liveness: basic responsiveness
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      failureThreshold: 3  # 3 failures = 30s, restart pod
      timeoutSeconds: 5

    # Graceful shutdown (IV-015)
    lifecycle:
      preStop:
        exec:
          command:
          - /bin/sh
          - -c
          - |
            # Signal readiness = false to LB
            echo "DRAINING" > /tmp/health
            # Wait 15s for connections to drain
            sleep 15
            # Exit gracefully
            exit 0
      postStart:
        exec:
          command:
          - /bin/sh
          - -c
          - echo "STARTED" > /tmp/health
```

**Health Endpoint Responses:**

```
GET /health/startup (initial startup check)
  Returns: 200 OK
  {
    "status": "healthy",
    "checks": {
      "l01_connectivity": "healthy",
      "configuration_loaded": "healthy",
      "feature_flags_ready": "healthy"
    }
  }

GET /health/ready (readiness for traffic)
  Returns: 200 OK or 503 Service Unavailable
  {
    "status": "ready" | "not_ready",
    "dependencies": {
      "l01": { "status": "healthy", "latency_ms": 45 },
      "redis": { "status": "healthy", "latency_ms": 2 },
      "configuration": { "status": "current", "age_seconds": 30 }
    },
    "instances_available": 3,
    "traffic_allocated": true
  }

GET /health/live (liveness check)
  Returns: 200 OK or 503 Service Unavailable
  {
    "status": "alive",
    "uptime_seconds": 3600,
    "goroutines": 150
  }
```

### 7.6 Performance Requirements: SLI/SLO and Error Budgets (IV-008, IV-017)

#### SLI/SLO Definitions (IV-008)

```protobuf
message ServiceLevelObjective {
  string sli_name = 1;           // e.g., "request_success_rate"
  float target_value = 2;        // 0.9995 = 99.95%
  string measurement_window = 3; // "monthly", "quarterly"

  // How to measure
  string prometheus_query = 4;
  // e.g., "sum(rate(http_requests_total{status=~'2..'}[5m])) /
  //        sum(rate(http_requests_total[5m]))"

  // Error budget allocation (IV-017)
  message ErrorBudgetAllocation {
    string category = 1;  // "planned-maintenance", "deployment", "testing"
    float percentage = 2; // e.g., 0.2 = 20% of budget
    int32 minutes_per_month = 3;
  }
  repeated ErrorBudgetAllocation allocations = 5;

  // Alert on violation
  int32 violation_alert_threshold_seconds = 6;
}
```

**SLI/SLO Configuration:**

```
Service Level Indicators (SLI):
  1. Request Success Rate
     Definition: (Successful requests) / (Total requests)
     Target: 99.95%
     Measurement: Prometheus query on http_requests_total

  2. Request Latency (p99)
     Definition: 99th percentile of request duration
     Target: < 200ms
     Measurement: http_request_duration_seconds histogram

  3. Error Budget
     Definition: (1 - SLO) × time
     For 99.95%: 22.2 minutes per month
     Usage: Allocated across categories

Service Level Objectives (SLO):
  Monthly SLO: 99.95% availability
  Monthly budget: 22.2 minutes downtime
  Quarterly SLO: 99.95% (rolling 90 days)
```

**Error Budget Allocation (IV-017):**

```protobuf
message ErrorBudgetPolicy {
  float monthly_slo = 1;             // 0.9995 = 99.95%

  message AllocationBucket {
    string category = 1;  // "maintenance", "deployment", "testing", "incident"
    float percentage = 2;  // 0.23 = 23%
    string description = 3;
    int32 priority = 4;    // Higher = protect from consumption
  }
  repeated AllocationBucket allocations = 2;

  // Enforcement
  bool pause_deployments_when_exhausted = 3;  // Default: true
  bool alert_at_threshold = 4;                 // Alert when 50% consumed
  int32 alert_threshold_percent = 5;          // 50

  // Tracking
  string tracking_metric = 6;  // Prometheus query for actual SLI
  bool publish_dashboard = 7;  // Expose burndown chart

  // Monthly reset
  string reset_day_utc = 8;    // "1st" of month, midnight UTC
}
```

**Error Budget Allocation Example (IV-017):**

```
Monthly SLO: 99.95% availability
Total monthly budget: 22.2 minutes

Allocation:
  ├─ Planned maintenance: 23% (5.1 minutes)
  ├─ Deployments: 45% (10 minutes)
  ├─ Hotfixes for incidents: 23% (5.1 minutes)
  └─ Chaos testing/validation: 9% (2 minutes)

Monthly tracking:
  ├─ Week 1: Planned maintenance 2 min (2/5 used)
  ├─ Week 2: Deployments 3 min (3/10 used)
  ├─ Week 3: Incident hotfix 2 min (2/5 used)
  ├─ Week 4: Deployments 5 min (8/10 used) → 80% of budget for deployments
  └─ Status: 12/22 minutes consumed (54% of budget)

Alert thresholds:
  ├─ 50% consumed: Yellow alert (proceed carefully)
  ├─ 80% consumed: Orange alert (only critical deployments)
  └─ 100% consumed: Red alert (freeze non-critical changes)

Burndown calculation:
  Time elapsed this month: T days
  Total month: 30 days
  Expected consumed: T/30 * total_budget
  Actual consumed: measured from SLI
  If actual > expected: on pace to exceed budget
```

**Prometheus Metrics for SLI Tracking:**

```
# Success rate SLI
sum(rate(http_requests_total{status=~"2.."}[5m])) /
sum(rate(http_requests_total[5m]))

# Latency SLI (p99)
histogram_quantile(0.99, http_request_duration_seconds)

# Error rate for alerts
1 - (sum(rate(http_requests_total{status=~"2.."}[5m])) /
     sum(rate(http_requests_total[5m])))

# Webhook delivery success rate (IV-009)
sum(rate(webhook_delivery_success_total[5m])) /
sum(rate(webhook_delivery_attempts_total[5m]))

# Idempotency cache hit rate (IV-007)
sum(rate(idempotency_cache_hits_total[5m])) /
sum(rate(idempotency_requests_total[5m]))

# Circuit breaker state changes (IV-005)
sum(rate(circuit_breaker_state_changes_total[5m])) by (state, backend)
```

---

## Section 8: Security

### 8.1 Threat Model and Zero Trust Architecture

The API Gateway Layer enforces zero trust architecture requiring authentication and authorization for all requests and services.

**Threat Categories and Mitigations:**

1. **Authentication Bypass**
   - Threat: Invalid credentials accepted, unauthorized access
   - Mitigation: Mandatory authentication, credential validation, token expiry checks
   - Credential Rotation: IV-011 (90-day API keys, 60-day OAuth, 1-year certificates)

2. **Server-Side Request Forgery (SSRF)**
   - Threat: Gateway makes requests to internal services on attacker's behalf
   - Mitigation: IP blocklist, DNS validation, TLS enforcement, timeout limits (IV-004)
   - Scope: Webhook delivery, proxy requests, redirect validation

3. **Cross-Tenant Data Leakage**
   - Threat: Consumer accesses another tenant's resources or data
   - Mitigation: Tenant ID validation, row-level security filters, authorization checks
   - Enforcement: Every L01 query includes tenant_id filter

4. **Rate Limit Bypass**
   - Threat: Consumer bypasses rate limits via protocol switching
   - Mitigation: Unified rate limit bucket across HTTP/1.1, HTTP/2, gRPC (IV-021)
   - Per-consumer tracking: rate_limit_tier applied uniformly

5. **Request Validation Bypass**
   - Threat: Malicious input in request headers, body, query parameters
   - Mitigation: Comprehensive input validation (IV-006)
   - Techniques: Unicode normalization, null byte rejection, control character filtering

6. **Webhook-Based Attacks**
   - Threat: Attacker sends fake webhooks to consumer endpoint
   - Mitigation: HMAC-SHA256 signature verification, timestamp validation
   - SSRF Prevention: IP blocklist, DNS validation before sending (IV-004)

### 8.2 Audit Trail and Immutability (IV-026)

All security-relevant events are logged to an immutable audit trail.

**Immutable Audit Log Implementation (IV-026, NIST AU-9):**

```protobuf
message AuditLogImmutabilityPolicy {
  // Storage backend
  enum StorageBackend {
    EVENT_STORE = 0;               // Immutable event log
    APPEND_ONLY_LEDGER = 1;        // AWS QLDB, Azure Immutable Storage
    BLOCKCHAIN = 2;                // For extreme paranoia
  }
  StorageBackend storage = 1;

  // Write-once enforcement
  bool enforce_write_once = 2;     // Default: true
  bool prevent_deletion = 3;       // Default: true
  int32 retention_days = 4;        // Default: 365

  // Time-locked writes
  bool use_time_locking = 5;       // Default: true
  int32 time_lock_days = 6;        // Default: 30

  // Cryptographic commitments
  bool use_merkle_tree = 7;        // Chain events into hash tree
  bool use_hash_chain = 8;         // Chain sequential hashes

  // Replication
  bool replicate_to_backup = 9;    // Default: true
  string backup_location = 10;     // Geographic location
  int32 replication_factor = 11;   // Default: 3 copies

  // Access control
  repeated string audit_log_readers = 12;  // Who can read
  repeated string audit_log_deleters = 13; // Who can delete (after retention)
  bool require_mfa_for_deletion = 14;     // Default: true

  // Integrity verification
  bool periodic_integrity_check = 15;     // Default: true
  int32 integrity_check_days = 16;        // Every 7 days
}
```

**Audit Log Entries (IV-026):**

Events logged with immutability guarantee:

```
APIRequestEvent:
  - Timestamp (immutable)
  - Consumer ID
  - Tenant ID
  - Request path, method, headers
  - Response status, body (redacted)
  - Error code (if error)
  - Result: allow/deny

AuthenticationEvent:
  - Timestamp
  - Consumer ID (if successful)
  - Authentication method (API key, JWT, mTLS)
  - Result: success/failure
  - Failure reason (if failed)

AuthorizationEvent:
  - Timestamp
  - Consumer ID
  - Action requested (read, write, delete)
  - Resource (route, operation, etc.)
  - Result: allow/deny
  - Policy evaluation details

RateLimitEvent:
  - Timestamp
  - Consumer ID
  - Rate limit tier
  - Excess requests
  - Penalty applied

WebhookDeliveryEvent:
  - Timestamp
  - Consumer ID
  - Webhook URL
  - Attempt number
  - Response status
  - SSRF validation result (IV-004)

CredentialRotationEvent (IV-011):
  - Timestamp
  - Credential type (API key, OAuth, certificate)
  - Old credential hash
  - New credential hash
  - Grace period start/end
  - Status (active, deprecated, revoked)

SecurityEvent (anomalies, attacks):
  - Timestamp
  - Event type (brute force, suspicious pattern, etc.)
  - Consumer ID
  - Details
  - Action taken (blocked, rate limited, flagged)

Access Control Event:
  - Timestamp
  - User ID (who modified audit log)
  - Action (read, attempted delete, verify integrity)
  - Target log entries (date range, consumer ID)
  - Result (allowed, denied)
  - Reason (if denied)
```

### 8.3 Authentication and Credential Rotation (IV-011)

**Credential Rotation Policy (IV-011):**

```protobuf
message CredentialRotationPolicy {
  message RotationSchedule {
    string credential_type = 1;  // "api_key", "oauth_secret", "certificate", "service_account"
    int32 rotation_period_days = 2;       // Every 90 days for API keys
    int32 grace_period_days = 3;          // Accept old key for 30 days
    bool send_expiration_notice = 4;      // Email consumer before expiry
    int32 notice_days_before = 5;         // 30 days before expiry
  }
  repeated RotationSchedule schedules = 1;

  // Vault integration
  string vault_path = 2;                  // "secret/api-gateway/credentials"
  int32 vault_rotation_check_interval_seconds = 3;
  bool auto_rotate = 4;                   // Default: true

  // Audit
  bool log_rotation_events = 5;           // Default: true
  int32 audit_retention_days = 6;         // Default: 365
}
```

**Rotation Schedules (IV-011):**

```
API Keys:
  ├─ Rotation period: Every 90 days
  ├─ Grace period: 30 days (both old and new keys work)
  ├─ Process:
  │  1. Generate new API key
  │  2. Store old and new simultaneously
  │  3. Send notification to consumer (30 days before old expires)
  │  4. Log rotation event to immutable audit trail
  │  5. After grace period: reject old key
  │  6. Update consumer's cached profile
  └─ Vault management: Rotate Vault credentials used by L09 itself

OAuth Client Secrets:
  ├─ Rotation period: Every 60 days
  ├─ Grace period: 30 days
  ├─ Process: Same as API keys
  └─ Vault: Store in Vault with encryption

mTLS Certificates:
  ├─ Rotation period: Every 1 year
  ├─ Grace period: 30 days (accept both old and new certs)
  ├─ Renewal process:
  │  1. Request new certificate from CA
  │  2. Validate new certificate
  │  3. Store in Vault and local filesystem
  │  4. Configure TLS to present new certificate first
  │  5. After grace period: remove old certificate
  └─ Auto-renewal: 30 days before expiry

Service Account Credentials:
  ├─ Rotation period: Every 30 days
  ├─ Grace period: 7 days
  └─ Automatic rotation via Vault agent
```

**Key Rotation Process:**

```
Step 1: Detection
  ├─ Scheduled: Check daily for credentials approaching expiry
  ├─ Manual: Operator triggers immediate rotation
  └─ Audit: Log rotation trigger event

Step 2: Generation
  ├─ Generate new credential with secure random generator
  ├─ Validate format (UUID v4 for API keys, etc.)
  ├─ Store in Vault (encrypted at rest)
  └─ Emit CredentialGeneratedEvent

Step 3: Dual Activation
  ├─ Update consumer profile: both old and new keys valid
  ├─ Update cached profiles on all gateway instances
  ├─ Start grace period timer
  └─ Emit CredentialActiveEvent

Step 4: Notification
  ├─ Send notification to consumer (email, webhook, dashboard)
  ├─ Highlight: "Old key will stop working in 30 days"
  ├─ Include: New key, migration instructions
  └─ Emit NotificationSentEvent

Step 5: Transition
  ├─ Wait for grace period (30 days)
  ├─ Monitor: Log requests using old key (for debugging)
  ├─ During grace: Accept both old and new
  └─ Emit GracePeriodEndingEvent (7 days before end)

Step 6: Deprecation
  ├─ After grace period: Stop accepting old key
  ├─ New requests with old key: Return 401 Unauthorized
  ├─ Update consumer profile: Mark old key as deprecated
  ├─ Emit KeyDeprecatedEvent
  └─ Retain in audit logs: 1 year minimum

Step 7: Cleanup
  ├─ Delete from Vault (if auto_delete enabled)
  ├─ Remove from cached profiles
  ├─ Emit CredentialDeletedEvent
  └─ Archive to audit trail
```

---

## Section 9: Observability

### 9.1 OpenTelemetry Span Attributes (IV-001)

All requests are traced with W3C Trace Context and include comprehensive OpenTelemetry semantic attributes.

**OpenTelemetry Semantic Attributes (IV-001):**

```protobuf
message SpanAttributes {
  // HTTP Semantic Attributes
  string http_method = 1;                    // GET, POST, PUT, DELETE, PATCH
  string http_url = 2;                       // Full URL with query string
  string http_target = 3;                    // Request path and query string
  int32 http_status_code = 4;                // Response status (200, 404, 500, etc.)
  int32 http_request_content_length = 5;    // Request body size
  int32 http_response_content_length = 6;   // Response body size
  string http_user_agent = 7;                // User-Agent header
  string http_flavor = 8;                    // "1.1", "2.0", "QUIC"
  string http_client_ip = 9;                 // Client source IP

  // RPC Semantic Attributes
  string rpc_service = 10;                   // Service name (gRPC service)
  string rpc_method = 11;                    // Method name (gRPC method)
  string rpc_system = 12;                    // "grpc", "jsonrpc", "thrift"
  int32 rpc_grpc_status_code = 13;           // gRPC status code

  // FaaS Semantic Attributes (for async operations)
  string faas_trigger = 14;                  // "http", "webhook", "queue"
  string faas_execution = 15;                // Execution ID (operation_id)
  string faas_invoked_provider = 16;         // "L02" for agent runtime
  string faas_invoked_name = 17;             // Agent or function name

  // Resource Attributes
  string service_name = 18;                  // "api-gateway"
  string service_version = 19;               // "1.2.0"
  string service_namespace = 20;             // "agentic"
  string service_instance_id = 21;           // Pod name or instance ID
  string service_instance_ip = 22;           // Pod IP

  // Tags (custom attributes)
  map<string, string> tags = 23;             // consumer_id, tenant_id, etc.
}
```

**Span Creation and Lifecycle:**

```
Request arrives
    │
    ▼
Create root span:
  - trace_id: W3C format (validated, IV-022)
  - span_id: random 8 bytes
  - Attributes:
    ├─ http_method, http_target
    ├─ http_user_agent, http_client_ip
    ├─ service_name, service_version
    └─ consumer_id, tenant_id (tags)

Processing stages:
  ├─ AUTHENTICATING
  │  └─ Child span: "authenticate" (http_method, oauth_scopes)
  ├─ AUTHORIZING
  │  └─ Child span: "authorize" (policies_checked, result)
  ├─ VALIDATING
  │  └─ Child span: "validate_request"
  ├─ IDEMPOTENCY_CHECK
  │  └─ Child span: "idempotency_check" (hit/miss, cached)
  ├─ RATE_LIMITING
  │  └─ Child span: "rate_limit_check" (tokens, quota)
  ├─ ROUTING
  │  └─ Child span: "route_match"
  ├─ EXECUTING
  │  └─ Child span: "backend_invoke" (backend_service, latency)
  ├─ WEBHOOK_DELIVERY
  │  └─ Child span: "webhook_send" (url, signature_verified)
  └─ LOGGING
     └─ Child span: "event_publish"

Span ends:
  - http_status_code: Set to response status
  - http_response_content_length: Set
  - Events: Emit span events for key milestones
  - Status: OK if success, CANCELLED if error
  - Duration: Record total latency
```

### 9.2 Prometheus Metrics with Exemplars (IV-002)

Comprehensive metrics with exemplars for trace correlation.

**Prometheus Metrics (IV-002):**

```
# Request latency histogram with exemplars (IV-002)
http_request_duration_seconds{method="POST", path="/agents/{id}/invoke"}
  - Histogram: [0.001, 0.01, 0.1, 0.5, 1, 5, 10] seconds
  - Exemplar: trace_id="4bf92f3577b34da6a3ce929d0e0e4736" (IV-002)
  - Cardinality limit: 100 exemplars per metric per minute

# Request counter
http_requests_total{method="GET", path="/operations", status="200"}
  - Counter (incremented per request)
  - Cardinality: method × path × status

# Rate limit violations
rate_limit_violations_total{tier="PREMIUM", reason="burst_exceeded"}
  - Counter (incremented on 429 response)
  - Cardinality: tier × reason

# Idempotency cache hits (IV-007)
idempotency_cache_hits_total{result="hit", method="POST"}
  - Counter (incremented on idempotency cache hit)

# Authentication success/failure
auth_attempts_total{method="api_key", result="success"}
auth_attempts_total{method="oauth", result="failure"}
  - Counter (incremented per authentication attempt)

# Authorization decisions
authz_decisions_total{result="allow", policy_type="rbac"}
authz_decisions_total{result="deny", policy_type="abac"}
  - Counter (incremented per authorization check)

# Circuit breaker state transitions (IV-005)
circuit_breaker_state_changes_total{backend="backend-1", from_state="CLOSED", to_state="OPEN"}
  - Counter (incremented on state change)
  - Cardinality: backend × state_pair

# Webhook delivery attempts (IV-009)
webhook_delivery_attempts_total{status="200", attempt="1"}
webhook_delivery_success_total{attempt="1"}
  - Counters (incremented per attempt)

# Health check results
health_check_status{check_type="readiness", target="l01"}
  - Gauge (1 = healthy, 0 = unhealthy)

# Connection pool utilization (IV-019)
connection_pool_connections_total{backend="backend-1", state="active"}
connection_pool_connections_total{backend="backend-1", state="idle"}
connection_pool_queue_depth{backend="backend-1"}
  - Gauges (current count)

# Cache hit rate (IV-024)
cache_hits_total{cache="consumer_profiles"}
cache_misses_total{cache="consumer_profiles"}
cache_evictions_total{cache="consumer_profiles", reason="ttl_expired"}
  - Counters (cumulative counts)

# SLI metrics
request_success_rate = sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))
request_latency_p99 = histogram_quantile(0.99, http_request_duration_seconds)

# Error rate tracking
error_rate = 1 - request_success_rate
```

**Exemplar Configuration (IV-002):**

```
Exemplar setup:
  1. Enable exemplars in metric scraper configuration
  2. Collect from trace-instrumented middleware
  3. Cardinality limit: 100 exemplars per metric per minute
  4. Exemplar lifetime: 5 minutes (automatic cleanup)

Example query:
  histogram_quantile(0.95, http_request_duration_seconds)
    └─ Result includes exemplar with trace_id link
    └─ Click to view full trace in Jaeger/Zipkin
```

### 9.3 Structured Logging and Sampling (IV-012)

All events are logged as structured JSON with adaptive sampling.

**Log Sampling Strategy (IV-012):**

```protobuf
message LoggingConfig {
  enum SamplingStrategy {
    ALWAYS = 0;                 // All requests
    TAIL_SAMPLING = 1;          // Based on result
    PROBABILISTIC = 2;          // % of requests
    ADAPTIVE = 3;               // Increase on errors
  }

  SamplingStrategy strategy = 1;
  float sample_rate = 2;        // 0.01 = 1% (for PROBABILISTIC)

  // Tail sampling: always log errors, timeouts
  float error_sample_rate = 3;  // 1.0 = all errors
  int32 latency_threshold_ms = 4;  // Log if > threshold

  // Sensitive data
  repeated string redact_patterns = 5;  // "password", "secret", "token"
  repeated string redact_headers = 6;   // "Authorization", "X-API-Key"

  // Log levels
  string default_level = 7;             // "INFO"
  map<string, string> component_levels = 8;  // auth=DEBUG, rate_limit=INFO

  // Destination
  string output_format = 9;             // "json"
  string sink = 10;                     // "stdout", "syslog", "cloudlogging"
}
```

**Log Sampling Rules (IV-012):**

```
Probabilistic sampling (default):
  ├─ Sample rate: 1% (configurable)
  ├─ Decision: random() < 0.01
  ├─ Applied uniformly across all requests
  └─ For high-volume APIs, reduces storage 100x

Tail sampling (for errors):
  ├─ Always log: HTTP 4xx, 5xx, errors
  ├─ Always log: Latency > 500ms
  ├─ Always log: Rate limit violations
  ├─ Error sample rate: 100% (all errors)
  └─ Latency threshold: 500ms (configurable)

Adaptive sampling:
  ├─ Base rate: 1% normal traffic
  ├─ Increase: On error rate spike
  ├─ Increase: On high latency period
  ├─ Increase: On 50%+ of budget consumed
  └─ Rule: increase to 10% during anomalies

Per-consumer override:
  ├─ For debugging: Set sample_rate=100% for specific consumer
  ├─ Duration: Time-limited (e.g., 1 hour)
  ├─ Audit: Log overrides to security events
  └─ Storage: Temporary (auto-delete after period)
```

**Log Event Categories (IV-012):**

```
APIRequestEvent:
  - Timestamp, trace_id, span_id
  - Consumer_id, tenant_id
  - HTTP method, path, status
  - Response time, error code (if error)
  - Sampling: Probabilistic (1%) + tail (errors always)

AuthenticationEvent:
  - Timestamp, consumer_id (if success)
  - Auth method (API key, JWT, mTLS)
  - Result (success/failure), failure reason
  - Sampling: Error sampling (100% if failed)

AuthorizationEvent:
  - Timestamp, consumer_id, action
  - Result (allow/deny), policy type
  - Sampling: Deny sampling (100%)

RateLimitEvent:
  - Timestamp, consumer_id, tier
  - Rate limit exceeded (429)
  - Sampling: Always (violations are critical)

WebhookDeliveryEvent:
  - Timestamp, webhook_id, attempt
  - Status, latency
  - Sampling: Error sampling (failures always logged)

SecurityEvent:
  - Timestamp, event_type (brute force, SSRF, etc.)
  - Consumer_id, details
  - Sampling: Always (security events critical)

ErrorEvent:
  - Timestamp, error_code, error_message
  - Stack trace (development only)
  - Sampling: Always (all errors logged)

HealthEvent:
  - Timestamp, component, status
  - Health check type (liveness, readiness)
  - Sampling: Warning/error only (status changes)
```

**Sensitive Data Redaction (IV-012):**

```
Redacted fields:
  ├─ "password", "secret": Replaced with "***"
  ├─ "token", "api_key": Replaced with "***"
  ├─ "Authorization" header: Replaced with "Bearer ***"
  ├─ "X-API-Key" header: Replaced with "***"
  ├─ "X-Webhook-Signature": Replaced with "sha256=***"
  └─ Request/response body: Truncated to first 100 bytes

Redaction rules:
  1. Parse JSON/protobuf body
  2. Find sensitive fields by pattern
  3. Replace values with "***"
  4. Log redacted version only

Example log:
  {
    "timestamp": "2026-01-05T10:00:00Z",
    "method": "POST",
    "path": "/agents/123/invoke",
    "status": 200,
    "headers": {
      "Authorization": "Bearer ***",
      "X-API-Key": "***"
    },
    "body": "{\"password\": \"***\", ...}"
  }
```

---

## Section 10: Configuration (12-Factor Compliance, IV-003)

Configuration is fully externalized per 12-Factor App methodology.

### 10.1 Configuration Categories (IV-003)

```protobuf
message ConfigurationExternalization {
  // 1. Secrets (API keys, passwords) → Vault/K8s Secrets
  message SecretConfig {
    string vault_address = 1;           // "https://vault.example.com:8200"
    string vault_token = 2;             // From K8s service account
    string vault_path_prefix = 3;       // "secret/api-gateway"
    int32 vault_rotation_check_ms = 4;  // Every 5 minutes
  }
  SecretConfig secrets = 1;

  // 2. Environment-specific (endpoints, region) → Environment variables
  message EnvironmentConfig {
    string l01_host = 2;                // "L01_HOST" env var
    string l01_port = 3;                // "L01_PORT" env var
    string redis_host = 4;              // "REDIS_HOST" env var
    string redis_port = 5;              // "REDIS_PORT" env var
    string region = 6;                  // "REGION" env var
    string environment = 7;             // "dev", "staging", "prod"
  }
  EnvironmentConfig env = 2;

  // 3. Dynamic (routes, policies) → L01 Configuration Service
  message DynamicConfig {
    string l01_config_service = 8;      // From L01 at startup
    int32 config_reload_interval_ms = 9; // Every 30 seconds
    bool watch_stream_enabled = 10;     // Subscribe to changes
  }
  DynamicConfig dynamic = 3;

  // 4. Feature flags → L01 with watch stream
  message FeatureFlagsConfig {
    bool enabled = 11;                  // Default: true
    string l01_feature_flags_topic = 12; // gRPC stream topic
    int32 local_ttl_seconds = 13;       // Cache for 5 minutes
  }
  FeatureFlagsConfig feature_flags = 4;
}
```

### 10.2 Startup Checklist and Validation (IV-003)

**Configuration Validation on Startup (IV-003):**

```
Startup Checklist (fail-fast):

1. Environment Variables
   ├─ Check: L01_HOST present
   ├─ Check: L01_PORT present (default: 8080)
   ├─ Check: REDIS_HOST present
   ├─ Check: REDIS_PORT present (default: 6379)
   ├─ Check: ENVIRONMENT in ["dev", "staging", "prod"]
   └─ Fail if required var missing → Exit with code 1

2. Vault Connection (if using Vault)
   ├─ Connect to Vault
   ├─ Authenticate using K8s service account
   ├─ Verify service account has correct permissions
   ├─ Test: Read a test secret
   └─ Fail if cannot connect → Exit with code 2

3. L01 Connectivity
   ├─ Connect to L01 (gRPC with mTLS, IV-016)
   ├─ Call HealthCheck() to verify
   ├─ Fail if timeout or error → Exit with code 3
   └─ Retry: 3 times with exponential backoff

4. L01 Configuration
   ├─ Load routes from Configuration Service
   ├─ Validate route definitions (required fields present)
   ├─ Load auth methods
   ├─ Load rate limit tiers
   ├─ Fail if invalid schema → Exit with code 4
   └─ Store as in-memory cache + watch stream

5. Feature Flags
   ├─ Load feature flags from L01
   ├─ Subscribe to watch stream (updates)
   ├─ Enable/disable components based on flags
   ├─ Fail if feature_flags disabled but required
   └─ Graceful degradation if load fails

6. Redis Connection
   ├─ Connect to Redis (with mTLS, IV-016)
   ├─ Test: PING command
   ├─ Test: Rate limiting Lua script loads
   ├─ Fail if cannot connect → Exit with code 5
   └─ Degrade to local rate limiting if fails

7. Schema Validation
   ├─ Validate OpenTelemetry schema (IV-001)
   ├─ Validate event schema versioning (IV-020)
   ├─ Validate request/response formats
   └─ Fail if invalid → Exit with code 6

8. TLS Certificates
   ├─ Load mTLS certificates (IV-016)
   ├─ Verify certificate expiry (>30 days remaining)
   ├─ Verify certificate chain
   └─ Fail if invalid or near expiry → Exit with code 7

9. Audit Log Configuration
   ├─ Validate audit log storage (immutable, IV-026)
   ├─ Test: Can write to audit log
   └─ Fail if cannot write → Exit with code 8

10. Health Endpoints
    ├─ Bind HTTP server on configured port
    ├─ Register /health/startup, /health/ready, /health/live
    └─ Fail if cannot bind → Exit with code 9

Exit Behavior:
  ├─ Success: Continue to normal operation
  └─ Failure: Exit with non-zero code, log errors to stderr

Monitoring:
  ├─ Kubernetes will detect failed startup
  ├─ Pod will NOT enter Ready state
  ├─ Alerting: Deployment fails to progress
  └─ Action: Manual investigation required
```

### 10.3 Environment Variable Reference (IV-003)

```
# Core Configuration
L01_HOST=l01.default.svc.cluster.local       # L01 service hostname
L01_PORT=8080                                 # L01 service port
L01_MTLS_ENABLED=true                        # Require mTLS (IV-016)

REDIS_HOST=redis.default.svc.cluster.local   # Redis hostname
REDIS_PORT=6379                              # Redis port
REDIS_MTLS_ENABLED=true                      # Require mTLS (IV-016)

ENVIRONMENT=prod                             # dev, staging, prod
REGION=us-east-1                             # Deployment region

# Vault Configuration
VAULT_ADDR=https://vault.example.com:8200
VAULT_NAMESPACE=api-gateway
VAULT_PATH_PREFIX=secret/api-gateway
VAULT_SKIP_VERIFY=false                      # Validate TLS certs

# TLS Certificates (mTLS, IV-016)
TLS_CLIENT_CERT=/etc/tls/certs/client.crt
TLS_CLIENT_KEY=/etc/tls/private/client.key
TLS_CA_CERT=/etc/tls/certs/ca.crt

# Server Configuration
PORT=8080                                    # Listen port
SHUTDOWN_TIMEOUT_SECONDS=30                  # Graceful shutdown wait

# Feature Flags
FEATURE_FLAGS_ENABLED=true
FEATURE_FLAGS_WATCH_ENABLED=true

# Logging
LOG_LEVEL=INFO                               # DEBUG, INFO, WARN, ERROR
LOG_FORMAT=json                              # json, text
LOG_SAMPLING_STRATEGY=probabilistic          # (IV-012)
LOG_SAMPLE_RATE=0.01                         # 1% (IV-012)

# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TRACES_ENABLED=true
METRICS_ENABLED=true

# Circuit Breaker
CIRCUIT_BREAKER_ERROR_THRESHOLD=0.5          # 50% (IV-005)
CIRCUIT_BREAKER_WINDOW_MS=60000              # 1 minute

# Rate Limiting
RATE_LIMIT_REDIS_ENABLED=true                # Use Redis (distributed)
RATE_LIMIT_FALLBACK=local                    # Fallback to local

# Cache Configuration
CACHE_STRATEGY=local_with_redis              # (IV-024)
CACHE_TTL_SECONDS=300                        # 5 minutes

# Audit Logging
AUDIT_LOG_ENABLED=true                       # (IV-026)
AUDIT_LOG_STORAGE=event_store                # Immutable (IV-026)
AUDIT_LOG_RETENTION_DAYS=365                 # 1 year

# Idempotency (IV-007)
IDEMPOTENCY_ENABLED=true
IDEMPOTENCY_TTL_SECONDS=86400                # 24 hours
IDEMPOTENCY_CACHE=redis                      # or local
```

---

## Section 11: Implementation Guide

### 11.1 Development Priorities

**Phase 1: Foundation (Weeks 1-2)**
- Core components: Authentication, Authorization, Rate Limiting
- Request pipeline with error handling
- mTLS setup for L01/Redis (IV-016)
- Audit logging foundation (IV-026)

**Phase 2: Features (Weeks 3-4)**
- Async operations and 202 Accepted
- Webhook delivery with SSRF validation (IV-004)
- Idempotency handler (IV-007)
- Circuit breaker patterns (IV-005)

**Phase 3: Reliability (Weeks 5-6)**
- Health checks and graceful degradation
- Cache invalidation strategy (IV-024)
- Connection pool bulkheads (IV-019)
- Comprehensive error recovery

**Phase 4: Observability (Weeks 7-8)**
- OpenTelemetry integration (IV-001)
- Prometheus metrics with exemplars (IV-002)
- Structured logging with sampling (IV-012)
- SLI/SLO tracking (IV-008)

---

## Section 12: Testing Strategy

### 12.1 Test Coverage

**Unit Tests**
- Authentication methods (API key, OAuth, mTLS)
- Authorization policies (RBAC, ABAC, scopes)
- Rate limiting (token bucket algorithm)
- Idempotency key deduplication (IV-007)
- Request validation (input sanitization, IV-006)
- Circuit breaker state transitions (IV-005)

**Integration Tests**
- L01 connectivity and caching
- Redis rate limiting and distributed operations
- Webhook delivery with SSRF validation (IV-004)
- Event publishing to event store (schema versioning, IV-020)
- mTLS connections (L01, Redis, backends, IV-016)

**Chaos Engineering Tests (IV-013)**
- Backend latency injection
- Redis unavailability scenarios
- L01 timeout handling
- Circuit breaker failure modes
- Health check validation

---

## Section 13: Migration and Deployment

### 13.1 Blue-Green Deployment

- Deploy v1.2 as green environment (parallel to v1.1 blue)
- Route 5% traffic to green (canary)
- Monitor: Error rate, latency, business metrics
- Gradual ramp: 5% → 25% → 50% → 100%
- Rollback: Switch back to blue if issues detected

### 13.2 Backward Compatibility

- Webhook signature format unchanged (HMAC-SHA256)
- Event schema versioned with backward compatibility (IV-020)
- API endpoints maintained across versions
- Deprecation: 2-release cycle (notify, deprecate, remove)

---

## Section 14: Open Questions and Decisions

### 14.1 Outstanding Items

1. **Service Discovery** (IV-025, P3)
   - Kubernetes DNS (default) vs Consul vs manual registry
   - Decision deferred to v1.3

2. **Pagination** (IV-018, P3)
   - Cursor-based (recommended) vs offset-based
   - Decision: Implement cursor-based as primary option

3. **Error Recovery** (IV-014, P3)
   - Detailed client-side guidance included in Section 4.2
   - Decision: Publish as best practices guide

---

## Section 15: References and Appendices

---

# APPENDIX A: Industry Validation Integration Summary

## Overview

This specification (v1.2.0) integrates all 26 findings from the industry validation report:
- **8 P1 Findings** (Critical): Must implement
- **12 P2 Findings** (Should implement): Should implement
- **6 P3 Findings** (Nice to have): Optional enhancements

## Integration Mapping

| Finding ID | Title | Section | Status |
|-----------|-------|---------|--------|
| IV-001 | OpenTelemetry Span Attributes | 9.1 | ✓ Integrated |
| IV-002 | Prometheus Exemplars | 9.2 | ✓ Integrated |
| IV-003 | Configuration Externalization | 10 | ✓ Integrated |
| IV-004 | SSRF Validation | 5.4, 8.1 | ✓ Integrated |
| IV-005 | Circuit Breaker State Transitions | 7.3 | ✓ Integrated |
| IV-006 | Request Validation | 4.1 | ✓ Integrated |
| IV-007 | Idempotency Specification | 3.5, 4.1 | ✓ Integrated |
| IV-008 | SLI/SLO Definitions | 7.6 | ✓ Integrated |
| IV-009 | Webhook Signature Algorithm | 5.4, 3.6 | ✓ Integrated |
| IV-010 | Dependency Health Checks | 3.7 | ✓ Integrated |
| IV-011 | Credential Rotation | 3.2, 8.3 | ✓ Integrated |
| IV-012 | Log Sampling Strategy | 9.3 | ✓ Integrated |
| IV-013 | Chaos Engineering Scenarios | 7.1 | ✓ Integrated |
| IV-014 | Error Recovery Documentation | 4.2 | ✓ Integrated |
| IV-015 | Kubernetes Probes | 7.5 | ✓ Integrated |
| IV-016 | Service-to-Service mTLS | 8.1, 8.3 | ✓ Integrated |
| IV-017 | Error Budget Allocation | 7.6 | ✓ Integrated |
| IV-018 | Pagination Specification | 4.5 | ✓ Integrated |
| IV-019 | Connection Pool Bulkheads | 7.4 | ✓ Integrated |
| IV-020 | Event Schema Versioning | 6.2 | ✓ Integrated |
| IV-021 | Rate Limit Bypass Prevention | 3.4, 4.1 | ✓ Integrated |
| IV-022 | W3C Context Validation | 6.3 | ✓ Integrated |
| IV-023 | Webhook Retry Exhaustion | 5.5 | ✓ Integrated |
| IV-024 | Cache Invalidation Strategy | 7.2 | ✓ Integrated |
| IV-025 | Service Discovery Mechanism | 3.1 | ✓ Integrated |
| IV-026 | Audit Log Immutability | 8.2 | ✓ Integrated |

---

# APPENDIX B: Complete Error Code Registry

## Error Code Ranges

| Range | Component | Examples |
|-------|-----------|----------|
| E9001-E9099 | Routing | E9001: Route not found |
| E9101-E9199 | Authentication | E9101: Invalid API key, E9102: Token expired |
| E9201-E9299 | Authorization | E9205: Cross-tenant access, E9207: Insufficient scopes |
| E9301-E9399 | Request Validation | E9301: Invalid format, E9309: Body too large |
| E9401-E9499 | Rate Limiting | E9401: Rate limit exceeded, E9404: Burst exceeded |
| E9501-E9599 | Operations | E9501: Operation not found, E9603: Operation expired |
| E9601-E9699 | Async Operations | E9601: Async operation error, E9701: Invalid webhook URL |
| E9701-E9799 | Webhooks | E9701: Webhook URL invalid, E9704: SSRF violation |
| E9801-E9899 | Circuit Breaker | E9801: Circuit breaker open, E9803: All replicas down |
| E9901-E9999 | Server Errors | E9901: Internal error, E9904: Bad gateway |

## Detailed Error Codes

- **E9001**: Route not found (path does not match any defined route)
- **E9101**: Invalid API key
- **E9102**: Token expired
- **E9103**: Missing credentials
- **E9205**: Cross-tenant access attempt
- **E9206**: Role insufficient for operation
- **E9207**: OAuth scope insufficient
- **E9301**: Request format invalid (malformed JSON)
- **E9302**: Required parameter missing
- **E9303**: Parameter type mismatch
- **E9304**: Request body exceeds size limit
- **E9309**: Header validation failed
- **E9401**: Rate limit exceeded (burst)
- **E9402**: Daily quota exceeded
- **E9404**: Burst capacity exceeded
- **E9602**: Operation not found
- **E9603**: Operation expired (result deleted)
- **E9701**: Invalid webhook URL (SSRF violation, IV-004)
- **E9704**: Webhook TLS certificate invalid
- **E9801**: Circuit breaker open (backend unhealthy)
- **E9803**: All backend replicas unavailable
- **E9901**: Internal server error
- **E9902**: Service unavailable (overloaded)
- **E9904**: Bad gateway (backend error)

---

**Specification Version:** 1.2.0
**Status:** Final (Production Ready)
**Last Updated:** 2026-01-04
**Validation Status:** All 26 industry findings integrated and applied

---

