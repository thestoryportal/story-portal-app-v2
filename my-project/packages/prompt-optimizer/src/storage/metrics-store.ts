/**
 * Metrics storage for performance and quality tracking.
 */

import type {
  MetricsEntry,
  MetricsSummary,
  MetricsQuery,
  MetricsExport,
  TimeSeriesMetrics,
  TimeSeriesPoint,
  Category,
  Complexity,
} from '../types/index.js';
import { FileAdapter, createFileAdapter } from './file-adapter.js';

/**
 * Maximum metrics entries to store.
 */
const MAX_ENTRIES = 10000;

/**
 * Stored metrics structure.
 */
interface StoredMetrics {
  version: string;
  entries: MetricsEntry[];
  lastCompacted: number;
}

/**
 * Metrics store class.
 */
export class MetricsStore {
  private adapter: FileAdapter<StoredMetrics>;
  private cache: StoredMetrics | null = null;
  private dirty = false;
  private flushTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(filename: string = 'metrics.json') {
    this.adapter = createFileAdapter<StoredMetrics>(filename);
  }

  /**
   * Load metrics from storage.
   */
  private load(): StoredMetrics {
    if (this.cache) {
      return this.cache;
    }

    const stored = this.adapter.read();

    if (stored) {
      this.cache = stored;
    } else {
      this.cache = {
        version: '1.0.0',
        entries: [],
        lastCompacted: Date.now(),
      };
      this.save();
    }

    return this.cache;
  }

  /**
   * Save metrics to storage.
   */
  private save(): boolean {
    if (!this.cache) {
      return false;
    }
    return this.adapter.write(this.cache);
  }

  /**
   * Schedule a flush to disk.
   */
  private scheduleFlush(): void {
    if (this.flushTimer) {
      return;
    }

    this.flushTimer = setTimeout(() => {
      if (this.dirty) {
        this.save();
        this.dirty = false;
      }
      this.flushTimer = null;
    }, 5000); // Flush every 5 seconds
  }

  /**
   * Record a metrics entry.
   */
  record(entry: MetricsEntry): void {
    const metrics = this.load();
    metrics.entries.push(entry);

    // Compact if needed
    if (metrics.entries.length > MAX_ENTRIES) {
      metrics.entries = metrics.entries.slice(-MAX_ENTRIES);
      metrics.lastCompacted = Date.now();
    }

    this.dirty = true;
    this.scheduleFlush();
  }

  /**
   * Query metrics.
   */
  query(options: MetricsQuery = {}): MetricsEntry[] {
    const metrics = this.load();
    let entries = [...metrics.entries];

    // Filter by time range
    if (options.startTime) {
      entries = entries.filter((e) => e.timestamp >= options.startTime!);
    }
    if (options.endTime) {
      entries = entries.filter((e) => e.timestamp <= options.endTime!);
    }

    // Filter by category
    if (options.category) {
      entries = entries.filter(
        (e) => e.classification.category === options.category
      );
    }

    // Filter by domain
    if (options.domain) {
      entries = entries.filter(
        (e) => e.classification.domain === options.domain
      );
    }

    // Filter by confidence
    if (options.minConfidence !== undefined) {
      entries = entries.filter(
        (e) => e.quality.confidence >= options.minConfidence!
      );
    }

    // Sort
    if (options.sortOrder === 'asc') {
      entries.sort((a, b) => a.timestamp - b.timestamp);
    } else {
      entries.sort((a, b) => b.timestamp - a.timestamp);
    }

    // Limit
    if (options.limit) {
      entries = entries.slice(0, options.limit);
    }

    return entries;
  }

  /**
   * Get summary statistics.
   */
  getSummary(options: MetricsQuery = {}): MetricsSummary {
    const entries = this.query(options);

    if (entries.length === 0) {
      return this.createEmptySummary();
    }

    // Calculate time period
    const timestamps = entries.map((e) => e.timestamp);
    const period = {
      start: Math.min(...timestamps),
      end: Math.max(...timestamps),
    };

    // Calculate distributions
    const categoryDistribution = this.calculateCategoryDistribution(entries);
    const domainDistribution = this.calculateDomainDistribution(entries);
    const complexityDistribution = this.calculateComplexityDistribution(entries);

    // Calculate averages
    const averages = this.calculateAverages(entries);

    // Calculate latency percentiles
    const latencyPercentiles = this.calculateLatencyPercentiles(entries);

    // Calculate acceptance rates
    const acceptanceRates = this.calculateAcceptanceRates(entries);

    // Calculate error rates
    const errorRates = this.calculateErrorRates(entries);

    return {
      period,
      totalCount: entries.length,
      categoryDistribution,
      domainDistribution,
      complexityDistribution,
      averages,
      latencyPercentiles,
      acceptanceRates,
      errorRates,
    };
  }

