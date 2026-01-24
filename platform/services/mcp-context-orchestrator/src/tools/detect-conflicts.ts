/**
 * detect_conflicts Tool
 * Cross-system conflict detection between task contexts
 */

import { z } from 'zod';
import * as db from '../db/client.js';
import type { ToolDependencies, Tool } from './index.js';

export const DetectConflictsInputSchema = z.object({
  taskIds: z.array(z.string()).optional().describe('Specific tasks to check. If omitted, checks all active tasks.'),
  conflictTypes: z.array(z.enum([
    'state_mismatch',
    'file_conflict',
    'spec_contradiction',
    'version_divergence',
    'lock_collision',
    'data_inconsistency'
  ])).optional().describe('Types of conflicts to detect. If omitted, checks all types.')
});

export type DetectConflictsInput = z.infer<typeof DetectConflictsInputSchema>;

export interface DetectedConflict {
  id?: string;
  taskAId: string;
  taskBId?: string;
  conflictType: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  strength: number;
  description: string;
  evidence: {
    field?: string;
    expectedValue?: unknown;
    actualValue?: unknown;
    location?: string;
  };
  suggestedResolution?: string;
}

export interface DetectConflictsOutput {
  detected: DetectedConflict[];
  existing: Array<{
    id: string;
    taskAId: string;
    taskBId?: string;
    conflictType: string;
    severity: string;
    description: string;
    detectedAt: string;
  }>;
  summary: {
    newConflicts: number;
    existingConflicts: number;
    criticalCount: number;
    highCount: number;
  };
  timestamp: string;
}

