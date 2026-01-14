import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { DatabaseService, createDatabaseService } from '../../src/db/index.js';

// Mock pg
vi.mock('pg', () => {
  const mockClient = {
    query: vi.fn(),
    release: vi.fn()
  };

  const mockPool = {
    query: vi.fn(),
    connect: vi.fn().mockResolvedValue(mockClient),
    end: vi.fn()
  };

  return {
    default: {
      Pool: vi.fn(() => mockPool)
    }
  };
});

describe('DatabaseService', () => {
  let dbService: DatabaseService;
  let mockPool: { query: Mock; connect: Mock; end: Mock };
  let mockClient: { query: Mock; release: Mock };

  const testConfig = {
    host: 'localhost',
    port: 5432,
    database: 'test',
    user: 'test',
    password: 'test',
    ssl: false
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    const pg = await import('pg');
    mockPool = (pg.default.Pool as Mock)() as typeof mockPool;
    mockClient = (await mockPool.connect()) as typeof mockClient;
    mockPool.connect.mockClear();

    dbService = new DatabaseService(testConfig);
  });

  describe('constructor', () => {
    it('should create pool with config', async () => {
      const pg = await import('pg');

      new DatabaseService(testConfig);

      expect(pg.default.Pool).toHaveBeenCalledWith(
        expect.objectContaining({
          host: 'localhost',
          port: 5432,
          database: 'test'
        })
      );
    });

    it('should enable SSL when configured', async () => {
      const pg = await import('pg');

      new DatabaseService({ ...testConfig, ssl: true });

      expect(pg.default.Pool).toHaveBeenCalledWith(
        expect.objectContaining({
          ssl: { rejectUnauthorized: false }
        })
      );
    });
  });

  describe('initialize', () => {
    it('should test connection by running query', async () => {
      mockPool.connect.mockResolvedValueOnce(mockClient);
      mockClient.query.mockResolvedValueOnce({ rows: [{ '?column?': 1 }] });

      await dbService.initialize();

      expect(mockClient.query).toHaveBeenCalledWith('SELECT 1');
      expect(mockClient.release).toHaveBeenCalled();
    });
  });

  describe('close', () => {
    it('should end pool connection', async () => {
      await dbService.close();

      expect(mockPool.end).toHaveBeenCalled();
    });
  });

  describe('transaction', () => {
    it('should execute transaction with BEGIN and COMMIT', async () => {
      mockPool.connect.mockResolvedValueOnce(mockClient);
      mockClient.query.mockResolvedValue({ rows: [] });

      const result = await dbService.transaction(async (client) => {
        await client.query('INSERT INTO test VALUES (1)');
        return 'success';
      });

      expect(result).toBe('success');
      expect(mockClient.query).toHaveBeenCalledWith('BEGIN');
      expect(mockClient.query).toHaveBeenCalledWith('INSERT INTO test VALUES (1)');
      expect(mockClient.query).toHaveBeenCalledWith('COMMIT');
      expect(mockClient.release).toHaveBeenCalled();
    });

    it('should rollback on error', async () => {
      mockPool.connect.mockResolvedValueOnce(mockClient);
      mockClient.query.mockImplementation((sql: string) => {
        if (sql === 'INSERT') throw new Error('Insert failed');
        return { rows: [] };
      });

      await expect(
        dbService.transaction(async (client) => {
          await client.query('INSERT');
        })
      ).rejects.toThrow('Insert failed');

      expect(mockClient.query).toHaveBeenCalledWith('ROLLBACK');
      expect(mockClient.release).toHaveBeenCalled();
    });
  });

  describe('DocumentRepository', () => {
    describe('create', () => {
      it('should insert document and return id', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'doc-1' }] });

        const id = await dbService.documents.create({
          id: 'doc-1',
          source_path: '/test.md',
          content_hash: 'abc123',
          format: 'markdown',
          document_type: 'documentation',
          title: 'Test Doc',
          authority_level: 1,
          raw_content: '# Test',
          frontmatter: { version: '1.0' }
        });

        expect(id).toBe('doc-1');
        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('INSERT INTO documents'),
          expect.arrayContaining(['doc-1', '/test.md'])
        );
      });
    });

    describe('findById', () => {
      it('should return document when found', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{
            id: 'doc-1',
            source_path: '/test.md',
            frontmatter: '{"version":"1.0"}'
          }]
        });

        const doc = await dbService.documents.findById('doc-1');

        expect(doc).toBeDefined();
        expect(doc?.id).toBe('doc-1');
        expect(doc?.frontmatter).toEqual({ version: '1.0' });
      });

      it('should return null when not found', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        const doc = await dbService.documents.findById('nonexistent');

        expect(doc).toBeNull();
      });
    });

    describe('findAll', () => {
      it('should return all documents', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [
            { id: 'doc-1', frontmatter: {} },
            { id: 'doc-2', frontmatter: {} }
          ]
        });

        const docs = await dbService.documents.findAll();

        expect(docs).toHaveLength(2);
      });
    });

    describe('findByPathPattern', () => {
      it('should convert glob to SQL LIKE', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.documents.findByPathPattern('docs/*.md');

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('LIKE'),
          ['docs/%.md']
        );
      });
    });

    describe('findByContentHash', () => {
      it('should find document by hash', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'doc-1', content_hash: 'abc', frontmatter: {} }]
        });

        const doc = await dbService.documents.findByContentHash('abc');

        expect(doc?.id).toBe('doc-1');
      });
    });

    describe('update', () => {
      it('should update document fields', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.documents.update('doc-1', {
          title: 'New Title',
          authority_level: 2
        });

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('UPDATE documents'),
          expect.arrayContaining(['New Title', 2, 'doc-1'])
        );
      });

      it('should skip update when no changes', async () => {
        await dbService.documents.update('doc-1', {});

        expect(mockPool.query).not.toHaveBeenCalled();
      });
    });

    describe('delete', () => {
      it('should delete document by id', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.documents.delete('doc-1');

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('DELETE FROM documents'),
          ['doc-1']
        );
      });
    });
  });

  describe('SectionRepository', () => {
    describe('create', () => {
      it('should insert section', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'sec-1' }] });

        const id = await dbService.sections.create({
          id: 'sec-1',
          document_id: 'doc-1',
          header: 'Introduction',
          content: 'Content here',
          level: 1,
          section_order: 0,
          start_line: 1,
          end_line: 10
        });

        expect(id).toBe('sec-1');
      });
    });

    describe('findByDocumentId', () => {
      it('should return sections ordered', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [
            { id: 'sec-1', section_order: 0 },
            { id: 'sec-2', section_order: 1 }
          ]
        });

        const sections = await dbService.sections.findByDocumentId('doc-1');

        expect(sections).toHaveLength(2);
        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('ORDER BY section_order'),
          ['doc-1']
        );
      });
    });

    describe('findByDocumentIds', () => {
      it('should return sections for multiple docs', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [
            { id: 'sec-1', document_id: 'doc-1' },
            { id: 'sec-2', document_id: 'doc-2' }
          ]
        });

        const sections = await dbService.sections.findByDocumentIds(['doc-1', 'doc-2']);

        expect(sections).toHaveLength(2);
      });

      it('should return empty for empty input', async () => {
        const sections = await dbService.sections.findByDocumentIds([]);
        expect(sections).toHaveLength(0);
      });
    });

    describe('findById', () => {
      it('should return section when found', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'sec-1', header: 'Test' }]
        });

        const section = await dbService.sections.findById('sec-1');
        expect(section?.header).toBe('Test');
      });
    });
  });

  describe('ClaimRepository', () => {
    describe('create', () => {
      it('should insert claim', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'claim-1' }] });

        const id = await dbService.claims.create({
          id: 'claim-1',
          document_id: 'doc-1',
          section_id: 'sec-1',
          subject: 'function',
          predicate: 'returns',
          object: 'number',
          confidence: 0.9,
          original_text: 'function returns number'
        });

        expect(id).toBe('claim-1');
      });
    });

    describe('findByDocumentId', () => {
      it('should return claims for document', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'claim-1' }]
        });

        const claims = await dbService.claims.findByDocumentId('doc-1');
        expect(claims).toHaveLength(1);
      });
    });

    describe('findBySubject', () => {
      it('should find claims by subject case-insensitive', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'claim-1', subject: 'MyFunction' }]
        });

        await dbService.claims.findBySubject('myfunction');

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('LOWER(subject) = LOWER'),
          ['myfunction']
        );
      });
    });

    describe('update', () => {
      it('should update claim fields', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.claims.update('claim-1', {
          deprecated: true,
          confidence: 0.5
        });

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('UPDATE claims'),
          expect.arrayContaining([true, 0.5, 'claim-1'])
        );
      });
    });
  });

  describe('ConflictRepository', () => {
    describe('create', () => {
      it('should insert conflict', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'conf-1' }] });

        const id = await dbService.conflicts.create({
          id: 'conf-1',
          claim_a_id: 'claim-1',
          claim_b_id: 'claim-2',
          conflict_type: 'value',
          strength: 0.9
        });

        expect(id).toBe('conf-1');
      });
    });

    describe('findByClaimIds', () => {
      it('should find conflicts involving claims', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'conf-1' }]
        });

        const conflicts = await dbService.conflicts.findByClaimIds(['claim-1']);
        expect(conflicts).toHaveLength(1);
      });

      it('should return empty for empty input', async () => {
        const conflicts = await dbService.conflicts.findByClaimIds([]);
        expect(conflicts).toHaveLength(0);
      });
    });

    describe('findUnresolved', () => {
      it('should find pending conflicts', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'conf-1', resolution_status: 'pending' }]
        });

        const conflicts = await dbService.conflicts.findUnresolved();
        expect(conflicts).toHaveLength(1);
      });
    });

    describe('resolve', () => {
      it('should mark conflict as resolved', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.conflicts.resolve('conf-1', { winner: 'claim-1' });

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining("resolution_status = 'resolved'"),
          [JSON.stringify({ winner: 'claim-1' }), 'conf-1']
        );
      });
    });
  });

  describe('SupersessionRepository', () => {
    describe('create', () => {
      it('should insert supersession', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'sup-1' }] });

        const id = await dbService.supersessions.create({
          old_document_id: 'doc-1',
          new_document_id: 'doc-2',
          reason: 'Updated version'
        });

        expect(id).toBe('sup-1');
      });
    });

    describe('findByOldDocumentId', () => {
      it('should find supersessions by old doc', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ old_document_id: 'doc-1', new_document_id: 'doc-2' }]
        });

        const supersessions = await dbService.supersessions.findByOldDocumentId('doc-1');
        expect(supersessions).toHaveLength(1);
      });
    });
  });

  describe('ConsolidationRepository', () => {
    describe('create', () => {
      it('should insert consolidation', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'cons-1' }] });

        const id = await dbService.consolidations.create({
          id: 'cons-1',
          source_document_ids: ['doc-1', 'doc-2'],
          result_document_id: 'doc-3',
          strategy: 'authority',
          conflicts_resolved: 5,
          conflicts_pending: 1
        });

        expect(id).toBe('cons-1');
      });
    });

    describe('findByClusterId', () => {
      it('should find consolidation by cluster id', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'cons-1' }]
        });

        const consolidation = await dbService.consolidations.findByClusterId('cons-1');
        expect(consolidation?.id).toBe('cons-1');
      });
    });
  });

  describe('ProvenanceRepository', () => {
    describe('create', () => {
      it('should insert provenance record', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'prov-1' }] });

        const id = await dbService.provenance.create({
          id: 'prov-1',
          document_id: 'doc-1',
          event_type: 'created',
          details: { source: 'upload' },
          timestamp: new Date()
        });

        expect(id).toBe('prov-1');
      });
    });

    describe('findByDocumentId', () => {
      it('should find provenance records', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'prov-1', details: '{"source":"upload"}' }]
        });

        const provenance = await dbService.provenance.findByDocumentId('doc-1');
        expect(provenance[0].details).toEqual({ source: 'upload' });
      });
    });
  });

  describe('DocumentTagRepository', () => {
    describe('add', () => {
      it('should add tag to document', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.documentTags.add('doc-1', 'important');

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('INSERT INTO document_tags'),
          ['doc-1', 'important']
        );
      });
    });

    describe('remove', () => {
      it('should remove tag from document', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [] });

        await dbService.documentTags.remove('doc-1', 'important');

        expect(mockPool.query).toHaveBeenCalledWith(
          expect.stringContaining('DELETE FROM document_tags'),
          ['doc-1', 'important']
        );
      });
    });

    describe('findByDocumentId', () => {
      it('should return tags for document', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ tag: 'important' }, { tag: 'reviewed' }]
        });

        const tags = await dbService.documentTags.findByDocumentId('doc-1');
        expect(tags).toEqual(['important', 'reviewed']);
      });
    });

    describe('findDocumentsByTag', () => {
      it('should return documents with tag', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ document_id: 'doc-1' }, { document_id: 'doc-2' }]
        });

        const docs = await dbService.documentTags.findDocumentsByTag('important');
        expect(docs).toEqual(['doc-1', 'doc-2']);
      });
    });
  });

  describe('EntityRepository', () => {
    describe('create', () => {
      it('should insert entity', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'ent-1' }] });

        const id = await dbService.entities.create({
          id: 'ent-1',
          canonical_id: 'canon-1',
          name: 'TestEntity',
          type: 'component',
          aliases: ['TE', 'test-entity']
        });

        expect(id).toBe('ent-1');
      });
    });

    describe('findByCanonicalId', () => {
      it('should find entity by canonical id', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ canonical_id: 'canon-1', properties: '{}' }]
        });

        const entity = await dbService.entities.findByCanonicalId('canon-1');
        expect(entity).toBeDefined();
      });
    });

    describe('findByName', () => {
      it('should find entities by name or alias', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ name: 'TestEntity', properties: {} }]
        });

        const entities = await dbService.entities.findByName('TestEntity');
        expect(entities).toHaveLength(1);
      });
    });
  });

  describe('FeedbackRepository', () => {
    describe('create', () => {
      it('should insert feedback', async () => {
        mockPool.query.mockResolvedValueOnce({ rows: [{ id: 'feed-1' }] });

        const id = await dbService.feedback.create({
          id: 'feed-1',
          document_id: 'doc-1',
          feedback_type: 'correction',
          content: 'This is incorrect'
        });

        expect(id).toBe('feed-1');
      });
    });

    describe('findByDocumentId', () => {
      it('should find feedback for document', async () => {
        mockPool.query.mockResolvedValueOnce({
          rows: [{ id: 'feed-1', content: 'Feedback text' }]
        });

        const feedback = await dbService.feedback.findByDocumentId('doc-1');
        expect(feedback).toHaveLength(1);
      });
    });
  });

  describe('createDatabaseService', () => {
    it('should create DatabaseService instance', () => {
      const service = createDatabaseService(testConfig);
      expect(service).toBeInstanceOf(DatabaseService);
    });
  });
});
