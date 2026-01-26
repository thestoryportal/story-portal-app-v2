# Service 42/44: TaskOrchestrator

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.task_orchestrator` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L02 AgentExecutor, L03 ToolExecutor, DependencyResolver |
| **Category** | Planning / Execution Orchestration |

## Role in Development Environment

The **TaskOrchestrator** coordinates parallel task execution with state machine management. It provides:
- Task state machine (PENDING → READY → EXECUTING → COMPLETED/FAILED/BLOCKED)
- Parallel task execution with concurrency limits
- Task dispatch to L02 AgentExecutor and L03 ToolExecutor
- Completion monitoring and output propagation
- Retry logic with configurable policies
- Input/output binding between dependent tasks

This is **the execution engine for task plans** - taking a validated plan and running all tasks in the correct order with proper parallelization.

## Data Model

### TaskStatus State Machine
```
PENDING ─────┐
             │ dependencies satisfied
             ▼
READY ───────┐
             │ execution started
             ▼
EXECUTING ───┬──────────────────────┐
             │ success              │ failure
             ▼                      ▼
COMPLETED              ┌──────── FAILED
                       │ retry available
                       ▼
                    PENDING (retry)
                       │ no retry
                       ▼
                    FAILED ────► BLOCKED (dependents)
```

### TaskResult
- `task_id: str` - Task identifier
- `success: bool` - Execution success
- `outputs: Dict` - Task outputs
- `error: str` - Error message (if failed)
- `execution_time_sec: float` - Execution duration

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dependency_resolver` | DependencyResolver() | Dependency resolution |
| `executor_client` | None | L02 AgentExecutor client |
| `tool_executor_client` | None | L03 ToolExecutor client |
| `max_parallel_tasks` | 10 | Maximum concurrent tasks |
| `task_timeout_sec` | 300 | Default task timeout |

## API Methods

| Method | Description |
|--------|-------------|
| `execute_plan(plan, context)` | Execute entire plan |
| `get_stats()` | Get orchestrator statistics |

## Use Cases in Your Workflow

### 1. Initialize Task Orchestrator
```python
from L05_planning.services.task_orchestrator import TaskOrchestrator
from L05_planning.services.dependency_resolver import DependencyResolver
from L02_runtime.services.agent_executor import AgentExecutor
from L03_tool_execution.services.tool_executor import ToolExecutor

# Default initialization
orchestrator = TaskOrchestrator()

# With full cross-layer integration
orchestrator = TaskOrchestrator(
    dependency_resolver=DependencyResolver(),
    executor_client=AgentExecutor(),
    tool_executor_client=ToolExecutor(),
    max_parallel_tasks=5,
    task_timeout_sec=300,
)
```

### 2. Execute Plan
```python
from L05_planning.models import ExecutionPlan

# Create and validate plan
plan = ExecutionPlan.create(goal_id="goal-123")
# ... add tasks ...

# Execute plan
result = await orchestrator.execute_plan(plan)

print(f"Plan status: {result['status']}")
print(f"Completed: {result['completed_tasks']}")
print(f"Failed: {result['failed_tasks']}")
```

### 3. Execute with Context
```python
# Provide execution context
context = {
    "agent_did": "did:agent:developer",
    "tenant_id": "tenant-123",
    "session_id": "session-456",
}

result = await orchestrator.execute_plan(plan, context=context)
```

### 4. Handle Execution Results
```python
try:
    result = await orchestrator.execute_plan(plan)

    if result['status'] == 'completed':
        print("Plan executed successfully!")

        # Access task outputs
        for task_id, outputs in result['outputs'].items():
            print(f"Task {task_id}: {outputs}")

except PlanningError as e:
    if e.code == ErrorCode.E5204:
        print(f"Some tasks failed: {e.details}")
    else:
        print(f"Execution error: {e.message}")
```

### 5. Monitor Task Status
```python
# During execution, task statuses are updated
for task in plan.tasks:
    print(f"{task.name}: {task.status.value}")

    if task.status == TaskStatus.COMPLETED:
        print(f"  Outputs: {task.outputs}")
    elif task.status == TaskStatus.FAILED:
        print(f"  Error: {task.error_message}")
```

