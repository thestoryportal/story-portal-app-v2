/**
 * Database Schema Types for Context Orchestrator
 * Matches PostgreSQL tables from 001_context_tables.sql
 */

// ============================================================================
// Enums
// ============================================================================

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked' | 'archived';

export type ChangeType = 'manual' | 'auto_save' | 'checkpoint' | 'recovery' | 'migration';

export type RelationshipType =
  | 'blocks'
  | 'blocked_by'
  | 'depends_on'
  | 'dependency_of'
  | 'related_to'
  | 'parent_of'
  | 'child_of';

export type SessionStatus = 'active' | 'ended' | 'crashed' | 'compacted' | 'recovered';

export type RecoveryType = 'crash' | 'compaction' | 'timeout' | 'manual';

export type ConflictType =
  | 'state_mismatch'
  | 'file_conflict'
  | 'spec_contradiction'
  | 'version_divergence'
  | 'lock_collision'
  | 'data_inconsistency';

export type ConflictSeverity = 'low' | 'medium' | 'high' | 'critical';

export type ResolutionStatus = 'unresolved' | 'investigating' | 'resolved' | 'ignored' | 'escalated';

export type CheckpointType = 'manual' | 'milestone' | 'pre_migration' | 'recovery_point' | 'auto';

export type CheckpointScope = 'task' | 'global' | 'multi_task';

// ============================================================================
// Immediate Context (nested in TaskContext)
// ============================================================================

export interface ImmediateContext {
  workingOn: string | null;
  lastAction: string | null;
  nextStep: string | null;
  blockers: string[];
  notes?: string;
}

// ============================================================================
// Task Context
// ============================================================================

export interface TaskContext {
  id: string;
  taskId: string;
  name: string;
  description?: string;
  agentType?: string;
  status: TaskStatus;
  priority: number;

  // State tracking
  currentPhase?: string;
  iteration: number;
  score?: number;
  lockedElements: string[];

  // Context data
  immediateContext: ImmediateContext;
  keyFiles: string[];
  technicalDecisions: string[];
  resumePrompt?: string;

  // Metadata
  keywords: string[];
  tokenEstimate?: number;

  // Timestamps
  createdAt: Date;
  updatedAt: Date;
  lastSessionAt?: Date;

  // Version
  version: number;
}

// ============================================================================
// Context Version
// ============================================================================

export interface ContextVersion {
  id: string;
  taskId: string;
  version: number;
  snapshot: Record<string, unknown>;
  changeSummary?: string;
  changeType?: ChangeType;
  createdBy?: string;
  sessionId?: string;
  createdAt: Date;
}

// ============================================================================
// Task Relationship
// ============================================================================

export interface TaskRelationship {
  id: string;
  sourceTaskId: string;
  targetTaskId: string;
  relationshipType: RelationshipType;
  metadata: Record<string, unknown>;
  strength: number;
  createdBy?: string;
  createdAt: Date;
}

// ============================================================================
// Active Session
// ============================================================================

export interface UnsavedChange {
  type: 'file_edit' | 'state_change' | 'config_update';
  path?: string;
  description: string;
  timestamp: string;
}

export interface ActiveSession {
  id: string;
  sessionId: string;
  taskId?: string;
  status: SessionStatus;
  startedAt: Date;
  lastHeartbeat: Date;
  endedAt?: Date;
  contextSnapshot?: Record<string, unknown>;
  recoveryNeeded: boolean;
  recoveryType?: RecoveryType;
  conversationSummary?: string;
  unsavedChanges: UnsavedChange[];
  projectDir?: string;
  gitBranch?: string;
}

// ============================================================================
// Context Conflict
// ============================================================================

export interface ConflictEvidence {
  field?: string;
  expectedValue?: unknown;
  actualValue?: unknown;
  location?: string;
  details?: string;
}

export interface ConflictResolution {
  action: 'use_a' | 'use_b' | 'merge' | 'custom' | 'ignore';
  resolvedValue?: unknown;
  notes?: string;
}

export interface ContextConflict {
  id: string;
  taskAId: string;
  taskBId?: string;
  conflictType: ConflictType;
  description: string;
  severity: ConflictSeverity;
  strength: number;
  evidence: ConflictEvidence;
  resolutionStatus: ResolutionStatus;
  resolution?: ConflictResolution;
  resolvedBy?: string;
  detectedAt: Date;
  resolvedAt?: Date;
  detectedBy?: string;
  detectionMethod?: string;
}

// ============================================================================
// Global Context
// ============================================================================

