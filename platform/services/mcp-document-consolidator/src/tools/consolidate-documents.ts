import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import { MergeEngine } from '../components/merge-engine.js';
import { ConflictDetector } from '../components/conflict-detector.js';
import { EmbeddingPipeline } from '../ai/embedding-pipeline.js';
import { LLMPipeline } from '../ai/llm-pipeline.js';
import type { DatabaseService } from '../db/index.js';
import type { MergeStrategy, ParsedDocument, AtomicClaim, Conflict, ConflictResolution } from '../types.js';

export const ConsolidateDocumentsInputSchema = z.object({
  // Source selection
  document_ids: z.array(z.string().uuid()).optional(),
  scope: z.array(z.string()).optional().describe('Glob patterns for source paths'),
  cluster_id: z.string().uuid().optional().describe('Use overlap cluster from find_overlaps'),

  // Merge strategy
  strategy: z.enum(['smart', 'newest_wins', 'authority_wins', 'merge_all']).default('smart'),
  authority_order: z.array(z.string().uuid()).optional().describe('Document priority for authority_wins'),

  // Conflict resolution
  conflict_threshold: z.number().min(0).max(1).default(0.7),
  auto_resolve_below: z.number().min(0).max(1).default(0.3),
  require_human_above: z.number().min(0).max(1).default(0.9),

  // Output options
  output_format: z.enum(['markdown', 'json', 'yaml']).default('markdown'),
  include_provenance: z.boolean().default(true),
  dry_run: z.boolean().default(false)
}).refine(
  data => data.document_ids || data.scope || data.cluster_id,
  { message: 'One of document_ids, scope, or cluster_id is required' }
);

export const ConsolidateDocumentsOutputSchema = z.object({
  consolidation_id: z.string().uuid(),
  status: z.enum(['completed', 'pending_review', 'failed']),
  output_document: z.object({
    document_id: z.string().uuid().optional(),
    title: z.string(),
    content: z.string(),
    format: z.string()
  }).optional(),
  source_documents: z.array(z.object({
    document_id: z.string().uuid(),
    title: z.string(),
    sections_used: z.number().int(),
    claims_included: z.number().int()
  })),
  conflicts_resolved: z.number().int(),
  conflicts_pending: z.array(z.object({
    conflict_id: z.string().uuid(),
    description: z.string(),
    options: z.array(z.object({
      source_document: z.string().uuid(),
      claim: z.string(),
      confidence: z.number()
    }))
  })),
  provenance_map: z.record(z.string(), z.array(z.string())).optional(),
  processing_time_ms: z.number().int()
});

export type ConsolidateDocumentsInput = z.infer<typeof ConsolidateDocumentsInputSchema>;
export type ConsolidateDocumentsOutput = z.infer<typeof ConsolidateDocumentsOutputSchema>;

interface ConsolidateToolDependencies {
  db: DatabaseService;
  embeddingPipeline: EmbeddingPipeline;
  llmPipeline: LLMPipeline;
  neo4jUri: string;
  neo4jAuth: { username: string; password: string };
}