### 6. Get Orchestrator Statistics
```python
stats = orchestrator.get_stats()

print(f"Plans executed: {stats['plans_executed']}")
print(f"Tasks executed: {stats['tasks_executed']}")
print(f"Tasks completed: {stats['tasks_completed']}")
print(f"Tasks failed: {stats['tasks_failed']}")
print(f"Tasks retried: {stats['tasks_retried']}")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Failure rate: {stats['failure_rate']:.1%}")
```

### 7. Integration with PlanningService
```python
from L05_planning.services.planning_service import PlanningService

# Create orchestrator
orchestrator = TaskOrchestrator(
    max_parallel_tasks=10
)

# Inject into planning service
service = PlanningService(orchestrator=orchestrator)

# Service uses orchestrator for execution
result = await service.execute_plan_direct(plan)
```

### 8. Handle Task Retries
```python
from L05_planning.models import Task, RetryPolicy

# Create task with retry policy
task = Task.create(
    plan_id=plan.plan_id,
    name="Flaky API call",
    description="Call external API",
    task_type=TaskType.TOOL_CALL,
    tool_name="http_request",
    timeout_seconds=30,
)
task.retry_policy = RetryPolicy(
    max_retries=3,
    initial_delay_sec=1,
    backoff_multiplier=2.0,  # 1s, 2s, 4s
)

# Orchestrator handles retries automatically
result = await orchestrator.execute_plan(plan)
```

### 9. Execute Different Task Types
```python
# Atomic task - dispatched to L02
atomic_task = Task.create(
    name="Process data",
    task_type=TaskType.ATOMIC,
    description="Process input data",
)

# Tool call - dispatched to L03
tool_task = Task.create(
    name="Read file",
    task_type=TaskType.TOOL_CALL,
    tool_name="file_read",
    inputs={"path": "/data/input.txt"},
)

# LLM call - dispatched to L02
llm_task = Task.create(
    name="Analyze text",
    task_type=TaskType.LLM_CALL,
    llm_prompt="Analyze the following text...",
)

# All executed through orchestrator
result = await orchestrator.execute_plan(plan)
```

### 10. Output Propagation
```python
# Task A produces output
task_a = Task.create(
    name="Fetch data",
    task_type=TaskType.TOOL_CALL,
    tool_name="fetch",
)
# Output: {"data": "..."}

# Task B uses Task A's output
task_b = Task.create(
    name="Process data",
    task_type=TaskType.ATOMIC,
    inputs={"source": "{{task_a.data}}"},  # Binding syntax
)
task_b.dependencies.append(
    TaskDependency(
        task_id=task_a.task_id,
        dependency_type=DependencyType.DATA,
        output_key="data",
    )
)

# Orchestrator binds outputs to inputs automatically
result = await orchestrator.execute_plan(plan)
```

## Service Interactions

```
+------------------+
|  TaskOrchestrator| <--- L05 Planning Layer
|       (L05)      |
+--------+---------+
         |
   Dispatches to:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
L02      L03      Depend   Async
Agent    Tool     Resolver Tasks
Executor Executor
(LLM,    (Tools)
Atomic)
```

**Integration Points:**
- **PlanningService (L05)**: Uses for plan execution
- **DependencyResolver (L05)**: Gets ready tasks
- **AgentExecutor (L02)**: Executes LLM and atomic tasks
- **ToolExecutor (L03)**: Executes tool calls
- **ExecutionPlan (L05)**: Plan being executed

## Execution Flow

```
Plan Execution Flow:

1. INITIALIZE
   ├─ Resolve dependencies
   ├─ Build dependency graph
   └─ Mark all tasks PENDING

2. EXECUTION LOOP
   ├─ Get ready tasks (deps satisfied)
   ├─ Mark ready tasks as READY
   ├─ Start executing (up to max_parallel)
   │   ├─ Mark as EXECUTING
   │   ├─ Prepare inputs (bind dep outputs)
   │   └─ Dispatch to L02/L03
   │
   ├─ Wait for first completion
   │
   └─ Process completed tasks
       ├─ Success:
       │   ├─ Mark COMPLETED
       │   ├─ Store outputs
       │   └─ Notify dependents
       │
       └─ Failure:
           ├─ Should retry? → Reset to PENDING
           └─ No retry:
               ├─ Mark FAILED
               └─ Mark dependents BLOCKED

3. COMPLETION
   ├─ All tasks terminal? → Done
   ├─ No progress? → Deadlock
   └─ Continue loop
```

