-- Migration: 001_create_refresh_tokens_table.sql
-- Description: Create refresh_tokens table for JWT token management
-- Author: Agentic Platform Team
-- Date: 2026-01-18
-- Related: P2-04 Token Refresh and Expiration

-- ============================================================================
-- Table: refresh_tokens
-- Purpose: Store refresh tokens with rotation and revocation support
-- ============================================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
    -- Primary Identification
    token_id VARCHAR(255) PRIMARY KEY,

    -- User Association
    user_id VARCHAR(255) NOT NULL,
    client_id VARCHAR(255),  -- OAuth client (web-app, mobile-app, etc.)

    -- Token Data
    token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of refresh token

    -- Expiration and Timestamps
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,

    -- Usage Tracking
    use_count INTEGER NOT NULL DEFAULT 0,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,

    -- Token Family (Rotation)
    parent_token_id VARCHAR(255),
    rotation_deadline TIMESTAMP,

    -- Metadata
    user_agent TEXT,
    ip_address INET,

    -- Constraints
    CONSTRAINT chk_use_count_positive CHECK (use_count >= 0),
    CONSTRAINT chk_expires_after_created CHECK (expires_at > created_at)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary lookup by hash (most common operation)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
ON refresh_tokens(token_hash);

-- Lookup all tokens for a user
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
ON refresh_tokens(user_id);

-- Cleanup expired tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
ON refresh_tokens(expires_at)
WHERE is_revoked = FALSE;  -- Partial index for active tokens

-- Token family queries
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_parent_token_id
ON refresh_tokens(parent_token_id)
WHERE parent_token_id IS NOT NULL;  -- Partial index for children

-- Admin queries (revoked tokens)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked
ON refresh_tokens(is_revoked, expires_at);

-- ============================================================================
-- Foreign Key for Token Families (Optional)
-- ============================================================================

-- Add foreign key constraint if you want to enforce referential integrity
-- Note: This prevents deletion of parent tokens until children are deleted
-- ALTER TABLE refresh_tokens
-- ADD CONSTRAINT fk_parent_token
-- FOREIGN KEY (parent_token_id)
-- REFERENCES refresh_tokens(token_id)
-- ON DELETE SET NULL;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE refresh_tokens IS 'Stores refresh tokens for JWT authentication with rotation and revocation support';
COMMENT ON COLUMN refresh_tokens.token_id IS 'Unique identifier for this token (URL-safe random)';
COMMENT ON COLUMN refresh_tokens.user_id IS 'User who owns this token';
COMMENT ON COLUMN refresh_tokens.client_id IS 'OAuth client identifier (web-app, mobile-app, etc.)';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 hash of the refresh token for secure storage';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Token expiration timestamp (typically 30 days)';
COMMENT ON COLUMN refresh_tokens.created_at IS 'Token creation timestamp';
COMMENT ON COLUMN refresh_tokens.last_used_at IS 'Last time token was used to refresh access token';
COMMENT ON COLUMN refresh_tokens.use_count IS 'Number of times token has been used (for reuse limits)';
COMMENT ON COLUMN refresh_tokens.is_revoked IS 'Whether token has been revoked (logout, compromise, etc.)';
COMMENT ON COLUMN refresh_tokens.parent_token_id IS 'Parent token ID for rotation tracking (forms token family tree)';
COMMENT ON COLUMN refresh_tokens.rotation_deadline IS 'Deadline for token rotation (used with grace period)';
COMMENT ON COLUMN refresh_tokens.user_agent IS 'Client user agent string (optional metadata)';
COMMENT ON COLUMN refresh_tokens.ip_address IS 'Client IP address (optional metadata)';

-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Get token by hash (most common - used in refresh_access_token)
-- SELECT * FROM refresh_tokens WHERE token_hash = $1;

-- Get all active tokens for a user
-- SELECT * FROM refresh_tokens
-- WHERE user_id = $1 AND is_revoked = FALSE AND expires_at > NOW();

-- Revoke token family (recursive CTE)
-- WITH RECURSIVE token_family AS (
--     SELECT token_id FROM refresh_tokens WHERE token_id = $1
--     UNION
--     SELECT rt.token_id
--     FROM refresh_tokens rt
--     INNER JOIN token_family tf ON rt.parent_token_id = tf.token_id
-- )
-- UPDATE refresh_tokens
-- SET is_revoked = TRUE
-- WHERE token_id IN (SELECT token_id FROM token_family);

-- Cleanup expired revoked tokens (run periodically)
-- DELETE FROM refresh_tokens
-- WHERE expires_at < NOW() - INTERVAL '90 days'
--   AND is_revoked = TRUE
-- LIMIT 1000;

-- ============================================================================
-- Rollback Migration
-- ============================================================================

-- To rollback this migration:
-- DROP TABLE IF EXISTS refresh_tokens CASCADE;
