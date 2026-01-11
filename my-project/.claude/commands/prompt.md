---
description: Prompt optimizer - auto mode, manual mode, or toggle settings
---

# Prompt Optimizer

Optimizes prompts for clarity with workflow-specific enhancements:
- **Specification** (!spec) - Goals, requirements, context for new features
- **Feedback** (!feedback) - What to change, direction for revisions
- **Bug Report** (!bug) - Expected/actual behavior, repro steps
- **Quick Task** (!quick) - Minimal optimization for simple actions
- **Architecture** (!arch) - Constraints, goals, trade-offs for design
- **Exploration** (!explore) - Scope, depth for research

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

**IMPORTANT: You MUST use the AskUserQuestion tool for EACH step below. Do NOT just ask questions in text.**

### Step 1: Workflow Selection
IMMEDIATELY use AskUserQuestion tool with these EXACT parameters:
- header: "Workflow"
- question: "What type of prompt are you optimizing?"
- options:
  1. label: "Auto-detect", description: "Let optimizer detect intent from content (Recommended)"
  2. label: "Specification", description: "New feature/project - adds goal, requirements, context sections"
  3. label: "Feedback", description: "Revision direction - adds what-to-change, direction sections"
  4. label: "Bug Report", description: "Issue description - adds expected/actual behavior, repro steps"

If user selects "Other", use AskUserQuestion again:
- header: "Workflow"
- question: "Additional workflow types:"
- options:
  1. label: "Quick Task", description: "Simple action with minimal optimization"
  2. label: "Architecture", description: "Design decision - adds constraints, goals, trade-offs"
  3. label: "Exploration", description: "Research/understanding - adds scope, depth sections"

### Step 2: Get the Prompt
After workflow is selected, use AskUserQuestion:
- header: "Prompt"
- question: "Enter the prompt you want to optimize:"
- options:
  1. label: "Type below", description: "Enter your prompt in the text field"

The user will type their prompt in the "Other" text field.

### Step 3: Run Optimizer
Run the optimizer with the appropriate workflow flag:
```bash
node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3 [WORKFLOW_FLAG] "USER_PROMPT"
```

Workflow flags:
- Auto-detect: (no flag)
- Specification: --workflow spec
- Feedback: --workflow feedback
- Bug Report: --workflow bug
- Quick Task: --workflow quick
- Architecture: --workflow arch
- Exploration: --workflow explore

### Step 4: Show Results
Display:
- Original prompt
- Optimized prompt
- Workflow mode applied
- Confidence percentage

### Step 5: Action Selection
Use AskUserQuestion:
- header: "Action"
- question: "What would you like to do with the optimized prompt?"
- options:
  1. label: "Use this", description: "Respond to the optimized version"
  2. label: "Iterate", description: "Re-optimize to improve confidence"
  3. label: "Use original", description: "Keep original prompt instead"
  4. label: "Cancel", description: "Don't process either prompt"

## If "Status" selected:

Run: test -f "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled" && echo "enabled" || echo "disabled"

Report current state to user.
