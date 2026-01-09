/**
 * Pass 1 (Initial Optimization) for the prompt optimizer.
 * Maps to spec section 4.2.
 */

import type {
  OptimizationRequest,
  PassOneOutput,
  Change,
  OptimizerApiClient,
} from '../../types/index.js';

/** Elements that should never be modified */
const PRESERVE_PATTERNS = [
  // Code blocks
  { pattern: /```[\s\S]*?```/g, type: 'code_block' as const },
  // Inline code
  { pattern: /`[^`]+`/g, type: 'inline_code' as const },
  // File paths
  { pattern: /(?:\/[\w.-]+)+(?:\.\w+)?/g, type: 'file_path' as const },
  // URLs
  { pattern: /https?:\/\/[^\s]+/g, type: 'url' as const },
  // Version numbers
  { pattern: /\bv?\d+\.\d+(?:\.\d+)?(?:-[\w.]+)?\b/g, type: 'version' as const },
  // Quoted strings
  { pattern: /"[^"]+"|'[^']+'/g, type: 'quoted' as const },
  // Technical terms (capitalized)
  { pattern: /\b[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+\b/g, type: 'technical_term' as const },
];

/**
 * Pass One optimizer for initial prompt improvement.
 */
export class PassOneOptimizer {
  constructor(private apiClient: OptimizerApiClient) {}

  /**
   * Execute pass one optimization.
   */
  async optimize(request: OptimizationRequest): Promise<PassOneOutput> {
    const startTime = Date.now();

    // Extract elements that must be preserved
    const preservedElements = this.extractPreservedElements(request.original);

    // Call API
    const response = await this.apiClient.optimize({
      ...request,
      config: {
        ...request.config,
        preserveElements: preservedElements,
      },
    });

    // Validate preservation
    const validationResult = this.validatePreservation(
      request.original,
      response.optimized,
      preservedElements
    );

    // If preservation failed, fall back to original with minimal changes
    if (!validationResult.valid) {
      const fallbackResult = this.createFallbackOptimization(
        request,
        preservedElements
      );
      return {
        ...fallbackResult,
        latencyMs: Date.now() - startTime,
      };
    }

    return {
      optimizedPrompt: response.optimized,
      changesMade: response.changes,
      preservedElements,
      initialConfidence: response.confidence,
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Extract elements that must be preserved.
   */
  private extractPreservedElements(input: string): string[] {
    const elements: string[] = [];

    for (const { pattern } of PRESERVE_PATTERNS) {
      const matches = input.match(pattern);
      if (matches) {
        elements.push(...matches);
      }
    }

    // Also preserve any negative constraints
    const negativePatterns = [
      /don't\s+[^.,]+/gi,
      /do not\s+[^.,]+/gi,
      /avoid\s+[^.,]+/gi,
      /never\s+[^.,]+/gi,
      /without\s+[^.,]+/gi,
      /except\s+[^.,]+/gi,
    ];

    for (const pattern of negativePatterns) {
      const matches = input.match(pattern);
      if (matches) {
        elements.push(...matches);
      }
    }

    return [...new Set(elements)]; // Remove duplicates
  }

  /**
   * Validate that preserved elements are still present.
   */
  private validatePreservation(
    _original: string,
    optimized: string,
    preservedElements: string[]
  ): { valid: boolean; missing: string[] } {
    const missing: string[] = [];

    for (const element of preservedElements) {
      // Check if element exists in optimized (allow for minor whitespace differences)
      const normalized = element.replace(/\s+/g, ' ').trim();
      const optimizedNormalized = optimized.replace(/\s+/g, ' ');

      if (!optimizedNormalized.includes(normalized)) {
        missing.push(element);
      }
    }

    return {
      valid: missing.length === 0,
      missing,
    };
  }

  /**
   * Create fallback optimization when preservation fails.
   */
  private createFallbackOptimization(
    request: OptimizationRequest,
    preservedElements: string[]
  ): Omit<PassOneOutput, 'latencyMs'> {
    // Apply minimal changes that don't risk breaking preserved elements
    const changes: Change[] = [];
    let optimized = request.original;

    // Only add context at the beginning or end
    const domain = request.classification.domain;
    if (domain) {
      const contextPrefix = this.getContextPrefix(request);
      if (contextPrefix) {
        optimized = `${contextPrefix}\n\n${optimized}`;
        changes.push({
          type: 'ADD_CONTEXT',
          originalSegment: '',
          newSegment: contextPrefix,
          reason: 'Added context information',
        });
      }
    }

    return {
      optimizedPrompt: optimized,
      changesMade: changes,
      preservedElements,
      initialConfidence: 0.6, // Lower confidence for fallback
    };
  }

  /**
   * Get context prefix to add.
   */
  private getContextPrefix(request: OptimizationRequest): string | null {
    const parts: string[] = [];

    // Add language/framework context
    if (request.context.project?.language) {
      parts.push(`Language: ${request.context.project.language}`);
    }
    if (request.context.project?.framework) {
      parts.push(`Framework: ${request.context.project.framework}`);
    }

    if (parts.length === 0) return null;
    return `[Context: ${parts.join(', ')}]`;
  }
}

/** Create a pass one optimizer */
export function createPassOneOptimizer(apiClient: OptimizerApiClient): PassOneOptimizer {
  return new PassOneOptimizer(apiClient);
}
