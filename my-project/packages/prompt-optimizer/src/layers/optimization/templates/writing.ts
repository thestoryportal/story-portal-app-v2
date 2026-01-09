/**
 * Writing domain template.
 * Specialized optimization strategies for writing and documentation tasks.
 */

import type { ChangeType } from '../../../types/index.js';
import { BaseDomainTemplate, type DomainTemplateConfig } from './base.js';

/**
 * Writing domain template configuration.
 */
const WRITING_CONFIG: DomainTemplateConfig = {
  domain: 'WRITING',
  description: 'Emails, documentation, articles, and other written content',
  keywords: [
    'email', 'letter', 'document', 'write', 'draft', 'compose',
    'article', 'blog', 'post', 'essay', 'report', 'summary',
    'professional', 'formal', 'informal', 'tone', 'proofread',
    'readme', 'documentation', 'describe', 'explain',
  ],
  enhancements: [
    {
      name: 'add-audience-context',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const needsAudience = lower.includes('email') || lower.includes('letter') || lower.includes('document');
        const hasAudience = lower.includes('audience') || lower.includes('reader') ||
          lower.includes('boss') || lower.includes('client') || lower.includes('team');
        return needsAudience && !hasAudience;
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null, // Don't auto-add, just note it
        };
      },
      priority: 10,
    },
    {
      name: 'add-tone-context',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const toneWords = ['formal', 'informal', 'professional', 'friendly', 'casual', 'serious', 'tone'];
        return !toneWords.some((tw) => lower.includes(tw));
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
      name: 'add-length-guidance',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const lengthWords = ['short', 'long', 'brief', 'detailed', 'concise', 'words', 'paragraphs', 'pages'];
        return !lengthWords.some((lw) => lower.includes(lw));
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
    // Quoted content to include
    /"[^"]+"/g,
    /'[^']+'/g,
    // Names and proper nouns (capitalized words)
    /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b/g,
    // Specific dates
    /\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b/g,
    // Specific times
    /\b\d{1,2}:\d{2}(?:\s*[APap][Mm])?\b/g,
    // Email addresses
    /\b[\w.-]+@[\w.-]+\.\w+\b/g,
    // Phone numbers
    /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g,
  ],
  clarityIndicators: [
    'formal tone',
    'professional',
    'friendly tone',
    'for my',
    'to my',
    'addressed to',
    'target audience',
    'word count',
    'paragraph',
  ],
  commonIssues: [
    {
      pattern: /\bwrite me\b/gi,
      fix: 'write',
      changeType: 'REMOVE_REDUNDANCY' as ChangeType,
      description: 'Removed redundant "me"',
    },
    {
      pattern: /\bsomething about\b/gi,
      fix: 'about',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Simplified vague phrasing',
    },
    {
      pattern: /\ba good\b/gi,
      fix: 'an effective',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Made quality descriptor more specific',
    },
    {
      pattern: /\bnice\b/gi,
      fix: 'appropriate',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Made descriptor more specific',
    },
  ],
  maxExpansionRatio: 1.8,
};

/**
 * Writing domain template class.
 */
export class WritingTemplate extends BaseDomainTemplate {
  constructor() {
    super(WRITING_CONFIG);
  }

