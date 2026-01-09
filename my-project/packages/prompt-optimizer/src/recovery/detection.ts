/**
 * Detection system for identifying problematic optimizations.
 * Implements "made it worse" detection from spec section 6.
 */

import type { Change, Complexity } from '../types/index.js';

/**
 * Detection result.
 */
export interface DetectionResult {
  /** Whether the optimization may have degraded quality */
  mayCauseDegradation: boolean;
  /** Confidence in the detection */
  confidence: number;
  /** Detected issues */
  issues: DetectedIssue[];
  /** Risk level */
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  /** Recommended action */
  recommendation: 'proceed' | 'review' | 'rollback' | 'abort';
}

/**
 * Detected issue.
 */
export interface DetectedIssue {
  /** Issue type */
  type: IssueType;
  /** Severity */
  severity: 'warning' | 'error' | 'critical';
  /** Description */
  description: string;
  /** Original content related to issue */
  original?: string;
  /** Optimized content related to issue */
  optimized?: string;
}

/**
 * Issue types.
 */
export type IssueType =
  | 'content_loss'
  | 'meaning_change'
  | 'constraint_removed'
  | 'context_loss'
  | 'over_expansion'
  | 'over_compression'
  | 'structure_loss'
  | 'specificity_loss'
  | 'intent_shift'
  | 'code_corruption';

/**
 * Detection options.
 */
export interface DetectionOptions {
  /** Strictness level */
  strictness?: 'relaxed' | 'normal' | 'strict';
  /** Domain-specific checks */
  domain?: string;
  /** Original complexity */
  complexity?: Complexity;
}

/**
 * Detector class.
 */
export class Detector {
  private options: Required<DetectionOptions>;

  constructor(options: DetectionOptions = {}) {
    this.options = {
      strictness: options.strictness ?? 'normal',
      domain: options.domain ?? 'general',
      complexity: options.complexity ?? 'MODERATE',
    };
  }

  /**
   * Detect potential issues in an optimization.
   */
  detect(
    original: string,
    optimized: string,
    _changes: Change[],
    confidence: number
  ): DetectionResult {
    const issues: DetectedIssue[] = [];

    // Run all detection checks
    issues.push(...this.detectContentLoss(original, optimized));
    issues.push(...this.detectMeaningChange(original, optimized));
    issues.push(...this.detectConstraintRemoval(original, optimized));
    issues.push(...this.detectOverExpansion(original, optimized));
    issues.push(...this.detectOverCompression(original, optimized));
    issues.push(...this.detectStructureLoss(original, optimized));
    issues.push(...this.detectSpecificityLoss(original, optimized));

    // Domain-specific checks
    if (this.options.domain === 'CODE') {
      issues.push(...this.detectCodeIssues(original, optimized));
    }

    // Calculate risk level
    const riskLevel = this.calculateRiskLevel(issues, confidence);

    // Determine recommendation
    const recommendation = this.determineRecommendation(riskLevel, confidence, issues);

    // Overall detection result
    const mayCauseDegradation =
      issues.some((i) => i.severity === 'critical' || i.severity === 'error') ||
      issues.filter((i) => i.severity === 'warning').length >= 3;

    const detectionConfidence = this.calculateDetectionConfidence(issues, confidence);

    return {
      mayCauseDegradation,
      confidence: detectionConfidence,
      issues,
      riskLevel,
      recommendation,
    };
  }

  /**
   * Detect content loss.
   */
  private detectContentLoss(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Check for significant keyword loss
    const originalWords = new Set(
      original.toLowerCase().match(/\b[a-z]{3,}\b/g) ?? []
    );
    const optimizedWords = new Set(
      optimized.toLowerCase().match(/\b[a-z]{3,}\b/g) ?? []
    );

    const lostWords: string[] = [];
    for (const word of originalWords) {
      if (!optimizedWords.has(word)) {
        lostWords.push(word);
      }
    }

    // Check loss ratio
    const lossRatio = lostWords.length / Math.max(1, originalWords.size);

    if (lossRatio > 0.3) {
      issues.push({
        type: 'content_loss',
        severity: lossRatio > 0.5 ? 'error' : 'warning',
        description: `Significant content loss detected (${(lossRatio * 100).toFixed(0)}% of unique words removed)`,
        original: lostWords.slice(0, 10).join(', '),
      });
    }

    // Check for lost named entities (capitalized words)
    const originalEntities = original.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*/g) ?? [];
    const optimizedText = optimized.toLowerCase();

    for (const entity of originalEntities) {
      if (!optimizedText.includes(entity.toLowerCase())) {
        issues.push({
          type: 'content_loss',
          severity: 'warning',
          description: `Named entity "${entity}" may have been lost`,
          original: entity,
        });
      }
    }