  /**
   * Create empty summary.
   */
  private createEmptySummary(): MetricsSummary {
    return {
      period: { start: Date.now(), end: Date.now() },
      totalCount: 0,
      categoryDistribution: {
        PASS_THROUGH: 0,
        DEBUG: 0,
        OPTIMIZE: 0,
        CLARIFY: 0,
      },
      domainDistribution: {},
      complexityDistribution: {
        SIMPLE: 0,
        MODERATE: 0,
        COMPLEX: 0,
      },
      averages: {
        latencyMs: 0,
        confidence: 0,
        intentPreservation: 0,
        optimizationRatio: 1,
        passesUsed: 0,
        changesCount: 0,
        decisionTimeMs: 0,
      },
      latencyPercentiles: {
        p50: 0,
        p90: 0,
        p95: 0,
        p99: 0,
      },
      acceptanceRates: {
        overall: 0,
        byCategory: {
          PASS_THROUGH: 0,
          DEBUG: 0,
          OPTIMIZE: 0,
          CLARIFY: 0,
        },
        byDomain: {},
        byConfidenceRange: {
          low: 0,
          medium: 0,
          high: 0,
        },
      },
      errorRates: {
        total: 0,
        byType: {},
      },
    };
  }

  /**
   * Calculate category distribution.
   */
  private calculateCategoryDistribution(
    entries: MetricsEntry[]
  ): Record<Category, number> {
    const dist: Record<Category, number> = {
      PASS_THROUGH: 0,
      DEBUG: 0,
      OPTIMIZE: 0,
      CLARIFY: 0,
    };

    for (const entry of entries) {
      dist[entry.classification.category]++;
    }

    return dist;
  }

  /**
   * Calculate domain distribution.
   */
  private calculateDomainDistribution(
    entries: MetricsEntry[]
  ): Record<string, number> {
    const dist: Record<string, number> = {};

    for (const entry of entries) {
      const domain = entry.classification.domain ?? 'unknown';
      dist[domain] = (dist[domain] ?? 0) + 1;
    }

    return dist;
  }

  /**
   * Calculate complexity distribution.
   */
  private calculateComplexityDistribution(
    entries: MetricsEntry[]
  ): Record<Complexity, number> {
    const dist: Record<Complexity, number> = {
      SIMPLE: 0,
      MODERATE: 0,
      COMPLEX: 0,
    };

    for (const entry of entries) {
      dist[entry.classification.complexity]++;
    }

    return dist;
  }

  /**
   * Calculate averages.
   */
  private calculateAverages(entries: MetricsEntry[]): MetricsSummary['averages'] {
    const count = entries.length;

    const latencyMs =
      entries.reduce((sum, e) => sum + e.latency.totalMs, 0) / count;
    const confidence =
      entries.reduce((sum, e) => sum + e.quality.confidence, 0) / count;
    const intentPreservation =
      entries.reduce((sum, e) => sum + e.quality.intentPreservation, 0) / count;
    const optimizationRatio =
      entries.reduce((sum, e) => sum + e.quality.optimizationRatio, 0) / count;
    const passesUsed =
      entries.reduce((sum, e) => sum + e.quality.passesUsed, 0) / count;
    const changesCount =
      entries.reduce((sum, e) => sum + e.optimization.changesCount, 0) / count;

    const decisionsWithTime = entries.filter(
      (e) => e.interaction.decisionTimeMs !== null
    );
    const decisionTimeMs =
      decisionsWithTime.length > 0
        ? decisionsWithTime.reduce(
            (sum, e) => sum + (e.interaction.decisionTimeMs ?? 0),
            0
          ) / decisionsWithTime.length
        : 0;

    return {
      latencyMs,
      confidence,
      intentPreservation,
      optimizationRatio,
      passesUsed,
      changesCount,
      decisionTimeMs,
    };
  }

