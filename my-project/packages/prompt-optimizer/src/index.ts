/**
 * CLI Prompt Optimizer
 *
 * An intelligent pre-processing layer for Claude CLI prompts.
 * Classifies, optimizes, and enhances prompts to improve response quality.
 *
 * @packageDocumentation
 */

// Main optimizer
export { PromptOptimizer, createOptimizer } from './core/optimizer.js';
export type { OptimizeResult, OptimizeOptions } from './core/optimizer.js';

// Pipeline for advanced usage
export { Pipeline, createPipeline } from './core/pipeline.js';
export type { PipelineResult, PipelineOptions } from './core/pipeline.js';

// Session management
export { Session, createSession } from './core/session.js';
export type { OptimizationRecord, SessionState } from './core/session.js';

// Layers for customization
export { Classifier, createClassifier } from './layers/classifier.js';
export { IntentVerifier, createIntentVerifier } from './layers/intent-verifier.js';
export { ContextAssembler, createContextAssembler } from './layers/context-assembler.js';
export type { ContextAssemblerConfig } from './layers/context-assembler.js';
export { ReviewGate, createReviewGate } from './layers/review-gate.js';
export type { ReviewDecision, ReviewGateOptions } from './layers/review-gate.js';
export { FeedbackLayer, createFeedbackLayer } from './layers/feedback.js';
export type { FeedbackRequest, FeedbackResponse } from './layers/feedback.js';

// Optimization layers
export {
  PassOneOptimizer,
  createPassOneOptimizer,
  PassTwoOptimizer,
  createPassTwoOptimizer,
  PassThreeOptimizer,
  createPassThreeOptimizer,
  MultiPassOptimizer,
  createMultiPassOptimizer,
} from './layers/optimization/index.js';

// Domain templates
export {
  TemplateRegistry,
  createTemplateRegistry,
  BaseDomainTemplate,
  CodeTemplate,
  createCodeTemplate,
  WritingTemplate,
  createWritingTemplate,
  AnalysisTemplate,
  createAnalysisTemplate,
  CreativeTemplate,
  createCreativeTemplate,
  ResearchTemplate,
  createResearchTemplate,
} from './layers/optimization/templates/index.js';
export type {
  DomainTemplateConfig,
  EnhancementStrategy,
  IssuePattern,
} from './layers/optimization/templates/index.js';

// Context providers
export {
  SessionContextProvider,
  createSessionContextProvider,
  ProjectContextProvider,
  createProjectContextProvider,
  UserContextProvider,
  createUserContextProvider,
  TerminalContextProvider,
  createTerminalContextProvider,
} from './context/index.js';

// Storage
export {
  FileAdapter,
  createFileAdapter,
  getStorageDir,
  ensureStorageDir,
  DEFAULT_STORAGE_DIR,
  ProfileStore,
  createProfileStore,
  MetricsStore,
  createMetricsStore,
  CacheStore,
  createCacheStore,
} from './storage/index.js';
export type {
  FileAdapterOptions,
  CacheEntry,
  CacheStats,
  CacheStoreOptions,
} from './storage/index.js';

// Learning engine
export {
  PreferenceEngine,
  createPreferenceEngine,
  PatternTracker,
  createPatternTracker,
  FeedbackProcessor,
  createFeedbackProcessor,
} from './learning/index.js';
export type {
  PreferenceSignal,
  LearnedPreferences,
  PatternMatch,
  UsagePatterns,
  FeedbackType,
  FeedbackInput,
  FeedbackAnalysis,
  FeedbackStats,
} from './learning/index.js';

// Metrics system
export {
  MetricsCollector,
  createMetricsCollector,
  MetricsAggregator,
  createMetricsAggregator,
  MetricsReporter,
  createMetricsReporter,
} from './metrics/index.js';
export type {
  TimingContext,
  ClassificationResult,
  OptimizationResult,
  QualityResult,
  AggregationWindow,
  TrendDirection,
  TrendAnalysis,
  ComparisonResult,
  ReportFormat,
  ReportSection,
  Report,
} from './metrics/index.js';

// Recovery system
export {
  OptimizationHistory,
  createOptimizationHistory,
  Detector,
  createDetector,
  RollbackManager,
  createRollbackManager,
} from './recovery/index.js';
export type {
  OptimizationHistoryEntry,
  HistoryOptions,
  DetectionResult,
  DetectedIssue,
  IssueType,
  DetectionOptions,
  RollbackResult,
  ReoptimizeRequest,
  RollbackOptions,
} from './recovery/index.js';

// Utilities
export {
  TokenCounter,
  countTokens,
  truncateTokens,
  SegmentAnalyzer,
  createSegmentAnalyzer,
  calculateConfidence,
  getComplexityAdjustment,
  calculateChangeMagnitude,
  ElementExtractor,
  createElementExtractor,
} from './utils/index.js';
export type {
  SegmentAnalysis,
  ConfidenceFactors,
  ConfidenceResult,
  ExtractedElements,
} from './utils/index.js';

// API clients
export { AnthropicClient, createAnthropicClient } from './api/anthropic-client.js';

// Types
export type {
  // Classification
  Category,
  Domain,
  Complexity,
  ClassificationRequest,
  ClassificationResponse,
  ExpertiseLevel,

  // Optimization
  ChangeType,
  OptimizationRequest,
  OptimizationConfig,
  OptimizationResponse,
  Change,
  PassOneOutput,
  PassTwoOutput,
  PassThreeOutput,
  CritiqueResult,
  CritiqueIssue,
  Severity,

  // Context
  Message,
  SessionContext,
  ProjectContext,
  UserContext,
  UserPreferences,
  StylePreference,
  TerminalContext,
  AssembledContext,
  ContextInjection,

  // Profile
  UserProfile,
  DomainPreferences,
  StylePreferences,
  LearnedPatterns,
  PatternEntry,
  CustomRule,
  FeedbackEntry,
  ProfileStats,

  // Metrics
  MetricsEntry,
  LatencyMetrics,
  QualityMetrics,
  ClassificationMetrics,
  OptimizationMetrics,
  InteractionMetrics,
  MetricsSummary,
  TimeSeriesMetrics,
  TimeSeriesPoint,
  HealthStatus,
  MetricsExport,
  MetricsQuery,

  // Config
  OptimizerConfig,
  BehaviorConfig,
  LimitsConfig,
  ContextConfig,
  LearningConfig,
  DisplayConfig,
  MetricsConfig,
  ApiConfig,
  RuntimeOptions,

  // API
  VerificationRequest,
  VerificationResponse,
  VerificationStatus,
  OptimizerApiClient,
  ApiClientConfig,
} from './types/index.js';

// Errors
export { OptimizerApiError, RateLimitError } from './types/api.js';

// Constants (for customization)
export {
  DEFAULT_CONFIG,
  MODEL_CONFIG,
  CLASSIFICATION_THRESHOLDS,
  VERIFICATION_THRESHOLDS,
  ROUTING_THRESHOLDS,
} from './constants/index.js';
