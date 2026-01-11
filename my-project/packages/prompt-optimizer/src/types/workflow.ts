/**
 * Workflow mode types for intent-based optimization.
 * Workflow modes are orthogonal to domains - they represent the
 * user's intent/purpose rather than the content domain.
 */

/** Available workflow modes */
export type WorkflowMode =
  | 'SPECIFICATION'
  | 'FEEDBACK'
  | 'BUG_REPORT'
  | 'QUICK_TASK'
  | 'ARCHITECTURE'
  | 'EXPLORATION';

/** Workflow mode prefix triggers for explicit selection */
export const WORKFLOW_PREFIXES: Record<string, WorkflowMode> = {
  '!spec': 'SPECIFICATION',
  '!feedback': 'FEEDBACK',
  '!bug': 'BUG_REPORT',
  '!quick': 'QUICK_TASK',
  '!arch': 'ARCHITECTURE',
  '!explore': 'EXPLORATION',
};

/** How the workflow mode was detected */
export type WorkflowModeSource = 'prefix' | 'auto' | 'override' | 'default';

/** Workflow mode detection result */
export interface WorkflowModeDetection {
  /** Detected workflow mode */
  mode: WorkflowMode;
  /** How it was detected */
  source: WorkflowModeSource;
  /** Detection confidence (0.0 - 1.0) */
  confidence: number;
  /** Reasoning for detection */
  reasoning: string;
  /** Original prompt with prefix stripped (if applicable) */
  cleanedPrompt: string;
}

/** Section requirement for structured output */
export interface SectionRequirement {
  /** Section name/header */
  name: string;
  /** Whether required or optional */
  required: boolean;
  /** Prompt text to add if section missing */
  promptIfMissing: string;
  /** Detection pattern to check if already present */
  detectionPattern: RegExp;
}

/** Workflow mode configuration */
export interface WorkflowModeConfig {
  /** Mode identifier */
  mode: WorkflowMode;
  /** Human-readable description */
  description: string;
  /** Detection keywords/phrases */
  detectionKeywords: string[];
  /** Detection patterns (regex) */
  detectionPatterns: RegExp[];
  /** Sections to add/ensure in output */
  requiredSections: SectionRequirement[];
  /** Confidence weight adjustment (1.0 = no change) */
  confidenceWeightAdjustment: number;
  /** Whether minimal optimization is preferred */
  minimalOptimization: boolean;
  /** Maximum expansion ratio for this mode */
  maxExpansionRatio: number;
}

/** A structural change made by workflow mode */
export interface StructuralChange {
  /** Type of structural change */
  type: 'ADD_SECTION' | 'REORDER' | 'FORMAT' | 'STRIP_PREFIX';
  /** Description */
  description: string;
  /** Before text if applicable */
  before?: string;
  /** After text if applicable */
  after?: string;
}

/** Workflow mode transform result */
export interface WorkflowModeTransformResult {
  /** Transformed prompt */
  transformed: string;
  /** Sections added */
  sectionsAdded: string[];
  /** Structural changes made */
  structuralChanges: StructuralChange[];
  /** Final confidence adjustment */
  confidenceAdjustment: number;
}

/** Menu option for workflow mode selection */
export interface WorkflowModeMenuOption {
  /** Mode value */
  value: WorkflowMode;
  /** Display label */
  label: string;
  /** Short prefix trigger */
  prefix: string;
}

/** Workflow mode menu options for UI */
export const WORKFLOW_MODE_MENU: WorkflowModeMenuOption[] = [
  { value: 'SPECIFICATION', label: 'Specification - New feature/project details', prefix: '!spec' },
  { value: 'FEEDBACK', label: 'Feedback - Iterate on existing work', prefix: '!feedback' },
  { value: 'BUG_REPORT', label: 'Bug Report - Issue with repro steps', prefix: '!bug' },
  { value: 'QUICK_TASK', label: 'Quick Task - Simple action', prefix: '!quick' },
  { value: 'ARCHITECTURE', label: 'Architecture - Design decisions', prefix: '!arch' },
  { value: 'EXPLORATION', label: 'Exploration - Research/understand', prefix: '!explore' },
];
