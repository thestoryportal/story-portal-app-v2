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

  if (!args.quiet) {
    spinner.start();
  }

  try {
    // Create optimizer with appropriate configuration
    // Only include local config options that are actually set
    const localConfig = args.local ? {
      ...(args.localModel && { model: args.localModel }),
      ...(args.localUrl && { baseUrl: args.localUrl }),
    } : undefined;

    const optimizer = createOptimizer({
      useMock: args.mock,
      useLocal: args.local,
      localConfig,
    });

    // Run optimization
    const result = await optimizer.optimize(args.prompt, {
      level: args.level,
      force: args.optimize,
      skip: args.noOptimize,
    });

    if (!args.quiet) {
      spinner.stop();
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