## Task Dispatch

### By Task Type
| Type | Dispatcher | Target |
|------|------------|--------|
| `atomic` | AgentExecutor | L02 |
| `compound` | (Not implemented) | - |
| `tool_call` | ToolExecutor | L03 |
| `llm_call` | AgentExecutor | L02 |

### Mock Mode
When no executor configured:
```python
# Without L02/L03 clients
orchestrator = TaskOrchestrator()

# Tasks execute in mock mode
result = await orchestrator.execute_plan(plan)
# All tasks succeed with mock outputs
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E5200 | General execution error | Maybe |
| E5204 | Task(s) failed | No |

## Execution Examples

```python
# Complete task orchestration workflow
from L05_planning.services.task_orchestrator import TaskOrchestrator
from L05_planning.services.dependency_resolver import DependencyResolver
from L05_planning.models import (
    ExecutionPlan,
    Task,
    TaskType,
    TaskStatus,
    TaskDependency,
    DependencyType,
    RetryPolicy,
    PlanningError,
)
import asyncio

# Initialize orchestrator
orchestrator = TaskOrchestrator(
    max_parallel_tasks=3,
    task_timeout_sec=60,
)

# 1. Create execution plan
plan = ExecutionPlan.create(goal_id="goal-demo")

# Task A: Root task (no dependencies)
task_a = Task.create(
    plan_id=plan.plan_id,
    name="Initialize",
    description="Initialize processing",
    task_type=TaskType.ATOMIC,
    timeout_seconds=30,
)
plan.add_task(task_a)

# Task B: Depends on A
task_b = Task.create(
    plan_id=plan.plan_id,
    name="Fetch data",
    description="Fetch data from source",
    task_type=TaskType.TOOL_CALL,
    tool_name="data_fetch",
    timeout_seconds=60,
)
task_b.dependencies.append(
    TaskDependency(task_id=task_a.task_id, dependency_type=DependencyType.BLOCKING)
)
plan.add_task(task_b)

# Task C: Depends on A (parallel with B)
task_c = Task.create(
    plan_id=plan.plan_id,
    name="Prepare output",
    description="Prepare output directory",
    task_type=TaskType.ATOMIC,
    timeout_seconds=30,
)
task_c.dependencies.append(
    TaskDependency(task_id=task_a.task_id, dependency_type=DependencyType.BLOCKING)
)
plan.add_task(task_c)

# Task D: Depends on B and C (uses B's output)
task_d = Task.create(
    plan_id=plan.plan_id,
    name="Process data",
    description="Process fetched data",
    task_type=TaskType.LLM_CALL,
    llm_prompt="Process the following data...",
    timeout_seconds=120,
)
task_d.dependencies.extend([
    TaskDependency(
        task_id=task_b.task_id,
        dependency_type=DependencyType.DATA,
        output_key="data",
    ),
    TaskDependency(
        task_id=task_c.task_id,
        dependency_type=DependencyType.BLOCKING,
    ),
])
plan.add_task(task_d)

# Task E: Depends on D (with retry)
task_e = Task.create(
    plan_id=plan.plan_id,
    name="Save results",
    description="Save processed results",
    task_type=TaskType.TOOL_CALL,
    tool_name="file_write",
    timeout_seconds=30,
)
task_e.dependencies.append(
    TaskDependency(task_id=task_d.task_id, dependency_type=DependencyType.BLOCKING)
)
task_e.retry_policy = RetryPolicy(max_retries=2, initial_delay_sec=1)
plan.add_task(task_e)

print(f"Created plan with {len(plan.tasks)} tasks")

# 2. Visualize dependency structure
print("\nDependency structure:")
print("  A (Initialize)")
print("  ├── B (Fetch data)")
print("  └── C (Prepare output)")
print("  └── D (Process data) [depends on B,C]")
print("      └── E (Save results)")

