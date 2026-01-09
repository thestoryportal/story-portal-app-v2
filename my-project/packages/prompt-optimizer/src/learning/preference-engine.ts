/**
 * Preference engine for learning user preferences over time.
 * Uses Exponential Moving Average (EMA) for adaptive learning.
 */

import type {
  Domain,
  Category,
  StylePreferences,
} from '../types/index.js';
import { ProfileStore, createProfileStore } from '../storage/profile-store.js';

/**
 * Preference signals from optimization.
 */
export interface PreferenceSignal {
  /** Feedback type */
  type: 'accept' | 'reject' | 'modify';
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Modified version if applicable */
  modified?: string;
  /** Classification category */
  category: Category;
  /** Detected domain */
  domain: Domain | null;
  /** Confidence score */
  confidence: number;
  /** Time taken to decide (ms) */
  decisionTimeMs?: number;
  /** Optional comment */
  comment?: string;
}

/**
 * Learned preferences for optimization.
 */
export interface LearnedPreferences {
  /** Domain-specific confidence thresholds */
  confidenceThresholds: Record<Domain, number>;
  /** Domain-specific acceptance rates */
  acceptanceRates: Record<Domain, number>;
  /** Preferred style settings */
  style: StylePreferences;
  /** Should auto-accept high confidence */
  autoAcceptHighConfidence: boolean;
  /** Auto-accept confidence threshold */
  autoAcceptThreshold: number;
  /** Preferred verbosity */
  preferredVerbosity: 'concise' | 'balanced' | 'detailed';
}

/**
 * EMA smoothing factors (reserved for future use).
 */
const _EMA_ALPHA = {
  acceptance: 0.1, // Slower learning for acceptance patterns
  confidence: 0.2, // Faster adaptation for confidence
  timing: 0.15, // Moderate for timing patterns
};
void _EMA_ALPHA; // Prevent unused variable warning

/**
 * Preference engine class.
 */
export class PreferenceEngine {
  private profileStore: ProfileStore;
  private sessionPreferences: Map<string, number> = new Map();

  constructor(profileStore?: ProfileStore) {
    this.profileStore = profileStore ?? createProfileStore();
  }

  /**
   * Process a preference signal and learn from it.
   */
  learn(signal: PreferenceSignal): void {
    // Record feedback in profile
    this.profileStore.recordFeedback({
      original: signal.original,
      optimized: signal.optimized,
      type: signal.type,
      modified: signal.modified,
      category: signal.category,
      domain: signal.domain,
      confidence: signal.confidence,
      comment: signal.comment,
    });

    // Update patterns based on signal type
    if (signal.type === 'accept') {
      this.learnFromAcceptance(signal);
    } else if (signal.type === 'reject') {
      this.learnFromRejection(signal);
    } else if (signal.type === 'modify') {
      this.learnFromModification(signal);
    }

    // Update timing patterns
    if (signal.decisionTimeMs !== undefined) {
      this.updateTimingPattern(signal);
    }

    // Update prompt length patterns
    this.profileStore.updateAveragePromptLength(signal.original.length);
  }

  /**
   * Learn from an acceptance.
   */
  private learnFromAcceptance(signal: PreferenceSignal): void {
    // Update confidence acceptance threshold
    this.profileStore.updateAcceptanceConfidence(signal.confidence);

    // If high confidence was accepted, user trusts the system
    if (signal.confidence >= 0.85 && signal.domain) {
      this.adjustConfidenceThreshold(signal.domain, -0.02); // Lower threshold slightly
    }

    // Track patterns from accepted optimizations
    this.extractAndLearnPatterns(signal.optimized, signal.category);
  }

  /**
   * Learn from a rejection.
   */
  private learnFromRejection(signal: PreferenceSignal): void {
    // Rejections at confidence levels indicate threshold needs adjustment
    if (signal.domain) {
      this.adjustConfidenceThreshold(signal.domain, 0.05); // Raise threshold
    }

    // Track what was rejected to avoid similar patterns
    this.trackRejectionPattern(signal);
  }

