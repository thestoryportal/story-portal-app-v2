# Agentic AI Workforce - Layer Definitions

**Version:** 1.1
**Date:** January 04, 2026
**Phase:** 1.2 - Layer Boundary Definitions
**Status:** Final (Post-Validation)

---

## Document Overview

This document provides detailed definitions for all 11 pending layers identified in Session 1.1. Layer L01 (Data Layer) is complete at v3.2.1 and serves as the reference architecture.

### Version 1.1 Changes

| Change ID | Type | Description |
|-----------|------|-------------|
| BC-1 | Boundary Clarification | Nested sandbox architecture (L02/L03) |
| BC-2 | Interface Definition | `tool.invoke()` interface (L03/L11) |
| BC-3 | Interface Definition | `inference_request` schema (L04/L05) |
| OC-1 | Architectural Constraint | Internal agent messaging prohibition |
| Q5-RES | Question Resolution | Webhook boundary L03/L11 resolved |
| Q6-RES | Question Resolution | Supervision data store resolved |

### Layer Status Summary

| Layer # | Layer Name | Abbreviation | Status |
|---------|------------|--------------|--------|
| L00 | Infrastructure Layer | INFRA | Pending - Defined Below |
| L01 | Data Layer | DATA | v3.2.1 COMPLETE |
| L02 | Agent Runtime Layer | RUNTIME | Pending - Defined Below |
| L03 | Tool Execution Layer | TOOLS | Pending - Defined Below |
| L04 | Model Gateway Layer | MODEL | Pending - Defined Below |
| L05 | Planning Layer | PLAN | Pending - Defined Below |
| L06 | Evaluation Layer | EVAL | Pending - Defined Below |
| L07 | Learning Layer | LEARN | Pending - Defined Below |
| L08 | Supervision Layer | SUPER | Pending - Defined Below |
| L09 | API Gateway Layer | API | Pending - Defined Below |
| L10 | Human Interface Layer | UI | Pending - Defined Below |
| L11 | Integration Layer | INTEG | Pending - Defined Below |

---

## Architectural Constraints (Cross-Layer)

### OC-1: Internal Agent Messaging Prohibition

**Constraint:** All internal agent-to-agent communication MUST use the Handoff Protocol (Data Layer L4). Direct agent messaging is architecturally prohibited.

**Applies To:** All layers

**Enforcement Points:**
- L02 (Agent Runtime): Sandbox network policies block direct agent-to-agent connections
- L01 (Data Layer): Handoff Manager is sole inter-agent communication channel
- L08 (Supervision): Monitors for policy violations

---

## Layer L00: Infrastructure Layer

### Purpose

The Infrastructure Layer provides the foundational deployment substrate upon which all other layers execute. It manages container orchestration, compute resource allocation, network topology, secrets management, and service discovery -- enabling horizontal scaling, fault tolerance, and secure inter-layer communication without application-level awareness of infrastructure concerns.

### Core Responsibilities

1. **Container Orchestration**: Manages Kubernetes clusters, pod scheduling, resource quotas, and namespace isolation for multi-tenant agent deployments
2. **Compute Resource Management**: Provisions and scales CPU, memory, GPU, and storage resources based on workload demands and cost constraints
3. **Network Infrastructure**: Configures service mesh (Istio/Linkerd), ingress controllers, DNS, load balancing, and network policies for east-west/north-south traffic
4. **Secrets Management**: Integrates with HashiCorp Vault or cloud KMS for secure credential storage, rotation, and injection into workloads
5. **Service Discovery**: Maintains service registry, health checking, and endpoint resolution for dynamic service-to-service communication
6. **Infrastructure Observability**: Deploys and manages Prometheus, Grafana, and log aggregation infrastructure (distinct from application-level observability)
7. **Infrastructure Rate Limit Alerting**: Monitors and alerts on infrastructure-level rate limits (CPU, memory, network); distinct from model-level limits in L04

### Owns

- Kubernetes cluster lifecycle (provisioning, upgrades, node pool management)
- Container runtime configuration (containerd, gVisor for sandboxing)
- Network policies and firewall rules at infrastructure level
- TLS certificate management for service mesh mTLS
- Infrastructure-as-Code definitions (Terraform, Pulumi)
- Cost allocation tags and resource quotas per namespace
- Disaster recovery infrastructure (backup targets, replication)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Application deployment manifests | Each application layer | Layers define their own Kubernetes specs |
| Agent-level sandboxing | Agent Runtime Layer (L02) | Runtime isolation is agent concern |
| API authentication/authorization | API Gateway Layer (L09) | Business-level auth is API layer concern |
| Application secrets content | Each application layer | Infra provides mechanism, not policy |
| Database schema/data | Data Layer (L01) | Infra provides storage, Data owns structure |
| LLM API credentials | Model Gateway Layer (L04) | Model layer manages provider relationships |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Cluster Manager | Provisions and maintains Kubernetes clusters across regions |
| Network Controller | Manages service mesh, ingress, and network policies |
| Secrets Operator | Syncs secrets from Vault to Kubernetes secrets |
| Resource Scaler | Handles cluster autoscaler and VPA/HPA configurations |
| Certificate Manager | Automates TLS certificate issuance and renewal (cert-manager) |
| Observability Stack | Deploys Prometheus, Grafana, Loki for infrastructure metrics |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| None directly | Infrastructure Layer sits below Data Layer |
| Event Store (indirect) | Infra events may be forwarded to Data Layer for audit |

**Note**: Infrastructure Layer has no direct dependency on Data Layer. All other layers depend on Infrastructure Layer first, then Data Layer.

### Dependencies

- **Depends On**: External cloud providers (AWS/GCP/Azure) or bare metal infrastructure
- **Depended By**: ALL other layers (L01-L11)

### Estimated Specification Effort

**Medium (M)** - Infrastructure patterns are well-established (Kubernetes, Terraform), but documenting multi-region HA, cost optimization, and agent-specific requirements (GPU scheduling, sandbox isolation) requires careful specification. Estimate 4-6 sessions.

### Open Questions

- Q1: Multi-cloud vs single-cloud deployment strategy?
- Q2: GPU sharing model for LLM inference workloads?
- Q3: Edge deployment requirements for latency-sensitive agents?

---

## Layer L02: Agent Runtime Layer

### Purpose

The Agent Runtime Layer executes agent instances within isolated sandboxes, enforcing resource limits and security boundaries while managing agent lifecycle from spawn to termination. It provides the execution engine that transforms agent definitions and plans into running processes, coordinating fleet-wide operations including auto-scaling, load distribution, and graceful degradation under resource pressure.

