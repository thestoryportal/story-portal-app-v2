# Service 25/44: MCPToolBridge

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.mcp_tool_bridge` |
| **Status** | Partially Implemented (Bridges Pending) |
| **Dependencies** | L02 DocumentBridge, L02 SessionBridge (via HTTP) |
| **Category** | Tool Management / MCP Integration |

## Role in Development Environment

The **MCPToolBridge** integrates L03 tool execution with MCP servers for document context and state checkpointing. It provides:
- Document Bridge for Phase 15 integration (document-consolidator)
- State Bridge for Phase 16 checkpointing (context-orchestrator)
- MCP stdio transport (JSON-RPC 2.0)
- Unified document and checkpoint access for tools

This is **the MCP integration layer for tool execution** - when tools need to access authoritative documents or create checkpoints for resumability, MCPToolBridge provides the bridge to L02 runtime services.

**Note:** Current implementation requires HTTP client for L02 cross-container communication. Direct imports are placeholders.

## Data Model

### CheckpointType Enum
- `MICRO` - Redis, 30s intervals, 1-hour TTL
- `MACRO` - PostgreSQL, event milestones, 90-day retention
- `NAMED` - PostgreSQL, manual recovery points, indefinite retention

### TaskStatus Enum
- `PENDING` - Task queued but not started
- `RUNNING` - Task actively executing
- `COMPLETED` - Task finished successfully
- `FAILED` - Task encountered error
- `CANCELLED` - Task cancelled by client

### DocumentContext Dataclass
- `document_refs: List[str]` - Document IDs to access
- `version_pinning: bool` - Pin document versions during execution
- `query: str` - Semantic search query for documents

### Checkpoint Dataclass
- `checkpoint_id: UUID` - Unique checkpoint identifier
- `invocation_id: UUID` - Parent invocation
- `checkpoint_type: CheckpointType` - Type (micro/macro/named)
- `checkpoint_label: str` - For named checkpoints
- `parent_checkpoint_id: UUID` - For delta encoding
- `is_delta: bool` - Delta checkpoint flag
- `state: Dict` - Tool execution state
- `state_compressed: bytes` - Compressed state (if > 10 KB)
- `state_size_bytes: int` - State size
- `progress_percent: int` - Progress (0-100)
- `current_phase: str` - Current phase label
- `document_versions: Dict[str, str]` - Pinned document versions
- `expires_at: datetime` - TTL expiration
- `archived_at: datetime` - Glacier archive timestamp

### Task Dataclass (MCP Tasks)
- `id: str` - Task identifier (format: "task:{tool_id}:{invocation_id}")
- `status: TaskStatus` - Current status
- `progress: TaskProgress` - Progress information
- `result: Any` - Task result (when completed)
- `error: str` - Error message (when failed)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `document_server_enabled` | true | Enable document-consolidator integration |
| `context_server_enabled` | true | Enable context-orchestrator integration |
| `document_bridge_config` | None | DocumentBridge configuration |
| `session_bridge_config` | None | SessionBridge configuration |

## API Methods

### Document Bridge (Phase 15)

| Method | Description |
|--------|-------------|
| `get_document(document_id, version_pinning)` | Retrieve document content |
| `search_documents(query, limit)` | Semantic document search |
| `get_documents_for_tool(document_context)` | Get all documents for tool execution |

### State Bridge (Phase 16)

| Method | Description |
|--------|-------------|
| `create_checkpoint(checkpoint)` | Create checkpoint via context-orchestrator |
| `restore_checkpoint(checkpoint_id)` | Restore checkpoint |
| `save_context_snapshot(task_id, state)` | Save context snapshot |

### Lifecycle

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize MCP server connections |
| `close()` | Close MCP server connections |

## Use Cases in Your Workflow

### 1. Initialize MCP Tool Bridge
```python
from L03_tool_execution.services.mcp_tool_bridge import MCPToolBridge

