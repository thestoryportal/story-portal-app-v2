import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { EntityResolver, EmbeddingService } from '../../src/components/entity-resolver.js';

// Mock neo4j-driver
vi.mock('neo4j-driver', () => {
  const mockSession = {
    run: vi.fn(),
    close: vi.fn()
  };

  const mockDriver = {
    session: vi.fn(() => mockSession),
    close: vi.fn()
  };

  return {
    default: {
      driver: vi.fn(() => mockDriver),
      auth: {
        basic: vi.fn((username: string, password: string) => ({ username, password }))
      }
    }
  };
});

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-uuid-123')
}));

describe('EntityResolver', () => {
  let resolver: EntityResolver;
  let mockEmbeddingService: EmbeddingService;
  let mockSession: { run: Mock; close: Mock };
  let mockDriver: { session: Mock; close: Mock };

  beforeEach(async () => {
    vi.clearAllMocks();

    mockEmbeddingService = {
      embed: vi.fn().mockResolvedValue([[0.1, 0.2, 0.3]])
    };

    // Get the mock driver and session
    const neo4j = await import('neo4j-driver');
    mockDriver = (neo4j.default.driver as Mock)() as typeof mockDriver;
    mockSession = mockDriver.session() as typeof mockSession;

    // Reset the mock to track new calls
    (neo4j.default.driver as Mock).mockClear();
    mockDriver.session.mockClear();

    resolver = new EntityResolver(
      mockEmbeddingService,
      'bolt://localhost:7687',
      { username: 'neo4j', password: 'password' }
    );
  });

  describe('constructor', () => {
    it('should accept embedding service first (new order)', async () => {
      const neo4j = await import('neo4j-driver');

      new EntityResolver(
        mockEmbeddingService,
        'bolt://localhost:7687',
        { username: 'neo4j', password: 'password' }
      );

      expect(neo4j.default.driver).toHaveBeenCalledWith(
        'bolt://localhost:7687',
        expect.anything()
      );
    });

    it('should accept neo4j uri first (old order)', async () => {
      const neo4j = await import('neo4j-driver');

      new EntityResolver(
        'bolt://localhost:7687',
        { username: 'neo4j', password: 'password' },
        mockEmbeddingService
      );

      expect(neo4j.default.driver).toHaveBeenCalledWith(
        'bolt://localhost:7687',
        expect.anything()
      );
    });
  });

  describe('resolve', () => {
    it('should resolve mentions to entities', async () => {
      // Mock exact match found
      mockSession.run.mockResolvedValueOnce({
        records: [{
          get: () => ({
            properties: {
              id: 'entity-1',
              canonical_name: 'test entity',
              type: 'component',
              aliases: ['te'],
              source_file: 'test.ts',
              attributes: {}
            }
          })
        }]
      });

      const mentions = [{ text: 'test entity', type: 'component' as const }];
      const result = await resolver.resolve(mentions);

      expect(result.size).toBe(1);
      expect(result.get('test entity')).toBeDefined();
      expect(result.get('test entity')?.canonical_name).toBe('test entity');
    });

    it('should create new entity when no match found', async () => {
      // Mock no exact match
      mockSession.run.mockResolvedValueOnce({ records: [] });
      // Mock no similarity match (error to skip)
      mockSession.run.mockRejectedValueOnce(new Error('GDS not available'));
      // Mock create entity
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'new entity', type: 'function' as const }];
      const result = await resolver.resolve(mentions);

      expect(result.size).toBe(1);
      expect(result.get('new entity')).toBeDefined();
      expect(result.get('new entity')?.canonical_id).toBe('mock-uuid-123');
    });

    it('should add alias when entity found but text differs', async () => {
      // Mock exact match found
      mockSession.run.mockResolvedValueOnce({
        records: [{
          get: () => ({
            properties: {
              id: 'entity-1',
              canonical_name: 'original name',
              type: 'component',
              aliases: [],
              attributes: {}
            }
          })
        }]
      });
      // Mock add alias
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'alias name' }];
      const result = await resolver.resolve(mentions);

      expect(result.size).toBe(1);
      // Should have called addAlias
      expect(mockSession.run).toHaveBeenCalledTimes(2);
    });

    it('should handle multiple mentions', async () => {
      // First mention - found
      mockSession.run.mockResolvedValueOnce({
        records: [{
          get: () => ({
            properties: {
              id: 'entity-1',
              canonical_name: 'entity one',
              type: 'component',
              aliases: [],
              attributes: {}
            }
          })
        }]
      });
      mockSession.run.mockResolvedValueOnce({ records: [] }); // add alias

      // Second mention - not found, create
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('GDS not available'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [
        { text: 'entity one', type: 'component' as const },
        { text: 'entity two', type: 'function' as const }
      ];
      const result = await resolver.resolve(mentions);

      expect(result.size).toBe(2);
    });

    it('should throw DatabaseError on failure', async () => {
      mockSession.run.mockRejectedValueOnce(new Error('Connection failed'));

      const mentions = [{ text: 'test' }];

      await expect(resolver.resolve(mentions)).rejects.toThrow('Database operation failed');
    });
  });

  describe('findBySimilarity', () => {
    it('should find similar entity using embeddings', async () => {
      // First call is exact match (no result)
      mockSession.run.mockResolvedValueOnce({ records: [] });
      // Second call is similarity search
      mockSession.run.mockResolvedValueOnce({
        records: [{
          get: (key: string) => {
            if (key === 'e') {
              return {
                properties: {
                  id: 'similar-entity',
                  canonical_name: 'similar',
                  type: 'component',
                  aliases: [],
                  attributes: {}
                }
              };
            }
            return 0.9;
          }
        }]
      });
      // Add alias call
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'almost similar' }];
      const result = await resolver.resolve(mentions);

      expect(mockEmbeddingService.embed).toHaveBeenCalledWith(['almost similar']);
      expect(result.get('almost similar')?.canonical_name).toBe('similar');
    });

    it('should fall back to create when similarity search fails', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] }); // exact match
      mockSession.run.mockRejectedValueOnce(new Error('GDS not installed')); // similarity
      mockSession.run.mockResolvedValueOnce({ records: [] }); // create

      const mentions = [{ text: 'new entity' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('new entity')?.canonical_id).toBe('mock-uuid-123');
    });
  });

  describe('inferEntityType', () => {
    it('should infer function type from get/set prefixes', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('skip'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'getUser' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('getUser')?.type).toBe('function');
    });

    it('should infer config type from config keywords', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('skip'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'databaseConfig' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('databaseConfig')?.type).toBe('config');
    });

    it('should infer file type from extensions', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('skip'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'app.ts' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('app.ts')?.type).toBe('file');
    });

    it('should infer person type from email patterns', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('skip'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'user@example.com' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('user@example.com')?.type).toBe('person');
    });

    it('should return unknown for unrecognized patterns', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });
      mockSession.run.mockRejectedValueOnce(new Error('skip'));
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const mentions = [{ text: 'random-thing' }];
      const result = await resolver.resolve(mentions);

      expect(result.get('random-thing')?.type).toBe('unknown');
    });
  });

  describe('linkClaimToEntity', () => {
    it('should link claim to entity in graph', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });

      await resolver.linkClaimToEntity('claim-1', 'entity-1', 'doc-1');

      expect(mockSession.run).toHaveBeenCalledWith(
        expect.stringContaining('MERGE (c:Claim'),
        expect.objectContaining({
          claimId: 'claim-1',
          entityId: 'entity-1',
          documentId: 'doc-1'
        })
      );
    });
  });

  describe('findRelatedEntities', () => {
    it('should find related entities through graph traversal', async () => {
      mockSession.run.mockResolvedValueOnce({
        records: [
          {
            get: () => ({
              properties: {
                id: 'related-1',
                canonical_name: 'related entity',
                type: 'component',
                aliases: ['rel'],
                attributes: {}
              }
            })
          }
        ]
      });

      const related = await resolver.findRelatedEntities('entity-1', 2);

      expect(related).toHaveLength(1);
      expect(related[0].canonical_id).toBe('related-1');
    });

    it('should return empty array when no related entities', async () => {
      mockSession.run.mockResolvedValueOnce({ records: [] });

      const related = await resolver.findRelatedEntities('entity-1');

      expect(related).toHaveLength(0);
    });
  });

  describe('getAllEntities', () => {
    it('should return all entities from graph', async () => {
      mockSession.run.mockResolvedValueOnce({
        records: [
          {
            get: () => ({
              properties: {
                id: 'entity-1',
                canonical_name: 'entity one',
                type: 'component',
                aliases: [],
                attributes: {}
              }
            })
          },
          {
            get: () => ({
              properties: {
                id: 'entity-2',
                canonical_name: 'entity two',
                type: 'function',
                aliases: ['e2'],
                attributes: { key: 'value' }
              }
            })
          }
        ]
      });

      const entities = await resolver.getAllEntities();

      expect(entities).toHaveLength(2);
      expect(entities[0].canonical_id).toBe('entity-1');
      expect(entities[1].canonical_id).toBe('entity-2');
    });
  });

  describe('close', () => {
    it('should close the driver connection', async () => {
      await resolver.close();

      expect(mockDriver.close).toHaveBeenCalled();
    });
  });
});
