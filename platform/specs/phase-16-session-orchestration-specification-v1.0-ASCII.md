# Phase 16: Session Orchestration Specification

**Version:** 1.0
**Status:** Draft
**Date:** January 14, 2026
**Scope:** Context Management, Session Lifecycle, Crash Recovery, Checkpoints
**Encoding:** ASCII-safe
**Error Code Range:** E1600-E1699

---

## Document Overview

This specification defines the Session Orchestration system for the Story Portal
platform. The system provides cross-session context preservation, crash recovery,
checkpoint management, and conflict detection for MCP-based agent workflows.

The Session Orchestrator ensures zero context loss across Claude Code sessions by
maintaining versioned state in PostgreSQL, fast-access caching in Redis, relationship
graphs in Neo4j, and file-based backups for recovery scenarios.

### Position in Architecture Stack

```
+-----------------------------------------------------------------------------+
|                           STORY PORTAL PLATFORM                              |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |                     AGENT ORCHESTRATION LAYER                          |  |
|  |  +-------------------+  +-------------------+  +-------------------+   |  |
|  |  | Claude Code       |  | Task Agents       |  | MCP Servers       |   |  |
|  |  | Sessions          |  | (Validators, etc) |  | (Tools)           |   |  |
|  |  +-------------------+  +-------------------+  +-------------------+   |  |
|  +-----------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+  |
|  |                 >>> PHASE 16: SESSION ORCHESTRATION <<<                |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  |  | Session       |  | Context       |  | Checkpoint    |              |  |
|  |  | Manager       |  | Manager       |  | Manager       |              |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  |  | Conflict      |  | Recovery      |  | Hot Context   |              |  |
|  |  | Detector      |  | Handler       |  | Cache         |              |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  +-----------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+  |
|  |                     MULTI-BACKEND PERSISTENCE                          |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  |  | PostgreSQL    |  | Redis         |  | Neo4j         |              |  |
|  |  | (Primary)     |  | (Cache)       |  | (Graph)       |              |  |
|  |  +---------------+  +---------------+  +---------------+              |  |
|  |                           |                                            |  |
|  |                           v                                            |  |
|  |                    +---------------+                                   |  |
|  |                    | File System   |                                   |  |
|  |                    | (.claude/)    |                                   |  |
|  |                    +---------------+                                   |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Table of Contents

1. [Executive Summary](#section-1)
2. [Scope Definition](#section-2)
3. [Architecture](#section-3)
4. [Interfaces](#section-4)
5. [Data Model](#section-5)
6. [Integration with Data Layer](#section-6)
7. [Reliability and Scalability](#section-7)
8. [Security](#section-8)
9. [Observability](#section-9)
10. [Configuration](#section-10)
11. [Implementation Guide](#section-11)
12. [Testing Strategy](#section-12)
13. [Migration and Deployment](#section-13)
14. [Open Questions and Decisions](#section-14)
15. [References and Appendices](#section-15)

---

<a id="section-1"></a>

# Section 1: Executive Summary

## 1.1 Purpose

The Session Orchestration system provides persistent context management for Claude
Code sessions, enabling:

- **Context Preservation**: Automatic versioning and multi-backend persistence
- **Crash Recovery**: Detection and restoration from unexpected session termination
- **Checkpoint Management**: Named snapshots for explicit rollback points
- **Task Switching**: Atomic context switching between tasks
- **Conflict Detection**: Cross-context validation and resolution

## 1.2 Key Capabilities

| Capability | Tool | Description |
|------------|------|-------------|
| Context CRUD | `save_context_snapshot`, `get_unified_context` | Versioned state management with auto-save triggers |
| Checkpoints | `create_checkpoint`, `rollback_to` | Named recovery points with full state snapshots |
| Sessions | `start_session`, `end_session`, `heartbeat` | Lifecycle tracking with heartbeat monitoring |
| Crash Recovery | `check_recovery` | 60-second heartbeat timeout detection |
| Task Switching | `switch_task` | Atomic context preservation during switches |
| Conflict Detection | `detect_conflicts`, `resolve_conflict` | Cross-context contradiction identification |
| Task Graph | `get_task_graph` | Neo4j-powered relationship visualization |
| Hot Sync | `sync_hot_context` | File cache synchronization from databases |

## 1.3 Reference Implementation

The `mcp-context-orchestrator/` directory contains the validated reference
implementation with 12/12 tests passing. This specification documents the
interfaces, data models, and behaviors validated by that implementation.

## 1.4 Design Principles

1. **Zero-Loss Architecture** -- Every state change is automatically versioned and
   persisted to multiple backends to prevent data loss.

2. **Trigger-Based Versioning** -- Database triggers handle auto-versioning to
   prevent missing saves from application-level failures.

3. **Hot Context Caching** -- Redis caches active task context for sub-second
   access during session operations.

4. **Atomic Operations** -- Task switching saves current state before loading new
   task, ensuring no context loss during transitions.

5. **Recovery-First Design** -- Sessions are marked for recovery before they crash;
   hooks detect crashes via stale heartbeats.

6. **Multi-Source Conflict Detection** -- File overlaps, lock collisions, and state
   mismatches are all detected and surfaced.

---

<a id="section-2"></a>

# Section 2: Scope Definition

## 2.1 System Boundaries

### 2.1.1 In Scope

| Component | Description |
|-----------|-------------|
| Session Lifecycle | Start, heartbeat, end, crash detection |
| Context Management | Task contexts with versioning |
| Checkpoint System | Named snapshots with rollback capability |
| Conflict Detection | Cross-context validation |
| Task Relationships | Graph-based dependency tracking |
| Multi-Backend Sync | PostgreSQL, Redis, Neo4j, File system |
| Recovery System | Crash and compaction recovery |

### 2.1.2 Out of Scope

| Component | Reason |
|-----------|--------|
| Agent Logic | Handled by individual task agents |
| Tool Execution | MCP server responsibility |
| Authentication | External identity provider |
| Network Transport | MCP protocol layer |

## 2.2 Schema Allocation

**Database**: `consolidator`
**Schema**: `mcp_contexts`

| Table | Purpose | Row Count Estimate |
|-------|---------|-------------------|
| `task_contexts` | Primary task state storage | 100-1000 |
| `context_versions` | Version history for rollback | 10,000-100,000 |
| `active_sessions` | Session lifecycle tracking | 10-100 |
| `checkpoints` | Named recovery snapshots | 100-1000 |
| `global_context` | Project-wide configuration | 1-10 |
| `context_conflicts` | Detected conflicts | 10-100 |
| `task_relationships` | Task dependency graph | 100-1000 |

## 2.3 Error Code Allocation

| Range | Category | Description |
|-------|----------|-------------|
| E1600-E1609 | Session Errors | Session lifecycle failures |
| E1610-E1619 | Context Errors | Context CRUD operations |
| E1620-E1629 | Checkpoint Errors | Checkpoint operations |
| E1630-E1639 | Recovery Errors | Crash recovery failures |
| E1640-E1649 | Conflict Errors | Conflict detection/resolution |
| E1650-E1659 | Sync Errors | Multi-backend synchronization |
| E1660-E1669 | Task Switch Errors | Task switching operations |
| E1690-E1699 | Configuration Errors | Configuration failures |

---

<a id="section-3"></a>

# Section 3: Architecture

## 3.1 High-Level Architecture

```
+-----------------------------------------------------------------------------+
|                         SESSION ORCHESTRATION SYSTEM                         |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +---------------------------+  +---------------------------+                |
|  |    SESSION MANAGER        |  |    CONTEXT MANAGER        |                |
|  +---------------------------+  +---------------------------+                |
|  | - start_session()         |  | - get_unified_context()   |                |
|  | - end_session()           |  | - save_context_snapshot() |                |
|  | - heartbeat()             |  | - version management      |                |
|  | - check_recovery()        |  | - hot context cache       |                |
|  +---------------------------+  +---------------------------+                |
|              |                              |                                |
|              v                              v                                |
|  +---------------------------+  +---------------------------+                |
|  |    CHECKPOINT MANAGER     |  |    CONFLICT DETECTOR      |                |
|  +---------------------------+  +---------------------------+                |
|  | - create_checkpoint()     |  | - detect_conflicts()      |                |
|  | - rollback_to()           |  | - resolve_conflict()      |                |
|  | - scope management        |  | - severity assessment     |                |
|  | - ES Memory integration   |  | - evidence collection     |                |
|  +---------------------------+  +---------------------------+                |
|              |                              |                                |
|              v                              v                                |
|  +---------------------------+  +---------------------------+                |
|  |    TASK SWITCH ENGINE     |  |    HOT CONTEXT CACHE      |                |
|  +---------------------------+  +---------------------------+                |
|  | - switch_task()           |  | - sync_hot_context()      |                |
|  | - atomic state save       |  | - Redis caching           |                |
|  | - relationship loading    |  | - File-based backup       |                |
|  | - blocking task check     |  | - TTL management          |                |
|  +---------------------------+  +---------------------------+                |
|                                                                              |
+-----------------------------------------------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                         PERSISTENCE LAYER                                    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +---------------+    +---------------+    +---------------+                 |
|  |  PostgreSQL   |    |    Redis      |    |    Neo4j      |                 |
|  |  (Primary)    |    |   (Cache)     |    |   (Graph)     |                 |
|  +---------------+    +---------------+    +---------------+                 |
|  | task_contexts |    | hot_context   |    | TaskNode      |                 |
|  | context_vers  |    | task_cache    |    | SessionNode   |                 |
|  | active_sess   |    | locks         |    | AgentNode     |                 |
|  | checkpoints   |    | heartbeat     |    | BLOCKS rel    |                 |
|  | conflicts     |    |               |    | DEPENDS_ON    |                 |
|  | global_ctx    |    |               |    | RELATED_TO    |                 |
|  +---------------+    +---------------+    +---------------+                 |
|                                                                              |
|                    +---------------------------+                              |
|                    |      File System          |                              |
|                    +---------------------------+                              |
|                    | .claude/contexts/         |                              |
|                    |   _registry.json          |                              |
|                    |   _hot_context.json       |                              |
|                    |   task-agents/{id}.json   |                              |
|                    |   shared/project-const.   |                              |
|                    +---------------------------+                              |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## 3.2 Component Responsibilities

### 3.2.1 Session Manager

**Responsibility**: Track Claude Code session lifecycle and detect crashes.

**Input**: Session start/end events, heartbeat signals
**Output**: Session state, recovery requirements

**Operations**:

1. Create session record with unique ID
2. Track current task being worked on
3. Record heartbeat timestamps
4. Detect stale sessions (heartbeat > 60 seconds)
5. Mark sessions for recovery on crash detection
6. Store conversation summary for context restoration

### 3.2.2 Context Manager

**Responsibility**: Manage task context with versioning and multi-backend persistence.

**Input**: Task updates, context queries
**Output**: Unified context, version history

**Operations**:

1. Load context from cache (Redis) or database (PostgreSQL)
2. Apply updates and persist to all backends
3. Trigger automatic versioning via database triggers
4. Aggregate global and task-specific context
5. Include relationship data from Neo4j

