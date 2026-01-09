/**
 * Confidence scoring utilities.
 * Provides calibrated confidence calculations for optimization decisions.
 */

import { CONFIDENCE_WEIGHTS } from '../constants/index.js';

/**
 * Confidence factors used in scoring.
 */
export interface ConfidenceFactors {
  /** Classification confidence (0-1) */
  classification?: number;
  /** Intent preservation score (0-1) */
  intentPreservation?: number;
  /** Domain match confidence (0-1) */
  domainMatch?: number;
  /** Complexity adjustment (-0.2 to 0.1) */
  complexityAdjustment?: number;
  /** User acceptance history (0-1) */
  userAcceptance?: number;
  /** Change magnitude (0-1, lower = less change = higher confidence) */
  changeMagnitude?: number;
  /** Critique result adjustment (-0.2 to 0.1) */
  critiqueAdjustment?: number;
}

/**
 * Confidence calculation result.
 */
export interface ConfidenceResult {
  /** Final confidence score (0-1) */
  score: number;
  /** Confidence level category */
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  /** Should prompt for user confirmation? */
  shouldConfirm: boolean;
  /** Human-readable explanation */
  explanation: string;
  /** Individual factor contributions */
  factors: Record<string, number>;
}

/**
 * Calculate combined confidence score.
 */
export function calculateConfidence(factors: ConfidenceFactors): ConfidenceResult {
  const weights = CONFIDENCE_WEIGHTS;
  let totalWeight = 0;
  let weightedSum = 0;
  const factorContributions: Record<string, number> = {};

  // Classification confidence
  if (factors.classification !== undefined) {
    const contribution = factors.classification * weights.classification;
    weightedSum += contribution;
    totalWeight += weights.classification;
    factorContributions.classification = contribution;
  }

  // Intent preservation (uses 'intent' weight)
  if (factors.intentPreservation !== undefined) {
    const contribution = factors.intentPreservation * weights.intent;
    weightedSum += contribution;
    totalWeight += weights.intent;
    factorContributions.intentPreservation = contribution;
  }

  // Domain match (uses 'domain' weight)
  if (factors.domainMatch !== undefined) {
    const contribution = factors.domainMatch * weights.domain;
    weightedSum += contribution;
    totalWeight += weights.domain;
    factorContributions.domainMatch = contribution;
  }

  // Complexity adjustment (additive, not weighted average)
  if (factors.complexityAdjustment !== undefined) {
    factorContributions.complexityAdjustment = factors.complexityAdjustment;
  }

  // User acceptance (uses 'context' weight as proxy for historical context)
  if (factors.userAcceptance !== undefined) {
    const contribution = factors.userAcceptance * weights.context;
    weightedSum += contribution;
    totalWeight += weights.context;
    factorContributions.userAcceptance = contribution;
  }

  // Change magnitude (uses 'optimization' weight - inverse - less change = higher confidence)
  if (factors.changeMagnitude !== undefined) {
    const inverseChange = 1 - factors.changeMagnitude;
    const contribution = inverseChange * weights.optimization;
    weightedSum += contribution;
    totalWeight += weights.optimization;
    factorContributions.changeMagnitude = contribution;
  }

  // Calculate base score
  let score = totalWeight > 0 ? weightedSum / totalWeight : 0.5;

  // Apply additive adjustments
  if (factors.complexityAdjustment !== undefined) {
    score += factors.complexityAdjustment;
  }
  if (factors.critiqueAdjustment !== undefined) {
    score += factors.critiqueAdjustment;
    factorContributions.critiqueAdjustment = factors.critiqueAdjustment;
  }

  // Clamp to valid range
  score = Math.max(0, Math.min(1, score));

  // Determine level and confirmation need
  const level = getConfidenceLevel(score);
  const shouldConfirm = score < 0.8;

  // Generate explanation
  const explanation = generateExplanation(score, level, factorContributions);

  return {
    score,
    level,
    shouldConfirm,
    explanation,
    factors: factorContributions,
  };
}

/**
 * Get confidence level category.
 */
export function getConfidenceLevel(score: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 0.85) return 'HIGH';
  if (score >= 0.7) return 'MEDIUM';
  return 'LOW';
}

/**
 * Generate human-readable confidence explanation.
 */
function generateExplanation(
  _score: number,
  level: 'HIGH' | 'MEDIUM' | 'LOW',
  factors: Record<string, number>
): string {
  const parts: string[] = [];

  // Overall statement
  if (level === 'HIGH') {
    parts.push('High confidence in optimization quality.');
  } else if (level === 'MEDIUM') {
    parts.push('Moderate confidence - review recommended.');
  } else {
    parts.push('Low confidence - careful review needed.');
  }

  // Key factor impacts
  if (factors.intentPreservation !== undefined) {
    if (factors.intentPreservation >= 0.4) {
      parts.push('Intent well preserved.');
    } else if (factors.intentPreservation >= 0.3) {
      parts.push('Some intent drift detected.');
    } else {
      parts.push('Significant intent drift - verify carefully.');
    }
  }

  if (factors.critiqueAdjustment !== undefined && factors.critiqueAdjustment < -0.1) {
    parts.push('Self-critique found issues.');
  }

  return parts.join(' ');
}

/**
 * Adjust confidence based on prompt complexity.
 */
export function getComplexityAdjustment(complexity: 'SIMPLE' | 'MODERATE' | 'COMPLEX'): number {
  switch (complexity) {
    case 'SIMPLE':
      return 0.05; // Boost for simple prompts
    case 'MODERATE':
      return 0;
    case 'COMPLEX':
      return -0.1; // Penalty for complex prompts
    default:
      return 0;
  }
}

/**
 * Calculate change magnitude from original to optimized.
 */
export function calculateChangeMagnitude(original: string, optimized: string): number {
  const originalWords = new Set(original.toLowerCase().split(/\s+/));
  const optimizedWords = new Set(optimized.toLowerCase().split(/\s+/));

  // Calculate Jaccard distance
  const intersection = new Set([...originalWords].filter((w) => optimizedWords.has(w)));
  const union = new Set([...originalWords, ...optimizedWords]);

  const similarity = union.size > 0 ? intersection.size / union.size : 1;

  // Change magnitude is inverse of similarity
  return 1 - similarity;
}

/**
 * Check if confidence is above auto-accept threshold.
 */
export function shouldAutoAccept(
  confidence: number,
  threshold: number = 0.9
): boolean {
  return confidence >= threshold;
}

/**
 * Check if confidence is below rejection threshold.
 */
export function shouldReject(
  confidence: number,
  threshold: number = 0.5
): boolean {
  return confidence < threshold;
}

/**
 * Blend multiple confidence scores.
 */
export function blendConfidences(
  confidences: number[],
  weights?: number[]
): number {
  if (confidences.length === 0) return 0.5;

  const effectiveWeights = weights ?? confidences.map(() => 1);

  let weightedSum = 0;
  let totalWeight = 0;

  for (let i = 0; i < confidences.length; i++) {
    weightedSum += confidences[i] * effectiveWeights[i];
    totalWeight += effectiveWeights[i];
  }

  return totalWeight > 0 ? weightedSum / totalWeight : 0.5;
}
