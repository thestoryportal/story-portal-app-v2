/**
 * resolve_conflict Tool
 * Apply resolution to a detected conflict
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const ResolveConflictInputSchema = z.object({
  conflictId: z.string().describe('ID of the conflict to resolve'),
  resolution: z.object({
    action: z.enum(['use_a', 'use_b', 'merge', 'custom', 'ignore']).describe('Resolution action to take'),
    resolvedValue: z.unknown().optional().describe('Custom value if action is "custom" or "merge"'),
    notes: z.string().optional().describe('Notes about the resolution')
  }),
  resolvedBy: z.string().optional().describe('Who resolved the conflict (session ID or agent ID)')
});

export type ResolveConflictInput = z.infer<typeof ResolveConflictInputSchema>;

export interface ResolveConflictOutput {
  success: boolean;
  conflictId: string;
  previousStatus: string;
  newStatus: string;
  resolution: {
    action: string;
    notes?: string;
  };
  timestamp: string;
}

export function createResolveConflictTool(deps: ToolDependencies): Tool<unknown, ResolveConflictOutput> {
  return {
    async execute(rawInput: unknown): Promise<ResolveConflictOutput> {
      const input = ResolveConflictInputSchema.parse(rawInput);
      const { conflictId, resolution, resolvedBy } = input;

      const timestamp = new Date().toISOString();

      // Get current conflict state
      const conflicts = await db.getUnresolvedConflicts();
      const conflict = conflicts.find(c => c.id === conflictId);

      if (!conflict) {
        throw new Error(`Conflict not found or already resolved: ${conflictId}`);
      }

      const previousStatus = conflict.resolutionStatus;

      // Determine new status based on action
      let newStatus: db.ResolutionStatus;
      if (resolution.action === 'ignore') {
        newStatus = 'ignored';
      } else {
        newStatus = 'resolved';
      }

      // Apply resolution
      await db.resolveConflict(conflictId, {
        resolutionStatus: newStatus,
        resolution: {
          action: resolution.action,
          resolvedValue: resolution.resolvedValue,
          notes: resolution.notes
        },
        resolvedBy
      });

      // If resolution involves applying changes, do so
      if (resolution.action === 'use_a' || resolution.action === 'use_b') {
        // Get task context to sync
        const taskA = await db.getTaskContext(conflict.taskAId);

        if (conflict.conflictType === 'state_mismatch') {
          // Sync cache with database
          if (taskA) {
            await deps.redis.setTaskContext(taskA.taskId, {
              taskId: taskA.taskId,
              name: taskA.name,
              status: taskA.status,
              currentPhase: taskA.currentPhase,
              iteration: taskA.iteration,
              immediateContext: taskA.immediateContext,
              keyFiles: taskA.keyFiles,
              resumePrompt: taskA.resumePrompt
            });
          }
        }
      }

      // Clear any related lock collisions
      if (conflict.conflictType === 'lock_collision') {
        await deps.redis.releaseLock(conflict.taskAId, 'system-resolution');
      }

      return {
        success: true,
        conflictId,
        previousStatus,
        newStatus,
        resolution: {
          action: resolution.action,
          notes: resolution.notes
        },
        timestamp
      };
    }
  };
}
