import { exec } from 'child_process';
import { promisify } from 'util';
import type { AtomicClaim, VerificationResult, VerificationSignal } from '../types.js';
import { LLMPipeline } from './llm-pipeline.js';

const execAsync = promisify(exec);

interface CodeAnalysisResult {
  matches: Array<{
    file: string;
    line: number;
    content: string;
  }>;
}

export class VerificationPipeline {
  private llm: LLMPipeline;

  constructor(llmPipeline: LLMPipeline) {
    this.llm = llmPipeline;
  }

  async verifyClaim(claim: AtomicClaim, codebasePath?: string): Promise<VerificationResult> {
    const results: VerificationSignal[] = [];

    // 1. Code verification (if applicable and codebase path provided)
    if (codebasePath && this.isCodeRelatedClaim(claim)) {
      const codeResult = await this.verifyAgainstCode(claim, codebasePath);
      results.push({ type: 'code', ...codeResult });
    }

    // 2. Self-consistency verification
    const consistencyResult = await this.llm.selfConsistencyVerify(
      this.buildVerificationPrompt(claim),
      5
    );
    results.push({
      type: 'consistency',
      confidence: consistencyResult.confidence,
      verdict: consistencyResult.answer,
      agreementRate: consistencyResult.agreementRate
    });

    // 3. Ensemble verification
    const ensembleResult = await this.llm.ensembleVote(
      this.buildVerificationPrompt(claim)
    );
    results.push({
      type: 'ensemble',
      confidence: ensembleResult.confidence,
      verdict: ensembleResult.verdict,
      votes: ensembleResult.votes
    });

    // 4. Debate verification (for low-confidence claims)
    if (claim.confidence < 0.8) {
      const debateResult = await this.llm.debate(
        claim.original_text,
        `Subject: ${claim.subject}\nPredicate: ${claim.predicate}\nObject: ${claim.object}`
      );
      results.push({
        type: 'debate',
        confidence: debateResult.confidence,
        verdict: debateResult.verdict,
        reasoning: debateResult.reasoning
      });
    }

    // Aggregate results
    return this.aggregateVerification(results);
  }

  private isCodeRelatedClaim(claim: AtomicClaim): boolean {
    const codeIndicators = [
      'function', 'class', 'method', 'variable', 'constant',
      'parameter', 'argument', 'return', 'type', 'interface',
      'import', 'export', 'module', 'component', 'hook',
      'config', 'setting', 'option', 'flag', 'value',
      'default', 'port', 'host', 'url', 'path'
    ];

    const claimText = `${claim.subject} ${claim.predicate} ${claim.object}`.toLowerCase();
    return codeIndicators.some(indicator => claimText.includes(indicator));
  }

  private async verifyAgainstCode(
    claim: AtomicClaim,
    codebasePath: string
  ): Promise<{ verified: boolean; confidence: number; evidence: string[] }> {
    // Extract potential values from claim
    const values = this.extractValues(claim);
    const evidence: string[] = [];
    let matches = 0;

    for (const value of values) {
      // Search codebase for value using grep
      const grepResult = await this.grepCodebase(codebasePath, value.toString());

      if (grepResult.matches.length > 0) {
        matches++;
        evidence.push(
          ...grepResult.matches.slice(0, 3).map(m => `${m.file}:${m.line}: ${m.content.trim()}`)
        );
      }
    }

    return {
      verified: matches > 0,
      confidence: values.length > 0 ? matches / values.length : 0,
      evidence
    };
  }

  private extractValues(claim: AtomicClaim): Array<string | number> {
    const values: Array<string | number> = [];

    // Extract numbers
    const numbers = claim.object.match(/\d+(\.\d+)?/g);
    if (numbers) {
      values.push(...numbers.map(n => n.includes('.') ? parseFloat(n) : parseInt(n, 10)));
    }

    // Extract quoted strings
    const quoted = claim.object.match(/["']([^"']+)["']/g);
    if (quoted) {
      values.push(...quoted.map(q => q.slice(1, -1)));
    }

    // Extract identifiers (camelCase, snake_case, SCREAMING_CASE)
    const identifiers = claim.object.match(/[a-zA-Z_][a-zA-Z0-9_]*/g);
    if (identifiers) {
      values.push(...identifiers.filter(id => id.length > 2));
    }

    // If no specific values extracted, use the whole object
    if (values.length === 0 && claim.object.trim()) {
      values.push(claim.object.trim());
    }

    return values;
  }

