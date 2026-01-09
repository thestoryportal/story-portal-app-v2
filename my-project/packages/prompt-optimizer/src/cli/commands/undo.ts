/**
 * Undo command for rolling back optimizations.
 */

import { RollbackManager, createRollbackManager } from '../../recovery/index.js';
import { Output } from '../output.js';

/**
 * Undo command options.
 */
export interface UndoOptions {
  /** Specific entry ID to undo */
  id?: string;
  /** Show diff before undo */
  diff?: boolean;
  /** List undoable entries */
  list?: boolean;
  /** Show last optimization */
  showLast?: boolean;
  /** Force undo without confirmation */
  force?: boolean;
}

/**
 * Session ID for rollback manager.
 */
let currentSessionId = `session_${Date.now()}`;

/**
 * Set session ID for undo operations.
 */
export function setUndoSessionId(sessionId: string): void {
  currentSessionId = sessionId;
}

/**
 * Execute undo command.
 */
export async function undoCommand(options: UndoOptions = {}): Promise<void> {
  const output = new Output();
  const rollback = createRollbackManager(currentSessionId);

  try {
    // List undoable entries
    if (options.list) {
      listUndoable(output, rollback);
      return;
    }

    // Show last optimization
    if (options.showLast) {
      showLast(output, rollback);
      return;
    }

    // Show diff
    if (options.diff) {
      const id = options.id ?? rollback.getLastEntry()?.id;
      if (id) {
        showDiff(output, rollback, id);
      } else {
        output.error('No optimization to show diff for');
      }
      return;
    }

    // Perform undo
    if (options.id) {
      performUndo(output, rollback, options.id);
    } else {
      performUndoLast(output, rollback);
    }
  } catch (error) {
    output.error(`Undo failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * List undoable entries.
 */
function listUndoable(output: Output, rollback: RollbackManager): void {
  const entries = rollback.getUndoableEntries(10);

  if (entries.length === 0) {
    output.info('No optimizations available to undo');
    return;
  }

  output.header('Undoable Optimizations');
  output.newLine();

  for (const entry of entries) {
    const date = new Date(entry.timestamp).toLocaleString();
    const preview = entry.original.slice(0, 50).replace(/\n/g, ' ');

    output.info(`[${entry.id}] ${date}`);
    output.indent(`Category: ${entry.category}, Confidence: ${(entry.confidence * 100).toFixed(0)}%`);
    output.indent(`Original: "${preview}..."`);
    output.newLine();
  }
}

/**
 * Show last optimization.
 */
function showLast(output: Output, rollback: RollbackManager): void {
  const entry = rollback.getLastEntry();

  if (!entry) {
    output.info('No optimizations recorded');
    return;
  }

  output.header('Last Optimization');
  output.newLine();

  const date = new Date(entry.timestamp).toLocaleString();

  output.info(`ID: ${entry.id}`);
  output.info(`Time: ${date}`);
  output.info(`Category: ${entry.category}`);
  output.info(`Domain: ${entry.domain ?? 'Unknown'}`);
  output.info(`Confidence: ${(entry.confidence * 100).toFixed(1)}%`);
  output.info(`Rolled Back: ${entry.rolledBack ? 'Yes' : 'No'}`);
  output.newLine();

  output.info('Original:');
  output.indent(entry.original);
  output.newLine();

  output.info('Optimized:');
  output.indent(entry.optimized);
}

/**
 * Show diff for an entry.
 */
function showDiff(output: Output, rollback: RollbackManager, id: string): void {
  const diff = rollback.getDiff(id);

  if (!diff) {
    output.error(`Entry ${id} not found`);
    return;
  }

  output.header('Optimization Diff');
  output.newLine();

  output.info('Changes:');
  output.raw(diff.diff);
  output.newLine();

  output.info('Original:');
  output.indent(diff.original);
  output.newLine();

  output.info('Optimized:');
  output.indent(diff.optimized);
}

/**
 * Perform undo of a specific entry.
 */
function performUndo(output: Output, rollback: RollbackManager, id: string): void {
  const result = rollback.rollback(id);

  if (!result.success) {
    output.error(result.error ?? 'Undo failed');
    return;
  }

  output.success('Optimization rolled back');
  output.newLine();

  output.info('Restored prompt:');
  output.indent(result.restoredPrompt ?? '');
}

/**
 * Perform undo of last optimization.
 */
function performUndoLast(output: Output, rollback: RollbackManager): void {
  if (!rollback.canUndo()) {
    output.info('No optimizations available to undo');
    return;
  }

  const result = rollback.undoLast();

  if (!result.success) {
    output.error(result.error ?? 'Undo failed');
    return;
  }

  output.success('Last optimization rolled back');
  output.newLine();

  output.info('Restored prompt:');
  output.indent(result.restoredPrompt ?? '');
}

/**
 * Re-optimize command.
 */
export async function reoptimizeCommand(options: { id?: string } = {}): Promise<void> {
  const output = new Output();
  const rollback = createRollbackManager(currentSessionId);

  const id = options.id ?? rollback.getLastEntry()?.id;

  if (!id) {
    output.error('No optimization to re-optimize');
    return;
  }

  const original = rollback.getOriginalPrompt(id);

  if (!original) {
    output.error(`Entry ${id} not found`);
    return;
  }

  output.info('Original prompt for re-optimization:');
  output.indent(original);
  output.newLine();
  output.info('Use this prompt with the optimize command to re-optimize');
}

/**
 * Show original command.
 */
export async function showOriginalCommand(options: { id?: string } = {}): Promise<void> {
  const output = new Output();
  const rollback = createRollbackManager(currentSessionId);

  const id = options.id ?? rollback.getLastEntry()?.id;

  if (!id) {
    output.error('No optimization found');
    return;
  }

  const original = rollback.getOriginalPrompt(id);

  if (!original) {
    output.error(`Entry ${id} not found`);
    return;
  }

  output.raw(original);
}

/**
 * History command.
 */
export async function historyCommand(options: { limit?: number } = {}): Promise<void> {
  const output = new Output();
  const rollback = createRollbackManager(currentSessionId);
  const history = rollback.getHistory();

  const entries = history.getRecent(options.limit ?? 20);

  if (entries.length === 0) {
    output.info('No optimization history');
    return;
  }

  output.header(`Optimization History (${entries.length} entries)`);
  output.newLine();

  for (const entry of entries) {
    const date = new Date(entry.timestamp).toLocaleString();
    const status = entry.rolledBack
      ? '↩ Rolled Back'
      : entry.userAction === 'accept'
      ? '✓ Accepted'
      : entry.userAction === 'reject'
      ? '✗ Rejected'
      : entry.userAction === 'modify'
      ? '~ Modified'
      : '? Pending';

    const preview = entry.original.slice(0, 40).replace(/\n/g, ' ');

    output.info(`${date} - ${status}`);
    output.indent(`${entry.category} | ${(entry.confidence * 100).toFixed(0)}% confidence`);
    output.indent(`"${preview}..."`);
    output.newLine();
  }

  // Show stats
  const stats = rollback.getStats();
  output.info(`Total: ${stats.totalOptimizations} | Rolled back: ${stats.rolledBack} (${(stats.rollbackRate * 100).toFixed(1)}%)`);
}
