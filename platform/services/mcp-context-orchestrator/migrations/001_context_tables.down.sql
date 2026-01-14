-- Rollback Migration: 001_context_tables
-- Description: Drop all context orchestration tables and related objects
-- WARNING: This will delete all data in these tables!

-- Drop views first
DROP VIEW IF EXISTS v_sessions_needing_recovery;
DROP VIEW IF EXISTS v_unresolved_conflicts;
DROP VIEW IF EXISTS v_active_tasks;

-- Drop triggers
DROP TRIGGER IF EXISTS auto_save_task_context_version ON task_contexts;
DROP TRIGGER IF EXISTS increment_task_contexts_version ON task_contexts;
DROP TRIGGER IF EXISTS update_task_contexts_updated_at ON task_contexts;
DROP TRIGGER IF EXISTS update_global_context_updated_at ON global_context;

-- Drop functions
DROP FUNCTION IF EXISTS auto_save_context_version();
DROP FUNCTION IF EXISTS increment_task_version();
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables (in dependency order)
DROP TABLE IF EXISTS checkpoints;
DROP TABLE IF EXISTS context_conflicts;
DROP TABLE IF EXISTS active_sessions;
DROP TABLE IF EXISTS task_relationships;
DROP TABLE IF EXISTS context_versions;
DROP TABLE IF EXISTS global_context;
DROP TABLE IF EXISTS task_contexts;
