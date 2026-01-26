#!/usr/bin/env node
/**
 * Post-Compact Recovery Hint
 *
 * This hook runs on SessionStart with reason='compact' to inject
 * a minimal recovery hint after compaction occurs.
 *
 * It reminds Claude to check for saved context if resuming complex work.
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

    // Only run on compact resume
    if (input.reason !== 'compact') {
      process.exit(0);
    }

    // Check if there was pre-compaction state saved
    const sessionStatePath = path.join(projectDir, '.claude/contexts/.session-state.json');
    let sessionState = null;

    try {
      if (fs.existsSync(sessionStatePath)) {
        sessionState = JSON.parse(fs.readFileSync(sessionStatePath, 'utf8'));
      }
    } catch (e) { /* ignore */ }

    if (sessionState?.preCompaction?.needsRecoveryCheck) {
      // Inject recovery hint
      console.log('<post-compaction-hint>');
      console.log('Context was compacted. If resuming complex work:');
      console.log('- Call check_recovery() to verify session state');
      console.log('- Call get_unified_context(taskId) for task details');
      console.log('- Saved context may contain information lost in compaction');
      console.log('</post-compaction-hint>');

      // Clear the recovery check flag
      sessionState.preCompaction.needsRecoveryCheck = false;
      sessionState.postCompaction = {
        timestamp: new Date().toISOString(),
        hintInjected: true
      };
      fs.writeFileSync(sessionStatePath, JSON.stringify(sessionState, null, 2));
    }

    process.exit(0);

  } catch (error) {
    process.exit(0);
  }
});
