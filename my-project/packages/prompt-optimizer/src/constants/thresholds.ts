/**
 * Confidence thresholds for the prompt optimizer.
 * Maps to spec sections 3, 5, and 8.
 */

/** Classification confidence thresholds */
export const CLASSIFICATION_THRESHOLDS = {
  /** Threshold for PASS_THROUGH (well-formed prompts) */
  PASS_THROUGH: 0.85,
  /** Threshold for DEBUG (troubleshooting requests) */
  DEBUG: 0.80,
  /** Threshold for OPTIMIZE (needs improvement) */
  OPTIMIZE: 0.75,
  /** Threshold for CLARIFY (needs clarification) */
  CLARIFY: 0.60,
} as const;

/** Intent verification thresholds */
export const VERIFICATION_THRESHOLDS = {
  /** High confidence - auto-send */
  HIGH: 0.90,
  /** Medium confidence - auto-send with logging */
  MEDIUM: 0.85,
  /** Low confidence - request user confirmation */
  LOW: 0.70,
  /** Rejected - fallback to CLARIFY */
  REJECTED: 0.70,
} as const;

/** Element preservation thresholds */
export const PRESERVATION_THRESHOLDS = {
  /** Minimum ratio for verified status */
  VERIFIED: 0.90,
  /** Minimum ratio for warn status */
  WARN: 0.80,
} as const;

/** Confidence scoring weights */
export const CONFIDENCE_WEIGHTS = {
  /** Weight for classification confidence */
  classification: 0.15,
  /** Weight for optimization confidence */
  optimization: 0.25,
  /** Weight for intent similarity (most important) */
  intent: 0.35,
  /** Weight for context reliability */
  context: 0.15,
  /** Weight for domain match confidence */
  domain: 0.10,
} as const;

/** Confidence penalties */
export const CONFIDENCE_PENALTIES = {
  /** Penalty for low intent similarity (<0.85) */
  lowIntentSimilarity: 0.8,
  /** Penalty for uncertain context (<0.70) */
  uncertainContext: 0.9,
} as const;

/** Confidence-based routing thresholds */
export const ROUTING_THRESHOLDS = {
  /** Auto-send, minimal logging */
  AUTO_HIGH: 0.90,
  /** Auto-send, show "Optimized ✓" indicator */
  AUTO_MEDIUM: 0.80,
  /** Show before/after, request confirmation */
  CONFIRM: 0.70,
  /** Offer optimization as suggestion */
  SUGGEST: 0.60,
  /** Fallback to CLARIFY mode */
  CLARIFY: 0.60,
} as const;

/** Token thresholds for complexity */
export const TOKEN_THRESHOLDS = {
  /** Maximum tokens for SIMPLE complexity */
  SIMPLE_MAX: 100,
  /** Maximum tokens for MODERATE complexity */
  MODERATE_MAX: 300,
  /** Threshold for auto-escalation to Sonnet */
  COMPLEX_ESCALATION: 200,
} as const;

/** Latency budgets in milliseconds */
export const LATENCY_BUDGETS = {
  /** Context assembly */
  CONTEXT_ASSEMBLY: 50,
  /** Classification */
  CLASSIFICATION: 100,
  /** Optimization per pass */
  OPTIMIZATION_PER_PASS: 200,
  /** Intent verification */
  INTENT_VERIFICATION: 100,
  /** Review gate */
  REVIEW_GATE: 50,
  /** Total for 1-pass */
  TOTAL_ONE_PASS: 500,
  /** Total for 3-pass */
  TOTAL_THREE_PASS: 900,
} as const;

/** Context token limits */
export const CONTEXT_LIMITS = {
  /** Max tokens for session context */
  SESSION: 2000,
  /** Max tokens for project context */
  PROJECT: 1000,
  /** Max tokens for user preferences */
  USER: 500,
  /** Max tokens for terminal context */
  TERMINAL: 500,
  /** Max total context tokens */
  TOTAL: 4000,
} as const;

/** Recovery detection thresholds */
export const RECOVERY_THRESHOLDS = {
  /** Undo within N seconds triggers detection */
  UNDO_SECONDS: 30,
  /** N+ --no-optimize triggers rate limiting */
  NO_OPTIMIZE_RATE_LIMIT: 3,
  /** Rejection count before pattern flagging */
  PATTERN_FLAG_COUNT: 5,
} as const;