### 3.2.3 Checkpoint Manager

**Responsibility**: Create named snapshots for explicit rollback points.

**Input**: Checkpoint creation requests, rollback commands
**Output**: Checkpoint records, restored state

**Operations**:

1. Capture full state snapshot (global + task contexts)
2. Generate unique checkpoint ID
3. Support task-scoped, global, and multi-task checkpoints
4. Restore state from checkpoint on rollback
5. Create backup checkpoint before rollback

### 3.2.4 Conflict Detector

**Responsibility**: Identify and manage cross-context contradictions.

**Input**: Task IDs, conflict types to detect
**Output**: Conflict records, resolution status

**Operations**:

1. Detect file conflicts (overlapping key_files)
2. Detect lock collisions (expired Redis locks)
3. Detect state mismatches (DB vs cache divergence)
4. Detect version divergence (multiple recovery versions)
5. Calculate conflict severity and strength
6. Track resolution status and actions

### 3.2.5 Task Switch Engine

**Responsibility**: Enable atomic context switching between tasks.

**Input**: Source task, target task, updates
**Output**: Previous task state, new task context

**Operations**:

1. Save current task state (if requested)
2. Apply any pending updates
3. Update global active task reference
4. Load new task context with relationships
5. Check blocking tasks from Neo4j
6. Update last_session_at timestamp

### 3.2.6 Hot Context Cache

**Responsibility**: Maintain fast-access cache and file backups.

**Input**: Sync requests, cache queries
**Output**: Cached context, sync status

**Operations**:

1. Update Redis hot context (1-hour TTL)
2. Sync to file system (.claude/contexts/)
3. Update task registry
4. Handle cache invalidation

## 3.3 Data Flow

### 3.3.1 Context Save Flow

```
+------------------+     +------------------+     +------------------+
| Tool Call:       |     | Context Manager  |     | PostgreSQL       |
| save_context_    | --> | Apply Updates    | --> | UPDATE task_ctx  |
| snapshot         |     |                  |     | (triggers vers)  |
+------------------+     +------------------+     +------------------+
                                 |
                                 v
                         +------------------+     +------------------+
                         | Redis            | --> | File System      |
                         | Update Cache     |     | Sync Context     |
                         +------------------+     +------------------+
```

### 3.3.2 Recovery Check Flow

```
+------------------+     +------------------+     +------------------+
| Tool Call:       |     | Session Manager  |     | Query Sessions   |
| check_recovery   | --> | Check DB         | --> | recovery_needed  |
+------------------+     +------------------+     | = TRUE           |
                                 |               +------------------+
                                 v
                         +------------------+     +------------------+
                         | Check File       |     | Format Recovery  |
                         | Heartbeat        | --> | Resume Prompt    |
                         +------------------+     +------------------+
```

---

<a id="section-4"></a>

# Section 4: Interfaces

## 4.1 Tool Specifications

### 4.1.1 get_unified_context

**Purpose**: Aggregate context from all sources for task or globally.

**Input Schema**:

```typescript
{
  taskId?: string                    // Optional; omit for global context
  includeRelationships?: boolean     // Default: true
  includeVersionHistory?: boolean    // Default: false
  maxVersions?: number               // Default: 5
}
```

**Output Schema**:

```typescript
{
  projectId: string
  global: {
    hardRules: string[]
    techStack: string[]
    keyPaths: Record<string, string>
    services: Record<string, string>
  }
  task?: {
    taskId: string
    name: string
    status: TaskStatus
    currentPhase: string
    iteration: number
    score?: number
    lockedElements: string[]
    immediateContext: ImmediateContext
    keyFiles: string[]
    technicalDecisions: string[]
    resumePrompt?: string
  }
  relationships?: {
    blocks: TaskRef[]
    blockedBy: TaskRef[]
    dependsOn: TaskRef[]
    relatedTo: TaskRef[]
  }
  versionHistory?: Array<{
    version: number
    createdAt: string
    changeType: ChangeType
    changeSummary: string
  }>
  conflicts?: Array<{
    id: string
    type: ConflictType
    severity: Severity
    description: string
  }>
  metadata: {
    source: 'database' | 'cache' | 'hybrid'
    loadedAt: string
    cacheHit: boolean
  }
}
```

**Algorithm**:

1. Try Redis cache first for hot context
2. Load global context from PostgreSQL
3. Load task context if taskId provided
4. Resolve relationships from Neo4j (if includeRelationships)
5. Load version history (if includeVersionHistory)
6. Check unresolved conflicts for task
7. Return aggregated context with metadata

**Errors**:

| Code | Condition |
|------|-----------|
| E1610 | Task not found |
| E1611 | Global context not found |
| E1650 | Cache synchronization failure |

---

### 4.1.2 save_context_snapshot

**Purpose**: Persist current state to all backends.

**Input Schema**:

```typescript
{
  taskId: string
  updates?: {
    currentPhase?: string
    iteration?: number
    score?: number
    status?: TaskStatus
    immediateContext?: ImmediateContext
    keyFiles?: string[]
    technicalDecisions?: string[]
    resumePrompt?: string
    lockedElements?: string[]
  }
  changeSummary?: string
  sessionId?: string
  syncToFile?: boolean  // Default: true
}
```

**Output Schema**:

```typescript
{
  success: boolean
  taskId: string
  version: number
  savedTo: {
    database: boolean
    redis: boolean
    file: boolean
  }
  timestamp: string
}
```

**Algorithm**:

1. Validate task exists
2. Apply updates to task_contexts table
3. Database trigger creates context_versions entry
4. Update Redis cache with new state
5. Sync to file system (if syncToFile)
6. Update hot context in Redis
7. Return save status for all backends

**Errors**:

| Code | Condition |
|------|-----------|
| E1610 | Task not found |
| E1612 | Update validation failed |
| E1650 | Redis sync failure |
| E1651 | File sync failure |

---

### 4.1.3 create_checkpoint

**Purpose**: Create named version snapshot with rollback capability.

**Input Schema**:

```typescript
{
  label: string
  description?: string
  taskId?: string                 // Omit for global checkpoint
  checkpointType?: CheckpointType // Default: 'manual'
  includeTasks?: string[]         // Additional task IDs for multi-task
  sessionId?: string
}
```

**Output Schema**:

```typescript
{
  success: boolean
  checkpointId: string            // Format: cp-{timestamp}-{randomID}
  label: string
  scope: CheckpointScope
  includedTasks: string[]
  createdAt: string
}
```

**Algorithm**:

1. Generate unique checkpoint ID
2. Determine scope based on task count:
   - 0 tasks -> global
   - 1 task -> task
   - 2+ tasks -> multi_task
3. Capture snapshot of global context
4. Capture snapshot of all included task contexts
5. Store checkpoint record
6. Return checkpoint metadata

**Errors**:

| Code | Condition |
|------|-----------|
| E1620 | Checkpoint creation failed |
| E1621 | Invalid scope configuration |
| E1610 | Referenced task not found |

---

### 4.1.4 rollback_to

**Purpose**: Restore task context to previous version or checkpoint.

**Input Schema**:

```typescript
{
  taskId: string
  target: {
    type: 'version' | 'checkpoint'
    version?: number              // If type='version'
    checkpointId?: string         // If type='checkpoint'
  }
  createBackup?: boolean          // Default: true
  sessionId?: string
}
```

**Output Schema**:

```typescript
{
  success: boolean
  taskId: string
  rolledBackTo: {
    type: 'version' | 'checkpoint'
    identifier: string | number
  }
  backupCheckpointId?: string
  restoredState: {
    currentPhase: string
    iteration: number
    status: TaskStatus
  }
  timestamp: string
}
```

**Algorithm**:

1. Validate target exists (version or checkpoint)
2. Get current state for backup
3. Create backup checkpoint if requested
4. If version target: restore from context_versions
5. If checkpoint target: extract task data from snapshot
6. Update task_contexts with restored data
7. Update Redis cache
8. Return rollback result

**Errors**:

| Code | Condition |
|------|-----------|
| E1622 | Checkpoint not found |
| E1623 | Version not found |
| E1624 | Rollback operation failed |
| E1610 | Task not found |

---

### 4.1.5 switch_task

**Purpose**: Atomic task switch with state preservation.

**Input Schema**:

```typescript
{
  fromTaskId?: string             // Current task; omit if just loading
  toTaskId: string                // Task to switch to
  saveCurrentState?: boolean      // Default: true
  currentTaskUpdates?: {
    immediateContext?: ImmediateContext
    currentPhase?: string
    iteration?: number
  }
  sessionId?: string
}
```

**Output Schema**:

```typescript
{
  success: boolean
  previousTask?: {
    taskId: string
    saved: boolean
    version: number
  }
  newTask: {
    taskId: string
    name: string
    status: TaskStatus
    currentPhase: string
    iteration: number
    immediateContext: ImmediateContext
    keyFiles: string[]
    resumePrompt?: string
    blockedBy: Array<{ taskId: string; name: string }>
  }
  timestamp: string
}
```

**Algorithm**:

1. If fromTaskId + saveCurrentState:
   a. Apply currentTaskUpdates
   b. Update database (triggers auto-save)
   c. Update Redis cache
2. Record session work in Neo4j
3. Load new task from database
4. Update global_context.active_task_id
5. Update hot context in Redis
6. Get blocking tasks from Neo4j
7. Update task's last_session_at
8. Return switch result

**Errors**:

| Code | Condition |
|------|-----------|
| E1660 | Source task not found |
| E1661 | Target task not found |
| E1662 | Task switch failed |
| E1612 | Update validation failed |

---

### 4.1.6 detect_conflicts

**Purpose**: Cross-system conflict detection between contexts.

**Input Schema**:

```typescript
{
  taskIds?: string[]              // Specific tasks; omit for all active
  conflictTypes?: ConflictType[]  // Types to detect; omit for all
}
```

**Output Schema**:

```typescript
{
  detected: Array<{
    id?: string
    taskAId: string
    taskBId?: string
    conflictType: ConflictType
    severity: Severity
    strength: number              // 0.0-1.0 confidence
    description: string
    evidence: {
      field: string
      expectedValue: unknown
      actualValue: unknown
      location: string
    }
    suggestedResolution?: string
  }>
  existing: Array<{
    id: string
    taskAId: string
    taskBId?: string
    conflictType: ConflictType
    severity: Severity
    description: string
    detectedAt: string
  }>
  summary: {
    newConflicts: number
    existingConflicts: number
    criticalCount: number
    highCount: number
  }
  timestamp: string
}
```

**Detection Methods**:

| Type | Detection | Severity Logic |
|------|-----------|----------------|
| `file_conflict` | Overlapping key_files between tasks | high if 3+ files, else medium |
| `lock_collision` | Redis locks with expiredAt < now | high |
| `state_mismatch` | DB vs Redis divergence | medium |
| `version_divergence` | Multiple recovery versions in history | low |

**Strength Calculation**:

- file_conflict: `min(overlappingCount / 5, 1.0)`
- lock_collision: `1.0`
- state_mismatch: `0.8`
- version_divergence: `0.5`