export function createConsolidateDocumentsTool(deps: ConsolidateToolDependencies) {
  const mergeEngine = new MergeEngine(deps.llmPipeline);
  const conflictDetector = new ConflictDetector(
    deps.embeddingPipeline,
    deps.llmPipeline,
    deps.neo4jUri,
    deps.neo4jAuth
  );

  return {
    name: 'consolidate_documents',
    description: 'Merge multiple documents into a single consolidated document with conflict resolution',
    inputSchema: ConsolidateDocumentsInputSchema,

    async execute(rawInput: unknown): Promise<ConsolidateDocumentsOutput> {
      // Validate input against schema
      const parseResult = ConsolidateDocumentsInputSchema.safeParse(rawInput);
      if (!parseResult.success) {
        throw new Error(`Schema validation failed: ${parseResult.error.issues.map(i => i.message).join(', ')}`);
      }
      const input = parseResult.data;

      const startTime = Date.now();
      const consolidationId = uuidv4();

      // 1. Resolve document IDs
      const documentIds = await resolveDocumentIds(deps.db, input);

      if (documentIds.length < 2) {
        throw new Error('At least 2 documents required for consolidation');
      }

      // 2. Load documents and their claims
      const documents: ParsedDocument[] = [];
      const allClaims: AtomicClaim[] = [];

      for (const docId of documentIds) {
        const doc = await deps.db.documents.findById(docId);
        if (!doc) continue;

        const sections = await deps.db.sections.findByDocumentId(docId);
        const claims = await deps.db.claims.findByDocumentId(docId);

        documents.push({
          id: doc.id,
          source_path: doc.source_path,
          content_hash: doc.content_hash,
          format: doc.format as 'markdown' | 'json' | 'yaml' | 'text',
          title: doc.title,
          raw_content: doc.raw_content,
          sections: sections.map(s => ({
            id: s.id,
            header: s.header,
            content: s.content,
            level: s.level,
            start_line: s.start_line,
            end_line: s.end_line
          })),
          frontmatter: doc.frontmatter || {},
          created_at: doc.created_at instanceof Date ? doc.created_at.toISOString() : (doc.created_at || new Date().toISOString())
        });

        allClaims.push(...claims);
      }

      // 3. Detect conflicts
      const conflicts = await conflictDetector.detectConflicts(allClaims);

      // 4. Categorize conflicts by resolution approach
      const { autoResolve, pendingReview, requireHuman } = categorizeConflicts(
        conflicts,
        input.auto_resolve_below,
        input.require_human_above
      );

      // 5. Build merge strategy
      const strategy: MergeStrategy = {
        type: input.strategy,
        authority_order: input.authority_order,
        conflict_resolution: {
          semantic_threshold: input.conflict_threshold,
          auto_resolve_types: ['value_conflict'],
          require_human_review_for: ['direct_negation']
        }
      };

      // 6. Execute merge (unless dry_run)
      let outputDocument: { document_id?: string; title: string; content: string; format: string } | undefined;
      let conflictsResolved = 0;
      const provenanceMap: Record<string, string[]> = {};

      // Ensure format is always set (default to 'markdown' if not specified)
      const outputFormat = input.output_format || 'markdown';

      if (!input.dry_run) {
        // Auto-resolve low-confidence conflicts
        const autoResolutions: ConflictResolution[] = [];
        for (const conflict of autoResolve) {
          const resolution = await autoResolveConflict(conflict, documents, input.strategy);
          autoResolutions.push(resolution);
          conflictsResolved++;
        }

        // Perform merge
        const mergeResult = await mergeEngine.merge(documents, allClaims, conflicts, strategy);

        // Generate output content
        const outputContent = await generateOutputContent(
          mergeResult,
          documents,
          outputFormat,
          input.include_provenance
        );

        // Store consolidated document
        const consolidatedDocId = uuidv4();

        await deps.db.documents.create({
          id: consolidatedDocId,
          source_path: `consolidated-${consolidationId}`,
          content_hash: hashContent(outputContent),
          format: outputFormat,
          document_type: 'reference',
          title: `Consolidated: ${documents.map(d => d.title).join(' + ')}`,
          authority_level: Math.max(...documents.map(d => (d.frontmatter?.authority_level as number) || 5)),
          raw_content: outputContent,
          frontmatter: {
            consolidated_from: documentIds,
            consolidation_id: consolidationId,
            strategy: input.strategy
          }
        });

        // Store consolidation record
        await deps.db.consolidations.create({
          id: consolidationId,
          source_document_ids: documentIds,
          result_document_id: consolidatedDocId,
          strategy: input.strategy,
          conflicts_resolved: conflictsResolved,
          conflicts_pending: pendingReview.length + requireHuman.length
        });

        // Build provenance map
        if (input.include_provenance) {
          for (const section of mergeResult.sections) {
            const sectionKey = section.header || `section-${uuidv4()}`;
            provenanceMap[sectionKey] = section.provenance.map(p => p.source_document_id);
          }
        }

        outputDocument = {
          document_id: consolidatedDocId,
          title: `Consolidated: ${documents.map(d => d.title).join(' + ')}`,
          content: outputContent,
          format: outputFormat
        };
      }

      // 7. Build pending conflicts response
      const conflictsPending = [...pendingReview, ...requireHuman].map(c => ({
        conflict_id: c.id,
        description: `${c.conflict_type}: "${c.claim_a.text}" vs "${c.claim_b.text}"`,
        options: [
          {
            source_document: c.claim_a.document_id,
            claim: c.claim_a.text,
            confidence: c.claim_a.confidence
          },
          {
            source_document: c.claim_b.document_id,
            claim: c.claim_b.text,
            confidence: c.claim_b.confidence
          }
        ]
      }));

      // 8. Build source documents summary
      const sourceDocuments = documents.map(doc => ({
        document_id: doc.id,
        title: doc.title || 'Untitled',
        sections_used: doc.sections.length,
        claims_included: allClaims.filter(c => c.document_id === doc.id).length
      }));

      return {
        consolidation_id: consolidationId,
        status: conflictsPending.length > 0 ? 'pending_review' : 'completed',
        output_document: outputDocument,
        source_documents: sourceDocuments,
        conflicts_resolved: conflictsResolved,
        conflicts_pending: conflictsPending,
        provenance_map: input.include_provenance ? provenanceMap : undefined,
        processing_time_ms: Date.now() - startTime
      };
    }
  };
}

