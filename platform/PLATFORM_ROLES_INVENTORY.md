# Platform Core Agentic Roles Inventory

**Complete catalog of all core roles, services, and orchestrators in the platform**

Last Updated: 2026-01-15

---

## Interface Status Legend

- 🟢 **HTTP API Available** - Can be accessed via REST endpoints
- 🟡 **Partial Interface** - Some capabilities exposed, many missing
- 🔴 **No Interface** - Python-only, must be imported programmatically
- 📊 **Data Store** - Backend persistence layer (accessed via L01 Client)

---

## L01: Data Layer (Persistence & Event Sourcing)

### Registries & Stores

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **AgentRegistry** | Registry | 🟢 `/api/v1/agents` | Agent metadata storage and lookup |
| **ToolRegistry** | Registry | 📊 L01 Client | Tool definitions and schemas |
| **ModelRegistry** (L01) | Registry | 📊 L01 Client | Model metadata tracking |
| **SessionService** | Service | 📊 L01 Client | Agent session management |
| **DatasetService** | Service | 📊 L01 Client | Training dataset storage |
| **TrainingExampleService** | Service | 📊 L01 Client | Training examples CRUD |
| **EventStore** | Store | 📊 L01 Client | Event sourcing persistence |
| **GoalStore** | Store | 🟢 `/api/v1/goals` | Goal lifecycle tracking |
| **PlanStore** | Store | 📊 L01 Client | Execution plan persistence |
| **DocumentStore** | Store | 📊 L01 Client | Knowledge base documents |
| **EvaluationStore** | Store | 📊 L01 Client | Evaluation results |
| **FeedbackStore** | Store | 📊 L01 Client | User feedback tracking |
| **ConfigStore** | Store | 📊 L01 Client | Configuration management |

**Access Methods:**
- Via L01 Client: `L01Client(base_url="http://localhost:8002")`
- Via L09 Gateway: `/api/v1/*` (limited CRUD only)
- Via L10 Dashboard: `/api/agents`, `/api/goals` (read-only)

---

## L02: Runtime Layer (Agent Lifecycle & Execution)

### Core Runtime Services

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **LifecycleManager** | Manager | 🔴 None | Agent spawn/terminate/suspend operations |
| **AgentExecutor** | Executor | 🔴 None | Execute agent logic with task handling |
| **FleetManager** | Manager | 🔴 None | Multi-agent fleet coordination & autoscaling |
| **StateManager** | Manager | 🔴 None | Agent state persistence & recovery |
| **ResourceManager** | Manager | 🔴 None | CPU/memory/network resource allocation |
| **SandboxManager** | Manager | 🔴 None | Sandbox environment provisioning |
| **WarmPoolManager** | Manager | 🔴 None | Pre-warmed agent pool for fast spawning |
| **WorkflowEngine** | Engine | 🔴 None | Multi-step workflow execution |
| **HealthMonitor** | Monitor | 🔴 None | Agent health checks & failure detection |

**Capabilities:**
- Spawn agents in isolated sandboxes
- Manage agent lifecycle (created → active → suspended → terminated)
- Autoscale agent fleets based on load
- Resource allocation and quota enforcement
- State checkpointing and recovery
- Warm pool optimization for latency reduction

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L02_runtime.services import LifecycleManager`
- ⚠️ Used internally by platform, not exposed to users

---

## L03: Tool Execution Layer

### Tool Management & Execution

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **ToolExecutor** | Executor | 🔴 None | Execute tool calls with sandboxing |
| **ToolRegistry** | Registry | 🔴 None | Tool discovery and schema management |
| **ToolComposer** | Composer | 🔴 None | Multi-tool workflow composition |
| **ToolSandbox** | Sandbox | 🔴 None | Isolated tool execution environments |
| **ResultCache** | Cache | 🔴 None | Tool result caching for efficiency |
| **MCPToolBridge** | Bridge | 🔴 None | Model Context Protocol tool integration |

**Capabilities:**
- Execute tools (Python functions, APIs, shell commands)
- Compose multi-step tool workflows
- Sandbox tool execution for security
- Cache tool results (semantic + exact match)
- MCP server integration

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L03_tool_execution.services import ToolExecutor`

---

## L04: Model Gateway Layer (LLM Routing)

