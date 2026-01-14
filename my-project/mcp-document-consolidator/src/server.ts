#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import { Client as ElasticsearchClient } from '@elastic/elasticsearch';
import { loadConfig } from './config.js';
import { createDatabaseService, type DatabaseService } from './db/index.js';
import { EmbeddingPipeline } from './ai/embedding-pipeline.js';
import { LLMPipeline } from './ai/llm-pipeline.js';
import { EntityResolver } from './components/entity-resolver.js';
import {
  createIngestDocumentTool,
  createFindOverlapsTool,
  createConsolidateDocumentsTool,
  createGetSourceOfTruthTool,
  createDeprecateDocumentTool,
  IngestDocumentInputSchema,
  FindOverlapsInputSchema,
  ConsolidateDocumentsInputSchema,
  GetSourceOfTruthInputSchema,
  DeprecateDocumentInputSchema
} from './tools/index.js';
import { zodToJsonSchema } from 'zod-to-json-schema';

interface ServerDependencies {
  db: DatabaseService;
  es: ElasticsearchClient;
  embeddingPipeline: EmbeddingPipeline;
  llmPipeline: LLMPipeline;
  entityResolver: EntityResolver;
  esIndex: string;
  neo4jUri: string;
  neo4jAuth: { username: string; password: string };
}

class DocumentConsolidatorServer {
  private server: Server;
  private deps: ServerDependencies | null = null;
  private tools: Map<string, { execute: (input: unknown) => Promise<unknown> }> = new Map();

  constructor() {
    this.server = new Server(
      {
        name: 'mcp-document-consolidator',
        version: '2.0.0'
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
            name: 'ingest_document',
            description: 'Add a document to the consolidation index with optional claim extraction and embedding generation',
            inputSchema: zodToJsonSchema(IngestDocumentInputSchema)
          },
          {
            name: 'find_overlaps',
            description: 'Identify redundant or conflicting content across documents',
            inputSchema: zodToJsonSchema(FindOverlapsInputSchema)
          },
          {
            name: 'consolidate_documents',
            description: 'Merge multiple documents into a single consolidated document with conflict resolution',
            inputSchema: zodToJsonSchema(ConsolidateDocumentsInputSchema)
          },
          {
            name: 'get_source_of_truth',
            description: 'Query the document corpus for authoritative answers with full provenance',
            inputSchema: zodToJsonSchema(GetSourceOfTruthInputSchema)
          },
          {
            name: 'deprecate_document',
            description: 'Mark a document as deprecated with optional migration to replacement',
            inputSchema: zodToJsonSchema(DeprecateDocumentInputSchema)
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

    // Initialize database
    const db = createDatabaseService({
      host: config.postgres.host,
      port: config.postgres.port,
      database: config.postgres.database,
      user: config.postgres.user,
      password: config.postgres.password,
      ssl: config.postgres.ssl
    });
    await db.initialize();

    // Initialize Elasticsearch
    const es = new ElasticsearchClient({
      node: `http://${config.elasticsearch.host}:${config.elasticsearch.port}`,
      auth: config.elasticsearch.username ? {
        username: config.elasticsearch.username,
        password: config.elasticsearch.password || ''
      } : undefined
    });

    // Initialize AI pipelines
    const embeddingPipeline = new EmbeddingPipeline({
      pythonPath: config.embedding.pythonPath,
      modelName: config.embedding.model,
      batchSize: config.embedding.batchSize,
      cacheEnabled: config.embedding.cacheEnabled
    });
    await embeddingPipeline.initialize();

    const llmPipeline = new LLMPipeline({
      baseUrl: config.ollama.baseUrl,
      defaultModel: config.ollama.defaultModel,
      temperature: config.ollama.temperature,
      maxTokens: config.ollama.maxTokens,
      timeout: config.ollama.timeout
    });

    // Initialize entity resolver
    const entityResolver = new EntityResolver(
      { embed: (texts: string[]) => embeddingPipeline.embed(texts) },
      config.neo4j.uri,
      { username: config.neo4j.username, password: config.neo4j.password }
    );

    // Store dependencies
    this.deps = {
      db,
      es,
      embeddingPipeline,
      llmPipeline,
      entityResolver,
      esIndex: config.elasticsearch.index,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password }
    };

    // Create tools
    const ingestTool = createIngestDocumentTool({
      db,
      es,
      embeddingPipeline,
      llmPipeline,
      entityResolver,
      esIndex: config.elasticsearch.index
    });

    const findOverlapsTool = createFindOverlapsTool({
      db,
      es,
      embeddingPipeline,
      llmPipeline,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password },
      esIndex: config.elasticsearch.index
    });

    const consolidateTool = createConsolidateDocumentsTool({
      db,
      es,
      embeddingPipeline,
      llmPipeline,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password },
      esIndex: config.elasticsearch.index
    });

    const sourceOfTruthTool = createGetSourceOfTruthTool({
      db,
      es,
      embeddingPipeline,
      llmPipeline,
      esIndex: config.elasticsearch.index
    });

    const deprecateTool = createDeprecateDocumentTool({
      db,
      es,
      esIndex: config.elasticsearch.index
    });

    // Register tools with type assertion for execute function compatibility
    this.tools.set('ingest_document', { execute: (input: unknown) => ingestTool.execute(input as Parameters<typeof ingestTool.execute>[0]) });
    this.tools.set('find_overlaps', { execute: (input: unknown) => findOverlapsTool.execute(input as Parameters<typeof findOverlapsTool.execute>[0]) });
    this.tools.set('consolidate_documents', { execute: (input: unknown) => consolidateTool.execute(input as Parameters<typeof consolidateTool.execute>[0]) });
    this.tools.set('get_source_of_truth', { execute: (input: unknown) => sourceOfTruthTool.execute(input as Parameters<typeof sourceOfTruthTool.execute>[0]) });
    this.tools.set('deprecate_document', { execute: (input: unknown) => deprecateTool.execute(input as Parameters<typeof deprecateTool.execute>[0]) });

    console.error('MCP Document Consolidator server initialized');
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP Document Consolidator server running on stdio');
  }

  async shutdown(): Promise<void> {
    if (this.deps) {
      await this.deps.embeddingPipeline.shutdown();
      await this.deps.db.close();
    }
    await this.server.close();
  }
}

// Main entry point
async function main(): Promise<void> {
  const server = new DocumentConsolidatorServer();

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