async function resolveDocumentIds(
  db: DatabaseService,
  input: ConsolidateDocumentsInput
): Promise<string[]> {
  const ids = new Set<string>();

  // Direct document IDs
  if (input.document_ids) {
    for (const id of input.document_ids) {
      ids.add(id);
    }
  }

  // Scope patterns
  if (input.scope) {
    for (const pattern of input.scope) {
      if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(pattern)) {
        ids.add(pattern);
      } else {
        const docs = await db.documents.findByPathPattern(pattern);
        for (const doc of docs) {
          ids.add(doc.id);
        }
      }
    }
  }

  // Cluster ID (from find_overlaps)
  if (input.cluster_id) {
    // Look up cluster members from previous overlap analysis
    const consolidation = await db.consolidations.findByClusterId(input.cluster_id);
    if (consolidation) {
      for (const id of consolidation.source_document_ids) {
        ids.add(id);
      }
    }
  }

  return Array.from(ids);
}

function categorizeConflicts(
  conflicts: Conflict[],
  autoResolveThreshold: number,
  requireHumanThreshold: number
): {
  autoResolve: Conflict[];
  pendingReview: Conflict[];
  requireHuman: Conflict[];
} {
  const autoResolve: Conflict[] = [];
  const pendingReview: Conflict[] = [];
  const requireHuman: Conflict[] = [];

  for (const conflict of conflicts) {
    if (conflict.strength < autoResolveThreshold) {
      autoResolve.push(conflict);
    } else if (conflict.strength > requireHumanThreshold) {
      requireHuman.push(conflict);
    } else {
      pendingReview.push(conflict);
    }
  }

  return { autoResolve, pendingReview, requireHuman };
}

