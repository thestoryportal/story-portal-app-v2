/**
 * Profile storage for user preferences and learning.
 */

import type {
  UserProfile,
  FeedbackEntry,
  PatternEntry,
  ProfileStats,
  Domain,
} from '../types/index.js';
import { DEFAULT_PROFILE } from '../types/index.js';
import { FileAdapter, createFileAdapter } from './file-adapter.js';

/**
 * Maximum feedback history entries.
 */
const MAX_FEEDBACK_HISTORY = 1000;

/**
 * Maximum pattern entries.
 */
const MAX_PATTERNS = 500;

/**
 * Profile store class.
 */
export class ProfileStore {
  private adapter: FileAdapter<UserProfile>;
  private profile: UserProfile | null = null;

  constructor(filename: string = 'profile.json') {
    this.adapter = createFileAdapter<UserProfile>(filename);
  }

  /**
   * Load profile from storage.
   */
  load(): UserProfile {
    if (this.profile) {
      return this.profile;
    }

    const stored = this.adapter.read();

    if (stored) {
      this.profile = stored;
    } else {
      this.profile = this.createNewProfile();
      this.save();
    }

    return this.profile;
  }

  /**
   * Save profile to storage.
   */
  save(): boolean {
    if (!this.profile) {
      return false;
    }

    this.profile.updatedAt = Date.now();
    return this.adapter.write(this.profile);
  }

  /**
   * Create a new profile with defaults.
   */
  private createNewProfile(): UserProfile {
    const now = Date.now();
    return {
      ...DEFAULT_PROFILE,
      id: `profile_${now}_${Math.random().toString(36).slice(2, 9)}`,
      createdAt: now,
      updatedAt: now,
    };
  }

