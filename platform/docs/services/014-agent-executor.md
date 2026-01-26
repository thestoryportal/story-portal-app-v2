# Service 14/44: AgentExecutor

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L02 (Runtime Layer) |
| **Module** | `L02_runtime.services.agent_executor` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (in-memory) |
| **Category** | Agent Management / Runtime |

## Role in Development Environment

The **AgentExecutor** is the core code execution engine for agents. It provides:
- Agent code execution within configured sandboxes
- Tool invocation with concurrency control and timeouts
- Execution context management with token tracking
- Streaming response support
- Retry logic with exponential backoff for failed tools
- Parallel tool execution

This is **the heart of agent execution** - when Claude Code or any agent runs, AgentExecutor manages the execution context, handles tool calls, and tracks token usage.

## Data Model

### ExecutionContext Dataclass
- `agent_id: str` - Agent identifier
- `session_id: str` - Session identifier
- `messages: List[Dict]` - Conversation history with timestamps
- `tools: List[ToolDefinition]` - Available tools
- `context_window_tokens: int` - Max tokens (default: 128000)
- `current_tokens: int` - Current token usage
- `metadata: Dict` - Additional context data

### ToolInvocation Dataclass
- `tool_name: str` - Name of tool to invoke
- `parameters: Dict` - Tool parameters
- `invocation_id: str` - Unique invocation ID
- `timeout_seconds: int` - Timeout (default: 300)

### ToolResult Dataclass
- `invocation_id: str` - Matching invocation ID
- `tool_name: str` - Tool that was invoked
- `success: bool` - Whether invocation succeeded
- `result: Any` - Result data (if success)
- `error: str` - Error message (if failed)
- `execution_time_ms: float` - Execution duration

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_concurrent_tools` | 10 | Max parallel tool invocations |
| `tool_timeout_seconds` | 300 | Default tool timeout (5 min) |
| `context_window_tokens` | 128000 | Context window size |
| `enable_streaming` | true | Enable streaming responses |
| `retry_on_tool_failure` | true | Retry failed tools |
| `max_tool_retries` | 3 | Maximum retry attempts |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize the executor |
| `register_tool(name, handler)` | Register a tool handler |
| `unregister_tool(name)` | Remove a tool handler |
| `create_context(agent_id, session_id, config)` | Create execution context |
| `get_context(agent_id)` | Get existing context |
| `execute(agent_id, input_data, stream)` | Execute agent with input |
| `invoke_tool(agent_id, invocation)` | Invoke a single tool |
| `invoke_tools_parallel(agent_id, invocations)` | Invoke multiple tools in parallel |
| `cleanup_context(agent_id)` | Cleanup agent context |
| `cleanup()` | Cleanup all contexts |

## Use Cases in Your Workflow

### 1. Initialize Executor with Configuration
```python
from L02_runtime.services.agent_executor import AgentExecutor

executor = AgentExecutor(config={
    "max_concurrent_tools": 10,
    "tool_timeout_seconds": 300,
    "context_window_tokens": 128000,
    "enable_streaming": True,
    "retry_on_tool_failure": True,
    "max_tool_retries": 3
})

await executor.initialize()
```

### 2. Register Tool Handlers
```python
# Register a bash tool
async def bash_handler(params: dict) -> dict:
    command = params.get("command")
    # Execute command...
    return {"stdout": "output", "exit_code": 0}

executor.register_tool("Bash", bash_handler)

# Register a read tool
async def read_handler(params: dict) -> dict:
    file_path = params.get("file_path")
    # Read file...
    return {"content": "file contents", "lines": 42}

executor.register_tool("Read", read_handler)

# Register an edit tool
async def edit_handler(params: dict) -> dict:
    file_path = params.get("file_path")
    old_string = params.get("old_string")
    new_string = params.get("new_string")
    # Edit file...
    return {"success": True, "lines_changed": 1}

executor.register_tool("Edit", edit_handler)
```

### 3. Create Execution Context
```python
from L02_runtime.models import AgentConfig, ToolDefinition

# Define available tools
tools = [
    ToolDefinition(name="Bash", description="Run shell commands"),
    ToolDefinition(name="Read", description="Read files"),
    ToolDefinition(name="Edit", description="Edit files"),
]

# Create agent config
config = AgentConfig(
    agent_id="agent-123",
    tools=tools,
    model="claude-opus-4-5-20251101"
)

# Create execution context
context = await executor.create_context(
    agent_id="agent-123",
    session_id="session-456",
    config=config,
    initial_context={
        "working_directory": "/project",
        "task": "Implement Steam Modal"
    }
)
```

### 4. Execute Agent with Input
```python
# Synchronous execution
result = await executor.execute(
    agent_id="agent-123",
    input_data={
        "content": "Implement a modal component with Steam-like animations"
    },
    stream=False
)

