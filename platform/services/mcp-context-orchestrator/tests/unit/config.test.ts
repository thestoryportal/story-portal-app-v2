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
      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.projectId).toBe('story-portal-app');
      expect(config.contextsDir).toBe('.claude/contexts');
      expect(config.postgres.host).toBe('localhost');
      expect(config.postgres.port).toBe(5433);
      expect(config.postgres.database).toBe('consolidator');
      expect(config.redis.host).toBe('localhost');
      expect(config.redis.port).toBe(6380);
    });

    it('should load config from environment variables', async () => {
      process.env.PROJECT_ID = 'test-project';
      process.env.CONTEXTS_DIR = '/custom/contexts';
      process.env.POSTGRES_HOST = 'db.example.com';
      process.env.POSTGRES_PORT = '5432';
      process.env.POSTGRES_DB = 'mydb';
      process.env.POSTGRES_USER = 'myuser';
      process.env.POSTGRES_PASSWORD = 'mypass';
      process.env.POSTGRES_SSL = 'true';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.projectId).toBe('test-project');
      expect(config.contextsDir).toBe('/custom/contexts');
      expect(config.postgres.host).toBe('db.example.com');
      expect(config.postgres.port).toBe(5432);
      expect(config.postgres.database).toBe('mydb');
      expect(config.postgres.user).toBe('myuser');
      expect(config.postgres.password).toBe('mypass');
      expect(config.postgres.ssl).toBe(true);
    });

    it('should load redis config', async () => {
      process.env.REDIS_HOST = 'redis.example.com';
      process.env.REDIS_PORT = '6379';
      process.env.REDIS_PASSWORD = 'redis-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.redis.host).toBe('redis.example.com');
      expect(config.redis.port).toBe(6379);
      expect(config.redis.password).toBe('redis-pass');
    });

    it('should load neo4j config', async () => {
      process.env.NEO4J_URI = 'bolt://neo4j.example.com:7687';
      process.env.NEO4J_USER = 'neo4j-user';
      process.env.NEO4J_PASSWORD = 'neo4j-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.neo4j.uri).toBe('bolt://neo4j.example.com:7687');
      expect(config.neo4j.username).toBe('neo4j-user');
      expect(config.neo4j.password).toBe('neo4j-pass');
    });

    it('should load elasticsearch config', async () => {
      process.env.ELASTICSEARCH_HOST = 'es.example.com';
      process.env.ELASTICSEARCH_PORT = '9200';
      process.env.ELASTICSEARCH_INDEX = 'test-index';
      process.env.ELASTICSEARCH_USERNAME = 'es-user';
      process.env.ELASTICSEARCH_PASSWORD = 'es-pass';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.elasticsearch.host).toBe('es.example.com');
      expect(config.elasticsearch.port).toBe(9200);
      expect(config.elasticsearch.index).toBe('test-index');
      expect(config.elasticsearch.username).toBe('es-user');
      expect(config.elasticsearch.password).toBe('es-pass');
    });

    it('should load ollama config', async () => {
      process.env.OLLAMA_BASE_URL = 'http://ollama.example.com:11434';
      process.env.OLLAMA_DEFAULT_MODEL = 'mistral:7b';
      process.env.OLLAMA_TIMEOUT = '60000';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.ollama.baseUrl).toBe('http://ollama.example.com:11434');
      expect(config.ollama.defaultModel).toBe('mistral:7b');
      expect(config.ollama.timeout).toBe(60000);
    });

    it('should load integration configs', async () => {
      process.env.ES_MEMORY_ENABLED = 'true';
      process.env.ES_MEMORY_API_URL = 'http://memory.example.com';
      process.env.DOC_CONSOLIDATOR_ENABLED = 'true';
      process.env.DOC_CONSOLIDATOR_API_URL = 'http://docs.example.com';

      const { loadConfig } = await import('../../src/config.js');
      const config = loadConfig();

      expect(config.esMemory.enabled).toBe(true);
      expect(config.esMemory.apiUrl).toBe('http://memory.example.com');
      expect(config.docConsolidator.enabled).toBe(true);
      expect(config.docConsolidator.apiUrl).toBe('http://docs.example.com');
    });
  });

  describe('getDatabaseUrl', () => {
    it('should generate database URL without SSL', async () => {
      const { loadConfig, getDatabaseUrl } = await import('../../src/config.js');
      process.env.POSTGRES_HOST = 'localhost';
      process.env.POSTGRES_PORT = '5432';
      process.env.POSTGRES_DB = 'testdb';
      process.env.POSTGRES_USER = 'testuser';
      process.env.POSTGRES_PASSWORD = 'testpass';
      process.env.POSTGRES_SSL = 'false';

      const config = loadConfig();
      const url = getDatabaseUrl(config);

      expect(url).toBe('postgresql://testuser:testpass@localhost:5432/testdb');
    });

    it('should generate database URL with SSL', async () => {
      const { loadConfig, getDatabaseUrl } = await import('../../src/config.js');
      process.env.POSTGRES_HOST = 'db.example.com';
      process.env.POSTGRES_PORT = '5432';
      process.env.POSTGRES_DB = 'proddb';
      process.env.POSTGRES_USER = 'produser';
      process.env.POSTGRES_PASSWORD = 'prodpass';
      process.env.POSTGRES_SSL = 'true';

      const config = loadConfig();
      const url = getDatabaseUrl(config);

      expect(url).toBe('postgresql://produser:prodpass@db.example.com:5432/proddb?sslmode=require');
    });
  });
});