**Errors**:

| Code | Condition |
|------|-----------|
| E1640 | Detection query failed |
| E1641 | Invalid conflict type |

---

### 4.1.7 resolve_conflict

**Purpose**: Apply resolution to detected conflict.

**Input Schema**:

```typescript
{
  conflictId: string
  resolution: {
    action: 'use_a' | 'use_b' | 'merge' | 'custom' | 'ignore'
    resolvedValue?: unknown
    notes?: string
  }
  resolvedBy?: string
}
```

**Output Schema**:

```typescript
{
  success: boolean
  conflictId: string
  previousStatus: ResolutionStatus
  newStatus: ResolutionStatus
  resolution: {
    action: string
    notes?: string
  }
  timestamp: string
}
```

**Algorithm**:

1. Load conflict record
2. Validate conflict is not already resolved
3. Apply resolution based on action:
   - `use_a`: Use task A's value
   - `use_b`: Use task B's value
   - `merge`: Apply merged value
   - `custom`: Apply resolvedValue
   - `ignore`: Mark as ignored
4. Update conflict record status
5. Apply side effects:
   - state_mismatch + use_a: sync cache with DB
   - lock_collision: release Redis lock
6. Return resolution result

**Errors**:

| Code | Condition |
|------|-----------|
| E1642 | Conflict not found |
| E1643 | Conflict already resolved |
| E1644 | Resolution action failed |

---

### 4.1.8 check_recovery

**Purpose**: Check for sessions needing recovery from crashes/compaction.

**Input Schema**:

```typescript
{
  markRecovered?: string          // Session ID to mark as recovered
  includeHistory?: boolean        // Include tool history in output
}
```

**Output Schema**:

```typescript
{
  needsRecovery: boolean
  sessions: Array<{
    sessionId: string
    taskId?: string
    taskName?: string
    recoveryType: RecoveryType
    lastActivity: string
    resumePrompt: string          // Formatted markdown
    toolHistory?: Array<{
      timestamp: string
      tool: string
      success: boolean
    }>                            // Last 10 if includeHistory
    unsavedChanges: Array<{
      type: string
      path: string
      description: string
    }>
  }>
  summary: string
  timestamp: string
}
```

**Recovery Sources**:

1. Database: sessions with `recovery_needed = TRUE`
2. File system: stale heartbeat (> CRASH_THRESHOLD_MINUTES)

**Resume Prompt Format**:

```markdown
## Recovery Required: {recoveryType}

### Task: {taskName}
- **Phase**: {currentPhase}
- **Iteration**: {iteration}

### Immediate Context
- **Working On**: {workingOn}
- **Last Action**: {lastAction}
- **Next Step**: {nextStep}
- **Blockers**: {blockers}

### Recent Tool Usage
{last 5 tool invocations}

### Pending Changes
{unsaved changes list}

### Conversation Summary
{conversation summary}

### Recommended Actions
1. {action 1}
2. {action 2}
```

**Errors**:

| Code | Condition |
|------|-----------|
| E1630 | Recovery check failed |
| E1631 | Session not found (for markRecovered) |

---

### 4.1.9 get_task_graph

**Purpose**: Neo4j-powered task relationship visualization.

**Input Schema**:

```typescript
{
  taskId?: string                 // Specific task focus; omit for overview
  depth?: number                  // Default: 2
  includeCompleted?: boolean      // Default: false
}
```

**Output Schema**:

```typescript
{
  nodes: Array<{
    taskId: string
    name: string
    status: TaskStatus
    phase?: string
    priority: number
    score?: number
  }>
  edges: Array<{
    from: string
    to: string
    type: 'blocks' | 'depends_on' | 'related_to'
    reason?: string
  }>
  focus?: {
    task: TaskGraphNode
    blockedBy: TaskGraphNode[]
    blocks: TaskGraphNode[]
    dependsOn: TaskGraphNode[]
    dependencyOf: TaskGraphNode[]
    relatedTo: TaskGraphNode[]
    agents: Array<{ agentId: string; type: string }>
    recentSessions: Array<{ sessionId: string; startedAt: string }>
  }
  readyTasks: TaskGraphNode[]
  blockedTasks: TaskGraphNode[]
  summary: {
    totalTasks: number
    inProgress: number
    blocked: number
    completed: number
    pending: number
  }
}
```

**Errors**:

| Code | Condition |
|------|-----------|
| E1610 | Task not found |
| E1652 | Neo4j query failed |

---

### 4.1.10 sync_hot_context

**Purpose**: Update file cache from databases.

**Input Schema**:

```typescript
{
  syncRedis?: boolean             // Default: true
  syncFiles?: boolean             // Default: true
  taskIds?: string[]              // Specific tasks; omit for all active
  updateRegistry?: boolean        // Default: true
}
```

**Output Schema**:

```typescript
{
  success: boolean
  synced: {
    redis: {
      hotContext: boolean
      taskContexts: number
    }
    files: {
      registry: boolean
      taskContexts: number
      hotContext: boolean
    }
  }
  errors: string[]
  timestamp: string
}
```

**Sync Targets**:

| Backend | Target | Content |
|---------|--------|---------|
| Redis | hot_context | Active task context |
| Redis | task:{id} | Individual task contexts |
| File | _registry.json | Task registry |
| File | task-agents/{id}.json | Per-task context files |
| File | _hot_context.json | Hot context backup |
| File | shared/project-constants.json | Global constants |

**Errors**:

| Code | Condition |
|------|-----------|
| E1650 | Redis sync failure |
| E1651 | File sync failure |
| E1653 | Partial sync (some backends failed) |

---

## 4.2 Type Definitions

### 4.2.1 Task Status

```typescript
type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'blocked'
  | 'archived'
```

### 4.2.2 Change Type

```typescript
type ChangeType =
  | 'manual'
  | 'auto_save'
  | 'checkpoint'
  | 'recovery'
  | 'migration'
```

### 4.2.3 Checkpoint Type

```typescript
type CheckpointType =
  | 'manual'
  | 'milestone'
  | 'pre_migration'
  | 'recovery_point'
  | 'auto'
```

### 4.2.4 Checkpoint Scope

```typescript
type CheckpointScope =
  | 'task'
  | 'global'
  | 'multi_task'
```

### 4.2.5 Relationship Type

```typescript
type RelationshipType =
  | 'blocks'
  | 'blocked_by'
  | 'depends_on'
  | 'dependency_of'
  | 'related_to'
  | 'parent_of'
  | 'child_of'
```

### 4.2.6 Conflict Type

```typescript
type ConflictType =
  | 'state_mismatch'
  | 'file_conflict'
  | 'spec_contradiction'
  | 'version_divergence'
  | 'lock_collision'
  | 'data_inconsistency'
```

### 4.2.7 Severity

```typescript
type Severity =
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'
```

### 4.2.8 Resolution Status

```typescript
type ResolutionStatus =
  | 'unresolved'
  | 'investigating'
  | 'resolved'
  | 'ignored'
  | 'escalated'
```

### 4.2.9 Session Status

```typescript
type SessionStatus =
  | 'active'
  | 'ended'
  | 'crashed'
  | 'compacted'
  | 'recovered'
```

### 4.2.10 Recovery Type

```typescript
type RecoveryType =
  | 'crash'
  | 'compaction'
  | 'timeout'
  | 'manual'
```

### 4.2.11 Immediate Context

```typescript
interface ImmediateContext {
  workingOn: string | null
  lastAction: string | null
  nextStep: string | null
  blockers: string[]
  notes?: string
}
```

### 4.2.12 Conflict Resolution

```typescript
interface ConflictResolution {
  action: 'use_a' | 'use_b' | 'merge' | 'custom' | 'ignore'
  resolvedValue?: unknown
  notes?: string
}
```

---

<a id="section-5"></a>

# Section 5: Data Model

## 5.1 Entity Relationship Diagram

```
+------------------+          +-------------------+
|  global_context  |          |   checkpoints     |
+------------------+          +-------------------+
| id [PK]          |          | id [PK]           |
| project_id [UQ]  |          | checkpoint_id [UQ]|
| project_name     |          | label             |
| description      |          | description       |
| hard_rules       |          | checkpoint_type   |
| tech_stack       |          | task_id [FK?]     |
| key_paths        |     +--->| scope             |
| services         |     |    | included_tasks    |
| active_task_id --+--+  |    | snapshot          |
| orchestrator_ctx |  |  |    | es_memory_id      |
| version          |  |  |    | created_by        |
+------------------+  |  |    | session_id        |
                      |  |    | created_at        |
                      |  |    +-------------------+
                      |  |
                      v  |
+------------------+  |  |    +-------------------+
|  task_contexts   |<-+--+----|  context_versions |
+------------------+          +-------------------+
| id [PK]          |          | id [PK]           |
| task_id [UQ]     |<---------| task_id [FK]      |
| name             |          | version           |
| description      |          | snapshot          |
| agent_type       |          | change_summary    |
| status           |          | change_type       |
| priority         |          | created_by        |
| current_phase    |          | session_id        |
| iteration        |          | created_at        |
| score            |          +-------------------+
| locked_elements  |                [UQ: task_id, version]
| immediate_context|
| key_files        |
| technical_dec    |          +-------------------+
| resume_prompt    |          | active_sessions   |
| keywords         |          +-------------------+
| token_estimate   |          | id [PK]           |
| created_at       |          | session_id [UQ]   |
| updated_at       |<---------| task_id [FK?]     |
| last_session_at  |          | status            |
| version          |          | started_at        |
+------------------+          | last_heartbeat    |
        |                     | ended_at          |
        |                     | context_snapshot  |
        | 1:N                 | recovery_needed   |
        v                     | recovery_type     |
+------------------+          | conversation_sum  |
| task_relationships          | unsaved_changes   |
+------------------+          | project_dir       |
| id [PK]          |          | git_branch        |
| source_task_id   |          +-------------------+
| target_task_id   |
| relationship_type|          +-------------------+
| metadata         |          | context_conflicts |
| strength         |          +-------------------+
| created_by       |          | id [PK]           |
| created_at       |          | task_a_id [FK]    |
+------------------+          | task_b_id [FK?]   |
[UQ: src, tgt, type]          | conflict_type     |
                              | description       |
                              | severity          |
                              | strength          |
                              | evidence          |
                              | resolution_status |
                              | resolution        |
                              | resolved_by       |
                              | detected_at       |
                              | resolved_at       |
                              | detected_by       |
                              | detection_method  |
                              +-------------------+
```

## 5.2 Table Definitions

### 5.2.1 task_contexts

