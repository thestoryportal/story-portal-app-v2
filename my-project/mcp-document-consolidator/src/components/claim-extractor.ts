import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import type { AtomicClaim } from '../types.js';
import { LLMError } from '../errors.js';

const ExtractionResponseSchema = z.object({
  claims: z.array(z.object({
    original_text: z.string(),
    subject: z.string(),
    predicate: z.string(),
    object: z.string(),
    qualifier: z.string().optional(),
    confidence: z.number().min(0).max(1),
    start_char: z.number().int(),
    end_char: z.number().int()
  }))
});

export interface LLMService {
  generate(params: {
    model?: string;
    prompt: string;
    format?: 'json';
    options?: Record<string, unknown>;
  }): Promise<string>;
}

export class ClaimExtractor {
  private llmService: LLMService;
  private model: string;

  constructor(llmService: LLMService, model: string = 'llama3.1:8b') {
    this.llmService = llmService;
    this.model = model;
  }

  async extract(sectionContent: string, sectionId: string): Promise<AtomicClaim[]> {
    if (!sectionContent.trim()) {
      return [];
    }

    const systemPrompt = `You are a precise claim extractor. Extract all factual claims from the text.
Each claim must be:
- Atomic (single fact, not compound)
- Verifiable (can be checked against code/config/docs)
- Complete (subject + predicate + object)

Examples of good extraction:
Text: "The animation uses 8 bolts with 150px length"
Claims:
1. Subject: "animation", Predicate: "uses bolt count", Object: "8"
2. Subject: "animation bolts", Predicate: "have length", Object: "150px"

Do NOT include:
- Opinions or subjective statements
- Vague claims that cannot be verified
- Compound claims (split them)

Output JSON format:
{
  "claims": [
    {
      "original_text": "exact text from source",
      "subject": "the entity",
      "predicate": "the property or relationship",
      "object": "the value",
      "qualifier": "optional conditions",
      "confidence": 0.0-1.0,
      "start_char": 0,
      "end_char": 10
    }
  ]
}`;

    try {
      const response = await this.llmService.generate({
        model: this.model,
        prompt: `${systemPrompt}\n\nExtract claims from this text:\n\n${sectionContent}`,
        format: 'json',
        options: { temperature: 0.1 }
      });

      const parsed = ExtractionResponseSchema.parse(JSON.parse(response));

      return parsed.claims.map(claim => ({
        id: uuidv4(),
        original_text: claim.original_text,
        subject: claim.subject,
        predicate: claim.predicate,
        object: claim.object,
        qualifier: claim.qualifier,
        confidence: claim.confidence,
        source_section_id: sectionId,
        source_span: {
          start: claim.start_char,
          end: claim.end_char
        }
      }));
    } catch (error) {
      if (error instanceof z.ZodError) {
        throw new LLMError(this.model, `Failed to parse LLM response: ${error.message}`);
      }
      throw new LLMError(this.model, `Claim extraction failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Extract claims from multiple sections in batch
   */
  async extractBatch(
    sections: Array<{ id: string; content: string }>,
    concurrency: number = 3
  ): Promise<Map<string, AtomicClaim[]>> {
    const results = new Map<string, AtomicClaim[]>();
    const queue = [...sections];
    const inProgress: Promise<void>[] = [];

    const processSection = async (section: { id: string; content: string }) => {
      const claims = await this.extract(section.content, section.id);
      results.set(section.id, claims);
    };

    while (queue.length > 0 || inProgress.length > 0) {
      // Start new tasks up to concurrency limit
      while (inProgress.length < concurrency && queue.length > 0) {
        const section = queue.shift()!;
        const promise = processSection(section).then(() => {
          const index = inProgress.indexOf(promise);
          if (index > -1) {
            inProgress.splice(index, 1);
          }
        });
        inProgress.push(promise);
      }

      // Wait for at least one task to complete
      if (inProgress.length > 0) {
        await Promise.race(inProgress);
      }
    }

    return results;
  }

  /**
   * Validate extracted claims against patterns
   */
  validateClaims(claims: AtomicClaim[]): Array<{ claim: AtomicClaim; issues: string[] }> {
    const invalidClaims: Array<{ claim: AtomicClaim; issues: string[] }> = [];

    for (const claim of claims) {
      const issues: string[] = [];

      // Check for empty fields
      if (!claim.subject.trim()) {
        issues.push('Empty subject');
      }
      if (!claim.predicate.trim()) {
        issues.push('Empty predicate');
      }
      if (!claim.object.trim()) {
        issues.push('Empty object');
      }

      // Check for suspiciously low confidence
      if (claim.confidence < 0.3) {
        issues.push(`Very low confidence: ${claim.confidence}`);
      }

      // Check for compound claims (multiple predicates)
      if (claim.predicate.includes(' and ') || claim.predicate.includes(', ')) {
        issues.push('Possibly compound claim - may need splitting');
      }

      // Check for vague predicates
      const vaguePredicates = ['is', 'has', 'does', 'can'];
      if (vaguePredicates.includes(claim.predicate.toLowerCase())) {
        issues.push('Vague predicate - may be too general');
      }

      if (issues.length > 0) {
        invalidClaims.push({ claim, issues });
      }
    }

    return invalidClaims;
  }

  /**
   * Deduplicate claims based on semantic similarity
   */
  deduplicateClaims(claims: AtomicClaim[], threshold: number = 0.9): AtomicClaim[] {
    const unique: AtomicClaim[] = [];

    for (const claim of claims) {
      const claimKey = `${claim.subject}|${claim.predicate}|${claim.object}`.toLowerCase();
      const isDuplicate = unique.some(existing => {
        const existingKey = `${existing.subject}|${existing.predicate}|${existing.object}`.toLowerCase();
        return this.stringSimilarity(claimKey, existingKey) >= threshold;
      });

      if (!isDuplicate) {
        unique.push(claim);
      }
    }

    return unique;
  }

  private stringSimilarity(a: string, b: string): number {
    if (a === b) return 1;
    if (a.length === 0 || b.length === 0) return 0;

    const longer = a.length > b.length ? a : b;
    const shorter = a.length > b.length ? b : a;

    const longerLength = longer.length;
    const editDistance = this.levenshteinDistance(longer, shorter);

    return (longerLength - editDistance) / longerLength;
  }

  private levenshteinDistance(a: string, b: string): number {
    const matrix: number[][] = [];

    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i];
    }
    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    return matrix[b.length][a.length];
  }
}
