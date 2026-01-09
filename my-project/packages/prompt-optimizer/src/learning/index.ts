/**
 * Learning engine exports.
 */

export {
  PreferenceEngine,
  createPreferenceEngine,
  type PreferenceSignal,
  type LearnedPreferences,
} from './preference-engine.js';

export {
  PatternTracker,
  createPatternTracker,
  type PatternMatch,
  type UsagePatterns,
} from './pattern-tracker.js';

export {
  FeedbackProcessor,
  createFeedbackProcessor,
  type FeedbackType,
  type FeedbackInput,
  type FeedbackAnalysis,
  type FeedbackStats,
} from './feedback-processor.js';
