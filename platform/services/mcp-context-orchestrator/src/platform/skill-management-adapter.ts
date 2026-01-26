/**
 * Skill Management Adapter for L14 Skill Library Layer
 *
 * Provides integration with the L14 SkillLibrary service for skill generation,
 * validation, retrieval, and optimization operations.
 *
 * Supports two modes:
 * 1. HTTP API mode - calls L14 service endpoints
 * 2. File-based mode - stores data in .claude/contexts/skills/ files
 */

import { promises as fs } from 'fs';
import * as path from 'path';

// Types matching L14 skill models
export interface SkillDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  yaml_content: string;
  token_count: number;
  keywords: string[];
  dependencies: string[];
  examples: string[];
  constraints: string[];
  validation_status: 'valid' | 'invalid' | 'pending';
  validation_issues: ValidationIssue[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ValidationIssue {
  severity: 'error' | 'warning' | 'info';
  field: string;
  message: string;
  suggestion?: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  suggestions: string[];
  parsed_skill?: Partial<SkillDefinition>;
}

export interface SkillAssignment {
  skill_id: string;
  role_id?: string;
  agent_id?: string;
  weight: number;
  required: boolean;
  context_modifier?: string;
  assigned_at: string;
}

export interface OptimizedSkillSet {
  skills: SkillDefinition[];
  loading_order: string[];
  total_tokens: number;
  budget_remaining: number;
  strategy_used: string;
  optimizations_applied: string[];
}

export interface GeneratedSkill {
  skill: SkillDefinition;
  yaml_content: string;
  validation: ValidationResult;
  confidence: number;
}

export interface SkillManagementAdapterConfig {
  mode?: 'http' | 'file';
  apiUrl?: string;
  contextsDir?: string;
}

/**
 * Skill Management Adapter
 *
 * Integrates with L14 SkillLibrary for skill management operations.
 */
export class SkillManagementAdapter {
  private config: Required<SkillManagementAdapterConfig>;
  private skillCache: Map<string, SkillDefinition> = new Map();
  private assignmentCache: Map<string, SkillAssignment[]> = new Map();

  constructor(config: SkillManagementAdapterConfig = {}) {
    this.config = {
      mode: config.mode || 'file',
      apiUrl: config.apiUrl || process.env.L14_API_URL || 'http://localhost:8014',
      contextsDir: config.contextsDir || process.env.CONTEXTS_DIR || '.claude/contexts',
    };
  }

  async initialize(): Promise<void> {
    if (this.config.mode === 'file') {
      // Ensure skills directory exists
      const skillsDir = path.join(this.config.contextsDir, 'skills');
      const assignmentsDir = path.join(this.config.contextsDir, 'skill-assignments');

      await fs.mkdir(skillsDir, { recursive: true });
      await fs.mkdir(assignmentsDir, { recursive: true });

      // Load existing skills into cache
      await this.loadSkillsFromFiles();
    }
    console.error('[SkillManagementAdapter] Initialized in', this.config.mode, 'mode');
  }

  private async loadSkillsFromFiles(): Promise<void> {
    const skillsDir = path.join(this.config.contextsDir, 'skills');
    try {
      const files = await fs.readdir(skillsDir);
      for (const file of files) {
        if (file.endsWith('.json')) {
          const content = await fs.readFile(path.join(skillsDir, file), 'utf-8');
          const skill = JSON.parse(content) as SkillDefinition;
          this.skillCache.set(skill.id, skill);
        }
      }
    } catch {
      // Directory may not exist yet
    }
  }

  /**
   * Generate a skill definition from role description using LLM
   */
  async generateSkill(params: {
    role_title: string;
    role_description: string;
    responsibilities?: string[];
    priority?: 'critical' | 'high' | 'medium' | 'low';
  }): Promise<GeneratedSkill> {
    const { role_title, role_description, responsibilities = [], priority = 'medium' } = params;

    if (this.config.mode === 'http') {
      return this.generateSkillViaHttp(params);
    }

    // File-based implementation (local generation without LLM)
    const skill_id = `skill-${this.slugify(role_title)}-${Date.now()}`;
    const now = new Date().toISOString();

    // Extract keywords from description and responsibilities
    const keywords = this.extractKeywords(role_description, responsibilities);

    // Build YAML content
    const yaml_content = this.buildSkillYaml({
      name: role_title,
      description: role_description,
      responsibilities,
      keywords,
      priority,
    });

    // Validate the generated YAML
    const validation = await this.validateSkill({ skill_yaml: yaml_content });

    const skill: SkillDefinition = {
      id: skill_id,
      name: role_title,
      description: role_description,
      category: this.inferCategory(role_title, keywords),
      version: '1.0.0',
      priority,
      yaml_content,
      token_count: this.estimateTokens(yaml_content),
      keywords,
      dependencies: [],
      examples: this.generateExamples(role_title, responsibilities),
      constraints: this.inferConstraints(role_description),
      validation_status: validation.valid ? 'valid' : 'invalid',
      validation_issues: validation.issues,
      metadata: {
        generated: true,
        source: 'role_description',
        responsibilities_count: responsibilities.length,
      },
      created_at: now,
      updated_at: now,
    };

    // Save to cache and file
    await this.saveSkill(skill);

    return {
      skill,
      yaml_content,
      validation,
      confidence: this.calculateConfidence(validation, responsibilities.length),
    };
  }

  private async generateSkillViaHttp(params: {
    role_title: string;
    role_description: string;
    responsibilities?: string[];
    priority?: 'critical' | 'high' | 'medium' | 'low';
  }): Promise<GeneratedSkill> {
    const response = await fetch(`${this.config.apiUrl}/skills/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`L14 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<GeneratedSkill>;
  }

  /**
   * Validate a skill definition against the schema
   */
  async validateSkill(params: {
    skill_yaml: string;
  }): Promise<ValidationResult> {
    const { skill_yaml } = params;

    if (this.config.mode === 'http') {
      return this.validateSkillViaHttp(params);
    }

    // File-based validation
    const issues: ValidationIssue[] = [];
    const suggestions: string[] = [];
    let parsed_skill: Partial<SkillDefinition> | undefined;

    try {
      // Parse YAML (simple line-based parsing for file mode)
      const parsed = this.parseSimpleYaml(skill_yaml);
      parsed_skill = {
        name: parsed.name,
        description: parsed.description,
        category: parsed.category,
        priority: parsed.priority as SkillDefinition['priority'],
        keywords: parsed.keywords ? parsed.keywords.split(',').map((k: string) => k.trim()) : [],
      };

      // Required field validation
      if (!parsed.name) {
        issues.push({
          severity: 'error',
          field: 'name',
          message: 'Skill name is required',
          suggestion: 'Add a name field with the skill identifier',
        });
      }

      if (!parsed.description) {
        issues.push({
          severity: 'error',
          field: 'description',
          message: 'Skill description is required',
          suggestion: 'Add a description explaining what this skill enables',
        });
      }

      // Warning-level validations
      if (!parsed.category) {
        issues.push({
          severity: 'warning',
          field: 'category',
          message: 'No category specified',
          suggestion: 'Add a category to help organize skills (e.g., development, analysis, communication)',
        });
      }

      if (!parsed.keywords) {
        issues.push({
          severity: 'warning',
          field: 'keywords',
          message: 'No keywords specified',
          suggestion: 'Add keywords for better skill discovery and matching',
        });
      }

      // Token count check
      const tokenCount = this.estimateTokens(skill_yaml);
      if (tokenCount > 2000) {
        issues.push({
          severity: 'warning',
          field: 'content',
          message: `Skill definition is large (${tokenCount} tokens)`,
          suggestion: 'Consider splitting into multiple focused skills for better optimization',
        });
      }

      // Suggestions for improvement
      if (parsed.description && parsed.description.length < 50) {
        suggestions.push('Consider adding more detail to the description for better context');
      }

      if (!parsed.examples) {
        suggestions.push('Adding usage examples can improve skill application accuracy');
      }

      if (!parsed.constraints) {
        suggestions.push('Defining constraints helps prevent misuse of the skill');
      }

    } catch (error) {
      issues.push({
        severity: 'error',
        field: 'yaml',
        message: `Failed to parse YAML: ${error instanceof Error ? error.message : 'Unknown error'}`,
        suggestion: 'Check YAML syntax and indentation',
      });
    }

    const valid = !issues.some(i => i.severity === 'error');

    return {
      valid,
      issues,
      suggestions,
      parsed_skill,
    };
  }

  private async validateSkillViaHttp(params: {
    skill_yaml: string;
  }): Promise<ValidationResult> {
    const response = await fetch(`${this.config.apiUrl}/skills/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`L14 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<ValidationResult>;
  }

  /**
   * Get all skills assigned to a specific role or agent
   */
  async getSkillsForRole(params: {
    role_id?: string;
    agent_id?: string;
    category?: string;
  }): Promise<{
    skills: SkillDefinition[];
    assignments: SkillAssignment[];
    total_tokens: number;
  }> {
    const { role_id, agent_id, category } = params;

    if (this.config.mode === 'http') {
      return this.getSkillsForRoleViaHttp(params);
    }

    // File-based implementation
    const assignmentKey = role_id || agent_id || 'global';
    let assignments = this.assignmentCache.get(assignmentKey);

    if (!assignments) {
      // Try to load from file
      const assignmentPath = path.join(
        this.config.contextsDir,
        'skill-assignments',
        `${assignmentKey}.json`
      );
      try {
        const content = await fs.readFile(assignmentPath, 'utf-8');
        const data = JSON.parse(content);
        assignments = data.assignments as SkillAssignment[];
        this.assignmentCache.set(assignmentKey, assignments);
      } catch {
        // No assignments found, create default
        assignments = await this.createDefaultAssignments(role_id, agent_id);
      }
    }

    // Get skills from assignments
    const skills: SkillDefinition[] = [];
    for (const assignment of assignments) {
      const skill = this.skillCache.get(assignment.skill_id);
      if (skill) {
        // Apply category filter
        if (!category || skill.category === category) {
          skills.push(skill);
        }
      }
    }

    // Filter assignments to match returned skills
    const filteredAssignments = assignments.filter(a =>
      skills.some(s => s.id === a.skill_id)
    );

    const total_tokens = skills.reduce((sum, s) => sum + s.token_count, 0);

    return {
      skills,
      assignments: filteredAssignments,
      total_tokens,
    };
  }

  private async getSkillsForRoleViaHttp(params: {
    role_id?: string;
    agent_id?: string;
    category?: string;
  }): Promise<{
    skills: SkillDefinition[];
    assignments: SkillAssignment[];
    total_tokens: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params.role_id) queryParams.set('role_id', params.role_id);
    if (params.agent_id) queryParams.set('agent_id', params.agent_id);
    if (params.category) queryParams.set('category', params.category);

    const response = await fetch(`${this.config.apiUrl}/skills/for-role?${queryParams}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`L14 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<{
      skills: SkillDefinition[];
      assignments: SkillAssignment[];
      total_tokens: number;
    }>;
  }

  /**
   * Optimize a set of skills for token budget
   */
  async optimizeSkills(params: {
    skill_ids: string[];
    token_budget: number;
    strategy?: 'token_reduction' | 'priority_loading' | 'context_aware';
    context?: string;
  }): Promise<OptimizedSkillSet> {
    const { skill_ids, token_budget, strategy = 'priority_loading', context } = params;

    if (this.config.mode === 'http') {
      return this.optimizeSkillsViaHttp(params);
    }

    // File-based optimization
    const skills: SkillDefinition[] = [];
    for (const id of skill_ids) {
      const skill = this.skillCache.get(id);
      if (skill) {
        skills.push(skill);
      } else {
        // Try to load from file
        try {
          const skillPath = path.join(this.config.contextsDir, 'skills', `${id}.json`);
          const content = await fs.readFile(skillPath, 'utf-8');
          const loadedSkill = JSON.parse(content) as SkillDefinition;
          this.skillCache.set(id, loadedSkill);
          skills.push(loadedSkill);
        } catch {
          console.error(`Skill not found: ${id}`);
        }
      }
    }

    const optimizations_applied: string[] = [];
    let optimizedSkills: SkillDefinition[];
    let loading_order: string[];

    switch (strategy) {
      case 'token_reduction':
        ({ skills: optimizedSkills, loading_order } = this.applyTokenReduction(skills, token_budget));
        optimizations_applied.push('token_reduction', 'content_trimming');
        break;

      case 'context_aware':
        ({ skills: optimizedSkills, loading_order } = this.applyContextAwareOptimization(
          skills,
          token_budget,
          context || ''
        ));
        optimizations_applied.push('context_aware', 'relevance_scoring', 'priority_loading');
        break;

      case 'priority_loading':
      default:
        ({ skills: optimizedSkills, loading_order } = this.applyPriorityLoading(skills, token_budget));
        optimizations_applied.push('priority_loading');
        break;
    }

    const total_tokens = optimizedSkills.reduce((sum, s) => sum + s.token_count, 0);
    const budget_remaining = token_budget - total_tokens;

    return {
      skills: optimizedSkills,
      loading_order,
      total_tokens,
      budget_remaining,
      strategy_used: strategy,
      optimizations_applied,
    };
  }

  private async optimizeSkillsViaHttp(params: {
    skill_ids: string[];
    token_budget: number;
    strategy?: 'token_reduction' | 'priority_loading' | 'context_aware';
    context?: string;
  }): Promise<OptimizedSkillSet> {
    const response = await fetch(`${this.config.apiUrl}/skills/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      throw new Error(`L14 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<OptimizedSkillSet>;
  }

  // Helper methods

  private slugify(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  private extractKeywords(description: string, responsibilities: string[]): string[] {
    const text = `${description} ${responsibilities.join(' ')}`;
    const words = text.toLowerCase().match(/\b[a-z]{4,}\b/g) || [];

    // Common stop words to exclude
    const stopWords = new Set([
      'that', 'this', 'with', 'from', 'have', 'will', 'been', 'were', 'they',
      'them', 'their', 'what', 'when', 'where', 'which', 'while', 'about',
      'into', 'over', 'such', 'more', 'some', 'than', 'only', 'other', 'also',
    ]);

    // Count word frequency
    const wordCount = new Map<string, number>();
    for (const word of words) {
      if (!stopWords.has(word)) {
        wordCount.set(word, (wordCount.get(word) || 0) + 1);
      }
    }

    // Return top keywords
    return Array.from(wordCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word]) => word);
  }

  private inferCategory(title: string, keywords: string[]): string {
    const lowerTitle = title.toLowerCase();
    const allText = `${lowerTitle} ${keywords.join(' ')}`;

    const categories: Record<string, string[]> = {
      development: ['code', 'develop', 'program', 'software', 'engineer', 'typescript', 'python', 'javascript'],
      analysis: ['analysis', 'analyze', 'data', 'research', 'investigate', 'evaluate'],
      design: ['design', 'architect', 'ux', 'ui', 'interface', 'visual'],
      testing: ['test', 'qa', 'quality', 'verify', 'validate'],
      operations: ['deploy', 'devops', 'infrastructure', 'cloud', 'kubernetes', 'docker'],
      communication: ['document', 'write', 'communicate', 'present', 'explain'],
      management: ['manage', 'lead', 'coordinate', 'plan', 'organize'],
    };

    for (const [category, words] of Object.entries(categories)) {
      if (words.some(w => allText.includes(w))) {
        return category;
      }
    }

    return 'general';
  }

  private generateExamples(title: string, responsibilities: string[]): string[] {
    const examples: string[] = [];

    for (const resp of responsibilities.slice(0, 3)) {
      examples.push(`When asked to ${resp.toLowerCase()}, apply ${title} expertise.`);
    }

    return examples;
  }

  private inferConstraints(description: string): string[] {
    const constraints: string[] = [];

    // Add common constraints based on description keywords
    if (description.toLowerCase().includes('security')) {
      constraints.push('Follow security best practices');
      constraints.push('Never expose sensitive information');
    }

    if (description.toLowerCase().includes('code') || description.toLowerCase().includes('develop')) {
      constraints.push('Write clean, maintainable code');
      constraints.push('Follow project coding standards');
    }

    if (description.toLowerCase().includes('document')) {
      constraints.push('Maintain clear and accurate documentation');
    }

    return constraints;
  }

  private buildSkillYaml(params: {
    name: string;
    description: string;
    responsibilities: string[];
    keywords: string[];
    priority: string;
  }): string {
    const lines = [
      '---',
      `name: ${params.name}`,
      `description: |`,
      `  ${params.description}`,
      `category: ${this.inferCategory(params.name, params.keywords)}`,
      `priority: ${params.priority}`,
      `keywords:`,
      ...params.keywords.map(k => `  - ${k}`),
    ];

    if (params.responsibilities.length > 0) {
      lines.push('responsibilities:');
      lines.push(...params.responsibilities.map(r => `  - ${r}`));
    }

    lines.push('---');

    return lines.join('\n');
  }

  private parseSimpleYaml(yaml: string): Record<string, string> {
    const result: Record<string, string> = {};
    const lines = yaml.split('\n');

    let currentKey = '';
    let inMultiline = false;
    let multilineValue = '';

    for (const line of lines) {
      if (line.trim() === '---') continue;

      if (!inMultiline && line.match(/^[a-z_]+:/)) {
        if (currentKey && multilineValue) {
          result[currentKey] = multilineValue.trim();
          multilineValue = '';
        }

        const [key, ...valueParts] = line.split(':');
        currentKey = key.trim();
        const value = valueParts.join(':').trim();

        if (value === '|') {
          inMultiline = true;
        } else if (value) {
          result[currentKey] = value;
          currentKey = '';
        }
      } else if (inMultiline) {
        if (line.startsWith('  ')) {
          multilineValue += line.slice(2) + '\n';
        } else {
          result[currentKey] = multilineValue.trim();
          multilineValue = '';
          inMultiline = false;
          currentKey = '';

          // Re-process this line
          if (line.match(/^[a-z_]+:/)) {
            const [key, ...valueParts] = line.split(':');
            currentKey = key.trim();
            const value = valueParts.join(':').trim();
            if (value && value !== '|') {
              result[currentKey] = value;
              currentKey = '';
            } else if (value === '|') {
              inMultiline = true;
            }
          }
        }
      }
    }

    if (currentKey && multilineValue) {
      result[currentKey] = multilineValue.trim();
    }

    return result;
  }

  private calculateConfidence(validation: ValidationResult, responsibilitiesCount: number): number {
    let confidence = 0.5;

    if (validation.valid) {
      confidence += 0.2;
    }

    // Reduce confidence for each error
    confidence -= validation.issues.filter(i => i.severity === 'error').length * 0.15;

    // Slight reduction for warnings
    confidence -= validation.issues.filter(i => i.severity === 'warning').length * 0.05;

    // Boost confidence if responsibilities were provided
    if (responsibilitiesCount > 0) {
      confidence += Math.min(responsibilitiesCount * 0.05, 0.2);
    }

    return Math.max(0, Math.min(1, confidence));
  }

  private async saveSkill(skill: SkillDefinition): Promise<void> {
    const skillPath = path.join(this.config.contextsDir, 'skills', `${skill.id}.json`);
    await fs.writeFile(skillPath, JSON.stringify(skill, null, 2));
    this.skillCache.set(skill.id, skill);
  }

  private async createDefaultAssignments(
    role_id?: string,
    agent_id?: string
  ): Promise<SkillAssignment[]> {
    // Get all skills from cache
    const allSkills = Array.from(this.skillCache.values());

    // Create basic assignments for all skills
    const assignments: SkillAssignment[] = allSkills.map(skill => ({
      skill_id: skill.id,
      role_id,
      agent_id,
      weight: skill.priority === 'critical' ? 1.0 :
              skill.priority === 'high' ? 0.8 :
              skill.priority === 'medium' ? 0.5 : 0.3,
      required: skill.priority === 'critical',
      assigned_at: new Date().toISOString(),
    }));

    // Cache and save
    const key = role_id || agent_id || 'global';
    this.assignmentCache.set(key, assignments);

    const assignmentPath = path.join(
      this.config.contextsDir,
      'skill-assignments',
      `${key}.json`
    );
    await fs.writeFile(assignmentPath, JSON.stringify({ role_id, agent_id, assignments }, null, 2));

    return assignments;
  }

  private applyPriorityLoading(
    skills: SkillDefinition[],
    tokenBudget: number
  ): { skills: SkillDefinition[]; loading_order: string[] } {
    // Sort by priority (critical > high > medium > low)
    const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
    const sorted = [...skills].sort(
      (a, b) => priorityOrder[b.priority] - priorityOrder[a.priority]
    );

    const result: SkillDefinition[] = [];
    let currentTokens = 0;

    for (const skill of sorted) {
      if (currentTokens + skill.token_count <= tokenBudget) {
        result.push(skill);
        currentTokens += skill.token_count;
      }
    }

    return {
      skills: result,
      loading_order: result.map(s => s.id),
    };
  }

  private applyTokenReduction(
    skills: SkillDefinition[],
    tokenBudget: number
  ): { skills: SkillDefinition[]; loading_order: string[] } {
    // First try priority loading
    const { skills: priorityLoaded, loading_order } = this.applyPriorityLoading(skills, tokenBudget);

    const totalTokens = priorityLoaded.reduce((sum, s) => sum + s.token_count, 0);

    if (totalTokens <= tokenBudget) {
      return { skills: priorityLoaded, loading_order };
    }

    // Need to trim content - create reduced versions
    const reductionFactor = tokenBudget / totalTokens;
    const reduced = priorityLoaded.map(skill => ({
      ...skill,
      // Trim description to fit budget
      description: skill.description.slice(0, Math.floor(skill.description.length * reductionFactor)),
      // Remove examples
      examples: [],
      // Recalculate token count
      token_count: Math.floor(skill.token_count * reductionFactor),
    }));

    return {
      skills: reduced,
      loading_order: reduced.map(s => s.id),
    };
  }

  private applyContextAwareOptimization(
    skills: SkillDefinition[],
    tokenBudget: number,
    context: string
  ): { skills: SkillDefinition[]; loading_order: string[] } {
    if (!context) {
      return this.applyPriorityLoading(skills, tokenBudget);
    }

    // Score skills based on relevance to context
    const contextWords = new Set(context.toLowerCase().match(/\b[a-z]{3,}\b/g) || []);

    const scored = skills.map(skill => {
      let relevanceScore = 0;

      // Check keyword overlap
      for (const keyword of skill.keywords) {
        if (contextWords.has(keyword.toLowerCase())) {
          relevanceScore += 2;
        }
      }

      // Check description overlap
      const descWords = skill.description.toLowerCase().match(/\b[a-z]{3,}\b/g) || [];
      for (const word of descWords) {
        if (contextWords.has(word)) {
          relevanceScore += 0.5;
        }
      }

      // Factor in priority
      const priorityBoost = { critical: 3, high: 2, medium: 1, low: 0 };
      relevanceScore += priorityBoost[skill.priority];

      return { skill, relevanceScore };
    });

    // Sort by relevance score
    scored.sort((a, b) => b.relevanceScore - a.relevanceScore);

    const result: SkillDefinition[] = [];
    let currentTokens = 0;

    for (const { skill } of scored) {
      if (currentTokens + skill.token_count <= tokenBudget) {
        result.push(skill);
        currentTokens += skill.token_count;
      }
    }

    return {
      skills: result,
      loading_order: result.map(s => s.id),
    };
  }

  private estimateTokens(text: string): number {
    if (!text) return 0;
    // Conservative estimate: 4 characters per token
    return Math.ceil(text.length / 4);
  }

  async close(): Promise<void> {
    this.skillCache.clear();
    this.assignmentCache.clear();
  }
}
