# Service 41/44: PlanValidator

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.plan_validator` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | ResourceEstimator, DependencyResolver |
| **Category** | Planning / Validation |

## Role in Development Environment

The **PlanValidator** performs multi-level validation of execution plans before they run. It provides:
- Syntax validation (format, types, required fields)
- Semantic validation (executability, input availability)
- Feasibility validation (resource availability, budget compliance)
- Security validation (authorization, constraint compliance)
- Warning collection for non-critical issues

This is **the quality gate for execution plans** - ensuring plans are complete, correct, and feasible before execution.

## Data Model

### ValidationResult
- `valid: bool` - Overall validation result
- `errors: List[ValidationError]` - List of validation errors
- `warnings: List[str]` - Non-critical warnings

### ValidationError
- `level: str` - Validation level (syntax, semantic, feasibility, security)
- `code: str` - Error code
- `message: str` - Error message
- `task_id: str` - Related task ID (optional)
- `details: Dict` - Additional details

### Validation Levels
1. **Syntax** - Format, types, required fields
2. **Semantic** - Task executability, dependencies
3. **Feasibility** - Resources, budget, time
4. **Security** - Authorization, constraints

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `resource_estimator` | ResourceEstimator() | Resource estimation component |
| `dependency_resolver` | DependencyResolver() | Dependency validation component |

## API Methods

| Method | Description |
|--------|-------------|
| `validate(plan)` | Perform complete plan validation |
| `get_stats()` | Get validator statistics |

## Use Cases in Your Workflow

### 1. Initialize Plan Validator
```python
from L05_planning.services.plan_validator import PlanValidator
from L05_planning.services.resource_estimator import ResourceEstimator
from L05_planning.services.dependency_resolver import DependencyResolver

# Default initialization
validator = PlanValidator()

# With custom components
validator = PlanValidator(
    resource_estimator=ResourceEstimator(),
    dependency_resolver=DependencyResolver()
)
```

### 2. Validate Execution Plan
```python
from L05_planning.models import ExecutionPlan

# Create plan
plan = ExecutionPlan.create(goal_id="goal-123")
# ... add tasks ...

# Validate plan
result = await validator.validate(plan)

if result.valid:
    print("Plan is valid!")
else:
    print(f"Validation failed with {len(result.errors)} errors")
    for error in result.errors:
        print(f"  [{error.level}] {error.code}: {error.message}")
```

### 3. Check Validation Errors
```python
result = await validator.validate(plan)

# Group errors by level
syntax_errors = [e for e in result.errors if e.level == "syntax"]
semantic_errors = [e for e in result.errors if e.level == "semantic"]
feasibility_errors = [e for e in result.errors if e.level == "feasibility"]
security_errors = [e for e in result.errors if e.level == "security"]

print(f"Syntax errors: {len(syntax_errors)}")
print(f"Semantic errors: {len(semantic_errors)}")
print(f"Feasibility errors: {len(feasibility_errors)}")
print(f"Security errors: {len(security_errors)}")
```

### 4. Check Validation Warnings
```python
result = await validator.validate(plan)

if result.warnings:
    print(f"{len(result.warnings)} warnings:")
    for warning in result.warnings:
        print(f"  ⚠ {warning}")
```

### 5. Handle Task-Specific Errors
```python
result = await validator.validate(plan)

# Find errors for specific task
task_id = "task-123"
task_errors = [e for e in result.errors if e.task_id == task_id]

if task_errors:
    print(f"Task {task_id} has {len(task_errors)} errors:")
    for error in task_errors:
        print(f"  - {error.message}")
```

### 6. Get Validator Statistics
```python
stats = validator.get_stats()

print(f"Plans validated: {stats['plans_validated']}")
print(f"Validation failures: {stats['validation_failures']}")
print(f"Failure rate: {stats['failure_rate']:.1%}")
```

### 7. Integration with PlanningService
```python
from L05_planning.services.planning_service import PlanningService

# Create validator
validator = PlanValidator()

# Inject into planning service
service = PlanningService(validator=validator)

# Service uses validator during create_plan()
plan = await service.create_plan(goal)
# Validation happens automatically
```

### 8. Validate Before Execution
```python
# Always validate before executing
result = await validator.validate(plan)

if not result.valid:
    # Log errors and abort
    for error in result.errors:
        logger.error(f"Validation error: {error.message}")
    raise ValueError("Plan validation failed")

# Safe to execute
result = await orchestrator.execute_plan(plan)
```

### 9. Custom Validation Response
```python
result = await validator.validate(plan)

if not result.valid:
    # Build user-friendly error response
    error_summary = {
        "valid": False,
        "error_count": len(result.errors),
        "errors_by_level": {},
        "affected_tasks": set(),
    }

    for error in result.errors:
        level = error.level
        if level not in error_summary["errors_by_level"]:
            error_summary["errors_by_level"][level] = []
        error_summary["errors_by_level"][level].append(error.message)

        if error.task_id:
            error_summary["affected_tasks"].add(error.task_id)

    return error_summary