  /**
   * Learn from a modification.
   */
  private learnFromModification(signal: PreferenceSignal): void {
    if (!signal.modified) return;

    // Analyze the modification to understand preference
    const changes = this.analyzeModification(signal.optimized, signal.modified);

    // Learn from the changes
    for (const change of changes) {
      if (change.type === 'added') {
        // User prefers more detail/content
        this.updateVerbosityPreference('detailed');
      } else if (change.type === 'removed') {
        // User prefers conciseness
        this.updateVerbosityPreference('concise');
      }
    }

    // Moderately adjust threshold
    if (signal.domain) {
      this.adjustConfidenceThreshold(signal.domain, 0.02);
    }
  }

  /**
   * Adjust confidence threshold for domain.
   */
  private adjustConfidenceThreshold(domain: Domain, delta: number): void {
    const current = this.profileStore.getDomainConfidenceThreshold(domain);
    const newThreshold = Math.max(0.5, Math.min(0.95, current + delta));
    this.profileStore.setDomainConfidenceThreshold(domain, newThreshold);
  }

  /**
   * Update verbosity preference using EMA.
   */
  private updateVerbosityPreference(
    tendency: 'concise' | 'balanced' | 'detailed'
  ): void {
    const key = `verbosity_${tendency}`;
    const current = this.sessionPreferences.get(key) ?? 0;
    this.sessionPreferences.set(key, current + 1);

    // After enough signals, update profile
    const total =
      (this.sessionPreferences.get('verbosity_concise') ?? 0) +
      (this.sessionPreferences.get('verbosity_balanced') ?? 0) +
      (this.sessionPreferences.get('verbosity_detailed') ?? 0);

    if (total >= 10) {
      const concise = this.sessionPreferences.get('verbosity_concise') ?? 0;
      const detailed = this.sessionPreferences.get('verbosity_detailed') ?? 0;

      let preferred: 'concise' | 'balanced' | 'detailed' = 'balanced';
      if (concise > detailed * 1.5) {
        preferred = 'concise';
      } else if (detailed > concise * 1.5) {
        preferred = 'detailed';
      }

      this.profileStore.updateStylePreferences({ verbosity: preferred });
    }
  }

  /**
   * Extract and learn patterns from text.
   */
  private extractAndLearnPatterns(text: string, context: string): void {
    // Extract common phrase patterns
    const patterns = this.extractPatterns(text);

    for (const pattern of patterns) {
      this.profileStore.learnPattern({
        pattern,
        count: 1,
        contexts: [context],
      });
    }
  }

  /**
   * Extract patterns from text.
   */
  private extractPatterns(text: string): string[] {
    const patterns: string[] = [];

    // Extract common structural patterns
    const structuralPatterns = [
      /^(please|can you|could you|help me|i need)/i,
      /(step[- ]by[- ]step|in detail|briefly|concisely)/i,
      /(with examples?|without examples?)/i,
      /(in \w+ format|as a \w+)/i,
    ];

    for (const regex of structuralPatterns) {
      const match = text.match(regex);
      if (match) {
        patterns.push(match[0].toLowerCase());
      }
    }

    return patterns;
  }

  /**
   * Track rejection patterns to avoid.
   */
  private trackRejectionPattern(signal: PreferenceSignal): void {
    // Track what types of optimizations get rejected
    const key = `rejection_${signal.category}_${signal.domain ?? 'unknown'}`;
    const current = this.sessionPreferences.get(key) ?? 0;
    this.sessionPreferences.set(key, current + 1);
  }

