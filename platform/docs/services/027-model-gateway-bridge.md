# Service 27/44: ModelGatewayBridge (ToolModelBridge)

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.model_gateway_bridge` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L04 Model Gateway (lazy loaded) |
| **Category** | Tool Management / AI Integration |

## Role in Development Environment

The **ModelGatewayBridge** (implemented as ToolModelBridge) integrates L04 Model Gateway with L03 Tool Execution, enabling AI-powered tools. It provides:
- LLM inference requests from within tool execution
- Result analysis using language models
- Multi-tool result composition via LLM
- Lazy loading of L04 Model Gateway
- Token usage tracking and logging

This is **the AI integration layer for tool execution** - when tools need to leverage LLM capabilities (analyzing code, composing results, generating content), ToolModelBridge provides the bridge to L04's inference infrastructure.

## Data Model

### L04 Integration (via imports)

Uses L04 models for inference:
- `Message` - Chat message structure
- `MessageRole` - USER, ASSISTANT, SYSTEM
- `InferenceRequest` - Complete inference request
- `InferenceResponse` - Response with content and token usage

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gateway` | None | Optional L04 ModelGateway instance |

When `gateway` is None, it's lazy loaded on first use.

## API Methods

| Method | Description |
|--------|-------------|
| `tool_request_inference(...)` | Request LLM inference during tool execution |
| `tool_analyze_result(...)` | Use LLM to analyze tool output |
| `tool_compose_with_llm(...)` | Compose results from multiple tools |
| `close()` | Cleanup resources |

## Use Cases in Your Workflow

### 1. Initialize Model Gateway Bridge
```python
from L03_tool_execution.services.model_gateway_bridge import ToolModelBridge

# Default initialization (lazy loads L04 gateway)
bridge = ToolModelBridge()

# Or with explicit gateway instance
from L04_model_gateway.services import ModelGateway
gateway = ModelGateway()
bridge = ToolModelBridge(gateway=gateway)
```

### 2. Request Inference During Tool Execution
```python
# Tool that uses LLM for code analysis
async def analyze_code_tool(file_content: str, agent_did: str):
    result = await bridge.tool_request_inference(
        tool_id="CodeAnalyzer",
        agent_did=agent_did,
        prompt=f"Analyze this code for potential issues:\n\n{file_content}",
        system_prompt="You are a code review expert.",
        temperature=0.3,  # Lower temperature for analysis
        max_tokens=1000,
        capabilities=["text", "code"]
    )
    return result

# Execute
analysis = await analyze_code_tool(
    file_content="def foo():\n    return bar + 1",
    agent_did="did:agent:abc123"
)
print(analysis)
# "The code references 'bar' which is not defined in the function scope..."
```

### 3. Analyze Tool Execution Results
```python
# After a tool produces output, use LLM to analyze it
tool_output = """
Files scanned: 42
Issues found: 7
- src/modal.tsx:15 - Missing accessibility label
- src/modal.tsx:28 - Unused import
- src/button.tsx:8 - Missing type annotation
...
"""

analysis = await bridge.tool_analyze_result(
    tool_id="LintAnalyzer",
    agent_did="did:agent:abc123",
    tool_output=tool_output,
    analysis_prompt="Summarize the issues and prioritize them by severity."
)

print(analysis["analysis"])
# "The linting found 7 issues. Priority 1 (High): Missing accessibility label..."

print(analysis["original_output"])
# Original tool output preserved
```

### 4. Compose Results from Multiple Tools
```python
# After running multiple tools, compose their results
previous_results = [
    {
        "tool_id": "Read",
        "output": "File contents: class Modal extends React.Component..."
    },
    {
        "tool_id": "Grep",
        "output": "Found 3 usages of Modal in: App.tsx, Header.tsx, Footer.tsx"
    },
    {
        "tool_id": "Analyze",
        "output": "Component has 2 props: isOpen (boolean), onClose (function)"
    }
]

composed = await bridge.tool_compose_with_llm(
    tool_id="Composer",
    agent_did="did:agent:abc123",
    previous_results=previous_results,
    composition_prompt="Create a summary of the Modal component based on these findings."
)

print(composed)
# "The Modal component is a React class component with 2 props (isOpen, onClose).
#  It is used in 3 locations: App.tsx, Header.tsx, and Footer.tsx..."
```

