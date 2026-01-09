/**
 * Metrics types for performance and quality tracking.
 * Maps to spec section 8 - Metrics & Analytics.
 */

import type { Category, Domain, Complexity } from './classification.js';

/**
 * Metrics collection entry.
 */
export interface MetricsEntry {
  /** Entry ID */
  id: string;
  /** Timestamp */
  timestamp: number;
  /** Session ID */
  sessionId: string;
  /** Latency metrics */
  latency: LatencyMetrics;
  /** Quality metrics */
  quality: QualityMetrics;
  /** Classification metadata */
  classification: ClassificationMetrics;
  /** Optimization metadata */
  optimization: OptimizationMetrics;
  /** User interaction */
  interaction: InteractionMetrics;
}

/**
 * Latency metrics.
 */
export interface LatencyMetrics {
  /** Total end-to-end latency */
  totalMs: number;
  /** Classification latency */
  classificationMs: number;
  /** Optimization latency */
  optimizationMs: number;
  /** Verification latency */
  verificationMs: number;
  /** Context assembly latency */
  contextMs: number;
}

/**
 * Quality metrics.
 */
export interface QualityMetrics {
  /** Final confidence score */
  confidence: number;
  /** Intent preservation score */
  intentPreservation: number;
  /** Element preservation rate */
  elementPreservation: number;
  /** Optimization ratio (optimized length / original length) */
  optimizationRatio: number;
  /** Number of passes used */
  passesUsed: number;
}

/**
 * Classification metrics.
 */
export interface ClassificationMetrics {
  /** Classified category */
  category: Category;
  /** Detected domain */
  domain: Domain | null;
  /** Complexity level */
  complexity: Complexity;
  /** Classification confidence */
  confidence: number;
  /** Whether cache was hit */
  cacheHit: boolean;
}

/**
 * Optimization metrics.
 */
export interface OptimizationMetrics {
  /** Number of changes made */
  changesCount: number;
  /** Types of changes */
  changeTypes: string[];
  /** Original prompt length */
  originalLength: number;
  /** Optimized prompt length */
  optimizedLength: number;
  /** Was context injected */
  contextInjected: boolean;
  /** Was domain template used */
  templateUsed: string | null;
}

/**
 * User interaction metrics.
 */
export interface InteractionMetrics {
  /** User's action on optimization */
  action: 'accept' | 'reject' | 'modify' | 'skip' | null;
  /** Time to decision (ms) */
  decisionTimeMs: number | null;
  /** Was review required */
  reviewRequired: boolean;
  /** User provided feedback */
  feedbackProvided: boolean;
}

/**
 * Aggregated metrics summary.
 */
export interface MetricsSummary {
  /** Time period */
  period: {
    start: number;
    end: number;
  };
  /** Total count */
  totalCount: number;
  /** Category distribution */
  categoryDistribution: Record<Category, number>;
  /** Domain distribution */
  domainDistribution: Record<string, number>;
  /** Complexity distribution */
  complexityDistribution: Record<Complexity, number>;
  /** Average metrics */
  averages: {
    latencyMs: number;
    confidence: number;
    intentPreservation: number;
    optimizationRatio: number;
    passesUsed: number;
    changesCount: number;
    decisionTimeMs: number;
  };
  /** Percentiles for latency */
  latencyPercentiles: {
    p50: number;
    p90: number;
    p95: number;
    p99: number;
  };
  /** Acceptance rates */
  acceptanceRates: {
    overall: number;
    byCategory: Record<Category, number>;
    byDomain: Record<string, number>;
    byConfidenceRange: {
      low: number; // < 0.7
      medium: number; // 0.7 - 0.85
      high: number; // >= 0.85
    };
  };
  /** Error rates */
  errorRates: {
    total: number;
    byType: Record<string, number>;
  };
}

/**
 * Time series data point.
 */
export interface TimeSeriesPoint {
  /** Timestamp */
  timestamp: number;
  /** Value */
  value: number;
  /** Optional label */
  label?: string;
}

/**
 * Time series metrics.
 */
export interface TimeSeriesMetrics {
  /** Metric name */
  name: string;
  /** Data points */
  points: TimeSeriesPoint[];
  /** Aggregation interval */
  interval: 'hour' | 'day' | 'week' | 'month';
}

/**
 * Health status.
 */
export interface HealthStatus {
  /** Overall health */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Component statuses */
  components: {
    api: 'up' | 'down' | 'degraded';
    cache: 'up' | 'down' | 'degraded';
    storage: 'up' | 'down' | 'degraded';
  };
  /** Recent error rate */
  errorRate: number;
  /** Average latency */
  avgLatencyMs: number;
  /** Uptime percentage */
  uptimePercent: number;
  /** Last check timestamp */
  lastCheck: number;
}

/**
 * Metrics export format.
 */
export interface MetricsExport {
  /** Export timestamp */
  exportedAt: number;
  /** Export version */
  version: string;
  /** Summary data */
  summary: MetricsSummary;
  /** Raw entries (optional) */
  entries?: MetricsEntry[];
  /** Time series data (optional) */
  timeSeries?: TimeSeriesMetrics[];
}

/**
 * Metrics query options.
 */
export interface MetricsQuery {
  /** Start timestamp */
  startTime?: number;
  /** End timestamp */
  endTime?: number;
  /** Filter by category */
  category?: Category;
  /** Filter by domain */
  domain?: Domain;
  /** Filter by minimum confidence */
  minConfidence?: number;
  /** Limit results */
  limit?: number;
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
}
