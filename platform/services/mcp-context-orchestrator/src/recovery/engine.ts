/**
 * Recovery Engine
 * Handles crash detection, session recovery, and context restoration
 */

import * as fs from 'fs';
import * as path from 'path';
import * as db from '../db/client.js';
import type { ActiveSession, TaskContext, RecoveryType } from '../db/schema.js';
import { loadConfig } from '../config.js';

// Lazy-loaded config
let _config: ReturnType<typeof loadConfig> | null = null;
function getConfig() {
  if (!_config) {
    _config = loadConfig();
  }
  return _config;
}

export interface RecoveryData {
  sessionId: string;
  taskId?: string;
  taskName?: string;
  recoveryType: RecoveryType;
  lastActivity: string;
  contextSnapshot: {
    workingOn?: string;
    lastAction?: string;
    nextStep?: string;
    blockers?: string[];
    phase?: string;
    iteration?: number;
  };
  toolHistory: ToolHistoryEntry[];
  unsavedChanges: UnsavedChange[];
  resumePrompt: string;
}

export interface ToolHistoryEntry {
  timestamp: string;
  tool: string;
  input: Record<string, unknown>;
  success: boolean;
}

export interface UnsavedChange {
  type: 'file_edit' | 'state_change' | 'config_update';
  path?: string;
  description: string;
  timestamp: string;
}

export interface RecoveryCheckResult {
  needsRecovery: boolean;
  sessions: RecoveryData[];
  summary: string;
}

// File paths for hook-generated data
const HEARTBEAT_FILE = '.session-heartbeat.json';
const TOOL_HISTORY_FILE = '.tool-history.json';
const PENDING_SAVES_FILE = '.pending-saves.json';
const SESSION_STATE_FILE = '.session-state.json';

// Recovery thresholds
const CRASH_THRESHOLD_MINUTES = 5;
const STALE_SESSION_HOURS = 24;

/**
 * Check for sessions that need recovery
 */
export async function checkForRecovery(): Promise<RecoveryCheckResult> {
  const sessions: RecoveryData[] = [];

  // Check 1: Database sessions marked for recovery
  const dbSessions = await db.getSessionsNeedingRecovery();
  for (const session of dbSessions) {
    const recoveryData = await buildRecoveryData(session);
    if (recoveryData) {
      sessions.push(recoveryData);
    }
  }

  // Check 2: File-based crash detection (heartbeat stale)
  const fileRecovery = await checkFileBasedRecovery();
  if (fileRecovery && !sessions.some(s => s.sessionId === fileRecovery.sessionId)) {
    sessions.push(fileRecovery);
  }

  // Build summary
  let summary = '';
  if (sessions.length === 0) {
    summary = 'No sessions need recovery.';
  } else if (sessions.length === 1) {
    const s = sessions[0];
    summary = `Found 1 session needing recovery: ${s.taskName || s.taskId || 'unknown task'} (${s.recoveryType})`;
  } else {
    summary = `Found ${sessions.length} sessions needing recovery.`;
  }

  return {
    needsRecovery: sessions.length > 0,
    sessions,
    summary
  };
}

/**
 * Build recovery data from database session
 */
async function buildRecoveryData(session: ActiveSession): Promise<RecoveryData | null> {
  let taskContext: TaskContext | null = null;
  if (session.taskId) {
    taskContext = await db.getTaskContext(session.taskId);
  }

  // Load tool history from file if available
  const toolHistory = await loadToolHistory(session.sessionId);

  // Generate resume prompt
  const resumePrompt = generateResumePrompt(session, taskContext, toolHistory);

  return {
    sessionId: session.sessionId,
    taskId: session.taskId,
    taskName: taskContext?.name,
    recoveryType: session.recoveryType || 'crash',
    lastActivity: session.lastHeartbeat.toISOString(),
    contextSnapshot: {
      workingOn: taskContext?.immediateContext?.workingOn || undefined,
      lastAction: taskContext?.immediateContext?.lastAction || undefined,
      nextStep: taskContext?.immediateContext?.nextStep || undefined,
      blockers: taskContext?.immediateContext?.blockers || [],
      phase: taskContext?.currentPhase,
      iteration: taskContext?.iteration
    },
    toolHistory,
    unsavedChanges: session.unsavedChanges || [],
    resumePrompt
  };
}

/**
 * Check for file-based crash detection
 */