export function createDetectConflictsTool(deps: ToolDependencies): Tool<unknown, DetectConflictsOutput> {
  return {
    async execute(rawInput: unknown): Promise<DetectConflictsOutput> {
      const input = DetectConflictsInputSchema.parse(rawInput);
      const { taskIds, conflictTypes } = input;

      const timestamp = new Date().toISOString();
      const detected: DetectedConflict[] = [];

      // Get tasks to check
      let tasksToCheck: db.TaskContext[];
      if (taskIds && taskIds.length > 0) {
        const tasks = await Promise.all(taskIds.map(id => db.getTaskContext(id)));
        tasksToCheck = tasks.filter((t): t is db.TaskContext => t !== null);
      } else {
        tasksToCheck = await db.getAllTaskContexts('in_progress');
      }

      // Get all unresolved conflicts
      const existingConflicts = await db.getUnresolvedConflicts();

      // Detect new conflicts
      const typesToCheck = conflictTypes || [
        'state_mismatch',
        'file_conflict',
        'version_divergence',
        'lock_collision',
        'data_inconsistency'
      ];

      // Check for file conflicts between tasks
      if (typesToCheck.includes('file_conflict')) {
        for (let i = 0; i < tasksToCheck.length; i++) {
          for (let j = i + 1; j < tasksToCheck.length; j++) {
            const taskA = tasksToCheck[i];
            const taskB = tasksToCheck[j];

            // Find overlapping key files
            const overlappingFiles = taskA.keyFiles.filter((f: string) => taskB.keyFiles.includes(f));
            if (overlappingFiles.length > 0) {
              // Check if this conflict already exists
              const exists = existingConflicts.some(
                c => c.conflictType === 'file_conflict' &&
                  ((c.taskAId === taskA.taskId && c.taskBId === taskB.taskId) ||
                   (c.taskAId === taskB.taskId && c.taskBId === taskA.taskId))
              );

              if (!exists) {
                detected.push({
                  taskAId: taskA.taskId,
                  taskBId: taskB.taskId,
                  conflictType: 'file_conflict',
                  severity: overlappingFiles.length > 3 ? 'high' : 'medium',
                  strength: Math.min(overlappingFiles.length / 5, 1),
                  description: `Tasks "${taskA.name}" and "${taskB.name}" are both modifying: ${overlappingFiles.slice(0, 3).join(', ')}${overlappingFiles.length > 3 ? ` and ${overlappingFiles.length - 3} more` : ''}`,
                  evidence: {
                    field: 'keyFiles',
                    expectedValue: taskA.keyFiles,
                    actualValue: taskB.keyFiles,
                    location: overlappingFiles.join(', ')
                  },
                  suggestedResolution: 'Coordinate changes between tasks or sequence their work on shared files.'
                });
              }
            }
          }
        }
      }

      // Check for lock collisions
      if (typesToCheck.includes('lock_collision')) {
        for (const task of tasksToCheck) {
          const lockInfo = await deps.redis.getLockInfo(task.taskId);
          if (lockInfo) {
            // Check if lock is stale (expired)
            const expiresAt = new Date(lockInfo.expiresAt);
            if (expiresAt < new Date()) {
              detected.push({
                taskAId: task.taskId,
                conflictType: 'lock_collision',
                severity: 'medium',
                strength: 0.7,
                description: `Task "${task.name}" has a stale lock from session ${lockInfo.sessionId}`,
                evidence: {
                  field: 'lock',
                  expectedValue: null,
                  actualValue: lockInfo,
                  location: `Redis key: context:lock:${task.taskId}`
                },
                suggestedResolution: 'Clear stale lock or verify session is still active.'
              });
            }
          }
        }
      }

      // Check for state mismatches between DB and cache
      if (typesToCheck.includes('state_mismatch')) {
        for (const task of tasksToCheck) {
          const cachedTask = await deps.redis.getTaskContext(task.taskId);
          if (cachedTask) {
            const cached = cachedTask as Record<string, unknown>;
            // Compare key fields
            if (cached.status !== task.status ||
                cached.iteration !== task.iteration ||
                cached.currentPhase !== task.currentPhase) {
              detected.push({
                taskAId: task.taskId,
                conflictType: 'state_mismatch',
                severity: 'high',
                strength: 0.9,
                description: `Task "${task.name}" has mismatched state between database and cache`,
                evidence: {
                  field: 'state',
                  expectedValue: { status: task.status, iteration: task.iteration, phase: task.currentPhase },
                  actualValue: { status: cached.status, iteration: cached.iteration, phase: cached.currentPhase },
                  location: 'database vs redis'
                },
                suggestedResolution: 'Sync cache with database using sync_hot_context tool.'
              });
            }
          }
        }
      }

      // Check for version divergence
      if (typesToCheck.includes('version_divergence')) {
        for (const task of tasksToCheck) {
          const versions = await db.getContextVersions(task.taskId, 10);
          if (versions.length >= 2) {
            // Check if recent versions have conflicting changes
            const recentVersions = versions.slice(0, 5);
            const recoveryVersions = recentVersions.filter(v => v.changeType === 'recovery');
            if (recoveryVersions.length >= 2) {
              detected.push({
                taskAId: task.taskId,
                conflictType: 'version_divergence',
                severity: 'medium',
                strength: 0.6,
                description: `Task "${task.name}" has multiple recovery versions, indicating instability`,
                evidence: {
                  field: 'versions',
                  expectedValue: 'stable progression',
                  actualValue: `${recoveryVersions.length} recovery versions in last ${recentVersions.length} versions`
                },
                suggestedResolution: 'Review recovery history and stabilize task state.'
              });
            }
          }
        }
      }

      // Save newly detected conflicts to database
      for (const conflict of detected) {
        const saved = await db.createConflict({
          taskAId: conflict.taskAId,
          taskBId: conflict.taskBId,
          conflictType: conflict.conflictType as db.ConflictType,
          description: conflict.description,
          severity: conflict.severity,
          strength: conflict.strength,
          evidence: conflict.evidence,
          detectedBy: 'system',
          detectionMethod: 'detect_conflicts tool'
        });
        conflict.id = saved.id;
      }

      // Calculate summary
      const allConflicts = [...detected, ...existingConflicts];
      const summary = {
        newConflicts: detected.length,
        existingConflicts: existingConflicts.length,
        criticalCount: allConflicts.filter(c => c.severity === 'critical').length,
        highCount: allConflicts.filter(c => c.severity === 'high').length
      };

      // Platform Services Integration
      if (deps.platform && detected.length > 0) {
        // Log conflict detection events to EventStore for audit trail
        try {
          await deps.platform.eventStore.createContextEvent(
            deps.projectId,
            'conflicts_detected',
            {
              newConflicts: detected.length,
              totalConflicts: allConflicts.length,
              criticalCount: summary.criticalCount,
              highCount: summary.highCount,
              conflictTypes: [...new Set(detected.map(c => c.conflictType))],
              affectedTasks: [...new Set(detected.flatMap(c => [c.taskAId, c.taskBId].filter(Boolean)))]
            },
            undefined // no session ID for system detection
          );
        } catch (error) {
          console.error('Failed to log conflict detection to EventStore:', error);
        }
      }

      return {
        detected,
        existing: existingConflicts.map(c => ({
          id: c.id,
          taskAId: c.taskAId,
          taskBId: c.taskBId,
          conflictType: c.conflictType,
          severity: c.severity,
          description: c.description,
          detectedAt: c.detectedAt.toISOString()
        })),
        summary,
        timestamp
      };
    }
  };
}
