/**
 * Workflow mode configurations with detection heuristics.
 * Each mode has keywords, patterns, and required sections.
 */

import type { WorkflowModeConfig } from '../../types/workflow.js';

export const WORKFLOW_MODE_CONFIGS: WorkflowModeConfig[] = [
  {
    mode: 'SPECIFICATION',
    description: 'New features/projects needing comprehensive detail for spec creation',
    detectionKeywords: [
      'new feature', 'implement', 'build', 'create', 'design', 'spec',
      'specification', 'requirements', 'project', 'from scratch',
      'comprehensive', 'detailed plan', 'full implementation',
      'develop', 'add support for', 'introduce'
    ],
    detectionPatterns: [
      /\b(need|want)\s+(to\s+)?(build|create|implement|design|develop)\b/i,
      /\bnew\s+(feature|functionality|capability|system|module|component)\b/i,
      /\bspec(ification)?\s+(for|of)\b/i,
      /\bfrom\s+scratch\b/i,
      /\bfull\s+(implementation|design)\b/i,
      /\badd\s+(support\s+for|a\s+new)\b/i,
    ],
    requiredSections: [
      {
        name: 'Goal/Objective',
        required: true,
        promptIfMissing: 'What is the primary goal or outcome you want to achieve?',
        detectionPattern: /\b(goal|objective|purpose|aim|outcome|achieve)\b/i,
      },
      {
        name: 'Requirements',
        required: true,
        promptIfMissing: 'What are the key requirements or constraints?',
        detectionPattern: /\b(require|must|should|constraint|need to)\b/i,
      },
      {
        name: 'Context',
        required: false,
        promptIfMissing: 'What is the existing context or system this integrates with?',
        detectionPattern: /\b(context|existing|current|integrate|alongside)\b/i,
      },
    ],
    confidenceWeightAdjustment: 1.0,
    minimalOptimization: false,
    maxExpansionRatio: 3.0,
  },

  {
    mode: 'FEEDBACK',
    description: 'Clear direction for iterations on existing work',
    detectionKeywords: [
      'change', 'update', 'modify', 'revise', 'adjust', 'tweak',
      'instead', 'rather', 'different', 'iteration', 'feedback',
      'not quite', 'almost', 'close but', 'try again', 'redo',
      'make it', 'can you', 'previous'
    ],
    detectionPatterns: [
      /\b(can\s+you|please)\s+(change|update|modify|revise|adjust|make)\b/i,
      /\b(instead\s+of|rather\s+than)\b/i,
      /\bnot\s+(quite|exactly)\s+(what|right)\b/i,
      /\btry\s+(again|differently|another)\b/i,
      /\bprevious\s+(attempt|version|iteration|output)\b/i,
      /\bmake\s+it\s+(more|less|bigger|smaller|different)\b/i,
    ],
    requiredSections: [
      {
        name: 'What to Change',
        required: true,
        promptIfMissing: 'What specific aspect needs to change?',
        detectionPattern: /\b(change|modify|update|revise|adjust|fix|alter)\b/i,
      },
      {
        name: 'Direction',
        required: true,
        promptIfMissing: 'What direction should the change go? (e.g., more/less, different style)',
        detectionPattern: /\b(should|instead|make\s+it|want|more|less)\b/i,
      },
    ],
    confidenceWeightAdjustment: 0.9,
    minimalOptimization: true,
    maxExpansionRatio: 1.5,
  },

  {
    mode: 'BUG_REPORT',
    description: 'Structured issue descriptions with repro steps',
    detectionKeywords: [
      'bug', 'error', 'issue', 'problem', 'broken', 'not working',
      'crash', 'fail', 'exception', 'unexpected', 'wrong', 'incorrect',
      'doesn\'t work', 'won\'t', 'can\'t', 'unable'
    ],
    detectionPatterns: [
      /\b(doesn't|does\s+not|won't|will\s+not|can't|cannot)\s+work\b/i,
      /\b(getting|seeing|receiving)\s+(an?\s+)?error\b/i,
      /\bexpected\s+.+\s+but\s+(got|received|saw|get)\b/i,
      /\bsteps\s+to\s+reproduce\b/i,
      /\bstack\s*trace\b/i,
      /```[\s\S]*error[\s\S]*```/i,
      /\bthrows?\s+(an?\s+)?exception\b/i,
      /\b(TypeError|ReferenceError|SyntaxError|Error):/i,
    ],
    requiredSections: [
      {
        name: 'Expected Behavior',
        required: true,
        promptIfMissing: 'What behavior did you expect to see?',
        detectionPattern: /\b(expect|should|supposed\s+to|want(ed)?)\b/i,
      },
      {
        name: 'Actual Behavior',
        required: true,
        promptIfMissing: 'What actually happened instead?',
        detectionPattern: /\b(actual|instead|but|got|receive[ds]?|see(ing)?)\b/i,
      },
      {
        name: 'Steps to Reproduce',
        required: false,
        promptIfMissing: 'How can this be reproduced? What steps lead to the issue?',
        detectionPattern: /\b(steps|reproduce|when\s+I|if\s+I|after)\b/i,
      },
    ],
    confidenceWeightAdjustment: 0.95,
    minimalOptimization: false,
    maxExpansionRatio: 2.0,
  },

  {
    mode: 'QUICK_TASK',
    description: 'Simple actions, minimal optimization needed',
    detectionKeywords: [
      'quick', 'simple', 'just', 'only', 'single', 'one thing',
      'briefly', 'short', 'fast', 'small', 'minor', 'tiny'
    ],
    detectionPatterns: [
      /^(just|only|simply)\s+/i,
      /\bquick(ly)?\s+(question|task|fix|change)\b/i,
      /\b(one|single)\s+(line|thing|question|change)\b/i,
      /\bsmall\s+(fix|change|update)\b/i,
    ],
    requiredSections: [], // No required sections for quick tasks
    confidenceWeightAdjustment: 0.8,
    minimalOptimization: true,
    maxExpansionRatio: 1.2,
  },

  {
    mode: 'ARCHITECTURE',
    description: 'Design decisions with trade-offs, constraints, requirements',
    detectionKeywords: [
      'architecture', 'design', 'structure', 'pattern', 'approach',
      'trade-off', 'tradeoff', 'pros and cons', 'decision', 'choice',
      'scalable', 'maintainable', 'system design', 'best practice',
      'organize', 'layout', 'strategy'
    ],
    detectionPatterns: [
      /\b(best|right|proper)\s+(way|approach|pattern|practice)\b/i,
      /\b(trade-?offs?|pros\s+(and|&)\s+cons)\b/i,
      /\b(architecture|design)\s+(decision|choice|pattern|question)\b/i,
      /\bhow\s+should\s+I\s+(structure|organize|design|architect|layout)\b/i,
      /\b(scalab|maintainab|extensib|testab)ility\b/i,
      /\bwhich\s+(approach|pattern|method)\b/i,
    ],
    requiredSections: [
      {
        name: 'Context/Constraints',
        required: true,
        promptIfMissing: 'What are the constraints or requirements for this decision?',
        detectionPattern: /\b(constraint|requirement|must|cannot|limit|restrict)\b/i,
      },
      {
        name: 'Goals',
        required: true,
        promptIfMissing: 'What are the key goals? (e.g., scalability, maintainability, performance)',
        detectionPattern: /\b(goal|priority|important|optimize\s+for|focus\s+on)\b/i,
      },
      {
        name: 'Trade-offs Willingness',
        required: false,
        promptIfMissing: 'What trade-offs are you willing to make?',
        detectionPattern: /\b(trade-?off|sacrifice|willing\s+to|accept|ok\s+with)\b/i,
      },
    ],
    confidenceWeightAdjustment: 1.0,
    minimalOptimization: false,
    maxExpansionRatio: 2.5,
  },

  {
    mode: 'EXPLORATION',
    description: 'Research/understand something, scope the question',
    detectionKeywords: [
      'explain', 'understand', 'learn', 'research', 'explore',
      'what is', 'how does', 'why is', 'difference between',
      'compare', 'overview', 'introduction', 'tell me about',
      'help me understand', 'curious'
    ],
    detectionPatterns: [
      /\b(what|how|why)\s+(is|does|are|do|works?)\b/i,
      /\bexplain\s+(to\s+me\s+)?/i,
      /\b(help\s+me\s+)?(understand|learn|grasp)\b/i,
      /\bdifference\s+between\b/i,
      /\b(compare|contrast)\b/i,
      /\bgive\s+(me\s+)?(an?\s+)?(overview|introduction|summary)\b/i,
      /\btell\s+me\s+(about|more)\b/i,
    ],
    requiredSections: [
      {
        name: 'Scope',
        required: false,
        promptIfMissing: 'How deep should the explanation go? (brief overview or detailed deep-dive)',
        detectionPattern: /\b(depth|detail|brief|comprehensive|deep|surface|overview)\b/i,
      },
      {
        name: 'Context/Level',
        required: false,
        promptIfMissing: 'What is your familiarity level with this topic?',
        detectionPattern: /\b(beginner|expert|familiar|new\s+to|background|experience)\b/i,
      },
    ],
    confidenceWeightAdjustment: 0.85,
    minimalOptimization: true,
    maxExpansionRatio: 1.5,
  },
];

/** Get configuration for a specific workflow mode */
export function getWorkflowModeConfig(mode: string): WorkflowModeConfig | undefined {
  return WORKFLOW_MODE_CONFIGS.find(c => c.mode === mode);
}

/** Default workflow mode when none detected */
export const DEFAULT_WORKFLOW_MODE = 'QUICK_TASK' as const;

/** Minimum confidence for auto-detection to be trusted */
export const WORKFLOW_AUTO_DETECT_MIN_CONFIDENCE = 0.4;
