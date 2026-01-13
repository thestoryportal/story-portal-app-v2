import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import {
  createFindOverlapsTool,
  FindOverlapsInputSchema
} from '../../src/tools/find-overlaps.js';
import type { DatabaseService } from '../../src/db/index.js';

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-cluster-uuid')
}));

// Mock conflict-detector
vi.mock('../../src/components/conflict-detector.js', () => ({
  ConflictDetector: vi.fn().mockImplementation(() => ({
    detectConflicts: vi.fn().mockResolvedValue([])
  }))
}));

describe('Find Overlaps Tool', () => {
  let mockDb: Partial<DatabaseService>;
  let mockEs: { index: Mock; search: Mock };
  let mockEmbeddingPipeline: { embed: Mock };
  let mockLlmPipeline: { generate: Mock };

  beforeEach(() => {
    vi.clearAllMocks();

    mockDb = {
      documents: {
        create: vi.fn(),
        findById: vi.fn().mockImplementation((id: string) => Promise.resolve({
          id,
          title: `Document ${id}`,
          source_path: `/path/to/${id}.md`,
          content_hash: 'hash123',
          format: 'markdown',
          document_type: 'spec',
          raw_content: '# Test\n\nContent',
          authority_level: 5,
          frontmatter: {},
          created_at: new Date()
        })),
        findAll: vi.fn().mockResolvedValue([
          { id: 'doc-1', title: 'Doc 1', document_type: 'spec' },
          { id: 'doc-2', title: 'Doc 2', document_type: 'guide' }
        ]),
        findByPathPattern: vi.fn().mockResolvedValue([]),
        findByContentHash: vi.fn(),
        update: vi.fn(),
        delete: vi.fn()
      } as unknown as DatabaseService['documents'],
      sections: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([
          { id: 'sec-1', document_id: 'doc-1', header: 'Section 1', content: 'Content 1' },
          { id: 'sec-2', document_id: 'doc-2', header: 'Section 2', content: 'Content 2' }
        ]),
        findById: vi.fn()
      } as unknown as DatabaseService['sections'],
      claims: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findBySubject: vi.fn().mockResolvedValue([])
      } as unknown as DatabaseService['claims']
    };

    mockEs = {
      index: vi.fn().mockResolvedValue({}),
      search: vi.fn().mockResolvedValue({
        hits: {
          hits: [
            {
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'Test content 1',
                header: 'Section 1',
                embedding: [0.1, 0.2, 0.3]
              }
            },
            {
              _source: {
                document_id: 'doc-2',
                section_id: 'sec-2',
                content: 'Test content 2',
                header: 'Section 2',
                embedding: [0.15, 0.25, 0.35]
              }
            }
          ]
        }
      })
    };

    mockEmbeddingPipeline = {
      embed: vi.fn().mockResolvedValue([[0.1, 0.2, 0.3]])
    };

    mockLlmPipeline = {
      generate: vi.fn().mockResolvedValue('{"result": "success"}')
    };
  });

  describe('FindOverlapsInputSchema', () => {
    it('should accept empty input with defaults', () => {
      const result = FindOverlapsInputSchema.safeParse({});

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.similarity_threshold).toBe(0.80);
        expect(result.data.include_archived).toBe(false);
      }
    });

    it('should accept scope with document IDs', () => {
      const result = FindOverlapsInputSchema.safeParse({
        scope: ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002']
      });

      expect(result.success).toBe(true);
    });

    it('should accept scope with glob patterns', () => {
      const result = FindOverlapsInputSchema.safeParse({
        scope: ['docs/**/*.md', 'specs/*.yaml']
      });

      expect(result.success).toBe(true);
    });

    it('should validate similarity_threshold range', () => {
      const result = FindOverlapsInputSchema.safeParse({
        similarity_threshold: 1.5
      });

      expect(result.success).toBe(false);
    });

    it('should accept valid conflict_types', () => {
      const result = FindOverlapsInputSchema.safeParse({
        conflict_types: ['direct_negation', 'value_conflict']
      });

      expect(result.success).toBe(true);
    });

    it('should reject invalid conflict_types', () => {
      const result = FindOverlapsInputSchema.safeParse({
        conflict_types: ['invalid_type']
      });

      expect(result.success).toBe(false);
    });

    it('should accept all valid conflict type values', () => {
      const allTypes = ['direct_negation', 'value_conflict', 'temporal_conflict', 'scope_conflict', 'implication_conflict'];

      const result = FindOverlapsInputSchema.safeParse({
        conflict_types: allTypes
      });

      expect(result.success).toBe(true);
    });
  });

  describe('createFindOverlapsTool', () => {
    it('should create tool with correct name', () => {
      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      expect(tool.name).toBe('find_overlaps');
    });

    it('should execute with default scope (all documents)', async () => {
      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(mockDb.documents?.findAll).toHaveBeenCalled();
      expect(result.overlap_clusters).toBeDefined();
      expect(result.conflict_pairs).toBeDefined();
      expect(result.redundancy_score).toBeDefined();
      expect(result.recommendations).toBeDefined();
      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });

    it('should resolve UUID scope to document IDs', async () => {
      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      await tool.execute({
        scope: ['550e8400-e29b-41d4-a716-446655440001'],
        similarity_threshold: 0.80,
        include_archived: false
      });

      // Should not call findByPathPattern for UUIDs
      expect(mockDb.documents?.findByPathPattern).not.toHaveBeenCalled();
    });

    it('should resolve glob patterns to document IDs', async () => {
      (mockDb.documents?.findByPathPattern as Mock).mockResolvedValue([
        { id: 'pattern-doc-1' },
        { id: 'pattern-doc-2' }
      ]);

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      await tool.execute({
        scope: ['docs/**/*.md'],
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(mockDb.documents?.findByPathPattern).toHaveBeenCalledWith('docs/**/*.md');
    });

    it('should filter archived documents when include_archived is false', async () => {
      (mockDb.documents?.findAll as Mock).mockResolvedValue([
        { id: 'doc-1', title: 'Doc 1', document_type: 'spec' },
        { id: 'doc-2', title: 'Doc 2', document_type: 'archive' }
      ]);

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      // Should filter out archived documents
      expect(mockDb.sections?.findByDocumentIds).toHaveBeenCalledWith(['doc-1']);
    });

    it('should include archived documents when include_archived is true', async () => {
      (mockDb.documents?.findAll as Mock).mockResolvedValue([
        { id: 'doc-1', title: 'Doc 1', document_type: 'spec' },
        { id: 'doc-2', title: 'Doc 2', document_type: 'archive' }
      ]);

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      await tool.execute({
        similarity_threshold: 0.80,
        include_archived: true
      });

      // Should include both documents
      expect(mockDb.sections?.findByDocumentIds).toHaveBeenCalledWith(['doc-1', 'doc-2']);
    });

    it('should detect overlap clusters from similar embeddings', async () => {
      // Set up ES to return similar sections (high similarity)
      mockEs.search.mockResolvedValue({
        hits: {
          hits: [
            {
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'Test content',
                header: 'Similar Section',
                embedding: [0.5, 0.5, 0.5]
              }
            },
            {
              _source: {
                document_id: 'doc-2',
                section_id: 'sec-2',
                content: 'Test content similar',
                header: 'Similar Section',
                embedding: [0.51, 0.49, 0.5] // Very similar embedding
              }
            }
          ]
        }
      });

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(result.overlap_clusters).toBeDefined();
      expect(Array.isArray(result.overlap_clusters)).toBe(true);
    });

    it('should generate recommendations for overlapping content', async () => {
      // Set up mock with highly similar content
      mockEs.search.mockResolvedValue({
        hits: {
          hits: [
            {
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'Content A',
                header: 'Header',
                embedding: [1, 0, 0]
              }
            },
            {
              _source: {
                document_id: 'doc-2',
                section_id: 'sec-2',
                content: 'Content A copy',
                header: 'Header',
                embedding: [0.99, 0.01, 0]
              }
            }
          ]
        }
      });

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(result.recommendations).toBeDefined();
      expect(Array.isArray(result.recommendations)).toBe(true);
    });

    it('should calculate redundancy score', async () => {
      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(typeof result.redundancy_score).toBe('number');
      expect(result.redundancy_score).toBeGreaterThanOrEqual(0);
      expect(result.redundancy_score).toBeLessThanOrEqual(100);
    });

    it('should filter conflicts by type', async () => {
      // Import and mock conflict detector with conflicts
      const { ConflictDetector } = await import('../../src/components/conflict-detector.js');
      (ConflictDetector as Mock).mockImplementation(() => ({
        detectConflicts: vi.fn().mockResolvedValue([
          {
            id: 'conflict-1',
            conflict_type: 'direct_negation',
            claim_a: { id: 'claim-1', document_id: 'doc-1', text: 'A is true' },
            claim_b: { id: 'claim-2', document_id: 'doc-2', text: 'A is false' },
            strength: 0.9,
            resolution_hints: ['Review both sources']
          },
          {
            id: 'conflict-2',
            conflict_type: 'value_conflict',
            claim_a: { id: 'claim-3', document_id: 'doc-1', text: 'X = 10' },
            claim_b: { id: 'claim-4', document_id: 'doc-2', text: 'X = 20' },
            strength: 0.8,
            resolution_hints: ['Check latest version']
          }
        ])
      }));

      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false,
        conflict_types: ['direct_negation']
      });

      // Should only include direct_negation conflicts
      const negationConflicts = result.conflict_pairs.filter(c => c.conflict_type === 'direct_negation');
      const valueConflicts = result.conflict_pairs.filter(c => c.conflict_type === 'value_conflict');

      expect(negationConflicts.length).toBeGreaterThanOrEqual(0);
      // value_conflict should be filtered out
      expect(valueConflicts.length).toBe(0);
    });

    it('should track processing time', async () => {
      const tool = createFindOverlapsTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        neo4jUri: 'bolt://localhost:7687',
        neo4jAuth: { username: 'neo4j', password: 'password' },
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        similarity_threshold: 0.80,
        include_archived: false
      });

      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });
  });
});