export interface GlobalContext {
  id: string;
  projectId: string;
  projectName: string;
  description?: string;
  hardRules: string[];
  techStack: string[];
  keyPaths: Record<string, string>;
  services: Record<string, string>;
  activeTaskId?: string;
  orchestratorContext: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

// ============================================================================
// Checkpoint
// ============================================================================

export interface Checkpoint {
  id: string;
  checkpointId: string;
  label: string;
  description?: string;
  checkpointType: CheckpointType;
  taskId?: string;
  scope: CheckpointScope;
  includedTasks: string[];
  snapshot: Record<string, unknown>;
  esMemoryId?: string;
  createdBy?: string;
  sessionId?: string;
  createdAt: Date;
}

// ============================================================================
// View Types (matching SQL views)
// ============================================================================

export interface ActiveTaskView {
  taskId: string;
  name: string;
  status: TaskStatus;
  currentPhase?: string;
  iteration: number;
  priority: number;
  updatedAt: Date;
  lastSessionAt?: Date;
  versionCount: number;
  relationshipCount: number;
}

export interface UnresolvedConflictView {
  id: string;
  taskAId: string;
  taskBId?: string;
  conflictType: ConflictType;
  severity: ConflictSeverity;
  description: string;
  detectedAt: Date;
  taskAName: string;
  taskBName?: string;
}

export interface SessionNeedingRecoveryView {
  sessionId: string;
  taskId?: string;
  startedAt: Date;
  lastHeartbeat: Date;
  recoveryType?: RecoveryType;
  conversationSummary?: string;
  unsavedChanges: UnsavedChange[];
}

// ============================================================================
// Input Types (for creating/updating)
// ============================================================================

export interface CreateTaskContextInput {
  taskId: string;
  name: string;
  description?: string;
  agentType?: string;
  status?: TaskStatus;
  priority?: number;
  currentPhase?: string;
  immediateContext?: Partial<ImmediateContext>;
  keyFiles?: string[];
  keywords?: string[];
  resumePrompt?: string;
}

export interface UpdateTaskContextInput {
  name?: string;
  description?: string;
  status?: TaskStatus;
  priority?: number;
  currentPhase?: string;
  iteration?: number;
  score?: number;
  lockedElements?: string[];
  immediateContext?: Partial<ImmediateContext>;
  keyFiles?: string[];
  technicalDecisions?: string[];
  resumePrompt?: string;
  keywords?: string[];
}

export interface CreateCheckpointInput {
  checkpointId: string;
  label: string;
  description?: string;
  checkpointType?: CheckpointType;
  taskId?: string;
  scope?: CheckpointScope;
  includedTasks?: string[];
  snapshot: Record<string, unknown>;
  esMemoryId?: string;
  createdBy?: string;
  sessionId?: string;
}

export interface CreateRelationshipInput {
  sourceTaskId: string;
  targetTaskId: string;
  relationshipType: RelationshipType;
  metadata?: Record<string, unknown>;
  strength?: number;
  createdBy?: string;
}

export interface CreateConflictInput {
  taskAId: string;
  taskBId?: string;
  conflictType: ConflictType;
  description: string;
  severity?: ConflictSeverity;
  strength: number;
  evidence?: ConflictEvidence;
  detectedBy?: string;
  detectionMethod?: string;
}

export interface ResolveConflictInput {
  resolutionStatus: ResolutionStatus;
  resolution?: ConflictResolution;
  resolvedBy?: string;
}

// ============================================================================
// Database Row Types (snake_case, as returned from DB)
// ============================================================================

export interface TaskContextRow {
  id: string;
  task_id: string;
  name: string;
  description: string | null;
  agent_type: string | null;
  status: TaskStatus;
  priority: number;
  current_phase: string | null;
  iteration: number;
  score: number | null;
  locked_elements: string[];
  immediate_context: ImmediateContext;
  key_files: string[];
  technical_decisions: string[];
  resume_prompt: string | null;
  keywords: string[];
  token_estimate: number | null;
  created_at: Date;
  updated_at: Date;
  last_session_at: Date | null;
  version: number;
}

export interface ContextVersionRow {
  id: string;
  task_id: string;
  version: number;
  snapshot: Record<string, unknown>;
  change_summary: string | null;
  change_type: ChangeType | null;
  created_by: string | null;
  session_id: string | null;
  created_at: Date;
}

export interface ActiveSessionRow {
  id: string;
  session_id: string;
  task_id: string | null;
  status: SessionStatus;
  started_at: Date;
  last_heartbeat: Date;
  ended_at: Date | null;
  context_snapshot: Record<string, unknown> | null;
  recovery_needed: boolean;
  recovery_type: RecoveryType | null;
  conversation_summary: string | null;
  unsaved_changes: UnsavedChange[];
  project_dir: string | null;
  git_branch: string | null;
}

// ============================================================================
// Utility: Convert DB row to domain type
// ============================================================================

export function rowToTaskContext(row: TaskContextRow): TaskContext {
  return {
    id: row.id,
    taskId: row.task_id,
    name: row.name,
    description: row.description ?? undefined,
    agentType: row.agent_type ?? undefined,
    status: row.status,
    priority: row.priority,
    currentPhase: row.current_phase ?? undefined,
    iteration: row.iteration,
    score: row.score ?? undefined,
    lockedElements: row.locked_elements,
    immediateContext: row.immediate_context,
    keyFiles: row.key_files,
    technicalDecisions: row.technical_decisions,
    resumePrompt: row.resume_prompt ?? undefined,
    keywords: row.keywords,
    tokenEstimate: row.token_estimate ?? undefined,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    lastSessionAt: row.last_session_at ?? undefined,
    version: row.version,
  };
}

export function rowToActiveSession(row: ActiveSessionRow): ActiveSession {
  return {
    id: row.id,
    sessionId: row.session_id,
    taskId: row.task_id ?? undefined,
    status: row.status,
    startedAt: row.started_at,
    lastHeartbeat: row.last_heartbeat,
    endedAt: row.ended_at ?? undefined,
    contextSnapshot: row.context_snapshot ?? undefined,
    recoveryNeeded: row.recovery_needed,
    recoveryType: row.recovery_type ?? undefined,
    conversationSummary: row.conversation_summary ?? undefined,
    unsavedChanges: row.unsaved_changes,
    projectDir: row.project_dir ?? undefined,
    gitBranch: row.git_branch ?? undefined,
  };
}