bridge = MCPToolBridge(
    document_server_enabled=True,
    context_server_enabled=True,
    document_bridge_config={
        "mcp_server_path": "/path/to/document-consolidator",
        "cache_ttl": 300
    },
    session_bridge_config={
        "mcp_server_path": "/path/to/context-orchestrator",
        "checkpoint_interval": 30
    }
)

await bridge.initialize()
# Connects to document-consolidator and context-orchestrator MCP servers
```

### 2. Get Document for Tool Execution
```python
# Retrieve a specific document
document = await bridge.get_document(
    document_id="spec-modal-component-v1",
    version_pinning=True  # Pin version during execution
)

if document:
    print(f"Document: {document['title']}")
    print(f"Version: {document['version']}")
    print(f"Content: {document['content'][:100]}...")
```

### 3. Search Documents
```python
# Semantic search for relevant documents
results = await bridge.search_documents(
    query="modal component implementation patterns",
    limit=5
)

for doc in results:
    print(f"{doc['title']} (confidence: {doc['confidence']:.2f})")
    print(f"  {doc['content'][:80]}...")
```

### 4. Get Documents for Tool Execution Context
```python
from L03_tool_execution.models import DocumentContext

# Define document context for tool
document_context = DocumentContext(
    document_refs=["spec-modal-v1", "guide-accessibility"],
    version_pinning=True,
    query="animation best practices"  # Additional semantic search
)

# Get all relevant documents
documents = await bridge.get_documents_for_tool(document_context)

print(f"Found {len(documents)} documents:")
for doc in documents:
    print(f"  - {doc['document_id']}: {doc['title']}")
```

### 5. Create Checkpoint During Tool Execution
```python
from L03_tool_execution.models import Checkpoint, CheckpointType

# Create micro checkpoint (every 30s)
checkpoint = Checkpoint(
    invocation_id=request.invocation_id,
    checkpoint_type=CheckpointType.MICRO,
    state={
        "current_step": 5,
        "processed_files": ["a.tsx", "b.tsx"],
        "intermediate_results": {...}
    },
    progress_percent=50,
    current_phase="analyzing_imports"
)

checkpoint_id = await bridge.create_checkpoint(checkpoint)
print(f"Created checkpoint: {checkpoint_id}")
```

### 6. Create Named Checkpoint (Manual Recovery Point)
```python
# Create named checkpoint for manual recovery
named_checkpoint = Checkpoint(
    invocation_id=request.invocation_id,
    checkpoint_type=CheckpointType.NAMED,
    checkpoint_label="before-refactor-phase",  # Human-readable label
    state={
        "full_state": {...},
        "validation_passed": True
    },
    progress_percent=75,
    current_phase="pre_refactor",
    document_versions={
        "spec-modal-v1": "1.2.3",  # Pin document versions
        "guide-components": "2.0.0"
    }
)

checkpoint_id = await bridge.create_checkpoint(named_checkpoint)
print(f"Created named checkpoint: {named_checkpoint.checkpoint_label}")
```

### 7. Restore from Checkpoint
```python
# Resume tool execution from checkpoint
checkpoint = await bridge.restore_checkpoint(checkpoint_id="abc123")

if checkpoint:
    print(f"Restored checkpoint type: {checkpoint.checkpoint_type.value}")
    print(f"Progress: {checkpoint.progress_percent}%")
    print(f"State keys: {list(checkpoint.state.keys())}")

    # Resume execution from saved state
    resume_from_state(checkpoint.state)
else:
    print("Checkpoint not found - starting fresh")
```

### 8. Save Context Snapshot
```python
# Save current context for session continuity
await bridge.save_context_snapshot(
    task_id="task-001",
    state={
        "status": "in_progress",
        "current_file": "/src/modal.tsx",
        "changes_made": ["added animation", "fixed accessibility"],
        "next_steps": ["run tests", "update docs"]
    },
    sync_to_file=True  # Also sync to .claude/contexts
)
```

### 9. Tool Execution with Document and Checkpoint Integration
```python
from L03_tool_execution.models import (
    ToolInvokeRequest,
    DocumentContext,
    CheckpointConfig
)

