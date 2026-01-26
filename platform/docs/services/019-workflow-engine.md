# Service 19/44: WorkflowEngine

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.workflow_engine` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | AgentExecutor, StateManager |
| **Category** | Agent Management / Orchestration |

## Role in Development Environment

The **WorkflowEngine** executes graph-based agent workflows with conditional routing and parallel execution. Inspired by LangGraph, it provides:
- Directed graph workflow execution
- Conditional branching based on state or results
- Parallel execution with branch limits
- Cycle detection and depth limiting
- Checkpoint/resume capabilities
- Timeout enforcement per workflow and per node
- Template variable substitution

This is **the orchestration layer for complex agent tasks** - when you need multiple agents working together, conditional logic, or parallel processing, WorkflowEngine manages the execution flow.

## Data Model

### WorkflowGraph Dataclass
- `graph_id: str` - Graph identifier
- `nodes: Dict[str, WorkflowNode]` - Node definitions
- `edges: List[WorkflowEdge]` - Edge connections
- `entry_node: str` - Starting node ID

### WorkflowNode Dataclass
- `node_id: str` - Node identifier
- `node_type: NodeType` - Type (agent, conditional, parallel, end)
- `config: Dict` - Node-specific configuration
- `metadata: Dict` - Additional metadata

### WorkflowEdge Dataclass
- `source: str` - Source node ID
- `target: str` - Target node ID
- `condition: str` - Optional condition expression

### NodeType Enum
- `AGENT` - Execute agent task
- `CONDITIONAL` - Branch based on condition
- `PARALLEL` - Execute children in parallel
- `END` - Workflow termination

### ExecutionContext Dataclass
- `workflow_id: str` - Workflow identifier
- `graph: WorkflowGraph` - Graph being executed
- `state: Dict` - Workflow state (shared across nodes)
- `visited_nodes: Set[str]` - Nodes already executed
- `execution_path: List[str]` - Ordered execution history
- `depth: int` - Current graph depth
- `started_at: datetime` - Execution start time
- `completed_at: datetime` - Execution end time (if completed)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_graph_depth` | 100 | Maximum node depth |
| `max_parallel_branches` | 10 | Maximum parallel children |
| `cycle_detection` | true | Detect and prevent cycles |
| `checkpoint_on_node_complete` | true | Save checkpoint after each node |
| `timeout_seconds` | 3600 | Workflow timeout (1 hour) |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize(agent_executor, state_manager)` | Initialize with dependencies |
| `register_node_handler(node_type, handler)` | Register custom node handler |
| `execute_workflow(workflow_id, graph, initial_state)` | Execute workflow graph |
| `get_execution_status(workflow_id)` | Get active workflow status |
| `resume_workflow(workflow_id, checkpoint_id)` | Resume from checkpoint |
| `cancel_workflow(workflow_id, reason)` | Cancel active workflow |
| `list_active_workflows()` | List all active workflows |
| `get_health_status()` | Get engine health |
| `get_metrics()` | Get execution metrics |
| `cleanup()` | Cleanup all resources |

## Use Cases in Your Workflow

### 1. Initialize Workflow Engine
```python
from L02_runtime.services.workflow_engine import WorkflowEngine
from L02_runtime.services.agent_executor import AgentExecutor
from L02_runtime.services.state_manager import StateManager

engine = WorkflowEngine(config={
    "max_graph_depth": 100,
    "max_parallel_branches": 10,
    "cycle_detection": True,
    "checkpoint_on_node_complete": True,
    "timeout_seconds": 3600
})

# Initialize with dependencies
await engine.initialize(
    agent_executor=AgentExecutor(),
    state_manager=StateManager()
)

# Default handlers registered:
# - "agent": Execute agent task
# - "conditional": Branch on condition
# - "parallel": Execute children in parallel
# - "end": Terminate workflow
```

### 2. Define a Simple Sequential Workflow
```python
from L02_runtime.models.workflow_models import (
    WorkflowGraph, WorkflowNode, WorkflowEdge, NodeType
)

