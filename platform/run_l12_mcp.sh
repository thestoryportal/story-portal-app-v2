#!/bin/bash
# L12 MCP Server Launcher for Claude CLI
#
# This script ensures proper environment setup for the MCP server

cd "/Volumes/Extreme SSD/projects/story-portal-app/platform"

export PYTHONPATH="/Volumes/Extreme SSD/projects/story-portal-app/platform"
export L12_SESSION_TTL_SECONDS=3600
export L12_USE_SEMANTIC_MATCHING=false

# Run the MCP server
exec python3 -m src.L12_nl_interface.interfaces.mcp_server_stdio "$@"
