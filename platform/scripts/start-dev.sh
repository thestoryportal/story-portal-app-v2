#!/bin/bash
# Start development environment for agentic platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting development environment..."

# Start Docker services (PostgreSQL + Redis)
echo "Starting Docker containers..."
docker compose -f "$PLATFORM_DIR/docker-compose.unified.yml" up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 5

# Check PostgreSQL
until docker exec agentic-postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "PostgreSQL is ready."

# Check Redis
until docker exec agentic-redis redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done
echo "Redis is ready."

# Start MCP services via PM2
echo "Starting MCP services..."
pm2 start "$PLATFORM_DIR/ecosystem.config.js"

echo ""
echo "Development environment started!"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - MCP services: pm2 status"
