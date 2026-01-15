"""Interface components for L12 Natural Language Interface.

This package provides external interfaces for L12:
- HTTP API: FastAPI REST interface with 6 endpoints
- MCP Server: Model Context Protocol server with 6 tools
- WebSocket Handler: Real-time event streaming (to be implemented)
"""

from .http_api import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]
