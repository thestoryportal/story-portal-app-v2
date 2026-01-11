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
const fs = require('fs');

const OPTIMIZER_PATH = path.resolve(__dirname, '../../packages/prompt-optimizer/dist/cli/index.js');

// Configuration via environment variable PROMPT_OPTIMIZER_MODE
// Options:
//   'api'   - Fast (~500ms), uses Anthropic API (requires ANTHROPIC_API_KEY)
//   'local' - Slow (~90s), uses Ollama local LLM (free)
//   'mock'  - Instant, basic transformations only (default for testing)
const MODE = process.env.PROMPT_OPTIMIZER_MODE || 'api';

// Toggle file to ENABLE auto-optimize (auto-optimize is OFF by default)
const ENABLE_FILE = path.resolve(__dirname, '.optimizer-auto-enabled');

// Minimum prompt length to optimize (skip very short inputs)
const MIN_LENGTH = 10;

// Confidence threshold for auto-send (below this, ask for approval)
const CONFIDENCE_THRESHOLD = 0.85;

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

  let prompt = inputData.prompt || '';
  let forceOptimize = false;
  let strippedPrefix = false;

  // Check for ! prefix (one-off optimization trigger)
  if (prompt.startsWith('!')) {
    prompt = prompt.slice(1).trimStart(); // Remove ! and any leading space
    forceOptimize = true;
    strippedPrefix = true;
  }

  // Check if auto-optimize is enabled (it's OFF by default)
  const autoEnabled = fs.existsSync(ENABLE_FILE);

  // Skip if auto-optimize is not enabled AND no ! prefix
  if (!forceOptimize && !autoEnabled) {
    process.exit(0);
  }

  // Skip optimization for short or command-like inputs
  if (prompt.length < MIN_LENGTH || SKIP_PATTERNS.some(p => p.test(prompt.trim()))) {
    // If ! prefix was used but prompt is too short/skip pattern, still need to pass through
    // the modified prompt (without the !)
    if (strippedPrefix) {
      const output = {
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: `<prompt-modification>
The user's prompt started with "!" but was too short to optimize. Using prompt without prefix: "${prompt}"
</prompt-modification>`
        }
      };
      console.log(JSON.stringify(output));
    }
    process.exit(0);
  }

  try {
    const result = await runOptimizer(prompt);

    if (result && result.optimized && result.optimized !== prompt && result.optimized.trim() !== prompt.trim()) {
      const confidence = result.confidence || 0;
      const confidencePercent = Math.round(confidence * 100);

      if (confidence >= CONFIDENCE_THRESHOLD) {
        // High confidence - auto-send
        const output = {
          hookSpecificOutput: {
            hookEventName: "UserPromptSubmit",
            additionalContext: `<prompt-optimization>
The user's input has been analyzed and optimized for clarity (${confidencePercent}% confidence):

**Original input:** ${prompt}

**Optimized version:** ${result.optimized}

Please respond to the OPTIMIZED version of the prompt. The optimization corrected any spelling/grammar issues and improved clarity while preserving the user's intent.
</prompt-optimization>`
          }
        };
        console.log(JSON.stringify(output));
      } else {
        // Low confidence - identify ambiguities and ask clarifying questions
        const output = {
          hookSpecificOutput: {
            hookEventName: "UserPromptSubmit",
            additionalContext: `<prompt-optimization-review>
The user's input was optimized but confidence is below threshold (${confidencePercent}% < 85%):

**Original input:** ${prompt}

**Proposed optimization:** ${result.optimized}

**Category:** ${result.category || 'unknown'} | **Domain:** ${result.domain || 'unknown'} | **Confidence:** ${confidencePercent}%

IMPORTANT: Do NOT respond to either prompt yet. Follow this process:

## Step 1: Analyze Ambiguities
Identify specific ambiguities in the original prompt that are causing low confidence. Look for:
- Vague references ("that thing", "you know what I mean", "the ones we discussed")
- Unclear sequencing ("before or after", "maybe", "I don't remember")
- Missing specifics (unnamed events, unspecified values, unclear scope)
- Assumed context (references to past conversations)

## Step 2: Present Options
Use AskUserQuestion with:
- header: "Action"
- question: "Optimization confidence is ${confidencePercent}% due to ambiguities. What would you like to do?"
- options:
  1. "Clarify & re-optimize" - Answer questions to resolve ambiguities, then re-optimize
  2. "Use optimized" - Proceed with current optimization as-is
  3. "Use original" - Keep original prompt, let Claude ask questions
  4. "Cancel" - Don't process either prompt

## Step 3: If "Clarify & re-optimize" selected
List the specific ambiguities you identified, then use AskUserQuestion to ask about EACH ambiguity. For example:
- "Validation timing: Should validation happen before or after email confirmation?"
- "Analytics events: Which specific events are needed? (e.g., signup_started, email_verified)"

After user answers ALL clarifying questions:
1. Rebuild the prompt incorporating their answers
2. Run the optimizer on the NEW prompt:
   node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3 "NEW_PROMPT"
3. Show the new result with confidence
4. If still below 85%, repeat this process
5. If 85%+, auto-send or ask for final confirmation

## Step 4: Execute chosen action
Wait for all user inputs before responding to the final prompt.
</prompt-optimization-review>`
          }
        };
        console.log(JSON.stringify(output));
      }
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
    // Default to level 3 (thorough) for highest quality optimization
    const args = [OPTIMIZER_PATH, '--json', '--auto', '--level', '3'];
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
          // Only return result if it was actually optimized
          if (result.wasOptimized && result.optimized) {
            resolve({
              optimized: result.optimized,
              confidence: result.confidence || 0,
              category: result.category,
              domain: result.domain
            });
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