### Core Responsibilities

1. **Sandbox Execution**: Runs agent code in isolated environments (gVisor, Firecracker, or container-based) with strict resource boundaries and syscall filtering
2. **Lifecycle Management**: Handles agent spawn, suspend, resume, checkpoint, and terminate operations with state persistence
3. **Resource Enforcement**: Enforces CPU, memory, token, and time quotas per agent instance; preempts runaway agents
4. **Fleet Operations**: Manages agent pool sizing, auto-scaling based on queue depth, and load distribution across available capacity
5. **Health Monitoring**: Tracks agent health, detects stuck/crashed agents, implements automatic restart with exponential backoff
6. **Execution Context**: Injects runtime context (credentials, configuration, Data Layer handles) into agent execution environment
7. **Runtime Metrics Collection**: Collects runtime performance metrics (execution time, resource usage); distinct from quality metrics in L06

### Sandbox Boundary Note (BC-1)

Agent sandboxes provide the outer security boundary. When agents invoke tools via L03 (Tool Execution Layer), tools run in nested sandboxes within the agent sandbox. L02 owns the outer agent isolation; L03 owns tool-specific restrictions within that boundary. Tools cannot escape the agent sandbox.

```
+------------------------------------------------------------------+
|  AGENT SANDBOX (L02 Runtime Layer owns)                          |
|  - Agent process isolation (gVisor/Firecracker)                  |
|  - Agent resource limits (CPU, memory, time)                     |
|  - Agent network restrictions                                    |
|  - Enforces OC-1: blocks direct agent-to-agent communication     |
|                                                                  |
|    +----------------------------------------------------------+  |
|    |  TOOL SANDBOX (L03 Tool Execution Layer owns)            |  |
|    |  - Tool process isolation (nested container/subprocess)  |  |
|    |  - Tool-specific network allowlist                       |  |
|    |  - Tool-specific filesystem mounts                       |  |
|    +----------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### Owns

- Agent process isolation and sandboxing technology choices
- Resource quota enforcement mechanisms (cgroups, token budgets)
- Agent instance registry (what's running, where, in what state)
- Warm pool management for fast agent startup
- Checkpoint/restore implementation for long-running agents
- Agent crash dumps and diagnostic capture
- Fleet-wide scaling policies and capacity planning
- Outer sandbox security boundary (per BC-1)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| What tasks agents execute | Planning Layer (L05) | Runtime executes; Planning decides |
| Tool invocation logic | Tool Execution Layer (L03) | Separate security boundary (BC-1) |
| Tool-specific sandboxing | Tool Execution Layer (L03) | Inner sandbox per BC-1 |
| LLM API calls | Model Gateway Layer (L04) | Model routing is specialized concern |
| Agent identity/credentials | Data Layer (L01) | DIDs and credentials in Data Layer |
| Container orchestration | Infrastructure Layer (L00) | Kubernetes is infra concern |
| Human approval workflows | Supervision Layer (L08) | HITL is supervision concern |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Sandbox Manager | Creates, configures, and destroys isolated execution environments |
| Execution Engine | Runs agent code, handles async operations, manages execution state |
| Resource Governor | Monitors and enforces resource quotas; terminates violations |
| Fleet Controller | Manages auto-scaling, load balancing, and agent placement decisions |
| Lifecycle Coordinator | Orchestrates spawn/terminate sequences, handles graceful shutdown |
| Health Monitor | Detects unhealthy agents, triggers restarts, maintains health metrics |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| DID Registry (L0) | Retrieves agent identity and credentials at spawn time |
| Event Store (L1) | Publishes agent.spawned, agent.terminated, agent.crashed events |
| Context Injector (L3) | Retrieves execution context for agent initialization |
| Lifecycle Manager (L7) | Coordinates lifecycle state transitions with Data Layer |
| Configuration Service (L9) | Fetches runtime configuration for agents |

### Dependencies

- **Depends On**: L00 (Infrastructure), L01 (Data), L04 (Model Gateway)
- **Depended By**: L03 (Tool Execution), L05 (Planning), L06 (Evaluation)

### Estimated Specification Effort

**Large (L)** - Core execution layer with complex sandboxing, resource management, and fleet coordination requirements. Security-critical with significant integration points. Estimate 6-8 sessions.

### Open Questions

- Q1: Preferred sandboxing technology (gVisor vs Firecracker vs container-only)?
- Q2: Checkpoint format for long-running agent state?
- Q3: How to handle agent migration between nodes during scale-down?

---

## Layer L03: Tool Execution Layer

### Purpose

The Tool Execution Layer provides a secure, isolated environment for agent tool invocations, maintaining a registry of available tools with capability manifests and enforcing tool-level permissions. It acts as the boundary between agent intent and external system access, implementing circuit breakers, rate limiting, and audit logging for all tool calls while abstracting the complexity of external API integrations from agent code.

### Core Responsibilities

1. **Tool Registry**: Maintains catalog of available tools with capability manifests (inputs, outputs, side effects, required permissions)
2. **Secure Execution**: Runs tool code in isolated sandboxes with network restrictions, filesystem isolation, and timeout enforcement
3. **Permission Enforcement**: Validates agent has required capabilities before tool execution; integrates with ABAC policies
4. **External API Management**: Handles authentication, rate limiting, and retry logic for external service calls
5. **Circuit Breaking**: Implements circuit breaker pattern to prevent cascade failures from unhealthy external services
6. **Result Validation**: Validates tool outputs against schemas; sanitizes results before returning to agents

### Sandbox Boundary Note (BC-1)

Tool sandboxes are nested within agent sandboxes owned by L02 (Agent Runtime Layer). L03 owns tool-specific isolation (network allowlists, filesystem mounts, timeout enforcement) but operates within the security boundary established by L02. Tool processes cannot exceed agent-level resource limits.

```
SANDBOX NESTING HIERARCHY
=========================

L02 (Agent Runtime) establishes:     L03 (Tool Execution) adds:
- Process isolation boundary         - Tool-specific network allowlist
- CPU/memory limits                  - Tool-specific filesystem mounts  
- Agent network policy               - Per-tool timeout enforcement
- Outer security perimeter           - Tool credential injection

Tool sandbox INHERITS agent sandbox constraints.
Tool cannot exceed agent resource limits.
Tool cannot access networks blocked at agent level.
```

### Provided Interfaces (BC-2)

```python
# Interface: tool.invoke (consumed by L11 Integration Layer)

class ToolInvokeRequest:
    tool_id: str                    # Registry identifier
    invocation_id: str              # Idempotency key
    payload: Dict[str, Any]         # Tool-specific input
    caller_did: str                 # Agent or integration DID
    timeout_seconds: int = 30       # Max execution time
    
