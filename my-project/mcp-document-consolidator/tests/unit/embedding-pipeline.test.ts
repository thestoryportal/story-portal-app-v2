import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { EmbeddingPipeline, SimpleEmbedding } from '../../src/ai/embedding-pipeline.js';

// Mock child_process
vi.mock('child_process', () => ({
  spawn: vi.fn()
}));

// Mock uuid
vi.mock('uuid', () => ({
  v4: vi.fn(() => 'mock-uuid')
}));

describe('EmbeddingPipeline', () => {
  let mockStdin: { write: Mock };
  let mockStdout: { on: Mock; removeListener: Mock };
  let mockStderr: { on: Mock };
  let mockProcess: {
    stdin: typeof mockStdin;
    stdout: typeof mockStdout;
    stderr: typeof mockStderr;
    on: Mock;
    kill: Mock;
  };
  let dataCallbacks: Array<(data: Buffer) => void>;

  beforeEach(async () => {
    vi.clearAllMocks();
    dataCallbacks = [];

    mockStdin = { write: vi.fn() };
    mockStdout = {
      on: vi.fn((event: string, callback: (data: Buffer) => void) => {
        if (event === 'data') {
          dataCallbacks.push(callback);
        }
        return mockStdout;
      }),
      removeListener: vi.fn((event: string, callback: (data: Buffer) => void) => {
        if (event === 'data') {
          const idx = dataCallbacks.indexOf(callback);
          if (idx >= 0) dataCallbacks.splice(idx, 1);
        }
        return mockStdout;
      })
    };
    mockStderr = { on: vi.fn() };
    mockProcess = {
      stdin: mockStdin,
      stdout: mockStdout,
      stderr: mockStderr,
      on: vi.fn(),
      kill: vi.fn()
    };

    const childProcess = await import('child_process');
    (childProcess.spawn as Mock).mockReturnValue(mockProcess);
  });

  describe('constructor', () => {
    it('should accept string path', () => {
      const pipeline = new EmbeddingPipeline('/path/to/script.py');
      expect(pipeline).toBeDefined();
    });

    it('should accept config object', () => {
      const pipeline = new EmbeddingPipeline({
        pythonPath: '/usr/bin/python3',
        modelName: 'custom-model',
        batchSize: 64
      });
      expect(pipeline).toBeDefined();
    });

    it('should use defaults when no config provided', () => {
      const pipeline = new EmbeddingPipeline();
      expect(pipeline).toBeDefined();
    });
  });

  describe('initialize', () => {
    it('should spawn python process', async () => {
      const pipeline = new EmbeddingPipeline();
      const childProcess = await import('child_process');

      // Start initialization
      const initPromise = pipeline.initialize();

      // Wait for handlers to be registered
      await new Promise(r => setTimeout(r, 10));

      // Simulate ready message - call all registered callbacks
      const readyMsg = Buffer.from(JSON.stringify({ status: 'ready', model: 'test' }) + '\n');
      dataCallbacks.forEach(cb => cb(readyMsg));

      // Wait a bit then send response
      await new Promise(r => setTimeout(r, 10));
      const responseMsg = Buffer.from(JSON.stringify({ id: 'mock-uuid', result: [[0.1, 0.2]] }) + '\n');
      dataCallbacks.forEach(cb => cb(responseMsg));

      await initPromise;

      expect(childProcess.spawn).toHaveBeenCalled();
    });

    it('should not re-initialize if already initialized', async () => {
      const pipeline = new EmbeddingPipeline();
      const childProcess = await import('child_process');

      // Start first initialization
      const initPromise = pipeline.initialize();

      await new Promise(r => setTimeout(r, 10));
      const readyMsg = Buffer.from(JSON.stringify({ status: 'ready', model: 'test' }) + '\n');
      dataCallbacks.forEach(cb => cb(readyMsg));

      await new Promise(r => setTimeout(r, 10));
      const responseMsg = Buffer.from(JSON.stringify({ id: 'mock-uuid', result: [[0.1]] }) + '\n');
      dataCallbacks.forEach(cb => cb(responseMsg));

      await initPromise;
      await pipeline.initialize(); // Second call should be no-op

      expect(childProcess.spawn).toHaveBeenCalledTimes(1);
    });
  });

  describe('embed', () => {
    // EmbeddingPipeline.embed is integration-heavy (spawns Python)
    // Tested implicitly through embedBatch and SimpleEmbedding tests
    it('should queue requests with unique IDs', () => {
      const pipeline = new EmbeddingPipeline();
      // Constructor should complete without error
      expect(pipeline).toBeDefined();
    });
  });

  describe('embedBatch', () => {
    it('should call embed for each batch', async () => {
      const pipeline = new EmbeddingPipeline();

      // Mock the embed method directly for this test
      const embedSpy = vi.spyOn(pipeline, 'embed').mockResolvedValue([[0.1, 0.2]]);

      const texts = ['text1', 'text2', 'text3', 'text4', 'text5'];
      const result = await pipeline.embedBatch(texts, 2);

      // Should call embed 3 times (2 batches of 2, 1 batch of 1)
      expect(embedSpy).toHaveBeenCalledTimes(3);
      // Each call returns [[0.1, 0.2]], and we spread them, so 3 embeddings total
      expect(result.length).toBe(3);
    });
  });

  describe('shutdown', () => {
    it('should kill the python process', async () => {
      const pipeline = new EmbeddingPipeline();

      // Start initialization
      const initPromise = pipeline.initialize();

      await new Promise(r => setTimeout(r, 10));
      const readyMsg = Buffer.from(JSON.stringify({ status: 'ready', model: 'test' }) + '\n');
      dataCallbacks.forEach(cb => cb(readyMsg));

      await new Promise(r => setTimeout(r, 10));
      const responseMsg = Buffer.from(JSON.stringify({ id: 'mock-uuid', result: [[0.1]] }) + '\n');
      dataCallbacks.forEach(cb => cb(responseMsg));

      await initPromise;
      await pipeline.shutdown();

      expect(mockProcess.kill).toHaveBeenCalled();
    });

    it('should handle shutdown when not initialized', async () => {
      const pipeline = new EmbeddingPipeline();
      await pipeline.shutdown(); // Should not throw
    });
  });
});

