/**
 * optimize_skills Tool
 * Optimizes a set of skills for token budget using specified strategy
 * from the L14 SkillLibrary service.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { OptimizedSkillSet } from '../platform/skill-management-adapter.js';

export const OptimizeSkillsInputSchema = z.object({
  skill_ids: z.array(z.string()).describe('IDs of skills to optimize'),
  token_budget: z.number().describe('Maximum token budget'),
  strategy: z.enum(['token_reduction', 'priority_loading', 'context_aware']).optional().describe('Optimization strategy (token_reduction/priority_loading/context_aware)'),
  context: z.string().optional().describe('Context for context_aware strategy'),
});

export type OptimizeSkillsInput = z.infer<typeof OptimizeSkillsInputSchema>;

export interface OptimizeSkillsOutput extends OptimizedSkillSet {}

export function createOptimizeSkillsTool(deps: ToolDependencies): Tool<unknown, OptimizeSkillsOutput> {
  return {
    async execute(rawInput: unknown): Promise<OptimizeSkillsOutput> {
      const input = OptimizeSkillsInputSchema.parse(rawInput);
      const { skill_ids, token_budget, strategy, context } = input;

      if (!deps.skillManagement) {
        throw new Error('Skill management adapter not available');
      }

      // Validate inputs
      if (skill_ids.length === 0) {
        throw new Error('At least one skill_id must be provided');
      }

      if (token_budget <= 0) {
        throw new Error('token_budget must be a positive number');
      }

      const result = await deps.skillManagement.optimizeSkills({
        skill_ids,
        token_budget,
        strategy,
        context,
      });

      // Platform Services Integration - create event for audit trail
      if (deps.platform) {
        try {
          await deps.platform.eventStore.createContextEvent(
            'skill-optimization',
            'skills_optimized',
            {
              input_skill_count: skill_ids.length,
              output_skill_count: result.skills.length,
              token_budget,
              total_tokens: result.total_tokens,
              budget_remaining: result.budget_remaining,
              strategy_used: result.strategy_used,
              optimizations_applied: result.optimizations_applied,
              loading_order: result.loading_order,
            }
          );
        } catch (error) {
          console.error('Failed to create EventStore entry:', error);
        }
      }

      return result;
    },
  };
}
