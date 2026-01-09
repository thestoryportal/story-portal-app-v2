/**
 * Profile command for managing user preferences and learning data.
 */

import { ProfileStore, createProfileStore } from '../../storage/profile-store.js';
import { PreferenceEngine, createPreferenceEngine } from '../../learning/preference-engine.js';
import { PatternTracker, createPatternTracker } from '../../learning/pattern-tracker.js';
import { Output } from '../output.js';

/**
 * Profile command options.
 */
export interface ProfileOptions {
  /** Show full profile */
  show?: boolean;
  /** Show statistics */
  stats?: boolean;
  /** Show patterns */
  patterns?: boolean;
  /** Reset profile */
  reset?: boolean;
  /** Export profile */
  export?: string;
  /** Import profile */
  import?: string;
  /** Output format */
  format?: 'text' | 'json';
}

/**
 * Execute profile command.
 */
export async function profileCommand(options: ProfileOptions = {}): Promise<void> {
  const output = new Output();
  const profileStore = createProfileStore();
  const preferenceEngine = createPreferenceEngine(profileStore);
  const patternTracker = createPatternTracker(profileStore);

  try {
    // Default to showing profile if no option specified
    if (options.show || (!options.stats && !options.patterns && !options.reset && !options.export && !options.import)) {
      showProfile(output, profileStore, options.format);
    }

    if (options.stats) {
      showStats(output, profileStore, options.format);
    }

    if (options.patterns) {
      showPatterns(output, profileStore, patternTracker, options.format);
    }

    if (options.reset) {
      await resetProfile(output, profileStore);
    }

    if (options.export) {
      exportProfile(output, profileStore, options.export);
    }

    if (options.import) {
      await importProfile(output, profileStore, options.import);
    }
  } catch (error) {
    output.error(`Profile operation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Show profile information.
 */
function showProfile(output: Output, store: ProfileStore, format?: 'text' | 'json'): void {
  const profile = store.export();

  if (format === 'json') {
    output.raw(JSON.stringify(profile, null, 2));
    return;
  }

  output.header('User Profile');
  output.newLine();

  output.info('Identification:');
  output.indent(`ID: ${profile.id}`);
  output.indent(`Created: ${new Date(profile.createdAt).toLocaleDateString()}`);
  output.indent(`Updated: ${new Date(profile.updatedAt).toLocaleDateString()}`);
  output.newLine();

  output.info('Style Preferences:');
  output.indent(`Verbosity: ${profile.stylePreferences.verbosity}`);
  output.indent(`Explanation Style: ${profile.stylePreferences.explanationStyle}`);
  output.indent(`Code Style: ${profile.stylePreferences.codeStyle}`);
  output.indent(`Show Tips: ${profile.stylePreferences.showTips ? 'Yes' : 'No'}`);
  output.indent(`Show Confidence: ${profile.stylePreferences.showConfidence ? 'Yes' : 'No'}`);
  output.indent(`Output Format: ${profile.stylePreferences.outputFormat}`);
  output.newLine();

  output.info('Domain Preferences:');
  if (profile.domainPreferences.preferred.length > 0) {
    output.indent(`Preferred: ${profile.domainPreferences.preferred.join(', ')}`);
  } else {
    output.indent('No preferred domains set');
  }

  const usageCounts = Object.entries(profile.domainPreferences.usageCounts);
  if (usageCounts.length > 0) {
    output.indent('Usage:');
    for (const [domain, count] of usageCounts) {
      output.indent(`  ${domain}: ${count} uses`);
    }
  }
  output.newLine();

  output.info('Custom Rules:');
  if (profile.customRules.length > 0) {
    for (const rule of profile.customRules) {
      const status = rule.enabled ? '✓' : '✗';
      output.indent(`${status} ${rule.name}: ${rule.condition} → ${rule.action}`);
    }
  } else {
    output.indent('No custom rules defined');
  }
}

/**
 * Show profile statistics.
 */
function showStats(output: Output, store: ProfileStore, format?: 'text' | 'json'): void {
  const stats = store.getStats();

  if (format === 'json') {
    output.raw(JSON.stringify(stats, null, 2));
    return;
  }

  output.header('Profile Statistics');
  output.newLine();

  output.info('Optimizations:');
  output.indent(`Total: ${stats.totalOptimizations}`);
  output.indent(`Acceptance Rate: ${(stats.acceptanceRate * 100).toFixed(1)}%`);
  output.indent(`Rejection Rate: ${(stats.rejectionRate * 100).toFixed(1)}%`);
  output.indent(`Modification Rate: ${(stats.modificationRate * 100).toFixed(1)}%`);
  output.newLine();

  output.info('Quality:');
  output.indent(`Avg Acceptance Confidence: ${(stats.avgAcceptanceConfidence * 100).toFixed(1)}%`);
  output.newLine();

  output.info('Usage:');
  output.indent(`Active Days: ${stats.activeDays}`);
  output.indent(`Avg Prompts/Day: ${stats.avgPromptsPerDay.toFixed(1)}`);
  if (stats.topDomain) {
    output.indent(`Top Domain: ${stats.topDomain}`);
  }
}

/**
 * Show learned patterns.
 */
function showPatterns(
  output: Output,
  store: ProfileStore,
  tracker: PatternTracker,
  format?: 'text' | 'json'
): void {
  const patterns = store.getCommonPatterns(20);
  const usagePatterns = tracker.getUsagePatterns();

  if (format === 'json') {
    output.raw(JSON.stringify({ patterns, usagePatterns }, null, 2));
    return;
  }

  output.header('Learned Patterns');
  output.newLine();

  output.info('Top Phrases:');
  if (patterns.length > 0) {
    for (const pattern of patterns.slice(0, 10)) {
      output.indent(`"${pattern.pattern}" (${pattern.count}x, contexts: ${pattern.contexts.join(', ')})`);
    }
  } else {
    output.indent('No patterns learned yet');
  }
  output.newLine();

  output.info('Usage Patterns:');
  if (usagePatterns.peakHours.length > 0) {
    output.indent(`Peak Hours: ${usagePatterns.peakHours.map((h) => `${h}:00`).join(', ')}`);
  }

  if (usagePatterns.topDomains.length > 0) {
    output.indent('Top Domains:');
    for (const { domain, count } of usagePatterns.topDomains.slice(0, 5)) {
      output.indent(`  ${domain}: ${count}`);
    }
  }

  if (usagePatterns.topCategories.length > 0) {
    output.indent('Top Categories:');
    for (const { category, count } of usagePatterns.topCategories) {
      output.indent(`  ${category}: ${count}`);
    }
  }
}

/**
 * Reset profile.
 */
async function resetProfile(output: Output, store: ProfileStore): Promise<void> {
  output.warning('This will reset all learned preferences and patterns.');

  // In a real CLI, we'd prompt for confirmation
  // For now, just reset
  store.reset();
  output.success('Profile reset to defaults');
}

/**
 * Export profile.
 */
function exportProfile(output: Output, store: ProfileStore, path: string): void {
  const profile = store.export();
  const json = JSON.stringify(profile, null, 2);

  // In a real implementation, we'd write to the file
  output.success(`Profile exported (${json.length} bytes)`);
  output.info(`Would write to: ${path}`);

  // Output the JSON for now
  output.raw(json);
}

/**
 * Import profile.
 */
async function importProfile(output: Output, store: ProfileStore, path: string): Promise<void> {
  // In a real implementation, we'd read from the file
  output.warning(`Would import from: ${path}`);
  output.info('Profile import requires file content');
}

/**
 * Update style preferences.
 */
export async function updateStyleCommand(
  preference: string,
  value: string
): Promise<void> {
  const output = new Output();
  const store = createProfileStore();

  const validPreferences = ['verbosity', 'explanationStyle', 'codeStyle', 'outputFormat'];

  if (!validPreferences.includes(preference)) {
    output.error(`Invalid preference: ${preference}`);
    output.info(`Valid preferences: ${validPreferences.join(', ')}`);
    return;
  }

  try {
    store.updateStylePreferences({ [preference]: value } as any);
    output.success(`Updated ${preference} to ${value}`);
  } catch (error) {
    output.error(`Failed to update preference: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Show feedback history.
 */
export async function feedbackHistoryCommand(limit: number = 10): Promise<void> {
  const output = new Output();
  const store = createProfileStore();

  const feedback = store.getRecentFeedback(limit);

  output.header(`Recent Feedback (${feedback.length})`);
  output.newLine();

  if (feedback.length === 0) {
    output.info('No feedback recorded yet');
    return;
  }

  for (const entry of feedback) {
    const date = new Date(entry.timestamp).toLocaleDateString();
    const typeIcon =
      entry.type === 'accept' ? '✓' : entry.type === 'reject' ? '✗' : '~';

    output.info(`${typeIcon} ${date} - ${entry.category} (${(entry.confidence * 100).toFixed(0)}%)`);
    output.indent(`Original: "${entry.original.slice(0, 50)}..."`);
    if (entry.comment) {
      output.indent(`Comment: ${entry.comment}`);
    }
    output.newLine();
  }
}