class ToolInvokeResponse:
    invocation_id: str
    status: Literal["success", "failure", "timeout"]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time_ms: int
```

**Usage:** L11 (Integration Layer) calls `tool.invoke()` to execute tools in response to inbound webhooks. L11 handles webhook reception, validation, and routing; L03 handles tool execution in sandbox.

### Owns

- Tool definition schema and registry storage
- Tool sandbox execution environment (nested within agent sandbox per BC-1)
- Tool-level rate limiting and quota tracking
- External service credential management for tools
- Tool versioning and compatibility checking
- Tool execution audit log (distinct from Data Layer event store)
- Tool health metrics and availability status
- `tool.invoke()` interface implementation (BC-2)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Agent execution sandbox | Agent Runtime Layer (L02) | Agent isolation is runtime concern; BC-1 |
| LLM tool/function calling format | Model Gateway Layer (L04) | Model-specific formats in Model layer |
| Webhook endpoints for external systems | Integration Layer (L11) | Inbound integrations in Integration layer |
| Tool selection strategy | Planning Layer (L05) | Which tools to use is planning decision |
| Tool output quality scoring | Evaluation Layer (L06) | Quality assessment is evaluation concern |
| Tool permission policies | Data Layer (L01) | ABAC policies stored in Data Layer |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Tool Registry | Stores tool definitions, manifests, and version history |
| Tool Executor | Runs tool code in isolated environment with resource limits |
| Permission Checker | Validates agent capabilities against tool requirements |
| External Adapter Manager | Manages connections, auth, and rate limits for external APIs |
| Circuit Breaker Controller | Monitors external service health; opens circuits on failures |
| Result Validator | Validates and sanitizes tool outputs before return |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes tool.invoked, tool.succeeded, tool.failed events |
| ABAC Engine | Queries permission policies for tool access decisions |
| Context Injector (L3) | Retrieves tool-specific context (credentials, config) |
| Audit Log | Writes detailed tool execution records for compliance |

### Dependencies

- **Depends On**: L01 (Data), L02 (Agent Runtime)
- **Depended By**: L11 (Integration)

### Estimated Specification Effort

**Medium (M)** - Well-understood patterns (registry, circuit breaker, sandboxing) but requires careful security design for external API access. Tool manifest schema needs thorough definition. Estimate 4-6 sessions.

### Open Questions

- Q1: Should tools be versioned independently or tied to agent versions?
- Q2: How to handle tools that require long-running external operations?
- ~~Q3: Boundary between Tool Execution and Integration Layer for webhooks?~~ **RESOLVED by BC-2**

---

## Layer L04: Model Gateway Layer

### Purpose

The Model Gateway Layer abstracts LLM provider complexity from consuming layers, routing inference requests across multiple providers (Anthropic, OpenAI, local models) based on capability requirements, cost constraints, and availability. It implements semantic caching, failover logic, usage quota enforcement, and request/response normalization -- ensuring agents receive consistent model access regardless of underlying provider topology.

### Core Responsibilities

1. **Provider Abstraction**: Normalizes request/response formats across providers; shields consumers from provider-specific APIs
2. **Intelligent Routing**: Routes requests based on model capability requirements, latency SLAs, cost tiers, and current provider health
3. **Failover Management**: Detects provider outages; automatically fails over to secondary providers with configurable retry policies
4. **Semantic Caching**: Caches semantically similar requests to reduce latency and cost; implements cache invalidation policies
5. **Usage Quota Enforcement**: Tracks token consumption per agent/project; enforces budget limits and rate caps
6. **Request Optimization**: Implements request batching, prompt compression, and token budget management
7. **Model Rate Limit Alerting**: Monitors and alerts on LLM provider rate limits; distinct from infrastructure limits in L00

### Required Interfaces (BC-3)

| Interface | Provider | Usage |
|-----------|----------|-------|
| `inference_request` | L05 (Planning) | Receive provider-agnostic prompts for routing and formatting |

**Contract:** L04 receives `InferenceRequest` containing `LogicalPrompt` (provider-agnostic) and formats it into provider-specific API calls (OpenAI format, Anthropic format, etc.).

### Owns

- LLM provider credentials and API key rotation
- Provider health monitoring and availability tracking
- Token usage metering and cost attribution
- Semantic cache storage and eviction policies
- Request queue management and prioritization
- Model capability registry (which models support which features)
- Provider SLA tracking and performance metrics
- Provider-specific prompt formatting (per BC-3)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Prompt construction/templating | Planning Layer (L05) | What to say is planning concern; BC-3 |
| Logical prompt structure | Planning Layer (L05) | L05 owns content; L04 owns formatting |
| Model fine-tuning pipelines | Learning Layer (L07) | Training is learning concern |
| Output quality evaluation | Evaluation Layer (L06) | Quality scoring is evaluation concern |
| Agent-level token budgets | Agent Runtime Layer (L02) | Agent resource limits in runtime |
| External API rate limiting | API Gateway Layer (L09) | Client-facing limits in API layer |
| Model selection strategy | Planning Layer (L05) | Which model for which task is planning |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Provider Adapter Registry | Maintains normalized interfaces for each LLM provider |
| Request Router | Selects optimal provider based on requirements and availability |
| Semantic Cache | Stores and retrieves cached responses using embedding similarity |
| Quota Manager | Tracks usage, enforces limits, generates usage reports |
| Failover Controller | Monitors provider health; orchestrates failover sequences |
| Response Normalizer | Transforms provider-specific responses to standard format |
| Prompt Formatter | Converts LogicalPrompt to provider-specific format (BC-3) |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes model.request, model.response, model.failover events |
| Configuration Service (L9) | Retrieves provider configs, routing rules, quota policies |
| Context Injector (L3) | Accesses usage history for quota calculations |
| DID Registry (L0) | Maps agent DIDs to quota buckets and cost centers |

### Dependencies

- **Depends On**: L00 (Infrastructure), L01 (Data)
- **Depended By**: L02 (Agent Runtime), L05 (Planning), L06 (Evaluation), L07 (Learning)

### Estimated Specification Effort

**Medium (M)** - Provider abstraction patterns are established, but semantic caching, intelligent routing, and multi-provider failover require careful design. Token economics adds complexity. Estimate 4-6 sessions.

### Open Questions

- Q1: Should semantic cache be shared across agents or per-agent isolated?
- Q2: Network boundary placement -- inside cluster or DMZ?
- Q3: Streaming response handling across failover scenarios?

---

## Layer L05: Planning Layer

### Purpose

The Planning Layer transforms high-level goals into executable task sequences, constructing prompts from templates and injected context while managing strategic reasoning approaches (chain-of-thought, tree-of-thought, reflection). It serves as the cognitive architecture layer, determining what agents should do and how they should think about problems -- distinct from the Runtime Layer which handles execution mechanics.

### Core Responsibilities

1. **Goal Decomposition**: Breaks high-level objectives into atomic, executable tasks with dependency graphs
2. **Prompt Construction**: Assembles prompts from templates, system instructions, context, and constraints
3. **Reasoning Strategy Selection**: Chooses appropriate reasoning approach (CoT, ToT, ReAct, reflection) based on task characteristics
4. **Plan Versioning**: Maintains plan history, supports rollback, tracks plan evolution across iterations
5. **Resource Estimation**: Estimates token/time/cost requirements for plans; flags plans exceeding budgets
6. **Adaptive Replanning**: Detects plan failures and triggers replanning with updated constraints

### Provided Interfaces (BC-3)

```python
# Interface: inference_request (consumed by L04 Model Gateway)

