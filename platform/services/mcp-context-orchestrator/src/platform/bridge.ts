/**
 * Platform Services Bridge
 *
 * Central coordinator for platform service integrations.
 * Manages connections and provides unified access to:
 * - StateManager (checkpoint/recovery)
 * - SessionService (session lifecycle)
 * - EventStore (audit trails)
 * - SemanticCache (embedding-based caching)
 */

import { StateManagerAdapter } from './state-manager-adapter.js';
import { SessionServiceAdapter } from './session-service-adapter.js';
import { EventStoreAdapter } from './event-store-adapter.js';
import { SemanticCacheAdapter } from './semantic-cache-adapter.js';

export interface PlatformBridgeConfig {
  /** Base URL for L12 HTTP API (when services are running) */
  l12ApiUrl?: string;
  /** PostgreSQL connection for direct DB access */
  postgresUrl?: string;
  /** Redis URL for cache operations */
  redisUrl?: string;
  /** Whether to prefer HTTP API over direct DB */
  preferHttpApi?: boolean;
  /** Enable semantic embeddings */
  enableEmbeddings?: boolean;
  /** Ollama URL for embeddings */
  ollamaUrl?: string;
}

export interface PlatformServices {
  stateManager: StateManagerAdapter;
  sessionService: SessionServiceAdapter;
  eventStore: EventStoreAdapter;
  semanticCache: SemanticCacheAdapter;
}

/**
 * Platform Services Bridge
 *
 * Provides unified access to all L12 platform services.
 */
export class PlatformBridge {
  private config: PlatformBridgeConfig;
  private services: PlatformServices | null = null;
  private initialized = false;

  constructor(config: PlatformBridgeConfig = {}) {
    this.config = {
      l12ApiUrl: config.l12ApiUrl || process.env.L12_API_URL || 'http://localhost:8012',
      postgresUrl: config.postgresUrl || process.env.DATABASE_URL,
      redisUrl: config.redisUrl || process.env.REDIS_URL || 'redis://localhost:6379',
      preferHttpApi: config.preferHttpApi ?? false,
      enableEmbeddings: config.enableEmbeddings ?? true,
      ollamaUrl: config.ollamaUrl || process.env.OLLAMA_URL || 'http://localhost:11434',
    };
  }

  /**
   * Initialize all platform service adapters
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Check if L12 HTTP API is available
    const httpAvailable = await this.checkHttpApi();

    // Initialize adapters with appropriate mode
    const mode = httpAvailable && this.config.preferHttpApi ? 'http' : 'database';

    this.services = {
      stateManager: new StateManagerAdapter({
        mode,
        apiUrl: this.config.l12ApiUrl,
        redisUrl: this.config.redisUrl,
      }),
      sessionService: new SessionServiceAdapter({
        mode,
        apiUrl: this.config.l12ApiUrl,
        redisUrl: this.config.redisUrl,
      }),
      eventStore: new EventStoreAdapter({
        mode,
        apiUrl: this.config.l12ApiUrl,
      }),
      semanticCache: new SemanticCacheAdapter({
        redisUrl: this.config.redisUrl,
        enableEmbeddings: this.config.enableEmbeddings,
        ollamaUrl: this.config.ollamaUrl,
      }),
    };

    // Initialize each adapter
    await Promise.all([
      this.services.stateManager.initialize(),
      this.services.sessionService.initialize(),
      this.services.eventStore.initialize(),
      this.services.semanticCache.initialize(),
    ]);

    this.initialized = true;
    console.log(`[PlatformBridge] Initialized in ${mode} mode`);
  }

  /**
   * Check if L12 HTTP API is available
   */
  private async checkHttpApi(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.l12ApiUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(2000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get all services
   */
  getServices(): PlatformServices {
    if (!this.services) {
      throw new Error('PlatformBridge not initialized. Call initialize() first.');
    }
    return this.services;
  }

  /**
   * Get StateManager adapter
   */
  get stateManager(): StateManagerAdapter {
    return this.getServices().stateManager;
  }

  /**
   * Get SessionService adapter
   */
  get sessionService(): SessionServiceAdapter {
    return this.getServices().sessionService;
  }

  /**
   * Get EventStore adapter
   */
  get eventStore(): EventStoreAdapter {
    return this.getServices().eventStore;
  }

  /**
   * Get SemanticCache adapter
   */
  get semanticCache(): SemanticCacheAdapter {
    return this.getServices().semanticCache;
  }

  /**
   * Cleanup and close all connections
   */
  async close(): Promise<void> {
    if (this.services) {
      await Promise.all([
        this.services.stateManager.close(),
        this.services.sessionService.close(),
        this.services.eventStore.close(),
        this.services.semanticCache.close(),
      ]);
    }
    this.initialized = false;
  }
}

// Singleton instance
let bridgeInstance: PlatformBridge | null = null;

/**
 * Get or create the platform bridge singleton
 */
export function getPlatformBridge(config?: PlatformBridgeConfig): PlatformBridge {
  if (!bridgeInstance) {
    bridgeInstance = new PlatformBridge(config);
  }
  return bridgeInstance;
}
