#!/usr/bin/env node
/**
 * Role Dispatch Hook - UserPromptSubmit
 *
 * Analyzes user prompts to detect role requests and injects appropriate role context.
 *
 * Flow:
 * 1. Receives prompt via stdin as JSON { prompt, session }
 * 2. Checks for explicit role requests (e.g., "as Frontend Developer...")
 * 3. Performs keyword matching against role index
 * 4. Classifies task type (human_primary/hybrid/ai_primary)
 * 5. Returns role injection if confidence > 0.7
 *
 * Role files are loaded from .claude/roles/*.yaml
 */

const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  confidenceThreshold: 0.7,
  rolesDir: '.claude/roles',
  debug: false,
};

// Keyword mappings for common role patterns
const KEYWORD_MAPPINGS = {
  frontend: {
    keywords: ['frontend', 'front-end', 'react', 'vue', 'angular', 'component', 'ui', 'css', 'styled', 'tailwind', 'jsx', 'tsx', 'dom', 'browser', 'responsive', 'layout', 'animation', 'state management', 'redux', 'zustand', 'hooks'],
    roleType: 'frontend-developer',
    taskType: 'hybrid',
  },
  backend: {
    keywords: ['backend', 'back-end', 'api', 'rest', 'graphql', 'database', 'sql', 'postgres', 'mysql', 'mongodb', 'redis', 'server', 'node', 'express', 'fastapi', 'django', 'flask', 'endpoint', 'controller', 'service', 'middleware', 'authentication', 'authorization'],
    roleType: 'backend-developer',
    taskType: 'hybrid',
  },
  qa: {
    keywords: ['test', 'testing', 'qa', 'quality', 'jest', 'pytest', 'cypress', 'playwright', 'e2e', 'unit test', 'integration test', 'coverage', 'assertion', 'mock', 'stub', 'fixture', 'regression', 'bug', 'defect'],
    roleType: 'qa-engineer',
    taskType: 'ai_primary',
  },
  architect: {
    keywords: ['architecture', 'architect', 'design', 'system design', 'scalability', 'microservices', 'monolith', 'pattern', 'structure', 'schema', 'diagram', 'adr', 'decision record', 'trade-off', 'technical debt', 'refactor', 'migration'],
    roleType: 'software-architect',
    taskType: 'human_primary',
  },
  devops: {
    keywords: ['devops', 'deploy', 'deployment', 'infrastructure', 'ci', 'cd', 'pipeline', 'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'aws', 'gcp', 'azure', 'cloud', 'container', 'helm', 'monitoring', 'logging', 'prometheus', 'grafana'],
    roleType: 'devops-engineer',
    taskType: 'hybrid',
  },
  security: {
    keywords: ['security', 'secure', 'vulnerability', 'cve', 'owasp', 'xss', 'csrf', 'injection', 'authentication', 'oauth', 'jwt', 'encryption', 'ssl', 'tls', 'penetration', 'audit', 'compliance'],
    roleType: 'security-engineer',
    taskType: 'human_primary',
  },
  data: {
    keywords: ['data', 'analytics', 'etl', 'pipeline', 'warehouse', 'bigquery', 'snowflake', 'spark', 'pandas', 'numpy', 'ml', 'machine learning', 'model', 'training', 'dataset', 'visualization'],
    roleType: 'data-engineer',
    taskType: 'hybrid',
  },
  ux: {
    keywords: ['ux', 'user experience', 'usability', 'accessibility', 'a11y', 'wcag', 'aria', 'wireframe', 'prototype', 'figma', 'design system', 'interaction', 'modal', 'form', 'navigation', 'user flow'],
    roleType: 'ux-designer',
    taskType: 'human_primary',
  },
  docs: {
    keywords: ['documentation', 'docs', 'readme', 'api docs', 'jsdoc', 'typedoc', 'swagger', 'openapi', 'comment', 'tutorial', 'guide', 'specification', 'spec'],
    roleType: 'technical-writer',
    taskType: 'ai_primary',
  },
  fullstack: {
    keywords: ['fullstack', 'full-stack', 'full stack', 'end to end', 'e2e feature', 'complete feature'],
    roleType: 'fullstack-developer',
    taskType: 'hybrid',
  },
};

// Explicit role request patterns
const EXPLICIT_ROLE_PATTERNS = [
  /\b(?:as|acting as|be|become|switch to|use)\s+(?:a\s+)?(?:the\s+)?([a-z][a-z\s-]+(?:developer|engineer|architect|designer|writer|lead|specialist))/i,
  /\b(?:as|acting as|be|become|switch to|use)\s+(?:a\s+)?(?:the\s+)?([a-z][a-z\s-]+)\s+role/i,
  /\brole:\s*([a-z][a-z\s-]+)/i,
  /\b@([a-z][a-z-]+(?:developer|engineer|architect|designer|writer))/i,
];

/**
 * Read stdin as JSON
 */
async function readInput() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => data += chunk);
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(data || '{}'));
      } catch {
        resolve({});
      }
    });
  });
}

