-- Migration: 001_context_tables
-- Description: Create core tables for context orchestration system
-- Created: 2026-01-13
-- Part of: mcp-context-orchestrator v3.0

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: task_contexts
-- Purpose: Store full task context with current state
-- ============================================================================
CREATE TABLE IF NOT EXISTS task_contexts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(500) NOT NULL,
  description TEXT,
  agent_type VARCHAR(100),
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'archived')),
  priority INTEGER DEFAULT 50,

  -- State tracking
  current_phase VARCHAR(255),
  iteration INTEGER DEFAULT 0,
  score DECIMAL(5,2),
  locked_elements JSONB DEFAULT '[]'::jsonb,

  -- Context data
  immediate_context JSONB NOT NULL DEFAULT '{}'::jsonb,
  key_files JSONB DEFAULT '[]'::jsonb,
  technical_decisions JSONB DEFAULT '[]'::jsonb,
  resume_prompt TEXT,

  -- Metadata
  keywords JSONB DEFAULT '[]'::jsonb,
  token_estimate INTEGER,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_session_at TIMESTAMP WITH TIME ZONE,

  -- Version tracking
  version INTEGER DEFAULT 1
);

-- Indices for task_contexts
CREATE INDEX IF NOT EXISTS idx_task_contexts_status ON task_contexts(status);
CREATE INDEX IF NOT EXISTS idx_task_contexts_priority ON task_contexts(priority);
CREATE INDEX IF NOT EXISTS idx_task_contexts_updated ON task_contexts(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_contexts_keywords ON task_contexts USING GIN (keywords);

-- ============================================================================
-- TABLE: context_versions
-- Purpose: Version history for task contexts (enables rollback)
-- ============================================================================
CREATE TABLE IF NOT EXISTS context_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id VARCHAR(255) NOT NULL,
  version INTEGER NOT NULL,

  -- Full snapshot of context at this version
  snapshot JSONB NOT NULL,

  -- Change metadata
  change_summary TEXT,
  change_type VARCHAR(50) CHECK (change_type IN ('manual', 'auto_save', 'checkpoint', 'recovery', 'migration')),

  -- Attribution
  created_by VARCHAR(255), -- session_id or agent_id
  session_id VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Ensure unique versions per task
  CONSTRAINT unique_task_version UNIQUE(task_id, version)
);

-- Indices for context_versions
CREATE INDEX IF NOT EXISTS idx_context_versions_task ON context_versions(task_id);
CREATE INDEX IF NOT EXISTS idx_context_versions_created ON context_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_context_versions_session ON context_versions(session_id);

-- ============================================================================
-- TABLE: task_relationships
-- Purpose: Track relationships between tasks (dependencies, blockers, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS task_relationships (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_task_id VARCHAR(255) NOT NULL,
  target_task_id VARCHAR(255) NOT NULL,

  -- Relationship type
  relationship_type VARCHAR(50) NOT NULL CHECK (
    relationship_type IN ('blocks', 'blocked_by', 'depends_on', 'dependency_of', 'related_to', 'parent_of', 'child_of')
  ),

  -- Additional metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  strength DECIMAL(3,2) DEFAULT 1.0,

  -- Attribution
  created_by VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Prevent duplicate relationships
  CONSTRAINT unique_relationship UNIQUE(source_task_id, target_task_id, relationship_type)
);

-- Indices for task_relationships
CREATE INDEX IF NOT EXISTS idx_task_rel_source ON task_relationships(source_task_id);
CREATE INDEX IF NOT EXISTS idx_task_rel_target ON task_relationships(target_task_id);
CREATE INDEX IF NOT EXISTS idx_task_rel_type ON task_relationships(relationship_type);

-- ============================================================================
-- TABLE: active_sessions
-- Purpose: Track active Claude sessions for crash recovery
-- ============================================================================
CREATE TABLE IF NOT EXISTS active_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id VARCHAR(255) NOT NULL UNIQUE,

  -- Current task being worked on
  task_id VARCHAR(255),

  -- Session state
  status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'ended', 'crashed', 'compacted', 'recovered')),

  -- Timing
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE,

  -- Recovery data
  context_snapshot JSONB,
  recovery_needed BOOLEAN DEFAULT FALSE,
  recovery_type VARCHAR(50) CHECK (recovery_type IN ('crash', 'compaction', 'timeout', 'manual')),

  -- Conversation summary for recovery
  conversation_summary TEXT,

  -- Unsaved changes tracking
  unsaved_changes JSONB DEFAULT '[]'::jsonb,

  -- Environment info
  project_dir VARCHAR(1000),
  git_branch VARCHAR(255)
);

