/**
 * Domain template exports.
 */

export { BaseDomainTemplate } from './base.js';
export type { DomainTemplateConfig, EnhancementStrategy, IssuePattern } from './base.js';

export { CodeTemplate, createCodeTemplate } from './code.js';
export { WritingTemplate, createWritingTemplate } from './writing.js';
export { AnalysisTemplate, createAnalysisTemplate } from './analysis.js';
export { CreativeTemplate, createCreativeTemplate } from './creative.js';
export { ResearchTemplate, createResearchTemplate } from './research.js';

import type { Domain } from '../../../types/index.js';
import { BaseDomainTemplate } from './base.js';
import { CodeTemplate } from './code.js';
import { WritingTemplate } from './writing.js';
import { AnalysisTemplate } from './analysis.js';
import { CreativeTemplate } from './creative.js';
import { ResearchTemplate } from './research.js';

/**
 * Template registry for domain templates.
 */
export class TemplateRegistry {
  private templates: Map<Domain, BaseDomainTemplate> = new Map();

  constructor() {
    this.register('CODE', new CodeTemplate());
    this.register('WRITING', new WritingTemplate());
    this.register('ANALYSIS', new AnalysisTemplate());
    this.register('CREATIVE', new CreativeTemplate());
    this.register('RESEARCH', new ResearchTemplate());
  }

  /**
   * Register a template for a domain.
   */
  register(domain: Domain, template: BaseDomainTemplate): void {
    this.templates.set(domain, template);
  }

  /**
   * Get template for a specific domain.
   */
  get(domain: Domain): BaseDomainTemplate | null {
    return this.templates.get(domain) ?? null;
  }

  /**
   * Find best matching template for a prompt.
   */
  findBestMatch(prompt: string): { domain: Domain; template: BaseDomainTemplate; confidence: number } | null {
    let bestMatch: { domain: Domain; template: BaseDomainTemplate; confidence: number } | null = null;

    for (const [domain, template] of this.templates) {
      if (template.matches(prompt)) {
        const confidence = template.getMatchConfidence(prompt);
        if (!bestMatch || confidence > bestMatch.confidence) {
          bestMatch = { domain, template, confidence };
        }
      }
    }

    return bestMatch;
  }

  /**
   * Get all templates.
   */
  getAll(): Map<Domain, BaseDomainTemplate> {
    return new Map(this.templates);
  }

  /**
   * Get supported domains.
   */
  getSupportedDomains(): Domain[] {
    return Array.from(this.templates.keys());
  }
}

/**
 * Create a template registry.
 */
export function createTemplateRegistry(): TemplateRegistry {
  return new TemplateRegistry();
}
