/**
 * Multi-pass optimization orchestrator.
 * Coordinates Pass 1, 2, and 3 based on complexity.
 * Maps to spec section 4.
 */

import type {
  OptimizationRequest,
  OptimizationResponse,
  PassOneOutput,
  PassTwoOutput,
  PassThreeOutput,
  OptimizerApiClient,
} from '../../types/index.js';
import { PassOneOptimizer } from './pass-one.js';
import { PassTwoOptimizer } from './pass-two.js';
import { PassThreeOptimizer } from './pass-three.js';

/**
 * Multi-pass optimization orchestrator.
 */
export class MultiPassOptimizer {
  private passOne: PassOneOptimizer;
  private passTwo: PassTwoOptimizer;
  private passThree: PassThreeOptimizer;

  constructor(apiClient: OptimizerApiClient) {
    this.passOne = new PassOneOptimizer(apiClient);
    this.passTwo = new PassTwoOptimizer(apiClient);
    this.passThree = new PassThreeOptimizer(apiClient);
  }

  /**
   * Execute multi-pass optimization.
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    const startTime = Date.now();

    // Determine number of passes based on complexity and config
    const passCount = this.determinePassCount(request);

    // Execute passes
    let result: OptimizationResponse;

    if (passCount === 1) {
      result = await this.executeSinglePass(request);
    } else if (passCount === 2) {
      result = await this.executeTwoPass(request);
    } else {
      result = await this.executeThreePass(request);
    }

    result.latencyMs = Date.now() - startTime;
    result.passesUsed = passCount;

    return result;
  }

  /**
   * Determine how many passes to use.
   */
  private determinePassCount(request: OptimizationRequest): 1 | 2 | 3 {
    // Use config max as upper bound
    const maxPasses = request.config.maxPasses;

    // Simple prompts only need one pass
    if (request.classification.complexity === 'SIMPLE') {
      return 1;
    }

    // Moderate prompts get two passes
    if (request.classification.complexity === 'MODERATE') {
      return Math.min(2, maxPasses) as 1 | 2 | 3;
    }

    // Complex prompts get all passes
    return maxPasses;
  }

  /**
   * Execute single pass optimization.
   */
  private async executeSinglePass(
    request: OptimizationRequest
  ): Promise<OptimizationResponse> {
    const passOneResult = await this.passOne.optimize(request);

    return this.buildResponse(
      request,
      passOneResult,
      null,
      null
    );
  }

  /**
   * Execute two-pass optimization.
   */
  private async executeTwoPass(
    request: OptimizationRequest
  ): Promise<OptimizationResponse> {
    // Pass 1: Initial optimization
    const passOneResult = await this.passOne.optimize(request);

    // Pass 2: Self-critique
    const passTwoResult = await this.passTwo.critique(
      request.original,
      passOneResult
    );

    // If rejected, fall back to original with explanation
    if (passTwoResult.critiqueResult === 'REJECT') {
      return this.buildRejectedResponse(request, passTwoResult);
    }

    return this.buildResponse(
      request,
      passOneResult,
      passTwoResult,
      null
    );
  }

  /**
   * Execute three-pass optimization.
   */
  private async executeThreePass(
    request: OptimizationRequest
  ): Promise<OptimizationResponse> {
    // Pass 1: Initial optimization
    const passOneResult = await this.passOne.optimize(request);

    // Pass 2: Self-critique
    const passTwoResult = await this.passTwo.critique(
      request.original,
      passOneResult
    );

    // If rejected, fall back to original
    if (passTwoResult.critiqueResult === 'REJECT') {
      return this.buildRejectedResponse(request, passTwoResult);
    }

    // Pass 3: Final polish
    const passThreeResult = await this.passThree.polish(
      request.original,
      passOneResult,
      passTwoResult
    );

    return this.buildResponse(
      request,
      passOneResult,
      passTwoResult,
      passThreeResult
    );
  }

