/**
 * Configuration types for the prompt optimizer.
 * Maps to spec section 12: Configuration System.
 */

/** Main optimizer configuration */
export interface OptimizerConfig {
  /** Whether optimization is enabled */
  enabled: boolean;

  /** Behavior settings */
  behavior: BehaviorConfig;

  /** Limits and budgets */
  limits: LimitsConfig;

  /** Context settings */
  context: ContextConfig;

  /** Learning settings */
  learning: LearningConfig;

  /** Display settings */
  display: DisplayConfig;

  /** Metrics settings */
  metrics: MetricsConfig;

  /** API settings */
  api: ApiConfig;
}

/** Behavior configuration */
export interface BehaviorConfig {
  /** Default optimization level (1-3) */
  defaultLevel: 1 | 2 | 3;
  /** Auto-escalate complex prompts to higher pass count */
  autoEscalateComplex: boolean;
  /** Confidence threshold for auto-confirmation */
  confirmationThreshold: number;
  /** Patterns that always require confirmation */
  alwaysConfirmPatterns: string[];
  /** Patterns that should never be optimized */
  neverOptimizePatterns: string[];
}

/** Limits configuration */
export interface LimitsConfig {
  /** Maximum number of optimization passes */
  maxPasses: number;
  /** Maximum latency in milliseconds */
  maxLatencyMs: number;
  /** Maximum token overhead added */
  maxTokenOverhead: number;
  /** Daily optimization budget */
  dailyOptimizationBudget: number;
}

/** Context configuration */
export interface ContextConfig {
  /** Number of session history turns to keep */
  sessionHistoryTurns: number;
  /** Whether to use project context */
  projectContextEnabled: boolean;
  /** Whether to use terminal context */
  terminalContextEnabled: boolean;
  /** Maximum tokens for all context */
  maxContextTokens: number;
}

/** Learning configuration */
export interface LearningConfig {
  /** Whether learning is enabled */
  enabled: boolean;
  /** Whether to store feedback */
  storeFeedback: boolean;
  /** Level of personalization */
  personalizationLevel: 'none' | 'minimal' | 'moderate' | 'aggressive';
}

/** Display configuration */
export interface DisplayConfig {
  /** Show confidence score in output */
  showConfidence: boolean;
  /** Show classification category */
  showCategory: boolean;
  /** Show detailed explanation */
  showExplanation: boolean;
  /** Show optimization tips */
  showTips: boolean;
}

/** Metrics configuration */
export interface MetricsConfig {
  /** Collect anonymous metrics */
  collectAnonymous: boolean;
  /** Enable local statistics */
  localStatsEnabled: boolean;
}

/** API configuration */
export interface ApiConfig {
  /** API provider to use */
  provider: 'anthropic' | 'agent-client';
  /** Anthropic API key (or from env) */
  anthropicApiKey?: string;
  /** Agent client base URL */
  agentClientBaseUrl?: string;
  /** Request timeout in milliseconds */
  timeout: number;
  /** Number of retries on failure */
  retries: number;
}

/** CLI arguments interface */
export interface CliArgs {
  /** Input prompt */
  prompt?: string;

  // Optimization control
  /** Skip optimization */
  noOptimize?: boolean;
  /** Force optimization */
  optimize?: boolean;
  /** Optimization level */
  optimizeLevel?: 1 | 2 | 3;

  // Confirmation
  /** Always confirm */
  confirm?: boolean;
  /** Never confirm */
  auto?: boolean;

  // Recovery
  /** Undo last optimization */
  undo?: boolean;
  /** Re-optimize with different approach */
  reoptimize?: boolean | string;
  /** Show original prompt */
  showOriginal?: boolean;

  // Display
  /** Show detailed explanation */
  explain?: boolean;
  /** Quiet mode */
  quiet?: boolean;

  // Other
  /** Show statistics */
  stats?: boolean;
  /** Provide feedback */
  feedback?: 'good' | 'bad';

  // Subcommands
  /** Subcommand */
  command?: 'config' | 'profile';
  /** Subcommand arguments */
  subArgs?: string[];
}

/** Runtime options passed to optimizer */
export interface RuntimeOptions {
  /** Override optimization level */
  level?: 1 | 2 | 3;
  /** Force confirmation */
  confirm?: boolean;
  /** Skip confirmation */
  auto?: boolean;
  /** Show explanation */
  explain?: boolean;
  /** Quiet mode */
  quiet?: boolean;
  /** Use mock API */
  useMock?: boolean;
}