### 5. Build AI-Powered Tool
```python
from L03_tool_execution.models import ToolInvokeRequest, ToolInvokeResponse

class SmartRefactorTool:
    def __init__(self, bridge: ToolModelBridge):
        self.bridge = bridge

    async def execute(self, request: ToolInvokeRequest) -> ToolInvokeResponse:
        file_path = request.parameters["file_path"]
        refactor_type = request.parameters.get("type", "general")

        # Step 1: Read file (using another tool)
        file_content = await read_file(file_path)

        # Step 2: Use LLM to suggest refactoring
        suggestions = await self.bridge.tool_request_inference(
            tool_id="SmartRefactor",
            agent_did=request.agent_context.agent_did,
            prompt=f"Suggest {refactor_type} refactoring for:\n\n{file_content}",
            system_prompt="You are an expert code refactoring assistant.",
            temperature=0.5,
            max_tokens=2000,
            capabilities=["code"]
        )

        return ToolInvokeResponse(
            invocation_id=request.invocation_id,
            status=ToolStatus.SUCCESS,
            result=ToolResult(
                result={
                    "file_path": file_path,
                    "suggestions": suggestions,
                    "refactor_type": refactor_type
                }
            )
        )
```

### 6. Chain Analysis Steps
```python
# Multi-step analysis using LLM
async def deep_analysis(file_path: str, agent_did: str):
    # Step 1: Initial analysis
    initial = await bridge.tool_request_inference(
        tool_id="DeepAnalyzer",
        agent_did=agent_did,
        prompt=f"What does this file do? {file_path}",
        max_tokens=500
    )

    # Step 2: Security analysis
    security = await bridge.tool_request_inference(
        tool_id="DeepAnalyzer",
        agent_did=agent_did,
        prompt=f"Given this analysis:\n{initial}\n\nWhat security concerns exist?",
        system_prompt="You are a security auditor.",
        max_tokens=500
    )

    # Step 3: Compose final report
    return await bridge.tool_compose_with_llm(
        tool_id="DeepAnalyzer",
        agent_did=agent_did,
        previous_results=[
            {"tool_id": "initial", "output": initial},
            {"tool_id": "security", "output": security}
        ],
        composition_prompt="Create a comprehensive analysis report."
    )
```

### 7. Handle Errors
```python
try:
    result = await bridge.tool_request_inference(
        tool_id="FailingTool",
        agent_did="did:agent:abc123",
        prompt="Test prompt"
    )
except Exception as e:
    logger.error(f"Inference failed: {e}")
    # Fallback to non-AI execution path
    result = fallback_analysis()
```

### 8. Cleanup
```python
# When done with the bridge
await bridge.close()
# Closes underlying L04 Model Gateway connection
```

## Service Interactions

```
+------------------+
|  ToolModelBridge | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Lazy loads/uses:
         |
+------------------+
|   ModelGateway   | <--- L04 Model Gateway Layer
|      (L04)       |
+------------------+
         |
   Routes to:
         |
+------------------+
|   LLM Providers  |
| (Anthropic, etc) |
+------------------+
```

**Integration Points:**
- **ModelGateway (L04)**: Provides LLM inference execution
- **ToolExecutor (L03)**: Uses for AI-powered tools
- **ToolComposer (L03)**: Uses for LLM-based composition
- **Message/InferenceRequest (L04)**: Request/response models

## Data Flow

```
1. Tool Requests Inference
   ├── Build Message with prompt
   ├── Create InferenceRequest with agent_did, tool_id
   ├── Add metadata (tool_id, source="tool_execution")
   └── Execute via ModelGateway

2. Analyze Tool Result
   ├── Combine tool_output + analysis_prompt
   ├── Set system_prompt for analysis context
   └── Return analysis + original_output

3. Compose Multi-Tool Results
   ├── Format previous_results as text
   ├── Combine with composition_prompt
   ├── Set system_prompt for composition context
   └── Return composed result
```

## Inference Request Metadata

Each request includes tool execution metadata:
```python
metadata={
    "tool_id": tool_id,        # Which tool made the request
    "source": "tool_execution"  # Origin context
}
```

This enables:
- Token usage tracking per tool
- Rate limiting per agent
- Audit trail for AI tool usage

## Error Handling

All methods propagate exceptions with logging:
```python
try:
    # ... inference request ...
except Exception as e:
    logger.error(f"Tool inference request failed for {tool_id}: {e}")
    raise  # Propagate to caller
```

