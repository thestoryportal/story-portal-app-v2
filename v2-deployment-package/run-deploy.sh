#!/bin/bash

# =============================================================================
# Story Portal Platform V2 - One-Command Deployment Launcher
# =============================================================================
# This script launches the autonomous V2 deployment using Claude Code CLI.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_PROMPT="$SCRIPT_DIR/MASTER-DEPLOYMENT-PROMPT.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}  STORY PORTAL PLATFORM V2 - AUTONOMOUS DEPLOYMENT${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

PREREQ_FAILED=0

echo "Checking prerequisites..."
echo ""

# Check Claude Code CLI
if command -v claude &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Claude Code CLI installed"
else
    echo -e "  ${RED}✗${NC} Claude Code CLI NOT installed"
    echo ""
    echo "    Install with:"
    echo "      Mac:     brew install anthropic/tap/claude-code"
    echo "      Windows: winget install Anthropic.ClaudeCode"
    echo "      Linux:   curl -fsSL https://claude.ai/install.sh | sh"
    PREREQ_FAILED=1
fi

# Check Docker
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker running"
else
    echo -e "  ${RED}✗${NC} Docker NOT running"
    echo "    Start Docker Desktop and try again"
    PREREQ_FAILED=1
fi

# Check Ollama
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Ollama running"
else
    echo -e "  ${YELLOW}!${NC} Ollama not running (will attempt to start)"
fi

# Check deployment prompt exists
if [ -f "$DEPLOY_PROMPT" ]; then
    echo -e "  ${GREEN}✓${NC} Deployment prompt found"
else
    echo -e "  ${RED}✗${NC} Deployment prompt NOT found at:"
    echo "    $DEPLOY_PROMPT"
    PREREQ_FAILED=1
fi

echo ""

if [ $PREREQ_FAILED -eq 1 ]; then
    echo -e "${RED}Prerequisites not met. Please fix the issues above and try again.${NC}"
    exit 1
fi

# =============================================================================
# NAVIGATE TO PROJECT ROOT
# =============================================================================

# Go to parent directory (story-portal-app-v2 root)
cd "$SCRIPT_DIR/.." || {
    echo -e "${RED}Cannot navigate to project root${NC}"
    exit 1
}

PROJECT_ROOT=$(pwd)
echo "Working directory: $PROJECT_ROOT"
echo ""

# Verify we're in the right place
if [ ! -d "./platform" ]; then
    echo -e "${YELLOW}Warning: 'platform' directory not found.${NC}"
    echo "Make sure you're in the story-portal-app-v2 root directory."
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# =============================================================================
# PRE-DEPLOYMENT SETUP
# =============================================================================

echo "Setting up deployment environment..."

# Create output directories
mkdir -p ./v2-deployment/{logs,configs,scripts,evidence,reports}

# Try to start Ollama if not running
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve &> ./v2-deployment/logs/ollama.log &
    sleep 5
fi

# =============================================================================
# LAUNCH DEPLOYMENT
# =============================================================================

echo ""
echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}  STARTING AUTONOMOUS DEPLOYMENT${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""
echo "This will deploy:"
echo "  • PostgreSQL + Redis + Ollama infrastructure"
echo "  • All 10 application layers (L01-L11)"
echo "  • Platform CLI tool"
echo "  • 5-agent development swarm"
echo "  • Prometheus + Grafana monitoring"
echo "  • Backup scripts"
echo ""
echo -e "${YELLOW}Estimated time: 45-90 minutes${NC}"
echo ""
echo "The deployment runs autonomously. You can leave it running."
echo ""
echo "Press Ctrl+C to cancel, or wait 10 seconds to begin..."
echo ""

# Countdown
for i in {10..1}; do
    echo -ne "\rStarting in $i seconds... "
    sleep 1
done
echo -e "\rStarting deployment...          "
echo ""

# Record start time
START_TIME=$(date +%s)
echo "Deployment started at $(date)" > ./v2-deployment/logs/deployment.log

# =============================================================================
# EXECUTE DEPLOYMENT VIA CLAUDE CODE CLI
# =============================================================================

# Method: Start Claude interactively with the prompt file
# This avoids shell buffer issues with large prompts

echo "Launching Claude Code CLI..."
echo ""

# Create a simple instruction file that tells Claude to read the main prompt
cat > ./v2-deployment/configs/deploy-instruction.txt << 'INSTEOF'
Read and execute the deployment instructions in v2-deployment-package/MASTER-DEPLOYMENT-PROMPT.md

Execute ALL phases autonomously without stopping for confirmation:
- Phase 0: Initialization
- Phase 1: Infrastructure Verification
- Phase 2: Database Initialization
- Phase 3: Application Services Deployment
- Phase 4: Service Health Verification
- Phase 5: CLI Tooling Creation
- Phase 6: Multi-Agent Deployment
- Phase 7: Backup Configuration
- Phase 8: Final Report

Continue even if individual steps fail - log errors and proceed.
Save all outputs to the v2-deployment/ directory.
Generate a final deployment summary when complete.
INSTEOF

# Launch Claude with the instruction
claude "$(cat ./v2-deployment/configs/deploy-instruction.txt)"

# =============================================================================
# POST-DEPLOYMENT
# =============================================================================

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}  DEPLOYMENT PROCESS COMPLETE${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo "Duration: ${MINUTES}m ${SECONDS}s"
echo ""
echo "Next steps:"
echo "  1. Check service status:  ./platform-cli/portal status"
echo "  2. View dashboard:        http://localhost:8010"
echo "  3. View monitoring:       http://localhost:3000 (admin/admin)"
echo ""
echo "Reports saved to: ./v2-deployment/reports/"
echo "Logs saved to:    ./v2-deployment/logs/"
echo ""