### LLM Management & Routing

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **ModelGateway** | Gateway | 🔴 None | Unified LLM inference interface |
| **ModelRegistry** | Registry | 🔴 None | Model metadata & capability tracking |
| **LLMRouter** | Router | 🔴 None | Route requests to optimal model |
| **SemanticCache** | Cache | 🔴 None | Semantic similarity caching |
| **CircuitBreaker** | Protector | 🔴 None | Failure protection for LLM calls |
| **RateLimiter** | Limiter | 🔴 None | Token-based rate limiting |
| **RequestQueue** | Queue | 🔴 None | Request prioritization & batching |

**Capabilities:**
- Route to OpenAI, Anthropic, Ollama, custom models
- Automatic fallback on failures
- Semantic caching (embedding-based)
- Token rate limiting per tenant
- Circuit breaker pattern
- Cost tracking per model/tenant

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L04_model_gateway.services import ModelGateway`
- 📊 Usage tracked in L01 via L04Bridge

---

## L05: Planning Layer (Goal Decomposition & Orchestration)

### Strategic Planning & Coordination

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **PlanningService** | Service | 🔴 None | System-level planning coordinator |
| **TaskOrchestrator** | Orchestrator | 🔴 None | Task execution with parallel coordination |
| **GoalDecomposer** | Decomposer | 🔴 None | Goal → Task decomposition (template + LLM) |
| **AgentAssigner** | Assigner | 🔴 None | Task → Agent assignment with capability matching |
| **DependencyResolver** | Resolver | 🔴 None | Task dependency DAG construction |
| **PlanValidator** | Validator | 🔴 None | Plan feasibility & resource validation |
| **ExecutionMonitor** | Monitor | 🔴 None | Track plan execution progress |
| **ResourceEstimator** | Estimator | 🔴 None | Estimate tokens/time/cost for plans |
| **PlanCache** | Cache | 🔴 None | Cache decomposed plans |
| **ContextInjector** | Injector | 🔴 None | Inject runtime context into plans |
| **TemplateRegistry** | Registry | 🔴 None | Goal decomposition templates |

**Capabilities:**
- Decompose natural language goals into task DAGs
- Template-based decomposition (fast)
- LLM-based decomposition (flexible)
- Parallel task execution coordination
- Agent capability matching
- Resource budget enforcement
- Plan caching and reuse

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L05_planning.services import PlanningService`

**Example Usage:**
```python
from L05_planning.services import PlanningService
from L05_planning.models import Goal, GoalConstraints

service = PlanningService()
goal = Goal(
    goal_text="Deploy monitoring agents",
    constraints=GoalConstraints(max_parallelism=5)
)
plan = await service.create_plan(goal)
result = await service.execute_plan(plan)
```

---

## L06: Evaluation Layer (Metrics & Quality)

### Observability & Quality Assurance

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **EvaluationService** | Service | 🔴 None | Evaluation orchestration |
| **MetricsEngine** | Engine | 🔴 None | Metrics collection & aggregation |
| **AlertManager** | Manager | 🔴 None | Alert rule evaluation & triggering |
| **AnomalyDetector** | Detector | 🔴 None | Statistical anomaly detection |
| **QualityScorer** | Scorer | 🔴 None | Output quality scoring |
| **ComplianceValidator** | Validator | 🔴 None | Policy compliance checking |
| **QueryEngine** | Engine | 🔴 None | Metrics query & aggregation |
| **DeduplicationEngine** | Engine | 🔴 None | Event deduplication |
| **AuditLogger** | Logger | 🔴 None | Compliance audit logging |
| **EventValidator** | Validator | 🔴 None | Event schema validation |
| **CacheManager** | Manager | 🔴 None | Metrics cache management |
| **StorageManager** | Manager | 🔴 None | Time-series metrics storage |
| **ConfigManager** | Manager | 🔴 None | Evaluation config management |

