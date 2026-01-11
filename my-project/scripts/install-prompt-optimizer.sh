#!/bin/bash
#
# Install Prompt Optimizer for Claude Code
#
# Usage:
#   ./install-prompt-optimizer.sh /path/to/target/project
#   ./install-prompt-optimizer.sh  # installs to current directory
#

set -e

# Source directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PROJECT="$(dirname "$SCRIPT_DIR")"

# Target directory (argument or current directory)
TARGET_PROJECT="${1:-.}"
TARGET_PROJECT="$(cd "$TARGET_PROJECT" && pwd)"

echo "=================================="
echo "Prompt Optimizer Installer"
echo "=================================="
echo ""
echo "Source: $SOURCE_PROJECT"
echo "Target: $TARGET_PROJECT"
echo ""

# Validate source files exist
if [ ! -f "$SOURCE_PROJECT/.claude/hooks/prompt-optimizer-hook.cjs" ]; then
    echo "Error: Source hook file not found at $SOURCE_PROJECT/.claude/hooks/prompt-optimizer-hook.cjs"
    exit 1
fi

if [ ! -d "$SOURCE_PROJECT/packages/prompt-optimizer" ]; then
    echo "Error: Source package not found at $SOURCE_PROJECT/packages/prompt-optimizer"
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$TARGET_PROJECT/.claude/hooks"
mkdir -p "$TARGET_PROJECT/.claude/commands"
mkdir -p "$TARGET_PROJECT/packages"

# Copy the prompt-optimizer package
echo "Copying prompt-optimizer package..."
if [ -d "$TARGET_PROJECT/packages/prompt-optimizer" ]; then
    echo "  Warning: packages/prompt-optimizer already exists, backing up..."
    mv "$TARGET_PROJECT/packages/prompt-optimizer" "$TARGET_PROJECT/packages/prompt-optimizer.backup.$(date +%s)"
fi
cp -r "$SOURCE_PROJECT/packages/prompt-optimizer" "$TARGET_PROJECT/packages/"

# Copy the hook file
echo "Copying hook file..."
cp "$SOURCE_PROJECT/.claude/hooks/prompt-optimizer-hook.cjs" "$TARGET_PROJECT/.claude/hooks/"

# Copy the command file
echo "Copying command file..."
cp "$SOURCE_PROJECT/.claude/commands/prompt.md" "$TARGET_PROJECT/.claude/commands/"

# Update or create settings.json
SETTINGS_FILE="$TARGET_PROJECT/.claude/settings.json"
echo "Configuring settings.json..."

if [ -f "$SETTINGS_FILE" ]; then
    # Check if hooks already configured
    if grep -q "UserPromptSubmit" "$SETTINGS_FILE"; then
        echo "  Warning: UserPromptSubmit hook already configured in settings.json"
        echo "  Please manually verify the hook configuration"
    else
        # Add hooks to existing settings (simple approach - may need manual adjustment for complex configs)
        echo "  Adding hook to existing settings.json..."
        # Create backup
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%s)"

        # Use node to safely merge JSON
        node -e "
const fs = require('fs');
const settings = JSON.parse(fs.readFileSync('$SETTINGS_FILE', 'utf8'));
settings.hooks = settings.hooks || {};
settings.hooks.UserPromptSubmit = settings.hooks.UserPromptSubmit || [];
if (!settings.hooks.UserPromptSubmit.includes('node .claude/hooks/prompt-optimizer-hook.cjs')) {
    settings.hooks.UserPromptSubmit.push('node .claude/hooks/prompt-optimizer-hook.cjs');
}
fs.writeFileSync('$SETTINGS_FILE', JSON.stringify(settings, null, 2));
"
    fi
else
    # Create new settings.json
    echo "  Creating new settings.json..."
    cat > "$SETTINGS_FILE" << 'SETTINGS_EOF'
{
  "hooks": {
    "UserPromptSubmit": [
      "node .claude/hooks/prompt-optimizer-hook.cjs"
    ]
  }
}
SETTINGS_EOF
fi

# Build the prompt-optimizer if needed
echo "Building prompt-optimizer..."
cd "$TARGET_PROJECT/packages/prompt-optimizer"
if [ -f "package.json" ]; then
    if [ ! -d "node_modules" ]; then
        echo "  Installing dependencies..."
        npm install --silent 2>/dev/null || echo "  Warning: npm install had issues, may need manual intervention"
    fi
    if [ ! -d "dist" ] || [ ! -f "dist/cli/index.js" ]; then
        echo "  Building..."
        npm run build --silent 2>/dev/null || echo "  Warning: build had issues, may need manual intervention"
    else
        echo "  Already built"
    fi
fi
cd "$TARGET_PROJECT"

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "Files installed:"
echo "  - .claude/hooks/prompt-optimizer-hook.cjs"
echo "  - .claude/commands/prompt.md"
echo "  - .claude/settings.json (updated)"
echo "  - packages/prompt-optimizer/"
echo ""
echo "Usage:"
echo "  /prompt          - Open optimizer menu (manual mode, toggle auto, check status)"
echo "  !your prompt     - One-off optimization (prefix any prompt with !)"
echo ""
echo "Modes (set via PROMPT_OPTIMIZER_MODE env var):"
echo "  api   - Anthropic API (default, fast, ~\$0.001/prompt)"
echo "  local - Ollama local LLM (free, slow ~60-90s)"
echo "  mock  - Rule-based only (instant, basic)"
echo ""
echo "For API mode, ensure ANTHROPIC_API_KEY is set:"
echo "  export ANTHROPIC_API_KEY=your-key-here"
echo ""
