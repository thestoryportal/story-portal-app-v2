#!/usr/bin/env node
/**
 * Plan Mode L05 Executor Hook
 *
 * UserPromptSubmit hook that detects Gate 2 choices and prepares execution.
 *
 * Listens for user responses like:
 * - "L05" / "L05 Automated" / "automated"
 * - "Traditional" / "traditional"
 * - "Hybrid" / "hybrid"
 *
 * Includes MCP health checking before L05 execution.
 */

const fs = require('fs');
const path = require('path');

// Import MCP health check utilities
let mcpHealth;
try {
  mcpHealth = require('./mcp-health-check.cjs');
} catch (e) {
  // Fallback if module not available
  mcpHealth = {
    performHealthCheck: async () => ({ healthy: false, details: { error: 'Health check module not loaded' } }),
    formatHealthStatus: (r) => `<mcp-health status="unknown">MCP status unknown</mcp-health>`,
  };
}

// Choice detection patterns
const CHOICE_PATTERNS = {
  l05_automated: [
    /\bl05\b/i,
    /\bautomated\b/i,
    /\bparallel\b/i,
    /option\s*2/i,
    /\bsecond\b.*option/i,
  ],
  traditional: [
    /\btraditional\b/i,
    /\bmanual\b/i,
    /\byou\s+implement/i,
    /\bclaude\s+implement/i,
    /option\s*1/i,
    /\bfirst\b.*option/i,
  ],
  hybrid: [
    /\bhybrid\b/i,
    /\bmix\b/i,
    /\bboth\b/i,
    /option\s*3/i,
    /\bthird\b.*option/i,
  ],
};

/**
 * Read stdin as JSON
 */
async function readInput() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => data += chunk);
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(data || '{}'));
      } catch {
        resolve({});
      }
    });
  });
}

/**
 * Check if there's a pending Gate 2 choice
 */
function getPendingGate2(projectDir) {
  const statePath = path.join(projectDir, '.claude', 'contexts', '.gate2-pending.json');

  try {
    if (fs.existsSync(statePath)) {
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      if (state.awaiting_choice) {
        return state;
      }
    }
  } catch (e) {
    // Ignore errors
  }

  return null;
}

/**
 * Detect which choice the user made
 */
function detectChoice(userMessage) {
  const message = userMessage.toLowerCase();

  for (const [choice, patterns] of Object.entries(CHOICE_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(message)) {
        return choice;
      }
    }
  }

  return null;
}

/**
 * Clear the pending Gate 2 state
 */
function clearPendingGate2(projectDir, choice) {
  const statePath = path.join(projectDir, '.claude', 'contexts', '.gate2-pending.json');

  try {
    if (fs.existsSync(statePath)) {
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      state.awaiting_choice = false;
      state.choice_made = choice;
      state.choice_timestamp = new Date().toISOString();
      fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
    }
  } catch (e) {
    // Ignore errors
  }
}

/**
 * Format execution instruction based on choice
 * @param {string} choice - User's choice
 * @param {object} gate2State - Gate 2 state
 * @param {object} mcpHealthResult - MCP health check result
 */
