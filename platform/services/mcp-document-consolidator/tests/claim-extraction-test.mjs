#!/usr/bin/env node
/**
 * Test claim extraction with increased Ollama memory
 */

import { spawn } from 'child_process';

const CONFIG = {
  serverCommand: 'node',
  serverArgs: ['dist/server.js'],
  timeout: 600000, // 10 minutes for LLM operations (CPU inference is slow)
};

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

async function runTest() {
  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('  Claim Extraction Test (with 6GB Ollama memory)');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log('Starting MCP server...');
  const server = spawn(CONFIG.serverCommand, CONFIG.serverArgs, {
    cwd: process.cwd(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let stderrOutput = '';
  server.stderr.on('data', (data) => {
    stderrOutput += data.toString();
    // Log LLM activity
    if (data.toString().includes('llama') || data.toString().includes('claim')) {
      process.stdout.write('.');
    }
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

  console.log('Server ready.\n');

  // Test document with clear claims
  const testDocument = `# Authentication API Specification

## Overview

This document specifies the authentication system for our platform.

## Authentication Methods

The API supports JWT-based authentication. All tokens expire after 24 hours.
Users must refresh their tokens before expiration to maintain access.

## Security Requirements

- All API endpoints require HTTPS
- Passwords must be at least 12 characters
- Failed login attempts are limited to 5 per hour
- Two-factor authentication is mandatory for admin accounts

## Rate Limiting

The API enforces rate limiting of 100 requests per minute per user.
Exceeding this limit results in a 429 status code.
`;

  console.log('Testing claim extraction with extract_claims: true...');
  console.log('(This may take 1-3 minutes for LLM processing)\n');

  const startTime = Date.now();

  const response = await sendRequest(server, {
    jsonrpc: '2.0',
    id: ++requestId,
    method: 'tools/call',
    params: {
      name: 'ingest_document',
      arguments: {
        content: testDocument,
        document_type: 'spec',
        extract_claims: true,  // THE KEY TEST
        generate_embeddings: true,
        build_entity_graph: false
      }
    }
  });

  const duration = Date.now() - startTime;

  console.log(`\nCompleted in ${(duration / 1000).toFixed(1)}s\n`);

  if (response.error) {
    console.log('\x1b[31m✗ FAILED\x1b[0m');
    console.log(`Error: ${response.error.message}`);
    server.kill('SIGTERM');
    process.exit(1);
  }

  const result = JSON.parse(response.result.content[0].text);

  console.log('\x1b[32m✓ SUCCESS\x1b[0m');
  console.log('\nResults:');
  console.log(`  Document ID: ${result.document_id}`);
  console.log(`  Sections extracted: ${result.sections_extracted}`);
  console.log(`  Claims extracted: ${result.claims_extracted}`);
  console.log(`  Entities identified: ${result.entities_identified}`);
  console.log(`  Embeddings generated: ${result.embeddings_generated}`);

  if (result.claims_extracted > 0) {
    console.log('\n\x1b[32m✓ Claim extraction is working!\x1b[0m');
  } else {
    console.log('\n\x1b[33m⚠ No claims extracted (LLM may not have returned structured claims)\x1b[0m');
  }

  server.kill('SIGTERM');
  process.exit(0);
}

runTest().catch((error) => {
  console.error('\x1b[31mFatal error:\x1b[0m', error.message);
  process.exit(1);
});
