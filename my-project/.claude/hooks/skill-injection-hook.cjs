#!/usr/bin/env node
/**
 * Skill Injection Hook v1.0
 *
 * Claude Code hook that loads skills for a dispatched role within a token budget.
 *
 * Input (via stdin JSON):
 * {
 *   role_id: string,        // Role identifier
 *   token_budget: number    // Optional, defaults to 3000
 * }
 *
 * Output format:
 * <role-skills role="{role_id}" tokens="{total_tokens}">
 * ## Skill: {skill_name}
 * {skill_content}
 * ...
 * </role-skills>
 *
 * Role files location:
 * - .claude/roles/{role_id}.yaml
 * - .claude/roles/**\/{role_id}.yaml (nested directories)
 *
 * Skill files location:
 * - .claude/skills/{skill_name}.md
 * - .claude/skills/**\/{skill_name}.md (nested directories)
 */

const fs = require('fs');
const path = require('path');

// === CONFIGURATION ===
const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const ROLES_DIR = path.join(PROJECT_DIR, '.claude', 'roles');
const SKILLS_DIR = path.join(PROJECT_DIR, '.claude', 'skills');
const DEFAULT_TOKEN_BUDGET = 3000;

// Approximate tokens per character (conservative estimate)
const CHARS_PER_TOKEN = 4;

// === YAML PARSER (simple, no dependencies) ===

/**
 * Simple YAML parser for role files
 * Supports:
 * - Key-value pairs
 * - Arrays (with - prefix)
 * - Nested objects (indentation-based)
 */
function parseYaml(content) {
  const lines = content.split('\n');
  const result = {};
  const stack = [{ obj: result, indent: -1 }];
  let currentArrayKey = null;
  let currentArray = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Skip empty lines and comments
    if (!line.trim() || line.trim().startsWith('#')) {
      continue;
    }

    // Calculate indentation
    const indent = line.search(/\S/);
    const trimmedLine = line.trim();

    // Handle array items
    if (trimmedLine.startsWith('- ')) {
      const value = trimmedLine.substring(2).trim();

      // Find or create the array
      if (currentArray && currentArrayKey) {
        currentArray.push(value);
      }
      continue;
    }

    // Handle key-value pairs
    const colonIndex = trimmedLine.indexOf(':');
    if (colonIndex > 0) {
      const key = trimmedLine.substring(0, colonIndex).trim();
      const rawValue = trimmedLine.substring(colonIndex + 1).trim();

      // Pop stack items with greater or equal indentation
      while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
        stack.pop();
      }

      const currentObj = stack[stack.length - 1].obj;

      if (rawValue === '' || rawValue === '|' || rawValue === '>') {
        // This could be an object or array start
        // Check next non-empty line
        let nextLineIdx = i + 1;
        while (nextLineIdx < lines.length && !lines[nextLineIdx].trim()) {
          nextLineIdx++;
        }

        if (nextLineIdx < lines.length) {
          const nextLine = lines[nextLineIdx];
          const nextTrimmed = nextLine.trim();

          if (nextTrimmed.startsWith('- ')) {
            // It's an array
            currentObj[key] = [];
            currentArray = currentObj[key];
            currentArrayKey = key;
          } else {
            // It's an object
            currentObj[key] = {};
            stack.push({ obj: currentObj[key], indent });
            currentArray = null;
            currentArrayKey = null;
          }
        }
      } else {
        // Direct value
        currentObj[key] = parseValue(rawValue);
        currentArray = null;
        currentArrayKey = null;
      }
    }
  }

  return result;
}

/**
 * Parse a YAML value (handles strings, numbers, booleans)
 */
