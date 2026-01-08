#!/bin/bash

# Enable Telemetry for Story Portal Development
# This script sources the telemetry configuration and launches Claude Code
#
# Usage:
#   ./enable-telemetry.sh
#
# Or source it manually:
#   source enable-telemetry.sh
#   claude

set -e

echo "🔧 Enabling telemetry for Story Portal development..."

# Source telemetry configuration
if [ -f "$(dirname "$0")/.env.telemetry" ]; then
  source "$(dirname "$0")/.env.telemetry"
  echo "✅ Telemetry enabled"
  echo ""
  echo "Token metrics will appear in console every 10 seconds"
  echo "Use /cost command to see total session cost"
  echo ""
else
  echo "❌ Error: .env.telemetry not found"
  exit 1
fi

# Optional: Show environment variables that were set
echo "📊 Configuration:"
echo "  CLAUDE_CODE_ENABLE_TELEMETRY=$CLAUDE_CODE_ENABLE_TELEMETRY"
echo "  OTE METRICS_EXPORTER=$OTEL_METRICS_EXPORTER"
echo "  OTEL_METRIC_EXPORT_INTERVAL=$OTEL_METRIC_EXPORT_INTERVAL"
echo ""

# Launch Claude Code
echo "Launching Claude Code..."
echo "---"
claude
