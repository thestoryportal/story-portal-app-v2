/**
 * CLI argument parsing for the prompt optimizer.
 */

import { Command } from 'commander';
import type { WorkflowMode } from '../types/workflow.js';

/** Parsed CLI arguments */
export interface ParsedArgs {
  /** Input prompt (positional) */
  prompt?: string;

  // Optimization control
  /** Skip optimization */
  noOptimize: boolean;
  /** Force optimization */
  optimize: boolean;
  /** Optimization level (1-3) */
  level: 1 | 2 | 3;

  // Confirmation
  /** Always confirm */
  confirm: boolean;
  /** Never confirm */
  auto: boolean;

  // Recovery
  /** Undo last optimization */
  undo: boolean;
  /** Re-optimize */
  reoptimize: boolean;
  /** Hint for re-optimization */
  reoptimizeHint?: string;
  /** Show original prompt */
  showOriginal: boolean;

  // Display
  /** Show detailed explanation */
  explain: boolean;
  /** Quiet mode */
  quiet: boolean;
  /** JSON output for machine parsing */
  json: boolean;

  // Workflow mode
  /** Override workflow mode */
  workflowMode?: WorkflowMode;

  // Other
  /** Show statistics */
  stats: boolean;
  /** Provide feedback */
  feedback?: 'good' | 'bad';
  /** Use mock API (for testing) */
  mock: boolean;
  /** Use local LLM (Ollama) */
  local: boolean;
  /** Local LLM model name */
  localModel?: string;
  /** Local LLM server URL */
  localUrl?: string;

  // Config subcommand
  /** Config action */
  configAction?: 'show' | 'set' | 'reset';
  /** Config key to set */
  configKey?: string;
  /** Config value to set */
  configValue?: string;

  // Profile subcommand
  /** Profile action */
  profileAction?: 'show' | 'export' | 'import';
  /** Profile file path */
  profilePath?: string;
}

/** Result from parsing */
interface ParseResult {
  prompt?: string;
  opts: Record<string, unknown>;
  configAction?: ParsedArgs['configAction'];
  configKey?: string;
  configValue?: string;
  profileAction?: ParsedArgs['profileAction'];
  profilePath?: string;
}

/**
 * Parse CLI arguments.
 */