-- Indices for active_sessions
CREATE INDEX IF NOT EXISTS idx_sessions_status ON active_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_heartbeat ON active_sessions(last_heartbeat DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_recovery ON active_sessions(recovery_needed) WHERE recovery_needed = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_task ON active_sessions(task_id);

-- ============================================================================
-- TABLE: context_conflicts
-- Purpose: Track and manage conflicts detected across contexts
-- ============================================================================
CREATE TABLE IF NOT EXISTS context_conflicts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Involved tasks
  task_a_id VARCHAR(255) NOT NULL,
  task_b_id VARCHAR(255), -- NULL if conflict is internal to task_a

  -- Conflict details
  conflict_type VARCHAR(50) NOT NULL CHECK (
    conflict_type IN ('state_mismatch', 'file_conflict', 'spec_contradiction', 'version_divergence', 'lock_collision', 'data_inconsistency')
  ),
  description TEXT NOT NULL,
  severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  strength DECIMAL(3,2) NOT NULL,

  -- Conflict evidence
  evidence JSONB DEFAULT '{}'::jsonb,

  -- Resolution tracking
  resolution_status VARCHAR(50) DEFAULT 'unresolved' CHECK (
    resolution_status IN ('unresolved', 'investigating', 'resolved', 'ignored', 'escalated')
  ),
  resolution JSONB,
  resolved_by VARCHAR(255),

  -- Timestamps
  detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  resolved_at TIMESTAMP WITH TIME ZONE,

  -- Auto-detection metadata
  detected_by VARCHAR(100), -- 'system', 'agent', 'manual'
  detection_method VARCHAR(255)
);

