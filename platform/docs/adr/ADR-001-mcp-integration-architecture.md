# ADR-001: MCP Integration Architecture

**Status:** Accepted

**Date:** January 14, 2025

## Context

The agentic platform requires robust document management and context persistence capabilities to support long-running agent operations. Agents need to:

- Access and consolidate documents across multiple repositories and sources
- Maintain persistent context across sessions and crashes
- Recover gracefully from failures without losing work
- Integrate seamlessly with Claude Code's native tooling

## Decision

We will implement MCP (Model Context Protocol) based integration using stdio transport with two core services:

### Phase 15: Document Consolidator
- Handles document ingestion, storage, and retrieval
- Provides semantic search and overlap detection
- Manages document metadata and relationships

### Phase 16: Context Orchestrator
- Manages agent context and state persistence
- Provides checkpoint and recovery mechanisms
- Handles context versioning and history

## Integration Points

The MCP services integrate with:

- **Data Layer v4.0**: Core data access and business logic
- **PostgreSQL**: Primary data store with pgvector extension for embeddings
- **Redis**: Caching layer for frequently accessed contexts
- **Ollama**: Local embedding generation for semantic search

## Architecture

```
Claude Code (Native MCP Client)
    |
    ├─> document-consolidator (stdio)
    |   └─> Data Layer v4.0
    |       └─> PostgreSQL + pgvector
    |
    └─> context-orchestrator (stdio)
        └─> Data Layer v4.0
            ├─> PostgreSQL (persistent context)
            └─> Redis (cached context)
```

## Consequences

### Positive

- **Native Tool Access**: Claude Code can directly invoke MCP tools without custom integration
- **Persistent Context**: Agent state survives crashes and can be resumed
- **Crash Recovery**: Checkpoint mechanism enables graceful recovery from failures
- **Standardized Protocol**: MCP is a well-defined protocol with broad support
- **Isolation**: Each service runs in its own process with clear boundaries

### Negative

- **Stdio Complexity**: Managing stdio transport requires careful process handling
- **Serialization Overhead**: JSON-RPC adds serialization/deserialization overhead
- **Process Management**: Must handle process lifecycle, crashes, and restarts
- **Debugging Complexity**: Distributed system makes debugging more challenging

## Implementation Notes

- MCP servers configured in `.mcp.json` at project root
- Services communicate via JSON-RPC 2.0 over stdio
- Data Layer v4.0 provides shared business logic for both services
- PostgreSQL handles all persistent storage
- Redis provides performance optimization for hot data
