#!/usr/bin/env bash
# MCP Document Consolidator - Stable Startup Script
# This script loads environment variables and starts the MCP server

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a  # automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # stop automatically exporting
fi

# Ensure required environment variables are set with defaults
export NODE_ENV="${NODE_ENV:-production}"
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-agentic_platform}"
export POSTGRES_USER="${POSTGRES_USER:-postgres}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
export POSTGRES_SSL="${POSTGRES_SSL:-false}"
export NEO4J_ENABLED="${NEO4J_ENABLED:-false}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export OLLAMA_ENABLED="${OLLAMA_ENABLED:-true}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_DEFAULT_MODEL="${OLLAMA_DEFAULT_MODEL:-llama3.2:3b}"
export EMBEDDING_ENABLED="${EMBEDDING_ENABLED:-true}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-all-MiniLM-L6-v2}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export LOG_FORMAT="${LOG_FORMAT:-json}"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found in PATH" >&2
    exit 1
fi

# Check if the dist directory exists
if [ ! -d "$SCRIPT_DIR/dist" ]; then
    echo "Error: dist directory not found. Run 'npm run build' first." >&2
    exit 1
fi

# Check if the server file exists
if [ ! -f "$SCRIPT_DIR/dist/server.js" ]; then
    echo "Error: dist/server.js not found. Run 'npm run build' first." >&2
    exit 1
fi

# Log startup info to stderr (MCP uses stdout for protocol)
echo "Starting MCP Document Consolidator..." >&2
echo "Working directory: $SCRIPT_DIR" >&2
echo "Node version: $(node --version)" >&2
echo "Environment: $NODE_ENV" >&2
echo "Database: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" >&2
echo "Ollama: ${OLLAMA_ENABLED} (${OLLAMA_BASE_URL})" >&2
echo "Embedding: ${EMBEDDING_ENABLED} (${EMBEDDING_MODEL})" >&2

# Start the MCP server
exec node "$SCRIPT_DIR/dist/server.js"
