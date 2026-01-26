#!/usr/bin/env node
/**
 * Plan Mode L05 Integration Hook
 *
 * Post-tool hook that triggers after ExitPlanMode to offer L05 execution options.
 *
 * Flow:
 * 1. User approves plan in CLI plan mode (Gate 1)
 * 2. ExitPlanMode is called
 * 3. This hook triggers
 * 4. Hook reads plan file and invokes L05 adapter
 * 5. Hook injects Gate 2 options into conversation
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Configuration
const CONFIG = {
  enabled: true,
  platformDir: '../platform',  // Relative to project dir
  timeout: 30000,              // 30 second timeout for Python bridge (includes Python startup)
  debug: true,                 // Enable debug logging to file
};

// Debug logging
const DEBUG_LOG_PATH = path.join(
  process.env.CLAUDE_PROJECT_DIR || process.cwd(),
  '.claude', 'contexts', '.hook-debug.log'
);

function debugLog(message, data = null) {
  if (!CONFIG.debug) return;
  const timestamp = new Date().toISOString();
  const logEntry = `[${timestamp}] ${message}${data ? '\n' + JSON.stringify(data, null, 2) : ''}\n`;
  try {
    fs.appendFileSync(DEBUG_LOG_PATH, logEntry);
  } catch (e) {
    // Ignore logging errors
  }
}

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
 * Extract plan file path from ExitPlanMode result
 */
