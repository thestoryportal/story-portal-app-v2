#!/usr/bin/env node
/**
 * Session Start Hook - Minimal Context Injection
 *
 * Runs at session start to:
 * 1. Check for crash recovery needs
 * 2. Inject minimal project context (NOT full task details)
 * 3. List available tasks (names only, not full content)
 *
 * Reads from BOTH:
 * - _registry.json (MCP-managed)
 * - _local_tasks.json (local-only, never overwritten)
 * - _hot_context.json (fast-access global context)
 *
 * Full context is fetched ON DEMAND via MCP tools.
 */

const fs = require('fs');
const path = require('path');

// Read hook input from stdin
let inputData = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => inputData += chunk);
process.stdin.on('end', async () => {
  try {
    const input = JSON.parse(inputData || '{}');
    const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

    // Determine session start reason
    const reason = input.hook_event_name === 'SessionStart'
      ? (input.reason || 'startup')
      : 'prompt';

    const contextLines = [];

    // Only inject on actual session start, not resume or compact
    if (reason === 'startup' || reason === 'clear') {

      // 1. Load hot context file (synced from MCP)
      const hotContextPath = path.join(projectDir, '.claude/contexts/_hot_context.json');
      const registryPath = path.join(projectDir, '.claude/contexts/_registry.json');
      const localTasksPath = path.join(projectDir, '.claude/contexts/_local_tasks.json');

      let hotContext = null;
      let allTasks = {};

      try {
        if (fs.existsSync(hotContextPath)) {
          hotContext = JSON.parse(fs.readFileSync(hotContextPath, 'utf8'));
        }
      } catch (e) { /* ignore */ }

      // Load MCP registry tasks
      try {
        if (fs.existsSync(registryPath)) {
          const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
          if (registry?.tasks) {
            allTasks = { ...allTasks, ...registry.tasks };
          }
        }
      } catch (e) { /* ignore */ }

      // Load local tasks (merge)
      try {
        if (fs.existsSync(localTasksPath)) {
          const localTasks = JSON.parse(fs.readFileSync(localTasksPath, 'utf8'));
          if (localTasks?.tasks) {
            allTasks = { ...allTasks, ...localTasks.tasks };
          }
        }
      } catch (e) { /* ignore */ }

      // 2. Build minimal context injection
      contextLines.push('<session-context type="auto-injected" size="minimal">');

      // Project identification
      if (hotContext?.projectId) {
        contextLines.push(`Project: ${hotContext.projectId}`);
      }

      // Tech stack (one line) - check both old and new structure
      const techStack = hotContext?.global?.techStack || hotContext?.globalContext?.techStack;
      if (techStack) {
        contextLines.push(`Stack: ${techStack.join(', ')}`);
      }

      // Hard rules (critical constraints)
      const hardRules = hotContext?.global?.hardRules || hotContext?.globalContext?.hardRules;
      if (hardRules?.length) {
        contextLines.push('');
        contextLines.push('Critical Rules:');
        hardRules.forEach(rule => {
          contextLines.push(`- ${rule}`);
        });
      }

      // Available tasks (names and status only - NOT full content)
      if (Object.keys(allTasks).length > 0) {
        const taskList = Object.entries(allTasks)
          .map(([id, task]) => `  - ${id}: ${task.name} [${task.status || 'unknown'}]`)
          .join('\n');

        contextLines.push('');
        contextLines.push('Available Tasks (use get_unified_context for details):');
        contextLines.push(taskList);
      }

      // Recovery hint
      contextLines.push('');
      contextLines.push('Context Tools Available:');
      contextLines.push('- check_recovery() - if resuming interrupted work');
      contextLines.push('- get_unified_context(taskId) - for full task details');
      contextLines.push('- /context - manual context management skill');

      contextLines.push('</session-context>');
    }

    // Output context to stdout (will be injected into conversation)
    if (contextLines.length > 0) {
      console.log(contextLines.join('\n'));
    }

    process.exit(0);
  } catch (error) {
    // Silent failure - don't break the session
    console.error(`Session start hook error: ${error.message}`);
    process.exit(0); // Exit 0 to not block session
  }
});
