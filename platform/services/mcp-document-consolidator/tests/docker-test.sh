#!/bin/bash
# MCP Document Consolidator - Docker E2E Test Runner
# This script copies the test file to the Docker container and runs it there.

set -e

CONTAINER="consolidator-server"
TEST_DIR="/app/tests"

echo "═══════════════════════════════════════════════════════════════"
echo "  MCP Document Consolidator - Docker E2E Tests"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "Error: Container ${CONTAINER} is not running!"
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "Container ${CONTAINER} is running."

# Copy test files to container
echo "Copying test files to container..."
docker cp tests/e2e-integration.mjs ${CONTAINER}:/app/tests/

# Run the tests inside the container
echo "Running E2E tests inside container..."
echo ""

docker exec -e NODE_ENV=production \
    -e POSTGRES_HOST=postgres \
    -e POSTGRES_PORT=5432 \
    -e POSTGRES_DB=consolidator \
    -e POSTGRES_USER=consolidator \
    -e POSTGRES_PASSWORD=consolidator_secret \
    -e NEO4J_URI=bolt://neo4j:7687 \
    -e NEO4J_USER=neo4j \
    -e NEO4J_PASSWORD=consolidator_secret \
    -e REDIS_HOST=redis \
    -e REDIS_PORT=6379 \
    -e OLLAMA_BASE_URL=http://ollama:11434 \
    -e OLLAMA_DEFAULT_MODEL=llama3.2:1b \
    -e EMBEDDING_MODEL=all-MiniLM-L6-v2 \
    ${CONTAINER} node /app/tests/e2e-integration.mjs

echo ""
echo "Tests completed."