/**
 * Simple YAML parser for role files (handles basic YAML structure)
 */
function parseSimpleYaml(content) {
  const result = {};
  const lines = content.split('\n');
  let currentKey = null;
  let currentArray = null;

  for (const line of lines) {
    // Skip comments and empty lines
    if (line.trim().startsWith('#') || !line.trim()) continue;

    // Check for array item
    if (line.match(/^\s+-\s+/)) {
      const value = line.replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, '');
      if (currentArray && currentKey) {
        result[currentKey].push(value);
      }
      continue;
    }

    // Check for key-value pair
    const match = line.match(/^(\w+):\s*(.*)?$/);
    if (match) {
      const key = match[1];
      const value = match[2]?.trim().replace(/^["']|["']$/g, '');

      if (value === '' || value === undefined) {
        // Start of array or nested object
        result[key] = [];
        currentKey = key;
        currentArray = true;
      } else {
        result[key] = value;
        currentKey = key;
        currentArray = false;
      }
    }
  }

  return result;
}

/**
 * Load role definitions from .claude/roles/ directory
 */
function loadRoles(projectDir) {
  const rolesDir = path.join(projectDir, CONFIG.rolesDir);
  const roles = {};

  if (!fs.existsSync(rolesDir)) {
    return roles;
  }

  try {
    const files = fs.readdirSync(rolesDir)
      .filter(f => f.endsWith('.yaml') || f.endsWith('.yml'));

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(rolesDir, file), 'utf8');
        const role = parseSimpleYaml(content);
        const roleId = path.basename(file, path.extname(file));
        roles[roleId] = {
          ...role,
          id: roleId,
          file: file,
        };
      } catch (e) {
        // Skip malformed files
      }
    }
  } catch (e) {
    // Roles directory not accessible
  }

  return roles;
}

/**
 * Extract explicit role request from prompt
 */
function extractExplicitRole(prompt) {
  for (const pattern of EXPLICIT_ROLE_PATTERNS) {
    const match = prompt.match(pattern);
    if (match) {
      const roleName = match[1].trim().toLowerCase().replace(/\s+/g, '-');
      return {
        explicit: true,
        roleName: roleName,
        confidence: 0.95,
      };
    }
  }
  return null;
}

/**
 * Calculate keyword match score for a role category
 */
