import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import {
  createConsolidateDocumentsTool,
  ConsolidateDocumentsInputSchema
} from '../../src/tools/consolidate-documents.js';
import type { DatabaseService } from '../../src/db/index.js';

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-uuid-123')
}));

// Mock merge-engine
vi.mock('../../src/components/merge-engine.js', () => ({
  MergeEngine: vi.fn().mockImplementation(() => ({
    merge: vi.fn().mockResolvedValue({
      sections: [
        {
          header: 'Section 1',
          content: 'Merged content',
          provenance: [{ source_document_id: 'doc-1' }]
        }
      ]
    })
  }))
}));

// Mock conflict-detector
vi.mock('../../src/components/conflict-detector.js', () => ({
  ConflictDetector: vi.fn().mockImplementation(() => ({
    detectConflicts: vi.fn().mockResolvedValue([])
  }))
}));

describe('Consolidate Documents Tool', () => {
  let mockDb: Partial<DatabaseService>;
  let mockEmbeddingPipeline: { embed: Mock };
  let mockLlmPipeline: { generate: Mock };

  beforeEach(() => {
    vi.clearAllMocks();

    mockDb = {
      documents: {
        create: vi.fn().mockResolvedValue('new-doc-id'),
        findById: vi.fn().mockImplementation((id: string) => Promise.resolve({
          id,
          title: `Document ${id}`,
          source_path: `/path/to/${id}.md`,
          content_hash: 'hash123',
          format: 'markdown',
          document_type: 'spec',
          raw_content: '# Test\n\nContent here',
          authority_level: 5,
          frontmatter: { authority_level: 5, created_at: '2024-01-01' },
          created_at: new Date()
        })),
        findAll: vi.fn().mockResolvedValue([]),
        findByPathPattern: vi.fn().mockResolvedValue([]),
        findByContentHash: vi.fn(),
        update: vi.fn(),
        delete: vi.fn()
      } as unknown as DatabaseService['documents'],
      sections: {
        create: vi.fn().mockResolvedValue('sec-1'),
        findByDocumentId: vi.fn().mockResolvedValue([
          { id: 'sec-1', header: 'Section 1', content: 'Content', level: 1, start_line: 1, end_line: 5 }
        ]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findById: vi.fn()
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
      } as unknown as DatabaseService['supersessions'],
      consolidations: {
        create: vi.fn().mockResolvedValue('cons-1'),
        findByClusterId: vi.fn().mockResolvedValue(null)
      } as unknown as DatabaseService['consolidations']
    };

    mockEmbeddingPipeline = {
      embed: vi.fn().mockResolvedValue([[0.1, 0.2, 0.3]])
    };

    mockLlmPipeline = {
      generate: vi.fn().mockResolvedValue('{"result": "success"}')
    };
  });

  describe('ConsolidateDocumentsInputSchema', () => {
    it('should require at least one source selector', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        strategy: 'smart'
      });

      expect(result.success).toBe(false);
    });

    it('should accept document_ids', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002']
      });

      expect(result.success).toBe(true);
    });

    it('should accept scope patterns', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        scope: ['docs/**/*.md']
      });

      expect(result.success).toBe(true);
    });

    it('should accept cluster_id', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        cluster_id: '550e8400-e29b-41d4-a716-446655440003'
      });

      expect(result.success).toBe(true);
    });

    it('should validate strategy enum', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001'],
        strategy: 'invalid_strategy'
      });

      expect(result.success).toBe(false);
    });

    it('should have correct default values', () => {
      const result = ConsolidateDocumentsInputSchema.parse({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002']
      });

      expect(result.strategy).toBe('smart');
      expect(result.conflict_threshold).toBe(0.7);
      expect(result.auto_resolve_below).toBe(0.3);
      expect(result.require_human_above).toBe(0.9);
      expect(result.output_format).toBe('markdown');
      expect(result.include_provenance).toBe(true);
      expect(result.dry_run).toBe(false);
    });

    it('should validate conflict_threshold range', () => {
      const result = ConsolidateDocumentsInputSchema.safeParse({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001'],
        conflict_threshold: 1.5
      });

      expect(result.success).toBe(false);
    });

    it('should accept all output formats', () => {
      const formats = ['markdown', 'json', 'yaml'];

      for (const format of formats) {
        const result = ConsolidateDocumentsInputSchema.safeParse({
          document_ids: ['550e8400-e29b-41d4-a716-446655440001'],
          output_format: format
        });
        expect(result.success).toBe(true);
      }
    });
  });

  describe('createConsolidateDocumentsTool', () => {
    it('should create tool with correct name', () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      expect(tool.name).toBe('consolidate_documents');
    });

    it('should throw error if less than 2 documents', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      await expect(tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: false
      })).rejects.toThrow('At least 2 documents required');
    });

    it('should execute dry run without creating documents', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: true
      });

      expect(result.consolidation_id).toBe('mock-uuid-123');
      expect(result.source_documents).toHaveLength(2);
      expect(mockDb.documents?.create).not.toHaveBeenCalled();
    });

    it('should execute consolidation with merge', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: false
      });

      expect(result.consolidation_id).toBe('mock-uuid-123');
      expect(result.status).toBe('completed');
      expect(result.output_document).toBeDefined();
      expect(mockDb.documents?.create).toHaveBeenCalled();
      expect(mockDb.consolidations?.create).toHaveBeenCalled();
    });

    it('should resolve scope patterns to document IDs', async () => {
      (mockDb.documents?.findByPathPattern as Mock).mockResolvedValue([
        { id: 'doc-from-pattern-1' },
        { id: 'doc-from-pattern-2' }
      ]);

      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        scope: ['docs/**/*.md'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: true
      });

      expect(mockDb.documents?.findByPathPattern).toHaveBeenCalledWith('docs/**/*.md');
      expect(result.source_documents).toHaveLength(2);
    });

    it('should use cluster_id to resolve documents', async () => {
      (mockDb.consolidations?.findByClusterId as Mock).mockResolvedValue({
        source_document_ids: ['cluster-doc-1', 'cluster-doc-2', 'cluster-doc-3']
      });

      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        cluster_id: '550e8400-e29b-41d4-a716-446655440099',
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: true
      });

      expect(mockDb.consolidations?.findByClusterId).toHaveBeenCalledWith('550e8400-e29b-41d4-a716-446655440099');
      expect(result.source_documents).toHaveLength(3);
    });

    it('should generate JSON output format', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'json',
        include_provenance: true,
        dry_run: false
      });

      expect(result.output_document?.format).toBe('json');
      expect(() => JSON.parse(result.output_document?.content || '')).not.toThrow();
    });

    it('should generate YAML output format', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'yaml',
        include_provenance: true,
        dry_run: false
      });

      expect(result.output_document?.format).toBe('yaml');
      expect(result.output_document?.content).toContain('title:');
    });

    it('should include provenance map when requested', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: false
      });

      expect(result.provenance_map).toBeDefined();
    });

    it('should track processing time', async () => {
      const tool = createConsolidateDocumentsTool({
        db: mockDb as DatabaseService,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' }
      });

      const result = await tool.execute({
        document_ids: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002'],
        strategy: 'smart',
        conflict_threshold: 0.7,
        auto_resolve_below: 0.3,
        require_human_above: 0.9,
        output_format: 'markdown',
        include_provenance: true,
        dry_run: true
      });

      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });
  });
});
