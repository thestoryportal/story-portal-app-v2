/**
 * Intent Verification layer for the prompt optimizer.
 * Ensures semantic similarity and element preservation.
 * Maps to spec section 5: Intent Verification System.
 */

import type {
  VerificationRequest,
  VerificationResponse,
  VerificationIssue,
  VerificationStatus,
  IssueSeverity,
  OptimizerApiClient,
} from '../types/index.js';
import {
  VERIFICATION_THRESHOLDS,
  PRESERVATION_THRESHOLDS,
} from '../constants/index.js';

/**
 * Intent verifier to check optimization quality.
 */
export class IntentVerifier {
  constructor(private apiClient: OptimizerApiClient) {}

  /**
   * Verify that the optimized prompt preserves intent.
   */
  async verify(request: VerificationRequest): Promise<VerificationResponse> {
    // First, do fast local checks
    const localResult = this.localVerification(request);

    // If local check fails badly, don't bother with API
    if (localResult.status === 'REJECTED' && localResult.similarityScore < 0.5) {
      return localResult;
    }

    // Use API for semantic verification
    try {
      const apiResult = await this.apiClient.verify(request);

      // Blend local and API results
      return this.blendResults(localResult, apiResult);
    } catch {
      // Fall back to local result if API fails
      return localResult;
    }
  }

  /**
   * Perform fast local verification.
   */
  private localVerification(request: VerificationRequest): VerificationResponse {
    const issues: VerificationIssue[] = [];

    // Check element preservation
    const preservedRatio = this.calculatePreservedRatio(request);
    if (preservedRatio < PRESERVATION_THRESHOLDS.WARN) {
      issues.push({
        type: 'LOST_CONSTRAINT',
        severity: preservedRatio < PRESERVATION_THRESHOLDS.WARN * 0.8 ? 'HIGH' : 'MEDIUM',
        description: `Only ${(preservedRatio * 100).toFixed(0)}% of required elements preserved`,
      });
    }

    // Check for added assumptions
    const addedAssumptions = this.detectAddedAssumptions(request);
    issues.push(...addedAssumptions);

    // Check for scope changes
    const scopeChanges = this.detectScopeChanges(request);
    issues.push(...scopeChanges);

    // Check for intent drift
    const similarityScore = this.calculateLocalSimilarity(request);
    if (similarityScore < VERIFICATION_THRESHOLDS.LOW) {
      issues.push({
        type: 'INTENT_DRIFT',
        severity: similarityScore < 0.5 ? 'HIGH' : 'MEDIUM',
        description: `Significant semantic drift detected (${(similarityScore * 100).toFixed(0)}% similarity)`,
      });
    }

    // Determine status
    const status = this.determineStatus(similarityScore, preservedRatio, issues);

    return {
      status,
      similarityScore,
      preservedRatio,
      issues,
      recommendation: this.generateRecommendation(status, issues),
    };
  }

  /**
   * Calculate ratio of preserved elements.
   */
  private calculatePreservedRatio(request: VerificationRequest): number {
    if (request.preservedElements.length === 0) {
      return 1.0; // Nothing to preserve
    }

    let preserved = 0;
    const optimizedLower = request.optimized.toLowerCase();

    for (const element of request.preservedElements) {
      // Normalize whitespace for comparison
      const normalized = element.toLowerCase().replace(/\s+/g, ' ').trim();
      const optimizedNormalized = optimizedLower.replace(/\s+/g, ' ');

      if (optimizedNormalized.includes(normalized)) {
        preserved++;
      }
    }

    return preserved / request.preservedElements.length;
  }

