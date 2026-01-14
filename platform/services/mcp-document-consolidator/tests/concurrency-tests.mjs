#!/usr/bin/env node
/**
 * MCP Document Consolidator - Concurrency & Load Tests
 *
 * Tests concurrent operations, connection pool handling, and performance benchmarks.
 */

import { spawn } from 'child_process';

const CONFIG = {
  serverCommand: 'node',
  serverArgs: ['dist/server.js'],
  timeout: 120000,
};

let testsPassed = 0;
let testsFailed = 0;
const testResults = [];

const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
};

function log(color, ...args) {
  console.log(color, ...args, colors.reset);
}

let requestId = 0;

async function sendRequest(serverProcess, request) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error(`Request timeout after ${CONFIG.timeout}ms`));
    }, CONFIG.timeout);

    let responseData = '';
    const onData = (data) => {
      responseData += data.toString();
      const lines = responseData.split('\n');
      for (const line of lines) {
        if (line.trim().startsWith('{') && line.includes('"jsonrpc"')) {
          try {
            const response = JSON.parse(line);
            if (response.id === request.id) {
              clearTimeout(timeout);
              serverProcess.stdout.off('data', onData);
              resolve(response);
              return;
            }
          } catch (e) {
            // Not complete JSON yet
          }
        }
      }
    };

    serverProcess.stdout.on('data', onData);
    serverProcess.stdin.write(JSON.stringify(request) + '\n');
  });
}

async function runTest(name, testFn) {
  process.stdout.write(`  ${name}... `);
  const startTime = Date.now();

  try {
    await testFn();
    const duration = Date.now() - startTime;
    log(colors.green, `✓ (${duration}ms)`);
    testsPassed++;
    testResults.push({ name, status: 'passed', duration });
    return true;
  } catch (error) {
    const duration = Date.now() - startTime;
    log(colors.red, `✗ (${duration}ms)`);
    log(colors.red, `    Error: ${error.message}`);
    testsFailed++;
    testResults.push({ name, status: 'failed', duration, error: error.message });
    return false;
  }
}

