import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { VerificationPipeline } from '../../src/ai/verification-pipeline.js';
import type { AtomicClaim } from '../../src/types.js';

// Mock child_process
vi.mock('child_process', () => ({
  exec: vi.fn()
}));

vi.mock('util', () => ({
  promisify: vi.fn((fn: unknown) => fn)
}));

describe('VerificationPipeline', () => {
  let pipeline: VerificationPipeline;
  let mockLLM: {
    selfConsistencyVerify: Mock;
    ensembleVote: Mock;
    debate: Mock;
    generate: Mock;
  };
  let mockExec: Mock;

  const createMockClaim = (overrides?: Partial<AtomicClaim>): AtomicClaim => ({
    id: 'claim-1',
    subject: 'testFunction',
    predicate: 'returns',
    object: 'number 42',
    original_text: 'testFunction returns number 42',
    confidence: 0.9,
    section_id: 'section-1',
    ...overrides
  });

  beforeEach(async () => {
    vi.clearAllMocks();

    mockLLM = {
      selfConsistencyVerify: vi.fn().mockResolvedValue({
        answer: 'verified',
        confidence: 0.8,
        agreementRate: 0.8
      }),
      ensembleVote: vi.fn().mockResolvedValue({
        verdict: 'verified',
        confidence: 0.8,
        votes: { model1: 'verified', model2: 'verified' }
      }),
      debate: vi.fn().mockResolvedValue({
        verdict: 'verified',
        confidence: 0.8,
        reasoning: 'Advocate had stronger arguments'
      }),
      generate: vi.fn()
    };

    pipeline = new VerificationPipeline(mockLLM as unknown as import('../../src/ai/llm-pipeline.js').LLMPipeline);

    const childProcess = await import('child_process');
    mockExec = childProcess.exec as unknown as Mock;
    mockExec.mockResolvedValue({ stdout: '', stderr: '' });
  });

  describe('verifyClaim', () => {
    it('should run consistency and ensemble verification', async () => {
      const claim = createMockClaim();
      const result = await pipeline.verifyClaim(claim);

      expect(mockLLM.selfConsistencyVerify).toHaveBeenCalled();
      expect(mockLLM.ensembleVote).toHaveBeenCalled();
      expect(result.verified).toBe(true);
      expect(result.signals).toHaveLength(2);
    });

    it('should run debate for low-confidence claims', async () => {
      const claim = createMockClaim({ confidence: 0.6 });
      await pipeline.verifyClaim(claim);

      expect(mockLLM.debate).toHaveBeenCalled();
    });

    it('should not run debate for high-confidence claims', async () => {
      const claim = createMockClaim({ confidence: 0.9 });
      await pipeline.verifyClaim(claim);

      expect(mockLLM.debate).not.toHaveBeenCalled();
    });

    it('should run code verification for code-related claims', async () => {
      const claim = createMockClaim({
        subject: 'myFunction',
        predicate: 'has parameter',
        object: 'timeout'
      });

      mockExec.mockResolvedValueOnce({
        stdout: 'src/file.ts:10:function myFunction(timeout: number)'
      });

      const result = await pipeline.verifyClaim(claim, '/codebase');

      expect(mockExec).toHaveBeenCalled();
      expect(result.signals.some(s => s.type === 'code')).toBe(true);
    });

    it('should not run code verification without codebase path', async () => {
      const claim = createMockClaim({
        subject: 'myFunction',
        predicate: 'returns',
        object: 'string'
      });

      const result = await pipeline.verifyClaim(claim);

      expect(mockExec).not.toHaveBeenCalled();
      expect(result.signals.every(s => s.type !== 'code')).toBe(true);
    });

    it('should flag low-confidence results for human review', async () => {
      mockLLM.selfConsistencyVerify.mockResolvedValueOnce({
        answer: 'uncertain',
        confidence: 0.4,
        agreementRate: 0.4
      });
      mockLLM.ensembleVote.mockResolvedValueOnce({
        verdict: 'uncertain',
        confidence: 0.4,
        votes: {}
      });

      const claim = createMockClaim();
      const result = await pipeline.verifyClaim(claim);

      expect(result.should_flag_for_human).toBe(true);
    });

    it('should mark as unverified when code verification fails', async () => {
      const claim = createMockClaim({
        subject: 'PORT',
        predicate: 'has value',
        object: '9999'
      });

      mockExec.mockResolvedValueOnce({ stdout: '' }); // No matches

      const result = await pipeline.verifyClaim(claim, '/codebase');

      expect(result.verified).toBe(false);
    });
  });

  describe('isCodeRelatedClaim', () => {
    it('should detect function-related claims', async () => {
      const claim = createMockClaim({
        subject: 'getData',
        predicate: 'is a',
        object: 'function'
      });

      mockExec.mockResolvedValueOnce({ stdout: '' });
      await pipeline.verifyClaim(claim, '/codebase');

      expect(mockExec).toHaveBeenCalled();
    });

    it('should detect config-related claims', async () => {
      const claim = createMockClaim({
        subject: 'timeout',
        predicate: 'is',
        object: 'a config option'
      });

      mockExec.mockResolvedValueOnce({ stdout: '' });
      await pipeline.verifyClaim(claim, '/codebase');

      expect(mockExec).toHaveBeenCalled();
    });

    it('should not flag non-code claims', async () => {
      const claim = createMockClaim({
        subject: 'The application',
        predicate: 'helps with',
        object: 'document management'
      });

      await pipeline.verifyClaim(claim, '/codebase');

      expect(mockExec).not.toHaveBeenCalled();
    });
  });

  describe('verifyAgainstCode', () => {
    it('should find numeric values in codebase', async () => {
      const claim = createMockClaim({
        subject: 'DEFAULT_PORT',
        predicate: 'has value',
        object: '3000'
      });

      mockExec.mockResolvedValueOnce({
        stdout: 'config.ts:5:const DEFAULT_PORT = 3000;\n'
      });

      const result = await pipeline.verifyClaim(claim, '/codebase');
      const codeSignal = result.signals.find(s => s.type === 'code');

      expect(codeSignal?.verified).toBe(true);
      expect(codeSignal?.evidence?.length).toBeGreaterThan(0);
    });

    it('should find string values in codebase', async () => {
      const claim = createMockClaim({
        subject: 'API_PATH',
        predicate: 'equals',
        object: '"/api/v1"'
      });

      mockExec.mockResolvedValueOnce({
        stdout: 'routes.ts:10:const API_PATH = "/api/v1";\n'
      });

      const result = await pipeline.verifyClaim(claim, '/codebase');
      const codeSignal = result.signals.find(s => s.type === 'code');

      expect(codeSignal?.verified).toBe(true);
    });

    it('should handle grep errors gracefully', async () => {
      const claim = createMockClaim({
        subject: 'someFunction',
        predicate: 'uses',
        object: 'regex pattern'
      });

      mockExec.mockRejectedValueOnce(new Error('grep failed'));

      const result = await pipeline.verifyClaim(claim, '/codebase');
      const codeSignal = result.signals.find(s => s.type === 'code');

      expect(codeSignal?.verified).toBe(false);
      expect(codeSignal?.confidence).toBe(0);
    });
  });

  describe('extractValues', () => {
    it('should extract numbers from object', async () => {
      const claim = createMockClaim({
        object: 'port 3000 or timeout 5000'
      });

      // Numbers should be found
      mockExec
        .mockResolvedValueOnce({ stdout: 'file:1:const port = 3000' })
        .mockResolvedValueOnce({ stdout: 'file:2:timeout: 5000' });

      const result = await pipeline.verifyClaim(claim, '/codebase');
      const codeSignal = result.signals.find(s => s.type === 'code');

      expect(codeSignal?.verified).toBe(true);
    });

    it('should extract identifiers from object', async () => {
      const claim = createMockClaim({
        object: 'uses maxRetries and timeoutMs'
      });

      mockExec
        .mockResolvedValueOnce({ stdout: '' })
        .mockResolvedValueOnce({ stdout: '' })
        .mockResolvedValueOnce({ stdout: '' })
        .mockResolvedValueOnce({ stdout: 'config.ts:10:maxRetries: 3' });

      const result = await pipeline.verifyClaim(claim, '/codebase');
      expect(mockExec).toHaveBeenCalled();
    });
  });

  describe('aggregateVerification', () => {
    it('should weight code verification highly', async () => {
      const claim = createMockClaim({
        subject: 'PORT',
        predicate: 'is',
        object: '3000'
      });

      // Code found but LLM uncertain
      mockExec.mockResolvedValueOnce({
        stdout: 'config.ts:1:PORT=3000'
      });
      mockLLM.selfConsistencyVerify.mockResolvedValueOnce({
        answer: 'uncertain',
        confidence: 0.5,
        agreementRate: 0.5
      });
      mockLLM.ensembleVote.mockResolvedValueOnce({
        verdict: 'uncertain',
        confidence: 0.5,
        votes: {}
      });

      const result = await pipeline.verifyClaim(claim, '/codebase');

      // Code weight (0.4) should boost confidence
      expect(result.confidence).toBeGreaterThan(0.5);
    });

    it('should fail verification on refuted verdict', async () => {
      const claim = createMockClaim();

      mockLLM.selfConsistencyVerify.mockResolvedValueOnce({
        answer: 'likely_wrong',
        confidence: 0.8,
        agreementRate: 0.8
      });

      const result = await pipeline.verifyClaim(claim);

      expect(result.verified).toBe(false);
    });
  });

  describe('verifyBatch', () => {
    it('should verify multiple claims with concurrency', async () => {
      const claims = [
        createMockClaim({ id: 'claim-1' }),
        createMockClaim({ id: 'claim-2' }),
        createMockClaim({ id: 'claim-3' })
      ];

      const results = await pipeline.verifyBatch(claims, undefined, 2);

      expect(results.size).toBe(3);
      expect(results.has('claim-1')).toBe(true);
      expect(results.has('claim-2')).toBe(true);
      expect(results.has('claim-3')).toBe(true);
    });

    it('should pass codebase path to individual verifications', async () => {
      const claims = [
        createMockClaim({
          id: 'claim-1',
          subject: 'function',
          predicate: 'exists',
          object: 'in code'
        })
      ];

      mockExec.mockResolvedValue({ stdout: 'file:1:match' });

      await pipeline.verifyBatch(claims, '/codebase', 1);

      expect(mockExec).toHaveBeenCalled();
    });

    it('should handle empty claims array', async () => {
      const results = await pipeline.verifyBatch([]);
      expect(results.size).toBe(0);
    });
  });
});
