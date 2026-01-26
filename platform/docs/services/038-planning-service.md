# Service 38/44: PlanningService

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.planning_service` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L01 Data Layer, L02 Runtime, L03 Tool Execution, L04 Model Gateway |
| **Category** | Planning / Orchestration |

## Role in Development Environment

The **PlanningService** is the main orchestrator for the L05 Planning Layer. It coordinates all planning components to transform high-level goals into executable task plans. It provides:
- Goal decomposition into task plans
- Dependency resolution across tasks
- Plan validation before execution
- Task orchestration during execution
- Execution monitoring and progress tracking
- Cross-layer integration with L02, L03, L04
- Persistent storage via L01 Data Layer

This is **the planning brain of the platform** - when agents need to accomplish complex goals, PlanningService breaks them down into manageable tasks, validates the approach, and orchestrates execution.

## Data Model

### Goal (Input)
- `goal_id: str` - Unique goal identifier
- `goal_text: str` - Natural language goal description
- `agent_did: str` - Agent DID for the goal
- `status: GoalStatus` - Current goal status
- `decomposition_strategy: str` - Strategy (hybrid, llm, template)
- `constraints: Dict` - Goal constraints

### ExecutionPlan (Output)
- `plan_id: str` - Unique plan identifier
- `goal_id: str` - Related goal ID
- `tasks: List[Task]` - List of tasks
- `dependency_graph: Dict` - Task dependencies
- `status: PlanStatus` - Current plan status
- `signature: str` - Plan integrity signature
- `metadata: PlanMetadata` - Execution metadata

### GoalStatus Enum
- `PENDING` - Goal received, not processed
- `DECOMPOSING` - Being decomposed
- `READY` - Plan created, ready to execute
- `EXECUTING` - Currently executing
- `COMPLETED` - Successfully completed
- `FAILED` - Failed during processing

### PlanStatus Enum
- `DRAFT` - Plan created but not validated
- `VALIDATED` - Passed validation
- `EXECUTING` - Currently executing
- `COMPLETED` - Successfully completed
- `FAILED` - Execution failed

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `decomposer` | GoalDecomposer() | Goal decomposition component |
| `resolver` | DependencyResolver() | Dependency resolution component |
| `validator` | PlanValidator() | Plan validation component |
| `orchestrator` | TaskOrchestrator() | Task execution orchestrator |
| `l01_bridge` | L05Bridge() | L01 Data Layer integration |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize service and components |
| `cleanup()` | Cleanup service resources |
| `create_plan(goal)` | Create execution plan from goal |
| `execute_plan_direct(plan, agent_did)` | Execute plan directly |
| `create_and_execute(goal)` | Create plan and execute immediately |
| `get_plan_status(plan_id)` | Get plan status from L01 |
| `list_plans(goal_id, status, limit)` | List plans with filters |
| `cancel_plan(plan_id)` | Cancel running plan |
| `get_stats()` | Get service statistics |
| `get_health_status()` | Get component health status |

## Use Cases in Your Workflow

### 1. Initialize Planning Service
```python
from L05_planning.services.planning_service import PlanningService

# Default initialization
service = PlanningService()
await service.initialize()

# With custom components
from L05_planning.services.goal_decomposer import GoalDecomposer
from L04_model_gateway.services.model_gateway import ModelGateway

gateway = ModelGateway()
decomposer = GoalDecomposer(gateway_client=gateway)

service = PlanningService(
    decomposer=decomposer,
    gateway_client=gateway
)
await service.initialize()
```

### 2. Create Plan from Goal
```python
from L05_planning.models import Goal

# Create goal
goal = Goal.create(
    agent_did="did:agent:abc123",
    goal_text="Create a REST API endpoint for user authentication",
    decomposition_strategy="hybrid"
)

# Create plan
plan = await service.create_plan(goal)

print(f"Plan ID: {plan.plan_id}")
print(f"Tasks: {len(plan.tasks)}")
print(f"Status: {plan.status.value}")
```

### 3. Execute Plan
```python
# Execute plan directly
result = await service.execute_plan_direct(
    plan,
    agent_did="did:agent:abc123"
)

print(f"Execution result: {result}")
```

### 4. Create and Execute in One Call
```python
# Combined operation
result = await service.create_and_execute(goal)

print(f"Goal ID: {result['goal_id']}")
print(f"Plan ID: {result['plan_id']}")
print(f"Result: {result['execution_result']}")
```

### 5. Check Plan Status
```python
# Get plan status from L01
status = await service.get_plan_status(plan.plan_id)

print(f"Status: {status['status']}")
print(f"Tasks: {status['task_count']}")
print(f"Completed: {status['completed_tasks']}")
print(f"Failed: {status['failed_tasks']}")
print(f"Execution time: {status['execution_time_ms']}ms")
```

### 6. List Plans
```python
# List all plans
plans = await service.list_plans(limit=50)

