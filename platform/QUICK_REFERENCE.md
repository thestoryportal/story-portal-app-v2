# Platform Quick Reference Card

**Fast lookup for core platform services and how to access them**

---

## What You Can Access TODAY (via HTTP)

### L09 API Gateway - `/api/v1/*`
```bash
# Agents
curl http://localhost:8001/api/v1/agents
curl http://localhost:8001/api/v1/agents/{id}

# Goals
curl http://localhost:8001/api/v1/goals
curl http://localhost:8001/api/v1/goals/{id}

# Tasks
curl http://localhost:8001/api/v1/tasks
```

### L10 Dashboard - Port 8003
```bash
# Web Dashboard
open http://localhost:8003/

# API Endpoints
curl http://localhost:8003/api/agents
curl http://localhost:8003/api/goals

# WebSocket Events
wscat -c ws://localhost:8003/ws
```

### L11 Integration - Port 8004
```bash
curl http://localhost:8004/services
curl http://localhost:8004/metrics
curl http://localhost:8004/health/detailed
```

---

## What You CANNOT Access (No Interface)

### Planning & Orchestration 🔴
- ❌ PlanningService - Strategic planning coordinator
- ❌ TaskOrchestrator - Task execution coordination
- ❌ GoalDecomposer - Goal → Task transformation
- ❌ SagaOrchestrator - Multi-step workflows
- ❌ RequestOrchestrator - Cross-layer routing

### Agent Management 🔴
- ❌ LifecycleManager - Spawn/terminate agents
- ❌ FleetManager - Multi-agent coordination
- ❌ AgentExecutor - Execute agent logic
- ❌ StateManager - Agent state persistence
- ❌ ResourceManager - Resource allocation

### Tool Execution 🔴
- ❌ ToolExecutor - Execute tool calls
- ❌ ToolComposer - Multi-tool workflows
- ❌ ToolRegistry - Tool discovery

### Model Gateway 🔴
- ❌ ModelGateway - LLM inference routing
- ❌ LLMRouter - Route to optimal model
- ❌ SemanticCache - Embedding-based caching

### Evaluation & Learning 🔴
- ❌ EvaluationService - Quality evaluation
- ❌ MetricsEngine - Metrics aggregation
- ❌ LearningService - Model training
- ❌ DatasetCurator - Dataset management

**Total:** 60+ core services with NO HTTP interface

---

## Workaround: Python Scripts

Until L12 NL Interface is implemented, use Python:

```python
# Example: Use PlanningService
from L05_planning.services import PlanningService
from L05_planning.models import Goal, GoalConstraints

async def plan_testing_strategy():
    service = PlanningService()
    await service.initialize()

    goal = Goal(
        goal_text="Plan comprehensive testing strategy",
        constraints=GoalConstraints(
            max_parallelism=10,
            max_execution_time_sec=3600
        )
    )

    plan = await service.create_plan(goal)
    print(f"Created plan with {len(plan.tasks)} tasks")

    result = await service.execute_plan(plan)
    print(f"Execution status: {result.status}")

# Run it
import asyncio
asyncio.run(plan_testing_strategy())
```

---

## Future: Natural Language Interface (L12)

**Goal:** Type commands like this in Claude CLI

```bash
# Natural language
"Plan a comprehensive testing strategy for the platform"
"Deploy 5 monitoring agents with high throughput config"
"What's the status of my data pipeline workflow?"

# Slash commands
/plan "Create testing strategy"
/deploy agent type=monitoring count=5
/status workflow_id=abc123
/goals status=active
/agents
```

**Status:** 🔴 Not implemented
**Documentation:**
- Requirements: `FEATURE_GAP_NL_INTERFACE.md`
- Implementation plan: `TODO_NL_INTERFACE.md`
- Full inventory: `PLATFORM_ROLES_INVENTORY.md`

---

## Service Lookup by Layer

| Layer | Key Services | Interface |
|-------|-------------|-----------|
| **L01** Data | AgentRegistry, GoalStore, EventStore | 🟢 Limited CRUD |
| **L02** Runtime | LifecycleManager, FleetManager, AgentExecutor | 🔴 None |
| **L03** Tools | ToolExecutor, ToolComposer, ToolRegistry | 🔴 None |
| **L04** Models | ModelGateway, LLMRouter, SemanticCache | 🔴 None |
| **L05** Planning | PlanningService, TaskOrchestrator, GoalDecomposer | 🔴 None |
| **L06** Evaluation | MetricsEngine, EvaluationService, AlertManager | 🔴 None |
| **L07** Learning | LearningService, FineTuningEngine, DatasetCurator | 🔴 None |
| **L09** Gateway | Authentication, Authorization, RateLimiter | 🟢 Implicit |
| **L10** Dashboard | DashboardService, EventStream | 🟡 Partial |
| **L11** Integration | SagaOrchestrator, RequestOrchestrator | 🟡 Minimal |

---

## Common Tasks & Solutions

### "I want to plan a goal"
**Current:** Write Python script with PlanningService
**Future:** `/plan "your goal description"`

### "I want to deploy agents"
**Current:** Write Python script with LifecycleManager
**Future:** `/deploy agent type=qa count=3`

### "I want to see metrics"
**Current:** Query L01 database directly
**Future:** `/metrics agent_id=abc123`

### "I want to execute a workflow"
**Current:** Write Python script with TaskOrchestrator
**Future:** `/execute plan_id=xyz789`

### "I want to monitor execution"
**Current:** Subscribe to L01 Redis events manually
**Future:** `/status` or WebSocket subscription via `/ws`

---

## Help & Documentation

- **Full Role Inventory:** `PLATFORM_ROLES_INVENTORY.md`
- **Feature Gap Analysis:** `FEATURE_GAP_NL_INTERFACE.md`
- **Implementation TODO:** `TODO_NL_INTERFACE.md`
- **Testing Report:** `TESTING_REPORT.md`
- **QA Findings:** `QA_FINDINGS.md`

---

**Last Updated:** 2026-01-15
**Status:** 🔴 Most platform capabilities not accessible without Python
