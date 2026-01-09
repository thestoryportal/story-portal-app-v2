/**
 * Creative domain template.
 * Specialized optimization strategies for creative and brainstorming tasks.
 */

import type { ChangeType } from '../../../types/index.js';
import { BaseDomainTemplate, type DomainTemplateConfig } from './base.js';

/**
 * Creative domain template configuration.
 */
const CREATIVE_CONFIG: DomainTemplateConfig = {
  domain: 'CREATIVE',
  description: 'Brainstorming, storytelling, design ideation, and creative writing',
  keywords: [
    'story', 'brainstorm', 'creative', 'idea', 'imagine', 'design',
    'concept', 'character', 'plot', 'narrative', 'fiction', 'poem',
    'song', 'script', 'dialogue', 'scene', 'world', 'fantasy',
    'innovate', 'original', 'unique', 'inventive', 'artistic',
  ],
  enhancements: [
    {
      name: 'preserve-creative-freedom',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        // Don't over-constrain creative prompts
        const constraintWords = ['must', 'should', 'exactly', 'specifically', 'only'];
        const hasConstraints = constraintWords.filter((cw) => lower.includes(cw)).length;
        return hasConstraints > 2;
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null, // Note: don't add constraints to creative prompts
        };
      },
      priority: 10,
    },
    {
      name: 'add-creative-parameters',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const hasStory = lower.includes('story') || lower.includes('narrative') || lower.includes('fiction');
        const hasParams = lower.includes('genre') || lower.includes('length') ||
          lower.includes('tone') || lower.includes('style');
        return hasStory && !hasParams;
      },
      apply: (prompt) => {
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 8,
    },
  ],
  preservePatterns: [
    // Character names
    /\b[A-Z][a-z]+(?:'s)?\b/g,
    // Quoted dialogue or phrases
    /"[^"]+"/g,
    // Specific creative constraints mentioned
    /\b\d+\s+(?:words?|pages?|chapters?|paragraphs?)\b/gi,
    // Genre terms
    /\b(?:fantasy|sci-fi|romance|mystery|thriller|horror|comedy|drama)\b/gi,
    // Setting descriptions
    /\b(?:medieval|futuristic|modern|ancient|post-apocalyptic)\b/gi,
  ],
  clarityIndicators: [
    'genre',
    'style',
    'tone',
    'setting',
    'character',
    'theme',
    'mood',
    'perspective',
    'length',
  ],
  commonIssues: [
    {
      pattern: /\ba story\b/gi,
      fix: 'a story',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Generic story request - consider adding genre or theme',
    },
    {
      pattern: /\bsomething creative\b/gi,
      fix: 'a creative piece',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Vague creative request - consider specifying type',
    },
  ],
  maxExpansionRatio: 1.5, // Keep creative prompts lean
};

/**
 * Creative domain template class.
 */
export class CreativeTemplate extends BaseDomainTemplate {
  constructor() {
    super(CREATIVE_CONFIG);
  }

  /**
   * Generate creative-specific tip.
   */
  generateTip(prompt: string): string {
    const lower = prompt.toLowerCase();

    // For stories
    if (lower.includes('story') || lower.includes('narrative')) {
      const hasGenre = ['fantasy', 'sci-fi', 'romance', 'mystery', 'thriller', 'horror']
        .some((g) => lower.includes(g));

      if (!hasGenre) {
        return 'Tip: Optionally specify genre, but feel free to let creativity flow freely.';
      }

      const hasLength = ['short', 'long', 'words', 'pages'].some((l) => lower.includes(l));
      if (!hasLength) {
        return 'Tip: Indicate desired length if you have a preference.';
      }
    }

    // For brainstorming
    if (lower.includes('brainstorm') || lower.includes('ideas')) {
      return 'Tip: Specify the number of ideas you want, or leave open for diverse exploration.';
    }

    // For character creation
    if (lower.includes('character')) {
      return 'Tip: Provide context about the story/world for more fitting character development.';
    }

    // Default creative tip
    return 'Tip: Balance constraints with creative freedom - too many limits can stifle creativity.';
  }

  /**
   * Detect creative type from prompt.
   */
  detectCreativeType(prompt: string): {
    type: 'story' | 'brainstorm' | 'character' | 'worldbuilding' | 'poetry' | 'dialogue' | 'design' | 'other';
    genre: string | null;
    mood: string | null;
  } {
    const lower = prompt.toLowerCase();

    // Detect type
    let type: 'story' | 'brainstorm' | 'character' | 'worldbuilding' | 'poetry' | 'dialogue' | 'design' | 'other' = 'other';
    if (lower.includes('story') || lower.includes('narrative') || lower.includes('tale')) type = 'story';
    else if (lower.includes('brainstorm') || lower.includes('ideas') || lower.includes('generate')) type = 'brainstorm';
    else if (lower.includes('character')) type = 'character';
    else if (lower.includes('world') || lower.includes('setting') || lower.includes('universe')) type = 'worldbuilding';
    else if (lower.includes('poem') || lower.includes('poetry') || lower.includes('verse')) type = 'poetry';
    else if (lower.includes('dialogue') || lower.includes('conversation') || lower.includes('script')) type = 'dialogue';
    else if (lower.includes('design') || lower.includes('concept') || lower.includes('logo')) type = 'design';

    // Detect genre
    let genre: string | null = null;
    const genres = ['fantasy', 'sci-fi', 'science fiction', 'romance', 'mystery', 'thriller',
      'horror', 'comedy', 'drama', 'adventure', 'historical'];
    for (const g of genres) {
      if (lower.includes(g)) {
        genre = g;
        break;
      }
    }

    // Detect mood
    let mood: string | null = null;
    const moods = ['dark', 'light', 'whimsical', 'serious', 'humorous', 'melancholic',
      'hopeful', 'tense', 'peaceful', 'mysterious'];
    for (const m of moods) {
      if (lower.includes(m)) {
        mood = m;
        break;
      }
    }

    return { type, genre, mood };
  }

  /**
   * Suggest creative parameters based on type.
   */
  suggestParameters(creativeType: 'story' | 'brainstorm' | 'character' | 'worldbuilding' | 'poetry' | 'dialogue' | 'design' | 'other'): string[] {
    switch (creativeType) {
      case 'story':
        return ['genre', 'length', 'protagonist', 'conflict', 'setting', 'tone'];
      case 'brainstorm':
        return ['number of ideas', 'constraints', 'domain', 'wildcard thinking'];
      case 'character':
        return ['role', 'personality', 'backstory', 'motivations', 'flaws', 'relationships'];
      case 'worldbuilding':
        return ['era', 'technology level', 'magic system', 'cultures', 'geography', 'conflicts'];
      case 'poetry':
        return ['form', 'theme', 'mood', 'rhyme scheme', 'length'];
      case 'dialogue':
        return ['characters', 'context', 'conflict', 'tone', 'subtext'];
      case 'design':
        return ['style', 'mood', 'colors', 'target audience', 'medium'];
      default:
        return ['type', 'style', 'constraints', 'inspiration'];
    }
  }

  /**
   * Check if prompt has appropriate creative freedom.
   */
  hasCreativeFreedom(prompt: string): boolean {
    const lower = prompt.toLowerCase();
    const constraintWords = ['must', 'should', 'exactly', 'specifically', 'only', 'never', 'always'];
    const constraintCount = constraintWords.filter((cw) => lower.includes(cw)).length;

    // Too many constraints reduce creative freedom
    return constraintCount <= 3;
  }
}

/**
 * Create a creative template instance.
 */
export function createCreativeTemplate(): CreativeTemplate {
  return new CreativeTemplate();
}