async function autoResolveConflict(
  conflict: Conflict,
  documents: ParsedDocument[],
  strategy: string
): Promise<ConflictResolution> {
  const resolution: ConflictResolution = {
    conflict_id: conflict.id,
    resolution_type: 'auto',
    chosen_claim_id: '',
    reasoning: '',
    resolved_at: new Date()
  };

  switch (strategy) {
    case 'newest_wins': {
      // Find newer document
      const docA = documents.find(d => d.id === conflict.claim_a.document_id);
      const docB = documents.find(d => d.id === conflict.claim_b.document_id);
      const dateA = (docA?.frontmatter?.updated_at as string) || (docA?.frontmatter?.created_at as string) || '';
      const dateB = (docB?.frontmatter?.updated_at as string) || (docB?.frontmatter?.created_at as string) || '';

      if (dateA > dateB) {
        resolution.chosen_claim_id = conflict.claim_a.id;
        resolution.reasoning = `Chose newer document (${dateA} vs ${dateB})`;
      } else {
        resolution.chosen_claim_id = conflict.claim_b.id;
        resolution.reasoning = `Chose newer document (${dateB} vs ${dateA})`;
      }
      break;
    }

    case 'authority_wins': {
      // Find higher authority document
      const docA = documents.find(d => d.id === conflict.claim_a.document_id);
      const docB = documents.find(d => d.id === conflict.claim_b.document_id);
      const authA = (docA?.frontmatter?.authority_level as number) || 5;
      const authB = (docB?.frontmatter?.authority_level as number) || 5;

      if (authA >= authB) {
        resolution.chosen_claim_id = conflict.claim_a.id;
        resolution.reasoning = `Chose higher authority document (${authA} vs ${authB})`;
      } else {
        resolution.chosen_claim_id = conflict.claim_b.id;
        resolution.reasoning = `Chose higher authority document (${authB} vs ${authA})`;
      }
      break;
    }

    default: {
      // Smart: prefer higher confidence claim
      if (conflict.claim_a.confidence >= conflict.claim_b.confidence) {
        resolution.chosen_claim_id = conflict.claim_a.id;
        resolution.reasoning = `Chose higher confidence claim (${conflict.claim_a.confidence.toFixed(2)} vs ${conflict.claim_b.confidence.toFixed(2)})`;
      } else {
        resolution.chosen_claim_id = conflict.claim_b.id;
        resolution.reasoning = `Chose higher confidence claim (${conflict.claim_b.confidence.toFixed(2)} vs ${conflict.claim_a.confidence.toFixed(2)})`;
      }
    }
  }

  return resolution;
}

async function generateOutputContent(
  mergeResult: { sections: Array<{ header: string; content: string; provenance: Array<{ source_document_id: string }> }> },
  documents: ParsedDocument[],
  format: string,
  includeProvenance: boolean
): Promise<string> {
  switch (format) {
    case 'json': {
      const output = {
        title: `Consolidated Document`,
        created_at: new Date().toISOString(),
        source_documents: documents.map(d => ({ id: d.id, title: d.title })),
        sections: mergeResult.sections.map(s => ({
          header: s.header,
          content: s.content,
          ...(includeProvenance ? { sources: s.provenance.map(p => p.source_document_id) } : {})
        }))
      };
      return JSON.stringify(output, null, 2);
    }

    case 'yaml': {
      const lines: string[] = [
        'title: Consolidated Document',
        `created_at: ${new Date().toISOString()}`,
        'source_documents:'
      ];
      for (const doc of documents) {
        lines.push(`  - id: ${doc.id}`);
        lines.push(`    title: "${doc.title || 'Untitled'}"`);
      }
      lines.push('sections:');
      for (const section of mergeResult.sections) {
        lines.push(`  - header: "${section.header}"`);
        lines.push(`    content: |`);
        for (const line of section.content.split('\n')) {
          lines.push(`      ${line}`);
        }
        if (includeProvenance) {
          lines.push(`    sources:`);
          for (const p of section.provenance) {
            lines.push(`      - ${p.source_document_id}`);
          }
        }
      }
      return lines.join('\n');
    }

    default: { // markdown
      const lines: string[] = [
        '# Consolidated Document',
        '',
        `> Generated: ${new Date().toISOString()}`,
        ''
      ];

      if (includeProvenance) {
        lines.push('## Source Documents');
        lines.push('');
        for (const doc of documents) {
          lines.push(`- **${doc.title || 'Untitled'}** (${doc.id})`);
        }
        lines.push('');
        lines.push('---');
        lines.push('');
      }

      for (const section of mergeResult.sections) {
        lines.push(`## ${section.header}`);
        lines.push('');
        lines.push(section.content);
        lines.push('');
        if (includeProvenance) {
          const sources = section.provenance.map(p => p.source_document_id);
          lines.push(`<!-- Sources: ${sources.join(', ')} -->`);
          lines.push('');
        }
      }

      return lines.join('\n');
    }
  }
}

function hashContent(content: string): string {
  // Simple hash for content deduplication
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}
