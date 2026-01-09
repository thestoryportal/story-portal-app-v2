/**
 * Pass 3 (Final Polish) for the prompt optimizer.
 * Applies refinements and produces final optimized prompt.
 * Maps to spec section 4.4.
 */

import type {
  PassOneOutput,
  PassTwoOutput,
  PassThreeOutput,
  OptimizerApiClient,
} from '../../types/index.js';

/**
 * Pass Three optimizer for final polish.
 */
export class PassThreeOptimizer {
  constructor(_apiClient: OptimizerApiClient) {}

  /**
   * Execute pass three final polish.
   */
  async polish(
    original: string,
    passOneOutput: PassOneOutput,
    passTwoOutput: PassTwoOutput
  ): Promise<PassThreeOutput> {
    const startTime = Date.now();

    // If pass two accepted without refinements, just clean up
    if (passTwoOutput.critiqueResult === 'ACCEPT' && passTwoOutput.refinementsNeeded.length === 0) {
      return {
        finalOptimizedPrompt: this.cleanUp(passOneOutput.optimizedPrompt),
        refinementsApplied: [],
        finalConfidence: passOneOutput.initialConfidence + passTwoOutput.confidenceAdjustment,
        explanationForUser: this.generateExplanation(passOneOutput, passTwoOutput),
        optimizationTip: this.generateTip(original, passOneOutput),
        latencyMs: Date.now() - startTime,
      };
    }

    // Apply refinements
    const refinedPrompt = this.applyRefinements(
      original,
      passOneOutput,
      passTwoOutput
    );

    // Clean up the result
    const finalPrompt = this.cleanUp(refinedPrompt.prompt);

    // Calculate final confidence
    const finalConfidence = this.calculateFinalConfidence(
      passOneOutput.initialConfidence,
      passTwoOutput
    );

    return {
      finalOptimizedPrompt: finalPrompt,
      refinementsApplied: refinedPrompt.applied,
      finalConfidence,
      explanationForUser: this.generateExplanation(passOneOutput, passTwoOutput),
      optimizationTip: this.generateTip(original, passOneOutput),
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Apply refinements from pass two.
   */
  private applyRefinements(
    original: string,
    passOneOutput: PassOneOutput,
    passTwoOutput: PassTwoOutput
  ): { prompt: string; applied: Array<{ refinement: string; howApplied: string }> } {
    let prompt = passOneOutput.optimizedPrompt;
    const applied: Array<{ refinement: string; howApplied: string }> = [];

    for (const refinement of passTwoOutput.refinementsNeeded) {
      const result = this.applyRefinement(original, prompt, refinement, passTwoOutput);
      if (result.changed) {
        prompt = result.prompt;
        applied.push({
          refinement,
          howApplied: result.howApplied,
        });
      }
    }

    return { prompt, applied };
  }

  /**
   * Apply a single refinement.
   */
  private applyRefinement(
    original: string,
    prompt: string,
    refinement: string,
    passTwoOutput: PassTwoOutput
  ): { prompt: string; changed: boolean; howApplied: string } {
    const refinementLower = refinement.toLowerCase();

    // Handle different refinement types
    if (refinementLower.includes('negative constraint')) {
      return this.restoreNegativeConstraint(original, prompt);
    }

    if (refinementLower.includes('element') && refinementLower.includes('preserved')) {
      return this.restoreElements(original, prompt, passTwoOutput);
    }

    if (refinementLower.includes('constraint') && refinementLower.includes('remove')) {
      return this.removeExcessConstraints(prompt);
    }

    if (refinementLower.includes('technology') || refinementLower.includes('hallucinated')) {
      return this.removeHallucinatedTech(original, prompt);
    }

    if (refinementLower.includes('length') || refinementLower.includes('reduce')) {
      return this.reduceLength(prompt);
    }

    if (refinementLower.includes('intent') || refinementLower.includes('realign')) {
      return this.realignIntent(original, prompt);
    }

    // Default: no change
    return { prompt, changed: false, howApplied: 'Unable to apply automatically' };
  }

  /**
   * Restore negative constraints from original.
   */
  private restoreNegativeConstraint(
    original: string,
    prompt: string
  ): { prompt: string; changed: boolean; howApplied: string } {
    const negativePatterns = [
      { pattern: /don't\s+[^.,!?]+/gi, keyword: "don't" },
      { pattern: /do not\s+[^.,!?]+/gi, keyword: 'do not' },
      { pattern: /avoid\s+[^.,!?]+/gi, keyword: 'avoid' },
      { pattern: /never\s+[^.,!?]+/gi, keyword: 'never' },
      { pattern: /without\s+[^.,!?]+/gi, keyword: 'without' },
      { pattern: /except\s+[^.,!?]+/gi, keyword: 'except' },
    ];

    for (const { pattern, keyword } of negativePatterns) {
      const originalMatches = original.match(pattern);
      if (originalMatches) {
        for (const match of originalMatches) {
          if (!prompt.toLowerCase().includes(match.toLowerCase())) {
            // Append the constraint
            return {
              prompt: `${prompt}\n\nNote: ${match}`,
              changed: true,
              howApplied: `Restored "${keyword}" constraint from original`,
            };
          }
        }
      }
    }

    return { prompt, changed: false, howApplied: '' };
  }

  /**
   * Restore required elements.
   */
  private restoreElements(
    original: string,
    prompt: string,
    passTwoOutput: PassTwoOutput
  ): { prompt: string; changed: boolean; howApplied: string } {
    const elementIssues = passTwoOutput.issuesFound.filter(
      (i) => i.description.includes('element not preserved')
    );

    if (elementIssues.length === 0) {
      return { prompt, changed: false, howApplied: '' };
    }

    // Extract what was lost and restore it
    // This is a simplified version - a real implementation would be smarter
    return {
      prompt: `${prompt}\n\n[Original context preserved: ${original.substring(0, 100)}...]`,
      changed: true,
      howApplied: 'Appended original context to ensure preservation',
    };
  }

  /**
   * Remove excess constraints.
   */
  private removeExcessConstraints(
    prompt: string
  ): { prompt: string; changed: boolean; howApplied: string } {
    const excessIndicators = [
      'specifically', 'exactly', 'precisely', 'critically important',
      'absolutely must', 'essential that',
    ];

    let modified = prompt;
    let removedCount = 0;

    for (const indicator of excessIndicators) {
      const regex = new RegExp(`\\b${indicator}\\b`, 'gi');
      const matches = modified.match(regex);
      if (matches && matches.length > 1) {
        // Keep first occurrence, remove extras
        let first = true;
        modified = modified.replace(regex, (match) => {
          if (first) {
            first = false;
            return match;
          }
          removedCount++;
          return '';
        });
      }
    }

    if (removedCount > 0) {
      return {
        prompt: modified.replace(/\s+/g, ' ').trim(),
        changed: true,
        howApplied: `Removed ${removedCount} redundant constraint indicators`,
      };
    }

    return { prompt, changed: false, howApplied: '' };
  }

  /**
   * Remove hallucinated technology references.
   */
  private removeHallucinatedTech(
    original: string,
    prompt: string
  ): { prompt: string; changed: boolean; howApplied: string } {
    const technologies = [
      'React', 'Vue', 'Angular', 'Svelte', 'Next.js', 'Nuxt',
      'TypeScript', 'Node.js', 'Deno', 'Bun',
    ];

    let modified = prompt;
    const removed: string[] = [];

    for (const tech of technologies) {
      if (
        prompt.toLowerCase().includes(tech.toLowerCase()) &&
        !original.toLowerCase().includes(tech.toLowerCase())
      ) {
        // Try to remove tech references that were added
        const regex = new RegExp(`\\b${tech}\\b`, 'gi');
        modified = modified.replace(regex, '');
        removed.push(tech);
      }
    }

    if (removed.length > 0) {
      return {
        prompt: modified.replace(/\s+/g, ' ').trim(),
        changed: true,
        howApplied: `Removed assumed technologies: ${removed.join(', ')}`,
      };
    }

    return { prompt, changed: false, howApplied: '' };
  }

  /**
   * Reduce prompt length.
   */
  private reduceLength(
    prompt: string
  ): { prompt: string; changed: boolean; howApplied: string } {
    // Remove filler words and phrases
    const fillers = [
      'basically', 'essentially', 'actually', 'really', 'very',
      'just', 'simply', 'in order to', 'that is to say',
      'as you can see', 'as mentioned', 'as stated',
    ];

    let modified = prompt;
    let removedCount = 0;

    for (const filler of fillers) {
      const regex = new RegExp(`\\b${filler}\\b`, 'gi');
      const matches = modified.match(regex);
      if (matches) {
        modified = modified.replace(regex, '');
        removedCount += matches.length;
      }
    }

    // Clean up multiple spaces
    modified = modified.replace(/\s+/g, ' ').trim();

    if (removedCount > 0) {
      return {
        prompt: modified,
        changed: true,
        howApplied: `Removed ${removedCount} filler words`,
      };
    }

    return { prompt, changed: false, howApplied: '' };
  }

  /**
   * Realign with original intent.
   */
  private realignIntent(
    original: string,
    prompt: string
  ): { prompt: string; changed: boolean; howApplied: string } {
    // Extract action from original
    const actionVerbs = [
      'create', 'write', 'implement', 'add', 'update', 'modify',
      'fix', 'debug', 'explain', 'analyze', 'compare', 'review',
    ];

    const originalLower = original.toLowerCase();
    const originalAction = actionVerbs.find((v) => originalLower.includes(v));

    if (originalAction && !prompt.toLowerCase().includes(originalAction)) {
      return {
        prompt: prompt.replace(/^(Please\s+)?/i, `Please ${originalAction} `),
        changed: true,
        howApplied: `Restored original action verb: ${originalAction}`,
      };
    }

    return { prompt, changed: false, howApplied: '' };
  }

  /**
   * Clean up the final prompt.
   */
  private cleanUp(prompt: string): string {
    return prompt
      // Normalize whitespace
      .replace(/\s+/g, ' ')
      // Remove trailing/leading whitespace
      .trim()
      // Fix double punctuation
      .replace(/([.!?])\1+/g, '$1')
      // Fix spacing around punctuation
      .replace(/\s+([.,!?])/g, '$1')
      // Ensure ends with period if no punctuation
      .replace(/([^.!?])$/, '$1.');
  }

  /**
   * Calculate final confidence.
   */
  private calculateFinalConfidence(
    initialConfidence: number,
    passTwoOutput: PassTwoOutput
  ): number {
    let confidence = initialConfidence + passTwoOutput.confidenceAdjustment;

    // Apply intent preservation factor
    if (passTwoOutput.intentPreservationScore < 0.9) {
      confidence *= passTwoOutput.intentPreservationScore;
    }

    // Cap between 0 and 1
    return Math.max(0, Math.min(1, confidence));
  }

  /**
   * Generate explanation for user.
   */
  private generateExplanation(
    passOneOutput: PassOneOutput,
    passTwoOutput: PassTwoOutput
  ): string {
    const parts: string[] = [];

    // Describe what was optimized
    const changeCount = passOneOutput.changesMade.length;
    if (changeCount > 0) {
      parts.push(`Made ${changeCount} improvement${changeCount > 1 ? 's' : ''} to your prompt.`);
    }

    // Describe refinements if any
    if (passTwoOutput.refinementsNeeded.length > 0) {
      parts.push('Applied additional refinements to preserve your original intent.');
    }

    // Intent preservation note
    if (passTwoOutput.intentPreservationScore >= 0.95) {
      parts.push('Your original intent is fully preserved.');
    } else if (passTwoOutput.intentPreservationScore >= 0.85) {
      parts.push('Core intent preserved with minor clarifications.');
    }

    return parts.join(' ') || 'Prompt optimized successfully.';
  }

  /**
   * Generate tip for user.
   */
  private generateTip(_original: string, passOneOutput: PassOneOutput): string {
    // Analyze what was missing
    const changes = passOneOutput.changesMade;

    if (changes.some((c) => c.type === 'ADD_CONTEXT')) {
      return 'Tip: Include relevant context (language, framework, file paths) in your prompts for better results.';
    }

    if (changes.some((c) => c.type === 'CLARIFY')) {
      return 'Tip: Be specific about what you want. Vague requests like "make it better" can lead to misunderstandings.';
    }

    if (changes.some((c) => c.type === 'RESTRUCTURE')) {
      return 'Tip: Structure complex requests with clear sections or numbered steps.';
    }

    if (changes.some((c) => c.type === 'REMOVE_REDUNDANCY')) {
      return 'Tip: Keep prompts concise. Remove filler words and redundant information.';
    }

    return 'Tip: Clear, specific prompts with context get the best results.';
  }
}

/** Create a pass three optimizer */
export function createPassThreeOptimizer(apiClient: OptimizerApiClient): PassThreeOptimizer {
  return new PassThreeOptimizer(apiClient);
}