class InferenceRequest:
    request_id: str                 # Correlation ID
    requester_did: str              # Requesting agent DID
    logical_prompt: LogicalPrompt   # Provider-agnostic prompt
    model_requirements: ModelReqs   # Capability requirements
    budget: TokenBudget             # Token/cost limits
    
class LogicalPrompt:
    system: str                     # System instructions
    context: List[ContextBlock]     # Injected context
    messages: List[Message]         # Conversation history
    output_format: Optional[str]    # Expected response format

class ModelReqs:
    min_context_window: int         # Minimum tokens
    capabilities: List[str]         # Required capabilities (vision, tools, etc.)
    latency_class: str              # "realtime", "interactive", "batch"

class TokenBudget:
    max_input_tokens: int
    max_output_tokens: int
    max_cost_cents: int

# Note: L04 (Model Gateway) is responsible for formatting
# LogicalPrompt into provider-specific API calls (OpenAI format,
# Anthropic format, etc.)
```

**Boundary:** L05 constructs provider-agnostic logical prompts (what to say, in what order). L04 formats for specific provider APIs (how to send it). The `inference_request` message is the contract.

### Owns

- Prompt template library and versioning system
- Task decomposition algorithms and heuristics
- Reasoning strategy configurations and selection rules
- Plan execution graphs and dependency tracking
- Plan optimization rules (parallelization, batching)
- A/B testing framework for prompt variants
- Planning metrics (success rates, iteration counts)
- Logical prompt structure (per BC-3)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Agent code execution | Agent Runtime Layer (L02) | Runtime executes plans |
| LLM API calls | Model Gateway Layer (L04) | Model access via gateway |
| Provider-specific formatting | Model Gateway Layer (L04) | L04 formats per BC-3 |
| Tool invocation mechanics | Tool Execution Layer (L03) | Tool calls via tool layer |
| Human approval decisions | Supervision Layer (L08) | HITL in supervision |
| Plan quality scoring | Evaluation Layer (L06) | Quality metrics in evaluation |
| Workflow state persistence | Data Layer (L01) | State stored in Data Layer |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Goal Analyzer | Parses objectives, identifies constraints, determines task type |
| Task Decomposer | Generates task graphs with dependencies and parallelization hints |
| Prompt Assembler | Constructs prompts from templates, context, and runtime parameters |
| Strategy Selector | Chooses reasoning approach based on task classification |
| Plan Optimizer | Refines plans for token efficiency, parallelism, cost |
| Replan Engine | Handles plan failures, generates recovery plans |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes plan.created, plan.updated, task.completed events |
| Context Injector (L3) | Retrieves relevant context for prompt construction |
| Workflow Engine (L4) | Registers plans as workflows; receives execution status |
| Configuration Service (L9) | Fetches prompt templates, strategy configs |

### Dependencies

- **Depends On**: L01 (Data), L02 (Agent Runtime), L04 (Model Gateway)
- **Depended By**: L08 (Supervision)

### Estimated Specification Effort

**Large (L)** - Novel territory combining prompt engineering, task decomposition, and reasoning strategies. Requires careful interface design with Runtime and Supervision layers. Estimate 6-8 sessions.

### Open Questions

- Q1: Standardized task decomposition schema or flexible per-domain?
- Q2: How to handle multi-agent collaborative planning?
- Q3: Integration point with external planning systems (e.g., classical AI planners)?

---

## Layer L06: Evaluation Layer

### Purpose

The Evaluation Layer measures agent and task output quality through automated scoring, success metrics, and regression detection. It provides the quality assurance infrastructure that enables continuous improvement by identifying degradation patterns, benchmarking against baselines, and feeding quality signals to the Learning Layer for model improvement decisions.

### Core Responsibilities

1. **Output Scoring**: Applies scoring models (LLM-as-judge, rule-based, embedding similarity) to agent outputs
2. **Success Measurement**: Tracks task completion rates, goal achievement metrics, and business KPIs
3. **Regression Detection**: Identifies quality degradation over time; alerts on performance drops
4. **Benchmark Management**: Maintains evaluation datasets, runs periodic benchmarks, tracks scores over time
5. **Comparative Analysis**: Compares performance across model versions, prompt variants, agent configurations
6. **Quality Reporting**: Generates quality dashboards, trend reports, and anomaly alerts
7. **Quality Metrics Collection**: Owns output quality metrics; distinct from runtime metrics in L02

### Owns

- Scoring model registry and versioning
- Evaluation dataset curation and maintenance
- Quality metrics definitions and calculation logic
- Benchmark suite configuration and scheduling
- Regression detection algorithms and thresholds
- Quality score storage and historical trends
- Evaluation pipeline orchestration

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Model training/fine-tuning | Learning Layer (L07) | Eval informs learning; doesn't execute |
| Agent execution | Agent Runtime Layer (L02) | Eval observes; doesn't execute |
| Runtime performance metrics | Agent Runtime Layer (L02) | L02 owns runtime; L06 owns quality |
| Human feedback collection | Supervision Layer (L08) | Human input via supervision |
| Prompt optimization | Planning Layer (L05) | Eval scores; planning optimizes |
| Business metrics definition | External (Product) | Business defines success criteria |
| Output storage | Data Layer (L01) | Outputs stored in Data Layer |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Scoring Engine | Applies scoring models to outputs; supports multiple scorer types |
| Benchmark Runner | Executes evaluation suites on schedule or trigger |
| Regression Detector | Analyzes score trends; identifies statistically significant drops |
| Dataset Manager | Stores, versions, and serves evaluation datasets |
| Metrics Aggregator | Computes aggregate metrics across dimensions (agent, task, time) |
| Quality Reporter | Generates dashboards, reports, and alert notifications |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Consumes task.completed events; publishes evaluation.completed |
| Storage (L2) | Reads agent outputs for evaluation |
| Context Injector (L3) | Retrieves evaluation context and ground truth |
| Configuration Service (L9) | Fetches scoring configs, benchmark schedules |

### Dependencies

- **Depends On**: L01 (Data), L02 (Agent Runtime), L04 (Model Gateway)
- **Depended By**: L07 (Learning)

### Estimated Specification Effort

**Medium (M)** - Evaluation patterns exist in MLOps, but LLM-specific scoring (LLM-as-judge, semantic similarity) and regression detection for stochastic outputs require careful design. Estimate 4-6 sessions.

### Open Questions

- Q1: Real-time streaming evaluation or batch-only?
- Q2: How to handle evaluation of multi-step agent workflows?
- Q3: Ground truth labeling workflow integration?

---

## Layer L07: Learning Layer

### Purpose

The Learning Layer captures feedback signals and orchestrates model improvement cycles, managing the pipeline from human corrections through dataset curation to fine-tuning triggers. It implements the continuous improvement loop that transforms evaluation insights and human feedback into better-performing models, while maintaining version control and rollback capabilities for model artifacts.

### Core Responsibilities

1. **Feedback Capture**: Collects human corrections, preference signals, and implicit feedback from agent interactions
2. **Dataset Curation**: Transforms raw feedback into training datasets; manages data quality, deduplication, and balancing
3. **Fine-tuning Orchestration**: Triggers fine-tuning jobs based on quality thresholds; manages training infrastructure integration
4. **RLHF Pipeline Management**: Implements reinforcement learning from human feedback workflows; manages reward model training
5. **Model Versioning**: Tracks model versions, training lineage, and performance deltas across versions
6. **Improvement Analytics**: Measures impact of training interventions; identifies high-value feedback sources

### Owns

- Feedback storage and normalization schemas
- Training dataset repositories and versioning
- Fine-tuning trigger policies and thresholds
- Reward model training and evaluation
- Model artifact registry (distinct from Model Gateway's runtime registry)
- Training job scheduling and resource allocation
- A/B testing infrastructure for model variants

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Model inference routing | Model Gateway Layer (L04) | Runtime routing in gateway |
| Output quality scoring | Evaluation Layer (L06) | Scoring informs learning; eval owns |
| Human feedback UI | Human Interface Layer (L10) | UI concerns in interface layer |
| Training compute infrastructure | Infrastructure Layer (L00) | GPU clusters are infra concern |
| Agent behavior policies | Planning Layer (L05) | Behavioral rules in planning |
| Feedback collection workflows | Supervision Layer (L08) | Human interaction via supervision |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Feedback Collector | Ingests feedback from multiple sources; normalizes to common schema |
| Dataset Builder | Constructs training datasets from feedback; handles sampling and balancing |
| Training Orchestrator | Manages fine-tuning job lifecycle; integrates with MLOps platforms |
| Reward Modeler | Trains and evaluates reward models for RLHF |
| Model Registry | Stores model artifacts, metadata, and performance benchmarks |
| Impact Analyzer | Measures improvement from training; identifies diminishing returns |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Consumes feedback.received, evaluation.completed events |
| Storage (L2) | Stores training datasets and model artifacts |
| Configuration Service (L9) | Fetches training configs, trigger thresholds |
| Audit Log | Records training decisions for compliance |

### Dependencies

- **Depends On**: L01 (Data), L04 (Model Gateway), L06 (Evaluation)
- **Depended By**: None directly (outputs flow to Model Gateway as new model versions)

### Estimated Specification Effort

**Large (L)** - Complex MLOps integration, RLHF pipelines, and model versioning requirements. Interfaces with external training infrastructure (cloud ML platforms). Estimate 6-8 sessions.

### Open Questions

- Q1: Integration approach with external MLOps platforms (SageMaker, Vertex AI)?
- Q2: On-premise vs cloud fine-tuning for data sensitivity?
- Q3: Automated vs human-approved model promotion to production?

---

## Layer L08: Supervision Layer

### Purpose

The Supervision Layer implements human-in-the-loop controls, managing approval workflows, escalation routing, and compliance audit trails. It serves as the governance layer ensuring human oversight of agent actions per regulatory requirements (EU AI Act, SOX) while balancing operational efficiency through configurable intervention policies and SLA-driven approval queues.

### Core Responsibilities

1. **Approval Workflow Management**: Routes actions requiring human approval; manages approval queues with SLAs and escalation
2. **Escalation Routing**: Directs issues to appropriate human reviewers based on expertise, availability, and workload
3. **Intervention Policy Enforcement**: Applies rules determining which actions require approval vs autonomous execution
4. **Audit Trail Maintenance**: Records all human-agent interactions, decisions, and overrides for compliance
5. **Compliance Reporting**: Generates reports for regulatory requirements (EU AI Act human oversight, SOX controls)
6. **Feedback Collection**: Captures human corrections and preferences during supervision interactions

### Data Store Resolution (Q6)

**Decision:** Supervision Layer uses Data Layer exclusively for all persistence. No dedicated data store required.

**Rationale:**
- Approval workflow state stored via Event Store (event sourcing)
- Workflow definitions managed via Workflow Engine (Data Layer L4)
- Audit trails leverage existing Data Layer event infrastructure
- Reduces operational complexity and ensures single source of truth

### Owns

- Approval workflow definitions and state machines
- Escalation rules and routing logic
- Intervention policy configuration
- Approval queue management and prioritization
- Compliance audit log (supplements Data Layer event store)
- SLA tracking and breach alerting
- Reviewer assignment and workload balancing

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| User authentication | API Gateway Layer (L09) | Auth is API boundary concern |
| Approval UI components | Human Interface Layer (L10) | UI in interface layer |
| Plan creation/modification | Planning Layer (L05) | Planning creates; supervision approves |
| Agent execution control | Agent Runtime Layer (L02) | Runtime executes approved plans |
| Feedback-to-training pipeline | Learning Layer (L07) | Learning consumes supervision feedback |
| Permission policies (ABAC) | Data Layer (L01) | Policy storage in Data Layer |
| Dedicated data store | N/A | Uses Data Layer exclusively (Q6 resolution) |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Workflow Engine | Executes approval workflows; manages state transitions |
| Escalation Router | Matches issues to reviewers; handles unavailability |
| Policy Evaluator | Determines intervention requirements for actions |
| Queue Manager | Prioritizes approval requests; tracks SLAs |
| Audit Recorder | Writes immutable audit records for all decisions |
| Compliance Reporter | Generates regulatory compliance reports |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes approval.requested, approval.granted, escalation.triggered |
| Workflow Engine (L4) | Registers approval workflows; receives workflow triggers |
| ABAC Engine | Queries policies for intervention requirements |
| Configuration Service (L9) | Fetches workflow definitions, escalation rules |

### Dependencies

- **Depends On**: L01 (Data), L05 (Planning), L10 (Human Interface)
- **Depended By**: None directly (human operators are external)

### Estimated Specification Effort

**Medium (M)** - Workflow patterns are established, but EU AI Act compliance requirements and multi-level escalation add complexity. Integration with Human Interface Layer requires coordination. Estimate 4-6 sessions.

### Open Questions

- ~~Q1: Does Supervision Layer need its own data store or exclusively use Data Layer?~~ **RESOLVED: Uses Data Layer exclusively**
- Q2: Real-time vs batched approval workflows for high-volume scenarios?
- Q3: Delegation rules for temporary reviewer unavailability?

---

## Layer L09: API Gateway Layer

### Purpose

The API Gateway Layer exposes external-facing APIs for programmatic access to the agent workforce, handling authentication, rate limiting, request validation, and API versioning. It serves as the security boundary between external clients and internal services, providing consistent API contracts while shielding internal architecture from external consumers.

### Core Responsibilities

1. **API Exposure**: Exposes REST and GraphQL endpoints for external client access to agent capabilities
2. **Authentication**: Validates client identity via OAuth2, API keys, or JWT tokens; integrates with identity providers
3. **Rate Limiting**: Enforces per-client rate limits and quotas; implements throttling and backpressure
4. **Request Validation**: Validates request schemas, sanitizes inputs, rejects malformed requests
5. **API Versioning**: Manages multiple API versions concurrently; handles deprecation and migration
6. **Developer Experience**: Provides OpenAPI documentation, SDK generation, and developer portal integration

### Owns

- External API endpoint definitions and routing
- Client credential management (API keys, OAuth clients)
- Rate limit policies per client/tier
- API version lifecycle and deprecation
- Request/response logging for external calls
- API usage analytics and billing metering
- Developer documentation and portal content

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Internal service-to-service auth | Infrastructure Layer (L00) | mTLS is infra concern |
| User session management | Human Interface Layer (L10) | UI sessions in interface layer |
| Business logic execution | Various internal layers | Gateway routes; doesn't execute |
| Agent-level permissions | Data Layer (L01) | ABAC in Data Layer |
| LLM provider rate limits | Model Gateway Layer (L04) | Provider limits in model layer |
| Webhook endpoints (inbound) | Integration Layer (L11) | Inbound integrations separate |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Route Manager | Maps external endpoints to internal services |
| Auth Handler | Validates credentials; issues/refreshes tokens |
| Rate Limiter | Tracks request counts; enforces limits with token bucket |
| Request Validator | Validates schemas; sanitizes inputs |
| Version Router | Routes requests to appropriate API version handlers |
| Usage Tracker | Records API calls for analytics and billing |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes api.request, api.response, api.rate_limited events |
| Configuration Service (L9) | Fetches rate limit configs, API version settings |
| DID Registry (L0) | Maps client credentials to agent permissions |

### Dependencies

- **Depends On**: L00 (Infrastructure), L01 (Data)
- **Depended By**: L10 (Human Interface), External clients

### Estimated Specification Effort

**Small (S)** - API gateway patterns are mature and well-documented. Standard components (Kong, AWS API Gateway patterns). Main effort is defining API contracts for agent operations. Estimate 2-4 sessions.

### Open Questions

- Q1: GraphQL vs REST-only for complex agent queries?
- Q2: WebSocket support for streaming agent responses?
- Q3: Multi-tenant isolation requirements at gateway level?

---

## Layer L10: Human Interface Layer

### Purpose

The Human Interface Layer provides web-based dashboards, approval consoles, and configuration interfaces for human operators interacting with the agent workforce. It translates complex system state into actionable visualizations, enables supervision workflows through approval UIs, and provides real-time visibility into agent operations -- serving as the primary touchpoint for non-programmatic human interaction.

### Core Responsibilities

1. **Monitoring Dashboards**: Displays real-time agent status, fleet health, task progress, and system metrics
2. **Approval Consoles**: Provides UI for reviewing and actioning approval requests from Supervision Layer
3. **Configuration Interfaces**: Enables agent configuration, policy management, and system settings through UI
4. **Real-time Visibility**: Streams live agent activity, logs, and events to operator displays
5. **Alerting Presentation**: Surfaces alerts and notifications; supports acknowledgment and snooze workflows
6. **Report Visualization**: Renders evaluation reports, compliance dashboards, and trend analytics

### Owns

- Frontend application code (React/Vue/Angular)
- UI component library and design system
- User session management and preferences
- Real-time WebSocket connections for live updates
- Dashboard layouts and widget configurations
- Notification preferences and delivery
- Accessibility compliance (WCAG)

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Approval workflow logic | Supervision Layer (L08) | UI presents; supervision orchestrates |
| User authentication | API Gateway Layer (L09) | Auth at API boundary |
| Metrics collection | Data Layer (L01) / Each Layer | UI consumes; layers produce |
| Alert rule definitions | Various layers | UI displays; layers define rules |
| Agent configuration schemas | Planning Layer (L05) | Planning defines; UI renders |
| External API endpoints | API Gateway Layer (L09) | Gateway exposes; UI consumes |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Dashboard Engine | Renders configurable dashboard layouts with widgets |
| Approval Console | Displays approval queue; captures decisions |
| Config Editor | Provides forms/editors for system configuration |
| Real-time Client | Manages WebSocket connections; handles reconnection |
| Notification Center | Aggregates and displays alerts; manages preferences |
| Report Viewer | Renders charts, tables, and exportable reports |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Subscribes to events for real-time activity feeds |
| Storage (L2) | Reads agent state, task history for display |
| Configuration Service (L9) | Reads/writes user preferences, dashboard configs |

### Dependencies

- **Depends On**: L01 (Data), L09 (API Gateway)
- **Depended By**: L08 (Supervision) -- for approval UI rendering

### Estimated Specification Effort

**Medium (M)** - Standard frontend patterns apply, but real-time streaming, complex approval workflows, and accessibility requirements add scope. Design system creation is significant effort. Estimate 4-6 sessions.

### Open Questions

- Q1: Should internal operator UI and external customer UI be separate applications?
- Q2: Mobile-responsive or dedicated mobile apps for on-call scenarios?
- Q3: Embedded analytics (Metabase/Superset) vs custom dashboards?

---

## Layer L11: Integration Layer

### Purpose

The Integration Layer connects the agent workforce to external systems through webhooks, bidirectional connectors, and protocol adapters. It manages the complexity of external system integration -- handling connection lifecycle, protocol translation, retry logic, and health monitoring -- enabling agents to interact with CRMs, ticketing systems, databases, and third-party APIs without embedding integration logic in agent code.

### Core Responsibilities

1. **Webhook Management**: Receives inbound webhooks from external systems; validates, transforms, and routes payloads
2. **Connector Lifecycle**: Manages bidirectional connectors (CRM, ticketing, databases); handles auth refresh and reconnection
3. **Protocol Translation**: Adapts between protocols (REST, GraphQL, SOAP, gRPC, message queues)
4. **Message Queue Integration**: Publishes/subscribes to external message brokers (Kafka, RabbitMQ, SQS)
5. **Connection Health Monitoring**: Tracks external system availability; alerts on degradation
6. **Data Transformation**: Maps external schemas to internal formats; handles versioning mismatches

### Required Interfaces (BC-2)

| Interface | Provider | Usage |
|-----------|----------|-------|
| `tool.invoke()` | L03 (Tool Execution) | Execute tools in response to webhooks |

**Webhook-to-Tool Flow:**
```
External System                Integration (L11)             Tools (L03)
      |                              |                            |
      |--- POST /webhook/event ----->|                            |
      |                              |                            |
      |                              |-- validate signature       |
      |                              |-- transform payload        |
      |                              |-- route to handler         |
      |                              |                            |
      |                              |--- tool.invoke(payload) -->|
      |                              |                            |
      |                              |                 execute in sandbox
      |                              |                            |
      |                              |<-- tool.result ------------|
      |                              |                            |
      |<-- 200 OK ------------------|                            |

