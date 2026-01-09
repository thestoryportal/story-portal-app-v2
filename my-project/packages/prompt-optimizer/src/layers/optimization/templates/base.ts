/**
 * Base domain template interface and utilities.
 * Provides structure for domain-specific optimization strategies.
 */

import type { Domain, Change, ChangeType } from '../../../types/index.js';

/**
 * Domain template definition.
 */
export interface DomainTemplateConfig {
  /** Domain this template handles */
  domain: Domain;
  /** Description of the domain */
  description: string;
  /** Keywords that indicate this domain */
  keywords: string[];
  /** Enhancement strategies for this domain */
  enhancements: EnhancementStrategy[];
  /** Elements to always preserve in this domain */
  preservePatterns: RegExp[];
  /** Elements that indicate clarity (don't optimize) */
  clarityIndicators: string[];
  /** Common issues to fix in this domain */
  commonIssues: IssuePattern[];
  /** Maximum expansion ratio for this domain */
  maxExpansionRatio: number;
}

/**
 * Enhancement strategy for a domain.
 */
export interface EnhancementStrategy {
  /** Strategy name */
  name: string;
  /** When to apply this strategy */
  condition: (prompt: string) => boolean;
  /** How to enhance */
  apply: (prompt: string) => { enhanced: string; change: Change | null };
  /** Priority (higher = apply first) */
  priority: number;
}

/**
 * Issue pattern to fix.
 */
export interface IssuePattern {
  /** Pattern to match */
  pattern: RegExp;
  /** Replacement or fix function */
  fix: string | ((match: string) => string);
  /** Change type */
  changeType: ChangeType;
  /** Description of the fix */
  description: string;
}

/**
 * Base domain template class.
 */
export abstract class BaseDomainTemplate {
  protected config: DomainTemplateConfig;

  constructor(config: DomainTemplateConfig) {
    this.config = config;
  }

  /**
   * Get the domain this template handles.
   */
  getDomain(): Domain {
    return this.config.domain;
  }

  /**
   * Check if this template applies to a prompt.
   */
  matches(prompt: string): boolean {
    const lower = prompt.toLowerCase();
    return this.config.keywords.some((kw) => lower.includes(kw.toLowerCase()));
  }

  /**
   * Get match confidence for this domain.
   */
  getMatchConfidence(prompt: string): number {
    const lower = prompt.toLowerCase();
    let matchCount = 0;

    for (const keyword of this.config.keywords) {
      if (lower.includes(keyword.toLowerCase())) {
        matchCount++;
      }
    }

    return Math.min(1, matchCount / 3);
  }

  /**
   * Check if prompt has clarity indicators (should not be heavily optimized).
   */
  hasClarityIndicators(prompt: string): boolean {
    const lower = prompt.toLowerCase();
    return this.config.clarityIndicators.some((ci) =>
      lower.includes(ci.toLowerCase())
    );
  }

  /**
   * Extract elements that must be preserved.
   */
  extractPreservedElements(prompt: string): string[] {
    const preserved: string[] = [];

    for (const pattern of this.config.preservePatterns) {
      const matches = prompt.match(pattern);
      if (matches) {
        preserved.push(...matches);
      }
    }

    return [...new Set(preserved)];
  }

  /**
   * Apply domain-specific enhancements.
   */
  enhance(prompt: string): { enhanced: string; changes: Change[] } {
    let current = prompt;
    const changes: Change[] = [];

    // Sort strategies by priority (descending)
    const strategies = [...this.config.enhancements].sort(
      (a, b) => b.priority - a.priority
    );

    for (const strategy of strategies) {
      if (strategy.condition(current)) {
        const result = strategy.apply(current);
        if (result.change) {
          current = result.enhanced;
          changes.push(result.change);
        }
      }
    }

    return { enhanced: current, changes };
  }

  /**
   * Fix common issues in the prompt.
   */
  fixCommonIssues(prompt: string): { fixed: string; changes: Change[] } {
    let current = prompt;
    const changes: Change[] = [];

    for (const issue of this.config.commonIssues) {
      const matches = current.match(issue.pattern);
      if (matches) {
        for (const match of matches) {
          const fixed = typeof issue.fix === 'function'
            ? issue.fix(match)
            : match.replace(issue.pattern, issue.fix);

          if (fixed !== match) {
            current = current.replace(match, fixed);
            changes.push({
              type: issue.changeType,
              originalSegment: match,
              newSegment: fixed,
              reason: issue.description,
            });
          }
        }
      }
    }

    return { fixed: current, changes };
  }

  /**
   * Check if optimization result is within acceptable expansion ratio.
   */
  isAcceptableExpansion(original: string, optimized: string): boolean {
    const ratio = optimized.length / original.length;
    return ratio <= this.config.maxExpansionRatio;
  }

  /**
   * Generate domain-specific tip.
   */
  abstract generateTip(prompt: string): string;
}