function extractPlanPath(input) {
  // The plan file path may be in the tool result or we can find it
  // by looking for the most recent .plan.md file
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const homeDir = process.env.HOME || process.env.USERPROFILE;

  // Check common plan file locations
  const planLocations = [
    path.join(projectDir, '.claude', 'plan.md'),
    path.join(projectDir, 'plan.md'),
    path.join(projectDir, '.plan.md'),
  ];

  // Check global ~/.claude/plans/ directory (where Claude Code saves plans)
  const globalPlansDir = path.join(homeDir, '.claude', 'plans');
  if (fs.existsSync(globalPlansDir)) {
    try {
      const files = fs.readdirSync(globalPlansDir)
        .filter(f => f.endsWith('.md'))
        .map(f => ({
          name: f,
          path: path.join(globalPlansDir, f),
          mtime: fs.statSync(path.join(globalPlansDir, f)).mtime
        }))
        .sort((a, b) => b.mtime - a.mtime);

      // Return the most recently modified plan (within last 24 hours)
      if (files.length > 0) {
        const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
        if (files[0].mtime.getTime() > oneDayAgo) {
          return files[0].path;
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }

  // Also check for timestamped plans in project .claude dir
  const claudeDir = path.join(projectDir, '.claude');
  if (fs.existsSync(claudeDir)) {
    try {
      const files = fs.readdirSync(claudeDir)
        .filter(f => f.endsWith('.plan.md') || f === 'plan.md')
        .map(f => ({
          name: f,
          path: path.join(claudeDir, f),
          mtime: fs.statSync(path.join(claudeDir, f)).mtime
        }))
        .sort((a, b) => b.mtime - a.mtime);

      if (files.length > 0) {
        return files[0].path;
      }
    } catch (e) {
      // Ignore errors
    }
  }

  // Check standard locations
  for (const loc of planLocations) {
    if (fs.existsSync(loc)) {
      return loc;
    }
  }

  return null;
}

/**
 * Run the L05 adapter via Python bridge script (async version)
 */
async function runL05Adapter(planPath, projectDir) {
  const platformDir = path.resolve(projectDir, CONFIG.platformDir);
  const bridgeScript = path.join(projectDir, '.claude', 'hooks', 'l05-bridge.py');

  debugLog('Running L05 adapter (async)', {
    planPath,
    platformDir,
    bridgeScript,
  });

  return new Promise((resolve) => {
    try {
      // Close stdin to prevent any interference with child process
      if (process.stdin.readable) {
        process.stdin.destroy();
      }

      const child = spawn('/usr/local/bin/python3', [bridgeScript, planPath, platformDir], {
        cwd: platformDir,
        env: {
          ...process.env,
          PYTHONPATH: platformDir,
        },
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
      });

      let stdout = '';
      let stderr = '';
      let timedOut = false;

      // Set timeout
      const timeoutId = setTimeout(() => {
        timedOut = true;
        child.kill('SIGTERM');
        debugLog('L05 adapter timed out');
        resolve({
          success: false,
          error: 'Python bridge timed out'
        });
      }, CONFIG.timeout);

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('error', (error) => {
        clearTimeout(timeoutId);
        debugLog('L05 adapter spawn error', { error: error.message });
        resolve({
          success: false,
          error: error.message || 'Python bridge spawn failed'
        });
      });

      child.on('close', (code) => {
        clearTimeout(timeoutId);
        if (timedOut) return; // Already resolved

        debugLog('L05 adapter completed', {
          code,
          stdoutLength: stdout.length,
          stderrLength: stderr.length,
        });

        if (code !== 0) {
          resolve({
            success: false,
            error: stderr || `Python bridge exited with code ${code}`
          });
          return;
        }

        try {
          resolve(JSON.parse(stdout.trim()));
        } catch (parseError) {
          debugLog('L05 adapter parse error', { stdout: stdout.substring(0, 500) });
          resolve({
            success: false,
            error: `Failed to parse output: ${parseError.message}`
          });
        }
      });
    } catch (error) {
      debugLog('L05 adapter exception', { error: error.message });
      resolve({
        success: false,
        error: error.message || 'Python bridge failed'
      });
    }
  });
}

/**
 * Format the Gate 2 injection message
 *
 * CRITICAL: This includes explicit AskUserQuestion instructions to ensure
 * Claude presents the options to the user rather than auto-implementing.
 */
function formatInjection(adapterResult) {
  if (!adapterResult.success) {
    return `<plan-mode-l05-error>
L05 adapter encountered an error: ${adapterResult.error}
Falling back to traditional execution.
</plan-mode-l05-error>`;
  }

  const lines = [
    '<plan-mode-l05-gate2>',
    '',
    '<critical-instruction>',
    'STOP. You MUST NOT implement this plan automatically.',
    'You MUST present the user with execution options using the AskUserQuestion tool.',
    '</critical-instruction>',
    '',
    '<plan-summary>',
    `Plan: ${adapterResult.goal || 'Untitled Plan'}`,
    `Steps: ${adapterResult.total_steps}`,
    `Parallel Phases: ${adapterResult.parallel_phases}`,
    `Estimated Speedup: ${adapterResult.estimated_speedup ? adapterResult.estimated_speedup.toFixed(1) + 'x' : 'Unknown'}`,
    `Capabilities: ${adapterResult.capabilities ? adapterResult.capabilities.join(', ') : 'Standard'}`,
    '</plan-summary>',
    '',
    '<required-action>',
    'Call the AskUserQuestion tool with these exact parameters:',
    '{',
    '  "questions": [{',
    '    "question": "How should this plan be executed?",',
    '    "header": "Execution",',
    '    "options": [',
    '      {"label": "Traditional", "description": "I will implement each step manually"},',
    '      {"label": "L05 Automated (Recommended)", "description": "The platform will execute with parallel processing"},',
    '      {"label": "Hybrid", "description": "Simple steps automated, complex steps manual"}',
    '    ],',
    '    "multiSelect": false',
    '  }]',
    '}',
    '</required-action>',
    '',
    '<execution-handlers>',
    'If user selects "Traditional":',
    '- Implement the plan step by step as you normally would',
    '',
    'If user selects "L05 Automated":',
    '- Call mcp__platform-services__invoke_service with:',
    '  - command: "PlanningService.execute_plan_direct"',
    '  - parameters: { "execution_plan": <full execution_plan from gate2 state> }',
    '- The execution_plan is stored in .claude/contexts/.gate2-pending.json',
    '',
    'If user selects "Hybrid":',
    '- Ask user which steps should be automated',
    '- Execute selected steps via L05, implement others manually',
    '</execution-handlers>',
    '',
    `<plan-id>${adapterResult.plan_id}</plan-id>`,
    `<goal-id>${adapterResult.goal_id}</goal-id>`,
    '',
    '</plan-mode-l05-gate2>',
  ];

  return lines.join('\n');
}

/**
 * Save state for later execution
 * CRITICAL: Stores the FULL ExecutionPlan and Goal objects for execute_plan_direct
 */
function saveGate2State(adapterResult, projectDir) {
  const statePath = path.join(projectDir, '.claude', 'contexts', '.gate2-pending.json');

  try {
    const state = {
      timestamp: new Date().toISOString(),
      plan_id: adapterResult.plan_id,
      goal_id: adapterResult.goal_id,
      goal: adapterResult.goal,
      recommended: adapterResult.recommended,
      options: adapterResult.options,
      awaiting_choice: true,

      // CRITICAL: Store full ExecutionPlan object for execute_plan_direct
      // This bypasses the E5002 error from execute_plan(plan_id) cache lookup
      execution_plan: adapterResult.execution_plan,
      goal_object: adapterResult.goal_object,

      // Fallback: store plan markdown path
      plan_markdown_path: adapterResult.plan_markdown_path,
    };

    fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  } catch (e) {
    // Ignore save errors
  }
}

/**
 * Format output for PostToolUse hook (JSON with hookSpecificOutput.additionalContext)
 * This is REQUIRED for PostToolUse hooks to inject context into the conversation.
 */
function formatPostToolUseOutput(content) {
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: content
    }
  });
}