function formatExecutionInstruction(choice, gate2State, mcpHealthResult = null) {
  const lines = ['<plan-mode-l05-execute>'];

  switch (choice) {
    case 'l05_automated':
      // Check MCP health for L05 execution
      if (mcpHealthResult && !mcpHealthResult.healthy) {
        lines.push('');
        lines.push('**User selected: L05 Automated Execution**');
        lines.push('');
        lines.push('⚠️ **MCP Connection Issue Detected**');
        lines.push('');
        lines.push(`Error: ${mcpHealthResult.details.error || 'Platform services MCP is not connected'}`);
        lines.push('');
        lines.push('**Options:**');
        lines.push('1. Restart Claude Code session to reconnect MCP');
        lines.push('2. Proceed with traditional execution instead');
        lines.push('');
        lines.push('The L05 planning pipeline requires the platform-services MCP to be connected.');
        lines.push('');
        lines.push('To check MCP status manually: `claude mcp list`');
        break;
      }

      // Check if we have the full execution_plan (required for execute_plan_direct)
      if (!gate2State.execution_plan) {
        lines.push('');
        lines.push('**User selected: L05 Automated Execution**');
        lines.push('');
        lines.push('⚠️ **Execution Plan Missing**');
        lines.push('');
        lines.push('The full execution plan is not available in state.');
        lines.push('This may be from an older version of the L05 hooks.');
        lines.push('');
        lines.push('Please re-run `/plan` to generate a new plan with full state.');
        break;
      }

      lines.push('');
      lines.push('**User selected: L05 Automated Execution**');
      lines.push('');
      lines.push('Execute this plan using the L05 Planning Stack via MCP:');
      lines.push('');
      lines.push('CRITICAL: Use `execute_plan_direct` with the FULL execution plan object.');
      lines.push('');
      lines.push('Use `mcp__platform-services__invoke_service` with:');
      lines.push('```json');
      lines.push('{');
      lines.push('  "command": "PlanningService.execute_plan_direct",');
      lines.push('  "parameters": {');
      lines.push('    "execution_plan": <the execution_plan object from gate2 state>');
      lines.push('  }');
      lines.push('}');
      lines.push('```');
      lines.push('');
      lines.push(`Plan ID: ${gate2State.plan_id}`);
      lines.push(`Goal ID: ${gate2State.goal_id}`);
      lines.push(`Task Count: ${gate2State.execution_plan?.tasks?.length || 'unknown'}`);
      lines.push('');
      lines.push('The plan will execute with:');
      lines.push('- Parallel task execution');
      lines.push('- Automatic error recovery');
      lines.push('- Progress tracking');
      lines.push('- Multi-agent task assignment');
      break;

    case 'hybrid':
      lines.push('');
      lines.push('**User selected: Hybrid Execution**');
      lines.push('');
      lines.push('Execute this plan using hybrid mode:');
      lines.push('- L05 handles parallelizable/simple steps automatically');
      lines.push('- Claude implements complex steps with user interaction');
      lines.push('');
      lines.push(`Plan ID: ${gate2State.plan_id}`);
      lines.push(`Goal ID: ${gate2State.goal_id}`);
      lines.push('');
      lines.push('Start by running the L05 adapter to get the task routing:');
      lines.push('```python');
      lines.push('from src.L05_planning.adapters import CLIPlanModeHook, ExecutionChoice');
      lines.push('');
      lines.push('result = await hook.execute_choice(');
      lines.push('    choice=ExecutionChoice.HYBRID,');
      lines.push('    execution_plan=plan,');
      lines.push('    goal=goal,');
      lines.push(')');
      lines.push('# Then implement claude_tasks manually');
      lines.push('```');
      break;

    case 'traditional':
    default:
      lines.push('');
      lines.push('**User selected: Traditional Execution**');
      lines.push('');
      lines.push(`Implement the plan "${gate2State.goal}" step by step.`);
      lines.push('');
      lines.push('Proceed with implementing each step sequentially.');
      lines.push('The plan file contains the full step details.');
      break;
  }

  lines.push('');
  lines.push('</plan-mode-l05-execute>');

  return lines.join('\n');
}

/**
 * Format the Gate 2 options prompt
 */
function formatGate2Prompt(gate2State) {
  const lines = [
    '<plan-mode-l05-gate2>',
    '',
    '## Execution Method',
    '',
    `Plan "${gate2State.goal}" is ready for execution.`,
    '',
    '**Choose how to execute:**',
    '',
  ];

  for (const opt of gate2State.options) {
    const marker = opt.id === gate2State.recommended ? '●' : '○';
    const rec = opt.id === gate2State.recommended ? ' **(Recommended)**' : '';
    lines.push(`${marker} **${opt.label}**${rec}`);
    lines.push(`   ${opt.description}`);
    lines.push('');
  }

  lines.push('Respond with: "L05", "traditional", or "hybrid"');
  lines.push('');
  lines.push(`Plan ID: \`${gate2State.plan_id}\``);
  lines.push('');
  lines.push('</plan-mode-l05-gate2>');

  return lines.join('\n');
}

/**
 * Main hook logic
 */
async function main() {
  const input = await readInput();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  // Check if there's a pending Gate 2 choice
  const gate2State = getPendingGate2(projectDir);
  if (!gate2State) {
    // No pending Gate 2 - exit silently
    process.exit(0);
  }

  // Get the user's message
  const userMessage = input.prompt || input.message || input.content || '';
  if (!userMessage) {
    // No message but pending Gate 2 - show the options
    console.log(formatGate2Prompt(gate2State));
    process.exit(0);
  }

  // Detect the choice
  const choice = detectChoice(userMessage);
  if (!choice) {
    // User didn't make a clear choice - show the Gate 2 prompt again
    console.log(formatGate2Prompt(gate2State));
    process.exit(0);
  }

  // For L05 execution, check MCP health first
  let mcpHealthResult = null;
  if (choice === 'l05_automated') {
    try {
      mcpHealthResult = await mcpHealth.performHealthCheck();
    } catch (e) {
      mcpHealthResult = { healthy: false, details: { error: e.message } };
    }
  }

  // Clear the pending state
  clearPendingGate2(projectDir, choice);

  // Output execution instruction (with MCP health info for L05)
  console.log(formatExecutionInstruction(choice, gate2State, mcpHealthResult));

  process.exit(0);
}

main().catch(error => {
  // Silent failure
  process.exit(0);
});