  /**
   * Update timing patterns.
   */
  private updateTimingPattern(signal: PreferenceSignal): void {
    // Quick decisions (< 2s) indicate confidence in the system
    // Slow decisions (> 10s) indicate uncertainty
    if (signal.decisionTimeMs! < 2000 && signal.type === 'accept') {
      // User quickly accepts - trusts the system
      this.sessionPreferences.set('quick_accepts', (this.sessionPreferences.get('quick_accepts') ?? 0) + 1);
    } else if (signal.decisionTimeMs! > 10000) {
      // User takes long to decide - needs more review
      this.sessionPreferences.set('slow_decisions', (this.sessionPreferences.get('slow_decisions') ?? 0) + 1);
    }
  }

  /**
   * Analyze modification to understand changes.
   */
  private analyzeModification(
    original: string,
    modified: string
  ): Array<{ type: 'added' | 'removed' | 'changed'; content: string }> {
    const changes: Array<{ type: 'added' | 'removed' | 'changed'; content: string }> = [];

    const originalWords = original.split(/\s+/);
    const modifiedWords = modified.split(/\s+/);

    // Simple diff analysis
    const originalSet = new Set(originalWords);
    const modifiedSet = new Set(modifiedWords);

    // Find removed words
    for (const word of originalWords) {
      if (!modifiedSet.has(word)) {
        changes.push({ type: 'removed', content: word });
      }
    }

    // Find added words
    for (const word of modifiedWords) {
      if (!originalSet.has(word)) {
        changes.push({ type: 'added', content: word });
      }
    }

    return changes;
  }

  /**
   * Get learned preferences for optimization.
   */
  getPreferences(): LearnedPreferences {
    const profile = this.profileStore.export();
    const stats = this.profileStore.getStats();

    // Determine auto-accept threshold based on acceptance patterns
    const avgConfidence = stats.avgAcceptanceConfidence;
    const acceptanceRate = stats.acceptanceRate;

    // Higher acceptance rate + higher average confidence = lower threshold needed
    const autoAcceptThreshold = Math.max(
      0.8,
      Math.min(0.95, 1 - acceptanceRate * 0.2 + (1 - avgConfidence) * 0.1)
    );

    // Determine if auto-accept should be enabled
    const quickAccepts = this.sessionPreferences.get('quick_accepts') ?? 0;
    const slowDecisions = this.sessionPreferences.get('slow_decisions') ?? 0;
    const autoAcceptHighConfidence = quickAccepts > slowDecisions * 2 && stats.totalOptimizations > 20;

    return {
      confidenceThresholds: profile.domainPreferences.confidenceThresholds as Record<Domain, number>,
      acceptanceRates: profile.domainPreferences.acceptanceRates as Record<Domain, number>,
      style: profile.stylePreferences,
      autoAcceptHighConfidence,
      autoAcceptThreshold,
      preferredVerbosity: profile.stylePreferences.verbosity,
    };
  }

  /**
   * Get confidence threshold for domain.
   */
  getConfidenceThreshold(domain: Domain): number {
    return this.profileStore.getDomainConfidenceThreshold(domain);
  }

  /**
   * Get acceptance rate for domain.
   */
  getAcceptanceRate(domain: Domain): number {
    return this.profileStore.getDomainAcceptanceRate(domain);
  }

  /**
   * Check if prompt should be auto-accepted based on learned preferences.
   */
  shouldAutoAccept(confidence: number, domain: Domain | null): boolean {
    const preferences = this.getPreferences();

    if (!preferences.autoAcceptHighConfidence) {
      return false;
    }

    // Check global threshold
    if (confidence < preferences.autoAcceptThreshold) {
      return false;
    }

    // Check domain-specific threshold if applicable
    if (domain) {
      const domainThreshold = this.getConfidenceThreshold(domain);
      if (confidence < domainThreshold) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get profile statistics.
   */
  getStats() {
    return this.profileStore.getStats();
  }

  /**
   * Reset learning.
   */
  reset(): void {
    this.profileStore.reset();
    this.sessionPreferences.clear();
  }
}

/**
 * Create a preference engine.
 */
export function createPreferenceEngine(profileStore?: ProfileStore): PreferenceEngine {
  return new PreferenceEngine(profileStore);
}
