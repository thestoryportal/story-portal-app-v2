import 'dotenv/config';
import { loadConfig } from './dist/config.js';
import { createDatabaseService } from './dist/db/index.js';
import { EmbeddingPipeline } from './dist/ai/embedding-pipeline.js';

console.error('TEST: Starting');

const config = loadConfig();
const db = createDatabaseService({
  host: config.postgres.host,
  port: config.postgres.port,
  database: config.postgres.database,
  user: config.postgres.user,
  password: config.postgres.password,
  ssl: config.postgres.ssl
});
await db.initialize();
console.error('TEST: DB initialized');

const pipeline = new EmbeddingPipeline({
  pythonPath: config.embedding.pythonPath,
  modelName: config.embedding.model
});

console.error('TEST: Initializing embedding...');
await pipeline.initialize();
console.error('TEST: Embedding initialized, Python PID:', pipeline.pythonProcess?.pid);

process.on('SIGTERM', async () => {
  console.error('TEST: SIGTERM received');
  await pipeline.shutdown();
  console.error('TEST: Pipeline shutdown done');
  await db.close();
  process.exit(0);
});

console.error('TEST: Ready');
