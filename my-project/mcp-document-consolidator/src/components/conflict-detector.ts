import { z } from 'zod';
import neo4j, { Driver } from 'neo4j-driver';
import { v4 as uuidv4 } from 'uuid';
import type { AtomicClaim, Conflict, ConflictType } from '../types.js';
import { LLMError } from '../errors.js';

export interface EmbeddingService {
  embed(texts: string[]): Promise<number[][]>;
}

export interface LLMService {
  generate(params: {
    model?: string;
    prompt: string;
    format?: 'json';
    options?: Record<string, unknown>;
  }): Promise<string>;
}

const ConflictVerificationSchema = z.object({
  is_conflict: z.boolean(),
  conflict_type: z.enum([
    'direct_negation', 'value_conflict', 'temporal_conflict',
    'scope_conflict', 'implication_conflict', 'not_a_conflict'
  ]),
  explanation: z.string(),
  resolution_hints: z.array(z.string())
});

export class ConflictDetector {
  private embeddingService: EmbeddingService;
  private llmService: LLMService;
  private neo4jDriver: Driver;

  constructor(
    embeddingService: EmbeddingService,
    llmService: LLMService,
    neo4jUri: string,
    neo4jAuth: { username: string; password: string }
  ) {
    this.embeddingService = embeddingService;
    this.llmService = llmService;
    this.neo4jDriver = neo4j.driver(
      neo4jUri,
      neo4j.auth.basic(neo4jAuth.username, neo4jAuth.password)
    );
  }

  async detectConflicts(claims: AtomicClaim[]): Promise<Conflict[]> {
    const conflicts: Conflict[] = [];

    // 1. Detect by semantic similarity (potential same topic)
    const semanticConflicts = await this.detectSemanticConflicts(claims);
    conflicts.push(...semanticConflicts);

    // 2. Detect by entity graph (transitive conflicts)
    const graphConflicts = await this.detectGraphConflicts(claims);
    conflicts.push(...graphConflicts);

    // 3. Detect by value extraction (same property, different value)
    const valueConflicts = this.detectValueConflicts(claims);
    conflicts.push(...valueConflicts);

    // 4. Verify with LLM reasoning and deduplicate
    const verifiedConflicts = await this.verifyConflictsWithLLM(conflicts);

    return this.deduplicateConflicts(verifiedConflicts);
  }

  private async detectSemanticConflicts(claims: AtomicClaim[]): Promise<Conflict[]> {
    const conflicts: Conflict[] = [];

    if (claims.length < 2) return conflicts;

    // Get embeddings for all claims
    const claimTexts = claims.map(c => `${c.subject} ${c.predicate} ${c.object}`);
    const embeddings = await this.embeddingService.embed(claimTexts);

    // Find pairs with high similarity (same topic) but different objects
    for (let i = 0; i < claims.length; i++) {
      for (let j = i + 1; j < claims.length; j++) {
        const similarity = this.cosineSimilarity(embeddings[i], embeddings[j]);

        // High similarity but from different sections
        if (similarity > 0.8 && claims[i].source_section_id !== claims[j].source_section_id) {
          // Check if objects are different
          if (claims[i].object.toLowerCase() !== claims[j].object.toLowerCase()) {
            conflicts.push({
              id: uuidv4(),
              claim_a: {
                id: claims[i].id,
                document_id: claims[i].document_id || claims[i].source_section_id, // Will be updated with actual document_id
                text: claims[i].original_text,
                confidence: claims[i].confidence
              },
              claim_b: {
                id: claims[j].id,
                document_id: claims[j].document_id || claims[j].source_section_id,
                text: claims[j].original_text,
                confidence: claims[j].confidence
              },
              conflict_type: 'value_conflict',
              strength: similarity,
              detected_by: 'semantic',
              resolution_hints: [],
              created_at: new Date().toISOString()
            });
          }
        }
      }
    }

    return conflicts;
  }

  private async detectGraphConflicts(_claims: AtomicClaim[]): Promise<Conflict[]> {
    const session = this.neo4jDriver.session();
    const conflicts: Conflict[] = [];

    try {
      // Find transitive conflicts via entity graph
      const result = await session.run(`
        MATCH path = (a:Claim)-[:ABOUT]->(e:Entity)<-[:ABOUT]-(b:Claim)
        WHERE a.id <> b.id
          AND a.predicate = b.predicate
          AND a.object <> b.object
        RETURN a, b, e
      `);

      for (const record of result.records) {
        const claimA = record.get('a').properties;
        const claimB = record.get('b').properties;

        conflicts.push({
          id: uuidv4(),
          claim_a: {
            id: claimA.id,
            document_id: claimA.document_id,
            text: claimA.original_text,
            confidence: claimA.confidence ?? 0.8
          },
          claim_b: {
            id: claimB.id,
            document_id: claimB.document_id,
            text: claimB.original_text,
            confidence: claimB.confidence ?? 0.8
          },
          conflict_type: 'value_conflict',
          strength: 0.9,
          detected_by: 'entity_graph',
          resolution_hints: ['Same entity, same property, different values'],
          created_at: new Date().toISOString()
        });
      }
    } catch {
      // If graph query fails, continue without graph conflicts
    } finally {
      await session.close();
    }

    return conflicts;
  }

