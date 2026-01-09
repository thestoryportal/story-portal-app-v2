/**
 * Feedback processor for analyzing and learning from user feedback.
 */

import type {
  Domain,
  Category,
} from '../types/index.js';
import { PreferenceEngine, createPreferenceEngine, type PreferenceSignal } from './preference-engine.js';
import { PatternTracker, createPatternTracker } from './pattern-tracker.js';

/**
 * Feedback types.
 */
export type FeedbackType = 'accept' | 'reject' | 'modify' | 'skip';

/**
 * Feedback input.
 */
export interface FeedbackInput {
  /** Feedback type */
  type: FeedbackType;
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Modified version (for 'modify' type) */
  modified?: string;
  /** Classification category */
  category: Category;
  /** Detected domain */
  domain: Domain | null;
  /** Confidence score at optimization time */
  confidence: number;
  /** Time taken to provide feedback (ms) */
  responseTimeMs?: number;
  /** Optional text comment */
  comment?: string;
  /** Rating (1-5) */
  rating?: number;
}

/**
 * Feedback analysis result.
 */
export interface FeedbackAnalysis {
  /** Satisfaction score (0-1) */
  satisfaction: number;
  /** Areas for improvement */
  improvements: string[];
  /** Patterns detected */
  patterns: string[];
  /** Suggested adjustments */
  suggestions: string[];
}

/**
 * Aggregated feedback statistics.
 */
export interface FeedbackStats {
  /** Total feedback count */
  total: number;
  /** Breakdown by type */
  byType: Record<FeedbackType, number>;
  /** Breakdown by domain */
  byDomain: Record<string, { accepts: number; rejects: number; modifies: number }>;
  /** Breakdown by category */
  byCategory: Record<Category, { accepts: number; rejects: number; modifies: number }>;
  /** Average response time by type */
  avgResponseTime: Record<FeedbackType, number>;
  /** Average rating */
  avgRating: number;
  /** Recent trend (last 10 vs previous 10) */
  trend: 'improving' | 'stable' | 'declining';
}

/**
 * Feedback processor class.
 */
export class FeedbackProcessor {
  private preferenceEngine: PreferenceEngine;
  private patternTracker: PatternTracker;
  private feedbackHistory: FeedbackInput[] = [];
  private maxHistorySize = 1000;

  constructor(
    preferenceEngine?: PreferenceEngine,
    patternTracker?: PatternTracker
  ) {
    this.preferenceEngine = preferenceEngine ?? createPreferenceEngine();
    this.patternTracker = patternTracker ?? createPatternTracker();
  }

  /**
   * Process feedback.
   */
  process(feedback: FeedbackInput): FeedbackAnalysis {
    // Store in history
    this.feedbackHistory.push(feedback);
    if (this.feedbackHistory.length > this.maxHistorySize) {
      this.feedbackHistory = this.feedbackHistory.slice(-this.maxHistorySize);
    }

    // Skip type doesn't provide learning signal
    if (feedback.type !== 'skip') {
      // Send to preference engine for learning
      const signal: PreferenceSignal = {
        type: feedback.type,
        original: feedback.original,
        optimized: feedback.optimized,
        modified: feedback.modified,
        category: feedback.category,
        domain: feedback.domain,
        confidence: feedback.confidence,
        decisionTimeMs: feedback.responseTimeMs,
        comment: feedback.comment,
      };

      this.preferenceEngine.learn(signal);

      // Track patterns
      this.patternTracker.track(feedback.original, feedback.category, feedback.domain);
    }

    // Analyze the feedback
    return this.analyze(feedback);
  }

  /**
   * Analyze feedback for insights.
   */
  private analyze(feedback: FeedbackInput): FeedbackAnalysis {
    const improvements: string[] = [];
    const patterns: string[] = [];
    const suggestions: string[] = [];

    // Calculate satisfaction based on feedback type and context
    let satisfaction = this.calculateSatisfaction(feedback);

    // Analyze rejection patterns
    if (feedback.type === 'reject') {
      improvements.push('Optimization was rejected');

      if (feedback.confidence > 0.85) {
        improvements.push('High confidence optimization rejected - calibration needed');
        suggestions.push('Consider raising confidence threshold for this domain');
      }

      if (feedback.comment) {
        patterns.push(`User comment: ${feedback.comment}`);
      }
    }

    // Analyze modification patterns
    if (feedback.type === 'modify' && feedback.modified) {
      const modificationAnalysis = this.analyzeModification(
        feedback.optimized,
        feedback.modified
      );

      improvements.push(...modificationAnalysis.issues);
      patterns.push(...modificationAnalysis.patterns);
      suggestions.push(...modificationAnalysis.suggestions);
    }

    // Analyze timing
    if (feedback.responseTimeMs !== undefined) {
      if (feedback.responseTimeMs > 30000) {
        patterns.push('Long decision time - user may be uncertain');
        suggestions.push('Consider providing more context or explanation');
      } else if (feedback.responseTimeMs < 1000 && feedback.type === 'accept') {
        patterns.push('Quick acceptance - user trusts optimization');
      }
    }

    return {
      satisfaction,
      improvements,
      patterns,
      suggestions,
    };
  }

