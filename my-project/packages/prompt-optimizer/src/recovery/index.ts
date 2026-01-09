/**
 * Recovery system exports.
 */

export {
  OptimizationHistory,
  createOptimizationHistory,
  type OptimizationHistoryEntry,
  type HistoryOptions,
} from './history.js';

export {
  Detector,
  createDetector,
  type DetectionResult,
  type DetectedIssue,
  type IssueType,
  type DetectionOptions,
} from './detection.js';

export {
  RollbackManager,
  createRollbackManager,
  type RollbackResult,
  type ReoptimizeRequest,
  type RollbackOptions,
} from './rollback.js';
