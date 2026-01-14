import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { EmbeddingError } from '../errors.js';

interface EmbeddingRequest {
  id: string;
  method: string;
  params: {
    texts: string[];
  };
}

interface EmbeddingResponse {
  id: string;
  result?: number[][];
  error?: { code: number; message: string };
}

interface ReadyMessage {
  status: string;
  model?: string;
}

interface PendingRequest {
  resolve: (embeddings: number[][]) => void;
  reject: (error: Error) => void;
}

export interface EmbeddingPipelineConfig {
  pythonPath?: string;
  modelName?: string;
  batchSize?: number;
  cacheEnabled?: boolean;
}

export class EmbeddingPipeline {
  private pythonProcess: ChildProcess | null = null;
  private requestQueue: Map<string, PendingRequest> = new Map();
  private pythonPath: string;
  private pythonScriptPath: string;
  private modelName: string;
  private isInitialized: boolean = false;
  private buffer: string = '';

  constructor(config?: string | EmbeddingPipelineConfig) {
    if (typeof config === 'string') {
      this.pythonScriptPath = config;
      this.pythonPath = 'python3';
      this.modelName = 'all-MiniLM-L6-v2';
    } else if (config) {
      this.pythonPath = config.pythonPath || 'python3';
      this.modelName = config.modelName || 'all-MiniLM-L6-v2';
      this.pythonScriptPath = path.join(process.cwd(), 'python', 'embedding_service.py');
    } else {
      this.pythonPath = 'python3';
      this.modelName = 'all-MiniLM-L6-v2';
      this.pythonScriptPath = path.join(process.cwd(), 'python', 'embedding_service.py');
    }
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    this.pythonProcess = spawn(this.pythonPath, [this.pythonScriptPath, '--model', this.modelName], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    this.pythonProcess.stdout?.on('data', (data: Buffer) => {
      this.buffer += data.toString();
      this.processBuffer();
    });

    this.pythonProcess.stderr?.on('data', (data: Buffer) => {
      console.error('Embedding service error:', data.toString());
    });

    this.pythonProcess.on('exit', (code) => {
      console.log(`Embedding service exited with code ${code}`);
      this.isInitialized = false;

      // Reject all pending requests
      for (const [, pending] of this.requestQueue) {
        pending.reject(new EmbeddingError('Embedding service exited unexpectedly'));
      }
      this.requestQueue.clear();
    });

    // Wait for the process to be ready
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new EmbeddingError('Embedding service failed to start'));
      }, 30000);

      // Listen for the ready message first, then send a test request
      const readyHandler = (data: Buffer) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line) as ReadyMessage | EmbeddingResponse;
            if ('status' in msg && msg.status === 'ready') {
              // Service is ready, now send test request
              const testId = uuidv4();
              this.requestQueue.set(testId, {
                resolve: () => {
                  clearTimeout(timeout);
                  this.isInitialized = true;
                  this.pythonProcess?.stdout?.removeListener('data', readyHandler);
                  resolve();
                },
                reject: (error) => {
                  clearTimeout(timeout);
                  reject(error);
                }
              });

              const testRequest: EmbeddingRequest = {
                id: testId,
                method: 'embed',
                params: { texts: ['test'] }
              };

              this.pythonProcess?.stdin?.write(JSON.stringify(testRequest) + '\n');
            }
          } catch {
            // Not valid JSON, ignore
          }
        }
      };

      this.pythonProcess?.stdout?.on('data', readyHandler);
    });
  }

  private processBuffer(): void {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      if (!line.trim()) continue;

      try {
        const parsed = JSON.parse(line);

        // Skip ready messages and other non-response messages
        if ('status' in parsed) continue;

        const response = parsed as EmbeddingResponse;
        const pending = this.requestQueue.get(response.id);

        if (pending) {
          if (response.error) {
            pending.reject(new EmbeddingError(response.error.message));
          } else if (response.result) {
            pending.resolve(response.result);
          }
          this.requestQueue.delete(response.id);
        }
      } catch (error) {
        console.error('Failed to parse embedding response:', error);
      }
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (!this.pythonProcess || !this.pythonProcess.stdin) {
      throw new EmbeddingError('Embedding service not available');
    }

    const requestId = uuidv4();

    return new Promise((resolve, reject) => {
      this.requestQueue.set(requestId, { resolve, reject });

      const request: EmbeddingRequest = {
        id: requestId,
        method: 'embed',
        params: { texts }
      };

      this.pythonProcess?.stdin?.write(JSON.stringify(request) + '\n');

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.requestQueue.has(requestId)) {
          this.requestQueue.delete(requestId);
          reject(new EmbeddingError('Embedding request timeout'));
        }
      }, 30000);
    });
  }

  async embedBatch(texts: string[], batchSize: number = 32): Promise<number[][]> {
    const results: number[][] = [];

    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const embeddings = await this.embed(batch);
      results.push(...embeddings);
    }

    return results;
  }

  async shutdown(): Promise<void> {
    if (this.pythonProcess) {
      this.pythonProcess.kill();
      this.pythonProcess = null;
      this.isInitialized = false;
    }
  }
}

/**
 * Fallback embedding using simple word vectors
 * Use when Python service is not available
 */
export class SimpleEmbedding {
  private vocabSize: number = 10000;
  private embeddingDim: number = 384;

  embed(texts: string[]): number[][] {
    return texts.map(text => this.embedText(text));
  }

  private embedText(text: string): number[] {
    const words = text.toLowerCase().split(/\s+/);
    const embedding = new Array(this.embeddingDim).fill(0);

    for (const word of words) {
      const wordVector = this.getWordVector(word);
      for (let i = 0; i < this.embeddingDim; i++) {
        embedding[i] += wordVector[i];
      }
    }

    // Normalize
    const norm = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    if (norm > 0) {
      for (let i = 0; i < embedding.length; i++) {
        embedding[i] /= norm;
      }
    }

    return embedding;
  }

  private getWordVector(word: string): number[] {
    // Simple hash-based word vector
    const hash = this.hashString(word);
    const vector = new Array(this.embeddingDim).fill(0);

    // Use hash to seed pseudo-random values
    for (let i = 0; i < this.embeddingDim; i++) {
      const seed = (hash + i * 31) % this.vocabSize;
      vector[i] = Math.sin(seed) * Math.cos(seed * 0.7);
    }

    return vector;
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }
}
