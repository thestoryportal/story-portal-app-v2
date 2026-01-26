#!/usr/bin/env node
/**
 * Pre-Compact Hook - Auto-Save Context Before Compaction
 *
 * Runs before context compaction to:
 * 1. Save current session state to hot context file
 * 2. Update session activity timestamp
 * 3. Ensure context can be recovered post-compaction
 *
 * Note: This saves to FILE only (fast). Full MCP persistence
 * should be done via explicit save_context_snapshot calls.
 */

const fs = require('fs');
const path = require('path');

let inputData = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => inputData += chunk);
process.stdin.on('end', async () => {
  try {
    const input = JSON.parse(inputData || '{}');
    const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
    const sessionId = input.session_id || 'unknown';
    const compactReason = input.reason || 'auto';

    const contextsDir = path.join(projectDir, '.claude/contexts');

    // Ensure contexts directory exists
    if (!fs.existsSync(contextsDir)) {
      fs.mkdirSync(contextsDir, { recursive: true });
    }

    // Update session activity file
    const sessionActivityPath = path.join(contextsDir, '.session-activity.json');
    let sessionActivity = {};

    try {
      if (fs.existsSync(sessionActivityPath)) {
        sessionActivity = JSON.parse(fs.readFileSync(sessionActivityPath, 'utf8'));
      }
    } catch (e) { /* ignore */ }

    sessionActivity.lastCompaction = {
      timestamp: new Date().toISOString(),
      sessionId,
      reason: compactReason
    };
    sessionActivity.compactionCount = (sessionActivity.compactionCount || 0) + 1;

    fs.writeFileSync(sessionActivityPath, JSON.stringify(sessionActivity, null, 2));

    // Update session state file with pre-compaction marker
    const sessionStatePath = path.join(contextsDir, '.session-state.json');
    let sessionState = {};

    try {
      if (fs.existsSync(sessionStatePath)) {
        sessionState = JSON.parse(fs.readFileSync(sessionStatePath, 'utf8'));
      }
    } catch (e) { /* ignore */ }

    sessionState.preCompaction = {
      timestamp: new Date().toISOString(),
      sessionId,
      reason: compactReason,
      needsRecoveryCheck: true
    };

    fs.writeFileSync(sessionStatePath, JSON.stringify(sessionState, null, 2));

    // Output message for verbose mode
    console.log(`Pre-compaction state saved (reason: ${compactReason})`);
    process.exit(0);

  } catch (error) {
    console.error(`Pre-compact hook error: ${error.message}`);
    process.exit(0); // Don't block compaction
  }
});
