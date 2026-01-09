/**
 * Pattern tracker for recognizing and learning usage patterns.
 */

import type { Domain, Category, PatternEntry } from '../types/index.js';
import { ProfileStore, createProfileStore } from '../storage/profile-store.js';

/**
 * Pattern match result.
 */
export interface PatternMatch {
  /** The matched pattern */
  pattern: string;
  /** Match confidence */
  confidence: number;
  /** Number of times seen */
  frequency: number;
  /** Contexts where pattern was seen */
  contexts: string[];
}

/**
 * Usage pattern statistics.
 */
export interface UsagePatterns {
  /** Most common phrases */
  topPhrases: PatternEntry[];
  /** Peak usage hours */
  peakHours: number[];
  /** Most used domains */
  topDomains: Array<{ domain: Domain; count: number }>;
  /** Most used categories */
  topCategories: Array<{ category: Category; count: number }>;
  /** Average session length */
  avgSessionLength: number;
  /** Average prompts per session */
  avgPromptsPerSession: number;
}

/**
 * Session tracking data.
 */
interface SessionData {
  startTime: number;
  promptCount: number;
  domains: Domain[];
  categories: Category[];
}

/**
 * Pattern tracker class.
 */
export class PatternTracker {
  private profileStore: ProfileStore;
  private sessionData: SessionData;
  private hourlyUsage: Map<number, number> = new Map();
  private domainUsage: Map<Domain, number> = new Map();
  private categoryUsage: Map<Category, number> = new Map();
  private phraseCache: Map<string, number> = new Map();

  constructor(profileStore?: ProfileStore) {
    this.profileStore = profileStore ?? createProfileStore();
    this.sessionData = {
      startTime: Date.now(),
      promptCount: 0,
      domains: [],
      categories: [],
    };
  }

  /**
   * Track a prompt usage.
   */
  track(
    prompt: string,
    category: Category,
    domain: Domain | null
  ): void {
    // Update session data
    this.sessionData.promptCount++;
    this.sessionData.categories.push(category);
    if (domain) {
      this.sessionData.domains.push(domain);
    }

    // Track hourly usage
    const hour = new Date().getHours();
    this.hourlyUsage.set(hour, (this.hourlyUsage.get(hour) ?? 0) + 1);

    // Track domain usage
    if (domain) {
      this.domainUsage.set(domain, (this.domainUsage.get(domain) ?? 0) + 1);
    }

    // Track category usage
    this.categoryUsage.set(category, (this.categoryUsage.get(category) ?? 0) + 1);

    // Extract and track patterns from prompt
    this.trackPatterns(prompt, category);
  }

  /**
   * Track patterns in a prompt.
   */
  private trackPatterns(prompt: string, context: string): void {
    const patterns = this.extractPatterns(prompt);

    for (const pattern of patterns) {
      // Update local cache
      this.phraseCache.set(pattern, (this.phraseCache.get(pattern) ?? 0) + 1);

      // Persist to profile if seen multiple times
      const count = this.phraseCache.get(pattern) ?? 0;
      if (count >= 3) {
        this.profileStore.learnPattern({
          pattern,
          count: 1,
          contexts: [context],
        });
      }
    }
  }

  /**
   * Extract patterns from prompt text.
   */
  private extractPatterns(prompt: string): string[] {
    const patterns: string[] = [];
    const normalizedPrompt = prompt.toLowerCase();

    // Common action phrases
    const actionPatterns = [
      /^(help me|can you|please|i need|i want|show me|explain|create|write|fix|debug|review)/,
      /(how do i|how can i|what is|why does|when should)/,
      /(step by step|in detail|briefly|concisely|thoroughly)/,
      /(with examples?|without examples?|including|excluding)/,
      /(in \w+ format|as a \w+|using \w+)/,
    ];

    for (const regex of actionPatterns) {
      const match = normalizedPrompt.match(regex);
      if (match) {
        patterns.push(match[0]);
      }
    }

    // Extract n-grams (2-3 words)
    const words = normalizedPrompt
      .split(/\s+/)
      .filter((w) => w.length > 2)
      .slice(0, 20); // Limit to first 20 words

    // Bigrams
    for (let i = 0; i < words.length - 1; i++) {
      const bigram = `${words[i]} ${words[i + 1]}`;
      if (this.isSignificantPhrase(bigram)) {
        patterns.push(bigram);
      }
    }

    // Trigrams
    for (let i = 0; i < words.length - 2; i++) {
      const trigram = `${words[i]} ${words[i + 1]} ${words[i + 2]}`;
      if (this.isSignificantPhrase(trigram)) {
        patterns.push(trigram);
      }
    }

    return patterns;
  }

