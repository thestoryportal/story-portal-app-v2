#!/usr/bin/env bash
# MCP Document Consolidator - Health Check Script
# Verifies all dependencies and configuration are correct

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== MCP Document Consolidator Health Check ==="
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

FAILED=0

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass "Node.js found: $NODE_VERSION"

    # Check version
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
    if [ "$NODE_MAJOR" -ge 20 ]; then
        pass "Node.js version >= 20 (required)"
    else
        fail "Node.js version must be >= 20 (found: $NODE_VERSION)"
        FAILED=1
    fi
else
    fail "Node.js not found in PATH"
    FAILED=1
fi
echo

# Check npm/node_modules
echo "Checking dependencies..."
if [ -d "$SCRIPT_DIR/node_modules" ]; then
    pass "node_modules directory exists"
else
    fail "node_modules not found. Run: npm install"
    FAILED=1
fi
echo

# Check build artifacts
echo "Checking build..."
if [ -d "$SCRIPT_DIR/dist" ]; then
    pass "dist directory exists"

    if [ -f "$SCRIPT_DIR/dist/server.js" ]; then
        pass "dist/server.js exists"
    else
        fail "dist/server.js not found. Run: npm run build"
        FAILED=1
    fi
else
    fail "dist directory not found. Run: npm run build"
    FAILED=1
fi
echo

# Check .env file
echo "Checking environment configuration..."
if [ -f "$SCRIPT_DIR/.env" ]; then
    pass ".env file exists"

    # Check required variables
    source "$SCRIPT_DIR/.env" 2>/dev/null || true

    if [ -n "${POSTGRES_PASSWORD:-}" ]; then
        pass "POSTGRES_PASSWORD is set"
    else
        warn "POSTGRES_PASSWORD not set in .env"
    fi

    if [ -n "${POSTGRES_HOST:-}" ]; then
        pass "POSTGRES_HOST is set: $POSTGRES_HOST"
    else
        warn "POSTGRES_HOST not set in .env"
    fi
else
    fail ".env file not found. Copy from .env.example"
    FAILED=1
fi
echo

# Check startup script
echo "Checking startup script..."
if [ -f "$SCRIPT_DIR/start-mcp.sh" ]; then
    pass "start-mcp.sh exists"

    if [ -x "$SCRIPT_DIR/start-mcp.sh" ]; then
        pass "start-mcp.sh is executable"
    else
        fail "start-mcp.sh is not executable. Run: chmod +x start-mcp.sh"
        FAILED=1
    fi
else
    fail "start-mcp.sh not found"
    FAILED=1
fi
echo

# Check PostgreSQL connection (optional)
echo "Checking PostgreSQL connection..."
source "$SCRIPT_DIR/.env" 2>/dev/null || true
PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-agentic_platform}"

if command -v psql &> /dev/null; then
    if PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" &> /dev/null; then
        pass "PostgreSQL connection successful"
    else
        warn "Cannot connect to PostgreSQL at $PG_HOST:$PG_PORT/$PG_DB"
        warn "Server may not work without database"
    fi
else
    warn "psql not found - skipping database connection test"
fi
echo

# Check Ollama (optional)
echo "Checking Ollama..."
source "$SCRIPT_DIR/.env" 2>/dev/null || true
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

if command -v curl &> /dev/null; then
    if curl -s "$OLLAMA_URL/api/version" &> /dev/null; then
        pass "Ollama is running at $OLLAMA_URL"
    else
        warn "Ollama not responding at $OLLAMA_URL"
        warn "LLM features will use mock implementation"
    fi
else
    warn "curl not found - skipping Ollama check"
fi
echo

# Check Python/Embedding (optional)
echo "Checking Python embedding service..."
source "$SCRIPT_DIR/.env" 2>/dev/null || true
PYTHON_PATH="${PYTHON_PATH:-python3}"

if [ -f "$PYTHON_PATH" ]; then
    if [ -x "$PYTHON_PATH" ]; then
        pass "Python found at: $PYTHON_PATH"
        PYTHON_VERSION=$("$PYTHON_PATH" --version 2>&1)
        pass "Python version: $PYTHON_VERSION"
    else
        warn "Python at $PYTHON_PATH is not executable"
    fi
else
    warn "Python not found at: $PYTHON_PATH"
    warn "Embedding features will use simple fallback"
fi
echo

# Check MCP configuration
echo "Checking MCP configuration..."
MCP_CONFIG="$HOME/.claude/mcp.json"
if [ -f "$MCP_CONFIG" ]; then
    pass "MCP config found at $MCP_CONFIG"

    if grep -q "document-consolidator" "$MCP_CONFIG"; then
        pass "document-consolidator is registered in MCP config"
    else
        fail "document-consolidator not found in $MCP_CONFIG"
        fail "Add server configuration to enable in Claude Code"
        FAILED=1
    fi
else
    fail "MCP config not found at $MCP_CONFIG"
    FAILED=1
fi
echo

# Summary
echo "=== Health Check Summary ==="
if [ $FAILED -eq 0 ]; then
    pass "All critical checks passed!"
    echo
    echo "The MCP Document Consolidator is ready to use."
    echo "Restart Claude Code to load the server."
    exit 0
else
    fail "Some critical checks failed"
    echo
    echo "Please fix the issues above before using the server."
    exit 1
fi