  /**
   * Record feedback on an optimization.
   */
  recordFeedback(feedback: Omit<FeedbackEntry, 'id' | 'timestamp'>): void {
    const profile = this.load();

    const entry: FeedbackEntry = {
      ...feedback,
      id: `fb_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: Date.now(),
    };

    profile.feedbackHistory.push(entry);

    // Trim history if needed
    if (profile.feedbackHistory.length > MAX_FEEDBACK_HISTORY) {
      profile.feedbackHistory = profile.feedbackHistory.slice(-MAX_FEEDBACK_HISTORY);
    }

    // Update counters
    profile.totalOptimizations++;
    if (feedback.type === 'accept') {
      profile.acceptedOptimizations++;
    } else if (feedback.type === 'reject') {
      profile.rejectedOptimizations++;
    } else if (feedback.type === 'modify') {
      profile.modifiedOptimizations++;
    }

    // Update domain stats
    if (feedback.domain) {
      const domain = feedback.domain;
      profile.domainPreferences.usageCounts[domain] =
        (profile.domainPreferences.usageCounts[domain] ?? 0) + 1;

      // Update acceptance rate for domain
      const domainFeedback = profile.feedbackHistory.filter(
        (f) => f.domain === domain
      );
      const domainAccepted = domainFeedback.filter(
        (f) => f.type === 'accept'
      ).length;
      profile.domainPreferences.acceptanceRates[domain] =
        domainFeedback.length > 0 ? domainAccepted / domainFeedback.length : 0.8;
    }

    this.save();
  }

  /**
   * Learn a pattern from usage.
   */
  learnPattern(pattern: Omit<PatternEntry, 'lastSeen'>): void {
    const profile = this.load();

    // Check if pattern already exists
    const existing = profile.patterns.commonPhrases.find(
      (p) => p.pattern === pattern.pattern
    );

    if (existing) {
      existing.count += pattern.count;
      existing.lastSeen = Date.now();
      existing.contexts = [...new Set([...existing.contexts, ...pattern.contexts])].slice(0, 5);
    } else {
      profile.patterns.commonPhrases.push({
        ...pattern,
        lastSeen: Date.now(),
      });
    }

    // Trim patterns if needed
    if (profile.patterns.commonPhrases.length > MAX_PATTERNS) {
      // Keep most frequent patterns
      profile.patterns.commonPhrases.sort((a, b) => b.count - a.count);
      profile.patterns.commonPhrases = profile.patterns.commonPhrases.slice(0, MAX_PATTERNS);
    }

    this.save();
  }

  /**
   * Update average prompt length using EMA.
   */
  updateAveragePromptLength(length: number): void {
    const profile = this.load();
    const alpha = 0.1; // EMA smoothing factor

    if (profile.patterns.averagePromptLength === 0) {
      profile.patterns.averagePromptLength = length;
    } else {
      profile.patterns.averagePromptLength =
        alpha * length + (1 - alpha) * profile.patterns.averagePromptLength;
    }

    this.save();
  }

  /**
   * Update average acceptance confidence using EMA.
   */
  updateAcceptanceConfidence(confidence: number): void {
    const profile = this.load();
    const alpha = 0.1;

    profile.patterns.averageAcceptanceConfidence =
      alpha * confidence + (1 - alpha) * profile.patterns.averageAcceptanceConfidence;

    this.save();
  }

  /**
   * Get profile statistics.
   */
  getStats(): ProfileStats {
    const profile = this.load();

    // Calculate acceptance rate
    const total = profile.totalOptimizations || 1;
    const acceptanceRate = profile.acceptedOptimizations / total;
    const rejectionRate = profile.rejectedOptimizations / total;
    const modificationRate = profile.modifiedOptimizations / total;

    // Find top domain
    let topDomain: Domain | null = null;
    let maxUsage = 0;
    for (const [domain, count] of Object.entries(profile.domainPreferences.usageCounts)) {
      if (count > maxUsage) {
        maxUsage = count;
        topDomain = domain as Domain;
      }
    }

    // Calculate active days
    const feedbackDates = new Set(
      profile.feedbackHistory.map((f) =>
        new Date(f.timestamp).toDateString()
      )
    );
    const activeDays = feedbackDates.size;

    // Calculate average acceptance confidence
    const acceptedFeedback = profile.feedbackHistory.filter(
      (f) => f.type === 'accept'
    );
    const avgAcceptanceConfidence =
      acceptedFeedback.length > 0
        ? acceptedFeedback.reduce((sum, f) => sum + f.confidence, 0) /
          acceptedFeedback.length
        : 0.8;

    // Calculate average prompts per day
    const avgPromptsPerDay = activeDays > 0 ? total / activeDays : 0;

    return {
      acceptanceRate,
      rejectionRate,
      modificationRate,
      avgAcceptanceConfidence,
      topDomain,
      totalOptimizations: profile.totalOptimizations,
      activeDays,
      avgPromptsPerDay,
    };
  }

  /**
   * Get acceptance rate for a specific domain.
   */
  getDomainAcceptanceRate(domain: Domain): number {
    const profile = this.load();
    return profile.domainPreferences.acceptanceRates[domain] ?? 0.8;
  }

  /**
   * Get confidence threshold for a domain.
   */
  getDomainConfidenceThreshold(domain: Domain): number {
    const profile = this.load();
    return profile.domainPreferences.confidenceThresholds[domain] ?? 0.7;
  }

  /**
   * Set confidence threshold for a domain.
   */
  setDomainConfidenceThreshold(domain: Domain, threshold: number): void {
    const profile = this.load();
    profile.domainPreferences.confidenceThresholds[domain] = Math.max(0, Math.min(1, threshold));
    this.save();
  }

  /**
   * Get recent feedback entries.
   */
  getRecentFeedback(limit: number = 10): FeedbackEntry[] {
    const profile = this.load();
    return profile.feedbackHistory.slice(-limit);
  }

  /**
   * Get common patterns.
   */
  getCommonPatterns(limit: number = 10): PatternEntry[] {
    const profile = this.load();
    return [...profile.patterns.commonPhrases]
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }

  /**
   * Update style preferences.
   */
  updateStylePreferences(preferences: Partial<UserProfile['stylePreferences']>): void {
    const profile = this.load();
    profile.stylePreferences = {
      ...profile.stylePreferences,
      ...preferences,
    };
    this.save();
  }

  /**
   * Reset profile to defaults.
   */
  reset(): void {
    this.profile = this.createNewProfile();
    this.save();
  }

  /**
   * Export profile.
   */
  export(): UserProfile {
    return { ...this.load() };
  }

  /**
   * Import profile.
   */
  import(profile: UserProfile): void {
    this.profile = profile;
    this.save();
  }
}

/**
 * Create a profile store.
 */
export function createProfileStore(filename?: string): ProfileStore {
  return new ProfileStore(filename);
}
