/**
 * Local LLM client for the prompt optimizer.
 * Supports Ollama and other OpenAI-compatible local LLM servers.
 */

import type {
  ClassificationRequest,
  ClassificationResponse,
  OptimizationRequest,
  OptimizationResponse,
  VerificationRequest,
  VerificationResponse,
  OptimizerApiClient,
} from '../types/index.js';
import {
  CLASSIFICATION_PROMPT,
  PASS_ONE_PROMPT,
  VERIFICATION_PROMPT,
} from '../constants/index.js';
import { OptimizerApiError } from '../types/api.js';

/** Local LLM configuration */
export interface LocalLLMConfig {
  /** Model name (e.g., 'llama3.2', 'mistral', 'codellama') */
  model?: string;
  /** Base URL for the LLM server */
  baseUrl?: string;
  /** Request timeout in ms */
  timeout?: number;
  /** Temperature for generation */
  temperature?: number;
}

/** Default configuration */
const DEFAULT_CONFIG: Required<LocalLLMConfig> = {
  model: 'llama3.2',
  baseUrl: 'http://localhost:11434',
  timeout: 60000,
  temperature: 0.3,
};

/** Ollama generate response */
interface OllamaGenerateResponse {
  model: string;
  response: string;
  done: boolean;
  context?: number[];
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  eval_count?: number;
}

/**
 * Local LLM client using Ollama API.
 */
export class LocalLLMClient implements OptimizerApiClient {
  private config: Required<LocalLLMConfig>;

