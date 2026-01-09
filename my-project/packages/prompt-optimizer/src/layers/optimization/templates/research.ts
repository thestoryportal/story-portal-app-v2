/**
 * Research domain template.
 * Specialized optimization strategies for learning and research tasks.
 */

import type { ChangeType } from '../../../types/index.js';
import { BaseDomainTemplate, type DomainTemplateConfig } from './base.js';

/**
 * Research domain template configuration.
 */
const RESEARCH_CONFIG: DomainTemplateConfig = {
  domain: 'RESEARCH',
  description: 'Learning, explaining concepts, research, and information gathering',
  keywords: [
    'explain', 'how does', 'what is', 'why does', 'learn', 'teach',
    'understand', 'research', 'study', 'concept', 'theory', 'principle',
    'difference between', 'definition', 'meaning', 'overview', 'introduction',
    'tutorial', 'guide', 'example', 'demonstrate', 'show me',
  ],
  enhancements: [
    {
      name: 'add-expertise-context',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const expertiseIndicators = ['beginner', 'intermediate', 'advanced', 'expert',
          'eli5', 'simple', 'technical', 'detailed'];
        return !expertiseIndicators.some((ei) => lower.includes(ei));
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 10,
    },
    {
      name: 'add-scope-context',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const scopeWords = ['overview', 'deep dive', 'brief', 'comprehensive', 'summary', 'detailed'];
        return !scopeWords.some((sw) => lower.includes(sw));
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 8,
    },
    {
      name: 'add-example-request',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const hasExampleRequest = lower.includes('example') || lower.includes('demonstrate') ||
          lower.includes('show me') || lower.includes('illustrate');
        const isConceptual = lower.includes('explain') || lower.includes('what is') ||
          lower.includes('how does');
        return isConceptual && !hasExampleRequest;
      },
      apply: (prompt) => {
        const clarification = ' Include practical examples where helpful.';
        return {
          enhanced: prompt + clarification,
          change: {
            type: 'ADD_CONTEXT' as ChangeType,
            originalSegment: '',
            newSegment: clarification.trim(),
            reason: 'Added request for examples to aid understanding',
          },
        };
      },
      priority: 7,
    },
  ],
  preservePatterns: [
    // Technical terms
    /\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b/g,
    // Specific concepts in quotes
    /"[^"]+"/g,
    /`[^`]+`/g,
    // Version numbers
    /v?\d+\.\d+(?:\.\d+)?/g,
    // Acronyms
    /\b[A-Z]{2,}\b/g,
    // Specific questions
    /\b(?:what|why|how|when|where|who)\s+[^?]+\?/gi,
  ],
  clarityIndicators: [
    'explain like',
    'eli5',
    'for beginners',
    'in simple terms',
    'technical deep dive',
    'comprehensive',
    'overview',
    'with examples',
  ],
  commonIssues: [
    {
      pattern: /\btell me about\b/gi,
      fix: 'explain',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Changed "tell me about" to more specific "explain"',
    },
    {
      pattern: /\beverything about\b/gi,
      fix: 'the key aspects of',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Scoped down overly broad request',
    },
    {
      pattern: /\ball about\b/gi,
      fix: 'the fundamentals of',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Scoped down overly broad request',
    },
  ],
  maxExpansionRatio: 2.0,
};

/**
 * Research domain template class.
 */
export class ResearchTemplate extends BaseDomainTemplate {
  constructor() {
    super(RESEARCH_CONFIG);
  }

  /**
   * Generate research-specific tip.
   */
  generateTip(prompt: string): string {
    const lower = prompt.toLowerCase();

    // Check for expertise level
    const expertiseWords = ['beginner', 'intermediate', 'advanced', 'expert', 'eli5', 'simple', 'technical'];
    const hasExpertise = expertiseWords.some((ew) => lower.includes(ew));

    if (!hasExpertise) {
      return 'Tip: Specify your knowledge level (beginner, intermediate, advanced) for appropriate depth.';
    }

    // Check for scope
    const scopeWords = ['overview', 'deep dive', 'brief', 'comprehensive', 'detailed'];
    const hasScope = scopeWords.some((sw) => lower.includes(sw));

    if (!hasScope) {
      return 'Tip: Indicate desired depth (quick overview, detailed explanation, deep dive).';
    }

    // Check for examples request
    if (lower.includes('explain') || lower.includes('what is')) {
      if (!lower.includes('example')) {
        return 'Tip: Request examples for better understanding of abstract concepts.';
      }
    }

    // Check for practical application
    if (!lower.includes('practical') && !lower.includes('apply') && !lower.includes('use case')) {
      return 'Tip: Ask about practical applications or use cases for actionable learning.';
    }

    return 'Tip: Include expertise level, desired depth, and request examples for effective learning.';
  }

  /**
   * Detect research type from prompt.
   */
  detectResearchType(prompt: string): {
    type: 'concept' | 'howto' | 'comparison' | 'troubleshooting' | 'overview' | 'other';
    depth: 'surface' | 'moderate' | 'deep' | 'unknown';
    expertiseLevel: 'beginner' | 'intermediate' | 'advanced' | 'unknown';
  } {
    const lower = prompt.toLowerCase();

    // Detect type
    let type: 'concept' | 'howto' | 'comparison' | 'troubleshooting' | 'overview' | 'other' = 'other';
    if (lower.includes('what is') || lower.includes('explain') || lower.includes('define')) {
      type = 'concept';
    } else if (lower.includes('how to') || lower.includes('how do') || lower.includes('steps to')) {
      type = 'howto';
    } else if (lower.includes('difference') || lower.includes('compare') || lower.includes('vs')) {
      type = 'comparison';
    } else if (lower.includes('why') || lower.includes('debug') || lower.includes('issue')) {
      type = 'troubleshooting';
    } else if (lower.includes('overview') || lower.includes('introduction') || lower.includes('basics')) {
      type = 'overview';
    }

    // Detect depth
    let depth: 'surface' | 'moderate' | 'deep' | 'unknown' = 'unknown';
    if (lower.includes('brief') || lower.includes('quick') || lower.includes('summary') || lower.includes('eli5')) {
      depth = 'surface';
    } else if (lower.includes('detailed') || lower.includes('comprehensive') || lower.includes('deep dive')) {
      depth = 'deep';
    } else if (lower.includes('explain') || lower.includes('understand')) {
      depth = 'moderate';
    }

    // Detect expertise level
    let expertiseLevel: 'beginner' | 'intermediate' | 'advanced' | 'unknown' = 'unknown';
    if (lower.includes('beginner') || lower.includes('new to') || lower.includes('eli5') || lower.includes('simple')) {
      expertiseLevel = 'beginner';
    } else if (lower.includes('intermediate') || lower.includes('some experience')) {
      expertiseLevel = 'intermediate';
    } else if (lower.includes('advanced') || lower.includes('expert') || lower.includes('technical')) {
      expertiseLevel = 'advanced';
    }

    return { type, depth, expertiseLevel };
  }

  /**
   * Suggest learning path based on topic.
   */
  suggestLearningPath(researchType: 'concept' | 'howto' | 'comparison' | 'troubleshooting' | 'overview' | 'other'): string[] {
    switch (researchType) {
      case 'concept':
        return [
          'Start with definition and core purpose',
          'Learn fundamental principles',
          'Understand common use cases',
          'Explore examples and analogies',
          'Learn related concepts',
        ];
      case 'howto':
        return [
          'Prerequisites and setup',
          'Basic steps walkthrough',
          'Common variations',
          'Best practices',
          'Troubleshooting common issues',
        ];
      case 'comparison':
        return [
          'Define comparison criteria',
          'Understand each option individually',
          'Compare on key dimensions',
          'Consider use cases for each',
          'Make informed decision',
        ];
      case 'troubleshooting':
        return [
          'Understand expected vs actual behavior',
          'Identify possible causes',
          'Systematic debugging approach',
          'Apply and verify fixes',
          'Prevent future occurrences',
        ];
      case 'overview':
        return [
          'What it is and why it matters',
          'Core concepts and terminology',
          'How it works at high level',
          'Common applications',
          'Where to go next',
        ];
      default:
        return [
          'Define your learning goal',
          'Gather foundational knowledge',
          'Apply through examples',
          'Deepen understanding',
          'Connect to broader context',
        ];
    }
  }

  /**
   * Generate follow-up questions for deeper learning.
   */
  generateFollowUpQuestions(prompt: string): string[] {
    const { type } = this.detectResearchType(prompt);

    switch (type) {
      case 'concept':
        return [
          'How does this differ from similar concepts?',
          'What are common misconceptions?',
          'How is this applied in practice?',
        ];
      case 'howto':
        return [
          'What are alternative approaches?',
          'What are common mistakes to avoid?',
          'How can I verify this worked correctly?',
        ];
      case 'comparison':
        return [
          'What are the trade-offs involved?',
          'When would I choose one over the other?',
          'Are there hybrid approaches?',
        ];
      default:
        return [
          'Can you provide more examples?',
          'How does this relate to X?',
          'What should I learn next?',
        ];
    }
  }
}

/**
 * Create a research template instance.
 */
export function createResearchTemplate(): ResearchTemplate {
  return new ResearchTemplate();
}
