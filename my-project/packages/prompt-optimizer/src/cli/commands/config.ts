/**
 * Config command for managing optimizer configuration.
 */

import { FileAdapter, createFileAdapter, DEFAULT_STORAGE_DIR } from '../../storage/file-adapter.js';
import type { OptimizerConfig, BehaviorConfig, LimitsConfig, DisplayConfig } from '../../types/index.js';
import { Output } from '../output.js';

/**
 * Default configuration.
 */
const DEFAULT_CONFIG: OptimizerConfig = {
  behavior: {
    autoOptimize: true,
    confirmBeforeOptimize: false,
    passThreshold: 0.85,
    maxPasses: 3,
    enableLearning: true,
    enableCaching: true,
    respectProjectConfig: true,
  },
  limits: {
    maxPromptLength: 10000,
    maxOptimizedLength: 15000,
    maxHistoryEntries: 500,
    maxCacheEntries: 1000,
    cacheRetentionDays: 30,
  },
  context: {
    enableSessionContext: true,
    enableProjectContext: true,
    enableUserContext: true,
    enableTerminalContext: false,
    maxContextTokens: 2000,
  },
  learning: {
    emaAlpha: 0.1,
    minFeedbackForAdaptation: 10,
    patternThreshold: 3,
    adaptConfidenceThresholds: true,
  },
  display: {
    showDiff: true,
    showConfidence: true,
    showChanges: true,
    colorOutput: true,
    verbosity: 'normal',
  },
  metrics: {
    enabled: true,
    reportingInterval: 'daily',
    retentionDays: 90,
  },
  api: {
    defaultModel: 'claude-3-haiku-20240307',
    complexModel: 'claude-3-5-sonnet-20241022',
    timeout: 30000,
    maxRetries: 3,
  },
};

/**
 * Config command options.
 */
export interface ConfigOptions {
  /** Show current config */
  show?: boolean;
  /** Get a specific config value */
  get?: string;
  /** Set a config value */
  set?: string;
  /** Reset to defaults */
  reset?: boolean;
  /** Output format */
  format?: 'text' | 'json';
  /** Config file path */
  file?: string;
}

/**
 * Execute config command.
 */
