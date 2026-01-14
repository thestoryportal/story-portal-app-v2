/**
 * get_unified_context Tool
 * Aggregates context from all sources for a task or globally
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const GetUnifiedContextInputSchema = z.object({
  taskId: z.string().optional().describe('Task ID to get context for. If omitted, returns global context.'),
  includeRelationships: z.boolean().default(true).describe('Include task relationships from Neo4j'),
  includeVersionHistory: z.boolean().default(false).describe('Include recent version history'),
  maxVersions: z.number().default(5).describe('Maximum versions to include if includeVersionHistory is true')
});

export type GetUnifiedContextInput = z.infer<typeof GetUnifiedContextInputSchema>;

export interface UnifiedContextOutput {
  projectId: string;
  global: {
    hardRules: string[];
    techStack: string[];
    keyPaths: Record<string, string>;
    services: Record<string, string>;
  };
  task?: {
    taskId: string;
    name: string;
    status: string;
    currentPhase?: string;
    iteration: number;
    score?: number;
    lockedElements: string[];
    immediateContext: {
      workingOn: string | null;
      lastAction: string | null;
      nextStep: string | null;
      blockers: string[];
    };
    keyFiles: string[];
    technicalDecisions: string[];
    resumePrompt?: string;
  };
  relationships?: {
    blocks: Array<{ taskId: string; name: string; status: string }>;
    blockedBy: Array<{ taskId: string; name: string; status: string }>;
    dependsOn: Array<{ taskId: string; name: string; status: string }>;
    relatedTo: Array<{ taskId: string; name: string; status: string }>;
  };
  versionHistory?: Array<{
    version: number;
    createdAt: string;
    changeType?: string;
    changeSummary?: string;
  }>;
  conflicts?: Array<{
    id: string;
    type: string;
    severity: string;
    description: string;
  }>;
  metadata: {
    source: 'database' | 'cache' | 'hybrid';
    loadedAt: string;
    cacheHit: boolean;
  };
}

export function createGetUnifiedContextTool(deps: ToolDependencies): Tool<unknown, UnifiedContextOutput> {
  return {
    async execute(rawInput: unknown): Promise<UnifiedContextOutput> {
      const input = GetUnifiedContextInputSchema.parse(rawInput);
      const { taskId, includeRelationships, includeVersionHistory, maxVersions } = input;

      let cacheHit = false;
      const loadedAt = new Date().toISOString();

      // Try to get from Redis cache first
      if (taskId) {
        const cachedTask = await deps.redis.getTaskContext(taskId);
        if (cachedTask) {
          cacheHit = true;
        }
      }

      // Load global context from database
      const globalContext = await db.getGlobalContext(deps.projectId);
      if (!globalContext) {
        throw new Error(`Global context not found for project: ${deps.projectId}`);
      }

      const result: UnifiedContextOutput = {
        projectId: deps.projectId,
        global: {
          hardRules: globalContext.hardRules,
          techStack: globalContext.techStack,
          keyPaths: globalContext.keyPaths,
          services: globalContext.services
        },
        metadata: {
          source: cacheHit ? 'cache' : 'database',
          loadedAt,
          cacheHit
        }
      };

      // Load task context if requested
      if (taskId) {
        const taskContext = await db.getTaskContext(taskId);
        if (taskContext) {
          result.task = {
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
            resumePrompt: taskContext.resumePrompt
          };

          // Update Redis cache
          await deps.redis.setTaskContext(taskId, result.task);

          // Load relationships if requested (requires Neo4j)
          if (includeRelationships && deps.neo4j) {
            const graph = await deps.neo4j.getTaskGraph(taskId);
            if (graph) {
              result.relationships = {
                blocks: graph.relationships.blocks.map(t => ({
                  taskId: t.taskId,
                  name: t.name,
                  status: t.status
                })),
                blockedBy: graph.relationships.blockedBy.map(t => ({
                  taskId: t.taskId,
                  name: t.name,
                  status: t.status
                })),
                dependsOn: graph.relationships.dependsOn.map(t => ({
                  taskId: t.taskId,
                  name: t.name,
                  status: t.status
                })),
                relatedTo: graph.relationships.relatedTo.map(t => ({
                  taskId: t.taskId,
                  name: t.name,
                  status: t.status
                }))
              };
            }
          }

          // Load version history if requested
          if (includeVersionHistory) {
            const versions = await db.getContextVersions(taskId, maxVersions);
            result.versionHistory = versions.map(v => ({
              version: v.version,
              createdAt: v.createdAt.toISOString(),
              changeType: v.changeType,
              changeSummary: v.changeSummary
            }));
          }
        }
      }

      // Check for unresolved conflicts
      const conflicts = await db.getUnresolvedConflicts();
      const relevantConflicts = taskId
        ? conflicts.filter(c => c.taskAId === taskId || c.taskBId === taskId)
        : conflicts;

      if (relevantConflicts.length > 0) {
        result.conflicts = relevantConflicts.map(c => ({
          id: c.id,
          type: c.conflictType,
          severity: c.severity,
          description: c.description
        }));
      }

      return result;
    }
  };
}