OWNERSHIP BOUNDARY:
- L11 owns: Webhook endpoint, signature validation, payload transformation, routing
- L03 owns: Tool invocation, sandbox execution, result validation
- Boundary: tool.invoke() API call from L11 to L03
```

### Owns

- Webhook endpoint registration and routing
- Connector configuration and credential storage
- Protocol adapter implementations
- External system health status registry
- Integration-specific retry and backoff policies
- Schema mapping definitions
- Integration audit logs

### Does NOT Own (Explicit Boundaries)

| Excluded Item | Owning Layer | Rationale |
|---------------|--------------|-----------|
| Tool execution sandbox | Tool Execution Layer (L03) | Tools call integrations; don't own them (BC-2) |
| Tool invocation logic | Tool Execution Layer (L03) | L11 routes; L03 executes (BC-2) |
| External API authentication | Per connector config | Integration stores; doesn't define auth standards |
| Business logic for integrations | Planning Layer (L05) | Planning decides what to integrate |
| Internal event bus | Data Layer (L01) | Internal events in Data Layer |
| Client-facing API endpoints | API Gateway Layer (L09) | External APIs via gateway |
| LLM provider connections | Model Gateway Layer (L04) | LLM is specialized integration |

### Key Components (Preliminary)

| Component | Purpose |
|-----------|---------|
| Webhook Router | Receives webhooks; validates signatures; routes to handlers |
| Connector Manager | Manages connector lifecycle; handles auth refresh |
| Protocol Adapter Registry | Maintains adapters for each supported protocol |
| Queue Bridge | Connects to external message brokers; manages subscriptions |
| Health Monitor | Polls external systems; maintains availability status |
| Schema Transformer | Maps between external and internal data formats |

### Data Layer Integration

| Data Layer Service | Usage |
|--------------------|-------|
| Event Store (L1) | Publishes integration.received, integration.sent events |
| Configuration Service (L9) | Stores connector configs, webhook registrations |
| Context Injector (L3) | Provides integration context to tools |

### Dependencies

- **Depends On**: L01 (Data), L03 (Tool Execution)
- **Depended By**: External systems (inbound), Tool Execution (outbound)

### Estimated Specification Effort

**Medium (M)** - Integration patterns are established, but connector diversity (each external system differs) and protocol translation complexity require thorough specification. Estimate 4-6 sessions.

### Open Questions

- ~~Q1: Boundary between Integration Layer and Tool Execution for webhook-triggered tools?~~ **RESOLVED by BC-2**
- Q2: iPaaS integration (Workato, Tray.io) vs native connectors?
- Q3: Real-time vs polling for systems without webhook support?

---

## Summary Artifacts

### Complete Layer Inventory

| Layer # | Layer Name | Abbrev | Status | Effort | Dependencies |
|---------|------------|--------|--------|--------|--------------|
| L00 | Infrastructure Layer | INFRA | Pending | M | External cloud |
| L01 | Data Layer | DATA | v3.2.1 COMPLETE | -- | L00 |
| L02 | Agent Runtime Layer | RUNTIME | Pending | L | L00, L01, L04 |
| L03 | Tool Execution Layer | TOOLS | Pending | M | L01, L02 |
| L04 | Model Gateway Layer | MODEL | Pending | M | L00, L01 |
| L05 | Planning Layer | PLAN | Pending | L | L01, L02, L04 |
| L06 | Evaluation Layer | EVAL | Pending | M | L01, L02, L04 |
| L07 | Learning Layer | LEARN | Pending | L | L01, L04, L06 |
| L08 | Supervision Layer | SUPER | Pending | M | L01, L05, L10 |
| L09 | API Gateway Layer | API | Pending | S | L00, L01 |
| L10 | Human Interface Layer | UI | Pending | M | L01, L09 |
| L11 | Integration Layer | INTEG | Pending | M | L01, L03 |

**Effort Summary**: 3 Large, 7 Medium, 1 Small (excludes completed Data Layer)

---

### Dependency Matrix

```
                    DEPENDS ON (columns)
                    L00  L01  L02  L03  L04  L05  L06  L07  L08  L09  L10  L11
                   +----+----+----+----+----+----+----+----+----+----+----+----+