  /**
   * Detect potentially added assumptions.
   */
  private detectAddedAssumptions(request: VerificationRequest): VerificationIssue[] {
    const issues: VerificationIssue[] = [];
    const original = request.original.toLowerCase();
    const optimized = request.optimized.toLowerCase();

    // Check for added framework/language assumptions
    const techAssumptions = [
      { term: 'typescript', indicator: 'ts' },
      { term: 'javascript', indicator: 'js' },
      { term: 'react', indicator: 'react' },
      { term: 'vue', indicator: 'vue' },
      { term: 'angular', indicator: 'angular' },
      { term: 'python', indicator: 'py' },
      { term: 'node.js', indicator: 'node' },
    ];

    for (const { term, indicator } of techAssumptions) {
      // If term appears in optimized but not in original (and not implied by context)
      if (optimized.includes(term) && !original.includes(term) && !original.includes(indicator)) {
        issues.push({
          type: 'ADDED_ASSUMPTION',
          severity: 'MEDIUM',
          description: `Added technology assumption: "${term}" not present in original`,
        });
      }
    }

    // Check for added requirements
    const requirementIndicators = [
      'must', 'should', 'need to', 'have to', 'required', 'important',
    ];

    for (const indicator of requirementIndicators) {
      const originalCount = (original.match(new RegExp(indicator, 'g')) ?? []).length;
      const optimizedCount = (optimized.match(new RegExp(indicator, 'g')) ?? []).length;

      if (optimizedCount > originalCount + 1) {
        issues.push({
          type: 'ADDED_ASSUMPTION',
          severity: 'LOW',
          description: `Added requirement language ("${indicator}") not in original`,
        });
        break; // Only flag once
      }
    }

    return issues;
  }

  /**
   * Detect scope changes.
   */
  private detectScopeChanges(request: VerificationRequest): VerificationIssue[] {
    const issues: VerificationIssue[] = [];
    const original = request.original.toLowerCase();
    const optimized = request.optimized.toLowerCase();

    // Check for scope expansion
    const scopeExpanders = ['all', 'entire', 'complete', 'whole', 'full'];
    for (const expander of scopeExpanders) {
      const originalCount = (original.match(new RegExp(`\\b${expander}\\b`, 'g')) ?? []).length;
      const optimizedCount = (optimized.match(new RegExp(`\\b${expander}\\b`, 'g')) ?? []).length;

      if (optimizedCount > originalCount) {
        issues.push({
          type: 'CHANGED_SCOPE',
          severity: 'MEDIUM',
          description: `Scope may have been expanded (added "${expander}")`,
        });
        break;
      }
    }

    // Check for scope reduction
    const scopeReducers = ['only', 'just', 'single', 'one', 'specific'];
    for (const reducer of scopeReducers) {
      const originalCount = (original.match(new RegExp(`\\b${reducer}\\b`, 'g')) ?? []).length;
      const optimizedCount = (optimized.match(new RegExp(`\\b${reducer}\\b`, 'g')) ?? []).length;

      if (optimizedCount > originalCount && originalCount === 0) {
        issues.push({
          type: 'CHANGED_SCOPE',
          severity: 'LOW',
          description: `Scope may have been narrowed (added "${reducer}")`,
        });
        break;
      }
    }

    // Check for lost negative constraints
    const negativeTerms = ["don't", 'do not', 'avoid', 'never', 'without', 'except'];
    for (const term of negativeTerms) {
      if (original.includes(term) && !optimized.includes(term)) {
        issues.push({
          type: 'LOST_CONSTRAINT',
          severity: 'HIGH',
          description: `Lost negative constraint: "${term}" removed from prompt`,
        });
      }
    }

    return issues;
  }

  /**
   * Calculate local similarity score using simple heuristics.
   */
  private calculateLocalSimilarity(request: VerificationRequest): number {
    const original = request.original.toLowerCase();
    const optimized = request.optimized.toLowerCase();

    // Calculate word overlap (Jaccard similarity)
    const originalWords = new Set(original.split(/\s+/).filter((w) => w.length > 2));
    const optimizedWords = new Set(optimized.split(/\s+/).filter((w) => w.length > 2));

    const intersection = new Set([...originalWords].filter((w) => optimizedWords.has(w)));
    const union = new Set([...originalWords, ...optimizedWords]);

    const jaccardSimilarity = union.size > 0 ? intersection.size / union.size : 0;

    // Calculate key phrase preservation
    const keyPhrases = this.extractKeyPhrases(request.original);
    let phrasesPreserved = 0;
    for (const phrase of keyPhrases) {
      if (optimized.includes(phrase.toLowerCase())) {
        phrasesPreserved++;
      }
    }
    const phraseScore = keyPhrases.length > 0 ? phrasesPreserved / keyPhrases.length : 1;

    // Combine scores with weights
    return jaccardSimilarity * 0.4 + phraseScore * 0.6;
  }

