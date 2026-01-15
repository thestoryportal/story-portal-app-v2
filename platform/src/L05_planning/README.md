# L05 Planning Layer

Autonomous goal decomposition and task orchestration layer for the agentic platform.

## Overview

The Planning Layer (L05) transforms high-level goals into executable task plans with dependency resolution, resource estimation, and execution context injection. It provides intelligent task scheduling with parallel execution, retry logic, and comprehensive monitoring.

## Architecture

### Core Components

1. **GoalDecomposer** - Decomposes goals into task plans
   - Hybrid strategy: Cache → Template → LLM
   - L04 Model Gateway integration for LLM-based decomposition
   - HMAC-SHA256 plan signing for integrity

2. **DependencyResolver** - Analyzes task dependency graphs
   - Cycle detection using DFS (O(V+E))
   - Topological sort for execution ordering
   - Critical path computation
   - Execution wave planning for parallelization

3. **PlanValidator** - Multi-level plan validation
   - Syntax validation (format, types, fields)
   - Semantic validation (executability, references)
   - Feasibility validation (resources, budget)
   - Security validation (authorization, constraints)

4. **TaskOrchestrator** - Manages task execution
   - State machine: PENDING → READY → EXECUTING → COMPLETED/FAILED/BLOCKED
   - Parallel execution with configurable concurrency
   - Automatic retry with exponential backoff
   - Output propagation between dependent tasks

5. **ContextInjector** - Prepares execution contexts
   - Input binding from parent task outputs
   - Secret resolution (vault integration)
   - Permission and scope management
   - Access control validation

6. **ResourceEstimator** - Estimates resource requirements
   - Task-type-specific estimates (LLM, tool, atomic, compound)
   - Token estimation for LLM tasks
   - Cost estimation with configurable pricing
   - Budget compliance checking

7. **AgentAssigner** - Assigns tasks to agents
   - Capability-based matching
   - Load balancing (least_loaded, round_robin)
   - Task affinity for efficiency
   - L02 Agent Registry integration

8. **ExecutionMonitor** - Monitors execution progress
   - Task completion tracking
   - Timeout and failure detection
   - Event emission to L01 Event Store
   - Escalation for critical failures

9. **PlanCache** - Two-level plan caching
   - L1: In-memory LRU cache (hot plans)
   - L2: Redis cache (warm plans)
   - Cache key derivation from normalized goal text

10. **PlanningService** - Main orchestrator
    - Coordinates all L05 components
    - End-to-end goal → execution pipeline
    - Comprehensive statistics aggregation

### Template System

**TemplateRegistry** - Predefined decomposition patterns
- Pattern matching using regex
- Parameter extraction and substitution
- Common templates: file processing, data pipeline, reporting, query

## Usage

### Basic Usage

```python
from src.L05_planning.services import PlanningService
from src.L05_planning.models import Goal, GoalConstraints

# Initialize service
service = PlanningService()
await service.initialize()

# Create goal
goal = Goal.create(
    agent_did="did:agent:test",
    goal_text="Create a summary of the project status",
    constraints=GoalConstraints(max_token_budget=10000)
)

# Create and execute plan
result = await service.create_and_execute(goal)

print(f"Execution result: {result}")

# Get statistics
stats = service.get_stats()
print(f"Statistics: {stats}")

await service.cleanup()
```

### Advanced Usage

```python
# Create plan only
plan = await service.create_plan(goal)

# Inspect plan
print(f"Plan ID: {plan.plan_id}")
print(f"Tasks: {len(plan.tasks)}")
for task in plan.tasks:
    print(f"  - {task.name}: {task.description}")

# Execute plan
result = await service.execute_plan_direct(plan)
```

## Error Codes

L05 uses error codes E5000-E5999:

| Range | Category |
|-------|----------|
| E5000-E5099 | Plan cache and retrieval |
| E5100-E5199 | Goal decomposition |
| E5200-E5299 | Task orchestration |
| E5300-E5399 | Dependency resolution |
| E5400-E5499 | Context management |
| E5500-E5599 | Resource planning |
| E5600-E5699 | Plan validation |
| E5700-E5799 | Execution monitoring |
| E5800-E5899 | Plan persistence |
| E5900-E5999 | Multi-agent coordination |

## Integration

### L04 Model Gateway

L05 integrates with L04 for LLM-based goal decomposition:

```python
from src.L04_model_gateway.services.model_gateway import ModelGateway

gateway = ModelGateway()
service = PlanningService(gateway_client=gateway)
```

### L02 Agent Runtime

Task execution is dispatched to L02 Agent Runtime (integration stubs in place).

### L03 Tool Execution

Tool call tasks are routed through L03 Tool Execution Layer (integration stubs in place).

## Configuration

Configure L05 components:

```python
# Custom decomposer with specific strategy
decomposer = GoalDecomposer(
    default_strategy="template",  # "hybrid", "llm", or "template"
    max_goal_length=50000,
)

# Custom orchestrator with higher parallelism
orchestrator = TaskOrchestrator(
    max_parallel_tasks=20,
    task_timeout_sec=600,
)

# Custom cache configuration
cache = PlanCache(
    l1_max_size=200,
    l2_ttl_seconds=7200,
    enable_l2=True,
)

service = PlanningService(
    decomposer=decomposer,
    orchestrator=orchestrator,
)
```

## Metrics

L05 tracks comprehensive metrics across all components:

- **Decomposition**: strategy usage, cache hit rates, latency
- **Validation**: success rates, error distribution
- **Execution**: task completion rates, retry rates, parallelism
- **Assignment**: affinity hits, load distribution
- **Monitoring**: events emitted, failures detected, timeouts

Access metrics via:

```python
stats = service.get_stats()
```

## Security

### Goal Input Validation

All goal text is validated for:
- Character whitelist (alphanumeric, spaces, basic punctuation)
- No shell metacharacters (< > | & ; $ backticks)
- No SQL keywords (DROP, DELETE, INSERT, UPDATE)
- No code patterns (eval(, __import__, exec(, <script>)
- Maximum 100,000 characters

### Plan Signing

All plans are signed with HMAC-SHA256 for integrity verification.

### Secret Management

Secrets are masked and referenced via vault integration (L00).

## Testing

Run tests:

```bash
cd platform
pytest src/L05_planning/tests/ -v
```

## Dependencies

- Python 3.9+
- Redis (optional, for L2 cache)
- L04 Model Gateway (for LLM decomposition)
- L02 Agent Runtime (for task execution)
- L03 Tool Execution (for tool calls)

## License

Internal use only.
