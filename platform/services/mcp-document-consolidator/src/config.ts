import { z } from 'zod';

const ConfigSchema = z.object({
  postgres: z.object({
    host: z.string().default('localhost'),
    port: z.number().int().default(5432),
    database: z.string().default('consolidator'),
    user: z.string().default('consolidator'),
    password: z.string(),
    ssl: z.boolean().default(false),
    maxConnections: z.number().int().default(20)
  }),

  neo4j: z.object({
    enabled: z.boolean().default(true),
    uri: z.string().default('bolt://localhost:7687'),
    username: z.string().default('neo4j'),
    password: z.string().default('')
  }),

  redis: z.object({
    host: z.string().default('localhost'),
    port: z.number().int().default(6379),
    password: z.string().optional()
  }),

  ollama: z.object({
    enabled: z.boolean().default(true),
    baseUrl: z.string().default('http://localhost:11434'),
    defaultModel: z.string().default('llama3.1:8b'),
    models: z.object({
      general: z.string().default('llama3.1:8b'),
      reasoning: z.string().default('llama3.1:8b'),
      code: z.string().default('codellama:7b'),
      fast: z.string().default('mistral:7b')
    }),
    temperature: z.number().default(0.1),
    maxTokens: z.number().int().default(2048),
    timeout: z.number().int().default(60000)
  }),

  embedding: z.object({
    enabled: z.boolean().default(true),
    provider: z.enum(['huggingface', 'ollama']).default('ollama'),
    pythonPath: z.string().default('python3'),
    model: z.string().default('all-MiniLM-L6-v2'),
    ollamaModel: z.string().default('nomic-embed-text'),
    ollamaDimensions: z.number().int().default(768),
    batchSize: z.number().int().default(32),
    cacheEnabled: z.boolean().default(true)
  }),

  processing: z.object({
    maxConcurrentDocuments: z.number().int().default(10),
    embeddingBatchSize: z.number().int().default(32),
    claimExtractionTimeoutMs: z.number().int().default(30000),
    conflictConfidenceThreshold: z.number().default(0.8)
  }),

  logging: z.object({
    level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
    format: z.enum(['json', 'pretty']).default('json')
  })
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(): Config {
  return ConfigSchema.parse({
    postgres: {
      host: process.env.POSTGRES_HOST,
      port: parseInt(process.env.POSTGRES_PORT || '5432'),
      database: process.env.POSTGRES_DB,
      user: process.env.POSTGRES_USER,
      password: process.env.POSTGRES_PASSWORD,
      ssl: process.env.POSTGRES_SSL === 'true',
      maxConnections: parseInt(process.env.POSTGRES_MAX_CONNECTIONS || '20')
    },
    neo4j: {
      enabled: process.env.NEO4J_ENABLED !== 'false',
      uri: process.env.NEO4J_URI,
      username: process.env.NEO4J_USER,
      password: process.env.NEO4J_PASSWORD || ''
    },
    redis: {
      host: process.env.REDIS_HOST,
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD
    },
    ollama: {
      enabled: process.env.OLLAMA_ENABLED !== 'false',
      baseUrl: process.env.OLLAMA_BASE_URL,
      defaultModel: process.env.OLLAMA_DEFAULT_MODEL,
      models: {
        general: process.env.LLM_MODEL_GENERAL,
        reasoning: process.env.LLM_MODEL_REASONING,
        code: process.env.LLM_MODEL_CODE,
        fast: process.env.LLM_MODEL_FAST
      },
      temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.1'),
      maxTokens: parseInt(process.env.LLM_MAX_TOKENS || '2048'),
      timeout: parseInt(process.env.LLM_TIMEOUT || '60000')
    },
    embedding: {
      enabled: process.env.EMBEDDING_ENABLED !== 'false',
      provider: process.env.EMBEDDING_PROVIDER as 'huggingface' | 'ollama' | undefined,
      pythonPath: process.env.PYTHON_PATH || process.env.EMBEDDING_PYTHON_PATH,
      model: process.env.EMBEDDING_MODEL,
      ollamaModel: process.env.OLLAMA_EMBEDDING_MODEL,
      ollamaDimensions: parseInt(process.env.OLLAMA_EMBEDDING_DIMENSIONS || '768'),
      batchSize: parseInt(process.env.EMBEDDING_BATCH_SIZE || '32'),
      cacheEnabled: process.env.EMBEDDING_CACHE_ENABLED !== 'false'
    },
    processing: {
      maxConcurrentDocuments: parseInt(process.env.MAX_CONCURRENT_DOCUMENTS || '10'),
      embeddingBatchSize: parseInt(process.env.EMBEDDING_BATCH_SIZE || '32'),
      claimExtractionTimeoutMs: parseInt(process.env.CLAIM_EXTRACTION_TIMEOUT_MS || '30000'),
      conflictConfidenceThreshold: parseFloat(process.env.CONFLICT_CONFIDENCE_THRESHOLD || '0.8')
    },
    logging: {
      level: process.env.LOG_LEVEL as 'debug' | 'info' | 'warn' | 'error' | undefined,
      format: process.env.LOG_FORMAT as 'json' | 'pretty' | undefined
    }
  });
}

// Singleton config instance
let configInstance: Config | null = null;

export function getConfig(): Config {
  if (!configInstance) {
    configInstance = loadConfig();
  }
  return configInstance;
}