  /**
   * Extract key phrases from text.
   */
  private extractKeyPhrases(text: string): string[] {
    const phrases: string[] = [];

    // Extract quoted phrases
    const quoted = text.match(/"[^"]+"|'[^']+'/g);
    if (quoted) {
      phrases.push(...quoted.map((q) => q.slice(1, -1)));
    }

    // Extract code references
    const codeRefs = text.match(/`[^`]+`/g);
    if (codeRefs) {
      phrases.push(...codeRefs.map((c) => c.slice(1, -1)));
    }

    // Extract capitalized terms (proper nouns, technical terms)
    const capitalizedTerms = text.match(/\b[A-Z][a-zA-Z0-9]+\b/g);
    if (capitalizedTerms) {
      phrases.push(...capitalizedTerms);
    }

    return [...new Set(phrases)];
  }

  /**
   * Determine verification status.
   */
  private determineStatus(
    similarity: number,
    preservation: number,
    issues: VerificationIssue[]
  ): VerificationStatus {
    const highIssues = issues.filter((i) => i.severity === 'HIGH').length;
    const mediumIssues = issues.filter((i) => i.severity === 'MEDIUM').length;

    // REJECTED if any HIGH issues or very low scores
    if (highIssues > 0 || similarity < VERIFICATION_THRESHOLDS.REJECTED || preservation < 0.7) {
      return 'REJECTED';
    }

    // WARN if medium issues or borderline scores
    if (mediumIssues > 0 || similarity < VERIFICATION_THRESHOLDS.MEDIUM || preservation < PRESERVATION_THRESHOLDS.VERIFIED) {
      return 'WARN';
    }

    return 'VERIFIED';
  }

  /**
   * Generate recommendation based on status.
   */
  private generateRecommendation(
    status: VerificationStatus,
    issues: VerificationIssue[]
  ): string {
    switch (status) {
      case 'VERIFIED':
        return 'Optimization verified. Intent and constraints preserved.';
      case 'WARN':
        return `Optimization has minor concerns: ${issues.map((i) => i.description).join('; ')}. Review recommended.`;
      case 'REJECTED':
        return `Optimization rejected due to: ${issues.filter((i) => i.severity === 'HIGH').map((i) => i.description).join('; ')}. Falling back to clarification.`;
    }
  }

  /**
   * Blend local and API verification results.
   */
  private blendResults(
    local: VerificationResponse,
    api: VerificationResponse
  ): VerificationResponse {
    // Combine similarity scores with preference for lower (more conservative)
    const similarityScore = Math.min(local.similarityScore, api.similarityScore);
    const preservedRatio = Math.min(local.preservedRatio, api.preservedRatio);

    // Merge issues, preferring higher severity
    const issueMap = new Map<string, VerificationIssue>();
    for (const issue of [...local.issues, ...api.issues]) {
      const key = `${issue.type}:${issue.description.substring(0, 50)}`;
      const existing = issueMap.get(key);
      if (!existing || this.severityRank(issue.severity) > this.severityRank(existing.severity)) {
        issueMap.set(key, issue);
      }
    }
    const issues = Array.from(issueMap.values());

    // Determine final status (prefer more conservative)
    const status = this.mostConservativeStatus(local.status, api.status);

    return {
      status,
      similarityScore,
      preservedRatio,
      issues,
      recommendation: this.generateRecommendation(status, issues),
    };
  }

  /**
   * Get severity rank for comparison.
   */
  private severityRank(severity: IssueSeverity): number {
    switch (severity) {
      case 'HIGH':
        return 3;
      case 'MEDIUM':
        return 2;
      case 'LOW':
        return 1;
    }
  }

  /**
   * Get the most conservative status.
   */
  private mostConservativeStatus(
    a: VerificationStatus,
    b: VerificationStatus
  ): VerificationStatus {
    const rank = { REJECTED: 0, WARN: 1, VERIFIED: 2 };
    return rank[a] < rank[b] ? a : b;
  }
}

/** Create an intent verifier */
export function createIntentVerifier(apiClient: OptimizerApiClient): IntentVerifier {
  return new IntentVerifier(apiClient);
}
