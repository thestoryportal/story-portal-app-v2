/**
 * Optimization history for tracking and recovery.
 */

import type { Category, Domain, Complexity, Change } from '../types/index.js';
import { FileAdapter, createFileAdapter } from '../storage/file-adapter.js';

/**
 * Optimization history entry.
 */
export interface OptimizationHistoryEntry {
  /** Entry ID */
  id: string;
  /** Timestamp */
  timestamp: number;
  /** Session ID */
  sessionId: string;
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Classification category */
  category: Category;
  /** Detected domain */
  domain: Domain | null;
  /** Complexity level */
  complexity: Complexity;
  /** Confidence score */
  confidence: number;
  /** Changes made */
  changes: Change[];
  /** Passes used */
  passesUsed: number;
  /** User action */
  userAction: 'accept' | 'reject' | 'modify' | 'undo' | 'pending' | null;
  /** Modified version if applicable */
  modified?: string;
  /** Whether this was rolled back */
  rolledBack: boolean;
  /** Parent entry ID if this is a re-optimization */
  parentId?: string;
}

/**
 * Stored history structure.
 */
interface StoredHistory {
  version: string;
  entries: OptimizationHistoryEntry[];
  lastCleanup: number;
}

/**
 * History options.
 */
export interface HistoryOptions {
  /** Maximum entries to keep */
  maxEntries?: number;
  /** Retention period in ms */
  retentionPeriod?: number;
}

/**
 * Default options.
 */
const DEFAULT_OPTIONS: Required<HistoryOptions> = {
  maxEntries: 500,
  retentionPeriod: 30 * 24 * 60 * 60 * 1000, // 30 days
};

/**
 * Optimization history class.
 */
export class OptimizationHistory {
  private adapter: FileAdapter<StoredHistory>;
  private cache: StoredHistory | null = null;
  private options: Required<HistoryOptions>;
  private sessionId: string;

  constructor(
    sessionId: string,
    filename: string = 'history.json',
    options: HistoryOptions = {}
  ) {
    this.sessionId = sessionId;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.adapter = createFileAdapter<StoredHistory>(filename);
  }

