/**
 * SemanticCache Adapter
 *
 * Integrates L04 SemanticCache with context orchestrator for:
 * - Embedding-based context caching
 * - Semantic similarity search on tasks
 * - Hot context with semantic lookup
 *
 * Maps to SemanticCache methods:
 * - get -> get (with semantic similarity)
 * - set -> set (with embedding generation)
 * - clear -> clear
 * - get_stats -> getStats
 */

import Redis from 'ioredis';

export interface SemanticCacheConfig {
  redisUrl?: string;
  ttlSeconds?: number;
  similarityThreshold?: number;
  enableEmbeddings?: boolean;
  ollamaUrl?: string;
  embeddingModel?: string;
}

export interface CacheEntry {
  key: string;
  value: Record<string, unknown>;
  embedding?: number[];
  metadata?: Record<string, unknown>;
  createdAt: Date;
  expiresAt: Date;
}

export interface CacheStats {
  hits: number;
  misses: number;
  writes: number;
  semanticHits: number;
  errors: number;
}

export interface SimilarityResult {
  key: string;
  score: number;
  value: Record<string, unknown>;
  // Additional fields for task context similarity
  taskId?: string;
  similarity?: number;
  context?: Record<string, unknown>;
}

/**
 * SemanticCache Adapter
 *
 * Provides embedding-based caching for context orchestrator.
 */