async function checkFileBasedRecovery(): Promise<RecoveryData | null> {
  const contextsDir = path.join(getConfig().contextsDir);
  const heartbeatPath = path.join(contextsDir, HEARTBEAT_FILE);

  try {
    if (!fs.existsSync(heartbeatPath)) {
      return null;
    }

    const heartbeat = JSON.parse(fs.readFileSync(heartbeatPath, 'utf8'));
    const lastActivity = new Date(heartbeat.timestamp);
    const minutesAgo = (Date.now() - lastActivity.getTime()) / (1000 * 60);

    // Check if heartbeat is stale (indicates crash)
    if (minutesAgo > CRASH_THRESHOLD_MINUTES && minutesAgo < STALE_SESSION_HOURS * 60) {
      const sessionState = loadSessionState(contextsDir);
      const toolHistory = await loadToolHistoryFromFile(contextsDir, heartbeat.sessionId);

      return {
        sessionId: heartbeat.sessionId,
        taskId: sessionState?.activeTask,
        taskName: undefined,
        recoveryType: 'crash',
        lastActivity: heartbeat.timestamp,
        contextSnapshot: {
          workingOn: undefined,
          lastAction: heartbeat.lastTool ? `Used ${heartbeat.lastTool} tool` : undefined,
          nextStep: undefined,
          blockers: []
        },
        toolHistory,
        unsavedChanges: loadPendingSaves(contextsDir),
        resumePrompt: generateFileBasedResumePrompt(heartbeat, sessionState, toolHistory)
      };
    }
  } catch (e) {
    // Ignore file read errors
  }

  return null;
}

/**
 * Load tool history from database or file
 */
async function loadToolHistory(sessionId: string): Promise<ToolHistoryEntry[]> {
  // First try file-based history
  const contextsDir = getConfig().contextsDir;
  const fileHistory = await loadToolHistoryFromFile(contextsDir, sessionId);
  if (fileHistory.length > 0) {
    return fileHistory;
  }

  // Fall back to empty (database doesn't store tool history currently)
  return [];
}

/**
 * Load tool history from file
 */
interface ToolHistoryFileEntry extends ToolHistoryEntry {
  sessionId?: string;
}

async function loadToolHistoryFromFile(contextsDir: string, sessionId: string): Promise<ToolHistoryEntry[]> {
  try {
    const historyPath = path.join(contextsDir, TOOL_HISTORY_FILE);
    if (fs.existsSync(historyPath)) {
      const history = JSON.parse(fs.readFileSync(historyPath, 'utf8')) as ToolHistoryFileEntry[];
      // Filter to specific session if sessionId provided
      return history.filter(h => !sessionId || h.sessionId === sessionId);
    }
  } catch (e) {
    // Ignore errors
  }
  return [];
}

/**
 * Load session state from file
 */
function loadSessionState(contextsDir: string): { activeTask?: string; sessionId?: string } | null {
  try {
    const statePath = path.join(contextsDir, SESSION_STATE_FILE);
    if (fs.existsSync(statePath)) {
      return JSON.parse(fs.readFileSync(statePath, 'utf8'));
    }
  } catch (e) {
    // Ignore errors
  }
  return null;
}

/**
 * Load pending saves from file
 */
function loadPendingSaves(contextsDir: string): UnsavedChange[] {
  try {
    const pendingPath = path.join(contextsDir, PENDING_SAVES_FILE);
    if (fs.existsSync(pendingPath)) {
      const pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
      return pending.map((p: Record<string, unknown>) => ({
        type: 'file_edit' as const,
        path: (p.trigger as Record<string, unknown>)?.file as string,
        description: `Triggered by ${(p.trigger as Record<string, unknown>)?.tool}`,
        timestamp: p.timestamp as string
      }));
    }
  } catch (e) {
    // Ignore errors
  }
  return [];
}

/**
 * Generate resume prompt from database session
 */
