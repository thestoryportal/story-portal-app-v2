/**
 * Terminal context provider.
 * Captures terminal state and environment information.
 * Maps to spec section 3.4 - Terminal Context.
 */

import type { TerminalContext } from '../types/index.js';

/**
 * Terminal context provider.
 */
export class TerminalContextProvider {
  private lastCommand: string | null = null;
  private lastOutput: string | null = null;
  private lastExitCode: number | null = null;
  private lastCommandTimestamp: number | null = null;

  /**
   * Get terminal context for assembly.
   */
  getContext(): TerminalContext {
    return {
      cwd: process.cwd(),
      shell: this.detectShell(),
      recentCommand: this.lastCommand,
      recentOutput: this.truncateOutput(this.lastOutput),
      exitCode: this.lastExitCode,
      environment: this.getRelevantEnv(),
      terminalSize: this.getTerminalSize(),
    };
  }

  /**
   * Record a command execution.
   */
  recordCommand(command: string, output?: string, exitCode?: number): void {
    this.lastCommand = command;
    this.lastOutput = output ?? null;
    this.lastExitCode = exitCode ?? null;
    this.lastCommandTimestamp = Date.now();
  }

  /**
   * Check if there's recent terminal context.
   */
  hasRecentContext(maxAgeMs: number = 5 * 60 * 1000): boolean {
    if (!this.lastCommandTimestamp) {
      return false;
    }
    return Date.now() - this.lastCommandTimestamp < maxAgeMs;
  }

  /**
   * Detect the current shell.
   */
  private detectShell(): string | null {
    // Check SHELL environment variable
    const shell = process.env.SHELL;
    if (shell) {
      // Extract shell name from path
      const parts = shell.split('/');
      return parts[parts.length - 1];
    }

    // Check ComSpec for Windows
    if (process.env.ComSpec) {
      return process.env.ComSpec.includes('cmd') ? 'cmd' : 'powershell';
    }

    return null;
  }

  /**
   * Get relevant environment variables.
   */
  private getRelevantEnv(): Record<string, string> {
    const relevantKeys = [
      'NODE_ENV',
      'DEBUG',
      'LOG_LEVEL',
      'CI',
      'TERM',
      'LANG',
      'HOME',
      'USER',
      'PATH',
    ];

    const env: Record<string, string> = {};

    for (const key of relevantKeys) {
      const value = process.env[key];
      if (value !== undefined) {
        // Truncate PATH for brevity
        if (key === 'PATH') {
          const paths = value.split(':');
          env[key] = paths.length > 3
            ? `${paths.slice(0, 3).join(':')}... (${paths.length} entries)`
            : value;
        } else {
          env[key] = value;
        }
      }
    }

    return env;
  }

  /**
   * Get terminal size.
   */
  private getTerminalSize(): { columns: number; rows: number } | null {
    if (process.stdout.columns && process.stdout.rows) {
      return {
        columns: process.stdout.columns,
        rows: process.stdout.rows,
      };
    }
    return null;
  }

  /**
   * Truncate output for context.
   */
  private truncateOutput(output: string | null): string | null {
    if (!output) {
      return null;
    }

    const maxLength = 500;
    const maxLines = 20;

    // Split into lines
    const lines = output.split('\n');

    // Truncate lines
    if (lines.length > maxLines) {
      const truncated = [
        ...lines.slice(0, maxLines / 2),
        `... (${lines.length - maxLines} lines truncated) ...`,
        ...lines.slice(-maxLines / 2),
      ];
      output = truncated.join('\n');
    }

    // Truncate total length
    if (output.length > maxLength) {
      return output.slice(0, maxLength) + '... (truncated)';
    }

    return output;
  }

  /**
   * Check if running in a TTY.
   */
  isTTY(): boolean {
    return process.stdout.isTTY === true;
  }

  /**
   * Check if running in CI environment.
   */
  isCI(): boolean {
    return (
      process.env.CI === 'true' ||
      process.env.CONTINUOUS_INTEGRATION === 'true' ||
      process.env.GITHUB_ACTIONS === 'true' ||
      process.env.GITLAB_CI === 'true' ||
      process.env.CIRCLECI === 'true' ||
      process.env.JENKINS_URL !== undefined
    );
  }

  /**
   * Check if colors are supported.
   */
  supportsColor(): boolean {
    if (this.isCI()) {
      return true; // Most CI environments support color
    }

    if (!this.isTTY()) {
      return false;
    }

    const term = process.env.TERM;
    if (term === 'dumb') {
      return false;
    }

    return true;
  }

  /**
   * Get platform information.
   */
  getPlatform(): { os: string; arch: string; nodeVersion: string } {
    return {
      os: process.platform,
      arch: process.arch,
      nodeVersion: process.version,
    };
  }

  /**
   * Clear recent context.
   */
  clear(): void {
    this.lastCommand = null;
    this.lastOutput = null;
    this.lastExitCode = null;
    this.lastCommandTimestamp = null;
  }
}

/**
 * Create a terminal context provider.
 */
export function createTerminalContextProvider(): TerminalContextProvider {
  return new TerminalContextProvider();
}