export class SemanticCacheAdapter {
  private config: SemanticCacheConfig;
  private redis: Redis | null = null;
  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    writes: 0,
    semanticHits: 0,
    errors: 0,
  };
  private initialized = false;

  constructor(config: SemanticCacheConfig = {}) {
    this.config = {
      redisUrl: config.redisUrl || process.env.REDIS_URL || 'redis://localhost:6379',
      ttlSeconds: config.ttlSeconds || 3600,
      similarityThreshold: config.similarityThreshold || 0.85,
      enableEmbeddings: config.enableEmbeddings ?? true,
      ollamaUrl: config.ollamaUrl || process.env.OLLAMA_URL || 'http://localhost:11434',
      embeddingModel: config.embeddingModel || 'nomic-embed-text',
    };
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    if (this.config.redisUrl) {
      this.redis = new Redis(this.config.redisUrl);
      this.redis.on('error', (err: Error) => console.error('[SemanticCache] Redis error:', err));
    }

    this.initialized = true;
  }

  /**
   * Get cached value by key or semantic similarity
   */
  async get(key: string): Promise<Record<string, unknown> | null> {
    if (!this.redis) return null;

    try {
      // Try exact match first
      const cacheKey = `semantic:${key}`;
      const data = await this.redis.get(cacheKey);

      if (data) {
        this.stats.hits++;
        return JSON.parse(data);
      }

      this.stats.misses++;
      return null;
    } catch (err) {
      this.stats.errors++;
      console.error('[SemanticCache] Get error:', err);
      return null;
    }
  }

  /**
   * Get by semantic similarity
   *
   * Searches for similar cached entries using embeddings.
   */
  async getSimilar(query: string, maxResults = 5): Promise<SimilarityResult[]> {
    if (!this.redis || !this.config.enableEmbeddings) return [];

    try {
      // Generate query embedding
      const queryEmbedding = await this.generateEmbedding(query);
      if (!queryEmbedding) return [];

      // Get all embeddings from cache
      const pattern = 'semantic:embedding:*';
      const keys = await this.redis.keys(pattern);

      const results: SimilarityResult[] = [];

      for (const key of keys) {
        const data = await this.redis.get(key);
        if (!data) continue;

        const entry = JSON.parse(data) as { embedding: number[]; valueKey: string };
        const score = this.cosineSimilarity(queryEmbedding, entry.embedding);

        if (score >= this.config.similarityThreshold!) {
          const value = await this.get(entry.valueKey);
          if (value) {
            results.push({
              key: entry.valueKey,
              score,
              value,
            });
          }
        }
      }

      // Sort by score descending
      results.sort((a, b) => b.score - a.score);

      if (results.length > 0) {
        this.stats.semanticHits += results.length;
      }

      return results.slice(0, maxResults);
    } catch (err) {
      this.stats.errors++;
      console.error('[SemanticCache] Semantic search error:', err);
      return [];
    }
  }

  /**
   * Set cached value with optional embedding
   */
  async set(
    key: string,
    value: Record<string, unknown>,
    textForEmbedding?: string
  ): Promise<void> {
    if (!this.redis) return;

    try {
      const cacheKey = `semantic:${key}`;

      // Store the value
      await this.redis.setex(cacheKey, this.config.ttlSeconds!, JSON.stringify(value));

      // Generate and store embedding if enabled
      if (this.config.enableEmbeddings && textForEmbedding) {
        const embedding = await this.generateEmbedding(textForEmbedding);
        if (embedding) {
          const embeddingKey = `semantic:embedding:${key}`;
          await this.redis.setex(
            embeddingKey,
            this.config.ttlSeconds!,
            JSON.stringify({ embedding, valueKey: key })
          );
        }
      }

      this.stats.writes++;
    } catch (err) {
      this.stats.errors++;
      console.error('[SemanticCache] Set error:', err);
    }
  }

  /**
   * Cache task context with semantic search capability
   */
  async cacheTaskContext(
    taskId: string,
    context: Record<string, unknown>
  ): Promise<void> {
    // Create searchable text from context
    const searchText = this.contextToSearchText(context);

    await this.set(`task:${taskId}`, context, searchText);
  }

  /**
   * Find similar task contexts
   */
  async findSimilarTasks(query: string, maxResults = 5): Promise<SimilarityResult[]> {
    const results = await this.getSimilar(query, maxResults);
    // Map results to include task-specific fields
    return results.map(r => ({
      ...r,
      taskId: r.key.replace('task:', ''),
      similarity: r.score,
      context: r.value,
    }));
  }

  /**
   * Clear all cached entries
   */
  async clear(): Promise<void> {
    if (!this.redis) return;

    try {
      const pattern = 'semantic:*';
      const keys = await this.redis.keys(pattern);

      if (keys.length > 0) {
        await this.redis.del(keys);
      }
    } catch (err) {
      this.stats.errors++;
      console.error('[SemanticCache] Clear error:', err);
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return { ...this.stats };
  }

  /**
   * Generate embedding using Ollama
   */
  private async generateEmbedding(text: string): Promise<number[] | null> {
    if (!this.config.enableEmbeddings || !this.config.ollamaUrl) {
      return null;
    }

    try {
      const response = await fetch(`${this.config.ollamaUrl}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.config.embeddingModel,
          prompt: text,
        }),
        signal: AbortSignal.timeout(10000),
      });

      if (!response.ok) {
        console.warn('[SemanticCache] Embedding generation failed:', response.statusText);
        return null;
      }

      const result = await response.json() as { embedding: number[] };
      return result.embedding;
    } catch (err) {
      // Ollama might not be running - this is expected in some environments
      console.debug('[SemanticCache] Embedding generation unavailable:', err);
      return null;
    }
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    const magnitude = Math.sqrt(normA) * Math.sqrt(normB);
    return magnitude === 0 ? 0 : dotProduct / magnitude;
  }

  /**
   * Convert context to searchable text
   */
  private contextToSearchText(context: Record<string, unknown>): string {
    const parts: string[] = [];

    // Extract key fields for embedding
    if (context.name) parts.push(String(context.name));
    if (context.description) parts.push(String(context.description));
    if (context.resumePrompt) parts.push(String(context.resumePrompt));

    if (context.keywords && Array.isArray(context.keywords)) {
      parts.push(context.keywords.join(' '));
    }

    if (context.keyFiles && Array.isArray(context.keyFiles)) {
      parts.push(context.keyFiles.join(' '));
    }

    if (context.immediateContext) {
      const ic = context.immediateContext as Record<string, unknown>;
      if (ic.workingOn) parts.push(String(ic.workingOn));
      if (ic.nextStep) parts.push(String(ic.nextStep));
      if (ic.blockers && Array.isArray(ic.blockers)) {
        parts.push(ic.blockers.join(' '));
      }
    }

    if (context.technicalDecisions && Array.isArray(context.technicalDecisions)) {
      parts.push(context.technicalDecisions.join(' '));
    }

    return parts.join('. ');
  }

  async close(): Promise<void> {
    if (this.redis) {
      this.redis.disconnect();
      this.redis = null;
    }
    this.initialized = false;
  }
}
