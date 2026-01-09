/**
 * Review gate layer.
 * Determines when user review is needed based on confidence and changes.
 * Maps to spec section 5.2 - Review Gate.
 */

import type { OptimizationResponse, ClassificationResponse } from '../types/index.js';
import { ROUTING_THRESHOLDS } from '../constants/index.js';
import {
  calculateConfidence,
  calculateChangeMagnitude,
  type ConfidenceFactors,
  type ConfidenceResult,
} from '../utils/confidence.js';
import { createElementExtractor, type ExtractedElements } from '../utils/element-extractor.js';

/**
 * Review decision result.
 */
export interface ReviewDecision {
  /** Whether user review is required */
  requiresReview: boolean;
  /** Reason for the decision */
  reason: string;
  /** Confidence analysis */
  confidence: ConfidenceResult;
  /** Risk level */
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  /** Specific concerns to highlight */
  concerns: string[];
  /** Suggested review focus areas */
  reviewFocus: string[];
}

/**
 * Review gate options.
 */
export interface ReviewGateOptions {
  /** Confidence threshold for auto-accept (default 0.9) */
  autoAcceptThreshold?: number;
  /** Confidence threshold for mandatory review (default 0.7) */
  reviewThreshold?: number;
  /** Maximum change magnitude for auto-accept (default 0.3) */
  maxAutoAcceptChange?: number;
  /** Whether to always review negative constraint changes */
  alwaysReviewConstraints?: boolean;
  /** User's historical acceptance rate */
  userAcceptanceRate?: number;
}

/**
 * Review gate class.
 */
export class ReviewGate {
  private elementExtractor = createElementExtractor();
  private options: Required<ReviewGateOptions>;

  constructor(options: ReviewGateOptions = {}) {
    this.options = {
      autoAcceptThreshold: options.autoAcceptThreshold ?? ROUTING_THRESHOLDS.AUTO_HIGH,
      reviewThreshold: options.reviewThreshold ?? ROUTING_THRESHOLDS.CONFIRM,
      maxAutoAcceptChange: options.maxAutoAcceptChange ?? 0.3,
      alwaysReviewConstraints: options.alwaysReviewConstraints ?? true,
      userAcceptanceRate: options.userAcceptanceRate ?? 0.8,
    };
  }

  /**
   * Evaluate whether optimization requires review.
   */
  evaluate(
    original: string,
    optimized: string,
    classification: ClassificationResponse,
    optimization: OptimizationResponse
  ): ReviewDecision {
    const concerns: string[] = [];
    const reviewFocus: string[] = [];

    // Calculate change magnitude
    const changeMagnitude = calculateChangeMagnitude(original, optimized);

    // Check element preservation
    const preservation = this.elementExtractor.checkPreservation(original, optimized);
    if (!preservation.preserved) {
      concerns.push(`Missing elements: ${preservation.missing.slice(0, 3).join(', ')}`);
      reviewFocus.push('Verify all important elements are preserved');
    }

    // Check for constraint changes
    const constraintChange = this.checkConstraintPreservation(
      preservation.elements,
      optimized
    );
    if (constraintChange.hasChange) {
      concerns.push(constraintChange.concern);
      reviewFocus.push('Verify constraints are correctly preserved');
    }

    // Build confidence factors
    const factors: ConfidenceFactors = {
      classification: classification.confidence,
      intentPreservation: optimization.intentSimilarity,
      domainMatch: classification.domain ? 0.9 : 0.7,
      changeMagnitude,
      userAcceptance: this.options.userAcceptanceRate,
    };

    // Calculate confidence
    const confidence = calculateConfidence(factors);

    // Determine if review is required
    const { requiresReview, reason, riskLevel } = this.makeDecision(
      confidence,
      changeMagnitude,
      concerns,
      optimization
    );

    // Add general review focus areas
    if (requiresReview) {
      if (changeMagnitude > 0.5) {
        reviewFocus.push('Compare overall meaning and intent');
      }
      if (optimization.changes.length > 3) {
        reviewFocus.push('Review multiple changes made');
      }
      if (classification.domain === 'CODE') {
        reviewFocus.push('Verify technical accuracy');
      }
    }

    return {
      requiresReview,
      reason,
      confidence,
      riskLevel,
      concerns,
      reviewFocus,
    };
  }

