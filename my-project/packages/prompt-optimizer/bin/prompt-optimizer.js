#!/usr/bin/env node

/**
 * CLI binary entry point for the prompt optimizer.
 * This file bootstraps the CLI from the compiled output.
 */

import('../dist/cli/index.js').catch((error) => {
  console.error('Failed to load prompt-optimizer CLI:', error.message);
  console.error('Run "pnpm build" in the packages/prompt-optimizer directory first.');
  process.exit(1);
});
