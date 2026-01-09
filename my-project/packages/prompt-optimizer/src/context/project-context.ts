/**
 * Project context provider.
 * Detects and provides project metadata from the filesystem.
 * Maps to spec section 3.2 - Project Context.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, basename } from 'node:path';
import type { ProjectContext } from '../types/index.js';

/**
 * Project context provider.
 */
export class ProjectContextProvider {
  private cachedContext: ProjectContext | null = null;
  private cachedPath: string | null = null;

  /**
   * Get project context for a directory.
   */
  async getContext(projectPath: string = process.cwd()): Promise<ProjectContext> {
    // Use cache if same path
    if (this.cachedPath === projectPath && this.cachedContext) {
      return this.cachedContext;
    }

    const context: ProjectContext = {
      name: basename(projectPath),
      type: this.detectProjectType(projectPath),
      language: this.detectLanguage(projectPath),
      framework: this.detectFramework(projectPath),
      dependencies: this.extractDependencies(projectPath),
      hasTests: this.hasTests(projectPath),
      hasCi: this.hasCi(projectPath),
    };

    this.cachedContext = context;
    this.cachedPath = projectPath;

    return context;
  }

  /**
   * Detect project type from config files.
   */
  private detectProjectType(projectPath: string): string | null {
    // Check for monorepo indicators
    if (
      existsSync(join(projectPath, 'lerna.json')) ||
      existsSync(join(projectPath, 'nx.json')) ||
      existsSync(join(projectPath, 'pnpm-workspace.yaml')) ||
      existsSync(join(projectPath, 'turbo.json'))
    ) {
      return 'monorepo';
    }

    // Check for library vs app indicators
    const packageJsonPath = join(projectPath, 'package.json');
    if (existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
        if (pkg.main || pkg.exports || pkg.types) {
          return 'library';
        }
        if (pkg.scripts?.start || pkg.scripts?.dev) {
          return 'application';
        }
      } catch {
        // Ignore parse errors
      }
    }

