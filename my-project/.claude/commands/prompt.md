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

**CRITICAL: Use AskUserQuestion tool for ALL selections. Never ask questions in plain text.**

### Step 1: Workflow Selection (Menu 1 of 2)
IMMEDIATELY use AskUserQuestion:
- header: "Workflow"
- question: "What type of prompt are you optimizing?"
- options:
  1. label: "Auto-detect (Recommended)", description: "Automatically detect intent from prompt content"
  2. label: "Specification", description: "New feature/project - goal, requirements, context"
  3. label: "Feedback", description: "Revision direction - what to change, which direction"
  4. label: "More workflows...", description: "Bug Report, Quick Task, Architecture, Exploration"

### Step 1b: If "More workflows..." selected (Menu 2 of 2)
Use AskUserQuestion:
- header: "Workflow"
- question: "Select workflow type:"
- options:
  1. label: "Bug Report", description: "Issue description - expected/actual behavior, repro steps"
  2. label: "Quick Task", description: "Simple action - minimal optimization"
  3. label: "Architecture", description: "Design decision - constraints, goals, trade-offs"
  4. label: "Exploration", description: "Research/understanding - scope, depth"

### Step 2: Get the Prompt
Use AskUserQuestion:
- header: "Prompt"
- question: "Enter the prompt to optimize:"
- options:
  1. label: "Type in Other field below", description: "Enter your full prompt text"

User enters their prompt in the "Other" text input field.

### Step 3: Run Optimizer
Execute with selected workflow:
```bash
node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3 [FLAGS] "PROMPT"
```

Flags by workflow:
- Auto-detect: (none)
- Specification: --workflow spec
- Feedback: --workflow feedback
- Bug Report: --workflow bug
- Quick Task: --workflow quick
- Architecture: --workflow arch
- Exploration: --workflow explore

### Step 4: Display Results
Show:
- **Original:** [user's input]
- **Optimized:** [result]
- **Workflow:** [mode] | **Confidence:** [X]%

### Step 5: Final Action
Use AskUserQuestion:
- header: "Action"
- question: "What would you like to do?"
- options:
  1. label: "Use optimized", description: "Respond to the optimized prompt"
  2. label: "Iterate", description: "Re-optimize with different settings"
  3. label: "Use original", description: "Respond to original prompt instead"
  4. label: "Cancel", description: "Don't process either prompt"

## If "Status" selected:

Run: test -f "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled" && echo "enabled" || echo "disabled"

Report current state to user.
