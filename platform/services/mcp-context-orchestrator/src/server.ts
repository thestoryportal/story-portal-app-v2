#!/usr/bin/env node
/**
 * MCP Context Orchestrator Server
 *
 * Unified context and state management system that ensures zero context loss
 * across all scenarios (new sessions, compaction, crashes) by integrating with
 * existing infrastructure (Elasticsearch, PostgreSQL, Neo4j, Redis).
 */

import 'dotenv/config';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { loadConfig, type ServerConfig } from './config.js';
import * as db from './db/client.js';
import { RedisCache } from './cache/redis-client.js';
import { Neo4jGraph } from './graph/neo4j-client.js';
import { PlatformBridge } from './platform/index.js';
import {
  createGetUnifiedContextTool,
  createSaveContextSnapshotTool,
  createSwitchTaskTool,
  createCreateCheckpointTool,
  createRollbackToTool,
  createDetectConflictsTool,
  createResolveConflictTool,
  createGetTaskGraphTool,
  createSyncHotContextTool,
  createCheckRecoveryTool,
  GetUnifiedContextInputSchema,
  SaveContextSnapshotInputSchema,
  SwitchTaskInputSchema,
  CreateCheckpointInputSchema,
  RollbackToInputSchema,
  DetectConflictsInputSchema,
  ResolveConflictInputSchema,
  GetTaskGraphInputSchema,
  SyncHotContextInputSchema,
  CheckRecoveryInputSchema
} from './tools/index.js';

interface ServerDependencies {
  config: ServerConfig;
  redis: RedisCache;
  neo4j: Neo4jGraph | null;
  projectId: string;
  platform: PlatformBridge;
}

class ContextOrchestratorServer {
  private server: Server;
  private deps: ServerDependencies | null = null;
  private tools: Map<string, { execute: (input: unknown) => Promise<unknown> }> = new Map();

