/**
 * Stats command for displaying metrics and statistics.
 */

import { MetricsReporter, createMetricsReporter, type AggregationWindow } from '../../metrics/index.js';
import { Output } from '../output.js';

/**
 * Stats command options.
 */
export interface StatsOptions {
  /** Time window */
  window?: 'hour' | 'day' | 'week' | 'month' | 'all';
  /** Output format */
  format?: 'text' | 'json' | 'markdown';
  /** Show trends */
  trends?: boolean;
  /** Show health */
  health?: boolean;
  /** Compare with previous period */
  compare?: boolean;
  /** Export to file */
  export?: string;
}

/**
 * Execute stats command.
 */
export async function statsCommand(options: StatsOptions = {}): Promise<void> {
  const output = new Output();
  const reporter = createMetricsReporter();

  const window: AggregationWindow = options.window ?? 'week';
  const format = options.format ?? 'text';

  try {
    // Quick stats
    output.info(reporter.getQuickStats(window));
    output.newLine();

    // Full report
    if (options.trends || options.health || !options.compare) {
      const report = reporter.generateSummaryReport(window, format);
      const rendered = reporter.renderReport(report, format);
      output.raw(rendered);
    }

    // Comparison
    if (options.compare) {
      const previousWindow = getPreviousWindow(window);
      const comparison = reporter.generateComparisonReport(window, previousWindow, format);
      const rendered = reporter.renderReport(comparison, format);
      output.newLine();
      output.raw(rendered);
    }

    // Export
    if (options.export) {
      const exportData = reporter.generateExport(window);
      const jsonContent = JSON.stringify(exportData, null, 2);

      // Would write to file in real implementation
      output.success(`Export data generated (${jsonContent.length} bytes)`);
      if (format === 'json') {
        output.raw(jsonContent);
      }
    }
  } catch (error) {
    output.error(`Failed to generate stats: ${error instanceof Error ? error.message : 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Get previous window for comparison.
 */
function getPreviousWindow(window: AggregationWindow): AggregationWindow {
  switch (window) {
    case 'hour':
      return 'day';
    case 'day':
      return 'week';
    case 'week':
      return 'month';
    case 'month':
    case 'all':
      return 'all';
  }
}

/**
 * Show quick stats summary.
 */
export async function quickStatsCommand(): Promise<void> {
  const output = new Output();
  const reporter = createMetricsReporter();

  try {
    output.info(reporter.getQuickStats('day'));
  } catch (error) {
    output.error('Failed to get stats');
  }
}

/**
 * Show health status.
 */
export async function healthCommand(): Promise<void> {
  const output = new Output();
  const reporter = createMetricsReporter();

  try {
    const health = reporter.getAggregator().getHealthStatus();

    const statusIcon =
      health.status === 'healthy' ? '✓' : health.status === 'degraded' ? '!' : '✗';

    output.header(`System Health: ${statusIcon} ${health.status.toUpperCase()}`);
    output.newLine();

    output.info('Components:');
    output.indent(`API: ${health.components.api}`);
    output.indent(`Cache: ${health.components.cache}`);
    output.indent(`Storage: ${health.components.storage}`);
    output.newLine();

    output.info('Metrics:');
    output.indent(`Error Rate: ${(health.errorRate * 100).toFixed(2)}%`);
    output.indent(`Avg Latency: ${Math.round(health.avgLatencyMs)}ms`);
    output.indent(`Uptime: ${health.uptimePercent.toFixed(2)}%`);
  } catch (error) {
    output.error('Failed to get health status');
  }
}

/**
 * Show efficiency metrics.
 */
export async function efficiencyCommand(window: AggregationWindow = 'week'): Promise<void> {
  const output = new Output();
  const reporter = createMetricsReporter();

  try {
    const efficiency = reporter.getAggregator().getEfficiencyMetrics(window);

    output.header('Optimization Efficiency');
    output.newLine();

    output.info(`Avg Optimization Ratio: ${efficiency.avgOptimizationRatio.toFixed(2)}`);
    output.info(`Avg Passes Used: ${efficiency.avgPassesUsed.toFixed(1)}`);
    output.info(`Avg Changes/Optimization: ${efficiency.avgChangesPerOptimization.toFixed(1)}`);
    output.info(`Cache Hit Rate: ${(efficiency.cacheHitRate * 100).toFixed(1)}%`);
    output.info(`Context Usage Rate: ${(efficiency.contextUsageRate * 100).toFixed(1)}%`);
  } catch (error) {
    output.error('Failed to get efficiency metrics');
  }
}
