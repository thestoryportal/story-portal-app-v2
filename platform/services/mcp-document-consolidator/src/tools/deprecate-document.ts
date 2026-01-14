import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import type { DatabaseService } from '../db/index.js';

export const DeprecateDocumentInputSchema = z.object({
  document_id: z.string().uuid(),
  reason: z.string().describe('Reason for deprecation'),
  superseded_by: z.string().uuid().optional().describe('ID of replacing document'),
  migrate_references: z.boolean().default(true),
  archive: z.boolean().default(false).describe('Move to archive instead of just marking deprecated')
});

export const DeprecateDocumentOutputSchema = z.object({
  document_id: z.string().uuid(),
  title: z.string(),
  status: z.enum(['deprecated', 'archived']),
  superseded_by: z.string().uuid().optional(),
  affected_references: z.array(z.object({
    referencing_document_id: z.string().uuid(),
    referencing_document_title: z.string(),
    reference_count: z.number().int(),
    migration_status: z.enum(['migrated', 'pending', 'manual_review_needed'])
  })),
  claims_affected: z.number().int(),
  sections_affected: z.number().int(),
  deprecation_id: z.string().uuid(),
  processing_time_ms: z.number().int()
});

export type DeprecateDocumentInput = z.infer<typeof DeprecateDocumentInputSchema>;
export type DeprecateDocumentOutput = z.infer<typeof DeprecateDocumentOutputSchema>;

interface DeprecateToolDependencies {
  db: DatabaseService;
}

export function createDeprecateDocumentTool(deps: DeprecateToolDependencies) {
  return {
    name: 'deprecate_document',
    description: 'Mark a document as deprecated with optional migration to replacement',
    inputSchema: DeprecateDocumentInputSchema,

    async execute(rawInput: unknown): Promise<DeprecateDocumentOutput> {
      // Validate input against schema
      const parseResult = DeprecateDocumentInputSchema.safeParse(rawInput);
      if (!parseResult.success) {
        throw new Error(`Schema validation failed: ${parseResult.error.issues.map(i => i.message).join(', ')}`);
      }
      const input = parseResult.data;

      const startTime = Date.now();
      const deprecationId = uuidv4();

      // 1. Verify document exists
      const document = await deps.db.documents.findById(input.document_id);
      if (!document) {
        throw new Error(`Document not found: ${input.document_id}`);
      }

      // 2. Verify superseding document exists (if provided)
      if (input.superseded_by) {
        const supersedingDoc = await deps.db.documents.findById(input.superseded_by);
        if (!supersedingDoc) {
          throw new Error(`Superseding document not found: ${input.superseded_by}`);
        }
      }

      // 3. Find all references to this document
      const references = await findDocumentReferences(deps.db, input.document_id);

      // 4. Get counts
      const sections = await deps.db.sections.findByDocumentId(input.document_id);
      const claims = await deps.db.claims.findByDocumentId(input.document_id);

      // 5. Create supersession record if applicable
      if (input.superseded_by) {
        await deps.db.supersessions.create({
          old_document_id: input.document_id,
          new_document_id: input.superseded_by,
          reason: input.reason
        });
      }

      // 6. Migrate references if requested
      const affectedReferences: Array<{
        referencing_document_id: string;
        referencing_document_title: string;
        reference_count: number;
        migration_status: 'migrated' | 'pending' | 'manual_review_needed';
      }> = [];

      for (const ref of references) {
        const refDoc = await deps.db.documents.findById(ref.referencing_document_id);
        let migrationStatus: 'migrated' | 'pending' | 'manual_review_needed' = 'pending';

        if (input.migrate_references && input.superseded_by) {
          // Attempt to migrate references
          const migrated = await migrateReferences(
            deps.db,
            ref.referencing_document_id,
            input.document_id,
            input.superseded_by
          );
          migrationStatus = migrated ? 'migrated' : 'manual_review_needed';
        } else if (!input.superseded_by) {
          migrationStatus = 'manual_review_needed';
        }

        affectedReferences.push({
          referencing_document_id: ref.referencing_document_id,
          referencing_document_title: refDoc?.title || 'Untitled',
          reference_count: ref.reference_count,
          migration_status: migrationStatus
        });
      }

      // 7. Update document status
      const newStatus = input.archive ? 'archived' : 'deprecated';
      const newDocumentType = input.archive ? 'archive' : document.document_type;

      await deps.db.documents.update(input.document_id, {
        document_type: newDocumentType,
        frontmatter: {
          ...document.frontmatter,
          deprecated: true,
          deprecated_at: new Date().toISOString(),
          deprecation_reason: input.reason,
          superseded_by: input.superseded_by
        }
      });

      // 8. Mark claims as deprecated
      for (const claim of claims) {
        await deps.db.claims.update(claim.id, {
          deprecated: true,
          deprecated_at: new Date()
        });
      }

      // 10. Record deprecation event
      await deps.db.provenance.create({
        id: deprecationId,
        document_id: input.document_id,
        event_type: 'deprecation',
        details: {
          reason: input.reason,
          superseded_by: input.superseded_by,
          archive: input.archive,
          references_migrated: affectedReferences.filter(r => r.migration_status === 'migrated').length
        },
        timestamp: new Date()
      });

      return {
        document_id: input.document_id,
        title: document.title || 'Untitled',
        status: newStatus === 'archived' ? 'archived' : 'deprecated',
        superseded_by: input.superseded_by,
        affected_references: affectedReferences,
        claims_affected: claims.length,
        sections_affected: sections.length,
        deprecation_id: deprecationId,
        processing_time_ms: Date.now() - startTime
      };
    }
  };
}

