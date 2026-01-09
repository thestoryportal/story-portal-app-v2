/**
 * Session state management.
 * Tracks optimization session state and history.
 */

import type { Message, ClassificationResponse, OptimizationResponse } from '../types/index.js';

/**
 * Optimization record in session history.
 */
export interface OptimizationRecord {
  /** Original prompt */
  original: string;
  /** Optimized prompt */
  optimized: string;
  /** Classification result */
  classification: ClassificationResponse;
  /** Optimization result */
  optimization: OptimizationResponse | null;
  /** Whether user accepted the optimization */
  accepted: boolean | null;
  /** Timestamp */
  timestamp: number;
}

/**
 * Session state.
 */
export interface SessionState {
  /** Session ID */
  id: string;
  /** Session start time */
  startedAt: number;
  /** Last activity time */
  lastActivityAt: number;
  /** Conversation messages */
  messages: Message[];
  /** Optimization history */
  optimizations: OptimizationRecord[];
  /** Current working directory */
  cwd: string;
  /** Active task */
  activeTask: string | null;
}

/**
 * Session manager.
 */
export class Session {
  private state: SessionState;

  constructor(cwd: string = process.cwd()) {
    this.state = {
      id: this.generateId(),
      startedAt: Date.now(),
      lastActivityAt: Date.now(),
      messages: [],
      optimizations: [],
      cwd,
      activeTask: null,
    };
  }

  /**
   * Generate a unique session ID.
   */
  private generateId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  /**
   * Get session ID.
   */
  getId(): string {
    return this.state.id;
  }

  /**
   * Get session duration in milliseconds.
   */
  getDuration(): number {
    return Date.now() - this.state.startedAt;
  }

  /**
   * Add a message to the session.
   */
  addMessage(role: Message['role'], content: string): void {
    this.state.messages.push({
      role,
      content,
      timestamp: Date.now(),
    });
    this.state.lastActivityAt = Date.now();
  }

  /**
   * Get recent messages.
   */
  getMessages(limit: number = 10): Message[] {
    return this.state.messages.slice(-limit);
  }

  /**
   * Record an optimization.
   */
  recordOptimization(record: Omit<OptimizationRecord, 'timestamp'>): void {
    this.state.optimizations.push({
      ...record,
      timestamp: Date.now(),
    });
    this.state.lastActivityAt = Date.now();
  }

  /**
   * Get recent optimizations.
   */
  getOptimizations(limit: number = 5): OptimizationRecord[] {
    return this.state.optimizations.slice(-limit);
  }

  /**
   * Get the last optimization.
   */
  getLastOptimization(): OptimizationRecord | null {
    return this.state.optimizations[this.state.optimizations.length - 1] ?? null;
  }

  /**
   * Mark the last optimization as accepted/rejected.
   */
  markLastOptimization(accepted: boolean): void {
    const last = this.getLastOptimization();
    if (last && last.accepted === null) {
      last.accepted = accepted;
    }
  }

  /**
   * Get acceptance rate for this session.
   */
  getAcceptanceRate(): number {
    const decided = this.state.optimizations.filter((o) => o.accepted !== null);
    if (decided.length === 0) return 0.8; // Default

    const accepted = decided.filter((o) => o.accepted === true).length;
    return accepted / decided.length;
  }

  /**
   * Set the active task.
   */
  setActiveTask(task: string | null): void {
    this.state.activeTask = task;
    this.state.lastActivityAt = Date.now();
  }

  /**
   * Get the active task.
   */
  getActiveTask(): string | null {
    return this.state.activeTask;
  }

  /**
   * Update working directory.
   */
  setCwd(cwd: string): void {
    this.state.cwd = cwd;
  }

  /**
   * Get working directory.
   */
  getCwd(): string {
    return this.state.cwd;
  }

  /**
   * Check if session is stale (no activity for 30 minutes).
   */
  isStale(): boolean {
    const maxAge = 30 * 60 * 1000; // 30 minutes
    return Date.now() - this.state.lastActivityAt > maxAge;
  }

  /**
   * Get session statistics.
   */
  getStats(): {
    messageCount: number;
    optimizationCount: number;
    acceptanceRate: number;
    duration: number;
    avgLatency: number;
  } {
    const optimizations = this.state.optimizations;
    const latencies = optimizations
      .filter((o) => o.optimization?.latencyMs)
      .map((o) => o.optimization!.latencyMs);

    return {
      messageCount: this.state.messages.length,
      optimizationCount: optimizations.length,
      acceptanceRate: this.getAcceptanceRate(),
      duration: this.getDuration(),
      avgLatency: latencies.length > 0
        ? latencies.reduce((a, b) => a + b, 0) / latencies.length
        : 0,
    };
  }

  /**
   * Export session state.
   */
  export(): SessionState {
    return { ...this.state };
  }

  /**
   * Import session state.
   */
  import(state: SessionState): void {
    this.state = { ...state };
  }

  /**
   * Reset session.
   */
  reset(): void {
    this.state = {
      id: this.generateId(),
      startedAt: Date.now(),
      lastActivityAt: Date.now(),
      messages: [],
      optimizations: [],
      cwd: this.state.cwd,
      activeTask: null,
    };
  }
}

/**
 * Create a new session.
 */
export function createSession(cwd?: string): Session {
  return new Session(cwd);
}
