/**
 * Code domain template.
 * Specialized optimization strategies for code-related prompts.
 */

import type { ChangeType } from '../../../types/index.js';
import { BaseDomainTemplate, type DomainTemplateConfig } from './base.js';

/**
 * Code domain template configuration.
 */
const CODE_CONFIG: DomainTemplateConfig = {
  domain: 'CODE',
  description: 'Programming, debugging, and software development tasks',
  keywords: [
    'function', 'class', 'component', 'api', 'endpoint', 'database',
    'bug', 'error', 'fix', 'debug', 'implement', 'refactor',
    'code', 'script', 'program', 'algorithm', 'test', 'deploy',
    'typescript', 'javascript', 'python', 'react', 'node', 'sql',
  ],
  enhancements: [
    {
      name: 'add-language-context',
      condition: (prompt) => {
        // Check if language is mentioned
        const languages = ['typescript', 'javascript', 'python', 'java', 'rust', 'go', 'ruby', 'php'];
        const lower = prompt.toLowerCase();
        return !languages.some((lang) => lower.includes(lang));
      },
      apply: (prompt) => {
        // Don't auto-add language - just flag it
        return {
          enhanced: prompt,
          change: null,
        };
      },
      priority: 10,
    },
    {
      name: 'clarify-expected-behavior',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        return (
          (lower.includes('fix') || lower.includes('bug') || lower.includes('error')) &&
          !lower.includes('expected') &&
          !lower.includes('should')
        );
      },
      apply: (prompt) => {
        const clarification = '\n\nPlease describe the expected behavior vs actual behavior.';
        return {
          enhanced: prompt + clarification,
          change: {
            type: 'ADD_CONTEXT' as ChangeType,
            originalSegment: '',
            newSegment: clarification.trim(),
            reason: 'Added clarification request for bug fix context',
          },
        };
      },
      priority: 8,
    },
    {
      name: 'add-file-path-request',
      condition: (prompt) => {
        const lower = prompt.toLowerCase();
        const hasFileRef = /[\/\\][\w-]+\.\w+/.test(prompt) || lower.includes('file');
        const needsFile = lower.includes('update') || lower.includes('modify') || lower.includes('change');
        return needsFile && !hasFileRef;
      },
      apply: (prompt) => {
        const clarification = '\n\nPlease specify the file path(s) to modify.';
        return {
          enhanced: prompt + clarification,
          change: {
            type: 'ADD_CONTEXT' as ChangeType,
            originalSegment: '',
            newSegment: clarification.trim(),
            reason: 'Added request for file path specification',
          },
        };
      },
      priority: 7,
    },
  ],
  preservePatterns: [
    // File paths
    /[\/\\][\w\-.]+[\/\\][\w\-.]+\.\w+/g,
    // Function/class names in backticks
    /`[a-zA-Z_]\w*`/g,
    // Code blocks
    /```[\s\S]*?```/g,
    // Inline code
    /`[^`]+`/g,
    // URLs
    /https?:\/\/[^\s]+/g,
    // Version numbers
    /v?\d+\.\d+\.\d+/g,
    // Error messages
    /Error:\s*[^\n]+/gi,
    // Stack traces
    /at\s+[\w.]+\s*\([^)]+\)/g,
  ],
  clarityIndicators: [
    'specifically',
    'exactly',
    'in this file',
    'in the following way',
    'step by step',
    'expected behavior',
    'actual behavior',
  ],
  commonIssues: [
    {
      pattern: /\bthe code\b/gi,
      fix: 'the code',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Generic "the code" reference - consider specifying',
    },
    {
      pattern: /\bthe function\b(?!\s+`)/gi,
      fix: 'the function',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Generic "the function" reference - consider naming it',
    },
    {
      pattern: /\bit doesn't work\b/gi,
      fix: () => 'it produces an error (please specify the error message)',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Vague error description clarified',
    },
    {
      pattern: /\bit's broken\b/gi,
      fix: () => 'there is an issue (please specify symptoms)',
      changeType: 'CLARIFY' as ChangeType,
      description: 'Vague problem description clarified',
    },
  ],
  maxExpansionRatio: 2.0,
};

/**
 * Code domain template class.
 */
export class CodeTemplate extends BaseDomainTemplate {
  constructor() {
    super(CODE_CONFIG);
  }

  /**
   * Generate code-specific tip.
   */
  generateTip(prompt: string): string {
    const lower = prompt.toLowerCase();

    // Check for missing language
    const languages = ['typescript', 'javascript', 'python', 'java', 'rust', 'go', 'ruby', 'php', 'c++', 'c#'];
    const hasLanguage = languages.some((lang) => lower.includes(lang));

    if (!hasLanguage) {
      return 'Tip: Specify the programming language for more accurate assistance.';
    }

    // Check for missing file context
    const hasFilePath = /[\/\\][\w-]+\.\w+/.test(prompt);
    if (!hasFilePath && (lower.includes('update') || lower.includes('modify'))) {
      return 'Tip: Include file paths when asking to modify existing code.';
    }

    // Check for error handling
    if (lower.includes('error') || lower.includes('bug')) {
      if (!prompt.includes('```')) {
        return 'Tip: Include the full error message and relevant code in code blocks.';
      }
    }

    // Check for test context
    if (lower.includes('test')) {
      return 'Tip: Specify your testing framework and what behavior you want to test.';
    }

    return 'Tip: Include file paths, language, and expected vs actual behavior for best results.';
  }

  /**
   * Extract code-specific context from prompt.
   */
  extractCodeContext(prompt: string): {
    language: string | null;
    framework: string | null;
    errorType: string | null;
    files: string[];
  } {
    const lower = prompt.toLowerCase();

    // Detect language
    const languageMap: Record<string, string> = {
      typescript: 'TypeScript',
      javascript: 'JavaScript',
      python: 'Python',
      java: 'Java',
      rust: 'Rust',
      go: 'Go',
      ruby: 'Ruby',
      php: 'PHP',
      'c++': 'C++',
      'c#': 'C#',
    };

    let language: string | null = null;
    for (const [key, value] of Object.entries(languageMap)) {
      if (lower.includes(key)) {
        language = value;
        break;
      }
    }

    // Detect framework
    const frameworkMap: Record<string, string> = {
      react: 'React',
      vue: 'Vue',
      angular: 'Angular',
      svelte: 'Svelte',
      nextjs: 'Next.js',
      'next.js': 'Next.js',
      express: 'Express',
      fastapi: 'FastAPI',
      django: 'Django',
      flask: 'Flask',
    };

    let framework: string | null = null;
    for (const [key, value] of Object.entries(frameworkMap)) {
      if (lower.includes(key)) {
        framework = value;
        break;
      }
    }

    // Detect error type
    let errorType: string | null = null;
    if (lower.includes('typeerror')) errorType = 'TypeError';
    else if (lower.includes('syntaxerror')) errorType = 'SyntaxError';
    else if (lower.includes('referenceerror')) errorType = 'ReferenceError';
    else if (lower.includes('cannot read property')) errorType = 'TypeError';
    else if (lower.includes('undefined')) errorType = 'undefined reference';
    else if (lower.includes('null')) errorType = 'null reference';

    // Extract file paths
    const files: string[] = [];
    const fileMatches = prompt.match(/[\/\\]?[\w\-.]+[\/\\][\w\-.]+\.\w+/g);
    if (fileMatches) {
      files.push(...fileMatches);
    }

    return { language, framework, errorType, files };
  }
}

/**
 * Create a code template instance.
 */
export function createCodeTemplate(): CodeTemplate {
  return new CodeTemplate();
}
