-- MCP Document Consolidator - Initial Schema
-- Version: 2.0.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('markdown', 'json', 'yaml', 'text')),
    document_type TEXT NOT NULL CHECK (document_type IN (
        'spec', 'guide', 'handoff', 'prompt', 'report', 'reference', 'decision', 'archive'
    )),
    title TEXT,
    authority_level INTEGER DEFAULT 5 CHECK (authority_level BETWEEN 1 AND 10),
    raw_content TEXT NOT NULL,
    frontmatter JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    modified_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    deprecated_at TIMESTAMPTZ,

    -- Relationships
    superseded_by UUID REFERENCES documents(id),

    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Sections table
CREATE TABLE sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    header TEXT,
    content TEXT NOT NULL,
    level INTEGER CHECK (level BETWEEN 1 AND 6),
    section_order INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,

    -- Metadata
    semantic_type TEXT CHECK (semantic_type IN (
        'overview', 'requirements', 'instructions', 'configuration',
        'examples', 'constraints', 'decisions', 'status', 'unknown'
    )),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Claims table
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,

    -- Claim structure
    original_text TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    qualifier TEXT,

    -- Metadata
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    source_span_start INTEGER,
    source_span_end INTEGER,
    deprecated BOOLEAN DEFAULT FALSE,

    -- Verification
    verification_status TEXT CHECK (verification_status IN (
        'unverified', 'verified', 'contradicted', 'uncertain'
    )) DEFAULT 'unverified',
    last_verified_at TIMESTAMPTZ,
    verification_evidence JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conflicts table
CREATE TABLE conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_a_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,

    conflict_type TEXT NOT NULL CHECK (conflict_type IN (
        'direct_negation', 'value_conflict', 'temporal_conflict',
        'scope_conflict', 'implication_conflict'
    )),
    strength FLOAT CHECK (strength BETWEEN 0 AND 1),
    detected_by TEXT NOT NULL,
    resolution_hints TEXT[],

    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolution TEXT CHECK (resolution IN ('chose_a', 'chose_b', 'merged', 'flagged')),
    resolution_reasoning TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,  -- 'auto' or user ID

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supersessions table
CREATE TABLE supersessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    old_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    new_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Consolidations table
CREATE TABLE consolidations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_document_ids UUID[] NOT NULL,
    output_content TEXT NOT NULL,
    output_document_id UUID REFERENCES documents(id),

    strategy JSONB NOT NULL,
    statistics JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Provenance table
CREATE TABLE provenance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consolidation_id UUID NOT NULL REFERENCES consolidations(id) ON DELETE CASCADE,
    output_section_header TEXT NOT NULL,
    source_document_id UUID NOT NULL REFERENCES documents(id),
    source_section_id UUID NOT NULL REFERENCES sections(id),
    contribution_type TEXT NOT NULL CHECK (contribution_type IN (
        'primary', 'supplementary', 'superseded'
    )),
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document tags
CREATE TABLE document_tags (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (document_id, tag)
);

-- Feedback table (for learning)
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consolidation_id UUID REFERENCES consolidations(id),
    conflict_id UUID REFERENCES conflicts(id),

    feedback_type TEXT NOT NULL CHECK (feedback_type IN (
        'wrong_resolution', 'missed_conflict', 'false_conflict',
        'bad_merge', 'wrong_provenance'
    )),
    original_output TEXT,
    corrected_output TEXT,
    explanation TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_deprecated ON documents(deprecated_at) WHERE deprecated_at IS NOT NULL;
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_sections_document ON sections(document_id);
CREATE INDEX idx_sections_order ON sections(document_id, section_order);
CREATE INDEX idx_claims_document ON claims(document_id);
CREATE INDEX idx_claims_section ON claims(section_id);
CREATE INDEX idx_claims_subject ON claims(subject);
CREATE INDEX idx_claims_deprecated ON claims(deprecated) WHERE deprecated = true;
CREATE INDEX idx_conflicts_claims ON conflicts(claim_a_id, claim_b_id);
CREATE INDEX idx_conflicts_resolved ON conflicts(resolved);
CREATE INDEX idx_document_tags_tag ON document_tags(tag);
CREATE INDEX idx_provenance_consolidation ON provenance(consolidation_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
