/**
 * Classification types for the prompt optimizer.
 * Maps to spec section 3: Classification System.
 */

/** 4-way classification categories */
export type Category = 'PASS_THROUGH' | 'DEBUG' | 'OPTIMIZE' | 'CLARIFY';

/** Domain detection for specialized optimization */
export type Domain = 'CODE' | 'WRITING' | 'ANALYSIS' | 'CREATIVE' | 'RESEARCH';

/** Complexity assessment for pass count determination */
export type Complexity = 'SIMPLE' | 'MODERATE' | 'COMPLEX';

/** Classification request input */
export interface ClassificationRequest {
  /** The user's raw input prompt */
  input: string;
  /** Optional context for classification */
  context?: {
    sessionHistory?: string[];
    projectLanguage?: string;
    projectFramework?: string;
    recentFiles?: string[];
    expertiseLevel?: ExpertiseLevel;
  };
}

/** Classification response output */
export interface ClassificationResponse {
  /** Primary classification category */
  category: Category;
  /** Detected domain (null if unclear) */
  domain: Domain | null;
  /** Complexity assessment */
  complexity: Complexity;
  /** Classification confidence (0.0 - 1.0) */
  confidence: number;
  /** Reasoning for the classification */
  reasoning: string;
  /** Whether result was from cache */
  cacheHit: boolean;
  /** Time taken in milliseconds */
  latencyMs: number;
}

/** User expertise level for context */
export type ExpertiseLevel = 'beginner' | 'intermediate' | 'senior' | 'expert';

/** Classification criteria for PASS_THROUGH */
export interface PassThroughCriteria {
  wellFormedQuestion: boolean;
  sufficientContext: boolean;
  clearIntent: boolean;
  reasonableLength: boolean;
  noVaguePronouns: boolean;
  technicalTermsCorrect: boolean;
}

/** Classification criteria for DEBUG */
export interface DebugCriteria {
  containsErrorMessage: boolean;
  containsStackTrace: boolean;
  explicitTroubleshootingRequest: boolean;
  codeWithBrokenIndicator: boolean;
  performanceIssue: boolean;
  buildOrRuntimeError: boolean;
}

/** Classification criteria for OPTIMIZE */
export interface OptimizeCriteria {
  vagueLanguage: boolean;
  missingCriticalContext: boolean;
  ramblingStructure: boolean;
  ambiguousPronouns: boolean;
  implicitAssumptions: boolean;
  explicitOptimizationRequest: boolean;
}

/** Classification criteria for CLARIFY */
export interface ClarifyCriteria {
  cannotDetermineIntent: boolean;
  multipleConflictingInterpretations: boolean;
  unknownContextReferences: boolean;
  extremelyShortInput: boolean;
  dangerousOperationWithoutConfirmation: boolean;
}

/** Domain indicators for detection */
export interface DomainIndicators {
  code: {
    fileExtensions: string[];
    languageKeywords: string[];
    errorMessages: boolean;
    codeBlocks: boolean;
  };
  writing: {
    documentTypes: string[];
    toneWords: string[];
    audienceMentions: boolean;
  };
  analysis: {
    dataReferences: boolean;
    comparisonWords: string[];
    metricsRequests: boolean;
  };
  creative: {
    storyMentions: boolean;
    designMentions: boolean;
    brainstormMentions: boolean;
  };
  research: {
    learnMentions: boolean;
    explainMentions: boolean;
    compareMentions: boolean;
  };
}

/** Token count thresholds for complexity */
export interface ComplexityThresholds {
  simple: { max: number };
  moderate: { min: number; max: number };
  complex: { min: number };
}
