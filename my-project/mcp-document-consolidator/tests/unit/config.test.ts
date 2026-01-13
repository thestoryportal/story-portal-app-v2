import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock environment before importing config
const originalEnv = process.env;

describe('Config', () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('loadConfig', () => {
    it('should load config with default values', async () => {
      process.env.POSTGRES_PASSWORD = 'test-password';
      process.env.NEO4J_PASSWORD = 'neo4j-password';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.postgres.host).toBe('localhost');
      expect(config.postgres.port).toBe(5432);
      expect(config.postgres.database).toBe('consolidator');
      expect(config.elasticsearch.port).toBe(9200);
      expect(config.neo4j.uri).toBe('bolt://localhost:7687');
      expect(config.ollama.defaultModel).toBe('llama3.1:8b');
    });

    it('should load config from environment variables', async () => {
      process.env.POSTGRES_HOST = 'db.example.com';
      process.env.POSTGRES_PORT = '5433';
      process.env.POSTGRES_DB = 'mydb';
      process.env.POSTGRES_USER = 'myuser';
      process.env.POSTGRES_PASSWORD = 'mypass';
      process.env.POSTGRES_SSL = 'true';
      process.env.NEO4J_PASSWORD = 'neo4j-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.postgres.host).toBe('db.example.com');
      expect(config.postgres.port).toBe(5433);
      expect(config.postgres.database).toBe('mydb');
      expect(config.postgres.user).toBe('myuser');
      expect(config.postgres.password).toBe('mypass');
      expect(config.postgres.ssl).toBe(true);
    });

    it('should load elasticsearch config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.ELASTICSEARCH_HOST = 'es.example.com';
      process.env.ELASTICSEARCH_PORT = '9201';
      process.env.ELASTICSEARCH_USERNAME = 'elastic';
      process.env.ELASTICSEARCH_PASSWORD = 'elastic-pass';
      process.env.ELASTICSEARCH_INDEX = 'my_index';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.elasticsearch.host).toBe('es.example.com');
      expect(config.elasticsearch.port).toBe(9201);
      expect(config.elasticsearch.username).toBe('elastic');
      expect(config.elasticsearch.password).toBe('elastic-pass');
      expect(config.elasticsearch.index).toBe('my_index');
    });

    it('should load neo4j config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_URI = 'bolt://neo4j.example.com:7688';
      process.env.NEO4J_USER = 'neo4j-user';
      process.env.NEO4J_PASSWORD = 'neo4j-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.neo4j.uri).toBe('bolt://neo4j.example.com:7688');
      expect(config.neo4j.username).toBe('neo4j-user');
      expect(config.neo4j.password).toBe('neo4j-pass');
    });

    it('should load redis config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.REDIS_HOST = 'redis.example.com';
      process.env.REDIS_PORT = '6380';
      process.env.REDIS_PASSWORD = 'redis-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.redis.host).toBe('redis.example.com');
      expect(config.redis.port).toBe(6380);
      expect(config.redis.password).toBe('redis-pass');
    });

    it('should load ollama config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.OLLAMA_BASE_URL = 'http://ollama.example.com:11434';
      process.env.OLLAMA_DEFAULT_MODEL = 'mistral:7b';
      process.env.LLM_MODEL_GENERAL = 'llama3:70b';
      process.env.LLM_MODEL_REASONING = 'mixtral:8x7b';
      process.env.LLM_MODEL_CODE = 'codellama:13b';
      process.env.LLM_MODEL_FAST = 'phi:2';
      process.env.LLM_TEMPERATURE = '0.5';
      process.env.LLM_MAX_TOKENS = '4096';
      process.env.LLM_TIMEOUT = '120000';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.ollama.baseUrl).toBe('http://ollama.example.com:11434');
      expect(config.ollama.defaultModel).toBe('mistral:7b');
      expect(config.ollama.models.general).toBe('llama3:70b');
      expect(config.ollama.models.reasoning).toBe('mixtral:8x7b');
      expect(config.ollama.models.code).toBe('codellama:13b');
      expect(config.ollama.models.fast).toBe('phi:2');
      expect(config.ollama.temperature).toBe(0.5);
      expect(config.ollama.maxTokens).toBe(4096);
      expect(config.ollama.timeout).toBe(120000);
    });

    it('should load embedding config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.PYTHON_PATH = '/usr/bin/python3.11';
      process.env.EMBEDDING_MODEL = 'sentence-transformers/all-mpnet-base-v2';
      process.env.EMBEDDING_BATCH_SIZE = '64';
      process.env.EMBEDDING_CACHE_ENABLED = 'false';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.embedding.pythonPath).toBe('/usr/bin/python3.11');
      expect(config.embedding.model).toBe('sentence-transformers/all-mpnet-base-v2');
      expect(config.embedding.batchSize).toBe(64);
      expect(config.embedding.cacheEnabled).toBe(false);
    });

    it('should load processing config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.MAX_CONCURRENT_DOCUMENTS = '20';
      process.env.CLAIM_EXTRACTION_TIMEOUT_MS = '60000';
      process.env.CONFLICT_CONFIDENCE_THRESHOLD = '0.9';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.processing.maxConcurrentDocuments).toBe(20);
      expect(config.processing.claimExtractionTimeoutMs).toBe(60000);
      expect(config.processing.conflictConfidenceThreshold).toBe(0.9);
    });

    it('should load logging config', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';
      process.env.LOG_LEVEL = 'debug';
      process.env.LOG_FORMAT = 'pretty';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.logging.level).toBe('debug');
      expect(config.logging.format).toBe('pretty');
    });
  });

  describe('getConfig', () => {
    it('should return singleton config instance', async () => {
      process.env.POSTGRES_PASSWORD = 'test';
      process.env.NEO4J_PASSWORD = 'test';

      const { getConfig } = await import('../../src/config.js');
      const config1 = getConfig();
      const config2 = getConfig();

      expect(config1).toBe(config2);
    });
  });
});
