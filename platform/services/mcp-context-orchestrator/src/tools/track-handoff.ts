/**
 * track_handoff Tool
 * Tracks handoff status and performs actions (create, acknowledge, reject)
 * on handoff artifacts between roles.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { HandoffArtifact } from '../platform/role-context-adapter.js';

export const TrackHandoffInputSchema = z.object({
  handoff_id: z.string().describe('The handoff ID to track or act on'),
  action: z.enum(['create', 'acknowledge', 'reject']).describe('Action to perform on the handoff'),
});

export type TrackHandoffInput = z.infer<typeof TrackHandoffInputSchema>;

export interface TrackHandoffOutput {
  handoff: HandoffArtifact;
  status: string;
}

export function createTrackHandoffTool(deps: ToolDependencies): Tool<unknown, TrackHandoffOutput> {
  return {
    async execute(rawInput: unknown): Promise<TrackHandoffOutput> {
      const input = TrackHandoffInputSchema.parse(rawInput);
      const { handoff_id, action } = input;

      if (!deps.roleContext) {
        throw new Error('Role context adapter not available');
      }

      const result = await deps.roleContext.trackHandoff({
        handoff_id,
        action,
      });

      // Platform Services Integration
      if (deps.platform) {
        // Create EventStore entry for handoff action
        try {
          await deps.platform.eventStore.createContextEvent(
            handoff_id,
            `handoff_${action}`,
            {
              handoff_id,
              action,
              from_role_id: result.handoff.from_role_id,
              to_role_id: result.handoff.to_role_id,
              status: result.status,
              artifacts_count: result.handoff.artifacts.length,
              timestamp: new Date().toISOString(),
            }
          );
        } catch (error) {
          console.error('Failed to create EventStore handoff event:', error);
        }

        // If acknowledged, mark completion in state manager
        if (action === 'acknowledge') {
          try {
            await deps.platform.stateManager.saveHotState(`handoff:${handoff_id}`, {
              handoffId: handoff_id,
              status: 'acknowledged',
              fromRole: result.handoff.from_role_id,
              toRole: result.handoff.to_role_id,
              acknowledgedAt: result.handoff.acknowledged_at,
            });
          } catch (error) {
            console.error('Failed to save handoff state:', error);
          }
        }

        // If rejected, trigger recovery workflow
        if (action === 'reject') {
          try {
            await deps.platform.eventStore.createContextEvent(
              result.handoff.from_role_id,
              'handoff_rejected',
              {
                handoff_id,
                rejected_by: result.handoff.to_role_id,
                artifacts: result.handoff.artifacts.map((a) => ({
                  type: a.type,
                  path: a.path,
                })),
                requires_recovery: true,
              }
            );
          } catch (error) {
            console.error('Failed to create rejection event:', error);
          }
        }
      }

      // Update Redis cache with handoff status
      await deps.redis.setTaskContext(`handoff:${handoff_id}`, {
        taskId: handoff_id,
        name: `Handoff: ${result.handoff.from_role_id} -> ${result.handoff.to_role_id}`,
        status: result.status === 'acknowledged' ? 'completed' : result.status === 'rejected' ? 'blocked' : 'in_progress',
        currentPhase: result.status,
        iteration: 1,
        immediateContext: {
          workingOn: `Handoff from ${result.handoff.from_role_id} to ${result.handoff.to_role_id}`,
          lastAction: `Action: ${action}`,
          nextStep: result.status === 'pending' ? 'Awaiting acknowledgement' : null,
          blockers: result.status === 'rejected' ? ['Handoff rejected'] : [],
        },
        keyFiles: result.handoff.artifacts
          .filter((a) => a.type === 'file' && a.path)
          .map((a) => a.path as string),
        resumePrompt: `Handoff ${handoff_id} is ${result.status}`,
      });

      return result;
    },
  };
}