function parseValue(value) {
  // Remove quotes if present
  if ((value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }

  // Boolean
  if (value.toLowerCase() === 'true') return true;
  if (value.toLowerCase() === 'false') return false;

  // Null
  if (value.toLowerCase() === 'null' || value === '~') return null;

  // Number
  if (!isNaN(value) && value !== '') {
    return Number(value);
  }

  return value;
}

// === FILE DISCOVERY ===

/**
 * Recursively find files matching a pattern in a directory
 */
function findFiles(dir, filename, maxDepth = 3, currentDepth = 0) {
  const results = [];

  if (currentDepth > maxDepth || !fs.existsSync(dir)) {
    return results;
  }

  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        results.push(...findFiles(fullPath, filename, maxDepth, currentDepth + 1));
      } else if (entry.isFile()) {
        // Check if filename matches (with or without extension)
        const baseName = path.basename(entry.name, path.extname(entry.name));
        if (entry.name === filename || baseName === filename) {
          results.push(fullPath);
        }
      }
    }
  } catch (e) {
    // Ignore directory read errors
  }

  return results;
}

/**
 * Find all skill files in the skills directory
 */
function discoverAllSkills() {
  const skills = new Map(); // skillName -> { path, size }

  function scanDir(dir, depth = 0) {
    if (depth > 3 || !fs.existsSync(dir)) return;

    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
          scanDir(fullPath, depth + 1);
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          const skillName = path.basename(entry.name, '.md');
          const stats = fs.statSync(fullPath);
          skills.set(skillName, {
            path: fullPath,
            size: stats.size,
            estimatedTokens: Math.ceil(stats.size / CHARS_PER_TOKEN)
          });
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }

  scanDir(SKILLS_DIR);
  return skills;
}

// === ROLE LOADING ===

/**
 * Find and load a role definition by role_id
 */
function loadRole(roleId) {
  // Try direct path first
  const directPaths = [
    path.join(ROLES_DIR, `${roleId}.yaml`),
    path.join(ROLES_DIR, `${roleId}.yml`),
  ];

  for (const rolePath of directPaths) {
    if (fs.existsSync(rolePath)) {
      try {
        const content = fs.readFileSync(rolePath, 'utf8');
        return { role: parseYaml(content), path: rolePath };
      } catch (e) {
        throw new Error(`Failed to parse role file ${rolePath}: ${e.message}`);
      }
    }
  }

  // Search recursively
  const yamlFiles = [
    ...findFiles(ROLES_DIR, `${roleId}.yaml`),
    ...findFiles(ROLES_DIR, `${roleId}.yml`),
  ];

  if (yamlFiles.length > 0) {
    try {
      const content = fs.readFileSync(yamlFiles[0], 'utf8');
      return { role: parseYaml(content), path: yamlFiles[0] };
    } catch (e) {
      throw new Error(`Failed to parse role file ${yamlFiles[0]}: ${e.message}`);
    }
  }

  return null;
}

// === SKILL LOADING ===

/**
 * Load a skill file by name
 */
function loadSkill(skillName, allSkills) {
  const skillInfo = allSkills.get(skillName);

  if (skillInfo) {
    try {
      const content = fs.readFileSync(skillInfo.path, 'utf8');
      return {
        name: skillName,
        content: content.trim(),
        tokens: Math.ceil(content.length / CHARS_PER_TOKEN),
        path: skillInfo.path
      };
    } catch (e) {
      return null;
    }
  }

  // Search for skill file
  const skillPaths = [
    path.join(SKILLS_DIR, `${skillName}.md`),
    ...findFiles(SKILLS_DIR, `${skillName}.md`),
  ];

  for (const skillPath of skillPaths) {
    if (fs.existsSync(skillPath)) {
      try {
        const content = fs.readFileSync(skillPath, 'utf8');
        return {
          name: skillName,
          content: content.trim(),
          tokens: Math.ceil(content.length / CHARS_PER_TOKEN),
          path: skillPath
        };
      } catch (e) {
        // Continue to next path
      }
    }
  }

  return null;
}

// === OUTPUT BUILDING ===

/**
 * Build the formatted skill context output
 */