Primary storage for task state with automatic versioning.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| task_id | VARCHAR(255) | UNIQUE, NOT NULL | Human-readable task ID |
| name | VARCHAR(500) | NOT NULL | Task display name |
| description | TEXT | | Optional description |
| agent_type | VARCHAR(100) | | Type of agent handling task |
| status | VARCHAR(50) | DEFAULT 'pending' | Task status enum |
| priority | INTEGER | DEFAULT 50 | Priority for ordering |
| current_phase | VARCHAR(255) | | Current work phase |
| iteration | INTEGER | DEFAULT 0 | Iteration count |
| score | DECIMAL(5,2) | | Quality/progress score |
| locked_elements | JSONB | DEFAULT '[]' | Array of locked elements |
| immediate_context | JSONB | | {workingOn, lastAction, nextStep, blockers} |
| key_files | JSONB | | Array of file paths |
| technical_decisions | JSONB | | Array of architectural decisions |
| resume_prompt | TEXT | | Single-line summary for resume |
| keywords | JSONB | | Array of searchable keywords |
| token_estimate | INTEGER | | Estimated token usage |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |
| last_session_at | TIMESTAMPTZ | | Last active session |
| version | INTEGER | DEFAULT 1 | Auto-incremented version |

**Indices**:

```sql
CREATE INDEX idx_task_contexts_status ON task_contexts(status);
CREATE INDEX idx_task_contexts_priority ON task_contexts(priority);
CREATE INDEX idx_task_contexts_updated ON task_contexts(updated_at DESC);
CREATE INDEX idx_task_contexts_keywords ON task_contexts USING GIN(keywords);
```

**Triggers**:

```sql
-- Auto-update updated_at
CREATE TRIGGER update_task_contexts_timestamp
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Auto-increment version
CREATE TRIGGER increment_task_version
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION increment_version();

-- Auto-save to context_versions on significant changes
CREATE TRIGGER auto_save_context_version
  AFTER UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION save_context_version();
```

---

### 5.2.2 context_versions

Version history for rollback capability.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| task_id | VARCHAR(255) | NOT NULL | Reference to task |
| version | INTEGER | NOT NULL | Version number |
| snapshot | JSONB | NOT NULL | Full task context snapshot |
| change_summary | TEXT | | Description of changes |
| change_type | VARCHAR(50) | | manual, auto_save, checkpoint, etc |
| created_by | VARCHAR(255) | | Session or agent ID |
| session_id | VARCHAR(255) | | Session that triggered change |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Version creation time |

**Constraints**:

```sql
UNIQUE(task_id, version)
```

**Indices**:

```sql
CREATE INDEX idx_context_versions_task ON context_versions(task_id);
CREATE INDEX idx_context_versions_created ON context_versions(created_at DESC);
CREATE INDEX idx_context_versions_session ON context_versions(session_id);
```

---

### 5.2.3 active_sessions

Track Claude Code sessions for crash/compaction recovery.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| session_id | VARCHAR(255) | UNIQUE, NOT NULL | Unique session identifier |
| task_id | VARCHAR(255) | | Current task being worked on |
| status | VARCHAR(50) | DEFAULT 'active' | Session status |
| started_at | TIMESTAMPTZ | DEFAULT NOW() | Session start time |
| last_heartbeat | TIMESTAMPTZ | DEFAULT NOW() | Latest heartbeat |
| ended_at | TIMESTAMPTZ | | Session end time |
| context_snapshot | JSONB | | Full context for recovery |
| recovery_needed | BOOLEAN | DEFAULT FALSE | Recovery flag |
| recovery_type | VARCHAR(50) | | crash, compaction, timeout, manual |
| conversation_summary | TEXT | | Summary for context restoration |
| unsaved_changes | JSONB | | Array of pending changes |
| project_dir | VARCHAR(1000) | | Project directory path |
| git_branch | VARCHAR(255) | | Git branch at session time |

**Indices**:

```sql
CREATE INDEX idx_sessions_status ON active_sessions(status);
CREATE INDEX idx_sessions_heartbeat ON active_sessions(last_heartbeat DESC);
CREATE INDEX idx_sessions_recovery ON active_sessions(recovery_needed)
  WHERE recovery_needed = TRUE;
CREATE INDEX idx_sessions_task ON active_sessions(task_id);
```

---

### 5.2.4 checkpoints

Named snapshots for explicit rollback points.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| checkpoint_id | VARCHAR(255) | UNIQUE, NOT NULL | Human-readable ID |
| label | VARCHAR(500) | NOT NULL | Human-readable label |
| description | TEXT | | Checkpoint description |
| checkpoint_type | VARCHAR(50) | DEFAULT 'manual' | Type enum |
| task_id | VARCHAR(255) | | Task for task-scoped checkpoints |
| scope | VARCHAR(50) | NOT NULL | task, global, multi_task |
| included_tasks | JSONB | DEFAULT '[]' | Array of included task IDs |
| snapshot | JSONB | NOT NULL | Full state snapshot |
| es_memory_id | VARCHAR(255) | | Reference to ES Memory document |
| created_by | VARCHAR(255) | | Creator session/agent ID |
| session_id | VARCHAR(255) | | Session that created checkpoint |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

**Indices**:

```sql
CREATE INDEX idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_type ON checkpoints(checkpoint_type);
CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);
CREATE INDEX idx_checkpoints_label ON checkpoints(label);
```

---

### 5.2.5 global_context

Project-wide context applying to all tasks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| project_id | VARCHAR(255) | UNIQUE, NOT NULL | Unique project ID |
| project_name | VARCHAR(500) | NOT NULL | Display name |
| description | TEXT | | Project description |
| hard_rules | JSONB | DEFAULT '[]' | Array of immutable rules |
| tech_stack | JSONB | DEFAULT '[]' | Array of technologies |
| key_paths | JSONB | DEFAULT '{}' | {name: path} mappings |
| services | JSONB | DEFAULT '{}' | {service: host:port} config |
| active_task_id | VARCHAR(255) | | Currently active task |
| orchestrator_context | JSONB | DEFAULT '{}' | Additional orchestrator state |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |
| version | INTEGER | DEFAULT 1 | Auto-incremented version |

**Initial Data**:

```sql
INSERT INTO global_context (project_id, project_name, description)
VALUES ('story-portal-app', 'Story Portal App',
        'Full-stack story collaboration platform');
```

---

### 5.2.6 context_conflicts

Track and manage detected conflicts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| task_a_id | VARCHAR(255) | NOT NULL | First involved task |
| task_b_id | VARCHAR(255) | | Second task (NULL for internal) |
| conflict_type | VARCHAR(50) | NOT NULL | Conflict type enum |
| description | TEXT | NOT NULL | Human-readable description |
| severity | VARCHAR(20) | NOT NULL | low, medium, high, critical |
| strength | DECIMAL(3,2) | | 0.0-1.0 confidence score |
| evidence | JSONB | | {field, expectedValue, actualValue, location} |
| resolution_status | VARCHAR(50) | DEFAULT 'unresolved' | Status enum |
| resolution | JSONB | | {action, resolvedValue, notes} |
| resolved_by | VARCHAR(255) | | Resolver identifier |
| detected_at | TIMESTAMPTZ | DEFAULT NOW() | Detection timestamp |
| resolved_at | TIMESTAMPTZ | | Resolution timestamp |
| detected_by | VARCHAR(100) | | 'system', 'agent', 'manual' |
| detection_method | VARCHAR(255) | | Tool/method used |

**Indices**:

```sql
CREATE INDEX idx_conflicts_task_a ON context_conflicts(task_a_id);
CREATE INDEX idx_conflicts_task_b ON context_conflicts(task_b_id);
CREATE INDEX idx_conflicts_status ON context_conflicts(resolution_status);
CREATE INDEX idx_conflicts_severity ON context_conflicts(severity);
CREATE INDEX idx_conflicts_unresolved ON context_conflicts(resolution_status)
  WHERE resolution_status = 'unresolved';
```

---

### 5.2.7 task_relationships

Graph of relationships between tasks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| source_task_id | VARCHAR(255) | NOT NULL | Source task |
| target_task_id | VARCHAR(255) | NOT NULL | Target task |
| relationship_type | VARCHAR(50) | NOT NULL | Relationship type enum |
| metadata | JSONB | DEFAULT '{}' | Additional metadata |
| strength | DECIMAL(3,2) | | 0.0-1.0 relationship strength |
| created_by | VARCHAR(255) | | Creator identifier |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

**Constraints**:

```sql
UNIQUE(source_task_id, target_task_id, relationship_type)
```

**Indices**:

```sql
CREATE INDEX idx_relationships_source ON task_relationships(source_task_id);
CREATE INDEX idx_relationships_target ON task_relationships(target_task_id);
CREATE INDEX idx_relationships_type ON task_relationships(relationship_type);
```

---

<a id="section-6"></a>

# Section 6: Integration with Data Layer

## 6.1 PostgreSQL Integration

### 6.1.1 Connection Configuration

```yaml
postgres:
  host: localhost
  port: 5433
  database: consolidator
  schema: mcp_contexts
  pool:
    min: 2
    max: 10
    idle_timeout: 30000
```

### 6.1.2 Trigger Functions

```sql
-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Version increment trigger function
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
  NEW.version = OLD.version + 1;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-save context version function
CREATE OR REPLACE FUNCTION save_context_version()
RETURNS TRIGGER AS $$
BEGIN
  -- Only save on significant changes (not just timestamp updates)
  IF OLD.current_phase IS DISTINCT FROM NEW.current_phase
     OR OLD.iteration IS DISTINCT FROM NEW.iteration
     OR OLD.status IS DISTINCT FROM NEW.status
     OR OLD.immediate_context IS DISTINCT FROM NEW.immediate_context THEN
    INSERT INTO context_versions (task_id, version, snapshot, change_type)
    VALUES (NEW.task_id, NEW.version, row_to_json(NEW), 'auto_save');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 6.2 Redis Integration

### 6.2.1 Connection Configuration

```yaml
redis:
  host: localhost
  port: 6379
  key_prefix: "context:"
  ttl:
    hot_context: 3600      # 1 hour
    task_context: 7200     # 2 hours
    locks: 300             # 5 minutes
```

### 6.2.2 Key Patterns

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `context:hot` | Active task context | 1 hour |
| `context:task:{taskId}` | Individual task cache | 2 hours |
| `context:lock:{taskId}` | Task edit lock | 5 minutes |
| `context:heartbeat:{sessionId}` | Session heartbeat | 2 minutes |

### 6.2.3 Hot Context Structure

```json
{
  "taskId": "string",
  "name": "string",
  "status": "string",
  "currentPhase": "string",
  "iteration": 0,
  "immediateContext": {
    "workingOn": "string",
    "lastAction": "string",
    "nextStep": "string",
    "blockers": []
  },
  "keyFiles": [],
  "resumePrompt": "string",
  "updatedAt": "ISO8601"
}
```

## 6.3 Neo4j Integration

### 6.3.1 Connection Configuration

```yaml
neo4j:
  uri: bolt://localhost:7687
  database: neo4j
  pool_size: 50