# Filter by goal ID
plans = await service.list_plans(goal_id="goal-123")

# Filter by status
plans = await service.list_plans(status="completed")

for plan in plans:
    print(f"- {plan['plan_id']}: {plan['status']}")
```

### 7. Cancel Plan
```python
# Cancel running plan
success = await service.cancel_plan(plan.plan_id)

if success:
    print("Plan cancelled successfully")
else:
    print("Failed to cancel plan")
```

### 8. Get Service Statistics
```python
stats = service.get_stats()

print(f"Goals received: {stats['service']['goals_received']}")
print(f"Plans created: {stats['service']['plans_created']}")
print(f"Plans executed: {stats['service']['plans_executed']}")
print(f"Execution failures: {stats['service']['execution_failures']}")
print(f"Decomposer cache hits: {stats['decomposer']['cache_hits']}")
print(f"Validator checks: {stats['validator']['validations_total']}")
```

### 9. Get Health Status
```python
health = service.get_health_status()

print(f"Healthy: {health['healthy']}")
print(f"Components: {health['components']}")
print(f"Cross-layer integrations: {health['cross_layer']}")
```

### 10. Full Planning Pipeline
```python
from L05_planning.services.planning_service import PlanningService
from L05_planning.models import Goal

# Initialize service
service = PlanningService()
await service.initialize()

# Create goal
goal = Goal.create(
    agent_did="did:agent:developer",
    goal_text="""
    Build a user authentication system with:
    1. Login endpoint with JWT tokens
    2. Password hashing with bcrypt
    3. Session management with Redis
    4. Rate limiting for failed attempts
    """,
    decomposition_strategy="hybrid"
)

# Create and execute plan
try:
    result = await service.create_and_execute(goal)

    print(f"Plan {result['plan_id']} executed successfully")
    print(f"Result: {result['execution_result']}")

except PlanningError as e:
    print(f"Planning failed: {e.message}")
    print(f"Details: {e.details}")

# Cleanup
await service.cleanup()
```

## Service Interactions

```
+------------------+
|  PlanningService | <--- L05 Planning Layer
|      (L05)       |
+--------+---------+
         |
   Coordinates:
         |
+--------+--------+--------+--------+--------+
|        |        |        |        |        |
v        v        v        v        v        v
Goal     Depend   Plan     Task     Agent    Exec
Decomp   Resolve  Valid    Orch     Assign   Monitor

         |
   Uses Cross-Layer:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
L01      L02      L03      L04
Data     Agent    Tool     Model
Layer    Executor Executor Gateway
```

**Integration Points:**
- **GoalDecomposer (L05)**: Decomposes goals into tasks
- **DependencyResolver (L05)**: Resolves task dependencies
- **PlanValidator (L05)**: Validates plans before execution
- **TaskOrchestrator (L05)**: Orchestrates task execution
- **AgentAssigner (L05)**: Assigns agents to tasks
- **ExecutionMonitor (L05)**: Monitors execution progress
- **L01 Data Layer**: Persists goals and plans
- **L02 AgentExecutor**: Executes agent tasks
- **L03 ToolExecutor**: Executes tool-based tasks
- **L04 ModelGateway**: LLM inference for decomposition

## Planning Pipeline

```
1. Goal Received
   └─> Validate goal input
   └─> Record goal in L01

2. Decomposition (via GoalDecomposer)
   └─> Check cache
   └─> Try template matching
   └─> Fall back to LLM

3. Dependency Resolution
   └─> Build dependency graph
   └─> Detect cycles
   └─> Topological sort

4. Plan Validation
   └─> Check task completeness
   └─> Validate dependencies
   └─> Estimate resources

5. Plan Storage
   └─> Sign plan with HMAC
   └─> Store in L01

6. Execution (via TaskOrchestrator)
   └─> Inject context
   └─> Assign agents
   └─> Execute tasks in order
   └─> Monitor progress

7. Completion
   └─> Update L01 with results
   └─> Return execution result
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E5100 | General planning error | Maybe |
| E5002 | Plan not found | No |
| E5200 | Execution failed | Maybe |
| E5600 | Validation failed | No |

## Execution Examples