  /**
   * Check if a phrase is significant (not just common words).
   */
  private isSignificantPhrase(phrase: string): boolean {
    const stopWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
      'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
      'this', 'that', 'these', 'those', 'it', 'its',
    ]);

    const words = phrase.split(' ');
    const significantWords = words.filter((w) => !stopWords.has(w));

    // At least half the words should be significant
    return significantWords.length >= words.length / 2;
  }

  /**
   * Find matching patterns in a prompt.
   */
  findMatches(prompt: string): PatternMatch[] {
    const commonPatterns = this.profileStore.getCommonPatterns(50);
    const matches: PatternMatch[] = [];
    const normalizedPrompt = prompt.toLowerCase();

    for (const entry of commonPatterns) {
      if (normalizedPrompt.includes(entry.pattern.toLowerCase())) {
        matches.push({
          pattern: entry.pattern,
          confidence: Math.min(1, entry.count / 10), // Cap at 1
          frequency: entry.count,
          contexts: entry.contexts,
        });
      }
    }

    // Sort by confidence
    matches.sort((a, b) => b.confidence - a.confidence);

    return matches;
  }

  /**
   * Get usage patterns.
   */
  getUsagePatterns(): UsagePatterns {
    // Get top phrases from profile
    const topPhrases = this.profileStore.getCommonPatterns(10);

    // Calculate peak hours
    const hourCounts: Array<[number, number]> = [];
    for (let h = 0; h < 24; h++) {
      hourCounts.push([h, this.hourlyUsage.get(h) ?? 0]);
    }
    hourCounts.sort((a, b) => b[1] - a[1]);
    const peakHours = hourCounts
      .filter(([_, count]) => count > 0)
      .slice(0, 3)
      .map(([hour]) => hour);

    // Get top domains
    const topDomains = Array.from(this.domainUsage.entries())
      .map(([domain, count]) => ({ domain, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Get top categories
    const topCategories = Array.from(this.categoryUsage.entries())
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count);

    // Calculate session stats
    const sessionDuration = Date.now() - this.sessionData.startTime;
    const avgSessionLength = sessionDuration / (1000 * 60); // minutes
    const avgPromptsPerSession = this.sessionData.promptCount;

    return {
      topPhrases,
      peakHours,
      topDomains,
      topCategories,
      avgSessionLength,
      avgPromptsPerSession,
    };
  }

  /**
   * Get pattern suggestions for a partial prompt.
   */
  getSuggestions(partialPrompt: string, limit: number = 5): string[] {
    const patterns = this.profileStore.getCommonPatterns(50);
    const normalizedPartial = partialPrompt.toLowerCase();
    const suggestions: Array<{ pattern: string; score: number }> = [];

    for (const entry of patterns) {
      const normalizedPattern = entry.pattern.toLowerCase();

      // Check if pattern could complete the prompt
      if (normalizedPattern.startsWith(normalizedPartial)) {
        suggestions.push({
          pattern: entry.pattern,
          score: entry.count,
        });
      }
    }

    // Sort by score and return
    suggestions.sort((a, b) => b.score - a.score);
    return suggestions.slice(0, limit).map((s) => s.pattern);
  }

  /**
   * Predict likely domain based on prompt start.
   */
  predictDomain(prompt: string): Domain | null {
    const normalizedPrompt = prompt.toLowerCase();

    // Domain keywords
    const domainKeywords: Record<Domain, string[]> = {
      CODE: ['code', 'function', 'bug', 'error', 'implement', 'class', 'method', 'api', 'database'],
      WRITING: ['write', 'draft', 'essay', 'article', 'blog', 'story', 'email', 'letter'],
      ANALYSIS: ['analyze', 'compare', 'evaluate', 'assess', 'review', 'examine', 'data'],
      CREATIVE: ['creative', 'story', 'poem', 'song', 'design', 'imagine', 'brainstorm'],
      RESEARCH: ['research', 'find', 'search', 'information', 'learn', 'study', 'sources'],
    };

    const scores: Partial<Record<Domain, number>> = {};

    for (const [domain, keywords] of Object.entries(domainKeywords)) {
      let score = 0;
      for (const keyword of keywords) {
        if (normalizedPrompt.includes(keyword)) {
          score++;
        }
      }
      if (score > 0) {
        scores[domain as Domain] = score;
      }
    }

    // Return domain with highest score
    let bestDomain: Domain | null = null;
    let bestScore = 0;

    for (const [domain, score] of Object.entries(scores)) {
      if (score > bestScore) {
        bestScore = score;
        bestDomain = domain as Domain;
      }
    }

    return bestDomain;
  }

  /**
   * Get session statistics.
   */
  getSessionStats(): SessionData & { durationMinutes: number } {
    const durationMinutes = (Date.now() - this.sessionData.startTime) / (1000 * 60);
    return {
      ...this.sessionData,
      durationMinutes,
    };
  }

  /**
   * Reset session tracking.
   */
  resetSession(): void {
    this.sessionData = {
      startTime: Date.now(),
      promptCount: 0,
      domains: [],
      categories: [],
    };
    this.hourlyUsage.clear();
    this.domainUsage.clear();
    this.categoryUsage.clear();
    this.phraseCache.clear();
  }
}

/**
 * Create a pattern tracker.
 */
export function createPatternTracker(profileStore?: ProfileStore): PatternTracker {
  return new PatternTracker(profileStore);
}
