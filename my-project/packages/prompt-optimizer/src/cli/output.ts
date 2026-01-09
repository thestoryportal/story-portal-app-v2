/**
 * CLI output formatting for the prompt optimizer.
 */

import chalk from 'chalk';
import type { OptimizeResult } from '../core/optimizer.js';

/** Output options */
export interface OutputOptions {
  /** Quiet mode - minimal output */
  quiet?: boolean;
  /** Show explanation */
  explain?: boolean;
  /** Show confidence */
  showConfidence?: boolean;
  /** Show category */
  showCategory?: boolean;
  /** Show tips */
  showTips?: boolean;
}

/**
 * Format optimization result for display.
 */
export function formatResult(result: OptimizeResult, options: OutputOptions = {}): string {
  const lines: string[] = [];

  if (options.quiet) {
    // Just output the prompt
    return result.prompt;
  }

  // Header
  if (result.wasOptimized) {
    lines.push(chalk.green('✓ Optimized'));
  } else {
    lines.push(chalk.blue('→ Passed through'));
  }

  // Category and domain
  if (options.showCategory !== false) {
    let categoryLine = chalk.dim(`  Category: ${result.category}`);
    if (result.domain) {
      categoryLine += chalk.dim(` (${result.domain})`);
    }
    lines.push(categoryLine);
  }

  // Confidence
  if (options.showConfidence !== false) {
    const confidencePercent = (result.confidence * 100).toFixed(0);
    const confidenceColor = result.confidence >= 0.85
      ? chalk.green
      : result.confidence >= 0.7
        ? chalk.yellow
        : chalk.red;
    lines.push(chalk.dim('  Confidence: ') + confidenceColor(`${confidencePercent}%`));
  }

  // Latency
  lines.push(chalk.dim(`  Latency: ${result.latencyMs}ms`));

  lines.push('');

  // The prompt
  lines.push(chalk.bold('Prompt:'));
  lines.push(chalk.white(result.prompt));

  // Changes (if explain mode)
  if (options.explain && result.changes && result.changes.length > 0) {
    lines.push('');
    lines.push(chalk.bold('Changes made:'));
    for (const change of result.changes) {
      lines.push(chalk.dim(`  • ${change.type}: ${change.reason}`));
    }
  }

  // Explanation
  if (options.explain) {
    lines.push('');
    lines.push(chalk.bold('Explanation:'));
    lines.push(chalk.dim(`  ${result.explanation}`));
  }

  // Tip
  if (options.showTips !== false && result.tip) {
    lines.push('');
    lines.push(chalk.cyan(`💡 Tip: ${result.tip}`));
  }

  // Confirmation needed
  if (result.needsConfirmation) {
    lines.push('');
    lines.push(chalk.yellow('⚠ Review recommended before sending'));
  }

  return lines.join('\n');
}

/**
 * Format a diff between original and optimized prompts.
 */
export function formatDiff(original: string, optimized: string): string {
  const lines: string[] = [];

  lines.push(chalk.bold('Original:'));
  lines.push(chalk.red(`  ${original}`));
  lines.push('');
  lines.push(chalk.bold('Optimized:'));
  lines.push(chalk.green(`  ${optimized}`));

  return lines.join('\n');
}

/**
 * Format an error message.
 */
export function formatError(error: Error): string {
  return chalk.red(`Error: ${error.message}`);
}

/**
 * Format a confirmation prompt.
 */
export function formatConfirmation(original: string, optimized: string): string {
  const lines: string[] = [];

  lines.push(chalk.yellow('┌─ Optimization Review ─────────────────────────────────'));
  lines.push('│');
  lines.push(chalk.yellow('│ ') + chalk.bold('Original:'));
  lines.push(chalk.yellow('│ ') + chalk.dim(original));
  lines.push('│');
  lines.push(chalk.yellow('│ ') + chalk.bold('Optimized:'));
  lines.push(chalk.yellow('│ ') + chalk.white(optimized));
  lines.push('│');
  lines.push(chalk.yellow('└───────────────────────────────────────────────────────'));
  lines.push('');
  lines.push('Send optimized? ' + chalk.dim('[Y/n/e(dit)/o(riginal)]'));

  return lines.join('\n');
}

/**
 * Format statistics.
 */
export function formatStats(stats: {
  totalOptimizations: number;
  accepted: number;
  rejected: number;
  averageConfidence: number;
  averageLatency: number;
}): string {
  const lines: string[] = [];

  lines.push(chalk.bold('Session Statistics'));
  lines.push(chalk.dim('─'.repeat(40)));
  lines.push(`Total optimizations: ${stats.totalOptimizations}`);
  lines.push(`Accepted: ${chalk.green(stats.accepted.toString())}`);
  lines.push(`Rejected: ${chalk.red(stats.rejected.toString())}`);
  lines.push(`Average confidence: ${(stats.averageConfidence * 100).toFixed(0)}%`);
  lines.push(`Average latency: ${stats.averageLatency.toFixed(0)}ms`);

  return lines.join('\n');
}

/**
 * Create a spinner-like progress indicator.
 */
export function createProgressMessage(message: string): string {
  return chalk.dim(`⏳ ${message}...`);
}

/**
 * Format success message.
 */
export function formatSuccess(message: string): string {
  return chalk.green(`✓ ${message}`);
}

/**
 * Format warning message.
 */
export function formatWarning(message: string): string {
  return chalk.yellow(`⚠ ${message}`);
}

/**
 * Format info message.
 */
export function formatInfo(message: string): string {
  return chalk.blue(`ℹ ${message}`);
}
