/**
 * API types for the prompt optimizer.
 * Maps to spec section 15: API Contracts.
 */

import type { ClassificationRequest, ClassificationResponse } from './classification.js';
import type { OptimizationRequest, OptimizationResponse } from './optimization.js';

/** Intent verification request */
export interface VerificationRequest {
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Elements that should be preserved */
  preservedElements: string[];
}

/** Verification status */
export type VerificationStatus = 'VERIFIED' | 'WARN' | 'REJECTED';

/** Issue types found during verification */
export type IssueType =
  | 'INTENT_DRIFT'
  | 'LOST_CONSTRAINT'
  | 'ADDED_ASSUMPTION'
  | 'CHANGED_SCOPE';

/** Severity levels */
export type IssueSeverity = 'HIGH' | 'MEDIUM' | 'LOW';

/** A verification issue */
export interface VerificationIssue {
  /** Type of issue */
  type: IssueType;
  /** Severity level */
  severity: IssueSeverity;
  /** Description of the issue */
  description: string;
}

/** Intent verification response */
export interface VerificationResponse {
  /** Verification status */
  status: VerificationStatus;
  /** Semantic similarity score (0.0 - 1.0) */
  similarityScore: number;
  /** Ratio of preserved elements (0.0 - 1.0) */
  preservedRatio: number;
  /** Issues found during verification */
  issues: VerificationIssue[];
  /** Recommendation for next action */
  recommendation: string;
}

/** API client interface */
export interface OptimizerApiClient {
  /** Classify a prompt */
  classify(request: ClassificationRequest): Promise<ClassificationResponse>;
  /** Optimize a prompt */
  optimize(request: OptimizationRequest): Promise<OptimizationResponse>;
  /** Verify intent preservation */
  verify(request: VerificationRequest): Promise<VerificationResponse>;
  /** Generate embeddings for similarity */
  embed(text: string): Promise<number[]>;
}

/** API client configuration */
export interface ApiClientConfig {
  /** API key */
  apiKey?: string;
  /** Base URL */
  baseUrl?: string;
  /** Request timeout in ms */
  timeout?: number;
  /** Number of retries */
  retries?: number;
  /** Use mock responses */
  useMock?: boolean;
}

/** API error */
export class OptimizerApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly code?: string,
    public readonly retryable?: boolean
  ) {
    super(message);
    this.name = 'OptimizerApiError';
  }
}

/** Rate limit error */
export class RateLimitError extends OptimizerApiError {
  constructor(
    message: string,
    public readonly retryAfterMs?: number
  ) {
    super(message, 429, 'RATE_LIMITED', true);
    this.name = 'RateLimitError';
  }
}

/** Model selection for API calls */
export interface ModelSelection {
  /** Model for classification */
  classification: string;
  /** Model for simple optimization */
  simpleOptimization: string;
  /** Model for complex optimization */
  complexOptimization: string;
  /** Model for intent verification */
  intentVerification: string;
}

/** API response wrapper */
export interface ApiResponse<T> {
  /** Whether the request succeeded */
  success: boolean;
  /** Response data */
  data?: T;
  /** Error information */
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  /** Metadata */
  meta?: {
    latencyMs: number;
    model: string;
    tokensUsed: {
      input: number;
      output: number;
    };
  };
}
