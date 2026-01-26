# Story Portal Platform - Layer Architecture Summary

## Overview

The Story Portal Platform is a **14-layer autonomous AI agent system** designed for local development and cloud scalability. Each layer provides specialized functionality for agent execution, planning, evaluation, and learning.

| Status | Layers |
|--------|--------|
| **Production Ready** | L01, L09, L12 |
| **Implementation Complete** | L02-L07, L10-L11, L13-L14 |
| **Planned** | L00, L08 |

---

## L00: Secrets Management (Planned)
**Port:** 8000 | **Status:** Planned

### Purpose
Centralized secrets, environment configuration, and vault integration.

### Planned Features
- Secret rotation and versioning
- Vault integration (HashiCorp Vault, AWS Secrets Manager)
- Configuration management with environment overrides
- Audit logging for all secret access

---

## L01: Data Layer
**Port:** 8001 | **Status:** Production Ready

### Purpose
Foundation layer providing persistent storage, event sourcing, and real-time pub/sub distribution. All platform state changes flow through L01.

### Services
| Service | Description |
|---------|-------------|
| AgentRegistry | Agent metadata and lifecycle tracking |
| GoalStore | Goal/objective persistence |
| PlanStore | Execution plan storage with versioning |
| EventStore | Event sourcing with audit trail and replay |
| SessionService | Session lifecycle management |
| DocumentStore | Knowledge document persistence |
| FeedbackStore | User feedback and correction storage |
| ConfigStore | Configuration key-value store |
| DatasetService | Training dataset CRUD and splits |
| EvaluationStore | Evaluation results and metrics |
| ToolRegistry | Tool definitions and schemas |

### Key Features
- Event Sourcing with CQRS pattern
- PostgreSQL 15+ backend with 15+ core tables
- Redis Pub/Sub for real-time events
- Bearer token authentication
- Pydantic schema validation

### Tools & APIs
```
GET/POST  /api/agents, /api/goals, /api/plans, /api/events, /api/sessions
GET       /health/live, /health/ready
```

### Dependencies
PostgreSQL 15+, Redis 7+, FastAPI, SQLAlchemy

---

## L02: Runtime Layer
**Port:** 8002 | **Status:** Phase 1 Complete

### Purpose
Manages agent lifecycle (spawn, suspend, resume, terminate) with pluggable runtime backends.

### Services
| Service | Description |
|---------|-------------|
| AgentRuntime | Main orchestrator for spawn/terminate/suspend/resume |
| LifecycleManager | Agent state machine management |
| SandboxManager | Trust-level-based sandbox selection |
| LocalRuntime | Docker-based local implementation |
| KubernetesRuntime | Production K8s deployment (stub) |

### Key Features
- Trust-Level Sandboxing: TRUSTED → STANDARD → UNTRUSTED → CONFIDENTIAL
- State Machine: PENDING → READY → EXECUTING → COMPLETED/FAILED/BLOCKED
- Per-agent CPU, memory, and token budgets
- Network policy isolation

### Tools & APIs
```
POST  /spawn, /terminate, /suspend, /resume
GET   /state/{agent_id}, /health/{agent_id}
```

### Dependencies
L01 Data Layer, Docker, Kubernetes (production)

---

## L03: Tool Execution Layer
**Port:** 8003 | **Status:** Implementation Complete

### Purpose
Secure, isolated execution of tools invoked by agents with permission enforcement and MCP integration.

### Services
| Service | Description |
|---------|-------------|
| ToolRegistry | PostgreSQL + pgvector catalog with semantic search |
| ToolExecutor | Tool execution with timeout/concurrency limits |
| ToolSandbox | Process isolation and resource limits |
| ResultCache | Redis-backed caching with TTL |
| ToolComposer | DAG-based sequential/parallel execution |
| MCPToolBridge | MCP document and state server integration |

### Key Features
- Semantic search via Ollama embeddings
- Nested sandbox inheriting agent constraints
- DAG workflow composition
- Idempotency key support

### Tools & APIs
```
POST  /tools/{tool_id}/invoke
GET   /tools, /tools/search, /tools/{tool_id}
POST  /tools/cache/clear
```

### Dependencies
L01, L02, PostgreSQL + pgvector, Redis, Ollama

---

## L04: Model Gateway Layer
**Port:** 8004 | **Status:** Implementation Complete

### Purpose
Unified interface for multiple LLM providers with intelligent routing, caching, and failover.

