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

    // L05 error pattern detection - inject fixes even without full task match
    const L05_ERROR_PATTERNS = [
      '401', 'unauthorized', 'e5106', 'e5101', 'e5600',
      'json parse', 'datetime.utcnow', 'deprecation', 'deprecationwarning'
    ];

    let errorPatternMatch = false;
    let matchedErrorPattern = null;
    for (const pattern of L05_ERROR_PATTERNS) {
      if (userPrompt.includes(pattern.toLowerCase())) {
        errorPatternMatch = true;
        matchedErrorPattern = pattern;
        break;
      }
    }

    // Cross-layer detection for non-L05 tasks
    const CROSS_LAYER_TRIGGERS = [
      'l05 bridge', 'planning service', 'model gateway bridge',
      'l01 client', 'goal decomposer', 'execution plan'
    ];

    let crossLayerMatch = false;
    let matchedCrossLayer = null;
    for (const trigger of CROSS_LAYER_TRIGGERS) {
      if (userPrompt.includes(trigger.toLowerCase())) {
        crossLayerMatch = true;
        matchedCrossLayer = trigger;
        break;
      }
    }

    // Only inject if we found a match with sufficient confidence
    // OR if we detected L05 error patterns / cross-layer triggers
    if (!matchedTask || maxScore < 5) {
      // Check if we should inject L05 fixes context anyway
      if (errorPatternMatch || crossLayerMatch) {
        // Force L05 task for error/cross-layer injection
        matchedTask = allTasks['test-task-planning'];
        matchedTaskId = 'test-task-planning';
        if (!matchedTask) {
          process.exit(0);
        }
      } else {
        process.exit(0);
      }
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

    // L05 Supplemental Context - inject relevant fixes on error pattern match
    if (matchedTaskId === 'test-task-planning' && (errorPatternMatch || crossLayerMatch)) {
      contextLines.push('');
      contextLines.push('<l05-quick-fixes>');

      // Load l05-known-fixes.yaml if error pattern matched
      if (errorPatternMatch) {
        const fixesPath = path.join(projectDir, '.claude/contexts/l05/l05-known-fixes.yaml');
        try {
          if (fs.existsSync(fixesPath)) {
            const fixesContent = fs.readFileSync(fixesPath, 'utf8');
            // Extract relevant fix based on pattern
            if (matchedErrorPattern.includes('401') || matchedErrorPattern.includes('unauthorized')) {
              contextLines.push('Fix P0_auth: Add X-API-Key header, use L01_API_KEY env var');
              contextLines.push('Files: shared/clients.py, L05_planning/integration/l01_bridge.py');
            } else if (matchedErrorPattern.includes('e5106') || matchedErrorPattern.includes('json parse')) {
              contextLines.push('Fix P2_llm_validation: Multi-strategy JSON extraction + retry logic');
              contextLines.push('File: L05_planning/services/goal_decomposer.py');
            } else if (matchedErrorPattern.includes('datetime') || matchedErrorPattern.includes('deprecation')) {
              contextLines.push('Fix P1_datetime: Replace datetime.utcnow() with datetime.now(timezone.utc)');
              contextLines.push('Files: L05 models/services, L04 providers, L02 bridges');
            } else if (matchedErrorPattern.includes('e5101') || matchedErrorPattern.includes('e5600')) {
              contextLines.push('Fix: Use execute_plan_direct(plan) instead of execute_plan(id)');
              contextLines.push('File: L05_planning/services/planning_service.py');
            }
          }
        } catch (e) { /* ignore */ }
      }

      // Load l05-cross-layer.yaml if cross-layer trigger matched
      if (crossLayerMatch) {
        const crossLayerPath = path.join(projectDir, '.claude/contexts/l05/l05-cross-layer.yaml');
        try {
          if (fs.existsSync(crossLayerPath)) {
            // Extract relevant boundary based on trigger
            if (matchedCrossLayer.includes('model gateway') || matchedCrossLayer.includes('l04')) {
              contextLines.push('Boundary L05_L04: ModelGatewayBridge - JSON parse errors, datetime warnings');
            } else if (matchedCrossLayer.includes('l01') || matchedCrossLayer.includes('bridge')) {
              contextLines.push('Boundary L05_L01: L01Client/L01Bridge - 401 Unauthorized, missing API key');
            } else if (matchedCrossLayer.includes('execution') || matchedCrossLayer.includes('planning')) {
              contextLines.push('Boundary L05_L02: AgentExecutor - use execute_plan_direct(plan)');
            }
          }
        } catch (e) { /* ignore */ }
      }

      contextLines.push('Full fixes: .claude/contexts/l05/l05-known-fixes.yaml');
      contextLines.push('</l05-quick-fixes>');
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