  constructor() {
    this.server = new Server(
      {
        name: 'mcp-context-orchestrator',
        version: '1.0.0'
      },
      {
        capabilities: {
          tools: {}
        }
      }
    );

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'get_unified_context',
            description: 'Aggregates context from ES Memory + Documents + Cache for a task or globally. Returns immediate context, state, key files, and resume guidance.',
            inputSchema: zodToJsonSchema(GetUnifiedContextInputSchema)
          },
          {
            name: 'save_context_snapshot',
            description: 'Persists current state to all backends (PostgreSQL, Redis, file cache). Call this before session end or when making significant changes.',
            inputSchema: zodToJsonSchema(SaveContextSnapshotInputSchema)
          },
          {
            name: 'switch_task',
            description: 'Atomic task switch with state preservation. Saves current task state and loads new task context.',
            inputSchema: zodToJsonSchema(SwitchTaskInputSchema)
          },
          {
            name: 'create_checkpoint',
            description: 'Creates a named version snapshot with rollback capability. Use for milestones or before risky operations.',
            inputSchema: zodToJsonSchema(CreateCheckpointInputSchema)
          },
          {
            name: 'rollback_to',
            description: 'Restore task context to a previous version or checkpoint.',
            inputSchema: zodToJsonSchema(RollbackToInputSchema)
          },
          {
            name: 'detect_conflicts',
            description: 'Cross-system conflict detection between task contexts, checking for state mismatches, spec contradictions, and version divergence.',
            inputSchema: zodToJsonSchema(DetectConflictsInputSchema)
          },
          {
            name: 'resolve_conflict',
            description: 'Apply resolution to a detected conflict.',
            inputSchema: zodToJsonSchema(ResolveConflictInputSchema)
          },
          {
            name: 'get_task_graph',
            description: 'Neo4j-powered task relationship view showing dependencies, blockers, and related tasks.',
            inputSchema: zodToJsonSchema(GetTaskGraphInputSchema)
          },
          {
            name: 'sync_hot_context',
            description: 'Update file cache from databases. Call this to ensure .claude/contexts files are up to date.',
            inputSchema: zodToJsonSchema(SyncHotContextInputSchema)
          },
          {
            name: 'check_recovery',
            description: 'Check for sessions needing recovery from crashes or compaction. Returns recovery prompts with context and tool history.',
            inputSchema: zodToJsonSchema(CheckRecoveryInputSchema)
          }
        ]
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      if (!this.deps) {
        throw new McpError(
          ErrorCode.InternalError,
          'Server not initialized. Call initialize() first.'
        );
      }

      const tool = this.tools.get(name);
      if (!tool) {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${name}`
        );
      }

      try {
        const result = await tool.execute(args || {});
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }
          ]
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${message}`
        );
      }
    });
  }

  async initialize(): Promise<void> {
    const config = loadConfig();

    // Initialize Redis cache
    const redis = new RedisCache({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      keyPrefix: 'context:'
    });
    await redis.connect();

    // Initialize Neo4j graph (optional - may not be available)
    let neo4j: Neo4jGraph | null = null;
    const neo4jEnabled = process.env.NEO4J_ENABLED !== 'false';
    if (neo4jEnabled) {
      try {
        neo4j = new Neo4jGraph({
          uri: config.neo4j.uri,
          username: config.neo4j.username,
          password: config.neo4j.password
        });
        await neo4j.connect();
      } catch (error) {
        console.error('Neo4j connection failed (continuing without graph features):', error instanceof Error ? error.message : error);
        neo4j = null;
      }
    } else {
      console.error('Neo4j disabled via NEO4J_ENABLED=false');
    }

    // Initialize Platform Services Bridge
    const platform = new PlatformBridge({
      redisUrl: `redis://${config.redis.host}:${config.redis.port}`,
      enableEmbeddings: process.env.EMBEDDINGS_ENABLED !== 'false',
      ollamaUrl: process.env.OLLAMA_URL || 'http://localhost:11434',
    });

    try {
      await platform.initialize();
      console.error('Platform services bridge initialized');
    } catch (error) {
      console.error('Platform services initialization failed (continuing with core features):', error instanceof Error ? error.message : error);
    }

    // Store dependencies
    this.deps = {
      config,
      redis,
      neo4j,
      projectId: config.projectId,
      platform
    };

    // Create tools with platform services integration
    const toolDeps = {
      redis,
      neo4j,
      projectId: config.projectId,
      contextsDir: config.contextsDir,
      platform: platform.getServices()
    };

    const getUnifiedContextTool = createGetUnifiedContextTool(toolDeps);
    const saveContextSnapshotTool = createSaveContextSnapshotTool(toolDeps);
    const switchTaskTool = createSwitchTaskTool(toolDeps);
    const createCheckpointTool = createCreateCheckpointTool(toolDeps);
    const rollbackToTool = createRollbackToTool(toolDeps);
    const detectConflictsTool = createDetectConflictsTool(toolDeps);
    const resolveConflictTool = createResolveConflictTool(toolDeps);
    const getTaskGraphTool = createGetTaskGraphTool(toolDeps);
    const syncHotContextTool = createSyncHotContextTool(toolDeps);
    const checkRecoveryTool = createCheckRecoveryTool(toolDeps);

    // Register tools
    this.tools.set('get_unified_context', { execute: (input: unknown) => getUnifiedContextTool.execute(input) });
    this.tools.set('save_context_snapshot', { execute: (input: unknown) => saveContextSnapshotTool.execute(input) });
    this.tools.set('switch_task', { execute: (input: unknown) => switchTaskTool.execute(input) });
    this.tools.set('create_checkpoint', { execute: (input: unknown) => createCheckpointTool.execute(input) });
    this.tools.set('rollback_to', { execute: (input: unknown) => rollbackToTool.execute(input) });
    this.tools.set('detect_conflicts', { execute: (input: unknown) => detectConflictsTool.execute(input) });
    this.tools.set('resolve_conflict', { execute: (input: unknown) => resolveConflictTool.execute(input) });
    this.tools.set('get_task_graph', { execute: (input: unknown) => getTaskGraphTool.execute(input) });
    this.tools.set('sync_hot_context', { execute: (input: unknown) => syncHotContextTool.execute(input) });
    this.tools.set('check_recovery', { execute: (input: unknown) => checkRecoveryTool.execute(input) });

    console.error('MCP Context Orchestrator server initialized');
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP Context Orchestrator server running on stdio');
  }

  async shutdown(): Promise<void> {
    if (this.deps) {
      await this.deps.platform.close();
      await this.deps.redis.disconnect();
      if (this.deps.neo4j) {
        await this.deps.neo4j.disconnect();
      }
      await db.closePool();
    }
    await this.server.close();
  }
}

// Main entry point
async function main(): Promise<void> {
  const server = new ContextOrchestratorServer();

  // Handle graceful shutdown
  const shutdown = async () => {
    console.error('Shutting down...');
    await server.shutdown();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  try {
    await server.initialize();
    await server.run();
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main().catch(console.error);