print(result)
# {
#     "agent_id": "agent-123",
#     "session_id": "session-456",
#     "response": "...",
#     "tool_calls": [...],
#     "tokens_used": 150
# }
```

### 5. Execute with Streaming Response
```python
# Streaming execution
async for chunk in await executor.execute(
    agent_id="agent-123",
    input_data={"content": "Analyze this code..."},
    stream=True
):
    if chunk["type"] == "content":
        print(chunk["delta"], end="", flush=True)
    elif chunk["type"] == "end":
        print(f"\nTokens used: {chunk['tokens_used']}")

# Output:
# Agent execution result (stub)
# Tokens used: 0
```

### 6. Invoke Single Tool
```python
from L02_runtime.services.agent_executor import ToolInvocation

# Create tool invocation
invocation = ToolInvocation(
    tool_name="Bash",
    parameters={"command": "npm test"},
    timeout_seconds=120
)

# Invoke tool (with automatic retry on failure)
result = await executor.invoke_tool(
    agent_id="agent-123",
    invocation=invocation
)

if result.success:
    print(f"Tool completed in {result.execution_time_ms}ms")
    print(f"Result: {result.result}")
else:
    print(f"Tool failed: {result.error}")
```

### 7. Invoke Multiple Tools in Parallel
```python
# Create multiple invocations
invocations = [
    ToolInvocation(tool_name="Read", parameters={"file_path": "a.ts"}),
    ToolInvocation(tool_name="Read", parameters={"file_path": "b.ts"}),
    ToolInvocation(tool_name="Read", parameters={"file_path": "c.ts"}),
]

# Invoke all in parallel (respects max_concurrent_tools)
results = await executor.invoke_tools_parallel(
    agent_id="agent-123",
    invocations=invocations
)

for result in results:
    if result.success:
        print(f"{result.tool_name}: success ({result.execution_time_ms}ms)")
    else:
        print(f"{result.tool_name}: failed - {result.error}")
```

### 8. Monitor Context Token Usage
```python
# Get execution context
context = await executor.get_context("agent-123")

# Check token usage
print(f"Current tokens: {context.current_tokens}")
print(f"Context window: {context.context_window_tokens}")
print(f"Usage: {context.current_tokens / context.context_window_tokens * 100:.1f}%")

# Check if context is full
if context.is_context_full():
    print("Warning: Context window exceeded!")
```

### 9. Cleanup After Execution
```python
# Cleanup single agent context
await executor.cleanup_context("agent-123")

# Cleanup all contexts (shutdown)
await executor.cleanup()
```

## Service Interactions

```
+------------------+
|  AgentExecutor   | <--- L02 Runtime Layer
|     (L02)        |
+--------+---------+
         |
   Manages execution for:
         |
+------------------+     +-------------------+     +------------------+
| SandboxManager   |     |   ToolRegistry    |     |  ModelBridge     |
|     (L02)        |     |      (L01)        |     |      (L04)       |
+------------------+     +-------------------+     +------------------+
         |
   Used by:
         |
+------------------+     +-------------------+     +------------------+
|  StateManager    |     | AgentOrchestrator |     | SessionService   |
|     (L02)        |     |      (L02)        |     |      (L01)       |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **SandboxManager (L02)**: Provides sandbox configuration for execution
- **ToolRegistry (L01)**: Stores tool definitions and execution logs
- **ModelBridge (L04)**: LLM inference for agent responses
- **StateManager (L02)**: Persists agent state between executions
- **AgentOrchestrator (L02)**: Orchestrates multi-agent workflows
- **SessionService (L01)**: Session context for execution

## Execution Flow

```
1. Create Context
   ├── agent_id, session_id
   ├── Available tools
   └── Context window size

2. Execute
   ├── Add input to context
   ├── Check context overflow
   ├── Call ModelBridge for inference
   └── Return response (or stream)

3. Tool Invocation
   ├── Validate tool exists
   ├── Acquire concurrency semaphore
   ├── Execute with timeout
   ├── Retry on failure (exponential backoff)
   └── Return ToolResult

4. Cleanup
   ├── Remove context from memory
   └── Unregister tools
```

## Retry Logic

The executor uses exponential backoff for failed tools:

```
Attempt 1: Execute immediately
Attempt 2: Wait 2 seconds, then execute
Attempt 3: Wait 4 seconds, then execute
(max_tool_retries reached, fail)
```

## Error Codes

| Code | Description |
|------|-------------|
| E2000 | Execution context not found for agent |
| E2001 | Tool not registered or tool execution failed |
| E2002 | Tool execution timeout |
| E2003 | Context window exceeded |
| E2004 | General execution failure |

