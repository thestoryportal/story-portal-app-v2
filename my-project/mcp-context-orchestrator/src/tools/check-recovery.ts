/**
 * check_recovery Tool
 * Check for sessions needing recovery and get recovery prompts
 */

import { z } from 'zod';
import * as recovery from '../recovery/engine.js';
import type { Tool } from './index.js';

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

export function createCheckRecoveryTool(): Tool<unknown, CheckRecoveryOutput> {
  return {
    async execute(rawInput: unknown): Promise<CheckRecoveryOutput> {
      const input = CheckRecoveryInputSchema.parse(rawInput);
      const { markRecovered, includeHistory } = input;

      const timestamp = new Date().toISOString();

      // If marking a session as recovered, do that first
      if (markRecovered) {
        await recovery.markSessionRecovered(markRecovered);
      }

      // Check for sessions needing recovery
      const result = await recovery.checkForRecovery();

      // Format sessions for output
      const sessions = result.sessions.map(s => ({
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
        needsRecovery: result.needsRecovery,
        sessions,
        summary: result.summary,
        timestamp
      };
    }
  };
}
