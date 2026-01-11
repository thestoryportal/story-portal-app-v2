/**
 * Workflow mode detection layer.
 * Detects user intent from prompt content or explicit prefixes.
 */

import type {
  WorkflowMode,
  WorkflowModeDetection,
  WorkflowModeConfig,
} from '../../types/workflow.js';
import { WORKFLOW_PREFIXES } from '../../types/workflow.js';
import {
  WORKFLOW_MODE_CONFIGS,
  DEFAULT_WORKFLOW_MODE,
  WORKFLOW_AUTO_DETECT_MIN_CONFIDENCE,
} from './configs.js';

export class WorkflowModeDetector {
  private configs: Map<WorkflowMode, WorkflowModeConfig>;

  constructor() {
    this.configs = new Map(
      WORKFLOW_MODE_CONFIGS.map(c => [c.mode, c])
    );
  }

  /**
   * Detect workflow mode from prompt.
   * Priority: 1. Explicit override, 2. Prefix trigger, 3. Auto-detect
   */
  detect(input: string, override?: WorkflowMode): WorkflowModeDetection {
    // Priority 1: Explicit override from CLI or API
    if (override) {
      return {
        mode: override,
        source: 'override',
        confidence: 1.0,
        reasoning: 'Explicitly specified workflow mode',
        cleanedPrompt: input,
      };
    }

    // Priority 2: Check for prefix triggers (!spec, !bug, etc.)
    const prefixResult = this.detectFromPrefix(input);
    if (prefixResult) {
      return prefixResult;
    }

    // Priority 3: Auto-detect from content
    return this.autoDetect(input);
  }

  /**
   * Check for !prefix triggers at the start of the prompt.
   */
  private detectFromPrefix(input: string): WorkflowModeDetection | null {
    const trimmed = input.trim();

    for (const [prefix, mode] of Object.entries(WORKFLOW_PREFIXES)) {
      // Check if prompt starts with the prefix (case-insensitive)
      if (trimmed.toLowerCase().startsWith(prefix.toLowerCase())) {
        // Extract the cleaned prompt (remove prefix and leading whitespace)
        const cleanedPrompt = trimmed.slice(prefix.length).trimStart();
        return {
          mode,
          source: 'prefix',
          confidence: 1.0,
          reasoning: `Prefix trigger "${prefix}" detected`,
          cleanedPrompt,
        };
      }
    }

    return null;
  }

  /**
   * Auto-detect workflow mode from content analysis.
   */
  private autoDetect(input: string): WorkflowModeDetection {
    const scores: Array<{
      mode: WorkflowMode;
      score: number;
      reasons: string[];
    }> = [];

    const lower = input.toLowerCase();
    const inputLength = input.length;

    for (const [mode, config] of this.configs) {
      let score = 0;
      const reasons: string[] = [];

      // Check keywords (each match adds to score)
      for (const keyword of config.detectionKeywords) {
        if (lower.includes(keyword.toLowerCase())) {
          score += 0.12;
          reasons.push(`Keyword: "${keyword}"`);
        }
      }

      // Check patterns (patterns are weighted higher than keywords)
      for (const pattern of config.detectionPatterns) {
        if (pattern.test(input)) {
          score += 0.20;
          reasons.push(`Pattern: ${pattern.source.slice(0, 30)}...`);
        }
      }

      // Length-based adjustments
      if (mode === 'QUICK_TASK' && inputLength < 50) {
        score += 0.15;
        reasons.push('Short input suggests quick task');
      } else if (mode === 'SPECIFICATION' && inputLength > 200) {
        score += 0.10;
        reasons.push('Long input suggests specification');
      }

      // Cap score at 1.0
      if (score > 0) {
        scores.push({
          mode,
          score: Math.min(score, 1.0),
          reasons,
        });
      }
    }

    // Sort by score descending
    scores.sort((a, b) => b.score - a.score);

    // Return best match if confidence is sufficient
    if (scores.length > 0 && scores[0].score >= WORKFLOW_AUTO_DETECT_MIN_CONFIDENCE) {
      return {
        mode: scores[0].mode,
        source: 'auto',
        confidence: scores[0].score,
        reasoning: scores[0].reasons.slice(0, 3).join('; '),
        cleanedPrompt: input,
      };
    }

    // Default to QUICK_TASK for undetected
    return {
      mode: DEFAULT_WORKFLOW_MODE,
      source: 'default',
      confidence: 0.5,
      reasoning: 'No specific workflow mode detected, defaulting to quick task',
      cleanedPrompt: input,
    };
  }

  /**
   * Get configuration for a specific mode.
   */
  getConfig(mode: WorkflowMode): WorkflowModeConfig | undefined {
    return this.configs.get(mode);
  }

  /**
   * Check if a prefix is a valid workflow mode trigger.
   */
  isValidPrefix(prefix: string): boolean {
    return prefix.toLowerCase() in WORKFLOW_PREFIXES;
  }

  /**
   * Get all available prefixes.
   */
  getAvailablePrefixes(): string[] {
    return Object.keys(WORKFLOW_PREFIXES);
  }
}
