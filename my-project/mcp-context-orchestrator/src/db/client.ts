/**
 * PostgreSQL Database Client
 * Handles connection pooling and query execution
 */

import pg from 'pg';
import {
  type TaskContext,
  type TaskContextRow,
  type CreateTaskContextInput,
  type UpdateTaskContextInput,
  type ActiveSession,
  type ActiveSessionRow,
  type ContextVersion,
  type ContextVersionRow,
  type GlobalContext,
  type Checkpoint,
  type TaskRelationship,
  type ContextConflict,
  type CreateCheckpointInput,
  type CreateRelationshipInput,
  type CreateConflictInput,
  type ResolveConflictInput,
  type ConflictResolution,
  rowToTaskContext,
  rowToActiveSession,
} from './schema.js';

const { Pool } = pg;

// Connection pool
let pool: pg.Pool | null = null;

/**
 * Build database URL from environment variables
 */
function getDatabaseConfig(): pg.PoolConfig {
  // Try DATABASE_URL first
  if (process.env.DATABASE_URL) {
    return {
      connectionString: process.env.DATABASE_URL,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    };
  }

  // Fall back to individual environment variables
  return {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5433', 10),
    database: process.env.POSTGRES_DB || 'consolidator',
    user: process.env.POSTGRES_USER || 'consolidator',
    password: process.env.POSTGRES_PASSWORD || 'consolidator_secret',
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  };
}

/**
 * Get or create the database connection pool
 */
export function getPool(): pg.Pool {
  if (!pool) {
    pool = new Pool(getDatabaseConfig());

    // Handle pool errors
    pool.on('error', (err) => {
      console.error('Unexpected database pool error:', err);
    });
  }
  return pool;
}

/**
 * Execute a query with automatic connection handling
 */
export async function query<T extends pg.QueryResultRow>(
  text: string,
  params?: unknown[]
): Promise<pg.QueryResult<T>> {
  const client = await getPool().connect();
  try {
    return await client.query<T>(text, params);
  } finally {
    client.release();
  }
}

/**
 * Execute a transaction with multiple queries
 */
