import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MergeEngine, type LLMService } from '../../src/components/merge-engine.js';
import type { ParsedDocument, AtomicClaim, Conflict, MergeStrategy } from '../../src/types.js';

describe('MergeEngine', () => {
  let engine: MergeEngine;
  let mockLLMService: LLMService;

  const createDocument = (overrides: Partial<ParsedDocument> = {}): ParsedDocument => ({
    id: `doc-${Math.random().toString(36).substr(2, 9)}`,
    source_path: '/path/to/doc.md',
    format: 'markdown',
    raw_content: '# Test',
    content_hash: 'abc123',
    sections: [
      {
        id: 'section-1',
        header: 'Test Section',
        content: 'Test content',
        level: 1,
        start_line: 1,
        end_line: 5
      }
    ],
    created_at: new Date().toISOString(),
    ...overrides
  });

  const createClaim = (overrides: Partial<AtomicClaim> = {}): AtomicClaim => ({
    id: `claim-${Math.random().toString(36).substr(2, 9)}`,
    original_text: 'Test claim',
    subject: 'API',
    predicate: 'uses port',
    object: '3000',
    confidence: 0.9,
    source_section_id: 'section-1',
    source_span: { start: 0, end: 10 },
    ...overrides
  });

  const createConflict = (overrides: Partial<Conflict> = {}): Conflict => ({
    id: `conflict-${Math.random().toString(36).substr(2, 9)}`,
    claim_a: {
      id: 'claim-a',
      document_id: 'doc-1',
      text: 'Server uses port 3000',
      confidence: 0.9
    },
    claim_b: {
      id: 'claim-b',
      document_id: 'doc-2',
      text: 'Server uses port 8080',
      confidence: 0.9
    },
    conflict_type: 'value_conflict',
    strength: 0.9,
    detected_by: 'value_extraction',
    resolution_hints: [],
    created_at: new Date().toISOString(),
    ...overrides
  });

  beforeEach(() => {
    mockLLMService = {
      generate: vi.fn()
    };
    engine = new MergeEngine(mockLLMService, 'test-model');
  });

  describe('merge', () => {
    it('should merge documents and return MergeResult', async () => {
      const documents = [createDocument({ title: 'Doc 1' })];
      const claims = [createClaim()];
      const conflicts: Conflict[] = [];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, conflicts, strategy);

      expect(result.id).toBeTruthy();
      expect(result.content).toBeTruthy();
      expect(result.sections).toBeInstanceOf(Array);
      expect(result.created_at).toBeTruthy();
    });

    it('should include statistics in result', async () => {
      const documents = [
        createDocument({ title: 'Doc 1' }),
        createDocument({ title: 'Doc 2' })
      ];
      const claims = [createClaim()];
      const conflicts: Conflict[] = [];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, conflicts, strategy);

      expect(result.statistics.documents_merged).toBe(2);
      expect(result.statistics.sections_merged).toBeGreaterThanOrEqual(0);
      expect(result.statistics.conflicts_auto_resolved).toBe(0);
      expect(result.statistics.conflicts_flagged).toBe(0);
    });

    it('should generate title from document titles', async () => {
      const documents = [
        createDocument({ title: 'API Documentation Guide' }),
        createDocument({ title: 'API Reference Manual' })
      ];
      const claims = [createClaim()];
      const conflicts: Conflict[] = [];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, conflicts, strategy);

      // Should extract common word 'API'
      expect(result.title).toBeTruthy();
    });

    it('should use default title when no documents have titles', async () => {
      const documents = [
        createDocument({ title: undefined }),
        createDocument({ title: undefined })
      ];
      const claims = [createClaim()];
      const conflicts: Conflict[] = [];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, conflicts, strategy);

      expect(result.title).toBe('Consolidated Document');
    });

    it('should group claims by topic', async () => {
      const documents = [createDocument()];
      const claims = [
        createClaim({ subject: 'API', predicate: 'uses', object: 'REST' }),
        createClaim({ subject: 'API', predicate: 'returns', object: 'JSON' }),
        createClaim({ subject: 'Database', predicate: 'type', object: 'PostgreSQL' })
      ];
      const conflicts: Conflict[] = [];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, conflicts, strategy);

      // Should have sections for 'API' and 'Database' topics
      expect(result.sections.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('conflict resolution', () => {
    describe('flag_all strategy', () => {
      it('should flag all conflicts when strategy is flag_all', async () => {
        const documents = [createDocument(), createDocument()];
        const claims = [createClaim()];
        const conflicts = [createConflict()];
        const strategy: MergeStrategy = { mode: 'smart', conflictResolution: 'flag_all' };

        const result = await engine.merge(documents, claims, conflicts, strategy);

        expect(result.conflicts_flagged).toHaveLength(1);
        expect(result.conflicts_resolved).toHaveLength(0);
      });
    });

    describe('newest_wins strategy', () => {
      it('should choose newer document claim', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          created_at: '2024-01-01T00:00:00Z',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          created_at: '2024-06-01T00:00:00Z',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'Old value', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'New value', confidence: 0.9 }
        });

        const strategy: MergeStrategy = { mode: 'newest_wins' };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_resolved).toHaveLength(1);
        expect(result.conflicts_resolved[0].resolution).toBe('chose_b');
      });

      it('should flag conflict when documents have same date', async () => {
        const sameDate = '2024-01-01T00:00:00Z';
        const doc1 = createDocument({
          id: 'doc-1',
          created_at: sameDate,
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          created_at: sameDate,
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'Value A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'Value B', confidence: 0.9 }
        });

        const strategy: MergeStrategy = { mode: 'newest_wins' };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_flagged).toHaveLength(1);
      });
    });

    describe('authority_wins strategy', () => {
      it('should choose claim from higher authority document', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          source_path: '/docs/official/api.md',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          source_path: '/docs/draft/api.md',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'Official', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'Draft', confidence: 0.9 }
        });

        const strategy: MergeStrategy = {
          mode: 'authority_wins',
          authorityOrder: ['*official*', '*draft*']
        };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_resolved).toHaveLength(1);
        expect(result.conflicts_resolved[0].resolution).toBe('chose_a');
      });

      it('should flag conflict when documents have same authority', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          source_path: '/docs/guide-a.md',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          source_path: '/docs/guide-b.md',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'Value A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'Value B', confidence: 0.9 }
        });

        const strategy: MergeStrategy = {
          mode: 'authority_wins',
          authorityOrder: ['*official*'] // Neither matches
        };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_flagged).toHaveLength(1);
      });
    });

    describe('smart strategy with LLM', () => {
      it('should use LLM to resolve conflicts', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'API uses port 3000', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'API uses port 8080', confidence: 0.9 }
        });

        const mockLLMResponse = JSON.stringify({
          choice: 'chose_a',
          confidence: 0.85,
          reasoning: 'Port 3000 is standard for development'
        });
        vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

        const strategy: MergeStrategy = { mode: 'smart', conflictThreshold: 0.8 };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(mockLLMService.generate).toHaveBeenCalled();
        expect(result.conflicts_resolved).toHaveLength(1);
        expect(result.conflicts_resolved[0].resolution).toBe('chose_a');
      });

      it('should flag conflict when LLM confidence below threshold', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'Value A', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'Value B', confidence: 0.9 }
        });

        const mockLLMResponse = JSON.stringify({
          choice: 'chose_a',
          confidence: 0.5, // Below threshold
          reasoning: 'Uncertain'
        });
        vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

        const strategy: MergeStrategy = { mode: 'smart', conflictThreshold: 0.8 };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_flagged).toHaveLength(1);
        expect(result.conflicts_flagged[0].reason).toContain('Confidence 0.50 below threshold');
      });

      it('should handle LLM merged resolution', async () => {
        const doc1 = createDocument({
          id: 'doc-1',
          sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
        });
        const doc2 = createDocument({
          id: 'doc-2',
          sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
        });

        const conflict = createConflict({
          claim_a: { id: 'c1', document_id: 'section-a', text: 'API supports JSON', confidence: 0.9 },
          claim_b: { id: 'c2', document_id: 'section-b', text: 'API supports XML', confidence: 0.9 }
        });

        const mockLLMResponse = JSON.stringify({
          choice: 'merged',
          confidence: 0.9,
          reasoning: 'Both formats are supported',
          merged_text: 'API supports both JSON and XML formats'
        });
        vi.mocked(mockLLMService.generate).mockResolvedValue(mockLLMResponse);

        const strategy: MergeStrategy = { mode: 'smart' };

        const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

        expect(result.conflicts_resolved).toHaveLength(1);
        expect(result.conflicts_resolved[0].resolution).toBe('merged');
      });
    });
  });

  describe('section building', () => {
    it('should build sections from claim groups', async () => {
      const documents = [createDocument()];
      const claims = [
        createClaim({ subject: 'API', predicate: 'protocol', object: 'REST' }),
        createClaim({ subject: 'API', predicate: 'format', object: 'JSON' })
      ];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, [], strategy);

      // Should have a section for 'API' topic
      const apiSection = result.sections.find(s => s.header.toLowerCase().includes('api'));
      expect(apiSection).toBeTruthy();
      expect(apiSection?.content).toContain('protocol');
      expect(apiSection?.content).toContain('REST');
    });

    it('should include provenance in sections', async () => {
      const doc = createDocument({
        id: 'doc-123',
        sections: [{ id: 'section-456', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
      });
      const claims = [createClaim({ source_section_id: 'section-456' })];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge([doc], claims, [], strategy);

      expect(result.sections[0].provenance).toBeInstanceOf(Array);
      expect(result.sections[0].provenance.length).toBeGreaterThan(0);
    });

    it('should format topic headers in title case', async () => {
      const documents = [createDocument()];
      const claims = [
        createClaim({ subject: 'api_endpoint', predicate: 'path', object: '/users' })
      ];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, [], strategy);

      const section = result.sections.find(s => s.header.includes('Api') || s.header.includes('Endpoint'));
      expect(section).toBeTruthy();
    });
  });

  describe('content generation', () => {
    it('should generate markdown content from sections', async () => {
      const documents = [createDocument()];
      const claims = [
        createClaim({ subject: 'Server', predicate: 'runs on', object: 'port 3000' })
      ];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, [], strategy);

      expect(result.content).toContain('##'); // Markdown headers
      expect(result.content).toContain('runs on');
      expect(result.content).toContain('port 3000');
    });

    it('should use highest confidence claim for each predicate', async () => {
      const documents = [createDocument(), createDocument()];
      const claims = [
        createClaim({
          subject: 'API',
          predicate: 'version',
          object: '1.0',
          confidence: 0.7,
          source_section_id: 'section-1'
        }),
        createClaim({
          subject: 'API',
          predicate: 'version',
          object: '2.0',
          confidence: 0.95,
          source_section_id: 'section-2'
        })
      ];
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, [], strategy);

      // Should use '2.0' as it has higher confidence
      expect(result.content).toContain('2.0');
    });
  });

  describe('statistics calculation', () => {
    it('should calculate redundancy elimination percentage', async () => {
      const documents = [
        createDocument({
          sections: [
            { id: 's1', header: 'A', content: 'A', level: 1, start_line: 1, end_line: 2 },
            { id: 's2', header: 'B', content: 'B', level: 1, start_line: 3, end_line: 4 }
          ]
        }),
        createDocument({
          sections: [
            { id: 's3', header: 'C', content: 'C', level: 1, start_line: 1, end_line: 2 },
            { id: 's4', header: 'D', content: 'D', level: 1, start_line: 3, end_line: 4 }
          ]
        })
      ];
      const claims = [createClaim()]; // Only one claim = one merged section
      const strategy: MergeStrategy = { mode: 'smart' };

      const result = await engine.merge(documents, claims, [], strategy);

      // 4 original sections, merged to 1 = 75% redundancy eliminated
      expect(result.statistics.redundancy_eliminated_percent).toBeGreaterThan(0);
    });

    it('should count resolved vs flagged conflicts', async () => {
      const doc1 = createDocument({
        id: 'doc-1',
        sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
      });
      const doc2 = createDocument({
        id: 'doc-2',
        sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
      });

      const conflicts = [
        createConflict({ id: 'c1', claim_a: { id: '1', document_id: 'section-a', text: 'A', confidence: 0.9 }, claim_b: { id: '2', document_id: 'section-b', text: 'B', confidence: 0.9 } }),
        createConflict({ id: 'c2', claim_a: { id: '3', document_id: 'section-a', text: 'C', confidence: 0.9 }, claim_b: { id: '4', document_id: 'section-b', text: 'D', confidence: 0.9 } })
      ];

      // First conflict resolves, second flags
      vi.mocked(mockLLMService.generate)
        .mockResolvedValueOnce(JSON.stringify({ choice: 'chose_a', confidence: 0.9, reasoning: 'Yes' }))
        .mockResolvedValueOnce(JSON.stringify({ choice: 'chose_b', confidence: 0.3, reasoning: 'Uncertain' }));

      const strategy: MergeStrategy = { mode: 'smart', conflictThreshold: 0.8 };

      const result = await engine.merge([doc1, doc2], [], conflicts, strategy);

      expect(result.statistics.conflicts_auto_resolved).toBe(1);
      expect(result.statistics.conflicts_flagged).toBe(1);
    });
  });

  describe('path pattern matching', () => {
    it('should match glob patterns in authority order', async () => {
      const doc1 = createDocument({
        id: 'doc-1',
        source_path: '/docs/api/v2/reference.md',
        sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
      });
      const doc2 = createDocument({
        id: 'doc-2',
        source_path: '/drafts/api-notes.md',
        sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
      });

      const conflict = createConflict({
        claim_a: { id: 'c1', document_id: 'section-a', text: 'Official', confidence: 0.9 },
        claim_b: { id: 'c2', document_id: 'section-b', text: 'Draft', confidence: 0.9 }
      });

      const strategy: MergeStrategy = {
        mode: 'authority_wins',
        authorityOrder: ['*/docs/*', '*/drafts/*']
      };

      const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

      expect(result.conflicts_resolved[0].resolution).toBe('chose_a');
    });

    it('should handle wildcard in pattern', async () => {
      const doc1 = createDocument({
        id: 'doc-1',
        source_path: '/official-docs/guide.md',
        sections: [{ id: 'section-a', header: 'Test', content: 'A', level: 1, start_line: 1, end_line: 2 }]
      });
      const doc2 = createDocument({
        id: 'doc-2',
        source_path: '/other/file.md',
        sections: [{ id: 'section-b', header: 'Test', content: 'B', level: 1, start_line: 1, end_line: 2 }]
      });

      const conflict = createConflict({
        claim_a: { id: 'c1', document_id: 'section-a', text: 'A', confidence: 0.9 },
        claim_b: { id: 'c2', document_id: 'section-b', text: 'B', confidence: 0.9 }
      });

      const strategy: MergeStrategy = {
        mode: 'authority_wins',
        authorityOrder: ['*official*']
      };

      const result = await engine.merge([doc1, doc2], [], [conflict], strategy);

      expect(result.conflicts_resolved[0].resolution).toBe('chose_a');
    });
  });
});