# Create a simple: analyze -> implement -> test workflow
graph = WorkflowGraph(
    graph_id="simple-workflow",
    entry_node="analyze",
    nodes={
        "analyze": WorkflowNode(
            node_id="analyze",
            node_type=NodeType.AGENT,
            config={
                "agent_id": "analyzer-agent",
                "input": {"task": "Analyze the requirements"},
                "output_key": "analysis_result",
                "timeout_seconds": 300
            }
        ),
        "implement": WorkflowNode(
            node_id="implement",
            node_type=NodeType.AGENT,
            config={
                "agent_id": "coder-agent",
                "input": {"task": "${analysis_result}"},  # Template variable
                "output_key": "implementation"
            }
        ),
        "test": WorkflowNode(
            node_id="test",
            node_type=NodeType.AGENT,
            config={
                "agent_id": "tester-agent",
                "input": {"code": "${implementation}"}
            }
        ),
        "end": WorkflowNode(
            node_id="end",
            node_type=NodeType.END,
            config={}
        )
    },
    edges=[
        WorkflowEdge(source="analyze", target="implement"),
        WorkflowEdge(source="implement", target="test"),
        WorkflowEdge(source="test", target="end")
    ]
)
```

### 3. Execute a Workflow
```python
# Execute with initial state
result = await engine.execute_workflow(
    workflow_id="workflow-001",
    graph=graph,
    initial_state={
        "requirements": "Build a Steam-style modal component",
        "language": "TypeScript"
    }
)

print(f"Final state: {result}")
# {
#     "analysis_result": {...},
#     "implementation": {...},
#     "test_result": {...}
# }
```

### 4. Conditional Branching Workflow
```python
# Create workflow with conditional logic
graph = WorkflowGraph(
    graph_id="conditional-workflow",
    entry_node="analyze",
    nodes={
        "analyze": WorkflowNode(
            node_id="analyze",
            node_type=NodeType.AGENT,
            config={
                "input": {"task": "Analyze code quality"},
                "output_key": "analysis"
            }
        ),
        "check_quality": WorkflowNode(
            node_id="check_quality",
            node_type=NodeType.CONDITIONAL,
            config={"condition_key": "analysis.score"}
        ),
        "fix_issues": WorkflowNode(
            node_id="fix_issues",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Fix quality issues"}}
        ),
        "approve": WorkflowNode(
            node_id="approve",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Approve code"}}
        ),
        "end": WorkflowNode(
            node_id="end",
            node_type=NodeType.END,
            config={}
        )
    },
    edges=[
        WorkflowEdge(source="analyze", target="check_quality"),
        # Branch based on quality score
        WorkflowEdge(
            source="check_quality",
            target="fix_issues",
            condition="state.analysis.score < 80"  # Low quality
        ),
        WorkflowEdge(
            source="check_quality",
            target="approve",
            condition="state.analysis.score >= 80"  # High quality
        ),
        WorkflowEdge(source="fix_issues", target="end"),
        WorkflowEdge(source="approve", target="end")
    ]
)
```

### 5. Parallel Execution Workflow
```python
# Create workflow with parallel branches
graph = WorkflowGraph(
    graph_id="parallel-workflow",
    entry_node="start",
    nodes={
        "start": WorkflowNode(
            node_id="start",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Initialize work"}}
        ),
        "parallel_tasks": WorkflowNode(
            node_id="parallel_tasks",
            node_type=NodeType.PARALLEL,
            config={
                "children": ["task_a", "task_b", "task_c"]
            }
        ),
        "task_a": WorkflowNode(
            node_id="task_a",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Run linting"}}
        ),
        "task_b": WorkflowNode(
            node_id="task_b",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Run type checking"}}
        ),
        "task_c": WorkflowNode(
            node_id="task_c",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Run unit tests"}}
        ),
        "merge": WorkflowNode(
            node_id="merge",
            node_type=NodeType.AGENT,
            config={"input": {"task": "Combine results"}}
        ),
        "end": WorkflowNode(
            node_id="end",
            node_type=NodeType.END,
            config={}
        )
    },
    edges=[
        WorkflowEdge(source="start", target="parallel_tasks"),
        WorkflowEdge(source="parallel_tasks", target="merge"),
        WorkflowEdge(source="merge", target="end")
    ]
)

# All three tasks run concurrently
result = await engine.execute_workflow("parallel-001", graph)
```

### 6. Check Workflow Status
```python
# Get status of active workflow
status = await engine.get_execution_status("workflow-001")

if status:
    print(f"Workflow: {status['workflow_id']}")
    print(f"Started: {status['started_at']}")
    print(f"Nodes executed: {status['nodes_executed']}")
    print(f"Current depth: {status['current_depth']}")
    print(f"Execution path: {status['execution_path']}")
```

### 7. Resume Workflow from Checkpoint
```python
# Resume a workflow that was interrupted
result = await engine.resume_workflow(
    workflow_id="workflow-001",
    checkpoint_id="chk-abc123"  # Optional, uses latest if not specified
)

