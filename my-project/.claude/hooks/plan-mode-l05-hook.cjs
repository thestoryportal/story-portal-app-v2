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
const { execSync } = require('child_process');

// Configuration
const CONFIG = {
  enabled: true,
  platformDir: '../platform',  // Relative to project dir
  minStepsForL05: 3,           // Minimum steps to offer L05
  timeout: 10000,              // 10 second timeout for Python bridge
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
 * Extract plan file path from ExitPlanMode result
 */
function extractPlanPath(input) {
  // The plan file path may be in the tool result or we can find it
  // by looking for the most recent .plan.md file
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  // Check common plan file locations
  const planLocations = [
    path.join(projectDir, '.claude', 'plan.md'),
    path.join(projectDir, 'plan.md'),
    path.join(projectDir, '.plan.md'),
  ];

  // Also check for timestamped plans
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
 * Run the L05 adapter via Python bridge script
 */
function runL05Adapter(planPath, projectDir) {
  const platformDir = path.resolve(projectDir, CONFIG.platformDir);
  const bridgeScript = path.join(projectDir, '.claude', 'hooks', 'l05-bridge.py');

  try {
    const result = execSync(
      `python3 "${bridgeScript}" "${planPath}" "${platformDir}"`,
      {
        cwd: platformDir,
        timeout: CONFIG.timeout,
        encoding: 'utf8',
        env: {
          ...process.env,
          PYTHONPATH: platformDir,
        }
      }
    );

    return JSON.parse(result.trim());
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Python bridge failed'
    };
  }
}

/**
 * Format the Gate 2 injection message
 */
function formatInjection(adapterResult) {
  if (!adapterResult.success) {
    return `<plan-mode-l05-error>
L05 adapter encountered an error: ${adapterResult.error}
Falling back to traditional execution.
</plan-mode-l05-error>`;
  }

  // Don't offer L05 for very simple plans
  if (adapterResult.total_steps < CONFIG.minStepsForL05) {
    return `<plan-mode-l05-skip>
Plan has only ${adapterResult.total_steps} steps - using traditional execution.
</plan-mode-l05-skip>`;
  }

  const lines = [
    '<plan-mode-l05-gate2>',
    '',
    '## Execution Method',
    '',
    `Plan "${adapterResult.goal}" is ready for execution.`,
    '',
    '**Choose how to execute:**',
    '',
  ];

  for (const opt of adapterResult.options) {
    const marker = opt.id === adapterResult.recommended ? '●' : '○';
    const rec = opt.id === adapterResult.recommended ? ' **(Recommended)**' : '';
    lines.push(`${marker} **${opt.label}**${rec}`);
    lines.push(`   ${opt.description}`);
    lines.push('');
  }

  lines.push('### Analysis');
  lines.push('');
  lines.push(`- **Total steps:** ${adapterResult.total_steps}`);
  lines.push(`- **Parallel phases:** ${adapterResult.parallel_phases}`);
  lines.push(`- **Estimated speedup:** ${adapterResult.estimated_speedup.toFixed(1)}x`);
  lines.push(`- **Capabilities:** ${adapterResult.capabilities.join(', ')}`);
  lines.push('');
  lines.push('---');
  lines.push(`Plan ID: \`${adapterResult.plan_id}\``);
  lines.push(`Goal ID: \`${adapterResult.goal_id}\``);
  lines.push('');
  lines.push('</plan-mode-l05-gate2>');

  return lines.join('\n');
}

/**
 * Save state for later execution
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
    };

    fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  } catch (e) {
    // Ignore save errors
  }
}

/**
 * Main hook logic
 */
async function main() {
  const input = await readInput();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  // Check if enabled
  if (!CONFIG.enabled) {
    process.exit(0);
  }

  // Check if this is an ExitPlanMode result
  const toolName = input.tool_name || input.toolName || '';
  if (toolName !== 'ExitPlanMode') {
    // Not our trigger - exit silently
    process.exit(0);
  }

  // Find the plan file
  const planPath = extractPlanPath(input);
  if (!planPath) {
    console.log('<plan-mode-l05-warning>');
    console.log('Could not find plan file. L05 integration skipped.');
    console.log('</plan-mode-l05-warning>');
    process.exit(0);
  }

  // Run the L05 adapter
  const adapterResult = runL05Adapter(planPath, projectDir);

  // Save state for execution
  if (adapterResult.success) {
    saveGate2State(adapterResult, projectDir);
  }

  // Output the Gate 2 injection
  console.log(formatInjection(adapterResult));

  process.exit(0);
}

main().catch(error => {
  console.error(`<plan-mode-l05-error>${error.message}</plan-mode-l05-error>`);
  process.exit(0);
});