export async function configCommand(options: ConfigOptions = {}): Promise<void> {
  const output = new Output();
  const adapter = createFileAdapter<OptimizerConfig>(options.file ?? 'config.json');

  try {
    // Load current config
    let config = adapter.read() ?? { ...DEFAULT_CONFIG };

    // Show config
    if (options.show || (!options.get && !options.set && !options.reset)) {
      showConfig(output, config, options.format);
      return;
    }

    // Get specific value
    if (options.get) {
      getValue(output, config, options.get, options.format);
      return;
    }

    // Set value
    if (options.set) {
      config = setValue(output, config, options.set);
      adapter.write(config);
      return;
    }

    // Reset to defaults
    if (options.reset) {
      adapter.write(DEFAULT_CONFIG);
      output.success('Configuration reset to defaults');
      return;
    }
  } catch (error) {
    output.error(`Config operation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Show full configuration.
 */
function showConfig(
  output: Output,
  config: OptimizerConfig,
  format?: 'text' | 'json'
): void {
  if (format === 'json') {
    output.raw(JSON.stringify(config, null, 2));
    return;
  }

  output.header('Optimizer Configuration');
  output.newLine();

  // Behavior
  output.info('Behavior:');
  showSection(output, config.behavior);
  output.newLine();

  // Limits
  output.info('Limits:');
  showSection(output, config.limits);
  output.newLine();

  // Context
  output.info('Context:');
  showSection(output, config.context);
  output.newLine();

  // Learning
  output.info('Learning:');
  showSection(output, config.learning);
  output.newLine();

  // Display
  output.info('Display:');
  showSection(output, config.display);
  output.newLine();

  // Metrics
  output.info('Metrics:');
  showSection(output, config.metrics);
  output.newLine();

  // API
  output.info('API:');
  showSection(output, config.api);
  output.newLine();

  output.info(`Config location: ${DEFAULT_STORAGE_DIR}/config.json`);
}

/**
 * Show a config section.
 */
function showSection(output: Output, section: Record<string, unknown>): void {
  for (const [key, value] of Object.entries(section)) {
    output.indent(`${key}: ${formatValue(value)}`);
  }
}

/**
 * Format a config value for display.
 */
function formatValue(value: unknown): string {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'number') {
    return value.toString();
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value);
}

/**
 * Get a specific config value.
 */
function getValue(
  output: Output,
  config: OptimizerConfig,
  path: string,
  format?: 'text' | 'json'
): void {
  const parts = path.split('.');
  let value: unknown = config;

  for (const part of parts) {
    if (value && typeof value === 'object' && part in value) {
      value = (value as Record<string, unknown>)[part];
    } else {
      output.error(`Config path not found: ${path}`);
      return;
    }
  }

  if (format === 'json') {
    output.raw(JSON.stringify(value, null, 2));
  } else {
    output.info(`${path}: ${formatValue(value)}`);
  }
}

/**
 * Set a config value.
 */
function setValue(
  output: Output,
  config: OptimizerConfig,
  assignment: string
): OptimizerConfig {
  const [path, rawValue] = assignment.split('=');

  if (!path || rawValue === undefined) {
    output.error('Invalid format. Use: config --set path.to.key=value');
    return config;
  }

  const parts = path.trim().split('.');
  let target: Record<string, unknown> = config as Record<string, unknown>;

  // Navigate to parent
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (target[part] && typeof target[part] === 'object') {
      target = target[part] as Record<string, unknown>;
    } else {
      output.error(`Config path not found: ${path}`);
      return config;
    }
  }

  const key = parts[parts.length - 1];
  const currentValue = target[key];

  // Parse value based on current type
  let newValue: unknown;
  const trimmedValue = rawValue.trim();

  if (typeof currentValue === 'boolean') {
    newValue = trimmedValue === 'true' || trimmedValue === 'yes' || trimmedValue === '1';
  } else if (typeof currentValue === 'number') {
    newValue = parseFloat(trimmedValue);
    if (isNaN(newValue as number)) {
      output.error(`Invalid number: ${trimmedValue}`);
      return config;
    }
  } else {
    newValue = trimmedValue;
  }

  target[key] = newValue;
  output.success(`Set ${path} = ${formatValue(newValue)}`);

  return config;
}

/**
 * Show config path.
 */
export async function configPathCommand(): Promise<void> {
  const output = new Output();
  output.info(`Config directory: ${DEFAULT_STORAGE_DIR}`);
}

/**
 * List available config keys.
 */
export async function configKeysCommand(): Promise<void> {
  const output = new Output();

  output.header('Available Config Keys');
  output.newLine();

  const keys = getConfigKeys(DEFAULT_CONFIG);

  for (const key of keys) {
    output.info(key);
  }
}

/**
 * Get all config keys recursively.
 */
function getConfigKeys(obj: Record<string, unknown>, prefix: string = ''): string[] {
  const keys: string[] = [];

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      keys.push(...getConfigKeys(value as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }

  return keys;
}

/**
 * Validate config.
 */
export async function validateConfigCommand(options: { file?: string } = {}): Promise<void> {
  const output = new Output();
  const adapter = createFileAdapter<OptimizerConfig>(options.file ?? 'config.json');

  const config = adapter.read();

  if (!config) {
    output.warning('No config file found, using defaults');
    return;
  }

  const issues: string[] = [];

  // Validate behavior
  if (config.behavior) {
    if (typeof config.behavior.passThreshold !== 'number' ||
        config.behavior.passThreshold < 0 ||
        config.behavior.passThreshold > 1) {
      issues.push('behavior.passThreshold must be between 0 and 1');
    }
    if (typeof config.behavior.maxPasses !== 'number' ||
        config.behavior.maxPasses < 1 ||
        config.behavior.maxPasses > 5) {
      issues.push('behavior.maxPasses must be between 1 and 5');
    }
  }

  // Validate limits
  if (config.limits) {
    if (typeof config.limits.maxPromptLength !== 'number' ||
        config.limits.maxPromptLength < 100) {
      issues.push('limits.maxPromptLength must be at least 100');
    }
  }

  // Validate learning
  if (config.learning) {
    if (typeof config.learning.emaAlpha !== 'number' ||
        config.learning.emaAlpha <= 0 ||
        config.learning.emaAlpha > 1) {
      issues.push('learning.emaAlpha must be between 0 and 1');
    }
  }

  if (issues.length > 0) {
    output.error('Configuration validation failed:');
    for (const issue of issues) {
      output.indent(`- ${issue}`);
    }
  } else {
    output.success('Configuration is valid');
  }
}
