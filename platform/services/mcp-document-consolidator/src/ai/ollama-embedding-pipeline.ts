import { Ollama } from 'ollama';
import { EmbeddingError } from '../errors.js';

export interface OllamaEmbeddingConfig {
  baseUrl?: string;
  model?: string;
  dimensions?: number;
  batchSize?: number;
}

const DEFAULT_CONFIG: Required<OllamaEmbeddingConfig> = {
  baseUrl: 'http://localhost:11434',
  model: 'nomic-embed-text',
  dimensions: 768,
  batchSize: 32
};

/**
 * Embedding pipeline using Ollama's embedding API.
 * Uses nomic-embed-text model by default (768 dimensions).
 */
export class OllamaEmbeddingPipeline {
  private client: Ollama;
  private model: string;
  private dimensions: number;
  private batchSize: number;
  private isInitialized: boolean = false;

  constructor(config?: OllamaEmbeddingConfig) {
    const mergedConfig = { ...DEFAULT_CONFIG, ...config };
    this.client = new Ollama({ host: mergedConfig.baseUrl });
    this.model = mergedConfig.model;
    this.dimensions = mergedConfig.dimensions;
    this.batchSize = mergedConfig.batchSize;
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Test the model by generating an embedding
      const response = await this.client.embed({
        model: this.model,
        input: ['test']
      });

      if (!response.embeddings || response.embeddings.length === 0) {
        throw new Error('No embeddings returned from Ollama');
      }

      const actualDimensions = response.embeddings[0].length;
      if (actualDimensions !== this.dimensions) {
        console.error(
          `Warning: Expected ${this.dimensions} dimensions, got ${actualDimensions}. ` +
          `Updating dimensions to match model output.`
        );
        this.dimensions = actualDimensions;
      }

      this.isInitialized = true;
      console.error(`Ollama embedding pipeline initialized (model: ${this.model}, dimensions: ${this.dimensions})`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new EmbeddingError(
        `Failed to initialize Ollama embedding pipeline: ${message}. ` +
        `Is Ollama running at ${(this.client as any).config?.host || 'localhost:11434'}? ` +
        `Is model ${this.model} pulled?`
      );
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (texts.length === 0) {
      return [];
    }

    try {
      const response = await this.client.embed({
        model: this.model,
        input: texts
      });

      if (!response.embeddings) {
        throw new EmbeddingError('No embeddings returned from Ollama');
      }

      return response.embeddings;
    } catch (error) {
      if (error instanceof EmbeddingError) throw error;
      const message = error instanceof Error ? error.message : String(error);
      throw new EmbeddingError(`Ollama embedding failed: ${message}`);
    }
  }

  async embedBatch(texts: string[], batchSize?: number): Promise<number[][]> {
    const actualBatchSize = batchSize ?? this.batchSize;
    const results: number[][] = [];

    for (let i = 0; i < texts.length; i += actualBatchSize) {
      const batch = texts.slice(i, i + actualBatchSize);
      const embeddings = await this.embed(batch);
      results.push(...embeddings);
    }

    return results;
  }

  async shutdown(): Promise<void> {
    // No cleanup needed for Ollama HTTP client
    this.isInitialized = false;
    console.error('Ollama embedding pipeline shutdown');
  }

  getDimensions(): number {
    return this.dimensions;
  }
}
