/**
 * get_role_context Tool
 * Retrieves role context including skills, project context, and constraints
 * from the L13 RoleContextBuilder service.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { RoleTemplate, Skill, ProjectContext } from '../platform/role-context-adapter.js';

export const GetRoleContextInputSchema = z.object({
  role_id: z.string().describe('The role ID to get context for'),
  include_skills: z.boolean().default(true).describe('Include skills in the response'),
  project_context: z.boolean().default(false).describe('Include project context overlay'),
  max_skill_tokens: z.number().default(2000).describe('Maximum tokens to allocate for skill descriptions'),
});

export type GetRoleContextInput = z.infer<typeof GetRoleContextInputSchema>;

export interface GetRoleContextOutput {
  role: RoleTemplate;
  skills: Skill[];
  project_overlay: ProjectContext | null;
  total_tokens: number;
}

export function createGetRoleContextTool(deps: ToolDependencies): Tool<unknown, GetRoleContextOutput> {
  return {
    async execute(rawInput: unknown): Promise<GetRoleContextOutput> {
      const input = GetRoleContextInputSchema.parse(rawInput);
      const { role_id, include_skills, project_context, max_skill_tokens } = input;

      if (!deps.roleContext) {
        throw new Error('Role context adapter not available');
      }

      const result = await deps.roleContext.getRoleContext({
        role_id,
        include_skills,
        project_context,
        max_skill_tokens,
      });

      // Platform Services Integration - create event for audit trail
      if (deps.platform) {
        try {
          await deps.platform.eventStore.createContextEvent(
            role_id,
            'role_context_loaded',
            {
              role_id,
              include_skills,
              project_context,
              total_tokens: result.total_tokens,
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
