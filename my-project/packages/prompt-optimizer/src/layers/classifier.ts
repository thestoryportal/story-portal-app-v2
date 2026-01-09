/**
 * Classification layer for the prompt optimizer.
 * Implements 4-way routing: PASS_THROUGH, DEBUG, OPTIMIZE, CLARIFY.
 * Maps to spec section 3: Classification System.
 */

import type {
  Domain,
  Complexity,
  ClassificationRequest,
  ClassificationResponse,
  OptimizerApiClient,
} from '../types/index.js';
import {
  TOKEN_THRESHOLDS,
  DOMAIN_KEYWORDS,
  DANGEROUS_PATTERNS,
} from '../constants/index.js';

/** Cache entry for classification results */
interface CacheEntry {
  response: ClassificationResponse;
  timestamp: number;
}

/**
 * Classifier for prompt categorization.
 */
export class Classifier {
  private cache: Map<string, CacheEntry> = new Map();
  private cacheTtlMs: number;

  constructor(
    private apiClient: OptimizerApiClient,
    options: { cacheTtlMs?: number } = {}
  ) {
    this.cacheTtlMs = options.cacheTtlMs ?? 60 * 60 * 1000; // 1 hour default
  }

  /**
   * Classify a prompt into one of four categories.
   */
  async classify(request: ClassificationRequest): Promise<ClassificationResponse> {
    const startTime = Date.now();

    // Check cache first
    const cacheKey = this.getCacheKey(request);
    const cached = this.getFromCache(cacheKey);
    if (cached) {
      return { ...cached, cacheHit: true, latencyMs: Date.now() - startTime };
    }

    // Pre-classify with heuristics for obvious cases
    const heuristicResult = this.heuristicClassify(request.input);
    if (heuristicResult && heuristicResult.confidence >= 0.95) {
      const response: ClassificationResponse = {
        ...heuristicResult,
        cacheHit: false,
        latencyMs: Date.now() - startTime,
      };
      this.setCache(cacheKey, response);
      return response;
    }

    // Use API for more nuanced classification
    const apiResponse = await this.apiClient.classify(request);

    // Blend heuristic and API results
    const finalResponse = this.blendResults(heuristicResult, apiResponse);
    finalResponse.latencyMs = Date.now() - startTime;
    finalResponse.cacheHit = false;

    this.setCache(cacheKey, finalResponse);
    return finalResponse;
  }

  /**
   * Perform fast heuristic classification.
   */
  private heuristicClassify(
    input: string
  ): Omit<ClassificationResponse, 'cacheHit' | 'latencyMs'> | null {
    const trimmed = input.trim();
    const tokenCount = this.estimateTokens(trimmed);

    // Single word or extremely short - CLARIFY
    if (tokenCount < 3) {
      return {
        category: 'CLARIFY',
        domain: null,
        complexity: 'SIMPLE',
        confidence: 0.95,
        reasoning: 'Input too short to determine intent',
      };
    }

    // Check for dangerous operations - require confirmation
    if (this.containsDangerousOperation(trimmed)) {
      return {
        category: 'CLARIFY',
        domain: this.detectDomain(trimmed),
        complexity: 'MODERATE',
        confidence: 0.90,
        reasoning: 'Contains potentially dangerous operation requiring confirmation',
      };
    }

    // Check for DEBUG indicators
    if (this.isDebugRequest(trimmed)) {
      return {
        category: 'DEBUG',
        domain: 'CODE',
        complexity: this.assessComplexity(tokenCount),
        confidence: 0.88,
        reasoning: 'Contains error messages or explicit debugging request',
      };
    }

    // Check for well-formed questions (PASS_THROUGH candidates)
    if (this.isWellFormed(trimmed)) {
      const domain = this.detectDomain(trimmed);
      return {
        category: 'PASS_THROUGH',
        domain,
        complexity: this.assessComplexity(tokenCount),
        confidence: 0.85,
        reasoning: 'Well-formed question with clear intent',
      };
    }

    // Check for vague language (OPTIMIZE candidates)
    if (this.isVague(trimmed)) {
      return {
        category: 'OPTIMIZE',
        domain: this.detectDomain(trimmed),
        complexity: this.assessComplexity(tokenCount),
        confidence: 0.82,
        reasoning: 'Contains vague language that could be clarified',
      };
    }

    // Default - let API decide
    return null;
  }

