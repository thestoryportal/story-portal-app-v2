/**
 * generate_skill Tool
 * Generates a skill definition from role description using LLM
 * from the L14 SkillLibrary service.
 */

import { z } from 'zod';
import type { ToolDependencies, Tool } from './index.js';
import type { GeneratedSkill } from '../platform/skill-management-adapter.js';

export const GenerateSkillInputSchema = z.object({
  role_title: z.string().describe('Title of the role'),
  role_description: z.string().describe('Description of what the role does'),
  responsibilities: z.array(z.string()).optional().describe('List of primary responsibilities'),
  priority: z.enum(['critical', 'high', 'medium', 'low']).optional().describe('Skill priority (critical/high/medium/low)'),
});

export type GenerateSkillInput = z.infer<typeof GenerateSkillInputSchema>;

export interface GenerateSkillOutput extends GeneratedSkill {}

export function createGenerateSkillTool(deps: ToolDependencies): Tool<unknown, GenerateSkillOutput> {
  return {
    async execute(rawInput: unknown): Promise<GenerateSkillOutput> {
      const input = GenerateSkillInputSchema.parse(rawInput);
      const { role_title, role_description, responsibilities, priority } = input;

      if (!deps.skillManagement) {
        throw new Error('Skill management adapter not available');
      }

      const result = await deps.skillManagement.generateSkill({
        role_title,
        role_description,
        responsibilities,
        priority,
      });

      // Platform Services Integration - create event for audit trail
      if (deps.platform) {
        try {
          await deps.platform.eventStore.createContextEvent(
            result.skill.id,
            'skill_generated',
            {
              role_title,
              skill_id: result.skill.id,
              priority: result.skill.priority,
              validation_status: result.validation.valid ? 'valid' : 'invalid',
              confidence: result.confidence,
              token_count: result.skill.token_count,
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