D  L00 INFRA       | -- |    |    |    |    |    |    |    |    |    |    |    |
E  L01 DATA        |  X | -- |    |    |    |    |    |    |    |    |    |    |
P  L02 RUNTIME     |  X |  X | -- |    |  X |    |    |    |    |    |    |    |
E  L03 TOOLS       |    |  X |  X | -- |    |    |    |    |    |    |    |    |
N  L04 MODEL       |  X |  X |    |    | -- |    |    |    |    |    |    |    |
D  L05 PLAN        |    |  X |  X |    |  X | -- |    |    |    |    |    |    |
E  L06 EVAL        |    |  X |  X |    |  X |    | -- |    |    |    |    |    |
D  L07 LEARN       |    |  X |    |    |  X |    |  X | -- |    |    |    |    |
   L08 SUPER       |    |  X |    |    |    |  X |    |    | -- |    |  X |    |
B  L09 API         |  X |  X |    |    |    |    |    |    |    | -- |    |    |
Y  L10 UI          |    |  X |    |    |    |    |    |    |    |  X | -- |    |
   L11 INTEG       |    |  X |    |  X |    |    |    |    |    |    |    | -- |
                   +----+----+----+----+----+----+----+----+----+----+----+----+

Legend: X = depends on, -- = self
```

**Key Observations**:
1. L01 (Data Layer) is the most depended-upon layer (10 dependents)
2. L00 (Infrastructure) is foundational (4 direct dependents, all others indirect)
3. L07 (Learning) has no downstream dependents (terminal layer)
4. L08 (Supervision) has an unusual dependency on L10 (UI) for approval interfaces

---

### Interface Contract Summary (New in v1.1)

| Interface | Provider | Consumer | Description |
|-----------|----------|----------|-------------|
| `tool.invoke()` | L03 (Tools) | L11 (Integration) | Execute tools from webhooks (BC-2) |
| `inference_request` | L05 (Planning) | L04 (Model) | Provider-agnostic prompts (BC-3) |
| Nested sandbox | L02 (Runtime) | L03 (Tools) | Agent sandbox contains tool sandbox (BC-1) |

---

### Updated Stack Diagram

```
+=====================================================================+
|                       EXTERNAL BOUNDARY                              |
+=====================================================================+
          |                                       |
          v                                       v
