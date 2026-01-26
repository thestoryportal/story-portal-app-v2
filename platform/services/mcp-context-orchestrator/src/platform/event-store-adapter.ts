/**
 * EventStore Adapter
 *
 * Integrates L01 EventStore with context orchestrator for:
 * - Event sourcing and audit trails
 * - Context version tracking
 * - Change replay capability
 *
 * Maps to EventStore methods:
 * - create_event -> createEvent
 * - get_event -> getEvent
 * - query_events -> queryEvents
 */

import * as db from '../db/client.js';

export interface EventStoreConfig {
  mode: 'http' | 'database';
  apiUrl?: string;
}

export interface Event {
  id: string;
  eventType: string;
  aggregateType: string;
  aggregateId: string;
  payload: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  version: number;
}

export interface EventCreate {
  eventType: string;
  aggregateType: string;
  aggregateId: string;
  payload: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface EventQuery {
  aggregateId?: string;
  aggregateType?: string;
  eventType?: string;
  limit?: number;
  offset?: number;
}

/**
 * EventStore Adapter
 *
 * Provides event sourcing integrated with context orchestrator's version system.
 */
export class EventStoreAdapter {
  private config: EventStoreConfig;
  private initialized = false;

  constructor(config: EventStoreConfig) {
    this.config = config;
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;
    this.initialized = true;
  }

  /**
   * Create a new event
   *
   * Maps events to context_versions table entries for audit trail.
   */
  async createEvent(eventData: EventCreate): Promise<Event> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(`${this.config.apiUrl}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData),
      });
      return response.json() as Promise<Event>;
    }

    // Direct database mode - store as context version
    const version = await db.createContextVersion(
      eventData.aggregateId, // task_id
      {
        eventType: eventData.eventType,
        aggregateType: eventData.aggregateType,
        payload: eventData.payload,
        metadata: eventData.metadata,
      },
      this.mapEventTypeToChangeType(eventData.eventType),
      `${eventData.eventType} on ${eventData.aggregateType}`,
      eventData.metadata?.createdBy as string | undefined,
      eventData.metadata?.sessionId as string | undefined
    );

    return {
      id: version.id,
      eventType: eventData.eventType,
      aggregateType: eventData.aggregateType,
      aggregateId: eventData.aggregateId,
      payload: eventData.payload,
      metadata: eventData.metadata,
      createdAt: version.createdAt,
      version: version.version,
    };
  }

  /**
   * Get an event by ID
   */
  async getEvent(eventId: string): Promise<Event | null> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const response = await fetch(`${this.config.apiUrl}/api/events/${eventId}`);
      if (!response.ok) return null;
      return response.json() as Promise<Event | null>;
    }

    // Events are stored as context versions - need to search by ID
    // For now, we don't have a direct lookup, so return null
    // A production implementation would add an events table
    console.warn(`[EventStore] Direct event lookup not implemented for ID: ${eventId}`);
    return null;
  }

  /**
   * Query events with filtering
   */
  async queryEvents(query: EventQuery): Promise<Event[]> {
    if (this.config.mode === 'http' && this.config.apiUrl) {
      const params = new URLSearchParams();
      if (query.aggregateId) params.set('aggregate_id', query.aggregateId);
      if (query.aggregateType) params.set('aggregate_type', query.aggregateType);
      if (query.eventType) params.set('event_type', query.eventType);
      if (query.limit) params.set('limit', query.limit.toString());
      if (query.offset) params.set('offset', query.offset.toString());

      const response = await fetch(`${this.config.apiUrl}/api/events?${params}`);
      return response.json() as Promise<Event[]>;
    }

    // Direct database mode - query context_versions
    if (!query.aggregateId) {
      // Need task ID to query versions
      console.warn('[EventStore] aggregateId (taskId) required for database queries');
      return [];
    }

    const versions = await db.getContextVersions(
      query.aggregateId,
      query.limit || 100
    );

    return versions
      .filter((v) => {
        // Filter by event type if specified
        if (query.eventType && v.changeType !== query.eventType) {
          return false;
        }
        return true;
      })
      .slice(query.offset || 0)
      .map((v) => this.mapVersionToEvent(v, query.aggregateId!));
  }

  /**
   * Create context change event
   *
   * Specialized method for context orchestrator integration.
   * Supports both core context events and role-aware events.
   */
  async createContextEvent(
    taskId: string,
    eventType:
      | 'context_updated'
      | 'checkpoint_created'
      | 'conflict_detected'
      | 'conflict_resolved'
      | 'context_rolled_back'
      | 'task_switched'
      | 'hot_context_synced'
      | 'conflicts_detected'
      // Role-aware event types
      | 'role_context_loaded'
      | 'role_switched'
      | 'handoff_create'
      | 'handoff_acknowledge'
      | 'handoff_reject'
      | 'handoff_rejected'
      | 'quality_checkpoint'
      // L14 Skill management event types
      | 'skill_generated'
      | 'skill_validated'
      | 'skills_retrieved'
      | 'skills_optimized',
    payload: Record<string, unknown>,
    sessionId?: string
  ): Promise<Event> {
    return this.createEvent({
      eventType,
      aggregateType: 'task_context',
      aggregateId: taskId,
      payload,
      metadata: { sessionId },
    });
  }

  /**
   * Get event history for a task
   */
  async getTaskHistory(taskId: string, limit = 50): Promise<Event[]> {
    return this.queryEvents({
      aggregateId: taskId,
      aggregateType: 'task_context',
      limit,
    });
  }

  /**
   * Replay events for a task
   *
   * Returns events in chronological order for state reconstruction.
   */
  async replayEvents(taskId: string, fromVersion?: number): Promise<Event[]> {
    const events = await this.getTaskHistory(taskId, 1000);

    // Filter from version and sort chronologically
    return events
      .filter((e) => !fromVersion || e.version >= fromVersion)
      .sort((a, b) => a.version - b.version);
  }

  /**
   * Map event type to change type for context versions
   */
  private mapEventTypeToChangeType(eventType: string): string {
    switch (eventType) {
      case 'context_updated':
        return 'manual';
      case 'checkpoint_created':
        return 'checkpoint';
      case 'conflict_detected':
      case 'conflict_resolved':
        return 'migration';
      case 'auto_save':
        return 'auto_save';
      case 'recovery':
        return 'recovery';
      default:
        return 'manual';
    }
  }

  /**
   * Map context version to Event interface
   */
  private mapVersionToEvent(version: db.ContextVersion, aggregateId: string): Event {
    const snapshot = version.snapshot as Record<string, unknown>;

    return {
      id: version.id,
      eventType: (snapshot.eventType as string) || version.changeType || 'context_updated',
      aggregateType: (snapshot.aggregateType as string) || 'task_context',
      aggregateId,
      payload: (snapshot.payload as Record<string, unknown>) || snapshot,
      metadata: snapshot.metadata as Record<string, unknown> | undefined,
      createdAt: version.createdAt,
      version: version.version,
    };
  }

  async close(): Promise<void> {
    this.initialized = false;
  }
}
