"""Interface components for L12 Natural Language Interface.

This package provides external interfaces for L12:
- HTTP API: FastAPI REST interface with 8 endpoints
- MCP Server: Model Context Protocol server with 6 tools
- MCP STDIO Server: Stdio-based MCP server for Claude CLI
- WebSocket Handler: Real-time event streaming (to be implemented)

Note: Imports are lazy to avoid dependency issues when only
the stdio server is needed (which has minimal dependencies).
"""


def create_app(*args, **kwargs):
    """Lazy import for create_app to avoid FastAPI dependency when not needed."""
    from .http_api import create_app as _create_app
    return _create_app(*args, **kwargs)


def get_app(*args, **kwargs):
    """Lazy import for get_app to avoid FastAPI dependency when not needed."""
    from .http_api import get_app as _get_app
    return _get_app(*args, **kwargs)


def MCPServer(*args, **kwargs):
    """Lazy import for MCPServer."""
    from .mcp_server import MCPServer as _MCPServer
    return _MCPServer(*args, **kwargs)


__all__ = [
    "create_app",
    "get_app",
    "MCPServer",
]