```

### 6.3.2 Node Types

| Label | Properties | Purpose |
|-------|------------|---------|
| `Task` | taskId, name, status, phase, priority | Task nodes |
| `Session` | sessionId, status, startedAt | Session tracking |
| `Agent` | agentId, type | Agent tracking |

### 6.3.3 Relationship Types

| Type | Direction | Properties | Purpose |
|------|-----------|------------|---------|
| `BLOCKS` | Task -> Task | reason | Blocking dependency |
| `DEPENDS_ON` | Task -> Task | strength | Soft dependency |
| `RELATED_TO` | Task -> Task | | Related tasks |
| `WORKS_ON` | Session -> Task | startedAt | Session-task mapping |
| `HANDLES` | Agent -> Task | | Agent assignment |

### 6.3.4 Example Queries

```cypher
// Get all tasks blocked by a specific task
MATCH (blocker:Task {taskId: $taskId})-[:BLOCKS]->(blocked:Task)
RETURN blocked

// Get ready tasks (no blocking dependencies)
MATCH (t:Task)
WHERE t.status = 'pending'
  AND NOT EXISTS { (other:Task)-[:BLOCKS]->(t) WHERE other.status <> 'completed' }
RETURN t

// Record session work
MERGE (s:Session {sessionId: $sessionId})
MERGE (t:Task {taskId: $taskId})
MERGE (s)-[:WORKS_ON {startedAt: datetime()}]->(t)
```

## 6.4 File System Integration

### 6.4.1 Directory Structure

```
.claude/
  contexts/
    _registry.json              # Task registry index
    _hot_context.json           # Hot context backup
    task-agents/
      {taskId}.json             # Per-task context files
    shared/
      project-constants.json    # Global constants
  recovery/
    .session-heartbeat.json     # Crash detection
    .tool-history.json          # Tool invocation history
    .pending-saves.json         # Unsaved changes
    .session-state.json         # Session state
```

### 6.4.2 Registry Format

```json
{
  "version": 1,
  "updatedAt": "ISO8601",
  "tasks": {
    "taskId": {
      "name": "string",
      "status": "string",
      "contextFile": "task-agents/{taskId}.json",
      "lastModified": "ISO8601"
    }
  },
  "activeTask": "taskId"
}
```

### 6.4.3 Task Context File Format

```json
{
  "taskId": "string",
  "name": "string",
  "status": "string",
  "currentPhase": "string",
  "iteration": 0,
  "immediateContext": {},
  "keyFiles": [],
  "technicalDecisions": [],
  "resumePrompt": "string",
  "version": 1,
  "updatedAt": "ISO8601"
}
```

---

<a id="section-7"></a>

# Section 7: Reliability and Scalability

## 7.1 Recovery Mechanisms

### 7.1.1 Crash Detection

**Heartbeat Protocol**:

```
Session Start
     |
     v
+--------------------+
| Register Session   |
| Set heartbeat = NOW|
+--------------------+
     |
     v
+--------------------+     60 seconds
| Heartbeat Loop     |<-----------------+
+--------------------+                  |
     |                                  |
     v                                  |
+--------------------+                  |
| Update heartbeat   |------------------+
| Update file marker |
+--------------------+
     |
     v (on crash)
+--------------------+
| Stale heartbeat    |
| detected by next   |
| session            |
+--------------------+
     |
     v
+--------------------+
| Mark session       |
| recovery_needed    |
+--------------------+
```

**Thresholds**:

| Threshold | Value | Description |
|-----------|-------|-------------|
| CRASH_THRESHOLD_MINUTES | 5 | Mark as crashed if heartbeat older |
| STALE_SESSION_HOURS | 24 | Clean up very old sessions |
| HEARTBEAT_INTERVAL_MS | 60000 | Heartbeat update frequency |

### 7.1.2 Compaction Recovery

Context compaction (when Claude Code reduces context window) is handled similarly
to crash recovery. The session detects compaction events and creates a recovery
record with:

- Current task state
- Conversation summary
- Unsaved changes
- Tool history

### 7.1.3 Recovery Flow

```
+------------------+     +------------------+     +------------------+
| New Session      |     | check_recovery   |     | Sessions with    |
| Start            | --> | called           | --> | recovery_needed  |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
                                                 +------------------+
                                                 | Format resume    |
                                                 | prompts          |
                                                 +------------------+
                                                          |
                                                          v
                                                 +------------------+
                                                 | User confirms    |
                                                 | recovery         |
                                                 +------------------+
                                                          |
                                                          v
                                                 +------------------+
                                                 | Mark session     |
                                                 | as recovered     |
                                                 +------------------+
```

## 7.2 Multi-Backend Persistence

### 7.2.1 Write Path

Every context update follows this write path:

```
Update Request
     |
     v
+------------------+
| Validate Input   |
+------------------+
     |
     v
+------------------+
| PostgreSQL Write |  <-- Primary, triggers versioning
+------------------+
     |
     +---> Version created via trigger
     |
     v
+------------------+
| Redis Update     |  <-- Cache layer
+------------------+
     |
     v
+------------------+
| File Sync        |  <-- Recovery backup
+------------------+
     |
     v
+------------------+
| Return Success   |
+------------------+
```

### 7.2.2 Read Path

Reads prioritize speed while ensuring consistency:

```
Read Request
     |
     v
+------------------+
| Check Redis      |  <-- Sub-millisecond access
+------------------+
     |
     | Cache Miss
     v
+------------------+
| Load PostgreSQL  |  <-- Source of truth
+------------------+
     |
     v
+------------------+
| Update Redis     |  <-- Populate cache
+------------------+
     |
     v
+------------------+
| Return Context   |
+------------------+
```

## 7.3 Atomic Task Switching

Task switching uses a transaction-like pattern:

```sql
BEGIN;
  -- Save current task state
  UPDATE task_contexts SET ... WHERE task_id = $fromTaskId;

  -- Load new task
  SELECT * FROM task_contexts WHERE task_id = $toTaskId;

  -- Update global active task
  UPDATE global_context SET active_task_id = $toTaskId;
COMMIT;
```

If any step fails, the entire switch is aborted and the previous state is preserved.

## 7.4 Scaling Considerations

| Component | Scaling Strategy | Limit |
|-----------|-----------------|-------|
| PostgreSQL | Connection pooling, read replicas | 10,000 tasks |
| Redis | Cluster mode, TTL-based eviction | 100,000 keys |
| Neo4j | Causal clustering | 1,000,000 nodes |
| File System | Archival of old contexts | 10,000 files |

---

<a id="section-8"></a>

# Section 8: Security

## 8.1 Session Validation

### 8.1.1 Session ID Generation

Session IDs are generated using cryptographically secure random values:

```typescript
const sessionId = `session-${Date.now()}-${crypto.randomUUID()}`;
```

### 8.1.2 Session Ownership

Sessions are bound to:

- Project directory path
- Git branch (optional)
- Process ID (for crash detection)

## 8.2 Lock Management

### 8.2.1 Task Locking

Tasks can be locked to prevent concurrent modifications:

```typescript
interface TaskLock {
  taskId: string;
  sessionId: string;
  lockedAt: string;
  expiresAt: string;
}
```

**Lock Acquisition**:

```typescript
// Redis SET with NX (only if not exists)
await redis.set(
  `context:lock:${taskId}`,
  JSON.stringify(lock),
  'EX', 300,  // 5 minute expiry
  'NX'        // Only if not exists
);
```

**Lock Collision Detection**:

The `detect_conflicts` tool identifies expired locks that may indicate a crashed
session left a task locked.

### 8.2.2 Locked Elements

Within a task, individual elements can be marked as locked:

```json
{
  "lockedElements": [
    "schema.sql",
    "api.endpoints",
    "critical-decisions"
  ]
}
```

Locked elements prevent modification by other agents/sessions until explicitly
unlocked.

## 8.3 Access Control Patterns

### 8.3.1 Read Access

All tools allow read access to any context:

- `get_unified_context`: Read any task or global context
- `get_task_graph`: Read task relationships
- `detect_conflicts`: Read conflict status

### 8.3.2 Write Access

Write operations record the actor:

- `save_context_snapshot`: Records `sessionId`
- `create_checkpoint`: Records `created_by`
- `resolve_conflict`: Records `resolved_by`

### 8.3.3 Audit Trail

All modifications are tracked via:

1. `context_versions` table (full snapshot history)
2. `created_by` / `session_id` columns
3. Timestamps on all operations

---

<a id="section-9"></a>

# Section 9: Observability

## 9.1 Metrics

### 9.1.1 Prometheus Metrics

```prometheus
# Session Metrics
session_orchestration_sessions_total{status} counter
session_orchestration_sessions_active gauge
session_orchestration_recovery_needed gauge
session_orchestration_heartbeat_age_seconds histogram

# Context Metrics
session_orchestration_context_saves_total{backend} counter
session_orchestration_context_save_duration_seconds{backend} histogram
session_orchestration_context_versions_total{task_id} gauge

# Checkpoint Metrics
session_orchestration_checkpoints_total{type,scope} counter
session_orchestration_rollbacks_total{type} counter

# Conflict Metrics
session_orchestration_conflicts_detected_total{type,severity} counter
session_orchestration_conflicts_unresolved gauge
session_orchestration_conflicts_resolved_total{action} counter

# Task Switch Metrics
session_orchestration_task_switches_total counter
session_orchestration_task_switch_duration_seconds histogram

