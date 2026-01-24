export { EmbeddingPipeline, SimpleEmbedding } from './embedding-pipeline.js';
export { OllamaEmbeddingPipeline, type OllamaEmbeddingConfig } from './ollama-embedding-pipeline.js';
export { LLMPipeline, type LLMConfig, type GenerateParams } from './llm-pipeline.js';
export { VerificationPipeline } from './verification-pipeline.js';

import { EmbeddingPipeline, SimpleEmbedding, type EmbeddingPipelineConfig } from './embedding-pipeline.js';
import { OllamaEmbeddingPipeline, type OllamaEmbeddingConfig } from './ollama-embedding-pipeline.js';

export interface EmbeddingService {
  embed(texts: string[]): Promise<number[][]> | number[][];
  embedBatch?(texts: string[], batchSize?: number): Promise<number[][]>;
  initialize?(): Promise<void>;
  shutdown?(): Promise<void>;
}

export type EmbeddingProvider = 'huggingface' | 'ollama' | 'simple';

export interface CreateEmbeddingPipelineOptions {
  provider: EmbeddingProvider;
  huggingface?: EmbeddingPipelineConfig;
  ollama?: OllamaEmbeddingConfig;
}

/**
 * Factory function to create the appropriate embedding pipeline based on provider.
 */
export function createEmbeddingPipeline(options: CreateEmbeddingPipelineOptions): EmbeddingService {
  switch (options.provider) {
    case 'ollama':
      return new OllamaEmbeddingPipeline(options.ollama);
    case 'huggingface':
      return new EmbeddingPipeline(options.huggingface);
    case 'simple':
    default:
      return new SimpleEmbedding();
  }
}
