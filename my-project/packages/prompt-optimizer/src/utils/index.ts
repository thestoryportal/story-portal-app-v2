/**
 * Utility exports for the prompt optimizer package.
 */

export {
  TokenCounter,
  countTokens,
  truncateTokens,
} from './token-counter.js';

export {
  SegmentAnalyzer,
  createSegmentAnalyzer,
} from './segment-analyzer.js';
export type { SegmentAnalysis } from './segment-analyzer.js';

export {
  calculateConfidence,
  getConfidenceLevel,
  getComplexityAdjustment,
  calculateChangeMagnitude,
  shouldAutoAccept,
  shouldReject,
  blendConfidences,
} from './confidence.js';
export type { ConfidenceFactors, ConfidenceResult } from './confidence.js';

export {
  ElementExtractor,
  createElementExtractor,
} from './element-extractor.js';
export type { ExtractedElements } from './element-extractor.js';
