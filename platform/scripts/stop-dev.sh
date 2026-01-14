#!/bin/bash
# Stop development environment for agentic platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping development environment..."

# Stop MCP services via PM2
echo "Stopping MCP services..."
pm2 stop all 2>/dev/null || true
pm2 delete all 2>/dev/null || true

# Stop Docker services
echo "Stopping Docker containers..."
docker compose -f "$PLATFORM_DIR/docker-compose.unified.yml" down

echo ""
echo "Development environment stopped."
