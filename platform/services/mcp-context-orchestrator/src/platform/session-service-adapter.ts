/**
 * SessionService Adapter
 *
 * Integrates L01 SessionService with context orchestrator for:
 * - Session lifecycle management
 * - Heartbeat tracking
 * - Recovery detection
 * - Multi-task session tracking
 *
 * Maps to SessionService methods:
 * - create_session -> createSession
 * - get_session -> getSession
 * - update_session -> updateSession
 * - list_sessions -> listSessions
 */

import Redis from 'ioredis';
import * as db from '../db/client.js';

export interface SessionServiceConfig {
  mode: 'http' | 'database';
  apiUrl?: string;
  redisUrl?: string;
}

export interface Session {
  id: string;
  sessionId: string;
  agentId?: string;
  taskId?: string;
  status: 'active' | 'ended' | 'crashed' | 'recovered';
  projectDir?: string;
  gitBranch?: string;
  startedAt: Date;
  endedAt?: Date;
  lastHeartbeat: Date;
  metadata?: Record<string, unknown>;
}

export interface SessionCreate {
  agentId?: string;
  taskId?: string;
  projectDir?: string;
  gitBranch?: string;
  metadata?: Record<string, unknown>;
}

export interface SessionUpdate {
  status?: Session['status'];
  taskId?: string;
  metadata?: Record<string, unknown>;
  endedAt?: Date;
}

/**
 * SessionService Adapter
 *
 * Manages session lifecycle integrated with context orchestrator.
 */
export class SessionServiceAdapter {
  private config: SessionServiceConfig;
  private redis: Redis | null = null;
  private heartbeatIntervals: Map<string, NodeJS.Timeout> = new Map();
  private initialized = false;

  constructor(config: SessionServiceConfig) {
    this.config = config;
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    if (this.config.redisUrl) {
      this.redis = new Redis(this.config.redisUrl);
      this.redis.on('error', (err: Error) => console.error('[SessionService] Redis error:', err));
    }

    this.initialized = true;
  }