  /**
   * Calculate satisfaction score.
   */
  private calculateSatisfaction(feedback: FeedbackInput): number {
    let base: number;

    switch (feedback.type) {
      case 'accept':
        base = 0.9;
        break;
      case 'modify':
        base = 0.6;
        break;
      case 'reject':
        base = 0.2;
        break;
      case 'skip':
        base = 0.5;
        break;
    }

    // Adjust based on rating if provided
    if (feedback.rating !== undefined) {
      base = (base + (feedback.rating / 5)) / 2;
    }

    // Adjust based on response time (quick = more satisfied)
    if (feedback.responseTimeMs !== undefined) {
      if (feedback.responseTimeMs < 2000) {
        base += 0.05;
      } else if (feedback.responseTimeMs > 10000) {
        base -= 0.05;
      }
    }

    return Math.max(0, Math.min(1, base));
  }

  /**
   * Analyze modification to understand what user changed.
   */
  private analyzeModification(
    original: string,
    modified: string
  ): {
    issues: string[];
    patterns: string[];
    suggestions: string[];
  } {
    const issues: string[] = [];
    const patterns: string[] = [];
    const suggestions: string[] = [];

    const originalLength = original.length;
    const modifiedLength = modified.length;
    const lengthRatio = modifiedLength / originalLength;

    // Analyze length changes
    if (lengthRatio > 1.5) {
      issues.push('User significantly expanded the prompt');
      patterns.push('User prefers more detailed prompts');
      suggestions.push('Consider being less aggressive with conciseness');
    } else if (lengthRatio < 0.7) {
      issues.push('User significantly shortened the prompt');
      patterns.push('User prefers more concise prompts');
      suggestions.push('Consider more aggressive optimization');
    }

    // Check for added/removed structural elements
    const originalHasStructure = /[\n•\-\d+\.]/.test(original);
    const modifiedHasStructure = /[\n•\-\d+\.]/.test(modified);

    if (!originalHasStructure && modifiedHasStructure) {
      patterns.push('User added structure/formatting');
      suggestions.push('Consider adding structure to optimizations');
    } else if (originalHasStructure && !modifiedHasStructure) {
      patterns.push('User removed structure/formatting');
      suggestions.push('Consider simpler formatting in optimizations');
    }

    // Check for constraint additions
    const constraintPatterns = [
      /must|should|need to|required/i,
      /don't|do not|avoid|without/i,
      /only|just|specifically/i,
    ];

    for (const pattern of constraintPatterns) {
      const inOriginal = pattern.test(original);
      const inModified = pattern.test(modified);

      if (!inOriginal && inModified) {
        patterns.push('User added constraints');
        suggestions.push('Preserve or add explicit constraints');
      }
    }

    return { issues, patterns, suggestions };
  }

  /**
   * Get aggregated feedback statistics.
   */
  getStats(): FeedbackStats {
    const total = this.feedbackHistory.length;

    // By type
    const byType: Record<FeedbackType, number> = {
      accept: 0,
      reject: 0,
      modify: 0,
      skip: 0,
    };

    // By domain
    const byDomain: Record<string, { accepts: number; rejects: number; modifies: number }> = {};

    // By category
    const byCategory: Record<Category, { accepts: number; rejects: number; modifies: number }> = {
      PASS_THROUGH: { accepts: 0, rejects: 0, modifies: 0 },
      DEBUG: { accepts: 0, rejects: 0, modifies: 0 },
      OPTIMIZE: { accepts: 0, rejects: 0, modifies: 0 },
      CLARIFY: { accepts: 0, rejects: 0, modifies: 0 },
    };

    // Response times
    const responseTimesByType: Record<FeedbackType, number[]> = {
      accept: [],
      reject: [],
      modify: [],
      skip: [],
    };

    // Ratings
    const ratings: number[] = [];

    for (const feedback of this.feedbackHistory) {
      // Type count
      byType[feedback.type]++;

      // Domain stats
      const domainKey = feedback.domain ?? 'unknown';
      if (!byDomain[domainKey]) {
        byDomain[domainKey] = { accepts: 0, rejects: 0, modifies: 0 };
      }
      if (feedback.type === 'accept') {
        byDomain[domainKey].accepts++;
      } else if (feedback.type === 'reject') {
        byDomain[domainKey].rejects++;
      } else if (feedback.type === 'modify') {
        byDomain[domainKey].modifies++;
      }

      // Category stats
      if (feedback.type === 'accept') {
        byCategory[feedback.category].accepts++;
      } else if (feedback.type === 'reject') {
        byCategory[feedback.category].rejects++;
      } else if (feedback.type === 'modify') {
        byCategory[feedback.category].modifies++;
      }

      // Response times
      if (feedback.responseTimeMs !== undefined) {
        responseTimesByType[feedback.type].push(feedback.responseTimeMs);
      }

      // Ratings
      if (feedback.rating !== undefined) {
        ratings.push(feedback.rating);
      }
    }

    // Calculate average response times
    const avgResponseTime: Record<FeedbackType, number> = {
      accept: this.average(responseTimesByType.accept),
      reject: this.average(responseTimesByType.reject),
      modify: this.average(responseTimesByType.modify),
      skip: this.average(responseTimesByType.skip),
    };

    // Average rating
    const avgRating = ratings.length > 0 ? this.average(ratings) : 0;

    // Calculate trend
    const trend = this.calculateTrend();

    return {
      total,
      byType,
      byDomain,
      byCategory,
      avgResponseTime,
      avgRating,
      trend,
    };
  }