# Create request with document context and checkpointing
request = ToolInvokeRequest(
    tool_id="Analyze",
    parameters={"path": "/project/src"},
    document_context=DocumentContext(
        document_refs=["style-guide"],
        query="code quality metrics"
    ),
    checkpoint_config=CheckpointConfig(
        enable_checkpointing=True,
        interval_seconds=30,  # Micro checkpoints every 30s
        resume_from=None  # Or checkpoint_id to resume
    )
)

# Get documents before execution
documents = await bridge.get_documents_for_tool(request.document_context)

# Execute tool (simplified)
result = await execute_tool(request, documents=documents)

# Create final checkpoint
final_checkpoint = Checkpoint(
    invocation_id=request.invocation_id,
    checkpoint_type=CheckpointType.MACRO,
    state={"result": result, "status": "completed"},
    progress_percent=100
)
await bridge.create_checkpoint(final_checkpoint)
```

## Service Interactions

```
+------------------+
|  MCPToolBridge   | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Connects to (via L02):
         |
+------------------+     +-------------------+
| DocumentBridge   |     |  SessionBridge    |
|     (L02)        |     |      (L02)        |
+------------------+     +-------------------+
         |                         |
         v                         v
+------------------+     +-------------------+
| document-        |     | context-          |
| consolidator MCP |     | orchestrator MCP  |
+------------------+     +-------------------+
```

**Integration Points:**
- **DocumentBridge (L02)**: Provides document access via document-consolidator MCP
- **SessionBridge (L02)**: Provides context/checkpoint via context-orchestrator MCP
- **ToolExecutor (L03)**: Uses for document context and checkpointing
- **ToolComposer (L03)**: Integrates for workflow checkpoints

## Phase 15: Document Integration

```
Tool Execution Request
        │
        ├── document_context
        │       ├── document_refs: ["spec-v1", "guide"]
        │       ├── version_pinning: true
        │       └── query: "implementation patterns"
        │
        v
MCPToolBridge.get_documents_for_tool()
        │
        ├── get_document("spec-v1") ──> DocumentBridge ──> MCP
        ├── get_document("guide") ──> DocumentBridge ──> MCP
        └── search_documents("patterns") ──> DocumentBridge ──> MCP
        │
        v
Documents returned with pinned versions
```

## Phase 16: Checkpoint Integration

```
Checkpoint Strategy (Hybrid)
        │
        ├── MICRO (Redis)
        │       ├── Interval: 30 seconds
        │       ├── TTL: 1 hour
        │       └── Fast recovery
        │
        ├── MACRO (PostgreSQL)
        │       ├── Event-based milestones
        │       ├── Retention: 90 days
        │       └── Durable recovery
        │
        └── NAMED (PostgreSQL)
                ├── Manual recovery points
                ├── Retention: Indefinite
                └── Human-labeled
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E3501 | Document retrieval failed | Yes |
| E3601 | Checkpoint creation failed | Yes |
| E3602 | Checkpoint restoration failed | Yes |

## Execution Examples