async function findDocumentReferences(
  db: DatabaseService,
  documentId: string
): Promise<Array<{ referencing_document_id: string; reference_count: number }>> {
  // Find documents that reference this document
  // This could be through:
  // 1. Direct links in content
  // 2. Claims referencing entities from this document
  // 3. Supersession chains

  const references: Map<string, number> = new Map();

  // Check for documents that link to this one
  const allDocs = await db.documents.findAll();

  for (const doc of allDocs) {
    if (doc.id === documentId) continue;

    // Check if this document references the target
    const refCount = countReferences(doc.raw_content, documentId);
    if (refCount > 0) {
      references.set(doc.id, refCount);
    }
  }

  // Check claims that reference entities from this document
  const docClaims = await db.claims.findByDocumentId(documentId);
  const subjects = new Set(docClaims.map(c => c.subject.toLowerCase()));

  for (const doc of allDocs) {
    if (doc.id === documentId) continue;
    if (references.has(doc.id)) continue;

    const otherClaims = await db.claims.findByDocumentId(doc.id);
    const matchingClaims = otherClaims.filter(c =>
      subjects.has(c.subject.toLowerCase()) || subjects.has(c.object.toLowerCase())
    );

    if (matchingClaims.length > 0) {
      references.set(doc.id, (references.get(doc.id) || 0) + matchingClaims.length);
    }
  }

  return Array.from(references.entries()).map(([id, count]) => ({
    referencing_document_id: id,
    reference_count: count
  }));
}

function countReferences(content: string, documentId: string): number {
  if (!content) return 0;

  let count = 0;

  // Check for direct UUID references
  const uuidMatches = content.match(new RegExp(documentId, 'gi'));
  if (uuidMatches) {
    count += uuidMatches.length;
  }

  return count;
}

async function migrateReferences(
  db: DatabaseService,
  referencingDocId: string,
  oldDocId: string,
  newDocId: string
): Promise<boolean> {
  try {
    const doc = await db.documents.findById(referencingDocId);
    if (!doc) return false;

    // Replace references in content
    const updatedContent = doc.raw_content.replace(
      new RegExp(oldDocId, 'gi'),
      newDocId
    );

    if (updatedContent !== doc.raw_content) {
      await db.documents.update(referencingDocId, {
        raw_content: updatedContent,
        frontmatter: {
          ...doc.frontmatter,
          references_migrated_at: new Date().toISOString(),
          migrations: [
            ...((doc.frontmatter?.migrations as Array<unknown>) || []),
            { from: oldDocId, to: newDocId, at: new Date().toISOString() }
          ]
        }
      });
    }

    // Update claims that reference entities from old document
    const claims = await db.claims.findByDocumentId(referencingDocId);
    for (const claim of claims) {
      // If claim references the old document in its source tracking
      if (claim.source_document_id === oldDocId) {
        await db.claims.update(claim.id, {
          source_document_id: newDocId
        });
      }
    }

    return true;
  } catch {
    return false;
  }
}

