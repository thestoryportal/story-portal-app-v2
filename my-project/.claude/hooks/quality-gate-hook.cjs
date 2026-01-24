#!/usr/bin/env node
/**
 * Quality Gate Hook - Enforces STOP Checkpoints for Role Templates
 *
 * This hook evaluates quality checkpoints defined in role templates and
 * determines whether execution should continue, stop for human review,
 * or escalate to a different authority.
 *
 * Input (via stdin):
 * {
 *   "execution_id": "...",
 *   "role_id": "...",
 *   "checkpoint": {
 *     "name": "...",
 *     "type": "phase_complete" | "artifact_ready" | "quality_threshold" | "manual",
 *     "data": { ... }
 *   }
 * }
 *
 * Output (via stdout):
 * {
 *   "action": "STOP" | "CONTINUE" | "ESCALATE",
 *   "checkpoint_name": "...",
 *   "message": "...",
 *   "recorded": true
 * }
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// === CONFIGURATION ===
const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const CONTEXTS_DIR = path.join(PROJECT_DIR, '.claude', 'contexts');
const AGENTS_DIR = path.join(PROJECT_DIR, '.claude', 'agents');
const ROLES_CONFIG_PATH = path.join(CONTEXTS_DIR, 'roles-config.json');
const CHECKPOINTS_PATH = path.join(CONTEXTS_DIR, 'quality-checkpoints.json');

// Default checkpoint configurations by action type
const DEFAULT_ACTIONS = {
  human_review: {
    action: 'STOP',
    requiresApproval: true
  },
  auto_approve: {
    action: 'CONTINUE',
    requiresApproval: false
  },
  escalate: {
    action: 'ESCALATE',
    requiresApproval: true
  }
};

// === MAIN ===
async function main() {
  let inputData;

  try {
    const chunks = [];
    process.stdin.setEncoding('utf8');
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    inputData = JSON.parse(chunks.join(''));
  } catch (e) {
    outputError('Failed to parse input', e.message);
    process.exit(1);
  }

  const { execution_id, role_id, checkpoint } = inputData;

  // Validate required fields
  if (!execution_id || !role_id || !checkpoint) {
    outputError('Missing required fields', 'execution_id, role_id, and checkpoint are required');
    process.exit(1);
  }

  // Load role definition
  const roleConfig = loadRoleConfig(role_id);
  if (!roleConfig) {
    // No role config found - default to CONTINUE (permissive)
    const result = {
      action: 'CONTINUE',
      checkpoint_name: checkpoint.name || 'unknown',
      message: `No role configuration found for "${role_id}". Continuing without checkpoint enforcement.`,
      recorded: recordCheckpoint(execution_id, checkpoint.name, 'CONTINUE', true, {
        reason: 'no_role_config'
      })
    };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  // Find matching checkpoint definition in role
  const checkpointDef = findCheckpointDefinition(roleConfig, checkpoint);

  if (!checkpointDef) {
    // No matching checkpoint - default to CONTINUE
    const result = {
      action: 'CONTINUE',
      checkpoint_name: checkpoint.name || 'unknown',
      message: `No checkpoint definition found for "${checkpoint.name}" in role "${role_id}".`,
      recorded: recordCheckpoint(execution_id, checkpoint.name, 'CONTINUE', true, {
        reason: 'no_checkpoint_def'
      })
    };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  // Evaluate checkpoint
  const evaluation = evaluateCheckpoint(checkpointDef, checkpoint);

  // Record the checkpoint
  const recorded = recordCheckpoint(
    execution_id,
    checkpoint.name,
    evaluation.action,
    evaluation.passed,
    {
      role_id,
      checkpoint_type: checkpoint.type,
      evaluation_details: evaluation.details
    }
  );

  // Build response
  const result = {
    action: evaluation.action,
    checkpoint_name: checkpoint.name,
    message: evaluation.message,
    recorded
  };

  if (evaluation.action === 'ESCALATE') {
    result.escalation_target = evaluation.escalationTarget || 'human';
    result.escalation_reason = evaluation.escalationReason;
  }

  console.log(JSON.stringify(result, null, 2));
  process.exit(0);
}

// === ROLE LOADING ===

/**
 * Load role configuration from multiple sources:
 * 1. roles-config.json (centralized config)
 * 2. .claude/agents/{role_id}.md (agent definition with frontmatter)
 */
function loadRoleConfig(roleId) {
  // Try centralized config first
  const centralConfig = loadCentralRoleConfig(roleId);
  if (centralConfig) {
    return centralConfig;
  }

  // Try loading from agent markdown file
  const agentConfig = loadAgentConfig(roleId);
  if (agentConfig) {
    return agentConfig;
  }

  return null;
}

/**
 * Load from centralized roles-config.json
 */
function loadCentralRoleConfig(roleId) {
  try {
    if (!fs.existsSync(ROLES_CONFIG_PATH)) {
      return null;
    }

    const config = JSON.parse(fs.readFileSync(ROLES_CONFIG_PATH, 'utf8'));
    return config.roles?.[roleId] || null;
  } catch (e) {
    return null;
  }
}