  /**
   * Calculate latency percentiles.
   */
  private calculateLatencyPercentiles(
    entries: MetricsEntry[]
  ): MetricsSummary['latencyPercentiles'] {
    const latencies = entries.map((e) => e.latency.totalMs).sort((a, b) => a - b);

    return {
      p50: this.percentile(latencies, 0.5),
      p90: this.percentile(latencies, 0.9),
      p95: this.percentile(latencies, 0.95),
      p99: this.percentile(latencies, 0.99),
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
   * Calculate acceptance rates.
   */
  private calculateAcceptanceRates(
    entries: MetricsEntry[]
  ): MetricsSummary['acceptanceRates'] {
    const withAction = entries.filter((e) => e.interaction.action !== null);

    const calculateRate = (filtered: MetricsEntry[]): number => {
      const accepted = filtered.filter(
        (e) => e.interaction.action === 'accept'
      ).length;
      return filtered.length > 0 ? accepted / filtered.length : 0;
    };

    // Overall
    const overall = calculateRate(withAction);

    // By category
    const byCategory: Record<Category, number> = {
      PASS_THROUGH: 0,
      DEBUG: 0,
      OPTIMIZE: 0,
      CLARIFY: 0,
    };

    for (const category of ['PASS_THROUGH', 'DEBUG', 'OPTIMIZE', 'CLARIFY'] as Category[]) {
      const filtered = withAction.filter(
        (e) => e.classification.category === category
      );
      byCategory[category] = calculateRate(filtered);
    }

    // By domain
    const byDomain: Record<string, number> = {};
    const domains = new Set(
      entries.map((e) => e.classification.domain ?? 'unknown')
    );

    for (const domain of domains) {
      const filtered = withAction.filter(
        (e) => (e.classification.domain ?? 'unknown') === domain
      );
      byDomain[domain] = calculateRate(filtered);
    }

    // By confidence range
    const lowConfidence = withAction.filter((e) => e.quality.confidence < 0.7);
    const mediumConfidence = withAction.filter(
      (e) => e.quality.confidence >= 0.7 && e.quality.confidence < 0.85
    );
    const highConfidence = withAction.filter((e) => e.quality.confidence >= 0.85);

    const byConfidenceRange = {
      low: calculateRate(lowConfidence),
      medium: calculateRate(mediumConfidence),
      high: calculateRate(highConfidence),
    };

    return {
      overall,
      byCategory,
      byDomain,
      byConfidenceRange,
    };
  }

  /**
   * Calculate error rates.
   */
  private calculateErrorRates(
    entries: MetricsEntry[]
  ): MetricsSummary['errorRates'] {
    // Errors are entries with very low confidence or high latency
    const errors = entries.filter(
      (e) =>
        e.quality.confidence < 0.3 ||
        e.latency.totalMs > 10000 ||
        e.interaction.action === 'reject'
    );

    const byType: Record<string, number> = {};

    for (const error of errors) {
      if (error.quality.confidence < 0.3) {
        byType['low_confidence'] = (byType['low_confidence'] ?? 0) + 1;
      }
      if (error.latency.totalMs > 10000) {
        byType['timeout'] = (byType['timeout'] ?? 0) + 1;
      }
      if (error.interaction.action === 'reject') {
        byType['rejected'] = (byType['rejected'] ?? 0) + 1;
      }
    }

    return {
      total: entries.length > 0 ? errors.length / entries.length : 0,
      byType,
    };
  }

  /**
   * Get time series metrics.
   */
  getTimeSeries(
    metricName: string,
    interval: TimeSeriesMetrics['interval'],
    options: MetricsQuery = {}
  ): TimeSeriesMetrics {
    const entries = this.query(options);
    const points: TimeSeriesPoint[] = [];

    // Group by interval
    const groups = new Map<number, MetricsEntry[]>();

    for (const entry of entries) {
      const bucket = this.getBucket(entry.timestamp, interval);
      const existing = groups.get(bucket) ?? [];
      existing.push(entry);
      groups.set(bucket, existing);
    }

    // Calculate metric for each group
    for (const [timestamp, groupEntries] of groups) {
      const value = this.calculateMetricValue(metricName, groupEntries);
      points.push({ timestamp, value });
    }

    // Sort by timestamp
    points.sort((a, b) => a.timestamp - b.timestamp);

    return {
      name: metricName,
      points,
      interval,
    };
  }

  /**
   * Get time bucket for interval.
   */
  private getBucket(
    timestamp: number,
    interval: TimeSeriesMetrics['interval']
  ): number {
    const date = new Date(timestamp);

    switch (interval) {
      case 'hour':
        date.setMinutes(0, 0, 0);
        break;
      case 'day':
        date.setHours(0, 0, 0, 0);
        break;
      case 'week':
        date.setHours(0, 0, 0, 0);
        date.setDate(date.getDate() - date.getDay());
        break;
      case 'month':
        date.setHours(0, 0, 0, 0);
        date.setDate(1);
        break;
    }

    return date.getTime();
  }

  /**
   * Calculate metric value for a group.
   */
  private calculateMetricValue(
    metricName: string,
    entries: MetricsEntry[]
  ): number {
    if (entries.length === 0) return 0;

    switch (metricName) {
      case 'count':
        return entries.length;
      case 'latency':
        return (
          entries.reduce((sum, e) => sum + e.latency.totalMs, 0) / entries.length
        );
      case 'confidence':
        return (
          entries.reduce((sum, e) => sum + e.quality.confidence, 0) /
          entries.length
        );
      case 'acceptance_rate': {
        const withAction = entries.filter((e) => e.interaction.action !== null);
        const accepted = withAction.filter(
          (e) => e.interaction.action === 'accept'
        ).length;
        return withAction.length > 0 ? accepted / withAction.length : 0;
      }
      default:
        return 0;
    }
  }

  /**
   * Export metrics.
   */
  export(options: MetricsQuery = {}): MetricsExport {
    const entries = this.query(options);
    const summary = this.getSummary(options);

    return {
      exportedAt: Date.now(),
      version: '1.0.0',
      summary,
      entries,
    };
  }

  /**
   * Get entry count.
   */
  getCount(): number {
    return this.load().entries.length;
  }

  /**
   * Clear all metrics.
   */
  clear(): void {
    this.cache = {
      version: '1.0.0',
      entries: [],
      lastCompacted: Date.now(),
    };
    this.save();
  }

  /**
   * Force flush to disk.
   */
  flush(): void {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    if (this.dirty) {
      this.save();
      this.dirty = false;
    }
  }
}

/**
 * Create a metrics store.
 */
export function createMetricsStore(filename?: string): MetricsStore {
  return new MetricsStore(filename);
}
