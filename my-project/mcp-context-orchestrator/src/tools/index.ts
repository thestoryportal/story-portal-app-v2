/**
 * MCP Tools Index
 * Exports all tool creators and input schemas
 */

// Re-export all tools and schemas
export * from './get-unified-context.js';
export * from './save-context-snapshot.js';
export * from './switch-task.js';
export * from './create-checkpoint.js';
export * from './rollback-to.js';
export * from './detect-conflicts.js';
export * from './resolve-conflict.js';
export * from './get-task-graph.js';
export * from './sync-hot-context.js';
export * from './check-recovery.js';

// Common types
export interface ToolDependencies {
  redis: import('../cache/redis-client.js').RedisCache;
  neo4j: import('../graph/neo4j-client.js').Neo4jGraph;
  projectId: string;
  contextsDir: string;
}

export interface Tool<TInput, TOutput> {
  execute: (input: TInput) => Promise<TOutput>;
}
