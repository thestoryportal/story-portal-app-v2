/**
 * check_recovery Tool
 * Check for sessions needing recovery and get recovery prompts
 *
 * Integrates with:
 * - SessionService for session lifecycle management
 * - Recovery engine for crash detection
 */

import { z } from 'zod';
import * as recovery from '../recovery/engine.js';
import type { Tool, ToolDependencies } from './index.js';

export const CheckRecoveryInputSchema = z.object({
  markRecovered: z.string().optional().describe('Session ID to mark as recovered after handling'),
  includeHistory: z.boolean().optional().describe('Include tool history in output')
});

export type CheckRecoveryInput = z.infer<typeof CheckRecoveryInputSchema>;

export interface CheckRecoveryOutput {
  needsRecovery: boolean;
  sessions: Array<{
    sessionId: string;
    taskId?: string;
    taskName?: string;
    recoveryType: string;
    lastActivity: string;
    resumePrompt: string;
    toolHistory?: Array<{
      timestamp: string;
      tool: string;
      success: boolean;
    }>;
    unsavedChanges: Array<{
      type: string;
      path?: string;
      description: string;
    }>;
  }>;
  summary: string;
  timestamp: string;
}

export function createCheckRecoveryTool(deps?: ToolDependencies): Tool<unknown, CheckRecoveryOutput> {
  return {
    async execute(rawInput: unknown): Promise<CheckRecoveryOutput> {
      const input = CheckRecoveryInputSchema.parse(rawInput);
      const { markRecovered, includeHistory } = input;

      const timestamp = new Date().toISOString();

      // If marking a session as recovered, do that first
      if (markRecovered) {
        await recovery.markSessionRecovered(markRecovered);

        // Also update via SessionService if available
        if (deps?.platform?.sessionService) {
          try {
            await deps.platform.sessionService.updateSession(markRecovered, {
              status: 'recovered'
            });
          } catch (error) {
            console.error('Failed to update session via SessionService:', error);
          }
        }
      }

      // Check for sessions needing recovery
      const result = await recovery.checkForRecovery();

      // Enhance with SessionService data if available
      let enhancedSessions = result.sessions;
      if (deps?.platform?.sessionService) {
        try {
          const platformSessions = await deps.platform.sessionService.getSessionsNeedingRecovery();
          // Merge platform sessions that aren't already in the recovery list
          const existingIds = new Set(result.sessions.map(s => s.sessionId));
          for (const ps of platformSessions) {
            if (!existingIds.has(ps.sessionId)) {
              enhancedSessions.push({
                sessionId: ps.sessionId,
                taskId: ps.taskId,
                taskName: undefined,
                recoveryType: ps.status === 'crashed' ? 'crash' : 'timeout',
                lastActivity: ps.lastHeartbeat.toISOString(),
                contextSnapshot: ps.metadata as { workingOn?: string; lastAction?: string; nextStep?: string; blockers?: string[]; phase?: string; iteration?: number; } || {},
                resumePrompt: `Resume session ${ps.sessionId}`,
                toolHistory: [],
                unsavedChanges: []
              });
            }
          }
        } catch (error) {
          console.error('Failed to get sessions from SessionService:', error);
        }
      }

      // Format sessions for output
      const sessions = enhancedSessions.map(s => ({
        sessionId: s.sessionId,
        taskId: s.taskId,
        taskName: s.taskName,
        recoveryType: s.recoveryType,
        lastActivity: s.lastActivity,
        resumePrompt: s.resumePrompt,
        toolHistory: includeHistory ? s.toolHistory.slice(-10).map(h => ({
          timestamp: h.timestamp,
          tool: h.tool,
          success: h.success
        })) : undefined,
        unsavedChanges: s.unsavedChanges.map(c => ({
          type: c.type,
          path: c.path,
          description: c.description
        }))
      }));

      return {
        needsRecovery: result.needsRecovery || sessions.length > 0,
        sessions,
        summary: result.summary || `Found ${sessions.length} session(s) needing recovery`,
        timestamp
      };
    }
  };
}