export async function transaction<T>(
  callback: (client: pg.PoolClient) => Promise<T>
): Promise<T> {
  const client = await getPool().connect();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Close the database pool
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

// ============================================================================
// Task Context Operations
// ============================================================================

export async function getTaskContext(taskId: string): Promise<TaskContext | null> {
  const result = await query<TaskContextRow>(
    'SELECT * FROM task_contexts WHERE task_id = $1',
    [taskId]
  );
  if (result.rows.length === 0) return null;
  return rowToTaskContext(result.rows[0]);
}

export async function getAllTaskContexts(
  status?: string
): Promise<TaskContext[]> {
  let sql = 'SELECT * FROM task_contexts';
  const params: unknown[] = [];

  if (status) {
    sql += ' WHERE status = $1';
    params.push(status);
  }

  sql += ' ORDER BY priority ASC, updated_at DESC';

  const result = await query<TaskContextRow>(sql, params);
  return result.rows.map(rowToTaskContext);
}

export async function createTaskContext(
  input: CreateTaskContextInput
): Promise<TaskContext> {
  const immediateContext = {
    workingOn: null,
    lastAction: null,
    nextStep: null,
    blockers: [],
    ...input.immediateContext,
  };

  const result = await query<TaskContextRow>(
    `INSERT INTO task_contexts (
      task_id, name, description, agent_type, status, priority,
      current_phase, immediate_context, key_files, keywords, resume_prompt
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    RETURNING *`,
    [
      input.taskId,
      input.name,
      input.description ?? null,
      input.agentType ?? null,
      input.status ?? 'pending',
      input.priority ?? 50,
      input.currentPhase ?? null,
      JSON.stringify(immediateContext),
      JSON.stringify(input.keyFiles ?? []),
      JSON.stringify(input.keywords ?? []),
      input.resumePrompt ?? null,
    ]
  );

  return rowToTaskContext(result.rows[0]);
}

export async function updateTaskContext(
  taskId: string,
  input: UpdateTaskContextInput
): Promise<TaskContext | null> {
  // Build dynamic update query
  const updates: string[] = [];
  const values: unknown[] = [];
  let paramIndex = 1;

  if (input.name !== undefined) {
    updates.push(`name = $${paramIndex++}`);
    values.push(input.name);
  }
  if (input.description !== undefined) {
    updates.push(`description = $${paramIndex++}`);
    values.push(input.description);
  }
  if (input.status !== undefined) {
    updates.push(`status = $${paramIndex++}`);
    values.push(input.status);
  }
  if (input.priority !== undefined) {
    updates.push(`priority = $${paramIndex++}`);
    values.push(input.priority);
  }
  if (input.currentPhase !== undefined) {
    updates.push(`current_phase = $${paramIndex++}`);
    values.push(input.currentPhase);
  }
  if (input.iteration !== undefined) {
    updates.push(`iteration = $${paramIndex++}`);
    values.push(input.iteration);
  }
  if (input.score !== undefined) {
    updates.push(`score = $${paramIndex++}`);
    values.push(input.score);
  }
  if (input.lockedElements !== undefined) {
    updates.push(`locked_elements = $${paramIndex++}`);
    values.push(JSON.stringify(input.lockedElements));
  }
  if (input.immediateContext !== undefined) {
    updates.push(`immediate_context = immediate_context || $${paramIndex++}`);
    values.push(JSON.stringify(input.immediateContext));
  }
  if (input.keyFiles !== undefined) {
    updates.push(`key_files = $${paramIndex++}`);
    values.push(JSON.stringify(input.keyFiles));
  }
  if (input.technicalDecisions !== undefined) {
    updates.push(`technical_decisions = $${paramIndex++}`);
    values.push(JSON.stringify(input.technicalDecisions));
  }
  if (input.resumePrompt !== undefined) {
    updates.push(`resume_prompt = $${paramIndex++}`);
    values.push(input.resumePrompt);
  }
  if (input.keywords !== undefined) {
    updates.push(`keywords = $${paramIndex++}`);
    values.push(JSON.stringify(input.keywords));
  }

  if (updates.length === 0) {
    return getTaskContext(taskId);
  }

  // Add last_session_at update
  updates.push(`last_session_at = NOW()`);

  values.push(taskId);

  const result = await query<TaskContextRow>(
    `UPDATE task_contexts SET ${updates.join(', ')} WHERE task_id = $${paramIndex} RETURNING *`,
    values
  );

  if (result.rows.length === 0) return null;
  return rowToTaskContext(result.rows[0]);
}

export async function deleteTaskContext(taskId: string): Promise<boolean> {
  const result = await query(
    'DELETE FROM task_contexts WHERE task_id = $1',
    [taskId]
  );
  return (result.rowCount ?? 0) > 0;
}

// ============================================================================
// Session Operations
// ============================================================================

export async function getActiveSession(sessionId: string): Promise<ActiveSession | null> {
  const result = await query<ActiveSessionRow>(
    'SELECT * FROM active_sessions WHERE session_id = $1',
    [sessionId]
  );
  if (result.rows.length === 0) return null;
  return rowToActiveSession(result.rows[0]);
}

export async function getSessionsNeedingRecovery(): Promise<ActiveSession[]> {
  const result = await query<ActiveSessionRow>(
    `SELECT * FROM active_sessions
     WHERE recovery_needed = TRUE AND status != 'recovered'
     ORDER BY last_heartbeat DESC`
  );
  return result.rows.map(rowToActiveSession);
}

export async function createSession(
  sessionId: string,
  taskId?: string,
  projectDir?: string,
  gitBranch?: string
): Promise<ActiveSession> {
  const result = await query<ActiveSessionRow>(
    `INSERT INTO active_sessions (session_id, task_id, project_dir, git_branch)
     VALUES ($1, $2, $3, $4)
     RETURNING *`,
    [sessionId, taskId ?? null, projectDir ?? null, gitBranch ?? null]
  );
  return rowToActiveSession(result.rows[0]);
}

export async function updateSessionHeartbeat(sessionId: string): Promise<void> {
  await query(
    'UPDATE active_sessions SET last_heartbeat = NOW() WHERE session_id = $1',
    [sessionId]
  );
}

export async function markSessionForRecovery(
  sessionId: string,
  recoveryType: string,
  contextSnapshot: Record<string, unknown>,
  conversationSummary?: string
): Promise<void> {
  await query(
    `UPDATE active_sessions SET
      recovery_needed = TRUE,
      recovery_type = $2,
      context_snapshot = $3,
      conversation_summary = $4,
      status = $2
     WHERE session_id = $1`,
    [sessionId, recoveryType, JSON.stringify(contextSnapshot), conversationSummary ?? null]
  );
}

export async function endSession(sessionId: string): Promise<void> {
  await query(
    `UPDATE active_sessions SET
      status = 'ended',
      ended_at = NOW(),
      recovery_needed = FALSE
     WHERE session_id = $1`,
    [sessionId]
  );
}

export async function markSessionRecovered(sessionId: string): Promise<void> {
  await query(
    `UPDATE active_sessions SET
      status = 'recovered',
      recovery_needed = FALSE
     WHERE session_id = $1`,
    [sessionId]
  );
}

// ============================================================================
// Context Version Operations
// ============================================================================

export async function getContextVersions(
  taskId: string,
  limit = 10
): Promise<ContextVersion[]> {
  const result = await query<ContextVersionRow>(
    `SELECT * FROM context_versions
     WHERE task_id = $1
     ORDER BY version DESC
     LIMIT $2`,
    [taskId, limit]
  );
  return result.rows.map((row) => ({
    id: row.id,
    taskId: row.task_id,
    version: row.version,
    snapshot: row.snapshot,
    changeSummary: row.change_summary ?? undefined,
    changeType: row.change_type ?? undefined,
    createdBy: row.created_by ?? undefined,
    sessionId: row.session_id ?? undefined,
    createdAt: row.created_at,
  }));
}

export async function createContextVersion(
  taskId: string,
  snapshot: Record<string, unknown>,
  changeType: string,
  changeSummary?: string,
  createdBy?: string,
  sessionId?: string
): Promise<ContextVersion> {
  // Get next version number
  const versionResult = await query<{ max: number }>(
    'SELECT COALESCE(MAX(version), 0) + 1 as max FROM context_versions WHERE task_id = $1',
    [taskId]
  );
  const nextVersion = versionResult.rows[0].max;

  const result = await query<ContextVersionRow>(
    `INSERT INTO context_versions (task_id, version, snapshot, change_type, change_summary, created_by, session_id)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     RETURNING *`,
    [taskId, nextVersion, JSON.stringify(snapshot), changeType, changeSummary ?? null, createdBy ?? null, sessionId ?? null]
  );

  const row = result.rows[0];
  return {
    id: row.id,
    taskId: row.task_id,
    version: row.version,
    snapshot: row.snapshot,
    changeSummary: row.change_summary ?? undefined,
    changeType: row.change_type ?? undefined,
    createdBy: row.created_by ?? undefined,
    sessionId: row.session_id ?? undefined,
    createdAt: row.created_at,
  };
}

export async function rollbackToVersion(
  taskId: string,
  version: number
): Promise<TaskContext | null> {
  return transaction(async (client) => {
    // Get the version snapshot
    const versionResult = await client.query<ContextVersionRow>(
      'SELECT * FROM context_versions WHERE task_id = $1 AND version = $2',
      [taskId, version]
    );

    if (versionResult.rows.length === 0) {
      throw new Error(`Version ${version} not found for task ${taskId}`);
    }

    const snapshot = versionResult.rows[0].snapshot as unknown as TaskContextRow;

    // Update task context with snapshot data
    await client.query(
      `UPDATE task_contexts SET
        name = $2,
        description = $3,
        status = $4,
        priority = $5,
        current_phase = $6,
        iteration = $7,
        score = $8,
        locked_elements = $9,
        immediate_context = $10,
        key_files = $11,
        technical_decisions = $12,
        resume_prompt = $13,
        keywords = $14
       WHERE task_id = $1`,
      [
        taskId,
        snapshot.name,
        snapshot.description,
        snapshot.status,
        snapshot.priority,
        snapshot.current_phase,
        snapshot.iteration,
        snapshot.score,
        JSON.stringify(snapshot.locked_elements),
        JSON.stringify(snapshot.immediate_context),
        JSON.stringify(snapshot.key_files),
        JSON.stringify(snapshot.technical_decisions),
        snapshot.resume_prompt,
        JSON.stringify(snapshot.keywords),
      ]
    );

    // Note: auto_save_context_version trigger creates version record automatically
    // when task_contexts is updated

    // Return updated context
    const result = await client.query<TaskContextRow>(
      'SELECT * FROM task_contexts WHERE task_id = $1',
      [taskId]
    );
    return rowToTaskContext(result.rows[0]);
  });
}

// ============================================================================
// Global Context Operations
// ============================================================================

export async function getGlobalContext(projectId: string): Promise<GlobalContext | null> {
  const result = await query<{
    id: string;
    project_id: string;
    project_name: string;
    description: string | null;
    hard_rules: string[];
    tech_stack: string[];
    key_paths: Record<string, string>;
    services: Record<string, string>;
    active_task_id: string | null;
    orchestrator_context: Record<string, unknown>;
    created_at: Date;
    updated_at: Date;
    version: number;
  }>(
    'SELECT * FROM global_context WHERE project_id = $1',
    [projectId]
  );

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  return {
    id: row.id,
    projectId: row.project_id,
    projectName: row.project_name,
    description: row.description ?? undefined,
    hardRules: row.hard_rules,
    techStack: row.tech_stack,
    keyPaths: row.key_paths,
    services: row.services,
    activeTaskId: row.active_task_id ?? undefined,
    orchestratorContext: row.orchestrator_context,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    version: row.version,
  };
}

export async function updateGlobalContext(
  projectId: string,
  updates: Partial<GlobalContext>
): Promise<GlobalContext | null> {
  const updateFields: string[] = [];
  const values: unknown[] = [];
  let paramIndex = 1;

  if (updates.hardRules !== undefined) {
    updateFields.push(`hard_rules = $${paramIndex++}`);
    values.push(JSON.stringify(updates.hardRules));
  }
  if (updates.techStack !== undefined) {
    updateFields.push(`tech_stack = $${paramIndex++}`);
    values.push(JSON.stringify(updates.techStack));
  }
  if (updates.keyPaths !== undefined) {
    updateFields.push(`key_paths = $${paramIndex++}`);
    values.push(JSON.stringify(updates.keyPaths));
  }
  if (updates.services !== undefined) {
    updateFields.push(`services = $${paramIndex++}`);
    values.push(JSON.stringify(updates.services));
  }
  if (updates.activeTaskId !== undefined) {
    updateFields.push(`active_task_id = $${paramIndex++}`);
    values.push(updates.activeTaskId);
  }
  if (updates.orchestratorContext !== undefined) {
    updateFields.push(`orchestrator_context = $${paramIndex++}`);
    values.push(JSON.stringify(updates.orchestratorContext));
  }

  if (updateFields.length === 0) {
    return getGlobalContext(projectId);
  }

  values.push(projectId);

  await query(
    `UPDATE global_context SET ${updateFields.join(', ')} WHERE project_id = $${paramIndex}`,
    values
  );

  return getGlobalContext(projectId);
}

// ============================================================================
// Checkpoint Operations
// ============================================================================

export async function createCheckpoint(
  input: CreateCheckpointInput
): Promise<Checkpoint> {
  const result = await query<{
    id: string;
    checkpoint_id: string;
    label: string;
    description: string | null;
    checkpoint_type: string;
    task_id: string | null;
    scope: string;
    included_tasks: string[];
    snapshot: Record<string, unknown>;
    es_memory_id: string | null;
    created_by: string | null;
    session_id: string | null;
    created_at: Date;
  }>(
    `INSERT INTO checkpoints (
      checkpoint_id, label, description, checkpoint_type, task_id,
      scope, included_tasks, snapshot, es_memory_id, created_by, session_id
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    RETURNING *`,
    [
      input.checkpointId,
      input.label,
      input.description ?? null,
      input.checkpointType ?? 'manual',
      input.taskId ?? null,
      input.scope ?? 'task',
      JSON.stringify(input.includedTasks ?? []),
      JSON.stringify(input.snapshot),
      input.esMemoryId ?? null,
      input.createdBy ?? null,
      input.sessionId ?? null,
    ]
  );

  const row = result.rows[0];
  return {
    id: row.id,
    checkpointId: row.checkpoint_id,
    label: row.label,
    description: row.description ?? undefined,
    checkpointType: row.checkpoint_type as Checkpoint['checkpointType'],
    taskId: row.task_id ?? undefined,
    scope: row.scope as Checkpoint['scope'],
    includedTasks: row.included_tasks,
    snapshot: row.snapshot,
    esMemoryId: row.es_memory_id ?? undefined,
    createdBy: row.created_by ?? undefined,
    sessionId: row.session_id ?? undefined,
    createdAt: row.created_at,
  };
}

export async function getCheckpoint(checkpointId: string): Promise<Checkpoint | null> {
  const result = await query<{
    id: string;
    checkpoint_id: string;
    label: string;
    description: string | null;
    checkpoint_type: string;
    task_id: string | null;
    scope: string;
    included_tasks: string[];
    snapshot: Record<string, unknown>;
    es_memory_id: string | null;
    created_by: string | null;
    session_id: string | null;
    created_at: Date;
  }>(
    'SELECT * FROM checkpoints WHERE checkpoint_id = $1',
    [checkpointId]
  );

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  return {
    id: row.id,
    checkpointId: row.checkpoint_id,
    label: row.label,
    description: row.description ?? undefined,
    checkpointType: row.checkpoint_type as Checkpoint['checkpointType'],
    taskId: row.task_id ?? undefined,
    scope: row.scope as Checkpoint['scope'],
    includedTasks: row.included_tasks,
    snapshot: row.snapshot,
    esMemoryId: row.es_memory_id ?? undefined,
    createdBy: row.created_by ?? undefined,
    sessionId: row.session_id ?? undefined,
    createdAt: row.created_at,
  };
}

export async function listCheckpoints(
  taskId?: string,
  limit = 20
): Promise<Checkpoint[]> {
  let sql = 'SELECT * FROM checkpoints';
  const params: unknown[] = [];

  if (taskId) {
    sql += ' WHERE task_id = $1 OR scope = \'global\'';
    params.push(taskId);
  }

  sql += ' ORDER BY created_at DESC LIMIT $' + (params.length + 1);
  params.push(limit);

  const result = await query<{
    id: string;
    checkpoint_id: string;
    label: string;
    description: string | null;
    checkpoint_type: string;
    task_id: string | null;
    scope: string;
    included_tasks: string[];
    snapshot: Record<string, unknown>;
    es_memory_id: string | null;
    created_by: string | null;
    session_id: string | null;
    created_at: Date;
  }>(sql, params);

  return result.rows.map((row) => ({
    id: row.id,
    checkpointId: row.checkpoint_id,
    label: row.label,
    description: row.description ?? undefined,
    checkpointType: row.checkpoint_type as Checkpoint['checkpointType'],
    taskId: row.task_id ?? undefined,
    scope: row.scope as Checkpoint['scope'],
    includedTasks: row.included_tasks,
    snapshot: row.snapshot,
    esMemoryId: row.es_memory_id ?? undefined,
    createdBy: row.created_by ?? undefined,
    sessionId: row.session_id ?? undefined,
    createdAt: row.created_at,
  }));
}

// ============================================================================
// Task Relationship Operations
// ============================================================================

export async function createRelationship(
  input: CreateRelationshipInput
): Promise<TaskRelationship> {
  const result = await query<{
    id: string;
    source_task_id: string;
    target_task_id: string;
    relationship_type: string;
    metadata: Record<string, unknown>;
    strength: number;
    created_by: string | null;
    created_at: Date;
  }>(
    `INSERT INTO task_relationships (source_task_id, target_task_id, relationship_type, metadata, strength, created_by)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING *`,
    [
      input.sourceTaskId,
      input.targetTaskId,
      input.relationshipType,
      JSON.stringify(input.metadata ?? {}),
      input.strength ?? 1.0,
      input.createdBy ?? null,
    ]
  );

  const row = result.rows[0];
  return {
    id: row.id,
    sourceTaskId: row.source_task_id,
    targetTaskId: row.target_task_id,
    relationshipType: row.relationship_type as TaskRelationship['relationshipType'],
    metadata: row.metadata,
    strength: row.strength,
    createdBy: row.created_by ?? undefined,
    createdAt: row.created_at,
  };
}

export async function getTaskRelationships(taskId: string): Promise<TaskRelationship[]> {
  const result = await query<{
    id: string;
    source_task_id: string;
    target_task_id: string;
    relationship_type: string;
    metadata: Record<string, unknown>;
    strength: number;
    created_by: string | null;
    created_at: Date;
  }>(
    `SELECT * FROM task_relationships
     WHERE source_task_id = $1 OR target_task_id = $1
     ORDER BY created_at DESC`,
    [taskId]
  );

  return result.rows.map((row) => ({
    id: row.id,
    sourceTaskId: row.source_task_id,
    targetTaskId: row.target_task_id,
    relationshipType: row.relationship_type as TaskRelationship['relationshipType'],
    metadata: row.metadata,
    strength: row.strength,
    createdBy: row.created_by ?? undefined,
    createdAt: row.created_at,
  }));
}

// ============================================================================
// Conflict Operations
// ============================================================================

export async function createConflict(
  input: CreateConflictInput
): Promise<ContextConflict> {
  const result = await query<{
    id: string;
    task_a_id: string;
    task_b_id: string | null;
    conflict_type: string;
    description: string;
    severity: string;
    strength: number;
    evidence: Record<string, unknown>;
    resolution_status: string;
    resolution: Record<string, unknown> | null;
    resolved_by: string | null;
    detected_at: Date;
    resolved_at: Date | null;
    detected_by: string | null;
    detection_method: string | null;
  }>(
    `INSERT INTO context_conflicts (
      task_a_id, task_b_id, conflict_type, description, severity,
      strength, evidence, detected_by, detection_method
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    RETURNING *`,
    [
      input.taskAId,
      input.taskBId ?? null,
      input.conflictType,
      input.description,
      input.severity ?? 'medium',
      input.strength,
      JSON.stringify(input.evidence ?? {}),
      input.detectedBy ?? null,
      input.detectionMethod ?? null,
    ]
  );

  const row = result.rows[0];
  return {
    id: row.id,
    taskAId: row.task_a_id,
    taskBId: row.task_b_id ?? undefined,
    conflictType: row.conflict_type as ContextConflict['conflictType'],
    description: row.description,
    severity: row.severity as ContextConflict['severity'],
    strength: row.strength,
    evidence: row.evidence as ContextConflict['evidence'],
    resolutionStatus: row.resolution_status as ContextConflict['resolutionStatus'],
    resolution: (row.resolution as unknown as ConflictResolution | undefined) ?? undefined,
    resolvedBy: row.resolved_by ?? undefined,
    detectedAt: row.detected_at,
    resolvedAt: row.resolved_at ?? undefined,
    detectedBy: row.detected_by ?? undefined,
    detectionMethod: row.detection_method ?? undefined,
  };
}

export async function getUnresolvedConflicts(): Promise<ContextConflict[]> {
  const result = await query<{
    id: string;
    task_a_id: string;
    task_b_id: string | null;
    conflict_type: string;
    description: string;
    severity: string;
    strength: number;
    evidence: Record<string, unknown>;
    resolution_status: string;
    resolution: Record<string, unknown> | null;
    resolved_by: string | null;
    detected_at: Date;
    resolved_at: Date | null;
    detected_by: string | null;
    detection_method: string | null;
  }>(
    `SELECT * FROM context_conflicts
     WHERE resolution_status = 'unresolved'
     ORDER BY
       CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
       detected_at DESC`
  );

  return result.rows.map((row) => ({
    id: row.id,
    taskAId: row.task_a_id,
    taskBId: row.task_b_id ?? undefined,
    conflictType: row.conflict_type as ContextConflict['conflictType'],
    description: row.description,
    severity: row.severity as ContextConflict['severity'],
    strength: row.strength,
    evidence: row.evidence as ContextConflict['evidence'],
    resolutionStatus: row.resolution_status as ContextConflict['resolutionStatus'],
    resolution: (row.resolution as unknown as ConflictResolution | undefined) ?? undefined,
    resolvedBy: row.resolved_by ?? undefined,
    detectedAt: row.detected_at,
    resolvedAt: row.resolved_at ?? undefined,
    detectedBy: row.detected_by ?? undefined,
    detectionMethod: row.detection_method ?? undefined,
  }));
}

export async function resolveConflict(
  conflictId: string,
  input: ResolveConflictInput
): Promise<ContextConflict | null> {
  await query(
    `UPDATE context_conflicts SET
      resolution_status = $2,
      resolution = $3,
      resolved_by = $4,
      resolved_at = CASE WHEN $2 = 'resolved' THEN NOW() ELSE NULL END
     WHERE id = $1`,
    [
      conflictId,
      input.resolutionStatus,
      input.resolution ? JSON.stringify(input.resolution) : null,
      input.resolvedBy ?? null,
    ]
  );

  const result = await query<{
    id: string;
    task_a_id: string;
    task_b_id: string | null;
    conflict_type: string;
    description: string;
    severity: string;
    strength: number;
    evidence: Record<string, unknown>;
    resolution_status: string;
    resolution: Record<string, unknown> | null;
    resolved_by: string | null;
    detected_at: Date;
    resolved_at: Date | null;
    detected_by: string | null;
    detection_method: string | null;
  }>('SELECT * FROM context_conflicts WHERE id = $1', [conflictId]);

  if (result.rows.length === 0) return null;

  const row = result.rows[0];
  return {
    id: row.id,
    taskAId: row.task_a_id,
    taskBId: row.task_b_id ?? undefined,
    conflictType: row.conflict_type as ContextConflict['conflictType'],
    description: row.description,
    severity: row.severity as ContextConflict['severity'],
    strength: row.strength,
    evidence: row.evidence as ContextConflict['evidence'],
    resolutionStatus: row.resolution_status as ContextConflict['resolutionStatus'],
    resolution: (row.resolution as unknown as ConflictResolution | undefined) ?? undefined,
    resolvedBy: row.resolved_by ?? undefined,
    detectedAt: row.detected_at,
    resolvedAt: row.resolved_at ?? undefined,
    detectedBy: row.detected_by ?? undefined,
    detectionMethod: row.detection_method ?? undefined,
  };
}

// Re-export types and converters
export {
  rowToTaskContext,
  rowToActiveSession,
  type TaskContext,
  type TaskStatus,
  type ImmediateContext,
  type ConflictType,
  type ResolutionStatus,
  type GlobalContext,
  type Checkpoint,
  type ContextVersion,
  type TaskRelationship,
  type ContextConflict,
} from './schema.js';
