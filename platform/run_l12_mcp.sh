#!/bin/bash
# L12 MCP Server Launcher for Claude CLI
#
# This script ensures proper environment setup for the MCP server

cd "/Volumes/Extreme SSD/projects/story-portal-app/platform"

export PYTHONPATH="/Volumes/Extreme SSD/projects/story-portal-app/platform"

# Session Management
export L12_SESSION_TTL_SECONDS=3600

# Semantic Matching (requires Ollama running on localhost:11434)
# Set to true to enable embedding-based similarity search
export L12_USE_SEMANTIC_MATCHING=false

# Redis Configuration (for WebSocket and Command History)
# Ensure Redis is running before enabling these features
export L12_REDIS_HOST=localhost
export L12_REDIS_PORT=6379

# Run the MCP server
exec python3 -m src.L12_nl_interface.interfaces.mcp_server_stdio "$@"