### Services
| Service | Description |
|---------|-------------|
| ModelRegistry | Model catalog with capabilities and pricing |
| LLMRouter | Capability-based model selection |
| SemanticCache | Embedding-based caching (85% similarity) |
| RateLimiter | Token bucket per agent/provider |
| CircuitBreaker | 4-state failover mechanism |
| RequestQueue | Priority queue for traffic spikes |
| ProviderAdapters | Anthropic, OpenAI, Azure, Google, Ollama |

### Key Features
- Multi-provider failover
- Semantic caching reduces API calls
- Cost tracking and budget enforcement
- Circuit breaker: CLOSED → OPEN → HALF_OPEN → RECOVERING

### Tools & APIs
```
POST  /infer, /route
GET   /models, /cache/stats
POST  /cache/clear
```

### Dependencies
L01, Redis, Anthropic/OpenAI/Azure/Google APIs, Ollama

---

## L05: Planning Layer
**Port:** 8005 | **Status:** Implementation Complete

### Purpose
Transforms high-level goals into executable task plans with dependency resolution and context injection.

### Services
| Service | Description |
|---------|-------------|
| GoalDecomposer | Goal → task plan (cache → template → LLM) |
| DependencyResolver | Cycle detection, topological sort |
| PlanValidator | Syntax, semantic, feasibility, security validation |
| TaskOrchestrator | Execution state machine with parallelism |
| ContextInjector | Token-budgeted input assembly |
| ResourceEstimator | Token, cost, and budget estimation |
| AgentAssigner | Capability-based task assignment |
| PlanCache | Two-level cache (LRU + Redis) |

### Key Features
- Hybrid decomposition: cache → template → LLM fallback
- Parallel task scheduling
- HMAC-SHA256 plan signing
- Critical path computation

### Tools & APIs
```
POST  /plans/create, /plans/execute, /plans/{plan_id}/validate
GET   /plans/{plan_id}, /tasks/{task_id}/status
```

### Dependencies
L01, L02, L03, L04, L11, Redis

---

## L06: Evaluation Layer
**Port:** 8006 | **Status:** Implementation Complete

### Purpose
Continuous quality measurement through multi-dimensional scoring, anomaly detection, and compliance validation.

### Services
| Service | Description |
|---------|-------------|
| EventValidator | CloudEvents schema validation |
| MetricsEngine | Time-series aggregation and correlation |
| QualityScorer | 5-dimensional scoring (0-100 scale) |
| AnomalyDetector | Statistical z-score detection |
| ComplianceValidator | Policy enforcement |
| AlertManager | Multi-channel notifications |
| AuditLogger | Immutable audit trail |

### Key Features
- **5 Dimensions:** Accuracy, Latency, Cost, Reliability, Compliance
- **Assessment Levels:** Good (≥80), Warning (60-79), Critical (<60)
- Statistical anomaly detection
- SLA monitoring and reporting

### Tools & APIs
```
GET  /metrics/query, /quality-scores, /anomalies
GET  /compliance/violations, /sla/status
GET/PUT /config
```

### Dependencies
L01, L02, L04, L05, Redis, PostgreSQL

---

## L07: Learning Layer
**Port:** 8007 | **Status:** Implementation Complete (Simulation Mode)

### Purpose
Continuous improvement through training data extraction, fine-tuning, and RLHF feedback loops.

### Services
| Service | Description |
|---------|-------------|
| TrainingDataExtractor | Extracts examples from L02/L05/L06 events |
| ExampleQualityFilter | Multi-criteria filtering (70/100 minimum) |
| DatasetCurator | Versioned datasets with train/val/test splits |
| FineTuningEngine | Training orchestration (simulated/HuggingFace) |
| RLHFEngine | Reinforcement learning from human feedback |
| ModelValidator | 5-stage validation gates |
| ModelRegistry | DEVELOPMENT → STAGING → PRODUCTION lifecycle |

### Key Features
- Automatic training data extraction
- Quality filtering with anomaly detection
- Semantic versioning with lineage tracking
- Production model signing and checksums

### Tools & APIs
```
POST  /datasets/create, /models/train, /models/{id}/validate, /models/{id}/deploy
GET   /models/{model_id}, /jobs/{job_id}
```

### Dependencies
L01, L04, L06, Redis, HuggingFace (production)

---

## L08: Supervision Layer (Planned)
**Port:** 8008 | **Status:** Planned

### Purpose
Policy enforcement, ABAC, and human oversight.

### Planned Features
- Attribute-based access control (ABAC)
- Policy evaluation engine
- Audit and compliance checking
- Human override capabilities
- Real-time policy enforcement

---

