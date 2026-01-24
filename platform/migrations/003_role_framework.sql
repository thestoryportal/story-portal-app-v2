-- Migration: 003_role_framework.sql
-- Description: Create role framework tables for AI/Human role management
-- Author: Agentic Platform Team
-- Date: 2026-01-24
-- Related: Role-based task execution with skills, handoffs, and quality checkpoints

-- ============================================================================
-- Table: roles
-- Purpose: Define roles with classification, skills, and handoff configurations
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    -- Primary Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id TEXT NOT NULL UNIQUE,

    -- Role Metadata
    name TEXT NOT NULL,
    department TEXT,

    -- Classification and Deployment
    classification TEXT NOT NULL,
    deployment_mode TEXT[] DEFAULT '{}',

    -- AI Configuration
    system_prompt TEXT,
    responsibilities JSONB DEFAULT '[]'::jsonb,
    core_skills TEXT[] DEFAULT '{}',

    -- Execution Controls
    stop_checkpoints JSONB DEFAULT '[]'::jsonb,
    can_handoff_to TEXT[] DEFAULT '{}',
    token_estimate INTEGER DEFAULT 4000,

    -- Search and Discovery
    keywords TEXT[] DEFAULT '{}',

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_classification CHECK (
        classification IN ('human_primary', 'hybrid', 'ai_primary')
    ),
    CONSTRAINT chk_token_estimate_positive CHECK (token_estimate > 0),
    CONSTRAINT chk_version_positive CHECK (version >= 1)
);

-- ============================================================================
-- Table: skills
-- Purpose: Store reusable skill definitions with content and metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS skills (
    -- Primary Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id TEXT NOT NULL UNIQUE,

    -- Skill Metadata
    name TEXT NOT NULL,
    category TEXT,

    -- Content
    content TEXT NOT NULL,
    token_count INTEGER,
    complexity TEXT,

    -- Versioning and Generation
    version INTEGER NOT NULL DEFAULT 1,
    is_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_skill_token_count_positive CHECK (token_count IS NULL OR token_count >= 0),
    CONSTRAINT chk_skill_version_positive CHECK (version >= 1)
);

-- ============================================================================
-- Table: role_skills
-- Purpose: Many-to-many mapping between roles and skills with priority
-- ============================================================================

CREATE TABLE IF NOT EXISTS role_skills (
    -- Composite Primary Key
    role_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,

    -- Relationship Metadata
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 1,

    -- Primary Key
    PRIMARY KEY (role_id, skill_id),

    -- Foreign Keys
    CONSTRAINT fk_role_skills_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_role_skills_skill
        FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_priority_positive CHECK (priority >= 1)
);

-- ============================================================================
-- Table: role_executions
-- Purpose: Track execution history for roles with quality metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS role_executions (
    -- Primary Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Role and Session Reference
    role_id TEXT NOT NULL,
    session_id TEXT NOT NULL,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Quality Metrics
    quality_score FLOAT,
    status TEXT NOT NULL DEFAULT 'in_progress',

    -- Foreign Keys
    CONSTRAINT fk_role_executions_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE SET NULL,

    -- Constraints
    CONSTRAINT chk_quality_score_range CHECK (
        quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)
    ),
    CONSTRAINT chk_completed_after_started CHECK (
        completed_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT chk_status_valid CHECK (
        status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')
    )
);

-- ============================================================================
-- Table: handoff_artifacts
-- Purpose: Store artifacts passed between roles during handoffs
-- ============================================================================