/**
 * Load from agent markdown file with frontmatter
 * Parses stop_checkpoints from YAML frontmatter or structured sections
 */
function loadAgentConfig(roleId) {
  const agentPath = path.join(AGENTS_DIR, `${roleId}.md`);

  try {
    if (!fs.existsSync(agentPath)) {
      return null;
    }

    const content = fs.readFileSync(agentPath, 'utf8');

    // Parse YAML frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!frontmatterMatch) {
      return { name: roleId, stop_checkpoints: [] };
    }

    const frontmatter = parseFrontmatter(frontmatterMatch[1]);

    // Extract stop_checkpoints from frontmatter or content
    let stopCheckpoints = frontmatter.stop_checkpoints || [];

    // Also check for ## Stop Checkpoints section in content
    const sectionMatch = content.match(/## Stop Checkpoints\n([\s\S]*?)(?=\n##|$)/);
    if (sectionMatch) {
      const sectionCheckpoints = parseCheckpointsSection(sectionMatch[1]);
      stopCheckpoints = [...stopCheckpoints, ...sectionCheckpoints];
    }

    return {
      name: frontmatter.name || roleId,
      description: frontmatter.description,
      model: frontmatter.model,
      stop_checkpoints: stopCheckpoints
    };
  } catch (e) {
    return null;
  }
}

/**
 * Simple YAML frontmatter parser
 */
