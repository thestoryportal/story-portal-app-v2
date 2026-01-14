// MCP Document Consolidator - Main Entry Point

// Configuration
export { loadConfig, getConfig, type Config } from './config.js';

// Types
export * from './types.js';

// Errors
export * from './errors.js';

// Database
export { createDatabaseService, type DatabaseService, type DatabaseConfig } from './db/index.js';

// Components
export {
  DocumentParser,
  ClaimExtractor,
  EntityResolver,
  ConflictDetector,
  MergeEngine
} from './components/index.js';

// AI Pipelines
export {
  EmbeddingPipeline,
  SimpleEmbedding,
  LLMPipeline,
  VerificationPipeline
} from './ai/index.js';

// Tools
export {
  createIngestDocumentTool,
  createFindOverlapsTool,
  createConsolidateDocumentsTool,
  createGetSourceOfTruthTool,
  createDeprecateDocumentTool,
  IngestDocumentInputSchema,
  IngestDocumentOutputSchema,
  FindOverlapsInputSchema,
  FindOverlapsOutputSchema,
  ConsolidateDocumentsInputSchema,
  ConsolidateDocumentsOutputSchema,
  GetSourceOfTruthInputSchema,
  GetSourceOfTruthOutputSchema,
  DeprecateDocumentInputSchema,
  DeprecateDocumentOutputSchema
} from './tools/index.js';
