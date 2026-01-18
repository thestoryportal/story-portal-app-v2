#!/bin/bash

# =============================================================================
# Story Portal Platform Audit - Setup Script
# =============================================================================
# This script prepares the environment for running the audit.
# Run this BEFORE running the audit if you want to verify prerequisites.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  Story Portal Platform Audit - Setup"
echo "=============================================="
echo ""

# Track failures
PREREQ_FAILED=0

# Function to check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}[✗]${NC} $1 is NOT installed"
        return 1
    fi
}

# Function to check service
check_service() {
    local name=$1
    local check_cmd=$2
    if eval "$check_cmd" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $name is running"
        return 0
    else
        echo -e "${YELLOW}[!]${NC} $name is not running (optional for audit)"
        return 0  # Don't fail for optional services
    fi
}

echo "Checking prerequisites..."
echo ""

# Required tools
echo "--- Required Tools ---"
check_command "claude" || PREREQ_FAILED=$((PREREQ_FAILED + 1))
check_command "docker" || PREREQ_FAILED=$((PREREQ_FAILED + 1))
check_command "python3" || PREREQ_FAILED=$((PREREQ_FAILED + 1))
check_command "bash" || PREREQ_FAILED=$((PREREQ_FAILED + 1))

echo ""
echo "--- Optional Tools (enhance audit) ---"
check_command "git" || true
check_command "jq" || true
check_command "psql" || true
check_command "redis-cli" || true
check_command "curl" || true
check_command "pm2" || true

echo ""
echo "--- Services ---"
check_service "Docker" "docker info"
check_service "PostgreSQL" "pg_isready -h localhost -p 5432"
check_service "Redis" "redis-cli ping"
check_service "Ollama" "curl -s http://localhost:11434/api/version"

echo ""
echo "--- Directory Structure ---"

# Check we're in the right place
if [ -d "./platform" ]; then
    echo -e "${GREEN}[✓]${NC} platform/ directory found"
else
    echo -e "${RED}[✗]${NC} platform/ directory NOT found"
    echo "    Make sure you run this from the story-portal-app-v2 root"
    PREREQ_FAILED=$((PREREQ_FAILED + 1))
fi

if [ -f "./audit-package/MASTER-AUDIT-PROMPT.md" ]; then
    echo -e "${GREEN}[✓]${NC} MASTER-AUDIT-PROMPT.md found"
else
    echo -e "${RED}[✗]${NC} MASTER-AUDIT-PROMPT.md NOT found"
    PREREQ_FAILED=$((PREREQ_FAILED + 1))
fi

echo ""
echo "--- Creating Output Directories ---"
mkdir -p ./audit/{findings,reports,checkpoints,evidence,logs,consolidated}
echo -e "${GREEN}[✓]${NC} Output directories created"

echo ""
echo "=============================================="
if [ $PREREQ_FAILED -eq 0 ]; then
    echo -e "${GREEN}  Setup Complete - Ready to Audit${NC}"
    echo "=============================================="
    echo ""
    echo "Next step: Run the audit with:"
    echo ""
    echo '  claude --print "$(cat audit-package/MASTER-AUDIT-PROMPT.md)"'
    echo ""
else
    echo -e "${RED}  Setup Incomplete - $PREREQ_FAILED issues found${NC}"
    echo "=============================================="
    echo ""
    echo "Please fix the issues above before running the audit."
    echo ""
    exit 1
fi
