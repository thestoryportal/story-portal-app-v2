/**
 * Role Context Adapter for L13 Role Management Layer
 *
 * Provides integration with the L13 RoleContextBuilder service for assembling
 * role contexts including skills, project context, and constraints.
 *
 * Supports two modes:
 * 1. HTTP API mode - calls L13 service endpoints
 * 2. File-based mode - stores data in .claude/contexts/roles/ files
 */

import { promises as fs } from 'fs';
import * as path from 'path';

// Types matching L13 role models
export interface Skill {
  name: string;
  level: 'novice' | 'intermediate' | 'advanced' | 'expert';
  description?: string;
  keywords: string[];
  weight: number;
}

export interface RoleTemplate {
  id: string;
  name: string;
  department: string;
  description: string;
  role_type: 'human_primary' | 'hybrid' | 'ai_primary';
  status: 'active' | 'inactive' | 'deprecated' | 'pending_approval';
  skills: Skill[];
  responsibilities: string[];
  constraints: Record<string, unknown>;
  token_budget: number;
  priority: number;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface RoleContext {
  role: RoleTemplate;
  system_prompt: string;
  skill_context: string;
  project_context: string;
  constraints_context: string;
  examples: string[];
  token_count: number;
  token_budget: number;
  budget_utilization: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProjectContext {
  project_id: string;
  project_name: string;
  description?: string;
  tech_stack: string[];
  key_paths: Record<string, string>;
  services: Record<string, string>;
  hard_rules: string[];
  active_task_id?: string;
}

export interface HandoffArtifact {
  id: string;
  from_role_id: string;
  to_role_id: string;
  status: 'pending' | 'acknowledged' | 'rejected' | 'completed';
  artifacts: Array<{
    type: string;
    path?: string;
    content?: string;
    metadata?: Record<string, unknown>;
  }>;
  context_snapshot?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  acknowledged_at?: string;
}

export interface RoleContextAdapterConfig {
  mode?: 'http' | 'file';
  apiUrl?: string;
  contextsDir?: string;
}

/**
 * Role Context Adapter
 *
 * Integrates with L13 RoleContextBuilder for role-aware context management.
 */
export class RoleContextAdapter {
  private config: Required<RoleContextAdapterConfig>;
  private roleCache: Map<string, RoleTemplate> = new Map();
  private handoffCache: Map<string, HandoffArtifact> = new Map();
  private qualityCheckpoints: Map<string, Array<{ name: string; score: number; timestamp: string }>> = new Map();

  constructor(config: RoleContextAdapterConfig = {}) {
    this.config = {
      mode: config.mode || 'file',
      apiUrl: config.apiUrl || process.env.L13_API_URL || 'http://localhost:8013',
      contextsDir: config.contextsDir || process.env.CONTEXTS_DIR || '.claude/contexts',
    };
  }

  async initialize(): Promise<void> {
    if (this.config.mode === 'file') {
      // Ensure roles directory exists
      const rolesDir = path.join(this.config.contextsDir, 'roles');
      const handoffsDir = path.join(this.config.contextsDir, 'handoffs');
      const qualityDir = path.join(this.config.contextsDir, 'quality');

      await fs.mkdir(rolesDir, { recursive: true });
      await fs.mkdir(handoffsDir, { recursive: true });
      await fs.mkdir(qualityDir, { recursive: true });

      // Load existing roles into cache
      await this.loadRolesFromFiles();
    }
    console.error('[RoleContextAdapter] Initialized in', this.config.mode, 'mode');
  }

  private async loadRolesFromFiles(): Promise<void> {
    const rolesDir = path.join(this.config.contextsDir, 'roles');
    try {
      const files = await fs.readdir(rolesDir);
      for (const file of files) {
        if (file.endsWith('.json')) {
          const content = await fs.readFile(path.join(rolesDir, file), 'utf-8');
          const role = JSON.parse(content) as RoleTemplate;
          this.roleCache.set(role.id, role);
        }
      }
    } catch {
      // Directory may not exist yet
    }
  }

  /**
   * Get role context with optional skill loading and project context
   */
  async getRoleContext(params: {
    role_id: string;
    include_skills?: boolean;
    project_context?: boolean;
    max_skill_tokens?: number;
  }): Promise<{
    role: RoleTemplate;
    skills: Skill[];
    project_overlay: ProjectContext | null;
    total_tokens: number;
  }> {
    const { role_id, include_skills = true, project_context = false, max_skill_tokens = 2000 } = params;

    if (this.config.mode === 'http') {
      return this.getRoleContextViaHttp(params);
    }

    // File-based implementation
    let role = this.roleCache.get(role_id);

    if (!role) {
      // Try to load from file
      const rolePath = path.join(this.config.contextsDir, 'roles', `${role_id}.json`);
      try {
        const content = await fs.readFile(rolePath, 'utf-8');
        role = JSON.parse(content) as RoleTemplate;
        this.roleCache.set(role_id, role);
      } catch {
        // Create a default role if not found
        role = this.createDefaultRole(role_id);
        await this.saveRole(role);
      }
    }

    // Filter skills based on token budget
    let skills: Skill[] = [];
    let skillTokens = 0;
    if (include_skills && role.skills) {
      const sortedSkills = [...role.skills].sort((a, b) => b.weight - a.weight);
      for (const skill of sortedSkills) {
        const skillText = `${skill.name}: ${skill.description || ''} (${skill.level})`;
        const tokens = this.estimateTokens(skillText);
        if (skillTokens + tokens <= max_skill_tokens) {
          skills.push(skill);
          skillTokens += tokens;
        }
      }
    }

    // Load project context if requested
    let project_overlay: ProjectContext | null = null;
    let projectTokens = 0;
    if (project_context) {
      project_overlay = await this.loadProjectContext();
      if (project_overlay) {
        projectTokens = this.estimateTokens(JSON.stringify(project_overlay));
      }
    }

    // Calculate total tokens
    const roleTokens = this.estimateTokens(JSON.stringify(role));
    const total_tokens = roleTokens + skillTokens + projectTokens;

    return {
      role,
      skills,
      project_overlay,
      total_tokens,
    };
  }

  private async getRoleContextViaHttp(params: {
    role_id: string;
    include_skills?: boolean;
    project_context?: boolean;
    max_skill_tokens?: number;
  }): Promise<{
    role: RoleTemplate;
    skills: Skill[];
    project_overlay: ProjectContext | null;
    total_tokens: number;
  }> {
    const response = await fetch(`${this.config.apiUrl}/roles/${params.role_id}/context`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        include_skills: params.include_skills ?? true,
        project_context: params.project_context ?? false,
        max_skill_tokens: params.max_skill_tokens ?? 2000,
      }),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`L13 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<{
      role: RoleTemplate;
      skills: Skill[];
      project_overlay: ProjectContext | null;
      total_tokens: number;
    }>;
  }

  /**
   * Switch from one role to another with handoff
   */
  async switchRole(params: {
    from_role_id: string;
    to_role_id: string;
    handoff_artifacts?: Array<{
      type: string;
      path?: string;
      content?: string;
      metadata?: Record<string, unknown>;
    }>;
    preserve_context?: boolean;
  }): Promise<{
    success: boolean;
    new_context: RoleContext;
    handoff_id: string;
  }> {
    const { from_role_id, to_role_id, handoff_artifacts = [], preserve_context = true } = params;

    if (this.config.mode === 'http') {
      return this.switchRoleViaHttp(params);
    }

    // File-based implementation
    const handoff_id = `handoff-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

    // Save current role state
    if (preserve_context) {
      const fromRole = this.roleCache.get(from_role_id);
      if (fromRole) {
        await this.saveRoleState(from_role_id, {
          role: fromRole,
          timestamp: new Date().toISOString(),
          handoff_to: to_role_id,
        });
      }
    }

    // Create handoff artifact
    const handoff: HandoffArtifact = {
      id: handoff_id,
      from_role_id,
      to_role_id,
      status: 'pending',
      artifacts: handoff_artifacts,
      context_snapshot: preserve_context ? await this.getCurrentContextSnapshot() : undefined,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    await this.saveHandoff(handoff);
    this.handoffCache.set(handoff_id, handoff);

    // Load new role context
    const { role, skills, project_overlay, total_tokens } = await this.getRoleContext({
      role_id: to_role_id,
      include_skills: true,
      project_context: true,
    });

    const new_context: RoleContext = {
      role,
      system_prompt: this.buildSystemPrompt(role),
      skill_context: this.buildSkillContext(skills),
      project_context: project_overlay ? JSON.stringify(project_overlay) : '',
      constraints_context: this.buildConstraintsContext(role.constraints),
      examples: [],
      token_count: total_tokens,
      token_budget: role.token_budget,
      budget_utilization: total_tokens / role.token_budget,
      metadata: {
        handoff_id,
        from_role_id,
        preserved_context: preserve_context,
      },
      created_at: new Date().toISOString(),
    };

    return {
      success: true,
      new_context,
      handoff_id,
    };
  }

  private async switchRoleViaHttp(params: {
    from_role_id: string;
    to_role_id: string;
    handoff_artifacts?: Array<{
      type: string;
      path?: string;
      content?: string;
      metadata?: Record<string, unknown>;
    }>;
    preserve_context?: boolean;
  }): Promise<{
    success: boolean;
    new_context: RoleContext;
    handoff_id: string;
  }> {
    const response = await fetch(`${this.config.apiUrl}/roles/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      throw new Error(`L13 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<{
      success: boolean;
      new_context: RoleContext;
      handoff_id: string;
    }>;
  }

  /**
   * Track handoff status and actions
   */
  async trackHandoff(params: {
    handoff_id: string;
    action: 'create' | 'acknowledge' | 'reject';
  }): Promise<{
    handoff: HandoffArtifact;
    status: string;
  }> {
    const { handoff_id, action } = params;

    if (this.config.mode === 'http') {
      return this.trackHandoffViaHttp(params);
    }

    // File-based implementation
    let handoff = this.handoffCache.get(handoff_id);

    if (!handoff) {
      // Try to load from file
      const handoffPath = path.join(this.config.contextsDir, 'handoffs', `${handoff_id}.json`);
      try {
        const content = await fs.readFile(handoffPath, 'utf-8');
        handoff = JSON.parse(content) as HandoffArtifact;
        this.handoffCache.set(handoff_id, handoff);
      } catch {
        throw new Error(`Handoff not found: ${handoff_id}`);
      }
    }

    // Update status based on action
    const now = new Date().toISOString();
    switch (action) {
      case 'acknowledge':
        handoff.status = 'acknowledged';
        handoff.acknowledged_at = now;
        break;
      case 'reject':
        handoff.status = 'rejected';
        break;
      case 'create':
        // Already created, just return current state
        break;
    }

    handoff.updated_at = now;
    await this.saveHandoff(handoff);
    this.handoffCache.set(handoff_id, handoff);

    return {
      handoff,
      status: handoff.status,
    };
  }

  private async trackHandoffViaHttp(params: {
    handoff_id: string;
    action: 'create' | 'acknowledge' | 'reject';
  }): Promise<{
    handoff: HandoffArtifact;
    status: string;
  }> {
    const response = await fetch(`${this.config.apiUrl}/handoffs/${params.handoff_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: params.action }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error(`L13 API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<{
      handoff: HandoffArtifact;
      status: string;
    }>;
  }

  /**
   * Checkpoint quality during execution
   */
  async checkpointQuality(params: {
    execution_id: string;
    checkpoint_name: string;
    quality_score: number;
  }): Promise<{
    action: 'STOP' | 'CONTINUE' | 'ESCALATE';
    message: string;
  }> {
    const { execution_id, checkpoint_name, quality_score } = params;

    // Track the checkpoint
    const checkpoints = this.qualityCheckpoints.get(execution_id) || [];
    checkpoints.push({
      name: checkpoint_name,
      score: quality_score,
      timestamp: new Date().toISOString(),
    });
    this.qualityCheckpoints.set(execution_id, checkpoints);

    // Save to file
    await this.saveQualityCheckpoint(execution_id, checkpoints);

    // Determine action based on score
    let action: 'STOP' | 'CONTINUE' | 'ESCALATE';
    let message: string;

    if (quality_score >= 0.8) {
      action = 'CONTINUE';
      message = `Quality checkpoint "${checkpoint_name}" passed with score ${quality_score}. Proceeding.`;
    } else if (quality_score >= 0.5) {
      action = 'ESCALATE';
      message = `Quality checkpoint "${checkpoint_name}" at ${quality_score}. Human review recommended.`;
    } else {
      action = 'STOP';
      message = `Quality checkpoint "${checkpoint_name}" failed with score ${quality_score}. Stopping execution.`;
    }

    // Check for declining trend
    if (checkpoints.length >= 3) {
      const recent = checkpoints.slice(-3);
      const declining = recent.every((c, i) => i === 0 || c.score < recent[i - 1].score);
      if (declining && action !== 'STOP') {
        action = 'ESCALATE';
        message += ' Warning: Quality scores are declining.';
      }
    }

    return { action, message };
  }

  // Helper methods

  private createDefaultRole(role_id: string): RoleTemplate {
    return {
      id: role_id,
      name: role_id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      department: 'General',
      description: `Default role template for ${role_id}`,
      role_type: 'hybrid',
      status: 'active',
      skills: [],
      responsibilities: [],
      constraints: {},
      token_budget: 4000,
      priority: 5,
      tags: [],
      metadata: { auto_generated: true },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  private async saveRole(role: RoleTemplate): Promise<void> {
    const rolePath = path.join(this.config.contextsDir, 'roles', `${role.id}.json`);
    await fs.writeFile(rolePath, JSON.stringify(role, null, 2));
    this.roleCache.set(role.id, role);
  }

  private async saveRoleState(role_id: string, state: Record<string, unknown>): Promise<void> {
    const statePath = path.join(this.config.contextsDir, 'roles', `${role_id}.state.json`);
    await fs.writeFile(statePath, JSON.stringify(state, null, 2));
  }

  private async saveHandoff(handoff: HandoffArtifact): Promise<void> {
    const handoffPath = path.join(this.config.contextsDir, 'handoffs', `${handoff.id}.json`);
    await fs.writeFile(handoffPath, JSON.stringify(handoff, null, 2));
  }

  private async saveQualityCheckpoint(
    execution_id: string,
    checkpoints: Array<{ name: string; score: number; timestamp: string }>
  ): Promise<void> {
    const qualityPath = path.join(this.config.contextsDir, 'quality', `${execution_id}.json`);
    await fs.writeFile(qualityPath, JSON.stringify({ execution_id, checkpoints }, null, 2));
  }

  private async loadProjectContext(): Promise<ProjectContext | null> {
    const globalPath = path.join(this.config.contextsDir, '_registry.json');
    try {
      const content = await fs.readFile(globalPath, 'utf-8');
      const registry = JSON.parse(content);
      return {
        project_id: registry.projectId || 'unknown',
        project_name: registry.projectName || 'Unknown Project',
        description: registry.description,
        tech_stack: registry.techStack || [],
        key_paths: registry.keyPaths || {},
        services: registry.services || {},
        hard_rules: registry.hardRules || [],
        active_task_id: registry.activeTaskId,
      };
    } catch {
      return null;
    }
  }

  private async getCurrentContextSnapshot(): Promise<Record<string, unknown>> {
    const hotContextPath = path.join(this.config.contextsDir, '_hot_context.json');
    try {
      const content = await fs.readFile(hotContextPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return {};
    }
  }

  private buildSystemPrompt(role: RoleTemplate): string {
    const lines = [
      `# Role: ${role.name}`,
      `Department: ${role.department}`,
      '',
      '## Description',
      role.description,
      '',
    ];

    if (role.responsibilities.length > 0) {
      lines.push('## Responsibilities');
      lines.push(...role.responsibilities.map((r) => `- ${r}`));
      lines.push('');
    }

    lines.push('## Role Classification');
    lines.push(`Type: ${role.role_type}`);
    lines.push(`Priority: ${role.priority}/10`);
    lines.push('');

    return lines.join('\n');
  }

  private buildSkillContext(skills: Skill[]): string {
    if (skills.length === 0) return '';

    const lines = ['## Skills and Expertise', ''];

    for (const skill of skills) {
      lines.push(`### ${skill.name} (${skill.level})`);
      if (skill.description) {
        lines.push(skill.description);
      }
      if (skill.keywords.length > 0) {
        lines.push(`Keywords: ${skill.keywords.join(', ')}`);
      }
      lines.push('');
    }

    return lines.join('\n');
  }

  private buildConstraintsContext(constraints: Record<string, unknown>): string {
    if (Object.keys(constraints).length === 0) return '';

    const lines = ['## Constraints and Guidelines', ''];

    const categories: Record<string, string> = {
      must: 'Must Do',
      must_not: 'Must Not Do',
      should: 'Should Do',
      avoid: 'Avoid',
      limits: 'Limits',
      permissions: 'Permissions',
    };

    for (const [key, label] of Object.entries(categories)) {
      if (key in constraints) {
        const value = constraints[key];
        if (Array.isArray(value)) {
          lines.push(`### ${label}`);
          lines.push(...value.map((item) => `- ${item}`));
          lines.push('');
        } else {
          lines.push(`### ${label}`);
          lines.push(String(value));
          lines.push('');
        }
      }
    }

    return lines.join('\n');
  }

  private estimateTokens(text: string): number {
    if (!text) return 0;
    // Conservative estimate: 4 characters per token
    return Math.ceil(text.length / 4);
  }

  async close(): Promise<void> {
    this.roleCache.clear();
    this.handoffCache.clear();
    this.qualityCheckpoints.clear();
  }
}
