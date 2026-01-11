---
description: Prompt optimizer - auto mode, manual mode, or toggle settings
---

# Prompt Optimizer

When user invokes /prompt, IMMEDIATELY use AskUserQuestion to show this menu:

## Initial Menu

Use AskUserQuestion with:
- header: "Optimizer"
- question: "What would you like to do?"
- options:
  1. "Auto ON" - Enable auto-optimization for all prompts
  2. "Auto OFF" - Disable auto-optimization
  3. "Manual optimize" - Optimize a specific prompt now
  4. "Status" - Check current auto-optimize state

## If "Auto ON" selected:

First, use AskUserQuestion for config:
- header: "Config"
- question: "Auto-optimize settings:"
- options:
  1. "Defaults (API, Level 3)" - Recommended settings
  2. "Custom" - Choose mode and level

If "Custom": show Mode (API/Local/Mock) and Level (1/2/3) selections.

Then run: touch "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled"

Confirm: "Auto-optimize ENABLED with [settings]. All prompts will be optimized (85%+ auto-sends, lower asks approval)."

## If "Auto OFF" selected:

Run: rm -f "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled"

Confirm: "Auto-optimize DISABLED. Use /prompt for manual optimization or ! prefix for one-off."

## If "Manual optimize" selected:

1. Ask: "What prompt would you like to optimize?"

2. Use AskUserQuestion for config:
   - header: "Config"
   - question: "Optimization settings:"
   - options:
     1. "Defaults (API, Level 3)" - Recommended
     2. "Custom" - Choose mode and level

3. Run optimizer: node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3 "PROMPT"

4. Show before/after with confidence

5. Use AskUserQuestion for action:
   - header: "Action"
   - question: "What would you like to do?"
   - options:
     1. "Use this" - Respond to optimized version
     2. "Iterate" - Re-optimize to improve confidence
     3. "Cancel" - Use original prompt

## If "Status" selected:

Run: test -f "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled" && echo "enabled" || echo "disabled"

Report current state to user.
