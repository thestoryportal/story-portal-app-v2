/**
 * Pass 2 (Self-Critique) for the prompt optimizer.
 * Reviews optimization quality and intent preservation.
 * Maps to spec section 4.3.
 */

import type {
  PassOneOutput,
  PassTwoOutput,
  CritiqueResult,
  CritiqueIssue,
  Severity,
  OptimizerApiClient,
} from '../../types/index.js';

/**
 * Pass Two optimizer for self-critique.
 */
export class PassTwoOptimizer {
  constructor(private apiClient: OptimizerApiClient) {}

  /**
   * Execute pass two self-critique.
   */
  async critique(
    original: string,
    passOneOutput: PassOneOutput
  ): Promise<PassTwoOutput> {
    const startTime = Date.now();

    // First, perform local critique
    const localCritique = this.localCritique(original, passOneOutput);

    // If local critique finds major issues, skip API call
    if (localCritique.critiqueResult === 'REJECT') {
      return {
        ...localCritique,
        latencyMs: Date.now() - startTime,
      };
    }

    // Use API for deeper critique
    try {
      const apiCritique = await this.apiCritique(original, passOneOutput);
      return this.blendCritiques(localCritique, apiCritique, Date.now() - startTime);
    } catch {
      // Fall back to local critique on API failure
      return {
        ...localCritique,
        latencyMs: Date.now() - startTime,
      };
    }
  }

  /**
   * Perform local critique without API.
   */
  private localCritique(
    original: string,
    passOneOutput: PassOneOutput
  ): Omit<PassTwoOutput, 'latencyMs'> {
    const issues: CritiqueIssue[] = [];

    // Check 1: Intent preservation
    const intentScore = this.calculateIntentScore(original, passOneOutput.optimizedPrompt);

    if (intentScore < 0.7) {
      issues.push({
        description: 'Significant intent drift detected',
        severity: 'HIGH',
      });
    } else if (intentScore < 0.85) {
      issues.push({
        description: 'Minor intent drift detected',
        severity: 'MEDIUM',
      });
    }

    // Check 2: Over-specification
    const overSpecification = this.detectOverSpecification(original, passOneOutput);
    issues.push(...overSpecification);

    // Check 3: Length bloat
    const lengthRatio = passOneOutput.optimizedPrompt.length / original.length;
    if (lengthRatio > 2.5) {
      issues.push({
        description: `Optimization increased length by ${((lengthRatio - 1) * 100).toFixed(0)}%`,
        severity: lengthRatio > 3 ? 'HIGH' : 'MEDIUM',
      });
    }

    // Check 4: Lost elements
    const lostElements = this.findLostElements(original, passOneOutput);
    issues.push(...lostElements);

    // Check 5: Hallucinated context
    const hallucinations = this.detectHallucinations(original, passOneOutput);
    issues.push(...hallucinations);

    // Determine result
    const critiqueResult = this.determineCritiqueResult(intentScore, issues);

    // Generate refinements
    const refinementsNeeded = this.generateRefinements(issues);

    // Calculate confidence adjustment
    const confidenceAdjustment = this.calculateConfidenceAdjustment(issues);

    return {
      critiqueResult,
      intentPreservationScore: intentScore,
      issuesFound: issues,
      refinementsNeeded,
      confidenceAdjustment,
    };
  }

  /**
   * Calculate intent preservation score.
   */
  private calculateIntentScore(original: string, optimized: string): number {
    const originalLower = original.toLowerCase();
    const optimizedLower = optimized.toLowerCase();

    // Word overlap
    const originalWords = new Set(originalLower.split(/\s+/).filter((w) => w.length > 2));
    const optimizedWords = new Set(optimizedLower.split(/\s+/).filter((w) => w.length > 2));

    const intersection = new Set([...originalWords].filter((w) => optimizedWords.has(w)));
    const wordOverlap = originalWords.size > 0 ? intersection.size / originalWords.size : 1;

    // Key phrase preservation
    const keyPhrases = this.extractKeyPhrases(original);
    let phrasesPreserved = 0;
    for (const phrase of keyPhrases) {
      if (optimizedLower.includes(phrase.toLowerCase())) {
        phrasesPreserved++;
      }
    }
    const phraseScore = keyPhrases.length > 0 ? phrasesPreserved / keyPhrases.length : 1;

    // Action verb alignment
    const originalActions = this.extractActionVerbs(original);
    const optimizedActions = this.extractActionVerbs(optimized);
    const actionMatch = originalActions.length > 0
      ? optimizedActions.filter((a) => originalActions.includes(a)).length / originalActions.length
      : 1;

    return wordOverlap * 0.3 + phraseScore * 0.5 + actionMatch * 0.2;
  }

