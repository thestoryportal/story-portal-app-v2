#!/usr/bin/env node
/**
 * MCP Tools Integration Test
 * Tests each tool via JSON-RPC over stdio
 */

import { spawn } from 'child_process';
import { createInterface } from 'readline';
import pg from 'pg';

const SERVER_PATH = './dist/server.js';

// Database config matching unified infrastructure
const dbConfig = {
  host: process.env.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
  database: process.env.POSTGRES_DB || 'agentic_platform',
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
};

class MCPTestClient {
  constructor() {
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.process = null;
    this.rl = null;
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.process = spawn('node', [SERVER_PATH], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          POSTGRES_HOST: dbConfig.host,
          POSTGRES_PORT: String(dbConfig.port),
          POSTGRES_DB: dbConfig.database,
          POSTGRES_USER: dbConfig.user,
          POSTGRES_PASSWORD: dbConfig.password,
        }
      });

      this.rl = createInterface({ input: this.process.stdout });

      this.rl.on('line', (line) => {
        try {
          const response = JSON.parse(line);
          const pending = this.pendingRequests.get(response.id);
          if (pending) {
            this.pendingRequests.delete(response.id);
            if (response.error) {
              pending.reject(new Error(response.error.message));
            } else {
              pending.resolve(response.result);
            }
          }
        } catch (e) {
          // Ignore non-JSON lines
        }
      });

      this.process.stderr.on('data', (data) => {
        const msg = data.toString();
        if (msg.includes('server initialized')) {
          resolve();
        }
      });

      this.process.on('error', reject);

      // Initialize the connection
      this.send({
        jsonrpc: '2.0',
        id: this.requestId++,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'test-client', version: '1.0.0' }
        }
      });
    });
  }

  send(message) {
    this.process.stdin.write(JSON.stringify(message) + '\n');
  }

  async call(method, params = {}) {
    const id = this.requestId++;
    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
      this.send({
        jsonrpc: '2.0',
        id,
        method,
        params
      });

      // Timeout after 10 seconds
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error('Request timeout'));
        }
      }, 10000);
    });
  }

  async callTool(name, args = {}) {
    return this.call('tools/call', { name, arguments: args });
  }

  async listTools() {
    return this.call('tools/list', {});
  }

  stop() {
    if (this.process) {
      this.process.kill('SIGTERM');
    }
  }
}

// Helper to create test task directly in database
async function createTestTask(pool, taskId, name) {
  const immediateContext = {
    workingOn: 'Running E2E tests',
    lastAction: 'Created test task',
    nextStep: 'Verify task creation',
    blockers: []
  };

  // Set schema for mcp_contexts
  await pool.query('SET search_path TO mcp_contexts');

  await pool.query(
    `INSERT INTO task_contexts (
      task_id, name, description, status, priority,
      current_phase, iteration, immediate_context, key_files, keywords, resume_prompt
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    ON CONFLICT (task_id) DO UPDATE SET
      name = EXCLUDED.name,
      current_phase = EXCLUDED.current_phase,
      iteration = EXCLUDED.iteration,
      immediate_context = EXCLUDED.immediate_context,
      updated_at = NOW()
    RETURNING *`,
    [
      taskId,
      name,
      'E2E Test Task for validating MCP tools',
      'in_progress',
      50,
      'testing',
      1,
      JSON.stringify(immediateContext),
      JSON.stringify(['test-tools.mjs']),
      JSON.stringify(['test', 'e2e']),
      'Continue E2E testing'
    ]
  );
}

// Helper to delete test task and related data
async function deleteTestTask(pool, taskId) {
  await pool.query('DELETE FROM context_versions WHERE task_id = $1', [taskId]);
  await pool.query("DELETE FROM checkpoints WHERE task_id = $1 OR checkpoint_id LIKE '%backup%'", [taskId]);
  await pool.query('DELETE FROM task_contexts WHERE task_id = $1', [taskId]);
}

