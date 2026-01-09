/**
 * Cache storage for optimization results.
 * Provides LRU caching with TTL expiration.
 */

import type { Category, Domain, Complexity } from '../types/index.js';
import { FileAdapter, createFileAdapter } from './file-adapter.js';

/**
 * Cache entry structure.
 */
export interface CacheEntry {
  /** Cache key (hash of original prompt) */
  key: string;
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
  /** Creation timestamp */
  createdAt: number;
  /** Last accessed timestamp */
  accessedAt: number;
  /** Access count */
  accessCount: number;
  /** Time-to-live in ms */
  ttl: number;
}

/**
 * Cache statistics.
 */
export interface CacheStats {
  /** Total entries */
  totalEntries: number;
  /** Total hits */
  hits: number;
  /** Total misses */
  misses: number;
  /** Hit rate */
  hitRate: number;
  /** Average access count */
  avgAccessCount: number;
  /** Cache size in bytes (estimated) */
  sizeBytes: number;
}

/**
 * Stored cache structure.
 */
interface StoredCache {
  version: string;
  entries: Record<string, CacheEntry>;
  stats: {
    hits: number;
    misses: number;
  };
}

/**
 * Cache store options.
 */
export interface CacheStoreOptions {
  /** Maximum cache entries */
  maxEntries?: number;
  /** Default TTL in ms */
  defaultTTL?: number;
  /** Cleanup interval in ms */
  cleanupInterval?: number;
}

/**
 * Default options.
 */
const DEFAULT_OPTIONS: Required<CacheStoreOptions> = {
  maxEntries: 1000,
  defaultTTL: 24 * 60 * 60 * 1000, // 24 hours
  cleanupInterval: 60 * 60 * 1000, // 1 hour
};

/**
 * Cache store class.
 */
export class CacheStore {
  private adapter: FileAdapter<StoredCache>;
  private cache: StoredCache | null = null;
  private options: Required<CacheStoreOptions>;
  private cleanupTimer: ReturnType<typeof setInterval> | null = null;

  constructor(filename: string = 'cache.json', options: CacheStoreOptions = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.adapter = createFileAdapter<StoredCache>(filename);

    // Start cleanup timer
    this.startCleanup();
  }

  /**
   * Load cache from storage.
   */
  private load(): StoredCache {
    if (this.cache) {
      return this.cache;
    }

    const stored = this.adapter.read();

    if (stored) {
      this.cache = stored;
    } else {
      this.cache = {
        version: '1.0.0',
        entries: {},
        stats: {
          hits: 0,
          misses: 0,
        },
      };
      this.save();
    }

    return this.cache;
  }

  /**
   * Save cache to storage.
   */
  private save(): boolean {
    if (!this.cache) {
      return false;
    }
    return this.adapter.write(this.cache);
  }

  /**
   * Generate cache key from prompt.
   */
  private generateKey(prompt: string): string {
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < prompt.length; i++) {
      const char = prompt.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return `cache_${Math.abs(hash).toString(36)}`;
  }

  /**
   * Check if entry is expired.
   */
  private isExpired(entry: CacheEntry): boolean {
    return Date.now() > entry.createdAt + entry.ttl;
  }

  /**
   * Get cached entry.
   */
  get(prompt: string): CacheEntry | null {
    const cache = this.load();
    const key = this.generateKey(prompt);
    const entry = cache.entries[key];

    if (!entry) {
      cache.stats.misses++;
      this.save();
      return null;
    }

    // Check expiration
    if (this.isExpired(entry)) {
      delete cache.entries[key];
      cache.stats.misses++;
      this.save();
      return null;
    }

    // Update access stats
    entry.accessedAt = Date.now();
    entry.accessCount++;
    cache.stats.hits++;
    this.save();

    return entry;
  }