Callers should handle:
- Import errors (L04 not available)
- Inference failures (rate limits, model errors)
- Timeout errors

## Execution Examples

```python
# Complete AI-powered tool workflow
from L03_tool_execution.services.model_gateway_bridge import ToolModelBridge

bridge = ToolModelBridge()

# 1. Simple inference
response = await bridge.tool_request_inference(
    tool_id="Summarizer",
    agent_did="did:agent:test",
    prompt="Summarize this code: def add(a, b): return a + b",
    temperature=0.3,
    max_tokens=100
)
print(f"Summary: {response}")

# 2. Analyze test results
test_output = "PASSED: 42 tests\nFAILED: 3 tests\nSKIPPED: 5 tests"
analysis = await bridge.tool_analyze_result(
    tool_id="TestAnalyzer",
    agent_did="did:agent:test",
    tool_output=test_output,
    analysis_prompt="What do these test results indicate about code quality?"
)
print(f"Analysis: {analysis['analysis']}")

# 3. Compose multi-step results
results = [
    {"tool_id": "Lint", "output": "3 warnings found"},
    {"tool_id": "TypeCheck", "output": "All types valid"},
    {"tool_id": "Test", "output": "95% coverage"}
]
report = await bridge.tool_compose_with_llm(
    tool_id="ReportGenerator",
    agent_did="did:agent:test",
    previous_results=results,
    composition_prompt="Generate a code quality report from these results."
)
print(f"Report: {report}")

# 4. Cleanup
await bridge.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| ToolModelBridge class | Complete |
| Lazy Gateway Loading | Complete |
| tool_request_inference | Complete |
| tool_analyze_result | Complete |
| tool_compose_with_llm | Complete |
| close() | Complete |
| Error Handling | Complete |
| Logging | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Streaming Support | Medium | Stream inference responses |
| Caching | Medium | Cache repeated inference requests |
| Rate Limiting | Medium | Per-tool rate limits |
| Batch Inference | Low | Multiple prompts in one request |
| Model Selection | Low | Tool-specific model preferences |
| Metrics Export | Low | Prometheus metrics for tool AI usage |

## Strengths

- **Lazy loading** - L04 Gateway only loaded when needed
- **Simple API** - Three core methods cover most use cases
- **Metadata tracking** - Tool context preserved in requests
- **Composable** - Chain multiple tool results
- **Error propagation** - Clear error handling with logging
- **Clean abstraction** - Hides L04 complexity from tools

## Weaknesses

- **No streaming** - Waits for complete response
- **No caching** - Repeated prompts re-executed
- **No rate limiting** - Relies on L04 limits only
- **No model selection** - Uses gateway defaults
- **Synchronous** - No batch processing
- **Single gateway** - No failover support

## Best Practices

### Temperature Selection
Match temperature to task:
```python
# Analysis/Factual (low temperature)
tool_request_inference(temperature=0.1, ...)

# General tasks (medium temperature)
tool_request_inference(temperature=0.5, ...)

# Creative tasks (higher temperature)
tool_request_inference(temperature=0.8, ...)
```

### Token Limits
Set appropriate limits:
```python
# Quick summary
tool_request_inference(max_tokens=100, ...)

# Detailed analysis
tool_request_inference(max_tokens=500, ...)

# Full generation
tool_request_inference(max_tokens=2000, ...)
```

### System Prompts
Use specific system prompts:
```python
# Code analysis
system_prompt="You are a senior software engineer reviewing code."

# Security audit
system_prompt="You are a security expert identifying vulnerabilities."

# Documentation
system_prompt="You are a technical writer creating clear documentation."
```

### Capabilities
Specify required capabilities:
```python
# Text-only
capabilities=["text"]

# Code understanding
capabilities=["text", "code"]

# Complex reasoning
capabilities=["text", "reasoning"]
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/model_gateway_bridge.py`
- L04 Models: `platform/src/L04_model_gateway/models/`
- L04 Gateway: `platform/src/L04_model_gateway/services/model_gateway.py`

## Related Services

- ModelGateway (L04) - Provides inference execution
- LLMRouter (L04) - Routes to appropriate model
- SemanticCache (L04) - Caches inference responses
- ToolExecutor (L03) - Executes AI-powered tools
- ToolComposer (L03) - Uses for LLM composition

---
*Generated: 2026-01-24 | Platform Services Documentation*
