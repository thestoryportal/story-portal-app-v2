/**
 * Metrics aggregator for computing statistics and trends.
 */

import type {
  MetricsSummary,
  MetricsQuery,
  TimeSeriesMetrics,
  HealthStatus,
  Category,
} from '../types/index.js';
import { MetricsStore, createMetricsStore } from '../storage/metrics-store.js';

/**
 * Aggregation window options.
 */
export type AggregationWindow = 'hour' | 'day' | 'week' | 'month' | 'all';

/**
 * Trend direction.
 */
export type TrendDirection = 'up' | 'down' | 'stable';

/**
 * Trend analysis result.
 */
export interface TrendAnalysis {
  metric: string;
  direction: TrendDirection;
  changePercent: number;
  currentValue: number;
  previousValue: number;
}

/**
 * Comparison result.
 */
export interface ComparisonResult {
  metric: string;
  currentPeriod: number;
  previousPeriod: number;
  change: number;
  changePercent: number;
}

/**
 * Metrics aggregator class.
 */
export class MetricsAggregator {
  private store: MetricsStore;

  constructor(store?: MetricsStore) {
    this.store = store ?? createMetricsStore();
  }

  /**
   * Get summary for a time window.
   */
  getSummary(window: AggregationWindow): MetricsSummary {
    const query = this.windowToQuery(window);
    return this.store.getSummary(query);
  }

  /**
   * Convert window to query.
   */
  private windowToQuery(window: AggregationWindow): MetricsQuery {
    const now = Date.now();

    switch (window) {
      case 'hour':
        return { startTime: now - 60 * 60 * 1000 };
      case 'day':
        return { startTime: now - 24 * 60 * 60 * 1000 };
      case 'week':
        return { startTime: now - 7 * 24 * 60 * 60 * 1000 };
      case 'month':
        return { startTime: now - 30 * 24 * 60 * 60 * 1000 };
      case 'all':
        return {};
    }
  }

  /**
   * Get time series for a metric.
   */
  getTimeSeries(
    metric: string,
    interval: TimeSeriesMetrics['interval'],
    window: AggregationWindow
  ): TimeSeriesMetrics {
    const query = this.windowToQuery(window);
    return this.store.getTimeSeries(metric, interval, query);
  }

  /**
   * Analyze trends for key metrics.
   */
  analyzeTrends(window: AggregationWindow = 'week'): TrendAnalysis[] {
    const trends: TrendAnalysis[] = [];

    // Get current and previous periods
    const currentQuery = this.windowToQuery(window);
    const previousQuery = this.getPreviousPeriodQuery(window);

    const currentSummary = this.store.getSummary(currentQuery);
    const previousSummary = this.store.getSummary(previousQuery);

    // Analyze latency trend
    trends.push(
      this.calculateTrend(
        'latency',
        currentSummary.averages.latencyMs,
        previousSummary.averages.latencyMs,
        true // lower is better
      )
    );

    // Analyze confidence trend
    trends.push(
      this.calculateTrend(
        'confidence',
        currentSummary.averages.confidence,
        previousSummary.averages.confidence
      )
    );

    // Analyze acceptance rate trend
    trends.push(
      this.calculateTrend(
        'acceptance_rate',
        currentSummary.acceptanceRates.overall,
        previousSummary.acceptanceRates.overall
      )
    );

    // Analyze intent preservation trend
    trends.push(
      this.calculateTrend(
        'intent_preservation',
        currentSummary.averages.intentPreservation,
        previousSummary.averages.intentPreservation
      )
    );

    // Analyze error rate trend
    trends.push(
      this.calculateTrend(
        'error_rate',
        currentSummary.errorRates.total,
        previousSummary.errorRates.total,
        true // lower is better
      )
    );

    return trends;
  }