async function runTests() {
  const client = new MCPTestClient();
  const pool = new pg.Pool(dbConfig);

  // Set search path to mcp_contexts schema
  pool.on('connect', (client) => {
    client.query('SET search_path TO mcp_contexts');
  });

  const results = [];
  const testTaskId = 'test-e2e-task';

  console.log('Setting up test data in PostgreSQL...');
  try {
    await createTestTask(pool, testTaskId, 'E2E Test Task');
    console.log('Test task created in database.\n');
  } catch (e) {
    console.error('Failed to create test task:', e.message);
    process.exit(1);
  }

  console.log('Starting MCP server...');
  await client.start();
  console.log('Server started.\n');

  // Test 1: List Tools
  console.log('=== Test: List Tools ===');
  try {
    const toolsResult = await client.listTools();
    const toolNames = toolsResult.tools.map(t => t.name);
    console.log('Available tools:', toolNames.join(', '));
    results.push({ test: 'list_tools', passed: toolNames.length === 10, details: `${toolNames.length} tools` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'list_tools', passed: false, details: e.message });
  }

  // Test 2: get_unified_context (global only)
  console.log('\n=== Test: get_unified_context (global) ===');
  try {
    const result = await client.callTool('get_unified_context', {});
    const data = JSON.parse(result.content[0].text);
    console.log('Project ID:', data.projectId);
    console.log('Global context loaded:', !!data.global);
    console.log('Tech stack:', data.global?.techStack?.length || 0, 'items');
    results.push({ test: 'get_unified_context', passed: !!data.global && !!data.projectId, details: data.projectId || 'loaded' });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'get_unified_context', passed: false, details: e.message });
  }

  // Test 3: get_unified_context (with task)
  console.log('\n=== Test: get_unified_context (with task) ===');
  try {
    const result = await client.callTool('get_unified_context', { taskId: testTaskId });
    const data = JSON.parse(result.content[0].text);
    console.log('Task loaded:', data.task?.name);
    console.log('Phase:', data.task?.currentPhase);
    results.push({ test: 'get_unified_context_task', passed: data.task?.name === 'E2E Test Task', details: data.task?.name || 'not found' });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'get_unified_context_task', passed: false, details: e.message });
  }

  // Test 4: save_context_snapshot
  console.log('\n=== Test: save_context_snapshot ===');
  try {
    const result = await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: {
        currentPhase: 'testing-snapshot',
        iteration: 2,
        immediateContext: {
          workingOn: 'Testing save_context_snapshot',
          lastAction: 'Updated context',
          nextStep: 'Verify snapshot saved'
        }
      },
      changeSummary: 'Test snapshot save'
    });
    const data = JSON.parse(result.content[0].text);
    console.log('Task saved:', data.taskId);
    console.log('Version:', data.version);
    console.log('Saved to DB:', data.savedTo?.database);
    console.log('Saved to Redis:', data.savedTo?.redis);
    results.push({ test: 'save_context_snapshot', passed: data.success && data.version >= 1, details: `v${data.version}` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'save_context_snapshot', passed: false, details: e.message });
  }

  // Test 5: create_checkpoint
  console.log('\n=== Test: create_checkpoint ===');
  let checkpointId = null;
  try {
    const result = await client.callTool('create_checkpoint', {
      taskId: testTaskId,
      label: 'e2e-test-checkpoint',
      description: 'Checkpoint created during E2E testing'
    });
    const data = JSON.parse(result.content[0].text);
    checkpointId = data.checkpointId;
    console.log('Checkpoint created:', checkpointId);
    results.push({ test: 'create_checkpoint', passed: !!checkpointId, details: checkpointId });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'create_checkpoint', passed: false, details: e.message });
  }

  // Test 6: Update task (create another version for rollback testing)
  console.log('\n=== Test: Update task (create version for rollback) ===');
  try {
    const result = await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: {
        currentPhase: 'verification',
        iteration: 3,
        immediateContext: {
          workingOn: 'Verifying checkpoint',
          lastAction: 'Updated phase to verification',
          nextStep: 'Test rollback'
        }
      },
      changeSummary: 'Update for rollback test'
    });
    const data = JSON.parse(result.content[0].text);
    console.log('Updated to version:', data.version);
    results.push({ test: 'update_task', passed: data.version >= 2, details: `v${data.version}` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'update_task', passed: false, details: e.message });
  }

  // Test 7: rollback_to (by version)
  // Note: Version 2 is the first version created by auto_save trigger when save_context_snapshot runs
  // Version 1 only exists in task_contexts.version column, not in context_versions table
  console.log('\n=== Test: rollback_to (by version) ===');
  try {
    const result = await client.callTool('rollback_to', {
      taskId: testTaskId,
      target: {
        type: 'version',
        version: 2  // First version saved to context_versions by trigger
      },
      createBackup: true
    });
    const data = JSON.parse(result.content[0].text);
    console.log('Rolled back to:', data.rolledBackTo?.type, data.rolledBackTo?.identifier);
    console.log('Current phase:', data.restoredState?.currentPhase);
    results.push({ test: 'rollback_to', passed: data.success, details: `v${data.rolledBackTo?.identifier}` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'rollback_to', passed: false, details: e.message });
  }

  // Test 8: switch_task (switch to same task to verify loading)
  console.log('\n=== Test: switch_task ===');
  try {
    // First update so we have something to switch from
    await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: { iteration: 5 }
    });

    const result = await client.callTool('switch_task', {
      toTaskId: testTaskId,
      sessionId: 'test-session-123'
    });
    const data = JSON.parse(result.content[0].text);
    console.log('Switched to task:', data.newTask?.name);
    console.log('Task status:', data.newTask?.status);
    results.push({ test: 'switch_task', passed: data.success && data.newTask?.taskId === testTaskId, details: data.newTask?.name || 'failed' });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'switch_task', passed: false, details: e.message });
  }

  // Test 9: detect_conflicts
  console.log('\n=== Test: detect_conflicts ===');
  try {
    const result = await client.callTool('detect_conflicts', {});
    const data = JSON.parse(result.content[0].text);
    console.log('New conflicts:', data.summary?.newConflicts ?? 0);
    console.log('Existing conflicts:', data.summary?.existingConflicts ?? 0);
    results.push({ test: 'detect_conflicts', passed: true, details: `${data.summary?.newConflicts ?? 0} new` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'detect_conflicts', passed: false, details: e.message });
  }

  // Test 10: get_task_graph
  console.log('\n=== Test: get_task_graph ===');
  try {
    const result = await client.callTool('get_task_graph', { taskId: testTaskId });
    const data = JSON.parse(result.content[0].text);
    console.log('Nodes:', data.nodes?.length || 0);
    console.log('Edges:', data.edges?.length || 0);
    results.push({ test: 'get_task_graph', passed: true, details: `${data.nodes?.length || 0} nodes` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'get_task_graph', passed: false, details: e.message });
  }

  // Test 11: sync_hot_context
  console.log('\n=== Test: sync_hot_context ===');
  try {
    const result = await client.callTool('sync_hot_context', { taskId: testTaskId });
    const data = JSON.parse(result.content[0].text);
    console.log('Hot context synced:', data.success);
    console.log('File path:', data.filePath);
    results.push({ test: 'sync_hot_context', passed: data.success, details: data.filePath || 'synced' });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'sync_hot_context', passed: false, details: e.message });
  }

  // Test 12: check_recovery
  console.log('\n=== Test: check_recovery ===');
  try {
    const result = await client.callTool('check_recovery', {});
    const data = JSON.parse(result.content[0].text);
    console.log('Needs recovery:', data.needsRecovery);
    console.log('Sessions:', data.sessions?.length || 0);
    results.push({ test: 'check_recovery', passed: true, details: `${data.sessions?.length || 0} sessions` });
  } catch (e) {
    console.log('FAILED:', e.message);
    results.push({ test: 'check_recovery', passed: false, details: e.message });
  }

  // Summary
  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;

  for (const r of results) {
    const status = r.passed ? '✓ PASS' : '✗ FAIL';
    console.log(`${status}: ${r.test} (${r.details})`);
  }

  console.log('----------------------------------------');
  console.log(`Total: ${passed} passed, ${failed} failed`);
  console.log('========================================');

  // Cleanup
  console.log('\nCleaning up test data...');
  try {
    await deleteTestTask(pool, testTaskId);
    console.log('Test task deleted.');
  } catch (e) {
    console.log('Cleanup note:', e.message);
  }

  await pool.end();
  client.stop();
  process.exit(failed > 0 ? 1 : 0);
}

runTests().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
