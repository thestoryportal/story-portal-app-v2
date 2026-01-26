/**
 * get_skills_for_role Tool
 * Gets all skills assigned to a specific role or agent
 * from the L14 SkillLibrary service.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { SkillDefinition, SkillAssignment } from '../platform/skill-management-adapter.js';

export const GetSkillsForRoleInputSchema = z.object({
  role_id: z.string().optional().describe('Role ID to get skills for'),
  agent_id: z.string().optional().describe('Agent ID to get skills for'),
  category: z.string().optional().describe('Filter by skill category'),
});

export type GetSkillsForRoleInput = z.infer<typeof GetSkillsForRoleInputSchema>;

export interface GetSkillsForRoleOutput {
  skills: SkillDefinition[];
  assignments: SkillAssignment[];
  total_tokens: number;
}

export function createGetSkillsForRoleTool(deps: ToolDependencies): Tool<unknown, GetSkillsForRoleOutput> {
  return {
    async execute(rawInput: unknown): Promise<GetSkillsForRoleOutput> {
      const input = GetSkillsForRoleInputSchema.parse(rawInput);
      const { role_id, agent_id, category } = input;

      if (!deps.skillManagement) {
        throw new Error('Skill management adapter not available');
      }

      // Validate at least one identifier is provided
      if (!role_id && !agent_id) {
        throw new Error('Either role_id or agent_id must be provided');
      }

      const result = await deps.skillManagement.getSkillsForRole({
        role_id,
        agent_id,
        category,
      });

      // Platform Services Integration - create event for audit trail
      if (deps.platform) {
        try {
          await deps.platform.eventStore.createContextEvent(
            role_id || agent_id || 'unknown',
            'skills_retrieved',
            {
              role_id,
              agent_id,
              category,
              skills_count: result.skills.length,
              total_tokens: result.total_tokens,
              skill_ids: result.skills.map(s => s.id),
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