**Capabilities:**
- Collect metrics (latency, tokens, cost, success rate)
- Real-time alerting on thresholds
- Anomaly detection (statistical)
- Quality scoring for agent outputs
- Policy compliance validation
- Audit trail for compliance

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L06_evaluation.services import EvaluationService`

---

## L07: Learning Layer (Model Training & Improvement)

### Continuous Learning & Adaptation

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **LearningService** | Service | 🔴 None | Learning orchestration |
| **FineTuningEngine** | Engine | 🔴 None | Model fine-tuning pipeline |
| **RLHFEngine** | Engine | 🔴 None | Reinforcement learning from human feedback |
| **DatasetCurator** | Curator | 🔴 None | Training dataset curation & filtering |
| **ModelRegistry** (L07) | Registry | 🔴 None | Fine-tuned model versioning |
| **ModelValidator** | Validator | 🔴 None | Model quality validation |
| **ExampleQualityFilter** | Filter | 🔴 None | Training example quality filtering |
| **TrainingDataExtractor** | Extractor | 🔴 None | Extract training data from interactions |

**Capabilities:**
- Extract training examples from agent interactions
- Curate high-quality datasets
- Fine-tune models (OpenAI, Anthropic)
- RLHF training loops
- Model versioning and A/B testing
- Quality-based curriculum learning

**Access Methods:**
- ❌ No HTTP interface
- ✅ Python imports: `from L07_learning.services import LearningService`

---

## L09: API Gateway Layer (External Access)

### Authentication, Authorization, Rate Limiting

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **AuthenticationHandler** | Handler | 🟢 Implicit | API key/JWT authentication |
| **AuthorizationEngine** | Engine | 🟢 Implicit | Permission-based authorization |
| **RateLimiter** | Limiter | 🟢 Implicit | Token bucket rate limiting |
| **IdempotencyHandler** | Handler | 🟢 Implicit | Idempotent request handling |
| **BackendExecutor** | Executor | 🔴 None | Backend request execution |
| **RequestRouter** | Router | 🔴 None | Route matching & forwarding |
| **RequestValidator** | Validator | 🔴 None | Input validation |
| **ResponseFormatter** | Formatter | 🔴 None | Response standardization |
| **AsyncHandler** | Handler | 🔴 None | Long-running async operations |
| **EventPublisher** | Publisher | 🔴 None | Request event publishing |

**Capabilities:**
- API key & JWT authentication
- Role-based authorization
- Rate limiting per consumer
- Idempotency via keys
- Request validation
- Cross-layer routing

**Access Methods:**
- 🟢 HTTP: All `/api/v1/*` routes go through gateway
- 🔴 Services not directly accessible

---

## L10: Human Interface Layer (Dashboard & Monitoring)

### User-Facing Interfaces

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **DashboardService** | Service | 🟡 `/api/agents`, `/api/goals` | Dashboard data aggregation |
| **AlertService** | Service | 🔴 None | User alert management |
| **AuditService** | Service | 🔴 None | Audit log queries |
| **ControlService** | Service | 🔴 None | Manual control operations |
| **CostService** | Service | 🔴 None | Cost tracking & budgets |
| **EventService** | Service | 🟢 `WS /ws` | Real-time event streaming |
| **WebSocketGateway** | Gateway | 🟢 `WS /ws` | WebSocket connection management |

**Capabilities:**
- Web dashboard (HTML/CSS/JS)
- Real-time event streaming via WebSocket
- Agent/goal/task visualization
- User interaction tracking
- Manual control operations

**Access Methods:**
- 🟢 HTTP Dashboard: `http://localhost:8003/`
- 🟢 WebSocket: `ws://localhost:8003/ws`
- 🟡 Limited APIs: `/api/agents`, `/api/goals`

---

## L11: Integration Layer (Cross-Layer Coordination)

### Service Mesh & Event Routing

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **RequestOrchestrator** | Orchestrator | 🔴 None | Cross-layer request routing |
| **SagaOrchestrator** | Orchestrator | 🔴 None | Multi-step workflows with rollback |
| **ServiceRegistry** | Registry | 🟡 `GET /services` | Service discovery & health |
| **EventBusManager** | Manager | 🔴 None | Event bus coordination |
| **CircuitBreaker** | Protector | 🟡 `GET /metrics` | Cross-service failure protection |
| **ObservabilityManager** | Manager | 🔴 None | Distributed tracing |

**Capabilities:**
- Cross-layer request routing
- Saga pattern (compensating transactions)
- Service discovery
- Circuit breaker pattern
- Event bus coordination
- Distributed tracing

**Access Methods:**
- 🟡 HTTP: `GET /services`, `GET /metrics` (limited)
- 🔴 Core orchestration not exposed

---

## Specialized Agents

### QA & Testing

| Role | Type | Interface | Purpose |
|------|------|-----------|---------|
| **QAOrchestrator** | Orchestrator | 🔴 None | Coordinate multi-agent QA campaigns |
| **APITester** | Agent | 🔴 None | API endpoint testing |
| **IntegrationTester** | Agent | 🔴 None | Cross-layer integration testing |
| **DataValidator** | Agent | 🔴 None | Data consistency validation |

**Access Methods:**
- ❌ No interface - Python classes only
- Must be instantiated and deployed manually

---

## Summary by Interface Availability

### 🟢 HTTP Accessible (Direct User Access)

**L01 Data Layer:**
- Agent CRUD: `GET/POST/PATCH /api/v1/agents`
- Goal CRUD: `GET/POST/PATCH /api/v1/goals`
- Task CRUD: `GET/POST/PATCH /api/v1/tasks`

**L10 Human Interface:**
- Dashboard: `GET /` (HTML page)
- Agent List: `GET /api/agents`
- Goal List: `GET /api/goals`
- Event Stream: `WS /ws`

**L11 Integration:**
- Service List: `GET /services`
- Metrics: `GET /metrics`

### 🔴 No Interface (60+ Core Services)

**All orchestrators:**
- PlanningService, TaskOrchestrator, QAOrchestrator
- SagaOrchestrator, RequestOrchestrator

**All managers:**
- LifecycleManager, FleetManager, ResourceManager
- StateManager, SandboxManager, WarmPoolManager
- AlertManager, CacheManager, ConfigManager

**All executors:**
- AgentExecutor, ToolExecutor, BackendExecutor

**All engines:**
- WorkflowEngine, MetricsEngine, QueryEngine
- DeduplicationEngine, AuthorizationEngine
- FineTuningEngine, RLHFEngine

**All registries:**
- ToolRegistry, ModelRegistry (L04 + L07)
- TemplateRegistry, ServiceRegistry

**All other services:**
- GoalDecomposer, AgentAssigner, DependencyResolver
- EvaluationService, LearningService, DatasetCurator
- SemanticCache, CircuitBreaker, EventBusManager
- And 40+ more...

---

## Your Options for Interfacing

### Option 1: Create L12 Natural Language Interface ⭐ RECOMMENDED

**Status:** Documented in `FEATURE_GAP_NL_INTERFACE.md` and `TODO_NL_INTERFACE.md`

Create a new layer that exposes all platform capabilities via:
- Natural language commands
- Slash commands (`/plan`, `/deploy`, `/status`)
- HTTP API for programmatic access
- MCP server for Claude CLI integration

**Coverage:**
- ✅ All orchestrators (Planning, Task, Saga, Request, QA)
- ✅ All managers (Lifecycle, Fleet, Resource, State)
- ✅ All executors (Agent, Tool, Workflow)
- ✅ All services (Evaluation, Learning, Metrics)

**Implementation:** 4-5 weeks (see TODO_NL_INTERFACE.md)

### Option 2: Write Python Scripts

**Current workaround** - Write Python scripts that import services directly:

```python
from L05_planning.services import PlanningService
from L02_runtime.services import LifecycleManager

# Use services programmatically
service = PlanningService()
plan = await service.create_plan(goal)
```

**Pros:** Full access to all features
**Cons:** Requires Python knowledge, no natural language interface

### Option 3: Extend Existing APIs

Add endpoints to L09/L10/L11 for specific use cases:
- Add `/api/orchestration/*` routes to L09
- Extend L10 dashboard with control panels
- Add `/api/planning/*` routes

**Pros:** Follows existing patterns
**Cons:** Piecemeal approach, no unified interface

---

## Recommended Next Steps

1. **Immediate:** Review `FEATURE_GAP_NL_INTERFACE.md` for full requirements
2. **Short-term:** Decide on L12 implementation approach
3. **Medium-term:** Implement L12 NL Interface with slash commands
4. **Long-term:** MCP server integration for seamless Claude CLI usage

---

**CRITICAL:** The platform has 60+ core agentic services, but only ~10 have HTTP interfaces. This creates a massive usability gap for operators, developers, and end users who want to leverage platform capabilities without writing Python code.
