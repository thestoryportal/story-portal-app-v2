/**
 * Default configurations for the prompt optimizer.
 * Maps to spec section 12.2.
 */

import type { OptimizerConfig, ModelSelection } from '../types/index.js';

/** Default optimizer configuration */
export const DEFAULT_CONFIG: OptimizerConfig = {
  enabled: true,

  behavior: {
    defaultLevel: 2,
    autoEscalateComplex: true,
    confirmationThreshold: 0.75,
    alwaysConfirmPatterns: ['delete', 'remove', 'drop', 'destroy', 'truncate'],
    neverOptimizePatterns: ['^/', '^cd ', '^ls ', '^git ', '^npm ', '^pnpm ', '^yarn '],
  },

  limits: {
    maxPasses: 3,
    maxLatencyMs: 1500,
    maxTokenOverhead: 100,
    dailyOptimizationBudget: 10000,
  },

  context: {
    sessionHistoryTurns: 5,
    projectContextEnabled: true,
    terminalContextEnabled: true,
    maxContextTokens: 4000,
  },

  learning: {
    enabled: true,
    storeFeedback: true,
    personalizationLevel: 'moderate',
  },

  display: {
    showConfidence: true,
    showCategory: true,
    showExplanation: false,
    showTips: true,
  },

  metrics: {
    collectAnonymous: true,
    localStatsEnabled: true,
  },

  api: {
    provider: 'anthropic',
    timeout: 30000,
    retries: 2,
  },
};

/** Model selection configuration */
export const MODEL_CONFIG: ModelSelection = {
  /** Model for classification (fast) */
  classification: 'claude-3-haiku-20240307',
  /** Model for simple optimization (fast) */
  simpleOptimization: 'claude-3-haiku-20240307',
  /** Model for complex optimization (thorough) */
  complexOptimization: 'claude-3-5-sonnet-20241022',
  /** Model for intent verification (fast) */
  intentVerification: 'claude-3-haiku-20240307',
};

/** Model escalation thresholds */
export const MODEL_ESCALATION = {
  /** Escalate to Sonnet if confidence below this */
  confidenceThreshold: 0.8,
  /** Auto-use Sonnet for prompts with more tokens than this */
  tokenThreshold: 200,
} as const;

/** Default user profile */
export const DEFAULT_USER_PROFILE = {
  expertiseLevel: 'intermediate' as const,
  preferredVerbosity: 'balanced' as const,
  autoOptimize: true,
  confirmationThreshold: 0.75,
  explanationMode: false,
};

/** Default session configuration */
export const DEFAULT_SESSION = {
  maxTurns: 5,
  maxEntities: 20,
  expirationMs: 30 * 60 * 1000, // 30 minutes
};

/** File paths for configuration storage */
export const CONFIG_PATHS = {
  /** Global config file */
  globalConfig: '~/.claude/optimizer-config.json',
  /** User profile file */
  userProfile: '~/.claude/optimizer-profile.json',
  /** Session cache directory */
  sessionCache: '~/.claude/optimizer-cache/',
  /** Metrics storage */
  metricsStore: '~/.claude/optimizer-metrics.json',
  /** History storage */
  historyStore: '~/.claude/optimizer-history.json',
  /** Project-specific config */
  projectConfig: '.claude/optimizer.json',
} as const;

/** Retry configuration */
export const RETRY_CONFIG = {
  /** Maximum number of retries */
  maxRetries: 2,
  /** Initial delay in ms */
  initialDelayMs: 1000,
  /** Multiplier for exponential backoff */
  backoffMultiplier: 2,
  /** Maximum delay in ms */
  maxDelayMs: 10000,
} as const;

/** Cache configuration */
export const CACHE_CONFIG = {
  /** Maximum cache entries */
  maxEntries: 1000,
  /** Cache TTL in ms */
  ttlMs: 24 * 60 * 60 * 1000, // 24 hours
  /** Cache cleanup interval in ms */
  cleanupIntervalMs: 60 * 60 * 1000, // 1 hour
} as const;

/** Domain detection keywords */
export const DOMAIN_KEYWORDS = {
  code: {
    extensions: ['.ts', '.js', '.py', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php'],
    keywords: [
      'function', 'class', 'const', 'let', 'var', 'import', 'export', 'async', 'await',
      'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'throw', 'error', 'bug',
      'fix', 'debug', 'compile', 'build', 'test', 'deploy', 'api', 'endpoint', 'database',
    ],
    errorIndicators: ['error', 'exception', 'stack trace', 'failed', 'undefined', 'null'],
  },
  writing: {
    types: ['email', 'letter', 'article', 'blog', 'post', 'essay', 'report', 'document'],
    toneWords: ['formal', 'casual', 'professional', 'friendly', 'persuasive', 'informative'],
    formatWords: ['paragraph', 'bullet', 'list', 'section', 'heading'],
  },
  analysis: {
    dataWords: ['data', 'dataset', 'metrics', 'statistics', 'numbers', 'trends'],
    comparisonWords: ['compare', 'contrast', 'versus', 'vs', 'difference', 'similar'],
    outputWords: ['table', 'chart', 'graph', 'summary', 'report'],
  },
  creative: {
    storyWords: ['story', 'narrative', 'plot', 'character', 'scene', 'dialogue'],
    designWords: ['design', 'logo', 'brand', 'visual', 'aesthetic', 'style'],
    ideaWords: ['brainstorm', 'ideas', 'creative', 'imagine', 'concept', 'innovate'],
  },
  research: {
    learnWords: ['learn', 'understand', 'explain', 'teach', 'how does', 'what is'],
    exploreWords: ['explore', 'investigate', 'research', 'study', 'analyze'],
    compareWords: ['compare', 'pros and cons', 'advantages', 'disadvantages', 'tradeoffs'],
  },
} as const;

/** Dangerous operation patterns */
export const DANGEROUS_PATTERNS = [
  /\bdelete\b.*\b(all|everything|database|table|collection)\b/i,
  /\bdrop\b.*\b(table|database|collection|index)\b/i,
  /\btruncate\b/i,
  /\brm\s+-rf\b/i,
  /\bformat\b.*\b(disk|drive|partition)\b/i,
  /\bsudo\b/i,
  /--force/i,
  /--hard/i,
] as const;
