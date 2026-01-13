import { z } from 'zod';
import { ConflictDetector } from '../components/conflict-detector.js';
import { EmbeddingPipeline } from '../ai/embedding-pipeline.js';
import { LLMPipeline } from '../ai/llm-pipeline.js';
import type { DatabaseService } from '../db/index.js';
import type { Client as ElasticsearchClient } from '@elastic/elasticsearch';
import type { Conflict, ConflictType } from '../types.js';
import { v4 as uuidv4 } from 'uuid';

export const FindOverlapsInputSchema = z.object({
  scope: z.array(z.string()).optional().describe('Document IDs or glob patterns'),
  similarity_threshold: z.number().min(0).max(1).default(0.80),
  include_archived: z.boolean().default(false),
  conflict_types: z.array(z.enum([
    'direct_negation', 'value_conflict', 'temporal_conflict', 'scope_conflict', 'implication_conflict'
  ])).optional()
});

export const FindOverlapsOutputSchema = z.object({
  overlap_clusters: z.array(z.object({
    cluster_id: z.string().uuid(),
    theme: z.string(),
    documents: z.array(z.object({
      document_id: z.string().uuid(),
      title: z.string(),
      relevant_sections: z.array(z.string())
    })),
    overlap_percentage: z.number(),
    recommended_action: z.enum(['merge', 'keep_newest', 'review'])
  })),
  conflict_pairs: z.array(z.object({
    conflict_id: z.string().uuid(),
    document_a: z.object({
      document_id: z.string().uuid(),
      title: z.string(),
      claim: z.string()
    }),
    document_b: z.object({
      document_id: z.string().uuid(),
      title: z.string(),
      claim: z.string()
    }),
    conflict_type: z.string(),
    strength: z.number(),
    resolution_hints: z.array(z.string())
  })),
  redundancy_score: z.number(),
  recommendations: z.array(z.object({
    action: z.string(),
    target_documents: z.array(z.string().uuid()),
    reason: z.string(),
    priority: z.enum(['high', 'medium', 'low'])
  })),
  processing_time_ms: z.number().int()
});

export type FindOverlapsInput = z.infer<typeof FindOverlapsInputSchema>;
export type FindOverlapsOutput = z.infer<typeof FindOverlapsOutputSchema>;

interface OverlapCluster {
  id: string;
  theme: string;
  documents: Array<{
    document_id: string;
    title: string;
    relevant_sections: string[];
  }>;
  overlapPercentage: number;
  recommendedAction: 'merge' | 'keep_newest' | 'review';
}

interface FindOverlapsToolDependencies {
  db: DatabaseService;
  es: ElasticsearchClient;
  embeddingPipeline: EmbeddingPipeline;
  llmPipeline: LLMPipeline;
  neo4jUri: string;
  neo4jAuth: { username: string; password: string };
  esIndex: string;
}

