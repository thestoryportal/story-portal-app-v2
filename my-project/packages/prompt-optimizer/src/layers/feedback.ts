/**
 * Feedback collection layer for gathering user feedback on optimizations.
 */

import type { Category, Domain } from '../types/index.js';
import {
  FeedbackProcessor,
  createFeedbackProcessor,
  type FeedbackInput,
  type FeedbackType,
  type FeedbackAnalysis,
} from '../learning/feedback-processor.js';
import { MetricsCollector, createMetricsCollector } from '../metrics/collector.js';

/**
 * Feedback request for user.
 */
export interface FeedbackRequest {
  /** Optimization ID */
  optimizationId: string;
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Classification category */
  category: Category;
  /** Detected domain */
  domain: Domain | null;
  /** Confidence score */
  confidence: number;
  /** Time optimization was shown */
  shownAt: number;
}

/**
 * Feedback response from user.
 */
export interface FeedbackResponse {
  /** Feedback type */
  type: FeedbackType;
  /** Modified text (for 'modify' type) */
  modified?: string;
  /** Optional comment */
  comment?: string;
  /** Optional rating (1-5) */
  rating?: number;
}

/**
 * Feedback layer class.
 */
export class FeedbackLayer {
  private processor: FeedbackProcessor;
  private metricsCollector: MetricsCollector;
  private pendingRequest: FeedbackRequest | null = null;

  constructor(
    processor?: FeedbackProcessor,
    metricsCollector?: MetricsCollector
  ) {
    this.processor = processor ?? createFeedbackProcessor();
    this.metricsCollector = metricsCollector ?? createMetricsCollector();
  }

  /**
   * Create a feedback request for an optimization.
   */
  createRequest(
    original: string,
    optimized: string,
    category: Category,
    domain: Domain | null,
    confidence: number
  ): FeedbackRequest {
    const request: FeedbackRequest = {
      optimizationId: `opt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      original,
      optimized,
      category,
      domain,
      confidence,
      shownAt: Date.now(),
    };

    this.pendingRequest = request;
    return request;
  }

  /**
   * Process feedback response.
   */
  processFeedback(response: FeedbackResponse): FeedbackAnalysis {
    if (!this.pendingRequest) {
      throw new Error('No pending feedback request');
    }

    const request = this.pendingRequest;
    const responseTimeMs = Date.now() - request.shownAt;

    // Build feedback input
    const input: FeedbackInput = {
      type: response.type,
      original: request.original,
      optimized: request.optimized,
      modified: response.modified,
      category: request.category,
      domain: request.domain,
      confidence: request.confidence,
      responseTimeMs,
      comment: response.comment,
      rating: response.rating,
    };

    // Process through feedback processor
    const analysis = this.processor.process(input);

    // Record metrics
    this.metricsCollector.recordInteraction(
      response.type === 'skip' ? 'skip' : response.type,
      responseTimeMs,
      request.confidence < 0.85, // review required if low confidence
      response.comment !== undefined || response.rating !== undefined
    );

    // Clear pending request
    this.pendingRequest = null;

    return analysis;
  }

  /**
   * Get pending request.
   */
  getPendingRequest(): FeedbackRequest | null {
    return this.pendingRequest;
  }

  /**
   * Cancel pending request.
   */
  cancelPending(): void {
    this.pendingRequest = null;
  }

  /**
   * Check if user feedback is recommended.
   */
  shouldRequestFeedback(confidence: number): boolean {
    // Always request feedback for:
    // 1. Low confidence optimizations
    // 2. First 10 optimizations (to build learning data)
    // 3. Randomly 10% of the time for high confidence

    const stats = this.processor.getStats();

    if (confidence < 0.7) {
      return true;
    }

    if (stats.total < 10) {
      return true;
    }

    // Random sampling for high confidence
    if (Math.random() < 0.1) {
      return true;
    }

    return false;
  }

  /**
   * Get quick feedback options.
   */
  getQuickOptions(): Array<{ type: FeedbackType; label: string; shortcut: string }> {
    return [
      { type: 'accept', label: 'Accept', shortcut: 'y' },
      { type: 'reject', label: 'Reject', shortcut: 'n' },
      { type: 'modify', label: 'Modify', shortcut: 'm' },
      { type: 'skip', label: 'Skip', shortcut: 's' },
    ];
  }

  /**
   * Validate modified prompt.
   */
  validateModified(modified: string, original: string): { valid: boolean; issues: string[] } {
    const issues: string[] = [];

    // Check minimum length
    if (modified.trim().length < 5) {
      issues.push('Modified prompt is too short');
    }

    // Check if it's identical to original
    if (modified.trim() === original.trim()) {
      issues.push('Modified prompt is identical to original');
    }

    // Check for suspicious patterns
    if (/^(test|asdf|xxx)/i.test(modified)) {
      issues.push('Modified prompt appears to be a test');
    }

    return {
      valid: issues.length === 0,
      issues,
    };
  }

  /**
   * Get feedback statistics.
   */
  getStats() {
    return this.processor.getStats();
  }

  /**
   * Get recommendations based on feedback.
   */
  getRecommendations(): string[] {
    return this.processor.getRecommendations();
  }

  /**
   * Check if user is satisfied.
   */
  isUserSatisfied(): boolean {
    return this.processor.isUserSatisfied();
  }

  /**
   * Get recent feedback.
   */
  getRecentFeedback(limit: number = 5) {
    return this.processor.getRecentFeedback(limit);
  }
}

/**
 * Create a feedback layer.
 */
export function createFeedbackLayer(
  processor?: FeedbackProcessor,
  metricsCollector?: MetricsCollector
): FeedbackLayer {
  return new FeedbackLayer(processor, metricsCollector);
}
