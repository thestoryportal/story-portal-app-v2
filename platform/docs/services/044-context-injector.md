# Service 44/44: ContextInjector

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.context_injector` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L00 Vault (optional for secrets) |
| **Category** | Planning / Context Management |

## Role in Development Environment

The **ContextInjector** prepares execution context for tasks before they run. It provides:
- Input binding resolution from parent task outputs
- Secret reference resolution via vault integration
- Execution scope and permission building
- Access control validation (RBAC)
- Context metadata assembly

This is **the context preparation layer for task execution** - before any task runs, ContextInjector ensures it has all required inputs, secrets, and permissions.

## Data Model

### ExecutionContext (Output)
- `task_id: str` - Task being executed
- `plan_id: str` - Parent plan ID
- `agent_did: str` - Agent DID for execution
- `scope: ContextScope` - Execution scope level
- `timeout_seconds: int` - Execution timeout
- `inputs: Dict` - Resolved input values
- `secrets: Dict` - Resolved secret references
- `permissions: List[str]` - Execution permissions

### ContextScope Enum
- `TASK` - Task-level scope (default)
- `PLAN` - Plan-level scope
- `AGENT` - Agent-level scope

### Input Binding Reference Format
```
{{task_id.output_key}}

Example:
{{task-123.api_result}}
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `vault_client` | None | L00 Vault client for secrets |
| `enable_secrets` | True | Enable secret resolution |

## API Methods

| Method | Description |
|--------|-------------|
| `inject_context(task, plan, parent_outputs, agent_did)` | Create execution context |
| `get_stats()` | Get injector statistics |

## Use Cases in Your Workflow

### 1. Initialize Context Injector
```python
from L05_planning.services.context_injector import ContextInjector

# Default initialization (no vault)
injector = ContextInjector()

# With vault integration
from L00_vault.client import VaultClient

vault = VaultClient()
injector = ContextInjector(
    vault_client=vault,
    enable_secrets=True
)

# Without secret resolution
injector = ContextInjector(enable_secrets=False)
```

### 2. Inject Context for Task
```python
from L05_planning.models import Task, ExecutionPlan

# Create task and plan
plan = ExecutionPlan.create(goal_id="goal-123")
task = Task.create(
    plan_id=plan.plan_id,
    name="Process data",
    description="Process API response",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)

# Inject context
context = await injector.inject_context(
    task=task,
    plan=plan,
    parent_outputs=None,
    agent_did="did:agent:abc123"
)

print(f"Context for task: {context.task_id}")
print(f"Scope: {context.scope}")
print(f"Permissions: {context.permissions}")
```

### 3. Resolve Input Bindings
```python
# Parent task outputs
parent_outputs = {
    "task-1": {"result": "success", "data": [1, 2, 3]},
    "task-2": {"api_response": {"status": 200}}
}

# Task with dependencies
task = Task.create(
    plan_id=plan.plan_id,
    name="Aggregate results",
    description="Combine outputs",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)

# Add data dependency
task.dependencies.append(
    TaskDependency(
        task_id="task-1",
        dependency_type="data",
        output_key="data"
    )
)

# Inject context with resolved inputs
context = await injector.inject_context(
    task=task,
    plan=plan,
    parent_outputs=parent_outputs,
)

print(f"Resolved inputs: {context.inputs}")
# {'data': [1, 2, 3]}
```

### 4. Use Template References
```python
# Task with input references
task = Task.create(
    plan_id=plan.plan_id,
    name="Transform data",
    description="Transform API response",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
    inputs={
        "source_data": "{{task-1.result}}",
        "api_status": "{{task-2.api_response.status}}"
    }
)

# Inject context
context = await injector.inject_context(
    task=task,
    plan=plan,
    parent_outputs=parent_outputs,
)

print(f"Resolved inputs: {context.inputs}")
# {'source_data': 'success', 'api_status': 200}
```