  /**
   * Calculate average.
   */
  private average(values: number[]): number {
    if (values.length === 0) return 0;
    return values.reduce((a, b) => a + b, 0) / values.length;
  }

  /**
   * Calculate trend based on recent vs previous feedback.
   */
  private calculateTrend(): 'improving' | 'stable' | 'declining' {
    if (this.feedbackHistory.length < 20) {
      return 'stable';
    }

    const recent = this.feedbackHistory.slice(-10);
    const previous = this.feedbackHistory.slice(-20, -10);

    const recentAcceptRate = recent.filter((f) => f.type === 'accept').length / recent.length;
    const previousAcceptRate = previous.filter((f) => f.type === 'accept').length / previous.length;

    const diff = recentAcceptRate - previousAcceptRate;

    if (diff > 0.1) {
      return 'improving';
    } else if (diff < -0.1) {
      return 'declining';
    }

    return 'stable';
  }

  /**
   * Get recent feedback.
   */
  getRecentFeedback(limit: number = 10): FeedbackInput[] {
    return this.feedbackHistory.slice(-limit);
  }

  /**
   * Check if user is satisfied based on recent feedback.
   */
  isUserSatisfied(): boolean {
    if (this.feedbackHistory.length < 5) {
      return true; // Assume satisfied with insufficient data
    }

    const recent = this.feedbackHistory.slice(-10);
    const acceptRate = recent.filter((f) => f.type === 'accept').length / recent.length;
    const rejectRate = recent.filter((f) => f.type === 'reject').length / recent.length;

    // Satisfied if accept rate > 50% and reject rate < 30%
    return acceptRate > 0.5 && rejectRate < 0.3;
  }

  /**
   * Get improvement recommendations.
   */
  getRecommendations(): string[] {
    const recommendations: string[] = [];
    const stats = this.getStats();

    // High rejection rate
    if (stats.total > 10) {
      const rejectRate = stats.byType.reject / stats.total;
      if (rejectRate > 0.3) {
        recommendations.push('High rejection rate - consider raising confidence thresholds');
      }
    }

    // High modification rate
    if (stats.total > 10) {
      const modifyRate = stats.byType.modify / stats.total;
      if (modifyRate > 0.4) {
        recommendations.push('High modification rate - optimization style may not match user preferences');
      }
    }

    // Domain-specific issues
    for (const [domain, domainStats] of Object.entries(stats.byDomain)) {
      const total = domainStats.accepts + domainStats.rejects + domainStats.modifies;
      if (total > 5) {
        const domainRejectRate = domainStats.rejects / total;
        if (domainRejectRate > 0.4) {
          recommendations.push(`High rejection rate for ${domain} domain - review domain-specific optimization`);
        }
      }
    }

    // Trend analysis
    if (stats.trend === 'declining') {
      recommendations.push('Acceptance rate is declining - review recent changes to optimization approach');
    }

    return recommendations;
  }

  /**
   * Clear feedback history.
   */
  clear(): void {
    this.feedbackHistory = [];
  }
}

/**
 * Create a feedback processor.
 */
export function createFeedbackProcessor(
  preferenceEngine?: PreferenceEngine,
  patternTracker?: PatternTracker
): FeedbackProcessor {
  return new FeedbackProcessor(preferenceEngine, patternTracker);
}
