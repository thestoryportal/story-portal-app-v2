/**
 * Rollback manager for undoing optimizations.
 */

import { OptimizationHistory, createOptimizationHistory, type OptimizationHistoryEntry } from './history.js';
import { Detector, createDetector, type DetectionResult } from './detection.js';

/**
 * Rollback result.
 */
export interface RollbackResult {
  /** Whether rollback was successful */
  success: boolean;
  /** Rolled back entry */
  entry: OptimizationHistoryEntry | null;
  /** Restored prompt */
  restoredPrompt: string | null;
  /** Error message if failed */
  error?: string;
}

/**
 * Re-optimization request.
 */
export interface ReoptimizeRequest {
  /** Entry to re-optimize */
  entry: OptimizationHistoryEntry;
  /** Use original prompt */
  useOriginal: boolean;
  /** Additional instructions */
  instructions?: string;
}

/**
 * Rollback options.
 */
export interface RollbackOptions {
  /** Auto-detect issues before rollback */
  autoDetect?: boolean;
  /** Confirm before rollback */
  requireConfirmation?: boolean;
}

/**
 * Rollback manager class.
 */
export class RollbackManager {
  private history: OptimizationHistory;
  private detector: Detector;

  constructor(
    sessionId: string,
    _options: RollbackOptions = {}
  ) {
    this.history = createOptimizationHistory(sessionId);
    this.detector = createDetector();
  }

  /**
   * Undo the last optimization.
   */
  undoLast(): RollbackResult {
    const lastEntry = this.history.getLast();

    if (!lastEntry) {
      return {
        success: false,
        entry: null,
        restoredPrompt: null,
        error: 'No optimizations to undo',
      };
    }

    if (lastEntry.rolledBack) {
      return {
        success: false,
        entry: lastEntry,
        restoredPrompt: null,
        error: 'Last optimization was already rolled back',
      };
    }

    return this.rollback(lastEntry.id);
  }

  /**
   * Undo a specific optimization by ID.
   */
  rollback(id: string): RollbackResult {
    const entry = this.history.get(id);

    if (!entry) {
      return {
        success: false,
        entry: null,
        restoredPrompt: null,
        error: `Optimization ${id} not found`,
      };
    }

    if (entry.rolledBack) {
      return {
        success: false,
        entry,
        restoredPrompt: null,
        error: 'This optimization was already rolled back',
      };
    }

    // Mark as rolled back
    this.history.markRolledBack(id);

    return {
      success: true,
      entry,
      restoredPrompt: entry.original,
    };
  }

  /**
   * Get rollback suggestion based on detection.
   */
  getSuggestion(
    original: string,
    optimized: string,
    confidence: number
  ): {
    shouldRollback: boolean;
    detection: DetectionResult;
    reason: string;
  } {
    const detection = this.detector.detect(original, optimized, [], confidence);

    let shouldRollback = false;
    let reason = '';

    if (detection.recommendation === 'rollback' || detection.recommendation === 'abort') {
      shouldRollback = true;
      reason = 'Optimization may have degraded prompt quality';
    } else if (detection.riskLevel === 'HIGH' && confidence < 0.7) {
      shouldRollback = true;
      reason = 'High risk with low confidence - rollback recommended';
    }

    if (detection.issues.length > 0) {
      const topIssues = detection.issues
        .filter((i) => i.severity !== 'warning')
        .slice(0, 2);

      if (topIssues.length > 0) {
        reason += `. Issues: ${topIssues.map((i) => i.description).join('; ')}`;
      }
    }

    return {
      shouldRollback,
      detection,
      reason,
    };
  }

  /**
   * Get entries available for rollback.
   */
  getUndoableEntries(limit: number = 10): OptimizationHistoryEntry[] {
    return this.history.getUndoable().slice(0, limit);
  }

  /**
   * Check if can undo.
   */
  canUndo(): boolean {
    const undoable = this.history.getUndoable();
    return undoable.length > 0;
  }

  /**
   * Get last entry.
   */
  getLastEntry(): OptimizationHistoryEntry | null {
    return this.history.getLast();
  }

