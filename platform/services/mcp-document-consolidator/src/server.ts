#!/usr/bin/env node

import 'dotenv/config';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import { loadConfig } from './config.js';
import { createDatabaseService, type DatabaseService } from './db/index.js';
import { EmbeddingPipeline, SimpleEmbedding } from './ai/embedding-pipeline.js';
import { LLMPipeline, MockLLMPipeline } from './ai/llm-pipeline.js';
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

interface EmbeddingService {
  embed(texts: string[]): Promise<number[][]> | number[][];
  shutdown?(): Promise<void>;
}

type LLMService = LLMPipeline | MockLLMPipeline;

interface ServerDependencies {
  db: DatabaseService;
  embeddingPipeline: EmbeddingService;
  llmPipeline: LLMService;
  entityResolver: EntityResolver | null;
  neo4jEnabled: boolean;
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

    // Initialize embedding service (use fallback if disabled)
    let embeddingPipeline: EmbeddingService;
    if (config.embedding.enabled) {
      const realPipeline = new EmbeddingPipeline({
        pythonPath: config.embedding.pythonPath,
        modelName: config.embedding.model,
        batchSize: config.embedding.batchSize,
        cacheEnabled: config.embedding.cacheEnabled
      });
      await realPipeline.initialize();
      embeddingPipeline = realPipeline;
      console.error('Embedding pipeline initialized (Python)');
    } else {
      embeddingPipeline = new SimpleEmbedding();
      console.error('Embedding pipeline disabled - using simple fallback');
    }

    // Initialize LLM pipeline (mock if disabled)
    let llmPipeline: LLMService;
    if (config.ollama.enabled) {
      llmPipeline = new LLMPipeline({
        baseUrl: config.ollama.baseUrl,
        defaultModel: config.ollama.defaultModel,
        temperature: config.ollama.temperature,
        maxTokens: config.ollama.maxTokens,
        timeout: config.ollama.timeout
      });
      console.error('LLM pipeline initialized (Ollama)');
    } else {
      llmPipeline = new MockLLMPipeline();
      console.error('LLM pipeline disabled - using mock');
    }

    // Initialize entity resolver (null if Neo4j disabled)
    let entityResolver: EntityResolver | null = null;
    if (config.neo4j.enabled) {
      entityResolver = new EntityResolver(
        { embed: async (texts: string[]) => Promise.resolve(embeddingPipeline.embed(texts)).then(r => r) },
        config.neo4j.uri,
        { username: config.neo4j.username, password: config.neo4j.password }
      );
      console.error('Entity resolver initialized (Neo4j)');
    } else {
      console.error('Neo4j disabled - entity resolution unavailable');
    }

    // Store dependencies
    this.deps = {
      db,
      embeddingPipeline,
      llmPipeline,
      entityResolver,
      neo4jEnabled: config.neo4j.enabled,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password }
    };

    // Create tools (cast to any for type compatibility with mock implementations)
    const ingestTool = createIngestDocumentTool({
      db,
      embeddingPipeline: embeddingPipeline as any,
      llmPipeline: llmPipeline as any,
      entityResolver: entityResolver as any
    });

    const findOverlapsTool = createFindOverlapsTool({
      db,
      embeddingPipeline: embeddingPipeline as any,
      llmPipeline: llmPipeline as any,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password }
    });

    const consolidateTool = createConsolidateDocumentsTool({
      db,
      embeddingPipeline: embeddingPipeline as any,
      llmPipeline: llmPipeline as any,
      neo4jUri: config.neo4j.uri,
      neo4jAuth: { username: config.neo4j.username, password: config.neo4j.password }
    });

    const sourceOfTruthTool = createGetSourceOfTruthTool({
      db,
      embeddingPipeline: embeddingPipeline as any,
      llmPipeline: llmPipeline as any
    });

    const deprecateTool = createDeprecateDocumentTool({
      db
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
      if (this.deps.embeddingPipeline.shutdown) {
        await this.deps.embeddingPipeline.shutdown();
      }
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
    // Safely log error to avoid Node.js inspect issues with complex error objects
    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;
    console.error('Failed to start server:', errorMessage);
    if (errorStack) {
      console.error(errorStack);
    }
    process.exit(1);
  }
}

main().catch((error) => {
  const errorMessage = error instanceof Error ? error.message : String(error);
  console.error('Unhandled error:', errorMessage);
  process.exit(1);
});
