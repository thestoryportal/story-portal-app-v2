#!/usr/bin/env node
/**
 * Claude Code UserPromptSubmit hook for automatic prompt optimization.
 *
 * Integrates the prompt-optimizer CLI to:
 * - Fix spelling and typing errors
 * - Improve clarity and specificity
 * - Optimize for Claude Code linguistics
 * - Expand or condense as needed
 */

const { spawn } = require('child_process');
const path = require('path');

const OPTIMIZER_PATH = path.resolve(__dirname, '../../packages/prompt-optimizer/dist/cli/index.js');

// Configuration via environment variable PROMPT_OPTIMIZER_MODE
// Options:
//   'api'   - Fast (~500ms), uses Anthropic API (requires ANTHROPIC_API_KEY)
//   'local' - Slow (~90s), uses Ollama local LLM (free)
//   'mock'  - Instant, basic transformations only (default for testing)
const MODE = process.env.PROMPT_OPTIMIZER_MODE || 'api';

// Minimum prompt length to optimize (skip very short inputs)
const MIN_LENGTH = 10;

// Skip patterns (commands, single words, etc.)
const SKIP_PATTERNS = [
  /^\/\w+/,           // Slash commands
  /^y(es)?$/i,        // Yes confirmations
  /^n(o)?$/i,         // No confirmations
  /^ok$/i,            // OK
  /^done$/i,          // Done
  /^stop$/i,          // Stop
  /^cancel$/i,        // Cancel
  /^continue$/i,      // Continue
  /^q(uit)?$/i,       // Quit
  /^exit$/i,          // Exit
  /^\d+$/,            // Just numbers
  /^commit/i,         // Commit commands
  /^push/i,           // Push commands
];

async function main() {
  let inputData;

  try {
    // Read JSON input from stdin
    const chunks = [];
    process.stdin.setEncoding('utf8');

    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    const input = chunks.join('');
    inputData = JSON.parse(input);
  } catch (e) {
    // If we can't parse input, just exit silently (don't block)
    process.exit(0);
  }

  const prompt = inputData.prompt || '';

  // Skip optimization for short or command-like inputs
  if (prompt.length < MIN_LENGTH || SKIP_PATTERNS.some(p => p.test(prompt.trim()))) {
    process.exit(0);
  }

  try {
    const optimized = await runOptimizer(prompt);

    if (optimized && optimized !== prompt && optimized.trim() !== prompt.trim()) {
      // Output context that tells Claude about the optimization
      const output = {
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: `<prompt-optimization>
The user's input has been analyzed and optimized for clarity:

**Original input:** ${prompt}

**Optimized version:** ${optimized}

Please respond to the OPTIMIZED version of the prompt. The optimization corrected any spelling/grammar issues and improved clarity while preserving the user's intent.
</prompt-optimization>`
        }
      };
      console.log(JSON.stringify(output));
    }
    // If not optimized or same, just exit without output (passes through unchanged)
    process.exit(0);

  } catch (e) {
    // On error, don't block - just let the original through
    process.stderr.write(`Optimizer hook error: ${e.message}\n`);
    process.exit(0);
  }
}

function runOptimizer(prompt) {
  return new Promise((resolve, reject) => {
    // Build args based on mode - use --json for clean machine-readable output
    const args = [OPTIMIZER_PATH, '--json', '--auto'];
    if (MODE === 'local') {
      args.push('--local');
    } else if (MODE === 'mock') {
      args.push('--mock');
    }
    // 'api' mode uses Anthropic API (default, no flag needed)
    args.push(prompt);

    const child = spawn('node', args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.resolve(__dirname, '../..')
    });

    let stdout = '';
    let stderr = '';

    // Manual timeout - local LLM needs longer
    const timeoutMs = MODE === 'local' ? 120000 : 15000;
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error('Optimizer timed out'));
    }, timeoutMs);

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0 || code === null) {
        try {
          // Parse JSON output
          const result = JSON.parse(stdout.trim());
          // Only return optimized if it was actually optimized
          if (result.wasOptimized && result.optimized) {
            resolve(result.optimized);
          } else {
            resolve(null); // Pass through unchanged
          }
        } catch (e) {
          // If JSON parse fails, return null to pass through
          resolve(null);
        }
      } else {
        reject(new Error(stderr || `Exit code ${code}`));
      }
    });

    child.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

main();
