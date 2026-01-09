/**
 * Metrics system exports.
 */

export {
  MetricsCollector,
  createMetricsCollector,
  type TimingContext,
  type ClassificationResult,
  type OptimizationResult,
  type QualityResult,
} from './collector.js';

export {
  MetricsAggregator,
  createMetricsAggregator,
  type AggregationWindow,
  type TrendDirection,
  type TrendAnalysis,
  type ComparisonResult,
} from './aggregator.js';

export {
  MetricsReporter,
  createMetricsReporter,
  type ReportFormat,
  type ReportSection,
  type Report,
} from './reporter.js';
