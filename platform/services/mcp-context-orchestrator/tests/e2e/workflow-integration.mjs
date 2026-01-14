#!/usr/bin/env node
/**
 * Full End-to-End Workflow Test
 * Tests the complete Context Orchestrator system workflow
 */

import { spawn, execSync } from 'child_process';
import { createInterface } from 'readline';
import pg from 'pg';
import * as fs from 'fs';
import * as path from 'path';

const SERVER_PATH = './dist/server.js';
const PROJECT_DIR = path.join(process.cwd(), '..');
const HOOKS_DIR = path.join(PROJECT_DIR, '.claude', 'hooks');
const CONTEXTS_DIR = path.join(PROJECT_DIR, '.claude', 'contexts');

const dbConfig = {
  host: process.env.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_PORT || '5433', 10),
  database: process.env.POSTGRES_DB || 'consolidator',
  user: process.env.POSTGRES_USER || 'consolidator',
  password: process.env.POSTGRES_PASSWORD || 'consolidator_secret',
};

class MCPClient {
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

      this.send({
        jsonrpc: '2.0',
        id: this.requestId++,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'e2e-test', version: '1.0.0' }
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
      this.send({ jsonrpc: '2.0', id, method, params });
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

  stop() {
    if (this.process) this.process.kill('SIGTERM');
  }
}

// Run hook via shell
function runHook(hookName, input) {
  const hookPath = path.join(HOOKS_DIR, hookName);
  try {
    const result = execSync(`echo '${JSON.stringify(input)}' | node "${hookPath}"`, {
      cwd: PROJECT_DIR,
      encoding: 'utf8',
      env: { ...process.env, CLAUDE_PROJECT_DIR: PROJECT_DIR }
    });
    return result ? JSON.parse(result) : null;
  } catch (e) {
    return null;
  }
}

async function runE2EWorkflow() {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║     CONTEXT ORCHESTRATOR v3.0 - END-TO-END WORKFLOW TEST    ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  const pool = new pg.Pool(dbConfig);
  const client = new MCPClient();
  const testTaskId = 'e2e-workflow-task';
  const results = [];

  try {
    // ========================================
    // PHASE 1: Setup
    // ========================================
    console.log('━━━ PHASE 1: Setup ━━━');

    // Clean up any leftover test data
    await pool.query("DELETE FROM context_versions WHERE task_id = $1", [testTaskId]);
    await pool.query("DELETE FROM checkpoints WHERE task_id = $1", [testTaskId]);
    await pool.query("DELETE FROM active_sessions WHERE task_id = $1", [testTaskId]);
    await pool.query("DELETE FROM task_contexts WHERE task_id = $1", [testTaskId]);
    console.log('✓ Cleaned previous test data');

    // Create test task
    await pool.query(
      `INSERT INTO task_contexts (task_id, name, status, current_phase, iteration, immediate_context, key_files, keywords)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [testTaskId, 'E2E Workflow Task', 'pending', 'initialization', 1,
       JSON.stringify({ workingOn: 'Setup', lastAction: null, nextStep: 'Start workflow', blockers: [] }),
       JSON.stringify(['test-e2e-workflow.mjs']), JSON.stringify(['e2e', 'test'])]
    );
    console.log('✓ Created test task\n');
    results.push({ phase: 'Setup', passed: true });

    // ========================================
    // PHASE 2: Context Loading (Hook Test)
    // ========================================
    console.log('━━━ PHASE 2: Context Loading (Hook) ━━━');

    const loaderResult = runHook('context-loader-hook.cjs', {
      prompt: 'Continue working on the e2e workflow test',
      userInfo: {}
    });

    const hasContext = loaderResult?.hookSpecificOutput?.additionalContext?.length > 0;
    console.log('Context loader result:', hasContext ? 'Context loaded' : 'No context');
    results.push({ phase: 'Context Loading', passed: hasContext });
    console.log(hasContext ? '✓ Context loader hook works\n' : '✗ Context loader failed\n');

    // ========================================
    // PHASE 3: MCP Server Operations
    // ========================================
    console.log('━━━ PHASE 3: MCP Server Operations ━━━');

    await client.start();
    console.log('✓ MCP server started');

    // Get unified context
    const contextResult = await client.callTool('get_unified_context', { taskId: testTaskId });
    const contextData = JSON.parse(contextResult.content[0].text);
    console.log('✓ get_unified_context:', contextData.task?.name || 'No task');

    // Update task via save_context_snapshot
    const saveResult = await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: {
        status: 'in_progress',
        currentPhase: 'executing',
        iteration: 2,
        immediateContext: {
          workingOn: 'Testing MCP tools',
          lastAction: 'Context loaded successfully',
          nextStep: 'Test checkpoint creation'
        }
      }
    });
    const saveData = JSON.parse(saveResult.content[0].text);
    console.log('✓ save_context_snapshot: Version', saveData.version);

    // Create checkpoint
    const checkpointResult = await client.callTool('create_checkpoint', {
      taskId: testTaskId,
      label: 'e2e-midpoint',
      description: 'Checkpoint during E2E workflow test'
    });
    const checkpointData = JSON.parse(checkpointResult.content[0].text);
    console.log('✓ create_checkpoint:', checkpointData.checkpointId);

    // Update task again
    await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: {
        currentPhase: 'verification',
        iteration: 3
      }
    });
    console.log('✓ Updated task to verification phase');

    // Rollback to checkpoint
    const rollbackResult = await client.callTool('rollback_to', {
      taskId: testTaskId,
      target: { type: 'version', version: saveData.version },
      createBackup: false
    });
    const rollbackData = JSON.parse(rollbackResult.content[0].text);
    console.log('✓ rollback_to: Rolled back to version', rollbackData.rolledBackTo?.identifier);

    // Verify rollback worked
    const verifyResult = await client.callTool('get_unified_context', { taskId: testTaskId });
    const verifyData = JSON.parse(verifyResult.content[0].text);
    const rollbackWorked = verifyData.task?.currentPhase === 'executing';
    console.log('✓ Verified rollback:', rollbackWorked ? 'Phase restored' : 'Phase not restored');

    results.push({ phase: 'MCP Operations', passed: rollbackWorked });
    console.log(rollbackWorked ? '✓ All MCP operations successful\n' : '✗ MCP operations had issues\n');

    // ========================================
    // PHASE 4: Context Saving (Hook Test)
    // ========================================
    console.log('━━━ PHASE 4: Context Saving (Hook) ━━━');

    // Simulate PreToolUse
    runHook('context-saver-hook.cjs', {
      hookEventName: 'PreToolUse',
      toolName: 'Edit',
      toolInput: { file_path: '/test/workflow.ts' }
    });

    // Check heartbeat was written
    const heartbeatPath = path.join(CONTEXTS_DIR, '.session-heartbeat.json');
    const heartbeatExists = fs.existsSync(heartbeatPath);
    console.log('✓ PreToolUse recorded:', heartbeatExists ? 'Heartbeat exists' : 'No heartbeat');

    // Simulate PostToolUse
    runHook('context-saver-hook.cjs', {
      hookEventName: 'PostToolUse',
      toolName: 'Edit',
      toolInput: { file_path: '/test/workflow.ts' },
      toolOutput: { success: true }
    });

    // Check tool history
    const historyPath = path.join(CONTEXTS_DIR, '.tool-history.json');
    const historyExists = fs.existsSync(historyPath);
    console.log('✓ PostToolUse recorded:', historyExists ? 'Tool history exists' : 'No history');

    results.push({ phase: 'Context Saving', passed: heartbeatExists && historyExists });
    console.log((heartbeatExists && historyExists) ? '✓ Context saver hook works\n' : '✗ Context saver had issues\n');

    // ========================================
    // PHASE 5: Recovery Check
    // ========================================
    console.log('━━━ PHASE 5: Recovery Check ━━━');

    const recoveryResult = await client.callTool('check_recovery', {});
    const recoveryData = JSON.parse(recoveryResult.content[0].text);
    console.log('✓ check_recovery: Needs recovery =', recoveryData.needsRecovery);
    console.log('✓ Sessions count:', recoveryData.sessions?.length || 0);

    results.push({ phase: 'Recovery Check', passed: true });
    console.log('✓ Recovery system operational\n');

    // ========================================
    // PHASE 6: Cleanup & Summary
    // ========================================
    console.log('━━━ PHASE 6: Cleanup & Summary ━━━');

    // Complete task
    await client.callTool('save_context_snapshot', {
      taskId: testTaskId,
      updates: {
        status: 'completed',
        currentPhase: 'done',
        immediateContext: {
          workingOn: null,
          lastAction: 'E2E workflow completed successfully',
          nextStep: null
        }
      }
    });
    console.log('✓ Task marked complete');

    client.stop();

    // Clean up test data
    await pool.query("DELETE FROM context_versions WHERE task_id = $1", [testTaskId]);
    await pool.query("DELETE FROM checkpoints WHERE task_id = $1", [testTaskId]);
    await pool.query("DELETE FROM task_contexts WHERE task_id = $1", [testTaskId]);
    console.log('✓ Test data cleaned up');

    await pool.end();

    // ========================================
    // Final Summary
    // ========================================
    console.log('\n╔══════════════════════════════════════════════════════════════╗');
    console.log('║                    E2E WORKFLOW SUMMARY                       ║');
    console.log('╠══════════════════════════════════════════════════════════════╣');

    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;

    for (const r of results) {
      const status = r.passed ? '✓ PASS' : '✗ FAIL';
      console.log(`║ ${status}: ${r.phase.padEnd(20)}                              ║`);
    }

    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log(`║ Total: ${passed} passed, ${failed} failed                                    ║`);
    console.log('╚══════════════════════════════════════════════════════════════╝');

    process.exit(failed > 0 ? 1 : 0);

  } catch (error) {
    console.error('\n✗ E2E workflow failed:', error.message);
    client.stop();
    await pool.end();
    process.exit(1);
  }
}

runE2EWorkflow();
