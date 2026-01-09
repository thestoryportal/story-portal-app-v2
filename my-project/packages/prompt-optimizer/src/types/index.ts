/**
 * Type exports for the prompt optimizer package.
 */

// Classification types
export type {
  Category,
  Domain,
  Complexity,
  ClassificationRequest,
  ClassificationResponse,
  ExpertiseLevel,
  PassThroughCriteria,
  DebugCriteria,
  OptimizeCriteria,
  ClarifyCriteria,
  DomainIndicators,
  ComplexityThresholds,
} from './classification.js';

// Optimization types
export type {
  ChangeType,
  OptimizationRequest,
  OptimizationConfig,
  OptimizationResponse,
  Change,
  PassOneOutput,
  CritiqueResult,
  Severity,
  CritiqueIssue,
  PassTwoOutput,
  PassThreeOutput,
  DomainTemplate,
  SegmentStatus,
  SegmentType,
  PromptSegment,
} from './optimization.js';

// Context types
export type {
  Message,
  SessionContext,
  ConversationTurn,
  ReferencedEntity,
  ProjectContext,
  ProjectStructure,
  UserPreferences,
  StylePreference,
  UserContext,
  TerminalContext,
  GitStatus,
  AssembledContext,
  ContextInjection,
  ContextInjectionRules,
} from './context.js';

// Config types
export type {
  OptimizerConfig,
  BehaviorConfig,
  LimitsConfig,
  ContextConfig,
  LearningConfig,
  DisplayConfig,
  MetricsConfig,
  ApiConfig,
  CliArgs,
  RuntimeOptions,
} from './config.js';

// API types
export type {
  VerificationRequest,
  VerificationStatus,
  IssueType,
  IssueSeverity,
  VerificationIssue,
  VerificationResponse,
  OptimizerApiClient,
  ApiClientConfig,
  ModelSelection,
  ApiResponse,
} from './api.js';

export { OptimizerApiError, RateLimitError } from './api.js';

// Profile types
export type {
  UserProfile,
  DomainPreferences,
  StylePreferences,
  LearnedPatterns,
  PatternEntry,
  CustomRule,
  FeedbackEntry,
  ProfileStats,
  ProfileUpdate,
} from './profile.js';
export { DEFAULT_PROFILE } from './profile.js';

// Metrics types
export type {
  MetricsEntry,
  LatencyMetrics,
  QualityMetrics,
  ClassificationMetrics,
  OptimizationMetrics,
  InteractionMetrics,
  MetricsSummary,
  TimeSeriesPoint,
  TimeSeriesMetrics,
  HealthStatus,
  MetricsExport,
  MetricsQuery,
} from './metrics.js';