-- Indices for context_conflicts
CREATE INDEX IF NOT EXISTS idx_conflicts_task_a ON context_conflicts(task_a_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_task_b ON context_conflicts(task_b_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON context_conflicts(resolution_status);
CREATE INDEX IF NOT EXISTS idx_conflicts_severity ON context_conflicts(severity);
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON context_conflicts(resolution_status) WHERE resolution_status = 'unresolved';

-- ============================================================================
-- TABLE: global_context
-- Purpose: Store project-wide context that applies to all tasks
-- ============================================================================
CREATE TABLE IF NOT EXISTS global_context (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id VARCHAR(255) NOT NULL UNIQUE,

  -- Project metadata
  project_name VARCHAR(500) NOT NULL,
  description TEXT,

  -- Global rules and constants
  hard_rules JSONB DEFAULT '[]'::jsonb,
  tech_stack JSONB DEFAULT '[]'::jsonb,
  key_paths JSONB DEFAULT '{}'::jsonb,
  services JSONB DEFAULT '{}'::jsonb,

  -- Current orchestrator state
  active_task_id VARCHAR(255),
  orchestrator_context JSONB DEFAULT '{}'::jsonb,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Version
  version INTEGER DEFAULT 1
);

-- ============================================================================
-- TABLE: checkpoints
-- Purpose: Named snapshots for rollback (integrates with ES Memory)
-- ============================================================================
CREATE TABLE IF NOT EXISTS checkpoints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  checkpoint_id VARCHAR(255) NOT NULL UNIQUE,

  -- Checkpoint metadata
  label VARCHAR(500) NOT NULL,
  description TEXT,
  checkpoint_type VARCHAR(50) DEFAULT 'manual' CHECK (
    checkpoint_type IN ('manual', 'milestone', 'pre_migration', 'recovery_point', 'auto')
  ),

  -- Scope
  task_id VARCHAR(255), -- NULL means global checkpoint
  scope VARCHAR(50) DEFAULT 'task' CHECK (scope IN ('task', 'global', 'multi_task')),
  included_tasks JSONB DEFAULT '[]'::jsonb,

  -- Full state snapshot
  snapshot JSONB NOT NULL,

  -- ES Memory reference (for integration)
  es_memory_id VARCHAR(255),

  -- Attribution
  created_by VARCHAR(255),
  session_id VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices for checkpoints
CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_type ON checkpoints(checkpoint_type);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_checkpoints_label ON checkpoints(label);

-- ============================================================================
-- FUNCTIONS: Auto-update timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to task_contexts
DROP TRIGGER IF EXISTS update_task_contexts_updated_at ON task_contexts;
CREATE TRIGGER update_task_contexts_updated_at
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to global_context
DROP TRIGGER IF EXISTS update_global_context_updated_at ON global_context;
CREATE TRIGGER update_global_context_updated_at
  BEFORE UPDATE ON global_context
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCTIONS: Auto-increment version on task update
-- ============================================================================
CREATE OR REPLACE FUNCTION increment_task_version()
RETURNS TRIGGER AS $$
BEGIN
  NEW.version = OLD.version + 1;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to task_contexts
DROP TRIGGER IF EXISTS increment_task_contexts_version ON task_contexts;
CREATE TRIGGER increment_task_contexts_version
  BEFORE UPDATE ON task_contexts
  FOR EACH ROW
  EXECUTE FUNCTION increment_task_version();

-- ============================================================================
-- FUNCTIONS: Auto-save context version on significant update
-- ============================================================================
CREATE OR REPLACE FUNCTION auto_save_context_version()
RETURNS TRIGGER AS $$
BEGIN
  -- Only save version if significant fields changed
  IF (OLD.current_phase IS DISTINCT FROM NEW.current_phase) OR
     (OLD.iteration IS DISTINCT FROM NEW.iteration) OR
     (OLD.status IS DISTINCT FROM NEW.status) OR
     (OLD.immediate_context IS DISTINCT FROM NEW.immediate_context) THEN

    INSERT INTO context_versions (task_id, version, snapshot, change_type, change_summary)
    VALUES (
      NEW.task_id,
      NEW.version,
      row_to_json(NEW)::jsonb,
      'auto_save',
      'Auto-saved on significant state change'
    );
  END IF;

  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to task_contexts
DROP TRIGGER IF EXISTS auto_save_task_context_version ON task_contexts;
CREATE TRIGGER auto_save_task_context_version
  AFTER UPDATE ON task_contexts
  FOR EACH ROW
  EXECUTE FUNCTION auto_save_context_version();

-- ============================================================================
-- VIEWS: Useful aggregations
-- ============================================================================

-- Active tasks with recent activity
CREATE OR REPLACE VIEW v_active_tasks AS
SELECT
  tc.task_id,
  tc.name,
  tc.status,
  tc.current_phase,
  tc.iteration,
  tc.priority,
  tc.updated_at,
  tc.last_session_at,
  COUNT(cv.id) as version_count,
  COUNT(DISTINCT tr.id) as relationship_count
FROM task_contexts tc
LEFT JOIN context_versions cv ON tc.task_id = cv.task_id
LEFT JOIN task_relationships tr ON tc.task_id = tr.source_task_id OR tc.task_id = tr.target_task_id
WHERE tc.status NOT IN ('completed', 'archived')
GROUP BY tc.id
ORDER BY tc.priority ASC, tc.updated_at DESC;

-- Unresolved conflicts summary
CREATE OR REPLACE VIEW v_unresolved_conflicts AS
SELECT
  cc.id,
  cc.task_a_id,
  cc.task_b_id,
  cc.conflict_type,
  cc.severity,
  cc.description,
  cc.detected_at,
  ta.name as task_a_name,
  tb.name as task_b_name
FROM context_conflicts cc
LEFT JOIN task_contexts ta ON cc.task_a_id = ta.task_id
LEFT JOIN task_contexts tb ON cc.task_b_id = tb.task_id
WHERE cc.resolution_status = 'unresolved'
ORDER BY
  CASE cc.severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 4
  END,
  cc.detected_at DESC;

-- Sessions requiring recovery
CREATE OR REPLACE VIEW v_sessions_needing_recovery AS
SELECT
  session_id,
  task_id,
  started_at,
  last_heartbeat,
  recovery_type,
  conversation_summary,
  unsaved_changes
FROM active_sessions
WHERE recovery_needed = TRUE
  AND status != 'recovered'
ORDER BY last_heartbeat DESC;

-- ============================================================================
-- INITIAL DATA: Seed global context
-- ============================================================================
INSERT INTO global_context (project_id, project_name, description, hard_rules, tech_stack, key_paths, services)
VALUES (
  'story-portal-app',
  'Story Portal App',
  'Steampunk-themed interactive booking application with WebGL animations',
  '["Canvas 2D is DEPRECATED - use ElectricityOrtho only", "Animation timing via React Spring, not CSS transitions", "All electricity effects must use R3F OrthographicCamera", "Never modify locked animation phases without explicit approval"]'::jsonb,
  '["React 19", "Three.js / React Three Fiber", "Vite 7", "TypeScript 5.x", "React Spring"]'::jsonb,
  '{"electricity": "src/components/electricity/ortho/", "forms": "src/components/form/", "tokens": "src/tokens/design-tokens.css", "contexts": ".claude/contexts/"}'::jsonb,
  '{"postgres": "localhost:5432", "elasticsearch": "localhost:9200", "neo4j": "localhost:7687", "redis": "localhost:6379", "ollama": "localhost:11434"}'::jsonb
)
ON CONFLICT (project_id) DO NOTHING;

-- ============================================================================
-- COMMENTS: Documentation
-- ============================================================================
COMMENT ON TABLE task_contexts IS 'Core table storing full context for each task including state, files, and resume information';
COMMENT ON TABLE context_versions IS 'Version history enabling rollback to any previous task state';
COMMENT ON TABLE task_relationships IS 'Graph of relationships between tasks (blocks, depends_on, etc.)';
COMMENT ON TABLE active_sessions IS 'Tracks Claude sessions for crash/compaction recovery';
COMMENT ON TABLE context_conflicts IS 'Detected conflicts between contexts with resolution tracking';
COMMENT ON TABLE global_context IS 'Project-wide context that applies to all tasks';
COMMENT ON TABLE checkpoints IS 'Named snapshots for explicit rollback points';

COMMENT ON VIEW v_active_tasks IS 'Active tasks with aggregated metadata';
COMMENT ON VIEW v_unresolved_conflicts IS 'Conflicts requiring attention, ordered by severity';
COMMENT ON VIEW v_sessions_needing_recovery IS 'Sessions that crashed or compacted and need state restoration';