## L09: API Gateway Layer
**Port:** 8009 | **Status:** Production Ready

### Purpose
Primary entry point for all external API requests with authentication, authorization, and rate limiting.

### Services
| Service | Description |
|---------|-------------|
| AuthenticationHandler | API key, OAuth 2.0, mTLS |
| AuthorizationEngine | RBAC (ADMIN, DEVELOPER, GUEST) |
| RateLimiter | Token bucket (STANDARD/PREMIUM/ENTERPRISE) |
| IdempotencyHandler | 24-hour deduplication |
| RequestValidator | Content validation, security checks |
| CircuitBreaker | 4-state failover |
| AsyncOperationHandler | 202 Accepted with webhooks |

### Key Features
- **Rate Limiting Tiers:** STANDARD (100 rps), PREMIUM (1k rps), ENTERPRISE (10k rps)
- SSRF prevention with private IP blocking
- Multi-tenant isolation
- HMAC-SHA256 signed webhooks

### Tools & APIs
```
ANY  /api/*
GET  /health/live, /health/ready, /health/detailed, /health/startup
```

### Dependencies
L01, L02, Redis, PostgreSQL

---

## L10: Human Interface Layer
**Port:** 8010 | **Status:** Implementation Complete

### Purpose
Real-time dashboard, control operations, and human-in-the-loop workflows.

### Services
| Service | Description |
|---------|-------------|
| DashboardService | Real-time state and metrics aggregation |
| ControlService | Pause/resume/adjust with distributed locking |
| WebSocketGateway | Push updates via Redis pub/sub (<500ms) |
| EventService | Event history with filtering |
| AlertService | Threshold-based alerting |
| AuditService | Control action audit trail |
| CostService | Usage attribution and tracking |

### Key Features
- Hybrid pull + push architecture
- Redis distributed locking (SET NX EX)
- 24-hour idempotency cache
- Graceful degradation on dependency failure

### Tools & APIs
```
GET   /dashboard/overview, /dashboard/agent/{id}
POST  /control/pause, /control/resume, /control/emergency_stop, /control/adjust_quota
GET   /events, /alerts, /audit, /costs/summary
WS    /ws/events
```

### Dependencies
L02, L06, L11, Redis, PostgreSQL

---

## L11: Integration Layer
**Port:** 8011 | **Status:** Implementation Complete

### Purpose
Communication backbone enabling cross-layer orchestration, event distribution, and distributed tracing.

### Services
| Service | Description |
|---------|-------------|
| ServiceRegistry | Layer discovery with health tracking |
| EventBus | Redis Pub/Sub with topic routing |
| CircuitBreaker | Per-service failure isolation |
| RequestOrchestrator | Cross-layer routing with tracing |
| SagaOrchestrator | Multi-step workflows with compensation |
| ObservabilityCollector | Distributed tracing and metrics |
| HealthChecker | Continuous service monitoring |

### Key Features
- Automatic layer registration
- Wildcard subscriptions (e.g., `agent.*`)
- Dead letter queue for failed events
- Trace/Span ID propagation

### Tools & APIs
```
POST  /services/register, /events/publish, /events/subscribe, /sagas/execute
GET   /services, /services/{name}/health, /traces/{trace_id}
```

### Dependencies
Redis, httpx, PostgreSQL (optional)

---

## L12: Natural Language Interface
**Port:** 8012 | **Status:** Production Ready (64% test coverage)

### Purpose
Seamless natural language access to all 60+ platform services with intelligent matching.

### Services
| Service | Description |
|---------|-------------|
| ServiceRegistry | Metadata catalog for 60+ services |
| ServiceFactory | Dynamic instantiation with dependencies |
| ExactMatcher | O(1) hash lookup |
| FuzzyMatcher | Keyword + semantic matching |
| CommandRouter | Route commands to service methods |
| SessionManager | 1-hour TTL conversation scope |
| EmbeddingService | Ollama-based semantic similarity |
| WorkflowTemplates | Pre-defined multi-service workflows |

### Key Features
- Exact matching: `PlanningService` → direct access
- Fuzzy matching: "Let's Plan" → smart disambiguation
- Semantic search with 90%+ accuracy
- 12 functional categories
- MCP server integration (10 tools)

### Tools & APIs
```
GET   /health, /v1/services, /v1/services/search, /v1/services/{name}
POST  /v1/services/invoke
GET   /v1/sessions/{id}, /v1/metrics
WS    /v1/ws/{session_id}
```

### Dependencies
All L01-L11 services, Ollama, Redis, Claude Code

---