# Cache Metrics
session_orchestration_cache_hits_total counter
session_orchestration_cache_misses_total counter
session_orchestration_cache_sync_duration_seconds histogram
```

### 9.1.2 Key Performance Indicators

| KPI | Target | Alert Threshold |
|-----|--------|-----------------|
| Context save latency (p99) | < 500ms | > 1s |
| Cache hit rate | > 80% | < 60% |
| Recovery detection time | < 5 min | > 10 min |
| Unresolved conflicts | 0 critical | > 0 critical |
| Active sessions | < 10 | > 20 |

## 9.2 Logging

### 9.2.1 Log Format

```json
{
  "timestamp": "2026-01-14T10:30:00.000Z",
  "level": "INFO",
  "logger": "session-orchestration",
  "message": "Context saved successfully",
  "context": {
    "taskId": "task-123",
    "version": 5,
    "savedTo": ["database", "redis", "file"],
    "duration_ms": 45
  },
  "trace_id": "abc123",
  "span_id": "def456",
  "session_id": "session-xyz"
}
```

### 9.2.2 Log Levels

| Level | Usage |
|-------|-------|
| ERROR | Operation failures, recovery needed |
| WARN | Stale heartbeats, conflicts detected |
| INFO | Context saves, task switches, checkpoints |
| DEBUG | Cache operations, query details |

### 9.2.3 Key Log Events

| Event | Level | Fields |
|-------|-------|--------|
| Session started | INFO | sessionId, taskId, projectDir |
| Session ended | INFO | sessionId, duration, tasksWorked |
| Session crashed | WARN | sessionId, lastHeartbeat, recoveryType |
| Context saved | INFO | taskId, version, backends, duration |
| Checkpoint created | INFO | checkpointId, scope, includedTasks |
| Rollback executed | INFO | taskId, target, backupCreated |
| Conflict detected | WARN | conflictType, severity, tasks |
| Conflict resolved | INFO | conflictId, action, resolvedBy |
| Task switched | INFO | fromTask, toTask, saved |

## 9.3 Tracing

### 9.3.1 Trace Structure

```
Trace: session_orchestration.save_context
|
+-- Span: validate_input (1ms)
|
+-- Span: postgres_update (20ms)
|   +-- Span: trigger_version_save (5ms)
|
+-- Span: redis_update (3ms)
|
+-- Span: file_sync (15ms)
```

### 9.3.2 Span Attributes

| Attribute | Description |
|-----------|-------------|
| `task.id` | Task identifier |
| `session.id` | Session identifier |
| `context.version` | Version number |
| `operation.type` | save, load, switch, etc |
| `backend.type` | postgres, redis, file, neo4j |

---

<a id="section-10"></a>

# Section 10: Configuration

## 10.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SCHEMA` | mcp_contexts | PostgreSQL schema name |
| `MCP_PROJECT_ID` | story-portal-app | Project identifier |
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5433 | PostgreSQL port |
| `POSTGRES_DB` | consolidator | Database name |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_KEY_PREFIX` | context: | Key prefix |
| `NEO4J_URI` | bolt://localhost:7687 | Neo4j connection URI |
| `CONTEXT_DIR` | .claude/contexts | Context file directory |
| `RECOVERY_DIR` | .claude/recovery | Recovery file directory |

## 10.2 Threshold Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `CRASH_THRESHOLD_MINUTES` | 5 | Minutes before session marked crashed |
| `STALE_SESSION_HOURS` | 24 | Hours before session cleanup |
| `HEARTBEAT_INTERVAL_MS` | 60000 | Heartbeat update interval |
| `REDIS_HOT_CONTEXT_TTL` | 3600 | Hot context TTL (seconds) |
| `REDIS_TASK_CONTEXT_TTL` | 7200 | Task context TTL (seconds) |
| `REDIS_LOCK_TTL` | 300 | Lock TTL (seconds) |
| `MAX_VERSIONS_DEFAULT` | 5 | Default versions in history |
| `MAX_VERSIONS_LIMIT` | 100 | Maximum versions to return |

## 10.3 Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_NEO4J` | true | Enable Neo4j integration |
| `ENABLE_FILE_SYNC` | true | Enable file system sync |
| `ENABLE_AUTO_RECOVERY_CHECK` | true | Auto-check recovery on start |
| `ENABLE_CONFLICT_DETECTION` | true | Enable conflict detection |

## 10.4 Configuration File

```yaml
# session-orchestration-config.yaml
version: 1

postgres:
  host: ${POSTGRES_HOST:localhost}
  port: ${POSTGRES_PORT:5433}
  database: ${POSTGRES_DB:consolidator}
  schema: ${MCP_SCHEMA:mcp_contexts}
  pool:
    min: 2
    max: 10

redis:
  host: ${REDIS_HOST:localhost}
  port: ${REDIS_PORT:6379}
  keyPrefix: ${REDIS_KEY_PREFIX:context:}
  ttl:
    hotContext: 3600
    taskContext: 7200
    locks: 300

neo4j:
  uri: ${NEO4J_URI:bolt://localhost:7687}
  enabled: ${ENABLE_NEO4J:true}

recovery:
  crashThresholdMinutes: 5
  staleSessionHours: 24
  heartbeatIntervalMs: 60000

features:
  enableFileSync: true
  enableAutoRecoveryCheck: true
  enableConflictDetection: true
```

---

<a id="section-11"></a>

# Section 11: Implementation Guide

## 11.1 Tool Implementation Pattern

### 11.1.1 Standard Tool Structure

```typescript
import { z } from 'zod';

// Input schema
const InputSchema = z.object({
  taskId: z.string().optional(),
  // ... other fields
});

// Tool handler
async function handleTool(input: unknown) {
  // 1. Validate input
  const params = InputSchema.parse(input);

  // 2. Execute operation
  try {
    const result = await executeOperation(params);

    // 3. Return structured response
    return {
      success: true,
      ...result,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    // 4. Handle errors with codes
    throw new McpError(
      ErrorCode.InternalError,
      `E1610: ${error.message}`
    );
  }
}
```

### 11.1.2 Database Transaction Pattern

```typescript
async function executeWithTransaction<T>(
  operation: (client: PoolClient) => Promise<T>
): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await operation(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}
```

### 11.1.3 Multi-Backend Sync Pattern

```typescript
async function syncToBackends(
  taskId: string,
  context: TaskContext
): Promise<SyncResult> {
  const results: SyncResult = {
    database: false,
    redis: false,
    file: false
  };

  // PostgreSQL (primary)
  results.database = await saveToPostgres(taskId, context);

  // Redis (cache) - non-blocking
  results.redis = await saveToRedis(taskId, context).catch(() => false);

  // File system (backup) - non-blocking
  results.file = await saveToFile(taskId, context).catch(() => false);

  return results;
}
```

## 11.2 Error Handling

### 11.2.1 Error Response Format

```typescript
interface ErrorResponse {
  success: false;
  error: {
    code: string;      // E16XX
    message: string;
    details?: unknown;
  };
  timestamp: string;
}
```

### 11.2.2 Error Propagation

```typescript
function wrapError(code: string, message: string, cause?: Error): McpError {
  const fullMessage = cause
    ? `${code}: ${message} - ${cause.message}`
    : `${code}: ${message}`;

  return new McpError(ErrorCode.InternalError, fullMessage);
}
```

## 11.3 Caching Strategy

### 11.3.1 Cache-Aside Pattern

```typescript
async function getContext(taskId: string): Promise<TaskContext> {
  // Try cache first
  const cached = await redis.get(`context:task:${taskId}`);
  if (cached) {
    return JSON.parse(cached);
  }

  // Load from database
  const context = await loadFromPostgres(taskId);

  // Populate cache
  await redis.setex(
    `context:task:${taskId}`,
    TASK_CONTEXT_TTL,
    JSON.stringify(context)
  );

  return context;
}
```

### 11.3.2 Cache Invalidation

Cache is invalidated on:

1. Direct context updates via `save_context_snapshot`
2. Rollback operations via `rollback_to`
3. Task switches via `switch_task`
4. Explicit sync via `sync_hot_context`

## 11.4 Recovery Implementation

### 11.4.1 Heartbeat Update

```typescript
async function updateHeartbeat(sessionId: string): Promise<void> {
  // Update database
  await pool.query(
    'UPDATE active_sessions SET last_heartbeat = NOW() WHERE session_id = $1',
    [sessionId]
  );

  // Update Redis
  await redis.setex(
    `context:heartbeat:${sessionId}`,
    120, // 2 minute TTL
    Date.now().toString()
  );

  // Update file marker
  await fs.writeFile(
    '.claude/recovery/.session-heartbeat.json',
    JSON.stringify({
      sessionId,
      timestamp: new Date().toISOString()
    })
  );
}
```

### 11.4.2 Crash Detection

```typescript
async function detectCrashedSessions(): Promise<Session[]> {
  const threshold = new Date(Date.now() - CRASH_THRESHOLD_MINUTES * 60 * 1000);

  const result = await pool.query(`
    SELECT * FROM active_sessions
    WHERE status = 'active'
      AND last_heartbeat < $1
  `, [threshold]);

  return result.rows;
}
```

## 11.5 Error Code Registry

| Code | Name | Description | Resolution |
|------|------|-------------|------------|
| E1600 | `SESSION_NOT_FOUND` | Session ID does not exist | Verify session ID |
| E1601 | `SESSION_ALREADY_EXISTS` | Session ID already in use | Use unique session ID |
| E1602 | `SESSION_ENDED` | Session already ended | Start new session |
| E1603 | `SESSION_CRASHED` | Session marked as crashed | Run recovery |
| E1610 | `TASK_NOT_FOUND` | Task ID does not exist | Verify task ID |
| E1611 | `GLOBAL_CONTEXT_NOT_FOUND` | Global context missing | Initialize project |
| E1612 | `UPDATE_VALIDATION_FAILED` | Invalid update data | Check input schema |
| E1613 | `TASK_LOCKED` | Task is locked by another session | Wait or force unlock |
| E1620 | `CHECKPOINT_CREATION_FAILED` | Could not create checkpoint | Check database |
| E1621 | `INVALID_CHECKPOINT_SCOPE` | Invalid scope configuration | Fix scope parameters |
| E1622 | `CHECKPOINT_NOT_FOUND` | Checkpoint ID does not exist | Verify checkpoint ID |
| E1623 | `VERSION_NOT_FOUND` | Version number does not exist | Check version history |
| E1624 | `ROLLBACK_FAILED` | Rollback operation failed | Check database state |
| E1630 | `RECOVERY_CHECK_FAILED` | Could not check recovery | Check database |
| E1631 | `RECOVERY_SESSION_NOT_FOUND` | Recovery session not found | Verify session ID |
| E1632 | `RECOVERY_ALREADY_COMPLETE` | Session already recovered | Skip recovery |
| E1640 | `CONFLICT_DETECTION_FAILED` | Detection query failed | Check database |
| E1641 | `INVALID_CONFLICT_TYPE` | Unknown conflict type | Use valid type |
| E1642 | `CONFLICT_NOT_FOUND` | Conflict ID does not exist | Verify conflict ID |
| E1643 | `CONFLICT_ALREADY_RESOLVED` | Conflict already resolved | Skip resolution |
| E1644 | `RESOLUTION_FAILED` | Resolution action failed | Check conflict state |
| E1650 | `REDIS_SYNC_FAILED` | Redis update failed | Check Redis connection |
| E1651 | `FILE_SYNC_FAILED` | File write failed | Check file permissions |
| E1652 | `NEO4J_QUERY_FAILED` | Neo4j query failed | Check Neo4j connection |
| E1653 | `PARTIAL_SYNC` | Some backends failed | Check error details |
| E1660 | `SOURCE_TASK_NOT_FOUND` | Source task does not exist | Verify fromTaskId |
| E1661 | `TARGET_TASK_NOT_FOUND` | Target task does not exist | Verify toTaskId |
| E1662 | `TASK_SWITCH_FAILED` | Switch operation failed | Check database state |
| E1690 | `CONFIG_INVALID` | Invalid configuration | Check config file |
| E1691 | `CONFIG_MISSING` | Required config missing | Set required values |

---

<a id="section-12"></a>

# Section 12: Testing Strategy

## 12.1 Test Categories

| Category | Scope | Tool | Coverage Target |
|----------|-------|------|-----------------|
| Unit | Individual functions | Jest | 90% |
| Integration | Multi-backend operations | Jest + Testcontainers | 80% |
| E2E | Full workflow scenarios | Custom test runner | 100% of critical paths |

## 12.2 Unit Tests

### 12.2.1 Input Validation Tests

```typescript
describe('save_context_snapshot', () => {
  it('should reject invalid task status', async () => {
    const input = {
      taskId: 'task-123',
      updates: { status: 'invalid_status' }
    };

    await expect(handleSaveContextSnapshot(input))
      .rejects.toThrow(/E1612/);
  });

  it('should accept valid status values', async () => {
    for (const status of ['pending', 'in_progress', 'completed']) {
      const input = { taskId: 'task-123', updates: { status } };
      const result = await handleSaveContextSnapshot(input);
      expect(result.success).toBe(true);
    }
  });
});
```

