/**
 * Main Optimizer class for the prompt optimizer package.
 * This is the primary entry point for using the optimizer.
 */

import type {
  OptimizerConfig,
  AssembledContext,
} from '../types/index.js';
import { Pipeline, type PipelineResult, type PipelineOptions } from './pipeline.js';
import { AnthropicClient } from '../api/anthropic-client.js';
import { DEFAULT_CONFIG } from '../constants/index.js';

/** Optimizer result exposed to users */
export interface OptimizeResult {
  /** The final prompt to use */
  prompt: string;
  /** Whether the prompt was optimized */
  wasOptimized: boolean;
  /** Confidence in the optimization (0-1) */
  confidence: number;
  /** Classification category */
  category: string;
  /** Detected domain */
  domain: string | null;
  /** Whether user confirmation is recommended */
  needsConfirmation: boolean;
  /** Human-readable explanation */
  explanation: string;
  /** Tip for writing better prompts */
  tip?: string;
  /** Changes made (if optimized) */
  changes?: Array<{
    type: string;
    reason: string;
  }>;
  /** Total processing time in ms */
  latencyMs: number;
}

/** Options for optimize call */
export interface OptimizeOptions {
  /** Override optimization level (1-3) */
  level?: 1 | 2 | 3;
  /** Force optimization */
  force?: boolean;
  /** Skip optimization */
  skip?: boolean;
  /** Additional context */
  context?: {
    /** Project language */
    language?: string;
    /** Project framework */
    framework?: string;
    /** User expertise level */
    expertise?: 'beginner' | 'intermediate' | 'senior' | 'expert';
    /** Recent files */
    recentFiles?: string[];
  };
}

/**
 * Main Optimizer class.
 */
export class PromptOptimizer {
  private pipeline: Pipeline;
  private config: OptimizerConfig;

  constructor(config: Partial<OptimizerConfig> & { useMock?: boolean } = {}) {
    const { useMock, ...restConfig } = config;
    this.config = { ...DEFAULT_CONFIG, ...restConfig };

    const apiClient = new AnthropicClient({
      apiKey: this.config.api.anthropicApiKey,
      timeout: this.config.api.timeout,
      retries: this.config.api.retries,
      useMock: useMock ?? process.env.NODE_ENV === 'test',
    });

    this.pipeline = new Pipeline(apiClient);
  }

  /**
   * Optimize a prompt.
   */
  async optimize(input: string, options: OptimizeOptions = {}): Promise<OptimizeResult> {
    // Build context from options
    const context = this.buildContext(options);

    // Build pipeline options
    const pipelineOptions: PipelineOptions = {
      level: options.level ?? this.config.behavior.defaultLevel,
      forceOptimize: options.force,
      skipOptimize: options.skip,
      context,
    };

    // Run pipeline
    const result = await this.pipeline.process(input, pipelineOptions);

    // Convert to user-facing result
    return this.toOptimizeResult(result);
  }

  /**
   * Quick check if a prompt should be optimized.
   * Useful for pre-flight checks without full optimization.
   */
  async shouldOptimize(input: string): Promise<{
    shouldOptimize: boolean;
    category: string;
    confidence: number;
    reason: string;
  }> {
    const result = await this.pipeline.process(input, { skipOptimize: true });

    const shouldOptimize = result.classification.category === 'OPTIMIZE' ||
      result.classification.category === 'DEBUG';

    return {
      shouldOptimize,
      category: result.classification.category,
      confidence: result.classification.confidence,
      reason: result.classification.reasoning,
    };
  }

  /**
   * Get current configuration.
   */
  getConfig(): OptimizerConfig {
    return { ...this.config };
  }

  /**
   * Update configuration.
   */
  updateConfig(updates: Partial<OptimizerConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  /**
   * Clear caches.
   */
  clearCache(): void {
    this.pipeline.clearCache();
  }

  /**
   * Build context from options.
   */
  private buildContext(options: OptimizeOptions): Partial<AssembledContext> {
    if (!options.context) return {};

    return {
      project: options.context.language || options.context.framework ? {
        language: options.context.language,
        framework: options.context.framework,
        recentFiles: options.context.recentFiles,
        maxTokens: 1000,
      } : undefined,
      user: options.context.expertise ? {
        expertiseLevel: options.context.expertise,
        preferredVerbosity: 'balanced',
        commonDomains: {},
        optimizationAcceptanceRate: 0.85,
        averageConfidenceAtAcceptance: 0.8,
        customRules: [],
        maxTokens: 500,
      } : undefined,
    };
  }

  /**
   * Convert pipeline result to user-facing result.
   */
  private toOptimizeResult(result: PipelineResult): OptimizeResult {
    return {
      prompt: result.output,
      wasOptimized: result.wasOptimized,
      confidence: result.optimization?.confidence ?? result.classification.confidence,
      category: result.classification.category,
      domain: result.classification.domain,
      needsConfirmation: result.needsConfirmation,
      explanation: result.explanation,
      tip: result.tip,
      changes: result.optimization?.changes.map((c) => ({
        type: c.type,
        reason: c.reason,
      })),
      latencyMs: result.totalLatencyMs,
    };
  }
}

/** Create a new optimizer instance */
export function createOptimizer(config?: Partial<OptimizerConfig>): PromptOptimizer {
  return new PromptOptimizer(config);
}