+-----------------------+               +-----------------------+
|   API GATEWAY (L09)   |               | HUMAN INTERFACE (L10) |
|   [S] Pending         |<------------->|   [M] Pending         |
+-----------------------+               +-----------------------+
          |                                       |
          +-----------------+-+-------------------+
                            | |
                            v v
                  +-------------------+
                  | SUPERVISION (L08) |
                  |   [M] Pending     |
                  +-------------------+
                            |
              +-------------+-------------+
              |                           |
              v                           |
    +-------------------+                 |
    |  PLANNING (L05)   |                 |
    |   [L] Pending     |                 |
    |                   |                 |
    | --inference_req-->|----+            |
    +-------------------+    |            |
              |              |            |
    +---------+---------+    |            |
    |                   |    |            |
    v                   v    v            |
+-------------------+  +-------------------+
|  LEARNING (L07)   |  | EVALUATION (L06)  |
|   [L] Pending     |  |   [M] Pending     |
+-------------------+  +-------------------+
    |                   |
    +-------------------+
              |
              v
    +-------------------+
    | AGENT RUNTIME     |
    | (L02) [L] Pending |
    | [outer sandbox]   |
    +-------------------+
         |           |
    +----+           +----+
    |                     |
    v                     v
+-------------------+  +-------------------+
| TOOL EXECUTION    |  |  MODEL GATEWAY    |
| (L03) [M] Pending |  |  (L04) [M] Pending|
| [inner sandbox]   |  | <--inference_req  |
| --tool.invoke()   |  +-------------------+
+-------------------+           |
    ^   |                       |
    |   v                       |
