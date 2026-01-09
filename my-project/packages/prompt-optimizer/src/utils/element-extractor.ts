/**
 * Element extractor for identifying key elements in prompts.
 * Extracts file paths, code references, constraints, and other important elements.
 */

/**
 * Extracted element types.
 */
export interface ExtractedElements {
  /** File paths mentioned */
  filePaths: string[];
  /** Code identifiers (function names, classes, etc.) */
  codeIdentifiers: string[];
  /** URLs and links */
  urls: string[];
  /** Version numbers */
  versions: string[];
  /** Negative constraints (don't, avoid, never, etc.) */
  negativeConstraints: string[];
  /** Positive constraints (must, should, required, etc.) */
  positiveConstraints: string[];
  /** Quoted content */
  quotedContent: string[];
  /** Technical terms */
  technicalTerms: string[];
  /** Numbers and measurements */
  numbers: string[];
  /** Code blocks */
  codeBlocks: string[];
}

/**
 * Element extraction patterns.
 */
const EXTRACTION_PATTERNS = {
  filePaths: [
    // Unix-style paths
    /(?:\/[\w\-.]+)+(?:\.\w+)?/g,
    // Windows-style paths
    /(?:[A-Za-z]:)?(?:\\[\w\-.]+)+(?:\.\w+)?/g,
    // Relative paths with extension
    /\.{1,2}\/[\w\-.\/]+\.\w+/g,
    // Simple filename with extension
    /\b[\w\-]+\.(?:ts|tsx|js|jsx|py|rb|rs|go|java|c|cpp|h|hpp|css|scss|html|json|yaml|yml|md|txt|xml|sql|sh|bash|zsh)\b/g,
  ],
  codeIdentifiers: [
    // Backtick-wrapped identifiers
    /`([a-zA-Z_]\w*)`/g,
    // camelCase or PascalCase identifiers
    /\b[a-z][a-zA-Z0-9]*(?:[A-Z][a-z0-9]*)+\b/g,
    // snake_case identifiers
    /\b[a-z]+(?:_[a-z0-9]+)+\b/g,
  ],
  urls: [
    /https?:\/\/[^\s<>"{}|\\^`[\]]+/g,
    /www\.[^\s<>"{}|\\^`[\]]+/g,
  ],
  versions: [
    /v?\d+\.\d+(?:\.\d+)?(?:-[\w.]+)?/g,
    /\b(?:version|ver\.?)\s*\d+(?:\.\d+)*/gi,
  ],
  negativeConstraints: [
    /(?:don't|do not)\s+[^.,!?\n]+/gi,
    /(?:avoid|never)\s+[^.,!?\n]+/gi,
    /(?:without|except)\s+[^.,!?\n]+/gi,
    /(?:not|no)\s+\w+(?:\s+\w+){0,3}/gi,
  ],
  positiveConstraints: [
    /(?:must|should)\s+[^.,!?\n]+/gi,
    /(?:required|necessary|essential)\s+[^.,!?\n]+/gi,
    /(?:always|ensure|make sure)\s+[^.,!?\n]+/gi,
  ],
  quotedContent: [
    /"([^"]+)"/g,
    /'([^']+)'/g,
  ],
  technicalTerms: [
    // API-related
    /\b(?:API|REST|GraphQL|gRPC|WebSocket|HTTP|HTTPS)\b/gi,
    // Database-related
    /\b(?:SQL|NoSQL|PostgreSQL|MySQL|MongoDB|Redis|database)\b/gi,
    // Framework-related
    /\b(?:React|Vue|Angular|Svelte|Next\.js|Nuxt|Express|FastAPI|Django)\b/gi,
    // Architecture-related
    /\b(?:microservice|monolith|serverless|container|docker|kubernetes)\b/gi,
  ],
  numbers: [
    /\b\d+(?:\.\d+)?(?:\s*(?:px|em|rem|%|ms|s|kb|mb|gb|tb))\b/gi,
    /\b\d+(?:\.\d+)?\s*(?:times|x|items?|rows?|columns?|records?)\b/gi,
  ],
  codeBlocks: [
    /```[\s\S]*?```/g,
    /`[^`]+`/g,
  ],
};

/**
 * Element extractor class.
 */
export class ElementExtractor {
  /**
   * Extract all elements from a prompt.
   */
  extract(prompt: string): ExtractedElements {
    return {
      filePaths: this.extractFilePaths(prompt),
      codeIdentifiers: this.extractCodeIdentifiers(prompt),
      urls: this.extractUrls(prompt),
      versions: this.extractVersions(prompt),
      negativeConstraints: this.extractNegativeConstraints(prompt),
      positiveConstraints: this.extractPositiveConstraints(prompt),
      quotedContent: this.extractQuotedContent(prompt),
      technicalTerms: this.extractTechnicalTerms(prompt),
      numbers: this.extractNumbers(prompt),
      codeBlocks: this.extractCodeBlocks(prompt),
    };
  }

  /**
   * Extract file paths.
   */
  private extractFilePaths(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.filePaths) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return [...new Set(matches)];
  }

  /**
   * Extract code identifiers.
   */
  private extractCodeIdentifiers(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.codeIdentifiers) {
      const regex = new RegExp(pattern.source, pattern.flags);
      let match;
      while ((match = regex.exec(prompt)) !== null) {
        // Use captured group if available, otherwise full match
        matches.push(match[1] ?? match[0]);
      }
    }
    return [...new Set(matches)];
  }

  /**
   * Extract URLs.
   */
  private extractUrls(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.urls) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return [...new Set(matches)];
  }

  /**
   * Extract version numbers.
   */
  private extractVersions(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.versions) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return [...new Set(matches)];
  }

  /**
   * Extract negative constraints.
   */
  private extractNegativeConstraints(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.negativeConstraints) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found.map((m) => m.trim()));
    }
    return [...new Set(matches)];
  }

  /**
   * Extract positive constraints.
   */
  private extractPositiveConstraints(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.positiveConstraints) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found.map((m) => m.trim()));
    }
    return [...new Set(matches)];
  }

  /**
   * Extract quoted content.
   */
  private extractQuotedContent(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.quotedContent) {
      const regex = new RegExp(pattern.source, pattern.flags);
      let match;
      while ((match = regex.exec(prompt)) !== null) {
        matches.push(match[1] ?? match[0]);
      }
    }
    return [...new Set(matches)];
  }

  /**
   * Extract technical terms.
   */
  private extractTechnicalTerms(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.technicalTerms) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return [...new Set(matches)];
  }

  /**
   * Extract numbers with units.
   */
  private extractNumbers(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.numbers) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return [...new Set(matches)];
  }

  /**
   * Extract code blocks.
   */
  private extractCodeBlocks(prompt: string): string[] {
    const matches: string[] = [];
    for (const pattern of EXTRACTION_PATTERNS.codeBlocks) {
      const found = prompt.match(pattern);
      if (found) matches.push(...found);
    }
    return matches; // Don't dedupe - order matters for code blocks
  }

  /**
   * Get all elements that must be preserved during optimization.
   */
  getMustPreserve(elements: ExtractedElements): string[] {
    return [
      ...elements.filePaths,
      ...elements.codeIdentifiers,
      ...elements.urls,
      ...elements.versions,
      ...elements.negativeConstraints,
      ...elements.quotedContent,
      ...elements.codeBlocks,
    ];
  }

  /**
   * Check if optimized prompt preserves all required elements.
   */
  checkPreservation(
    original: string,
    optimized: string
  ): {
    preserved: boolean;
    missing: string[];
    elements: ExtractedElements;
  } {
    const elements = this.extract(original);
    const mustPreserve = this.getMustPreserve(elements);

    const missing: string[] = [];
    const optimizedLower = optimized.toLowerCase();

    for (const element of mustPreserve) {
      // Check if element or its normalized form exists in optimized
      const normalizedElement = element.toLowerCase().replace(/\s+/g, ' ').trim();
      if (!optimizedLower.includes(normalizedElement)) {
        // Check for partial match (element might be reformatted)
        const words = normalizedElement.split(/\s+/).filter((w) => w.length > 2);
        const allWordsPresent = words.length > 0 &&
          words.every((w) => optimizedLower.includes(w));

        if (!allWordsPresent) {
          missing.push(element);
        }
      }
    }

    return {
      preserved: missing.length === 0,
      missing,
      elements,
    };
  }

  /**
   * Get element counts for analysis.
   */
  getCounts(elements: ExtractedElements): Record<string, number> {
    return {
      filePaths: elements.filePaths.length,
      codeIdentifiers: elements.codeIdentifiers.length,
      urls: elements.urls.length,
      versions: elements.versions.length,
      negativeConstraints: elements.negativeConstraints.length,
      positiveConstraints: elements.positiveConstraints.length,
      quotedContent: elements.quotedContent.length,
      technicalTerms: elements.technicalTerms.length,
      numbers: elements.numbers.length,
      codeBlocks: elements.codeBlocks.length,
    };
  }
}

/**
 * Create an element extractor.
 */
export function createElementExtractor(): ElementExtractor {
  return new ElementExtractor();
}
