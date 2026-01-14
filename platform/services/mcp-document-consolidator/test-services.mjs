import { createDatabaseService } from './dist/db/index.js';
import { EmbeddingPipeline } from './dist/ai/embedding-pipeline.js';

const config = {
  postgres: {
    host: 'localhost',
    port: 5432,
    database: 'docstore',
    user: 'agentic',
    password: 'agentic123'
  },
  python: '/Volumes/Extreme SSD/projects/story-portal-app/my-project/mcp-document-consolidator/python/venv/bin/python'
};

async function testServices() {
  console.log('Testing MCP Document Consolidator components...\n');
  
  // Test 1: PostgreSQL
  console.log('1. Testing PostgreSQL connection...');
  try {
    const db = createDatabaseService(config.postgres);
    await db.initialize();
    const result = await db.query('SELECT COUNT(*) as count FROM documents');
    console.log(`   ✓ PostgreSQL connected. Documents in DB: ${result.rows[0].count}`);
    await db.close();
  } catch (e) {
    console.log(`   ✗ PostgreSQL error: ${e.message}`);
  }

  // Test 2: Neo4j
  console.log('\n2. Testing Neo4j connection...');
  try {
    const response = await fetch('http://localhost:7474/db/neo4j/tx', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + Buffer.from('neo4j:consolidator_secret').toString('base64')
      },
      body: JSON.stringify({ statements: [{ statement: 'RETURN 1 as test' }] })
    });
    const data = await response.json();
    if (data.results?.[0]?.data?.[0]?.row?.[0] === 1) {
      console.log('   ✓ Neo4j connected and responding');
    } else {
      console.log('   ✗ Neo4j unexpected response');
    }
  } catch (e) {
    console.log(`   ✗ Neo4j error: ${e.message}`);
  }

  // Test 3: Ollama
  console.log('\n3. Testing Ollama connection...');
  try {
    const response = await fetch('http://localhost:11434/api/tags');
    const data = await response.json();
    const models = data.models?.map(m => m.name).join(', ') || 'none';
    console.log(`   ✓ Ollama connected. Models: ${models}`);
  } catch (e) {
    console.log(`   ✗ Ollama error: ${e.message}`);
  }

  // Test 4: Embedding Pipeline
  console.log('\n4. Testing Embedding Pipeline...');
  try {
    const pipeline = new EmbeddingPipeline({
      pythonPath: config.python,
      modelName: 'all-MiniLM-L6-v2',
      batchSize: 32,
      cacheEnabled: true
    });
    await pipeline.initialize();
    const embeddings = await pipeline.embed(['This is a test sentence']);
    console.log(`   ✓ Embedding pipeline working. Vector dimension: ${embeddings[0].length}`);
    await pipeline.shutdown();
  } catch (e) {
    console.log(`   ✗ Embedding error: ${e.message}`);
  }

  console.log('\n✓ All component tests complete!');
}

testServices().catch(console.error);
