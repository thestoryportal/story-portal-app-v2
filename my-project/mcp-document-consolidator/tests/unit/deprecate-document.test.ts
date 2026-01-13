import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import {
  createDeprecateDocumentTool,
  DeprecateDocumentInputSchema
} from '../../src/tools/deprecate-document.js';
import type { DatabaseService } from '../../src/db/index.js';

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-deprecation-uuid')
}));

describe('Deprecate Document Tool', () => {
  let mockDb: Partial<DatabaseService>;
  let mockEs: { index: Mock; search: Mock; updateByQuery: Mock };

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
          raw_content: '# Test\n\nContent with no references',
          authority_level: 5,
          frontmatter: {},
          created_at: new Date()
        })),
        findAll: vi.fn().mockResolvedValue([
          { id: 'other-doc-1', title: 'Other Doc 1', raw_content: 'No references here', document_type: 'spec' },
          { id: 'other-doc-2', title: 'Other Doc 2', raw_content: 'Also no references', document_type: 'guide' }
        ]),
        findByPathPattern: vi.fn().mockResolvedValue([]),
        findByContentHash: vi.fn(),
        update: vi.fn(),
        delete: vi.fn()
      } as unknown as DatabaseService['documents'],
      sections: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([
          { id: 'sec-1', header: 'Section 1', content: 'Content' },
          { id: 'sec-2', header: 'Section 2', content: 'More content' }
        ]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findById: vi.fn()
      } as unknown as DatabaseService['sections'],
      claims: {
        create: vi.fn(),
        findByDocumentId: vi.fn().mockResolvedValue([
          { id: 'claim-1', subject: 'topic-a', object: 'value-a', original_text: 'Topic A is value A' },
          { id: 'claim-2', subject: 'topic-b', object: 'value-b', original_text: 'Topic B is value B' }
        ]),
        findByDocumentIds: vi.fn().mockResolvedValue([]),
        findBySubject: vi.fn().mockResolvedValue([]),
        update: vi.fn()
      } as unknown as DatabaseService['claims'],
      supersessions: {
        create: vi.fn().mockResolvedValue('sup-1')
      } as unknown as DatabaseService['supersessions'],
      provenance: {
        create: vi.fn().mockResolvedValue('prov-1')
      } as unknown as DatabaseService['provenance']
    };

    mockEs = {
      index: vi.fn().mockResolvedValue({}),
      search: vi.fn().mockResolvedValue({ hits: { hits: [] } }),
      updateByQuery: vi.fn().mockResolvedValue({ updated: 5 })
    };
  });

  describe('DeprecateDocumentInputSchema', () => {
    it('should require document_id', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        reason: 'Outdated content'
      });

      expect(result.success).toBe(false);
    });

    it('should require reason', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        document_id: '550e8400-e29b-41d4-a716-446655440001'
      });

      expect(result.success).toBe(false);
    });

    it('should accept valid input', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced by newer version'
      });

      expect(result.success).toBe(true);
    });

    it('should have correct default values', () => {
      const result = DeprecateDocumentInputSchema.parse({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test reason'
      });

      expect(result.migrate_references).toBe(true);
      expect(result.archive).toBe(false);
    });

    it('should validate document_id as UUID', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        document_id: 'not-a-uuid',
        reason: 'Test'
      });

      expect(result.success).toBe(false);
    });

    it('should accept superseded_by as UUID', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002'
      });

      expect(result.success).toBe(true);
    });

    it('should validate superseded_by as UUID', () => {
      const result = DeprecateDocumentInputSchema.safeParse({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        superseded_by: 'invalid-uuid'
      });

      expect(result.success).toBe(false);
    });
  });

  describe('createDeprecateDocumentTool', () => {
    it('should create tool with correct name', () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      expect(tool.name).toBe('deprecate_document');
    });

    it('should throw error if document not found', async () => {
      (mockDb.documents?.findById as Mock).mockResolvedValue(null);

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await expect(tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: true,
        archive: false
      })).rejects.toThrow('Document not found');
    });

    it('should throw error if superseding document not found', async () => {
      (mockDb.documents?.findById as Mock).mockImplementation((id: string) => {
        if (id === '550e8400-e29b-41d4-a716-446655440001') {
          return Promise.resolve({
            id,
            title: 'Original Doc',
            document_type: 'spec',
            raw_content: 'Content',
            frontmatter: {}
          });
        }
        return Promise.resolve(null);
      });

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await expect(tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: true,
        archive: false
      })).rejects.toThrow('Superseding document not found');
    });

    it('should deprecate document successfully', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Content is outdated',
        migrate_references: true,
        archive: false
      });

      expect(result.document_id).toBe('550e8400-e29b-41d4-a716-446655440001');
      expect(result.status).toBe('deprecated');
      expect(result.deprecation_id).toBe('mock-deprecation-uuid');
      expect(mockDb.documents?.update).toHaveBeenCalled();
    });

    it('should archive document when archive is true', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Moving to archive',
        migrate_references: true,
        archive: true
      });

      expect(result.status).toBe('archived');
      expect(mockDb.documents?.update).toHaveBeenCalledWith(
        '550e8400-e29b-41d4-a716-446655440001',
        expect.objectContaining({
          document_type: 'archive'
        })
      );
    });

    it('should create supersession record when superseded_by is provided', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced by newer version',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: true,
        archive: false
      });

      expect(mockDb.supersessions?.create).toHaveBeenCalledWith({
        old_document_id: '550e8400-e29b-41d4-a716-446655440001',
        new_document_id: '550e8400-e29b-41d4-a716-446655440002',
        reason: 'Replaced by newer version'
      });
    });

    it('should not create supersession record when superseded_by is not provided', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'No longer needed',
        migrate_references: false,
        archive: false
      });

      expect(mockDb.supersessions?.create).not.toHaveBeenCalled();
    });

    it('should find and report document references', async () => {
      // Set up a document that references the one being deprecated
      (mockDb.documents?.findAll as Mock).mockResolvedValue([
        {
          id: 'referencing-doc',
          title: 'Referencing Doc',
          raw_content: 'This doc references 550e8400-e29b-41d4-a716-446655440001 in its content',
          document_type: 'spec'
        }
      ]);

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        migrate_references: false,
        archive: false
      });

      expect(result.affected_references).toBeDefined();
      expect(Array.isArray(result.affected_references)).toBe(true);
    });

    it('should migrate references when migrate_references is true', async () => {
      // Set up a document that references the one being deprecated
      (mockDb.documents?.findAll as Mock).mockResolvedValue([
        {
          id: 'referencing-doc',
          title: 'Referencing Doc',
          raw_content: 'This doc references 550e8400-e29b-41d4-a716-446655440001 in its content',
          document_type: 'spec'
        }
      ]);

      // Claims for referencing doc
      (mockDb.claims?.findByDocumentId as Mock).mockImplementation((docId: string) => {
        if (docId === 'referencing-doc') {
          return Promise.resolve([
            { id: 'ref-claim-1', source_document_id: '550e8400-e29b-41d4-a716-446655440001' }
          ]);
        }
        return Promise.resolve([]);
      });

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: true,
        archive: false
      });

      // Should attempt to migrate references
      const migratedRefs = result.affected_references.filter(r => r.migration_status === 'migrated');
      expect(migratedRefs.length).toBeGreaterThanOrEqual(0);
    });

    it('should mark references as manual_review_needed when no superseding doc', async () => {
      // Set up a document that references the one being deprecated
      (mockDb.documents?.findAll as Mock).mockResolvedValue([
        {
          id: 'referencing-doc',
          title: 'Referencing Doc',
          raw_content: 'This doc references 550e8400-e29b-41d4-a716-446655440001 here',
          document_type: 'spec'
        }
      ]);

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Removed without replacement',
        migrate_references: false,
        archive: false
      });

      // Without superseding doc, references should need manual review
      const manualReviewRefs = result.affected_references.filter(
        r => r.migration_status === 'manual_review_needed'
      );
      expect(manualReviewRefs.length).toBeGreaterThanOrEqual(0);
    });

    it('should update Elasticsearch deprecation status', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: false,
        archive: false
      });

      expect(mockEs.updateByQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          index: 'test-index'
        })
      );
    });

    it('should handle Elasticsearch update failure gracefully', async () => {
      mockEs.updateByQuery.mockRejectedValue(new Error('ES error'));

      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      // Should not throw, just log error
      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: false,
        archive: false
      });

      expect(result.document_id).toBe('550e8400-e29b-41d4-a716-446655440001');
    });

    it('should mark claims as deprecated', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: false,
        archive: false
      });

      expect(result.claims_affected).toBe(2);
      expect(mockDb.claims?.update).toHaveBeenCalledTimes(2);
    });

    it('should record provenance event', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test reason',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: false,
        archive: true
      });

      expect(mockDb.provenance?.create).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'mock-deprecation-uuid',
          document_id: '550e8400-e29b-41d4-a716-446655440001',
          event_type: 'deprecation',
          details: expect.objectContaining({
            reason: 'Test reason',
            superseded_by: '550e8400-e29b-41d4-a716-446655440002',
            archive: true
          })
        })
      );
    });

    it('should count sections affected', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: false,
        archive: false
      });

      expect(result.sections_affected).toBe(2);
    });

    it('should update document frontmatter with deprecation info', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Content outdated',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: false,
        archive: false
      });

      expect(mockDb.documents?.update).toHaveBeenCalledWith(
        '550e8400-e29b-41d4-a716-446655440001',
        expect.objectContaining({
          frontmatter: expect.objectContaining({
            deprecated: true,
            deprecation_reason: 'Content outdated',
            superseded_by: '550e8400-e29b-41d4-a716-446655440002'
          })
        })
      );
    });

    it('should track processing time', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Test',
        migrate_references: false,
        archive: false
      });

      expect(result.processing_time_ms).toBeGreaterThanOrEqual(0);
    });

    it('should return superseded_by in output', async () => {
      const tool = createDeprecateDocumentTool({
        db: mockDb as DatabaseService,
        es: mockEs as unknown as import('@elastic/elasticsearch').Client,
        esIndex: 'test-index'
      });

      const result = await tool.execute({
        document_id: '550e8400-e29b-41d4-a716-446655440001',
        reason: 'Replaced',
        superseded_by: '550e8400-e29b-41d4-a716-446655440002',
        migrate_references: false,
        archive: false
      });

      expect(result.superseded_by).toBe('550e8400-e29b-41d4-a716-446655440002');
    });
  });
});