```python
# Complete MCP bridge workflow
bridge = MCPToolBridge(
    document_server_enabled=True,
    context_server_enabled=True
)

await bridge.initialize()

# Phase 15: Document access
documents = await bridge.search_documents(
    query="component architecture patterns",
    limit=3
)

for doc in documents:
    full_doc = await bridge.get_document(doc['document_id'])
    print(f"Loaded: {full_doc['title']} v{full_doc['version']}")

# Phase 16: Checkpointing workflow
from L03_tool_execution.models import Checkpoint, CheckpointType

# Create micro checkpoint during execution
micro = Checkpoint(
    checkpoint_type=CheckpointType.MICRO,
    state={"step": 1, "data": {...}},
    progress_percent=25
)
await bridge.create_checkpoint(micro)

# Create macro checkpoint at milestone
macro = Checkpoint(
    checkpoint_type=CheckpointType.MACRO,
    state={"completed_phases": ["init", "analyze"]},
    progress_percent=50,
    current_phase="transform"
)
await bridge.create_checkpoint(macro)

# Create named checkpoint before risky operation
named = Checkpoint(
    checkpoint_type=CheckpointType.NAMED,
    checkpoint_label="pre-database-migration",
    state={"full_backup": True, "validation": "passed"},
    progress_percent=75
)
await bridge.create_checkpoint(named)

# Restore if needed
restored = await bridge.restore_checkpoint(str(named.checkpoint_id))
if restored:
    print(f"Restored: {restored.checkpoint_label}")

# Cleanup
await bridge.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize | Complete |
| Close | Complete |
| Get Document | Complete (pending L02 bridge) |
| Search Documents | Complete (pending L02 bridge) |
| Get Documents for Tool | Complete |
| Create Checkpoint | Complete (pending L02 bridge) |
| Restore Checkpoint | Complete (pending L02 bridge) |
| Save Context Snapshot | Complete (pending L02 bridge) |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| L02 HTTP Client | High | HTTP-based L02 communication |
| DocumentBridge Integration | High | Full MCP document access |
| SessionBridge Integration | High | Full MCP checkpoint access |
| Delta Encoding | Medium | Implement Gap G-015 |
| Compression | Medium | Implement Gap G-016 |
| S3 Glacier Archive | Low | Archive old checkpoints |
| Metrics Export | Low | Checkpoint/document metrics |

## Strengths

- **Phase 15/16 ready** - Document and checkpoint integration
- **Hybrid checkpointing** - Micro, macro, named strategy
- **Version pinning** - Consistent document versions
- **MCP-aligned** - Standard MCP Tasks abstraction
- **Graceful degradation** - Works without L02 bridges

## Weaknesses

- **L02 bridges pending** - Requires HTTP client implementation
- **No delta encoding** - Full state in every checkpoint
- **No compression** - Large states stored uncompressed
- **No archival** - Old checkpoints not archived
- **Single server** - No MCP server failover

## Best Practices

### Document Context Configuration
```python
# Explicit document references for known docs
DocumentContext(
    document_refs=["spec-modal-v1", "style-guide"],
    version_pinning=True  # Always pin in production
)

# Semantic search for dynamic discovery
DocumentContext(
    query="accessibility modal patterns",
    version_pinning=True
)

# Combined approach
DocumentContext(
    document_refs=["required-spec"],
    query="optional context",
    version_pinning=True
)
```

### Checkpoint Strategy Selection
```python
# Micro: Frequent, ephemeral (long-running tools)
Checkpoint(checkpoint_type=CheckpointType.MICRO)

# Macro: Milestones (phase transitions)
Checkpoint(checkpoint_type=CheckpointType.MACRO)

# Named: Recovery points (before risky operations)
Checkpoint(
    checkpoint_type=CheckpointType.NAMED,
    checkpoint_label="before-database-migration"
)
```

### Error Handling
```python
try:
    document = await bridge.get_document(doc_id)
except ToolExecutionError as e:
    if e.code == ErrorCode.E3501:
        # Document not found - use fallback
        document = await get_default_document()
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/mcp_tool_bridge.py`
- Models: `platform/src/L03_tool_execution/models/checkpoint_models.py`
- Document Context: `platform/src/L03_tool_execution/models/tool_result.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: ADR-001 (stdio transport), Phase 15/16 specifications

## Related Services

- DocumentBridge (L02) - MCP document access
- SessionBridge (L02) - MCP context/checkpoint access
- ToolExecutor (L03) - Uses for tool execution
- ToolComposer (L03) - Uses for workflow checkpoints
- StateManager (L02) - Alternative checkpoint storage
- ContextOrchestrator (MCP) - Higher-level context management

---
*Generated: 2026-01-24 | Platform Services Documentation*
