#!/bin/bash
# Wrapper script to run l05-bridge.py in isolation
# This helps avoid issues with Node.js spawnSync and piped stdin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="${SCRIPT_DIR}/l05-bridge.py"

# Close stdin to ensure no interference
exec 0</dev/null

# Execute Python with proper environment
export PYTHONPATH="$2"
exec /usr/local/bin/python3 "$BRIDGE_SCRIPT" "$1" "$2"