### 12.2.2 Conflict Detection Tests

```typescript
describe('detect_conflicts', () => {
  it('should detect file conflicts between tasks', async () => {
    // Setup: Two tasks with overlapping key_files
    await createTask('task-a', { keyFiles: ['file1.ts', 'file2.ts'] });
    await createTask('task-b', { keyFiles: ['file2.ts', 'file3.ts'] });

    const result = await handleDetectConflicts({});

    expect(result.detected).toContainEqual(
      expect.objectContaining({
        conflictType: 'file_conflict',
        taskAId: 'task-a',
        taskBId: 'task-b'
      })
    );
  });
});
```

## 12.3 Integration Tests

### 12.3.1 Multi-Backend Sync Test

```typescript
describe('multi-backend persistence', () => {
  it('should sync context to all backends', async () => {
    const taskId = 'test-task';
    const context = { currentPhase: 'testing' };

    await handleSaveContextSnapshot({
      taskId,
      updates: context
    });

    // Verify PostgreSQL
    const dbResult = await pool.query(
      'SELECT * FROM task_contexts WHERE task_id = $1',
      [taskId]
    );
    expect(dbResult.rows[0].current_phase).toBe('testing');

    // Verify Redis
    const cached = await redis.get(`context:task:${taskId}`);
    expect(JSON.parse(cached).currentPhase).toBe('testing');

    // Verify File
    const fileContent = await fs.readFile(
      `.claude/contexts/task-agents/${taskId}.json`,
      'utf-8'
    );
    expect(JSON.parse(fileContent).currentPhase).toBe('testing');
  });
});
```

### 12.3.2 Recovery Flow Test

```typescript
describe('crash recovery', () => {
  it('should detect and recover from crashed session', async () => {
    // Setup: Create active session with old heartbeat
    await createSession('crashed-session', {
      lastHeartbeat: new Date(Date.now() - 10 * 60 * 1000) // 10 min ago
    });

    // Check recovery
    const result = await handleCheckRecovery({});

    expect(result.needsRecovery).toBe(true);
    expect(result.sessions).toContainEqual(
      expect.objectContaining({
        sessionId: 'crashed-session',
        recoveryType: 'crash'
      })
    );

    // Mark recovered
    await handleCheckRecovery({ markRecovered: 'crashed-session' });

    // Verify recovered
    const afterResult = await handleCheckRecovery({});
    expect(afterResult.needsRecovery).toBe(false);
  });
});
```

## 12.4 E2E Workflow Tests

### 12.4.1 Complete Session Lifecycle

```typescript
describe('E2E: Session Lifecycle', () => {
  it('should handle full session lifecycle', async () => {
    // 1. Start session
    const session = await startSession('test-session', 'project-dir');
    expect(session.status).toBe('active');

    // 2. Create task and save context
    await handleSaveContextSnapshot({
      taskId: 'e2e-task',
      updates: {
        status: 'in_progress',
        currentPhase: 'implementation',
        immediateContext: {
          workingOn: 'Feature X',
          lastAction: 'Created file',
          nextStep: 'Write tests',
          blockers: []
        }
      }
    });

    // 3. Create checkpoint
    const checkpoint = await handleCreateCheckpoint({
      label: 'Pre-test checkpoint',
      taskId: 'e2e-task',
      checkpointType: 'manual'
    });
    expect(checkpoint.checkpointId).toBeDefined();

    // 4. Make more changes
    await handleSaveContextSnapshot({
      taskId: 'e2e-task',
      updates: { currentPhase: 'testing' }
    });

    // 5. Rollback to checkpoint
    const rollback = await handleRollbackTo({
      taskId: 'e2e-task',
      target: {
        type: 'checkpoint',
        checkpointId: checkpoint.checkpointId
      }
    });
    expect(rollback.restoredState.currentPhase).toBe('implementation');

    // 6. End session
    await endSession('test-session');

    // 7. Verify no recovery needed
    const recovery = await handleCheckRecovery({});
    expect(recovery.needsRecovery).toBe(false);
  });
});
```

### 12.4.2 Task Switching Test

```typescript
describe('E2E: Task Switching', () => {
  it('should atomically switch between tasks', async () => {
    // Setup
    await createTask('task-a', { currentPhase: 'phase-a' });
    await createTask('task-b', { currentPhase: 'phase-b' });

    // Switch with state preservation
    const result = await handleSwitchTask({
      fromTaskId: 'task-a',
      toTaskId: 'task-b',
      saveCurrentState: true,
      currentTaskUpdates: {
        currentPhase: 'phase-a-updated'
      }
    });

    // Verify previous task saved
    expect(result.previousTask.saved).toBe(true);

    // Verify new task loaded
    expect(result.newTask.taskId).toBe('task-b');
    expect(result.newTask.currentPhase).toBe('phase-b');

    // Verify task-a update persisted
    const taskA = await handleGetUnifiedContext({ taskId: 'task-a' });
    expect(taskA.task.currentPhase).toBe('phase-a-updated');
  });
});
```

## 12.5 Test Data Management

### 12.5.1 Test Fixtures

```typescript
const fixtures = {
  task: {
    minimal: { taskId: 'test-task', name: 'Test Task' },
    full: {
      taskId: 'full-task',
      name: 'Full Test Task',
      status: 'in_progress',
      currentPhase: 'development',
      iteration: 3,
      immediateContext: {
        workingOn: 'Feature implementation',
        lastAction: 'Added tests',
        nextStep: 'Code review',
        blockers: []
      },
      keyFiles: ['src/main.ts', 'src/utils.ts'],
      technicalDecisions: ['Use TypeScript', 'PostgreSQL backend']
    }
  },
  session: {
    active: {
      sessionId: 'test-session',
      status: 'active',
      lastHeartbeat: new Date()
    },
    crashed: {
      sessionId: 'crashed-session',
      status: 'active',
      lastHeartbeat: new Date(Date.now() - 10 * 60 * 1000)
    }
  }
};
```

### 12.5.2 Database Cleanup

```typescript
async function cleanupTestData() {
  await pool.query('DELETE FROM context_conflicts WHERE task_a_id LIKE $1', ['test-%']);
  await pool.query('DELETE FROM context_versions WHERE task_id LIKE $1', ['test-%']);
  await pool.query('DELETE FROM checkpoints WHERE task_id LIKE $1', ['test-%']);
  await pool.query('DELETE FROM task_contexts WHERE task_id LIKE $1', ['test-%']);
  await pool.query('DELETE FROM active_sessions WHERE session_id LIKE $1', ['test-%']);
  await redis.keys('context:*test*').then(keys =>
    keys.length && redis.del(...keys)
  );
}
```

---

<a id="section-13"></a>

# Section 13: Migration and Deployment

## 13.1 Schema Migration

### 13.1.1 Initial Schema Creation

```sql
-- V1__create_mcp_contexts_schema.sql

-- Create schema
CREATE SCHEMA IF NOT EXISTS mcp_contexts;
SET search_path TO mcp_contexts;

-- Create task_contexts table
CREATE TABLE task_contexts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(500) NOT NULL,
  description TEXT,
  agent_type VARCHAR(100),
  status VARCHAR(50) DEFAULT 'pending',
  priority INTEGER DEFAULT 50,
  current_phase VARCHAR(255),
  iteration INTEGER DEFAULT 0,
  score DECIMAL(5,2),
  locked_elements JSONB DEFAULT '[]',
  immediate_context JSONB,
  key_files JSONB,
  technical_decisions JSONB,
  resume_prompt TEXT,
  keywords JSONB,
  token_estimate INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_session_at TIMESTAMPTZ,
  version INTEGER DEFAULT 1
);

-- Create context_versions table
CREATE TABLE context_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id VARCHAR(255) NOT NULL,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  change_summary TEXT,
  change_type VARCHAR(50),
  created_by VARCHAR(255),
  session_id VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(task_id, version)
);

-- Create active_sessions table
CREATE TABLE active_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id VARCHAR(255) UNIQUE NOT NULL,
  task_id VARCHAR(255),
  status VARCHAR(50) DEFAULT 'active',
  started_at TIMESTAMPTZ DEFAULT NOW(),
  last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  context_snapshot JSONB,
  recovery_needed BOOLEAN DEFAULT FALSE,
  recovery_type VARCHAR(50),
  conversation_summary TEXT,
  unsaved_changes JSONB,
  project_dir VARCHAR(1000),
  git_branch VARCHAR(255)
);

-- Create checkpoints table
CREATE TABLE checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checkpoint_id VARCHAR(255) UNIQUE NOT NULL,
  label VARCHAR(500) NOT NULL,
  description TEXT,
  checkpoint_type VARCHAR(50) DEFAULT 'manual',
  task_id VARCHAR(255),
  scope VARCHAR(50) NOT NULL,
  included_tasks JSONB DEFAULT '[]',
  snapshot JSONB NOT NULL,
  es_memory_id VARCHAR(255),
  created_by VARCHAR(255),
  session_id VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create global_context table
CREATE TABLE global_context (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id VARCHAR(255) UNIQUE NOT NULL,
  project_name VARCHAR(500) NOT NULL,
  description TEXT,
  hard_rules JSONB DEFAULT '[]',
  tech_stack JSONB DEFAULT '[]',
  key_paths JSONB DEFAULT '{}',
  services JSONB DEFAULT '{}',
  active_task_id VARCHAR(255),
  orchestrator_context JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version INTEGER DEFAULT 1
);

-- Create context_conflicts table
CREATE TABLE context_conflicts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_a_id VARCHAR(255) NOT NULL,
  task_b_id VARCHAR(255),
  conflict_type VARCHAR(50) NOT NULL,
  description TEXT NOT NULL,
  severity VARCHAR(20) NOT NULL,
  strength DECIMAL(3,2),
  evidence JSONB,
  resolution_status VARCHAR(50) DEFAULT 'unresolved',
  resolution JSONB,
  resolved_by VARCHAR(255),
  detected_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  detected_by VARCHAR(100),
  detection_method VARCHAR(255)
);

-- Create task_relationships table
CREATE TABLE task_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_task_id VARCHAR(255) NOT NULL,
  target_task_id VARCHAR(255) NOT NULL,
  relationship_type VARCHAR(50) NOT NULL,
  metadata JSONB DEFAULT '{}',
  strength DECIMAL(3,2),
  created_by VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source_task_id, target_task_id, relationship_type)
);

-- Create indices
CREATE INDEX idx_task_contexts_status ON task_contexts(status);
CREATE INDEX idx_task_contexts_priority ON task_contexts(priority);
CREATE INDEX idx_task_contexts_updated ON task_contexts(updated_at DESC);
CREATE INDEX idx_task_contexts_keywords ON task_contexts USING GIN(keywords);

CREATE INDEX idx_context_versions_task ON context_versions(task_id);
CREATE INDEX idx_context_versions_created ON context_versions(created_at DESC);
CREATE INDEX idx_context_versions_session ON context_versions(session_id);

CREATE INDEX idx_sessions_status ON active_sessions(status);
CREATE INDEX idx_sessions_heartbeat ON active_sessions(last_heartbeat DESC);
CREATE INDEX idx_sessions_recovery ON active_sessions(recovery_needed)
  WHERE recovery_needed = TRUE;
CREATE INDEX idx_sessions_task ON active_sessions(task_id);

CREATE INDEX idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_type ON checkpoints(checkpoint_type);
CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);
CREATE INDEX idx_checkpoints_label ON checkpoints(label);

CREATE INDEX idx_conflicts_task_a ON context_conflicts(task_a_id);
CREATE INDEX idx_conflicts_task_b ON context_conflicts(task_b_id);
CREATE INDEX idx_conflicts_status ON context_conflicts(resolution_status);
CREATE INDEX idx_conflicts_severity ON context_conflicts(severity);
CREATE INDEX idx_conflicts_unresolved ON context_conflicts(resolution_status)
  WHERE resolution_status = 'unresolved';

CREATE INDEX idx_relationships_source ON task_relationships(source_task_id);
CREATE INDEX idx_relationships_target ON task_relationships(target_task_id);
CREATE INDEX idx_relationships_type ON task_relationships(relationship_type);

-- Create trigger functions
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
  NEW.version = OLD.version + 1;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION save_context_version()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.current_phase IS DISTINCT FROM NEW.current_phase
     OR OLD.iteration IS DISTINCT FROM NEW.iteration
     OR OLD.status IS DISTINCT FROM NEW.status
     OR OLD.immediate_context IS DISTINCT FROM NEW.immediate_context THEN
    INSERT INTO context_versions (task_id, version, snapshot, change_type)
    VALUES (NEW.task_id, NEW.version, row_to_json(NEW), 'auto_save');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER update_task_contexts_timestamp
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER increment_task_version
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER auto_save_context_version
  AFTER UPDATE ON task_contexts
  FOR EACH ROW EXECUTE FUNCTION save_context_version();

CREATE TRIGGER update_global_context_timestamp
  BEFORE UPDATE ON global_context
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER increment_global_version
  BEFORE UPDATE ON global_context
  FOR EACH ROW EXECUTE FUNCTION increment_version();

-- Insert initial global context
INSERT INTO global_context (project_id, project_name, description)
VALUES ('story-portal-app', 'Story Portal App',
        'Full-stack story collaboration platform');
```