  /**
   * Set cached entry.
   */
  set(
    original: string,
    optimized: string,
    metadata: {
      category: Category;
      domain: Domain | null;
      complexity: Complexity;
      confidence: number;
    },
    ttl?: number
  ): void {
    const cache = this.load();
    const key = this.generateKey(original);

    const entry: CacheEntry = {
      key,
      original,
      optimized,
      category: metadata.category,
      domain: metadata.domain,
      complexity: metadata.complexity,
      confidence: metadata.confidence,
      createdAt: Date.now(),
      accessedAt: Date.now(),
      accessCount: 1,
      ttl: ttl ?? this.options.defaultTTL,
    };

    cache.entries[key] = entry;

    // Enforce max entries with LRU eviction
    this.enforceMaxEntries();

    this.save();
  }

  /**
   * Check if prompt is cached.
   */
  has(prompt: string): boolean {
    const cache = this.load();
    const key = this.generateKey(prompt);
    const entry = cache.entries[key];

    if (!entry) {
      return false;
    }

    return !this.isExpired(entry);
  }

  /**
   * Delete cached entry.
   */
  delete(prompt: string): boolean {
    const cache = this.load();
    const key = this.generateKey(prompt);

    if (cache.entries[key]) {
      delete cache.entries[key];
      this.save();
      return true;
    }

    return false;
  }

  /**
   * Enforce maximum entries using LRU eviction.
   */
  private enforceMaxEntries(): void {
    const cache = this.load();
    const entries = Object.values(cache.entries);

    if (entries.length <= this.options.maxEntries) {
      return;
    }

    // Sort by last accessed (oldest first)
    entries.sort((a, b) => a.accessedAt - b.accessedAt);

    // Remove oldest entries
    const toRemove = entries.length - this.options.maxEntries;
    for (let i = 0; i < toRemove; i++) {
      delete cache.entries[entries[i].key];
    }
  }

  /**
   * Clean up expired entries.
   */
  cleanup(): number {
    const cache = this.load();
    let removed = 0;

    for (const [key, entry] of Object.entries(cache.entries)) {
      if (this.isExpired(entry)) {
        delete cache.entries[key];
        removed++;
      }
    }

    if (removed > 0) {
      this.save();
    }

    return removed;
  }

  /**
   * Start automatic cleanup.
   */
  private startCleanup(): void {
    if (this.cleanupTimer) {
      return;
    }

    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, this.options.cleanupInterval);
  }

  /**
   * Stop automatic cleanup.
   */
  stopCleanup(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
  }

  /**
   * Get cache statistics.
   */
  getStats(): CacheStats {
    const cache = this.load();
    const entries = Object.values(cache.entries);

    const totalEntries = entries.length;
    const hits = cache.stats.hits;
    const misses = cache.stats.misses;
    const hitRate = hits + misses > 0 ? hits / (hits + misses) : 0;
    const avgAccessCount =
      totalEntries > 0
        ? entries.reduce((sum, e) => sum + e.accessCount, 0) / totalEntries
        : 0;

    // Estimate size
    const sizeBytes = entries.reduce(
      (sum, e) =>
        sum +
        e.original.length * 2 +
        e.optimized.length * 2 +
        100, // Overhead
      0
    );

    return {
      totalEntries,
      hits,
      misses,
      hitRate,
      avgAccessCount,
      sizeBytes,
    };
  }

  /**
   * Clear cache.
   */
  clear(): void {
    this.cache = {
      version: '1.0.0',
      entries: {},
      stats: {
        hits: 0,
        misses: 0,
      },
    };
    this.save();
  }

  /**
   * Get all entries (for debugging).
   */
  getAllEntries(): CacheEntry[] {
    const cache = this.load();
    return Object.values(cache.entries);
  }

  /**
   * Get entry count.
   */
  getCount(): number {
    const cache = this.load();
    return Object.keys(cache.entries).length;
  }
}

/**
 * Create a cache store.
 */
export function createCacheStore(
  filename?: string,
  options?: CacheStoreOptions
): CacheStore {
  return new CacheStore(filename, options);
}
