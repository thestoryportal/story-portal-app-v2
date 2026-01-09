#!/usr/bin/env node
/**
 * CLI entry point for the prompt optimizer.
 */

import { parseArgs } from './args.js';
import {
  executeOptimize,
  executeUndo,
  executeReoptimize,
  executeStats,
  executeFeedback,
} from './commands/optimize.js';
import { formatError, formatInfo } from './output.js';

/**
 * Main CLI entry point.
 */
async function main(): Promise<void> {
  try {
    const args = parseArgs(process.argv);

    // Handle subcommands
    if (args.configAction) {
      await handleConfig(args);
      return;
    }

    if (args.profileAction) {
      await handleProfile(args);
      return;
    }

    // Handle recovery commands
    if (args.undo) {
      await executeUndo(args);
      return;
    }

    if (args.reoptimize) {
      await executeReoptimize(args);
      return;
    }

    // Handle stats
    if (args.stats) {
      await executeStats(args);
      return;
    }

    // Handle feedback
    if (args.feedback) {
      await executeFeedback(args);
      return;
    }

    // Default: optimize command
    await executeOptimize(args);
  } catch (error) {
    console.error(formatError(error as Error));
    process.exit(1);
  }
}

/**
 * Handle config subcommand.
 */
async function handleConfig(args: ReturnType<typeof parseArgs>): Promise<void> {
  switch (args.configAction) {
    case 'show':
      console.log(formatInfo('Current configuration:'));
      console.log('(Config management coming in Phase 5.)');
      break;
    case 'set':
      console.log(formatInfo(`Setting ${args.configKey} = ${args.configValue}`));
      console.log('(Config management coming in Phase 5.)');
      break;
    case 'reset':
      console.log(formatInfo('Resetting configuration to defaults.'));
      console.log('(Config management coming in Phase 5.)');
      break;
  }
}

/**
 * Handle profile subcommand.
 */
async function handleProfile(args: ReturnType<typeof parseArgs>): Promise<void> {
  switch (args.profileAction) {
    case 'show':
      console.log(formatInfo('Current profile:'));
      console.log('(Profile management coming in Phase 4.)');
      break;
    case 'export':
      console.log(formatInfo(`Exporting profile to ${args.profilePath}`));
      console.log('(Profile management coming in Phase 4.)');
      break;
    case 'import':
      console.log(formatInfo(`Importing profile from ${args.profilePath}`));
      console.log('(Profile management coming in Phase 4.)');
      break;
  }
}

// Run main
main().catch((error) => {
  console.error(formatError(error));
  process.exit(1);
});