### 5. Resolve Secrets
```python
# Task with secret references
task = Task.create(
    plan_id=plan.plan_id,
    name="Call external API",
    description="Fetch data from external service",
    task_type=TaskType.TOOL_CALL,
    timeout_seconds=120,
    metadata={
        "secrets": {
            "api_key": "external-api/api-key",
            "auth_token": "external-api/auth-token"
        }
    }
)

# Inject context
context = await injector.inject_context(
    task=task,
    plan=plan,
)

# Secrets added as vault references (not actual values)
print(f"Secrets: {context.secrets}")
# {'api_key': 'vault://external-api/api-key', 'auth_token': 'vault://...'}
```

### 6. Handle Task-Specific Permissions
```python
# Task with custom permissions
task = Task.create(
    plan_id=plan.plan_id,
    name="File operations",
    description="Read and write files",
    task_type=TaskType.TOOL_CALL,
    timeout_seconds=60,
    metadata={
        "permissions": ["file.read", "file.write", "file.delete"]
    }
)

# Inject context
context = await injector.inject_context(task=task, plan=plan)

print(f"Permissions: {context.permissions}")
# ['tool.execute', 'read', 'write', 'file.read', 'file.write', 'file.delete']
```

### 7. Get Injector Statistics
```python
stats = injector.get_stats()

print(f"Contexts created: {stats['contexts_created']}")
print(f"Secrets resolved: {stats['secrets_resolved']}")
print(f"Input bindings resolved: {stats['input_bindings_resolved']}")
print(f"Access denied: {stats['access_denied_count']}")
```

### 8. Integration with TaskOrchestrator
```python
from L05_planning.services.task_orchestrator import TaskOrchestrator
from L05_planning.services.context_injector import ContextInjector

# Create injector
injector = ContextInjector(vault_client=vault)

# Inject into orchestrator
orchestrator = TaskOrchestrator(
    context_injector=injector
)

# Orchestrator uses injector before each task execution
result = await orchestrator.execute_plan(plan, agent_did)
```

### 9. Handle Missing Dependencies
```python
# Task with missing dependency output
task = Task.create(
    plan_id=plan.plan_id,
    name="Process missing data",
    description="Requires unavailable input",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)

task.dependencies.append(
    TaskDependency(
        task_id="task-999",  # Non-existent
        dependency_type="data",
        output_key="result"
    )
)

try:
    context = await injector.inject_context(
        task=task,
        plan=plan,
        parent_outputs={},  # No outputs available
    )
except PlanningError as e:
    print(f"Error: {e.message}")
    # Missing required input from dependency
```

### 10. Scope-Based Permissions
```python
# Different task types get different default permissions

# LLM call task
llm_task = Task.create(
    plan_id=plan.plan_id,
    name="Generate text",
    task_type=TaskType.LLM_CALL,
)

context_llm = await injector.inject_context(task=llm_task, plan=plan)
print(f"LLM permissions: {context_llm.permissions}")
# ['llm.inference', 'read']

# Tool call task
tool_task = Task.create(
    plan_id=plan.plan_id,
    name="Execute tool",
    task_type=TaskType.TOOL_CALL,
)

context_tool = await injector.inject_context(task=tool_task, plan=plan)
print(f"Tool permissions: {context_tool.permissions}")
# ['tool.execute', 'read', 'write']

# Atomic task
atomic_task = Task.create(
    plan_id=plan.plan_id,
    name="Simple task",
    task_type=TaskType.ATOMIC,
)

context_atomic = await injector.inject_context(task=atomic_task, plan=plan)
print(f"Atomic permissions: {context_atomic.permissions}")
# ['read']
```

## Service Interactions

```
+-------------------+
|  ContextInjector  | <--- L05 Planning Layer
|       (L05)       |
+--------+----------+
         |
   Provides:
         |
+--------+--------+--------+--------+
|        |        |        |        |
v        v        v        v        v
Input    Secret   Scope    Access   Context
Resolve  Resolve  Build    Valid    Create
```

