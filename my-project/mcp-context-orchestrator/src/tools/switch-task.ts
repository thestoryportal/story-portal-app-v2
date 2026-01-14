/**
 * switch_task Tool
 * Atomic task switch with state preservation
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const SwitchTaskInputSchema = z.object({
  fromTaskId: z.string().optional().describe('Current task to save and switch from. If omitted, just loads new task.'),
  toTaskId: z.string().describe('Task to switch to'),
  saveCurrentState: z.boolean().default(true).describe('Save current task state before switching'),
  currentTaskUpdates: z.object({
    immediateContext: z.object({
      workingOn: z.string().nullable().optional(),
      lastAction: z.string().nullable().optional(),
      nextStep: z.string().nullable().optional(),
      blockers: z.array(z.string()).optional()
    }).optional(),
    currentPhase: z.string().optional(),
    iteration: z.number().optional()
  }).optional().describe('Updates to apply to current task before switching'),
  sessionId: z.string().optional().describe('Session ID for tracking')
});

export type SwitchTaskInput = z.infer<typeof SwitchTaskInputSchema>;

export interface SwitchTaskOutput {
  success: boolean;
  previousTask?: {
    taskId: string;
    saved: boolean;
    version?: number;
  };
  newTask: {
    taskId: string;
    name: string;
    status: string;
    currentPhase?: string;
    iteration: number;
    immediateContext: {
      workingOn: string | null;
      lastAction: string | null;
      nextStep: string | null;
      blockers: string[];
    };
    keyFiles: string[];
    resumePrompt?: string;
    blockedBy: Array<{ taskId: string; name: string }>;
  };
  timestamp: string;
}

export function createSwitchTaskTool(deps: ToolDependencies): Tool<unknown, SwitchTaskOutput> {
  return {
    async execute(rawInput: unknown): Promise<SwitchTaskOutput> {
      const input = SwitchTaskInputSchema.parse(rawInput);
      const { fromTaskId, toTaskId, saveCurrentState, currentTaskUpdates, sessionId } = input;

      const timestamp = new Date().toISOString();
      let previousTask: SwitchTaskOutput['previousTask'];

      // Save current task if specified
      if (fromTaskId && saveCurrentState) {
        try {
          let currentContext;

          // Apply updates if provided - this triggers auto_save_context_version
          if (currentTaskUpdates) {
            currentContext = await db.updateTaskContext(fromTaskId, currentTaskUpdates);
          } else {
            // No updates provided, just get current context
            currentContext = await db.getTaskContext(fromTaskId);
          }

          if (currentContext) {
            // Update Redis cache
            await deps.redis.setTaskContext(fromTaskId, {
              taskId: currentContext.taskId,
              name: currentContext.name,
              status: currentContext.status,
              currentPhase: currentContext.currentPhase,
              iteration: currentContext.iteration,
              immediateContext: currentContext.immediateContext,
              keyFiles: currentContext.keyFiles,
              resumePrompt: currentContext.resumePrompt
            });

            // Version is auto-created by database trigger when updates are applied
            previousTask = {
              taskId: fromTaskId,
              saved: true,
              version: currentContext.version
            };

            // Record session work in Neo4j (if available)
            if (sessionId && deps.neo4j) {
              await deps.neo4j.recordSession(sessionId, fromTaskId);
            }
          }
        } catch (error) {
          console.error('Failed to save previous task:', error);
          previousTask = {
            taskId: fromTaskId,
            saved: false
          };
        }
      }

      // Load new task
      const newTaskContext = await db.getTaskContext(toTaskId);
      if (!newTaskContext) {
        throw new Error(`Task not found: ${toTaskId}`);
      }

      // Update global context active task
      await db.updateGlobalContext(deps.projectId, {
        activeTaskId: toTaskId
      });

      // Update hot context
      await deps.redis.updateHotContextTask(deps.projectId, {
        taskId: newTaskContext.taskId,
        name: newTaskContext.name,
        status: newTaskContext.status,
        currentPhase: newTaskContext.currentPhase,
        iteration: newTaskContext.iteration,
        immediateContext: newTaskContext.immediateContext,
        keyFiles: newTaskContext.keyFiles,
        resumePrompt: newTaskContext.resumePrompt
      });

      // Get blocking tasks (requires Neo4j, fallback to empty)
      const blockingTasks = deps.neo4j
        ? await deps.neo4j.getBlockingTasks(toTaskId)
        : [];

      // Record session work on new task (if Neo4j available)
      if (sessionId && deps.neo4j) {
        await deps.neo4j.recordSession(sessionId, toTaskId);
      }

      // Update task last session time
      await db.updateTaskContext(toTaskId, {});

      return {
        success: true,
        previousTask,
        newTask: {
          taskId: newTaskContext.taskId,
          name: newTaskContext.name,
          status: newTaskContext.status,
          currentPhase: newTaskContext.currentPhase,
          iteration: newTaskContext.iteration,
          immediateContext: newTaskContext.immediateContext,
          keyFiles: newTaskContext.keyFiles,
          resumePrompt: newTaskContext.resumePrompt,
          blockedBy: blockingTasks.map(t => ({
            taskId: t.taskId,
            name: t.name
          }))
        },
        timestamp
      };
    }
  };
}