### 13.1.2 Migration Checklist

| Step | Command | Verification |
|------|---------|--------------|
| 1. Backup existing data | `pg_dump -s consolidator > backup.sql` | File exists |
| 2. Run migration | `psql -f V1__create_mcp_contexts_schema.sql` | No errors |
| 3. Verify tables | `\dt mcp_contexts.*` | 7 tables |
| 4. Verify triggers | `\df mcp_contexts.*` | 3 functions |
| 5. Verify indices | `\di mcp_contexts.*` | 17+ indices |
| 6. Insert test data | Run test script | Data visible |
| 7. Run tool tests | `npm test` | 12/12 pass |

## 13.2 Deployment Steps

### 13.2.1 Prerequisites

1. PostgreSQL 14+ running on port 5433
2. Redis running on port 6379
3. Neo4j running on port 7687 (optional)
4. Node.js 18+ installed

### 13.2.2 Deployment Sequence

```bash
# 1. Clone/update repository
git pull origin main

# 2. Install dependencies
cd mcp-context-orchestrator
npm install

# 3. Run database migrations
psql -h localhost -p 5433 -d consolidator -f src/schema.sql

# 4. Build TypeScript
npm run build

# 5. Verify installation
npm test

# 6. Start MCP server
npm start
```

### 13.2.3 Health Check

```bash
# Verify MCP server is responding
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'

# Expected: List of 10 tools
```

## 13.3 Rollback Procedure

### 13.3.1 Schema Rollback

```sql
-- V1_rollback__drop_mcp_contexts_schema.sql

DROP SCHEMA IF EXISTS mcp_contexts CASCADE;
```

### 13.3.2 Data Recovery

```bash
# Restore from backup
psql -h localhost -p 5433 -d consolidator -f backup.sql
```

---

<a id="section-14"></a>

# Section 14: Open Questions and Decisions

## 14.1 Resolved Decisions

### 14.1.1 Multi-Backend Strategy

**Decision**: Use PostgreSQL as primary with Redis cache and file backup.

**Rationale**:
- PostgreSQL provides ACID guarantees and trigger-based versioning
- Redis provides sub-millisecond read access for hot context
- File system provides recovery backup independent of database state

**Trade-offs**:
- (+) Zero data loss across multiple failure modes
- (+) Fast reads via cache
- (-) Write latency includes multiple backends
- (-) Complexity in sync maintenance

### 14.1.2 Heartbeat Interval

**Decision**: 60-second heartbeat interval with 5-minute crash threshold.

**Rationale**:
- 60 seconds balances detection speed with resource usage
- 5 minutes allows for brief network issues without false positives

**Trade-offs**:
- (+) Reliable crash detection
- (+) Low overhead
- (-) Up to 5-minute delay in crash detection

### 14.1.3 Conflict Detection Scope

**Decision**: Automatic detection for active tasks only.

**Rationale**:
- Active tasks are most likely to have conflicts
- Archived/completed tasks are immutable
- Reduces detection overhead

## 14.2 Open Questions

### 14.2.1 ES Memory Integration

**Question**: How should checkpoints integrate with ES Memory long-term storage?

**Options**:
1. Store full snapshot in ES Memory
2. Store reference only, keep snapshot in PostgreSQL
3. Hybrid based on checkpoint age

**Status**: Pending ES Memory specification

### 14.2.2 Neo4j Requirement

**Question**: Should Neo4j be required or optional?

**Current**: Optional with feature flag

**Consideration**: Neo4j provides rich relationship queries but adds operational
complexity. Consider providing PostgreSQL-only fallback for simpler deployments.

### 14.2.3 Cross-Project Context

**Question**: Should the system support multiple projects?

**Current**: Single project (story-portal-app)

**Consideration**: The schema supports multiple projects via `project_id`, but
current implementation assumes single project.

---

<a id="section-15"></a>

# Section 15: References and Appendices

## Appendix A: Complete Schema Reference

See [Section 5: Data Model](#section-5) for complete table definitions.

## Appendix B: Error Code Registry

### B.1 Session Errors (E1600-E1609)

| Code | Name | Description |
|------|------|-------------|
| E1600 | SESSION_NOT_FOUND | Session ID does not exist |
| E1601 | SESSION_ALREADY_EXISTS | Session ID already in use |
| E1602 | SESSION_ENDED | Session already ended |
| E1603 | SESSION_CRASHED | Session marked as crashed |

### B.2 Context Errors (E1610-E1619)

| Code | Name | Description |
|------|------|-------------|
| E1610 | TASK_NOT_FOUND | Task ID does not exist |
| E1611 | GLOBAL_CONTEXT_NOT_FOUND | Global context missing |
| E1612 | UPDATE_VALIDATION_FAILED | Invalid update data |
| E1613 | TASK_LOCKED | Task is locked by another session |

### B.3 Checkpoint Errors (E1620-E1629)

| Code | Name | Description |
|------|------|-------------|
| E1620 | CHECKPOINT_CREATION_FAILED | Could not create checkpoint |
| E1621 | INVALID_CHECKPOINT_SCOPE | Invalid scope configuration |
| E1622 | CHECKPOINT_NOT_FOUND | Checkpoint ID does not exist |
| E1623 | VERSION_NOT_FOUND | Version number does not exist |
| E1624 | ROLLBACK_FAILED | Rollback operation failed |

### B.4 Recovery Errors (E1630-E1639)

| Code | Name | Description |
|------|------|-------------|
| E1630 | RECOVERY_CHECK_FAILED | Could not check recovery |
| E1631 | RECOVERY_SESSION_NOT_FOUND | Recovery session not found |
| E1632 | RECOVERY_ALREADY_COMPLETE | Session already recovered |

### B.5 Conflict Errors (E1640-E1649)

| Code | Name | Description |
|------|------|-------------|
| E1640 | CONFLICT_DETECTION_FAILED | Detection query failed |
| E1641 | INVALID_CONFLICT_TYPE | Unknown conflict type |
| E1642 | CONFLICT_NOT_FOUND | Conflict ID does not exist |
| E1643 | CONFLICT_ALREADY_RESOLVED | Conflict already resolved |
| E1644 | RESOLUTION_FAILED | Resolution action failed |

### B.6 Sync Errors (E1650-E1659)

| Code | Name | Description |
|------|------|-------------|
| E1650 | REDIS_SYNC_FAILED | Redis update failed |
| E1651 | FILE_SYNC_FAILED | File write failed |
| E1652 | NEO4J_QUERY_FAILED | Neo4j query failed |
| E1653 | PARTIAL_SYNC | Some backends failed |

### B.7 Task Switch Errors (E1660-E1669)

| Code | Name | Description |
|------|------|-------------|
| E1660 | SOURCE_TASK_NOT_FOUND | Source task does not exist |
| E1661 | TARGET_TASK_NOT_FOUND | Target task does not exist |
| E1662 | TASK_SWITCH_FAILED | Switch operation failed |

### B.8 Configuration Errors (E1690-E1699)

| Code | Name | Description |
|------|------|-------------|
| E1690 | CONFIG_INVALID | Invalid configuration |
| E1691 | CONFIG_MISSING | Required config missing |

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Checkpoint** | Named snapshot of task/global state for rollback |
| **Conflict** | Contradiction between two contexts |
| **Context** | Complete state of a task or project |
| **Context Version** | Historical snapshot of task context |
| **Crash** | Unexpected session termination |
| **Heartbeat** | Periodic signal indicating session is alive |
| **Hot Context** | Currently active task context cached for fast access |
| **Immediate Context** | Current working state (workingOn, lastAction, nextStep, blockers) |
| **Recovery** | Process of restoring session state after crash |
| **Session** | Claude Code interaction session |
| **Task** | Unit of work with associated context |
| **Task Graph** | Relationship network between tasks |

## Appendix D: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-14 | Initial specification |

## Appendix E: Implementation Checklist

| Item | Status | Notes |
|------|--------|-------|
| Schema migration script | Complete | V1__create_mcp_contexts_schema.sql |
| get_unified_context tool | Complete | 12/12 tests pass |
| save_context_snapshot tool | Complete | 12/12 tests pass |
| create_checkpoint tool | Complete | 12/12 tests pass |
| rollback_to tool | Complete | 12/12 tests pass |
| switch_task tool | Complete | 12/12 tests pass |
| detect_conflicts tool | Complete | 12/12 tests pass |
| resolve_conflict tool | Complete | 12/12 tests pass |
| check_recovery tool | Complete | 12/12 tests pass |
| get_task_graph tool | Complete | 12/12 tests pass |
| sync_hot_context tool | Complete | 12/12 tests pass |
| Redis integration | Complete | Hot context caching |
| Neo4j integration | Complete | Task graph queries |
| File system integration | Complete | Recovery backup |
| Error code registry | Complete | E1600-E1699 allocated |

---

**End of Specification**