  /**
   * Get previous period query.
   */
  private getPreviousPeriodQuery(window: AggregationWindow): MetricsQuery {
    const now = Date.now();
    let periodMs: number;

    switch (window) {
      case 'hour':
        periodMs = 60 * 60 * 1000;
        break;
      case 'day':
        periodMs = 24 * 60 * 60 * 1000;
        break;
      case 'week':
        periodMs = 7 * 24 * 60 * 60 * 1000;
        break;
      case 'month':
        periodMs = 30 * 24 * 60 * 60 * 1000;
        break;
      case 'all':
        return {}; // No previous period for 'all'
    }

    return {
      startTime: now - 2 * periodMs,
      endTime: now - periodMs,
    };
  }

  /**
   * Calculate trend from current and previous values.
   */
  private calculateTrend(
    metric: string,
    currentValue: number,
    previousValue: number,
    lowerIsBetter: boolean = false
  ): TrendAnalysis {
    const changePercent =
      previousValue > 0
        ? ((currentValue - previousValue) / previousValue) * 100
        : currentValue > 0
        ? 100
        : 0;

    let direction: TrendDirection;
    if (Math.abs(changePercent) < 5) {
      direction = 'stable';
    } else if (lowerIsBetter) {
      direction = changePercent < 0 ? 'up' : 'down';
    } else {
      direction = changePercent > 0 ? 'up' : 'down';
    }

    return {
      metric,
      direction,
      changePercent,
      currentValue,
      previousValue,
    };
  }

  /**
   * Compare metrics between two periods.
   */
  compare(
    currentWindow: AggregationWindow,
    previousWindow: AggregationWindow
  ): ComparisonResult[] {
    const currentSummary = this.getSummary(currentWindow);
    const previousSummary = this.getSummary(previousWindow);

    const results: ComparisonResult[] = [];

    // Compare key metrics
    const metrics: Array<{
      name: string;
      current: number;
      previous: number;
    }> = [
      {
        name: 'total_count',
        current: currentSummary.totalCount,
        previous: previousSummary.totalCount,
      },
      {
        name: 'latency_ms',
        current: currentSummary.averages.latencyMs,
        previous: previousSummary.averages.latencyMs,
      },
      {
        name: 'confidence',
        current: currentSummary.averages.confidence,
        previous: previousSummary.averages.confidence,
      },
      {
        name: 'acceptance_rate',
        current: currentSummary.acceptanceRates.overall,
        previous: previousSummary.acceptanceRates.overall,
      },
      {
        name: 'passes_used',
        current: currentSummary.averages.passesUsed,
        previous: previousSummary.averages.passesUsed,
      },
    ];

    for (const { name, current, previous } of metrics) {
      const change = current - previous;
      const changePercent = previous > 0 ? (change / previous) * 100 : 0;

      results.push({
        metric: name,
        currentPeriod: current,
        previousPeriod: previous,
        change,
        changePercent,
      });
    }

    return results;
  }

  /**
   * Get health status.
   */
  getHealthStatus(): HealthStatus {
    const hourSummary = this.getSummary('hour');

    // Calculate error rate
    const errorRate = hourSummary.errorRates.total;

    // Calculate average latency
    const avgLatencyMs = hourSummary.averages.latencyMs;

    // Determine component statuses
    const apiStatus: 'up' | 'down' | 'degraded' =
      avgLatencyMs < 1000 ? 'up' : avgLatencyMs < 3000 ? 'degraded' : 'down';

    const cacheStatus: 'up' | 'down' | 'degraded' = 'up'; // Assume cache is always up

    const storageStatus: 'up' | 'down' | 'degraded' =
      this.store.getCount() > 0 ? 'up' : 'down';

    // Determine overall health
    let status: HealthStatus['status'] = 'healthy';
    if (apiStatus === 'down' || storageStatus === 'down' || errorRate > 0.3) {
      status = 'unhealthy';
    } else if (apiStatus === 'degraded' || errorRate > 0.1) {
      status = 'degraded';
    }

    // Calculate uptime (simplified - based on error rate)
    const uptimePercent = Math.max(0, (1 - errorRate) * 100);

    return {
      status,
      components: {
        api: apiStatus,
        cache: cacheStatus,
        storage: storageStatus,
      },
      errorRate,
      avgLatencyMs,
      uptimePercent,
      lastCheck: Date.now(),
    };
  }

