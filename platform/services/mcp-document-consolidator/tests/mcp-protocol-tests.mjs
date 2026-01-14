#!/usr/bin/env node
/**
 * MCP Document Consolidator - MCP Protocol Tests
 *
 * Tests JSON-RPC protocol compliance, schema validation, and large document handling.
 */

import { spawn } from 'child_process';

const CONFIG = {
  serverCommand: 'node',
  serverArgs: ['dist/server.js'],
  timeout: 60000,
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
            clearTimeout(timeout);
            serverProcess.stdout.off('data', onData);
            resolve(response);
            return;
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
  log(colors.blue, '  MCP Document Consolidator - MCP Protocol Tests');
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
  // SECTION 2.1: Stdio Transport
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 2.1: Stdio Transport');
  log(colors.blue, '│');

  await runTest('JSON-RPC request parsing', async () => {
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/list',
      params: {}
    });

    if (!response.result && !response.error) {
      throw new Error('No valid response received');
    }
    if (response.jsonrpc !== '2.0') {
      throw new Error('Invalid JSON-RPC version in response');
    }
    if (response.id !== 1) {
      throw new Error('Response ID does not match request');
    }
  });

  await runTest('JSON-RPC response formatting', async () => {
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {}
    });

    // Verify response structure
    if (!response.result) {
      throw new Error('No result in response');
    }
    if (!Array.isArray(response.result.tools)) {
      throw new Error('tools/list should return array of tools');
    }
    // Verify expected tools exist
    const toolNames = response.result.tools.map(t => t.name);
    const expectedTools = ['ingest_document', 'find_overlaps', 'consolidate_documents', 'get_source_of_truth', 'deprecate_document'];
    for (const expected of expectedTools) {
      if (!toolNames.includes(expected)) {
        throw new Error(`Missing expected tool: ${expected}`);
      }
    }
  });

  await runTest('Error response code - MethodNotFound', async () => {
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 3,
      method: 'nonexistent/method',
      params: {}
    });

    if (!response.error) {
      throw new Error('Expected error response for unknown method');
    }
    // MCP MethodNotFound error code is -32601
    if (response.error.code !== -32601) {
      throw new Error(`Expected error code -32601, got ${response.error.code}`);
    }
  });

  await runTest('Error response - missing required parameters', async () => {
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 4,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {} // Missing required 'content' and 'document_type'
      }
    });

    if (!response.error) {
      throw new Error('Expected error for missing required parameters');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 2.1 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 2.2: Tool Schema Validation
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 2.2: Tool Schema Validation');
  log(colors.blue, '│');

  await runTest('ingest_document schema validation', async () => {
    // Test with invalid document_type
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 5,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: 'test content',
          document_type: 'invalid_type' // Invalid enum value
        }
      }
    });

    if (!response.error) {
      throw new Error('Expected schema validation error for invalid document_type');
    }
  });

  await runTest('find_overlaps schema validation', async () => {
    // Test with invalid similarity_threshold
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 6,
      method: 'tools/call',
      params: {
        name: 'find_overlaps',
        arguments: {
          similarity_threshold: 1.5 // Invalid: must be 0-1
        }
      }
    });

    if (!response.error) {
      throw new Error('Expected schema validation error for invalid threshold');
    }
  });

  await runTest('consolidate_documents schema validation', async () => {
    // Test with no document source specified
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 7,
      method: 'tools/call',
      params: {
        name: 'consolidate_documents',
        arguments: {
          strategy: 'smart'
          // Missing: document_ids, scope, or cluster_id
        }
      }
    });

    if (!response.error) {
      throw new Error('Expected schema validation error for missing document source');
    }
  });

  await runTest('get_source_of_truth schema validation', async () => {
    // Test with valid minimal params
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 8,
      method: 'tools/call',
      params: {
        name: 'get_source_of_truth',
        arguments: {
          query: 'What is the test?'
        }
      }
    });

    // Should succeed with just a query
    if (response.error && response.error.message.includes('schema')) {
      throw new Error('Schema validation should pass with just query param');
    }
  });

  await runTest('deprecate_document schema validation', async () => {
    // Test with invalid UUID
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 9,
      method: 'tools/call',
      params: {
        name: 'deprecate_document',
        arguments: {
          document_id: 'not-a-valid-uuid',
          reason: 'test'
        }
      }
    });

    if (!response.error) {
      throw new Error('Expected schema validation error for invalid UUID');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 2.2 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 2.3: Large Document Handling
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 2.3: Large Document Handling');
  log(colors.blue, '│');

  await runTest('Ingestion of document > 100KB', async () => {
    // Generate ~120KB document
    const largeSections = [];
    for (let i = 0; i < 60; i++) {
      largeSections.push(`## Section ${i + 1}\n\n${'Lorem ipsum dolor sit amet. '.repeat(100)}\n`);
    }
    const largeContent = `# Large Test Document\n\n${largeSections.join('\n')}`;

    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 10,
      method: 'tools/call',
      params: {
        name: 'ingest_document',
        arguments: {
          content: largeContent,
          document_type: 'spec',
          extract_claims: false,
          generate_embeddings: true,
          build_entity_graph: false
        }
      }
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    if (result.sections_count < 50) {
      throw new Error(`Expected 50+ sections, got ${result.sections_count}`);
    }
  });

  await runTest('Memory stability after large document', async () => {
    // Run a simple query to verify server is still responsive
    const response = await sendRequest(server, {
      jsonrpc: '2.0',
      id: 11,
      method: 'tools/list',
      params: {}
    });

    if (response.error) {
      throw new Error('Server unresponsive after large document');
    }
    if (!response.result.tools) {
      throw new Error('Invalid response after large document');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 2.3 Complete\n');

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