  private detectValueConflicts(claims: AtomicClaim[]): Conflict[] {
    const conflicts: Conflict[] = [];

    // Group claims by subject + predicate
    const claimGroups = new Map<string, AtomicClaim[]>();

    for (const claim of claims) {
      const key = `${claim.subject.toLowerCase()}|${claim.predicate.toLowerCase()}`;
      const group = claimGroups.get(key) || [];
      group.push(claim);
      claimGroups.set(key, group);
    }

    // Find conflicts within groups
    for (const [, group] of claimGroups) {
      if (group.length < 2) continue;

      // Extract unique values
      const values = new Set(group.map(c => c.object.toLowerCase()));
      if (values.size > 1) {
        // Multiple different values for same subject + predicate
        for (let i = 0; i < group.length; i++) {
          for (let j = i + 1; j < group.length; j++) {
            if (group[i].object.toLowerCase() !== group[j].object.toLowerCase()) {
              conflicts.push({
                id: uuidv4(),
                claim_a: {
                  id: group[i].id,
                  document_id: group[i].document_id || group[i].source_section_id,
                  text: group[i].original_text,
                  confidence: group[i].confidence
                },
                claim_b: {
                  id: group[j].id,
                  document_id: group[j].document_id || group[j].source_section_id,
                  text: group[j].original_text,
                  confidence: group[j].confidence
                },
                conflict_type: 'value_conflict',
                strength: 0.95,
                detected_by: 'value_extraction',
                resolution_hints: [`Different values for ${group[i].subject}.${group[i].predicate}`],
                created_at: new Date().toISOString()
              });
            }
          }
        }
      }
    }

    return conflicts;
  }

  private async verifyConflictsWithLLM(conflicts: Conflict[]): Promise<Conflict[]> {
    const verified: Conflict[] = [];

    for (const conflict of conflicts) {
      try {
        const response = await this.llmService.generate({
          model: 'llama3.1:8b',
          prompt: `
Analyze if these two claims are truly in conflict:

CLAIM A: "${conflict.claim_a.text}"
CLAIM B: "${conflict.claim_b.text}"

Consider:
1. Are they about the same thing?
2. Could both be true in different contexts?
3. Is one more specific than the other?
4. Is one a temporal update to the other?

Output JSON: {
  "is_conflict": boolean,
  "conflict_type": "direct_negation" | "value_conflict" | "temporal_conflict" | "scope_conflict" | "implication_conflict" | "not_a_conflict",
  "explanation": string,
  "resolution_hints": string[]
}`,
          format: 'json',
          options: { temperature: 0.1 }
        });

        const analysis = ConflictVerificationSchema.parse(JSON.parse(response));

        if (analysis.is_conflict) {
          verified.push({
            ...conflict,
            conflict_type: analysis.conflict_type === 'not_a_conflict'
              ? conflict.conflict_type
              : analysis.conflict_type as ConflictType,
            resolution_hints: analysis.resolution_hints
          });
        }
      } catch (error) {
        // If LLM verification fails, keep the conflict as-is
        if (error instanceof z.ZodError) {
          verified.push(conflict);
        } else {
          throw new LLMError(
            'llama3.1:8b',
            `Conflict verification failed: ${error instanceof Error ? error.message : 'Unknown error'}`
          );
        }
      }
    }

    return verified;
  }

  private deduplicateConflicts(conflicts: Conflict[]): Conflict[] {
    const seen = new Set<string>();
    const unique: Conflict[] = [];

    for (const conflict of conflicts) {
      // Create a normalized key for the conflict pair
      const key = [conflict.claim_a.id, conflict.claim_b.id].sort().join('|');

      if (!seen.has(key)) {
        seen.add(key);
        unique.push(conflict);
      }
    }

    return unique;
  }

  private cosineSimilarity(a: number[], b: number[]): number {
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

  /**
   * Get conflicts for specific document
   */
  async getConflictsForDocument(documentId: string, allConflicts: Conflict[]): Promise<Conflict[]> {
    return allConflicts.filter(
      c => c.claim_a.document_id === documentId || c.claim_b.document_id === documentId
    );
  }

  /**
   * Close the Neo4j driver connection
   */
  async close(): Promise<void> {
    await this.neo4jDriver.close();
  }
}
