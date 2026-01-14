/**
 * Redis Cache Client
 * Handles hot context caching, distributed locking, and change streaming
 */

import Redis from 'ioredis';

export interface RedisCacheConfig {
  host: string;
  port: number;
  password?: string;
  keyPrefix?: string;
}

export interface HotContext {
  projectId: string;
  activeTaskId?: string;
  taskContext?: {
    taskId: string;
    name: string;
    status: string;
    currentPhase?: string;
    iteration: number;
    immediateContext: {
      workingOn: string | null;
      lastAction: string | null;
      nextStep: string | null;
      blockers: string[];
    };
    keyFiles: string[];
    resumePrompt?: string;
  };
  globalContext: {
    hardRules: string[];
    techStack: string[];
    keyPaths: Record<string, string>;
  };
  lastUpdated: string;
}

export interface LockInfo {
  sessionId: string;
  acquiredAt: string;
  expiresAt: string;
}

export class RedisCache {
  private client: Redis | null = null;
  private config: RedisCacheConfig;
  private keyPrefix: string;

  constructor(config: RedisCacheConfig) {
    this.config = config;
    this.keyPrefix = config.keyPrefix || 'context:';
  }

  async connect(): Promise<void> {
    this.client = new Redis({
      host: this.config.host,
      port: this.config.port,
      password: this.config.password,
      retryStrategy: (times) => {
        if (times > 3) {
          console.error('Redis connection failed after 3 retries');
          return null;
        }
        return Math.min(times * 100, 3000);
      },
      lazyConnect: true
    });

    this.client.on('error', (err) => {
      console.error('Redis client error:', err.message);
    });

    this.client.on('connect', () => {
      console.error('Redis connected');
    });

    await this.client.connect();
  }

  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.quit();
      this.client = null;
    }
  }

  private getKey(suffix: string): string {
    return `${this.keyPrefix}${suffix}`;
  }

  // ============================================================================
  // Hot Context Operations
  // ============================================================================

  async getHotContext(projectId: string): Promise<HotContext | null> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`hot:${projectId}`);
    const data = await this.client.get(key);

    if (!data) return null;

    try {
      return JSON.parse(data) as HotContext;
    } catch {
      return null;
    }
  }

  async setHotContext(context: HotContext): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`hot:${context.projectId}`);
    const data = JSON.stringify({
      ...context,
      lastUpdated: new Date().toISOString()
    });

    // Set with 1 hour expiry (will be refreshed by daemon)
    await this.client.setex(key, 3600, data);
  }

  async updateHotContextTask(projectId: string, taskContext: HotContext['taskContext']): Promise<void> {
    const current = await this.getHotContext(projectId);
    if (!current) return;

    await this.setHotContext({
      ...current,
      activeTaskId: taskContext?.taskId,
      taskContext
    });
  }

  // ============================================================================
  // Task Context Cache
  // ============================================================================

  async getTaskContext(taskId: string): Promise<Record<string, unknown> | null> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`task:${taskId}`);
    const data = await this.client.get(key);

    if (!data) return null;

    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  async setTaskContext(taskId: string, context: Record<string, unknown>): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`task:${taskId}`);
    const data = JSON.stringify(context);

    // Set with 4 hour expiry (typical session length)
    await this.client.setex(key, 14400, data);
  }

  async deleteTaskContext(taskId: string): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`task:${taskId}`);
    await this.client.del(key);
  }

  // ============================================================================
  // Distributed Locking
  // ============================================================================

  async acquireLock(
    taskId: string,
    sessionId: string,
    ttlSeconds = 30
  ): Promise<boolean> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`lock:${taskId}`);
    const lockInfo: LockInfo = {
      sessionId,
      acquiredAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + ttlSeconds * 1000).toISOString()
    };

    // Use SET NX (set if not exists) with expiry
    const result = await this.client.set(
      key,
      JSON.stringify(lockInfo),
      'EX',
      ttlSeconds,
      'NX'
    );

    return result === 'OK';
  }

  async releaseLock(taskId: string, sessionId: string): Promise<boolean> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`lock:${taskId}`);

    // Only release if we own the lock
    const current = await this.client.get(key);
    if (!current) return true;

    try {
      const lockInfo = JSON.parse(current) as LockInfo;
      if (lockInfo.sessionId !== sessionId) {
        return false; // Not our lock
      }
    } catch {
      // Invalid lock data, safe to delete
    }

    await this.client.del(key);
    return true;
  }

  async refreshLock(taskId: string, sessionId: string, ttlSeconds = 30): Promise<boolean> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`lock:${taskId}`);

    // Check if we own the lock
    const current = await this.client.get(key);
    if (!current) return false;

    try {
      const lockInfo = JSON.parse(current) as LockInfo;
      if (lockInfo.sessionId !== sessionId) {
        return false; // Not our lock
      }

      // Refresh the lock
      lockInfo.expiresAt = new Date(Date.now() + ttlSeconds * 1000).toISOString();
      await this.client.setex(key, ttlSeconds, JSON.stringify(lockInfo));
      return true;
    } catch {
      return false;
    }
  }

  async getLockInfo(taskId: string): Promise<LockInfo | null> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`lock:${taskId}`);
    const data = await this.client.get(key);

    if (!data) return null;

    try {
      return JSON.parse(data) as LockInfo;
    } catch {
      return null;
    }
  }

  // ============================================================================
  // Recovery Markers
  // ============================================================================

  async setRecoveryMarker(
    sessionId: string,
    state: Record<string, unknown>
  ): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`recovery:${sessionId}`);
    const data = JSON.stringify({
      ...state,
      timestamp: new Date().toISOString()
    });

    // Set with 24 hour expiry
    await this.client.setex(key, 86400, data);
  }

  async getRecoveryMarker(sessionId: string): Promise<Record<string, unknown> | null> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`recovery:${sessionId}`);
    const data = await this.client.get(key);

    if (!data) return null;

    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  async clearRecoveryMarker(sessionId: string): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const key = this.getKey(`recovery:${sessionId}`);
    await this.client.del(key);
  }

  // ============================================================================
  // Change Stream (Pub/Sub)
  // ============================================================================

  async publishChange(channel: string, message: Record<string, unknown>): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    await this.client.publish(
      this.getKey(`changes:${channel}`),
      JSON.stringify({
        ...message,
        timestamp: new Date().toISOString()
      })
    );
  }

  // ============================================================================
  // Utility Operations
  // ============================================================================

  async ping(): Promise<boolean> {
    if (!this.client) return false;

    try {
      const result = await this.client.ping();
      return result === 'PONG';
    } catch {
      return false;
    }
  }

  async getKeys(pattern: string): Promise<string[]> {
    if (!this.client) throw new Error('Redis not connected');

    return this.client.keys(this.getKey(pattern));
  }

  async flushTaskCaches(): Promise<void> {
    if (!this.client) throw new Error('Redis not connected');

    const keys = await this.getKeys('task:*');
    if (keys.length > 0) {
      await this.client.del(...keys);
    }
  }
}
