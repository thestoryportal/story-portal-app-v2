import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ClaimExtractor, type LLMService } from '../../src/components/claim-extractor.js';
import type { AtomicClaim } from '../../src/types.js';

describe('ClaimExtractor', () => {
  let extractor: ClaimExtractor;
  let mockLLMService: LLMService;

  beforeEach(() => {
    mockLLMService = {
      generate: vi.fn()
    };
    extractor = new ClaimExtractor(mockLLMService);
  });

  describe('extract', () => {
    it('should extract claims from section content', async () => {
      const mockResponse = JSON.stringify({
        claims: [
          {
            original_text: 'The API uses REST protocol',
            subject: 'API',
            predicate: 'uses protocol',
            object: 'REST',
            confidence: 0.95,
            start_char: 0,
            end_char: 25
          }
        ]
      });

      vi.mocked(mockLLMService.generate).mockResolvedValue(mockResponse);

      const claims = await extractor.extract('The API uses REST protocol', 'section-123');

      expect(claims).toHaveLength(1);
      expect(claims[0].subject).toBe('API');
      expect(claims[0].predicate).toBe('uses protocol');
      expect(claims[0].object).toBe('REST');
      expect(claims[0].confidence).toBe(0.95);
      expect(claims[0].source_section_id).toBe('section-123');
    });

    it('should return empty array for empty content', async () => {
      const claims = await extractor.extract('', 'section-123');

      expect(claims).toHaveLength(0);
      expect(mockLLMService.generate).not.toHaveBeenCalled();
    });

    it('should return empty array for whitespace-only content', async () => {
      const claims = await extractor.extract('   \n\t  ', 'section-123');

      expect(claims).toHaveLength(0);
      expect(mockLLMService.generate).not.toHaveBeenCalled();
    });

    it('should generate unique IDs for each claim', async () => {
      const mockResponse = JSON.stringify({
        claims: [
          {
            original_text: 'Claim 1',
            subject: 'A',
            predicate: 'is',
            object: 'B',
            confidence: 0.9,
            start_char: 0,
            end_char: 7
          },
          {
            original_text: 'Claim 2',
            subject: 'C',
            predicate: 'is',
            object: 'D',
            confidence: 0.9,
            start_char: 8,
            end_char: 15
          }
        ]
      });

      vi.mocked(mockLLMService.generate).mockResolvedValue(mockResponse);

      const claims = await extractor.extract('Claim 1\nClaim 2', 'section-123');

      expect(claims).toHaveLength(2);
      expect(claims[0].id).toBeTruthy();
      expect(claims[1].id).toBeTruthy();
      expect(claims[0].id).not.toBe(claims[1].id);
    });

    it('should map source_span correctly', async () => {
      const mockResponse = JSON.stringify({
        claims: [
          {
            original_text: 'Test claim',
            subject: 'Test',
            predicate: 'is',
            object: 'claim',
            confidence: 0.8,
            start_char: 10,
            end_char: 20
          }
        ]
      });

      vi.mocked(mockLLMService.generate).mockResolvedValue(mockResponse);

      const claims = await extractor.extract('Test content', 'section-123');

      expect(claims[0].source_span).toEqual({ start: 10, end: 20 });
    });

    it('should include optional qualifier when present', async () => {
      const mockResponse = JSON.stringify({
        claims: [
          {
            original_text: 'Server runs on port 3000 in development',
            subject: 'Server',
            predicate: 'runs on port',
            object: '3000',
            qualifier: 'in development',
            confidence: 0.9,
            start_char: 0,
            end_char: 39
          }
        ]
      });

      vi.mocked(mockLLMService.generate).mockResolvedValue(mockResponse);

      const claims = await extractor.extract('Server runs on port 3000 in development', 'section-123');

      expect(claims[0].qualifier).toBe('in development');
    });

    it('should call LLM with correct parameters', async () => {
      const mockResponse = JSON.stringify({ claims: [] });
      vi.mocked(mockLLMService.generate).mockResolvedValue(mockResponse);

      await extractor.extract('Test content', 'section-123');

      expect(mockLLMService.generate).toHaveBeenCalledWith(
        expect.objectContaining({
          format: 'json',
          options: { temperature: 0.1 }
        })
      );
    });

    it('should throw LLMError on invalid JSON response', async () => {
      vi.mocked(mockLLMService.generate).mockResolvedValue('invalid json');

      await expect(extractor.extract('Test', 'section-123')).rejects.toThrow();
    });

    it('should throw LLMError on invalid schema response', async () => {
      const invalidResponse = JSON.stringify({
        claims: [
          {
            // Missing required fields
            subject: 'Test'
          }
        ]
      });

      vi.mocked(mockLLMService.generate).mockResolvedValue(invalidResponse);

      await expect(extractor.extract('Test', 'section-123')).rejects.toThrow();
    });
  });

  describe('extractBatch', () => {
    it('should extract claims from multiple sections', async () => {
      const mockResponse1 = JSON.stringify({
        claims: [{ original_text: 'A', subject: 'A', predicate: 'is', object: 'B', confidence: 0.9, start_char: 0, end_char: 1 }]
      });
      const mockResponse2 = JSON.stringify({
        claims: [{ original_text: 'C', subject: 'C', predicate: 'is', object: 'D', confidence: 0.9, start_char: 0, end_char: 1 }]
      });

      vi.mocked(mockLLMService.generate)
        .mockResolvedValueOnce(mockResponse1)
        .mockResolvedValueOnce(mockResponse2);

      const sections = [
        { id: 'section-1', content: 'Content 1' },
        { id: 'section-2', content: 'Content 2' }
      ];

      const results = await extractor.extractBatch(sections, 2);

      expect(results.size).toBe(2);
      expect(results.get('section-1')).toHaveLength(1);
      expect(results.get('section-2')).toHaveLength(1);
    });

    it('should respect concurrency limit', async () => {
      const mockResponse = JSON.stringify({ claims: [] });
      vi.mocked(mockLLMService.generate).mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return mockResponse;
      });

      const sections = Array.from({ length: 5 }, (_, i) => ({
        id: `section-${i}`,
        content: `Content ${i}`
      }));

      const results = await extractor.extractBatch(sections, 2);

      expect(results.size).toBe(5);
    });
  });

  describe('validateClaims', () => {
    const createClaim = (overrides: Partial<AtomicClaim> = {}): AtomicClaim => ({
      id: 'claim-123',
      original_text: 'Test claim',
      subject: 'Test',
      predicate: 'has property',
      object: 'value',
      confidence: 0.9,
      source_section_id: 'section-123',
      source_span: { start: 0, end: 10 },
      ...overrides
    });

    it('should return empty array for valid claims', () => {
      const claims = [createClaim()];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(0);
    });

    it('should flag claim with empty subject', () => {
      const claims = [createClaim({ subject: '' })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues).toContain('Empty subject');
    });

    it('should flag claim with empty predicate', () => {
      const claims = [createClaim({ predicate: '' })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues).toContain('Empty predicate');
    });

    it('should flag claim with empty object', () => {
      const claims = [createClaim({ object: '' })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues).toContain('Empty object');
    });

    it('should flag claim with very low confidence', () => {
      const claims = [createClaim({ confidence: 0.2 })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues[0]).toContain('Very low confidence');
    });

    it('should flag compound claims with "and"', () => {
      const claims = [createClaim({ predicate: 'is red and blue' })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues).toContain('Possibly compound claim - may need splitting');
    });

    it('should flag compound claims with commas', () => {
      const claims = [createClaim({ predicate: 'has height, width, depth' })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues).toContain('Possibly compound claim - may need splitting');
    });

    it('should flag vague predicates', () => {
      const vaguePredicates = ['is', 'has', 'does', 'can'];

      for (const predicate of vaguePredicates) {
        const claims = [createClaim({ predicate })];
        const invalid = extractor.validateClaims(claims);

        expect(invalid).toHaveLength(1);
        expect(invalid[0].issues).toContain('Vague predicate - may be too general');
      }
    });

    it('should accumulate multiple issues', () => {
      const claims = [createClaim({
        subject: '',
        predicate: 'is',
        confidence: 0.1
      })];
      const invalid = extractor.validateClaims(claims);

      expect(invalid).toHaveLength(1);
      expect(invalid[0].issues.length).toBeGreaterThan(1);
    });
  });

  describe('deduplicateClaims', () => {
    const createClaim = (subject: string, predicate: string, object: string): AtomicClaim => ({
      id: `claim-${Math.random()}`,
      original_text: `${subject} ${predicate} ${object}`,
      subject,
      predicate,
      object,
      confidence: 0.9,
      source_section_id: 'section-123',
      source_span: { start: 0, end: 10 }
    });

    it('should remove exact duplicates', () => {
      const claims = [
        createClaim('API', 'uses', 'REST'),
        createClaim('API', 'uses', 'REST')
      ];

      const unique = extractor.deduplicateClaims(claims);

      expect(unique).toHaveLength(1);
    });

    it('should keep different claims', () => {
      const claims = [
        createClaim('API', 'uses', 'REST'),
        createClaim('Server', 'runs on', 'port 3000')
      ];

      const unique = extractor.deduplicateClaims(claims);

      expect(unique).toHaveLength(2);
    });

    it('should remove case-insensitive duplicates', () => {
      const claims = [
        createClaim('API', 'uses', 'REST'),
        createClaim('api', 'USES', 'rest')
      ];

      const unique = extractor.deduplicateClaims(claims);

      expect(unique).toHaveLength(1);
    });

    it('should use similarity threshold', () => {
      const claims = [
        createClaim('API', 'uses protocol', 'REST'),
        createClaim('API', 'uses protocols', 'REST') // Very similar
      ];

      const unique = extractor.deduplicateClaims(claims, 0.9);

      expect(unique).toHaveLength(1);
    });

    it('should keep claims below similarity threshold', () => {
      const claims = [
        createClaim('API', 'uses protocol', 'REST'),
        createClaim('API', 'uses protocol', 'GraphQL')
      ];

      const unique = extractor.deduplicateClaims(claims, 0.9);

      expect(unique).toHaveLength(2);
    });

    it('should preserve first occurrence', () => {
      const claim1 = createClaim('API', 'uses', 'REST');
      const claim2 = createClaim('API', 'uses', 'REST');

      const unique = extractor.deduplicateClaims([claim1, claim2]);

      expect(unique[0].id).toBe(claim1.id);
    });
  });
});