  /**
   * Get top performing categories.
   */
  getTopCategories(
    window: AggregationWindow = 'week',
    metric: 'acceptance' | 'confidence' | 'speed' = 'acceptance'
  ): Array<{ category: Category; value: number }> {
    const summary = this.getSummary(window);
    const results: Array<{ category: Category; value: number }> = [];

    for (const category of ['PASS_THROUGH', 'DEBUG', 'OPTIMIZE', 'CLARIFY'] as Category[]) {
      let value: number;

      switch (metric) {
        case 'acceptance':
          value = summary.acceptanceRates.byCategory[category];
          break;
        case 'confidence':
          // Would need to calculate from entries
          value = summary.averages.confidence;
          break;
        case 'speed':
          // Would need to calculate from entries
          value = 1 / Math.max(1, summary.averages.latencyMs);
          break;
      }

      results.push({ category, value });
    }

    // Sort by value descending
    results.sort((a, b) => b.value - a.value);

    return results;
  }

  /**
   * Get performance percentiles.
   */
  getPercentiles(window: AggregationWindow = 'day'): {
    latency: { p50: number; p90: number; p95: number; p99: number };
    confidence: { p50: number; p90: number; p95: number; p99: number };
  } {
    const query = this.windowToQuery(window);
    const entries = this.store.query(query);

    const latencies = entries.map((e) => e.latency.totalMs).sort((a, b) => a - b);
    const confidences = entries.map((e) => e.quality.confidence).sort((a, b) => a - b);

    return {
      latency: {
        p50: this.percentile(latencies, 0.5),
        p90: this.percentile(latencies, 0.9),
        p95: this.percentile(latencies, 0.95),
        p99: this.percentile(latencies, 0.99),
      },
      confidence: {
        p50: this.percentile(confidences, 0.5),
        p90: this.percentile(confidences, 0.9),
        p95: this.percentile(confidences, 0.95),
        p99: this.percentile(confidences, 0.99),
      },
    };
  }

  /**
   * Calculate percentile.
   */
  private percentile(sorted: number[], p: number): number {
    if (sorted.length === 0) return 0;
    const index = Math.ceil(sorted.length * p) - 1;
    return sorted[Math.max(0, index)];
  }

  /**
   * Get optimization efficiency metrics.
   */
  getEfficiencyMetrics(window: AggregationWindow = 'week'): {
    avgOptimizationRatio: number;
    avgPassesUsed: number;
    avgChangesPerOptimization: number;
    cacheHitRate: number;
    contextUsageRate: number;
  } {
    const query = this.windowToQuery(window);
    const entries = this.store.query(query);

    if (entries.length === 0) {
      return {
        avgOptimizationRatio: 1,
        avgPassesUsed: 0,
        avgChangesPerOptimization: 0,
        cacheHitRate: 0,
        contextUsageRate: 0,
      };
    }

    const avgOptimizationRatio =
      entries.reduce((sum, e) => sum + e.quality.optimizationRatio, 0) /
      entries.length;

    const avgPassesUsed =
      entries.reduce((sum, e) => sum + e.quality.passesUsed, 0) / entries.length;

    const avgChangesPerOptimization =
      entries.reduce((sum, e) => sum + e.optimization.changesCount, 0) /
      entries.length;

    const cacheHits = entries.filter((e) => e.classification.cacheHit).length;
    const cacheHitRate = cacheHits / entries.length;

    const contextUsed = entries.filter((e) => e.optimization.contextInjected).length;
    const contextUsageRate = contextUsed / entries.length;

    return {
      avgOptimizationRatio,
      avgPassesUsed,
      avgChangesPerOptimization,
      cacheHitRate,
      contextUsageRate,
    };
  }

  /**
   * Get the underlying store.
   */
  getStore(): MetricsStore {
    return this.store;
  }
}

/**
 * Create a metrics aggregator.
 */
export function createMetricsAggregator(store?: MetricsStore): MetricsAggregator {
  return new MetricsAggregator(store);
}
