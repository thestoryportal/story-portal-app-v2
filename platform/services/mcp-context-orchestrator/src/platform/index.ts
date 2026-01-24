/**
 * Platform Services Bridge
 *
 * Integrates L12 platform services (StateManager, SessionService, EventStore, SemanticCache)
 * with the context orchestrator for unified state management.
 *
 * Supports two modes:
 * 1. Direct database access (when Python services aren't running)
 * 2. HTTP API calls (when L12 services are running)
 */

export * from './state-manager-adapter.js';
export * from './session-service-adapter.js';
export * from './event-store-adapter.js';
export * from './semantic-cache-adapter.js';
export * from './bridge.js';
