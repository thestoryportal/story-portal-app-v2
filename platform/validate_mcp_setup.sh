#!/bin/bash
# Post-Restart Validation Script for L12 MCP Server
#
# Run this after restarting Claude CLI to verify everything is set up correctly

echo "======================================================================"
echo "L12 MCP Server - Post-Restart Validation"
echo "======================================================================"
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

checks_passed=0
checks_total=0

# Check 1: Config file exists and has l12-platform
echo "Check 1: Claude CLI configuration"
checks_total=$((checks_total + 1))
if grep -q '"l12-platform"' ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} L12 MCP server found in configuration"
    checks_passed=$((checks_passed + 1))
else
    echo -e "  ${RED}✗${NC} L12 MCP server NOT found in configuration"
    echo "  → Check ~/Library/Application Support/Claude/claude_desktop_config.json"
fi
echo

# Check 2: Launcher script exists and is executable
echo "Check 2: Launcher script"
checks_total=$((checks_total + 1))
if [ -x "/Volumes/Extreme SSD/projects/story-portal-app/platform/run_l12_mcp.sh" ]; then
    echo -e "  ${GREEN}✓${NC} Launcher script exists and is executable"
    checks_passed=$((checks_passed + 1))
else
    echo -e "  ${RED}✗${NC} Launcher script missing or not executable"
    echo "  → Run: chmod +x /Volumes/Extreme\ SSD/projects/story-portal-app/platform/run_l12_mcp.sh"
fi
echo

# Check 3: MCP server module can be imported
echo "Check 3: Python module imports"
checks_total=$((checks_total + 1))
cd "/Volumes/Extreme SSD/projects/story-portal-app/platform"
if PYTHONPATH=. python3 -c "from src.L12_nl_interface.interfaces.mcp_server_stdio import L12MCPServer" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} MCP server module imports successfully"
    checks_passed=$((checks_passed + 1))
else
    echo -e "  ${RED}✗${NC} Failed to import MCP server module"
    echo "  → Check Python dependencies and PYTHONPATH"
fi
echo

# Check 4: Service catalog exists
echo "Check 4: Service catalog"
checks_total=$((checks_total + 1))
if [ -f "/Volumes/Extreme SSD/projects/story-portal-app/platform/src/L12_nl_interface/data/service_catalog.json" ]; then
    services=$(python3 -c "import json; f=open('src/L12_nl_interface/data/service_catalog.json'); print(len(json.load(f)))" 2>/dev/null)
    if [ ! -z "$services" ]; then
        echo -e "  ${GREEN}✓${NC} Service catalog found with $services services"
        checks_passed=$((checks_passed + 1))
    else
        echo -e "  ${YELLOW}!${NC} Service catalog exists but couldn't parse"
    fi
else
    echo -e "  ${RED}✗${NC} Service catalog not found"
fi
echo

# Check 5: Test if server can start (quick test)
echo "Check 5: MCP server startup test"
checks_total=$((checks_total + 1))
timeout 2 /Volumes/Extreme\ SSD/projects/story-portal-app/platform/run_l12_mcp.sh < /dev/null > /dev/null 2>&1 &
PID=$!
sleep 1
if ps -p $PID > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} MCP server starts successfully"
    kill $PID 2>/dev/null
    wait $PID 2>/dev/null
    checks_passed=$((checks_passed + 1))
else
    echo -e "  ${YELLOW}!${NC} MCP server may have startup issues"
    echo "  → Check /tmp/l12_mcp_server.log for errors"
fi
echo

# Check 6: Log file location is writable
echo "Check 6: Log file location"
checks_total=$((checks_total + 1))
if touch /tmp/l12_mcp_server.log 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Log file location is writable"
    checks_passed=$((checks_passed + 1))
else
    echo -e "  ${RED}✗${NC} Cannot write to /tmp/l12_mcp_server.log"
fi
echo

echo "======================================================================"
echo "Summary: $checks_passed/$checks_total checks passed"
echo "======================================================================"
echo

if [ $checks_passed -eq $checks_total ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo
    echo "The L12 MCP server is properly configured."
    echo
    echo "Next steps:"
    echo "  1. Restart Claude CLI (quit and reopen)"
    echo "  2. Start a new conversation"
    echo "  3. Try: 'List all available platform services'"
    echo
elif [ $checks_passed -ge 4 ]; then
    echo -e "${YELLOW}⚠️  Most checks passed, but some issues detected${NC}"
    echo
    echo "The setup should work, but there may be minor issues."
    echo "Try restarting Claude CLI and test. If problems occur, check the log file."
    echo
else
    echo -e "${RED}❌ Several checks failed${NC}"
    echo
    echo "There are configuration issues that need to be resolved."
    echo "Review the failed checks above and fix them before restarting Claude CLI."
    echo
fi

echo "For more information, see:"
echo "  /Volumes/Extreme SSD/projects/story-portal-app/platform/L12_MCP_SETUP_COMPLETE.md"
echo
