# Service 22/44: ToolRegistry

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L03 (Tool Execution Layer) |
| **Module** | `L03_tool_execution.services.tool_registry` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL (pgvector), Ollama |
| **Category** | Tool Management / Registry |

## Role in Development Environment

The **ToolRegistry** maintains a catalog of available tools with semantic search capabilities. It provides:
- Tool registration and versioning (Gap G-001, G-002)
- Semantic search via pgvector + Ollama embeddings
- Tool deprecation workflow (Gap G-003)
- Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
- Category-based filtering and listing
- Tool manifest storage with version history

This is **the central tool catalog** - when agents need to discover, query, or register tools, ToolRegistry provides the database-backed storage with intelligent search capabilities.

## Data Model

### ToolCategory Enum
- `DATA_ACCESS` - Data retrieval tools
- `COMPUTATION` - Processing and calculation tools
- `EXTERNAL_API` - External service integrations
- `FILE_SYSTEM` - File operations
- `LLM_INTERACTION` - LLM-based tools

### DeprecationState Enum
- `ACTIVE` - Tool is available for use
- `DEPRECATED` - Tool still works but scheduled for removal
- `SUNSET` - Tool in sunset period (limited support)
- `REMOVED` - Tool no longer available

### SourceType Enum
- `MCP` - Model Context Protocol tool
- `OPENAPI` - OpenAPI-defined tool
- `LANGCHAIN` - LangChain tool
- `NATIVE` - Platform native tool

### ExecutionMode Enum
- `SYNC` - Synchronous execution only
- `ASYNC` - Asynchronous execution only
- `BOTH` - Supports both modes

### ToolDefinition Dataclass
- `tool_id: str` - Unique tool identifier
- `tool_name: str` - Human-readable name
- `description: str` - Tool description
- `category: ToolCategory` - Tool category
- `tags: List[str]` - Searchable tags
- `latest_version: str` - Current version
- `source_type: SourceType` - Tool source
- `source_metadata: Dict` - Source-specific metadata
- `deprecation_state: DeprecationState` - Lifecycle state
- `deprecation_date: datetime` - When deprecated (if applicable)
- `requires_approval: bool` - Needs user approval
- `default_timeout_seconds: int` - Default timeout
- `default_cpu_millicore_limit: int` - Default CPU limit
- `default_memory_mb_limit: int` - Default memory limit
- `required_permissions: Dict` - Permission requirements
- `result_schema: Dict` - JSON Schema for result validation
- `retry_policy: Dict` - Retry configuration
- `circuit_breaker_config: Dict` - Circuit breaker settings
- `description_embedding: List[float]` - 768-dim vector for semantic search

### ToolManifest Dataclass
- `tool_id: str` - Tool identifier
- `tool_name: str` - Tool name
- `version: str` - Semantic version
- `description: str` - Tool description
- `category: ToolCategory` - Category
- `parameters_schema: Dict` - JSON Schema for parameters
- `result_schema: Dict` - JSON Schema for results
- `permissions: ToolPermissions` - Permission requirements
- `execution_config: ExecutionConfig` - Execution settings
- `execution_mode: ExecutionMode` - Sync/async mode
- `estimated_duration_seconds: int` - Expected duration
- `progress_updates: bool` - Supports progress reporting

### ToolVersion Dataclass
- `version_id: UUID` - Unique version ID
- `tool_id: str` - Parent tool ID
- `version: str` - Semantic version (e.g., "2.1.0")
- `manifest: ToolManifest` - Full manifest
- `compatibility_range: str` - Compatible agent versions
- `release_notes: str` - Version notes
- `deprecated_in_favor_of: str` - Migration target
- `removed_at: datetime` - Removal timestamp

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `db_connection_string` | Required | PostgreSQL connection string |
| `ollama_base_url` | "http://localhost:11434" | Ollama API endpoint |
| `embedding_model` | "mistral:7b" | Ollama model for embeddings |
| `embedding_dimensions` | 768 | Vector dimensions |
| `semantic_search_threshold` | 0.7 | Cosine similarity threshold |

## API Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize database pool and schema |
| `close()` | Close connections |
| `register_tool(definition, manifest)` | Register new tool |
| `get_tool(tool_id)` | Get tool by ID |
| `list_tools(category, include_deprecated)` | List all tools |
| `semantic_search(query, limit, category)` | Semantic tool search |
| `generate_embedding(text)` | Generate embedding via Ollama |

## Use Cases in Your Workflow

