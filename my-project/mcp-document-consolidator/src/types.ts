import { z } from 'zod';

// Document Types
export const DocumentFormatSchema = z.enum(['markdown', 'json', 'yaml', 'text']);
export type DocumentFormat = z.infer<typeof DocumentFormatSchema>;

export const DocumentTypeSchema = z.enum([
  'spec', 'guide', 'handoff', 'prompt', 'report', 'reference', 'decision', 'archive'
]);
export type DocumentType = z.infer<typeof DocumentTypeSchema>;

export const SectionSchema = z.object({
  id: z.string().uuid(),
  header: z.string(),
  level: z.number().int().min(1).max(6),
  content: z.string(),
  start_line: z.number().int(),
  end_line: z.number().int()
});
export type Section = z.infer<typeof SectionSchema>;

export const ParsedDocumentSchema = z.object({
  id: z.string().uuid(),
  source_path: z.string(),
  content_hash: z.string(),
  format: DocumentFormatSchema,
  frontmatter: z.record(z.unknown()).optional(),
  title: z.string().optional(),
  sections: z.array(SectionSchema),
  raw_content: z.string(),
  created_at: z.string().datetime(),
  modified_at: z.string().datetime().optional()
});
export type ParsedDocument = z.infer<typeof ParsedDocumentSchema>;

// Claim Types
export const AtomicClaimSchema = z.object({
  id: z.string().uuid(),
  original_text: z.string(),
  subject: z.string().describe('The entity this claim is about'),
  predicate: z.string().describe('The property or relationship'),
  object: z.string().describe('The value or target'),
  qualifier: z.string().optional().describe('Conditions or context'),
  confidence: z.number().min(0).max(1),
  document_id: z.string().uuid().optional(),
  section_id: z.string().uuid().optional(),
  source_section_id: z.string().uuid(),
  claim_type: z.string().optional(),
  source_span: z.object({
    start: z.number().int(),
    end: z.number().int()
  })
});
export type AtomicClaim = z.infer<typeof AtomicClaimSchema>;

// Entity Types
export const EntityTypeSchema = z.enum([
  'component', 'function', 'config', 'file', 'concept', 'person', 'unknown'
]);
export type EntityType = z.infer<typeof EntityTypeSchema>;

export const EntitySchema = z.object({
  id: z.string().uuid().optional(),
  canonical_id: z.string(),
  name: z.string(),
  canonical_name: z.string().optional(),
  type: EntityTypeSchema,
  aliases: z.array(z.string()),
  source_file: z.string().optional(),
  attributes: z.record(z.unknown()).optional(),
  properties: z.record(z.unknown()).optional()
});
export type Entity = z.infer<typeof EntitySchema>;

export interface EntityMention {
  text: string;
  type?: EntityType;
  context?: string;
}

// Conflict Types
export const ConflictTypeSchema = z.enum([
  'direct_negation',
  'value_conflict',
  'temporal_conflict',
  'scope_conflict',
  'implication_conflict'
]);
export type ConflictType = z.infer<typeof ConflictTypeSchema>;

export const ConflictDetectionMethodSchema = z.enum([
  'semantic', 'entity_graph', 'value_extraction', 'llm_reasoning'
]);
export type ConflictDetectionMethod = z.infer<typeof ConflictDetectionMethodSchema>;

export const ConflictSchema = z.object({
  id: z.string().uuid(),
  claim_a: z.object({
    id: z.string().uuid(),
    document_id: z.string().uuid(),
    text: z.string(),
    confidence: z.number().min(0).max(1)
  }),
  claim_b: z.object({
    id: z.string().uuid(),
    document_id: z.string().uuid(),
    text: z.string(),
    confidence: z.number().min(0).max(1)
  }),
  conflict_type: ConflictTypeSchema,
  strength: z.number().min(0).max(1),
  detected_by: ConflictDetectionMethodSchema,
  resolution_hints: z.array(z.string()),
  created_at: z.string().datetime()
});
export type Conflict = z.infer<typeof ConflictSchema>;

// Merge Types
export const ContributionTypeSchema = z.enum(['primary', 'supplementary', 'superseded']);
export type ContributionType = z.infer<typeof ContributionTypeSchema>;

export const ResolutionTypeSchema = z.enum(['chose_a', 'chose_b', 'merged', 'flagged']);
export type ResolutionType = z.infer<typeof ResolutionTypeSchema>;

export const MergeStrategyModeSchema = z.enum(['smart', 'newest_wins', 'authority_wins', 'manual']);
export type MergeStrategyMode = z.infer<typeof MergeStrategyModeSchema>;

export const ConflictResolutionModeSchema = z.enum(['auto', 'flag_all', 'threshold']);
export type ConflictResolutionMode = z.infer<typeof ConflictResolutionModeSchema>;

export interface MergeStrategy {
  type: string;
  mode?: MergeStrategyMode;
  conflictResolution?: ConflictResolutionMode;
  conflict_resolution?: {
    semantic_threshold?: number;
    auto_resolve_types?: string[];
    require_human_review_for?: string[];
  };
  conflictThreshold?: number;
  authority_order?: string[];
  authorityOrder?: string[];
}

export interface ConflictResolution {
  conflict_id: string;
  resolution_type: string;
  chosen_claim_id: string;
  reasoning: string;
  resolved_at: Date;
}

export interface ProvenanceEntry {
  source_document_id: string;
  source_section_id: string;
  contribution_type: ContributionType;
  confidence: number;
}

export interface MergedSection {
  header: string;
  content: string;
  provenance: ProvenanceEntry[];
}

export interface ResolvedConflict {
  conflict_id: string;
  resolution: ResolutionType;
  reasoning: string;
}

export interface FlaggedConflict {
  conflict_id: string;
  reason: string;
}

export const MergeResultSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  content: z.string(),
  sections: z.array(z.object({
    header: z.string(),
    content: z.string(),
    provenance: z.array(z.object({
      source_document_id: z.string().uuid(),
      source_section_id: z.string().uuid(),
      contribution_type: ContributionTypeSchema,
      confidence: z.number().min(0).max(1)
    }))
  })),
  conflicts_resolved: z.array(z.object({
    conflict_id: z.string().uuid(),
    resolution: ResolutionTypeSchema,
    reasoning: z.string()
  })),
  conflicts_flagged: z.array(z.object({
    conflict_id: z.string().uuid(),
    reason: z.string()
  })),
  statistics: z.object({
    documents_merged: z.number().int(),
    sections_merged: z.number().int(),
    conflicts_auto_resolved: z.number().int(),
    conflicts_flagged: z.number().int(),
    redundancy_eliminated_percent: z.number()
  }),
  created_at: z.string().datetime()
});
export type MergeResult = z.infer<typeof MergeResultSchema>;

// Verification Types
export interface VerificationSignal {
  type: 'code' | 'consistency' | 'ensemble' | 'debate';
  verified?: boolean;
  confidence: number;
  evidence?: string[];
  verdict?: string;
  agreementRate?: number;
  votes?: Record<string, string>;
  reasoning?: string;
}

export interface VerificationResult {
  verified: boolean;
  confidence: number;
  signals: VerificationSignal[];
  should_flag_for_human: boolean;
}

// Audit Types
export interface AuditEntry {
  timestamp: string;
  action: string;
  details: Record<string, unknown>;
}
