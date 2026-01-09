/**
 * Metrics reporter for generating reports and exports.
 */

import type {
  MetricsSummary,
  MetricsExport,
  HealthStatus,
} from '../types/index.js';
import { MetricsAggregator, createMetricsAggregator, type AggregationWindow, type TrendAnalysis } from './aggregator.js';

/**
 * Report format options.
 */
export type ReportFormat = 'text' | 'json' | 'markdown';

/**
 * Report section.
 */
export interface ReportSection {
  title: string;
  content: string;
}

/**
 * Generated report.
 */
export interface Report {
  title: string;
  generatedAt: number;
  period: string;
  sections: ReportSection[];
  rawData?: unknown;
}

/**
 * Metrics reporter class.
 */
export class MetricsReporter {
  private aggregator: MetricsAggregator;

  constructor(aggregator?: MetricsAggregator) {
    this.aggregator = aggregator ?? createMetricsAggregator();
  }

  /**
   * Generate a summary report.
   */
  generateSummaryReport(
    window: AggregationWindow = 'week',
    format: ReportFormat = 'text'
  ): Report {
    const summary = this.aggregator.getSummary(window);
    const trends = this.aggregator.analyzeTrends(window);
    const health = this.aggregator.getHealthStatus();

    const sections: ReportSection[] = [];

    // Overview section
    sections.push({
      title: 'Overview',
      content: this.formatOverview(summary, format),
    });

    // Performance section
    sections.push({
      title: 'Performance',
      content: this.formatPerformance(summary, format),
    });

    // Quality section
    sections.push({
      title: 'Quality',
      content: this.formatQuality(summary, format),
    });

    // Trends section
    sections.push({
      title: 'Trends',
      content: this.formatTrends(trends, format),
    });

    // Health section
    sections.push({
      title: 'Health',
      content: this.formatHealth(health, format),
    });

    return {
      title: `Optimizer Metrics Report - ${this.windowLabel(window)}`,
      generatedAt: Date.now(),
      period: this.windowLabel(window),
      sections,
      rawData: format === 'json' ? { summary, trends, health } : undefined,
    };
  }

  /**
   * Get window label.
   */
  private windowLabel(window: AggregationWindow): string {
    switch (window) {
      case 'hour':
        return 'Last Hour';
      case 'day':
        return 'Last 24 Hours';
      case 'week':
        return 'Last 7 Days';
      case 'month':
        return 'Last 30 Days';
      case 'all':
        return 'All Time';
    }
  }

  /**
   * Format overview section.
   */
  private formatOverview(summary: MetricsSummary, format: ReportFormat): string {
    const data = {
      totalOptimizations: summary.totalCount,
      acceptanceRate: (summary.acceptanceRates.overall * 100).toFixed(1) + '%',
      avgLatency: Math.round(summary.averages.latencyMs) + 'ms',
      avgConfidence: (summary.averages.confidence * 100).toFixed(1) + '%',
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }

    if (format === 'markdown') {
      return [
        `| Metric | Value |`,
        `|--------|-------|`,
        `| Total Optimizations | ${data.totalOptimizations} |`,
        `| Acceptance Rate | ${data.acceptanceRate} |`,
        `| Avg Latency | ${data.avgLatency} |`,
        `| Avg Confidence | ${data.avgConfidence} |`,
      ].join('\n');
    }

    return [
      `Total Optimizations: ${data.totalOptimizations}`,
      `Acceptance Rate: ${data.acceptanceRate}`,
      `Average Latency: ${data.avgLatency}`,
      `Average Confidence: ${data.avgConfidence}`,
    ].join('\n');
  }

  /**
   * Format performance section.
   */
  private formatPerformance(summary: MetricsSummary, format: ReportFormat): string {
    const data = {
      latencyP50: Math.round(summary.latencyPercentiles.p50) + 'ms',
      latencyP90: Math.round(summary.latencyPercentiles.p90) + 'ms',
      latencyP95: Math.round(summary.latencyPercentiles.p95) + 'ms',
      latencyP99: Math.round(summary.latencyPercentiles.p99) + 'ms',
      avgPasses: summary.averages.passesUsed.toFixed(1),
      avgChanges: summary.averages.changesCount.toFixed(1),
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }

    if (format === 'markdown') {
      return [
        `**Latency Percentiles:**`,
        `- P50: ${data.latencyP50}`,
        `- P90: ${data.latencyP90}`,
        `- P95: ${data.latencyP95}`,
        `- P99: ${data.latencyP99}`,
        ``,
        `**Optimization Stats:**`,
        `- Avg Passes: ${data.avgPasses}`,
        `- Avg Changes: ${data.avgChanges}`,
      ].join('\n');
    }

    return [
      'Latency Percentiles:',
      `  P50: ${data.latencyP50}`,
      `  P90: ${data.latencyP90}`,
      `  P95: ${data.latencyP95}`,
      `  P99: ${data.latencyP99}`,
      '',
      'Optimization Stats:',
      `  Avg Passes: ${data.avgPasses}`,
      `  Avg Changes: ${data.avgChanges}`,
    ].join('\n');
  }

