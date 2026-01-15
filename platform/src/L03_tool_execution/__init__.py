"""
L03 Tool Execution Layer

This module provides secure, isolated execution of tools invoked by AI agents.
Based on tool-execution-layer-specification-v1.2-ASCII.md

Key Features:
- Tool registry with semantic search (pgvector)
- Nested sandbox execution (BC-1)
- Permission enforcement (JWT + OPA)
- External API management with circuit breakers
- MCP integration for documents (Phase 15) and checkpoints (Phase 16)
- Comprehensive observability and audit logging
"""

from .models import (
    ToolDefinition,
    ToolVersion,
    ToolManifest,
    ToolResult,
    ToolInvokeRequest,
    ToolInvokeResponse,
    ExecutionContext,
    ResourceLimits,
    SandboxConfig,
    Checkpoint,
    CheckpointConfig,
)

from .services import (
    ToolRegistry,
    ToolExecutor,
    ToolSandbox,
    ResultCache,
    MCPToolBridge,
    ToolComposer,
)

__version__ = "1.0.0"

__all__ = [
    # Models
    "ToolDefinition",
    "ToolVersion",
    "ToolManifest",
    "ToolResult",
    "ToolInvokeRequest",
    "ToolInvokeResponse",
    "ExecutionContext",
    "ResourceLimits",
    "SandboxConfig",
    "Checkpoint",
    "CheckpointConfig",
    # Services
    "ToolRegistry",
    "ToolExecutor",
    "ToolSandbox",
    "ResultCache",
    "MCPToolBridge",
    "ToolComposer",
]
