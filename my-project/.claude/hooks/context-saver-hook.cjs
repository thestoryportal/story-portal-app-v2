#!/usr/bin/env node
/**
 * Claude Code Context Saver Hook v3.0
 *
 * PURPOSE:
 * Automatic context saving and session tracking for crash recovery.
 * Runs on tool use events to track session activity and trigger saves.
 *
 * TRIGGERS:
 * - PreToolUse: Record heartbeat
 * - PostToolUse: If file-modifying tool -> queue context save
 *
 * DESIGN PRINCIPLES:
 * 1. Non-blocking - writes to files for async processing
 * 2. Lightweight - minimal processing in hook
 * 3. Recovery-focused - always maintain recoverable state
 * 4. Works without database - file-first approach
 *
 * FILES WRITTEN:
 * - .session-heartbeat.json: Last activity timestamp for crash detection
 * - .pending-saves.json: Queue of contexts needing save to database
 * - .tool-history.json: Recent tool usage for recovery context
 */

const fs = require('fs');
const path = require('path');

// === CONFIGURATION ===
const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const CONTEXTS_DIR = path.join(PROJECT_DIR, '.claude', 'contexts');
const HEARTBEAT_PATH = path.join(CONTEXTS_DIR, '.session-heartbeat.json');
const PENDING_SAVES_PATH = path.join(CONTEXTS_DIR, '.pending-saves.json');
const TOOL_HISTORY_PATH = path.join(CONTEXTS_DIR, '.tool-history.json');
const SESSION_STATE_PATH = path.join(CONTEXTS_DIR, '.session-state.json');

// Tools that modify files and should trigger context saves
const FILE_MODIFYING_TOOLS = [
  'Write',
  'Edit',
  'NotebookEdit',
  'Bash' // May modify files via shell
];

// Maximum entries to keep in history
const MAX_TOOL_HISTORY = 50;
const MAX_PENDING_SAVES = 20;

// === MAIN ===
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

  const hookEvent = inputData.hookEventName;
  const toolName = inputData.toolName || 'unknown';
  const toolInput = inputData.toolInput || {};

  // Ensure contexts directory exists
  ensureDir(CONTEXTS_DIR);

  // Get session ID from session state
  const sessionId = getSessionId();

  // === HANDLE EVENTS ===
  if (hookEvent === 'PreToolUse') {
    // Record heartbeat before tool execution
    recordHeartbeat(sessionId, toolName);
  } else if (hookEvent === 'PostToolUse') {
    // Record tool usage
    recordToolUsage(sessionId, toolName, toolInput, inputData.toolOutput);

    // Check if tool modifies files
    if (shouldTriggerSave(toolName, toolInput)) {
      queueContextSave(sessionId, toolName, toolInput);
    }
  }

  // Always exit cleanly - hooks should not block
  process.exit(0);
}

// === HEARTBEAT ===

function recordHeartbeat(sessionId, toolName) {
  try {
    const heartbeat = {
      sessionId,
      timestamp: new Date().toISOString(),
      lastTool: toolName,
      projectDir: PROJECT_DIR
    };
    fs.writeFileSync(HEARTBEAT_PATH, JSON.stringify(heartbeat, null, 2));
  } catch (e) {
    // Ignore errors - heartbeat is best-effort
  }
}

// === TOOL USAGE TRACKING ===

function recordToolUsage(sessionId, toolName, toolInput, toolOutput) {
  try {
    let history = [];
    try {
      history = JSON.parse(fs.readFileSync(TOOL_HISTORY_PATH, 'utf8'));
    } catch (e) {
      history = [];
    }

    // Add new entry
    history.push({
      sessionId,
      timestamp: new Date().toISOString(),
      tool: toolName,
      input: summarizeInput(toolName, toolInput),
      success: !toolOutput?.error
    });

    // Keep only recent entries
    if (history.length > MAX_TOOL_HISTORY) {
      history = history.slice(-MAX_TOOL_HISTORY);
    }

    fs.writeFileSync(TOOL_HISTORY_PATH, JSON.stringify(history, null, 2));
  } catch (e) {
    // Ignore errors
  }
}

function summarizeInput(toolName, input) {
  // Create a summarized version of tool input for history
  // Avoid storing full file contents
  if (!input) return {};

  const summary = {};

  if (toolName === 'Write' || toolName === 'Edit') {
    summary.file = input.file_path || input.path;
    if (input.content) {
      summary.contentLength = input.content.length;
    }
  } else if (toolName === 'Read') {
    summary.file = input.file_path || input.path;
  } else if (toolName === 'Bash') {
    summary.command = (input.command || '').slice(0, 100);
  } else if (toolName === 'Grep' || toolName === 'Glob') {
    summary.pattern = input.pattern;
    summary.path = input.path;
  } else {
    // Generic summary - just keys
    summary.keys = Object.keys(input).slice(0, 5);
  }

  return summary;
}

// === CONTEXT SAVE QUEUE ===

function shouldTriggerSave(toolName, toolInput) {
  // Check if this tool typically modifies files
  if (FILE_MODIFYING_TOOLS.includes(toolName)) {
    // For Bash, check if command looks like it modifies files
    if (toolName === 'Bash') {
      const cmd = (toolInput.command || '').toLowerCase();
      const modifyPatterns = [
        'echo', '>', '>>', 'tee',
        'mv', 'cp', 'rm', 'mkdir', 'rmdir',
        'touch', 'chmod', 'chown',
        'npm install', 'npm update', 'npm uninstall',
        'git commit', 'git checkout', 'git merge', 'git reset',
        'sed -i', 'awk'
      ];
      return modifyPatterns.some(p => cmd.includes(p));
    }
    return true;
  }
  return false;
}

function queueContextSave(sessionId, toolName, toolInput) {
  try {
    let pending = [];
    try {
      pending = JSON.parse(fs.readFileSync(PENDING_SAVES_PATH, 'utf8'));
    } catch (e) {
      pending = [];
    }

    // Add save request
    pending.push({
      sessionId,
      timestamp: new Date().toISOString(),
      trigger: {
        tool: toolName,
        file: toolInput.file_path || toolInput.path || extractFileFromBash(toolInput.command)
      },
      status: 'pending'
    });

    // Keep only recent entries
    if (pending.length > MAX_PENDING_SAVES) {
      pending = pending.slice(-MAX_PENDING_SAVES);
    }

    fs.writeFileSync(PENDING_SAVES_PATH, JSON.stringify(pending, null, 2));
  } catch (e) {
    // Ignore errors
  }
}

function extractFileFromBash(command) {
  if (!command) return null;

  // Try to extract file path from common bash patterns
  const patterns = [
    />\s*["']?([^\s"']+)/,      // redirect: > file
    /tee\s+["']?([^\s"']+)/,    // tee file
    /mv\s+\S+\s+["']?([^\s"']+)/, // mv src dest
    /cp\s+\S+\s+["']?([^\s"']+)/  // cp src dest
  ];

  for (const pattern of patterns) {
    const match = command.match(pattern);
    if (match) return match[1];
  }

  return null;
}

// === HELPERS ===

function ensureDir(dir) {
  try {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  } catch (e) {
    // Ignore
  }
}

function getSessionId() {
  try {
    const state = JSON.parse(fs.readFileSync(SESSION_STATE_PATH, 'utf8'));
    return state.sessionId || 'unknown';
  } catch (e) {
    return 'unknown';
  }
}

// === RUN ===
main();
