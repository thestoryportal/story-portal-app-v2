#!/usr/bin/env bash
# MCP Document Consolidator - Simple Monitor Script
# Checks if dependencies are available before allowing the server to start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to check if PostgreSQL is accessible
check_postgres() {
    source "$SCRIPT_DIR/.env" 2>/dev/null || true
    PG_HOST="${POSTGRES_HOST:-localhost}"
    PG_PORT="${POSTGRES_PORT:-5432}"
    PG_USER="${POSTGRES_USER:-postgres}"
    PG_DB="${POSTGRES_DB:-agentic_platform}"

    # Try to connect using node (no psql dependency needed)
    node -e "
        const { Client } = require('pg');
        const client = new Client({
            host: '$PG_HOST',
            port: $PG_PORT,
            user: '$PG_USER',
            password: process.env.POSTGRES_PASSWORD,
            database: '$PG_DB'
        });
        client.connect()
            .then(() => client.query('SELECT 1'))
            .then(() => {
                console.log('PostgreSQL connection: OK');
                client.end();
                process.exit(0);
            })
            .catch(err => {
                console.error('PostgreSQL connection: FAILED -', err.message);
                process.exit(1);
            });
    " 2>&1
}

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

echo "Checking dependencies..." >&2

# Check build exists
if [ ! -f "$SCRIPT_DIR/dist/server.js" ]; then
    echo "ERROR: Server not built. Run: npm run build" >&2
    exit 1
fi

# Check database connection
echo "Testing PostgreSQL connection..." >&2
if check_postgres; then
    echo "All dependency checks passed." >&2
else
    echo "WARNING: PostgreSQL connection failed. Server may not work correctly." >&2
    echo "         Continuing anyway (server has fallback handling)..." >&2
fi

# Start the server using the main startup script
exec "$SCRIPT_DIR/start-mcp.sh"
