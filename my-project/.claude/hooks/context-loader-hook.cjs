#!/usr/bin/env node
/**
 * Claude Code Context Loader Hook v3.0
 *
 * DESIGN PRINCIPLES:
 * 1. ALWAYS loads context (no dependencies)
 * 2. PRIMARY: Read from _hot_context.json (synced from PostgreSQL/Redis)
 * 3. FALLBACK: File-based contexts for backward compatibility
 * 4. Registers session activity for crash recovery
 * 5. Works with zero configuration (graceful degradation)
 * 6. Portable to any project (copy .claude/contexts/ structure)
 *
 * DATA FLOW:
 * 1. Hook reads _hot_context.json (fastest, pre-synced from databases)
 * 2. If stale or missing, falls back to file-based registry
 * 3. Writes session heartbeat for recovery tracking
 * 4. Returns context via additionalContext for prompt injection
 *
 * v3.0 CHANGES:
 * - Hot context file support (_hot_context.json)
 * - Session activity tracking for crash recovery
 * - Integration with Context Orchestrator MCP
 * - Staleness detection and fallback
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// === CONFIGURATION ===
const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const CONTEXTS_DIR = path.join(PROJECT_DIR, '.claude', 'contexts');
const HOT_CONTEXT_PATH = path.join(CONTEXTS_DIR, '_hot_context.json');
const REGISTRY_PATH = path.join(CONTEXTS_DIR, '_registry.json');
const SHARED_PATH = path.join(CONTEXTS_DIR, 'shared', 'project-constants.json');
const CLAUDE_MD_PATH = path.join(PROJECT_DIR, 'CLAUDE.md');

// Session tracking
const SESSION_STATE_PATH = path.join(CONTEXTS_DIR, '.session-state.json');
const SESSION_ACTIVITY_PATH = path.join(CONTEXTS_DIR, '.session-activity.json');
const SESSION_TIMEOUT_HOURS = 4;
const HOT_CONTEXT_STALE_MINUTES = 5;

// Generate or load session ID
function getSessionId() {
  const state = loadSessionState();
  if (state.sessionId) {
    return state.sessionId;
  }
  return crypto.randomUUID();
}

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

  const prompt = inputData.prompt || '';

  // Skip for slash commands
  if (prompt.trim().startsWith('/')) {
    process.exit(0);
  }

  const sessionId = getSessionId();
  const sessionState = loadSessionState();
  const isFirstPrompt = !sessionState.contextLoaded;

  // === TRY HOT CONTEXT FIRST (v3.0) ===
  const hotContext = loadHotContext();

  let output;
  let detectedTask = null;
  let usedHotContext = false;

  if (hotContext && !isHotContextStale(hotContext)) {
    // Use hot context (fast path from PostgreSQL/Redis sync)
    usedHotContext = true;
    detectedTask = hotContext.activeTaskId || detectTaskFromPrompt(prompt, hotContext);

    if (detectedTask && hotContext.taskContext) {
      output = buildHotContextOutput(hotContext, detectedTask);
    } else {
      output = buildHotContextGlobalOutput(hotContext);
    }
  } else {
    // === FALLBACK TO FILE-BASED CONTEXT ===
    const globalContext = loadGlobalContext();
    const registry = loadRegistry();
    detectedTask = registry ? detectTask(prompt, registry) : null;

    if (detectedTask) {
      const taskContext = loadTaskContext(detectedTask, registry);
      output = buildTaskContextOutput(globalContext, taskContext, detectedTask, registry);
      if (registry) {
        updateRegistryActiveTask(registry, detectedTask);
      }
    } else if (isFirstPrompt && registry && Object.keys(registry.tasks || {}).length > 0) {
      output = buildSelectionOutput(globalContext, registry);
    } else {
      output = buildGlobalOnlyOutput(globalContext, registry);
    }
  }

  // === RECORD SESSION ACTIVITY (v3.0) ===
  recordSessionActivity(sessionId, {
    timestamp: new Date().toISOString(),
    activeTask: detectedTask,
    usedHotContext,
    promptHash: hashPrompt(prompt)
  });

  // Update session state
  updateSessionState({
    sessionId,
    contextLoaded: true,
    activeTask: detectedTask,
    lastActivity: new Date().toISOString()
  });

  if (output) {
    console.log(JSON.stringify(output));
  }

  process.exit(0);
}

// === HOT CONTEXT (v3.0) ===

function loadHotContext() {
  try {
    return JSON.parse(fs.readFileSync(HOT_CONTEXT_PATH, 'utf8'));
  } catch (e) {
    return null;
  }
}

function isHotContextStale(hotContext) {
  if (!hotContext.lastUpdated) return true;

  const lastUpdated = new Date(hotContext.lastUpdated);
  const minutesAgo = (Date.now() - lastUpdated.getTime()) / (1000 * 60);
  return minutesAgo > HOT_CONTEXT_STALE_MINUTES;
}

function detectTaskFromPrompt(prompt, hotContext) {
  if (!hotContext.availableTasks) return null;

  const lowerPrompt = prompt.toLowerCase();

  // Check keywords for each available task
  for (const task of hotContext.availableTasks) {
    const keywords = task.keywords || [];
    const matches = keywords.filter(kw => lowerPrompt.includes(kw.toLowerCase()));
    if (matches.length >= 2) {
      return task.taskId;
    }
  }

  // Check explicit task references
  const switchPatterns = ['switch to', 'work on', 'continue', 'resume', 'back to'];
  for (const pattern of switchPatterns) {
    if (lowerPrompt.includes(pattern)) {
      for (const task of hotContext.availableTasks) {
        if (lowerPrompt.includes(task.taskId.toLowerCase()) ||
            lowerPrompt.includes((task.name || '').toLowerCase())) {
          return task.taskId;
        }
      }
    }
  }

  return null;
}

function buildHotContextOutput(hotContext, taskId) {
  const tc = hotContext.taskContext || {};
  const gc = hotContext.globalContext || {};

  let xml = `<project-context source="hot-context-v3">
## Active Task: ${tc.name || taskId}

### State
- Phase: ${tc.currentPhase || 'unknown'}
- Iteration: ${tc.iteration || 0}
${tc.score ? `- Score: ${tc.score}` : ''}
${tc.lockedElements?.length ? `- Locked: ${tc.lockedElements.join(', ')}` : ''}

### Context
- Working on: ${tc.immediateContext?.workingOn || 'Not specified'}
- Last action: ${tc.immediateContext?.lastAction || 'None'}
- Next step: ${tc.immediateContext?.nextStep || 'Determine next step'}
${tc.immediateContext?.blockers?.length ? `- Blockers: ${tc.immediateContext.blockers.join(', ')}` : ''}

### Key Files
${tc.keyFiles?.slice(0, 5).map(f => `- ${f}`).join('\n') || 'See task context'}

### Resume Guidance
${tc.resumePrompt || 'Continue from current state.'}
`;

  // Add global context
  if (gc.hardRules?.length) {
    xml += `
### Project Rules
${gc.hardRules.map(r => `- ${r}`).join('\n')}
`;
  }

  if (gc.techStack?.length) {
    xml += `
### Tech Stack
${gc.techStack.join(', ')}
`;
  }

  xml += `
<context-metadata>
- Source: Hot Context (PostgreSQL/Redis synced)
- Last Updated: ${hotContext.lastUpdated || 'unknown'}
- Task ID: ${taskId}
</context-metadata>
</project-context>`;

  return {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: xml
    }
  };
}

function buildHotContextGlobalOutput(hotContext) {
  const gc = hotContext.globalContext || {};

  let xml = `<project-context source="hot-context-v3">`;

  if (gc.hardRules?.length) {
    xml += `
### Project Rules
${gc.hardRules.map(r => `- ${r}`).join('\n')}
`;
  }

  if (gc.techStack?.length) {
    xml += `
### Tech Stack
${gc.techStack.join(', ')}
`;
  }

  // Show available tasks
  if (hotContext.availableTasks?.length) {
    xml += `
### Available Tasks
${hotContext.availableTasks.map((t, i) => {
  const status = t.status === 'in_progress' ? ' (in progress)' :
                 t.status === 'completed' ? ' (completed)' : '';
  return `${i + 1}. **${t.name}**${status}`;
}).join('\n')}

To work on a task, mention it by name or use keywords.
`;
  }

  xml += `
<context-metadata>
- Source: Hot Context (PostgreSQL/Redis synced)
- Last Updated: ${hotContext.lastUpdated || 'unknown'}
</context-metadata>
</project-context>`;

  return {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: xml
    }
  };
}

// === SESSION ACTIVITY TRACKING (v3.0) ===

function recordSessionActivity(sessionId, activity) {
  try {
    const activityFile = SESSION_ACTIVITY_PATH;
    let activities = [];

    try {
      activities = JSON.parse(fs.readFileSync(activityFile, 'utf8'));
    } catch (e) {
      activities = [];
    }

    // Add new activity
    activities.push({
      sessionId,
      ...activity
    });

    // Keep last 100 activities
    if (activities.length > 100) {
      activities = activities.slice(-100);
    }

    fs.writeFileSync(activityFile, JSON.stringify(activities, null, 2));
  } catch (e) {
    // Ignore write errors
  }
}

function hashPrompt(prompt) {
  return crypto.createHash('sha256').update(prompt).digest('hex').slice(0, 8);
}

// === FILE-BASED LOADERS (FALLBACK) ===

function loadGlobalContext() {
  const context = {
    claudeMd: null,
    sharedConstants: null,
    hasAnyContext: false
  };

  try {
    const claudeMd = fs.readFileSync(CLAUDE_MD_PATH, 'utf8');
    context.claudeMd = extractKeyInstructions(claudeMd);
    context.hasAnyContext = true;
  } catch (e) {
    // CLAUDE.md is optional
  }

  try {
    context.sharedConstants = JSON.parse(fs.readFileSync(SHARED_PATH, 'utf8'));
    context.hasAnyContext = true;
  } catch (e) {
    // Shared constants are optional
  }

  return context;
}

function extractKeyInstructions(claudeMd) {
  const sections = [];

  const hardRulesMatch = claudeMd.match(/## Hard Rules\n([\s\S]*?)(?=\n##|$)/);
  if (hardRulesMatch) {
    sections.push('**Hard Rules:**\n' + hardRulesMatch[1].trim());
  }

  const keyPathsMatch = claudeMd.match(/## Key Paths\n([\s\S]*?)(?=\n##|$)/);
  if (keyPathsMatch) {
    sections.push('**Key Paths:**\n' + keyPathsMatch[1].trim());
  }

  return sections.length > 0 ? sections.join('\n\n') : null;
}

function loadRegistry() {
  try {
    return JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
  } catch (e) {
    return null;
  }
}

function loadTaskContext(taskId, registry) {
  if (!registry || !registry.tasks || !registry.tasks[taskId]) {
    return null;
  }

  const task = registry.tasks[taskId];
  const contextPath = path.join(CONTEXTS_DIR, task.contextFile);

  try {
    return JSON.parse(fs.readFileSync(contextPath, 'utf8'));
  } catch (e) {
    return null;
  }
}

// === TASK DETECTION ===

function detectTask(prompt, registry) {
  if (!registry || !registry.tasks) return null;

  const lowerPrompt = prompt.toLowerCase();

  for (const [taskId, task] of Object.entries(registry.tasks)) {
    const keywords = task.keywords || [];
    const matches = keywords.filter(kw => lowerPrompt.includes(kw.toLowerCase()));
    if (matches.length >= 2) {
      return taskId;
    }
  }

  const switchPatterns = ['switch to', 'work on', 'continue', 'resume', 'back to'];
  for (const pattern of switchPatterns) {
    if (lowerPrompt.includes(pattern)) {
      for (const [taskId, task] of Object.entries(registry.tasks)) {
        if (lowerPrompt.includes(taskId.toLowerCase()) ||
            lowerPrompt.includes(task.name.toLowerCase())) {
          return taskId;
        }
      }
    }
  }

  return null;
}

// === OUTPUT BUILDERS (FILE-BASED) ===

function buildTaskContextOutput(globalContext, taskContext, taskId, registry) {
  const task = registry.tasks[taskId];
  const tc = taskContext || {};

  let xml = `<project-context source="file-based-v3">
## Active Task: ${task.name}

### State
- Phase: ${tc.state?.phase || 'unknown'}
- Iteration: ${tc.state?.iteration || 0}
${tc.state?.score ? `- Score: ${tc.state.score}` : ''}
${tc.state?.lockedElements?.length ? `- Locked: ${tc.state.lockedElements.join(', ')}` : ''}

### Context
- Working on: ${tc.immediateContext?.workingOn || 'Not specified'}
- Last action: ${tc.immediateContext?.lastAction || 'None'}
- Next step: ${tc.immediateContext?.nextStep || 'Determine next step'}
${tc.immediateContext?.blockers?.length ? `- Blockers: ${tc.immediateContext.blockers.join(', ')}` : ''}

### Key Files
${tc.keyFiles?.slice(0, 5).map(f => `- ${f}`).join('\n') || 'See task context file'}

### Resume Guidance
${tc.resumePrompt || 'Continue from current state.'}
`;

  if (globalContext.sharedConstants) {
    const sc = globalContext.sharedConstants;
    xml += `
### Project Constants
${sc.hardRules?.map(r => `- ${r}`).join('\n') || ''}
`;
  }

  if (globalContext.claudeMd) {
    xml += `
${globalContext.claudeMd}
`;
  }

  xml += `</project-context>`;

  return {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: xml
    }
  };
}

function buildSelectionOutput(globalContext, registry) {
  const tasks = Object.entries(registry.tasks)
    .sort((a, b) => (a[1].priority || 99) - (b[1].priority || 99))
    .map(([id, task], i) => {
      const status = task.status === 'in_progress' ? ' (in progress)' :
                     task.status === 'completed' ? ' (completed)' : '';
      return `${i + 1}. **${task.name}**${status}`;
    });

  let xml = `<project-context source="file-based-v3">
## Available Tasks

${tasks.join('\n')}

To work on a task, mention it by name or use keywords. Or describe new work.
`;

  if (globalContext.sharedConstants?.hardRules) {
    xml += `
### Project Rules
${globalContext.sharedConstants.hardRules.map(r => `- ${r}`).join('\n')}
`;
  }

  if (globalContext.claudeMd) {
    xml += `
${globalContext.claudeMd}
`;
  }

  xml += `</project-context>`;

  return {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: xml
    }
  };
}

function buildGlobalOnlyOutput(globalContext, registry) {
  if (!globalContext.hasAnyContext) {
    return null;
  }

  let xml = `<project-context source="file-based-v3">`;

  if (globalContext.sharedConstants?.hardRules) {
    xml += `
### Project Rules
${globalContext.sharedConstants.hardRules.map(r => `- ${r}`).join('\n')}
`;
  }

  if (globalContext.claudeMd) {
    xml += `
${globalContext.claudeMd}
`;
  }

  if (registry && registry.tasks && Object.keys(registry.tasks).length > 0) {
    const taskNames = Object.values(registry.tasks).map(t => t.name).join(', ');
    xml += `
### Registered Tasks
${taskNames}
(Mention a task name to load its specific context)
`;
  }

  xml += `</project-context>`;

  return {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: xml
    }
  };
}

// === SESSION STATE ===

function loadSessionState() {
  try {
    const state = JSON.parse(fs.readFileSync(SESSION_STATE_PATH, 'utf8'));
    const loadedAt = new Date(state.loadedAt || 0);
    const hoursAgo = (Date.now() - loadedAt.getTime()) / (1000 * 60 * 60);

    if (hoursAgo > SESSION_TIMEOUT_HOURS) {
      return { contextLoaded: false };
    }
    return state;
  } catch (e) {
    return { contextLoaded: false };
  }
}

function updateSessionState(updates) {
  try {
    const current = loadSessionState();
    const newState = {
      ...current,
      ...updates,
      loadedAt: new Date().toISOString()
    };
    fs.writeFileSync(SESSION_STATE_PATH, JSON.stringify(newState, null, 2));
  } catch (e) {
    // Ignore write errors
  }
}

function updateRegistryActiveTask(registry, taskId) {
  try {
    registry.activeTask = taskId;
    registry.lastUpdated = new Date().toISOString();
    if (registry.tasks[taskId]) {
      registry.tasks[taskId].lastSession = new Date().toISOString();
    }
    fs.writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2));
  } catch (e) {
    // Ignore write errors
  }
}

// === RUN ===
main();
