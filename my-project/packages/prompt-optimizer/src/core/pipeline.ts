/**
 * Processing pipeline for the prompt optimizer.
 * Orchestrates the flow through classification, optimization, and verification.
 */

import type {
  ClassificationRequest,
  ClassificationResponse,
  OptimizationRequest,
  OptimizationResponse,
  VerificationResponse,
  AssembledContext,
  OptimizerApiClient,
} from '../types/index.js';
import { Classifier } from '../layers/classifier.js';
import { PassOneOptimizer } from '../layers/optimization/pass-one.js';
import { IntentVerifier } from '../layers/intent-verifier.js';
import {
  ROUTING_THRESHOLDS,
  DEFAULT_CONFIG,
} from '../constants/index.js';

/** Pipeline result */
export interface PipelineResult {
  /** Original input */
  original: string;
  /** Final output (optimized or original) */
  output: string;
  /** Whether optimization was applied */
  wasOptimized: boolean;
  /** Classification result */
  classification: ClassificationResponse;
  /** Optimization result (if applied) */
  optimization?: OptimizationResponse;
  /** Verification result (if optimized) */
  verification?: VerificationResponse;
  /** Total latency in ms */
  totalLatencyMs: number;
  /** Whether user confirmation is needed */
  needsConfirmation: boolean;
  /** Explanation for user */
  explanation: string;
  /** Tip for user */
  tip?: string;
}

/** Pipeline options */
export interface PipelineOptions {
  /** Override optimization level */
  level?: 1 | 2 | 3;
  /** Force optimization regardless of classification */
  forceOptimize?: boolean;
  /** Skip optimization regardless of classification */
  skipOptimize?: boolean;
  /** Context to inject */
  context?: Partial<AssembledContext>;
}

/**
 * Processing pipeline that orchestrates optimization flow.
 */
export class Pipeline {
  private classifier: Classifier;
  private passOneOptimizer: PassOneOptimizer;
  private intentVerifier: IntentVerifier;

  constructor(apiClient: OptimizerApiClient) {
    this.classifier = new Classifier(apiClient);
    this.passOneOptimizer = new PassOneOptimizer(apiClient);
    this.intentVerifier = new IntentVerifier(apiClient);
  }

  /**
   * Process a prompt through the optimization pipeline.
   */
  async process(input: string, options: PipelineOptions = {}): Promise<PipelineResult> {
    const startTime = Date.now();

    // Step 1: Classification
    const classificationRequest: ClassificationRequest = {
      input,
      context: options.context ? {
        projectLanguage: options.context.project?.language ?? undefined,
        projectFramework: options.context.project?.framework ?? undefined,
        expertiseLevel: options.context.user?.expertiseLevel,
      } : undefined,
    };

    const classification = await this.classifier.classify(classificationRequest);

    // Step 2: Route based on classification
    const route = this.determineRoute(classification, options);

    if (route === 'PASS_THROUGH') {
      return {
        original: input,
        output: input,
        wasOptimized: false,
        classification,
        totalLatencyMs: Date.now() - startTime,
        needsConfirmation: false,
        explanation: 'Prompt passed through without optimization (well-formed).',
      };
    }

    if (route === 'CLARIFY') {
      return {
        original: input,
        output: input,
        wasOptimized: false,
        classification,
        totalLatencyMs: Date.now() - startTime,
        needsConfirmation: true,
        explanation: 'Prompt needs clarification before optimization.',
      };
    }

    // Step 3: Optimize
    const context: AssembledContext = {
      ...options.context,
      totalTokens: 0,
      confidence: 0.8,
    };

    const optimizationRequest: OptimizationRequest = {
      original: input,
      classification,
      context,
      config: {
        maxPasses: options.level ?? DEFAULT_CONFIG.behavior.defaultLevel,
        targetConfidence: ROUTING_THRESHOLDS.AUTO_MEDIUM,
        preserveElements: [],
        domainOptimization: true,
      },
    };

    const optimization = await this.optimizeWithPassOne(optimizationRequest);

    // Step 4: Verify intent preservation
    const verification = await this.intentVerifier.verify({
      original: input,
      optimized: optimization.optimized,
      preservedElements: optimization.preservedElements,
    });

    // Step 5: Determine final output based on verification
    const shouldUseOptimized = this.shouldUseOptimized(verification, options);
    const needsConfirmation = this.needsConfirmation(
      optimization.confidence,
      verification,
      options
    );

    return {
      original: input,
      output: shouldUseOptimized ? optimization.optimized : input,
      wasOptimized: shouldUseOptimized,
      classification,
      optimization,
      verification,
      totalLatencyMs: Date.now() - startTime,
      needsConfirmation,
      explanation: this.generateExplanation(
        classification,
        optimization,
        verification,
        shouldUseOptimized
      ),
      tip: optimization.tip,
    };
  }