### 1. Initialize Tool Registry
```python
from L03_tool_execution.services.tool_registry import ToolRegistry

registry = ToolRegistry(
    db_connection_string="postgresql://user:pass@localhost:5432/platform",
    ollama_base_url="http://localhost:11434",
    embedding_model="mistral:7b",
    embedding_dimensions=768,
    semantic_search_threshold=0.7
)

await registry.initialize()
# Creates tables: tool_definitions, tool_versions
# Creates indexes for category, deprecation_state, embeddings
```

### 2. Register a New Tool
```python
from L03_tool_execution.models import (
    ToolDefinition,
    ToolManifest,
    ToolCategory,
    SourceType,
    DeprecationState,
    ToolPermissions,
    ExecutionConfig
)

# Define the tool
tool_def = ToolDefinition(
    tool_id="read-file-v1",
    tool_name="Read",
    description="Read contents of a file from the filesystem",
    category=ToolCategory.FILE_SYSTEM,
    tags=["file", "read", "filesystem"],
    latest_version="1.0.0",
    source_type=SourceType.NATIVE,
    source_metadata={"module": "tools.filesystem.read"},
    deprecation_state=DeprecationState.ACTIVE,
    requires_approval=False,
    default_timeout_seconds=30,
    default_cpu_millicore_limit=100,
    default_memory_mb_limit=256
)

# Create manifest with parameter schema
manifest = ToolManifest(
    tool_id="read-file-v1",
    tool_name="Read",
    version="1.0.0",
    description="Read contents of a file from the filesystem",
    category=ToolCategory.FILE_SYSTEM,
    parameters_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to file"
            },
            "offset": {
                "type": "integer",
                "description": "Line offset to start reading"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum lines to read"
            }
        },
        "required": ["file_path"]
    },
    result_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "line_count": {"type": "integer"}
        }
    },
    permissions=ToolPermissions(
        filesystem=[{"path": "*", "mode": "read"}]
    )
)

# Register
success = await registry.register_tool(tool_def, manifest)
print(f"Registered: {success}")
```

### 3. Get Tool by ID
```python
# Retrieve tool definition
tool = await registry.get_tool("read-file-v1")

print(f"Tool: {tool.tool_name}")
print(f"Description: {tool.description}")
print(f"Category: {tool.category.value}")
print(f"Version: {tool.latest_version}")
print(f"Source: {tool.source_type.value}")
print(f"Timeout: {tool.default_timeout_seconds}s")
```

### 4. List Tools by Category
```python
from L03_tool_execution.models import ToolCategory

# List file system tools
fs_tools = await registry.list_tools(
    category=ToolCategory.FILE_SYSTEM,
    include_deprecated=False
)

print(f"Found {len(fs_tools)} file system tools:")
for tool in fs_tools:
    print(f"  - {tool.tool_name}: {tool.description[:50]}...")

# List all active tools
all_tools = await registry.list_tools(include_deprecated=False)
print(f"Total active tools: {len(all_tools)}")

# Include deprecated tools
all_with_deprecated = await registry.list_tools(include_deprecated=True)
print(f"Total tools (including deprecated): {len(all_with_deprecated)}")
```

### 5. Semantic Search for Tools
```python
# Find tools using natural language
results = await registry.semantic_search(
    query="read and write files on disk",
    limit=5,
    category=ToolCategory.FILE_SYSTEM
)

print(f"Found {len(results)} matching tools:")
for tool, similarity in results:
    print(f"  {tool.tool_name} (score: {similarity:.3f})")
    print(f"    {tool.description[:60]}...")

# Search across all categories
api_results = await registry.semantic_search(
    query="make HTTP requests to external APIs",
    limit=10
)

for tool, score in api_results:
    print(f"{score:.2f} - {tool.tool_name}: {tool.category.value}")
```

### 6. Generate Embeddings
```python
# Generate embedding for custom text
embedding = await registry.generate_embedding(
    "A tool that analyzes code for security vulnerabilities"
)

print(f"Embedding dimensions: {len(embedding)}")
print(f"Sample values: {embedding[:5]}")
```

### 7. Register MCP Tool
```python
# Register a Model Context Protocol tool
mcp_tool = ToolDefinition(
    tool_id="mcp-browser-navigate",
    tool_name="navigate",
    description="Navigate browser to a URL",
    category=ToolCategory.EXTERNAL_API,
    tags=["mcp", "browser", "navigation"],
    latest_version="1.2.0",
    source_type=SourceType.MCP,
    source_metadata={
        "server": "claude-in-chrome",
        "mcp_version": "1.0"
    }
)

mcp_manifest = ToolManifest(
    tool_id="mcp-browser-navigate",
    tool_name="navigate",
    version="1.2.0",
    description="Navigate browser to a URL",
    category=ToolCategory.EXTERNAL_API,
    parameters_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "tabId": {"type": "integer"}
        },
        "required": ["url", "tabId"]
    },
    permissions=ToolPermissions(
        network=[{"host": "*", "port": 443}]
    )
)

await registry.register_tool(mcp_tool, mcp_manifest)
```

