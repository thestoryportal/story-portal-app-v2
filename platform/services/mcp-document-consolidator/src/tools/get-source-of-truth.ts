import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import { EmbeddingPipeline } from '../ai/embedding-pipeline.js';
import { LLMPipeline } from '../ai/llm-pipeline.js';
import { VerificationPipeline } from '../ai/verification-pipeline.js';
import type { DatabaseService } from '../db/index.js';
import type { AtomicClaim } from '../types.js';

export const GetSourceOfTruthInputSchema = z.object({
  query: z.string().describe('Natural language question or topic'),
  query_type: z.enum(['factual', 'procedural', 'conceptual', 'comparative']).default('factual'),
  scope: z.array(z.string()).optional().describe('Limit to specific documents or patterns'),
  include_deprecated: z.boolean().default(false),
  confidence_threshold: z.number().min(0).max(1).default(0.7),
  max_sources: z.number().int().min(1).max(20).default(5),
  verify_claims: z.boolean().default(true),
  codebase_path: z.string().optional().describe('Path to codebase for code verification')
});

export const GetSourceOfTruthOutputSchema = z.object({
  answer: z.string(),
  confidence: z.number(),
  sources: z.array(z.object({
    document_id: z.string().uuid(),
    document_title: z.string(),
    section_id: z.string().uuid().optional(),
    section_header: z.string().optional(),
    relevance_score: z.number(),
    excerpt: z.string(),
    authority_level: z.number().int()
  })),
  supporting_claims: z.array(z.object({
    claim_id: z.string().uuid(),
    text: z.string(),
    confidence: z.number(),
    verified: z.boolean().optional(),
    verification_method: z.string().optional()
  })),
  conflicting_claims: z.array(z.object({
    claim_a: z.object({
      claim_id: z.string().uuid(),
      text: z.string(),
      source_document: z.string()
    }),
    claim_b: z.object({
      claim_id: z.string().uuid(),
      text: z.string(),
      source_document: z.string()
    }),
    conflict_type: z.string()
  })),
  knowledge_gaps: z.array(z.string()),
  query_id: z.string().uuid(),
  processing_time_ms: z.number().int()
});

export type GetSourceOfTruthInput = z.infer<typeof GetSourceOfTruthInputSchema>;
export type GetSourceOfTruthOutput = z.infer<typeof GetSourceOfTruthOutputSchema>;

interface SourceOfTruthToolDependencies {
  db: DatabaseService;
  embeddingPipeline: EmbeddingPipeline;
  llmPipeline: LLMPipeline;
}

