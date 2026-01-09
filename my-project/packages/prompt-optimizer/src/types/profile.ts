/**
 * Profile types for user preference tracking.
 * Maps to spec section 7 - User Preference Learning.
 */

import type { Domain } from './classification.js';

/**
 * User profile containing learned preferences.
 */
export interface UserProfile {
  /** Profile ID */
  id: string;
  /** Profile creation timestamp */
  createdAt: number;
  /** Last updated timestamp */
  updatedAt: number;
  /** Total number of optimizations */
  totalOptimizations: number;
  /** Number of accepted optimizations */
  acceptedOptimizations: number;
  /** Number of rejected optimizations */
  rejectedOptimizations: number;
  /** Number of modified optimizations */
  modifiedOptimizations: number;
  /** Domain preferences */
  domainPreferences: DomainPreferences;
  /** Style preferences */
  stylePreferences: StylePreferences;
  /** Learned patterns */
  patterns: LearnedPatterns;
  /** Custom rules defined by user */
  customRules: CustomRule[];
  /** Feedback history */
  feedbackHistory: FeedbackEntry[];
}

/**
 * Domain-specific preferences.
 */
export interface DomainPreferences {
  /** Preferred domains */
  preferred: Domain[];
  /** Domain-specific acceptance rates */
  acceptanceRates: Record<Domain, number>;
  /** Domain-specific confidence thresholds */
  confidenceThresholds: Record<Domain, number>;
  /** Domain usage counts */
  usageCounts: Record<Domain, number>;
}

/**
 * Style preferences for output.
 */
export interface StylePreferences {
  /** Preferred verbosity level */
  verbosity: 'concise' | 'balanced' | 'detailed';
  /** Preferred explanation style */
  explanationStyle: 'minimal' | 'standard' | 'thorough';
  /** Code style preference */
  codeStyle: 'terse' | 'commented' | 'documented';
  /** Whether to show tips */
  showTips: boolean;
  /** Whether to show confidence scores */
  showConfidence: boolean;
  /** Preferred output format */
  outputFormat: 'plain' | 'markdown' | 'structured';
}

/**
 * Learned usage patterns.
 */
export interface LearnedPatterns {
  /** Common phrase patterns */
  commonPhrases: PatternEntry[];
  /** Preferred terminology */
  preferredTerminology: Record<string, string>;
  /** Frequently used constraints */
  commonConstraints: string[];
  /** Peak usage hours */
  peakUsageHours: number[];
  /** Average prompt length */
  averagePromptLength: number;
  /** Average optimization acceptance confidence */
  averageAcceptanceConfidence: number;
}

/**
 * A learned pattern entry.
 */
export interface PatternEntry {
  /** The pattern */
  pattern: string;
  /** Occurrence count */
  count: number;
  /** Last seen timestamp */
  lastSeen: number;
  /** Context where pattern was used */
  contexts: string[];
}

/**
 * Custom rule defined by user.
 */
export interface CustomRule {
  /** Rule ID */
  id: string;
  /** Rule name */
  name: string;
  /** Rule condition (regex pattern or keyword) */
  condition: string;
  /** Action to take */
  action: 'always_optimize' | 'never_optimize' | 'always_review' | 'skip_context';
  /** Whether rule is enabled */
  enabled: boolean;
  /** Rule creation timestamp */
  createdAt: number;
}

/**
 * Feedback entry for learning.
 */
export interface FeedbackEntry {
  /** Feedback ID */
  id: string;
  /** Timestamp */
  timestamp: number;
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Feedback type */
  type: 'accept' | 'reject' | 'modify';
  /** Modified version if applicable */
  modified?: string;
  /** Classification category */
  category: string;
  /** Domain */
  domain: Domain | null;
  /** Confidence at feedback */
  confidence: number;
  /** Optional feedback comment */
  comment?: string;
}

/**
 * Profile statistics summary.
 */
export interface ProfileStats {
  /** Overall acceptance rate */
  acceptanceRate: number;
  /** Overall rejection rate */
  rejectionRate: number;
  /** Modification rate */
  modificationRate: number;
  /** Average confidence at acceptance */
  avgAcceptanceConfidence: number;
  /** Most used domain */
  topDomain: Domain | null;
  /** Total optimizations */
  totalOptimizations: number;
  /** Active days */
  activeDays: number;
  /** Average prompts per day */
  avgPromptsPerDay: number;
}

/**
 * Profile update operation.
 */
export interface ProfileUpdate {
  /** Fields to update */
  updates: Partial<UserProfile>;
  /** Feedback to record */
  feedback?: FeedbackEntry;
  /** Pattern to learn */
  pattern?: PatternEntry;
}

/**
 * Default profile values.
 */
export const DEFAULT_PROFILE: Omit<UserProfile, 'id' | 'createdAt' | 'updatedAt'> = {
  totalOptimizations: 0,
  acceptedOptimizations: 0,
  rejectedOptimizations: 0,
  modifiedOptimizations: 0,
  domainPreferences: {
    preferred: [],
    acceptanceRates: {} as Record<Domain, number>,
    confidenceThresholds: {} as Record<Domain, number>,
    usageCounts: {} as Record<Domain, number>,
  },
  stylePreferences: {
    verbosity: 'balanced',
    explanationStyle: 'standard',
    codeStyle: 'commented',
    showTips: true,
    showConfidence: true,
    outputFormat: 'markdown',
  },
  patterns: {
    commonPhrases: [],
    preferredTerminology: {},
    commonConstraints: [],
    peakUsageHours: [],
    averagePromptLength: 0,
    averageAcceptanceConfidence: 0.8,
  },
  customRules: [],
  feedbackHistory: [],
};