function buildOutput(roleId, loadedSkills, totalTokens, errors) {
  const lines = [];

  lines.push(`<role-skills role="${roleId}" tokens="${totalTokens}">`);

  if (errors.length > 0) {
    lines.push('');
    lines.push('<!-- Skill loading warnings:');
    for (const error of errors) {
      lines.push(`  - ${error}`);
    }
    lines.push('-->');
  }

  for (const skill of loadedSkills) {
    lines.push('');
    lines.push(`## Skill: ${skill.name}`);
    lines.push('');
    lines.push(skill.content);
  }

  lines.push('');
  lines.push('</role-skills>');

  return lines.join('\n');
}

// === MAIN ===

async function main() {
  let inputData;

  // Read input from stdin
  try {
    const chunks = [];
    process.stdin.setEncoding('utf8');
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    const rawInput = chunks.join('');
    if (!rawInput.trim()) {
      console.error(JSON.stringify({ error: 'No input provided. Expected { role_id, token_budget? }' }));
      process.exit(1);
    }
    inputData = JSON.parse(rawInput);
  } catch (e) {
    console.error(JSON.stringify({ error: `Failed to parse input JSON: ${e.message}` }));
    process.exit(1);
  }

  // Extract parameters
  const roleId = inputData.role_id;
  const tokenBudget = inputData.token_budget || DEFAULT_TOKEN_BUDGET;

  if (!roleId) {
    console.error(JSON.stringify({ error: 'Missing required parameter: role_id' }));
    process.exit(1);
  }

  // Load role definition
  const roleResult = loadRole(roleId);
  if (!roleResult) {
    console.error(JSON.stringify({
      error: `Role not found: ${roleId}`,
      searched: [
        path.join(ROLES_DIR, `${roleId}.yaml`),
        `${ROLES_DIR}/**/${roleId}.yaml`
      ]
    }));
    process.exit(1);
  }

  const { role, path: rolePath } = roleResult;

  // Get required skills from role
  const coreSkills = role.core_skills || role.coreSkills || role.skills || [];

  if (!Array.isArray(coreSkills) || coreSkills.length === 0) {
    // No skills required, output empty context
    console.log(buildOutput(roleId, [], 0, ['No core_skills defined in role']));
    process.exit(0);
  }

  // Discover all available skills
  const allSkills = discoverAllSkills();

  // Load skills within token budget
  const loadedSkills = [];
  const errors = [];
  let totalTokens = 0;

  // Calculate overhead for XML wrapper (approximately)
  const wrapperOverhead = 50;
  let remainingBudget = tokenBudget - wrapperOverhead;

  // Sort skills: required skills first (in order), then by estimated size
  const skillsToLoad = [...coreSkills];

  for (const skillName of skillsToLoad) {
    if (remainingBudget <= 0) {
      errors.push(`Token budget exceeded. Skipped: ${skillName}`);
      continue;
    }

    const skill = loadSkill(skillName, allSkills);

    if (!skill) {
      errors.push(`Skill not found: ${skillName}`);
      continue;
    }

    // Check if skill fits in remaining budget
    // Add some overhead for skill header
    const skillOverhead = 30; // "## Skill: {name}\n\n"
    const skillTotalTokens = skill.tokens + skillOverhead;

    if (skillTotalTokens > remainingBudget) {
      errors.push(`Skill too large for remaining budget: ${skillName} (${skill.tokens} tokens, ${remainingBudget} remaining)`);
      continue;
    }

    loadedSkills.push(skill);
    totalTokens += skillTotalTokens;
    remainingBudget -= skillTotalTokens;
  }

  // Build and output the formatted context
  const output = buildOutput(roleId, loadedSkills, totalTokens, errors);
  console.log(output);

  process.exit(0);
}

main().catch(error => {
  console.error(JSON.stringify({
    error: `Hook failed: ${error.message}`,
    stack: error.stack
  }));
  process.exit(1);
});