export function parseArgs(argv: string[]): ParsedArgs {
  const program = new Command();
  const result: ParseResult = { opts: {} };

  program
    .name('prompt-optimize')
    .description('Intelligent prompt optimizer for Claude CLI')
    .version('0.1.0')
    .argument('[prompt]', 'The prompt to optimize')
    // Optimization control
    .option('--no-optimize', 'Skip optimization for this prompt')
    .option('--optimize', 'Force optimization even if well-formed')
    .option('-l, --level <level>', 'Optimization level (1=fast, 2=balanced, 3=thorough)', '2')
    // Confirmation
    .option('-c, --confirm', 'Always show before/after and confirm')
    .option('-a, --auto', 'Never confirm, auto-send')
    // Recovery
    .option('-u, --undo', 'Resend original prompt (undo last optimization)')
    .option('-r, --reoptimize [hint]', 'Re-optimize with different approach')
    .option('--show-original', 'Display original before optimization')
    // Display
    .option('-e, --explain', 'Show detailed optimization explanation')
    .option('-q, --quiet', 'Minimal output')
    .option('--json', 'Output as JSON for machine parsing')
    // Workflow mode
    .option('-w, --workflow <mode>', 'Override workflow mode (spec, feedback, bug, quick, arch, explore)')
    // Other
    .option('-s, --stats', 'Show session optimization statistics')
    .option('-f, --feedback <rating>', 'Rate last optimization (good/bad)')
    .option('--mock', 'Use mock API for testing (no API key required)')
    .option('--local', 'Use local LLM via Ollama (no API key required)')
    .option('--local-model <model>', 'Local LLM model name (default: llama3.2:1b)')
    .option('--local-url <url>', 'Local LLM server URL (default: http://localhost:11434)')
    // Action handler to capture the positional argument
    .action((prompt, options) => {
      result.prompt = prompt;
      result.opts = options;
    });

  // Config subcommand
  program
    .command('config')
    .description('Manage optimizer configuration')
    .option('--show', 'Show current configuration')
    .option('--set <key=value>', 'Set a configuration value')
    .option('--reset', 'Reset to default configuration')
    .action((options) => {
      if (options.show) {
        result.configAction = 'show';
      } else if (options.set) {
        result.configAction = 'set';
        const [key, value] = options.set.split('=');
        result.configKey = key;
        result.configValue = value;
      } else if (options.reset) {
        result.configAction = 'reset';
      }
    });

  // Profile subcommand
  program
    .command('profile')
    .description('Manage user profile')
    .option('--show', 'Show current profile')
    .option('--export <path>', 'Export profile to file')
    .option('--import <path>', 'Import profile from file')
    .action((options) => {
      if (options.show) {
        result.profileAction = 'show';
      } else if (options.export) {
        result.profileAction = 'export';
        result.profilePath = options.export;
      } else if (options.import) {
        result.profileAction = 'import';
        result.profilePath = options.import;
      }
    });

  program.parse(argv);

  const opts = result.opts;

  // Parse level
  let level: 1 | 2 | 3 = 2;
  const levelVal = opts.level as string | undefined;
  if (levelVal) {
    const parsed = parseInt(levelVal, 10);
    if (parsed >= 1 && parsed <= 3) {
      level = parsed as 1 | 2 | 3;
    }
  }

  // Parse reoptimize
  let reoptimize = false;
  let reoptimizeHint: string | undefined;
  const reoptimizeVal = opts.reoptimize as string | boolean | undefined;
  if (reoptimizeVal !== undefined) {
    reoptimize = true;
    if (typeof reoptimizeVal === 'string') {
      reoptimizeHint = reoptimizeVal;
    }
  }

  // Parse feedback
  let feedback: 'good' | 'bad' | undefined;
  const feedbackVal = opts.feedback as string | undefined;
  if (feedbackVal === 'good' || feedbackVal === 'bad') {
    feedback = feedbackVal;
  }

  // Parse workflow mode
  let workflowMode: WorkflowMode | undefined;
  const workflowVal = opts.workflow as string | undefined;
  if (workflowVal) {
    const workflowMap: Record<string, WorkflowMode> = {
      spec: 'SPECIFICATION',
      specification: 'SPECIFICATION',
      feedback: 'FEEDBACK',
      bug: 'BUG_REPORT',
      quick: 'QUICK_TASK',
      arch: 'ARCHITECTURE',
      architecture: 'ARCHITECTURE',
      explore: 'EXPLORATION',
      exploration: 'EXPLORATION',
    };
    workflowMode = workflowMap[workflowVal.toLowerCase()];
  }

  return {
    prompt: result.prompt,
    noOptimize: opts.optimize === false, // --no-optimize sets optimize to false
    optimize: opts.optimize === true,
    level,
    confirm: (opts.confirm as boolean) ?? false,
    auto: (opts.auto as boolean) ?? false,
    undo: (opts.undo as boolean) ?? false,
    reoptimize,
    reoptimizeHint,
    showOriginal: (opts.showOriginal as boolean) ?? false,
    explain: (opts.explain as boolean) ?? false,
    quiet: (opts.quiet as boolean) ?? false,
    json: (opts.json as boolean) ?? false,
    workflowMode,
    stats: (opts.stats as boolean) ?? false,
    feedback,
    mock: (opts.mock as boolean) ?? false,
    local: (opts.local as boolean) ?? false,
    localModel: opts.localModel as string | undefined,
    localUrl: opts.localUrl as string | undefined,
    configAction: result.configAction,
    configKey: result.configKey,
    configValue: result.configValue,
    profileAction: result.profileAction,
    profilePath: result.profilePath,
  };
}
