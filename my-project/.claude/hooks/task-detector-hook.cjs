#!/usr/bin/env node
/**
 * Task Detector Hook - Keyword-Based Context Injection
 *
 * Runs on UserPromptSubmit to:
 * 1. Detect task keywords in user's prompt
 * 2. Inject MINIMAL task context (resume prompt only)
 * 3. Full details fetched via MCP tools on demand
 *
 * Reads from BOTH:
 * - _registry.json (MCP-managed, may be overwritten by sync)
 * - _local_tasks.json (local-only, never overwritten)
 *
 * This keeps context lean while providing useful hints.
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
    const userPrompt = (input.prompt || '').toLowerCase();

    // Skip if prompt is too short or a command
    if (userPrompt.length < 10 || userPrompt.startsWith('/')) {
      process.exit(0);
    }

    // Load tasks from both sources
    const registryPath = path.join(projectDir, '.claude/contexts/_registry.json');
    const localTasksPath = path.join(projectDir, '.claude/contexts/_local_tasks.json');

    let allTasks = {};

    // Load MCP registry tasks
    try {
      if (fs.existsSync(registryPath)) {
        const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
        if (registry?.tasks) {
          allTasks = { ...allTasks, ...registry.tasks };
        }
      }
    } catch (e) { /* ignore */ }

    // Load local tasks (these take precedence for keywords)
    try {
      if (fs.existsSync(localTasksPath)) {
        const localTasks = JSON.parse(fs.readFileSync(localTasksPath, 'utf8'));
        if (localTasks?.tasks) {
          // Merge, with local tasks overriding registry for same ID
          allTasks = { ...allTasks, ...localTasks.tasks };
        }
      }
    } catch (e) { /* ignore */ }

    if (Object.keys(allTasks).length === 0) {
      process.exit(0);
    }

    // Detect task from keywords
    let matchedTask = null;
    let matchedTaskId = null;
    let maxScore = 0;

    for (const [taskId, task] of Object.entries(allTasks)) {
      if (!task.keywords?.length) continue;

      let score = 0;
      for (const keyword of task.keywords) {
        if (userPrompt.includes(keyword.toLowerCase())) {
          score += keyword.length; // Longer keywords = more specific = higher score
        }
      }

      if (score > maxScore) {
        maxScore = score;
        matchedTask = task;
        matchedTaskId = taskId;
      }
    }

    // Only inject if we found a match with sufficient confidence
    if (!matchedTask || maxScore < 5) {
      process.exit(0);
    }

    // Load task's context file for minimal injection
    const contextFilePath = path.join(projectDir, '.claude/contexts', matchedTask.contextFile);
    let taskContext = null;

    try {
      if (fs.existsSync(contextFilePath)) {
        taskContext = JSON.parse(fs.readFileSync(contextFilePath, 'utf8'));
      }
    } catch (e) {
      // Fall back to registry info only
    }

    // Build MINIMAL context injection
    const contextLines = [];
    contextLines.push(`<task-context task="${matchedTaskId}" type="auto-detected" size="minimal">`);
    contextLines.push(`Task: ${matchedTask.name}`);

    if (taskContext?.immediateContext) {
      const ic = taskContext.immediateContext;
      if (ic.workingOn) {
        contextLines.push(`Working on: ${ic.workingOn}`);
      }
      if (ic.lastAction) {
        contextLines.push(`Last action: ${ic.lastAction}`);
      }
      if (ic.nextStep) {
        contextLines.push(`Next step: ${ic.nextStep}`);
      }
      if (ic.blockers?.length) {
        contextLines.push(`Blockers: ${ic.blockers.join(', ')}`);
      }
    }

    // Resume prompt (most important - concise summary)
    if (taskContext?.resumePrompt) {
      contextLines.push('');
      contextLines.push(`Resume: ${taskContext.resumePrompt}`);
    }

    // Hint for full context
    contextLines.push('');
    contextLines.push(`For full details: get_unified_context({ taskId: "${matchedTaskId}" })`);
    contextLines.push('</task-context>');

    console.log(contextLines.join('\n'));
    process.exit(0);

  } catch (error) {
    // Silent failure
    process.exit(0);
  }
});