  /**
   * Determine routing based on classification.
   */
  private determineRoute(
    classification: ClassificationResponse,
    options: PipelineOptions
  ): 'PASS_THROUGH' | 'OPTIMIZE' | 'CLARIFY' {
    // Force options override classification
    if (options.forceOptimize) return 'OPTIMIZE';
    if (options.skipOptimize) return 'PASS_THROUGH';

    // Route based on category
    switch (classification.category) {
      case 'PASS_THROUGH':
        return 'PASS_THROUGH';
      case 'DEBUG':
      case 'OPTIMIZE':
        return 'OPTIMIZE';
      case 'CLARIFY':
        return 'CLARIFY';
    }
  }

  /**
   * Optimize using Pass One.
   */
  private async optimizeWithPassOne(
    request: OptimizationRequest
  ): Promise<OptimizationResponse> {
    const passOneResult = await this.passOneOptimizer.optimize(request);

    return {
      optimized: passOneResult.optimizedPrompt,
      changes: passOneResult.changesMade,
      preservedElements: passOneResult.preservedElements,
      passesUsed: 1,
      confidence: passOneResult.initialConfidence,
      intentSimilarity: 0.9, // Will be updated by verification
      explanation: 'Single-pass optimization complete.',
      tip: this.generateTip(request, passOneResult),
      latencyMs: passOneResult.latencyMs,
    };
  }

  /**
   * Generate optimization tip.
   */
  private generateTip(
    request: OptimizationRequest,
    result: { changesMade: unknown[] }
  ): string {
    const changes = result.changesMade.length;
    const domain = request.classification.domain;

    if (changes === 0) {
      return 'Your prompt was already well-structured.';
    }

    const tips: Record<string, string> = {
      CODE: 'Include specific file paths and error messages for faster debugging.',
      WRITING: 'Specify your target audience and desired tone upfront.',
      ANALYSIS: 'Define clear comparison criteria and output format.',
      CREATIVE: 'Balance constraints with creative freedom.',
      RESEARCH: 'Specify the depth of explanation you need.',
    };

    return tips[domain ?? ''] ?? 'Be specific about what you want to achieve.';
  }

  /**
   * Determine if optimized version should be used.
   */
  private shouldUseOptimized(
    verification: VerificationResponse,
    _options: PipelineOptions
  ): boolean {
    // Only use if verification passes
    return verification.status !== 'REJECTED';
  }

  /**
   * Determine if user confirmation is needed.
   */
  private needsConfirmation(
    confidence: number,
    verification: VerificationResponse,
    _options: PipelineOptions
  ): boolean {
    // Always confirm if verification has warnings
    if (verification.status === 'WARN') return true;

    // Low confidence requires confirmation
    if (confidence < ROUTING_THRESHOLDS.CONFIRM) return true;

    // Force confirmation can be set via options (not implemented in PipelineOptions yet)
    return false;
  }

  /**
   * Generate explanation for user.
   */
  private generateExplanation(
    classification: ClassificationResponse,
    optimization: OptimizationResponse,
    verification: VerificationResponse,
    wasOptimized: boolean
  ): string {
    if (!wasOptimized) {
      if (verification.status === 'REJECTED') {
        return `Optimization rejected: ${verification.recommendation}. Original prompt preserved.`;
      }
      return 'Prompt passed through without changes.';
    }

    const parts: string[] = [];

    // Classification info
    parts.push(`Classified as ${classification.category}`);
    if (classification.domain) {
      parts.push(`(${classification.domain} domain)`);
    }

    // Optimization summary
    const changeCount = optimization.changes.length;
    if (changeCount > 0) {
      parts.push(`with ${changeCount} improvement${changeCount > 1 ? 's' : ''}`);
    }

    // Confidence info
    parts.push(`(${(optimization.confidence * 100).toFixed(0)}% confidence)`);

    return parts.join(' ') + '.';
  }

  /**
   * Clear classifier cache.
   */
  clearCache(): void {
    this.classifier.clearCache();
  }
}

/** Create a new pipeline */
export function createPipeline(apiClient: OptimizerApiClient): Pipeline {
  return new Pipeline(apiClient);
}