    return issues;
  }

  /**
   * Detect meaning changes.
   */
  private detectMeaningChange(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Check for negation changes
    const negationWords = ['not', 'no', 'never', "don't", "doesn't", "won't", "can't", 'without'];

    for (const neg of negationWords) {
      const inOriginal = new RegExp(`\\b${neg}\\b`, 'i').test(original);
      const inOptimized = new RegExp(`\\b${neg}\\b`, 'i').test(optimized);

      if (inOriginal !== inOptimized) {
        issues.push({
          type: 'meaning_change',
          severity: 'error',
          description: `Negation "${neg}" was ${inOriginal ? 'removed' : 'added'}, potentially reversing meaning`,
        });
      }
    }

    // Check for comparison changes
    const comparisons = ['more', 'less', 'better', 'worse', 'higher', 'lower', 'faster', 'slower'];

    for (const comp of comparisons) {
      const originalHas = new RegExp(`\\b${comp}\\b`, 'i').test(original);
      const optimizedHas = new RegExp(`\\b${comp}\\b`, 'i').test(optimized);

      if (originalHas && !optimizedHas) {
        issues.push({
          type: 'meaning_change',
          severity: 'warning',
          description: `Comparison term "${comp}" was removed`,
        });
      }
    }

    return issues;
  }

  /**
   * Detect constraint removal.
   */
  private detectConstraintRemoval(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Constraint patterns
    const constraintPatterns = [
      { pattern: /\bmust\b/i, name: 'must' },
      { pattern: /\bshould\b/i, name: 'should' },
      { pattern: /\brequired?\b/i, name: 'required' },
      { pattern: /\bneed(s|ed)?\sto\b/i, name: 'needs to' },
      { pattern: /\bonly\b/i, name: 'only' },
      { pattern: /\bexactly\b/i, name: 'exactly' },
      { pattern: /\bspecifically\b/i, name: 'specifically' },
      { pattern: /\bmaximum\b/i, name: 'maximum' },
      { pattern: /\bminimum\b/i, name: 'minimum' },
      { pattern: /\bat least\b/i, name: 'at least' },
      { pattern: /\bat most\b/i, name: 'at most' },
    ];

    for (const { pattern, name } of constraintPatterns) {
      const inOriginal = pattern.test(original);
      const inOptimized = pattern.test(optimized);

      if (inOriginal && !inOptimized) {
        issues.push({
          type: 'constraint_removed',
          severity: 'warning',
          description: `Constraint "${name}" was removed from the prompt`,
        });
      }
    }

    // Check for numeric constraints
    const originalNumbers: string[] = original.match(/\b\d+\b/g) ?? [];
    const optimizedNumbers: string[] = optimized.match(/\b\d+\b/g) ?? [];

    for (const num of originalNumbers) {
      if (!optimizedNumbers.includes(num)) {
        issues.push({
          type: 'constraint_removed',
          severity: 'warning',
          description: `Numeric value "${num}" was removed`,
        });
      }
    }

    return issues;
  }

  /**
   * Detect over-expansion.
   */
  private detectOverExpansion(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    const ratio = optimized.length / Math.max(1, original.length);

    if (ratio > 2.5) {
      issues.push({
        type: 'over_expansion',
        severity: ratio > 4 ? 'error' : 'warning',
        description: `Optimization expanded prompt by ${((ratio - 1) * 100).toFixed(0)}%`,
      });
    }

    return issues;
  }

  /**
   * Detect over-compression.
   */
  private detectOverCompression(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    const ratio = optimized.length / Math.max(1, original.length);

    if (ratio < 0.3 && original.length > 50) {
      issues.push({
        type: 'over_compression',
        severity: ratio < 0.2 ? 'error' : 'warning',
        description: `Optimization compressed prompt by ${((1 - ratio) * 100).toFixed(0)}%`,
      });
    }

    return issues;
  }

  /**
   * Detect structure loss.
   */
  private detectStructureLoss(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Check for list structure
    const originalHasList =
      /^[\s]*[-•*\d+\.]\s/m.test(original) || original.includes('\n-') || original.includes('\n•');
    const optimizedHasList =
      /^[\s]*[-•*\d+\.]\s/m.test(optimized) || optimized.includes('\n-') || optimized.includes('\n•');

    if (originalHasList && !optimizedHasList) {
      issues.push({
        type: 'structure_loss',
        severity: 'warning',
        description: 'List structure was removed from the prompt',
      });
    }

    // Check for section headers
    const originalHeaders = (original.match(/^#+\s.+$/gm) ?? []).length;
    const optimizedHeaders = (optimized.match(/^#+\s.+$/gm) ?? []).length;

    if (originalHeaders > 0 && optimizedHeaders === 0) {
      issues.push({
        type: 'structure_loss',
        severity: 'warning',
        description: 'Section headers were removed from the prompt',
      });
    }

    // Check for paragraph structure
    const originalParagraphs = original.split(/\n\n+/).length;
    const optimizedParagraphs = optimized.split(/\n\n+/).length;

    if (originalParagraphs > 2 && optimizedParagraphs === 1) {
      issues.push({
        type: 'structure_loss',
        severity: 'warning',
        description: 'Paragraph structure was collapsed',
      });
    }

    return issues;
  }

  /**
   * Detect specificity loss.
   */
  private detectSpecificityLoss(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Check for quotes (specific examples)
    const originalQuotes = (original.match(/"[^"]+"/g) ?? []).length;
    const optimizedQuotes = (optimized.match(/"[^"]+"/g) ?? []).length;

    if (originalQuotes > 0 && optimizedQuotes < originalQuotes) {
      issues.push({
        type: 'specificity_loss',
        severity: 'warning',
        description: `${originalQuotes - optimizedQuotes} quoted example(s) removed`,
      });
    }

    // Check for technical terms
    const technicalPatterns = [
      /\b[A-Z]{2,}\b/, // Acronyms
      /\b\w+\.\w+\b/, // Dotted notation
      /`[^`]+`/, // Code backticks
    ];

    for (const pattern of technicalPatterns) {
      const originalMatches = (original.match(new RegExp(pattern, 'g')) ?? []).length;
      const optimizedMatches = (optimized.match(new RegExp(pattern, 'g')) ?? []).length;

      if (originalMatches > optimizedMatches + 1) {
        issues.push({
          type: 'specificity_loss',
          severity: 'warning',
          description: 'Technical terminology may have been simplified',
        });
        break;
      }
    }

    return issues;
  }

  /**
   * Detect code-specific issues.
   */
  private detectCodeIssues(original: string, optimized: string): DetectedIssue[] {
    const issues: DetectedIssue[] = [];

    // Check for code blocks
    const originalCodeBlocks = (original.match(/```[\s\S]*?```/g) ?? []).length;
    const optimizedCodeBlocks = (optimized.match(/```[\s\S]*?```/g) ?? []).length;

    if (originalCodeBlocks > 0 && optimizedCodeBlocks < originalCodeBlocks) {
      issues.push({
        type: 'code_corruption',
        severity: 'error',
        description: `${originalCodeBlocks - optimizedCodeBlocks} code block(s) removed`,
      });
    }

    // Check for inline code
    const originalInlineCode = (original.match(/`[^`]+`/g) ?? []).length;
    const optimizedInlineCode = (optimized.match(/`[^`]+`/g) ?? []).length;

    if (originalInlineCode > 0 && optimizedInlineCode < originalInlineCode / 2) {
      issues.push({
        type: 'code_corruption',
        severity: 'warning',
        description: 'Significant inline code may have been removed',
      });
    }

    return issues;
  }

  /**
   * Calculate risk level.
   */
  private calculateRiskLevel(
    issues: DetectedIssue[],
    confidence: number
  ): DetectionResult['riskLevel'] {
    const criticalCount = issues.filter((i) => i.severity === 'critical').length;
    const errorCount = issues.filter((i) => i.severity === 'error').length;
    const warningCount = issues.filter((i) => i.severity === 'warning').length;

    if (criticalCount > 0 || (errorCount >= 2 && confidence < 0.7)) {
      return 'CRITICAL';
    }

    if (errorCount > 0 || (warningCount >= 3 && confidence < 0.8)) {
      return 'HIGH';
    }

    if (warningCount >= 2 || confidence < 0.7) {
      return 'MEDIUM';
    }

    return 'LOW';
  }

  /**
   * Determine recommendation.
   */
  private determineRecommendation(
    riskLevel: DetectionResult['riskLevel'],
    _confidence: number,
    issues: DetectedIssue[]
  ): DetectionResult['recommendation'] {
    if (riskLevel === 'CRITICAL') {
      return 'abort';
    }

    if (riskLevel === 'HIGH') {
      return issues.some((i) => i.type === 'meaning_change') ? 'rollback' : 'review';
    }

    if (riskLevel === 'MEDIUM') {
      return 'review';
    }

    return 'proceed';
  }

  /**
   * Calculate detection confidence.
   */
  private calculateDetectionConfidence(
    issues: DetectedIssue[],
    optimizationConfidence: number
  ): number {
    // Higher confidence when more issues found with low optimization confidence
    if (issues.length === 0) {
      return 0.3; // Low confidence in "no issues" when nothing detected
    }

    const severityWeight = {
      critical: 0.9,
      error: 0.7,
      warning: 0.4,
    };

    let totalWeight = 0;
    for (const issue of issues) {
      totalWeight += severityWeight[issue.severity];
    }

    // Normalize and combine with inverse of optimization confidence
    const issueScore = Math.min(1, totalWeight / 3);
    const confidenceScore = 1 - optimizationConfidence;

    return Math.min(1, (issueScore + confidenceScore) / 2 + 0.3);
  }
}

/**
 * Create a detector.
 */
export function createDetector(options?: DetectionOptions): Detector {
  return new Detector(options);
}