## L13: Role Management Layer
**Port:** 8013 | **Status:** Implementation Complete

### Purpose
Intelligent role-based task routing with human/AI/hybrid classification and context assembly.

### Services
| Service | Description |
|---------|-------------|
| RoleRegistry | Role definitions with skills |
| RoleDispatcher | Task-to-role matching with scoring |
| ClassificationEngine | Human/AI/Hybrid classifier |
| RoleContextBuilder | Token-budgeted context assembly |
| SkillMatcher | Semantic skill-to-task matching |
| KeywordAnalyzer | NL classification support |

### Key Features
- **Role Types:** AI_PRIMARY, HUMAN_PRIMARY, HYBRID
- **Skill Levels:** BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
- Token budget management (default: 4000)
- Weighted skill scoring

### Tools & APIs
```
GET/POST/PATCH/DELETE  /roles, /roles/{id}
POST  /roles/dispatch, /roles/classify
GET   /roles/{id}/context, /roles/statistics
```

### Dependencies
L01, L04, Redis (optional)

---

## L14: Skill Library
**Port:** 8014 | **Status:** Implementation Complete

### Purpose
Skill management for Claude Code agents with LLM-powered generation, validation, and optimization.

### Services
| Service | Description |
|---------|-------------|
| SkillStore | In-memory storage with optional L01 persistence |
| SkillGenerator | LLM-powered skill creation |
| SkillValidator | Schema and logical validation |
| SkillOptimizer | Token optimization and priority loading |
| SkillFileParser | YAML parsing and schema validation |

### Key Features
- YAML-based skill definitions
- Claude-powered skill generation
- Multi-level validation
- **Categories:** Tool, Communication, Analysis, System
- **Status:** DRAFT, ACTIVE, DEPRECATED, ARCHIVED

### Tools & APIs
```
GET/POST/PATCH/DELETE  /skills, /skills/{id}
GET   /skills/by-name/{name}, /skills/agent/{agent_id}, /skills/stats/summary
POST  /skills/validate, /skills/generate, /skills/optimize
```

### Dependencies
L04 Model Gateway, L01 (optional), Redis

---

## Cross-Layer Dependencies

```
L01 ─────────────────────────────────────────────────────► (All Layers)
  │
L02 ◄── L01
  │
L03 ◄── L01, L02
  │
L04 ◄── L01 ──────────────────────────────────────────────► L05, L07, L12, L14
  │
L05 ◄── L01, L02, L03, L04, L11 ─────────────────────────► L06, L10
  │
L06 ◄── L01, L02, L04, L05 ──────────────────────────────► L07, L10, L11
  │
L07 ◄── L01, L04, L06
  │
L09 ◄── L01 (external entry point)
  │
L10 ◄── L02, L06, L11 (UI layer)
  │
L11 ◄── All layers publish ──────────────────────────────► All layers consume
  │
L12 ◄── L01-L11 (external queries)
  │
L13 ◄── L01, L04, L14 ───────────────────────────────────► L05, L09, L12
  │
L14 ◄── L04 ─────────────────────────────────────────────► L02, L13
```

---

## Execution Flow: Goal → Completion

```
1. User Input
   ↓
2. L12 NLP Interface ─── Parse natural language
   ↓
3. L13 Role Management ─── Classify and route
   ↓
4. L05 Planning ─── Decompose goal → tasks
   ├─ L04 Model Gateway (LLM decomposition)
   ├─ L01 Data Layer (plan storage)
   └─ L11 Integration (events)
   ↓
5. L02 Runtime ─── Spawn agent
   └─ L14 Skills (capabilities)
   ↓
6. L03 Tool Execution ─── Execute tools
   ├─ L01 (tool registry)
   └─ L11 (event publishing)
   ↓
7. L04 Model Gateway ─── LLM reasoning
   └─ L06 (quality scoring)
   ↓
8. L06 Evaluation ─── Measure quality
   └─ L01 (event storage)
   ↓
9. L07 Learning ─── Extract training data
   └─ Improve L04 models
   ↓
10. L10 Human Interface ─── Display results
    └─ L11 (real-time updates)
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Layers | 14 (12 implemented, 2 planned) |
| Total Microservices | 60+ |
| Error Code Ranges | E1000-E14999 |
| Primary Database | PostgreSQL 15 (15+ tables) |
| Cache Backend | Redis 7 |
| API Framework | FastAPI (async) |
| Message Bus | Redis Pub/Sub |
| Event Publishing Latency | <100ms |
| WebSocket Broadcast Latency | <500ms |
| Average API Response | <100ms (<50ms cached) |