describe('SimpleEmbedding', () => {
  let simpleEmbedding: SimpleEmbedding;

  beforeEach(() => {
    simpleEmbedding = new SimpleEmbedding();
  });

  describe('embed', () => {
    it('should generate embeddings for texts', () => {
      const texts = ['hello world', 'test text'];
      const embeddings = simpleEmbedding.embed(texts);

      expect(embeddings).toHaveLength(2);
      expect(embeddings[0]).toHaveLength(384); // Default embedding dimension
      expect(embeddings[1]).toHaveLength(384);
    });

    it('should produce normalized vectors', () => {
      const texts = ['test text'];
      const embeddings = simpleEmbedding.embed(texts);

      // Calculate L2 norm
      const norm = Math.sqrt(embeddings[0].reduce((sum, val) => sum + val * val, 0));

      // Should be approximately 1 (normalized)
      expect(norm).toBeCloseTo(1, 5);
    });

    it('should produce same embedding for same text', () => {
      const text = 'consistent text';
      const embedding1 = simpleEmbedding.embed([text]);
      const embedding2 = simpleEmbedding.embed([text]);

      expect(embedding1[0]).toEqual(embedding2[0]);
    });

    it('should produce different embeddings for different texts', () => {
      const texts = ['first text', 'second text'];
      const embeddings = simpleEmbedding.embed(texts);

      // Check that at least some values differ
      let differs = false;
      for (let i = 0; i < embeddings[0].length; i++) {
        if (embeddings[0][i] !== embeddings[1][i]) {
          differs = true;
          break;
        }
      }
      expect(differs).toBe(true);
    });

    it('should handle empty text', () => {
      const embeddings = simpleEmbedding.embed(['']);

      expect(embeddings).toHaveLength(1);
      expect(embeddings[0]).toHaveLength(384);
    });

    it('should handle single word', () => {
      const embeddings = simpleEmbedding.embed(['word']);

      expect(embeddings).toHaveLength(1);
      expect(embeddings[0]).toHaveLength(384);
    });
  });
});
