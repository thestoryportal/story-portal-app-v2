/**
 * Main optimize command for the CLI.
 */

import ora from 'ora';
import { createOptimizer, type OptimizeResult } from '../../core/optimizer.js';
import type { ParsedArgs } from '../args.js';
import {
  formatResult,
  formatDiff,
  formatError,
  formatConfirmation,
  formatSuccess,
} from '../output.js';

/**
 * Determine mode from environment variable and CLI flags.
 * CLI flags take precedence over environment variable.
 */
function resolveMode(args: ParsedArgs): { useMock: boolean; useLocal: boolean } {
  // CLI flags take precedence
  if (args.mock) {
    return { useMock: true, useLocal: false };
  }
  if (args.local) {
    return { useMock: false, useLocal: true };
  }

  // Check environment variable
  const envMode = process.env.PROMPT_OPTIMIZER_MODE?.toLowerCase();
  switch (envMode) {
    case 'mock':
      return { useMock: true, useLocal: false };
    case 'local':
      return { useMock: false, useLocal: true };
    case 'api':
    default:
      // Default to API mode (neither mock nor local)
      return { useMock: false, useLocal: false };
  }
}

/**
 * Execute the optimize command.
 */
export async function executeOptimize(args: ParsedArgs): Promise<void> {
  // Validate input
  if (!args.prompt) {
    console.log(formatError(new Error('No prompt provided. Usage: prompt-optimize "your prompt"')));
    process.exit(1);
  }

  const spinner = ora({
    text: 'Optimizing prompt...',
    spinner: 'dots',
  });

  // Don't show spinner for JSON output
  if (!args.quiet && !args.json) {
    spinner.start();
  }

  try {
    // Resolve mode from env var and CLI flags
    const { useMock, useLocal } = resolveMode(args);

    // Only include local config options that are actually set
    const localConfig = useLocal ? {
      ...(args.localModel && { model: args.localModel }),
      ...(args.localUrl && { baseUrl: args.localUrl }),
    } : undefined;

    const optimizer = createOptimizer({
      useMock,
      useLocal,
      localConfig,
    });

    // Run optimization
    const result = await optimizer.optimize(args.prompt, {
      level: args.level,
      force: args.optimize,
      skip: args.noOptimize,
      workflowMode: args.workflowMode,
    });

    if (!args.quiet && !args.json) {
      spinner.stop();
    }

    // JSON output mode - clean machine-readable output
    if (args.json) {
      const jsonOutput = {
        original: args.prompt,
        optimized: result.prompt,
        wasOptimized: result.wasOptimized,
        category: result.category,
        domain: result.domain,
        workflowMode: result.workflowMode.mode,
        workflowModeSource: result.workflowMode.source,
        confidence: result.confidence,
      };
      console.log(JSON.stringify(jsonOutput));
      return;
    }

    // Handle output based on mode
    if (args.confirm || result.needsConfirmation) {
      await handleConfirmation(args, result);
    } else {
      // Normal output
      const output = formatResult(result, {
        quiet: args.quiet,
        explain: args.explain,
        showConfidence: true,
        showCategory: true,
        showTips: !args.quiet,
      });
      console.log(output);
    }

    // Show diff if --show-original
    if (args.showOriginal && result.wasOptimized) {
      console.log('\n' + formatDiff(args.prompt, result.prompt));
    }
  } catch (error) {
    if (!args.quiet) {
      spinner.stop();
    }
    console.log(formatError(error as Error));
    process.exit(1);
  }
}

/**
 * Handle confirmation flow.
 */
async function handleConfirmation(args: ParsedArgs, result: OptimizeResult): Promise<void> {
  if (!result.wasOptimized) {
    // Nothing to confirm
    console.log(formatResult(result, { quiet: args.quiet }));
    return;
  }

  // Show confirmation dialog
  console.log(formatConfirmation(args.prompt!, result.prompt));

  // In a real implementation, we'd wait for user input here
  // For now, just output the result
  console.log('\n' + formatSuccess('Optimization ready. Use --auto to skip confirmation.'));
  console.log('\n' + formatResult(result, { quiet: true }));
}

/**
 * Execute undo command.
 */
export async function executeUndo(_args: ParsedArgs): Promise<void> {
  // TODO: Implement undo with history storage
  console.log(formatError(new Error('Undo not yet implemented. Coming in Phase 5.')));
}

/**
 * Execute reoptimize command.
 */
export async function executeReoptimize(args: ParsedArgs): Promise<void> {
  // TODO: Implement reoptimize with history storage
  console.log(formatError(new Error('Reoptimize not yet implemented. Coming in Phase 5.')));

  if (args.reoptimizeHint) {
    console.log(`Hint provided: ${args.reoptimizeHint}`);
  }
}

/**
 * Execute stats command.
 */
export async function executeStats(_args: ParsedArgs): Promise<void> {
  // TODO: Implement stats with metrics storage
  console.log(formatError(new Error('Stats not yet implemented. Coming in Phase 4.')));
}

/**
 * Execute feedback command.
 */
export async function executeFeedback(args: ParsedArgs): Promise<void> {
  // TODO: Implement feedback with learning engine
  if (args.feedback) {
    console.log(formatSuccess(`Feedback recorded: ${args.feedback}`));
    console.log('(Full feedback integration coming in Phase 4.)');
  }
}
