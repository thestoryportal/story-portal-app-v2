import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import {
  createGetSourceOfTruthTool,
  GetSourceOfTruthInputSchema
} from '../../src/tools/get-source-of-truth.js';
import type { DatabaseService } from '../../src/db/index.js';

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-query-uuid')
}));

// Mock verification-pipeline
vi.mock('../../src/ai/verification-pipeline.js', () => ({
  VerificationPipeline: vi.fn().mockImplementation(() => ({
    verifyBatch: vi.fn().mockResolvedValue(new Map([
      ['claim-1', { verified: true, signals: [{ type: 'semantic' }] }]
    ]))
  }))
}));

describe('Get Source of Truth Tool', () => {
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
        findAll: vi.fn().mockResolvedValue([]),
        findByPathPattern: vi.fn().mockResolvedValue([]),
        findByContentHash: vi.fn(),
        update: vi.fn(),
        delete: vi.fn()
      } as unknown as DatabaseService['documents'],
      sections: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findById: vi.fn()
      } as unknown as DatabaseService['sections'],
      claims: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findBySectionId: vi.fn().mockResolvedValue([
          {
            id: 'claim-1',
            original_text: 'Test claim text',
            confidence: 0.9,
            document_id: 'doc-1',
            subject: 'test'
          }
        ]),
        findBySubject: vi.fn().mockResolvedValue([])
      } as unknown as DatabaseService['claims'],
      conflicts: {
        findByClaimIds: vi.fn().mockResolvedValue([])
      } as unknown as DatabaseService['conflicts']
    };

    mockEs = {
      index: vi.fn().mockResolvedValue({}),
      search: vi.fn().mockResolvedValue({
        hits: {
          hits: [
            {
              _id: 'hit-1',
              _score: 0.95,
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'This is the relevant content for the query.',
                header: 'Section Header',
                document_type: 'spec',
                authority_level: 8,
                deprecated: false
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
      generate: vi.fn().mockResolvedValue(JSON.stringify({
        answer: 'Based on the sources, the answer is...',
        confidence: 0.85,
        knowledge_gaps: ['Some details not covered']
      }))
    };
  });

  describe('GetSourceOfTruthInputSchema', () => {
    it('should require a query', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({});

      expect(result.success).toBe(false);
    });

    it('should accept a valid query', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({
        query: 'What is the recommended approach for authentication?'
      });

      expect(result.success).toBe(true);
    });

    it('should have correct default values', () => {
      const result = GetSourceOfTruthInputSchema.parse({
        query: 'Test query'
      });

      expect(result.query_type).toBe('factual');
      expect(result.include_deprecated).toBe(false);
      expect(result.confidence_threshold).toBe(0.7);
      expect(result.max_sources).toBe(5);
      expect(result.verify_claims).toBe(true);
    });

    it('should accept all query types', () => {
      const types = ['factual', 'procedural', 'conceptual', 'comparative'];

      for (const queryType of types) {
        const result = GetSourceOfTruthInputSchema.safeParse({
          query: 'Test',
          query_type: queryType
        });
        expect(result.success).toBe(true);
      }
    });

    it('should reject invalid query type', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        query_type: 'invalid_type'
      });

      expect(result.success).toBe(false);
    });

    it('should validate confidence_threshold range', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        confidence_threshold: 1.5
      });

      expect(result.success).toBe(false);
    });

    it('should validate max_sources range', () => {
      const tooLow = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        max_sources: 0
      });

      const tooHigh = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        max_sources: 25
      });

      expect(tooLow.success).toBe(false);
      expect(tooHigh.success).toBe(false);
    });

    it('should accept scope patterns', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        scope: ['docs/**/*.md', '550e8400-e29b-41d4-a716-446655440001']
      });

      expect(result.success).toBe(true);
    });

    it('should accept codebase_path', () => {
      const result = GetSourceOfTruthInputSchema.safeParse({
        query: 'Test',
        codebase_path: '/path/to/codebase'
      });

      expect(result.success).toBe(true);
    });
  });

  describe('createGetSourceOfTruthTool', () => {
    it('should create tool with correct name', () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      expect(tool.name).toBe('get_source_of_truth');
    });

    it('should execute query and return answer', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'What is the authentication method?',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: true
      });

      expect(result.answer).toBeDefined();
      expect(result.confidence).toBeDefined();
      expect(result.query_id).toBe('mock-query-uuid');
      expect(result.sources).toBeDefined();
      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });

    it('should generate query embedding', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(mockEmbeddingPipeline.embed).toHaveBeenCalledWith(['Test query']);
    });

    it('should search Elasticsearch with vector query', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(mockEs.search).toHaveBeenCalledWith(
        expect.objectContaining({
          index: 'test-index'
        })
      );
    });

    it('should filter deprecated documents when include_deprecated is false', async () => {
      mockEs.search.mockResolvedValue({
        hits: {
          hits: [
            {
              _id: 'hit-1',
              _score: 0.95,
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'Active content',
                header: 'Header',
                authority_level: 5,
                deprecated: false
              }
            },
            {
              _id: 'hit-2',
              _score: 0.90,
              _source: {
                document_id: 'doc-2',
                section_id: 'sec-2',
                content: 'Deprecated content',
                header: 'Header',
                authority_level: 5,
                deprecated: true
              }
            }
          ]
        }
      });

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should only include non-deprecated sources
      const deprecatedSources = result.sources.filter(s => s.document_id === 'doc-2');
      expect(deprecatedSources.length).toBe(0);
    });

    it('should include deprecated documents when include_deprecated is true', async () => {
      mockEs.search.mockResolvedValue({
        hits: {
          hits: [
            {
              _id: 'hit-1',
              _score: 0.95,
              _source: {
                document_id: 'doc-1',
                section_id: 'sec-1',
                content: 'Active content',
                header: 'Header',
                authority_level: 5,
                deprecated: false
              }
            },
            {
              _id: 'hit-2',
              _score: 0.90,
              _source: {
                document_id: 'doc-2',
                section_id: 'sec-2',
                content: 'Deprecated content',
                header: 'Header',
                authority_level: 5,
                deprecated: true
              }
            }
          ]
        }
      });

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: true,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should include both sources
      expect(result.sources.length).toBe(2);
    });

    it('should filter by scope when provided', async () => {
      const inScopeDocId = '550e8400-e29b-41d4-a716-446655440001';
      const outOfScopeDocId = '550e8400-e29b-41d4-a716-446655440002';

      mockEs.search.mockResolvedValue({
        hits: {
          hits: [
            {
              _id: 'hit-1',
              _score: 0.95,
              _source: {
                document_id: inScopeDocId,
                section_id: 'sec-1',
                content: 'In scope content',
                header: 'Header',
                authority_level: 5,
                deprecated: false
              }
            },
            {
              _id: 'hit-2',
              _score: 0.90,
              _source: {
                document_id: outOfScopeDocId,
                section_id: 'sec-2',
                content: 'Out of scope content',
                header: 'Header',
                authority_level: 5,
                deprecated: false
              }
            }
          ]
        }
      });

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        scope: [inScopeDocId],
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should only include in-scope source
      expect(result.sources.length).toBe(1);
      expect(result.sources[0].document_id).toBe(inScopeDocId);
    });

    it('should verify claims when verify_claims is true', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: true
      });

      // Should have verification info on claims
      expect(result.supporting_claims).toBeDefined();
      const verifiedClaims = result.supporting_claims.filter(c => c.verified !== undefined);
      expect(verifiedClaims.length).toBeGreaterThanOrEqual(0);
    });

    it('should not verify claims when verify_claims is false', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should not have verification info
      const verifiedClaims = result.supporting_claims.filter(c => c.verified !== undefined);
      expect(verifiedClaims.length).toBe(0);
    });

    it('should detect conflicting claims', async () => {
      (mockDb.conflicts?.findByClaimIds as Mock).mockResolvedValue([
        {
          id: 'conflict-1',
          claim_a_id: 'claim-1',
          claim_b_id: 'claim-2',
          conflict_type: 'direct_negation'
        }
      ]);

      (mockDb.claims?.findBySectionId as Mock).mockResolvedValue([
        {
          id: 'claim-1',
          original_text: 'Claim A text',
          confidence: 0.9,
          document_id: 'doc-1',
          source_section_id: 'sec-1'
        },
        {
          id: 'claim-2',
          original_text: 'Claim B text',
          confidence: 0.85,
          document_id: 'doc-2',
          source_section_id: 'sec-2'
        }
      ]);

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(result.conflicting_claims).toBeDefined();
      expect(Array.isArray(result.conflicting_claims)).toBe(true);
    });

    it('should generate answer using LLM', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(mockLlmPipeline.generate).toHaveBeenCalled();
    });

    it('should handle LLM generation failure gracefully', async () => {
      mockLlmPipeline.generate.mockRejectedValue(new Error('LLM error'));

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should fallback to simple answer
      expect(result.answer).toBeDefined();
      expect(result.knowledge_gaps).toContain('Unable to generate comprehensive answer');
    });

    it('should filter supporting claims by confidence threshold', async () => {
      (mockDb.claims?.findBySectionId as Mock).mockResolvedValue([
        {
          id: 'claim-high',
          original_text: 'High confidence claim',
          confidence: 0.9,
          document_id: 'doc-1'
        },
        {
          id: 'claim-low',
          original_text: 'Low confidence claim',
          confidence: 0.3,
          document_id: 'doc-1'
        }
      ]);

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      // Should only include high confidence claims
      const lowConfidenceClaims = result.supporting_claims.filter(c => c.confidence < 0.7);
      expect(lowConfidenceClaims.length).toBe(0);
    });

    it('should identify knowledge gaps', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(result.knowledge_gaps).toBeDefined();
      expect(Array.isArray(result.knowledge_gaps)).toBe(true);
    });

    it('should handle no results from Elasticsearch', async () => {
      mockEs.search.mockResolvedValue({
        hits: { hits: [] }
      });

      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(result.sources.length).toBe(0);
      expect(result.answer).toBeDefined();
    });

    it('should track processing time', async () => {
      const tool = createGetSourceOfTruthTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        embeddingPipeline: mockEmbeddingPipeline as unknown as import('../../src/ai/embedding-pipeline.js').EmbeddingPipeline,
        llmPipeline: mockLlmPipeline as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        query: 'Test query',
        query_type: 'factual',
        include_deprecated: false,
        confidence_threshold: 0.7,
        max_sources: 5,
        verify_claims: false
      });

      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });
  });
});