export function createFindOverlapsTool(deps: FindOverlapsToolDependencies) {
  const conflictDetector = new ConflictDetector(
    deps.embeddingPipeline,
    deps.llmPipeline,
    deps.neo4jUri,
    deps.neo4jAuth
  );

  return {
    name: 'find_overlaps',
    description: 'Identify redundant or conflicting content across documents',
    inputSchema: FindOverlapsInputSchema,

    async execute(input: FindOverlapsInput): Promise<FindOverlapsOutput> {
      const startTime = Date.now();

      // 1. Resolve scope to document IDs
      const documentIds = await resolveScope(deps.db, input.scope, input.include_archived);

      // 2. Load all sections for scoped documents
      const sections = await deps.db.sections.findByDocumentIds(documentIds);

      // 3. Get embeddings from Elasticsearch
      const embeddings = await deps.es.search({
        index: deps.esIndex,
        body: {
          query: {
            terms: { document_id: documentIds }
          },
          size: 10000,
          _source: ['document_id', 'section_id', 'content', 'header', 'embedding']
        }
      });

      // 4. Cluster similar sections
      const clusters = clusterBySimilarity(
        embeddings.hits.hits as Array<{ _source: { document_id: string; section_id: string; content: string; header: string; embedding: number[] } }>,
        input.similarity_threshold,
        deps.db
      );

      // 5. Detect conflicts within clusters
      const claims = await deps.db.claims.findByDocumentIds(documentIds);
      const conflicts = await conflictDetector.detectConflicts(claims);

      // 6. Filter by conflict types if specified
      const filteredConflicts = input.conflict_types
        ? conflicts.filter(c => input.conflict_types!.includes(c.conflict_type as ConflictType))
        : conflicts;

      // 7. Calculate redundancy score
      const redundancyScore = calculateRedundancyScore(clusters, sections.length);

      // 8. Generate recommendations
      const recommendations = generateRecommendations(clusters, filteredConflicts);

      // 9. Build output
      const overlapClusters = await Promise.all(clusters.map(async c => {
        const docs = await Promise.all(c.documents.map(async d => {
          const doc = await deps.db.documents.findById(d.document_id);
          return {
            document_id: d.document_id,
            title: doc?.title || 'Untitled',
            relevant_sections: d.relevant_sections
          };
        }));

        return {
          cluster_id: c.id,
          theme: c.theme,
          documents: docs,
          overlap_percentage: c.overlapPercentage,
          recommended_action: c.recommendedAction
        };
      }));

      const conflictPairs = await Promise.all(filteredConflicts.map(async c => {
        const docA = await deps.db.documents.findById(c.claim_a.document_id);
        const docB = await deps.db.documents.findById(c.claim_b.document_id);

        return {
          conflict_id: c.id,
          document_a: {
            document_id: c.claim_a.document_id,
            title: docA?.title || 'Untitled',
            claim: c.claim_a.text
          },
          document_b: {
            document_id: c.claim_b.document_id,
            title: docB?.title || 'Untitled',
            claim: c.claim_b.text
          },
          conflict_type: c.conflict_type,
          strength: c.strength,
          resolution_hints: c.resolution_hints
        };
      }));

      return {
        overlap_clusters: overlapClusters,
        conflict_pairs: conflictPairs,
        redundancy_score: redundancyScore,
        recommendations,
        processing_time_ms: Date.now() - startTime
      };
    }
  };
}

async function resolveScope(
  db: DatabaseService,
  scope: string[] | undefined,
  includeArchived: boolean
): Promise<string[]> {
  if (!scope || scope.length === 0) {
    // Return all non-archived documents
    const docs = await db.documents.findAll();
    return docs
      .filter(d => includeArchived || d.document_type !== 'archive')
      .map(d => d.id);
  }

  const ids: string[] = [];

  for (const pattern of scope) {
    // Check if it's a UUID
    if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(pattern)) {
      ids.push(pattern);
    } else {
      // Treat as glob pattern for source_path
      const docs = await db.documents.findByPathPattern(pattern);
      ids.push(...docs.map(d => d.id));
    }
  }

  // Filter archived if needed
  if (!includeArchived) {
    const docs = await Promise.all(ids.map(id => db.documents.findById(id)));
    return docs
      .filter((d): d is NonNullable<typeof d> => d !== null && d.document_type !== 'archive')
      .map(d => d.id);
  }

  return ids;
}

