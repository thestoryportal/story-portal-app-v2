/**
 * sync_hot_context Tool
 * Update file cache from databases
 */

import { z } from 'zod';
import fs from 'fs';
import path from 'path';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';
import type { HotContext } from '../cache/redis-client.js';

export const SyncHotContextInputSchema = z.object({
  syncRedis: z.boolean().default(true).describe('Sync Redis cache with database'),
  syncFiles: z.boolean().default(true).describe('Sync file cache with database'),
  taskIds: z.array(z.string()).optional().describe('Specific tasks to sync. If omitted, syncs all active tasks.'),
  updateRegistry: z.boolean().default(true).describe('Update _registry.json file')
});

export type SyncHotContextInput = z.infer<typeof SyncHotContextInputSchema>;

export interface SyncHotContextOutput {
  success: boolean;
  synced: {
    redis: {
      hotContext: boolean;
      taskContexts: number;
    };
    files: {
      registry: boolean;
      taskContexts: number;
      hotContext: boolean;
    };
  };
  errors: string[];
  timestamp: string;
}

export function createSyncHotContextTool(deps: ToolDependencies): Tool<unknown, SyncHotContextOutput> {
  return {
    async execute(rawInput: unknown): Promise<SyncHotContextOutput> {
      const input = SyncHotContextInputSchema.parse(rawInput);
      const { syncRedis, syncFiles, taskIds, updateRegistry } = input;

      const timestamp = new Date().toISOString();
      const errors: string[] = [];
      const synced = {
        redis: { hotContext: false, taskContexts: 0 },
        files: { registry: false, taskContexts: 0, hotContext: false }
      };

      // Get global context
      const globalContext = await db.getGlobalContext(deps.projectId);
      if (!globalContext) {
        throw new Error(`Global context not found for project: ${deps.projectId}`);
      }

      // Get tasks to sync
      let tasksToSync: db.TaskContext[];
      if (taskIds && taskIds.length > 0) {
        const tasks = await Promise.all(taskIds.map(id => db.getTaskContext(id)));
        tasksToSync = tasks.filter((t): t is db.TaskContext => t !== null);
      } else {
        tasksToSync = await db.getAllTaskContexts();
        // Filter to active tasks
        tasksToSync = tasksToSync.filter(t =>
          t.status === 'in_progress' || t.status === 'pending' || t.status === 'blocked'
        );
      }

      // Get active task
      const activeTask = globalContext.activeTaskId
        ? tasksToSync.find(t => t.taskId === globalContext.activeTaskId) || null
        : null;

      // Sync to Redis
      if (syncRedis) {
        try {
          // Build and set hot context
          const hotContext: HotContext = {
            projectId: deps.projectId,
            activeTaskId: globalContext.activeTaskId,
            taskContext: activeTask ? {
              taskId: activeTask.taskId,
              name: activeTask.name,
              status: activeTask.status,
              currentPhase: activeTask.currentPhase,
              iteration: activeTask.iteration,
              immediateContext: activeTask.immediateContext,
              keyFiles: activeTask.keyFiles,
              resumePrompt: activeTask.resumePrompt
            } : undefined,
            globalContext: {
              hardRules: globalContext.hardRules,
              techStack: globalContext.techStack,
              keyPaths: globalContext.keyPaths
            },
            lastUpdated: timestamp
          };

          await deps.redis.setHotContext(hotContext);
          synced.redis.hotContext = true;

          // Sync individual task contexts
          for (const task of tasksToSync) {
            try {
              await deps.redis.setTaskContext(task.taskId, {
                taskId: task.taskId,
                name: task.name,
                status: task.status,
                currentPhase: task.currentPhase,
                iteration: task.iteration,
                score: task.score,
                immediateContext: task.immediateContext,
                keyFiles: task.keyFiles,
                resumePrompt: task.resumePrompt
              });
              synced.redis.taskContexts++;
            } catch (error) {
              errors.push(`Redis sync failed for task ${task.taskId}: ${error}`);
            }
          }
        } catch (error) {
          errors.push(`Redis hot context sync failed: ${error}`);
        }
      }

      // Sync to files
      if (syncFiles) {
        const contextsDir = path.join(process.cwd(), deps.contextsDir);

        // Ensure directories exist
        const taskAgentsDir = path.join(contextsDir, 'task-agents');
        const sharedDir = path.join(contextsDir, 'shared');

        try {
          if (!fs.existsSync(taskAgentsDir)) {
            fs.mkdirSync(taskAgentsDir, { recursive: true });
          }
          if (!fs.existsSync(sharedDir)) {
            fs.mkdirSync(sharedDir, { recursive: true });
          }
        } catch (error) {
          errors.push(`Failed to create directories: ${error}`);
        }

        // Update registry
        if (updateRegistry) {
          try {
            const registry = {
              version: '1.0',
              activeTask: globalContext.activeTaskId || null,
              lastUpdated: timestamp,
              tasks: {} as Record<string, unknown>
            };

            for (const task of tasksToSync) {
              registry.tasks[task.taskId] = {
                name: task.name,
                status: task.status,
                contextFile: `task-agents/${task.taskId}.json`,
                tokenEstimate: task.tokenEstimate || 500,
                priority: task.priority,
                keywords: task.keywords,
                lastSession: task.lastSessionAt?.toISOString()
              };
            }

            const registryPath = path.join(contextsDir, '_registry.json');
            fs.writeFileSync(registryPath, JSON.stringify(registry, null, 2));
            synced.files.registry = true;
          } catch (error) {
            errors.push(`Registry sync failed: ${error}`);
          }
        }

        // Sync task context files
        for (const task of tasksToSync) {
          try {
            const taskFile = {
              taskId: task.taskId,
              agentType: task.agentType,
              version: '1.0',
              lastUpdated: timestamp,
              state: {
                phase: task.currentPhase,
                iteration: task.iteration,
                score: task.score,
                status: task.status,
                lockedElements: task.lockedElements
              },
              immediateContext: task.immediateContext,
              keyFiles: task.keyFiles,
              technicalDecisions: task.technicalDecisions,
              resumePrompt: task.resumePrompt
            };

            const filePath = path.join(taskAgentsDir, `${task.taskId}.json`);
            fs.writeFileSync(filePath, JSON.stringify(taskFile, null, 2));
            synced.files.taskContexts++;
          } catch (error) {
            errors.push(`File sync failed for task ${task.taskId}: ${error}`);
          }
        }

        // Sync hot context file
        try {
          const hotContextFile = {
            projectId: deps.projectId,
            activeTaskId: globalContext.activeTaskId,
            lastUpdated: timestamp,
            taskContext: activeTask ? {
              taskId: activeTask.taskId,
              name: activeTask.name,
              status: activeTask.status,
              currentPhase: activeTask.currentPhase,
              iteration: activeTask.iteration,
              immediateContext: activeTask.immediateContext,
              keyFiles: activeTask.keyFiles.slice(0, 5),
              resumePrompt: activeTask.resumePrompt
            } : null,
            globalContext: {
              hardRules: globalContext.hardRules,
              techStack: globalContext.techStack,
              keyPaths: globalContext.keyPaths
            }
          };

          const hotContextPath = path.join(contextsDir, '_hot_context.json');
          fs.writeFileSync(hotContextPath, JSON.stringify(hotContextFile, null, 2));
          synced.files.hotContext = true;
        } catch (error) {
          errors.push(`Hot context file sync failed: ${error}`);
        }

        // Sync shared constants
        try {
          const sharedConstants = {
            version: '1.0',
            project: deps.projectId,
            hardRules: globalContext.hardRules,
            techStack: globalContext.techStack,
            paths: globalContext.keyPaths,
            services: globalContext.services
          };

          const sharedPath = path.join(sharedDir, 'project-constants.json');
          fs.writeFileSync(sharedPath, JSON.stringify(sharedConstants, null, 2));
        } catch (error) {
          errors.push(`Shared constants sync failed: ${error}`);
        }
      }

      return {
        success: errors.length === 0,
        synced,
        errors,
        timestamp
      };
    }
  };
}
