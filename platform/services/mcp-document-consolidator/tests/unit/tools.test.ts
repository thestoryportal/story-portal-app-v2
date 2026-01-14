import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import {
  createIngestDocumentTool,
  IngestDocumentInputSchema
} from '../../src/tools/ingest-document.js';
import type { DatabaseService } from '../../src/db/index.js';

// Mock fs
vi.mock('fs/promises', () => ({
  default: {
    readFile: vi.fn()
  }
}));

describe('Ingest Document Tool', () => {
  let mockDb: Partial<DatabaseService>;
  let mockEmbeddingPipeline: { embed: Mock };
  let mockLlmPipeline: { generate: Mock };
  let mockEntityResolver: { resolve: Mock; linkClaimToEntity: Mock };

  beforeEach(() => {
    vi.clearAllMocks();

    mockDb = {
      documents: {
        create: vi.fn().mockResolvedValue('doc-1'),
        findById: vi.fn(),
        findAll: vi.fn(),
        findByPathPattern: vi.fn(),
        findByContentHash: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
        updateEmbedding: vi.fn().mockResolvedValue(undefined),
        findSimilar: vi.fn().mockResolvedValue([])
      } as unknown as DatabaseService['documents'],
      sections: {
        create: vi.fn().mockResolvedValue('sec-1'),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findById: vi.fn(),
        updateEmbedding: vi.fn().mockResolvedValue(undefined)
      } as unknown as DatabaseService['sections'],
      claims: {
        create: vi.fn().mockResolvedValue('claim-1'),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findBySubject: vi.fn().mockResolvedValue([])
      } as unknown as DatabaseService['claims'],
      documentTags: {
        add: vi.fn(),
        remove: vi.fn(),
        findByDocumentId: vi.fn(),
        findDocumentsByTag: vi.fn()
      } as unknown as DatabaseService['documentTags'],
      supersessions: {
        create: vi.fn().mockResolvedValue('sup-1')
      } as unknown as DatabaseService['supersessions']
    };

    mockEmbeddingPipeline = {
      embed: vi.fn().mockResolvedValue([[0.1, 0.2, 0.3]])
    };

    mockLlmPipeline = {
      generate: vi.fn().mockResolvedValue('{"claims": []}')
    };

    mockEntityResolver = {
      resolve: vi.fn().mockResolvedValue(new Map()),
      linkClaimToEntity: vi.fn()
    };
  });

  describe('IngestDocumentInputSchema', () => {
    it('should require at least one content source', () => {
      const result = IngestDocumentInputSchema.safeParse({
        document_type: 'spec'
      });

      expect(result.success).toBe(false);
    });

    it('should accept file_path', () => {
      const result = IngestDocumentInputSchema.safeParse({
        file_path: '/path/to/doc.md',
        document_type: 'spec'
      });

      expect(result.success).toBe(true);
    });

    it('should accept content', () => {
      const result = IngestDocumentInputSchema.safeParse({
        content: '# My Document',
        document_type: 'guide'
      });

      expect(result.success).toBe(true);
    });

    it('should accept url', () => {
      const result = IngestDocumentInputSchema.safeParse({
        url: 'https://example.com/doc.md',
        document_type: 'reference'
      });

      expect(result.success).toBe(true);
    });

    it('should validate document_type enum', () => {
      const result = IngestDocumentInputSchema.safeParse({
        content: '# Test',
        document_type: 'invalid_type'
      });

      expect(result.success).toBe(false);
    });

    it('should validate authority_level range', () => {
      const result = IngestDocumentInputSchema.safeParse({
        content: '# Test',
        document_type: 'spec',
        authority_level: 15
      });

      expect(result.success).toBe(false);
    });
  });

  describe('createIngestDocumentTool', () => {
    it('should create tool with correct name', () => {
      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      expect(tool.name).toBe('ingest_document');
    });

    it('should execute with inline content', async () => {
      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      const result = await tool.execute({
        content: '# Test Document\n\nThis is test content.',
        document_type: 'spec',
        tags: ['test'],
        authority_level: 5,
        supersedes: [],
        extract_claims: false,
        generate_embeddings: false,
        build_entity_graph: false
      });

      expect(result.document_id).toBe('doc-1');
      expect(result.sections_extracted).toBeGreaterThanOrEqual(1);
      expect(mockDb.documents?.create).toHaveBeenCalled();
    });

    it('should execute with file path', async () => {
      const fs = await import('fs/promises');
      (fs.default.readFile as Mock).mockResolvedValueOnce('# File Content\n\nText here.');

      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      const result = await tool.execute({
        file_path: '/path/to/doc.md',
        document_type: 'guide',
        tags: [],
        authority_level: 5,
        supersedes: [],
        extract_claims: false,
        generate_embeddings: false,
        build_entity_graph: false
      });

      expect(fs.default.readFile).toHaveBeenCalledWith('/path/to/doc.md', 'utf-8');
      expect(result.document_id).toBe('doc-1');
    });

    it('should add tags to document', async () => {
      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      await tool.execute({
        content: '# Test',
        document_type: 'spec',
        tags: ['important', 'v2'],
        authority_level: 5,
        supersedes: [],
        extract_claims: false,
        generate_embeddings: false,
        build_entity_graph: false
      });

      expect(mockDb.documentTags?.add).toHaveBeenCalledWith('doc-1', 'important');
      expect(mockDb.documentTags?.add).toHaveBeenCalledWith('doc-1', 'v2');
    });

    it('should generate embeddings when enabled', async () => {
      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      const result = await tool.execute({
        content: '# Test',
        document_type: 'spec',
        tags: [],
        authority_level: 5,
        supersedes: [],
        extract_claims: false,
        generate_embeddings: true,
        build_entity_graph: false
      });

      expect(mockEmbeddingPipeline.embed).toHaveBeenCalled();
      expect(result.embeddings_generated).toBeGreaterThan(0);
    });

    it('should handle supersession', async () => {
      const tool = createIngestDocumentTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        entityResolver: mockEntityResolver as unknown as import('../../src/components/entity-resolver.js').EntityResolver
      });

      await tool.execute({
        content: '# New Version',
        document_type: 'spec',
        tags: [],
        authority_level: 5,
        supersedes: ['550e8400-e29b-41d4-a716-446655440000'],
        extract_claims: false,
        generate_embeddings: false,
        build_entity_graph: false
      });

      expect(mockDb.supersessions?.create).toHaveBeenCalledWith(
        expect.objectContaining({
          old_document_id: '550e8400-e29b-41d4-a716-446655440000',
          new_document_id: 'doc-1'
        })
      );
    });
  });
});

describe('Tool Schema Validation', () => {
  describe('IngestDocumentInputSchema', () => {
    it('should have default values', () => {
      const result = IngestDocumentInputSchema.parse({
        content: '# Test',
        document_type: 'spec'
      });

      expect(result.tags).toEqual([]);
      expect(result.authority_level).toBe(5);
      expect(result.supersedes).toEqual([]);
      expect(result.extract_claims).toBe(true);
      expect(result.generate_embeddings).toBe(true);
      expect(result.build_entity_graph).toBe(true);
    });

    it('should accept all document types', () => {
      const types = ['spec', 'guide', 'handoff', 'prompt', 'report', 'reference', 'decision', 'archive'];

      for (const docType of types) {
        const result = IngestDocumentInputSchema.safeParse({
          content: '# Test',
          document_type: docType
        });
        expect(result.success).toBe(true);
      }
    });
  });
});
