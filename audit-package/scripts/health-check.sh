#!/bin/bash

# =============================================================================
# Story Portal Platform - Quick Health Check
# =============================================================================
# Run this to verify services are running before starting the audit.
# =============================================================================

echo "=============================================="
echo "  Service Health Check"
echo "=============================================="
echo ""

# PostgreSQL
echo -n "PostgreSQL (5432): "
if pg_isready -h localhost -p 5432 &> /dev/null; then
    echo "✓ RUNNING"
else
    echo "✗ NOT RUNNING"
    echo "  Start with: docker start agentic-postgres"
fi

# Redis
echo -n "Redis (6379): "
if redis-cli ping &> /dev/null; then
    echo "✓ RUNNING"
else
    echo "✗ NOT RUNNING"
    echo "  Start with: docker start agentic-redis"
fi

# Ollama
echo -n "Ollama (11434): "
if curl -s http://localhost:11434/api/version &> /dev/null; then
    echo "✓ RUNNING"
else
    echo "✗ NOT RUNNING"
    echo "  Start with: ollama serve"
fi

# Docker
echo -n "Docker: "
if docker info &> /dev/null; then
    echo "✓ RUNNING"
    echo ""
    echo "Containers:"
    docker ps --format "  - {{.Names}}: {{.Status}}"
else
    echo "✗ NOT RUNNING"
    echo "  Start Docker Desktop or docker service"
fi

echo ""
echo "=============================================="

# Application layer check (optional)
echo ""
echo "Application Layers (optional):"
for port in 8001 8002 8003 8004 8005 8006 8007; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "  Port $port: ✓ HEALTHY"
    else
        echo "  Port $port: - not responding"
    fi
done

echo ""
