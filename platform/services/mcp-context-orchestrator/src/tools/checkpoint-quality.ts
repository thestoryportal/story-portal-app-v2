/**
 * checkpoint_quality Tool
 * Records quality checkpoints during execution and determines
 * whether to continue, stop, or escalate based on quality scores.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';

export const CheckpointQualityInputSchema = z.object({
  execution_id: z.string().describe('The execution/task ID to checkpoint'),
  checkpoint_name: z.string().describe('Name of this quality checkpoint'),
  quality_score: z.number().min(0).max(1).describe('Quality score between 0.0 and 1.0'),
});

export type CheckpointQualityInput = z.infer<typeof CheckpointQualityInputSchema>;

export interface CheckpointQualityOutput {
  action: 'STOP' | 'CONTINUE' | 'ESCALATE';
  message: string;
}

export function createCheckpointQualityTool(deps: ToolDependencies): Tool<unknown, CheckpointQualityOutput> {
  return {
    async execute(rawInput: unknown): Promise<CheckpointQualityOutput> {
      const input = CheckpointQualityInputSchema.parse(rawInput);
      const { execution_id, checkpoint_name, quality_score } = input;

      if (!deps.roleContext) {
        throw new Error('Role context adapter not available');
      }

      const result = await deps.roleContext.checkpointQuality({
        execution_id,
        checkpoint_name,
        quality_score,
      });

      const timestamp = new Date().toISOString();

      // Platform Services Integration
      if (deps.platform) {
        // Create EventStore entry for quality checkpoint
        try {
          await deps.platform.eventStore.createContextEvent(
            execution_id,
            'quality_checkpoint',
            {
              execution_id,
              checkpoint_name,
              quality_score,
              action: result.action,
              message: result.message,
              timestamp,
            }
          );
        } catch (error) {
          console.error('Failed to create EventStore quality checkpoint event:', error);
        }

        // If STOP or ESCALATE, create alert in state manager
        if (result.action === 'STOP' || result.action === 'ESCALATE') {
          try {
            await deps.platform.stateManager.saveHotState(`quality-alert:${execution_id}`, {
              executionId: execution_id,
              checkpointName: checkpoint_name,
              qualityScore: quality_score,
              action: result.action,
              message: result.message,
              severity: result.action === 'STOP' ? 'critical' : 'warning',
              timestamp,
            });
          } catch (error) {
            console.error('Failed to save quality alert state:', error);
          }
        }

        // Track quality trend in SemanticCache
        try {
          await deps.platform.semanticCache.cacheTaskContext(`quality:${execution_id}:${checkpoint_name}`, {
            name: `Quality: ${checkpoint_name}`,
            description: result.message,
            keywords: [result.action.toLowerCase(), 'quality', 'checkpoint'],
            keyFiles: [],
            immediateContext: {
              workingOn: `Quality checkpoint: ${checkpoint_name}`,
              lastAction: `Score: ${quality_score} -> ${result.action}`,
              nextStep: result.action === 'CONTINUE' ? 'Proceed with execution' : result.action === 'ESCALATE' ? 'Await human review' : 'Execution halted',
              blockers: result.action === 'STOP' ? ['Quality below threshold'] : [],
            },
            technicalDecisions: [`${checkpoint_name}: ${quality_score} (${result.action})`],
            resumePrompt: result.message,
          });
        } catch (error) {
          console.error('Failed to cache quality checkpoint in SemanticCache:', error);
        }
      }

      // Update Redis cache with checkpoint status
      await deps.redis.setTaskContext(`quality:${execution_id}`, {
        taskId: execution_id,
        name: `Quality: ${execution_id}`,
        status: result.action === 'STOP' ? 'blocked' : result.action === 'ESCALATE' ? 'pending' : 'in_progress',
        currentPhase: `checkpoint:${checkpoint_name}`,
        iteration: 1,
        immediateContext: {
          workingOn: `Quality monitoring for ${execution_id}`,
          lastAction: `Checkpoint "${checkpoint_name}": ${quality_score}`,
          nextStep: result.action === 'CONTINUE' ? 'Continue execution' : result.action === 'ESCALATE' ? 'Human review needed' : 'Execution stopped',
          blockers: result.action === 'STOP' ? ['Quality threshold not met'] : [],
        },
        keyFiles: [],
        resumePrompt: result.message,
      });

      // If action is STOP, also record in Neo4j for task graph (if available)
      if (result.action === 'STOP' && deps.neo4j) {
        try {
          // Record quality failure as a blocking relationship
          await deps.neo4j.recordSession(`quality-block:${execution_id}`, execution_id);
        } catch (error) {
          console.error('Failed to record quality block in Neo4j:', error);
        }
      }

      return result;
    },
  };
}
