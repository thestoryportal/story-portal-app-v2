/**
 * Anthropic API client for the prompt optimizer.
 * Provides direct SDK integration with mock support for testing.
 */

import Anthropic from '@anthropic-ai/sdk';
import type {
  ClassificationRequest,
  ClassificationResponse,
  OptimizationRequest,
  OptimizationResponse,
  VerificationRequest,
  VerificationResponse,
  OptimizerApiClient,
} from '../types/index.js';
import type { ClientConfig, RequestOptions, ParsedResponse } from './types.js';
import {
  CLASSIFICATION_PROMPT,
  PASS_ONE_PROMPT,
  VERIFICATION_PROMPT,
  MODEL_CONFIG,
  RETRY_CONFIG,
} from '../constants/index.js';
import { OptimizerApiError, RateLimitError } from '../types/api.js';

/** Mock responses for testing */
const MOCK_RESPONSES = {
  classification: {
    category: 'OPTIMIZE' as const,
    domain: 'CODE' as const,
    complexity: 'MODERATE' as const,
    confidence: 0.85,
    reasoning: 'Mock classification response',
    cacheHit: false,
    latencyMs: 50,
  },
  verification: {
    status: 'VERIFIED' as const,
    similarityScore: 0.92,
    preservedRatio: 0.95,
    issues: [],
    recommendation: 'Optimization verified successfully',
  },
};

/**
 * Generate a mock optimized prompt based on the input.
 * Makes the optimization realistic enough to pass local verification.
 */
function generateMockOptimization(original: string): {
  optimized: string;
  changes: Array<{ type: 'CLARIFY'; originalSegment: string; newSegment: string; reason: string }>;
  preservedElements: string[];
  passesUsed: number;
  confidence: number;
  intentSimilarity: number;
  explanation: string;
  tip: string;
  latencyMs: number;
} {
  // Create an optimized version that preserves the original but adds minimal clarification
  // Keep most words intact for high similarity score
  let optimized = original;
  const changes: Array<{ type: 'CLARIFY'; originalSegment: string; newSegment: string; reason: string }> = [];

  // Simple transformation: replace "help me" with "Please help me" if present
  if (/^help\s+me/i.test(original)) {
    optimized = original.replace(/^help\s+me/i, 'Please help me');
    changes.push({ type: 'CLARIFY' as const, originalSegment: 'help me', newSegment: 'Please help me', reason: 'Added polite prefix' });
  } else if (/^help\b/i.test(original)) {
    optimized = original.replace(/^help\b/i, 'Please help');
    changes.push({ type: 'CLARIFY' as const, originalSegment: 'help', newSegment: 'Please help', reason: 'Added polite prefix' });
  } else {
    // Add context request suffix
    optimized = original + ' Please provide specific details.';
    changes.push({ type: 'CLARIFY' as const, originalSegment: '', newSegment: 'Please provide specific details.', reason: 'Added context request' });
  }

  return {
    optimized,
    changes,
    preservedElements: original.split(' ').filter(w => w.length > 3),
    passesUsed: 1,
    confidence: 0.88,
    intentSimilarity: 0.95,
    explanation: 'Added clarity to the request',
    tip: 'Be more specific in your requests',
    latencyMs: 100,
  };
}

/**
 * Anthropic API client with mock support.
 */
export class AnthropicClient implements OptimizerApiClient {
  private client: Anthropic | null = null;
  private useMock: boolean;
  private timeout: number;
  private retries: number;

  constructor(config: ClientConfig = {}) {
    this.useMock = config.useMock ?? process.env.NODE_ENV === 'test';
    this.timeout = config.timeout ?? 30000;
    this.retries = config.retries ?? RETRY_CONFIG.maxRetries;

    if (!this.useMock) {
      const apiKey = config.apiKey ?? process.env.ANTHROPIC_API_KEY;
      if (!apiKey) {
        throw new OptimizerApiError(
          'ANTHROPIC_API_KEY is required. Set it in environment or pass apiKey in config.',
          undefined,
          'MISSING_API_KEY'
        );
      }
      this.client = new Anthropic({
        apiKey,
        baseURL: config.baseUrl,
        timeout: this.timeout,
      });
    }
  }

