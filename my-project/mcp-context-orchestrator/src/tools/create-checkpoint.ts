/**
 * create_checkpoint Tool
 * Creates a named version snapshot with rollback capability
 */

import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const CreateCheckpointInputSchema = z.object({
  label: z.string().describe('Human-readable label for the checkpoint'),
  description: z.string().optional().describe('Detailed description of what this checkpoint represents'),
  taskId: z.string().optional().describe('Task to checkpoint. If omitted, creates global checkpoint.'),
  checkpointType: z.enum(['manual', 'milestone', 'pre_migration', 'recovery_point', 'auto']).default('manual'),
  includeTasks: z.array(z.string()).optional().describe('Additional task IDs to include in multi-task checkpoint'),
  sessionId: z.string().optional().describe('Session ID for attribution')
});

export type CreateCheckpointInput = z.infer<typeof CreateCheckpointInputSchema>;

export interface CreateCheckpointOutput {
  success: boolean;
  checkpointId: string;
  label: string;
  scope: 'task' | 'global' | 'multi_task';
  includedTasks: string[];
  createdAt: string;
}

export function createCreateCheckpointTool(deps: ToolDependencies): Tool<unknown, CreateCheckpointOutput> {
  return {
    async execute(rawInput: unknown): Promise<CreateCheckpointOutput> {
      const input = CreateCheckpointInputSchema.parse(rawInput);
      const { label, description, taskId, checkpointType, includeTasks, sessionId } = input;

      const checkpointId = `cp-${Date.now()}-${uuidv4().slice(0, 8)}`;
      const createdAt = new Date().toISOString();

      // Determine scope
      let scope: 'task' | 'global' | 'multi_task';
      const allTaskIds: string[] = [];

      if (taskId) {
        allTaskIds.push(taskId);
      }
      if (includeTasks && includeTasks.length > 0) {
        allTaskIds.push(...includeTasks.filter(id => !allTaskIds.includes(id)));
      }

      if (allTaskIds.length === 0) {
        scope = 'global';
      } else if (allTaskIds.length === 1) {
        scope = 'task';
      } else {
        scope = 'multi_task';
      }

      // Build snapshot
      const snapshot: Record<string, unknown> = {
        createdAt,
        projectId: deps.projectId
      };

      // Include global context
      const globalContext = await db.getGlobalContext(deps.projectId);
      if (globalContext) {
        snapshot.global = {
          hardRules: globalContext.hardRules,
          techStack: globalContext.techStack,
          keyPaths: globalContext.keyPaths,
          services: globalContext.services,
          activeTaskId: globalContext.activeTaskId
        };
      }

      // Include task contexts
      if (allTaskIds.length > 0) {
        snapshot.tasks = {};
        for (const tid of allTaskIds) {
          const taskContext = await db.getTaskContext(tid);
          if (taskContext) {
            (snapshot.tasks as Record<string, unknown>)[tid] = {
              taskId: taskContext.taskId,
              name: taskContext.name,
              status: taskContext.status,
              currentPhase: taskContext.currentPhase,
              iteration: taskContext.iteration,
              score: taskContext.score,
              lockedElements: taskContext.lockedElements,
              immediateContext: taskContext.immediateContext,
              keyFiles: taskContext.keyFiles,
              technicalDecisions: taskContext.technicalDecisions,
              resumePrompt: taskContext.resumePrompt,
              version: taskContext.version
            };
          }
        }
      }

      // Create checkpoint in database
      await db.createCheckpoint({
        checkpointId,
        label,
        description,
        checkpointType,
        taskId: taskId || undefined,
        scope,
        includedTasks: allTaskIds,
        snapshot,
        createdBy: sessionId,
        sessionId
      });

      // Also cache in Redis for quick access
      await deps.redis.setTaskContext(`checkpoint:${checkpointId}`, {
        checkpointId,
        label,
        scope,
        includedTasks: allTaskIds,
        createdAt
      });

      return {
        success: true,
        checkpointId,
        label,
        scope,
        includedTasks: allTaskIds,
        createdAt
      };
    }
  };
}