  /**
   * Generate writing-specific tip.
   */
  generateTip(prompt: string): string {
    const lower = prompt.toLowerCase();

    // Check for missing audience
    const audienceWords = ['audience', 'reader', 'boss', 'client', 'team', 'colleague', 'manager'];
    const hasAudience = audienceWords.some((aw) => lower.includes(aw));

    if (!hasAudience && (lower.includes('email') || lower.includes('letter'))) {
      return 'Tip: Specify who the recipient is for better tone calibration.';
    }

    // Check for missing tone
    const toneWords = ['formal', 'informal', 'professional', 'friendly', 'casual', 'serious'];
    const hasTone = toneWords.some((tw) => lower.includes(tw));

    if (!hasTone) {
      return 'Tip: Specify the desired tone (formal, friendly, professional) for better results.';
    }

    // Check for missing length
    const lengthWords = ['short', 'long', 'brief', 'detailed', 'concise', 'words', 'paragraphs'];
    const hasLength = lengthWords.some((lw) => lower.includes(lw));

    if (!hasLength) {
      return 'Tip: Indicate desired length (brief, detailed, X words) for appropriately sized output.';
    }

    // Check for missing format
    if (lower.includes('document') || lower.includes('article')) {
      return 'Tip: Specify format requirements (headings, bullet points, sections) if needed.';
    }

    return 'Tip: Include audience, tone, and length requirements for best writing results.';
  }

  /**
   * Detect writing type from prompt.
   */
  detectWritingType(prompt: string): {
    type: 'email' | 'letter' | 'article' | 'documentation' | 'social' | 'other';
    formality: 'formal' | 'semi-formal' | 'informal' | 'unknown';
    purpose: string | null;
  } {
    const lower = prompt.toLowerCase();

    // Detect type
    let type: 'email' | 'letter' | 'article' | 'documentation' | 'social' | 'other' = 'other';
    if (lower.includes('email')) type = 'email';
    else if (lower.includes('letter')) type = 'letter';
    else if (lower.includes('article') || lower.includes('blog') || lower.includes('post')) type = 'article';
    else if (lower.includes('readme') || lower.includes('documentation') || lower.includes('doc')) type = 'documentation';
    else if (lower.includes('tweet') || lower.includes('social')) type = 'social';

    // Detect formality
    let formality: 'formal' | 'semi-formal' | 'informal' | 'unknown' = 'unknown';
    if (lower.includes('formal') || lower.includes('professional')) formality = 'formal';
    else if (lower.includes('friendly') || lower.includes('casual') || lower.includes('informal')) formality = 'informal';
    else if (lower.includes('business')) formality = 'semi-formal';

    // Infer formality from type if not specified
    if (formality === 'unknown') {
      if (type === 'letter') formality = 'formal';
      else if (type === 'social') formality = 'informal';
      else if (type === 'documentation') formality = 'semi-formal';
    }

    // Detect purpose
    let purpose: string | null = null;
    if (lower.includes('apologize') || lower.includes('apology')) purpose = 'apology';
    else if (lower.includes('thank')) purpose = 'gratitude';
    else if (lower.includes('request') || lower.includes('asking for')) purpose = 'request';
    else if (lower.includes('inform') || lower.includes('announce')) purpose = 'announcement';
    else if (lower.includes('follow up') || lower.includes('follow-up')) purpose = 'follow-up';
    else if (lower.includes('introduce') || lower.includes('introduction')) purpose = 'introduction';

    return { type, formality, purpose };
  }

  /**
   * Suggest structure based on writing type.
   */
  suggestStructure(writingType: 'email' | 'letter' | 'article' | 'documentation' | 'social' | 'other'): string[] {
    switch (writingType) {
      case 'email':
        return ['Subject line', 'Greeting', 'Opening/context', 'Main content', 'Call to action', 'Closing'];
      case 'letter':
        return ['Header', 'Date', 'Salutation', 'Opening paragraph', 'Body', 'Closing paragraph', 'Sign-off'];
      case 'article':
        return ['Title', 'Introduction/hook', 'Body sections with headings', 'Conclusion', 'Call to action'];
      case 'documentation':
        return ['Title', 'Overview', 'Prerequisites', 'Instructions', 'Examples', 'Troubleshooting'];
      case 'social':
        return ['Hook', 'Main message', 'Hashtags/mentions'];
      default:
        return ['Introduction', 'Body', 'Conclusion'];
    }
  }
}

/**
 * Create a writing template instance.
 */
export function createWritingTemplate(): WritingTemplate {
  return new WritingTemplate();
}
