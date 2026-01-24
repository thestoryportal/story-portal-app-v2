/**
 * StateManager Adapter
 *
 * Integrates L02 StateManager with context orchestrator for:
 * - Agent state checkpointing
 * - Checkpoint restoration
 * - Hot state caching (Redis)
 * - State persistence (PostgreSQL)
 *
 * Maps to StateManager methods:
 * - create_checkpoint -> createCheckpoint
 * - restore_checkpoint -> restoreCheckpoint
 * - save_hot_state -> saveHotState
 * - load_hot_state -> loadHotState
 * - list_checkpoints -> listCheckpoints
 */

import Redis from 'ioredis';
import * as db from '../db/client.js';

export interface StateManagerConfig {
  mode: 'http' | 'database';
  apiUrl?: string;
  redisUrl?: string;
}

export interface AgentState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  currentTask?: string;
  progress?: number;
  metadata?: Record<string, unknown>;
}

export interface StateSnapshot {
  agentId: string;
  sessionId: string;
  state: AgentState;
  context: Record<string, unknown>;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface CheckpointMetadata {
  checkpointId: string;
  agentId: string;
  sessionId: string;
  timestamp: Date;
  sizeBytes: number;
  compressed: boolean;
}

/**
 * StateManager Adapter
 *
 * Provides checkpoint/recovery functionality integrated with context orchestrator.
 */
export class StateManagerAdapter {
  private config: StateManagerConfig;
  private redis: Redis | null = null;
  private initialized = false;

  constructor(config: StateManagerConfig) {
    this.config = config;
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Initialize Redis connection for hot state
    if (this.config.redisUrl) {
      this.redis = new Redis(this.config.redisUrl);
      this.redis.on('error', (err: Error) => console.error('[StateManager] Redis error:', err));
    }

    this.initialized = true;
  }

  /**
   * Create a checkpoint of agent state
   *
   * Integrates with context orchestrator's checkpoint system.
   * Stores in both PostgreSQL (via context_versions) and Redis (hot cache).
   */
  async createCheckpoint(
    agentId: string,
    sessionId: string,
    state: AgentState,
    context: Record<string, unknown>,
    metadata?: Record<string, unknown>
  ): Promise<string> {
    const checkpointId = `chk_${agentId}_${Date.now()}`;

    // Create snapshot
    const snapshot: StateSnapshot = {
      agentId,
      sessionId,
      state,
      context,
      timestamp: new Date(),
      metadata,
    };

    if (this.config.mode === 'http' && this.config.apiUrl) {
      // Call L12 API
      const response = await fetch(`${this.config.apiUrl}/api/state/checkpoint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentId, sessionId, state, context, metadata }),
      });
      const result = await response.json() as { checkpointId: string };
      return result.checkpointId;
    }

    // Direct database mode - use context orchestrator's checkpoint system
    await db.createCheckpoint({
      checkpointId,
      label: `Agent ${agentId} checkpoint`,
      description: `State checkpoint for agent ${agentId} in session ${sessionId}`,
      checkpointType: 'auto',
      taskId: agentId, // Map agent to task
      scope: 'task',
      snapshot: snapshot as unknown as Record<string, unknown>,
      sessionId,
    });

    // Also save to Redis hot cache
    await this.saveHotState(agentId, snapshot);

    return checkpointId;
  }

  /**
   * Restore state from a checkpoint
   */
  async restoreCheckpoint(checkpointId: string): Promise<StateSnapshot | null> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(
        `${this.config.apiUrl}/api/state/checkpoint/${checkpointId}`
      );
      if (!response.ok) return null;
      return response.json() as Promise<StateSnapshot | null>;
    }

    // Direct database mode
    const checkpoint = await db.getCheckpoint(checkpointId);
    if (!checkpoint) return null;

    return checkpoint.snapshot as unknown as StateSnapshot;
  }

  /**
   * Save agent state to Redis hot cache
   */
  async saveHotState(agentId: string, stateData: StateSnapshot | Record<string, unknown>): Promise<void> {
    if (!this.redis) return;

    const key = `state:hot:${agentId}`;
    await this.redis.setex(key, 3600, JSON.stringify(stateData)); // 1 hour TTL
  }

  /**
   * Load agent state from Redis hot cache
   */
  async loadHotState(agentId: string): Promise<StateSnapshot | null> {
    if (!this.redis) return null;

    const key = `state:hot:${agentId}`;
    const data = await this.redis.get(key);
    if (!data) return null;

    return JSON.parse(data);
  }

  /**
   * Save agent state with automatic checkpointing
   *
   * Combines hot cache update with periodic checkpointing.
   */
  async saveAgentState(
    agentId: string,
    sessionId: string,
    state: AgentState,
    context: Record<string, unknown>,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    const snapshot: StateSnapshot = {
      agentId,
      sessionId,
      state,
      context,
      timestamp: new Date(),
      metadata,
    };

    // Always update hot cache
    await this.saveHotState(agentId, snapshot);

    // Update task context in database
    await db.updateTaskContext(agentId, {
      status: this.mapAgentStatusToTaskStatus(state.status),
      immediateContext: {
        workingOn: state.currentTask || null,
        lastAction: `State: ${state.status}`,
        nextStep: null,
        blockers: [],
      },
    });
  }

  /**
   * Load most recent agent state
   */
  async loadAgentState(agentId: string): Promise<StateSnapshot | null> {
    // Try hot cache first
    const hotState = await this.loadHotState(agentId);
    if (hotState) return hotState;

    // Fall back to database checkpoints
    const checkpoints = await this.listCheckpoints(agentId, 1);
    if (checkpoints.length > 0) {
      return this.restoreCheckpoint(checkpoints[0].checkpointId);
    }

    return null;
  }

  /**
   * List checkpoints for an agent
   */
  async listCheckpoints(agentId: string, limit = 10): Promise<CheckpointMetadata[]> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(
        `${this.config.apiUrl}/api/state/checkpoints/${agentId}?limit=${limit}`
      );
      return response.json() as Promise<CheckpointMetadata[]>;
    }

    // Direct database mode
    const checkpoints = await db.listCheckpoints(agentId, limit);

    return checkpoints.map((cp) => ({
      checkpointId: cp.checkpointId,
      agentId,
      sessionId: cp.sessionId || '',
      timestamp: cp.createdAt,
      sizeBytes: JSON.stringify(cp.snapshot).length,
      compressed: false,
    }));
  }

  /**
   * Cleanup old checkpoints
   */
  async cleanupOldCheckpoints(agentId?: string, retentionDays = 30): Promise<number> {
    // This would be implemented with a database query
    // For now, return 0 as checkpoints are managed by context orchestrator
    console.log(`[StateManager] Cleanup requested for agent ${agentId}, retention ${retentionDays} days`);
    return 0;
  }

  /**
   * Map agent status to task status
   */
  private mapAgentStatusToTaskStatus(
    status: AgentState['status']
  ): 'pending' | 'in_progress' | 'completed' | 'blocked' | 'archived' {
    switch (status) {
      case 'idle':
        return 'pending';
      case 'running':
        return 'in_progress';
      case 'paused':
        return 'blocked';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'blocked';
      default:
        return 'pending';
    }
  }

  async close(): Promise<void> {
    if (this.redis) {
      this.redis.disconnect();
      this.redis = null;
    }
    this.initialized = false;
  }
}