## Execution Examples

```python
# Full execution workflow
executor = AgentExecutor(config={
    "max_concurrent_tools": 5,
    "tool_timeout_seconds": 60,
    "retry_on_tool_failure": True
})

await executor.initialize()

# Register tools
executor.register_tool("Read", read_handler)
executor.register_tool("Edit", edit_handler)
executor.register_tool("Bash", bash_handler)

# Create context
context = await executor.create_context(
    agent_id="agent-1",
    session_id="session-1",
    config=agent_config
)

# Execute
result = await executor.execute(
    agent_id="agent-1",
    input_data={"content": "Fix the bug in main.py"}
)

# Invoke tools as needed
tool_result = await executor.invoke_tool(
    agent_id="agent-1",
    invocation=ToolInvocation(
        tool_name="Read",
        parameters={"file_path": "main.py"}
    )
)

# Cleanup
await executor.cleanup_context("agent-1")
```

## Context Window Management

The executor tracks token usage to prevent context overflow:

```python
context = await executor.get_context("agent-1")

# Each message adds to token count
context.add_message("user", "Hello", tokens=5)
context.add_message("assistant", "Hi there!", tokens=4)

# Check before execution
if context.is_context_full():
    raise ExecutorError(code="E2003", message="Context window exceeded")

# Monitor usage
usage_percent = (context.current_tokens / context.context_window_tokens) * 100
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Executor Initialization | Complete |
| Tool Registration | Complete |
| Context Creation | Complete |
| Sync Execution | Complete (stub) |
| Streaming Execution | Complete (stub) |
| Tool Invocation | Complete |
| Parallel Tool Invocation | Complete |
| Retry Logic | Complete |
| Timeout Handling | Complete |
| Concurrency Control | Complete |
| Context Cleanup | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| ModelBridge Integration | High | Connect to LLM for inference |
| Token Counting | High | Accurate token estimation |
| Tool Result Streaming | Medium | Stream tool results |
| Context Compaction | Medium | Summarize when near limit |
| Tool Caching | Low | Cache tool results |
| Metrics/Telemetry | Low | Execution metrics |
| Tool Priority Scheduling | Low | Priority-based tool ordering |

## Strengths

- **Concurrent tool execution** - Semaphore-controlled parallelism
- **Retry logic** - Automatic retry with exponential backoff
- **Timeout handling** - Prevents hung tools
- **Streaming support** - AsyncIterator for streaming responses
- **Context tracking** - Token usage monitoring
- **Clean API** - Simple register/invoke/cleanup pattern

## Weaknesses

- **No persistence** - Contexts are in-memory only
- **Stub LLM integration** - ModelBridge not connected
- **Simple token counting** - Word-based estimation
- **No tool caching** - Repeated invocations re-execute
- **No context compaction** - No summarization on overflow
- **No metrics** - No execution telemetry

## Best Practices

### Tool Handler Design
Keep handlers simple and async:
```python
async def my_tool_handler(params: dict) -> dict:
    # Validate params
    required = params.get("required_param")
    if not required:
        raise ValueError("required_param is required")

    # Do work
    result = await do_async_work(required)

    # Return structured result
    return {"success": True, "data": result}
```

### Timeout Settings
Match timeouts to tool characteristics:
```python
# Quick tools
ToolInvocation(tool_name="Read", timeout_seconds=30)

# Medium tools
ToolInvocation(tool_name="Bash", timeout_seconds=120)

# Long tools
ToolInvocation(tool_name="Build", timeout_seconds=600)
```

### Concurrency Configuration
Set based on system resources:
```python
# Low resource environment
AgentExecutor(config={"max_concurrent_tools": 3})

# High resource environment
AgentExecutor(config={"max_concurrent_tools": 20})
```

### Error Handling
Always handle ExecutorError:
```python
try:
    result = await executor.invoke_tool(agent_id, invocation)
except ExecutorError as e:
    if e.code == "E2002":  # Timeout
        # Handle timeout
        pass
    elif e.code == "E2001":  # Tool failure
        # Handle failure
        pass
```

## Source Files

- Service: `platform/src/L02_runtime/services/agent_executor.py`
- Models: `platform/src/L02_runtime/models/agent_models.py`
- Spec: `platform/specs/agent-runtime-layer-specification-v1.2-final-ASCII.md` (Section 3.3.1)

## Related Services

- SandboxManager (L02) - Sandbox configuration
- StateManager (L02) - State persistence
- ToolRegistry (L01) - Tool definitions
- SessionService (L01) - Session context
- ModelBridge (L04) - LLM inference
- WorkflowEngine (L02) - Multi-step workflows

---
*Generated: 2026-01-24 | Platform Services Documentation*