  /**
   * Format quality section.
   */
  private formatQuality(summary: MetricsSummary, format: ReportFormat): string {
    const data = {
      intentPreservation: (summary.averages.intentPreservation * 100).toFixed(1) + '%',
      optimizationRatio: summary.averages.optimizationRatio.toFixed(2),
      acceptanceByConfidence: {
        low: (summary.acceptanceRates.byConfidenceRange.low * 100).toFixed(1) + '%',
        medium: (summary.acceptanceRates.byConfidenceRange.medium * 100).toFixed(1) + '%',
        high: (summary.acceptanceRates.byConfidenceRange.high * 100).toFixed(1) + '%',
      },
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }

    if (format === 'markdown') {
      return [
        `**Quality Metrics:**`,
        `- Intent Preservation: ${data.intentPreservation}`,
        `- Optimization Ratio: ${data.optimizationRatio}`,
        ``,
        `**Acceptance by Confidence:**`,
        `- Low (<70%): ${data.acceptanceByConfidence.low}`,
        `- Medium (70-85%): ${data.acceptanceByConfidence.medium}`,
        `- High (>85%): ${data.acceptanceByConfidence.high}`,
      ].join('\n');
    }

    return [
      'Quality Metrics:',
      `  Intent Preservation: ${data.intentPreservation}`,
      `  Optimization Ratio: ${data.optimizationRatio}`,
      '',
      'Acceptance by Confidence:',
      `  Low (<70%): ${data.acceptanceByConfidence.low}`,
      `  Medium (70-85%): ${data.acceptanceByConfidence.medium}`,
      `  High (>85%): ${data.acceptanceByConfidence.high}`,
    ].join('\n');
  }

  /**
   * Format trends section.
   */
  private formatTrends(trends: TrendAnalysis[], format: ReportFormat): string {
    if (format === 'json') {
      return JSON.stringify(trends, null, 2);
    }

    const formatTrend = (trend: TrendAnalysis): string => {
      const arrow =
        trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→';
      const change =
        Math.abs(trend.changePercent) < 0.1
          ? 'stable'
          : `${trend.changePercent > 0 ? '+' : ''}${trend.changePercent.toFixed(1)}%`;
      return `${trend.metric}: ${arrow} ${change}`;
    };

    if (format === 'markdown') {
      return [
        `| Metric | Trend | Change |`,
        `|--------|-------|--------|`,
        ...trends.map(
          (t) =>
            `| ${t.metric} | ${t.direction === 'up' ? '↑' : t.direction === 'down' ? '↓' : '→'} | ${t.changePercent.toFixed(1)}% |`
        ),
      ].join('\n');
    }

    return trends.map(formatTrend).join('\n');
  }

  /**
   * Format health section.
   */
  private formatHealth(health: HealthStatus, format: ReportFormat): string {
    if (format === 'json') {
      return JSON.stringify(health, null, 2);
    }

    const statusIcon =
      health.status === 'healthy'
        ? '✓'
        : health.status === 'degraded'
        ? '!'
        : '✗';

    const componentStatus = (status: 'up' | 'down' | 'degraded'): string => {
      switch (status) {
        case 'up':
          return '✓ Up';
        case 'down':
          return '✗ Down';
        case 'degraded':
          return '! Degraded';
      }
    };

    if (format === 'markdown') {
      return [
        `**Overall Status:** ${statusIcon} ${health.status.toUpperCase()}`,
        ``,
        `**Components:**`,
        `- API: ${componentStatus(health.components.api)}`,
        `- Cache: ${componentStatus(health.components.cache)}`,
        `- Storage: ${componentStatus(health.components.storage)}`,
        ``,
        `**Metrics:**`,
        `- Error Rate: ${(health.errorRate * 100).toFixed(2)}%`,
        `- Uptime: ${health.uptimePercent.toFixed(2)}%`,
      ].join('\n');
    }

    return [
      `Overall Status: ${statusIcon} ${health.status.toUpperCase()}`,
      '',
      'Components:',
      `  API: ${componentStatus(health.components.api)}`,
      `  Cache: ${componentStatus(health.components.cache)}`,
      `  Storage: ${componentStatus(health.components.storage)}`,
      '',
      'Metrics:',
      `  Error Rate: ${(health.errorRate * 100).toFixed(2)}%`,
      `  Uptime: ${health.uptimePercent.toFixed(2)}%`,
    ].join('\n');
  }

