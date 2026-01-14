/**
 * get_task_graph Tool
 * Neo4j-powered task relationship view
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const GetTaskGraphInputSchema = z.object({
  taskId: z.string().optional().describe('Task ID to get graph for. If omitted, returns overview of all tasks.'),
  depth: z.number().default(2).describe('How many relationship levels to traverse'),
  includeCompleted: z.boolean().default(false).describe('Include completed tasks in results')
});

export type GetTaskGraphInput = z.infer<typeof GetTaskGraphInputSchema>;

export interface TaskGraphNode {
  taskId: string;
  name: string;
  status: string;
  phase?: string;
  priority: number;
  score?: number;
}

export interface TaskGraphEdge {
  from: string;
  to: string;
  type: 'blocks' | 'depends_on' | 'related_to';
  reason?: string;
}

export interface GetTaskGraphOutput {
  nodes: TaskGraphNode[];
  edges: TaskGraphEdge[];
  focus?: {
    task: TaskGraphNode;
    blockedBy: TaskGraphNode[];
    blocks: TaskGraphNode[];
    dependsOn: TaskGraphNode[];
    dependencyOf: TaskGraphNode[];
    relatedTo: TaskGraphNode[];
    agents: Array<{ agentId: string; type: string }>;
    recentSessions: Array<{ sessionId: string; startedAt: string }>;
  };
  readyTasks: TaskGraphNode[];
  blockedTasks: TaskGraphNode[];
  summary: {
    totalTasks: number;
    inProgress: number;
    blocked: number;
    completed: number;
    pending: number;
  };
}

export function createGetTaskGraphTool(deps: ToolDependencies): Tool<unknown, GetTaskGraphOutput> {
  return {
    async execute(rawInput: unknown): Promise<GetTaskGraphOutput> {
      const input = GetTaskGraphInputSchema.parse(rawInput);
      const { taskId, includeCompleted } = input;

      const nodes: TaskGraphNode[] = [];
      const edges: TaskGraphEdge[] = [];
      const nodeIds = new Set<string>();

      // Get all tasks from database
      const allTasks = await db.getAllTaskContexts();
      const filteredTasks = includeCompleted
        ? allTasks
        : allTasks.filter(t => t.status !== 'completed' && t.status !== 'archived');

      // Build nodes
      for (const task of filteredTasks) {
        if (!nodeIds.has(task.taskId)) {
          nodes.push({
            taskId: task.taskId,
            name: task.name,
            status: task.status,
            phase: task.currentPhase,
            priority: task.priority,
            score: task.score
          });
          nodeIds.add(task.taskId);
        }

        // Get relationships from database
        const relationships = await db.getTaskRelationships(task.taskId);
        for (const rel of relationships) {
          // Only add edges where both nodes exist
          if (nodeIds.has(rel.sourceTaskId) || filteredTasks.some(t => t.taskId === rel.sourceTaskId)) {
            if (nodeIds.has(rel.targetTaskId) || filteredTasks.some(t => t.taskId === rel.targetTaskId)) {
              const edgeType = rel.relationshipType.includes('block') ? 'blocks' :
                              rel.relationshipType.includes('depend') ? 'depends_on' : 'related_to';
              edges.push({
                from: rel.sourceTaskId,
                to: rel.targetTaskId,
                type: edgeType
              });
            }
          }
        }
      }

      // Get focus task details if specified (requires Neo4j)
      let focus: GetTaskGraphOutput['focus'];
      if (taskId && deps.neo4j) {
        const graph = await deps.neo4j.getTaskGraph(taskId);
        if (graph) {
          focus = {
            task: graph.task,
            blockedBy: graph.relationships.blockedBy,
            blocks: graph.relationships.blocks,
            dependsOn: graph.relationships.dependsOn,
            dependencyOf: graph.relationships.dependencyOf,
            relatedTo: graph.relationships.relatedTo,
            agents: graph.agents.map(a => ({ agentId: a.agentId, type: a.type })),
            recentSessions: graph.recentSessions.map(s => ({
              sessionId: s.sessionId,
              startedAt: s.startedAt
            }))
          };
        }
      }

      // Get ready and blocked tasks (Neo4j provides ready tasks, fallback to filtering)
      const readyTasks = deps.neo4j
        ? await deps.neo4j.getReadyTasks()
        : filteredTasks.filter(t => t.status === 'pending');
      const blockedTasks = filteredTasks.filter(t => t.status === 'blocked');

      // Build summary
      const summary = {
        totalTasks: allTasks.length,
        inProgress: allTasks.filter(t => t.status === 'in_progress').length,
        blocked: allTasks.filter(t => t.status === 'blocked').length,
        completed: allTasks.filter(t => t.status === 'completed').length,
        pending: allTasks.filter(t => t.status === 'pending').length
      };

      return {
        nodes,
        edges,
        focus,
        readyTasks: readyTasks.filter(t =>
          includeCompleted || (t.status !== 'completed' && t.status !== 'archived')
        ),
        blockedTasks: blockedTasks.map(t => ({
          taskId: t.taskId,
          name: t.name,
          status: t.status,
          phase: t.currentPhase,
          priority: t.priority,
          score: t.score
        })),
        summary
      };
    }
  };
}
