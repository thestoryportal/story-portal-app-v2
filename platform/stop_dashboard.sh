#!/bin/bash
#
# Stop L01 Data Layer and L10 Human Interface Dashboard
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping AI Agent Platform Dashboard Services${NC}"

# Function to kill process by PID file
kill_service() {
    local service=$1
    local pidfile="logs/${service}.pid"

    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping $service (PID: $pid)..."
            kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            rm "$pidfile"
            echo -e "${GREEN}$service stopped${NC}"
        else
            echo "$service not running (stale PID file)"
            rm "$pidfile"
        fi
    else
        echo "$service PID file not found"
    fi
}

# Kill by port if PID files don't exist
kill_port() {
    local port=$1
    local service=$2
    local pid=$(lsof -ti :"$port" 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "Stopping $service on port $port (PID: $pid)..."
        kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
        echo -e "${GREEN}$service stopped${NC}"
    fi
}

# Try PID files first
kill_service "l01"
kill_service "l10"

# Fallback to port-based killing
kill_port 8002 "L01 Data Layer"
kill_port 8010 "L10 Dashboard"

echo -e "${GREEN}All services stopped${NC}"