  constructor(config: LocalLLMConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Classify a prompt into one of four categories.
   */
  async classify(request: ClassificationRequest): Promise<ClassificationResponse> {
    const startTime = Date.now();

    const prompt = this.buildClassificationPrompt(request);
    const response = await this.generate(prompt);

    try {
      const parsed = this.parseJsonResponse<{
        category: string;
        domain: string | null;
        complexity: string;
        confidence: number;
        reasoning: string;
      }>(response);

      return {
        category: this.validateCategory(parsed.category),
        domain: this.validateDomain(parsed.domain),
        complexity: this.validateComplexity(parsed.complexity),
        confidence: Math.min(1, Math.max(0, parsed.confidence ?? 0.7)),
        reasoning: parsed.reasoning ?? 'Classification complete',
        cacheHit: false,
        latencyMs: Date.now() - startTime,
      };
    } catch {
      // Fallback to heuristic classification if parsing fails
      return this.heuristicClassify(request, Date.now() - startTime);
    }
  }

  /**
   * Optimize a prompt based on classification.
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    const startTime = Date.now();

    const prompt = this.buildOptimizationPrompt(request);
    const response = await this.generate(prompt);

    try {
      const parsed = this.parseJsonResponse<{
        optimized_prompt: string;
        changes_made: Array<{ type: string; original: string; new: string; reason: string }>;
        preserved_elements: string[];
        confidence: number;
      }>(response);

      return {
        optimized: parsed.optimized_prompt ?? request.original,
        changes: (parsed.changes_made ?? []).map((c) => ({
          type: this.validateChangeType(c.type),
          originalSegment: c.original ?? '',
          newSegment: c.new ?? '',
          reason: c.reason ?? 'Optimization applied',
        })),
        preservedElements: parsed.preserved_elements ?? [],
        passesUsed: 1,
        confidence: Math.min(1, Math.max(0, parsed.confidence ?? 0.75)),
        intentSimilarity: 0.9,
        explanation: 'Optimization complete via local LLM',
        tip: this.generateTip(request.classification.domain),
        latencyMs: Date.now() - startTime,
      };
    } catch {
      // Fallback: return original with minor enhancement
      return this.fallbackOptimize(request, Date.now() - startTime);
    }
  }

  /**
   * Verify intent preservation between original and optimized prompts.
   */
  async verify(request: VerificationRequest): Promise<VerificationResponse> {
    const startTime = Date.now();

    const prompt = this.buildVerificationPrompt(request);
    const response = await this.generate(prompt);

    try {
      const parsed = this.parseJsonResponse<{
        status: string;
        similarity_score: number;
        preserved_ratio: number;
        issues: Array<{ type: string; severity: string; description: string }>;
        recommendation: string;
      }>(response);

      return {
        status: this.validateStatus(parsed.status),
        similarityScore: Math.min(1, Math.max(0, parsed.similarity_score ?? 0.85)),
        preservedRatio: Math.min(1, Math.max(0, parsed.preserved_ratio ?? 0.9)),
        issues: (parsed.issues ?? []).map((i) => ({
          type: this.validateIssueType(i.type),
          severity: this.validateSeverity(i.severity),
          description: i.description ?? 'Issue detected',
        })),
        recommendation: parsed.recommendation ?? 'Verification complete',
      };
    } catch {
      // Fallback to simple verification
      return this.fallbackVerify(request, Date.now() - startTime);
    }
  }

  /**
   * Generate embeddings (not supported for local LLM, returns empty).
   */
  async embed(_text: string): Promise<number[]> {
    // Local embedding could be implemented with Ollama's embedding API
    // For now, return empty array - similarity is computed differently
    return [];
  }

  /**
   * Make a generation request to Ollama.
   */
  private async generate(prompt: string): Promise<string> {
    const url = `${this.config.baseUrl}/api/generate`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.config.model,
          prompt,
          stream: false,
          options: {
            temperature: this.config.temperature,
          },
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new OptimizerApiError(
          `Local LLM request failed: ${response.status} ${response.statusText} - ${errorText}`,
          response.status,
          'LOCAL_LLM_ERROR'
        );
      }

      const data = (await response.json()) as OllamaGenerateResponse;
      return data.response;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof OptimizerApiError) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new OptimizerApiError(
          `Local LLM request timed out after ${this.config.timeout}ms`,
          408,
          'TIMEOUT'
        );
      }

      throw new OptimizerApiError(
        `Failed to connect to local LLM at ${this.config.baseUrl}. Is Ollama running? Error: ${(error as Error).message}`,
        undefined,
        'CONNECTION_ERROR'
      );
    }
  }

  /**
   * Build classification prompt.
   */
  private buildClassificationPrompt(request: ClassificationRequest): string {
    return `${CLASSIFICATION_PROMPT}

Input prompt to classify:
${request.input}

${request.context ? `Context:
- Language: ${request.context.projectLanguage ?? 'unknown'}
- Framework: ${request.context.projectFramework ?? 'unknown'}
- Expertise: ${request.context.expertiseLevel ?? 'unknown'}` : ''}

Respond with a JSON object containing: category, domain, complexity, confidence, reasoning.
Categories: PASS_THROUGH, DEBUG, OPTIMIZE, CLARIFY
Domains: CODE, WRITING, ANALYSIS, CREATIVE, RESEARCH, or null
Complexity: SIMPLE, MODERATE, COMPLEX

JSON response:`;
  }

  /**
   * Build optimization prompt.
   */
  private buildOptimizationPrompt(request: OptimizationRequest): string {
    const systemPrompt = PASS_ONE_PROMPT
      .replace('{domain}', request.classification.domain ?? 'UNKNOWN')
      .replace('{session_context}', JSON.stringify(request.context.session ?? {}))
      .replace('{project_context}', JSON.stringify(request.context.project ?? {}))
      .replace('{user_preferences}', JSON.stringify(request.context.user ?? {}));

    return `${systemPrompt}

Original prompt to optimize:
${request.original}

Classification:
- Category: ${request.classification.category}
- Domain: ${request.classification.domain ?? 'unknown'}
- Complexity: ${request.classification.complexity}

Respond with a JSON object containing: optimized_prompt, changes_made (array of {type, original, new, reason}), preserved_elements (array of strings), confidence (0-1).
Change types: ADD_CONTEXT, CLARIFY, RESTRUCTURE, REMOVE_REDUNDANCY

JSON response:`;
  }

  /**
   * Build verification prompt.
   */
  private buildVerificationPrompt(request: VerificationRequest): string {
    const prompt = VERIFICATION_PROMPT
      .replace('{original}', request.original)
      .replace('{optimized}', request.optimized)
      .replace('{preserved_elements}', request.preservedElements.join(', '));

    return `${prompt}

Respond with a JSON object containing: status (VERIFIED/WARN/REJECTED), similarity_score (0-1), preserved_ratio (0-1), issues (array of {type, severity, description}), recommendation.
Issue types: INTENT_DRIFT, LOST_CONSTRAINT, ADDED_ASSUMPTION, CHANGED_SCOPE
Severity: HIGH, MEDIUM, LOW

JSON response:`;
  }

  /**
   * Parse JSON from response text.
   */
  private parseJsonResponse<T>(text: string): T {
    // Try to extract JSON from the response
    // Handle markdown code blocks
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    let jsonText = jsonMatch ? jsonMatch[1] : text;

    // Try to find JSON object in text
    const objectMatch = jsonText.match(/\{[\s\S]*\}/);
    if (objectMatch) {
      jsonText = objectMatch[0];
    }

    try {
      return JSON.parse(jsonText.trim()) as T;
    } catch {
      throw new OptimizerApiError(
        `Failed to parse JSON from local LLM response`,
        undefined,
        'JSON_PARSE_ERROR'
      );
    }
  }

  /**
   * Heuristic classification fallback.
   */
  private heuristicClassify(
    request: ClassificationRequest,
    latencyMs: number
  ): ClassificationResponse {
    const input = request.input.toLowerCase();

    // Determine category
    let category: ClassificationResponse['category'] = 'OPTIMIZE';
    if (input.length < 10) {
      category = 'CLARIFY';
    } else if (/\b(error|exception|failed|bug|crash|broken)\b/.test(input)) {
      category = 'DEBUG';
    } else if (input.length > 100 && /\b(please|help|how|what|why|explain)\b/.test(input)) {
      category = 'PASS_THROUGH';
    }

    // Determine domain
    let domain: ClassificationResponse['domain'] = null;
    if (/\b(code|function|class|variable|api|debug|error|bug)\b/.test(input)) {
      domain = 'CODE';
    } else if (/\b(write|essay|article|blog|story|document)\b/.test(input)) {
      domain = 'WRITING';
    } else if (/\b(analyze|compare|evaluate|review|assess)\b/.test(input)) {
      domain = 'ANALYSIS';
    } else if (/\b(creative|brainstorm|idea|story|poem)\b/.test(input)) {
      domain = 'CREATIVE';
    } else if (/\b(research|learn|explain|understand|study)\b/.test(input)) {
      domain = 'RESEARCH';
    }

    // Determine complexity
    let complexity: ClassificationResponse['complexity'] = 'MODERATE';
    if (input.length < 50) {
      complexity = 'SIMPLE';
    } else if (input.length > 200 || input.split('\n').length > 5) {
      complexity = 'COMPLEX';
    }

    return {
      category,
      domain,
      complexity,
      confidence: 0.7,
      reasoning: 'Classified using heuristics (LLM parsing failed)',
      cacheHit: false,
      latencyMs,
    };
  }

  /**
   * Fallback optimization when LLM response parsing fails.
   */
  private fallbackOptimize(
    request: OptimizationRequest,
    latencyMs: number
  ): OptimizationResponse {
    let optimized = request.original;
    const changes: OptimizationResponse['changes'] = [];

    // Simple enhancements
    if (/^help\s+me/i.test(optimized)) {
      optimized = optimized.replace(/^help\s+me/i, 'Please help me');
      changes.push({
        type: 'CLARIFY',
        originalSegment: 'help me',
        newSegment: 'Please help me',
        reason: 'Added polite prefix',
      });
    } else if (/^help\b/i.test(optimized)) {
      optimized = optimized.replace(/^help\b/i, 'Please help');
      changes.push({
        type: 'CLARIFY',
        originalSegment: 'help',
        newSegment: 'Please help',
        reason: 'Added polite prefix',
      });
    }

    return {
      optimized,
      changes,
      preservedElements: [],
      passesUsed: 1,
      confidence: 0.6,
      intentSimilarity: 0.95,
      explanation: 'Basic optimization applied (LLM parsing failed)',
      tip: this.generateTip(request.classification.domain),
      latencyMs,
    };
  }

  /**
   * Fallback verification when LLM response parsing fails.
   */
  private fallbackVerify(
    request: VerificationRequest,
    _latencyMs: number
  ): VerificationResponse {
    // Simple word overlap check
    const originalWords = new Set(request.original.toLowerCase().split(/\s+/));
    const optimizedWords = new Set(request.optimized.toLowerCase().split(/\s+/));
    const intersection = [...originalWords].filter((w) => optimizedWords.has(w));
    const similarity = intersection.length / Math.max(originalWords.size, 1);

    return {
      status: similarity > 0.5 ? 'VERIFIED' : 'WARN',
      similarityScore: similarity,
      preservedRatio: 1,
      issues: [],
      recommendation: 'Verification complete (using fallback)',
    };
  }

  /**
   * Validate and normalize category.
   */
  private validateCategory(category: string): ClassificationResponse['category'] {
    const normalized = category?.toUpperCase();
    if (['PASS_THROUGH', 'DEBUG', 'OPTIMIZE', 'CLARIFY'].includes(normalized)) {
      return normalized as ClassificationResponse['category'];
    }
    return 'OPTIMIZE';
  }

  /**
   * Validate and normalize domain.
   */
  private validateDomain(domain: string | null): ClassificationResponse['domain'] {
    if (!domain) return null;
    const normalized = domain.toUpperCase();
    if (['CODE', 'WRITING', 'ANALYSIS', 'CREATIVE', 'RESEARCH'].includes(normalized)) {
      return normalized as ClassificationResponse['domain'];
    }
    return null;
  }

  /**
   * Validate and normalize complexity.
   */
  private validateComplexity(complexity: string): ClassificationResponse['complexity'] {
    const normalized = complexity?.toUpperCase();
    if (['SIMPLE', 'MODERATE', 'COMPLEX'].includes(normalized)) {
      return normalized as ClassificationResponse['complexity'];
    }
    return 'MODERATE';
  }

  /**
   * Validate and normalize change type.
   */
  private validateChangeType(type: string): OptimizationResponse['changes'][0]['type'] {
    const normalized = type?.toUpperCase();
    if (['ADD_CONTEXT', 'CLARIFY', 'RESTRUCTURE', 'REMOVE_REDUNDANCY'].includes(normalized)) {
      return normalized as OptimizationResponse['changes'][0]['type'];
    }
    return 'CLARIFY';
  }

  /**
   * Validate and normalize verification status.
   */
  private validateStatus(status: string): VerificationResponse['status'] {
    const normalized = status?.toUpperCase();
    if (['VERIFIED', 'WARN', 'REJECTED'].includes(normalized)) {
      return normalized as VerificationResponse['status'];
    }
    return 'VERIFIED';
  }

  /**
   * Validate and normalize issue type.
   */
  private validateIssueType(type: string): VerificationResponse['issues'][0]['type'] {
    const normalized = type?.toUpperCase();
    if (['INTENT_DRIFT', 'LOST_CONSTRAINT', 'ADDED_ASSUMPTION', 'CHANGED_SCOPE'].includes(normalized)) {
      return normalized as VerificationResponse['issues'][0]['type'];
    }
    return 'INTENT_DRIFT';
  }

  /**
   * Validate and normalize severity.
   */
  private validateSeverity(severity: string): VerificationResponse['issues'][0]['severity'] {
    const normalized = severity?.toUpperCase();
    if (['HIGH', 'MEDIUM', 'LOW'].includes(normalized)) {
      return normalized as VerificationResponse['issues'][0]['severity'];
    }
    return 'MEDIUM';
  }

  /**
   * Generate a tip based on domain.
   */
  private generateTip(domain: string | null): string {
    const tips: Record<string, string> = {
      CODE: 'Include specific file paths and error messages for faster debugging.',
      WRITING: 'Specify your target audience and desired tone upfront.',
      ANALYSIS: 'Define clear comparison criteria and output format.',
      CREATIVE: 'Balance constraints with creative freedom.',
      RESEARCH: 'Specify the depth of explanation you need.',
    };
    return tips[domain ?? ''] ?? 'Be specific about what you want to achieve.';
  }
}

/**
 * Create a local LLM client.
 */
export function createLocalLLMClient(config?: LocalLLMConfig): LocalLLMClient {
  return new LocalLLMClient(config);
}
