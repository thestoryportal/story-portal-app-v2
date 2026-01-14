import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { ConflictDetector, type EmbeddingService, type LLMService } from '../../src/components/conflict-detector.js';
import type { AtomicClaim } from '../../src/types.js';

// Mock neo4j-driver
vi.mock('neo4j-driver', () => ({
  default: {
    driver: vi.fn(() => ({
      session: vi.fn(() => ({
        run: vi.fn().mockResolvedValue({ records: [] }),
        close: vi.fn().mockResolvedValue(undefined)
      })),
      close: vi.fn().mockResolvedValue(undefined)
    })),
    auth: {
      basic: vi.fn((username: string, password: string) => ({ username, password }))
    }
  }
}));

describe('ConflictDetector', () => {
  let detector: ConflictDetector;
  let mockEmbeddingService: EmbeddingService;
  let mockLLMService: LLMService;

  const createClaim = (overrides: Partial<AtomicClaim> = {}): AtomicClaim => ({
    id: `claim-${Math.random().toString(36).substr(2, 9)}`,
    original_text: 'Test claim',
    subject: 'API',
    predicate: 'uses port',
    object: '3000',
    confidence: 0.9,
    source_section_id: 'section-123',
    source_span: { start: 0, end: 10 },
    ...overrides
  });

  beforeEach(() => {
    mockEmbeddingService = {
      embed: vi.fn()
    };

    mockLLMService = {
      generate: vi.fn()
    };

    detector = new ConflictDetector(
      mockEmbeddingService,
      mockLLMService,
      'bolt://localhost:7687',
      { username: 'neo4j', password: 'password' }
    );
  });

  afterEach(async () => {
    await detector.close();
  });

  describe('detectConflicts', () => {
    it('should return empty array when no claims provided', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([]);

      const conflicts = await detector.detectConflicts([]);

      expect(conflicts).toHaveLength(0);
    });

    it('should return empty array for single claim', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([[0.1, 0.2, 0.3]]);

      const claims = [createClaim()];
      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts).toHaveLength(0);
    });

    it('should detect value conflicts for same subject+predicate with different objects', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.1, 0.2, 0.3],
        [0.1, 0.2, 0.3]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Different port values',
        resolution_hints: ['Check which is correct']
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Server', predicate: 'uses port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'uses port', object: '8080', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts.length).toBeGreaterThan(0);
      expect(conflicts[0].conflict_type).toBe('value_conflict');
    });

    it('should not detect conflict for same values', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.1, 0.2, 0.3],
        [0.1, 0.2, 0.3]
      ]);

      const claims = [
        createClaim({ subject: 'Server', predicate: 'uses port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'uses port', object: '3000', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts).toHaveLength(0);
    });

    it('should include claim details in conflicts', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.1, 0.2, 0.3],
        [0.1, 0.2, 0.3]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Test',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claim1 = createClaim({
        id: 'claim-1',
        subject: 'Server',
        predicate: 'uses port',
        object: '3000',
        original_text: 'Server uses port 3000',
        source_section_id: 'section-1'
      });
      const claim2 = createClaim({
        id: 'claim-2',
        subject: 'Server',
        predicate: 'uses port',
        object: '8080',
        original_text: 'Server uses port 8080',
        source_section_id: 'section-2'
      });

      const conflicts = await detector.detectConflicts([claim1, claim2]);

      expect(conflicts[0].claim_a.text).toBe('Server uses port 3000');
      expect(conflicts[0].claim_b.text).toBe('Server uses port 8080');
    });
  });

  describe('semantic conflict detection', () => {
    it('should detect conflicts for semantically similar claims with different values', async () => {
      // Return high similarity embeddings
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [0.99, 0.1, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Test',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({
          subject: 'API',
          predicate: 'response time',
          object: '100ms',
          source_section_id: 'section-1'
        }),
        createClaim({
          subject: 'API',
          predicate: 'response time',
          object: '500ms',
          source_section_id: 'section-2'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts.length).toBeGreaterThan(0);
    });

    it('should not detect semantic conflict for low similarity claims', async () => {
      // Return low similarity embeddings
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [0, 1, 0]
      ]);

      const claims = [
        createClaim({
          subject: 'API',
          predicate: 'response time',
          object: '100ms',
          source_section_id: 'section-1'
        }),
        createClaim({
          subject: 'Database',
          predicate: 'connection limit',
          object: '10',
          source_section_id: 'section-2'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts).toHaveLength(0);
    });

    it('should not detect semantic conflict for claims from same section', async () => {
      // Return high similarity embeddings
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [0.99, 0.1, 0]
      ]);

      const claims = [
        createClaim({
          subject: 'API',
          predicate: 'uses protocol',
          object: 'REST',
          source_section_id: 'same-section'
        }),
        createClaim({
          subject: 'API',
          predicate: 'uses format',
          object: 'JSON',
          source_section_id: 'same-section'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Only value conflicts should be detected, not semantic
      const semanticConflicts = conflicts.filter(c => c.detected_by === 'semantic');
      expect(semanticConflicts).toHaveLength(0);
    });
  });

  describe('value conflict detection', () => {
    it('should detect conflicts when subject and predicate match but object differs', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Different values',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({
          subject: 'Config',
          predicate: 'max connections',
          object: '100',
          source_section_id: 'section-1'
        }),
        createClaim({
          subject: 'Config',
          predicate: 'max connections',
          object: '200',
          source_section_id: 'section-2'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Should detect value conflicts (either from value_extraction or verified by LLM)
      expect(conflicts.length).toBeGreaterThan(0);
      expect(conflicts[0].conflict_type).toBe('value_conflict');
    });

    it('should be case-insensitive for subject and predicate matching', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Different values',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({
          subject: 'API',
          predicate: 'Uses Port',
          object: '3000',
          source_section_id: 'section-1'
        }),
        createClaim({
          subject: 'api',
          predicate: 'uses port',
          object: '8080',
          source_section_id: 'section-2'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts.length).toBeGreaterThan(0);
    });

    it('should handle multiple conflicts from same group', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Different values',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Server', predicate: 'port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'port', object: '8080', source_section_id: 'section-2' }),
        createClaim({ subject: 'Server', predicate: 'port', object: '9000', source_section_id: 'section-3' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Should create pairwise conflicts
      expect(conflicts.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('LLM verification', () => {
    it('should filter out non-conflicts after LLM verification', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: false,
        conflict_type: 'not_a_conflict',
        explanation: 'These are about different contexts',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Server', predicate: 'port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'port', object: '8080', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts).toHaveLength(0);
    });

    it('should update conflict type from LLM analysis', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'temporal_conflict',
        explanation: 'One is newer than the other',
        resolution_hints: ['Use the newer value']
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Version', predicate: 'is', object: '1.0', source_section_id: 'section-1' }),
        createClaim({ subject: 'Version', predicate: 'is', object: '2.0', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts[0].conflict_type).toBe('temporal_conflict');
    });

    it('should include resolution hints from LLM', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Different values specified',
        resolution_hints: ['Check the configuration file', 'Verify with team lead']
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Timeout', predicate: 'is', object: '30s', source_section_id: 'section-1' }),
        createClaim({ subject: 'Timeout', predicate: 'is', object: '60s', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      expect(conflicts[0].resolution_hints).toContain('Check the configuration file');
      expect(conflicts[0].resolution_hints).toContain('Verify with team lead');
    });

    it('should keep conflict on LLM parse error', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      // Return invalid JSON that fails Zod validation
      vi.mocked(mockLLMService.generate).mockResolvedValue('{"invalid": "schema"}');

      const claims = [
        createClaim({ subject: 'Server', predicate: 'port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'port', object: '8080', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Should keep the conflict even with parse error
      expect(conflicts.length).toBeGreaterThan(0);
    });
  });

  describe('deduplication', () => {
    it('should remove duplicate conflicts', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [0.99, 0.1, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Test',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      // Claims that would trigger both semantic and value detection
      const claims = [
        createClaim({
          id: 'claim-1',
          subject: 'Server',
          predicate: 'port',
          object: '3000',
          source_section_id: 'section-1'
        }),
        createClaim({
          id: 'claim-2',
          subject: 'Server',
          predicate: 'port',
          object: '8080',
          source_section_id: 'section-2'
        })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Should be deduplicated to a single conflict
      const uniquePairs = new Set(
        conflicts.map(c => [c.claim_a.id, c.claim_b.id].sort().join('|'))
      );
      expect(uniquePairs.size).toBe(conflicts.length);
    });
  });

  describe('getConflictsForDocument', () => {
    it('should filter conflicts by document ID', async () => {
      const allConflicts = [
        {
          id: 'conflict-1',
          claim_a: { id: 'c1', document_id: 'doc-1', text: 'A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'doc-2', text: 'B', confidence: 0.9 },
          conflict_type: 'value_conflict' as const,
          strength: 0.9,
          detected_by: 'semantic' as const,
          resolution_hints: [],
          created_at: new Date().toISOString()
        },
        {
          id: 'conflict-2',
          claim_a: { id: 'c3', document_id: 'doc-3', text: 'C', confidence: 0.9 },
          claim_b: { id: 'c4', document_id: 'doc-4', text: 'D', confidence: 0.9 },
          conflict_type: 'value_conflict' as const,
          strength: 0.9,
          detected_by: 'semantic' as const,
          resolution_hints: [],
          created_at: new Date().toISOString()
        }
      ];

      const doc1Conflicts = await detector.getConflictsForDocument('doc-1', allConflicts);

      expect(doc1Conflicts).toHaveLength(1);
      expect(doc1Conflicts[0].id).toBe('conflict-1');
    });

    it('should return conflicts where document is in either claim', async () => {
      const allConflicts = [
        {
          id: 'conflict-1',
          claim_a: { id: 'c1', document_id: 'doc-1', text: 'A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'doc-2', text: 'B', confidence: 0.9 },
          conflict_type: 'value_conflict' as const,
          strength: 0.9,
          detected_by: 'semantic' as const,
          resolution_hints: [],
          created_at: new Date().toISOString()
        }
      ];

      const doc1Conflicts = await detector.getConflictsForDocument('doc-1', allConflicts);
      const doc2Conflicts = await detector.getConflictsForDocument('doc-2', allConflicts);

      expect(doc1Conflicts).toHaveLength(1);
      expect(doc2Conflicts).toHaveLength(1);
    });

    it('should return empty array for document with no conflicts', async () => {
      const allConflicts = [
        {
          id: 'conflict-1',
          claim_a: { id: 'c1', document_id: 'doc-1', text: 'A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'doc-2', text: 'B', confidence: 0.9 },
          conflict_type: 'value_conflict' as const,
          strength: 0.9,
          detected_by: 'semantic' as const,
          resolution_hints: [],
          created_at: new Date().toISOString()
        }
      ];

      const conflicts = await detector.getConflictsForDocument('doc-999', allConflicts);

      expect(conflicts).toHaveLength(0);
    });
  });

  describe('cosine similarity', () => {
    it('should calculate similarity correctly for identical vectors', async () => {
      // Use identical embeddings which should give similarity of 1
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [1, 0, 0]
      ]);

      const claims = [
        createClaim({ object: 'A', source_section_id: 'section-1' }),
        createClaim({ object: 'B', source_section_id: 'section-2' })
      ];

      // Even with identical embeddings, different objects should be detected
      // The high similarity (>0.8) triggers semantic conflict detection
      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Test',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const conflicts = await detector.detectConflicts(claims);

      // Should detect semantic conflict due to high similarity
      const semanticConflicts = conflicts.filter(c => c.detected_by === 'semantic');
      expect(semanticConflicts.length).toBeGreaterThan(0);
    });

    it('should handle orthogonal vectors', async () => {
      // Orthogonal vectors have similarity of 0
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [1, 0, 0],
        [0, 1, 0]
      ]);

      const claims = [
        createClaim({ subject: 'A', predicate: 'is', object: 'X', source_section_id: 'section-1' }),
        createClaim({ subject: 'B', predicate: 'does', object: 'Y', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // No semantic conflicts due to low similarity
      const semanticConflicts = conflicts.filter(c => c.detected_by === 'semantic');
      expect(semanticConflicts).toHaveLength(0);
    });
  });

  describe('conflict strength', () => {
    it('should assign strength based on detection method', async () => {
      vi.mocked(mockEmbeddingService.embed).mockResolvedValue([
        [0.5, 0.5, 0],
        [0.5, 0.5, 0]
      ]);

      const mockLLMResponse = JSON.stringify({
        is_conflict: true,
        conflict_type: 'value_conflict',
        explanation: 'Test',
        resolution_hints: []
      });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

      const claims = [
        createClaim({ subject: 'Server', predicate: 'port', object: '3000', source_section_id: 'section-1' }),
        createClaim({ subject: 'Server', predicate: 'port', object: '8080', source_section_id: 'section-2' })
      ];

      const conflicts = await detector.detectConflicts(claims);

      // Value extraction conflicts should have high strength (0.95)
      const valueConflicts = conflicts.filter(c => c.detected_by === 'value_extraction');
      if (valueConflicts.length > 0) {
        expect(valueConflicts[0].strength).toBe(0.95);
      }
    });
  });
});