  /**
   * Get original prompt for an entry.
   */
  getOriginalPrompt(id: string): string | null {
    const entry = this.history.get(id);
    return entry?.original ?? null;
  }

  /**
   * Get optimized prompt for an entry.
   */
  getOptimizedPrompt(id: string): string | null {
    const entry = this.history.get(id);
    return entry?.optimized ?? null;
  }

  /**
   * Record a new optimization.
   */
  recordOptimization(
    original: string,
    optimized: string,
    metadata: {
      category: OptimizationHistoryEntry['category'];
      domain: OptimizationHistoryEntry['domain'];
      complexity: OptimizationHistoryEntry['complexity'];
      confidence: number;
      changes: OptimizationHistoryEntry['changes'];
      passesUsed: number;
    }
  ): OptimizationHistoryEntry {
    return this.history.add({
      original,
      optimized,
      ...metadata,
    });
  }

  /**
   * Update user action for an entry.
   */
  recordUserAction(
    id: string,
    action: OptimizationHistoryEntry['userAction'],
    modified?: string
  ): void {
    this.history.updateAction(id, action, modified);
  }

  /**
   * Show diff between original and optimized.
   */
  getDiff(id: string): {
    original: string;
    optimized: string;
    diff: string;
  } | null {
    const entry = this.history.get(id);

    if (!entry) {
      return null;
    }

    // Simple diff representation
    const diff = this.generateSimpleDiff(entry.original, entry.optimized);

    return {
      original: entry.original,
      optimized: entry.optimized,
      diff,
    };
  }

  /**
   * Generate a simple diff.
   */
  private generateSimpleDiff(original: string, optimized: string): string {
    const lines: string[] = [];

    // Split into words for comparison
    const originalWords = original.split(/\s+/);
    const optimizedWords = optimized.split(/\s+/);

    const originalSet = new Set(originalWords);
    const optimizedSet = new Set(optimizedWords);

    // Find removed words
    const removed: string[] = [];
    for (const word of originalWords) {
      if (!optimizedSet.has(word)) {
        removed.push(word);
      }
    }

    // Find added words
    const added: string[] = [];
    for (const word of optimizedWords) {
      if (!originalSet.has(word)) {
        added.push(word);
      }
    }

    if (removed.length > 0) {
      lines.push(`- Removed: ${removed.slice(0, 10).join(', ')}${removed.length > 10 ? '...' : ''}`);
    }

    if (added.length > 0) {
      lines.push(`+ Added: ${added.slice(0, 10).join(', ')}${added.length > 10 ? '...' : ''}`);
    }

    // Length change
    const lengthChange = optimized.length - original.length;
    if (lengthChange !== 0) {
      lines.push(`Length: ${lengthChange > 0 ? '+' : ''}${lengthChange} chars`);
    }

    return lines.join('\n');
  }

  /**
   * Get rollback statistics.
   */
  getStats(): {
    totalOptimizations: number;
    rolledBack: number;
    rollbackRate: number;
    avgConfidenceAtRollback: number;
  } {
    const historyStats = this.history.getStats();
    const undoCount = historyStats.byAction['undo'] ?? 0;

    // Calculate average confidence for rolled back entries
    const entries = this.history.getRecent(100);
    const rolledBackEntries = entries.filter((e) => e.rolledBack);
    const avgConfidenceAtRollback =
      rolledBackEntries.length > 0
        ? rolledBackEntries.reduce((sum, e) => sum + e.confidence, 0) /
          rolledBackEntries.length
        : 0;

    return {
      totalOptimizations: historyStats.total,
      rolledBack: undoCount,
      rollbackRate: historyStats.undoRate,
      avgConfidenceAtRollback,
    };
  }

  /**
   * Get the history.
   */
  getHistory(): OptimizationHistory {
    return this.history;
  }

  /**
   * Get the detector.
   */
  getDetector(): Detector {
    return this.detector;
  }
}

/**
 * Create a rollback manager.
 */
export function createRollbackManager(
  sessionId: string,
  options?: RollbackOptions
): RollbackManager {
  return new RollbackManager(sessionId, options);
}