  /**
   * Make the review decision.
   */
  private makeDecision(
    confidence: ConfidenceResult,
    changeMagnitude: number,
    concerns: string[],
    optimization: OptimizationResponse
  ): {
    requiresReview: boolean;
    reason: string;
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  } {
    // High confidence + low change + no concerns = auto-accept
    if (
      confidence.score >= this.options.autoAcceptThreshold &&
      changeMagnitude <= this.options.maxAutoAcceptChange &&
      concerns.length === 0
    ) {
      return {
        requiresReview: false,
        reason: 'High confidence optimization with minimal changes',
        riskLevel: 'LOW',
      };
    }

    // Any concerns = require review
    if (concerns.length > 0) {
      return {
        requiresReview: true,
        reason: `Review needed: ${concerns[0]}`,
        riskLevel: concerns.length > 1 ? 'HIGH' : 'MEDIUM',
      };
    }

    // Low confidence = require review
    if (confidence.score < this.options.reviewThreshold) {
      return {
        requiresReview: true,
        reason: `Low confidence (${(confidence.score * 100).toFixed(0)}%) - review recommended`,
        riskLevel: confidence.score < 0.5 ? 'HIGH' : 'MEDIUM',
      };
    }

    // High change magnitude = require review
    if (changeMagnitude > this.options.maxAutoAcceptChange) {
      return {
        requiresReview: true,
        reason: `Significant changes (${(changeMagnitude * 100).toFixed(0)}% difference)`,
        riskLevel: changeMagnitude > 0.6 ? 'HIGH' : 'MEDIUM',
      };
    }

    // Many changes = require review
    if (optimization.changes.length > 5) {
      return {
        requiresReview: true,
        reason: `Multiple changes (${optimization.changes.length}) - review recommended`,
        riskLevel: 'MEDIUM',
      };
    }

    // Moderate confidence with acceptable changes = auto-accept
    if (confidence.score >= this.options.reviewThreshold) {
      return {
        requiresReview: false,
        reason: 'Acceptable confidence with moderate changes',
        riskLevel: 'LOW',
      };
    }

    // Default to requiring review
    return {
      requiresReview: true,
      reason: 'Review recommended for quality assurance',
      riskLevel: 'MEDIUM',
    };
  }

  /**
   * Check if constraints are preserved.
   */
  private checkConstraintPreservation(
    originalElements: ExtractedElements,
    optimized: string
  ): { hasChange: boolean; concern: string } {
    if (!this.options.alwaysReviewConstraints) {
      return { hasChange: false, concern: '' };
    }

    const optimizedLower = optimized.toLowerCase();

    // Check negative constraints
    for (const constraint of originalElements.negativeConstraints) {
      const normalizedConstraint = constraint.toLowerCase().trim();

      // Check if key negative words are preserved
      const negativeWords = ['don\'t', 'do not', 'never', 'avoid', 'without', 'except', 'not'];
      const hasNegative = negativeWords.some((neg) => normalizedConstraint.includes(neg));

      if (hasNegative) {
        // Check if the constraint is still in the optimized version
        const keyWords = normalizedConstraint
          .split(/\s+/)
          .filter((w) => w.length > 3 && !negativeWords.includes(w));

        const preserved = keyWords.length === 0 ||
          keyWords.some((kw) => optimizedLower.includes(kw));

        if (!preserved) {
          return {
            hasChange: true,
            concern: `Negative constraint may have been lost: "${constraint.slice(0, 50)}..."`,
          };
        }
      }
    }

    return { hasChange: false, concern: '' };
  }

  /**
   * Update options.
   */
  updateOptions(options: Partial<ReviewGateOptions>): void {
    this.options = {
      ...this.options,
      ...options,
    };
  }

  /**
   * Get current options.
   */
  getOptions(): Required<ReviewGateOptions> {
    return { ...this.options };
  }
}

/**
 * Create a review gate.
 */
export function createReviewGate(options?: ReviewGateOptions): ReviewGate {
  return new ReviewGate(options);
}
