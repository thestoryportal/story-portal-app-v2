# Story Portal Platform V2 - Architecture Documentation

**Version:** 2.0.0
**Last Updated:** 2026-01-18
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architectural Principles](#architectural-principles)
3. [Layer Architecture (L01-L12)](#layer-architecture)
4. [Service Communication](#service-communication)
5. [Data Flow](#data-flow)
6. [Port Allocation](#port-allocation)
7. [Infrastructure Components](#infrastructure-components)

---

## Overview

The Story Portal Platform V2 is a **12-layer microservices architecture** designed for building, deploying, and managing AI-powered agentic applications. Each layer provides specific functionality and communicates via HTTP/REST APIs.

### Key Characteristics

- **HTTP-First Design**: All layers expose RESTful APIs (no CLI entry points by design)
- **Microservices Architecture**: Each layer is an independent containerized service
- **Horizontal Scalability**: Stateless services can scale independently
- **Health-Check Driven**: All services expose standardized health endpoints
- **Observability Built-In**: Prometheus metrics, structured logging, distributed tracing

---

## Architectural Principles

### 1. Separation of Concerns
Each layer has a single, well-defined responsibility. Layers do not bypass the abstraction hierarchy.

### 2. HTTP-Only Communication
- No CLI interfaces (intentional design decision)
- All inter-service communication via HTTP/REST
- External interaction via API Gateway (L09) or Human Interface (L10)

### 3. Statelessness Where Possible
- Application state in PostgreSQL (persistent)
- Session/cache state in Redis (ephemeral)
- Service processes are stateless and horizontally scalable

### 4. Progressive Disclosure
- Simple operations use simple endpoints
- Complex operations composed from simple primitives
- API versioning for backward compatibility

---

## Layer Architecture

### L01: Data Layer (Port 8001)
**Purpose:** Persistent data management and database operations

**Responsibilities:**
- PostgreSQL database access and ORM (SQLAlchemy)
- CRUD operations for core entities (agents, tasks, runs, artifacts)
- Schema migrations and data integrity
- Query optimization and indexing

**Technology Stack:**
- FastAPI + SQLAlchemy
- PostgreSQL 16
- Alembic for migrations

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe (DB connectivity)
- `POST /agents` - Create agent
- `GET /agents/{id}` - Retrieve agent
- `POST /tasks` - Create task
- `GET /runs/{id}` - Get run status

---

### L02: Runtime Layer (Port 8002)
**Purpose:** Agent execution environment and process management

**Responsibilities:**
- Agent process lifecycle (spawn, monitor, terminate)
- Resource allocation and sandboxing
- Execution context management
- Output capture and streaming

**Technology Stack:**
- FastAPI + asyncio
- Docker SDK for containerized agents
- Process isolation (cgroups, namespaces)

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `POST /execute` - Execute agent
- `GET /status/{run_id}` - Check execution status
- `POST /terminate/{run_id}` - Stop execution

---

### L03: Tool Execution Layer (Port 8003)
**Purpose:** Tool and function execution for agents

**Responsibilities:**
- Tool registry and discovery
- Function invocation with parameter validation
- Result serialization and error handling
- Security sandboxing for tool execution

**Technology Stack:**
- FastAPI + Pydantic
- Tool SDK integration
- Sandboxed execution environment

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `GET /tools` - List available tools
- `POST /execute/{tool_name}` - Execute tool
- `GET /tools/{name}/schema` - Get tool schema

---

### L04: Model Gateway Layer (Port 8004)
**Purpose:** LLM abstraction and unified inference API

**Responsibilities:**
- Multi-model support (OpenAI, Anthropic, local Ollama)
- Request routing and load balancing
- Token counting and rate limiting
- Response streaming and caching

**Technology Stack:**
- FastAPI
- LiteLLM for model abstraction
- Redis for caching
- Ollama for local models

**Supported Models:**
- GPT-4, GPT-3.5 (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- llama3.2, gemma2, qwen2.5, deepseek-coder (Ollama local)

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `POST /chat/completions` - Chat completion (OpenAI-compatible)
- `POST /embeddings` - Generate embeddings
- `GET /models` - List available models

---

### L05: Planning Layer (Port 8005)
**Purpose:** Agent planning and task decomposition

**Responsibilities:**
- Task breakdown into subtasks
- Dependency graph construction
- Planning strategy selection
- Plan validation and optimization

**Technology Stack:**
- FastAPI
- Graph algorithms (NetworkX)
- LLM-based planning (via L04)

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `POST /plan` - Generate execution plan
- `GET /plans/{id}` - Retrieve plan
- `POST /validate` - Validate plan feasibility

---

### L06: Evaluation Layer (Port 8006)
**Purpose:** Agent performance evaluation and quality assessment

**Responsibilities:**
- Output quality scoring
- Success/failure determination
- Metric collection and aggregation
- A/B testing infrastructure

**Technology Stack:**
- FastAPI
- Metric computation libraries
- LLM-as-judge evaluation

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `POST /evaluate` - Evaluate agent output
- `GET /metrics/{run_id}` - Get run metrics
- `POST /judge` - LLM-based quality assessment

---

### L07: Learning Layer (Port 8007)
**Purpose:** Agent improvement through learning and adaptation

**Responsibilities:**
- Experience replay and memory
- Performance trend analysis
- Prompt optimization suggestions
- Agent behavior tuning

**Technology Stack:**
- FastAPI
- Time-series analysis
- Vector database for memory (Redis Vector)

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `POST /learn` - Process learning from run
- `GET /insights/{agent_id}` - Get improvement insights
- `POST /optimize` - Suggest optimizations

---

### L08: Reserved (Future Microservices Orchestration)
**Status:** ⚠️ **INTENTIONALLY RESERVED** - Not implemented in V2.0

**Planned Purpose:** Advanced microservices orchestration and service mesh

**Why Reserved:**
The L08 layer is intentionally reserved for future implementation of advanced orchestration capabilities that are not yet required in V2.0 but are planned for future releases.

**Planned Responsibilities (V3.0+):**
- Service mesh management (Istio/Linkerd integration)
- Advanced traffic routing (canary, blue-green deployments)
- Circuit breaker and retry logic
- Distributed tracing coordination
- Cross-service transaction management

**Design Decision:**
Rather than leaving a confusing gap in the layer sequence (L01-L07, then L09+), we explicitly reserve L08 to maintain architectural clarity and allow for future expansion without renumbering existing layers.

**Current Workaround:**
Orchestration functionality in V2.0 is handled by:
- L09 API Gateway for request routing
- L12 Service Hub for service discovery
- Docker Compose for container orchestration

**Migration Path:**
When L08 is implemented in future versions:
1. Existing L09-L12 will remain unchanged (no renumbering)
2. L08 will be inserted as a new layer between L07 and L09
3. Orchestration logic will migrate from L09/L12 to L08
4. Backward compatibility maintained through API versioning

---

### L09: API Gateway (Port 8009)
**Purpose:** External API access point and request routing

**Responsibilities:**
- Authentication and authorization (JWT tokens)
- Request validation and rate limiting
- API versioning and routing
- Response transformation and caching

**Technology Stack:**
- FastAPI
- JWT authentication
- Redis for rate limiting
- API key management

**Key Endpoints:**
- `GET /health/live` - Liveness probe (public)
- `POST /auth/token` - Obtain JWT token
- `GET /api/v1/*` - Versioned API routes
- All proxied endpoints from L01-L07

---

### L10: Human Interface Layer (Port 8010)
**Purpose:** Web UI and human interaction

**Responsibilities:**
- Web dashboard serving
- Real-time status updates (WebSocket)
- User session management
- Interactive agent control

**Technology Stack:**
- FastAPI + Jinja2 templates
- WebSocket for real-time updates
- Static file serving
- Session management

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `GET /` - Dashboard homepage
- `GET /agents` - Agent management UI
- `WS /ws` - WebSocket for real-time updates

---

### L11: Integration Layer (Port 8011)
**Purpose:** External service integrations and webhooks

**Responsibilities:**
- Third-party API integrations
- Webhook handling and event forwarding
- OAuth flow management
- External data source connectors

**Technology Stack:**
- FastAPI
- OAuth2 client library
- Webhook signature verification
- Async HTTP client (httpx)

**Key Endpoints:**
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /health/detailed` - Detailed diagnostics
- `POST /webhooks/{service}` - Webhook receiver
- `GET /integrations` - List configured integrations

---

### L12: Service Hub (Port 8012)
**Purpose:** Service discovery and internal coordination

**Responsibilities:**
- Service registry and health monitoring
- Internal service-to-service communication coordination
- Configuration distribution
- Centralized logging aggregation

**Technology Stack:**
- FastAPI
- Service discovery (Consul-like functionality)
- Health check aggregation
- Configuration management

**Key Endpoints:**
- `GET /health` - Liveness probe (L12 uses /health, not /health/live)
- `GET /services` - List registered services
- `POST /register` - Register service
- `GET /config/{service}` - Get service configuration

---

## Service Communication

### Request Flow (External → Internal)

```
User/Client
    ↓
L09 API Gateway (authentication, rate limiting)
    ↓
[L01-L07] Application Layers (business logic)
    ↓
L01 Data Layer (persistence)
    ↓
PostgreSQL / Redis
```

### Service-to-Service Communication

- **Synchronous:** Direct HTTP calls between layers
- **Asynchronous:** Event publishing via L11 Integration (webhooks)
- **Discovery:** L12 Service Hub provides service registry

### Authentication Flow

1. Client requests token from `L09:/auth/token`
2. L09 validates credentials against L01
3. JWT token issued with role/permissions
4. Subsequent requests include `Authorization: Bearer <token>`
5. L09 validates token and forwards to backend layers

---

## Data Flow

### Agent Execution Flow

```
L10 (UI) → L09 (Gateway) → L02 (Runtime)
                              ↓
                         L05 (Planning) → L04 (Models)
                              ↓
                         L03 (Tool Execution)
                              ↓
                         L06 (Evaluation)
                              ↓
                         L07 (Learning)
                              ↓
                         L01 (Data) → PostgreSQL
```

### Data Persistence

- **PostgreSQL (L01):** Agents, tasks, runs, artifacts, users
- **Redis:** Sessions, cache, rate limit counters, pub/sub
- **Object Storage (planned):** Large artifacts, logs, media

---

## Port Allocation

### Application Layers
- **8001** - L01 Data Layer
- **8002** - L02 Runtime Layer
- **8003** - L03 Tool Execution
- **8004** - L04 Model Gateway
- **8005** - L05 Planning
- **8006** - L06 Evaluation
- **8007** - L07 Learning
- **8008** - L08 Reserved (Not Used)
- **8009** - L09 API Gateway
- **8010** - L10 Human Interface
- **8011** - L11 Integration
- **8012** - L12 Service Hub

### Infrastructure Components
- **5432** - PostgreSQL
- **6379** - Redis
- **11434** - Ollama (LLM inference)
- **9090** - Prometheus (metrics)
- **3000** - Grafana (monitoring dashboard)

### Monitoring Exporters
- **9100** - Node Exporter (host metrics)
- **9121** - Redis Exporter
- **9187** - PostgreSQL Exporter
- **8080** - cAdvisor (container metrics)

---

## Infrastructure Components

### PostgreSQL (agentic-postgres)
- **Version:** 16
- **Port:** 5432
- **Database:** agentic_platform
- **Purpose:** Primary persistent data store
- **Backup Strategy:** Daily automated backups (planned)

### Redis (agentic-redis)
- **Version:** 7
- **Port:** 6379
- **Purpose:** Session store, cache, rate limiting, pub/sub
- **Persistence:** RDB snapshots + AOF

### Ollama (Host Service)
- **Port:** 11434
- **Purpose:** Local LLM inference
- **Models:** llama3.2, gemma2, qwen2.5, deepseek-coder, llava-llama3
- **Deployment:** Host service (not containerized in V2.0)

### Prometheus (agentic-prometheus)
- **Port:** 9090
- **Purpose:** Metrics collection and storage
- **Scrape Interval:** 15s
- **Retention:** 15 days

### Grafana (agentic-grafana)
- **Port:** 3000
- **Purpose:** Metrics visualization and dashboards
- **Datasource:** Prometheus
- **Dashboards:** System metrics, application metrics, business KPIs

---

## Health Check Standardization

All layers expose standardized health check endpoints:

### Public Endpoints (No Authentication Required)

**`GET /health`**
- Basic health status
- Returns: `{"status": "healthy", "service": "l01-data-layer", "version": "2.0.0"}`

**`GET /health/live`**
- Liveness probe (for Kubernetes)
- Returns 200 if service is running

**`GET /health/ready`**
- Readiness probe (for Kubernetes)
- Returns 200 if service is ready to accept traffic
- Checks dependencies (DB, Redis, upstream services)

### Protected Endpoints (Authentication Required)

**`GET /health/detailed`**
- Comprehensive diagnostics
- Dependency status
- Resource utilization
- Recent errors

---

## Design Philosophy: HTTP-Only Architecture

### Why No CLI Entry Points?

The Story Portal Platform V2 is intentionally designed as an **HTTP-first** system:

1. **Microservices Nature:** Each layer is a service, not a standalone application
2. **API-Driven:** All functionality exposed via REST APIs
3. **Programmatic Access:** Integration via HTTP clients, not shell scripts
4. **Cloud-Native:** Designed for containerized, orchestrated deployment

### How to Interact with the Platform

**For Development:**
```bash
# Direct HTTP requests
curl http://localhost:8001/health/live
curl -X POST http://localhost:8002/execute -d '{"agent_id": "123"}'

# Using httpie (cleaner syntax)
http GET localhost:8001/agents
http POST localhost:8002/execute agent_id=123
```

**For Production:**
- Use L09 API Gateway: `https://api.example.com/v1/`
- Use L10 Web Dashboard: `https://portal.example.com/`
- Use client libraries (Python, JavaScript, etc.)

**Future CLI (Planned V2.1+):**
A CLI tool may be added in future versions, but it will be a thin wrapper around HTTP endpoints, not a replacement for the HTTP-first design.

---

## Deployment Considerations

### Development Environment
- Docker Compose for local orchestration
- All services on localhost with different ports
- Shared Docker network for inter-service communication

### Production Environment (Planned)
- Kubernetes deployment with Helm charts
- Service mesh (Istio/Linkerd) via L08 (future)
- Horizontal pod autoscaling based on metrics
- Persistent volumes for PostgreSQL and Redis
- Ingress controller for external access

### Scaling Strategy
- **Stateless Layers (L02-L07, L09-L11):** Horizontal scaling with load balancing
- **Stateful Layers (L01):** Database connection pooling, read replicas
- **Infrastructure (PostgreSQL, Redis):** Master-replica for HA

---

## Security Architecture

### Authentication & Authorization
- JWT tokens issued by L09 API Gateway
- Role-Based Access Control (RBAC)
- API key support for service-to-service auth

### Network Security
- Internal service mesh network (Docker network)
- Only L09 (Gateway) and L10 (UI) exposed externally
- TLS termination at L09 (production)

### Data Security
- Encrypted database connections (TLS)
- Redis AUTH password protection
- Secrets management via environment variables (Docker secrets in prod)

---

## Observability

### Metrics
- Prometheus scrapes all services every 15s
- Custom business metrics exposed by each layer
- Infrastructure metrics via exporters

### Logging
- Structured JSON logs
- Centralized collection via L12 Service Hub (planned)
- Log levels: DEBUG, INFO, WARNING, ERROR

### Tracing
- Distributed tracing support (OpenTelemetry ready)
- Trace IDs propagated across service boundaries

---

## Future Roadmap

### V2.1 (Q2 2026)
- CLI wrapper tool for HTTP endpoints
- Enhanced L11 integrations (Slack, GitHub, Jira)
- Advanced caching strategies

### V3.0 (Q4 2026)
- **L08 Service Mesh Layer** implementation
- Kubernetes-native deployment
- Multi-region support
- Advanced orchestration features

### V3.5 (Q1 2027)
- Agent marketplace
- Plugin system for custom layers
- Multi-tenancy support

---

## Appendix: Layer Dependency Matrix

| Layer | Depends On | Used By |
|-------|-----------|---------|
| L01 Data | PostgreSQL, Redis | L02, L05, L06, L07, L09 |
| L02 Runtime | L01, L04, L05 | L09, L10 |
| L03 Tool Exec | L01 | L02 |
| L04 Model Gateway | Ollama, OpenAI, Anthropic | L02, L05, L06, L07 |
| L05 Planning | L01, L04 | L02 |
| L06 Evaluation | L01, L04 | L02, L07 |
| L07 Learning | L01, L06 | L02 |
| L08 Reserved | - | - |
| L09 API Gateway | L01-L07 | External clients |
| L10 Human Interface | L09 | Users (web browsers) |
| L11 Integration | L01, L09 | External services |
| L12 Service Hub | All layers | All layers (discovery) |

---

## Questions or Contributions

For questions about the architecture, please refer to:
- Development Guide: `docs/DEVELOPMENT.md`
- Deployment Guide: `docs/DEPLOYMENT.md`
- API Documentation: `docs/API.md`

For contributions, see `CONTRIBUTING.md` in the project root.

---

**Document Version:** 1.0.0
**Author:** Story Portal Platform Team
**Last Review:** 2026-01-18
