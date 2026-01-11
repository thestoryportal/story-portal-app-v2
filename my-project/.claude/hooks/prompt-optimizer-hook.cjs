#!/usr/bin/env node
/**
 * Claude Code UserPromptSubmit hook for automatic prompt optimization.
 *
 * Features:
 * - Fix spelling and typing errors
 * - Improve clarity and specificity
 * - Optimize for Claude Code linguistics
 * - Workflow-specific optimizations with structured sections
 * - Iterative clarifying questions for low-confidence results
 *
 * Workflow Modes (via prefix triggers):
 * - !spec    - Specification: goal, requirements, context
 * - !feedback - Feedback: what to change, direction
 * - !bug     - Bug Report: expected/actual behavior, repro steps
 * - !quick   - Quick Task: minimal optimization
 * - !arch    - Architecture: constraints, goals, trade-offs
 * - !explore - Exploration: scope, depth
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const OPTIMIZER_PATH = path.resolve(__dirname, '../../packages/prompt-optimizer/dist/cli/index.js');

// Workflow mode prefixes - maps prefix to CLI flag value
const WORKFLOW_PREFIXES = {
  '!spec': 'spec',
  '!specification': 'spec',
  '!feedback': 'feedback',
  '!bug': 'bug',
  '!quick': 'quick',
  '!arch': 'arch',
  '!architecture': 'arch',
  '!explore': 'explore',
  '!exploration': 'explore',
};

// Workflow mode full names for display
const WORKFLOW_NAMES = {
  spec: 'Specification',
  feedback: 'Feedback',
  bug: 'Bug Report',
  quick: 'Quick Task',
  arch: 'Architecture',
  explore: 'Exploration',
};

// Workflow mode descriptions
const WORKFLOW_DESCRIPTIONS = {
  spec: 'New feature/project specs with goal, requirements, and context sections',
  feedback: 'Revision direction with what-to-change and direction sections',
  bug: 'Issue description with expected/actual behavior and repro steps',
  quick: 'Simple actions with minimal optimization',
  arch: 'Design decisions with constraints, goals, and trade-offs',
  explore: 'Research/understanding with scope and depth',
};

// Workflow-specific missing section checks and clarifying questions
const WORKFLOW_SECTIONS = {
  spec: {
    name: 'Specification',
    sections: [
      { name: 'Goal/Objective', question: 'What is the primary outcome you want to achieve?', required: true },
      { name: 'Requirements', question: 'What are the must-have requirements or constraints?', required: true },
      { name: 'Context', question: 'How does this integrate with existing systems?', required: false },
    ],
    examples: [
      { header: 'Clarify', question: 'What is the primary goal?', options: ['Add new capability', 'Replace existing feature', 'Improve performance', 'Fix user pain point'] },
      { header: 'Clarify', question: 'What are the key requirements?', options: ['Must be backwards compatible', 'Needs authentication', 'Should scale horizontally', 'Must work offline'] },
    ],
  },
  feedback: {
    name: 'Feedback',
    sections: [
      { name: 'What to Change', question: 'What specific aspect needs to change?', required: true },
      { name: 'Direction', question: 'How should it be different?', required: true },
    ],
    examples: [
      { header: 'Clarify', question: 'What aspect needs to change?', options: ['Visual design/styling', 'Functionality/behavior', 'Performance', 'Code structure'] },
      { header: 'Clarify', question: 'What direction should it go?', options: ['Simpler/minimal', 'More detailed/comprehensive', 'Different approach entirely', 'Fix specific issue'] },
    ],
  },
  bug: {
    name: 'Bug Report',
    sections: [
      { name: 'Expected Behavior', question: 'What should happen?', required: true },
      { name: 'Actual Behavior', question: 'What actually happens instead?', required: true },
      { name: 'Repro Steps', question: 'What are the exact steps to reproduce?', required: true },
      { name: 'Environment', question: 'What browser/OS/version are you using?', required: false },
    ],
    examples: [
      { header: 'Clarify', question: 'What behavior did you EXPECT?', options: ['Form submits once successfully', 'Validation then submit', 'Loading state then complete', 'Error message shown'] },
      { header: 'Clarify', question: 'What ACTUALLY happens?', options: ['Nothing on first clicks', 'Multiple submissions/duplicates', 'Error in console', 'UI freezes/crashes'] },
      { header: 'Clarify', question: 'Steps to reproduce?', options: ['Click submit immediately', 'Fill form then submit', 'Specific sequence of actions', 'Happens randomly'] },
    ],
  },
  arch: {
    name: 'Architecture',
    sections: [
      { name: 'Constraints', question: 'What are the technical or business constraints?', required: true },
      { name: 'Goals', question: 'What qualities matter most (speed, scale, simplicity)?', required: true },
      { name: 'Trade-offs', question: 'What are you willing to compromise on?', required: false },
    ],
    examples: [
      { header: 'Clarify', question: 'What are the key constraints?', options: ['Must use existing tech stack', 'Budget/time limited', 'Team expertise', 'Regulatory/compliance'] },
      { header: 'Clarify', question: 'What qualities matter most?', options: ['Performance/speed', 'Scalability', 'Simplicity/maintainability', 'Cost efficiency'] },
    ],
  },
  explore: {
    name: 'Exploration',
    sections: [
      { name: 'Scope', question: 'How deep should the exploration go?', required: false },
      { name: 'Familiarity', question: 'What do you already know about this topic?', required: false },
    ],
    examples: [
      { header: 'Clarify', question: 'How deep should we explore?', options: ['High-level overview', 'Moderate detail', 'Deep dive with examples', 'Comprehensive analysis'] },
      { header: 'Clarify', question: 'Your familiarity level?', options: ['Complete beginner', 'Some basics', 'Intermediate', 'Advanced, need specifics'] },
    ],
  },
  quick: {
    name: 'Quick Task',
    sections: [],
    examples: [],
  },
};

// Configuration via environment variable PROMPT_OPTIMIZER_MODE
const MODE = process.env.PROMPT_OPTIMIZER_MODE || 'api';

// Toggle file to ENABLE auto-optimize (OFF by default)
const ENABLE_FILE = path.resolve(__dirname, '.optimizer-auto-enabled');

// Minimum prompt length to optimize
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
    const chunks = [];
    process.stdin.setEncoding('utf8');
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    inputData = JSON.parse(chunks.join(''));
  } catch (e) {
    process.exit(0);
  }

  let prompt = inputData.prompt || '';
  let forceOptimize = false;
  let strippedPrefix = false;
  let workflowMode = null;

  // Check for workflow mode prefixes (!spec, !bug, !feedback, etc.)
  const lowerPrompt = prompt.toLowerCase();
  for (const [prefix, mode] of Object.entries(WORKFLOW_PREFIXES)) {
    if (lowerPrompt.startsWith(prefix + ' ') || lowerPrompt === prefix) {
      workflowMode = mode;
      prompt = prompt.slice(prefix.length).trimStart();
      forceOptimize = true;
      strippedPrefix = true;
      break;
    }
  }

  // Check for generic ! prefix (one-off optimization without workflow mode)
  if (!strippedPrefix && prompt.startsWith('!')) {
    prompt = prompt.slice(1).trimStart();
    forceOptimize = true;
    strippedPrefix = true;
  }

  // Check if auto-optimize is enabled
  const autoEnabled = fs.existsSync(ENABLE_FILE);

  // Skip if not enabled and no prefix
  if (!forceOptimize && !autoEnabled) {
    process.exit(0);
  }

  // Skip for short or command-like inputs
  if (prompt.length < MIN_LENGTH || SKIP_PATTERNS.some(p => p.test(prompt.trim()))) {
    if (strippedPrefix) {
      const output = {
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: `<prompt-modification>
The user's prompt started with a prefix but was too short to optimize. Using: "${prompt}"
</prompt-modification>`
        }
      };
      console.log(JSON.stringify(output));
    }
    process.exit(0);
  }

  try {
    const result = await runOptimizer(prompt, workflowMode);

    if (result && result.optimized && result.optimized !== prompt && result.optimized.trim() !== prompt.trim()) {
      const confidence = result.confidence || 0;
      const confidencePercent = Math.round(confidence * 100);
      const detectedWorkflow = result.workflowMode || workflowMode;
      const workflowName = WORKFLOW_NAMES[detectedWorkflow] || 'Auto-detected';
      const workflowDesc = WORKFLOW_DESCRIPTIONS[detectedWorkflow] || '';

      if (confidence >= CONFIDENCE_THRESHOLD) {
        // High confidence - auto-send
        const output = {
          hookSpecificOutput: {
            hookEventName: "UserPromptSubmit",
            additionalContext: generateHighConfidenceContext(prompt, result, confidencePercent, workflowName, workflowDesc)
          }
        };
        console.log(JSON.stringify(output));
      } else {
        // Low confidence - clarifying questions flow
        const output = {
          hookSpecificOutput: {
            hookEventName: "UserPromptSubmit",
            additionalContext: generateLowConfidenceContext(prompt, result, confidencePercent, detectedWorkflow, workflowName)
          }
        };
        console.log(JSON.stringify(output));
      }
    }
    process.exit(0);

  } catch (e) {
    process.stderr.write(`Optimizer hook error: ${e.message}\n`);
    process.exit(0);
  }
}

function generateHighConfidenceContext(original, result, confidencePercent, workflowName, workflowDesc) {
  const workflowInfo = workflowName !== 'Auto-detected'
    ? `\n**Workflow:** ${workflowName} - ${workflowDesc}`
    : '';

  return `<prompt-optimization>
The user's input has been analyzed and optimized for clarity (${confidencePercent}% confidence):

**Original input:** ${original}

**Optimized version:** ${result.optimized}${workflowInfo}

**Category:** ${result.category || 'unknown'} | **Domain:** ${result.domain || 'unknown'}

Please respond to the OPTIMIZED version of the prompt. The optimization corrected spelling/grammar issues and improved clarity while preserving the user's intent.
</prompt-optimization>`;
}

function generateLowConfidenceContext(original, result, confidencePercent, workflowMode, workflowName) {
  const workflowConfig = WORKFLOW_SECTIONS[workflowMode] || null;

  // Build workflow-specific guidance
  let workflowGuidance = '';
  let clarifyingQuestionsExample = '';

  if (workflowConfig && workflowConfig.sections.length > 0) {
    workflowGuidance = `
### ${workflowConfig.name} Mode - Check for Missing Sections:
${workflowConfig.sections.map(s => `- **${s.name}**${s.required ? ' (required)' : ''}: ${s.question}`).join('\n')}`;

    if (workflowConfig.examples.length > 0) {
      clarifyingQuestionsExample = `

### Example Clarifying Questions for ${workflowConfig.name}:
${workflowConfig.examples.map((ex, i) => `
**Question ${i + 1}:**
Use AskUserQuestion with:
- header: "${ex.header}"
- question: "${ex.question}"
- options: ${JSON.stringify(ex.options.map((opt, j) => ({ label: opt, description: `Option ${j + 1}` })))}`).join('\n')}

(User can also type custom answers in "Other" field)`;
    }
  }

  return `<prompt-optimization-review>
The user's input was optimized but confidence is below threshold (${confidencePercent}% < 85%):

**Original input:** ${original}

**Proposed optimization:** ${result.optimized}

**Category:** ${result.category || 'unknown'} | **Domain:** ${result.domain || 'unknown'} | **Workflow:** ${workflowName} | **Confidence:** ${confidencePercent}%

---

## IMPORTANT: Do NOT respond to either prompt yet. Follow this process:

### Step 1: Analyze Ambiguities
Identify specific ambiguities causing low confidence:
- Vague references ("that thing", "you know what I mean")
- Unclear sequencing ("before or after", "maybe")
- Missing specifics (unnamed events, unspecified values)
- Assumed context (references to past conversations)
${workflowGuidance}

### Step 2: Present Action Menu
Use AskUserQuestion with:
- header: "Action"
- question: "Optimization confidence is ${confidencePercent}%. What would you like to do?"
- options:
  1. label: "Clarify & re-optimize", description: "Answer questions to resolve ambiguities"
  2. label: "Use optimized", description: "Proceed with current optimization as-is"
  3. label: "Use original", description: "Keep original prompt, let Claude ask questions"
  4. label: "Cancel", description: "Don't process either prompt"

### Step 3: If "Clarify & re-optimize" Selected

**DO NOT restart workflow selection. Keep workflow as: ${workflowName}**

List the specific ambiguities identified, then use AskUserQuestion for EACH one.
${clarifyingQuestionsExample}

After user answers ALL clarifying questions:
1. Rebuild the prompt incorporating their answers
2. Re-run optimizer with SAME workflow:
   \`\`\`bash
   node "$CLAUDE_PROJECT_DIR/packages/prompt-optimizer/dist/cli/index.js" --json --auto --level 3${workflowMode ? ` --workflow ${workflowMode}` : ''} "ENHANCED_PROMPT"
   \`\`\`
3. Show iteration results:
   - **Iteration:** [N]
   - **Original:** [user's initial input]
   - **Clarifications added:** [list what was added]
   - **New optimized:** [result]
   - **Confidence:** [X]%
4. Return to Step 2 action menu
5. Repeat until confidence ≥85% or user accepts

### Step 4: Execute Chosen Action
- "Use optimized" → Respond to the optimized prompt
- "Use original" → Respond to original prompt
- "Cancel" → Acknowledge and wait for new input
</prompt-optimization-review>`;
}

function runOptimizer(prompt, workflowMode) {
  return new Promise((resolve, reject) => {
    const args = [OPTIMIZER_PATH, '--json', '--auto', '--level', '3'];

    if (MODE === 'local') {
      args.push('--local');
    } else if (MODE === 'mock') {
      args.push('--mock');
    }

    if (workflowMode) {
      args.push('--workflow', workflowMode);
    }

    args.push(prompt);

    const child = spawn('node', args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.resolve(__dirname, '../..')
    });

    let stdout = '';
    let stderr = '';

    const timeoutMs = MODE === 'local' ? 120000 : 15000;
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error('Optimizer timed out'));
    }, timeoutMs);

    child.stdout.on('data', (data) => { stdout += data.toString(); });
    child.stderr.on('data', (data) => { stderr += data.toString(); });

    child.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0 || code === null) {
        try {
          const result = JSON.parse(stdout.trim());
          if (result.wasOptimized && result.optimized) {
            resolve({
              optimized: result.optimized,
              confidence: result.confidence || 0,
              category: result.category,
              domain: result.domain,
              workflowMode: result.workflowMode,
              workflowModeSource: result.workflowModeSource
            });
          } else {
            resolve(null);
          }
        } catch (e) {
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
