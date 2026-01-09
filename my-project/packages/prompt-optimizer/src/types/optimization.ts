/**
 * Optimization types for the prompt optimizer.
 * Maps to spec section 4: Multi-Pass Optimization Engine.
 */

import type { ClassificationResponse, Domain } from './classification.js';
import type { AssembledContext } from './context.js';

/** Types of changes made during optimization */
export type ChangeType =
  | 'ADD_CONTEXT'
  | 'CLARIFY'
  | 'RESTRUCTURE'
  | 'REMOVE_REDUNDANCY';

/** Optimization request input */
export interface OptimizationRequest {
  /** Original user prompt */
  original: string;
  /** Classification result */
  classification: ClassificationResponse;
  /** Assembled context */
  context: AssembledContext;
  /** Optimization configuration */
  config: OptimizationConfig;
}

/** Configuration for optimization */
export interface OptimizationConfig {
  /** Maximum number of passes (1-3) */
  maxPasses: 1 | 2 | 3;
  /** Target confidence to achieve */
  targetConfidence: number;
  /** Elements that must be preserved */
  preserveElements: string[];
  /** Domain-specific optimization enabled */
  domainOptimization: boolean;
}

/** Optimization response output */
export interface OptimizationResponse {
  /** Optimized prompt text */
  optimized: string;
  /** List of changes made */
  changes: Change[];
  /** Elements that were preserved */
  preservedElements: string[];
  /** Number of passes used */
  passesUsed: number;
  /** Final confidence score */
  confidence: number;
  /** Semantic similarity to original */
  intentSimilarity: number;
  /** Human-readable explanation */
  explanation: string;
  /** Tip for the user */
  tip: string;
  /** Total time taken in milliseconds */
  latencyMs: number;
}

/** A single change made during optimization */
export interface Change {
  /** Type of change */
  type: ChangeType;
  /** Original segment that was changed */
  originalSegment: string;
  /** New segment after change */
  newSegment: string;
  /** Reason for the change */
  reason: string;
}

/** Pass 1 (Initial Optimization) output */
export interface PassOneOutput {
  /** Optimized prompt */
  optimizedPrompt: string;
  /** Changes made in this pass */
  changesMade: Change[];
  /** Elements preserved */
  preservedElements: string[];
  /** Initial confidence score */
  initialConfidence: number;
  /** Time taken */
  latencyMs: number;
}

/** Pass 2 (Self-Critique) result */
export type CritiqueResult = 'ACCEPT' | 'REFINE' | 'REJECT';

/** Severity levels for issues */
export type Severity = 'HIGH' | 'MEDIUM' | 'LOW';

/** Issue found during critique */
export interface CritiqueIssue {
  /** Description of the issue */
  description: string;
  /** Severity level */
  severity: Severity;
}

/** Pass 2 (Self-Critique) output */
export interface PassTwoOutput {
  /** Critique result */
  critiqueResult: CritiqueResult;
  /** Intent preservation score */
  intentPreservationScore: number;
  /** Issues found */
  issuesFound: CritiqueIssue[];
  /** Refinements needed */
  refinementsNeeded: string[];
  /** Confidence adjustment */
  confidenceAdjustment: number;
  /** Time taken */
  latencyMs: number;
}

/** Pass 3 (Final Polish) output */
export interface PassThreeOutput {
  /** Final optimized prompt */
  finalOptimizedPrompt: string;
  /** Refinements that were applied */
  refinementsApplied: Array<{
    refinement: string;
    howApplied: string;
  }>;
  /** Final confidence score */
  finalConfidence: number;
  /** Explanation for user */
  explanationForUser: string;
  /** Optimization tip */
  optimizationTip: string;
  /** Time taken */
  latencyMs: number;
}

/** Domain-specific optimization template */
export interface DomainTemplate {
  /** Domain this template is for */
  domain: Domain;
  /** Elements to add if missing */
  addIfMissing: string[];
  /** Elements to always preserve */
  alwaysPreserve: string[];
  /** Special rules for this domain */
  specialRules: string[];
  /** Whether to preserve ambiguity (for creative) */
  preserveAmbiguity: boolean;
}

/** Segment status for partial optimization */
export type SegmentStatus = 'CLEAR' | 'NEEDS_OPTIMIZATION' | 'NEEDS_CLARIFICATION';

/** Segment type */
export type SegmentType = 'instruction' | 'context' | 'constraint' | 'question' | 'reference';

/** A segment of the prompt for partial optimization */
export interface PromptSegment {
  /** Original text of the segment */
  content: string;
  /** Status of the segment */
  status: SegmentStatus;
  /** Confidence score (0-1) */
  confidence: number;
  /** Type of segment */
  type: SegmentType;
  /** Index of the segment */
  index: number;
  /** Start index in original prompt */
  start: number;
  /** End index in original prompt */
  end: number;
  /** Optimized text (if VAGUE) */
  optimizedText?: string;
}