  /**
   * Generate a full export.
   */
  generateExport(window: AggregationWindow = 'all'): MetricsExport {
    return this.aggregator.getStore().export(this.aggregator['windowToQuery'](window));
  }

  /**
   * Generate a comparison report.
   */
  generateComparisonReport(
    currentWindow: AggregationWindow,
    previousWindow: AggregationWindow,
    format: ReportFormat = 'text'
  ): Report {
    const comparison = this.aggregator.compare(currentWindow, previousWindow);

    const sections: ReportSection[] = [];

    const content = comparison
      .map((c) => {
        const arrow = c.change > 0 ? '↑' : c.change < 0 ? '↓' : '→';
        const changeStr =
          Math.abs(c.changePercent) < 0.1
            ? 'No change'
            : `${c.change > 0 ? '+' : ''}${c.changePercent.toFixed(1)}%`;

        if (format === 'markdown') {
          return `| ${c.metric} | ${c.currentPeriod.toFixed(2)} | ${c.previousPeriod.toFixed(2)} | ${arrow} ${changeStr} |`;
        }

        return `${c.metric}: ${c.currentPeriod.toFixed(2)} vs ${c.previousPeriod.toFixed(2)} (${arrow} ${changeStr})`;
      })
      .join('\n');

    if (format === 'markdown') {
      sections.push({
        title: 'Comparison',
        content: [
          `| Metric | Current | Previous | Change |`,
          `|--------|---------|----------|--------|`,
          content,
        ].join('\n'),
      });
    } else {
      sections.push({
        title: 'Comparison',
        content,
      });
    }

    return {
      title: `Comparison: ${this.windowLabel(currentWindow)} vs ${this.windowLabel(previousWindow)}`,
      generatedAt: Date.now(),
      period: `${this.windowLabel(currentWindow)} vs ${this.windowLabel(previousWindow)}`,
      sections,
      rawData: format === 'json' ? comparison : undefined,
    };
  }

  /**
   * Render a report to string.
   */
  renderReport(report: Report, format: ReportFormat = 'text'): string {
    if (format === 'json') {
      return JSON.stringify(report, null, 2);
    }

    const lines: string[] = [];

    if (format === 'markdown') {
      lines.push(`# ${report.title}`);
      lines.push(`_Generated: ${new Date(report.generatedAt).toISOString()}_`);
      lines.push('');

      for (const section of report.sections) {
        lines.push(`## ${section.title}`);
        lines.push(section.content);
        lines.push('');
      }
    } else {
      lines.push('═'.repeat(60));
      lines.push(report.title);
      lines.push(`Generated: ${new Date(report.generatedAt).toISOString()}`);
      lines.push('═'.repeat(60));
      lines.push('');

      for (const section of report.sections) {
        lines.push(`── ${section.title} ${'─'.repeat(Math.max(0, 54 - section.title.length))}`);
        lines.push(section.content);
        lines.push('');
      }
    }

    return lines.join('\n');
  }

  /**
   * Get quick stats summary.
   */
  getQuickStats(window: AggregationWindow = 'day'): string {
    const summary = this.aggregator.getSummary(window);

    return [
      `${summary.totalCount} optimizations`,
      `${(summary.acceptanceRates.overall * 100).toFixed(0)}% accepted`,
      `${Math.round(summary.averages.latencyMs)}ms avg latency`,
      `${(summary.averages.confidence * 100).toFixed(0)}% avg confidence`,
    ].join(' | ');
  }

  /**
   * Get the aggregator.
   */
  getAggregator(): MetricsAggregator {
    return this.aggregator;
  }
}

/**
 * Create a metrics reporter.
 */
export function createMetricsReporter(aggregator?: MetricsAggregator): MetricsReporter {
  return new MetricsReporter(aggregator);
}
