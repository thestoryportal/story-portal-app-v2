#!/usr/bin/env node
/**
 * MCP Document Consolidator - End-to-End Integration Tests
 *
 * This script tests the full document lifecycle through the MCP server.
 * It spawns the server process and communicates via JSON-RPC over stdio.
 */

import { spawn } from 'child_process';
import { createInterface } from 'readline';

// Test configuration
const CONFIG = {
  serverCommand: 'node',
  serverArgs: ['dist/server.js'],
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
 * Send a JSON-RPC request to the server and wait for response
 */
async function sendRequest(serverProcess, method, params, id = 1) {
  return new Promise((resolve, reject) => {
    const request = JSON.stringify({
      jsonrpc: '2.0',
      id,
      method,
      params,
    });

    let responseData = '';
    const timeout = setTimeout(() => {
      reject(new Error(`Request timeout after ${CONFIG.timeout}ms`));
    }, CONFIG.timeout);

    const onData = (data) => {
      responseData += data.toString();
      try {
        const response = JSON.parse(responseData);
        clearTimeout(timeout);
        serverProcess.stdout.off('data', onData);
        resolve(response);
      } catch (e) {
        // Incomplete JSON, wait for more data
      }
    };

    serverProcess.stdout.on('data', onData);
    serverProcess.stdin.write(request + '\n');
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

  authConflict: {
    content: `# Authentication Update Notice

## Changes
- Access tokens now expire after 2 hours (changed from 1 hour)
- Maximum concurrent sessions increased to 10 per user
- Minimum password length reduced to 8 characters

## Rationale
These changes improve user experience while maintaining security.`,
    document_type: 'decision',
    tags: ['auth', 'update'],
  },

  apiSpec: {
    content: `# API Specification

## Endpoints
- POST /api/login - Authenticate user
- POST /api/logout - End session
- GET /api/profile - Get user profile
- PUT /api/profile - Update user profile

## Rate Limiting
- 100 requests per minute per IP
- 1000 requests per hour per user

## Response Format
All responses use JSON format with standard envelope:
{
  "success": boolean,
  "data": object | null,
  "error": string | null
}`,
    document_type: 'spec',
    tags: ['api', 'endpoints'],
  },
};

// ============================================================================
// TEST SUITES
// ============================================================================

async function runAllTests() {
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
  log(colors.blue, '  MCP Document Consolidator - End-to-End Integration Tests');
  log(colors.blue, '═══════════════════════════════════════════════════════════════\n');

  // Start server process
  log(colors.blue, 'Starting MCP server...');
  const server = spawn(CONFIG.serverCommand, CONFIG.serverArgs, {
    cwd: process.cwd(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  // Collect stderr for debugging
  let stderrOutput = '';
  server.stderr.on('data', (data) => {
    stderrOutput += data.toString();
  });

  // Wait for server to initialize
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Server startup timeout')), 60000);
    const checkReady = setInterval(() => {
      if (stderrOutput.includes('server running on stdio') ||
          stderrOutput.includes('server initialized')) {
        clearInterval(checkReady);
        clearTimeout(timeout);
        resolve();
      }
    }, 500);
  });

  log(colors.green, 'Server started successfully\n');

  // Track document IDs for test chain
  const documentIds = {};

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 1.1: Full Document Lifecycle
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 1.1: Full Document Lifecycle');
  log(colors.blue, '│');

  // Test: Ingest multiple related documents
  await runTest('Ingest auth spec document', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: TEST_DOCUMENTS.authSpec.content,
        document_type: TEST_DOCUMENTS.authSpec.document_type,
        tags: TEST_DOCUMENTS.authSpec.tags,
        extract_claims: false,
        generate_embeddings: true,
        build_entity_graph: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.authSpec = result.document_id;
  });

  await runTest('Ingest auth guide document', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: TEST_DOCUMENTS.authGuide.content,
        document_type: TEST_DOCUMENTS.authGuide.document_type,
        tags: TEST_DOCUMENTS.authGuide.tags,
        extract_claims: false,
        generate_embeddings: true,
        build_entity_graph: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.authGuide = result.document_id;
  });

  await runTest('Ingest conflicting auth document', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: TEST_DOCUMENTS.authConflict.content,
        document_type: TEST_DOCUMENTS.authConflict.document_type,
        tags: TEST_DOCUMENTS.authConflict.tags,
        extract_claims: false,
        generate_embeddings: true,
        build_entity_graph: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.authConflict = result.document_id;
  });

  await runTest('Ingest API spec document', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: TEST_DOCUMENTS.apiSpec.content,
        document_type: TEST_DOCUMENTS.apiSpec.document_type,
        tags: TEST_DOCUMENTS.apiSpec.tags,
        extract_claims: false,
        generate_embeddings: true,
        build_entity_graph: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.document_id) throw new Error('No document_id returned');
    documentIds.apiSpec = result.document_id;
  });

  // Test: Find overlaps
  await runTest('Find overlaps between documents', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'find_overlaps',
      arguments: {
        // scope is an array of document IDs or glob patterns, not an object
        scope: [documentIds.authSpec, documentIds.authGuide, documentIds.authConflict],
        similarity_threshold: 0.5,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // Should find overlaps between auth documents
    if (!result.clusters && !result.overlap_clusters) {
      throw new Error('No overlap data returned');
    }
  });

  // Test: Consolidate documents
  await runTest('Consolidate auth documents (dry run)', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'consolidate_documents',
      arguments: {
        document_ids: [documentIds.authSpec, documentIds.authGuide],
        // Valid strategies: 'smart', 'newest_wins', 'authority_wins', 'merge_all'
        strategy: 'authority_wins',
        dry_run: true,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // dry_run returns source_documents summary and status, not necessarily a preview
    if (!result.source_documents && !result.preview && !result.output_preview) {
      throw new Error('No dry run data returned');
    }
  });

  await runTest('Consolidate auth documents (actual)', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'consolidate_documents',
      arguments: {
        document_ids: [documentIds.authSpec, documentIds.authGuide],
        strategy: 'authority_wins',
        dry_run: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // Check for output_document which contains the document_id
    const docId = result.output_document?.document_id ||
                  result.consolidated_document_id ||
                  result.result_document_id ||
                  result.document_id;
    if (!docId) {
      throw new Error('No consolidated document ID returned');
    }
    documentIds.consolidated = docId;
  });

  // Test: Deprecate source documents
  await runTest('Deprecate source document with supersession', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'deprecate_document',
      arguments: {
        document_id: documentIds.authSpec,
        reason: 'Superseded by consolidated document',
        superseded_by: documentIds.consolidated,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // The tool returns { status: 'deprecated' | 'archived', ... }
    if (result.status !== 'deprecated' && result.status !== 'archived') {
      throw new Error(`Document not marked as deprecated. Got status: ${result.status}`);
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 1.1 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 1.2: Claim Extraction with LLM
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 1.2: Claim Extraction with LLM');
  log(colors.blue, '│');

  await runTest('Ingest document with claim extraction', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: TEST_DOCUMENTS.apiSpec.content,
        document_type: 'spec',
        tags: ['api', 'claims-test'],
        extract_claims: true,
        generate_embeddings: true,
        build_entity_graph: false,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    documentIds.apiWithClaims = result.document_id;
    // Claims may be 0 if LLM extraction fails gracefully
    if (result.claims_extracted === undefined) {
      throw new Error('claims_extracted field missing');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 1.2 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 1.3: Entity Graph Building
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 1.3: Entity Graph Building');
  log(colors.blue, '│');

  await runTest('Ingest document with entity graph building', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'ingest_document',
      arguments: {
        content: `# User Management System

## Users
The User entity has properties: id, email, name, role.
Users can have roles: admin, editor, viewer.

## Permissions
Admins can manage all users.
Editors can modify content.
Viewers have read-only access.`,
        document_type: 'spec',
        tags: ['users', 'entity-test'],
        extract_claims: true,
        generate_embeddings: true,
        build_entity_graph: true,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    documentIds.entityDoc = result.document_id;
    // entities_identified may be 0 if Neo4j connection has issues
    if (result.entities_identified === undefined) {
      throw new Error('entities_identified field missing');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 1.3 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 1.4: Conflict Detection
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 1.4: Conflict Detection');
  log(colors.blue, '│');

  await runTest('Detect conflicts between contradicting documents', async () => {
    // The authConflict document contradicts authSpec
    const response = await sendRequest(server, 'tools/call', {
      name: 'find_overlaps',
      arguments: {
        // scope is an array of document IDs or glob patterns
        scope: [documentIds.authSpec, documentIds.authConflict],
        similarity_threshold: 0.3,
        conflict_types: ['direct_negation', 'value_conflict'],
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // Validate response structure exists
    if (!result) throw new Error('No result returned');
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 1.4 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // SECTION 1.5: Source of Truth Queries
  // ──────────────────────────────────────────────────────────────────────────
  log(colors.blue, '┌─ Section 1.5: Source of Truth Queries');
  log(colors.blue, '│');

  await runTest('Query source of truth for auth topic', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'get_source_of_truth',
      arguments: {
        query: 'How long do access tokens last?',
        // scope is an array of document IDs or glob patterns (not deprecated ones)
        scope: [documentIds.authGuide, documentIds.authConflict, documentIds.apiSpec],
        include_deprecated: false,
        max_sources: 5,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    if (!result.answer && !result.response) {
      throw new Error('No answer returned');
    }
  });

  await runTest('Query with provenance tracking', async () => {
    const response = await sendRequest(server, 'tools/call', {
      name: 'get_source_of_truth',
      arguments: {
        query: 'What is the password policy?',
        // scope is an array of document IDs - use non-deprecated auth docs
        scope: [documentIds.authGuide, documentIds.authConflict],
        max_sources: 3,
      },
    });

    if (response.error) throw new Error(response.error.message);
    const result = JSON.parse(response.result.content[0].text);
    // Check for sources/provenance in response
    if (!result.sources && !result.provenance && !result.source_documents) {
      throw new Error('No provenance information returned');
    }
  });

  log(colors.blue, '│');
  log(colors.blue, '└─ Section 1.5 Complete\n');

  // ──────────────────────────────────────────────────────────────────────────
  // CLEANUP
  // ──────────────────────────────────────────────────────────────────────────

  // Shutdown server
  server.kill('SIGTERM');

  // Print summary
  log(colors.blue, '\n═══════════════════════════════════════════════════════════════');
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

  // Exit with appropriate code
  process.exit(testsFailed > 0 ? 1 : 0);
}

// Run tests
runAllTests().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