  /**
   * Classify a prompt into one of four categories.
   */
  async classify(request: ClassificationRequest): Promise<ClassificationResponse> {
    if (this.useMock) {
      await this.mockDelay(50);
      return { ...MOCK_RESPONSES.classification };
    }

    const startTime = Date.now();
    const response = await this.makeRequest<{
      category: string;
      domain: string | null;
      complexity: string;
      confidence: number;
      reasoning: string;
    }>({
      model: MODEL_CONFIG.classification,
      systemPrompt: CLASSIFICATION_PROMPT,
      userMessage: this.buildClassificationMessage(request),
      maxTokens: 500,
      temperature: 0,
    });

    return {
      category: response.data.category as ClassificationResponse['category'],
      domain: response.data.domain as ClassificationResponse['domain'],
      complexity: response.data.complexity as ClassificationResponse['complexity'],
      confidence: response.data.confidence,
      reasoning: response.data.reasoning,
      cacheHit: false,
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Optimize a prompt based on classification.
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    if (this.useMock) {
      await this.mockDelay(100);
      return generateMockOptimization(request.original);
    }

    const startTime = Date.now();
    const model = this.selectOptimizationModel(request);
    const systemPrompt = this.buildOptimizationPrompt(request);

    const response = await this.makeRequest<{
      optimized_prompt: string;
      changes_made: Array<{ type: string; original: string; new: string; reason: string }>;
      preserved_elements: string[];
      initial_confidence: number;
    }>({
      model,
      systemPrompt,
      userMessage: request.original,
      maxTokens: 2000,
      temperature: 0.3,
    });

    return {
      optimized: response.data.optimized_prompt,
      changes: response.data.changes_made.map((c) => ({
        type: c.type as OptimizationResponse['changes'][0]['type'],
        originalSegment: c.original,
        newSegment: c.new,
        reason: c.reason,
      })),
      preservedElements: response.data.preserved_elements,
      passesUsed: 1,
      confidence: response.data.initial_confidence,
      intentSimilarity: 0.9, // Will be updated by verification
      explanation: 'Optimization complete',
      tip: 'Consider being more specific in future prompts',
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Verify intent preservation between original and optimized prompts.
   */
  async verify(request: VerificationRequest): Promise<VerificationResponse> {
    if (this.useMock) {
      await this.mockDelay(50);
      return { ...MOCK_RESPONSES.verification };
    }

    const response = await this.makeRequest<{
      status: string;
      similarity_score: number;
      preserved_ratio: number;
      issues: Array<{ type: string; severity: string; description: string }>;
      recommendation: string;
    }>({
      model: MODEL_CONFIG.intentVerification,
      systemPrompt: VERIFICATION_PROMPT.replace('{original}', request.original)
        .replace('{optimized}', request.optimized)
        .replace('{preserved_elements}', request.preservedElements.join(', ')),
      userMessage: 'Verify the intent preservation.',
      maxTokens: 500,
      temperature: 0,
    });

    return {
      status: response.data.status as VerificationResponse['status'],
      similarityScore: response.data.similarity_score,
      preservedRatio: response.data.preserved_ratio,
      issues: response.data.issues.map((i) => ({
        type: i.type as VerificationResponse['issues'][0]['type'],
        severity: i.severity as VerificationResponse['issues'][0]['severity'],
        description: i.description,
      })),
      recommendation: response.data.recommendation,
    };
  }

  /**
   * Generate embeddings for semantic similarity.
   * Note: Anthropic doesn't have a native embedding API, so we use a simple approach.
   */
  async embed(_text: string): Promise<number[]> {
    // For now, return empty array - we'll compute similarity differently
    // In production, consider using a dedicated embedding service
    return [];
  }

  /**
   * Make an API request with retry logic.
   */
  private async makeRequest<T>(options: RequestOptions): Promise<ParsedResponse<T>> {
    if (!this.client) {
      throw new OptimizerApiError('Client not initialized', undefined, 'CLIENT_NOT_INITIALIZED');
    }

    let lastError: Error | null = null;
    let delay: number = RETRY_CONFIG.initialDelayMs;

    for (let attempt = 0; attempt <= this.retries; attempt++) {
      try {
        const startTime = Date.now();
        const response = await this.client.messages.create({
          model: options.model,
          max_tokens: options.maxTokens ?? 1000,
          system: options.systemPrompt,
          messages: [{ role: 'user', content: options.userMessage }],
          temperature: options.temperature,
        });

        const textContent = response.content.find((c) => c.type === 'text');
        if (!textContent || textContent.type !== 'text') {
          throw new OptimizerApiError('No text content in response', undefined, 'NO_TEXT_CONTENT');
        }

        const parsed = this.parseJsonResponse<T>(textContent.text);

        return {
          data: parsed,
          raw: textContent.text,
          usage: {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
          },
          latencyMs: Date.now() - startTime,
        };
      } catch (error) {
        lastError = error as Error;

        if (this.isRateLimitError(error)) {
          const retryAfter = this.getRetryAfter(error);
          throw new RateLimitError('Rate limited by Anthropic API', retryAfter);
        }

        if (!this.isRetryableError(error) || attempt === this.retries) {
          break;
        }

        await this.sleep(delay);
        delay = Math.min(delay * RETRY_CONFIG.backoffMultiplier, RETRY_CONFIG.maxDelayMs);
      }
    }

    throw new OptimizerApiError(
      `API request failed after ${this.retries + 1} attempts: ${lastError?.message}`,
      undefined,
      'REQUEST_FAILED',
      false
    );
  }

  /**
   * Parse JSON from response text.
   */
  private parseJsonResponse<T>(text: string): T {
    // Extract JSON from markdown code blocks if present
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    const jsonText = jsonMatch ? jsonMatch[1] : text;

    try {
      return JSON.parse(jsonText.trim()) as T;
    } catch {
      throw new OptimizerApiError(
        `Failed to parse JSON response: ${text.substring(0, 100)}...`,
        undefined,
        'JSON_PARSE_ERROR'
      );
    }
  }

  /**
   * Build classification message from request.
   */
  private buildClassificationMessage(request: ClassificationRequest): string {
    let message = `Classify this prompt:\n\n${request.input}`;

    if (request.context) {
      message += '\n\n## Context';
      if (request.context.projectLanguage) {
        message += `\nLanguage: ${request.context.projectLanguage}`;
      }
      if (request.context.projectFramework) {
        message += `\nFramework: ${request.context.projectFramework}`;
      }
      if (request.context.expertiseLevel) {
        message += `\nExpertise: ${request.context.expertiseLevel}`;
      }
    }

    return message;
  }

  /**
   * Build optimization prompt with context.
   */
  private buildOptimizationPrompt(request: OptimizationRequest): string {
    let prompt = PASS_ONE_PROMPT;

    prompt = prompt.replace('{domain}', request.classification.domain ?? 'UNKNOWN');
    prompt = prompt.replace('{session_context}', JSON.stringify(request.context.session ?? {}));
    prompt = prompt.replace('{project_context}', JSON.stringify(request.context.project ?? {}));
    prompt = prompt.replace('{user_preferences}', JSON.stringify(request.context.user ?? {}));

    return prompt;
  }

  /**
   * Select optimization model based on complexity.
   */
  private selectOptimizationModel(request: OptimizationRequest): string {
    if (request.classification.complexity === 'COMPLEX') {
      return MODEL_CONFIG.complexOptimization;
    }
    return MODEL_CONFIG.simpleOptimization;
  }

  /**
   * Check if error is rate limit.
   */
  private isRateLimitError(error: unknown): boolean {
    if (error && typeof error === 'object' && 'status' in error) {
      return (error as { status: number }).status === 429;
    }
    return false;
  }

  /**
   * Get retry-after from rate limit error.
   */
  private getRetryAfter(error: unknown): number | undefined {
    if (error && typeof error === 'object' && 'headers' in error) {
      const headers = (error as { headers: Record<string, string> }).headers;
      const retryAfter = headers['retry-after'];
      if (retryAfter) {
        return parseInt(retryAfter, 10) * 1000;
      }
    }
    return undefined;
  }

  /**
   * Check if error is retryable.
   */
  private isRetryableError(error: unknown): boolean {
    if (error && typeof error === 'object' && 'status' in error) {
      const status = (error as { status: number }).status;
      return status >= 500 || status === 429;
    }
    return true; // Retry network errors
  }

  /**
   * Sleep for specified milliseconds.
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Mock delay for testing.
   */
  private mockDelay(ms: number): Promise<void> {
    return this.sleep(ms);
  }
}

/** Create a new Anthropic client */
export function createAnthropicClient(config?: ClientConfig): AnthropicClient {
  return new AnthropicClient(config);
}