function calculateKeywordScore(prompt, category) {
  const promptLower = prompt.toLowerCase();
  const { keywords } = category;

  let matchCount = 0;
  let totalWeight = 0;
  const matchedKeywords = [];

  for (const keyword of keywords) {
    const keywordLower = keyword.toLowerCase();
    // Use word boundary matching for accuracy
    const regex = new RegExp(`\\b${keywordLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (regex.test(promptLower)) {
      matchCount++;
      // Longer keywords get more weight
      const weight = Math.min(keyword.length / 5, 2);
      totalWeight += weight;
      matchedKeywords.push(keyword);
    }
  }

  // Calculate confidence based on matches and weights
  const baseScore = matchCount / Math.min(keywords.length, 5);
  const weightedScore = totalWeight / 5;
  const confidence = Math.min((baseScore + weightedScore) / 2, 1.0);

  return {
    matchCount,
    totalWeight,
    confidence,
    matchedKeywords,
  };
}

/**
 * Match prompt against keyword mappings
 */
function matchKeywords(prompt) {
  const results = [];

  for (const [category, data] of Object.entries(KEYWORD_MAPPINGS)) {
    const score = calculateKeywordScore(prompt, data);
    if (score.matchCount > 0) {
      results.push({
        category,
        roleType: data.roleType,
        taskType: data.taskType,
        ...score,
      });
    }
  }

  // Sort by confidence descending
  results.sort((a, b) => b.confidence - a.confidence);
  return results;
}

/**
 * Match prompt against loaded role definitions
 */
function matchRoleDefinitions(prompt, roles) {
  const promptLower = prompt.toLowerCase();
  const results = [];

  for (const [roleId, role] of Object.entries(roles)) {
    let confidence = 0;
    const matchedItems = [];

    // Match against role name
    const roleName = (role.name || roleId).toLowerCase();
    if (promptLower.includes(roleName)) {
      confidence += 0.4;
      matchedItems.push(`name:${roleName}`);
    }

    // Match against keywords
    const keywords = role.keywords || [];
    let keywordMatches = 0;
    for (const keyword of keywords) {
      if (promptLower.includes(keyword.toLowerCase())) {
        keywordMatches++;
        matchedItems.push(`keyword:${keyword}`);
      }
    }
    if (keywords.length > 0) {
      confidence += (keywordMatches / keywords.length) * 0.4;
    }

    // Match against responsibilities
    const responsibilities = role.responsibilities || [];
    let respMatches = 0;
    for (const resp of responsibilities) {
      // Check for key words in responsibilities
      const respWords = resp.toLowerCase().split(/\s+/).filter(w => w.length > 4);
      for (const word of respWords) {
        if (promptLower.includes(word)) {
          respMatches++;
          break;
        }
      }
    }
    if (responsibilities.length > 0) {
      confidence += (respMatches / responsibilities.length) * 0.2;
    }

    if (confidence > 0.1) {
      results.push({
        roleId,
        role,
        confidence: Math.min(confidence, 1.0),
        matchedItems,
      });
    }
  }

  // Sort by confidence descending
  results.sort((a, b) => b.confidence - a.confidence);
  return results;
}

/**
 * Classify task type based on prompt content
 */
function classifyTaskType(prompt) {
  const promptLower = prompt.toLowerCase();

  // Human-primary indicators (requires human judgment/decisions)
  const humanPrimaryIndicators = [
    'should i', 'what do you think', 'recommend', 'suggest', 'advice',
    'design decision', 'architecture decision', 'trade-off', 'pros and cons',
    'review', 'evaluate', 'assess', 'opinion'
  ];

  // AI-primary indicators (can be largely automated)
  const aiPrimaryIndicators = [
    'write', 'generate', 'create', 'implement', 'add', 'fix', 'update',
    'refactor', 'test', 'document', 'format', 'lint', 'optimize'
  ];

  let humanScore = 0;
  let aiScore = 0;

  for (const indicator of humanPrimaryIndicators) {
    if (promptLower.includes(indicator)) humanScore++;
  }

  for (const indicator of aiPrimaryIndicators) {
    if (promptLower.includes(indicator)) aiScore++;
  }

  if (humanScore > aiScore * 1.5) return 'human_primary';
  if (aiScore > humanScore * 1.5) return 'ai_primary';
  return 'hybrid';
}

/**
 * Build role injection context
 */
function buildInjectionContext(roleMatch, taskType) {
  const lines = [];

  lines.push(`<role-context role="${roleMatch.roleId || roleMatch.roleType}" confidence="${roleMatch.confidence.toFixed(2)}" task-type="${taskType}">`);

  if (roleMatch.role) {
    // From role definition file
    if (roleMatch.role.name) {
      lines.push(`Role: ${roleMatch.role.name}`);
    }
    if (roleMatch.role.description) {
      lines.push(`Description: ${roleMatch.role.description}`);
    }
    if (roleMatch.role.responsibilities?.length) {
      lines.push('');
      lines.push('Responsibilities:');
      for (const resp of roleMatch.role.responsibilities.slice(0, 5)) {
        lines.push(`- ${resp}`);
      }
    }
    if (roleMatch.role.principles?.length) {
      lines.push('');
      lines.push('Guiding Principles:');
      for (const principle of roleMatch.role.principles.slice(0, 3)) {
        lines.push(`- ${principle}`);
      }
    }
  } else {
    // From keyword mapping
    lines.push(`Role Type: ${roleMatch.roleType}`);
    if (roleMatch.matchedKeywords?.length) {
      lines.push(`Detected via: ${roleMatch.matchedKeywords.join(', ')}`);
    }
  }

  lines.push('');
  lines.push(`Task Classification: ${taskType}`);

  if (taskType === 'human_primary') {
    lines.push('Mode: Provide analysis, options, and recommendations. Wait for human decisions.');
  } else if (taskType === 'ai_primary') {
    lines.push('Mode: Proceed with implementation. Request clarification only if blocked.');
  } else {
    lines.push('Mode: Collaborate - implement where clear, consult on ambiguous decisions.');
  }

  lines.push('</role-context>');

  return lines.join('\n');
}

/**
 * Main hook logic
 */
async function main() {
  const input = await readInput();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const prompt = input.prompt || '';

  // Skip if prompt is too short or a command
  if (prompt.length < 10 || prompt.trim().startsWith('/')) {
    process.exit(0);
  }

  // 1. Check for explicit role request
  const explicitRole = extractExplicitRole(prompt);
  if (explicitRole) {
    const roles = loadRoles(projectDir);
    const taskType = classifyTaskType(prompt);

    // Try to find matching role definition
    const matchingRole = Object.entries(roles).find(([id, role]) =>
      id.toLowerCase() === explicitRole.roleName ||
      (role.name || '').toLowerCase().includes(explicitRole.roleName)
    );

    if (matchingRole) {
      const [roleId, role] = matchingRole;
      const injectionContext = buildInjectionContext({
        roleId,
        role,
        confidence: explicitRole.confidence,
      }, taskType);

      console.log(JSON.stringify({
        role_id: roleId,
        confidence: explicitRole.confidence,
        task_type: taskType,
        explicit: true,
        inject_context: injectionContext,
      }));
      process.exit(0);
    }

    // Fall back to keyword-based role type
    const keywordMatches = matchKeywords(prompt);
    if (keywordMatches.length > 0) {
      const best = keywordMatches[0];
      const injectionContext = buildInjectionContext({
        roleType: best.roleType,
        confidence: explicitRole.confidence,
        matchedKeywords: best.matchedKeywords,
      }, taskType);

      console.log(JSON.stringify({
        role_id: best.roleType,
        confidence: explicitRole.confidence,
        task_type: taskType,
        explicit: true,
        inject_context: injectionContext,
      }));
      process.exit(0);
    }
  }

  // 2. Load role definitions and check for matches
  const roles = loadRoles(projectDir);
  const roleMatches = matchRoleDefinitions(prompt, roles);

  // 3. Check keyword mappings
  const keywordMatches = matchKeywords(prompt);

  // 4. Determine best match
  let bestMatch = null;
  let source = null;

  if (roleMatches.length > 0 && roleMatches[0].confidence >= CONFIG.confidenceThreshold) {
    bestMatch = roleMatches[0];
    source = 'role_definition';
  }

  if (keywordMatches.length > 0 && keywordMatches[0].confidence >= CONFIG.confidenceThreshold) {
    if (!bestMatch || keywordMatches[0].confidence > bestMatch.confidence) {
      bestMatch = keywordMatches[0];
      source = 'keyword_mapping';
    }
  }

  // 5. If no match above threshold, exit silently
  if (!bestMatch) {
    process.exit(0);
  }

  // 6. Classify task type
  const taskType = classifyTaskType(prompt);

  // 7. Build and output injection context
  const injectionContext = buildInjectionContext(bestMatch, taskType);

  console.log(JSON.stringify({
    role_id: bestMatch.roleId || bestMatch.roleType,
    confidence: bestMatch.confidence,
    task_type: taskType,
    source: source,
    inject_context: injectionContext,
  }));

  process.exit(0);
}

main().catch(() => {
  // Silent failure
  process.exit(0);
});