**Integration Points:**
- **TaskOrchestrator (L05)**: Creates context before execution
- **L00 Vault**: Secret resolution
- **ExecutionContext (L05)**: Output model
- **Task (L05)**: Input source

## Context Injection Pipeline

```
inject_context(task, plan, parent_outputs)
                     │
        ┌────────────▼────────────┐
        │  Create Base Context    │
        │  - task_id, plan_id     │
        │  - agent_did, timeout   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Resolve Input Bindings │
        │  - Static inputs        │
        │  - Data dependencies    │
        │  - Template references  │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Resolve Secrets        │
        │  - Vault lookups        │
        │  - Masked references    │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Build Scope            │
        │  - Execution scope      │
        │  - Default permissions  │
        │  - Task permissions     │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Validate Access        │
        │  - RBAC check           │
        │  - Permission verify    │
        └────────────┬────────────┘
                     │
                     ▼
              ExecutionContext
```

## Input Binding Resolution

### Data Dependency Binding
```python
# Dependency specifies output_key
task.dependencies.append(
    TaskDependency(
        task_id="parent-task",
        dependency_type="data",
        output_key="result"  # Specific key
    )
)
# Resolved: inputs["result"] = parent_outputs["parent-task"]["result"]

# Dependency without output_key (all outputs)
task.dependencies.append(
    TaskDependency(
        task_id="parent-task",
        dependency_type="data",
        output_key=None  # All outputs
    )
)
# Resolved: inputs.update(parent_outputs["parent-task"])
```

### Template Reference Binding
```python
# Reference format: {{task_id.output_key}}
task.inputs = {
    "value": "{{task-1.result}}",
    "count": "{{task-2.item_count}}"
}
# Resolved from parent_outputs
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E5400 | General context error | Maybe |
| E5401 | Secret resolution failed | Yes |
| E5402 | Missing input binding | No |
| E5404 | Access denied | No |

## Execution Examples

```python
# Complete context injection workflow
from L05_planning.services.context_injector import ContextInjector
from L05_planning.models import (
    Task,
    TaskType,
    ExecutionPlan,
    TaskDependency,
    PlanningError,
)

# Initialize injector
injector = ContextInjector(enable_secrets=True)

# 1. Create plan
plan = ExecutionPlan.create(goal_id="goal-workflow")
print(f"Plan: {plan.plan_id}")

# 2. Create tasks with dependencies
task_fetch = Task.create(
    plan_id=plan.plan_id,
    name="Fetch data",
    description="Fetch data from API",
    task_type=TaskType.TOOL_CALL,
    timeout_seconds=30,
)
plan.add_task(task_fetch)

task_process = Task.create(
    plan_id=plan.plan_id,
    name="Process data",
    description="Transform fetched data",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
    inputs={
        "source": "{{" + task_fetch.task_id + ".response}}"
    }
)
task_process.dependencies.append(
    TaskDependency(
        task_id=task_fetch.task_id,
        dependency_type="data",
        output_key="response"
    )
)
plan.add_task(task_process)

task_store = Task.create(
    plan_id=plan.plan_id,
    name="Store results",
    description="Save processed data",
    task_type=TaskType.TOOL_CALL,
    timeout_seconds=30,
    metadata={
        "secrets": {"db_password": "database/password"},
        "permissions": ["database.write"]
    }
)
task_store.dependencies.append(
    TaskDependency(
        task_id=task_process.task_id,
        dependency_type="data",
    )
)
plan.add_task(task_store)

print(f"Created {len(plan.tasks)} tasks")

# 3. Inject context for each task
parent_outputs = {}

# Task 1: Fetch (no dependencies)
context1 = await injector.inject_context(
    task=task_fetch,
    plan=plan,
    parent_outputs=parent_outputs,
    agent_did="did:agent:workflow"
)
print(f"\nContext for '{task_fetch.name}':")
print(f"  Permissions: {context1.permissions}")
print(f"  Inputs: {context1.inputs}")