```python
# Complete planning service workflow
from L05_planning.services.planning_service import PlanningService
from L05_planning.models import Goal, PlanningError
from L04_model_gateway.services.model_gateway import ModelGateway
from L02_runtime.services.agent_executor import AgentExecutor

# Initialize with all cross-layer integrations
gateway = ModelGateway()
executor = AgentExecutor()

service = PlanningService(
    gateway_client=gateway,
    executor_client=executor,
)
await service.initialize()

# 1. Create a complex goal
goal = Goal.create(
    agent_did="did:agent:developer",
    goal_text="""
    Implement a microservice for order processing:
    1. Create order API endpoint
    2. Integrate with payment gateway
    3. Send confirmation emails
    4. Update inventory
    """,
    decomposition_strategy="hybrid"
)

print(f"Created goal: {goal.goal_id}")

# 2. Create execution plan
try:
    plan = await service.create_plan(goal)

    print(f"\nPlan created: {plan.plan_id}")
    print(f"Tasks: {len(plan.tasks)}")
    for task in plan.tasks:
        print(f"  - {task.name} ({task.task_type.value})")
    print(f"Status: {plan.status.value}")

except PlanningError as e:
    print(f"Plan creation failed: {e.message}")

# 3. Execute the plan
try:
    result = await service.execute_plan_direct(plan)

    print(f"\nExecution result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

except PlanningError as e:
    print(f"Execution failed: {e.message}")
    print(f"Recovery suggestion: {e.recovery_suggestion}")

# 4. Check status
status = await service.get_plan_status(plan.plan_id)
print(f"\nFinal status: {status['status']}")
print(f"Completed tasks: {status['completed_tasks']}/{status['task_count']}")

# 5. Get statistics
stats = service.get_stats()
print(f"\nService stats:")
print(f"  Goals received: {stats['service']['goals_received']}")
print(f"  Plans created: {stats['service']['plans_created']}")
print(f"  Plans executed: {stats['service']['plans_executed']}")
print(f"  Cache hit rate: {stats['cache']['hit_rate']:.1%}")

# 6. Health check
health = service.get_health_status()
print(f"\nHealth: {'✓' if health['healthy'] else '✗'}")
for component, status in health['components'].items():
    print(f"  {component}: {status}")

# 7. Cleanup
await service.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| PlanningService class | Complete |
| initialize() | Complete |
| cleanup() | Complete |
| create_plan() | Complete |
| execute_plan_direct() | Complete |
| create_and_execute() | Complete |
| get_plan_status() | Complete |
| list_plans() | Complete |
| cancel_plan() | Complete |
| get_stats() | Complete |
| get_health_status() | Complete |
| L01 integration | Complete |
| Cross-layer integration | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| execute_plan() by ID | High | Load plan from L01 and execute |
| Plan versioning | Medium | Track plan revisions |
| Parallel execution | Medium | Execute independent tasks in parallel |
| Plan rollback | Medium | Rollback failed plans |
| Event streaming | Low | Real-time execution events |
| Prometheus metrics | Low | Export planning metrics |

## Strengths

- **Full orchestration** - Coordinates all planning components
- **Cross-layer integration** - Works with L01, L02, L03, L04
- **Persistent storage** - Goals and plans stored in L01
- **Comprehensive validation** - Plans validated before execution
- **Execution monitoring** - Tracks task progress
- **Error handling** - Graceful failure with recovery suggestions

## Weaknesses

- **No plan loading by ID** - execute_plan() not implemented
- **Sequential execution** - Tasks not parallelized
- **No rollback** - Failed plans can't be rolled back
- **In-memory orchestration** - State lost on restart
- **No events** - No real-time streaming
- **Single strategy** - Can't change strategy mid-execution

## Best Practices

### Goal Creation
Create goals with clear, actionable descriptions:
```python
Goal.create(
    agent_did="did:agent:xxx",
    goal_text="""
    Clear, specific goal description with:
    1. Numbered steps if appropriate
    2. Success criteria
    3. Any constraints
    """,
    decomposition_strategy="hybrid"  # Usually best
)
```

### Error Handling
Always handle planning errors:
```python
from L05_planning.models import PlanningError, ErrorCode

try:
    result = await service.create_and_execute(goal)
except PlanningError as e:
    if e.code == ErrorCode.E5600:  # Validation failed
        logger.error(f"Invalid plan: {e.details['errors']}")
    elif e.code == ErrorCode.E5200:  # Execution failed
        logger.error(f"Execution error: {e.message}")
        # Consider retry or fallback
```

### Resource Cleanup
Always cleanup on shutdown:
```python
try:
    # Use service
    result = await service.create_and_execute(goal)
finally:
    await service.cleanup()
```

## Source Files

- Service: `platform/src/L05_planning/services/planning_service.py`
- Models: `platform/src/L05_planning/models/`
- Error Codes: `platform/src/L05_planning/models/__init__.py`
- Spec: L05 Planning Layer specification

## Related Services

- GoalDecomposer (L05) - Decomposes goals into tasks
- DependencyResolver (L05) - Resolves task dependencies
- PlanValidator (L05) - Validates plans
- TaskOrchestrator (L05) - Orchestrates execution
- L05Bridge (L05) - L01 Data Layer integration
- ModelGateway (L04) - LLM inference
- AgentExecutor (L02) - Agent task execution
- ToolExecutor (L03) - Tool task execution

---
*Generated: 2026-01-24 | Platform Services Documentation*
