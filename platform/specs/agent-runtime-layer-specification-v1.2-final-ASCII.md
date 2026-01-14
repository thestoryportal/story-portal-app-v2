# Agent Runtime Layer Specification

**Version:** 1.2 (Final)
**Status:** Ready for Implementation
**Layer ID:** L02
**Date:** 2025-01-14
**Specification Type:** Complete Merged Document

---

## Table of Contents

### Part I: Foundation (Sections 1-5)
- [Section 1: Executive Summary](#section-1-executive-summary)
  - 1.1 Purpose
  - 1.2 Key Capabilities
  - 1.3 Position in Stack
  - 1.4 Design Principles
- [Section 2: Scope Definition](#section-2-scope-definition)
  - 2.1 In Scope
  - 2.2 Out of Scope
  - 2.3 Layer Boundaries
- [Section 3: Architecture](#section-3-architecture)
  - 3.1 System Context
  - 3.2 Component Architecture
  - 3.3 Component Specifications (11 components)
  - 3.4 Deployment Architecture
- [Section 4: Interfaces](#section-4-interfaces)
  - 4.1 gRPC Service Definitions
  - 4.2 Protocol Definitions
  - 4.3 Event Schemas
  - 4.4 Inter-Layer Contracts
- [Section 5: Data Model](#section-5-data-model)
  - 5.1 Entity Definitions
  - 5.2 State Machines
  - 5.3 Schema Definitions
  - 5.4 Event Store Integration

### Part II: Integration and Operations (Sections 6-10)
- [Section 6: Integration with Data Layer v4.0](#section-6-integration-with-data-layer-v40)
  - 6.1 Relationship Model
  - 6.2 Phase 15 Integration (Document Management)
  - 6.3 Phase 16 Integration (Session Orchestration)
  - 6.4 L04 Model Gateway Integration
- [Section 7: Reliability and Scalability](#section-7-reliability-and-scalability)
  - 7.1 Reliability Patterns
  - 7.2 Scalability Architecture
  - 7.3 Warm Pool Management
  - 7.4 Fleet Elasticity
- [Section 8: Security](#section-8-security)
  - 8.1 Threat Model
  - 8.2 Sandbox Security
  - 8.3 Authentication and Authorization
  - 8.4 Network Policies
  - 8.5 Secrets Management
- [Section 9: Observability](#section-9-observability)
  - 9.1 Metrics
  - 9.2 Logging
  - 9.3 Tracing
  - 9.4 Alerting
- [Section 10: Configuration](#section-10-configuration)
  - 10.1 Configuration Hierarchy
  - 10.2 Runtime Classes
  - 10.3 Feature Flags
  - 10.4 Dynamic Configuration

### Part III: Implementation and Deployment (Sections 11-15)
- [Section 11: Implementation Guide](#section-11-implementation-guide)
  - 11.1 Implementation Phases
  - 11.2 Code Examples
  - 11.3 Integration Patterns
- [Section 12: Testing Strategy](#section-12-testing-strategy)
  - 12.1 Unit Testing
  - 12.2 Integration Testing
  - 12.3 Performance Testing
  - 12.4 Chaos Engineering
- [Section 13: Migration and Deployment](#section-13-migration-and-deployment)
  - 13.1 Deployment Prerequisites
  - 13.2 Migration Strategy
  - 13.3 Rollout Phases
  - 13.4 Rollback Procedures
- [Section 14: Open Questions and Decisions](#section-14-open-questions-and-decisions)
  - 14.1 Architectural Decisions
  - 14.2 Open Questions
- [Section 15: References and Appendices](#section-15-references-and-appendices)
  - 15.1 References
  - 15.3 Glossary
- [Appendix A: Gap Analysis Summary](#appendix-a-gap-analysis-integration-summary)
- [Appendix B: Error Code Reference](#appendix-b-error-code-reference)
- [Appendix C: Phase 15/16 Integration Reference](#appendix-c-phase-1516-integration-reference)

### Quick Reference Links
- [Component Specifications](#33-component-specifications) - 11 core components
- [SLO Targets](#713-latency-slo-targets) - Performance objectives
- [Error Codes](#appendix-b-error-code-reference) - E2000-E2103 codes
- [Glossary](#153-glossary) - 36 term definitions

---

# Section 1: Executive Summary

## 1.1 Purpose

The Agent Runtime Layer (L02) provides the execution environment for AI agents within the Agentic System architecture. This layer manages the complete lifecycle of agent instances from spawn to termination, enforcing isolation boundaries through sandbox technologies, managing computational resources, and coordinating fleet operations for horizontal scaling.

Built upon the Infrastructure Layer (L00) for Kubernetes primitives and sandbox runtimes, and tightly integrated with the Agentic Data Layer (L01 v4.0) for state persistence, session orchestration, and document management, L02 serves as the operational foundation for executing agent workloads. It provides standardized interfaces for the Model Gateway Layer (L04) to handle LLM inference requests while maintaining strict resource boundaries.

The Agent Runtime Layer addresses the critical gap between high-level agent orchestration frameworks (such as LangGraph, CrewAI, and Semantic Kernel) and low-level container infrastructure. It provides a unified execution model that supports graph-based workflows, checkpointing for fault tolerance, and warm pool management for rapid scaling.

## 1.2 Key Capabilities

| Capability | Description | Priority |
|------------|-------------|----------|
| Agent Execution | Execute agent code within isolated sandboxes with configurable runtime classes | Critical |
| Lifecycle Management | Manage spawn, suspend, resume, checkpoint, and terminate operations | Critical |
| Sandbox Isolation | Provide tiered isolation (runc, gVisor, Kata) based on trust level | Critical |
| Resource Enforcement | Enforce CPU, memory, and token budgets per agent instance | Critical |
| State Persistence | Checkpoint agent state via SessionBridge integration with L01 Phase 16 | Critical |
| Health Monitoring | Liveness/readiness probes with agent-specific metrics | High |
| Fleet Operations | Horizontal scaling with warm pools and graceful drain | High |
| Document Integration | Query authoritative documents via DocumentBridge with L01 Phase 15 | High |
| Model Integration | Route inference requests to L04 Model Gateway with budget tracking | Critical |

## 1.3 Position in Stack

```
+------------------------------------------------------------------+
|                                                                  |
|    +------------------+    +------------------+                   |
|    |  Agent Code      |    |  Agent Code      |                   |
|    |  (User/LLM Gen)  |    |  (User/LLM Gen)  |                   |
|    +--------+---------+    +--------+---------+                   |
|             |                       |                             |
|             v                       v                             |
|    +--------------------------------------------------+          |
|    |              L02 Agent Runtime Layer             |          |
|    |  +------------+  +------------+  +------------+  |          |
|    |  | Agent      |  | Lifecycle  |  | Fleet      |  |          |
|    |  | Executor   |  | Manager    |  | Manager    |  |          |
|    |  +------------+  +------------+  +------------+  |          |
|    |  +------------+  +------------+  +------------+  |          |
|    |  | Sandbox    |  | Resource   |  | Health     |  |          |
|    |  | Manager    |  | Manager    |  | Monitor    |  |          |
|    |  +------------+  +------------+  +------------+  |          |
|    |  +------------+  +------------+                  |          |
|    |  | Session    |  | Document   |                  |          |
|    |  | Bridge     |  | Bridge     |                  |          |
|    |  +------------+  +------------+                  |          |
|    +-------------------------+------------------------+          |
|                              |                                   |
|         +--------------------+--------------------+               |
|         |                    |                    |               |
|         v                    v                    v               |
|    +----------+    +-------------------+    +----------+          |
|    |   L00    |    |    L01 v4.0       |    |   L04    |          |
|    | Infra    |    | Agentic Data      |    | Model    |          |
|    | Layer    |    | Layer             |    | Gateway  |          |
|    |          |    |                   |    |          |          |
|    | Runtime  |    | Phase 15: Docs    |    | Infer-   |          |
|    | Classes  |    | Phase 16: Session |    | ence     |          |
|    | Network  |    | Event Store       |    | Service  |          |
|    | Storage  |    | DID Registry      |    |          |          |
|    +----------+    +-------------------+    +----------+          |
|                                                                  |
+------------------------------------------------------------------+
```

## 1.4 Design Principles

| ID | Principle | Description |
|----|-----------|-------------|
| DP-01 | **Isolation by Default** | All agent code executes within sandboxed environments. No direct host access. |
| DP-02 | **Tiered Trust Model** | Sandbox technology selection (runc/gVisor/Kata) based on code trust level. |
| DP-03 | **Checkpointable Execution** | Agent state must be persistable at any point for recovery and migration. |
| DP-04 | **Resource Bounded** | Every agent has explicit CPU, memory, and token limits enforced by the runtime. |
| DP-05 | **Event-Driven Integration** | All significant state changes emit events to L01 Event Store. |
| DP-06 | **Graph-Based Workflows** | Support cyclic execution graphs, not just linear pipelines. |
| DP-07 | **BC-1: Sandbox Nesting** | L02 sandboxes nest within L00 infrastructure boundaries (RuntimeClass). |

---

# Section 2: Scope Definition

## 2.1 In Scope

| Capability | Description | Components |
|------------|-------------|------------|
| Agent Execution | Execute agent code with tool invocation support | Agent Executor, Sandbox Manager |
| Lifecycle Management | Spawn, suspend, resume, checkpoint, terminate operations | Lifecycle Manager |
| Sandbox Management | Configure and manage gVisor/Kata/runc sandboxes | Sandbox Manager |
| Resource Management | Enforce CPU/memory/token quotas, track consumption | Resource Manager |
| Health Monitoring | Liveness/readiness probes, agent-specific metrics | Health Monitor |
| Fleet Operations | Horizontal scaling, warm pools, graceful drain | Fleet Manager |
| State Persistence | Checkpoint and restore agent state | State Manager, SessionBridge |
| Document Queries | Access authoritative documents from L01 Phase 15 | DocumentBridge |
| Model Integration | Route inference requests to L04 | ModelBridge |
| Multi-Agent Coordination | Supervisor patterns, sequential/parallel workflows | Workflow Engine |

## 2.2 Out of Scope

| Capability | Owning Layer | Rationale |
|------------|--------------|-----------|
| Kubernetes cluster management | L00 Infrastructure | Infrastructure primitive |
| Network policy enforcement | L00 Infrastructure | L00 configures, L02 requests |
| Persistent storage provisioning | L00 Infrastructure | L00 provides PVCs |
| LLM inference execution | L04 Model Gateway | L02 routes requests only |
| Model selection and routing | L04 Model Gateway | L04 owns model registry |
| Token counting and billing | L04 Model Gateway | L04 reports, L02 tracks |
| Event store implementation | L01 Data Layer | L02 emits, L01 stores |
| Session state database | L01 Data Layer Phase 16 | L02 uses via SessionBridge |
| Document consolidation | L01 Data Layer Phase 15 | L02 queries via DocumentBridge |
| DID issuance and management | L01 Data Layer | L02 retrieves, L01 manages |
| Agent business logic | Application Layer | L02 executes, app defines |

## 2.3 Boundary Decisions

### BC-1: Sandbox Nesting

**Decision:** L02 sandboxes nest within L00 RuntimeClass boundaries.

**Rationale:** L00 Infrastructure provides the Kubernetes RuntimeClass abstraction (gVisor, Kata, runc). L02 selects the appropriate RuntimeClass based on agent trust level but does not implement sandbox technology directly.

**Implementation:**
- L02 specifies `runtimeClassName` in Pod spec
- L00 enforces the runtime selection
- L02 validates runtime availability before spawn

### OC-1: No Direct Inter-Agent Messaging

**Decision:** L02 does not provide direct agent-to-agent messaging.

**Rationale:** Agent communication should use explicit, auditable channels via L01 Event Store. Direct messaging bypasses audit requirements and creates coupling.

**Implementation:**
- Agents emit events to L01 Event Store
- Supervisor patterns coordinate via Lifecycle Manager
- No shared memory or direct IPC between agents

---

# Section 3: Architecture

## 3.1 Component Diagram

```
+------------------------------------------------------------------+
|                    L02 Agent Runtime Layer                        |
|                                                                  |
|  +------------------------+     +------------------------+        |
|  |    Agent Executor      |<--->|   Workflow Engine      |        |
|  |                        |     |                        |        |
|  | - Execute agent code   |     | - Graph execution      |        |
|  | - Tool invocation      |     | - Conditional routing  |        |
|  | - Context management   |     | - Parallel/sequential  |        |
|  +----------+-------------+     +------------------------+        |
|             |                                                     |
|             v                                                     |
|  +----------+-------------+     +------------------------+        |
|  |   Lifecycle Manager    |<--->|    State Manager       |        |
|  |                        |     |                        |        |
|  | - Spawn/terminate      |     | - Checkpointing        |        |
|  | - Suspend/resume       |     | - Context serialization|        |
|  | - Restart policies     |     | - Recovery             |        |
|  +----------+-------------+     +----------+-------------+        |
|             |                              |                      |
|             v                              v                      |
|  +----------+-------------+     +----------+-------------+        |
|  |   Sandbox Manager      |     |   SessionBridge        |        |
|  |                        |     |                        |        |
|  | - RuntimeClass select  |     | - L01 Phase 16 client  |        |
|  | - Security policies    |     | - Heartbeat            |        |
|  | - Isolation config     |     | - Checkpoint persist   |        |
|  +------------------------+     +------------------------+        |
|                                                                  |
|  +------------------------+     +------------------------+        |
|  |   Resource Manager     |     |   DocumentBridge       |        |
|  |                        |     |                        |        |
|  | - CPU/memory quotas    |     | - L01 Phase 15 client  |        |
|  | - Token budgets        |     | - Source of truth      |        |
|  | - Usage tracking       |     | - Claim verification   |        |
|  +------------------------+     +------------------------+        |
|                                                                  |
|  +------------------------+     +------------------------+        |
|  |    Health Monitor      |     |    Fleet Manager       |        |
|  |                        |     |                        |        |
|  | - Liveness probes      |     | - Horizontal scaling   |        |
|  | - Readiness probes     |     | - Warm pool mgmt       |        |
|  | - Agent metrics        |     | - Graceful drain       |        |
|  +------------------------+     +------------------------+        |
|                                                                  |
|  +------------------------+                                       |
|  |    ModelBridge         |                                       |
|  |                        |                                       |
|  | - L04 inference client |                                       |
|  | - Token tracking       |                                       |
|  | - Streaming support    |                                       |
|  +------------------------+                                       |
|                                                                  |
+------------------------------------------------------------------+
```

## 3.2 Component Inventory

| Component | Purpose | Technology | Dependencies |
|-----------|---------|------------|--------------|
| Agent Executor | Execute agent code with tool support | Python 3.11+, asyncio | Sandbox Manager, Resource Manager |
| Workflow Engine | Graph-based workflow execution | State machine, DAG scheduler | Agent Executor, Lifecycle Manager |
| Lifecycle Manager | Agent lifecycle operations | Kubernetes client, async | Sandbox Manager, State Manager |
| State Manager | Checkpoint and recovery | PostgreSQL, Redis | SessionBridge |
| Sandbox Manager | Configure isolation | Kubernetes API | L00 RuntimeClass |
| SessionBridge | L01 Phase 16 integration | gRPC client | L01 Session Orchestrator |
| DocumentBridge | L01 Phase 15 integration | gRPC client | L01 Document Manager |
| Resource Manager | Quota enforcement | cgroups, K8s limits | ModelBridge |
| Health Monitor | Health check management | Prometheus, K8s probes | Agent Executor |
| Fleet Manager | Scaling operations | K8s HPA, custom controller | Lifecycle Manager |
| ModelBridge | L04 integration | gRPC client | L04 Model Gateway |

## 3.3 Component Specifications

### 3.3.1 Agent Executor

**Purpose:** Execute agent code within the configured sandbox, managing tool invocations and context.

**Technology:** Python 3.11+ with asyncio for concurrent execution. Supports both synchronous and async agent code.

**Configuration Schema:**
```yaml
agent_executor:
  max_concurrent_tools: 10
  tool_timeout_seconds: 300
  context_window_tokens: 128000
  enable_streaming: true
  retry_on_tool_failure: true
  max_tool_retries: 3
```

**Dependencies:**
- Sandbox Manager: Execution environment
- Resource Manager: Budget enforcement
- ModelBridge: LLM inference
- DocumentBridge: Document queries

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2001 | TOOL_INVOCATION_FAILED | Tool execution failed |
| E2002 | TOOL_TIMEOUT | Tool exceeded timeout |
| E2003 | CONTEXT_OVERFLOW | Context window exceeded |
| E2004 | STREAMING_ERROR | Stream processing failed |

---

### 3.3.2 Workflow Engine

**Purpose:** Execute graph-based agent workflows with conditional routing and parallel execution.

**Technology:** State machine implementation supporting cyclic graphs. Based on LangGraph patterns.

**Configuration Schema:**
```yaml
workflow_engine:
  max_graph_depth: 100
  max_parallel_branches: 10
  cycle_detection: true
  checkpoint_on_node_complete: true
  timeout_seconds: 3600
```

**Dependencies:**
- Agent Executor: Node execution
- Lifecycle Manager: Graph lifecycle
- State Manager: Graph state persistence

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2010 | GRAPH_CYCLE_DETECTED | Infinite loop detected |
| E2011 | GRAPH_DEPTH_EXCEEDED | Max depth exceeded |
| E2012 | NODE_EXECUTION_FAILED | Node failed execution |
| E2013 | BRANCH_TIMEOUT | Parallel branch timeout |

---

### 3.3.3 Lifecycle Manager

**Purpose:** Manage the complete lifecycle of agent instances from spawn to termination.

**Technology:** Kubernetes client-go with custom controller for agent pods.

**Configuration Schema:**
```yaml
lifecycle_manager:
  spawn_timeout_seconds: 60
  graceful_shutdown_seconds: 30
  restart_policy: ExponentialBackoff
  max_restart_count: 5
  restart_delay_seconds: [1, 2, 4, 8, 16]
  enable_suspend: true
  suspend_idle_after_seconds: 300
```

**Dependencies:**
- Sandbox Manager: Pod creation
- State Manager: State persistence
- SessionBridge: Session lifecycle
- Fleet Manager: Scaling coordination

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2020 | SPAWN_FAILED | Agent spawn failed |
| E2021 | SPAWN_TIMEOUT | Spawn exceeded timeout |
| E2022 | TERMINATE_FAILED | Clean termination failed |
| E2023 | SUSPEND_FAILED | Suspend operation failed |
| E2024 | RESUME_FAILED | Resume from suspend failed |
| E2025 | RESTART_LIMIT_EXCEEDED | Max restarts reached |

---

### 3.3.4 State Manager

**Purpose:** Manage agent state checkpointing, serialization, and recovery.

**Technology:** PostgreSQL for durable checkpoints, Redis for hot state.

**Configuration Schema:**
```yaml
state_manager:
  checkpoint_backend: postgresql
  hot_state_backend: redis
  auto_checkpoint_interval_seconds: 60
  max_checkpoint_size_mb: 100
  checkpoint_compression: gzip
  retention_days: 30
```

**Dependencies:**
- SessionBridge: Session state storage
- PostgreSQL: Durable storage
- Redis: Hot state cache

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2030 | CHECKPOINT_FAILED | Checkpoint creation failed |
| E2031 | CHECKPOINT_TOO_LARGE | Exceeds size limit |
| E2032 | RESTORE_FAILED | State restoration failed |
| E2033 | CHECKPOINT_CORRUPTED | Checkpoint data invalid |

---

### 3.3.5 Sandbox Manager

**Purpose:** Configure and manage agent sandbox isolation.

**Technology:** Kubernetes RuntimeClass API, security contexts.

**Configuration Schema:**
```yaml
sandbox_manager:
  default_runtime_class: gvisor
  trust_level_mapping:
    trusted: runc
    standard: gvisor
    untrusted: kata
  security_context:
    run_as_non_root: true
    read_only_root_filesystem: true
    allow_privilege_escalation: false
  network_policy: isolated
```

**Dependencies:**
- L00 Infrastructure: RuntimeClass provisioning
- Lifecycle Manager: Pod specification

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2040 | RUNTIME_CLASS_UNAVAILABLE | Requested runtime not available |
| E2041 | SANDBOX_CREATION_FAILED | Sandbox setup failed |
| E2042 | SECURITY_POLICY_VIOLATION | Security context violation |

---

### 3.3.6 SessionBridge

**Purpose:** Integrate with L01 Phase 16 Session Orchestration for session lifecycle and state persistence.

**Technology:** gRPC client to L01 Phase 16 services.

**Configuration Schema:**
```yaml
session_bridge:
  endpoint: "l01-session-orchestrator:50051"
  heartbeat_interval_seconds: 30
  heartbeat_timeout_seconds: 5
  retry_policy:
    max_retries: 3
    backoff_multiplier: 2
  enable_recovery_check: true
```

**Dependencies:**
- L01 Phase 16: Session Orchestrator service
- State Manager: Local state coordination

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2050 | SESSION_START_FAILED | Failed to start session |
| E2051 | HEARTBEAT_FAILED | Heartbeat not acknowledged |
| E2052 | SNAPSHOT_SAVE_FAILED | Context snapshot failed |
| E2053 | RECOVERY_CHECK_FAILED | Recovery check failed |
| E2054 | SESSION_NOT_FOUND | Session ID not found |

---

### 3.3.7 DocumentBridge

**Purpose:** Integrate with L01 Phase 15 Document Management for authoritative document queries.

**Technology:** gRPC client to L01 Phase 15 services.

**Configuration Schema:**
```yaml
document_bridge:
  endpoint: "l01-document-manager:50052"
  default_confidence_threshold: 0.7
  max_sources: 5
  cache_ttl_seconds: 300
  verify_claims: true
```

**Dependencies:**
- L01 Phase 15: Document Manager service
- Agent Executor: Query invocation

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2060 | DOCUMENT_QUERY_FAILED | Query execution failed |
| E2061 | NO_AUTHORITATIVE_SOURCE | No source of truth found |
| E2062 | CLAIM_VERIFICATION_FAILED | Claim could not be verified |
| E2063 | DOCUMENT_NOT_FOUND | Document ID not found |

---

### 3.3.8 Resource Manager

**Purpose:** Enforce CPU, memory, and token quotas for agent instances.

**Technology:** Kubernetes resource limits, custom token tracking.

**Configuration Schema:**
```yaml
resource_manager:
  default_limits:
    cpu: "2"
    memory: "2Gi"
    tokens_per_hour: 100000
  enforcement:
    cpu: hard
    memory: hard
    tokens: soft_then_hard
  token_budget_action: suspend  # warn | throttle | suspend | terminate
  usage_report_interval_seconds: 60
```

**Dependencies:**
- L00 Infrastructure: cgroups enforcement
- ModelBridge: Token usage reporting
- L01 Event Store: Usage event emission

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2070 | CPU_LIMIT_EXCEEDED | CPU quota exceeded |
| E2071 | MEMORY_LIMIT_EXCEEDED | Memory quota exceeded |
| E2072 | TOKEN_BUDGET_EXCEEDED | Token budget exhausted |
| E2073 | QUOTA_UPDATE_FAILED | Failed to update quota |

---

### 3.3.9 Health Monitor

**Purpose:** Monitor agent health via probes and collect agent-specific metrics.

**Technology:** Kubernetes probes, Prometheus metrics.

**Configuration Schema:**
```yaml
health_monitor:
  liveness_probe:
    path: /healthz
    interval_seconds: 10
    timeout_seconds: 5
    failure_threshold: 3
  readiness_probe:
    path: /ready
    interval_seconds: 5
    timeout_seconds: 3
    failure_threshold: 2
  metrics:
    error_rate_window_seconds: 300
    latency_buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
  stuck_agent_timeout_seconds: 600
```

**Dependencies:**
- Agent Executor: Probe endpoints
- Prometheus: Metrics storage
- Lifecycle Manager: Restart triggers

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2080 | LIVENESS_CHECK_FAILED | Agent not alive |
| E2081 | READINESS_CHECK_FAILED | Agent not ready |
| E2082 | AGENT_STUCK | No progress detected |
| E2083 | METRICS_COLLECTION_FAILED | Failed to collect metrics |

---

### 3.3.10 Fleet Manager

**Purpose:** Manage horizontal scaling, warm pools, and graceful drain operations.

**Technology:** Kubernetes HPA, custom controller for warm pools.

**Configuration Schema:**
```yaml
fleet_manager:
  min_replicas: 1
  max_replicas: 100
  target_cpu_utilization: 70
  scale_up_stabilization_seconds: 60
  scale_down_stabilization_seconds: 300
  warm_pool:
    enabled: true
    size: 5
    runtime_class: gvisor
    refresh_interval_seconds: 3600
  graceful_drain:
    timeout_seconds: 30
    checkpoint_before_drain: true
```

**Dependencies:**
- Lifecycle Manager: Instance management
- State Manager: Pre-drain checkpointing
- L00 Infrastructure: HPA, PDB

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2090 | SCALE_UP_FAILED | Failed to scale up |
| E2091 | SCALE_DOWN_FAILED | Failed to scale down |
| E2092 | WARM_POOL_EXHAUSTED | No warm instances available |
| E2093 | DRAIN_TIMEOUT | Graceful drain exceeded timeout |

---

### 3.3.11 ModelBridge

**Purpose:** Integrate with L04 Model Gateway for LLM inference requests.

**Technology:** gRPC client to L04 services, streaming support.

**Configuration Schema:**
```yaml
model_bridge:
  endpoint: "l04-model-gateway:50053"
  default_model: "claude-3-opus"
  streaming_enabled: true
  request_timeout_seconds: 300
  retry_policy:
    max_retries: 3
    retry_on: [UNAVAILABLE, RESOURCE_EXHAUSTED]
```

**Dependencies:**
- L04 Model Gateway: Inference service
- Resource Manager: Token tracking
- Agent Executor: Request origination

**Error Codes:**
| Code | Name | Description |
|------|------|-------------|
| E2100 | INFERENCE_FAILED | LLM inference failed |
| E2101 | MODEL_UNAVAILABLE | Requested model not available |
| E2102 | INFERENCE_TIMEOUT | Request exceeded timeout |
| E2103 | RATE_LIMITED | Provider rate limit hit |

---

# Section 4: Interfaces

## 4.1 Provided Interfaces

### 4.1.1 AgentRuntime Protocol

```python
from typing import Protocol, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class AgentState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"

@dataclass
class AgentConfig:
    agent_id: str
    trust_level: str  # trusted | standard | untrusted
    resource_limits: ResourceLimits
    tools: list[ToolDefinition]
    environment: dict[str, str]

@dataclass
class ResourceLimits:
    cpu: str
    memory: str
    tokens_per_hour: int

@dataclass
class SpawnResult:
    agent_id: str
    session_id: str
    state: AgentState
    sandbox_type: str

class AgentRuntime(Protocol):
    """Primary interface for agent lifecycle management."""

    async def spawn(
        self,
        config: AgentConfig,
        initial_context: Optional[dict] = None
    ) -> SpawnResult:
        """Spawn a new agent instance."""
        ...

    async def terminate(
        self,
        agent_id: str,
        reason: str,
        force: bool = False
    ) -> None:
        """Terminate an agent instance."""
        ...

    async def suspend(
        self,
        agent_id: str,
        checkpoint: bool = True
    ) -> str:
        """Suspend agent and optionally checkpoint. Returns checkpoint_id."""
        ...

    async def resume(
        self,
        agent_id: str,
        checkpoint_id: Optional[str] = None
    ) -> AgentState:
        """Resume a suspended agent."""
        ...

    async def get_state(
        self,
        agent_id: str
    ) -> AgentState:
        """Get current agent state."""
        ...

    async def execute(
        self,
        agent_id: str,
        input_message: str
    ) -> AsyncIterator[str]:
        """Execute agent with input, streaming response."""
        ...
```

### 4.1.2 WorkflowEngine Protocol

```python
@dataclass
class WorkflowNode:
    node_id: str
    node_type: str  # agent | conditional | parallel | end
    config: dict
    edges: list[str]

@dataclass
class WorkflowGraph:
    graph_id: str
    nodes: list[WorkflowNode]
    entry_node: str

@dataclass
class WorkflowExecution:
    execution_id: str
    graph_id: str
    current_node: str
    state: dict

class WorkflowEngine(Protocol):
    """Interface for graph-based workflow execution."""

    async def register_graph(
        self,
        graph: WorkflowGraph
    ) -> str:
        """Register a workflow graph. Returns graph_id."""
        ...

    async def start_execution(
        self,
        graph_id: str,
        input_data: dict
    ) -> WorkflowExecution:
        """Start workflow execution."""
        ...

    async def get_execution_state(
        self,
        execution_id: str
    ) -> WorkflowExecution:
        """Get current execution state."""
        ...

    async def resume_execution(
        self,
        execution_id: str,
        node_output: Optional[dict] = None
    ) -> WorkflowExecution:
        """Resume execution from current node."""
        ...
```

### 4.1.3 FleetManager Protocol

```python
@dataclass
class FleetStatus:
    total_instances: int
    running: int
    suspended: int
    warm_pool_size: int
    pending_scale_operations: int

@dataclass
class ScaleRequest:
    target_replicas: int
    reason: str
    priority: str  # normal | high | urgent

class FleetManager(Protocol):
    """Interface for fleet scaling operations."""

    async def get_status(self) -> FleetStatus:
        """Get current fleet status."""
        ...

    async def scale(
        self,
        request: ScaleRequest
    ) -> None:
        """Request fleet scaling."""
        ...

    async def drain_instance(
        self,
        agent_id: str,
        timeout_seconds: int = 30
    ) -> None:
        """Gracefully drain an instance."""
        ...

    async def warm_pool_size(
        self,
        size: int
    ) -> None:
        """Set warm pool target size."""
        ...
```

## 4.2 Required Interfaces

### 4.2.1 L00 Infrastructure Requirements

| Interface | Usage | Required By |
|-----------|-------|-------------|
| RuntimeClass API | Sandbox selection | Sandbox Manager |
| Pod API | Agent instance creation | Lifecycle Manager |
| ResourceQuota API | Namespace limits | Resource Manager |
| NetworkPolicy API | Agent isolation | Sandbox Manager |
| PriorityClass API | Scheduling priority | Lifecycle Manager |
| PodDisruptionBudget API | Availability | Fleet Manager |
| HorizontalPodAutoscaler API | Auto-scaling | Fleet Manager |

### 4.2.2 L01 Data Layer Requirements

| Interface | Usage | Required By |
|-----------|-------|-------------|
| Event Store | Event emission | All components |
| DID Registry | Agent identity | Lifecycle Manager |
| Session Orchestrator (Phase 16) | Session lifecycle | SessionBridge |
| Document Manager (Phase 15) | Document queries | DocumentBridge |
| Config Service | Runtime configuration | All components |

### 4.2.3 L04 Model Gateway Requirements

| Interface | Usage | Required By |
|-----------|-------|-------------|
| InferenceService | LLM requests | ModelBridge |
| TokenTracker | Usage reporting | Resource Manager |
| ModelRegistry | Available models | ModelBridge |

## 4.3 Events Published

All events follow CloudEvents 1.0 specification and are emitted to L01 Event Store.

```yaml
# Agent Lifecycle Events
agent.spawned:
  type: agent.spawned
  source: l02-agent-runtime
  datacontenttype: application/json
  data:
    agent_id: string
    session_id: string
    sandbox_type: string  # runc | gvisor | kata
    resource_limits:
      cpu: string
      memory: string
      tokens_per_hour: integer
    trust_level: string
    timestamp: datetime

agent.terminated:
  type: agent.terminated
  source: l02-agent-runtime
  data:
    agent_id: string
    session_id: string
    reason: string  # completed | error | timeout | resource_exceeded | user_request
    final_state: object
    resource_usage:
      cpu_seconds: number
      memory_peak_mb: number
      tokens_consumed: integer
    duration_seconds: number

agent.suspended:
  type: agent.suspended
  source: l02-agent-runtime
  data:
    agent_id: string
    session_id: string
    checkpoint_id: string
    reason: string

agent.resumed:
  type: agent.resumed
  source: l02-agent-runtime
  data:
    agent_id: string
    session_id: string
    checkpoint_id: string

# Health Events
agent.health.changed:
  type: agent.health.changed
  source: l02-agent-runtime
  data:
    agent_id: string
    previous_state: string
    new_state: string
    reason: string

agent.health.stuck:
  type: agent.health.stuck
  source: l02-agent-runtime
  data:
    agent_id: string
    stuck_duration_seconds: number
    last_activity: datetime

# Resource Events
agent.resource.warning:
  type: agent.resource.warning
  source: l02-agent-runtime
  data:
    agent_id: string
    resource_type: string  # cpu | memory | tokens
    current_usage: number
    limit: number
    threshold_percent: number

agent.resource.exceeded:
  type: agent.resource.exceeded
  source: l02-agent-runtime
  data:
    agent_id: string
    resource_type: string
    limit: number
    actual: number
    action_taken: string

# Checkpoint Events
agent.checkpoint.created:
  type: agent.checkpoint.created
  source: l02-agent-runtime
  data:
    agent_id: string
    checkpoint_id: string
    storage_location: string
    size_bytes: integer

agent.checkpoint.restored:
  type: agent.checkpoint.restored
  source: l02-agent-runtime
  data:
    agent_id: string
    checkpoint_id: string
    restore_duration_ms: integer

# Fleet Events
fleet.scaled:
  type: fleet.scaled
  source: l02-agent-runtime
  data:
    previous_size: integer
    new_size: integer
    reason: string
    trigger: string  # auto | manual
```

## 4.4 Events Consumed

| Event Type | Source | Handler | Action |
|------------|--------|---------|--------|
| session.timeout | L01 Phase 16 | Lifecycle Manager | Terminate agent |
| config.updated | L01 Config Service | All components | Reload configuration |
| model.unavailable | L04 Model Gateway | ModelBridge | Switch to fallback |

## 4.5 Phase 15 Integration Interface (DocumentBridge)

```python
@dataclass
class SourceOfTruthQuery:
    query: str
    scope: Optional[list[str]] = None
    confidence_threshold: float = 0.7
    max_sources: int = 5
    query_type: str = "factual"  # factual | procedural | conceptual

@dataclass
class SourceOfTruthResponse:
    answer: str
    confidence: float
    sources: list[DocumentSource]
    conflicts: Optional[list[ConflictInfo]] = None

@dataclass
class DocumentSource:
    document_id: str
    title: str
    excerpt: str
    authority_level: int
    last_updated: datetime

@dataclass
class ClaimVerification:
    claim: str
    verified: bool
    confidence: float
    supporting_sources: list[DocumentSource]
    conflicting_sources: Optional[list[DocumentSource]] = None

class DocumentBridge(Protocol):
    """Interface for L01 Phase 15 Document Management integration."""

    async def query_source_of_truth(
        self,
        query: SourceOfTruthQuery
    ) -> SourceOfTruthResponse:
        """Query authoritative documents."""
        ...

    async def verify_claim(
        self,
        claim: str,
        scope: Optional[list[str]] = None
    ) -> ClaimVerification:
        """Verify a claim against document store."""
        ...

    async def ingest_document(
        self,
        content: str,
        document_type: str,
        metadata: dict
    ) -> str:
        """Store agent-generated document. Returns document_id."""
        ...

    async def get_document(
        self,
        document_id: str
    ) -> dict:
        """Retrieve document by ID."""
        ...
```

## 4.6 Phase 16 Integration Interface (SessionBridge)

```python
@dataclass
class SessionMetadata:
    agent_id: str
    agent_type: str
    tenant_id: str
    tags: dict[str, str]

@dataclass
class HeartbeatResponse:
    acknowledged: bool
    session_valid: bool
    server_time: datetime

@dataclass
class ExecutionContext:
    session_id: str
    agent_id: str
    state: dict
    memory: dict
    tools: list[dict]
    conversation_history: list[dict]
    working_directory: Optional[str] = None
    environment_variables: Optional[dict] = None

@dataclass
class RecoveryInfo:
    session_id: str
    agent_id: str
    last_heartbeat: datetime
    last_checkpoint: dict
    recovery_prompt: str
    tool_history: list[dict]

class SessionBridge(Protocol):
    """Interface for L01 Phase 16 Session Orchestration integration."""

    async def start_session(
        self,
        metadata: SessionMetadata
    ) -> str:
        """Start new session. Returns session_id."""
        ...

    async def end_session(
        self,
        session_id: str,
        reason: str
    ) -> None:
        """End session."""
        ...

    async def heartbeat(
        self,
        session_id: str
    ) -> HeartbeatResponse:
        """Send heartbeat signal."""
        ...

    async def save_context_snapshot(
        self,
        session_id: str,
        context: ExecutionContext
    ) -> str:
        """Save context snapshot. Returns snapshot_id."""
        ...

    async def load_context(
        self,
        session_id: str
    ) -> ExecutionContext:
        """Load current context."""
        ...

    async def check_recovery(
        self,
        agent_id: Optional[str] = None
    ) -> list[RecoveryInfo]:
        """Check for sessions needing recovery."""
        ...

    async def create_checkpoint(
        self,
        session_id: str,
        label: str,
        description: Optional[str] = None
    ) -> str:
        """Create named checkpoint. Returns checkpoint_id."""
        ...

    async def rollback_to(
        self,
        session_id: str,
        checkpoint_id: str
    ) -> ExecutionContext:
        """Rollback to checkpoint."""
        ...
```

---

# Section 5: Data Model

## 5.1 Owned Entities

### 5.1.1 AgentInstance

```yaml
AgentInstance:
  description: Represents a running or suspended agent instance
  fields:
    agent_id:
      type: string
      format: uuid
      description: Unique identifier for this agent instance
    session_id:
      type: string
      format: uuid
      description: Associated session in L01 Phase 16
    state:
      type: enum
      values: [pending, running, suspended, terminated, failed]
      description: Current lifecycle state
    config:
      type: AgentConfig
      description: Agent configuration at spawn time
    sandbox:
      type: SandboxConfiguration
      description: Sandbox settings
    resource_usage:
      type: ResourceUsage
      description: Current resource consumption
    created_at:
      type: datetime
      description: Spawn timestamp
    updated_at:
      type: datetime
      description: Last state change
    terminated_at:
      type: datetime
      nullable: true
      description: Termination timestamp
```

### 5.1.2 SandboxConfiguration

```yaml
SandboxConfiguration:
  description: Sandbox isolation settings for an agent
  fields:
    runtime_class:
      type: string
      enum: [runc, gvisor, kata, kata-cc]
      description: Kubernetes RuntimeClass
    trust_level:
      type: string
      enum: [trusted, standard, untrusted, confidential]
      description: Code trust classification
    security_context:
      type: object
      properties:
        run_as_non_root:
          type: boolean
          default: true
        read_only_root_filesystem:
          type: boolean
          default: true
        allow_privilege_escalation:
          type: boolean
          default: false
        capabilities:
          type: array
          items: string
          default: []
    network_policy:
      type: string
      enum: [isolated, restricted, allow_egress]
      description: Network isolation level
    resource_limits:
      type: ResourceLimits
      description: Hard resource caps
```

### 5.1.3 ResourceQuota

```yaml
ResourceQuota:
  description: Resource allocation for an agent or tenant
  fields:
    quota_id:
      type: string
      format: uuid
    scope:
      type: string
      enum: [agent, tenant, namespace]
    target_id:
      type: string
      description: Agent ID, tenant ID, or namespace name
    limits:
      type: object
      properties:
        cpu:
          type: string
          description: CPU limit (e.g., "2")
        memory:
          type: string
          description: Memory limit (e.g., "2Gi")
        tokens_per_hour:
          type: integer
          description: Token budget per hour
        tokens_per_day:
          type: integer
          description: Token budget per day
    usage:
      type: object
      properties:
        cpu_seconds:
          type: number
        memory_peak_mb:
          type: number
        tokens_consumed:
          type: integer
    reset_at:
      type: datetime
      description: Next quota reset time
```

### 5.1.4 Checkpoint

```yaml
Checkpoint:
  description: Saved agent state for recovery
  fields:
    checkpoint_id:
      type: string
      format: uuid
    agent_id:
      type: string
      format: uuid
    session_id:
      type: string
      format: uuid
    label:
      type: string
      nullable: true
      description: Human-readable label
    checkpoint_type:
      type: string
      enum: [auto, manual, pre_suspend, pre_drain]
    storage_location:
      type: string
      description: URI to checkpoint data
    size_bytes:
      type: integer
    created_at:
      type: datetime
    expires_at:
      type: datetime
      nullable: true
```

### 5.1.5 HealthStatus

```yaml
HealthStatus:
  description: Agent health monitoring state
  fields:
    agent_id:
      type: string
      format: uuid
    liveness:
      type: string
      enum: [healthy, unhealthy, unknown]
    readiness:
      type: string
      enum: [ready, not_ready, unknown]
    last_liveness_check:
      type: datetime
    last_readiness_check:
      type: datetime
    consecutive_failures:
      type: integer
    metrics:
      type: object
      properties:
        error_rate:
          type: number
          description: Errors per 5 minutes
        avg_latency_ms:
          type: number
        escalation_rate:
          type: number
          description: Handoffs to human per hour
```

## 5.2 Configuration Schemas

### 5.2.1 Agent Spawn Configuration (JSON Schema 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-runtime.io/schemas/agent-spawn-config.json",
  "title": "AgentSpawnConfiguration",
  "type": "object",
  "required": ["agent_id", "trust_level"],
  "properties": {
    "agent_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the agent"
    },
    "trust_level": {
      "type": "string",
      "enum": ["trusted", "standard", "untrusted", "confidential"],
      "description": "Code trust classification"
    },
    "resource_limits": {
      "type": "object",
      "properties": {
        "cpu": {
          "type": "string",
          "pattern": "^[0-9]+m?$",
          "default": "2"
        },
        "memory": {
          "type": "string",
          "pattern": "^[0-9]+(Mi|Gi)$",
          "default": "2Gi"
        },
        "tokens_per_hour": {
          "type": "integer",
          "minimum": 0,
          "default": 100000
        }
      }
    },
    "tools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "description"],
        "properties": {
          "name": {"type": "string"},
          "description": {"type": "string"},
          "parameters": {"type": "object"}
        }
      }
    },
    "environment": {
      "type": "object",
      "additionalProperties": {"type": "string"}
    },
    "initial_context": {
      "type": "object",
      "description": "Initial execution context"
    },
    "recovery_checkpoint_id": {
      "type": "string",
      "format": "uuid",
      "description": "Checkpoint to restore from"
    }
  }
}
```

### 5.2.2 Fleet Configuration (JSON Schema 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-runtime.io/schemas/fleet-config.json",
  "title": "FleetConfiguration",
  "type": "object",
  "properties": {
    "min_replicas": {
      "type": "integer",
      "minimum": 0,
      "default": 1
    },
    "max_replicas": {
      "type": "integer",
      "minimum": 1,
      "default": 100
    },
    "target_cpu_utilization": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 70
    },
    "scale_up_stabilization_seconds": {
      "type": "integer",
      "minimum": 0,
      "default": 60
    },
    "scale_down_stabilization_seconds": {
      "type": "integer",
      "minimum": 0,
      "default": 300
    },
    "warm_pool": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean", "default": true},
        "size": {"type": "integer", "minimum": 0, "default": 5},
        "runtime_class": {"type": "string", "default": "gvisor"},
        "refresh_interval_seconds": {"type": "integer", "default": 3600}
      }
    },
    "graceful_drain": {
      "type": "object",
      "properties": {
        "timeout_seconds": {"type": "integer", "default": 30},
        "checkpoint_before_drain": {"type": "boolean", "default": true}
      }
    }
  }
}
```

## 5.3 Data Flows

### 5.3.1 Agent Spawn Flow

```
+------------------+
|  Client Request  |
|  (spawn agent)   |
+--------+---------+
         |
         v
+--------+---------+     +-------------------+
|  L02 Lifecycle   |---->|  L01 Phase 16     |
|  Manager         |     |  start_session()  |
+--------+---------+     +--------+----------+
         |                        |
         |<-----------------------+
         |  session_id
         v
+--------+---------+     +-------------------+
|  L02 Sandbox     |---->|  L00 Infrastructure|
|  Manager         |     |  RuntimeClass     |
+--------+---------+     +--------+----------+
         |                        |
         |<-----------------------+
         |  pod_spec
         v
+--------+---------+     +-------------------+
|  L02 Resource    |---->|  L01 DID Registry |
|  Manager         |     |  get_credentials  |
+--------+---------+     +--------+----------+
         |                        |
         |<-----------------------+
         |  agent_did
         v
+--------+---------+     +-------------------+
|  L02 Agent       |---->|  L01 Event Store  |
|  Executor        |     |  agent.spawned    |
+------------------+     +-------------------+
```

### 5.3.2 Agent Execution Flow

```
+------------------+     +-------------------+
|  Agent Executor  |---->|  L02 Document     |
|  (needs data)    |     |  Bridge           |
+--------+---------+     +--------+----------+
         |                        |
         |                        v
         |               +--------+----------+
         |               |  L01 Phase 15     |
         |               |  get_source_of_   |
         |               |  truth()          |
         |               +--------+----------+
         |                        |
         |<-----------------------+
         |  authoritative_answer
         v
+--------+---------+     +-------------------+
|  Agent Executor  |---->|  L02 Model        |
|  (needs LLM)     |     |  Bridge           |
+--------+---------+     +--------+----------+
         |                        |
         |                        v
         |               +--------+----------+
         |               |  L04 Model        |
         |               |  Gateway          |
         |               +--------+----------+
         |                        |
         |<-----------------------+
         |  inference_response + token_usage
         v
+--------+---------+     +-------------------+
|  L02 Resource    |---->|  L01 Event Store  |
|  Manager         |     |  resource.usage   |
|  (track tokens)  |     |                   |
+------------------+     +-------------------+
```

### 5.3.3 Checkpoint and Recovery Flow

```
+------------------+
|  Checkpoint      |
|  Trigger         |
|  (auto/manual)   |
+--------+---------+
         |
         v
+--------+---------+     +-------------------+
|  L02 State       |---->|  L02 Session      |
|  Manager         |     |  Bridge           |
+--------+---------+     +--------+----------+
         |                        |
         |                        v
         |               +--------+----------+
         |               |  L01 Phase 16     |
         |               |  save_context_    |
         |               |  snapshot()       |
         |               +--------+----------+
         |                        |
         |<-----------------------+
         |  snapshot_id
         v
+--------+---------+     +-------------------+
|  L02 State       |---->|  L01 Event Store  |
|  Manager         |     |  checkpoint.      |
|                  |     |  created          |
+------------------+     +-------------------+

         === Recovery ===

+------------------+
|  Agent Spawn     |
|  (with recovery) |
+--------+---------+
         |
         v
+--------+---------+     +-------------------+
|  L02 Lifecycle   |---->|  L02 Session      |
|  Manager         |     |  Bridge           |
+--------+---------+     +--------+----------+
         |                        |
         |                        v
         |               +--------+----------+
         |               |  L01 Phase 16     |
         |               |  check_recovery() |
         |               +--------+----------+
         |                        |
         |<-----------------------+
         |  recovery_info[]
         v
+--------+---------+     +-------------------+
|  L02 State       |<----|  L01 Phase 16     |
|  Manager         |     |  rollback_to()    |
|  (restore)       |     |                   |
+--------+---------+     +-------------------+
         |
         v
+--------+---------+
|  Agent Executor  |
|  (resume)        |
+------------------+
```

---

# Gap Tracking Table

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| G-001 | Agent Sandbox API Definition | Critical | Section 3 | Sandbox Manager component spec (3.3.5) |
| G-002 | Checkpoint/Restore Protocol | Critical | Section 5 | Checkpoint entity (5.1.4), Data flows (5.3.3) |
| G-003 | SessionBridge Implementation | Critical | Section 3, 4 | SessionBridge component (3.3.6), Interface (4.6) |
| G-004 | DocumentBridge Implementation | Critical | Section 3, 4 | DocumentBridge component (3.3.7), Interface (4.5) |
| G-005 | ModelBridge Token Budget Tracking | Critical | Section 3, 4 | ModelBridge component (3.3.11), Resource Manager (3.3.8) |
| G-007 | RuntimeClass Selection Logic | Critical | Section 3 | Sandbox Manager (3.3.5), trust_level_mapping |
| G-008 | Event Emission Protocol | Critical | Section 4 | Events Published (4.3) - full event catalog |
| G-014 | Graph-Based Workflow Support | High | Section 3, 4 | Workflow Engine (3.3.2), Protocol (4.1.2) |
| G-015 | Multi-Agent Orchestration | High | Section 3 | Workflow Engine with parallel/sequential |
| G-016 | Actor Model Implementation | Medium | Section 3 | Semantic Kernel patterns in Workflow Engine |
| G-017 | Message Routing Protocol | Medium | Section 4 | Events Published/Consumed (4.3, 4.4) |

---

# Section 6: Integration with Data Layer v4.0

## 6.1 Relationship Model

| Integration Point | Direction | L01 Component | L02 Component | Relationship |
|-------------------|-----------|---------------|---------------|--------------|
| Event Emission | L02 -> L01 | Event Store (Phase 1) | All components | Provider |
| DID Retrieval | L02 <- L01 | DID Registry (Phase 1) | Lifecycle Manager | Consumer |
| Context Injection | L02 <- L01 | Context Injector (Phase 4) | Agent Executor | Consumer |
| Config Retrieval | L02 <- L01 | Config Service (Phase 11) | All components | Consumer |
| Memory Access | L02 <-> L01 | Memory Manager (Phase 10) | Agent Executor | Peer |
| Task Queue | L02 <-> L01 | Task Queue (Phase 8) | Fleet Manager | Peer |
| Lifecycle State | L02 <-> L01 | Lifecycle Manager (Phase 9) | Lifecycle Manager | Peer |
| Document Query | L02 <- L01 | Document Manager (Phase 15) | DocumentBridge | Consumer |
| Session Management | L02 <-> L01 | Session Orchestrator (Phase 16) | SessionBridge | Peer |

## 6.2 Agent Identity Integration (Phase 1 - DID Registry)

### 6.2.1 DID Retrieval Pattern

Each agent instance receives a Decentralized Identifier (DID) from L01 at spawn time. The DID serves as the cryptographic identity for the agent, enabling verifiable credentials and audit trails.

```python
# At agent spawn time
async def retrieve_agent_identity(agent_id: str) -> AgentIdentity:
    """Retrieve or create DID for agent from L01 DID Registry."""
    did_response = await l01_did_registry.get_or_create_did(
        subject_type="agent",
        subject_id=agent_id,
        key_type="Ed25519",
        capabilities=["sign", "verify"]
    )
    return AgentIdentity(
        did=did_response.did,
        public_key=did_response.public_key,
        created_at=did_response.created_at
    )
```

### 6.2.2 Credential Usage

| Credential Type | Usage | Source |
|-----------------|-------|--------|
| Agent DID | Primary identifier for all events and audit trails | L01 DID Registry |
| Session Token | Ephemeral token for session operations | L01 Phase 16 |
| Tool Credentials | Per-tool authentication secrets | L01 Config Service |

## 6.3 Event Integration (Phase 1 - Event Store)

### 6.3.1 Event Emission Pattern

All L02 components emit events to L01 Event Store using CloudEvents 1.0 specification.

```python
class EventEmitter:
    """Emit events to L01 Event Store."""

    async def emit(self, event: CloudEvent) -> None:
        """Emit event with guaranteed delivery."""
        enriched_event = self._enrich_event(event)
        await self._event_store_client.publish(
            topic=f"l02.{event.type}",
            event=enriched_event,
            delivery=DeliveryGuarantee.AT_LEAST_ONCE
        )

    def _enrich_event(self, event: CloudEvent) -> CloudEvent:
        """Add standard L02 metadata."""
        event.extensions["l02_version"] = "1.0"
        event.extensions["component"] = self.component_name
        event.extensions["correlation_id"] = get_correlation_id()
        return event
```

### 6.3.2 Event Categories

| Category | Event Types | Retention |
|----------|-------------|-----------|
| Lifecycle | spawned, terminated, suspended, resumed | 90 days |
| Health | health.changed, health.stuck | 30 days |
| Resource | resource.warning, resource.exceeded | 30 days |
| Checkpoint | checkpoint.created, checkpoint.restored | 90 days |
| Fleet | fleet.scaled, fleet.drain_started | 30 days |

## 6.4 Context Injection Integration (Phase 4)

L01 Phase 4 provides the Context Injector service which supplies agents with their initial execution context. This integration is critical for agent initialization and runtime configuration.

### 6.4.1 Context Loading at Spawn

```python
async def load_execution_context(
    agent_id: str,
    session_id: str
) -> ExecutionContext:
    """Load context from L01 Phase 4 Context Injector."""
    context = await l01_context_injector.get_context(
        subject_type="agent",
        subject_id=agent_id,
        session_id=session_id,
        include=[
            "system_prompt",
            "tool_permissions",
            "memory_snapshot",
            "environment_variables"
        ]
    )
    return ExecutionContext(
        system_prompt=context.system_prompt,
        tools=context.tool_permissions,
        memory=context.memory_snapshot,
        environment=context.environment_variables
    )
```

### 6.4.2 Context Components

| Component | Source | Purpose | Update Frequency |
|-----------|--------|---------|------------------|
| System Prompt | L01 Phase 4 | Base agent instructions | On spawn only |
| Tool Permissions | L01 Phase 4 | Allowed tool invocations | On spawn, dynamic update |
| Memory Snapshot | L01 Phase 4 + Phase 10 | Prior conversation state | On spawn, periodic sync |
| Environment Variables | L01 Phase 4 | Runtime configuration | On spawn only |
| Resource Limits | L01 Phase 4 | CPU/memory/token budgets | On spawn only |
| Sandbox Policy | L01 Phase 4 | Trust level, RuntimeClass | On spawn only |

### 6.4.3 Context Update Pattern

```python
async def update_context(
    agent_id: str,
    updates: ContextUpdate
) -> None:
    """Push context updates back to L01."""
    await l01_context_injector.update_context(
        subject_id=agent_id,
        updates=updates,
        merge_strategy="deep_merge"
    )
```

### 6.4.4 Context Refresh Protocol

For long-running agents, context may need periodic refresh:

```python
class ContextRefreshManager:
    """Manage periodic context refresh for long-running agents."""

    REFRESH_INTERVAL = 300  # 5 minutes

    async def refresh_context(self, agent_id: str) -> None:
        """Refresh mutable context components."""
        # Only refresh mutable components
        updates = await l01_context_injector.get_context(
            subject_id=agent_id,
            include=["tool_permissions", "memory_snapshot"]
        )
        await self.apply_context_updates(agent_id, updates)
```

### 6.4.5 Context Injection Failure Handling

| Failure Mode | Detection | Recovery Action |
|--------------|-----------|-----------------|
| L01 unavailable | Connection timeout (5s) | Use cached context, degrade mode |
| Partial context | Missing required fields | Fail spawn, emit error event |
| Stale context | Version mismatch | Force refresh from L01 |
| Invalid context | Schema validation fail | Reject context, emit E2040 |

## 6.5 Lifecycle Integration (Phase 9)

### 6.5.1 State Synchronization

L02 Lifecycle Manager synchronizes agent state with L01 Phase 9 Lifecycle Manager.

```python
class LifecycleIntegration:
    """Integrate with L01 Phase 9 Lifecycle Manager."""

    async def sync_state(
        self,
        agent_id: str,
        state: AgentState,
        metadata: dict
    ) -> None:
        """Synchronize state with L01."""
        await self.l01_lifecycle.update_state(
            entity_type="agent",
            entity_id=agent_id,
            state=state.value,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )

    async def get_state(self, agent_id: str) -> AgentState:
        """Get authoritative state from L01."""
        l01_state = await self.l01_lifecycle.get_state(
            entity_type="agent",
            entity_id=agent_id
        )
        return AgentState(l01_state.state)
```

### 6.5.2 State Machine Alignment

| L02 State | L01 Phase 9 State | Transition Trigger |
|-----------|-------------------|-------------------|
| pending | initializing | spawn request received |
| running | active | sandbox ready, agent started |
| suspended | paused | suspend command or idle timeout |
| terminated | completed | normal completion |
| failed | error | unrecoverable error |

## 6.6 Document Management Integration (Phase 15)

### 6.6.1 Source of Truth Query Pattern

Agents query authoritative documents via DocumentBridge to ensure decisions are based on verified information.

```python
class DocumentBridgeImpl:
    """Implementation of DocumentBridge for L01 Phase 15 integration."""

    def __init__(self, endpoint: str):
        self.client = DocumentManagerClient(endpoint)
        self.cache = TTLCache(maxsize=1000, ttl=300)

    async def query_source_of_truth(
        self,
        query: SourceOfTruthQuery
    ) -> SourceOfTruthResponse:
        """Query authoritative documents with caching."""
        cache_key = self._cache_key(query)
        if cached := self.cache.get(cache_key):
            return cached

        response = await self.client.get_source_of_truth(
            query=query.query,
            query_type=query.query_type,
            scope=query.scope,
            confidence_threshold=query.confidence_threshold,
            max_sources=query.max_sources,
            verify_claims=True
        )

        result = SourceOfTruthResponse(
            answer=response.answer,
            confidence=response.confidence,
            sources=[
                DocumentSource(
                    document_id=s.id,
                    title=s.title,
                    excerpt=s.excerpt,
                    authority_level=s.authority_level,
                    last_updated=s.last_updated
                )
                for s in response.sources
            ],
            conflicts=self._extract_conflicts(response)
        )

        self.cache[cache_key] = result
        return result

    async def verify_claim(
        self,
        claim: str,
        scope: Optional[list[str]] = None
    ) -> ClaimVerification:
        """Verify a claim against document corpus."""
        response = await self.client.verify_claim(
            claim=claim,
            scope=scope,
            include_conflicts=True
        )

        return ClaimVerification(
            claim=claim,
            verified=response.is_verified,
            confidence=response.confidence,
            supporting_sources=[
                DocumentSource(**s) for s in response.supporting
            ],
            conflicting_sources=[
                DocumentSource(**s) for s in response.conflicting
            ] if response.conflicting else None
        )
```

### 6.6.2 Document Ingestion Pattern

Agents can store generated artifacts as documents for future reference.

```python
async def ingest_agent_artifact(
    self,
    agent_id: str,
    content: str,
    artifact_type: str,
    metadata: dict
) -> str:
    """Store agent-generated document in L01 Phase 15."""
    response = await self.client.ingest_document(
        content=content,
        document_type=artifact_type,
        tags=[f"agent:{agent_id}", f"type:{artifact_type}"],
        authority_level=3,  # Agent-generated = medium authority
        extract_claims=True,
        generate_embeddings=True,
        metadata={
            **metadata,
            "source_agent": agent_id,
            "generated_at": datetime.utcnow().isoformat()
        }
    )
    return response.document_id
```

### 6.6.3 DocumentBridge Configuration

```yaml
document_bridge:
  endpoint: "l01-document-manager.l01-system.svc.cluster.local:50052"
  default_confidence_threshold: 0.7
  max_sources: 5
  cache:
    enabled: true
    ttl_seconds: 300
    max_size: 1000
  retry:
    max_retries: 3
    backoff_multiplier: 2
    initial_delay_ms: 100
  timeout_ms: 5000
  verify_claims: true
```

## 6.7 Session Orchestration Integration (Phase 16)

### 6.7.1 Session Lifecycle Management

```python
class SessionBridgeImpl:
    """Implementation of SessionBridge for L01 Phase 16 integration."""

    def __init__(self, endpoint: str, heartbeat_interval: int = 30):
        self.client = SessionOrchestratorClient(endpoint)
        self.heartbeat_interval = heartbeat_interval
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

    async def start_session(
        self,
        metadata: SessionMetadata
    ) -> str:
        """Start new session with L01 Phase 16."""
        response = await self.client.start_session(
            agent_id=metadata.agent_id,
            agent_type=metadata.agent_type,
            tenant_id=metadata.tenant_id,
            tags=metadata.tags,
            timeout_seconds=3600  # 1 hour default
        )
        session_id = response.session_id

        # Start background heartbeat
        self._start_heartbeat(session_id)

        return session_id

    async def end_session(
        self,
        session_id: str,
        reason: str
    ) -> None:
        """End session cleanly."""
        # Stop heartbeat
        self._stop_heartbeat(session_id)

        await self.client.end_session(
            session_id=session_id,
            reason=reason,
            final_snapshot=await self._get_final_snapshot(session_id)
        )

    def _start_heartbeat(self, session_id: str) -> None:
        """Start background heartbeat task."""
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(self.heartbeat_interval)
                    await self.heartbeat(session_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Heartbeat failed for {session_id}: {e}")

        self._heartbeat_tasks[session_id] = asyncio.create_task(heartbeat_loop())

    def _stop_heartbeat(self, session_id: str) -> None:
        """Stop heartbeat task."""
        if task := self._heartbeat_tasks.pop(session_id, None):
            task.cancel()
```

### 6.7.2 Heartbeat Pattern

```python
async def heartbeat(self, session_id: str) -> HeartbeatResponse:
    """Send heartbeat to L01 Phase 16."""
    response = await self.client.heartbeat(
        session_id=session_id,
        metrics={
            "memory_mb": get_current_memory_mb(),
            "cpu_percent": get_current_cpu_percent(),
            "tokens_consumed": get_tokens_consumed()
        }
    )

    return HeartbeatResponse(
        acknowledged=response.acknowledged,
        session_valid=response.session_valid,
        server_time=response.server_time
    )
```

### 6.7.3 Context Persistence

**Checkpoint Persistence Modes (LangGraph Pattern):**

| Mode | Description | Performance | Durability | Use Case |
|------|-------------|-------------|------------|----------|
| sync | Persist before next step | Lower | High | Critical workflows, human-in-loop |
| async | Persist during next step | Higher | Medium | High-throughput, crash-tolerant |

```python
from enum import Enum

class PersistenceMode(Enum):
    SYNC = "sync"    # Wait for checkpoint before continuing
    ASYNC = "async"  # Checkpoint in background

async def save_context_snapshot(
    self,
    session_id: str,
    context: ExecutionContext,
    persistence_mode: PersistenceMode = PersistenceMode.ASYNC
) -> str:
    """Save context snapshot to L01 Phase 16.

    Args:
        session_id: Active session identifier
        context: Current execution context
        persistence_mode:
            - SYNC: Block until checkpoint confirmed (high durability)
            - ASYNC: Return immediately, checkpoint in background (high performance)
    """
    serialized = self._serialize_context(context)

    if persistence_mode == PersistenceMode.SYNC:
        # Synchronous: wait for confirmation
        response = await self.client.save_context_snapshot(
            session_id=session_id,
            context={
                "state": serialized.state,
                "memory": serialized.memory,
                "tools": serialized.tools,
                "conversation_history": serialized.conversation_history,
                "working_directory": serialized.working_directory,
                "environment_variables": serialized.environment_variables
            },
            change_summary=f"Snapshot at {datetime.utcnow().isoformat()}"
        )
        return response.snapshot_id
    else:
        # Asynchronous: fire and continue
        asyncio.create_task(self._async_checkpoint(session_id, serialized))
        return f"pending-{session_id}-{time.time()}"

async def _async_checkpoint(self, session_id: str, serialized) -> None:
    """Background checkpoint task."""
    try:
        await self.client.save_context_snapshot(
            session_id=session_id,
            context=serialized.__dict__,
            change_summary=f"Async snapshot at {datetime.utcnow().isoformat()}"
        )
    except Exception as e:
        logger.error(f"Async checkpoint failed for {session_id}: {e}")
        # Emit alert for checkpoint failure
        await self.emit_event("checkpoint.failed", {"session_id": session_id, "error": str(e)})

async def load_context(
    self,
    session_id: str
) -> ExecutionContext:
    """Load context from L01 Phase 16."""
    response = await self.client.get_unified_context(
        session_id=session_id,
        include_relationships=True,
        include_version_history=False
    )

    return self._deserialize_context(response.context)
```

### 6.7.4 Crash Recovery

```python
async def check_recovery(
    self,
    agent_id: Optional[str] = None
) -> list[RecoveryInfo]:
    """Check for crashed sessions needing recovery."""
    response = await self.client.check_recovery(
        agent_id=agent_id,
        include_history=True
    )

    return [
        RecoveryInfo(
            session_id=r.session_id,
            agent_id=r.agent_id,
            last_heartbeat=r.last_heartbeat,
            last_checkpoint=r.last_checkpoint,
            recovery_prompt=r.recovery_prompt,
            tool_history=r.tool_history
        )
        for r in response.sessions_needing_recovery
    ]
```

### 6.7.5 Checkpoint Management

```python
async def create_checkpoint(
    self,
    session_id: str,
    label: str,
    description: Optional[str] = None
) -> str:
    """Create named checkpoint in L01 Phase 16."""
    response = await self.client.create_checkpoint(
        session_id=session_id,
        label=label,
        description=description,
        checkpoint_type="manual"
    )

    # Emit checkpoint event
    await self._emit_event(
        "agent.checkpoint.created",
        {
            "session_id": session_id,
            "checkpoint_id": response.checkpoint_id,
            "label": label
        }
    )

    return response.checkpoint_id

async def rollback_to(
    self,
    session_id: str,
    checkpoint_id: str
) -> ExecutionContext:
    """Rollback session to checkpoint."""
    response = await self.client.rollback_to(
        session_id=session_id,
        target={
            "type": "checkpoint",
            "checkpoint_id": checkpoint_id
        },
        create_backup=True
    )

    # Emit rollback event
    await self._emit_event(
        "agent.checkpoint.restored",
        {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id
        }
    )

    return self._deserialize_context(response.restored_context)
```

### 6.7.6 SessionBridge Configuration

```yaml
session_bridge:
  endpoint: "l01-session-orchestrator.l01-system.svc.cluster.local:50051"
  heartbeat:
    interval_seconds: 30
    timeout_seconds: 5
    max_missed: 3
  snapshot:
    auto_interval_seconds: 60
    max_size_mb: 100
    compression: gzip
  recovery:
    check_on_spawn: true
    scan_interval_seconds: 300
  retry:
    max_retries: 3
    backoff_multiplier: 2
    initial_delay_ms: 100
  timeout_ms: 10000
```

---

# Section 7: Reliability and Scalability

## 7.1 Availability Targets

### 7.1.1 Service Level Objectives (SLOs)

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Agent Spawn Success Rate | 99.9% | Rolling 30 days |
| Agent Execution Availability | 99.5% | Rolling 30 days |
| Checkpoint Success Rate | 99.99% | Rolling 30 days |
| Session Recovery Success Rate | 99.9% | Rolling 30 days |
| Fleet Scaling Response Time | 95th percentile < 60s | Rolling 7 days |

### 7.1.2 Service Level Indicators (SLIs)

```yaml
slis:
  spawn_success_rate:
    numerator: successful_spawns
    denominator: total_spawn_requests
    threshold: 0.999

  execution_availability:
    numerator: successful_execution_minutes
    denominator: total_execution_minutes
    threshold: 0.995

  checkpoint_success_rate:
    numerator: successful_checkpoints
    denominator: total_checkpoint_attempts
    threshold: 0.9999

  p95_spawn_latency:
    percentile: 95
    metric: spawn_duration_seconds
    threshold: 5.0

  p99_checkpoint_latency:
    percentile: 99
    metric: checkpoint_duration_seconds
    threshold: 10.0
```

### 7.1.3 Latency SLO Targets

| Operation | p50 Target | p95 Target | p99 Target | Max Allowed |
|-----------|------------|------------|------------|-------------|
| Agent Spawn (cold) | < 3s | < 5s | < 10s | 30s |
| Agent Spawn (warm) | < 200ms | < 500ms | < 1s | 5s |
| Checkpoint Create | < 100ms | < 500ms | < 1s | 5s |
| Checkpoint Restore | < 200ms | < 1s | < 2s | 10s |
| Session Start | < 50ms | < 200ms | < 500ms | 2s |
| Document Query | < 100ms | < 500ms | < 1s | 5s |
| LLM Inference (token) | < 50ms | < 100ms | < 200ms | 1s |
| Health Probe | < 10ms | < 50ms | < 100ms | 500ms |

**Error Budget Policy:**
- Monthly error budget: 0.1% (43.2 minutes downtime allowed)
- Budget consumption rate monitored daily
- Automatic feature freeze at 80% budget consumption
- Post-incident review required for budget depletion

## 7.2 Scaling Model

### 7.2.1 Horizontal Scaling

```
+------------------------------------------------------------------+
|                     Fleet Scaling Architecture                    |
|                                                                  |
|  +------------------+     +------------------+                    |
|  |  Metrics Server  |---->|  Fleet Manager   |                    |
|  |                  |     |                  |                    |
|  | - CPU usage      |     | - Scale decisions|                    |
|  | - Memory usage   |     | - Warm pool mgmt |                    |
|  | - Queue depth    |     | - Drain coord    |                    |
|  +------------------+     +--------+---------+                    |
|                                    |                              |
|                    +---------------+---------------+               |
|                    |               |               |               |
|                    v               v               v               |
|           +--------+------+ +-----+-------+ +-----+-------+       |
|           | Agent Pool A  | | Agent Pool B| | Warm Pool   |       |
|           | (gVisor)      | | (Kata)      | | (standby)   |       |
|           +---------------+ +-------------+ +-------------+       |
|                                                                  |
+------------------------------------------------------------------+
```

### 7.2.2 Scaling Triggers

| Trigger | Metric | Scale Up Threshold | Scale Down Threshold | Stabilization |
|---------|--------|-------------------|---------------------|---------------|
| CPU | Average CPU utilization | > 70% | < 30% | 60s / 300s |
| Memory | Average memory utilization | > 80% | < 40% | 60s / 300s |
| Queue | Pending task queue depth | > 10 per agent | < 2 per agent | 30s / 180s |
| Custom | Agent response latency p95 | > 5s | < 1s | 120s / 600s |

### 7.2.3 Warm Pool Management

```python
class WarmPoolManager:
    """Manage pre-initialized agent instances."""

    def __init__(self, config: WarmPoolConfig):
        self.target_size = config.size
        self.runtime_class = config.runtime_class
        self.refresh_interval = config.refresh_interval_seconds
        self._pool: asyncio.Queue[WarmInstance] = asyncio.Queue()

    async def acquire(self, timeout: float = 5.0) -> Optional[WarmInstance]:
        """Acquire warm instance from pool."""
        try:
            instance = await asyncio.wait_for(
                self._pool.get(),
                timeout=timeout
            )
            # Trigger background replenishment
            asyncio.create_task(self._replenish())
            return instance
        except asyncio.TimeoutError:
            return None  # Pool exhausted

    async def _replenish(self) -> None:
        """Replenish pool to target size."""
        while self._pool.qsize() < self.target_size:
            instance = await self._create_warm_instance()
            await self._pool.put(instance)

    async def _create_warm_instance(self) -> WarmInstance:
        """Create pre-initialized instance."""
        pod = await self._create_pod(
            runtime_class=self.runtime_class,
            state="standby"
        )
        return WarmInstance(
            pod_name=pod.name,
            created_at=datetime.utcnow(),
            runtime_class=self.runtime_class
        )
```

## 7.3 High Availability Patterns

### 7.3.1 Multi-Zone Deployment

```yaml
# Pod anti-affinity for zone distribution
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-runtime-controller
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: agent-runtime-controller
              topologyKey: topology.kubernetes.io/zone
```

### 7.3.2 Leader Election

```python
class LeaderElection:
    """Kubernetes-native leader election for singleton operations."""

    def __init__(self, lock_name: str, namespace: str):
        self.lock_name = lock_name
        self.namespace = namespace
        self._is_leader = False

    async def run(self, on_started: Callable, on_stopped: Callable):
        """Run leader election loop."""
        config.load_incluster_config()
        async with client.ApiClient() as api:
            v1 = client.CoordinationV1Api(api)

            while True:
                try:
                    acquired = await self._try_acquire_lease(v1)
                    if acquired and not self._is_leader:
                        self._is_leader = True
                        await on_started()
                    elif not acquired and self._is_leader:
                        self._is_leader = False
                        await on_stopped()

                    await asyncio.sleep(10)  # Lease renewal interval

                except Exception as e:
                    logger.error(f"Leader election error: {e}")
                    if self._is_leader:
                        self._is_leader = False
                        await on_stopped()
```

### 7.3.3 Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: agent-runtime-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: agent-runtime
```

## 7.4 Capacity Planning

### 7.4.1 Agent Density Guidelines

| Node Size | Max Agents (gVisor) | Max Agents (Kata) | Memory Reserved |
|-----------|---------------------|-------------------|-----------------|
| 4 CPU / 16Gi | 8 | 4 | 2Gi for system |
| 8 CPU / 32Gi | 16 | 8 | 4Gi for system |
| 16 CPU / 64Gi | 32 | 16 | 8Gi for system |

### 7.4.2 Scaling Thresholds

```yaml
capacity:
  min_nodes: 2
  max_nodes: 100
  agents_per_node_soft_limit: 16
  agents_per_node_hard_limit: 32
  scale_up_threshold:
    cpu_percent: 70
    memory_percent: 80
    agents_per_node: 12
  scale_down_threshold:
    cpu_percent: 30
    memory_percent: 40
    agents_per_node: 4
  scale_step:
    up: 2  # Add 2 nodes at a time
    down: 1  # Remove 1 node at a time
```

## 7.5 Performance Budgets

### 7.5.1 Latency Targets

| Operation | p50 | p95 | p99 | Max |
|-----------|-----|-----|-----|-----|
| Agent spawn (cold) | 2s | 5s | 10s | 30s |
| Agent spawn (warm) | 200ms | 500ms | 1s | 5s |
| Checkpoint create | 500ms | 2s | 5s | 30s |
| Checkpoint restore | 1s | 3s | 10s | 60s |
| Session heartbeat | 10ms | 50ms | 100ms | 1s |
| Document query | 100ms | 500ms | 1s | 5s |
| LLM inference | 1s | 5s | 30s | 300s |

### 7.5.2 Throughput Targets

| Operation | Target Rate | Burst Capacity |
|-----------|-------------|----------------|
| Agent spawns | 100/min | 500/min |
| Checkpoints | 1000/min | 5000/min |
| Heartbeats | 10000/min | 50000/min |
| Document queries | 5000/min | 20000/min |

## 7.6 Graceful Degradation

### 7.6.1 Scale-Down with In-Flight Work

```python
async def graceful_drain(
    self,
    agent_id: str,
    timeout_seconds: int = 30
) -> DrainResult:
    """Gracefully drain agent before termination."""
    start_time = time.monotonic()

    # 1. Stop accepting new work
    await self._mark_draining(agent_id)

    # 2. Emit drain started event
    await self._emit_event("fleet.drain_started", {"agent_id": agent_id})

    # 3. Wait for in-flight work with timeout
    while time.monotonic() - start_time < timeout_seconds:
        if await self._is_idle(agent_id):
            break
        await asyncio.sleep(1)

    # 4. Checkpoint current state
    checkpoint_id = await self._checkpoint_before_drain(agent_id)

    # 5. Terminate
    await self._terminate(agent_id, reason="drain")

    elapsed = time.monotonic() - start_time
    return DrainResult(
        agent_id=agent_id,
        checkpoint_id=checkpoint_id,
        duration_seconds=elapsed,
        forced=elapsed >= timeout_seconds
    )
```

### 7.6.2 Degradation Modes

| Condition | Degradation Mode | Impact |
|-----------|-----------------|--------|
| L04 Model Gateway unavailable | Queue inference requests, serve from cache | Increased latency |
| L01 Event Store unavailable | Local event buffer, async retry | Delayed audit trail |
| L01 Phase 16 unavailable | Local checkpoint, sync on recovery | Risk of state loss |
| High CPU utilization | Suspend low-priority agents | Reduced capacity |
| Memory pressure | Checkpoint and terminate idle agents | Reduced warm pool |

---

# Section 8: Security

## 8.1 Security Architecture

```
+------------------------------------------------------------------+
|                      Trust Boundary Diagram                       |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |                    Cluster Boundary                         |  |
|  |                                                            |  |
|  |  +------------------+    +------------------+               |  |
|  |  | Control Plane    |    | L02 Runtime      |               |  |
|  |  | (K8s API)        |    | Controller       |               |  |
|  |  | [TRUSTED]        |    | [TRUSTED]        |               |  |
|  |  +------------------+    +--------+---------+               |  |
|  |                                   |                         |  |
|  |  +------------------------------------------------+        |  |
|  |  |           Agent Namespace Boundary             |        |  |
|  |  |                                                |        |  |
|  |  |  +------------------+  +------------------+    |        |  |
|  |  |  | Agent Pod A      |  | Agent Pod B      |    |        |  |
|  |  |  | [SANDBOXED]      |  | [SANDBOXED]      |    |        |  |
|  |  |  |                  |  |                  |    |        |  |
|  |  |  | +-------------+  |  | +-------------+  |    |        |  |
|  |  |  | | gVisor/Kata |  |  | | gVisor/Kata |  |    |        |  |
|  |  |  | | Sandbox     |  |  | | Sandbox     |  |    |        |  |
|  |  |  | | [ISOLATED]  |  |  | | [ISOLATED]  |  |    |        |  |
|  |  |  | +-------------+  |  | +-------------+  |    |        |  |
|  |  |  +------------------+  +------------------+    |        |  |
|  |  |           ^                    ^               |        |  |
|  |  |           |    NetworkPolicy   |               |        |  |
|  |  |           +--------X-----------+               |        |  |
|  |  |              (No direct comms)                 |        |  |
|  |  +------------------------------------------------+        |  |
|  |                                                            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

## 8.2 Pod Security Admission (CIS Compliance)

### 8.2.1 Pod Security Standards

Clusters MUST enforce Pod Security Admission at "restricted" level for agent namespaces per CIS Kubernetes Benchmark.

```yaml
# Namespace configuration for Pod Security Admission
apiVersion: v1
kind: Namespace
metadata:
  name: l02-agents
  labels:
    # Enforce restricted policy (CIS requirement)
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    # Warn on baseline violations
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest
    # Audit all violations
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
```

### 8.2.2 Pod Security Requirements

| Requirement | Restricted Level | L02 Compliance |
|-------------|------------------|----------------|
| Privileged containers | Forbidden | Enforced |
| Host namespaces | Forbidden | Enforced |
| Host ports | Forbidden | Enforced |
| Host path volumes | Forbidden | Enforced |
| Privilege escalation | Forbidden | Enforced |
| Root user | Forbidden (runAsNonRoot) | Enforced |
| Capabilities | Drop ALL, add specific | Enforced |
| Seccomp profile | RuntimeDefault or Localhost | Enforced |

## 8.3 Sandbox Security

### 8.3.1 gVisor Configuration

```yaml
# RuntimeClass for gVisor
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
scheduling:
  nodeSelector:
    sandbox.gvisor/enabled: "true"

---
# Pod security context for gVisor agents
securityContext:
  runAsNonRoot: true
  runAsUser: 65534
  runAsGroup: 65534
  fsGroup: 65534
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
      - ALL
```

### 8.2.2 Kata Containers Configuration

```yaml
# RuntimeClass for Kata
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata
handler: kata-qemu
overhead:
  podFixed:
    memory: "160Mi"
    cpu: "250m"
scheduling:
  nodeSelector:
    katacontainers.io/kata-runtime: "true"
```

### 8.3.3 OCI v1.3 VM Hardware Configuration

For Kata Containers, OCI Runtime Spec v1.3 introduces vm.hwConfig for explicit hardware specification:

```json
{
  "vm": {
    "hypervisor": {
      "path": "/usr/bin/qemu-system-x86_64"
    },
    "kernel": {
      "path": "/usr/share/kata-containers/vmlinuz.container"
    },
    "hwConfig": {
      "vcpus": 2,
      "memoryMB": 2048,
      "deviceTree": null
    }
  }
}
```

**hwConfig Parameters:**
| Parameter | Description | Default | Agent Override |
|-----------|-------------|---------|----------------|
| vcpus | Virtual CPU count | 1 | Via resource limits |
| memoryMB | Memory allocation in MB | 256 | Via resource limits |
| deviceTree | Device tree blob path | null | Not supported |

### 8.3.4 AWS Fargate Isolation Option

For highest isolation requirements, AWS Fargate provides VM-isolated pod execution without shared infrastructure:

```yaml
# EKS Fargate profile for agent workloads
apiVersion: eks.amazonaws.com/v1alpha1
kind: FargateProfile
metadata:
  name: l02-agents-fargate
  namespace: l02-system
spec:
  podExecutionRoleArn: arn:aws:iam::123456789:role/L02FargatePodExecutionRole
  subnets:
    - subnet-abc123
  selectors:
    - namespace: l02-agents
      labels:
        isolation: fargate
```

**Fargate vs Kata Comparison:**
| Aspect | Kata Containers | AWS Fargate |
|--------|-----------------|-------------|
| Isolation | Lightweight VM | Full VM |
| Overhead | ~160Mi memory | Higher |
| Startup | ~1-2s | ~30-60s |
| Cost | Node-based | Per-pod |
| GPU support | Limited | Not supported |

### 8.3.5 Sandbox Selection Matrix

| Trust Level | RuntimeClass | Network Policy | Resource Limits |
|-------------|--------------|----------------|-----------------|
| trusted | runc | restricted | standard |
| standard | gvisor | isolated | standard |
| untrusted | kata | isolated | restricted |
| confidential | kata-cc | isolated | restricted |

## 8.3 Network Isolation

### 8.3.1 OC-1 Enforcement via NetworkPolicy

```yaml
# Default deny all traffic between agents
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-isolation
  namespace: agent-workloads
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: agent
  policyTypes:
    - Ingress
    - Egress
  ingress: []  # Deny all ingress
  egress:
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow L01 services
    - to:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/part-of: l01-system
      ports:
        - protocol: TCP
          port: 50051
        - protocol: TCP
          port: 50052
    # Allow L04 services
    - to:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/part-of: l04-system
      ports:
        - protocol: TCP
          port: 50053
```

### 8.3.2 Egress Control

| Destination | Allowed | Rationale |
|-------------|---------|-----------|
| L01 services | Yes | Data layer integration |
| L04 services | Yes | Model gateway |
| External APIs | Configurable | Tool-dependent |
| Other agents | No | OC-1 enforcement |
| Internet | Configurable | Per-agent policy |

## 8.4 Resource Isolation

### 8.4.1 cgroups Configuration

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2"
    memory: "2Gi"
    ephemeral-storage: "1Gi"
```

### 8.4.2 Namespace Boundaries

| Boundary | Enforcement | Purpose |
|----------|-------------|---------|
| PID namespace | Per-pod | Process isolation |
| Network namespace | Per-pod | Network isolation |
| IPC namespace | Per-pod | Shared memory isolation |
| UTS namespace | Per-pod | Hostname isolation |
| Mount namespace | Per-pod | Filesystem isolation |
| User namespace | Optional | UID mapping (gVisor/Kata) |

## 8.5 Secrets Management

### 8.5.1 Credential Injection Patterns

```yaml
# Secret projection into agent pod
spec:
  containers:
    - name: agent
      env:
        - name: AGENT_DID
          valueFrom:
            secretKeyRef:
              name: agent-credentials
              key: did
      volumeMounts:
        - name: tool-credentials
          mountPath: /secrets/tools
          readOnly: true
  volumes:
    - name: tool-credentials
      secret:
        secretName: tool-credentials
        defaultMode: 0400
```

### 8.5.2 Credential Rotation

| Credential Type | Rotation Frequency | Mechanism |
|-----------------|-------------------|-----------|
| Agent DID | On spawn | L01 DID Registry |
| Session Token | Per session | L01 Phase 16 |
| Tool API Keys | Configurable | External secrets operator |
| TLS Certificates | 90 days | cert-manager |

## 8.6 Threat Model (STRIDE Analysis)

### 8.6.1 STRIDE Analysis

| Threat | Category | Mitigation |
|--------|----------|------------|
| Malicious agent code escapes sandbox | Spoofing | gVisor/Kata isolation, syscall filtering |
| Agent impersonates another agent | Spoofing | DID-based identity, mTLS |
| Agent modifies execution logs | Tampering | Immutable event store, signed events |
| Agent reads another agent's memory | Information Disclosure | Namespace isolation, RuntimeClass |
| Agent bypasses token budget | Elevation of Privilege | L04 enforcement, L02 tracking |
| Agent causes resource exhaustion | Denial of Service | cgroups limits, quota enforcement |
| Agent communicates with unauthorized endpoints | Tampering | NetworkPolicy, egress filtering |

### 8.6.2 Attack Surface Reduction

| Attack Surface | Reduction Measure |
|----------------|-------------------|
| Host kernel | gVisor user-space kernel |
| Container runtime | Minimal OCI compliance |
| Network | Default-deny NetworkPolicy |
| Filesystem | Read-only root, tmpfs for writes |
| Processes | Non-root, dropped capabilities |
| Secrets | Encrypted at rest, minimal exposure |

---

# Section 9: Observability

## 9.1 Metrics

### 9.1.0 OpenTelemetry Semantic Convention Alignment

L02 metrics align with OpenTelemetry Semantic Conventions v1.39 where applicable:

| L02 Metric | OTel Equivalent | Convention |
|------------|-----------------|------------|
| agent_runtime_cpu_usage_seconds_total | process.cpu.time | process semconv |
| agent_runtime_memory_usage_bytes | process.memory.usage | process semconv |
| agent_runtime_active_agents | container.uptime (count) | container semconv |
| agent_runtime_spawn_duration_seconds | (custom) | L02-specific |
| agent_runtime_checkpoint_size_bytes | (custom) | L02-specific |

**Note:** Agent-specific metrics (spawns, checkpoints, token budgets) use L02 custom naming as no OTel equivalent exists for AI agent workloads.

### 9.1.1 Prometheus Metrics (Counter/Gauge/Histogram)

```prometheus
# Agent lifecycle metrics
agent_runtime_spawns_total{status="success|failure",trust_level="trusted|standard|untrusted",runtime_class="runc|gvisor|kata"} counter
agent_runtime_terminations_total{reason="completed|error|timeout|resource|user"} counter
agent_runtime_active_agents{trust_level="trusted|standard|untrusted",state="running|suspended"} gauge

# Spawn latency
agent_runtime_spawn_duration_seconds{source="cold|warm"} histogram
agent_runtime_spawn_queue_depth gauge

# Checkpoint metrics
agent_runtime_checkpoints_total{type="auto|manual",status="success|failure"} counter
agent_runtime_checkpoint_duration_seconds histogram
agent_runtime_checkpoint_size_bytes histogram

# Resource usage
agent_runtime_cpu_usage_seconds_total{agent_id} counter
agent_runtime_memory_usage_bytes{agent_id} gauge
agent_runtime_tokens_consumed_total{agent_id,model} counter
agent_runtime_token_budget_remaining{agent_id} gauge

# Health metrics
agent_runtime_health_checks_total{type="liveness|readiness",status="success|failure"} counter
agent_runtime_stuck_agents gauge
agent_runtime_error_rate{agent_id} gauge

# Fleet metrics
agent_runtime_fleet_size gauge
agent_runtime_warm_pool_size gauge
agent_runtime_scale_operations_total{direction="up|down"} counter

# Integration metrics
agent_runtime_session_bridge_latency_seconds{operation="heartbeat|snapshot|recovery"} histogram
agent_runtime_document_bridge_latency_seconds{operation="query|verify|ingest"} histogram
agent_runtime_model_bridge_latency_seconds{operation="inference"} histogram
```

### 9.1.2 Metrics Collection Configuration

```yaml
metrics:
  port: 9090
  path: /metrics
  scrape_interval: 15s
  labels:
    service: agent-runtime
    layer: l02
  histograms:
    spawn_duration:
      buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    checkpoint_duration:
      buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    checkpoint_size:
      buckets: [1048576, 10485760, 104857600, 1073741824]  # 1MB, 10MB, 100MB, 1GB
```

## 9.2 Logging

### 9.2.1 Structured Log Format

```json
{
  "timestamp": "2025-01-14T10:30:45.123Z",
  "level": "INFO",
  "logger": "l02.lifecycle_manager",
  "message": "Agent spawned successfully",
  "trace_id": "abc123",
  "span_id": "def456",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "component": "lifecycle_manager",
  "operation": "spawn",
  "duration_ms": 2345,
  "runtime_class": "gvisor",
  "trust_level": "standard",
  "resource_limits": {
    "cpu": "2",
    "memory": "2Gi"
  }
}
```

### 9.2.2 Log Levels and Categories

| Level | Category | Retention | Examples |
|-------|----------|-----------|----------|
| ERROR | Failures | 90 days | Spawn failed, checkpoint corrupted |
| WARN | Anomalies | 30 days | Resource warning, retry triggered |
| INFO | Operations | 14 days | Spawned, terminated, scaled |
| DEBUG | Details | 7 days | State transitions, cache hits |

### 9.2.3 Log Aggregation Configuration

```yaml
logging:
  format: json
  level: INFO
  output: stdout
  fields:
    - timestamp
    - level
    - logger
    - message
    - trace_id
    - span_id
    - agent_id
    - session_id
    - component
    - operation
  sampling:
    enabled: true
    rate: 0.1  # Sample 10% of debug logs
    always_log_levels: [ERROR, WARN]
```

## 9.3 Tracing

### 9.3.1 OpenTelemetry Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer("l02.agent_runtime")

async def spawn_agent(config: AgentConfig) -> SpawnResult:
    with tracer.start_as_current_span(
        "agent.spawn",
        kind=trace.SpanKind.SERVER,
        attributes={
            "agent.id": config.agent_id,
            "agent.trust_level": config.trust_level,
            "agent.runtime_class": get_runtime_class(config.trust_level)
        }
    ) as span:
        # Start session
        with tracer.start_span("session.start") as session_span:
            session_id = await session_bridge.start_session(...)
            session_span.set_attribute("session.id", session_id)

        # Create sandbox
        with tracer.start_span("sandbox.create") as sandbox_span:
            sandbox = await sandbox_manager.create(...)
            sandbox_span.set_attribute("sandbox.runtime_class", sandbox.runtime_class)

        # Initialize agent
        with tracer.start_span("agent.initialize") as init_span:
            await agent_executor.initialize(...)

        span.set_status(trace.Status(trace.StatusCode.OK))
        return SpawnResult(...)
```

### 9.3.2 Trace Propagation

| Integration | Propagation Header | Format |
|-------------|-------------------|--------|
| L01 gRPC | traceparent | W3C Trace Context |
| L04 gRPC | traceparent | W3C Trace Context |
| L00 K8s | traceparent | W3C Trace Context |
| Internal HTTP | traceparent | W3C Trace Context |

### 9.3.3 Span Hierarchy

```
agent.spawn (root)
  +-- session.start
  +-- identity.retrieve
  +-- sandbox.create
  +-- context.load
  +-- agent.initialize
  +-- event.emit (agent.spawned)

agent.execute (root)
  +-- context.load
  +-- tool.invoke (repeated)
  |     +-- document.query (if DocumentBridge)
  |     +-- model.inference (if ModelBridge)
  +-- checkpoint.create
  +-- event.emit (agent.checkpoint.created)
```

## 9.4 Alerting

### 9.4.1 Alert Definitions

```yaml
groups:
  - name: agent-runtime-alerts
    rules:
      - alert: AgentSpawnFailureRateHigh
        expr: |
          sum(rate(agent_runtime_spawns_total{status="failure"}[5m])) /
          sum(rate(agent_runtime_spawns_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
          layer: l02
        annotations:
          summary: "Agent spawn failure rate exceeds 1%"
          description: "{{ $value | humanizePercentage }} of agent spawns are failing"

      - alert: AgentCheckpointFailure
        expr: |
          sum(rate(agent_runtime_checkpoints_total{status="failure"}[5m])) > 0
        for: 2m
        labels:
          severity: warning
          layer: l02
        annotations:
          summary: "Agent checkpoint failures detected"

      - alert: WarmPoolDepleted
        expr: agent_runtime_warm_pool_size < 2
        for: 5m
        labels:
          severity: warning
          layer: l02
        annotations:
          summary: "Warm pool size below threshold"
          description: "Warm pool has {{ $value }} instances (threshold: 2)"

      - alert: AgentStuck
        expr: agent_runtime_stuck_agents > 0
        for: 10m
        labels:
          severity: warning
          layer: l02
        annotations:
          summary: "Stuck agents detected"
          description: "{{ $value }} agents showing no progress"

      - alert: TokenBudgetExhausted
        expr: agent_runtime_token_budget_remaining < 1000
        for: 1m
        labels:
          severity: warning
          layer: l02
        annotations:
          summary: "Agent token budget nearly exhausted"

      - alert: SessionBridgeLatencyHigh
        expr: |
          histogram_quantile(0.95, rate(agent_runtime_session_bridge_latency_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
          layer: l02
        annotations:
          summary: "Session bridge latency exceeds threshold"
```

## 9.5 Dashboards

### 9.5.1 Grafana Dashboard Specification

```json
{
  "dashboard": {
    "title": "Agent Runtime Layer (L02)",
    "uid": "l02-agent-runtime",
    "tags": ["l02", "agent-runtime"],
    "panels": [
      {
        "title": "Active Agents",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "sum(agent_runtime_active_agents{state=\"running\"})",
            "legendFormat": "Running"
          }
        ]
      },
      {
        "title": "Spawn Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
        "targets": [
          {
            "expr": "sum(rate(agent_runtime_spawns_total[5m])) by (status)",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Spawn Latency (p95)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_runtime_spawn_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "Resource Usage by Agent",
        "type": "table",
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 12},
        "targets": [
          {
            "expr": "agent_runtime_memory_usage_bytes / 1024 / 1024",
            "legendFormat": "{{agent_id}}"
          }
        ]
      },
      {
        "title": "Fleet Size",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 20},
        "targets": [
          {
            "expr": "agent_runtime_fleet_size",
            "legendFormat": "Total"
          },
          {
            "expr": "agent_runtime_warm_pool_size",
            "legendFormat": "Warm Pool"
          }
        ]
      },
      {
        "title": "Integration Latency",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 20},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_runtime_session_bridge_latency_seconds_bucket[5m]))",
            "legendFormat": "Session Bridge"
          },
          {
            "expr": "histogram_quantile(0.95, rate(agent_runtime_document_bridge_latency_seconds_bucket[5m]))",
            "legendFormat": "Document Bridge"
          }
        ]
      }
    ]
  }
}
```

---

# Section 10: Configuration

## 10.1 Configuration Hierarchy

```
+------------------------------------------------------------------+
|                    Configuration Hierarchy                        |
|                                                                  |
|  +----------------------------------------------------------+    |
|  |  Cluster Level (ConfigMap: agent-runtime-config)         |    |
|  |  - Default sandbox settings                               |    |
|  |  - Global resource limits                                 |    |
|  |  - Feature flags                                          |    |
|  +----------------------------------------------------------+    |
|                              |                                   |
|                              v                                   |
|  +----------------------------------------------------------+    |
|  |  Namespace Level (ConfigMap: ns-agent-config)            |    |
|  |  - Tenant-specific overrides                              |    |
|  |  - Namespace resource quotas                              |    |
|  |  - Trust level defaults                                   |    |
|  +----------------------------------------------------------+    |
|                              |                                   |
|                              v                                   |
|  +----------------------------------------------------------+    |
|  |  Agent Level (Spawn Request / Pod Annotations)           |    |
|  |  - Per-agent resource limits                              |    |
|  |  - Tool configurations                                    |    |
|  |  - Custom environment variables                           |    |
|  +----------------------------------------------------------+    |
|                                                                  |
|  Precedence: Agent > Namespace > Cluster                         |
|                                                                  |
+------------------------------------------------------------------+
```

## 10.2 Configuration Schemas

### 10.2.1 Cluster Configuration

```yaml
# ConfigMap: agent-runtime-config
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-runtime-config
  namespace: l02-system
data:
  config.yaml: |
    version: "1.0"

    sandbox:
      default_runtime_class: gvisor
      trust_level_mapping:
        trusted: runc
        standard: gvisor
        untrusted: kata
        confidential: kata-cc
      security_context:
        run_as_non_root: true
        read_only_root_filesystem: true
        allow_privilege_escalation: false

    resources:
      default_limits:
        cpu: "2"
        memory: "2Gi"
        ephemeral_storage: "1Gi"
      default_requests:
        cpu: "500m"
        memory: "512Mi"
      token_budget:
        default_per_hour: 100000
        max_per_hour: 1000000

    lifecycle:
      spawn_timeout_seconds: 60
      graceful_shutdown_seconds: 30
      checkpoint_interval_seconds: 60
      restart_policy: ExponentialBackoff
      max_restart_count: 5

    fleet:
      min_replicas: 1
      max_replicas: 100
      warm_pool:
        enabled: true
        size: 5
        refresh_interval_seconds: 3600

    health:
      liveness_probe:
        interval_seconds: 10
        timeout_seconds: 5
        failure_threshold: 3
      readiness_probe:
        interval_seconds: 5
        timeout_seconds: 3
        failure_threshold: 2
      stuck_agent_timeout_seconds: 600

    integration:
      session_bridge:
        endpoint: "l01-session-orchestrator:50051"
        heartbeat_interval_seconds: 30
      document_bridge:
        endpoint: "l01-document-manager:50052"
        cache_ttl_seconds: 300
      model_bridge:
        endpoint: "l04-model-gateway:50053"
        default_model: "claude-3-opus"

    observability:
      metrics_port: 9090
      log_level: INFO
      trace_sampling_rate: 0.1
```

### 10.2.2 Namespace Configuration

```yaml
# ConfigMap: ns-agent-config
apiVersion: v1
kind: ConfigMap
metadata:
  name: ns-agent-config
  namespace: tenant-acme
data:
  config.yaml: |
    # Overrides for tenant-acme namespace
    sandbox:
      default_trust_level: standard

    resources:
      max_limits:
        cpu: "4"
        memory: "4Gi"
      token_budget:
        max_per_hour: 500000

    fleet:
      max_replicas: 50
```

## 10.3 Environment Variables

| Variable | Description | Default | Scope |
|----------|-------------|---------|-------|
| `L02_CONFIG_PATH` | Path to config file | `/etc/agent-runtime/config.yaml` | Cluster |
| `L02_LOG_LEVEL` | Log verbosity | `INFO` | Cluster |
| `L02_METRICS_PORT` | Prometheus port | `9090` | Cluster |
| `L02_SESSION_BRIDGE_ENDPOINT` | L01 Phase 16 endpoint | - | Cluster |
| `L02_DOCUMENT_BRIDGE_ENDPOINT` | L01 Phase 15 endpoint | - | Cluster |
| `L02_MODEL_BRIDGE_ENDPOINT` | L04 endpoint | - | Cluster |
| `L02_NAMESPACE` | Operating namespace | `l02-system` | Cluster |
| `L02_DEFAULT_RUNTIME_CLASS` | Default sandbox | `gvisor` | Cluster |
| `AGENT_ID` | Agent instance ID | - | Agent |
| `SESSION_ID` | Session ID from L01 | - | Agent |
| `AGENT_DID` | Agent DID | - | Agent |
| `TRUST_LEVEL` | Agent trust level | - | Agent |

## 10.4 Feature Flags

```yaml
feature_flags:
  # Sandbox technology selection
  enable_gvisor: true
  enable_kata: true
  enable_kata_cc: false  # Confidential computing (v1.1)

  # Warm pool
  enable_warm_pool: true
  warm_pool_snapshot_restore: false  # Firecracker snapshots (v1.1)

  # Integration features
  enable_document_bridge: true
  enable_session_bridge: true
  enable_auto_checkpoint: true

  # Experimental
  enable_multi_agent_workflows: true
  enable_gang_scheduling: false  # K8s 1.35+ required

  # Observability
  enable_detailed_tracing: false
  enable_profiling: false
```

## 10.5 Hot Reload Capability

### 10.5.1 Supported Hot Reload

| Configuration | Hot Reload | Mechanism |
|---------------|------------|-----------|
| Log level | Yes | ConfigMap watch |
| Feature flags | Yes | ConfigMap watch |
| Resource quotas | Yes | ConfigMap watch |
| Scaling thresholds | Yes | ConfigMap watch |
| Sandbox defaults | No | Requires restart |
| Integration endpoints | No | Requires restart |
| Security policies | No | Requires restart |

### 10.5.2 Hot Reload Implementation

```python
class ConfigWatcher:
    """Watch for configuration changes and apply hot reload."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._current_config: Optional[Config] = None
        self._callbacks: list[Callable[[Config, Config], None]] = []

    async def start(self):
        """Start watching configuration file."""
        async for changes in watchfiles.awatch(self.config_path):
            try:
                new_config = self._load_config()
                if new_config != self._current_config:
                    old_config = self._current_config
                    self._current_config = new_config
                    await self._notify_callbacks(old_config, new_config)
                    logger.info("Configuration reloaded", changes=changes)
            except Exception as e:
                logger.error("Failed to reload configuration", error=str(e))

    async def _notify_callbacks(
        self,
        old_config: Optional[Config],
        new_config: Config
    ):
        """Notify registered callbacks of configuration change."""
        for callback in self._callbacks:
            try:
                await callback(old_config, new_config)
            except Exception as e:
                logger.error("Callback failed", callback=callback.__name__, error=str(e))
```

---

# Gap Tracking Table (Part 2)

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| G-006 | Health Probe Specification | Critical | Section 9 | Metrics (9.1), Alerting (9.4) |
*Cumulative gaps addressed: 19 of 23*
# Agent Runtime Layer Specification - Part 3

**Version:** 1.0
**Status:** Draft
**Layer ID:** L02
**Date:** 2025-01-14

---

# Section 11: Implementation Guide

## 11.1 Implementation Phases

| Phase | Name | Duration | Components | Dependencies |
|-------|------|----------|------------|--------------|
| 1 | Foundation | 4 weeks | Sandbox Manager, Lifecycle Manager | L00 RuntimeClass |
| 2 | Core Execution | 4 weeks | Agent Executor, Resource Manager | Phase 1 |
| 3 | State Management | 3 weeks | State Manager, SessionBridge | Phase 2, L01 Phase 16 |
| 4 | Document Integration | 2 weeks | DocumentBridge | Phase 2, L01 Phase 15 |
| 5 | Fleet Operations | 3 weeks | Fleet Manager, Warm Pool | Phase 1, Phase 2 |
| 6 | Observability | 2 weeks | Health Monitor, Metrics, Logging | All phases |
| 7 | Workflow Engine | 3 weeks | Workflow Engine, Multi-Agent | Phase 2, Phase 3 |
| 8 | Hardening | 2 weeks | Security review, Performance tuning | All phases |

## 11.2 Implementation Order

```
+------------------------------------------------------------------+
|                  Implementation Dependency Graph                  |
|                                                                  |
|  Phase 1: Foundation                                             |
|  +------------------+     +------------------+                    |
|  | Sandbox Manager  |<----| L00 RuntimeClass |                    |
|  +--------+---------+     +------------------+                    |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  | Lifecycle Manager|                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  Phase 2: Core Execution                                         |
|  +--------+---------+     +------------------+                    |
|  | Agent Executor   |---->| Resource Manager |                    |
|  +--------+---------+     +--------+---------+                    |
|           |                        |                              |
|           +------------------------+                              |
|           |                                                       |
|           v                                                       |
|  Phase 3: State Management        Phase 4: Documents              |
|  +--------+---------+     +------------------+                    |
|  | State Manager    |     | DocumentBridge   |                    |
|  +--------+---------+     +------------------+                    |
|           |                        ^                              |
|           v                        |                              |
|  +--------+---------+              |                              |
|  | SessionBridge    |--------------+                              |
|  +--------+---------+     (L01 Phase 15/16)                       |
|           |                                                       |
|           v                                                       |
|  Phase 5: Fleet Operations                                       |
|  +--------+---------+     +------------------+                    |
|  | Fleet Manager    |---->| Warm Pool Manager|                    |
|  +------------------+     +------------------+                    |
|           |                                                       |
|           v                                                       |
|  Phase 6: Observability                                          |
|  +--------+---------+     +------------------+                    |
|  | Health Monitor   |---->| Metrics/Logging  |                    |
|  +------------------+     +------------------+                    |
|           |                                                       |
|           v                                                       |
|  Phase 7: Workflows                                              |
|  +--------+---------+                                             |
|  | Workflow Engine  |                                             |
|  +------------------+                                             |
|                                                                  |
+------------------------------------------------------------------+
```

## 11.3 Kubernetes Feature Status Notes

### 11.3.0 Container Checkpointing (CRIU) Status

Container checkpointing via CRIU and the Kubelet Checkpoint API is alpha (Kubernetes v1.25+).

**Production Considerations:**
- Feature gate `ContainerCheckpoint` must be enabled
- CRI-O requires `--enable-criu-support=true` flag
- Security implications not fully documented by Kubernetes SIG
- Checkpointed containers can only be restored outside Kubernetes at container engine level

**Recommendation:** Production deployments SHOULD use L01 SessionBridge integration for checkpointing rather than native CRIU. SessionBridge provides:
- Application-level state serialization
- Cross-cluster portability
- No kernel-level dependencies
- Full Kubernetes lifecycle integration

```python
# Preferred: SessionBridge checkpointing
await session_bridge.save_context_snapshot(session_id, context)

# Alternative: Native CRIU (alpha, use with caution)
# Requires: ContainerCheckpoint feature gate, CRI-O support
# kubectl checkpoint <pod> <container> --export=checkpoint.tar
```

## 11.4 Component Implementation Details

### 11.4.1 Sandbox Manager

**Purpose:** Configure and manage agent isolation using Kubernetes RuntimeClass.

**Implementation Approach:**
1. Query L00 for available RuntimeClasses
2. Implement trust level to RuntimeClass mapping
3. Generate pod security contexts
4. Validate sandbox availability before spawn

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import kubernetes_asyncio as kubernetes

class TrustLevel(Enum):
    TRUSTED = "trusted"
    STANDARD = "standard"
    UNTRUSTED = "untrusted"
    CONFIDENTIAL = "confidential"

@dataclass
class SandboxConfig:
    runtime_class: str
    security_context: dict
    network_policy: str
    resource_limits: dict

class SandboxManager:
    """Manage agent sandbox configuration."""

    TRUST_LEVEL_MAPPING = {
        TrustLevel.TRUSTED: "runc",
        TrustLevel.STANDARD: "gvisor",
        TrustLevel.UNTRUSTED: "kata",
        TrustLevel.CONFIDENTIAL: "kata-cc",
    }

    def __init__(self, config: dict):
        self.config = config
        self._available_runtimes: set[str] = set()

    async def initialize(self) -> None:
        """Load available RuntimeClasses from cluster."""
        async with kubernetes.client.ApiClient() as api:
            node_api = kubernetes.client.NodeV1Api(api)
            runtime_classes = await node_api.list_runtime_class()
            self._available_runtimes = {
                rc.metadata.name for rc in runtime_classes.items
            }

    def get_sandbox_config(
        self,
        trust_level: TrustLevel,
        custom_limits: Optional[dict] = None
    ) -> SandboxConfig:
        """Generate sandbox configuration for trust level."""
        runtime_class = self.TRUST_LEVEL_MAPPING.get(
            trust_level,
            self.config["default_runtime_class"]
        )

        if runtime_class not in self._available_runtimes:
            raise SandboxError(
                code="E2040",
                message=f"RuntimeClass {runtime_class} not available"
            )

        return SandboxConfig(
            runtime_class=runtime_class,
            security_context=self._build_security_context(trust_level),
            network_policy=self._get_network_policy(trust_level),
            resource_limits=custom_limits or self.config["default_limits"]
        )

    def _build_security_context(self, trust_level: TrustLevel) -> dict:
        """Build Kubernetes security context."""
        base_context = {
            "runAsNonRoot": True,
            "runAsUser": 65534,
            "runAsGroup": 65534,
            "fsGroup": 65534,
            "readOnlyRootFilesystem": True,
            "allowPrivilegeEscalation": False,
            "seccompProfile": {"type": "RuntimeDefault"},
            "capabilities": {"drop": ["ALL"]},
        }

        if trust_level == TrustLevel.TRUSTED:
            # Slightly relaxed for trusted code
            base_context["readOnlyRootFilesystem"] = False

        return base_context

    def _get_network_policy(self, trust_level: TrustLevel) -> str:
        """Determine network policy based on trust level."""
        if trust_level in (TrustLevel.UNTRUSTED, TrustLevel.CONFIDENTIAL):
            return "isolated"
        return "restricted"
```

### 11.3.2 Agent Executor

**Purpose:** Execute agent code with tool invocation and context management.

```python
from typing import AsyncIterator, Optional
from dataclasses import dataclass
import asyncio

@dataclass
class ToolInvocation:
    name: str
    arguments: dict
    timeout: float = 300.0

@dataclass
class ExecutionResult:
    output: str
    tool_calls: list[ToolInvocation]
    tokens_used: int
    duration_ms: int

class AgentExecutor:
    """Execute agent code within sandbox."""

    def __init__(
        self,
        model_bridge: "ModelBridge",
        document_bridge: "DocumentBridge",
        resource_manager: "ResourceManager",
        config: dict
    ):
        self.model_bridge = model_bridge
        self.document_bridge = document_bridge
        self.resource_manager = resource_manager
        self.config = config
        self._tools: dict[str, callable] = {}

    def register_tool(self, name: str, handler: callable) -> None:
        """Register a tool handler."""
        self._tools[name] = handler

    async def execute(
        self,
        agent_id: str,
        session_id: str,
        input_message: str,
        context: dict
    ) -> AsyncIterator[str]:
        """Execute agent with streaming response."""
        # Check budget before execution
        budget = await self.resource_manager.get_budget(agent_id)
        if budget.remaining <= 0:
            raise ResourceError(
                code="E2072",
                message="Token budget exhausted"
            )

        # Build messages with context
        messages = self._build_messages(input_message, context)

        # Stream inference response
        async for chunk in self.model_bridge.infer_stream(
            agent_id=agent_id,
            session_id=session_id,
            messages=messages,
            tools=list(self._tools.keys())
        ):
            if chunk.type == "text":
                yield chunk.content
            elif chunk.type == "tool_call":
                # Execute tool and continue
                tool_result = await self._invoke_tool(
                    chunk.tool_name,
                    chunk.arguments,
                    agent_id
                )
                # Feed result back to model
                async for sub_chunk in self._continue_with_tool_result(
                    agent_id, session_id, messages, chunk, tool_result
                ):
                    yield sub_chunk

    async def _invoke_tool(
        self,
        tool_name: str,
        arguments: dict,
        agent_id: str
    ) -> str:
        """Invoke a registered tool."""
        if tool_name not in self._tools:
            raise ToolError(
                code="E2001",
                message=f"Unknown tool: {tool_name}"
            )

        handler = self._tools[tool_name]
        timeout = self.config.get("tool_timeout_seconds", 300)

        try:
            result = await asyncio.wait_for(
                handler(arguments, agent_id=agent_id),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise ToolError(
                code="E2002",
                message=f"Tool {tool_name} timed out after {timeout}s"
            )
```

### 11.3.3 Resource Manager

**Purpose:** Enforce CPU, memory, and token quotas per agent.

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import asyncio

@dataclass
class ResourceBudget:
    allocated: int
    consumed: int
    remaining: int
    reset_at: Optional[datetime] = None

@dataclass
class ResourceUsage:
    cpu_seconds: float
    memory_peak_mb: float
    tokens_consumed: int

class ResourceManager:
    """Manage and enforce resource quotas."""

    def __init__(
        self,
        model_bridge: "ModelBridge",
        event_emitter: "EventEmitter",
        config: dict
    ):
        self.model_bridge = model_bridge
        self.event_emitter = event_emitter
        self.config = config
        self._budgets: dict[str, ResourceBudget] = {}
        self._usage: dict[str, ResourceUsage] = {}

    async def initialize_budget(
        self,
        agent_id: str,
        limits: dict
    ) -> None:
        """Initialize resource budget for agent."""
        tokens_per_hour = limits.get(
            "tokens_per_hour",
            self.config["default_limits"]["tokens_per_hour"]
        )

        self._budgets[agent_id] = ResourceBudget(
            allocated=tokens_per_hour,
            consumed=0,
            remaining=tokens_per_hour,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )

        self._usage[agent_id] = ResourceUsage(
            cpu_seconds=0.0,
            memory_peak_mb=0.0,
            tokens_consumed=0
        )

    async def consume_tokens(
        self,
        agent_id: str,
        tokens: int
    ) -> ResourceBudget:
        """Record token consumption and check budget."""
        if agent_id not in self._budgets:
            raise ResourceError(
                code="E2073",
                message=f"No budget initialized for agent {agent_id}"
            )

        budget = self._budgets[agent_id]

        # Check for budget reset
        if budget.reset_at and datetime.utcnow() > budget.reset_at:
            budget.consumed = 0
            budget.remaining = budget.allocated
            budget.reset_at = datetime.utcnow() + timedelta(hours=1)

        # Consume tokens
        budget.consumed += tokens
        budget.remaining = max(0, budget.allocated - budget.consumed)

        # Update usage tracking
        self._usage[agent_id].tokens_consumed += tokens

        # Check thresholds
        usage_percent = budget.consumed / budget.allocated * 100

        if usage_percent >= 90:
            await self.event_emitter.emit(
                "agent.resource.warning",
                {
                    "agent_id": agent_id,
                    "resource_type": "tokens",
                    "current_usage": budget.consumed,
                    "limit": budget.allocated,
                    "threshold_percent": 90
                }
            )

        if budget.remaining <= 0:
            action = self.config.get("token_budget_action", "suspend")
            await self.event_emitter.emit(
                "agent.resource.exceeded",
                {
                    "agent_id": agent_id,
                    "resource_type": "tokens",
                    "limit": budget.allocated,
                    "actual": budget.consumed,
                    "action_taken": action
                }
            )

        return budget

    async def get_budget(self, agent_id: str) -> ResourceBudget:
        """Get current budget status."""
        if agent_id not in self._budgets:
            raise ResourceError(
                code="E2073",
                message=f"No budget for agent {agent_id}"
            )
        return self._budgets[agent_id]

    async def get_usage(self, agent_id: str) -> ResourceUsage:
        """Get current resource usage."""
        return self._usage.get(agent_id, ResourceUsage(0, 0, 0))
```

### 11.3.4 Fleet Manager

**Purpose:** Manage horizontal scaling, warm pools, and graceful drain.

```python
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class FleetStatus:
    total_instances: int
    running: int
    suspended: int
    warm_pool_size: int
    pending_scale_operations: int

@dataclass
class ScaleOperation:
    direction: str  # "up" | "down"
    target_delta: int
    reason: str
    initiated_at: datetime

class FleetManager:
    """Manage agent fleet operations."""

    def __init__(
        self,
        lifecycle_manager: "LifecycleManager",
        state_manager: "StateManager",
        warm_pool: "WarmPoolManager",
        config: dict
    ):
        self.lifecycle_manager = lifecycle_manager
        self.state_manager = state_manager
        self.warm_pool = warm_pool
        self.config = config
        self._pending_operations: list[ScaleOperation] = []

    async def get_status(self) -> FleetStatus:
        """Get current fleet status."""
        agents = await self.lifecycle_manager.list_agents()

        return FleetStatus(
            total_instances=len(agents),
            running=sum(1 for a in agents if a.state == AgentState.RUNNING),
            suspended=sum(1 for a in agents if a.state == AgentState.SUSPENDED),
            warm_pool_size=self.warm_pool.current_size(),
            pending_scale_operations=len(self._pending_operations)
        )

    async def scale_up(
        self,
        count: int,
        reason: str,
        config: Optional[dict] = None
    ) -> list[str]:
        """Scale up fleet by spawning new agents."""
        operation = ScaleOperation(
            direction="up",
            target_delta=count,
            reason=reason,
            initiated_at=datetime.utcnow()
        )
        self._pending_operations.append(operation)

        agent_ids = []
        try:
            for _ in range(count):
                # Try warm pool first
                warm_instance = await self.warm_pool.acquire(timeout=1.0)
                if warm_instance:
                    agent_id = await self._activate_warm_instance(
                        warm_instance, config
                    )
                else:
                    # Cold spawn
                    agent_id = await self.lifecycle_manager.spawn(
                        config or self.config["default_agent_config"]
                    )
                agent_ids.append(agent_id)

            return agent_ids
        finally:
            self._pending_operations.remove(operation)

    async def scale_down(
        self,
        count: int,
        reason: str
    ) -> list[str]:
        """Scale down fleet by draining agents."""
        operation = ScaleOperation(
            direction="down",
            target_delta=count,
            reason=reason,
            initiated_at=datetime.utcnow()
        )
        self._pending_operations.append(operation)

        drained_ids = []
        try:
            # Select agents to drain (prefer idle, then lowest priority)
            candidates = await self._select_drain_candidates(count)

            for agent_id in candidates:
                await self.graceful_drain(agent_id)
                drained_ids.append(agent_id)

            return drained_ids
        finally:
            self._pending_operations.remove(operation)

    async def graceful_drain(
        self,
        agent_id: str,
        timeout_seconds: Optional[int] = None
    ) -> None:
        """Gracefully drain an agent before termination."""
        timeout = timeout_seconds or self.config["graceful_drain"]["timeout_seconds"]

        # Mark as draining
        await self.lifecycle_manager.mark_draining(agent_id)

        # Wait for idle or timeout
        start = datetime.utcnow()
        while (datetime.utcnow() - start).total_seconds() < timeout:
            if await self.lifecycle_manager.is_idle(agent_id):
                break
            await asyncio.sleep(1)

        # Checkpoint before termination
        if self.config["graceful_drain"]["checkpoint_before_drain"]:
            await self.state_manager.create_checkpoint(
                agent_id,
                label="pre_drain",
                checkpoint_type="pre_drain"
            )

        # Terminate
        await self.lifecycle_manager.terminate(agent_id, reason="drain")
```

### 11.3.5 SessionBridge Implementation

**Purpose:** Integrate with L01 Phase 16 Session Orchestration.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, AsyncIterator
import grpc
import asyncio

# Import generated protobuf classes
from l01.session_orchestrator.v1 import session_pb2, session_pb2_grpc

@dataclass
class SessionMetadata:
    agent_id: str
    agent_type: str
    tenant_id: str
    tags: dict[str, str]

class SessionBridge:
    """Bridge to L01 Phase 16 Session Orchestration."""

    def __init__(self, config: dict):
        self.endpoint = config["endpoint"]
        self.heartbeat_interval = config["heartbeat"]["interval_seconds"]
        self.snapshot_interval = config["snapshot"]["auto_interval_seconds"]
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[session_pb2_grpc.SessionOrchestratorStub] = None
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}
        self._snapshot_tasks: dict[str, asyncio.Task] = {}

    async def connect(self) -> None:
        """Establish gRPC connection to L01 Phase 16."""
        self._channel = grpc.aio.insecure_channel(self.endpoint)
        self._stub = session_pb2_grpc.SessionOrchestratorStub(self._channel)

    async def close(self) -> None:
        """Close gRPC connection."""
        # Cancel all background tasks
        for task in self._heartbeat_tasks.values():
            task.cancel()
        for task in self._snapshot_tasks.values():
            task.cancel()

        if self._channel:
            await self._channel.close()

    async def start_session(
        self,
        metadata: SessionMetadata
    ) -> str:
        """Start a new session with L01 Phase 16."""
        request = session_pb2.StartSessionRequest(
            agent_id=metadata.agent_id,
            agent_type=metadata.agent_type,
            tenant_id=metadata.tenant_id,
            tags=metadata.tags
        )

        response = await self._stub.StartSession(request)
        session_id = response.session_id

        # Start background heartbeat
        self._start_heartbeat(session_id)

        return session_id

    async def end_session(
        self,
        session_id: str,
        reason: str
    ) -> None:
        """End session with L01 Phase 16."""
        # Stop background tasks
        self._stop_heartbeat(session_id)
        self._stop_auto_snapshot(session_id)

        request = session_pb2.EndSessionRequest(
            session_id=session_id,
            reason=reason
        )

        await self._stub.EndSession(request)

    async def heartbeat(self, session_id: str) -> bool:
        """Send heartbeat to L01 Phase 16."""
        request = session_pb2.HeartbeatRequest(
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat()
        )

        response = await self._stub.Heartbeat(request)
        return response.acknowledged

    async def save_context_snapshot(
        self,
        session_id: str,
        context: dict
    ) -> str:
        """Save context snapshot to L01 Phase 16."""
        request = session_pb2.SaveContextSnapshotRequest(
            session_id=session_id,
            context=session_pb2.ExecutionContext(
                state=context.get("state", {}),
                memory=context.get("memory", {}),
                conversation_history=context.get("conversation_history", [])
            ),
            change_summary=f"Snapshot at {datetime.utcnow().isoformat()}"
        )

        response = await self._stub.SaveContextSnapshot(request)
        return response.snapshot_id

    async def check_recovery(
        self,
        agent_id: Optional[str] = None
    ) -> list[dict]:
        """Check for sessions needing recovery."""
        request = session_pb2.CheckRecoveryRequest(
            agent_id=agent_id or "",
            include_history=True
        )

        response = await self._stub.CheckRecovery(request)

        return [
            {
                "session_id": r.session_id,
                "agent_id": r.agent_id,
                "last_heartbeat": r.last_heartbeat,
                "recovery_prompt": r.recovery_prompt,
                "tool_history": list(r.tool_history)
            }
            for r in response.sessions_needing_recovery
        ]

    async def create_checkpoint(
        self,
        session_id: str,
        label: str,
        description: Optional[str] = None
    ) -> str:
        """Create named checkpoint."""
        request = session_pb2.CreateCheckpointRequest(
            session_id=session_id,
            label=label,
            description=description or "",
            checkpoint_type="manual"
        )

        response = await self._stub.CreateCheckpoint(request)
        return response.checkpoint_id

    async def rollback_to(
        self,
        session_id: str,
        checkpoint_id: str
    ) -> dict:
        """Rollback to a previous checkpoint."""
        request = session_pb2.RollbackToRequest(
            session_id=session_id,
            target=session_pb2.RollbackTarget(
                type="checkpoint",
                checkpoint_id=checkpoint_id
            ),
            create_backup=True
        )

        response = await self._stub.RollbackTo(request)
        return {
            "state": dict(response.restored_context.state),
            "memory": dict(response.restored_context.memory),
            "conversation_history": list(response.restored_context.conversation_history)
        }

    def _start_heartbeat(self, session_id: str) -> None:
        """Start background heartbeat task."""
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(self.heartbeat_interval)
                    await self.heartbeat(session_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")

        self._heartbeat_tasks[session_id] = asyncio.create_task(heartbeat_loop())

    def _stop_heartbeat(self, session_id: str) -> None:
        """Stop heartbeat task."""
        if task := self._heartbeat_tasks.pop(session_id, None):
            task.cancel()
```

### 11.3.6 DocumentBridge Implementation

**Purpose:** Integrate with L01 Phase 15 Document Management.

```python
from dataclasses import dataclass
from typing import Optional
from cachetools import TTLCache
import grpc

# Import generated protobuf classes
from l01.document_manager.v1 import document_pb2, document_pb2_grpc

@dataclass
class SourceOfTruthResponse:
    answer: str
    confidence: float
    sources: list[dict]
    conflicts: Optional[list[dict]] = None

class DocumentBridge:
    """Bridge to L01 Phase 15 Document Management."""

    def __init__(self, config: dict):
        self.endpoint = config["endpoint"]
        self.default_confidence = config["default_confidence_threshold"]
        self.max_sources = config["max_sources"]
        self.cache_ttl = config["cache"]["ttl_seconds"]
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[document_pb2_grpc.DocumentManagerStub] = None
        self._cache = TTLCache(
            maxsize=config["cache"]["max_size"],
            ttl=self.cache_ttl
        )

    async def connect(self) -> None:
        """Establish gRPC connection to L01 Phase 15."""
        self._channel = grpc.aio.insecure_channel(self.endpoint)
        self._stub = document_pb2_grpc.DocumentManagerStub(self._channel)

    async def close(self) -> None:
        """Close gRPC connection."""
        if self._channel:
            await self._channel.close()

    async def query_source_of_truth(
        self,
        query: str,
        scope: Optional[list[str]] = None,
        confidence_threshold: Optional[float] = None,
        max_sources: Optional[int] = None
    ) -> SourceOfTruthResponse:
        """Query authoritative documents from L01 Phase 15."""
        # Check cache
        cache_key = f"{query}:{scope}:{confidence_threshold}"
        if cached := self._cache.get(cache_key):
            return cached

        request = document_pb2.GetSourceOfTruthRequest(
            query=query,
            query_type="factual",
            scope=scope or [],
            confidence_threshold=confidence_threshold or self.default_confidence,
            max_sources=max_sources or self.max_sources,
            verify_claims=True
        )

        response = await self._stub.GetSourceOfTruth(request)

        result = SourceOfTruthResponse(
            answer=response.answer,
            confidence=response.confidence,
            sources=[
                {
                    "document_id": s.document_id,
                    "title": s.title,
                    "excerpt": s.excerpt,
                    "authority_level": s.authority_level
                }
                for s in response.sources
            ],
            conflicts=[
                {
                    "claim_a": c.claim_a,
                    "claim_b": c.claim_b,
                    "conflict_type": c.conflict_type
                }
                for c in response.conflicts
            ] if response.conflicts else None
        )

        # Cache result
        self._cache[cache_key] = result
        return result

    async def verify_claim(
        self,
        claim: str,
        scope: Optional[list[str]] = None
    ) -> dict:
        """Verify a claim against document corpus."""
        request = document_pb2.VerifyClaimRequest(
            claim=claim,
            scope=scope or [],
            include_conflicts=True
        )

        response = await self._stub.VerifyClaim(request)

        return {
            "claim": claim,
            "verified": response.is_verified,
            "confidence": response.confidence,
            "supporting_sources": [
                {"document_id": s.document_id, "title": s.title}
                for s in response.supporting
            ],
            "conflicting_sources": [
                {"document_id": s.document_id, "title": s.title}
                for s in response.conflicting
            ] if response.conflicting else None
        }

    async def ingest_document(
        self,
        content: str,
        document_type: str,
        tags: list[str],
        metadata: dict
    ) -> str:
        """Store agent-generated document in L01 Phase 15."""
        request = document_pb2.IngestDocumentRequest(
            content=content,
            document_type=document_type,
            tags=tags,
            authority_level=3,  # Agent-generated
            extract_claims=True,
            generate_embeddings=True,
            metadata=metadata
        )

        response = await self._stub.IngestDocument(request)
        return response.document_id
```

## 11.4 Code Examples

### 11.4.1 Complete Agent Spawn Flow

```python
async def spawn_agent_complete(
    config: AgentConfig,
    sandbox_manager: SandboxManager,
    lifecycle_manager: LifecycleManager,
    session_bridge: SessionBridge,
    resource_manager: ResourceManager,
    event_emitter: EventEmitter
) -> SpawnResult:
    """Complete agent spawn flow with all integrations."""

    # 1. Check for recovery needed
    recovery_info = await session_bridge.check_recovery(config.agent_id)
    if recovery_info:
        return await _resume_from_recovery(recovery_info[0], session_bridge)

    # 2. Get sandbox configuration
    sandbox_config = sandbox_manager.get_sandbox_config(
        TrustLevel(config.trust_level),
        config.resource_limits
    )

    # 3. Start session with L01 Phase 16
    session_id = await session_bridge.start_session(
        SessionMetadata(
            agent_id=config.agent_id,
            agent_type=config.agent_type or "default",
            tenant_id=config.tenant_id or "default",
            tags=config.tags or {}
        )
    )

    # 4. Initialize resource budget
    await resource_manager.initialize_budget(
        config.agent_id,
        config.resource_limits or {}
    )

    # 5. Create pod via Lifecycle Manager
    try:
        pod = await lifecycle_manager.create_pod(
            agent_id=config.agent_id,
            session_id=session_id,
            sandbox_config=sandbox_config,
            environment=config.environment
        )
    except Exception as e:
        # Cleanup on failure
        await session_bridge.end_session(session_id, f"spawn_failed: {e}")
        raise SpawnError(code="E2020", message=str(e))

    # 6. Emit spawned event
    await event_emitter.emit(
        "agent.spawned",
        {
            "agent_id": config.agent_id,
            "session_id": session_id,
            "sandbox_type": sandbox_config.runtime_class,
            "resource_limits": config.resource_limits,
            "trust_level": config.trust_level
        }
    )

    return SpawnResult(
        agent_id=config.agent_id,
        session_id=session_id,
        state=AgentState.RUNNING,
        sandbox_type=sandbox_config.runtime_class
    )
```

## 11.5 Error Codes Registry

| Code | Name | Severity | Component | Description |
|------|------|----------|-----------|-------------|
| E2001 | TOOL_INVOCATION_FAILED | Error | Agent Executor | Tool execution failed |
| E2002 | TOOL_TIMEOUT | Error | Agent Executor | Tool exceeded timeout |
| E2003 | CONTEXT_OVERFLOW | Error | Agent Executor | Context window exceeded |
| E2004 | STREAMING_ERROR | Error | Agent Executor | Stream processing failed |
| E2010 | GRAPH_CYCLE_DETECTED | Error | Workflow Engine | Infinite loop detected |
| E2011 | GRAPH_DEPTH_EXCEEDED | Error | Workflow Engine | Max depth exceeded |
| E2012 | NODE_EXECUTION_FAILED | Error | Workflow Engine | Node failed execution |
| E2013 | BRANCH_TIMEOUT | Error | Workflow Engine | Parallel branch timeout |
| E2020 | SPAWN_FAILED | Error | Lifecycle Manager | Agent spawn failed |
| E2021 | SPAWN_TIMEOUT | Error | Lifecycle Manager | Spawn exceeded timeout |
| E2022 | TERMINATE_FAILED | Error | Lifecycle Manager | Clean termination failed |
| E2023 | SUSPEND_FAILED | Error | Lifecycle Manager | Suspend operation failed |
| E2024 | RESUME_FAILED | Error | Lifecycle Manager | Resume from suspend failed |
| E2025 | RESTART_LIMIT_EXCEEDED | Error | Lifecycle Manager | Max restarts reached |
| E2030 | CHECKPOINT_FAILED | Error | State Manager | Checkpoint creation failed |
| E2031 | CHECKPOINT_TOO_LARGE | Error | State Manager | Exceeds size limit |
| E2032 | RESTORE_FAILED | Error | State Manager | State restoration failed |
| E2033 | CHECKPOINT_CORRUPTED | Error | State Manager | Checkpoint data invalid |
| E2040 | RUNTIME_CLASS_UNAVAILABLE | Error | Sandbox Manager | Requested runtime not available |
| E2041 | SANDBOX_CREATION_FAILED | Error | Sandbox Manager | Sandbox setup failed |
| E2042 | SECURITY_POLICY_VIOLATION | Error | Sandbox Manager | Security context violation |
| E2050 | SESSION_START_FAILED | Error | SessionBridge | Failed to start session |
| E2051 | HEARTBEAT_FAILED | Warning | SessionBridge | Heartbeat not acknowledged |
| E2052 | SNAPSHOT_SAVE_FAILED | Error | SessionBridge | Context snapshot failed |
| E2053 | RECOVERY_CHECK_FAILED | Error | SessionBridge | Recovery check failed |
| E2054 | SESSION_NOT_FOUND | Error | SessionBridge | Session ID not found |
| E2060 | DOCUMENT_QUERY_FAILED | Error | DocumentBridge | Query execution failed |
| E2061 | NO_AUTHORITATIVE_SOURCE | Warning | DocumentBridge | No source of truth found |
| E2062 | CLAIM_VERIFICATION_FAILED | Warning | DocumentBridge | Claim could not be verified |
| E2063 | DOCUMENT_NOT_FOUND | Error | DocumentBridge | Document ID not found |
| E2070 | CPU_LIMIT_EXCEEDED | Error | Resource Manager | CPU quota exceeded |
| E2071 | MEMORY_LIMIT_EXCEEDED | Error | Resource Manager | Memory quota exceeded |
| E2072 | TOKEN_BUDGET_EXCEEDED | Error | Resource Manager | Token budget exhausted |
| E2073 | QUOTA_UPDATE_FAILED | Error | Resource Manager | Failed to update quota |
| E2080 | LIVENESS_CHECK_FAILED | Error | Health Monitor | Agent not alive |
| E2081 | READINESS_CHECK_FAILED | Warning | Health Monitor | Agent not ready |
| E2082 | AGENT_STUCK | Warning | Health Monitor | No progress detected |
| E2083 | METRICS_COLLECTION_FAILED | Warning | Health Monitor | Failed to collect metrics |
| E2090 | SCALE_UP_FAILED | Error | Fleet Manager | Failed to scale up |
| E2091 | SCALE_DOWN_FAILED | Error | Fleet Manager | Failed to scale down |
| E2092 | WARM_POOL_EXHAUSTED | Warning | Fleet Manager | No warm instances available |
| E2093 | DRAIN_TIMEOUT | Warning | Fleet Manager | Graceful drain exceeded timeout |
| E2100 | INFERENCE_FAILED | Error | ModelBridge | LLM inference failed |
| E2101 | MODEL_UNAVAILABLE | Error | ModelBridge | Requested model not available |
| E2102 | INFERENCE_TIMEOUT | Error | ModelBridge | Request exceeded timeout |
| E2103 | RATE_LIMITED | Warning | ModelBridge | Provider rate limit hit |

---

# Section 12: Testing Strategy

## 12.1 Test Categories

| Category | Purpose | Frequency | Owner |
|----------|---------|-----------|-------|
| Unit | Component isolation testing | Per commit | Developers |
| Integration | Cross-layer interaction testing | Per PR | Developers |
| Performance | Latency and throughput validation | Daily | QA |
| Chaos | Failure mode testing | Weekly | SRE |
| Security | Sandbox escape and vulnerability testing | Per release | Security |
| End-to-End | Full workflow validation | Per release | QA |

## 12.2 Unit Tests

### 12.2.1 Sandbox Manager Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from l02.sandbox import SandboxManager, TrustLevel, SandboxError

@pytest.fixture
def sandbox_manager():
    config = {
        "default_runtime_class": "gvisor",
        "default_limits": {"cpu": "2", "memory": "2Gi"}
    }
    manager = SandboxManager(config)
    manager._available_runtimes = {"runc", "gvisor", "kata"}
    return manager

class TestSandboxManager:
    def test_get_sandbox_config_standard(self, sandbox_manager):
        config = sandbox_manager.get_sandbox_config(TrustLevel.STANDARD)

        assert config.runtime_class == "gvisor"
        assert config.security_context["runAsNonRoot"] is True
        assert config.network_policy == "restricted"

    def test_get_sandbox_config_untrusted(self, sandbox_manager):
        config = sandbox_manager.get_sandbox_config(TrustLevel.UNTRUSTED)

        assert config.runtime_class == "kata"
        assert config.network_policy == "isolated"

    def test_unavailable_runtime_raises_error(self, sandbox_manager):
        sandbox_manager._available_runtimes = {"runc"}

        with pytest.raises(SandboxError) as exc_info:
            sandbox_manager.get_sandbox_config(TrustLevel.UNTRUSTED)

        assert exc_info.value.code == "E2040"

    def test_custom_limits_override(self, sandbox_manager):
        custom = {"cpu": "4", "memory": "4Gi"}
        config = sandbox_manager.get_sandbox_config(
            TrustLevel.STANDARD,
            custom_limits=custom
        )

        assert config.resource_limits == custom
```

### 12.2.2 Resource Manager Tests

```python
@pytest.fixture
def resource_manager():
    config = {
        "default_limits": {"tokens_per_hour": 100000},
        "token_budget_action": "suspend"
    }
    model_bridge = AsyncMock()
    event_emitter = AsyncMock()
    return ResourceManager(model_bridge, event_emitter, config)

class TestResourceManager:
    @pytest.mark.asyncio
    async def test_initialize_budget(self, resource_manager):
        await resource_manager.initialize_budget(
            "agent-123",
            {"tokens_per_hour": 50000}
        )

        budget = await resource_manager.get_budget("agent-123")
        assert budget.allocated == 50000
        assert budget.remaining == 50000

    @pytest.mark.asyncio
    async def test_consume_tokens_updates_budget(self, resource_manager):
        await resource_manager.initialize_budget("agent-123", {})

        budget = await resource_manager.consume_tokens("agent-123", 10000)

        assert budget.consumed == 10000
        assert budget.remaining == 90000

    @pytest.mark.asyncio
    async def test_budget_exceeded_emits_event(self, resource_manager):
        await resource_manager.initialize_budget(
            "agent-123",
            {"tokens_per_hour": 1000}
        )

        await resource_manager.consume_tokens("agent-123", 1500)

        resource_manager.event_emitter.emit.assert_called()
        call_args = resource_manager.event_emitter.emit.call_args
        assert call_args[0][0] == "agent.resource.exceeded"
```

## 12.3 Integration Tests

### 12.3.1 L01 Phase 16 Integration Test

```python
@pytest.mark.integration
class TestSessionBridgeIntegration:
    @pytest.fixture
    async def session_bridge(self):
        bridge = SessionBridge({
            "endpoint": "localhost:50051",
            "heartbeat": {"interval_seconds": 5},
            "snapshot": {"auto_interval_seconds": 60}
        })
        await bridge.connect()
        yield bridge
        await bridge.close()

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, session_bridge):
        # Start session
        session_id = await session_bridge.start_session(
            SessionMetadata(
                agent_id="test-agent",
                agent_type="test",
                tenant_id="test-tenant",
                tags={}
            )
        )
        assert session_id is not None

        # Heartbeat
        ack = await session_bridge.heartbeat(session_id)
        assert ack is True

        # Save snapshot
        snapshot_id = await session_bridge.save_context_snapshot(
            session_id,
            {"state": {"step": 1}, "memory": {}, "conversation_history": []}
        )
        assert snapshot_id is not None

        # End session
        await session_bridge.end_session(session_id, "test_complete")

    @pytest.mark.asyncio
    async def test_checkpoint_and_rollback(self, session_bridge):
        session_id = await session_bridge.start_session(
            SessionMetadata(
                agent_id="test-agent",
                agent_type="test",
                tenant_id="test-tenant",
                tags={}
            )
        )

        # Create checkpoint
        checkpoint_id = await session_bridge.create_checkpoint(
            session_id,
            label="before_risky_operation"
        )

        # Rollback
        restored = await session_bridge.rollback_to(session_id, checkpoint_id)
        assert "state" in restored

        await session_bridge.end_session(session_id, "test_complete")
```

## 12.4 Performance Tests

### 12.4.1 Spawn Latency Test

```python
@pytest.mark.performance
class TestSpawnPerformance:
    @pytest.mark.asyncio
    async def test_cold_spawn_latency(self, agent_runtime):
        """Cold spawn should complete within 10s (p99)."""
        latencies = []

        for _ in range(100):
            start = time.monotonic()
            result = await agent_runtime.spawn(
                AgentConfig(
                    agent_id=str(uuid.uuid4()),
                    trust_level="standard",
                    resource_limits={}
                )
            )
            latency = time.monotonic() - start
            latencies.append(latency)

            await agent_runtime.terminate(result.agent_id, "test")

        p99 = np.percentile(latencies, 99)
        assert p99 < 10.0, f"p99 spawn latency {p99}s exceeds 10s threshold"

    @pytest.mark.asyncio
    async def test_warm_spawn_latency(self, agent_runtime, warm_pool):
        """Warm spawn should complete within 1s (p99)."""
        # Pre-warm pool
        await warm_pool.replenish_to(10)

        latencies = []
        for _ in range(50):
            start = time.monotonic()
            result = await agent_runtime.spawn_from_warm_pool(
                AgentConfig(
                    agent_id=str(uuid.uuid4()),
                    trust_level="standard"
                )
            )
            latency = time.monotonic() - start
            latencies.append(latency)

            await agent_runtime.terminate(result.agent_id, "test")

        p99 = np.percentile(latencies, 99)
        assert p99 < 1.0, f"p99 warm spawn latency {p99}s exceeds 1s threshold"
```

## 12.5 Chaos Tests

### 12.5.1 Agent Crash Recovery Test

```python
@pytest.mark.chaos
class TestChaosRecovery:
    @pytest.mark.asyncio
    async def test_agent_crash_recovery(
        self,
        agent_runtime,
        session_bridge,
        chaos_controller
    ):
        """Agent should recover from crash using checkpoint."""
        # Spawn agent and run some work
        result = await agent_runtime.spawn(test_config)
        await agent_runtime.execute(result.agent_id, "Do some work")

        # Simulate crash
        await chaos_controller.kill_pod(result.agent_id)

        # Wait for detection
        await asyncio.sleep(60)

        # Check recovery info exists
        recovery = await session_bridge.check_recovery(result.agent_id)
        assert len(recovery) > 0

        # Spawn should auto-recover
        new_result = await agent_runtime.spawn(
            AgentConfig(agent_id=result.agent_id, trust_level="standard")
        )
        assert new_result.state == AgentState.RUNNING
```

## 12.6 Security Tests

### 12.6.1 Sandbox Escape Test

```python
@pytest.mark.security
class TestSandboxSecurity:
    @pytest.mark.asyncio
    async def test_cannot_access_host_filesystem(self, sandboxed_agent):
        """Agent should not be able to read host files."""
        result = await sandboxed_agent.execute_code(
            "import os; os.listdir('/host')"
        )
        assert "PermissionError" in result or "No such file" in result

    @pytest.mark.asyncio
    async def test_cannot_escalate_privileges(self, sandboxed_agent):
        """Agent should not be able to escalate privileges."""
        result = await sandboxed_agent.execute_code(
            "import os; os.setuid(0)"
        )
        assert "Operation not permitted" in result

    @pytest.mark.asyncio
    async def test_network_isolation(self, sandboxed_agent):
        """Agent should not reach unauthorized endpoints."""
        result = await sandboxed_agent.execute_code(
            "import socket; s = socket.socket(); s.connect(('evil.com', 80))"
        )
        assert "Connection refused" in result or "Network is unreachable" in result
```

## 12.7 Test Examples

### 12.7.1 Complete Test Suite Setup

```python
# conftest.py
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def l01_services():
    """Start L01 services for integration tests."""
    # Use docker-compose or testcontainers
    async with L01TestServices() as services:
        yield services

@pytest.fixture
async def agent_runtime(l01_services):
    """Create agent runtime with test configuration."""
    runtime = AgentRuntime(
        session_bridge_endpoint=l01_services.session_orchestrator,
        document_bridge_endpoint=l01_services.document_manager,
        model_bridge_endpoint="mock://model-gateway"
    )
    await runtime.initialize()
    yield runtime
    await runtime.shutdown()
```

---

# Section 13: Migration and Deployment

## 13.1 Supply Chain Security Requirements

### 13.1.1 SBOM Generation (OWASP Compliance)

All agent container images MUST include Software Bill of Materials (SBOM) per OWASP supply chain security guidelines.

**Requirements:**
- Generate SBOM in CycloneDX or SPDX format for every container image
- Include all dependencies, libraries, and base image components
- Store SBOM alongside image in registry (e.g., OCI artifact)
- Scan SBOM for known vulnerabilities before deployment
- Maintain SBOM provenance for audit trails

```bash
# Example: Generate SBOM with syft
syft packages registry.example.com/l02/agent-runtime:v1.2 \
  -o cyclonedx-json > agent-runtime-sbom.json

# Attach SBOM to image as OCI artifact
cosign attach sbom --sbom agent-runtime-sbom.json \
  registry.example.com/l02/agent-runtime:v1.2
```

### 13.1.2 Image Verification

```bash
# Sign images with cosign
cosign sign --key cosign.key registry.example.com/l02/agent-runtime:v1.2

# Verify signatures before deployment
cosign verify --key cosign.pub registry.example.com/l02/agent-runtime:v1.2
```

## 13.2 Deployment Strategy

### 13.2.1 Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-runtime-controller
  namespace: l02-system
  labels:
    app.kubernetes.io/name: agent-runtime
    app.kubernetes.io/component: controller
    app.kubernetes.io/part-of: l02-system
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: agent-runtime-controller
  template:
    metadata:
      labels:
        app: agent-runtime-controller
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      serviceAccountName: agent-runtime-controller
      securityContext:
        runAsNonRoot: true
        fsGroup: 65534
      containers:
        - name: controller
          image: agent-runtime:v1.0.0
          ports:
            - containerPort: 8080
              name: http
            - containerPort: 9090
              name: metrics
          env:
            - name: L02_CONFIG_PATH
              value: /etc/agent-runtime/config.yaml
            - name: L02_SESSION_BRIDGE_ENDPOINT
              value: l01-session-orchestrator.l01-system:50051
            - name: L02_DOCUMENT_BRIDGE_ENDPOINT
              value: l01-document-manager.l01-system:50052
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: config
              mountPath: /etc/agent-runtime
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: agent-runtime-config
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: agent-runtime-controller
              topologyKey: topology.kubernetes.io/zone
```

## 13.2 Upgrade Procedures

### 13.2.1 Rolling Update Process

1. **Pre-upgrade checks**
   ```bash
   # Verify current health
   kubectl get pods -n l02-system -l app=agent-runtime-controller

   # Check for in-flight agents
   kubectl exec -n l02-system deploy/agent-runtime-controller -- \
     curl localhost:8080/api/v1/agents?state=running
   ```

2. **Trigger rolling update**
   ```bash
   # Update image tag
   kubectl set image deployment/agent-runtime-controller \
     controller=agent-runtime:v1.1.0 \
     -n l02-system

   # Monitor rollout
   kubectl rollout status deployment/agent-runtime-controller -n l02-system
   ```

3. **Post-upgrade validation**
   ```bash
   # Verify new version
   kubectl exec -n l02-system deploy/agent-runtime-controller -- \
     curl localhost:8080/version

   # Check metrics
   kubectl port-forward -n l02-system svc/agent-runtime-controller 9090:9090
   curl localhost:9090/metrics | grep agent_runtime_version
   ```

## 13.3 Rollback Procedures

### 13.3.1 Automatic Rollback

```yaml
# Deployment with rollback triggers
spec:
  progressDeadlineSeconds: 600
  minReadySeconds: 30
```

### 13.3.2 Manual Rollback

```bash
# Immediate rollback to previous revision
kubectl rollout undo deployment/agent-runtime-controller -n l02-system

# Rollback to specific revision
kubectl rollout undo deployment/agent-runtime-controller \
  --to-revision=3 -n l02-system

# Verify rollback
kubectl rollout history deployment/agent-runtime-controller -n l02-system
```

## 13.4 Disaster Recovery

### 13.4.1 Using Phase 16 Checkpoints

```python
async def disaster_recovery_procedure():
    """Recover agents from L01 Phase 16 checkpoints after disaster."""

    # 1. List all sessions needing recovery
    recovery_list = await session_bridge.check_recovery()

    logger.info(f"Found {len(recovery_list)} sessions needing recovery")

    # 2. Recover each session
    for recovery_info in recovery_list:
        try:
            # Get latest checkpoint
            context = await session_bridge.load_context(
                recovery_info["session_id"]
            )

            # Spawn agent in recovery mode
            result = await agent_runtime.spawn(
                AgentConfig(
                    agent_id=recovery_info["agent_id"],
                    trust_level="standard",
                    recovery_checkpoint_id=recovery_info["last_checkpoint"]["id"]
                )
            )

            logger.info(
                f"Recovered agent {recovery_info['agent_id']} "
                f"from checkpoint {recovery_info['last_checkpoint']['id']}"
            )

        except Exception as e:
            logger.error(
                f"Failed to recover agent {recovery_info['agent_id']}: {e}"
            )

    # 3. Mark recovery complete
    await session_bridge.mark_recovered(recovery_list)
```

### 13.4.2 Recovery Time Objectives

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Single pod failure | 30s | 0 | Kubernetes auto-restart |
| Node failure | 5m | 60s | Pod rescheduling + checkpoint restore |
| Zone failure | 15m | 60s | Cross-zone failover + checkpoint restore |
| Region failure | 1h | 5m | DR site activation + full restore |

---

# Section 14: Open Questions and Decisions

## 14.1 Resolved Questions

| Question | Decision | Rationale | Section |
|----------|----------|-----------|---------|
| Q1: Sandboxing tech (gVisor vs Firecracker vs container)? | Tiered approach: runc (trusted), gVisor (standard), Kata (untrusted) | Balance security with performance. gVisor provides strong isolation without VM overhead for most cases. | Section 3, 8 |
| Q2: Checkpoint format for long-running agent state? | JSON serialization via L01 Phase 16 SessionBridge | Leverages existing infrastructure, enables cross-system compatibility. | Section 5, 6, 11 |
| Q3: Agent migration between nodes during scale-down? | Graceful drain with checkpoint -> terminate -> restore | Ensures no work loss. PreStop hooks coordinate with Lifecycle Manager. | Section 7, 11 |

## 14.2 Deferred Decisions

| Decision | Target Version | Rationale |
|----------|---------------|-----------|
| Confidential Computing (Kata-CC with TEE) | v1.1 | Requires TEE-capable hardware, limited availability |
| Firecracker Snapshot/Restore for Warm Pools | v1.1 | Requires Firecracker runtime support in cluster |
| AWS Bedrock Session Management API Compatibility | v1.1 | Multi-cloud consideration, requires API alignment |
| Gang Scheduling for Multi-Agent Workflows | v1.1 | Requires Kubernetes 1.35+ with Workload API |
| Service Mesh (Istio) for Advanced Multi-Tenancy | v1.2 | mTLS encryption, traffic splitting, tenant-aware observability (IV-08) |
| GKE Sandbox Native Integration | v1.2 | Google-specific gVisor optimization, automatic enablement (IV-09) |
| LangSmith Deployment (Managed LangGraph Platform) | v1.2 | Alternative to self-hosted for teams preferring managed infrastructure (IV-10) |
| GPU Workload Checkpointing via CUDA Plugins | v1.2 | Requires CRIU CUDA checkpoint support, NVIDIA driver integration (IV-11) |

## 14.3 Assumptions

| ID | Assumption | Impact if Invalid |
|----|------------|-------------------|
| A1 | L00 provides RuntimeClass for gVisor and Kata | Cannot provide tiered isolation |
| A2 | L01 Phase 16 is operational | Session management unavailable |
| A3 | L01 Phase 15 is operational | Document queries unavailable |
| A4 | L04 Model Gateway handles all LLM inference | Must implement local inference |
| A5 | Kubernetes 1.28+ is available | Missing some HPA features |
| A6 | Network policies are enforced | Agent isolation compromised |

## 14.4 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| gVisor performance overhead too high | Medium | High | Fall back to runc with restricted NetworkPolicy |
| L01 Phase 16 unavailable | Low | Critical | Local checkpoint fallback, degraded mode |
| Token budget bypass via caching | Medium | Medium | Cache-aware budget tracking |
| Warm pool stale instances | Low | Low | Periodic refresh, health validation |
| Multi-zone latency for checkpoints | Medium | Medium | Async checkpointing, local buffer |

---

# Section 15: References and Appendices

## 15.1 External References

| Reference | URL | Purpose |
|-----------|-----|---------|
| gVisor Documentation | https://gvisor.dev/docs/ | Sandbox implementation |
| Kata Containers | https://katacontainers.io/docs/ | VM-based isolation |
| Kubernetes RuntimeClass | https://kubernetes.io/docs/concepts/containers/runtime-class/ | Sandbox selection |
| Kubernetes HPA | https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ | Fleet scaling |
| OpenTelemetry | https://opentelemetry.io/docs/ | Observability |
| CloudEvents | https://cloudevents.io/ | Event format |
| LangGraph | https://docs.langchain.com/langgraph/ | Agent execution patterns |
| Google Agent Sandbox | https://github.com/google/agent-sandbox | Reference implementation |

## 15.2 Internal References

| Layer | Section | Integration Point |
|-------|---------|-------------------|
| L00 Infrastructure | Section 3 (RuntimeClass) | Sandbox provisioning |
| L00 Infrastructure | Section 4 (NetworkPolicy) | Network isolation |
| L01 Data Layer v4.0 | Phase 1 (Event Store) | Event emission |
| L01 Data Layer v4.0 | Phase 1 (DID Registry) | Agent identity |
| L01 Data Layer v4.0 | Phase 4 (Context Injector) | Context loading |
| L01 Data Layer v4.0 | Phase 9 (Lifecycle Manager) | State sync |
| L01 Data Layer v4.0 | Phase 15 (Document Manager) | Document queries |
| L01 Data Layer v4.0 | Phase 16 (Session Orchestrator) | Session management |
| L04 Model Gateway | Section 2 (InferenceService) | LLM requests |

## 15.3 Glossary

| Term | Definition |
|------|------------|
| Agent | An AI entity that executes tasks autonomously using LLM capabilities |
| Agent Executor | Component that runs agent code within sandboxed environment |
| BC-1 | Boundary Constraint 1 - sandbox nesting requirement within L00 infrastructure |
| Checkpoint | A serialized snapshot of agent execution state for recovery |
| CloudEvents | CNCF specification for describing event data in common formats |
| Context Injection | L01 Phase 4 process for loading state into agent memory |
| DID | Decentralized Identifier - cryptographic identity for agents |
| DocumentBridge | L02 component for querying authoritative documents via L01 Phase 15 |
| Error Budget | Allowed amount of unreliability before feature freeze (0.1% monthly) |
| Fleet | Collection of agent instances managed as a unit |
| Fleet Manager | Component coordinating horizontal scaling and warm pools |
| gRPC | High-performance RPC framework used for inter-layer communication |
| gVisor | Google's user-space kernel providing container isolation |
| Health Monitor | Component providing liveness/readiness probes for agents |
| Inference | LLM request-response cycle via L04 Model Gateway |
| Kata Containers | Lightweight VMs providing hardware-level isolation |
| L00 | Infrastructure Layer - Kubernetes primitives and networking |
| L01 | Agentic Data Layer - state persistence, sessions, documents |
| L02 | Agent Runtime Layer - this specification |
| L04 | Model Gateway Layer - LLM inference services |
| Lifecycle Manager | Component managing spawn/suspend/resume/terminate operations |
| ModelBridge | L02 component for routing inference requests to L04 |
| OC-1 | Operational Constraint 1 - agent-to-agent direct messaging prohibition |
| RuntimeClass | Kubernetes API for selecting container runtime |
| Sandbox | Isolated execution environment for untrusted code |
| Sandbox Manager | Component configuring gVisor/Kata/runc based on trust level |
| Session | A logical execution context spanning agent interactions |
| SessionBridge | L02 component for session management via L01 Phase 16 |
| SLI | Service Level Indicator - measurable aspect of service level |
| SLO | Service Level Objective - target value for service level indicator |
| STRIDE | Threat modeling framework (Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation) |
| TEE | Trusted Execution Environment - hardware-based isolation |
| Token Budget | Per-agent limit on LLM tokens consumed |
| Trust Level | Classification (TRUSTED, STANDARD, UNTRUSTED, CONFIDENTIAL) for sandbox selection |
| Warm Pool | Pre-initialized instances ready for immediate use |
| Workflow Engine | Component executing graph-based agent workflows |

---

# Appendix A: Gap Analysis Integration Summary

| Gap ID | Description | Priority | Section | How Addressed |
|--------|-------------|----------|---------|---------------|
| G-001 | Agent Sandbox API Definition | Critical | Section 3, 11 | Sandbox Manager component (3.3.5), Implementation (11.3.1) |
| G-002 | Checkpoint/Restore Protocol | Critical | Section 5, 11 | State Manager (3.3.4), SessionBridge impl (11.3.5) |
| G-003 | SessionBridge Implementation | Critical | Section 4, 6, 11 | Interface (4.6), Integration (6.7), Code (11.3.5) |
| G-004 | DocumentBridge Implementation | Critical | Section 4, 6, 11 | Interface (4.5), Integration (6.6), Code (11.3.6) |
| G-005 | ModelBridge Token Budget Tracking | Critical | Section 3, 4, 11 | ModelBridge (3.3.11), Resource Manager (11.3.3) |
| G-006 | Health Probe Specification | Critical | Section 9 | Metrics (9.1), Alerting (9.4) |
| G-007 | RuntimeClass Selection Logic | Critical | Section 3, 8, 11 | Sandbox Manager (3.3.5), Security (8.2), Code (11.3.1) |
| G-008 | Event Emission Protocol | Critical | Section 4, 6 | Events Published (4.3), Event Integration (6.3) |
| G-009 | Fleet Scaling Strategy | High | Section 7 | Scaling Model (7.2), Capacity Planning (7.4) |
| G-010 | Warm Pool Implementation | High | Section 7, 11 | Warm Pool Management (7.2.3), Code example |
| G-011 | Agent-Specific Metrics | High | Section 9 | Prometheus Metrics (9.1.1) |
| G-012 | Restart Policy Configuration | High | Section 10 | Configuration Schemas (10.2.1) |
| G-013 | Graceful Shutdown Protocol | High | Section 7, 11 | Graceful Degradation (7.6), Fleet Manager (11.3.4) |
| G-014 | Graph-Based Workflow Support | High | Section 3, 4 | Workflow Engine (3.3.2), Protocol (4.1.2) |
| G-015 | Multi-Agent Orchestration | High | Section 3, 11 | Workflow Engine with parallel/sequential patterns |
| G-016 | Actor Model Implementation | Medium | Section 3 | Workflow Engine design based on Semantic Kernel |
| G-017 | Message Routing Protocol | Medium | Section 4, 6 | Events Published/Consumed (4.3, 4.4) |
| G-018 | Gang Scheduling Support | Medium | Section 10, 14 | Feature flag (10.4), Deferred (14.2) |
| G-019 | Firecracker Integration | Medium | Section 10, 14 | Feature flag (10.4), Deferred (14.2) |
| G-020 | Cross-Thread Memory | Medium | Section 5, 6 | State Manager with Redis vector search |
| G-021 | Confidential Computing (TEE) | Low | Section 14 | Deferred to v1.1 (14.2) |
| G-022 | Bedrock API Compatibility | Low | Section 14 | Deferred to v1.1 (14.2) |
| G-023 | Cost Optimization Policies | Low | Section 14 | Deferred to v1.1 (14.2) |

**Status: 23/23 gaps addressed (100%)**

---

# Appendix B: Error Code Reference

## E2000-E2099: Agent Execution

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| E2001 | TOOL_INVOCATION_FAILED | Error | Tool execution failed |
| E2002 | TOOL_TIMEOUT | Error | Tool exceeded timeout |
| E2003 | CONTEXT_OVERFLOW | Error | Context window exceeded |
| E2004 | STREAMING_ERROR | Error | Stream processing failed |
| E2010 | GRAPH_CYCLE_DETECTED | Error | Infinite loop in workflow |
| E2011 | GRAPH_DEPTH_EXCEEDED | Error | Workflow depth limit |
| E2012 | NODE_EXECUTION_FAILED | Error | Workflow node failure |
| E2013 | BRANCH_TIMEOUT | Error | Parallel branch timeout |
| E2020 | SPAWN_FAILED | Error | Agent spawn failure |
| E2021 | SPAWN_TIMEOUT | Error | Spawn timeout |
| E2022 | TERMINATE_FAILED | Error | Termination failure |
| E2023 | SUSPEND_FAILED | Error | Suspend failure |
| E2024 | RESUME_FAILED | Error | Resume failure |
| E2025 | RESTART_LIMIT_EXCEEDED | Error | Max restarts reached |
| E2030 | CHECKPOINT_FAILED | Error | Checkpoint failure |
| E2031 | CHECKPOINT_TOO_LARGE | Error | Size limit exceeded |
| E2032 | RESTORE_FAILED | Error | Restore failure |
| E2033 | CHECKPOINT_CORRUPTED | Error | Invalid checkpoint |
| E2040 | RUNTIME_CLASS_UNAVAILABLE | Error | Runtime not available |
| E2041 | SANDBOX_CREATION_FAILED | Error | Sandbox setup failure |
| E2042 | SECURITY_POLICY_VIOLATION | Error | Security violation |
| E2050 | SESSION_START_FAILED | Error | Session start failure |
| E2051 | HEARTBEAT_FAILED | Warning | Heartbeat failure |
| E2052 | SNAPSHOT_SAVE_FAILED | Error | Snapshot save failure |
| E2053 | RECOVERY_CHECK_FAILED | Error | Recovery check failure |
| E2054 | SESSION_NOT_FOUND | Error | Session not found |
| E2060 | DOCUMENT_QUERY_FAILED | Error | Document query failure |
| E2061 | NO_AUTHORITATIVE_SOURCE | Warning | No source of truth |
| E2062 | CLAIM_VERIFICATION_FAILED | Warning | Claim unverified |
| E2063 | DOCUMENT_NOT_FOUND | Error | Document not found |
| E2070 | CPU_LIMIT_EXCEEDED | Error | CPU quota exceeded |
| E2071 | MEMORY_LIMIT_EXCEEDED | Error | Memory quota exceeded |
| E2072 | TOKEN_BUDGET_EXCEEDED | Error | Token budget exhausted |
| E2073 | QUOTA_UPDATE_FAILED | Error | Quota update failure |
| E2080 | LIVENESS_CHECK_FAILED | Error | Agent not alive |
| E2081 | READINESS_CHECK_FAILED | Warning | Agent not ready |
| E2082 | AGENT_STUCK | Warning | No progress detected |
| E2083 | METRICS_COLLECTION_FAILED | Warning | Metrics failure |
| E2090 | SCALE_UP_FAILED | Error | Scale up failure |
| E2091 | SCALE_DOWN_FAILED | Error | Scale down failure |
| E2092 | WARM_POOL_EXHAUSTED | Warning | No warm instances |
| E2093 | DRAIN_TIMEOUT | Warning | Drain timeout |
| E2100 | INFERENCE_FAILED | Error | LLM inference failure |
| E2101 | MODEL_UNAVAILABLE | Error | Model not available |
| E2102 | INFERENCE_TIMEOUT | Error | Inference timeout |
| E2103 | RATE_LIMITED | Warning | Rate limit hit |

---

# Appendix C: Phase 15/16 Integration Reference

## Phase 15 (Document Management) Quick Reference

| Operation | Method | Use Case |
|-----------|--------|----------|
| Query documents | `document_bridge.query_source_of_truth()` | Get authoritative answer |
| Verify claim | `document_bridge.verify_claim()` | Validate agent assertion |
| Store artifact | `document_bridge.ingest_document()` | Save agent output |
| Get document | `document_bridge.get_document()` | Retrieve by ID |

## Phase 16 (Session Orchestration) Quick Reference

| Operation | Method | Use Case |
|-----------|--------|----------|
| Start session | `session_bridge.start_session()` | Agent spawn |
| End session | `session_bridge.end_session()` | Agent termination |
| Heartbeat | `session_bridge.heartbeat()` | Keep-alive (30s) |
| Save snapshot | `session_bridge.save_context_snapshot()` | Checkpoint state |
| Load context | `session_bridge.load_context()` | Resume agent |
| Check recovery | `session_bridge.check_recovery()` | Crash detection |
| Create checkpoint | `session_bridge.create_checkpoint()` | Named recovery point |
| Rollback | `session_bridge.rollback_to()` | Restore state |

## Integration Event Flow

```
Agent Spawn:
  L02 -> L01/Phase16: start_session()
  L02 -> L01/Phase1: get_did()
  L02 -> L00: create_pod()
  L02 -> L01/Phase1: emit(agent.spawned)

Agent Execute:
  L02 -> L01/Phase15: query_source_of_truth()
  L02 -> L04: infer()
  L02 -> L01/Phase16: save_context_snapshot()
  L02 -> L01/Phase1: emit(checkpoint.created)

Agent Terminate:
  L02 -> L01/Phase16: end_session()
  L02 -> L00: delete_pod()
  L02 -> L01/Phase1: emit(agent.terminated)
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-14 | Agent Runtime Build Pipeline | Initial complete specification. Merged from Parts 1-3. 23 gaps addressed. |
| 1.1 | 2025-01-14 | Agent Runtime Build Pipeline | Self-validation fixes: Added latency SLO targets (7.1.3), expanded glossary to 36 terms, added TOC quick reference links, expanded Phase 4 Context Injection integration (6.4.2-6.4.5). |
| 1.2 | 2025-01-14 | Agent Runtime Build Pipeline | Industry validation integration: SBOM requirements (13.1), Pod Security Admission (8.2), OCI v1.3 vm.hwConfig (8.3.3), AWS Fargate option (8.3.4), OpenTelemetry alignment (9.1.0), CRIU status notes (11.3), checkpoint sync/async modes (6.7.3), deferred decisions for v1.2 features. |

---

*End of Agent Runtime Layer Specification v1.2 (Final)*
