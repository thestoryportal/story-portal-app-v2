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
  2. label: "Iterate", description: "Answer clarifying questions to improve confidence"
  3. label: "Use original", description: "Respond to original prompt instead"
  4. label: "Cancel", description: "Don't process either prompt"

---

## If "Iterate" selected (Clarifying Questions Flow)

**DO NOT restart workflow selection. Keep the same workflow type. Ask clarifying questions to improve confidence.**

### Step I1: Identify Missing Information
Based on the workflow type, identify what's missing or ambiguous:

**Bug Report missing sections:**
- Expected behavior: "What should happen when you click submit?"
- Actual behavior: "What exactly happens instead?"
- Repro steps: "What are the exact steps to reproduce this?"
- Environment: "What browser/OS/version are you using?"

**Specification missing sections:**
- Goal: "What is the primary outcome you want to achieve?"
- Requirements: "What are the must-have requirements?"
- Context: "How does this integrate with existing systems?"

**Feedback missing sections:**
- What to change: "What specific aspect needs to change?"
- Direction: "How should it be different?"

**Architecture missing sections:**
- Constraints: "What are the technical/business constraints?"
- Goals: "What qualities matter most (speed, scale, simplicity)?"
- Trade-offs: "What are you willing to compromise on?"

**Exploration missing sections:**
- Scope: "How deep should the exploration go?"
- Familiarity: "What do you already know about this topic?"

### Step I2: Ask Clarifying Questions
Use AskUserQuestion for EACH missing/ambiguous item. Example for Bug Report:

Question 1:
- header: "Clarify"
- question: "What behavior did you EXPECT when clicking submit?"
- options:
  1. label: "Form submits once", description: "Single submission, success message"
  2. label: "Validation then submit", description: "Validate fields, then submit"
  3. label: "Loading state then submit", description: "Show spinner, then complete"

Question 2:
- header: "Clarify"
- question: "What ACTUALLY happens?"
- options:
  1. label: "Nothing on first clicks", description: "Button unresponsive initially"
  2. label: "Multiple submissions", description: "Duplicates created in database"
  3. label: "Error shown", description: "Console or UI error appears"

(User can also type custom answers in "Other" field)

### Step I3: Rebuild and Re-optimize
1. Incorporate user's answers into the prompt
2. Re-run optimizer with SAME workflow flag:
```bash
node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3 --workflow [SAME_MODE] "ENHANCED_PROMPT"
```

### Step I4: Show New Results
Display:
- **Iteration:** 2 (or 3, 4...)
- **Original:** [user's initial input]
- **Clarifications added:** [list what was added]
- **New optimized:** [result]
- **Confidence:** [X]% (should be higher now)

### Step I5: Action Menu (Again)
Return to Step 5 Final Action menu. User can:
- "Use optimized" - if confidence is acceptable
- "Iterate" - continue clarifying (loop back to I1)
- "Use original" - abandon optimization
- "Cancel" - stop entirely

---

## If "Status" selected:

Run: test -f "$CLAUDE_PROJECT_DIR/.claude/.optimizer-auto-enabled" && echo "enabled" || echo "disabled"

Report current state to user.