  /**
   * Build optimization response.
   */
  private buildResponse(
    request: OptimizationRequest,
    passOne: PassOneOutput,
    passTwo: PassTwoOutput | null,
    passThree: PassThreeOutput | null
  ): OptimizationResponse {
    // Determine final prompt
    const optimized = passThree?.finalOptimizedPrompt ?? passOne.optimizedPrompt;

    // Determine confidence
    let confidence = passOne.initialConfidence;
    if (passTwo) {
      confidence += passTwo.confidenceAdjustment;
    }
    if (passThree) {
      confidence = passThree.finalConfidence;
    }

    // Determine intent similarity
    const intentSimilarity = passTwo?.intentPreservationScore ?? 0.9;

    // Build explanation
    const explanation = passThree?.explanationForUser ??
      this.buildExplanation(passOne, passTwo);

    // Build tip
    const tip = passThree?.optimizationTip ??
      this.buildTip(request, passOne);

    return {
      optimized,
      changes: passOne.changesMade,
      preservedElements: passOne.preservedElements,
      passesUsed: passThree ? 3 : passTwo ? 2 : 1,
      confidence: Math.max(0, Math.min(1, confidence)),
      intentSimilarity,
      explanation,
      tip,
      latencyMs: 0, // Will be set by caller
    };
  }

  /**
   * Build response when optimization is rejected.
   */
  private buildRejectedResponse(
    request: OptimizationRequest,
    passTwoResult: PassTwoOutput
  ): OptimizationResponse {
    const issues = passTwoResult.issuesFound
      .filter((i) => i.severity === 'HIGH')
      .map((i) => i.description)
      .join('; ');

    return {
      optimized: request.original,
      changes: [],
      preservedElements: [],
      passesUsed: 2,
      confidence: 0.5,
      intentSimilarity: passTwoResult.intentPreservationScore,
      explanation: `Optimization rejected: ${issues}. Original prompt preserved.`,
      tip: 'Try being more specific in your request to enable optimization.',
      latencyMs: 0,
    };
  }

  /**
   * Build explanation from passes.
   */
  private buildExplanation(
    passOne: PassOneOutput,
    passTwo: PassTwoOutput | null
  ): string {
    const parts: string[] = [];

    // Describe changes
    if (passOne.changesMade.length > 0) {
      parts.push(`Made ${passOne.changesMade.length} improvement(s)`);
    }

    // Describe verification
    if (passTwo) {
      if (passTwo.critiqueResult === 'ACCEPT') {
        parts.push('verified intent preservation');
      } else if (passTwo.critiqueResult === 'REFINE') {
        parts.push('applied refinements');
      }
    }

    return parts.length > 0
      ? `Optimization: ${parts.join(', ')}.`
      : 'Prompt optimized successfully.';
  }

  /**
   * Build tip from request and results.
   */
  private buildTip(
    request: OptimizationRequest,
    passOne: PassOneOutput
  ): string {
    // Domain-specific tips
    const domain = request.classification.domain;

    const domainTips: Record<string, string> = {
      CODE: 'Include file paths, language, and expected vs actual behavior.',
      WRITING: 'Specify tone, audience, and format requirements.',
      ANALYSIS: 'Define comparison criteria and desired output format.',
      CREATIVE: 'Balance creative freedom with specific constraints.',
      RESEARCH: 'Indicate desired depth and scope.',
    };

    if (domain && domainTips[domain]) {
      return domainTips[domain];
    }

    // Generic tip based on changes
    if (passOne.changesMade.some((c) => c.type === 'ADD_CONTEXT')) {
      return 'Provide more context upfront for better results.';
    }

    return 'Clear, specific prompts get the best results.';
  }
}

/** Create a multi-pass optimizer */
export function createMultiPassOptimizer(apiClient: OptimizerApiClient): MultiPassOptimizer {
  return new MultiPassOptimizer(apiClient);
}
