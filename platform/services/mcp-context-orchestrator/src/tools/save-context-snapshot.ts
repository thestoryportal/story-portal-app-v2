/**
 * save_context_snapshot Tool
 * Persists current state to all backends
 */

import { z } from 'zod';
import fs from 'fs';
import path from 'path';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const SaveContextSnapshotInputSchema = z.object({
  taskId: z.string().describe('Task ID to save snapshot for'),
  updates: z.object({
    currentPhase: z.string().optional(),
    iteration: z.number().optional(),
    score: z.number().optional(),
    status: z.enum(['pending', 'in_progress', 'completed', 'blocked', 'archived']).optional(),
    immediateContext: z.object({
      workingOn: z.string().nullable().optional(),
      lastAction: z.string().nullable().optional(),
      nextStep: z.string().nullable().optional(),
      blockers: z.array(z.string()).optional()
    }).optional(),
    keyFiles: z.array(z.string()).optional(),
    technicalDecisions: z.array(z.string()).optional(),
    resumePrompt: z.string().optional(),
    lockedElements: z.array(z.string()).optional()
  }).optional().describe('Updates to apply before saving'),
  changeSummary: z.string().optional().describe('Description of changes for version history'),
  sessionId: z.string().optional().describe('Session ID for attribution'),
  syncToFile: z.boolean().default(true).describe('Also sync to .claude/contexts file')
});

export type SaveContextSnapshotInput = z.infer<typeof SaveContextSnapshotInputSchema>;

export interface SaveContextSnapshotOutput {
  success: boolean;
  taskId: string;
  version: number;
  savedTo: {
    database: boolean;
    redis: boolean;
    file: boolean;
  };
  timestamp: string;
}

export function createSaveContextSnapshotTool(deps: ToolDependencies): Tool<unknown, SaveContextSnapshotOutput> {
  return {
    async execute(rawInput: unknown): Promise<SaveContextSnapshotOutput> {
      const input = SaveContextSnapshotInputSchema.parse(rawInput);
      // Note: changeSummary and sessionId are part of schema for documentation
      // but versioning is handled by database triggers
      const { taskId, updates, syncToFile } = input;

      const timestamp = new Date().toISOString();
      const savedTo = {
        database: false,
        redis: false,
        file: false
      };

      // Apply updates and save to database
      let updatedContext;
      if (updates) {
        updatedContext = await db.updateTaskContext(taskId, updates);
      } else {
        updatedContext = await db.getTaskContext(taskId);
      }

      if (!updatedContext) {
        throw new Error(`Task not found: ${taskId}`);
      }

      savedTo.database = true;

      // Note: Version is auto-created by database trigger (auto_save_context_version)
      // when significant fields change. The task_contexts.version is auto-incremented
      // by the increment_task_version trigger.

      // Update Redis cache
      try {
        await deps.redis.setTaskContext(taskId, {
          taskId: updatedContext.taskId,
          name: updatedContext.name,
          status: updatedContext.status,
          currentPhase: updatedContext.currentPhase,
          iteration: updatedContext.iteration,
          score: updatedContext.score,
          lockedElements: updatedContext.lockedElements,
          immediateContext: updatedContext.immediateContext,
          keyFiles: updatedContext.keyFiles,
          technicalDecisions: updatedContext.technicalDecisions,
          resumePrompt: updatedContext.resumePrompt
        });
        savedTo.redis = true;
      } catch (error) {
        console.error('Failed to update Redis cache:', error);
      }

      // Sync to file if requested
      if (syncToFile) {
        try {
          const filePath = path.join(
            process.cwd(),
            deps.contextsDir,
            'task-agents',
            `${taskId}.json`
          );

          // Ensure directory exists
          const dir = path.dirname(filePath);
          if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
          }

          // Write file
          const fileContent = {
            taskId: updatedContext.taskId,
            agentType: updatedContext.agentType,
            version: '1.0',
            lastUpdated: timestamp,
            state: {
              phase: updatedContext.currentPhase,
              iteration: updatedContext.iteration,
              score: updatedContext.score,
              status: updatedContext.status,
              lockedElements: updatedContext.lockedElements
            },
            immediateContext: updatedContext.immediateContext,
            keyFiles: updatedContext.keyFiles,
            technicalDecisions: updatedContext.technicalDecisions,
            resumePrompt: updatedContext.resumePrompt
          };

          fs.writeFileSync(filePath, JSON.stringify(fileContent, null, 2));
          savedTo.file = true;
        } catch (error) {
          console.error('Failed to sync to file:', error);
        }
      }

      // Update hot context
      try {
        await deps.redis.updateHotContextTask(deps.projectId, {
          taskId: updatedContext.taskId,
          name: updatedContext.name,
          status: updatedContext.status,
          currentPhase: updatedContext.currentPhase,
          iteration: updatedContext.iteration,
          immediateContext: updatedContext.immediateContext,
          keyFiles: updatedContext.keyFiles,
          resumePrompt: updatedContext.resumePrompt
        });
      } catch (error) {
        console.error('Failed to update hot context:', error);
      }

      // Platform Services Integration
      if (deps.platform) {
        // Save to StateManager hot cache for fast access
        try {
          await deps.platform.stateManager.saveHotState(taskId, {
            taskId: updatedContext.taskId,
            status: updatedContext.status,
            currentPhase: updatedContext.currentPhase,
            iteration: updatedContext.iteration,
            immediateContext: updatedContext.immediateContext,
            timestamp
          });
        } catch (error) {
          console.error('Failed to save to StateManager hot cache:', error);
        }

        // Create event in EventStore for audit trail
        try {
          await deps.platform.eventStore.createContextEvent(
            taskId,
            'context_updated',
            {
              version: updatedContext.version,
              updates: updates || {},
              savedTo
            },
            input.sessionId
          );
        } catch (error) {
          console.error('Failed to create EventStore event:', error);
        }

        // Update SemanticCache for similarity search
        try {
          await deps.platform.semanticCache.cacheTaskContext(taskId, {
            name: updatedContext.name,
            description: updatedContext.description,
            keywords: updatedContext.keywords,
            keyFiles: updatedContext.keyFiles,
            immediateContext: updatedContext.immediateContext,
            technicalDecisions: updatedContext.technicalDecisions,
            resumePrompt: updatedContext.resumePrompt
          });
        } catch (error) {
          console.error('Failed to update SemanticCache:', error);
        }
      }

      return {
        success: true,
        taskId,
        version: updatedContext.version,
        savedTo,
        timestamp
      };
    }
  };
}
