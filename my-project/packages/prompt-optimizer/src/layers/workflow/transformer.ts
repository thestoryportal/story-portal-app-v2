/**
 * Workflow mode transformer.
 * Applies structural transformations based on workflow mode.
 */

import type {
  WorkflowMode,
  WorkflowModeConfig,
  WorkflowModeTransformResult,
  StructuralChange,
  SectionRequirement,
} from '../../types/workflow.js';
import { WORKFLOW_MODE_CONFIGS } from './configs.js';

export class WorkflowModeTransformer {
  private configs: Map<WorkflowMode, WorkflowModeConfig>;

  constructor() {
    this.configs = new Map(
      WORKFLOW_MODE_CONFIGS.map(c => [c.mode, c])
    );
  }

  /**
   * Transform a prompt based on workflow mode.
   * Adds missing required sections and applies structural changes.
   */
  transform(
    prompt: string,
    mode: WorkflowMode
  ): WorkflowModeTransformResult {
    const config = this.configs.get(mode);
    if (!config) {
      return {
        transformed: prompt,
        sectionsAdded: [],
        structuralChanges: [],
        confidenceAdjustment: 0,
      };
    }

    // If minimal optimization mode, apply minimal changes
    if (config.minimalOptimization) {
      return this.minimalTransform(prompt, config);
    }

    return this.fullTransform(prompt, config);
  }

  /**
   * Full transformation for comprehensive modes (SPECIFICATION, BUG_REPORT, ARCHITECTURE).
   * Adds prompts for all missing required sections.
   */
  private fullTransform(
    prompt: string,
    config: WorkflowModeConfig
  ): WorkflowModeTransformResult {
    const changes: StructuralChange[] = [];
    const sectionsAdded: string[] = [];
    let transformed = prompt;

    // Check each required section
    for (const section of config.requiredSections) {
      const isPresent = section.detectionPattern.test(prompt);

      if (!isPresent && section.required) {
        // Add prompting text for missing required section
        transformed = this.addSectionPrompt(transformed, section);
        sectionsAdded.push(section.name);
        changes.push({
          type: 'ADD_SECTION',
          description: `Added "${section.name}" section prompt`,
          after: section.promptIfMissing,
        });
      }
    }

    // Calculate confidence adjustment
    const confidenceAdjustment = this.calculateConfidenceAdjustment(
      config,
      sectionsAdded.length
    );

    return {
      transformed,
      sectionsAdded,
      structuralChanges: changes,
      confidenceAdjustment,
    };
  }

  /**
   * Minimal transformation for quick/feedback/exploration modes.
   * Only adds inline clarifications for truly critical missing info.
   */
  private minimalTransform(
    prompt: string,
    config: WorkflowModeConfig
  ): WorkflowModeTransformResult {
    const changes: StructuralChange[] = [];
    const sectionsAdded: string[] = [];
    let transformed = prompt;

    // Only check required sections marked as required
    const requiredSections = config.requiredSections.filter(s => s.required);

    for (const section of requiredSections) {
      const isPresent = section.detectionPattern.test(prompt);

      if (!isPresent) {
        // For minimal mode, add as inline clarification rather than full section
        transformed += `\n\n[Clarification needed: ${section.promptIfMissing}]`;
        sectionsAdded.push(section.name);
        changes.push({
          type: 'ADD_SECTION',
          description: `Added clarification for "${section.name}"`,
        });
      }
    }

    return {
      transformed,
      sectionsAdded,
      structuralChanges: changes,
      confidenceAdjustment: config.confidenceWeightAdjustment - 1.0,
    };
  }

  /**
   * Add section prompt to transformed text with clear formatting.
   */
  private addSectionPrompt(prompt: string, section: SectionRequirement): string {
    return `${prompt}\n\n**${section.name}**: ${section.promptIfMissing}`;
  }

  /**
   * Calculate confidence adjustment based on missing sections.
   * More missing sections = lower confidence.
   */
  private calculateConfidenceAdjustment(
    config: WorkflowModeConfig,
    sectionsAdded: number
  ): number {
    // Base adjustment from config
    let adjustment = config.confidenceWeightAdjustment - 1.0;

    // Penalize for many missing sections
    if (sectionsAdded > 0) {
      adjustment -= 0.05 * sectionsAdded;
    }

    return adjustment;
  }

  /**
   * Get configuration for a specific mode.
   */
  getConfig(mode: WorkflowMode): WorkflowModeConfig | undefined {
    return this.configs.get(mode);
  }

  /**
   * Get list of missing sections for a prompt in a given mode.
   * Useful for generating clarifying questions.
   */
  getMissingSections(prompt: string, mode: WorkflowMode): SectionRequirement[] {
    const config = this.configs.get(mode);
    if (!config) {
      return [];
    }

    return config.requiredSections.filter(
      section => !section.detectionPattern.test(prompt)
    );
  }

  /**
   * Get max expansion ratio for a mode.
   */
  getMaxExpansionRatio(mode: WorkflowMode): number {
    const config = this.configs.get(mode);
    return config?.maxExpansionRatio ?? 2.0;
  }

  /**
   * Check if mode prefers minimal optimization.
   */
  isMinimalMode(mode: WorkflowMode): boolean {
    const config = this.configs.get(mode);
    return config?.minimalOptimization ?? false;
  }
}