  /**
   * Extract key phrases from text.
   */
  private extractKeyPhrases(text: string): string[] {
    const phrases: string[] = [];

    // Quoted text
    const quoted = text.match(/"[^"]+"|'[^']+'/g);
    if (quoted) phrases.push(...quoted.map((q) => q.slice(1, -1)));

    // Code references
    const code = text.match(/`[^`]+`/g);
    if (code) phrases.push(...code.map((c) => c.slice(1, -1)));

    // Proper nouns
    const proper = text.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g);
    if (proper) phrases.push(...proper);

    return [...new Set(phrases)];
  }

  /**
   * Extract action verbs from text.
   */
  private extractActionVerbs(text: string): string[] {
    const actionVerbs = [
      'create', 'write', 'implement', 'add', 'update', 'modify', 'delete', 'remove',
      'fix', 'debug', 'refactor', 'optimize', 'explain', 'describe', 'analyze',
      'compare', 'review', 'test', 'deploy', 'build', 'configure', 'install',
    ];

    const lower = text.toLowerCase();
    return actionVerbs.filter((verb) => lower.includes(verb));
  }

  /**
   * Detect over-specification.
   */
  private detectOverSpecification(
    original: string,
    passOneOutput: PassOneOutput
  ): CritiqueIssue[] {
    const issues: CritiqueIssue[] = [];
    const optimized = passOneOutput.optimizedPrompt.toLowerCase();
    const originalLower = original.toLowerCase();

    // Check for added specificity indicators not in original
    const specificityIndicators = [
      'specifically', 'exactly', 'precisely', 'must', 'should', 'need to',
      'required', 'necessary', 'important', 'critical', 'essential',
    ];

    let addedIndicators = 0;
    for (const indicator of specificityIndicators) {
      const origCount = (originalLower.match(new RegExp(indicator, 'g')) ?? []).length;
      const optCount = (optimized.match(new RegExp(indicator, 'g')) ?? []).length;
      if (optCount > origCount) {
        addedIndicators += optCount - origCount;
      }
    }

    if (addedIndicators > 3) {
      issues.push({
        description: 'Optimization may be over-specified with added constraints',
        severity: addedIndicators > 5 ? 'MEDIUM' : 'LOW',
      });
    }

    return issues;
  }

  /**
   * Find lost elements.
   */
  private findLostElements(
    original: string,
    passOneOutput: PassOneOutput
  ): CritiqueIssue[] {
    const issues: CritiqueIssue[] = [];
    const optimized = passOneOutput.optimizedPrompt.toLowerCase();

    // Check for lost negative constraints
    const negativePatterns = ["don't", 'do not', 'avoid', 'never', 'without', 'except', 'not'];
    for (const pattern of negativePatterns) {
      if (original.toLowerCase().includes(pattern) && !optimized.includes(pattern)) {
        issues.push({
          description: `Lost negative constraint: "${pattern}" removed from prompt`,
          severity: 'HIGH',
        });
      }
    }

    // Check for lost preserved elements
    for (const element of passOneOutput.preservedElements) {
      const normalized = element.toLowerCase().replace(/\s+/g, ' ').trim();
      if (!optimized.replace(/\s+/g, ' ').includes(normalized)) {
        issues.push({
          description: `Required element not preserved: "${element.substring(0, 50)}..."`,
          severity: 'HIGH',
        });
      }
    }

    return issues;
  }

  /**
   * Detect hallucinated context.
   */
  private detectHallucinations(
    original: string,
    passOneOutput: PassOneOutput
  ): CritiqueIssue[] {
    const issues: CritiqueIssue[] = [];
    const optimized = passOneOutput.optimizedPrompt.toLowerCase();
    const originalLower = original.toLowerCase();

    // Check for added technology assumptions
    const technologies = [
      'react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt',
      'typescript', 'javascript', 'python', 'java', 'rust', 'go',
      'node.js', 'deno', 'bun', 'express', 'fastapi', 'django', 'flask',
      'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
      'docker', 'kubernetes', 'aws', 'gcp', 'azure',
    ];

    for (const tech of technologies) {
      if (optimized.includes(tech) && !originalLower.includes(tech)) {
        // Check if it's in the changes (explicit addition)
        const wasAddedExplicitly = passOneOutput.changesMade.some(
          (c) => c.type === 'ADD_CONTEXT' && c.newSegment.toLowerCase().includes(tech)
        );

        if (!wasAddedExplicitly) {
          issues.push({
            description: `Potentially hallucinated technology: "${tech}" not in original`,
            severity: 'MEDIUM',
          });
        }
      }
    }

    return issues;
  }

  /**
   * Determine critique result.
   */
  private determineCritiqueResult(
    intentScore: number,
    issues: CritiqueIssue[]
  ): CritiqueResult {
    const highIssues = issues.filter((i) => i.severity === 'HIGH').length;
    const mediumIssues = issues.filter((i) => i.severity === 'MEDIUM').length;

    // REJECT if any HIGH issues or very low intent score
    if (highIssues > 0 || intentScore < 0.7) {
      return 'REJECT';
    }

    // REFINE if medium issues or borderline intent
    if (mediumIssues > 0 || intentScore < 0.85) {
      return 'REFINE';
    }

    return 'ACCEPT';
  }

  /**
   * Generate refinement suggestions.
   */
  private generateRefinements(issues: CritiqueIssue[]): string[] {
    const refinements: string[] = [];

    for (const issue of issues) {
      if (issue.severity === 'HIGH' || issue.severity === 'MEDIUM') {
        if (issue.description.includes('negative constraint')) {
          refinements.push('Restore the lost negative constraint');
        } else if (issue.description.includes('element not preserved')) {
          refinements.push('Ensure all required elements are preserved');
        } else if (issue.description.includes('over-specified')) {
          refinements.push('Remove unnecessary constraints');
        } else if (issue.description.includes('hallucinated')) {
          refinements.push('Remove assumed technology not in original');
        } else if (issue.description.includes('length')) {
          refinements.push('Reduce length while preserving key information');
        } else if (issue.description.includes('intent drift')) {
          refinements.push('Realign with original intent');
        }
      }
    }

    return [...new Set(refinements)];
  }

  /**
   * Calculate confidence adjustment.
   */
  private calculateConfidenceAdjustment(issues: CritiqueIssue[]): number {
    let adjustment = 0;

    for (const issue of issues) {
      switch (issue.severity) {
        case 'HIGH':
          adjustment -= 0.15;
          break;
        case 'MEDIUM':
          adjustment -= 0.08;
          break;
        case 'LOW':
          adjustment -= 0.03;
          break;
      }
    }

    // Cap adjustment
    return Math.max(-0.2, Math.min(0.1, adjustment));
  }

  /**
   * Use API for deeper critique.
   */
  private async apiCritique(
    original: string,
    passOneOutput: PassOneOutput
  ): Promise<Omit<PassTwoOutput, 'latencyMs'>> {
    // For now, return a stub - actual API implementation would go here
    const result = await this.apiClient.verify({
      original,
      optimized: passOneOutput.optimizedPrompt,
      preservedElements: passOneOutput.preservedElements,
    });

    return {
      critiqueResult: result.status === 'VERIFIED' ? 'ACCEPT' :
        result.status === 'WARN' ? 'REFINE' : 'REJECT',
      intentPreservationScore: result.similarityScore,
      issuesFound: result.issues.map((i) => ({
        description: i.description,
        severity: i.severity as Severity,
      })),
      refinementsNeeded: result.issues
        .filter((i) => i.severity !== 'LOW')
        .map((i) => `Address: ${i.description}`),
      confidenceAdjustment: result.status === 'VERIFIED' ? 0.05 :
        result.status === 'WARN' ? -0.05 : -0.15,
    };
  }

  /**
   * Blend local and API critiques.
   */
  private blendCritiques(
    local: Omit<PassTwoOutput, 'latencyMs'>,
    api: Omit<PassTwoOutput, 'latencyMs'>,
    latencyMs: number
  ): PassTwoOutput {
    // Use the more conservative result
    const critiqueResult = this.moreConservative(local.critiqueResult, api.critiqueResult);

    // Merge issues
    const allIssues = [...local.issuesFound, ...api.issuesFound];
    const uniqueIssues = this.deduplicateIssues(allIssues);

    // Use lower intent score
    const intentPreservationScore = Math.min(
      local.intentPreservationScore,
      api.intentPreservationScore
    );

    // Merge refinements
    const refinementsNeeded = [...new Set([
      ...local.refinementsNeeded,
      ...api.refinementsNeeded,
    ])];

    // Average confidence adjustment
    const confidenceAdjustment = (local.confidenceAdjustment + api.confidenceAdjustment) / 2;

    return {
      critiqueResult,
      intentPreservationScore,
      issuesFound: uniqueIssues,
      refinementsNeeded,
      confidenceAdjustment,
      latencyMs,
    };
  }

  /**
   * Get more conservative critique result.
   */
  private moreConservative(a: CritiqueResult, b: CritiqueResult): CritiqueResult {
    const rank = { REJECT: 0, REFINE: 1, ACCEPT: 2 };
    return rank[a] < rank[b] ? a : b;
  }

  /**
   * Deduplicate issues.
   */
  private deduplicateIssues(issues: CritiqueIssue[]): CritiqueIssue[] {
    const seen = new Set<string>();
    return issues.filter((issue) => {
      const key = `${issue.severity}:${issue.description.substring(0, 50)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}

/** Create a pass two optimizer */
export function createPassTwoOptimizer(apiClient: OptimizerApiClient): PassTwoOptimizer {
  return new PassTwoOptimizer(apiClient);
}