  /**
   * Create a new session
   *
   * Integrates with context orchestrator's active_sessions table.
   */
  async createSession(sessionData: SessionCreate): Promise<Session> {
    const sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(`${this.config.apiUrl}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, ...sessionData }),
      });
      return response.json() as Promise<Session>;
    }

    // Direct database mode
    const dbSession = await db.createSession(
      sessionId,
      sessionData.taskId,
      sessionData.projectDir,
      sessionData.gitBranch
    );

    // Start heartbeat tracking
    this.startHeartbeat(sessionId);

    // Publish session start event to Redis
    await this.publishEvent('session:started', {
      sessionId,
      taskId: sessionData.taskId,
      timestamp: new Date().toISOString(),
    });

    return this.mapDbSessionToSession(dbSession);
  }

  /**
   * Get a session by ID
   */
  async getSession(sessionId: string): Promise<Session | null> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(`${this.config.apiUrl}/api/sessions/${sessionId}`);
      if (!response.ok) return null;
      return response.json() as Promise<Session | null>;
    }

    const dbSession = await db.getActiveSession(sessionId);
    if (!dbSession) return null;

    return this.mapDbSessionToSession(dbSession);
  }

  /**
   * Update a session
   */
  async updateSession(sessionId: string, sessionData: SessionUpdate): Promise<Session | null> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(`${this.config.apiUrl}/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sessionData),
      });
      if (!response.ok) return null;
      return response.json() as Promise<Session | null>;
    }

    // Handle status updates
    if (sessionData.status === 'ended') {
      await db.endSession(sessionId);
      this.stopHeartbeat(sessionId);
    } else if (sessionData.status === 'recovered') {
      await db.markSessionRecovered(sessionId);
    }

    // Publish update event
    await this.publishEvent('session:updated', {
      sessionId,
      status: sessionData.status,
      timestamp: new Date().toISOString(),
    });

    return this.getSession(sessionId);
  }

  /**
   * List sessions with optional filtering
   */
  async listSessions(agentId?: string, limit = 100): Promise<Session[]> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (agentId) params.set('agent_id', agentId);

      const response = await fetch(`${this.config.apiUrl}/api/sessions?${params}`);
      return response.json() as Promise<Session[]>;
    }

    // Direct database mode - get sessions needing recovery or all active
    const sessions = await db.getSessionsNeedingRecovery();

    return sessions
      .filter((s) => !agentId || s.taskId === agentId)
      .slice(0, limit)
      .map((s) => this.mapDbSessionToSession(s));
  }

  /**
   * Get sessions needing recovery
   */
  async getSessionsNeedingRecovery(): Promise<Session[]> {
    const sessions = await db.getSessionsNeedingRecovery();
    return sessions.map((s) => this.mapDbSessionToSession(s));
  }

  /**
   * Mark session for recovery
   */
  async markForRecovery(
    sessionId: string,
    recoveryType: string,
    contextSnapshot: Record<string, unknown>,
    conversationSummary?: string
  ): Promise<void> {
    await db.markSessionForRecovery(
      sessionId,
      recoveryType,
      contextSnapshot,
      conversationSummary
    );

    this.stopHeartbeat(sessionId);

    // Publish recovery event
    await this.publishEvent('session:recovery_needed', {
      sessionId,
      recoveryType,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * End a session
   */
  async endSession(sessionId: string): Promise<void> {
    await db.endSession(sessionId);
    this.stopHeartbeat(sessionId);

    await this.publishEvent('session:ended', {
      sessionId,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Start heartbeat tracking for a session
   */
  private startHeartbeat(sessionId: string): void {
    // Update heartbeat every 30 seconds
    const interval = setInterval(async () => {
      try {
        await db.updateSessionHeartbeat(sessionId);
      } catch (err) {
        console.error(`[SessionService] Heartbeat failed for ${sessionId}:`, err);
      }
    }, 30000);

    this.heartbeatIntervals.set(sessionId, interval);
  }

  /**
   * Stop heartbeat tracking for a session
   */
  private stopHeartbeat(sessionId: string): void {
    const interval = this.heartbeatIntervals.get(sessionId);
    if (interval) {
      clearInterval(interval);
      this.heartbeatIntervals.delete(sessionId);
    }
  }

  /**
   * Publish event to Redis pub/sub
   */
  private async publishEvent(channel: string, data: Record<string, unknown>): Promise<void> {
    if (!this.redis) return;

    try {
      await this.redis.publish(channel, JSON.stringify(data));
    } catch (err) {
      console.error(`[SessionService] Failed to publish event:`, err);
    }
  }

  /**
   * Map database session to Session interface
   */
  private mapDbSessionToSession(dbSession: db.ActiveSession): Session {
    return {
      id: dbSession.id,
      sessionId: dbSession.sessionId,
      taskId: dbSession.taskId || undefined,
      status: this.mapDbStatus(dbSession.status),
      projectDir: dbSession.projectDir || undefined,
      gitBranch: dbSession.gitBranch || undefined,
      startedAt: dbSession.startedAt,
      endedAt: dbSession.endedAt || undefined,
      lastHeartbeat: dbSession.lastHeartbeat,
      metadata: dbSession.contextSnapshot || undefined,
    };
  }

  /**
   * Map database status to Session status
   */
  private mapDbStatus(status: string): Session['status'] {
    switch (status) {
      case 'active':
        return 'active';
      case 'ended':
        return 'ended';
      case 'recovered':
        return 'recovered';
      case 'crash':
      case 'compaction':
      case 'timeout':
        return 'crashed';
      default:
        return 'active';
    }
  }

  async close(): Promise<void> {
    // Stop all heartbeats
    for (const [sessionId] of this.heartbeatIntervals) {
      this.stopHeartbeat(sessionId);
    }

    if (this.redis) {
      this.redis.disconnect();
      this.redis = null;
    }
    this.initialized = false;
  }
}