### 8. Register Tool with Retry Policy
```python
from L03_tool_execution.models import RetryPolicy, CircuitBreakerConfig

# External API tool with resilience settings
api_tool = ToolDefinition(
    tool_id="github-api-v1",
    tool_name="GitHubAPI",
    description="Interact with GitHub REST API",
    category=ToolCategory.EXTERNAL_API,
    tags=["github", "api", "git"],
    latest_version="1.0.0",
    source_type=SourceType.OPENAPI,
    source_metadata={
        "openapi_spec": "https://api.github.com/openapi.json"
    },
    retry_policy={
        "max_attempts": 3,
        "base_delay_ms": 1000,
        "max_delay_ms": 30000,
        "retryable_errors": ["E3103", "E5001"]
    },
    circuit_breaker_config={
        "failure_rate_threshold": 50.0,
        "sliding_window_size": 100,
        "wait_duration_seconds": 60
    }
)
```

## Service Interactions

```
+------------------+
|  ToolRegistry    | <--- L03 Tool Execution Layer
|     (L03)        |
+--------+---------+
         |
   Depends on:
         |
+------------------+     +-------------------+
|   PostgreSQL     |     |     Ollama        |
|   (pgvector)     |     |   (Embeddings)    |
+------------------+     +-------------------+
         |
   Used by:
         |
+------------------+     +-------------------+
|  ToolExecutor    |     |  MCPToolBridge    |
|     (L03)        |     |      (L03)        |
+------------------+     +-------------------+
         |
         v
+------------------+
| AgentExecutor    |
|     (L02)        |
+------------------+
```

**Integration Points:**
- **PostgreSQL (pgvector)**: Stores tool definitions and embeddings
- **Ollama**: Generates semantic embeddings for search
- **ToolExecutor (L03)**: Resolves tool definitions for execution
- **MCPToolBridge (L03)**: Registers MCP tools
- **AgentExecutor (L02)**: Queries available tools for agents

## Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Tool definitions table
CREATE TABLE tool_definitions (
    tool_id VARCHAR(255) PRIMARY KEY,
    tool_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    tags TEXT[],
    latest_version VARCHAR(50) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_metadata JSONB,
    deprecation_state VARCHAR(20) DEFAULT 'active',
    deprecation_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    requires_approval BOOLEAN DEFAULT FALSE,
    default_timeout_seconds INTEGER DEFAULT 30,
    default_cpu_millicore_limit INTEGER DEFAULT 500,
    default_memory_mb_limit INTEGER DEFAULT 1024,
    required_permissions JSONB,
    result_schema JSONB,
    retry_policy JSONB,
    circuit_breaker_config JSONB,
    description_embedding VECTOR(768)
);

-- Tool versions table
CREATE TABLE tool_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id VARCHAR(255) REFERENCES tool_definitions(tool_id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    manifest JSONB NOT NULL,
    compatibility_range VARCHAR(100),
    release_notes TEXT,
    deprecated_in_favor_of VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP,
    UNIQUE(tool_id, version)
);

-- Indexes
CREATE INDEX idx_tool_category ON tool_definitions(category);
CREATE INDEX idx_tool_deprecation_state ON tool_definitions(deprecation_state);
CREATE INDEX idx_tool_description_embedding
    ON tool_definitions USING ivfflat (description_embedding vector_cosine_ops);
CREATE INDEX idx_tool_version_tool_id ON tool_versions(tool_id);
```

## Semantic Search Flow

```
1. Query Input
   ├── "find tools for reading files"
   │
   v
2. Generate Embedding
   ├── POST /api/embeddings to Ollama
   ├── Returns 768-dim vector
   │
   v
3. Vector Search (pgvector)
   ├── SELECT ... WHERE 1 - (embedding <=> query_vec) >= threshold
   ├── ORDER BY similarity DESC
   │
   v
4. Return Results
   ├── List of (ToolDefinition, similarity_score)
   └── Filtered by category if specified
```

## Error Codes (E3000-E3099)

| Code | Description | Retryable |
|------|-------------|-----------|
| E3001 | Tool not found | No |
| E3005 | Semantic search embedding generation failed | Yes |
| E3007 | Tool already registered (duplicate) | No |
| E3008 | Tool registration/listing failed (DB error) | Yes |

## Execution Examples

```python
# Complete tool registry workflow
registry = ToolRegistry(
    db_connection_string="postgresql://localhost/platform",
    ollama_base_url="http://localhost:11434",
    embedding_model="mistral:7b"
)

await registry.initialize()

