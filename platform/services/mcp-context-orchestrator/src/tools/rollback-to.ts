/**
 * rollback_to Tool
 * Restore task context to a previous version or checkpoint
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const RollbackToInputSchema = z.object({
  taskId: z.string().describe('Task ID to rollback'),
  target: z.union([
    z.object({
      type: z.literal('version'),
      version: z.number().describe('Version number to rollback to')
    }),
    z.object({
      type: z.literal('checkpoint'),
      checkpointId: z.string().describe('Checkpoint ID to rollback to')
    })
  ]).describe('Target to rollback to - either a version number or checkpoint ID'),
  createBackup: z.boolean().default(true).describe('Create a backup checkpoint before rollback'),
  sessionId: z.string().optional().describe('Session ID for attribution')
});

export type RollbackToInput = z.infer<typeof RollbackToInputSchema>;

export interface RollbackToOutput {
  success: boolean;
  taskId: string;
  rolledBackTo: {
    type: 'version' | 'checkpoint';
    identifier: string | number;
  };
  backupCheckpointId?: string;
  restoredState: {
    currentPhase?: string;
    iteration: number;
    status: string;
  };
  timestamp: string;
}

export function createRollbackToTool(deps: ToolDependencies): Tool<unknown, RollbackToOutput> {
  return {
    async execute(rawInput: unknown): Promise<RollbackToOutput> {
      const input = RollbackToInputSchema.parse(rawInput);
      const { taskId, target, createBackup, sessionId } = input;

      const timestamp = new Date().toISOString();
      let backupCheckpointId: string | undefined;

      // Get current state
      const currentContext = await db.getTaskContext(taskId);
      if (!currentContext) {
        throw new Error(`Task not found: ${taskId}`);
      }

      // Create backup if requested
      if (createBackup) {
        const backupId = `backup-${Date.now()}`;
        await db.createCheckpoint({
          checkpointId: backupId,
          label: `Backup before rollback`,
          description: `Auto-created backup before rolling back task ${taskId}`,
          checkpointType: 'recovery_point',
          taskId,
          scope: 'task',
          includedTasks: [taskId],
          snapshot: currentContext as unknown as Record<string, unknown>,
          createdBy: sessionId,
          sessionId
        });
        backupCheckpointId = backupId;
      }

      let restoredContext: db.TaskContext | null = null;

      if (target.type === 'version') {
        // Rollback to specific version
        restoredContext = await db.rollbackToVersion(taskId, target.version);
      } else {
        // Rollback to checkpoint
        const checkpoint = await db.getCheckpoint(target.checkpointId);
        if (!checkpoint) {
          throw new Error(`Checkpoint not found: ${target.checkpointId}`);
        }

        // Extract task data from checkpoint
        const tasks = checkpoint.snapshot.tasks as Record<string, Record<string, unknown>> | undefined;
        if (!tasks || !tasks[taskId]) {
          throw new Error(`Task ${taskId} not found in checkpoint ${target.checkpointId}`);
        }

        const taskSnapshot = tasks[taskId];

        // Update task with checkpoint data
        // Note: auto_save_context_version trigger creates version record automatically
        restoredContext = await db.updateTaskContext(taskId, {
          status: taskSnapshot.status as db.TaskStatus,
          currentPhase: taskSnapshot.currentPhase as string | undefined,
          iteration: taskSnapshot.iteration as number,
          score: taskSnapshot.score as number | undefined,
          lockedElements: taskSnapshot.lockedElements as string[],
          immediateContext: taskSnapshot.immediateContext as db.ImmediateContext,
          keyFiles: taskSnapshot.keyFiles as string[],
          technicalDecisions: taskSnapshot.technicalDecisions as string[],
          resumePrompt: taskSnapshot.resumePrompt as string | undefined
        });
      }

      if (!restoredContext) {
        throw new Error('Failed to restore context');
      }

      // Update Redis cache
      await deps.redis.setTaskContext(taskId, {
        taskId: restoredContext.taskId,
        name: restoredContext.name,
        status: restoredContext.status,
        currentPhase: restoredContext.currentPhase,
        iteration: restoredContext.iteration,
        immediateContext: restoredContext.immediateContext,
        keyFiles: restoredContext.keyFiles,
        resumePrompt: restoredContext.resumePrompt
      });

      // Update hot context
      await deps.redis.updateHotContextTask(deps.projectId, {
        taskId: restoredContext.taskId,
        name: restoredContext.name,
        status: restoredContext.status,
        currentPhase: restoredContext.currentPhase,
        iteration: restoredContext.iteration,
        immediateContext: restoredContext.immediateContext,
        keyFiles: restoredContext.keyFiles,
        resumePrompt: restoredContext.resumePrompt
      });

      return {
        success: true,
        taskId,
        rolledBackTo: {
          type: target.type,
          identifier: target.type === 'version' ? target.version : target.checkpointId
        },
        backupCheckpointId,
        restoredState: {
          currentPhase: restoredContext.currentPhase,
          iteration: restoredContext.iteration,
          status: restoredContext.status
        },
        timestamp
      };
    }
  };
}