  /**
   * Check if input contains DEBUG indicators.
   */
  private isDebugRequest(input: string): boolean {
    const lower = input.toLowerCase();

    // Check for error-related keywords
    const errorKeywords = [
      'error', 'exception', 'stack trace', 'traceback', 'failed',
      'crash', 'bug', 'broken', 'not working', "doesn't work", 'failing',
    ];
    const hasError = errorKeywords.some((kw) => lower.includes(kw));

    // Check for code blocks with errors
    const hasCodeBlock = input.includes('```') || input.includes('`');

    // Check for explicit debug request
    const debugKeywords = ['debug', 'troubleshoot', 'fix', 'solve', 'why is'];
    const hasDebugRequest = debugKeywords.some((kw) => lower.includes(kw));

    return hasError || (hasCodeBlock && hasDebugRequest);
  }

  /**
   * Check if input is well-formed.
   */
  private isWellFormed(input: string): boolean {
    const lower = input.toLowerCase();

    // Check for question structure
    const isQuestion = input.includes('?') ||
      lower.startsWith('how') ||
      lower.startsWith('what') ||
      lower.startsWith('why') ||
      lower.startsWith('when') ||
      lower.startsWith('where') ||
      lower.startsWith('can you') ||
      lower.startsWith('could you') ||
      lower.startsWith('please');

    // Check for reasonable length
    const tokenCount = this.estimateTokens(input);
    const reasonableLength = tokenCount >= 10 && tokenCount <= 500;

    // Check for clear action verbs
    const actionVerbs = [
      'create', 'write', 'implement', 'add', 'update', 'modify',
      'explain', 'describe', 'analyze', 'compare', 'review', 'refactor',
    ];
    const hasAction = actionVerbs.some((verb) => lower.includes(verb));

    // Check for specific references (files, functions, etc.)
    const hasSpecificRef = /\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-z]{2,4}\b/.test(input) || // file.ext
      /\b[A-Z][a-zA-Z0-9]*\b/.test(input) || // ClassName
      /`[^`]+`/.test(input); // inline code

    return (isQuestion || hasAction) && reasonableLength && hasSpecificRef;
  }

  /**
   * Check if input contains vague language.
   */
  private isVague(input: string): boolean {
    const lower = input.toLowerCase();

    // Vague phrases
    const vaguePhrases = [
      'help with', 'make it better', 'improve', 'fix it', 'the thing',
      'that stuff', 'some code', 'a function', 'the file', 'it doesn\'t',
      'something wrong', 'kind of', 'sort of', 'maybe', 'i think',
      'idk', 'not sure', 'whatever', 'etc', 'and stuff',
    ];
    const hasVague = vaguePhrases.some((phrase) => lower.includes(phrase));

    // Ambiguous pronouns without clear referent
    const ambiguousPronouns = ['it', 'that', 'this', 'those', 'these'];
    const hasAmbiguousPronoun = ambiguousPronouns.some((pron) => {
      const regex = new RegExp(`\\b${pron}\\b`, 'gi');
      return regex.test(lower) && !lower.includes(`${pron} is`) && !lower.includes(`${pron} should`);
    });

    // Too short without context
    const tokenCount = this.estimateTokens(input);
    const tooShort = tokenCount < 20;

    return hasVague || (hasAmbiguousPronoun && tooShort);
  }

  /**
   * Detect the domain of the input.
   */
  private detectDomain(input: string): Domain | null {
    const lower = input.toLowerCase();

    // Check for code indicators
    const codeScore = this.calculateDomainScore(input, DOMAIN_KEYWORDS.code);
    const writingScore = this.calculateDomainScore(input, DOMAIN_KEYWORDS.writing);
    const analysisScore = this.calculateDomainScore(input, DOMAIN_KEYWORDS.analysis);
    const creativeScore = this.calculateDomainScore(input, DOMAIN_KEYWORDS.creative);
    const researchScore = this.calculateDomainScore(input, DOMAIN_KEYWORDS.research);

    // Code has special indicators
    const hasCodeBlock = input.includes('```') || /`[^`]+`/.test(input);
    const hasFileRef = /\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-z]{2,4}\b/.test(input);
    const hasErrorIndicator = DOMAIN_KEYWORDS.code.errorIndicators.some((e) => lower.includes(e));

    if (hasCodeBlock || hasFileRef || hasErrorIndicator) {
      return 'CODE';
    }

    const scores = [
      { domain: 'CODE' as const, score: codeScore },
      { domain: 'WRITING' as const, score: writingScore },
      { domain: 'ANALYSIS' as const, score: analysisScore },
      { domain: 'CREATIVE' as const, score: creativeScore },
      { domain: 'RESEARCH' as const, score: researchScore },
    ];

    const best = scores.reduce((a, b) => (a.score > b.score ? a : b));
    return best.score > 0.3 ? best.domain : null;
  }

  /**
   * Calculate domain score for a category.
   */
  private calculateDomainScore(input: string, keywords: Record<string, unknown>): number {
    const lower = input.toLowerCase();
    let matches = 0;
    let total = 0;

    for (const [_key, value] of Object.entries(keywords)) {
      if (Array.isArray(value)) {
        total += value.length;
        matches += value.filter((v: string) => lower.includes(v.toLowerCase())).length;
      }
    }

    return total > 0 ? matches / total : 0;
  }

  /**
   * Assess complexity based on token count.
   */
  private assessComplexity(tokenCount: number): Complexity {
    if (tokenCount <= TOKEN_THRESHOLDS.SIMPLE_MAX) {
      return 'SIMPLE';
    }
    if (tokenCount <= TOKEN_THRESHOLDS.MODERATE_MAX) {
      return 'MODERATE';
    }
    return 'COMPLEX';
  }

  /**
   * Check for dangerous operations.
   */
  private containsDangerousOperation(input: string): boolean {
    return DANGEROUS_PATTERNS.some((pattern) => pattern.test(input));
  }

  /**
   * Estimate token count (rough approximation).
   */
  private estimateTokens(text: string): number {
    // Rough estimate: ~4 characters per token for English
    return Math.ceil(text.length / 4);
  }

  /**
   * Blend heuristic and API results.
   */
  private blendResults(
    heuristic: Omit<ClassificationResponse, 'cacheHit' | 'latencyMs'> | null,
    api: ClassificationResponse
  ): ClassificationResponse {
    if (!heuristic) {
      return api;
    }

    // If both agree, increase confidence
    if (heuristic.category === api.category) {
      return {
        ...api,
        confidence: Math.min(1.0, (heuristic.confidence + api.confidence) / 2 + 0.1),
      };
    }

    // If heuristic has higher confidence, prefer it
    if (heuristic.confidence > api.confidence) {
      return {
        ...heuristic,
        cacheHit: api.cacheHit,
        latencyMs: api.latencyMs,
      };
    }

    return api;
  }

  /**
   * Get cache key for request.
   */
  private getCacheKey(request: ClassificationRequest): string {
    return `${request.input.trim().substring(0, 500)}`;
  }

  /**
   * Get from cache if valid.
   */
  private getFromCache(key: string): ClassificationResponse | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() - entry.timestamp > this.cacheTtlMs) {
      this.cache.delete(key);
      return null;
    }

    return entry.response;
  }

  /**
   * Set cache entry.
   */
  private setCache(key: string, response: ClassificationResponse): void {
    this.cache.set(key, { response, timestamp: Date.now() });

    // Clean up old entries periodically
    if (this.cache.size > 1000) {
      const now = Date.now();
      for (const [k, v] of this.cache.entries()) {
        if (now - v.timestamp > this.cacheTtlMs) {
          this.cache.delete(k);
        }
      }
    }
  }

  /**
   * Clear the cache.
   */
  clearCache(): void {
    this.cache.clear();
  }
}

/** Create a new classifier */
export function createClassifier(
  apiClient: OptimizerApiClient,
  options?: { cacheTtlMs?: number }
): Classifier {
  return new Classifier(apiClient, options);
}
