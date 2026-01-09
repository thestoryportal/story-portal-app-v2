/**
 * File system adapter for persistent storage.
 * Provides JSON file-based storage with atomic writes.
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, unlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';

/**
 * Default storage directory.
 */
export const DEFAULT_STORAGE_DIR = join(homedir(), '.claude', 'optimizer');

/**
 * File adapter options.
 */
export interface FileAdapterOptions {
  /** Base directory for storage */
  baseDir?: string;
  /** Pretty print JSON */
  prettyPrint?: boolean;
  /** Create directory if missing */
  createDir?: boolean;
}

/**
 * File adapter class.
 */
export class FileAdapter<T> {
  private filePath: string;
  private options: Required<FileAdapterOptions>;

  constructor(filename: string, options: FileAdapterOptions = {}) {
    this.options = {
      baseDir: options.baseDir ?? DEFAULT_STORAGE_DIR,
      prettyPrint: options.prettyPrint ?? true,
      createDir: options.createDir ?? true,
    };

    this.filePath = join(this.options.baseDir, filename);

    // Ensure directory exists
    if (this.options.createDir) {
      this.ensureDir();
    }
  }

  /**
   * Ensure storage directory exists.
   */
  private ensureDir(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
  }

  /**
   * Check if file exists.
   */
  exists(): boolean {
    return existsSync(this.filePath);
  }

  /**
   * Read data from file.
   */
  read(): T | null {
    if (!this.exists()) {
      return null;
    }

    try {
      const content = readFileSync(this.filePath, 'utf-8');
      return JSON.parse(content) as T;
    } catch (error) {
      console.error(`Error reading ${this.filePath}:`, error);
      return null;
    }
  }

  /**
   * Write data to file.
   */
  write(data: T): boolean {
    try {
      const content = this.options.prettyPrint
        ? JSON.stringify(data, null, 2)
        : JSON.stringify(data);

      // Atomic write: write to temp file first, then rename
      const tempPath = `${this.filePath}.tmp`;
      writeFileSync(tempPath, content, 'utf-8');

      // On Node.js, renameSync is atomic on most file systems
      const { renameSync } = require('node:fs');
      renameSync(tempPath, this.filePath);

      return true;
    } catch (error) {
      console.error(`Error writing ${this.filePath}:`, error);
      return false;
    }
  }

  /**
   * Update data with a modifier function.
   */
  update(modifier: (data: T | null) => T): boolean {
    const current = this.read();
    const updated = modifier(current);
    return this.write(updated);
  }

  /**
   * Delete the file.
   */
  delete(): boolean {
    if (!this.exists()) {
      return true;
    }

    try {
      unlinkSync(this.filePath);
      return true;
    } catch (error) {
      console.error(`Error deleting ${this.filePath}:`, error);
      return false;
    }
  }

  /**
   * Get the file path.
   */
  getPath(): string {
    return this.filePath;
  }

  /**
   * Get file size in bytes.
   */
  getSize(): number {
    if (!this.exists()) {
      return 0;
    }

    try {
      const { statSync } = require('node:fs');
      return statSync(this.filePath).size;
    } catch {
      return 0;
    }
  }

  /**
   * Get last modified time.
   */
  getModifiedTime(): number | null {
    if (!this.exists()) {
      return null;
    }

    try {
      const { statSync } = require('node:fs');
      return statSync(this.filePath).mtimeMs;
    } catch {
      return null;
    }
  }
}

/**
 * Create a file adapter for a specific data type.
 */
export function createFileAdapter<T>(
  filename: string,
  options?: FileAdapterOptions
): FileAdapter<T> {
  return new FileAdapter<T>(filename, options);
}

/**
 * Get the default storage directory.
 */
export function getStorageDir(): string {
  return DEFAULT_STORAGE_DIR;
}

/**
 * Ensure storage directory exists.
 */
export function ensureStorageDir(): void {
  if (!existsSync(DEFAULT_STORAGE_DIR)) {
    mkdirSync(DEFAULT_STORAGE_DIR, { recursive: true });
  }
}