# Register core tools
tools = [
    ("Read", "Read file contents", ToolCategory.FILE_SYSTEM),
    ("Edit", "Edit file contents", ToolCategory.FILE_SYSTEM),
    ("Write", "Write new file", ToolCategory.FILE_SYSTEM),
    ("Bash", "Execute shell command", ToolCategory.COMPUTATION),
    ("WebFetch", "Fetch web content", ToolCategory.EXTERNAL_API),
]

for name, desc, category in tools:
    tool_def = ToolDefinition(
        tool_id=f"{name.lower()}-v1",
        tool_name=name,
        description=desc,
        category=category,
        latest_version="1.0.0",
        source_type=SourceType.NATIVE
    )
    manifest = ToolManifest(
        tool_id=f"{name.lower()}-v1",
        tool_name=name,
        version="1.0.0",
        description=desc,
        category=category,
        parameters_schema={"type": "object", "properties": {}}
    )
    await registry.register_tool(tool_def, manifest)

# Search for tools
results = await registry.semantic_search("modify source code files")
print(f"Best match: {results[0][0].tool_name} (score: {results[0][1]:.2f})")

# List by category
fs_tools = await registry.list_tools(category=ToolCategory.FILE_SYSTEM)
print(f"File system tools: {[t.tool_name for t in fs_tools]}")

# Cleanup
await registry.close()
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Initialize (schema creation) | Complete |
| Register Tool | Complete |
| Get Tool | Complete |
| List Tools | Complete |
| Semantic Search | Complete |
| Embedding Generation | Complete |
| Category Filtering | Complete |
| Deprecation Filtering | Complete |
| pgvector Integration | Complete |
| Ollama Integration | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Update Tool | Medium | Update existing tool definition |
| Delete Tool | Medium | Remove tool from registry |
| Deprecate Tool | Medium | Transition tool through deprecation states |
| Version Management | Medium | Add/update tool versions |
| Permission Validation | Low | Validate required_permissions schema |
| Bulk Registration | Low | Register multiple tools at once |
| Export/Import | Low | Export registry to JSON/YAML |

## Strengths

- **Semantic search** - Natural language tool discovery
- **Protocol-agnostic** - Supports MCP, OpenAPI, LangChain, native
- **Version tracking** - Multiple versions per tool
- **Deprecation workflow** - Graceful tool retirement
- **pgvector integration** - Fast vector similarity search
- **Rich metadata** - Categories, tags, permissions, schemas

## Weaknesses

- **No update/delete** - Can only register new tools
- **No deprecation workflow** - State changes not implemented
- **No version management** - Only stores initial version
- **Ollama dependency** - Requires Ollama for embeddings
- **No caching** - Every search hits database
- **No bulk operations** - Single tool registration only

## Best Practices

### Tool ID Naming
Use consistent tool ID format:
```python
# Good: descriptive, versioned
ToolDefinition(tool_id="read-file-v1", ...)
ToolDefinition(tool_id="github-api-v2", ...)

# Avoid: ambiguous or unversioned
ToolDefinition(tool_id="read", ...)
ToolDefinition(tool_id="tool1", ...)
```

### Description Quality
Write searchable descriptions:
```python
# Good: specific, searchable
ToolDefinition(
    description="Read contents of a file from the local filesystem, "
                "supporting offset and limit for large files"
)

# Avoid: vague
ToolDefinition(description="File tool")
```

### Category Selection
Match category to primary function:
```python
# FILE_SYSTEM for local file operations
ToolCategory.FILE_SYSTEM

# EXTERNAL_API for HTTP/network operations
ToolCategory.EXTERNAL_API

# COMPUTATION for processing tasks
ToolCategory.COMPUTATION

# LLM_INTERACTION for LLM-based tools
ToolCategory.LLM_INTERACTION
```

### Search Threshold Tuning
Adjust threshold based on needs:
```python
# Strict matching (fewer results, higher quality)
ToolRegistry(semantic_search_threshold=0.8)

# Loose matching (more results, may include less relevant)
ToolRegistry(semantic_search_threshold=0.5)
```

## Source Files

- Service: `platform/src/L03_tool_execution/services/tool_registry.py`
- Models: `platform/src/L03_tool_execution/models/tool_definition.py`
- Error Codes: `platform/src/L03_tool_execution/models/error_codes.py`
- Spec: Section 3.3.1 and 5.1.1/5.1.2 of tool-execution-layer-specification

## Related Services

- ToolExecutor (L03) - Executes tools from registry
- ToolComposer (L03) - Composes tool workflows
- MCPToolBridge (L03) - Registers MCP tools
- ResultCache (L03) - Caches tool results
- AgentExecutor (L02) - Queries tools for agents

---
*Generated: 2026-01-24 | Platform Services Documentation*