  private async grepCodebase(codebasePath: string, pattern: string): Promise<CodeAnalysisResult> {
    try {
      // Escape special regex characters
      const escapedPattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

      const { stdout } = await execAsync(
        `grep -rn --include="*.ts" --include="*.js" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.md" "${escapedPattern}" "${codebasePath}" 2>/dev/null | head -20`,
        { maxBuffer: 1024 * 1024 }
      );

      const matches = stdout.split('\n')
        .filter(line => line.trim())
        .map(line => {
          const colonIndex = line.indexOf(':');
          const secondColonIndex = line.indexOf(':', colonIndex + 1);

          if (colonIndex === -1 || secondColonIndex === -1) {
            return null;
          }

          return {
            file: line.slice(0, colonIndex),
            line: parseInt(line.slice(colonIndex + 1, secondColonIndex), 10),
            content: line.slice(secondColonIndex + 1)
          };
        })
        .filter((m): m is NonNullable<typeof m> => m !== null);

      return { matches };
    } catch {
      return { matches: [] };
    }
  }

  private buildVerificationPrompt(claim: AtomicClaim): string {
    return `
Verify if this claim is likely to be accurate based on your knowledge.

Claim: "${claim.original_text}"
- Subject: ${claim.subject}
- Predicate: ${claim.predicate}
- Object: ${claim.object}
${claim.qualifier ? `- Qualifier: ${claim.qualifier}` : ''}

Consider:
1. Is this a plausible technical claim?
2. Does the object value make sense for the subject and predicate?
3. Are there any obvious errors or contradictions?

Output JSON: {
  "verdict": "verified" | "uncertain" | "likely_wrong",
  "confidence": number (0-1),
  "reasoning": string
}`;
  }

  private aggregateVerification(signals: VerificationSignal[]): VerificationResult {
    // Weighted aggregation
    const weights: Record<string, number> = {
      code: 0.4,
      consistency: 0.2,
      ensemble: 0.2,
      debate: 0.2
    };

    let totalWeight = 0;
    let weightedConfidence = 0;
    let verified = true;

    for (const signal of signals) {
      const weight = weights[signal.type] || 0.1;
      totalWeight += weight;
      weightedConfidence += weight * signal.confidence;

      // Code verification failure is strong negative signal
      if (signal.type === 'code' && signal.verified === false) {
        verified = false;
      }

      // Strong negative verdict from LLM is also concerning
      if (signal.verdict === 'refuted' || signal.verdict === 'likely_wrong') {
        verified = false;
      }
    }

    const finalConfidence = totalWeight > 0 ? weightedConfidence / totalWeight : 0;

    return {
      verified: verified && finalConfidence > 0.7,
      confidence: finalConfidence,
      signals,
      should_flag_for_human: finalConfidence < 0.6 || !verified
    };
  }

  /**
   * Batch verify multiple claims
   */
  async verifyBatch(
    claims: AtomicClaim[],
    codebasePath?: string,
    concurrency: number = 3
  ): Promise<Map<string, VerificationResult>> {
    const results = new Map<string, VerificationResult>();
    const queue = [...claims];
    const inProgress: Promise<void>[] = [];

    const processClaim = async (claim: AtomicClaim) => {
      const result = await this.verifyClaim(claim, codebasePath);
      results.set(claim.id, result);
    };

    while (queue.length > 0 || inProgress.length > 0) {
      while (inProgress.length < concurrency && queue.length > 0) {
        const claim = queue.shift()!;
        const promise = processClaim(claim).then(() => {
          const index = inProgress.indexOf(promise);
          if (index > -1) {
            inProgress.splice(index, 1);
          }
        });
        inProgress.push(promise);
      }

      if (inProgress.length > 0) {
        await Promise.race(inProgress);
      }
    }

    return results;
  }
}
