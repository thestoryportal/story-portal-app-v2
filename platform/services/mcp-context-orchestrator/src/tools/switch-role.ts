/**
 * switch_role Tool
 * Switches from one role to another with handoff artifact creation.
 * Saves current role state, creates handoff, and loads new role context.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { RoleContext } from '../platform/role-context-adapter.js';

export const SwitchRoleInputSchema = z.object({
  from_role_id: z.string().describe('Current role ID to switch from'),
  to_role_id: z.string().describe('Target role ID to switch to'),
  handoff_artifacts: z
    .array(
      z.object({
        type: z.string().describe('Artifact type (e.g., "file", "decision", "context")'),
        path: z.string().optional().describe('File path if type is "file"'),
        content: z.string().optional().describe('Artifact content or summary'),
        metadata: z.record(z.unknown()).optional().describe('Additional artifact metadata'),
      })
    )
    .default([])
    .describe('Artifacts to pass to the new role'),
  preserve_context: z.boolean().default(true).describe('Whether to preserve context during handoff'),
});

export type SwitchRoleInput = z.infer<typeof SwitchRoleInputSchema>;

export interface SwitchRoleOutput {
  success: boolean;
  new_context: RoleContext;
  handoff_id: string;
}

export function createSwitchRoleTool(deps: ToolDependencies): Tool<unknown, SwitchRoleOutput> {
  return {
    async execute(rawInput: unknown): Promise<SwitchRoleOutput> {
      const input = SwitchRoleInputSchema.parse(rawInput);
      const { from_role_id, to_role_id, handoff_artifacts, preserve_context } = input;

      if (!deps.roleContext) {
        throw new Error('Role context adapter not available');
      }

      const timestamp = new Date().toISOString();

      // Perform the role switch
      const result = await deps.roleContext.switchRole({
        from_role_id,
        to_role_id,
        handoff_artifacts,
        preserve_context,
      });

      // Platform Services Integration
      if (deps.platform) {
        // Create EventStore entry for role switch audit trail
        try {
          await deps.platform.eventStore.createContextEvent(
            to_role_id,
            'role_switched',
            {
              from_role_id,
              to_role_id,
              handoff_id: result.handoff_id,
              artifacts_count: handoff_artifacts.length,
              preserve_context,
              timestamp,
            }
          );
        } catch (error) {
          console.error('Failed to create EventStore role switch event:', error);
        }

        // Cache new role context in SemanticCache for similarity search
        try {
          await deps.platform.semanticCache.cacheTaskContext(`role:${to_role_id}`, {
            name: result.new_context.role.name,
            description: result.new_context.role.description,
            keywords: result.new_context.role.tags,
            keyFiles: [],
            immediateContext: {
              workingOn: `Role context for ${result.new_context.role.name}`,
              lastAction: `Switched from ${from_role_id}`,
              nextStep: null,
              blockers: [],
            },
            technicalDecisions: [],
            resumePrompt: result.new_context.system_prompt,
          });
        } catch (error) {
          console.error('Failed to cache role context in SemanticCache:', error);
        }

        // Save hot state for quick access
        try {
          await deps.platform.stateManager.saveHotState(`role:${to_role_id}`, {
            roleId: to_role_id,
            roleName: result.new_context.role.name,
            department: result.new_context.role.department,
            roleType: result.new_context.role.role_type,
            tokenCount: result.new_context.token_count,
            handoffId: result.handoff_id,
            timestamp,
          });
        } catch (error) {
          console.error('Failed to save hot state to StateManager:', error);
        }
      }

      // Update Redis cache with role context
      await deps.redis.setTaskContext(`role:${to_role_id}`, {
        taskId: `role:${to_role_id}`,
        name: result.new_context.role.name,
        status: 'active',
        currentPhase: 'role_active',
        iteration: 1,
        immediateContext: {
          workingOn: result.new_context.role.description,
          lastAction: `Switched from ${from_role_id}`,
          nextStep: null,
          blockers: [],
        },
        keyFiles: [],
        resumePrompt: result.new_context.system_prompt,
      });

      return result;
    },
  };
}