```

### 10. Conditional Validation
```python
# Full validation for production
if environment == "production":
    result = await validator.validate(plan)
    if not result.valid:
        raise ValidationError(result.errors)

# Lenient validation for development
elif environment == "development":
    result = await validator.validate(plan)
    # Allow execution with warnings only
    if any(e.level == "security" for e in result.errors):
        raise SecurityError("Security validation failed")
```

## Service Interactions

```
+------------------+
|   PlanValidator  | <--- L05 Planning Layer
|      (L05)       |
+--------+---------+
         |
   Uses:
         |
+--------+--------+
|                 |
v                 v
Resource       Dependency
Estimator      Resolver
(Feasibility)  (Semantic)
```

**Integration Points:**
- **PlanningService (L05)**: Validates plans during creation
- **ResourceEstimator (L05)**: Feasibility validation
- **DependencyResolver (L05)**: Semantic validation
- **ExecutionPlan (L05)**: Validated data model

## Validation Pipeline

```
Plan Validation Pipeline:

1. SYNTAX VALIDATION
   ├─ Check plan has tasks
   ├─ Check task_id exists
   ├─ Check task name exists
   ├─ Check task description exists
   ├─ Check task type valid
   └─ Check timeout > 0

   If syntax fails → Return early (can't proceed)

2. SEMANTIC VALIDATION
   ├─ Check for circular dependencies
   ├─ Check all dependencies exist
   ├─ Check tool tasks have tool_name
   └─ Check LLM tasks have llm_prompt

3. FEASIBILITY VALIDATION
   ├─ Estimate resources
   └─ Check against budget (if set)
       ├─ Execution time
       ├─ Token count
       └─ Cost

4. SECURITY VALIDATION
   └─ Check task count < 100

5. COLLECT WARNINGS
   ├─ Long execution time (> 1 hour)
   ├─ High cost (> $1.00)
   ├─ High token usage (> 100K)
   └─ Many independent tasks (> 10)

6. RETURN RESULT
   valid = len(errors) == 0
```

## Error Codes

| Code | Description | Level |
|------|-------------|-------|
| E5301 | Circular dependencies | semantic |
| E5302 | Missing dependency | semantic |
| E5500 | Resource estimation failed | feasibility |
| E5504 | Invalid timeout | syntax |
| E5603 | Budget exceeded | feasibility |
| E5604 | Excessive task count | security |
| E5605 | Invalid task type | syntax |
| E5606 | Missing required field | syntax |

## Execution Examples

```python
# Complete plan validation workflow
from L05_planning.services.plan_validator import PlanValidator
from L05_planning.services.resource_estimator import ResourceEstimator
from L05_planning.models import (
    ExecutionPlan,
    Task,
    TaskType,
    TaskDependency,
    DependencyType,
    ResourceBudget,
)

# Initialize
validator = PlanValidator()

# 1. Create a plan with various issues for testing
plan = ExecutionPlan.create(goal_id="goal-test")

# Valid task
task1 = Task.create(
    plan_id=plan.plan_id,
    name="Setup environment",
    description="Initialize project environment",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
plan.add_task(task1)

# Task missing description (syntax error)
task2 = Task.create(
    plan_id=plan.plan_id,
    name="Missing description task",
    description="",  # Empty description
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
plan.add_task(task2)

# Tool call without tool_name (semantic error)
task3 = Task.create(
    plan_id=plan.plan_id,
    name="Tool call task",
    description="Calls a tool",
    task_type=TaskType.TOOL_CALL,
    timeout_seconds=60,
    # tool_name not set!
)
plan.add_task(task3)

# Task with dependency on non-existent task (semantic error)
task4 = Task.create(
    plan_id=plan.plan_id,
    name="Bad dependency",
    description="Has invalid dependency",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
task4.dependencies.append(
    TaskDependency(task_id="non-existent-task", dependency_type=DependencyType.BLOCKING)
)
plan.add_task(task4)

print(f"Created plan with {len(plan.tasks)} tasks")

# 2. Validate the plan
result = await validator.validate(plan)

print(f"\nValidation result: {'PASS' if result.valid else 'FAIL'}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# 3. Analyze errors by level
levels = {}
for error in result.errors:
    if error.level not in levels:
        levels[error.level] = []
    levels[error.level].append(error)

print("\nErrors by level:")
for level, errors in levels.items():
    print(f"\n  {level.upper()}:")
    for error in errors:
        task_info = f" (task: {error.task_id})" if error.task_id else ""
        print(f"    [{error.code}] {error.message}{task_info}")

# 4. Show warnings
if result.warnings:
    print("\nWarnings:")
    for warning in result.warnings:
        print(f"  ⚠ {warning}")

# 5. Create a valid plan
valid_plan = ExecutionPlan.create(goal_id="goal-valid")

valid_task1 = Task.create(
    plan_id=valid_plan.plan_id,
    name="Step 1",
    description="First step",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
valid_plan.add_task(valid_task1)

valid_task2 = Task.create(
    plan_id=valid_plan.plan_id,
    name="Step 2",
    description="Second step",
    task_type=TaskType.ATOMIC,
    timeout_seconds=60,
)
valid_task2.dependencies.append(
    TaskDependency(task_id=valid_task1.task_id, dependency_type=DependencyType.BLOCKING)
)
valid_plan.add_task(valid_task2)

# 6. Validate the valid plan
valid_result = await validator.validate(valid_plan)

print(f"\nValid plan result: {'PASS' if valid_result.valid else 'FAIL'}")
print(f"Errors: {len(valid_result.errors)}")

# 7. Test with budget constraints
budget_plan = ExecutionPlan.create(goal_id="goal-budget")
budget_plan.resource_budget = ResourceBudget(
    max_tokens=1000,      # Low limit
    max_cost_usd=0.01,    # Low budget
    max_time_sec=10,      # Short time
)

# Add task that might exceed budget
expensive_task = Task.create(
    plan_id=budget_plan.plan_id,
    name="Expensive task",
    description="High resource task",
    task_type=TaskType.LLM_CALL,
    timeout_seconds=300,  # Long timeout
    llm_prompt="Generate a detailed report",
)
budget_plan.add_task(expensive_task)

budget_result = await validator.validate(budget_plan)
print(f"\nBudget plan result: {'PASS' if budget_result.valid else 'FAIL'}")

feasibility_errors = [e for e in budget_result.errors if e.level == "feasibility"]
print(f"Feasibility errors: {len(feasibility_errors)}")
for error in feasibility_errors:
    print(f"  - {error.message}")

# 8. Get statistics
stats = validator.get_stats()
print(f"\nValidator statistics:")
print(f"  Plans validated: {stats['plans_validated']}")
print(f"  Failures: {stats['validation_failures']}")
print(f"  Failure rate: {stats['failure_rate']:.1%}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| PlanValidator class | Complete |
| validate() | Complete |
| Syntax validation | Complete |
| Semantic validation | Complete |
| Feasibility validation | Complete |
| Security validation | Complete |
| Warning collection | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Tool availability check | High | Verify tools exist in L03 |
| Agent capability check | Medium | Verify agents can execute tasks |
| Custom validation rules | Medium | User-defined validation rules |
| Validation caching | Low | Cache validation results |
| Async validation hooks | Low | External validation services |

## Strengths

- **Multi-level validation** - Comprehensive coverage
- **Early failure** - Stops at syntax errors
- **Task-level errors** - Identifies problem tasks
- **Warning collection** - Non-blocking feedback
- **Resource awareness** - Budget validation
- **Clean separation** - Validation levels independent

## Weaknesses

- **No tool availability** - Doesn't check if tools exist
- **Basic security** - Only task count limit
- **No agent validation** - Doesn't verify agent capabilities
- **Synchronous feasibility** - Blocking resource estimation
- **Fixed thresholds** - Hardcoded warning limits
- **No custom rules** - Can't add validation rules

## Best Practices

### Handle All Validation Levels
```python
result = await validator.validate(plan)

if not result.valid:
    # Categorize errors for appropriate handling
    syntax_errors = [e for e in result.errors if e.level == "syntax"]
    semantic_errors = [e for e in result.errors if e.level == "semantic"]

    if syntax_errors:
        # Plan structure is broken - needs regeneration
        raise InvalidPlanError("Plan has structural errors")

    if semantic_errors:
        # Plan logic is wrong - may be fixable
        fix_semantic_issues(plan, semantic_errors)
```

### Validate Before Storage
```python
# Always validate before persisting
result = await validator.validate(plan)
if not result.valid:
    raise ValidationError(result.errors)

# Safe to store
await l01_bridge.record_plan(plan)
```

### Log Warnings
```python
result = await validator.validate(plan)

# Log warnings even if valid
for warning in result.warnings:
    logger.warning(f"Plan validation warning: {warning}")

if not result.valid:
    for error in result.errors:
        logger.error(f"Validation error: {error.message}")
```

## Source Files

- Service: `platform/src/L05_planning/services/plan_validator.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- PlanningService (L05) - Uses validator during creation
- ResourceEstimator (L05) - Feasibility validation
- DependencyResolver (L05) - Semantic validation
- GoalDecomposer (L05) - Creates plans to validate
- TaskOrchestrator (L05) - Executes validated plans

---
*Generated: 2026-01-24 | Platform Services Documentation*
