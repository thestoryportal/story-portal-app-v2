/**
 * Configuration loader for Context Orchestrator
 * Loads settings from environment variables with sensible defaults
 */

export interface ServerConfig {
  projectId: string;
  contextsDir: string;

  postgres: {
    host: string;
    port: number;
    database: string;
    user: string;
    password: string;
    ssl: boolean;
  };

  redis: {
    host: string;
    port: number;
    password?: string;
  };

  neo4j: {
    uri: string;
    username: string;
    password: string;
  };

  elasticsearch: {
    host: string;
    port: number;
    index: string;
    username?: string;
    password?: string;
  };

  ollama: {
    baseUrl: string;
    defaultModel: string;
    timeout: number;
  };

  esMemory: {
    enabled: boolean;
    apiUrl?: string;
  };

  docConsolidator: {
    enabled: boolean;
    apiUrl?: string;
  };
}

export function loadConfig(): ServerConfig {
  return {
    projectId: process.env.PROJECT_ID || 'story-portal-app',
    contextsDir: process.env.CONTEXTS_DIR || '.claude/contexts',

    postgres: {
      host: process.env.POSTGRES_HOST || 'localhost',
      port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
      database: process.env.POSTGRES_DB || 'agentic_platform',
      user: process.env.POSTGRES_USER || 'postgres',
      password: process.env.POSTGRES_PASSWORD || 'postgres',
      ssl: process.env.POSTGRES_SSL === 'true'
    },

    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379', 10),
      password: process.env.REDIS_PASSWORD || undefined
    },

    neo4j: {
      uri: process.env.NEO4J_URI || 'bolt://localhost:7687',
      username: process.env.NEO4J_USER || 'neo4j',
      password: process.env.NEO4J_PASSWORD || 'neo4j'
    },

    elasticsearch: {
      host: process.env.ELASTICSEARCH_HOST || 'localhost',
      port: parseInt(process.env.ELASTICSEARCH_PORT || '9200', 10),
      index: process.env.ELASTICSEARCH_INDEX || 'context_orchestrator',
      username: process.env.ELASTICSEARCH_USERNAME,
      password: process.env.ELASTICSEARCH_PASSWORD
    },

    ollama: {
      baseUrl: process.env.OLLAMA_BASE_URL || 'http://localhost:11434',
      defaultModel: process.env.OLLAMA_DEFAULT_MODEL || 'llama3.2:3b',
      timeout: parseInt(process.env.OLLAMA_TIMEOUT || '120000', 10)
    },

    esMemory: {
      enabled: process.env.ES_MEMORY_ENABLED !== 'false',
      apiUrl: process.env.ES_MEMORY_API_URL
    },

    docConsolidator: {
      enabled: process.env.DOC_CONSOLIDATOR_ENABLED !== 'false',
      apiUrl: process.env.DOC_CONSOLIDATOR_API_URL
    }
  };
}

/**
 * Get PostgreSQL connection URL from config
 */
export function getDatabaseUrl(config: ServerConfig): string {
  const { host, port, database, user, password, ssl } = config.postgres;
  const sslParam = ssl ? '?sslmode=require' : '';
  return `postgresql://${user}:${password}@${host}:${port}/${database}${sslParam}`;
}