function parseFrontmatter(yaml) {
  const result = {};
  const lines = yaml.split('\n');

  let currentKey = null;
  let currentValue = [];
  let inArray = false;

  for (const line of lines) {
    // Key-value pair
    const kvMatch = line.match(/^(\w+):\s*(.*)$/);
    if (kvMatch) {
      // Save previous key if exists
      if (currentKey) {
        result[currentKey] = inArray ? currentValue : currentValue.join('\n');
      }

      currentKey = kvMatch[1];
      const value = kvMatch[2].trim();

      if (value === '') {
        // Could be start of array or multiline
        currentValue = [];
        inArray = false;
      } else if (value.startsWith('[') && value.endsWith(']')) {
        // Inline array
        result[currentKey] = JSON.parse(value);
        currentKey = null;
      } else {
        result[currentKey] = value.replace(/^["']|["']$/g, '');
        currentKey = null;
      }
    }
    // Array item
    else if (line.match(/^\s*-\s+/)) {
      inArray = true;
      const item = line.replace(/^\s*-\s+/, '').trim();
      currentValue.push(item);
    }
    // Continuation
    else if (currentKey && line.trim()) {
      currentValue.push(line.trim());
    }
  }

  // Save last key
  if (currentKey) {
    result[currentKey] = inArray ? currentValue : currentValue.join('\n');
  }

  return result;
}

/**
 * Parse checkpoints from markdown section
 * Format:
 * - **checkpoint_name**: action_type - description
 */
function parseCheckpointsSection(section) {
  const checkpoints = [];
  const lines = section.split('\n');

  for (const line of lines) {
    const match = line.match(/^\s*-\s+\*\*(.+?)\*\*:\s*(\w+)(?:\s*-\s*(.+))?$/);
    if (match) {
      checkpoints.push({
        name: match[1],
        action: match[2],
        description: match[3] || '',
        triggers: ['manual']
      });
    }
  }

  return checkpoints;
}

// === CHECKPOINT EVALUATION ===

/**
 * Find matching checkpoint definition for the triggered checkpoint
 */
function findCheckpointDefinition(roleConfig, checkpoint) {
  if (!roleConfig.stop_checkpoints || !Array.isArray(roleConfig.stop_checkpoints)) {
    return null;
  }

  // Match by name
  const byName = roleConfig.stop_checkpoints.find(
    cp => cp.name === checkpoint.name
  );
  if (byName) return byName;

  // Match by type/trigger
  const byType = roleConfig.stop_checkpoints.find(
    cp => cp.triggers?.includes(checkpoint.type)
  );
  if (byType) return byType;

  return null;
}

/**
 * Evaluate checkpoint and determine action
 */
function evaluateCheckpoint(checkpointDef, checkpoint) {
  const actionType = checkpointDef.action || 'human_review';
  const data = checkpoint.data || {};

  // Handle different action types
  switch (actionType) {
    case 'human_review':
      return evaluateHumanReview(checkpointDef, data);

    case 'auto_approve_if_quality_above':
      return evaluateQualityThreshold(checkpointDef, data);

    case 'auto_approve':
      return {
        action: 'CONTINUE',
        passed: true,
        message: `Checkpoint "${checkpoint.name}" auto-approved.`,
        details: { reason: 'auto_approve' }
      };

    case 'escalate':
      return evaluateEscalation(checkpointDef, data);

    default:
      // Unknown action type - default to human review
      return {
        action: 'STOP',
        passed: false,
        message: `Unknown action type "${actionType}". Stopping for human review.`,
        details: { reason: 'unknown_action' }
      };
  }
}

/**
 * Evaluate human_review checkpoint
 */
function evaluateHumanReview(checkpointDef, data) {
  const reviewPrompt = checkpointDef.review_prompt ||
    `Checkpoint "${checkpointDef.name}" requires human review.`;

  return {
    action: 'STOP',
    passed: false, // Will be marked passed when approved
    message: reviewPrompt,
    details: {
      reason: 'human_review_required',
      review_criteria: checkpointDef.criteria || [],
      artifacts: data.artifacts || []
    }
  };
}

/**
 * Evaluate quality threshold checkpoint
 * Format: auto_approve_if_quality_above_X where X is 0-100
 */
function evaluateQualityThreshold(checkpointDef, data) {
  // Parse threshold from action string or use explicit threshold
  let threshold = checkpointDef.threshold;

  if (!threshold && typeof checkpointDef.action === 'string') {
    const match = checkpointDef.action.match(/auto_approve_if_quality_above[_-]?(\d+)/);
    if (match) {
      threshold = parseInt(match[1], 10);
    }
  }

  // Default threshold
  threshold = threshold || 80;

  // Get quality score from data
  const qualityScore = data.quality_score ?? data.score ?? data.quality ?? null;

  if (qualityScore === null) {
    // No quality score provided - require human review
    return {
      action: 'STOP',
      passed: false,
      message: `No quality score provided. Human review required for "${checkpointDef.name}".`,
      details: {
        reason: 'missing_quality_score',
        threshold
      }
    };
  }

  const passed = qualityScore >= threshold;

  if (passed) {
    return {
      action: 'CONTINUE',
      passed: true,
      message: `Quality score ${qualityScore} meets threshold ${threshold}. Auto-approved.`,
      details: {
        reason: 'quality_threshold_met',
        score: qualityScore,
        threshold
      }
    };
  } else {
    return {
      action: 'STOP',
      passed: false,
      message: `Quality score ${qualityScore} below threshold ${threshold}. Human review required.`,
      details: {
        reason: 'quality_threshold_not_met',
        score: qualityScore,
        threshold
      }
    };
  }
}

/**
 * Evaluate escalation checkpoint
 */
function evaluateEscalation(checkpointDef, data) {
  const escalationTarget = checkpointDef.escalate_to || 'human';
  const escalationReason = checkpointDef.escalation_reason ||
    data.reason ||
    `Checkpoint "${checkpointDef.name}" triggered escalation.`;

  return {
    action: 'ESCALATE',
    passed: false,
    message: `Escalating to ${escalationTarget}: ${escalationReason}`,
    escalationTarget,
    escalationReason,
    details: {
      reason: 'escalation_triggered',
      target: escalationTarget
    }
  };
}

// === CHECKPOINT RECORDING ===

/**
 * Record checkpoint to quality-checkpoints.json
 */
function recordCheckpoint(executionId, checkpointName, action, passed, metadata = {}) {
  try {
    // Ensure contexts directory exists
    if (!fs.existsSync(CONTEXTS_DIR)) {
      fs.mkdirSync(CONTEXTS_DIR, { recursive: true });
    }

    // Load existing checkpoints
    let checkpoints = { records: [], summary: {} };
    try {
      if (fs.existsSync(CHECKPOINTS_PATH)) {
        checkpoints = JSON.parse(fs.readFileSync(CHECKPOINTS_PATH, 'utf8'));
      }
    } catch (e) {
      // Start fresh if file is corrupted
      checkpoints = { records: [], summary: {} };
    }

    // Ensure arrays exist
    if (!Array.isArray(checkpoints.records)) {
      checkpoints.records = [];
    }

    // Create checkpoint record
    const record = {
      id: crypto.randomUUID(),
      execution_id: executionId,
      checkpoint_name: checkpointName,
      triggered_at: new Date().toISOString(),
      action,
      passed,
      ...metadata
    };

    // Add to records
    checkpoints.records.push(record);

    // Update summary
    if (!checkpoints.summary[executionId]) {
      checkpoints.summary[executionId] = {
        total: 0,
        passed: 0,
        failed: 0,
        checkpoints: []
      };
    }

    checkpoints.summary[executionId].total++;
    if (passed) {
      checkpoints.summary[executionId].passed++;
    } else {
      checkpoints.summary[executionId].failed++;
    }
    checkpoints.summary[executionId].checkpoints.push(checkpointName);
    checkpoints.summary[executionId].last_updated = new Date().toISOString();

    // Keep only last 500 records
    if (checkpoints.records.length > 500) {
      checkpoints.records = checkpoints.records.slice(-500);
    }

    // Write back
    fs.writeFileSync(CHECKPOINTS_PATH, JSON.stringify(checkpoints, null, 2));

    return true;
  } catch (e) {
    // Log error but don't fail the hook
    console.error(`Warning: Failed to record checkpoint: ${e.message}`);
    return false;
  }
}

// === UTILITIES ===

/**
 * Output error in expected format
 */
function outputError(title, detail) {
  console.log(JSON.stringify({
    action: 'STOP',
    checkpoint_name: 'error',
    message: `${title}: ${detail}`,
    recorded: false,
    error: true
  }, null, 2));
}

// === RUN ===
main().catch(error => {
  outputError('Hook execution failed', error.message);
  process.exit(1);
});