# Simulate task completion
parent_outputs[task_fetch.task_id] = {
    "response": {"status": 200, "data": [1, 2, 3]}
}

# Task 2: Process (depends on fetch)
context2 = await injector.inject_context(
    task=task_process,
    plan=plan,
    parent_outputs=parent_outputs,
    agent_did="did:agent:workflow"
)
print(f"\nContext for '{task_process.name}':")
print(f"  Permissions: {context2.permissions}")
print(f"  Inputs: {context2.inputs}")

# Simulate task completion
parent_outputs[task_process.task_id] = {
    "processed_data": [2, 4, 6],
    "count": 3
}

# Task 3: Store (depends on process)
context3 = await injector.inject_context(
    task=task_store,
    plan=plan,
    parent_outputs=parent_outputs,
    agent_did="did:agent:workflow"
)
print(f"\nContext for '{task_store.name}':")
print(f"  Permissions: {context3.permissions}")
print(f"  Inputs: {context3.inputs}")
print(f"  Secrets: {context3.secrets}")

# 4. Get statistics
stats = injector.get_stats()
print(f"\nInjector stats:")
print(f"  Contexts created: {stats['contexts_created']}")
print(f"  Input bindings resolved: {stats['input_bindings_resolved']}")
print(f"  Secrets resolved: {stats['secrets_resolved']}")
print(f"  Access denied: {stats['access_denied_count']}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| ContextInjector class | Complete |
| inject_context() | Complete |
| Input binding resolution | Complete |
| Template reference parsing | Complete |
| Secret resolution | Complete |
| Scope building | Complete |
| Permission assignment | Complete |
| Access validation | Stub (always allows) |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| RBAC validation | High | Implement actual access control |
| Vault integration | High | Full L00 Vault integration |
| Nested references | Medium | Support {{a.b.c}} deep paths |
| Context caching | Low | Cache repeated contexts |
| Audit logging | Low | Log context creation events |
| Scope inheritance | Low | Inherit from parent contexts |

## Strengths

- **Flexible input binding** - Multiple resolution methods
- **Template references** - Dynamic input specification
- **Secret masking** - Never exposes actual secrets
- **Scope-based permissions** - Different defaults per task type
- **Error handling** - Clear error codes for failures
- **Extensible** - Easy to add resolution strategies

## Weaknesses

- **No RBAC** - Access validation is stub only
- **Mock vault** - No actual vault integration
- **Flat references** - No nested path support
- **No caching** - Recomputes each time
- **Synchronous validation** - Blocks on checks
- **No audit trail** - Doesn't log creations

## Best Practices

### Input Specification
Prefer explicit dependencies over template references:
```python
# Good: Explicit dependency
task.dependencies.append(
    TaskDependency(task_id="parent", dependency_type="data")
)

# Avoid: Template references for critical data
task.inputs = {"data": "{{parent.result}}"}  # Harder to trace
```

### Secret Management
Use metadata for secret references:
```python
task.metadata = {
    "secrets": {
        "api_key": "path/to/secret",  # Vault path
    }
}
```

### Permission Scoping
Add only necessary permissions:
```python
task.metadata = {
    "permissions": ["file.read"]  # Minimal
}
# Don't add permissions you don't need
```

### Error Handling
Handle missing bindings gracefully:
```python
try:
    context = await injector.inject_context(task, plan, outputs)
except PlanningError as e:
    if e.code == ErrorCode.E5402:
        logger.error(f"Missing input: {e.details}")
        # Handle missing dependency
```

## Source Files

- Service: `platform/src/L05_planning/services/context_injector.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- TaskOrchestrator (L05) - Primary context user
- PlanningService (L05) - Orchestrates execution
- L00 Vault - Secret storage
- ExecutionPlan (L05) - Contains task dependencies
- Task (L05) - Context source

---
*Generated: 2026-01-24 | Platform Services Documentation*