export function createGetSourceOfTruthTool(deps: SourceOfTruthToolDependencies) {
  const verificationPipeline = new VerificationPipeline(deps.llmPipeline);

  return {
    name: 'get_source_of_truth',
    description: 'Query the document corpus for authoritative answers with full provenance',
    inputSchema: GetSourceOfTruthInputSchema,

    async execute(rawInput: unknown): Promise<GetSourceOfTruthOutput> {
      // Validate input against schema
      const parseResult = GetSourceOfTruthInputSchema.safeParse(rawInput);
      if (!parseResult.success) {
        throw new Error(`Schema validation failed: ${parseResult.error.issues.map(i => i.message).join(', ')}`);
      }
      const input = parseResult.data;

      const startTime = Date.now();
      const queryId = uuidv4();

      // 1. Generate query embedding
      const queryEmbedding = await deps.embeddingPipeline.embed([input.query]);

      // 2. Resolve scope to document IDs if provided
      let scopeDocIds: string[] | undefined;
      if (input.scope && input.scope.length > 0) {
        const scopeSet = new Set<string>();
        for (const pattern of input.scope) {
          if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(pattern)) {
            scopeSet.add(pattern);
          } else {
            const docs = await deps.db.documents.findByPathPattern(pattern);
            for (const doc of docs) {
              scopeSet.add(doc.id);
            }
          }
        }
        scopeDocIds = Array.from(scopeSet);
      }

      // 3. Execute pgvector semantic search
      const searchResults = await deps.db.sections.semanticSearch(
        queryEmbedding[0],
        input.max_sources * 3, // Over-fetch for filtering
        scopeDocIds
      );

      // 4. Filter deprecated documents if needed and get document metadata
      const sources: Array<{
        document_id: string;
        document_title: string;
        section_id: string;
        section_header: string;
        relevance_score: number;
        excerpt: string;
        authority_level: number;
      }> = [];

      for (const hit of searchResults) {
        if (sources.length >= input.max_sources) break;

        const doc = await deps.db.documents.findById(hit.document_id);
        if (!doc) continue;

        // Filter deprecated if not requested
        if (!input.include_deprecated && doc.document_type === 'archive') {
          continue;
        }

        sources.push({
          document_id: hit.document_id,
          document_title: doc.title || 'Untitled',
          section_id: hit.section_id,
          section_header: hit.header,
          relevance_score: hit.similarity,
          excerpt: truncateExcerpt(hit.content, 500),
          authority_level: doc.authority_level || 5
        });
      }

      // 7. Find relevant claims
      const relevantClaims: AtomicClaim[] = [];
      for (const source of sources) {
        if (source.section_id) {
          const claims = await deps.db.claims.findBySectionId(source.section_id);
          relevantClaims.push(...claims);
        }
      }

      // 8. Verify claims if requested
      const verifiedClaims: Array<{
        claim_id: string;
        text: string;
        confidence: number;
        verified?: boolean;
        verification_method?: string;
      }> = [];

      if (input.verify_claims && relevantClaims.length > 0) {
        const verificationResults = await verificationPipeline.verifyBatch(
          relevantClaims.slice(0, 10), // Limit verification for performance
          input.codebase_path,
          3
        );

        for (const claim of relevantClaims) {
          const verification = verificationResults.get(claim.id);
          verifiedClaims.push({
            claim_id: claim.id,
            text: claim.original_text,
            confidence: claim.confidence,
            verified: verification?.verified,
            verification_method: verification ?
              verification.signals.map(s => s.type).join(', ') :
              undefined
          });
        }
      } else {
        for (const claim of relevantClaims) {
          verifiedClaims.push({
            claim_id: claim.id,
            text: claim.original_text,
            confidence: claim.confidence
          });
        }
      }

      // 9. Detect conflicting claims
      const conflictingClaims = await findConflictingClaims(deps.db, relevantClaims, sources);

      // 10. Generate answer using LLM
      const { answer, confidence, knowledgeGaps } = await generateAnswer(
        deps.llmPipeline,
        input.query,
        input.query_type,
        sources,
        verifiedClaims,
        input.confidence_threshold
      );

      return {
        answer,
        confidence,
        sources,
        supporting_claims: verifiedClaims.filter(c => c.confidence >= input.confidence_threshold),
        conflicting_claims: conflictingClaims,
        knowledge_gaps: knowledgeGaps,
        query_id: queryId,
        processing_time_ms: Date.now() - startTime
      };
    }
  };
}

function truncateExcerpt(content: string, maxLength: number): string {
  if (content.length <= maxLength) {
    return content;
  }

  // Try to truncate at sentence boundary
  const truncated = content.slice(0, maxLength);
  const lastPeriod = truncated.lastIndexOf('.');
  const lastNewline = truncated.lastIndexOf('\n');
  const cutoff = Math.max(lastPeriod, lastNewline, maxLength - 50);

  return truncated.slice(0, cutoff + 1) + '...';
}

async function findConflictingClaims(
  db: DatabaseService,
  claims: AtomicClaim[],
  sources: Array<{ document_id: string; document_title: string }>
): Promise<Array<{
  claim_a: { claim_id: string; text: string; source_document: string };
  claim_b: { claim_id: string; text: string; source_document: string };
  conflict_type: string;
}>> {
  const conflicts: Array<{
    claim_a: { claim_id: string; text: string; source_document: string };
    claim_b: { claim_id: string; text: string; source_document: string };
    conflict_type: string;
  }> = [];

  // Find existing conflicts for these claims
  const claimIds = claims.map(c => c.id);
  const existingConflicts = await db.conflicts.findByClaimIds(claimIds);

  const sourceMap = new Map(sources.map(s => [s.document_id, s.document_title]));

  for (const conflict of existingConflicts) {
    const claimA = claims.find(c => c.id === conflict.claim_a_id);
    const claimB = claims.find(c => c.id === conflict.claim_b_id);

    if (claimA && claimB) {
      const docIdA = claimA.document_id || claimA.source_section_id;
      const docIdB = claimB.document_id || claimB.source_section_id;
      conflicts.push({
        claim_a: {
          claim_id: claimA.id,
          text: claimA.original_text,
          source_document: sourceMap.get(docIdA) || docIdA
        },
        claim_b: {
          claim_id: claimB.id,
          text: claimB.original_text,
          source_document: sourceMap.get(docIdB) || docIdB
        },
        conflict_type: conflict.conflict_type
      });
    }
  }

  return conflicts;
}