  /**
   * Load history from storage.
   */
  private load(): StoredHistory {
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
        lastCleanup: Date.now(),
      };
      this.save();
    }

    return this.cache;
  }

  /**
   * Save history to storage.
   */
  private save(): boolean {
    if (!this.cache) {
      return false;
    }
    return this.adapter.write(this.cache);
  }

  /**
   * Add an optimization to history.
   */
  add(entry: Omit<OptimizationHistoryEntry, 'id' | 'timestamp' | 'sessionId' | 'userAction' | 'rolledBack'>): OptimizationHistoryEntry {
    const history = this.load();

    const fullEntry: OptimizationHistoryEntry = {
      ...entry,
      id: `hist_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: Date.now(),
      sessionId: this.sessionId,
      userAction: 'pending',
      rolledBack: false,
    };

    history.entries.push(fullEntry);

    // Cleanup if needed
    this.cleanup();

    this.save();
    return fullEntry;
  }

  /**
   * Update user action for an entry.
   */
  updateAction(
    id: string,
    action: OptimizationHistoryEntry['userAction'],
    modified?: string
  ): boolean {
    const history = this.load();
    const entry = history.entries.find((e) => e.id === id);

    if (!entry) {
      return false;
    }

    entry.userAction = action;
    if (modified) {
      entry.modified = modified;
    }

    this.save();
    return true;
  }

  /**
   * Mark entry as rolled back.
   */
  markRolledBack(id: string): boolean {
    const history = this.load();
    const entry = history.entries.find((e) => e.id === id);

    if (!entry) {
      return false;
    }

    entry.rolledBack = true;
    entry.userAction = 'undo';
    this.save();
    return true;
  }

  /**
   * Get entry by ID.
   */
  get(id: string): OptimizationHistoryEntry | null {
    const history = this.load();
    return history.entries.find((e) => e.id === id) ?? null;
  }

  /**
   * Get last entry.
   */
  getLast(): OptimizationHistoryEntry | null {
    const history = this.load();
    return history.entries.length > 0
      ? history.entries[history.entries.length - 1]
      : null;
  }

  /**
   * Get last N entries.
   */
  getRecent(limit: number = 10): OptimizationHistoryEntry[] {
    const history = this.load();
    return history.entries.slice(-limit).reverse();
  }

  /**
   * Get entries for current session.
   */
  getSessionEntries(): OptimizationHistoryEntry[] {
    const history = this.load();
    return history.entries
      .filter((e) => e.sessionId === this.sessionId)
      .reverse();
  }

  /**
   * Get entries that can be undone (pending or accepted).
   */
  getUndoable(): OptimizationHistoryEntry[] {
    const history = this.load();
    return history.entries
      .filter(
        (e) =>
          !e.rolledBack &&
          (e.userAction === 'accept' || e.userAction === 'pending')
      )
      .reverse();
  }

  /**
   * Search history by original prompt.
   */
  searchByOriginal(query: string, limit: number = 10): OptimizationHistoryEntry[] {
    const history = this.load();
    const lowerQuery = query.toLowerCase();

    return history.entries
      .filter((e) => e.original.toLowerCase().includes(lowerQuery))
      .slice(-limit)
      .reverse();
  }

  /**
   * Get entries by domain.
   */
  getByDomain(domain: Domain, limit: number = 10): OptimizationHistoryEntry[] {
    const history = this.load();
    return history.entries
      .filter((e) => e.domain === domain)
      .slice(-limit)
      .reverse();
  }

  /**
   * Get entries by category.
   */
  getByCategory(category: Category, limit: number = 10): OptimizationHistoryEntry[] {
    const history = this.load();
    return history.entries
      .filter((e) => e.category === category)
      .slice(-limit)
      .reverse();
  }

  /**
   * Get statistics.
   */
  getStats(): {
    total: number;
    byAction: Record<string, number>;
    byCategory: Record<string, number>;
    byDomain: Record<string, number>;
    undoRate: number;
    avgConfidence: number;
  } {
    const history = this.load();
    const entries = history.entries;

    const byAction: Record<string, number> = {};
    const byCategory: Record<string, number> = {};
    const byDomain: Record<string, number> = {};
    let undoCount = 0;
    let totalConfidence = 0;

    for (const entry of entries) {
      // By action
      const action = entry.userAction ?? 'unknown';
      byAction[action] = (byAction[action] ?? 0) + 1;

      // By category
      byCategory[entry.category] = (byCategory[entry.category] ?? 0) + 1;

      // By domain
      const domain = entry.domain ?? 'unknown';
      byDomain[domain] = (byDomain[domain] ?? 0) + 1;

      // Undo count
      if (entry.rolledBack) {
        undoCount++;
      }

      // Confidence
      totalConfidence += entry.confidence;
    }

    return {
      total: entries.length,
      byAction,
      byCategory,
      byDomain,
      undoRate: entries.length > 0 ? undoCount / entries.length : 0,
      avgConfidence: entries.length > 0 ? totalConfidence / entries.length : 0,
    };
  }

  /**
   * Cleanup old entries.
   */
  private cleanup(): void {
    const history = this.load();
    const now = Date.now();

    // Skip if cleaned up recently
    if (now - history.lastCleanup < 60 * 60 * 1000) {
      return;
    }

    // Remove old entries
    const cutoff = now - this.options.retentionPeriod;
    history.entries = history.entries.filter((e) => e.timestamp > cutoff);

    // Enforce max entries
    if (history.entries.length > this.options.maxEntries) {
      history.entries = history.entries.slice(-this.options.maxEntries);
    }

    history.lastCleanup = now;
  }

  /**
   * Clear all history.
   */
  clear(): void {
    this.cache = {
      version: '1.0.0',
      entries: [],
      lastCleanup: Date.now(),
    };
    this.save();
  }

  /**
   * Get count.
   */
  getCount(): number {
    return this.load().entries.length;
  }
}

/**
 * Create an optimization history.
 */
export function createOptimizationHistory(
  sessionId: string,
  filename?: string,
  options?: HistoryOptions
): OptimizationHistory {
  return new OptimizationHistory(sessionId, filename, options);
}
