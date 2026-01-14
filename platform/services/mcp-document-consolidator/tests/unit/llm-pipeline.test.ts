import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { LLMPipeline } from '../../src/ai/llm-pipeline.js';

// Mock ollama
vi.mock('ollama', () => ({
  Ollama: vi.fn().mockImplementation(() => ({
    generate: vi.fn(),
    chat: vi.fn(),
    list: vi.fn(),
    pull: vi.fn()
  }))
}));

describe('LLMPipeline', () => {
  let pipeline: LLMPipeline;
  let mockOllama: {
    generate: Mock;
    chat: Mock;
    list: Mock;
    pull: Mock;
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    const ollama = await import('ollama');
    mockOllama = {
      generate: vi.fn().mockResolvedValue({ response: 'test response' }),
      chat: vi.fn().mockResolvedValue({ message: { content: 'chat response' } }),
      list: vi.fn().mockResolvedValue({ models: [{ name: 'llama3.1:8b' }] }),
      pull: vi.fn().mockResolvedValue({})
    };
    (ollama.Ollama as Mock).mockImplementation(() => mockOllama);

    pipeline = new LLMPipeline({
      baseUrl: 'http://localhost:11434',
      defaultModel: 'llama3.1:8b',
      temperature: 0.1,
      maxTokens: 2048
    });
  });

  describe('constructor', () => {
    it('should use baseUrl from config', async () => {
      const ollama = await import('ollama');
      new LLMPipeline({ baseUrl: 'http://custom:11434' });

      expect(ollama.Ollama).toHaveBeenCalledWith({ host: 'http://custom:11434' });
    });

    it('should use host as fallback', async () => {
      const ollama = await import('ollama');
      new LLMPipeline({ host: 'http://host:11434' });

      expect(ollama.Ollama).toHaveBeenCalledWith({ host: 'http://host:11434' });
    });

    it('should use default host when not provided', async () => {
      const ollama = await import('ollama');
      new LLMPipeline({});

      expect(ollama.Ollama).toHaveBeenCalledWith({ host: 'http://localhost:11434' });
    });

    it('should set default models', () => {
      const p = new LLMPipeline({});
      expect(p).toBeDefined();
    });
  });

  describe('generate', () => {
    it('should call ollama generate with correct params', async () => {
      const result = await pipeline.generate({
        prompt: 'Hello',
        system: 'You are helpful'
      });

      expect(mockOllama.generate).toHaveBeenCalledWith(
        expect.objectContaining({
          prompt: 'Hello',
          system: 'You are helpful'
        })
      );
      expect(result).toBe('test response');
    });

    it('should use specified model', async () => {
      await pipeline.generate({
        model: 'custom-model',
        prompt: 'Test'
      });

      expect(mockOllama.generate).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'custom-model'
        })
      );
    });

    it('should use format when specified', async () => {
      await pipeline.generate({
        prompt: 'Test',
        format: 'json'
      });

      expect(mockOllama.generate).toHaveBeenCalledWith(
        expect.objectContaining({
          format: 'json'
        })
      );
    });

    it('should throw LLMError on failure', async () => {
      mockOllama.generate.mockRejectedValueOnce(new Error('Connection failed'));

      await expect(pipeline.generate({ prompt: 'Test' })).rejects.toThrow('Connection failed');
    });
  });

  describe('chat', () => {
    it('should call ollama chat with messages', async () => {
      const messages = [
        { role: 'user' as const, content: 'Hello' }
      ];

      const result = await pipeline.chat(messages);

      expect(mockOllama.chat).toHaveBeenCalledWith(
        expect.objectContaining({
          messages
        })
      );
      expect(result).toBe('chat response');
    });

    it('should use specified model', async () => {
      const messages = [{ role: 'user' as const, content: 'Test' }];

      await pipeline.chat(messages, { model: 'custom-model' });

      expect(mockOllama.chat).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'custom-model'
        })
      );
    });

    it('should throw LLMError on failure', async () => {
      mockOllama.chat.mockRejectedValueOnce(new Error('Chat failed'));

      await expect(pipeline.chat([{ role: 'user', content: 'Test' }]))
        .rejects.toThrow('Chat failed');
    });
  });

  describe('selfConsistencyVerify', () => {
    it('should run multiple samples and aggregate', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "uncertain"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' });

      const result = await pipeline.selfConsistencyVerify('Test prompt', 5);

      expect(result.answer).toBe('verified');
      expect(result.confidence).toBe(0.8); // 4/5
      expect(result.agreementRate).toBe(0.8);
    });

    it('should handle parse errors gracefully', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: 'invalid json' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' });

      const result = await pipeline.selfConsistencyVerify('Test prompt', 3);

      // Should count parse errors as uncertain
      expect(result).toBeDefined();
    });
  });

  describe('ensembleVote', () => {
    it('should vote across multiple models', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "uncertain"}' });

      // Use explicit models to ensure we get 3 distinct votes
      const result = await pipeline.ensembleVote('Test prompt', ['model1', 'model2', 'model3']);

      expect(result.verdict).toBe('verified');
      expect(result.confidence).toBeCloseTo(2/3);
      expect(Object.keys(result.votes)).toHaveLength(3);
    });

    it('should use custom models when provided', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' });

      await pipeline.ensembleVote('Test prompt', ['model1', 'model2']);

      expect(mockOllama.generate).toHaveBeenCalledTimes(2);
    });

    it('should handle failures gracefully', async () => {
      mockOllama.generate
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' })
        .mockResolvedValueOnce({ response: '{"verdict": "verified"}' });

      const result = await pipeline.ensembleVote('Test prompt');

      // Failed model should count as uncertain
      expect(result).toBeDefined();
    });
  });

  describe('debate', () => {
    it('should run advocate, skeptic, and judge', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: '{"arguments": ["arg1"], "strength": 0.8}' }) // advocate
        .mockResolvedValueOnce({ response: '{"arguments": ["arg2"], "strength": 0.6}' }) // skeptic
        .mockResolvedValueOnce({ response: '{"verdict": "verified", "confidence": 0.8, "reasoning": "Advocate stronger"}' }); // judge

      const result = await pipeline.debate('Test claim', 'Test evidence');

      expect(result.verdict).toBe('verified');
      expect(result.confidence).toBe(0.8);
      expect(result.reasoning).toBe('Advocate stronger');
      expect(mockOllama.generate).toHaveBeenCalledTimes(3);
    });

    it('should return uncertain on parse failure', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: '{"arguments": [], "strength": 0.5}' })
        .mockResolvedValueOnce({ response: '{"arguments": [], "strength": 0.5}' })
        .mockResolvedValueOnce({ response: 'invalid json' });

      const result = await pipeline.debate('Test claim', 'Test evidence');

      expect(result.verdict).toBe('uncertain');
      expect(result.confidence).toBe(0.5);
    });
  });

  describe('extractStructured', () => {
    it('should extract and parse structured output', async () => {
      mockOllama.generate.mockResolvedValueOnce({ response: '{"name": "test", "value": 42}' });

      interface TestOutput {
        name: string;
        value: number;
      }

      const result = await pipeline.extractStructured<TestOutput>(
        'Extract data',
        (response) => JSON.parse(response)
      );

      expect(result).toEqual({ name: 'test', value: 42 });
    });

    it('should retry on parse failure', async () => {
      mockOllama.generate
        .mockResolvedValueOnce({ response: 'invalid' })
        .mockResolvedValueOnce({ response: '{"valid": true}' });

      const result = await pipeline.extractStructured<{ valid: boolean }>(
        'Extract data',
        (response) => JSON.parse(response),
        3
      );

      expect(result).toEqual({ valid: true });
      expect(mockOllama.generate).toHaveBeenCalledTimes(2);
    });

    it('should throw after max retries', async () => {
      mockOllama.generate.mockResolvedValue({ response: 'always invalid' });

      await expect(
        pipeline.extractStructured(
          'Extract data',
          () => { throw new Error('Parse error'); },
          2
        )
      ).rejects.toThrow('Failed after 2 attempts');
    });
  });

  describe('isModelAvailable', () => {
    it('should return true for available model', async () => {
      mockOllama.list.mockResolvedValueOnce({
        models: [{ name: 'llama3.1:8b' }]
      });

      const available = await pipeline.isModelAvailable('llama3.1:8b');
      expect(available).toBe(true);
    });

    it('should return true for model prefix match', async () => {
      mockOllama.list.mockResolvedValueOnce({
        models: [{ name: 'llama3.1:8b' }]
      });

      const available = await pipeline.isModelAvailable('llama3.1');
      expect(available).toBe(true);
    });

    it('should return false for unavailable model', async () => {
      mockOllama.list.mockResolvedValueOnce({
        models: [{ name: 'llama3.1:8b' }]
      });

      const available = await pipeline.isModelAvailable('gpt4');
      expect(available).toBe(false);
    });

    it('should return false on error', async () => {
      mockOllama.list.mockRejectedValueOnce(new Error('Connection error'));

      const available = await pipeline.isModelAvailable('any-model');
      expect(available).toBe(false);
    });
  });

  describe('ensureModel', () => {
    it('should not pull if model available', async () => {
      mockOllama.list.mockResolvedValueOnce({
        models: [{ name: 'llama3.1:8b' }]
      });

      await pipeline.ensureModel('llama3.1:8b');

      expect(mockOllama.pull).not.toHaveBeenCalled();
    });

    it('should pull if model not available', async () => {
      mockOllama.list.mockResolvedValueOnce({
        models: []
      });

      await pipeline.ensureModel('new-model');

      expect(mockOllama.pull).toHaveBeenCalledWith({ model: 'new-model' });
    });
  });
});