    return 'unknown';
  }

  /**
   * Detect primary language.
   */
  private detectLanguage(projectPath: string): string | null {
    // Check TypeScript
    if (existsSync(join(projectPath, 'tsconfig.json'))) {
      return 'typescript';
    }

    // Check Python
    if (
      existsSync(join(projectPath, 'pyproject.toml')) ||
      existsSync(join(projectPath, 'setup.py'))
    ) {
      return 'python';
    }

    // Check Rust
    if (existsSync(join(projectPath, 'Cargo.toml'))) {
      return 'rust';
    }

    // Check Go
    if (existsSync(join(projectPath, 'go.mod'))) {
      return 'go';
    }

    // Check Ruby
    if (existsSync(join(projectPath, 'Gemfile'))) {
      return 'ruby';
    }

    // Check PHP
    if (existsSync(join(projectPath, 'composer.json'))) {
      return 'php';
    }

    // Check Java
    if (
      existsSync(join(projectPath, 'pom.xml')) ||
      existsSync(join(projectPath, 'build.gradle'))
    ) {
      return 'java';
    }

    // Default to JavaScript if package.json exists
    if (existsSync(join(projectPath, 'package.json'))) {
      return 'javascript';
    }

    return null;
  }

  /**
   * Detect framework from config files.
   */
  private detectFramework(projectPath: string): string | null {
    // Next.js
    if (
      existsSync(join(projectPath, 'next.config.js')) ||
      existsSync(join(projectPath, 'next.config.mjs')) ||
      existsSync(join(projectPath, 'next.config.ts'))
    ) {
      return 'nextjs';
    }

    // Remix
    if (existsSync(join(projectPath, 'remix.config.js'))) {
      return 'remix';
    }

    // Nuxt
    if (
      existsSync(join(projectPath, 'nuxt.config.ts')) ||
      existsSync(join(projectPath, 'nuxt.config.js'))
    ) {
      return 'nuxt';
    }

    // Vite (React/Vue)
    if (existsSync(join(projectPath, 'vite.config.ts'))) {
      return 'vite';
    }

    // Django
    if (existsSync(join(projectPath, 'manage.py'))) {
      return 'django';
    }

    // FastAPI
    if (this.hasDependency(projectPath, 'fastapi')) {
      return 'fastapi';
    }

    // Flask
    if (this.hasDependency(projectPath, 'flask')) {
      return 'flask';
    }

    // Express
    if (this.hasDependency(projectPath, 'express')) {
      return 'express';
    }

    // Check package.json for React/Vue/Angular
    const packageJsonPath = join(projectPath, 'package.json');
    if (existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
        const deps = { ...pkg.dependencies, ...pkg.devDependencies };

        if (deps['react']) return 'react';
        if (deps['vue']) return 'vue';
        if (deps['@angular/core']) return 'angular';
        if (deps['svelte']) return 'svelte';
      } catch {
        // Ignore parse errors
      }
    }

    return null;
  }

  /**
   * Check if project has a specific dependency.
   */
  private hasDependency(projectPath: string, dep: string): boolean {
    const packageJsonPath = join(projectPath, 'package.json');
    if (existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
        const deps = { ...pkg.dependencies, ...pkg.devDependencies };
        return dep in deps;
      } catch {
        // Ignore parse errors
      }
    }

    // Check Python requirements
    const requirementsPath = join(projectPath, 'requirements.txt');
    if (existsSync(requirementsPath)) {
      try {
        const content = readFileSync(requirementsPath, 'utf-8');
        return content.toLowerCase().includes(dep.toLowerCase());
      } catch {
        // Ignore read errors
      }
    }

    return false;
  }

  /**
   * Extract key dependencies.
   */
  private extractDependencies(projectPath: string): string[] {
    const deps: string[] = [];

    const packageJsonPath = join(projectPath, 'package.json');
    if (existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
        const allDeps = Object.keys({
          ...pkg.dependencies,
          ...pkg.devDependencies,
        });

        // Filter to important deps
        const importantDeps = allDeps.filter((d) =>
          [
            'react', 'vue', 'angular', 'svelte', 'next', 'nuxt', 'express',
            'fastify', 'prisma', 'typeorm', 'mongoose', 'typescript',
            'tailwindcss', 'styled-components', 'jest', 'vitest', 'mocha',
          ].some((important) => d.includes(important))
        );

        deps.push(...importantDeps.slice(0, 10));
      } catch {
        // Ignore parse errors
      }
    }

    return deps;
  }

  /**
   * Check if project has tests.
   */
  private hasTests(projectPath: string): boolean {
    // Check common test directories
    const testDirs = ['test', 'tests', '__tests__', 'spec', 'specs'];
    for (const dir of testDirs) {
      if (existsSync(join(projectPath, dir))) {
        return true;
      }
    }

    // Check for test config files
    const testConfigs = [
      'jest.config.js', 'jest.config.ts',
      'vitest.config.ts', 'vitest.config.js',
      'pytest.ini', 'pyproject.toml',
      '.mocharc.js', '.mocharc.json',
    ];

    for (const config of testConfigs) {
      if (existsSync(join(projectPath, config))) {
        return true;
      }
    }

    return false;
  }

  /**
   * Check if project has CI configuration.
   */
  private hasCi(projectPath: string): boolean {
    const ciPaths = [
      '.github/workflows',
      '.gitlab-ci.yml',
      '.circleci',
      'Jenkinsfile',
      '.travis.yml',
      'azure-pipelines.yml',
      'bitbucket-pipelines.yml',
    ];

    for (const ciPath of ciPaths) {
      if (existsSync(join(projectPath, ciPath))) {
        return true;
      }
    }

    return false;
  }

  /**
   * Clear cached context.
   */
  clearCache(): void {
    this.cachedContext = null;
    this.cachedPath = null;
  }
}

/**
 * Create a project context provider.
 */
export function createProjectContextProvider(): ProjectContextProvider {
  return new ProjectContextProvider();
}