/**
 * Main hook logic
 */
async function main() {
  debugLog('=== Hook invoked ===');

  const input = await readInput();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  debugLog('Received input', {
    tool_name: input.tool_name,
    toolName: input.toolName,
    hook_event_name: input.hook_event_name,
    keys: Object.keys(input),
    projectDir,
    CLAUDE_PROJECT_DIR: process.env.CLAUDE_PROJECT_DIR
  });

  // Check if enabled
  if (!CONFIG.enabled) {
    debugLog('Hook disabled, exiting');
    process.exit(0);
  }

  // Check if this is an ExitPlanMode result
  const toolName = input.tool_name || input.toolName || '';
  debugLog(`Tool name check: "${toolName}" === "ExitPlanMode"? ${toolName === 'ExitPlanMode'}`);

  if (toolName !== 'ExitPlanMode') {
    // Not our trigger - exit silently
    debugLog('Not ExitPlanMode, exiting silently');
    process.exit(0);
  }

  debugLog('ExitPlanMode detected, proceeding with L05 integration');

  // Find the plan file
  const planPath = extractPlanPath(input);
  if (!planPath) {
    // Output as proper PostToolUse JSON format
    console.log(formatPostToolUseOutput(
      '<plan-mode-l05-warning>\nCould not find plan file. L05 integration skipped.\n</plan-mode-l05-warning>'
    ));
    process.exit(0);
  }

  // Run the L05 adapter
  const adapterResult = await runL05Adapter(planPath, projectDir);

  // Save state for execution
  if (adapterResult.success) {
    saveGate2State(adapterResult, projectDir);
  }

  // Output the Gate 2 injection in proper PostToolUse JSON format
  const injectionContent = formatInjection(adapterResult);
  const finalOutput = formatPostToolUseOutput(injectionContent);

  debugLog('Final output being sent to stdout', {
    injectionContentLength: injectionContent.length,
    finalOutputLength: finalOutput.length,
    parsedOutput: JSON.parse(finalOutput)
  });

  console.log(finalOutput);

  debugLog('Hook completed successfully');
  process.exit(0);
}

main().catch(error => {
  console.error(`<plan-mode-l05-error>${error.message}</plan-mode-l05-error>`);
  process.exit(0);
});
