#!/usr/bin/env node
/**
 * MCP Document Consolidator - Docker E2E Integration Tests
 *
 * This script tests the MCP server running in Docker containers.
 * It sends JSON-RPC requests via docker exec to the running server.
 */

import { spawn } from 'child_process';

// Test configuration
const CONFIG = {
  containerName: 'consolidator-server',
  timeout: 180000, // 3 minutes for LLM operations
};

// Test state
let testsPassed = 0;
let testsFailed = 0;
let testsSkipped = 0;
const testResults = [];

// Colors for output
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

/**
 * Send a JSON-RPC request to the server via docker exec
 */
async function sendRequest(method, params, id = 1) {
  return new Promise((resolve, reject) => {
    const request = JSON.stringify({
      jsonrpc: '2.0',
      id,
      method,
      params,
    });

    const timeout = setTimeout(() => {
      reject(new Error(`Request timeout after ${CONFIG.timeout}ms`));
    }, CONFIG.timeout);

    // Use docker exec to send the request to the running server
    const dockerProcess = spawn('docker', [
      'exec', '-i', CONFIG.containerName,
      'node', '-e', `
        const req = ${JSON.stringify(request)};
        process.stdin.on('data', (data) => {
          // Server responds on stdout
        });
        // Send request to stdin
        const net = require('net');
        const fs = require('fs');

        // Read server response
        let response = '';
        process.stdin.resume();
        process.stdin.setEncoding('utf8');

        // Write request to stdout (which connects to server stdin)
        console.log(req);
      `
    ], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    dockerProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    dockerProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    dockerProcess.on('close', (code) => {
      clearTimeout(timeout);
      if (code !== 0) {
        reject(new Error(`Docker exec failed: ${stderr || stdout}`));
      } else {
        try {
          // Try to parse JSON response
          const jsonMatch = stdout.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            resolve(JSON.parse(jsonMatch[0]));
          } else {
            reject(new Error(`Invalid response: ${stdout}`));
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${stdout}`));
        }
      }
    });
  });
}

/**
 * Send JSON-RPC request using a simpler approach - write to a file and pipe it
 */
async function sendToolRequest(toolName, toolArgs) {
  return new Promise((resolve, reject) => {
    const request = JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: toolArgs
      }
    });

    const timeout = setTimeout(() => {
      reject(new Error(`Request timeout after ${CONFIG.timeout}ms`));
    }, CONFIG.timeout);

    // Pipe the request through docker exec
    const dockerProcess = spawn('docker', [
      'exec', '-i', CONFIG.containerName,
      'node', 'dist/server.js'
    ], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    dockerProcess.stdout.on('data', (data) => {
      stdout += data.toString();
      // Check if we have a complete JSON response
      try {
        const lines = stdout.split('\n').filter(l => l.trim());
        for (const line of lines) {
          if (line.startsWith('{') && line.includes('"result"')) {
            clearTimeout(timeout);
            dockerProcess.kill();
            resolve(JSON.parse(line));
            return;
          }
          if (line.startsWith('{') && line.includes('"error"')) {
            clearTimeout(timeout);
            dockerProcess.kill();
            resolve(JSON.parse(line));
            return;
          }
        }
      } catch (e) {
        // Continue waiting for complete response
      }
    });

    dockerProcess.stderr.on('data', (data) => {
      stderr += data.toString();
      // Check for server ready message
      if (stderr.includes('server running on stdio') || stderr.includes('server initialized')) {
        // Server is ready, send the request
        dockerProcess.stdin.write(request + '\n');
      }
    });

    dockerProcess.on('close', (code) => {
      clearTimeout(timeout);
      if (!stdout.includes('"result"') && !stdout.includes('"error"')) {
        reject(new Error(`Process exited without response. stderr: ${stderr}`));
      }
    });

    dockerProcess.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });

    // Set a longer timeout for the first request (model loading)
    setTimeout(() => {
      if (!stderr.includes('server running')) {
        // Force send request anyway after delay
        dockerProcess.stdin.write(request + '\n');
      }
    }, 5000);
  });
}

/**
 * Run a single test
 */
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

/**
 * Skip a test
 */
function skipTest(name, reason) {
  log(colors.yellow, `  ${name}... SKIPPED (${reason})`);
  testsSkipped++;
  testResults.push({ name, status: 'skipped', reason });
}

// ============================================================================
// TEST DOCUMENTS
// ============================================================================

const TEST_DOCUMENTS = {
  authSpec: {
    content: `# Authentication Specification

## Overview
This document defines the authentication system for the application.

## Token Configuration
- Access tokens expire after 1 hour
- Refresh tokens expire after 7 days
- Tokens use JWT format with RS256 signing

## Session Management
- Sessions are stored in Redis
- Maximum concurrent sessions: 5 per user
- Inactive sessions timeout after 30 minutes

## Security Requirements
- All passwords must be hashed with bcrypt
- Minimum password length: 12 characters
- Two-factor authentication is required for admin accounts`,
    document_type: 'spec',
    tags: ['auth', 'security', 'tokens'],
  },

  authGuide: {
    content: `# Authentication Implementation Guide

## Overview
Guide for implementing the authentication system.

## Token Handling
Access tokens are valid for 60 minutes (1 hour).
Refresh tokens remain valid for one week.
All tokens use JWT with RS256 algorithm.

## Database Configuration
User sessions are cached in Redis for performance.
Each user can have up to 5 active sessions.

## Password Policy
Use bcrypt for password hashing.
Require at least 12 characters for passwords.
Admin users must enable 2FA.`,
    document_type: 'guide',
    tags: ['auth', 'implementation'],
  },
};

// ============================================================================
// QUICK VALIDATION TEST
// ============================================================================

async function runQuickValidation() {
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  MCP Document Consolidator - Docker E2E Quick Validation');
  log(colors.blue, '═══════════════════════════════════════════════════════════════\n');

  // Check if container is running
  log(colors.blue, 'Checking Docker container status...');
  const containerCheck = spawn('docker', ['ps', '--filter', `name=${CONFIG.containerName}`, '--format', '{{.Status}}']);

  const status = await new Promise((resolve) => {
    let output = '';
    containerCheck.stdout.on('data', d => output += d.toString());
    containerCheck.on('close', () => resolve(output.trim()));
  });

  if (!status || !status.includes('Up')) {
    log(colors.red, `Container ${CONFIG.containerName} is not running!`);
    log(colors.yellow, 'Start it with: docker-compose up -d consolidator');
    process.exit(1);
  }

  log(colors.green, `Container is ${status}\n`);

  // Track document IDs
  const documentIds = {};

  // ──────────────────────────────────────────────────────────────────────────
  // Test 1: Ingest document
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Testing Document Ingestion');
  log(colors.blue, '│');

  await runTest('Ingest auth spec document', async () => {
    const response = await sendToolRequest('ingest_document', {
      content: TEST_DOCUMENTS.authSpec.content,
      document_type: TEST_DOCUMENTS.authSpec.document_type,
      tags: TEST_DOCUMENTS.authSpec.tags,
      extract_claims: false,
      generate_embeddings: true,
      build_entity_graph: false,
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.authSpec = result.document_id;
  });

  await runTest('Ingest auth guide document', async () => {
    const response = await sendToolRequest('ingest_document', {
      content: TEST_DOCUMENTS.authGuide.content,
      document_type: TEST_DOCUMENTS.authGuide.document_type,
      tags: TEST_DOCUMENTS.authGuide.tags,
      extract_claims: false,
      generate_embeddings: true,
      build_entity_graph: false,
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.authGuide = result.document_id;
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Ingestion Tests Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // Test 2: Find overlaps
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Testing Overlap Detection');
  log(colors.blue, '│');

  await runTest('Find overlaps between documents', async () => {
    const response = await sendToolRequest('find_overlaps', {
      scope: [documentIds.authSpec, documentIds.authGuide],
      similarity_threshold: 0.5,
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // Response should have overlap_clusters array
    if (!result.overlap_clusters) {
      throw new Error('No overlap_clusters returned');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Overlap Tests Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // Test 3: Consolidate
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Testing Document Consolidation');
  log(colors.blue, '│');

  await runTest('Consolidate documents', async () => {
    const response = await sendToolRequest('consolidate_documents', {
      document_ids: [documentIds.authSpec, documentIds.authGuide],
      strategy: 'authority_wins',
      dry_run: false,
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    const docId = result.output_document?.document_id ||
                  result.consolidation_id;
    if (!docId) {
      throw new Error('No consolidated document ID returned');
    }
    documentIds.consolidated = docId;
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Consolidation Tests Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // Test 4: Source of Truth
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Testing Source of Truth Query');
  log(colors.blue, '│');

  await runTest('Query source of truth', async () => {
    const response = await sendToolRequest('get_source_of_truth', {
      query: 'How long do access tokens last?',
      scope: [documentIds.authSpec, documentIds.authGuide],
      max_sources: 5,
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.answer) {
      throw new Error('No answer returned');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Source of Truth Tests Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // Test 5: Deprecate
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Testing Document Deprecation');
  log(colors.blue, '│');

  await runTest('Deprecate source document', async () => {
    const response = await sendToolRequest('deprecate_document', {
      document_id: documentIds.authSpec,
      reason: 'Superseded by consolidated document',
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.success && !result.deprecated) {
      throw new Error('Document not marked as deprecated');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Deprecation Tests Complete\n');

  // Print summary
  log(colors.blue, '═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  Test Summary');
  log(colors.blue, '═══════════════════════════════════════════════════════════════\n');

  log(colors.green, `  Passed:  ${testsPassed}`);
  if (testsFailed > 0) {
    log(colors.red, `  Failed:  ${testsFailed}`);
  }
  if (testsSkipped > 0) {
    log(colors.yellow, `  Skipped: ${testsSkipped}`);
  }
  log(colors.blue, `  Total:   ${testsPassed + testsFailed + testsSkipped}\n`);

  process.exit(testsFailed > 0 ? 1 : 0);
}

// Run tests
runQuickValidation().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