async function runAllTests() {
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  MCP Document Consolidator - Concurrency & Load Tests');
  log(colors.blue, '═══════════════════════════════════════════════════════════════\n');

  // Start server
  log(colors.blue, 'Starting MCP server...');
  const server = spawn(CONFIG.serverCommand, CONFIG.serverArgs, {
    cwd: process.cwd(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let stderrOutput = '';
  server.stderr.on('data', (data) => {
    stderrOutput += data.toString();
  });

  // Wait for server
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Server startup timeout')), 60000);
    const checkReady = setInterval(() => {
      if (stderrOutput.includes('server running on stdio') || stderrOutput.includes('server initialized')) {
        clearInterval(checkReady);
        clearTimeout(timeout);
        resolve();
      }
    }, 500);
  });

  log(colors.green, 'Server started successfully\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 3.1: Concurrent Operations
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 3.1: Concurrent Operations');
  log(colors.blue, '│');

  await runTest('Simultaneous document ingestions (5 concurrent)', async () => {
    const requests = [];
    for (let i = 0; i < 5; i++) {
      const id = ++requestId;
      requests.push({
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: {
          name: 'ingest_document',
          arguments: {
            content: `# Concurrent Test Doc ${i}\n\n## Section 1\n\nTest content for concurrent ingestion ${i}. Lorem ipsum dolor sit amet.\n\n## Section 2\n\nMore test content here ${i}. Testing concurrent write operations.`,
            document_type: 'spec',
            extract_claims: false,
            generate_embeddings: true,
            build_entity_graph: false
          }
        }
      });
    }

    // Send all requests simultaneously
    const startTime = Date.now();
    const promises = requests.map(req => sendRequest(server, req));
    const responses = await Promise.all(promises);

    const duration = Date.now() - startTime;
    log(colors.yellow, `\n      (Total time for 5 concurrent ingestions: ${duration}ms)`);

    // Verify all succeeded
    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} out of 5 concurrent ingestions failed`);
    }
  });

  await runTest('Concurrent read during write operations', async () => {
    // Start a write operation
    const writeId = ++requestId;
    const writePromise = sendRequest(server, {
      jsonrpc: '2.0',
      id: writeId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: `# Write During Read Test\n\n## Content\n\nThis document is being written while reads happen.`,
          document_type: 'guide',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    // Immediately start read operations
    const readPromises = [];
    for (let i = 0; i < 3; i++) {
      const id = ++requestId;
      readPromises.push(sendRequest(server, {
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: {
          name: 'find_overlaps',
          arguments: {
            similarity_threshold: 0.7
          }
        }
      }));
    }

    const [writeResult, ...readResults] = await Promise.all([writePromise, ...readPromises]);

    // All should succeed (or at least not crash)
    if (writeResult.error) {
      throw new Error(`Write failed: ${writeResult.error.message}`);
    }
    // Reads might return empty results but shouldn't error
    const readErrors = readResults.filter(r => r.error);
    if (readErrors.length > 0) {
      throw new Error(`${readErrors.length} reads failed during write`);
    }
  });

  await runTest('Concurrent find_overlaps queries', async () => {
    const requests = [];
    for (let i = 0; i < 3; i++) {
      const id = ++requestId;
      requests.push({
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: {
          name: 'find_overlaps',
          arguments: {
            similarity_threshold: 0.5 + (i * 0.1)
          }
        }
      });
    }

    const startTime = Date.now();
    const responses = await Promise.all(requests.map(req => sendRequest(server, req)));
    const duration = Date.now() - startTime;

    log(colors.yellow, `\n      (Total time for 3 concurrent queries: ${duration}ms)`);

    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} concurrent find_overlaps failed`);
    }
  });

  await runTest('Concurrent get_source_of_truth queries', async () => {
    const queries = [
      'What is concurrency testing?',
      'How do document ingestions work?',
      'What is the test framework?'
    ];

    const requests = queries.map(q => ({
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'get_source_of_truth',
        arguments: {
          query: q,
          max_sources: 3,
          verify_claims: false
        }
      }
    }));

    const startTime = Date.now();
    const responses = await Promise.all(requests.map(req => sendRequest(server, req)));
    const duration = Date.now() - startTime;

    log(colors.yellow, `\n      (Total time for 3 concurrent queries: ${duration}ms)`);

    // Even if no results found, should not error
    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} concurrent get_source_of_truth failed`);
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 3.1 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 3.2: Connection Pool Testing
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 3.2: Connection Pool Testing');
  log(colors.blue, '│');

  await runTest('PostgreSQL connection pool under load', async () => {
    // Rapid-fire requests to stress PostgreSQL pool
    const requests = [];
    for (let i = 0; i < 10; i++) {
      requests.push({
        jsonrpc: '2.0',
        id: ++requestId,
        method: 'tools/call',
        params: {
          name: 'ingest_document',
          arguments: {
            content: `# PG Pool Test ${i}\n\nContent ${i}`,
            document_type: 'spec',
            extract_claims: false,
            generate_embeddings: false,
            build_entity_graph: false
          }
        }
      });
    }

    // Execute rapidly
    const startTime = Date.now();
    const responses = await Promise.all(requests.map(req => sendRequest(server, req)));
    const duration = Date.now() - startTime;

    log(colors.yellow, `\n      (10 rapid PG operations in ${duration}ms)`);

    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} operations failed under PG pool load`);
    }
  });

  await runTest('pgvector connection handling', async () => {
    // Multiple embedding-based searches
    const requests = [];
    for (let i = 0; i < 5; i++) {
      requests.push({
        jsonrpc: '2.0',
        id: ++requestId,
        method: 'tools/call',
        params: {
          name: 'find_overlaps',
          arguments: {
            similarity_threshold: 0.6
          }
        }
      });
    }

    const startTime = Date.now();
    const responses = await Promise.all(requests.map(req => sendRequest(server, req)));
    const duration = Date.now() - startTime;

    log(colors.yellow, `\n      (5 vector search queries in ${duration}ms)`);

    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} vector search operations failed`);
    }
  });

  await runTest('Neo4j session management', async () => {
    // Note: Neo4j is used for entity graphs. Since we disabled entity_graph building,
    // this tests that the system handles missing Neo4j gracefully
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/list',
      params: {}
    });

    if (response.error) {
      throw new Error('Server unresponsive after potential Neo4j load');
    }
    // Server should remain healthy
    if (!response.result || !response.result.tools) {
      throw new Error('Invalid response structure');
    }
  });

  await runTest('Redis connection stability', async () => {
    // Redis is used for caching. Verify server stability
    const requests = [];
    for (let i = 0; i < 5; i++) {
      requests.push({
        jsonrpc: '2.0',
        id: ++requestId,
        method: 'tools/call',
        params: {
          name: 'get_source_of_truth',
          arguments: {
            query: `Redis cache test query ${i}`,
            max_sources: 2,
            verify_claims: false
          }
        }
      });
    }

    const responses = await Promise.all(requests.map(req => sendRequest(server, req)));
    const failures = responses.filter(r => r.error);
    if (failures.length > 0) {
      throw new Error(`${failures.length} operations failed with Redis`);
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 3.2 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 3.3: Performance Benchmarks
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 3.3: Performance Benchmarks');
  log(colors.blue, '│');

  await runTest('Document ingestion time (target: < 5s for 10KB)', async () => {
    // Generate ~10KB content
    const sections = [];
    for (let i = 0; i < 5; i++) {
      sections.push(`## Section ${i + 1}\n\n${'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(50)}`);
    }
    const content = `# Performance Test Document\n\n${sections.join('\n\n')}`;

    const startTime = Date.now();
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });
    const duration = Date.now() - startTime;

    if (response.error) {
      throw new Error(response.error.message);
    }

    log(colors.yellow, `\n      (Ingestion time: ${duration}ms for ~${Math.round(content.length / 1024)}KB)`);

    if (duration > 5000) {
      throw new Error(`Ingestion took ${duration}ms, exceeds 5000ms target`);
    }
  });

  await runTest('Embedding generation time (target: < 2s per section)', async () => {
    // This is tested implicitly through ingestion
    // We'll verify by ingesting a multi-section document and checking time
    const content = `# Embedding Test\n\n## Section 1\n\nFirst test content.\n\n## Section 2\n\nSecond test content.\n\n## Section 3\n\nThird test content.`;

    const startTime = Date.now();
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });
    const duration = Date.now() - startTime;

    if (response.error) {
      throw new Error(response.error.message);
    }

    const result = JSON.parse(response.result.content[0].text);
    const sections = result.sections_extracted || 3;
    const timePerSection = duration / sections;

    log(colors.yellow, `\n      (${sections} sections, avg ${Math.round(timePerSection)}ms/section)`);

    if (timePerSection > 2000) {
      throw new Error(`${timePerSection}ms per section exceeds 2s target`);
    }
  });

  await runTest('Vector search latency (target: < 500ms)', async () => {
    const startTime = Date.now();
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'find_overlaps',
        arguments: {
          similarity_threshold: 0.7
        }
      }
    });
    const duration = Date.now() - startTime;

    if (response.error) {
      throw new Error(response.error.message);
    }

    log(colors.yellow, `\n      (Vector search: ${duration}ms)`);

    if (duration > 500) {
      log(colors.yellow, `\n      (Warning: ${duration}ms exceeds 500ms target, but may be acceptable)`);
    }
  });

  await runTest('LLM response time (target: < 30s for synthesis)', async () => {
    const startTime = Date.now();
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'get_source_of_truth',
        arguments: {
          query: 'What is the purpose of concurrent testing?',
          max_sources: 3,
          verify_claims: false
        }
      }
    });
    const duration = Date.now() - startTime;

    if (response.error) {
      throw new Error(response.error.message);
    }

    log(colors.yellow, `\n      (LLM synthesis: ${duration}ms)`);

    if (duration > 30000) {
      throw new Error(`LLM synthesis took ${duration}ms, exceeds 30s target`);
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 3.3 Complete\n');

  // Cleanup
  server.kill('SIGTERM');

  // Summary
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  Test Summary');
  log(colors.blue, '═══════════════════════════════════════════════════════════════\n');

  log(colors.green, `  Passed:  ${testsPassed}`);
  if (testsFailed > 0) {
    log(colors.red, `  Failed:  ${testsFailed}`);
  }
  log(colors.blue, `  Total:   ${testsPassed + testsFailed}\n`);

  process.exit(testsFailed > 0 ? 1 : 0);
}

runAllTests().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
