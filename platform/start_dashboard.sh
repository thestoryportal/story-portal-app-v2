#!/bin/bash
#
# Start L01 Data Layer and L10 Human Interface Dashboard
# This script ensures both services start with correct Python environment and configuration
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Agent Platform Dashboard Services${NC}"
echo "Working directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at .venv${NC}"
    echo "Please create virtual environment first: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if required packages are installed
if ! .venv/bin/python -c "import uvicorn, websockets, httpx, fastapi" 2>/dev/null; then
    echo -e "${RED}Error: Required packages not installed${NC}"
    echo "Please install requirements: pip install -r requirements.txt"
    exit 1
fi

# Function to check if port is in use
check_port() {
    lsof -i :"$1" > /dev/null 2>&1
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti :"$port" 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Killing existing process on port $port (PID: $pid)${NC}"
        kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
}

# Stop existing services if running
echo -e "${YELLOW}Checking for existing services...${NC}"
if check_port 8002; then
    echo "L01 Data Layer already running on port 8002"
    kill_port 8002
fi

if check_port 8010; then
    echo "L10 Dashboard already running on port 8010"
    kill_port 8010
fi

# Create logs directory
mkdir -p logs

# Start L01 Data Layer
echo -e "${GREEN}Starting L01 Data Layer on port 8002...${NC}"
.venv/bin/python -m uvicorn src.L01_data_layer.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    > logs/l01.log 2>&1 &
L01_PID=$!
echo "L01 Data Layer started (PID: $L01_PID)"

# Wait for L01 to be ready
echo -e "${YELLOW}Waiting for L01 to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8002/health/live > /dev/null 2>&1; then
        echo -e "${GREEN}L01 Data Layer is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}L01 Data Layer failed to start${NC}"
        echo "Check logs/l01.log for details"
        kill $L01_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Start L10 Human Interface Dashboard
echo -e "${GREEN}Starting L10 Dashboard on port 8010...${NC}"
.venv/bin/python -m uvicorn src.L10_human_interface.app:app \
    --host 0.0.0.0 \
    --port 8010 \
    --reload \
    > logs/l10.log 2>&1 &
L10_PID=$!
echo "L10 Dashboard started (PID: $L10_PID)"

# Wait for L10 to be ready
echo -e "${YELLOW}Waiting for L10 to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8010/ > /dev/null 2>&1; then
        echo -e "${GREEN}L10 Dashboard is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}L10 Dashboard failed to start${NC}"
        echo "Check logs/l10.log for details"
        kill $L01_PID $L10_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Save PIDs for later
echo $L01_PID > logs/l01.pid
echo $L10_PID > logs/l10.pid

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Services Started Successfully!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "L01 Data Layer:    http://localhost:8002"
echo "L10 Dashboard:     http://localhost:8010"
echo ""
echo "Process IDs:"
echo "  L01: $L01_PID"
echo "  L10: $L10_PID"
echo ""
echo "Logs:"
echo "  L01: logs/l01.log"
echo "  L10: logs/l10.log"
echo ""
echo "To stop services, run: ./stop_dashboard.sh"
echo "To view logs: tail -f logs/l10.log"
echo ""