# 3. Execute the plan
print("\nExecuting plan...")
try:
    result = await orchestrator.execute_plan(
        plan,
        context={"agent_did": "did:agent:demo"}
    )

    print(f"\nExecution result:")
    print(f"  Status: {result['status']}")
    print(f"  Completed: {result['completed_tasks']}")
    print(f"  Failed: {result['failed_tasks']}")

    # 4. Check task states
    print("\nFinal task states:")
    for task in plan.tasks:
        status = task.status.value
        icon = "✓" if status == "completed" else "✗" if status == "failed" else "○"
        print(f"  {icon} {task.name}: {status}")

    # 5. Access outputs
    print("\nTask outputs:")
    for task_id, outputs in result['outputs'].items():
        task = plan.get_task(task_id)
        print(f"  {task.name}: {outputs}")

except PlanningError as e:
    print(f"\nExecution failed: {e.message}")
    print(f"Details: {e.details}")

# 6. Get statistics
stats = orchestrator.get_stats()
print(f"\nOrchestrator statistics:")
print(f"  Plans executed: {stats['plans_executed']}")
print(f"  Tasks executed: {stats['tasks_executed']}")
print(f"  Tasks completed: {stats['tasks_completed']}")
print(f"  Tasks failed: {stats['tasks_failed']}")
print(f"  Tasks retried: {stats['tasks_retried']}")
print(f"  Success rate: {stats['success_rate']:.1%}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| TaskOrchestrator class | Complete |
| execute_plan() | Complete |
| State machine | Complete |
| Parallel execution | Complete |
| Ready task detection | Complete |
| L02 dispatch | Complete |
| L03 dispatch | Complete |
| Output propagation | Complete |
| Retry logic | Complete |
| Timeout handling | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Compound tasks | High | Execute compound/nested tasks |
| Cancellation | Medium | Cancel running tasks |
| Pause/Resume | Medium | Pause and resume execution |
| Priority scheduling | Low | Prioritize certain tasks |
| Resource limits | Low | Memory/CPU limits per task |
| Event streaming | Low | Real-time execution events |

## Strengths

- **Parallel execution** - Runs independent tasks concurrently
- **State machine** - Clear task lifecycle
- **Cross-layer integration** - L02 and L03 dispatch
- **Retry support** - Automatic retry with backoff
- **Output propagation** - Binds outputs to inputs
- **Deadlock detection** - Identifies stuck execution
- **Mock mode** - Works without L02/L03

## Weaknesses

- **No compound tasks** - Can't execute nested plans
- **No cancellation** - Can't stop running tasks
- **No pause/resume** - Can't interrupt execution
- **Fixed parallelism** - Same limit for all tasks
- **No priority** - FIFO within ready tasks
- **In-memory state** - Lost on restart

## Best Practices

### Configure Parallelism
Set based on resource constraints:
```python
# CPU-bound tasks
TaskOrchestrator(max_parallel_tasks=4)

# I/O-bound tasks
TaskOrchestrator(max_parallel_tasks=20)

# Mixed workload
TaskOrchestrator(max_parallel_tasks=10)
```

### Use Retry Policies
Configure retries for flaky operations:
```python
task.retry_policy = RetryPolicy(
    max_retries=3,
    initial_delay_sec=1,
    backoff_multiplier=2.0,  # Exponential backoff
    max_delay_sec=30,
)
```

### Handle Failures
Plan for task failures:
```python
try:
    result = await orchestrator.execute_plan(plan)
except PlanningError as e:
    if e.code == ErrorCode.E5204:
        # Some tasks failed
        failed_tasks = e.details.get('failed_tasks', 0)
        logger.error(f"{failed_tasks} tasks failed")
        # Consider: retry, alert, cleanup
```

### Timeout Configuration
Set appropriate timeouts:
```python
# Quick tasks
task.timeout_seconds = 30

# API calls
task.timeout_seconds = 60

# LLM generation
task.timeout_seconds = 300

# Long-running processing
task.timeout_seconds = 3600
```

## Source Files

- Service: `platform/src/L05_planning/services/task_orchestrator.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- PlanningService (L05) - Uses for plan execution
- DependencyResolver (L05) - Gets ready tasks
- ExecutionMonitor (L05) - Monitors progress
- AgentExecutor (L02) - Executes LLM/atomic tasks
- ToolExecutor (L03) - Executes tool calls
- ExecutionPlan (L05) - Plan being executed

---
*Generated: 2026-01-24 | Platform Services Documentation*