# Or resume from hot state (faster)
result = await engine.resume_workflow("workflow-001")
```

### 8. Cancel Active Workflow
```python
# Cancel a running workflow
cancelled = await engine.cancel_workflow(
    workflow_id="workflow-001",
    reason="User requested cancellation"
)

if cancelled:
    print("Workflow cancelled and checkpointed")
else:
    print("Workflow not found")
```

### 9. List Active Workflows
```python
# Get all active workflows
active = engine.list_active_workflows()

for workflow in active:
    print(f"{workflow['workflow_id']}: "
          f"{workflow['nodes_executed']} nodes, "
          f"depth {workflow['current_depth']}")
```

### 10. Register Custom Node Handler
```python
# Register a custom node type
async def custom_handler(node, context):
    """Custom node handler for specialized processing."""
    input_data = node.config.get("input", {})

    # Do custom processing
    result = await process_custom_logic(input_data)

    # Store in state
    context.state[node.node_id] = result
    return result

engine.register_node_handler("custom", custom_handler)

# Now use in graphs
node = WorkflowNode(
    node_id="custom_step",
    node_type="custom",  # Uses custom handler
    config={"input": {...}}
)
```

## Service Interactions

```
+------------------+
|  WorkflowEngine  | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+
|  AgentExecutor   |     |   StateManager    |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
|AgentOrchestrator |     |  ExecutionEngine  |
|     (L02)        |     |      (L05)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **AgentExecutor (L02)**: Executes agent nodes
- **StateManager (L02)**: Checkpoints workflow state
- **AgentOrchestrator (L02)**: Orchestrates multi-agent workflows
- **ExecutionEngine (L05)**: Higher-level task execution

## Condition Expressions

The engine supports multiple condition types for routing:

### Simple Boolean Conditions
```python
# Success/failure checks
"success"    # Result has success=True
"failure"    # Result has success=False
"always"     # Always true
"never"      # Always false
```

### State-Based Conditions
```python
# Check workflow state values
"state.score == 100"
"state.status != 'error'"
"state.count > 10"
"state.priority >= 'high'"
"state.type in ['a', 'b', 'c']"
```

### Result-Based Conditions
```python
# Check node result values
"result.success == True"
"result.error != None"
"result.items > 0"
```

### Nested Key Access
```python
# Dot notation for nested values
"state.analysis.quality.score >= 80"
"result.data.status == 'complete'"
```

## Execution Flow

```
1. Start Execution
   ├── Create ExecutionContext
   ├── Find entry node
   └── Begin graph traversal

2. Execute Node
   ├── Check depth limit
   ├── Cycle detection
   ├── Get node handler
   ├── Execute handler
   ├── Checkpoint (if enabled)
   └── Get next nodes

3. Route to Next
   ├── Conditional: Evaluate conditions
   ├── Parallel: Execute all children
   └── Sequential: Follow first edge

4. Complete
   ├── Execute END node
   ├── Return final state
   └── Cleanup context
```

## Error Codes

| Code | Description |
|------|-------------|
| E2010 | Graph cycle detected |
| E2011 | Max graph depth exceeded |
| E2012 | Workflow execution failed (various causes) |
| E2013 | Timeout or parallel branch limit exceeded |

## Execution Examples