function generateResumePrompt(
  session: ActiveSession,
  taskContext: TaskContext | null,
  toolHistory: ToolHistoryEntry[]
): string {
  const parts: string[] = [];

  parts.push('## Session Recovery');
  parts.push('');
  parts.push(`A previous session (${session.recoveryType || 'crash'}) was detected.`);
  parts.push('');

  if (taskContext) {
    parts.push(`### Task: ${taskContext.name}`);
    if (taskContext.currentPhase) {
      parts.push(`- Phase: ${taskContext.currentPhase}`);
    }
    if (taskContext.iteration) {
      parts.push(`- Iteration: ${taskContext.iteration}`);
    }
    parts.push('');
  }

  if (taskContext?.immediateContext) {
    const ic = taskContext.immediateContext;
    parts.push('### Context');
    if (ic.workingOn) parts.push(`- Working on: ${ic.workingOn}`);
    if (ic.lastAction) parts.push(`- Last action: ${ic.lastAction}`);
    if (ic.nextStep) parts.push(`- Next step: ${ic.nextStep}`);
    if (ic.blockers?.length) parts.push(`- Blockers: ${ic.blockers.join(', ')}`);
    parts.push('');
  }

  if (toolHistory.length > 0) {
    parts.push('### Recent Tool Usage');
    const recent = toolHistory.slice(-5);
    for (const entry of recent) {
      const status = entry.success ? '✓' : '✗';
      parts.push(`- ${status} ${entry.tool}`);
    }
    parts.push('');
  }

  if (session.unsavedChanges?.length) {
    parts.push('### Pending Changes');
    for (const change of session.unsavedChanges) {
      parts.push(`- ${change.description}${change.path ? ` (${change.path})` : ''}`);
    }
    parts.push('');
  }

  if (session.conversationSummary) {
    parts.push('### Conversation Summary');
    parts.push(session.conversationSummary);
    parts.push('');
  }

  parts.push('### Recommended Actions');
  parts.push('1. Review any pending changes and verify they were saved');
  parts.push('2. Check the state of files that were being modified');
  parts.push('3. Continue from the last known step');

  return parts.join('\n');
}

/**
 * Generate resume prompt from file-based recovery
 */
function generateFileBasedResumePrompt(
  heartbeat: Record<string, unknown>,
  sessionState: { activeTask?: string; sessionId?: string } | null,
  toolHistory: ToolHistoryEntry[]
): string {
  const parts: string[] = [];

  parts.push('## Session Recovery');
  parts.push('');
  parts.push('A previous session crash was detected.');
  parts.push(`Last activity: ${heartbeat.timestamp}`);
  if (heartbeat.lastTool) {
    parts.push(`Last tool used: ${heartbeat.lastTool}`);
  }
  parts.push('');

  if (sessionState?.activeTask) {
    parts.push(`### Active Task`);
    parts.push(`Task ID: ${sessionState.activeTask}`);
    parts.push('');
  }

  if (toolHistory.length > 0) {
    parts.push('### Recent Tool Usage');
    const recent = toolHistory.slice(-5);
    for (const entry of recent) {
      const status = entry.success ? '✓' : '✗';
      const input = entry.input;
      let detail = '';
      if (input.file) detail = ` (${input.file})`;
      else if (input.command) detail = ` (${String(input.command).slice(0, 50)}...)`;
      parts.push(`- ${status} ${entry.tool}${detail}`);
    }
    parts.push('');
  }

  parts.push('### Recommended Actions');
  parts.push('1. Check if any file modifications were lost');
  parts.push('2. Review tool history to understand last actions');
  parts.push('3. Continue from where you left off');

  return parts.join('\n');
}

/**
 * Mark a session as recovered
 */
export async function markSessionRecovered(sessionId: string): Promise<void> {
  await db.markSessionRecovered(sessionId);

  // Clear file-based recovery markers
  const contextsDir = getConfig().contextsDir;
  const heartbeatPath = path.join(contextsDir, HEARTBEAT_FILE);

  try {
    if (fs.existsSync(heartbeatPath)) {
      const heartbeat = JSON.parse(fs.readFileSync(heartbeatPath, 'utf8'));
      if (heartbeat.sessionId === sessionId) {
        fs.unlinkSync(heartbeatPath);
      }
    }
  } catch (e) {
    // Ignore errors
  }
}

/**
 * Register a new session for tracking
 */
export async function registerSession(
  sessionId: string,
  taskId?: string,
  projectDir?: string
): Promise<void> {
  await db.createSession(sessionId, taskId, projectDir);
}

/**
 * Update session heartbeat
 */
export async function updateHeartbeat(sessionId: string): Promise<void> {
  await db.updateSessionHeartbeat(sessionId);
}

/**
 * Mark session as ended cleanly
 */
export async function endSession(sessionId: string): Promise<void> {
  await db.endSession(sessionId);
}

/**
 * Mark session for recovery (e.g., on compaction)
 */
export async function markForRecovery(
  sessionId: string,
  recoveryType: RecoveryType,
  contextSnapshot: Record<string, unknown>,
  summary?: string
): Promise<void> {
  await db.markSessionForRecovery(sessionId, recoveryType, contextSnapshot, summary);
}