+-------------------+           |
| INTEGRATION (L11) |           |
|   [M] Pending     |           |
| <--tool.invoke()  |           |
+-------------------+           |
    |                           |
    +----------+----------------+
               |
               v
+=============================================================+
||                      DATA LAYER (L01)                     ||
||                      [x] v3.2.1 COMPLETE                  ||
||  Identity | Events | Storage | Context | Coordination    ||
+=============================================================+
               |
               v
+-------------------------------------------------------------+
|                   INFRASTRUCTURE (L00)                       |
|                      [M] Pending                             |
|  Containers | Compute | Network | Secrets | Service Mesh    |
+-------------------------------------------------------------+
               |
               v
         [Cloud / Bare Metal]
```

---

### Effort Estimation Summary

| Effort | Layers | Total Sessions (Est.) |
|--------|--------|----------------------|
| Large (L) | L02, L05, L07 | 18-24 sessions |
| Medium (M) | L00, L03, L04, L06, L08, L10, L11 | 28-42 sessions |
| Small (S) | L09 | 2-4 sessions |
| **TOTAL** | **11 layers** | **48-70 sessions** |

**Note**: Estimates assume 4-6 sessions for Medium, 6-8 for Large, 2-4 for Small per the workflow guide.

---

### Open Questions Consolidated

| # | Question | Layer(s) | Priority | Status |
|---|----------|----------|----------|--------|
| Q1 | Multi-cloud vs single-cloud deployment strategy? | L00 | High | Open |
| Q2 | GPU sharing model for LLM inference workloads? | L00 | High | Open |
| Q3 | Preferred sandboxing technology (gVisor vs Firecracker)? | L02 | High | Open |
| Q4 | Checkpoint format for long-running agent state? | L02 | Medium | Open |
| Q5 | Should semantic cache be shared across agents? | L04 | Medium | Open |
| Q6 | Network boundary for Model Gateway (cluster vs DMZ)? | L04 | High | Open |
| Q7 | Multi-agent collaborative planning approach? | L05 | Medium | Open |
| Q8 | Real-time vs batch evaluation streaming? | L06 | Medium | Open |
| Q9 | MLOps platform integration (SageMaker, Vertex)? | L07 | Medium | Open |
| Q10 | Supervision Layer dedicated data store? | L08 | Medium | **RESOLVED** |
| Q11 | Boundary: Integration Layer vs Tool Execution for webhooks? | L03, L11 | High | **RESOLVED** |
| Q12 | Internal vs external UI separation? | L10 | Low | Open |

---

## Document Complete

**All 11 pending layers defined with**:
- Purpose statements
- 5+ core responsibilities
- Explicit ownership boundaries
- Key components
- Data Layer integration points
- Dependencies (up and down)
- Effort estimates
- Open questions
- Interface contracts (new in v1.1)
- Boundary clarifications (BC-1, BC-2, BC-3)
- Architectural constraints (OC-1)

**Next Step**: Begin Wave 1 with L00 Infrastructure Layer specification

---

*Document generated: January 04, 2026*
*Version: 1.1 (Post-Validation)*
*Ready for: Phase 2 - Per-Layer Development*
