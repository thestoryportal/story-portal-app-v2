import { z } from 'zod';
import fs from 'fs/promises';
import { DocumentParser } from '../components/document-parser.js';
import { ClaimExtractor } from '../components/claim-extractor.js';
import { EntityResolver } from '../components/entity-resolver.js';
import { EmbeddingPipeline } from '../ai/embedding-pipeline.js';
import { LLMPipeline } from '../ai/llm-pipeline.js';
import type { DocumentType } from '../types.js';
import type { DatabaseService } from '../db/index.js';

export const IngestDocumentInputSchema = z.object({
  // Source (one required)
  file_path: z.string().optional(),
  content: z.string().optional(),
  url: z.string().url().optional(),

  // Metadata
  document_type: z.enum(['spec', 'guide', 'handoff', 'prompt', 'report', 'reference', 'decision', 'archive']),
  tags: z.array(z.string()).default([]),
  authority_level: z.number().int().min(1).max(10).default(5),
  supersedes: z.array(z.string().uuid()).default([]),

  // Processing options
  extract_claims: z.boolean().default(true),
  generate_embeddings: z.boolean().default(true),
  build_entity_graph: z.boolean().default(true)
}).refine(
  data => data.file_path || data.content || data.url,
  { message: 'One of file_path, content, or url is required' }
);

export const IngestDocumentOutputSchema = z.object({
  document_id: z.string().uuid(),
  title: z.string(),
  sections_extracted: z.number().int(),
  claims_extracted: z.number().int(),
  entities_identified: z.number().int(),
  embeddings_generated: z.number().int(),
  similar_documents: z.array(z.object({
    document_id: z.string().uuid(),
    title: z.string(),
    similarity: z.number()
  })),
  potential_conflicts: z.number().int(),
  processing_time_ms: z.number().int()
});

export type IngestDocumentInput = z.infer<typeof IngestDocumentInputSchema>;
export type IngestDocumentOutput = z.infer<typeof IngestDocumentOutputSchema>;

interface IngestToolDependencies {
  db: DatabaseService;
  embeddingPipeline: EmbeddingPipeline;
  llmPipeline: LLMPipeline;
  entityResolver: EntityResolver | null;
}

export function createIngestDocumentTool(deps: IngestToolDependencies) {
  const parser = new DocumentParser();
  const claimExtractor = new ClaimExtractor(deps.llmPipeline);

  return {
    name: 'ingest_document',
    description: 'Add a document to the consolidation index with optional claim extraction and embedding generation',
    inputSchema: IngestDocumentInputSchema,

    async execute(rawInput: unknown): Promise<IngestDocumentOutput> {
      // Parse input through zod to apply defaults
      const input = IngestDocumentInputSchema.parse(rawInput);
      const startTime = Date.now();

      // 1. Load document content
      let content: string;
      let sourcePath: string;

      if (input.file_path) {
        content = await fs.readFile(input.file_path, 'utf-8');
        sourcePath = input.file_path;
      } else if (input.content) {
        content = input.content;
        sourcePath = `inline-${Date.now()}`;
      } else if (input.url) {
        const response = await fetch(input.url);
        content = await response.text();
        sourcePath = input.url;
      } else {
        throw new Error('No content source provided');
      }

      // 2. Parse document
      const parsed = await parser.parse(content, sourcePath);

      // 3. Store in PostgreSQL
      const documentId = await deps.db.documents.create({
        id: parsed.id,
        source_path: parsed.source_path,
        content_hash: parsed.content_hash,
        format: parsed.format,
        document_type: input.document_type as DocumentType,
        title: parsed.title || sourcePath,
        authority_level: input.authority_level,
        raw_content: parsed.raw_content,
        frontmatter: parsed.frontmatter || {}
      });

      // Store sections
      for (let i = 0; i < parsed.sections.length; i++) {
        const section = parsed.sections[i];
        await deps.db.sections.create({
          id: section.id,
          document_id: documentId,
          header: section.header,
          content: section.content,
          level: section.level,
          section_order: i,
          start_line: section.start_line,
          end_line: section.end_line
        });
      }

      // Store tags
      for (const tag of input.tags) {
        await deps.db.documentTags.add(documentId, tag);
      }

      // 4. Extract claims (if enabled)
      let claimsExtracted = 0;
      if (input.extract_claims) {
        for (const section of parsed.sections) {
          const claims = await claimExtractor.extract(section.content, section.id);
          for (const claim of claims) {
            await deps.db.claims.create({
              ...claim,
              document_id: documentId,
              section_id: section.id
            });
          }
          claimsExtracted += claims.length;
        }
      }

      // 5. Generate embeddings and store in pgvector (if enabled)
      let embeddingsGenerated = 0;
      let documentEmbedding: number[] | null = null;
      if (input.generate_embeddings) {
        for (const section of parsed.sections) {
          const embeddings = await deps.embeddingPipeline.embed([section.content]);
          // Store section embedding in pgvector
          await deps.db.sections.updateEmbedding(section.id, embeddings[0]);
          embeddingsGenerated++;

          // Use first section's embedding as document embedding
          if (!documentEmbedding) {
            documentEmbedding = embeddings[0];
          }
        }

        // Store document-level embedding (average of first section or dedicated)
        if (documentEmbedding) {
          await deps.db.documents.updateEmbedding(documentId, documentEmbedding);
        }
      }

      // 6. Build entity graph (if enabled and entityResolver available)
      let entitiesIdentified = 0;
      if (input.build_entity_graph && deps.entityResolver) {
        const claims = await deps.db.claims.findByDocumentId(documentId);
        const mentions = claims.flatMap(c => [
          { text: c.subject, type: undefined },
          { text: c.object, type: undefined }
        ]);
        const entities = await deps.entityResolver.resolve(mentions);
        entitiesIdentified = entities.size;

        // Link claims to entities
        for (const claim of claims) {
          const subjectEntity = entities.get(claim.subject);
          if (subjectEntity) {
            await deps.entityResolver.linkClaimToEntity(claim.id, subjectEntity.canonical_id, documentId);
          }
        }
      }

      // 7. Find similar documents using pgvector
      const similarDocs = documentEmbedding
        ? await deps.db.documents.findSimilar(documentEmbedding, 5, documentId)
        : [];
      const similarDocuments = similarDocs.map(d => ({
        document_id: d.id,
        title: d.title,
        similarity: d.similarity
      }));

      // 8. Count potential conflicts
      const potentialConflicts = await countPotentialConflicts(deps.db, documentId);

      // 9. Handle supersession
      if (input.supersedes.length > 0) {
        for (const oldId of input.supersedes) {
          await deps.db.supersessions.create({
            old_document_id: oldId,
            new_document_id: documentId,
            reason: 'Explicitly superseded by new document'
          });
        }
      }

      return {
        document_id: documentId,
        title: parsed.title || sourcePath,
        sections_extracted: parsed.sections.length,
        claims_extracted: claimsExtracted,
        entities_identified: entitiesIdentified,
        embeddings_generated: embeddingsGenerated,
        similar_documents: similarDocuments,
        potential_conflicts: potentialConflicts,
        processing_time_ms: Date.now() - startTime
      };
    }
  };
}

async function countPotentialConflicts(
  db: DatabaseService,
  documentId: string
): Promise<number> {
  const claims = await db.claims.findByDocumentId(documentId);
  const subjects = new Set(claims.map(c => c.subject.toLowerCase()));

  // Count claims from other documents with same subjects
  let count = 0;
  for (const subject of subjects) {
    const otherClaims = await db.claims.findBySubject(subject);
    count += otherClaims.filter(c => c.document_id !== documentId).length;
  }

  return count;
}