```python
# Complete workflow execution
engine = WorkflowEngine(config={
    "max_graph_depth": 50,
    "max_parallel_branches": 5,
    "timeout_seconds": 1800
})

await engine.initialize(
    agent_executor=agent_exec,
    state_manager=state_mgr
)

# Build graph
graph = WorkflowGraph(
    graph_id="dev-workflow",
    entry_node="plan",
    nodes={
        "plan": WorkflowNode(
            node_id="plan",
            node_type=NodeType.AGENT,
            config={
                "agent_id": "planner",
                "input": {"task": "Create implementation plan"},
                "output_key": "plan"
            }
        ),
        "implement": WorkflowNode(
            node_id="implement",
            node_type=NodeType.AGENT,
            config={
                "agent_id": "coder",
                "input": {"plan": "${plan}"},
                "retry_count": 2,
                "timeout_seconds": 600
            }
        ),
        "verify": WorkflowNode(
            node_id="verify",
            node_type=NodeType.CONDITIONAL,
            config={"condition_key": "implement.success"}
        ),
        "fix": WorkflowNode(
            node_id="fix",
            node_type=NodeType.AGENT,
            config={"input": {"issues": "${implement.errors}"}}
        ),
        "end": WorkflowNode(
            node_id="end",
            node_type=NodeType.END,
            config={}
        )
    },
    edges=[
        WorkflowEdge(source="plan", target="implement"),
        WorkflowEdge(source="implement", target="verify"),
        WorkflowEdge(source="verify", target="end", condition="success"),
        WorkflowEdge(source="verify", target="fix", condition="failure"),
        WorkflowEdge(source="fix", target="implement")  # Loop back
    ]
)

# Execute
try:
    result = await engine.execute_workflow(
        workflow_id="dev-001",
        graph=graph,
        initial_state={"project": "steam-modal"}
    )
    print(f"Completed: {result}")
except WorkflowError as e:
    print(f"Failed: {e.code} - {e.message}")

# Check metrics
metrics = engine.get_metrics()
print(f"Active: {metrics['active_workflows']}")
print(f"Total nodes: {metrics['total_nodes_executed']}")

# Cleanup
await engine.cleanup()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Graph Execution | Complete |
| Agent Node Handler | Complete |
| Conditional Node Handler | Complete |
| Parallel Node Handler | Complete |
| End Node Handler | Complete |
| Cycle Detection | Complete |
| Depth Limiting | Complete |
| Timeout Enforcement | Complete |
| Checkpoint on Node | Complete |
| Resume from Checkpoint | Complete |
| Cancel Workflow | Complete |
| Template Substitution | Complete |
| Condition Evaluation | Complete |
| Node Retry Logic | Complete |
| Custom Node Handlers | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Subgraph Execution | Medium | Execute nested graphs |
| Dynamic Graph Modification | Medium | Add/remove nodes at runtime |
| Workflow Versioning | Low | Version control for graphs |
| Execution History | Low | Persistent execution logs |
| Visual Graph Editor | Low | UI for graph construction |
| Distributed Execution | Low | Execute across workers |

## Strengths

- **LangGraph-inspired** - Familiar state machine patterns
- **Flexible routing** - Conditional and parallel execution
- **Safety guards** - Cycle detection and depth limits
- **Checkpoint/resume** - Recovery from interruption
- **Template substitution** - Dynamic input from state
- **Timeout enforcement** - Prevent hung workflows
- **Retry support** - Agent node retry on failure

## Weaknesses

- **No subgraphs** - Cannot nest workflow graphs
- **No dynamic modification** - Graph is static during execution
- **No distributed execution** - Single-process only
- **No versioning** - Graphs not version controlled
- **Memory-based** - Active executions not persisted
- **Simple conditions** - No complex expression language

## Best Practices

### Graph Design
Keep graphs simple and testable:
```python
# Good: Linear with clear branches
start -> analyze -> check -> [pass/fail] -> end

# Avoid: Complex tangled graphs
start -> A -> B -> C -> A (loop) -> D -> B (another loop)
```

### Node Configuration
Use meaningful keys and timeouts:
```python
WorkflowNode(
    node_id="analyze_code",  # Descriptive ID
    node_type=NodeType.AGENT,
    config={
        "agent_id": "code-analyzer",
        "input": {"file": "${file_path}"},
        "output_key": "analysis",  # Clear output location
        "timeout_seconds": 300,    # Reasonable timeout
        "retry_count": 2           # Handle transient failures
    }
)
```

### Condition Design
Use explicit conditions:
```python
# Good: Explicit state checks
"state.analysis.score >= 80"
"result.success == True"

# Avoid: Implicit truthy checks
"state.score"  # Less clear
```

### Error Handling
Handle workflow failures:
```python
try:
    result = await engine.execute_workflow(...)
except WorkflowError as e:
    if e.code == "E2010":  # Cycle
        logger.error("Graph has a cycle")
    elif e.code == "E2011":  # Depth
        logger.error("Graph too deep")
    elif e.code == "E2013":  # Timeout
        # Resume from checkpoint
        result = await engine.resume_workflow(workflow_id)
```

### Parallel Branch Limits
Respect resource constraints:
```python
# Configure based on system capacity
WorkflowEngine(config={
    "max_parallel_branches": 5  # Don't overload system
})

# Or limit in graph design
WorkflowNode(
    node_type=NodeType.PARALLEL,
    config={"children": ["a", "b", "c"]}  # Reasonable count
)
```

## Source Files

- Service: `platform/src/L02_runtime/services/workflow_engine.py`
- Models: `platform/src/L02_runtime/models/workflow_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.2)

## Related Services

- AgentExecutor (L02) - Executes agent nodes
- StateManager (L02) - Checkpoints workflow state
- AgentOrchestrator (L02) - Multi-agent coordination
- LifecycleManager (L02) - Agent lifecycle
- ExecutionEngine (L05) - Higher-level execution
- PlanningService (L05) - Generates workflow plans

---
*Generated: 2026-01-24 | Platform Services Documentation*
