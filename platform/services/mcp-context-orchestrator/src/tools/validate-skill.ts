/**
 * validate_skill Tool
 * Validates a skill definition against the schema
 * from the L14 SkillLibrary service.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { ValidationResult } from '../platform/skill-management-adapter.js';

export const ValidateSkillInputSchema = z.object({
  skill_yaml: z.string().describe('YAML content of the skill to validate'),
});

export type ValidateSkillInput = z.infer<typeof ValidateSkillInputSchema>;

export interface ValidateSkillOutput extends ValidationResult {}

export function createValidateSkillTool(deps: ToolDependencies): Tool<unknown, ValidateSkillOutput> {
  return {
    async execute(rawInput: unknown): Promise<ValidateSkillOutput> {
      const input = ValidateSkillInputSchema.parse(rawInput);
      const { skill_yaml } = input;

      if (!deps.skillManagement) {
        throw new Error('Skill management adapter not available');
      }

      const result = await deps.skillManagement.validateSkill({
        skill_yaml,
      });

      // Platform Services Integration - create event for audit trail
      if (deps.platform) {
        try {
          await deps.platform.eventStore.createContextEvent(
            'skill-validation',
            'skill_validated',
            {
              valid: result.valid,
              issues_count: result.issues.length,
              error_count: result.issues.filter(i => i.severity === 'error').length,
              warning_count: result.issues.filter(i => i.severity === 'warning').length,
              suggestions_count: result.suggestions.length,
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
