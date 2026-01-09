/**
 * Analysis domain template.
 * Specialized optimization strategies for analytical and comparison tasks.
 */

import type { ChangeType } from '../../../types/index.js';
import { BaseDomainTemplate, type DomainTemplateConfig } from './base.js';

/**
 * Analysis domain template configuration.
 */
const ANALYSIS_CONFIG: DomainTemplateConfig = {
  domain: 'ANALYSIS',
  description: 'Comparisons, data analysis, evaluations, and decision support',
  keywords: [
    'compare', 'comparison', 'analyze', 'analysis', 'evaluate', 'evaluation',
    'pros and cons', 'advantages', 'disadvantages', 'trade-offs', 'tradeoffs',
    'metrics', 'data', 'statistics', 'benchmark', 'performance',
    'difference', 'similarities', 'versus', 'vs', 'between',
    'review', 'assess', 'criteria', 'decision',
  ],
  enhancements: [
    {
      name: 'add-criteria-request',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const needsCriteria = lower.includes('compare') || lower.includes('evaluate') || lower.includes('analyze');
        const hasCriteria = lower.includes('criteria') || lower.includes('based on') ||
          lower.includes('in terms of') || lower.includes('regarding');
        return needsCriteria && !hasCriteria;
      },
      apply: (prompt) => {
        const clarification = '\n\nWhat criteria should be used for this analysis?';
        return {
          enhanced: prompt + clarification,
          change: {
            type: 'ADD_CONTEXT' as ChangeType,
            originalSegment: '',
            newSegment: clarification.trim(),
            reason: 'Added criteria clarification for analysis',
          },
        };
      },
      priority: 10,
    },
    {
      name: 'add-format-request',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const formatWords = ['table', 'list', 'chart', 'format', 'structure', 'bullet', 'section'];
        return !formatWords.some((fw) => lower.includes(fw));
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 7,
    },
    {
      name: 'add-depth-request',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const depthWords = ['brief', 'detailed', 'comprehensive', 'summary', 'in-depth', 'quick', 'thorough'];
        return !depthWords.some((dw) => lower.includes(dw));
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 6,
    },
  ],
  preservePatterns: [
    // Specific items being compared
    /\b(?:option|choice|alternative)\s+[A-Za-z0-9]/gi,
    // Numbers and percentages
    /\b\d+(?:\.\d+)?%?\b/g,
    // Technical terms in quotes or backticks
    /"[^"]+"/g,
    /`[^`]+`/g,
    // Specific metrics mentioned
    /\b(?:latency|throughput|accuracy|precision|recall|f1|cost|price|time|speed)\b/gi,
  ],
  clarityIndicators: [
    'criteria',
    'based on',
    'in terms of',
    'considering',
    'factors',
    'metrics',
    'weight',
    'priority',
    'importance',
  ],
  commonIssues: [
    {
      pattern: /\bwhich is better\b/gi,
      fix: 'which is more suitable for the specified criteria',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Clarified "better" to require criteria',
    },
    {
      pattern: /\bthe best\b/gi,
      fix: 'the most suitable',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Changed subjective "best" to objective phrasing',
    },
    {
      pattern: /\bthose two\b/gi,
      fix: 'the mentioned options',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Clarified vague reference',
    },
  ],
  maxExpansionRatio: 2.0,
};

/**
 * Analysis domain template class.
 */
export class AnalysisTemplate extends BaseDomainTemplate {
  constructor() {
    super(ANALYSIS_CONFIG);
  }

  /**
   * Generate analysis-specific tip.
   */
  generateTip(prompt: string): string {
    const lower = prompt.toLowerCase();

    // Check for missing criteria
    const criteriaWords = ['criteria', 'based on', 'in terms of', 'considering', 'factors'];
    const hasCriteria = criteriaWords.some((cw) => lower.includes(cw));

    if (!hasCriteria) {
      return 'Tip: Specify the criteria for comparison/analysis for more focused results.';
    }

    // Check for missing format
    const formatWords = ['table', 'list', 'chart', 'format', 'structure'];
    const hasFormat = formatWords.some((fw) => lower.includes(fw));

    if (!hasFormat) {
      return 'Tip: Specify the desired output format (table, list, sections) for clearer results.';
    }

    // Check for missing depth
    const depthWords = ['brief', 'detailed', 'comprehensive', 'summary', 'in-depth'];
    const hasDepth = depthWords.some((dw) => lower.includes(dw));

    if (!hasDepth) {
      return 'Tip: Indicate desired analysis depth (brief overview or comprehensive analysis).';
    }

    return 'Tip: Include specific criteria, desired format, and analysis depth for best results.';
  }

  /**
   * Detect analysis type from prompt.
   */
  detectAnalysisType(prompt: string): {
    type: 'comparison' | 'evaluation' | 'decision' | 'data' | 'review' | 'other';
    subjects: string[];
    suggestedCriteria: string[];
  } {
    const lower = prompt.toLowerCase();

    // Detect type
    let type: 'comparison' | 'evaluation' | 'decision' | 'data' | 'review' | 'other' = 'other';
    if (lower.includes('compare') || lower.includes('vs') || lower.includes('versus') || lower.includes('difference')) {
      type = 'comparison';
    } else if (lower.includes('evaluate') || lower.includes('assess')) {
      type = 'evaluation';
    } else if (lower.includes('decide') || lower.includes('choose') || lower.includes('should i')) {
      type = 'decision';
    } else if (lower.includes('data') || lower.includes('metrics') || lower.includes('statistics')) {
      type = 'data';
    } else if (lower.includes('review') || lower.includes('analyze')) {
      type = 'review';
    }

    // Extract subjects being compared/analyzed
    const subjects: string[] = [];
    const vsMatch = prompt.match(/(\w+(?:\s+\w+)?)\s+(?:vs\.?|versus|or|and)\s+(\w+(?:\s+\w+)?)/gi);
    if (vsMatch) {
      for (const match of vsMatch) {
        const parts = match.split(/\s+(?:vs\.?|versus|or|and)\s+/i);
        subjects.push(...parts);
      }
    }

    // Suggest criteria based on context
    const suggestedCriteria: string[] = [];
    if (lower.includes('framework') || lower.includes('library') || lower.includes('tool')) {
      suggestedCriteria.push('performance', 'learning curve', 'community support', 'documentation', 'maintenance');
    } else if (lower.includes('service') || lower.includes('provider') || lower.includes('platform')) {
      suggestedCriteria.push('pricing', 'features', 'reliability', 'support', 'scalability');
    } else if (lower.includes('approach') || lower.includes('method') || lower.includes('strategy')) {
      suggestedCriteria.push('effectiveness', 'complexity', 'time required', 'resources', 'risk');
    } else {
      suggestedCriteria.push('cost', 'quality', 'time', 'ease of use', 'sustainability');
    }

    return { type, subjects: [...new Set(subjects)], suggestedCriteria };
  }

  /**
   * Suggest output format based on analysis type.
   */
  suggestOutputFormat(analysisType: 'comparison' | 'evaluation' | 'decision' | 'data' | 'review' | 'other'): string {
    switch (analysisType) {
      case 'comparison':
        return 'Consider requesting a comparison table with rows for criteria and columns for options.';
      case 'evaluation':
        return 'Consider requesting a scored assessment with criteria weights and ratings.';
      case 'decision':
        return 'Consider requesting a decision matrix or pros/cons list with recommendation.';
      case 'data':
        return 'Consider requesting summary statistics, trends, and key insights.';
      case 'review':
        return 'Consider requesting structured sections: overview, strengths, weaknesses, recommendations.';
      default:
        return 'Consider specifying the desired output format (table, list, sections, summary).';
    }
  }
}

/**
 * Create an analysis template instance.
 */
export function createAnalysisTemplate(): AnalysisTemplate {
  return new AnalysisTemplate();
}