CREATE TABLE IF NOT EXISTS handoff_artifacts (
    -- Primary Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handoff_id TEXT NOT NULL UNIQUE,

    -- Role References
    source_role_id TEXT NOT NULL,
    target_role_id TEXT NOT NULL,

    -- Artifact Data
    artifact_type TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Status and Timing
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Foreign Keys
    CONSTRAINT fk_handoff_source_role
        FOREIGN KEY (source_role_id)
        REFERENCES roles(role_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_handoff_target_role
        FOREIGN KEY (target_role_id)
        REFERENCES roles(role_id)
        ON DELETE SET NULL,

    -- Constraints
    CONSTRAINT chk_handoff_status CHECK (
        status IN ('pending', 'accepted', 'rejected', 'completed', 'expired')
    ),
    CONSTRAINT chk_different_roles CHECK (
        source_role_id != target_role_id
    )
);

-- ============================================================================
-- Table: quality_checkpoints
-- Purpose: Record STOP checkpoint evaluations during role execution
-- ============================================================================

CREATE TABLE IF NOT EXISTS quality_checkpoints (
    -- Primary Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Execution Reference
    execution_id UUID NOT NULL,

    -- Checkpoint Data
    checkpoint_name TEXT NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    passed BOOLEAN NOT NULL,
    action_taken TEXT,

    -- Foreign Keys
    CONSTRAINT fk_quality_checkpoints_execution
        FOREIGN KEY (execution_id)
        REFERENCES role_executions(id)
        ON DELETE CASCADE
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Roles indexes
CREATE INDEX IF NOT EXISTS idx_roles_department
ON roles(department)
WHERE department IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_roles_classification
ON roles(classification);

CREATE INDEX IF NOT EXISTS idx_roles_keywords
ON roles USING GIN(keywords);

CREATE INDEX IF NOT EXISTS idx_roles_core_skills
ON roles USING GIN(core_skills);

CREATE INDEX IF NOT EXISTS idx_roles_can_handoff_to
ON roles USING GIN(can_handoff_to);

-- Skills indexes
CREATE INDEX IF NOT EXISTS idx_skills_category
ON skills(category)
WHERE category IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_skills_is_generated
ON skills(is_generated);

CREATE INDEX IF NOT EXISTS idx_skills_complexity
ON skills(complexity)
WHERE complexity IS NOT NULL;

-- Role skills indexes
CREATE INDEX IF NOT EXISTS idx_role_skills_skill_id
ON role_skills(skill_id);

CREATE INDEX IF NOT EXISTS idx_role_skills_required
ON role_skills(role_id)
WHERE is_required = TRUE;

-- Role executions indexes
CREATE INDEX IF NOT EXISTS idx_role_executions_role_id
ON role_executions(role_id);

CREATE INDEX IF NOT EXISTS idx_role_executions_session_id
ON role_executions(session_id);

CREATE INDEX IF NOT EXISTS idx_role_executions_status
ON role_executions(status)
WHERE status = 'in_progress';

CREATE INDEX IF NOT EXISTS idx_role_executions_started_at
ON role_executions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_role_executions_quality
ON role_executions(quality_score DESC NULLS LAST)
WHERE quality_score IS NOT NULL;

-- Handoff artifacts indexes
CREATE INDEX IF NOT EXISTS idx_handoff_artifacts_source_role
ON handoff_artifacts(source_role_id);

CREATE INDEX IF NOT EXISTS idx_handoff_artifacts_target_role
ON handoff_artifacts(target_role_id);

CREATE INDEX IF NOT EXISTS idx_handoff_artifacts_status
ON handoff_artifacts(status)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_handoff_artifacts_created_at
ON handoff_artifacts(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_handoff_artifacts_type
ON handoff_artifacts(artifact_type);

-- Quality checkpoints indexes
CREATE INDEX IF NOT EXISTS idx_quality_checkpoints_execution_id
ON quality_checkpoints(execution_id);

CREATE INDEX IF NOT EXISTS idx_quality_checkpoints_passed
ON quality_checkpoints(execution_id, passed)
WHERE passed = FALSE;

CREATE INDEX IF NOT EXISTS idx_quality_checkpoints_triggered_at
ON quality_checkpoints(triggered_at DESC);

-- ============================================================================
-- Comments
-- ============================================================================

-- Roles table comments
COMMENT ON TABLE roles IS 'Role definitions for AI/human task execution with skills and handoff configurations';
COMMENT ON COLUMN roles.id IS 'Internal UUID primary key';
COMMENT ON COLUMN roles.role_id IS 'Unique text identifier for the role (e.g., code-reviewer, story-writer)';
COMMENT ON COLUMN roles.name IS 'Human-readable display name for the role';
COMMENT ON COLUMN roles.department IS 'Organizational department this role belongs to';
COMMENT ON COLUMN roles.classification IS 'Role type: human_primary (human-led), hybrid (collaborative), ai_primary (AI-led)';
COMMENT ON COLUMN roles.deployment_mode IS 'Array of deployment contexts (e.g., cli, web, api)';
COMMENT ON COLUMN roles.system_prompt IS 'Base system prompt for AI execution of this role';
COMMENT ON COLUMN roles.responsibilities IS 'JSONB array of responsibility definitions';
COMMENT ON COLUMN roles.core_skills IS 'Array of skill_ids required for this role';
COMMENT ON COLUMN roles.stop_checkpoints IS 'JSONB array of STOP checkpoint configurations for quality gates';
COMMENT ON COLUMN roles.can_handoff_to IS 'Array of role_ids this role can hand off work to';
COMMENT ON COLUMN roles.token_estimate IS 'Estimated token budget for role execution';
COMMENT ON COLUMN roles.keywords IS 'Array of keywords for role discovery and matching';
COMMENT ON COLUMN roles.version IS 'Version number for role definition changes';
COMMENT ON COLUMN roles.created_at IS 'Timestamp when role was created';

-- Skills table comments
COMMENT ON TABLE skills IS 'Reusable skill definitions that can be composed into roles';
COMMENT ON COLUMN skills.id IS 'Internal UUID primary key';
COMMENT ON COLUMN skills.skill_id IS 'Unique text identifier for the skill';
COMMENT ON COLUMN skills.name IS 'Human-readable display name for the skill';
COMMENT ON COLUMN skills.category IS 'Skill category for organization (e.g., coding, writing, analysis)';
COMMENT ON COLUMN skills.content IS 'Full skill content/instructions';
COMMENT ON COLUMN skills.token_count IS 'Token count of the skill content';
COMMENT ON COLUMN skills.complexity IS 'Skill complexity level (e.g., basic, intermediate, advanced)';
COMMENT ON COLUMN skills.version IS 'Version number for skill content changes';
COMMENT ON COLUMN skills.is_generated IS 'Whether this skill was AI-generated vs manually authored';
COMMENT ON COLUMN skills.created_at IS 'Timestamp when skill was created';

-- Role skills table comments
COMMENT ON TABLE role_skills IS 'Many-to-many mapping between roles and skills with priority ordering';
COMMENT ON COLUMN role_skills.role_id IS 'Reference to the role';
COMMENT ON COLUMN role_skills.skill_id IS 'Reference to the skill';
COMMENT ON COLUMN role_skills.is_required IS 'Whether this skill is required or optional for the role';
COMMENT ON COLUMN role_skills.priority IS 'Priority order for skill loading (lower = higher priority)';

-- Role executions table comments
COMMENT ON TABLE role_executions IS 'Execution history tracking for role-based task execution';
COMMENT ON COLUMN role_executions.id IS 'Unique execution identifier';
COMMENT ON COLUMN role_executions.role_id IS 'Role being executed';
COMMENT ON COLUMN role_executions.session_id IS 'Session or conversation ID for this execution';
COMMENT ON COLUMN role_executions.started_at IS 'When execution started';
COMMENT ON COLUMN role_executions.completed_at IS 'When execution completed (null if in progress)';
COMMENT ON COLUMN role_executions.quality_score IS 'Quality score from 0.0 to 1.0 based on checkpoint evaluations';
COMMENT ON COLUMN role_executions.status IS 'Execution status: pending, in_progress, completed, failed, cancelled';

-- Handoff artifacts table comments
COMMENT ON TABLE handoff_artifacts IS 'Artifacts passed between roles during work handoffs';
COMMENT ON COLUMN handoff_artifacts.id IS 'Internal UUID primary key';
COMMENT ON COLUMN handoff_artifacts.handoff_id IS 'Unique text identifier for the handoff';
COMMENT ON COLUMN handoff_artifacts.source_role_id IS 'Role initiating the handoff';
COMMENT ON COLUMN handoff_artifacts.target_role_id IS 'Role receiving the handoff';
COMMENT ON COLUMN handoff_artifacts.artifact_type IS 'Type of artifact (e.g., code, document, analysis)';
COMMENT ON COLUMN handoff_artifacts.content IS 'JSONB content of the artifact';
COMMENT ON COLUMN handoff_artifacts.status IS 'Handoff status: pending, accepted, rejected, completed, expired';
COMMENT ON COLUMN handoff_artifacts.created_at IS 'Timestamp when handoff was created';

-- Quality checkpoints table comments
COMMENT ON TABLE quality_checkpoints IS 'STOP checkpoint evaluation records during role execution';
COMMENT ON COLUMN quality_checkpoints.id IS 'Unique checkpoint record identifier';
COMMENT ON COLUMN quality_checkpoints.execution_id IS 'Reference to the role execution';
COMMENT ON COLUMN quality_checkpoints.checkpoint_name IS 'Name of the checkpoint that was triggered';
COMMENT ON COLUMN quality_checkpoints.triggered_at IS 'When the checkpoint was evaluated';
COMMENT ON COLUMN quality_checkpoints.passed IS 'Whether the checkpoint passed or failed';
COMMENT ON COLUMN quality_checkpoints.action_taken IS 'Description of action taken after checkpoint evaluation';

-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Get all AI-primary roles with their skills
-- SELECT r.role_id, r.name, r.classification,
--        array_agg(s.name ORDER BY rs.priority) as skills
-- FROM roles r
-- LEFT JOIN role_skills rs ON r.role_id = rs.role_id
-- LEFT JOIN skills s ON rs.skill_id = s.skill_id
-- WHERE r.classification = 'ai_primary'
-- GROUP BY r.role_id, r.name, r.classification;

-- Get execution history with quality metrics for a role
-- SELECT re.id, re.session_id, re.started_at, re.completed_at,
--        re.quality_score, re.status,
--        COUNT(qc.id) as total_checkpoints,
--        SUM(CASE WHEN qc.passed THEN 1 ELSE 0 END) as passed_checkpoints
-- FROM role_executions re
-- LEFT JOIN quality_checkpoints qc ON re.id = qc.execution_id
-- WHERE re.role_id = $1
-- GROUP BY re.id
-- ORDER BY re.started_at DESC;

-- Get pending handoffs for a target role
-- SELECT ha.handoff_id, ha.artifact_type, ha.content,
--        ha.created_at, r.name as source_role_name
-- FROM handoff_artifacts ha
-- JOIN roles r ON ha.source_role_id = r.role_id
-- WHERE ha.target_role_id = $1 AND ha.status = 'pending'
-- ORDER BY ha.created_at DESC;

-- Find roles by keyword search
-- SELECT role_id, name, department, classification
-- FROM roles
-- WHERE keywords && ARRAY[$1]::text[]
-- ORDER BY name;

-- Get failed checkpoints for analysis
-- SELECT qc.checkpoint_name, qc.action_taken, qc.triggered_at,
--        re.role_id, re.session_id
-- FROM quality_checkpoints qc
-- JOIN role_executions re ON qc.execution_id = re.id
-- WHERE qc.passed = FALSE
-- ORDER BY qc.triggered_at DESC
-- LIMIT 100;

-- ============================================================================
-- Rollback Migration
-- ============================================================================

-- To rollback this migration, run the following commands in order:
-- DROP TABLE IF EXISTS quality_checkpoints CASCADE;
-- DROP TABLE IF EXISTS handoff_artifacts CASCADE;
-- DROP TABLE IF EXISTS role_executions CASCADE;
-- DROP TABLE IF EXISTS role_skills CASCADE;
-- DROP TABLE IF EXISTS skills CASCADE;
-- DROP TABLE IF EXISTS roles CASCADE;
