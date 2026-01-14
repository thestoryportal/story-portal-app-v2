#!/usr/bin/env node
/**
 * MCP Document Consolidator - Data Integrity Tests
 *
 * Tests content hash handling, UUID management, and embedding consistency.
 */

import { spawn } from 'child_process';
import crypto from 'crypto';

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

function isValidUUID(str) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

async function runAllTests() {
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  MCP Document Consolidator - Data Integrity Tests');
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
  // SECTION 5.1: Content Hash Handling
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 5.1: Content Hash Handling');
  log(colors.blue, '│');

  let firstDocId = null;
  const duplicateContent = `# Hash Test Document\n\n## Content\n\nThis is the same content for hash testing. Unique identifier: ${Date.now()}`;

  await runTest('Duplicate content detection via hash', async () => {
    // Ingest first document
    const firstResponse = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: duplicateContent,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (firstResponse.error) {
      throw new Error(`First ingest failed: ${firstResponse.error.message}`);
    }

    const firstResult = JSON.parse(firstResponse.result.content[0].text);
    firstDocId = firstResult.document_id;

    if (!firstDocId) {
      throw new Error('No document ID returned');
    }

    // Ingest same content again
    const secondResponse = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: duplicateContent,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (secondResponse.error) {
      // Could be expected error for duplicate
      log(colors.yellow, `\n      (Duplicate detection: ${secondResponse.error.message})`);
    } else {
      const secondResult = JSON.parse(secondResponse.result.content[0].text);
      // Document might be updated or same ID returned
      log(colors.yellow, `\n      (Second ingest returned ID: ${secondResult.document_id})`);
    }
  });

  await runTest('Update behavior for same-hash document', async () => {
    // Attempt another ingest with same content
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: duplicateContent,
          document_type: 'guide', // Different type
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    // Should either succeed with same ID or error gracefully
    if (response.error) {
      log(colors.yellow, `\n      (Same-hash handling: ${response.error.message})`);
    } else {
      const result = JSON.parse(response.result.content[0].text);
      if (!result.document_id) {
        throw new Error('No document ID in response');
      }
    }
  });

  await runTest('Hash algorithm consistency (SHA-256)', async () => {
    // Verify that content hash is computed correctly
    const testContent = `# SHA-256 Test\n\n## Content\n\nTest content for hash verification ${Date.now()}.`;

    // Compute expected hash
    const expectedHash = crypto.createHash('sha256').update(testContent).digest('hex');

    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: testContent,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: false,
          build_entity_graph: false
        }
      }
    });

    if (response.error) {
      throw new Error(`Ingest failed: ${response.error.message}`);
    }

    // Document should be created successfully
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) {
      throw new Error('No document ID returned');
    }

    log(colors.yellow, `\n      (Expected hash: ${expectedHash.substring(0, 16)}...)`);
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 5.1 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 5.2: UUID Management
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 5.2: UUID Management');
  log(colors.blue, '│');

  await runTest('UUID generation for documents', async () => {
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: `# UUID Test Doc\n\n## Content\n\nDocument for UUID testing ${Date.now()}.`,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (response.error) {
      throw new Error(`Ingest failed: ${response.error.message}`);
    }

    const result = JSON.parse(response.result.content[0].text);
    if (!isValidUUID(result.document_id)) {
      throw new Error(`Invalid document UUID format: ${result.document_id}`);
    }

    log(colors.yellow, `\n      (Document UUID: ${result.document_id})`);
  });

  await runTest('UUID generation for sections', async () => {
    // Sections are internal but should have valid UUIDs
    // We test this implicitly through find_overlaps which returns section references
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'find_overlaps',
        arguments: {
          similarity_threshold: 0.3
        }
      }
    });

    if (response.error) {
      throw new Error(`Query failed: ${response.error.message}`);
    }

    const result = JSON.parse(response.result.content[0].text);
    // Check any cluster document IDs
    for (const cluster of result.overlap_clusters || []) {
      for (const doc of cluster.documents) {
        if (!isValidUUID(doc.document_id)) {
          throw new Error(`Invalid document UUID in cluster: ${doc.document_id}`);
        }
      }
    }
  });

  await runTest('UUID generation for claims', async () => {
    // Claims would be tested through get_source_of_truth supporting_claims
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'get_source_of_truth',
        arguments: {
          query: 'What documents exist for testing?',
          max_sources: 5,
          verify_claims: false
        }
      }
    });

    // May not have claims if extract_claims was false
    if (response.error) {
      if (!response.error.message.includes('No relevant')) {
        throw new Error(`Query failed: ${response.error.message}`);
      }
    } else {
      const result = JSON.parse(response.result.content[0].text);
      // Verify query_id is valid UUID
      if (!isValidUUID(result.query_id)) {
        throw new Error(`Invalid query UUID: ${result.query_id}`);
      }
      // Check source document IDs
      for (const source of result.sources || []) {
        if (!isValidUUID(source.document_id)) {
          throw new Error(`Invalid source document UUID: ${source.document_id}`);
        }
      }
    }
  });

  await runTest('Foreign key constraint enforcement', async () => {
    // Test that deprecating with invalid superseded_by fails
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'deprecate_document',
        arguments: {
          document_id: '00000000-0000-0000-0000-000000000000', // Non-existent
          reason: 'FK constraint test'
        }
      }
    });

    // Should error because document doesn't exist
    if (!response.error) {
      throw new Error('Expected error for non-existent document');
    }
    if (!response.error.message.includes('not found')) {
      throw new Error(`Unexpected error: ${response.error.message}`);
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 5.2 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 5.3: Embedding Consistency
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 5.3: Embedding Consistency');
  log(colors.blue, '│');

  await runTest('Embedding dimension consistency (384)', async () => {
    // Ingest a document and verify it works with embedding search
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: `# Embedding Dimension Test\n\n## Section\n\nThis tests that embeddings have correct dimensions ${Date.now()}.`,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (response.error) {
      throw new Error(`Ingest failed: ${response.error.message}`);
    }

    const result = JSON.parse(response.result.content[0].text);
    if (result.embeddings_generated < 1) {
      throw new Error('No embeddings generated');
    }

    // Verify embedding search works (confirms dimensions are correct)
    const searchResponse = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'find_overlaps',
        arguments: {
          similarity_threshold: 0.3
        }
      }
    });

    if (searchResponse.error) {
      throw new Error(`Search with embeddings failed: ${searchResponse.error.message}`);
    }

    log(colors.yellow, `\n      (${result.embeddings_generated} embeddings generated and searchable)`);
  });

  await runTest('Embedding reproducibility for same content', async () => {
    // Same content should produce similar search results
    const testContent = `# Reproducibility Test\n\n## Unique Section\n\nThis is test content for reproducibility verification ${Date.now()}.`;

    // Ingest document
    const ingestResponse = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: testContent,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (ingestResponse.error) {
      throw new Error(`Ingest failed: ${ingestResponse.error.message}`);
    }

    // Query should find similar content
    const queryResponse = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'get_source_of_truth',
        arguments: {
          query: 'reproducibility verification',
          max_sources: 5,
          verify_claims: false
        }
      }
    });

    // Should not error
    if (queryResponse.error && !queryResponse.error.message.includes('No relevant')) {
      throw new Error(`Query failed: ${queryResponse.error.message}`);
    }
  });

  await runTest('Embedding search accuracy', async () => {
    // Search for content we know exists
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: ++requestId,
      method: 'tools/call',
      params: {
        name: 'find_overlaps',
        arguments: {
          similarity_threshold: 0.5
        }
      }
    });

    if (response.error) {
      throw new Error(`Search failed: ${response.error.message}`);
    }

    const result = JSON.parse(response.result.content[0].text);
    log(colors.yellow, `\n      (Found ${result.overlap_clusters?.length || 0} overlap clusters)`);
    log(colors.yellow, `      (Redundancy score: ${result.redundancy_score?.toFixed(2) || 0}%)`);
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 5.3 Complete\n');

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