function clusterBySimilarity(
  hits: Array<{ _source: { document_id: string; section_id: string; content: string; header: string; embedding: number[] } }>,
  threshold: number,
  _db: DatabaseService
): OverlapCluster[] {
  const clusters: OverlapCluster[] = [];
  const assigned = new Set<string>();

  for (let i = 0; i < hits.length; i++) {
    const hitA = hits[i]._source;
    if (assigned.has(hitA.section_id)) continue;

    const clusterMembers: Array<{ document_id: string; section_id: string; header: string }> = [
      { document_id: hitA.document_id, section_id: hitA.section_id, header: hitA.header }
    ];

    for (let j = i + 1; j < hits.length; j++) {
      const hitB = hits[j]._source;
      if (assigned.has(hitB.section_id)) continue;

      // Calculate cosine similarity
      const similarity = cosineSimilarity(hitA.embedding, hitB.embedding);

      if (similarity >= threshold) {
        clusterMembers.push({
          document_id: hitB.document_id,
          section_id: hitB.section_id,
          header: hitB.header
        });
        assigned.add(hitB.section_id);
      }
    }

    if (clusterMembers.length > 1) {
      assigned.add(hitA.section_id);

      // Group by document
      const byDocument = new Map<string, string[]>();
      for (const member of clusterMembers) {
        const sections = byDocument.get(member.document_id) || [];
        sections.push(member.section_id);
        byDocument.set(member.document_id, sections);
      }

      const docCount = byDocument.size;
      const overlapPercentage = (clusterMembers.length - docCount) / clusterMembers.length * 100;

      clusters.push({
        id: uuidv4(),
        theme: hitA.header || 'Unnamed Section',
        documents: Array.from(byDocument.entries()).map(([docId, sectionIds]) => ({
          document_id: docId,
          title: '',
          relevant_sections: sectionIds
        })),
        overlapPercentage,
        recommendedAction: overlapPercentage > 70 ? 'merge' : overlapPercentage > 40 ? 'keep_newest' : 'review'
      });
    }
  }

  return clusters;
}

function cosineSimilarity(a: number[], b: number[]): number {
  if (!a || !b || a.length !== b.length) return 0;

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const denominator = Math.sqrt(normA) * Math.sqrt(normB);
  return denominator === 0 ? 0 : dotProduct / denominator;
}

function calculateRedundancyScore(clusters: OverlapCluster[], totalSections: number): number {
  if (totalSections === 0) return 0;

  // Sum up sections involved in overlaps
  const overlappingSections = clusters.reduce((sum, cluster) => {
    return sum + cluster.documents.reduce((docSum, doc) => docSum + doc.relevant_sections.length, 0);
  }, 0);

  return Math.min(100, (overlappingSections / totalSections) * 100);
}

function generateRecommendations(
  clusters: OverlapCluster[],
  conflicts: Conflict[]
): Array<{
  action: string;
  target_documents: string[];
  reason: string;
  priority: 'high' | 'medium' | 'low';
}> {
  const recommendations: Array<{
    action: string;
    target_documents: string[];
    reason: string;
    priority: 'high' | 'medium' | 'low';
  }> = [];

  // Recommend merging highly overlapping clusters
  for (const cluster of clusters) {
    if (cluster.recommendedAction === 'merge') {
      recommendations.push({
        action: 'Consolidate overlapping documents',
        target_documents: cluster.documents.map(d => d.document_id),
        reason: `${cluster.overlapPercentage.toFixed(0)}% content overlap detected in "${cluster.theme}"`,
        priority: 'high'
      });
    }
  }

  // Recommend resolving conflicts
  const conflictsByDocPair = new Map<string, Conflict[]>();
  for (const conflict of conflicts) {
    const key = [conflict.claim_a.document_id, conflict.claim_b.document_id].sort().join('|');
    const existing = conflictsByDocPair.get(key) || [];
    existing.push(conflict);
    conflictsByDocPair.set(key, existing);
  }

  for (const [key, docConflicts] of conflictsByDocPair) {
    const [docA, docB] = key.split('|');
    recommendations.push({
      action: 'Resolve document conflicts',
      target_documents: [docA, docB],
      reason: `${docConflicts.length} conflict(s) detected between documents`,
      priority: docConflicts.length > 3 ? 'high' : docConflicts.length > 1 ? 'medium' : 'low'
    });
  }

  return recommendations;
}