async function generateAnswer(
  llm: LLMPipeline,
  query: string,
  queryType: string,
  sources: Array<{ document_title: string; excerpt: string; authority_level: number; relevance_score: number }>,
  claims: Array<{ text: string; confidence: number; verified?: boolean }>,
  confidenceThreshold: number
): Promise<{ answer: string; confidence: number; knowledgeGaps: string[] }> {
  // Build context from sources
  const context = sources.map((s, i) =>
    `[Source ${i + 1}: ${s.document_title} (Authority: ${s.authority_level}/10)]\n${s.excerpt}`
  ).join('\n\n');

  // Build claims context
  const claimsContext = claims
    .filter(c => c.confidence >= confidenceThreshold)
    .map(c => `- ${c.text} (confidence: ${c.confidence.toFixed(2)}${c.verified ? ', verified' : ''})`)
    .join('\n');

  const prompt = buildQueryPrompt(query, queryType, context, claimsContext);

  try {
    const response = await llm.generate({
      prompt,
      temperature: 0.3,
      maxTokens: 1000
    });

    // Parse structured response
    const parsed = parseAnswerResponse(response);

    return {
      answer: parsed.answer,
      confidence: parsed.confidence,
      knowledgeGaps: parsed.knowledgeGaps
    };
  } catch {
    // Fallback to simple answer
    return {
      answer: sources.length > 0
        ? `Based on the available documentation, the most relevant information comes from: ${sources[0].document_title}.\n\n${sources[0].excerpt}`
        : 'No relevant information found in the document corpus.',
      confidence: sources.length > 0 ? 0.5 : 0,
      knowledgeGaps: ['Unable to generate comprehensive answer']
    };
  }
}

function buildQueryPrompt(
  query: string,
  queryType: string,
  context: string,
  claimsContext: string
): string {
  const typeInstructions: Record<string, string> = {
    factual: 'Provide a direct, factual answer with specific values, names, or data points.',
    procedural: 'Provide step-by-step instructions or a process description.',
    conceptual: 'Explain the concept, its purpose, and how it relates to other concepts.',
    comparative: 'Compare and contrast the relevant items, highlighting similarities and differences.'
  };

  return `You are a documentation expert providing authoritative answers based on source documents.

Query Type: ${queryType}
Instructions: ${typeInstructions[queryType] || typeInstructions.factual}

User Query: ${query}

Available Sources:
${context}

Extracted Claims:
${claimsContext || 'No specific claims extracted.'}

Provide a response in the following JSON format:
{
  "answer": "Your comprehensive answer based on the sources",
  "confidence": 0.0-1.0 (how confident you are in the answer based on source quality and coverage),
  "knowledge_gaps": ["List any aspects of the query not covered by sources", "Or areas where information is incomplete"]
}

Important:
- Base your answer ONLY on the provided sources
- If sources conflict, acknowledge the conflict
- If information is incomplete, note the gaps
- Cite source numbers when making claims`;
}

function parseAnswerResponse(response: string): {
  answer: string;
  confidence: number;
  knowledgeGaps: string[];
} {
  try {
    // Try to extract JSON from response
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        answer: parsed.answer || response,
        confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0.7,
        knowledgeGaps: Array.isArray(parsed.knowledge_gaps) ? parsed.knowledge_gaps : []
      };
    }
  } catch {
    // Fall through to default
  }

  // Default parsing
  return {
    answer: response.trim(),
    confidence: 0.7,
    knowledgeGaps: []
  };
}
