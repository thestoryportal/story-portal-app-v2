/**
 * User context provider.
 * Tracks user preferences and patterns.
 * Maps to spec section 3.3 - User Context.
 */

import type { UserContext, UserPreferences, StylePreference } from '../types/index.js';

/**
 * Default user preferences.
 */
const DEFAULT_PREFERENCES: UserPreferences = {
  optimizationLevel: 2,
  verbosity: 'normal',
  autoOptimize: true,
  confirmThreshold: 0.7,
  preferredDomains: [],
  stylePreferences: {
    codeStyle: 'concise',
    explanationDepth: 'medium',
    formatPreference: 'markdown',
  },
};

/**
 * User context provider.
 */
export class UserContextProvider {
  private preferences: UserPreferences;
  private patterns: Map<string, number> = new Map();
  private feedbackHistory: Array<{ type: 'positive' | 'negative'; category: string; timestamp: number }> = [];
  private usageCount: number = 0;

  constructor(initialPreferences: Partial<UserPreferences> = {}) {
    this.preferences = {
      ...DEFAULT_PREFERENCES,
      ...initialPreferences,
      stylePreferences: {
        ...DEFAULT_PREFERENCES.stylePreferences,
        ...initialPreferences.stylePreferences,
      },
    };
  }

  /**
   * Get user context for assembly.
   */
  getContext(): UserContext {
    return {
      preferences: { ...this.preferences },
      frequentPatterns: this.getFrequentPatterns(),
      acceptanceRate: this.calculateAcceptanceRate(),
      expertiseLevel: this.inferExpertiseLevel(),
    };
  }

  /**
   * Update preferences.
   */
  updatePreferences(updates: Partial<UserPreferences>): void {
    this.preferences = {
      ...this.preferences,
      ...updates,
      stylePreferences: {
        ...this.preferences.stylePreferences,
        ...updates.stylePreferences,
      },
    };
  }

  /**
   * Get current preferences.
   */
  getPreferences(): UserPreferences {
    return { ...this.preferences };
  }

  /**
   * Record a usage pattern.
   */
  recordPattern(pattern: string): void {
    const count = this.patterns.get(pattern) ?? 0;
    this.patterns.set(pattern, count + 1);
    this.usageCount++;
  }

  /**
   * Get frequent patterns.
   */
  private getFrequentPatterns(): string[] {
    const sorted = Array.from(this.patterns.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    return sorted.map(([pattern]) => pattern);
  }

  /**
   * Record feedback.
   */
  recordFeedback(type: 'positive' | 'negative', category: string): void {
    this.feedbackHistory.push({
      type,
      category,
      timestamp: Date.now(),
    });

    // Keep only last 100 feedback entries
    if (this.feedbackHistory.length > 100) {
      this.feedbackHistory = this.feedbackHistory.slice(-100);
    }
  }

  /**
   * Calculate acceptance rate from feedback.
   */
  private calculateAcceptanceRate(): number {
    if (this.feedbackHistory.length === 0) {
      return 0.8; // Default acceptance rate
    }

    // Weight recent feedback more heavily
    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;

    let weightedPositive = 0;
    let totalWeight = 0;

    for (const feedback of this.feedbackHistory) {
      const ageInDays = (now - feedback.timestamp) / dayMs;
      const weight = Math.exp(-ageInDays / 7); // Decay over ~7 days

      totalWeight += weight;
      if (feedback.type === 'positive') {
        weightedPositive += weight;
      }
    }

    return totalWeight > 0 ? weightedPositive / totalWeight : 0.8;
  }

  /**
   * Infer expertise level from usage patterns.
   */
  private inferExpertiseLevel(): 'beginner' | 'intermediate' | 'expert' {
    // Based on usage count and pattern complexity
    if (this.usageCount < 10) {
      return 'beginner';
    }

    // Check for advanced patterns
    const advancedPatterns = [
      'refactor', 'optimize', 'architecture', 'design pattern',
      'performance', 'security', 'debugging', 'profiling',
    ];

    let advancedCount = 0;
    for (const [pattern, count] of this.patterns) {
      if (advancedPatterns.some((ap) => pattern.toLowerCase().includes(ap))) {
        advancedCount += count;
      }
    }

    if (advancedCount > this.usageCount * 0.3) {
      return 'expert';
    }

    if (this.usageCount > 50) {
      return 'intermediate';
    }

    return 'beginner';
  }

  /**
   * Get style preference for a specific context.
   */
  getStylePreference(context: 'code' | 'explanation' | 'format'): StylePreference[keyof StylePreference] {
    switch (context) {
      case 'code':
        return this.preferences.stylePreferences.codeStyle;
      case 'explanation':
        return this.preferences.stylePreferences.explanationDepth;
      case 'format':
        return this.preferences.stylePreferences.formatPreference;
      default:
        return 'medium';
    }
  }

  /**
   * Check if optimization should be auto-applied.
   */
  shouldAutoOptimize(confidence: number): boolean {
    return (
      this.preferences.autoOptimize &&
      confidence >= this.preferences.confirmThreshold
    );
  }

  /**
   * Get optimization level.
   */
  getOptimizationLevel(): 1 | 2 | 3 {
    return this.preferences.optimizationLevel;
  }

  /**
   * Export user context for persistence.
   */
  export(): {
    preferences: UserPreferences;
    patterns: Array<[string, number]>;
    feedbackHistory: Array<{ type: 'positive' | 'negative'; category: string; timestamp: number }>;
    usageCount: number;
  } {
    return {
      preferences: this.preferences,
      patterns: Array.from(this.patterns.entries()),
      feedbackHistory: this.feedbackHistory,
      usageCount: this.usageCount,
    };
  }

  /**
   * Import user context from persistence.
   */
  import(data: {
    preferences: UserPreferences;
    patterns: Array<[string, number]>;
    feedbackHistory: Array<{ type: 'positive' | 'negative'; category: string; timestamp: number }>;
    usageCount: number;
  }): void {
    this.preferences = {
      ...DEFAULT_PREFERENCES,
      ...data.preferences,
      stylePreferences: {
        ...DEFAULT_PREFERENCES.stylePreferences,
        ...data.preferences.stylePreferences,
      },
    };
    this.patterns = new Map(data.patterns);
    this.feedbackHistory = data.feedbackHistory;
    this.usageCount = data.usageCount;
  }

  /**
   * Reset to defaults.
   */
  reset(): void {
    this.preferences = { ...DEFAULT_PREFERENCES };
    this.patterns.clear();
    this.feedbackHistory = [];
    this.usageCount = 0;
  }
}

/**
 * Create a user context provider.
 */
export function createUserContextProvider(
  initialPreferences?: Partial<UserPreferences>
): UserContextProvider {
  return new UserContextProvider(initialPreferences);
}
