/**
 * Token counting utilities.
 * Provides accurate token estimation for context budgeting.
 */

/**
 * Simple token counter using character-based estimation.
 * More accurate counting would use tiktoken, but this is sufficient for budgeting.
 */
export class TokenCounter {
  private static readonly CHARS_PER_TOKEN = 4;
  private static readonly CODE_CHARS_PER_TOKEN = 3.5;
  private static readonly WHITESPACE_RATIO = 0.15;

  /**
   * Count tokens in a string.
   */
  static count(text: string): number {
    if (!text) return 0;

    // Detect if content is code-like
    const isCode = this.isCodeLike(text);
    const charsPerToken = isCode
      ? this.CODE_CHARS_PER_TOKEN
      : this.CHARS_PER_TOKEN;

    // Account for whitespace efficiency
    const effectiveLength = text.length * (1 - this.WHITESPACE_RATIO);

    return Math.ceil(effectiveLength / charsPerToken);
  }

  /**
   * Count tokens in multiple strings.
   */
  static countAll(...texts: string[]): number {
    return texts.reduce((sum, text) => sum + this.count(text), 0);
  }

  /**
   * Check if text appears to be code.
   */
  private static isCodeLike(text: string): boolean {
    const codeIndicators = [
      /[{}[\]();]/, // Brackets
      /\b(function|const|let|var|class|import|export|return)\b/, // Keywords
      /^\s*(\/\/|#|\/\*)/, // Comments
      /\.\w+\(/, // Method calls
      /=>\s*[{(]/, // Arrow functions
    ];

    return codeIndicators.some((pattern) => pattern.test(text));
  }

  /**
   * Truncate text to fit within token limit.
   */
  static truncateToLimit(text: string, maxTokens: number): string {
    const currentTokens = this.count(text);

    if (currentTokens <= maxTokens) {
      return text;
    }

    // Estimate character limit
    const targetLength = Math.floor(
      text.length * (maxTokens / currentTokens) * 0.9 // 10% buffer
    );

    // Find natural break point
    const truncated = text.slice(0, targetLength);
    const lastBreak = Math.max(
      truncated.lastIndexOf('\n'),
      truncated.lastIndexOf('. '),
      truncated.lastIndexOf('! '),
      truncated.lastIndexOf('? ')
    );

    if (lastBreak > targetLength * 0.7) {
      return truncated.slice(0, lastBreak + 1) + '...';
    }

    return truncated + '...';
  }

  /**
   * Check if text fits within token limit.
   */
  static fitsInLimit(text: string, maxTokens: number): boolean {
    return this.count(text) <= maxTokens;
  }

  /**
   * Get remaining tokens from a budget.
   */
  static remaining(budget: number, ...usedTexts: string[]): number {
    const used = this.countAll(...usedTexts);
    return Math.max(0, budget - used);
  }

  /**
   * Split text into chunks that fit token limits.
   */
  static chunk(text: string, maxTokensPerChunk: number): string[] {
    if (this.fitsInLimit(text, maxTokensPerChunk)) {
      return [text];
    }

    const chunks: string[] = [];
    const paragraphs = text.split(/\n\n+/);
    let currentChunk = '';

    for (const paragraph of paragraphs) {
      const combined = currentChunk
        ? `${currentChunk}\n\n${paragraph}`
        : paragraph;

      if (this.fitsInLimit(combined, maxTokensPerChunk)) {
        currentChunk = combined;
      } else {
        if (currentChunk) {
          chunks.push(currentChunk);
        }

        // If single paragraph is too large, split by sentences
        if (!this.fitsInLimit(paragraph, maxTokensPerChunk)) {
          const sentences = paragraph.split(/(?<=[.!?])\s+/);
          currentChunk = '';

          for (const sentence of sentences) {
            const sentenceCombined = currentChunk
              ? `${currentChunk} ${sentence}`
              : sentence;

            if (this.fitsInLimit(sentenceCombined, maxTokensPerChunk)) {
              currentChunk = sentenceCombined;
            } else {
              if (currentChunk) {
                chunks.push(currentChunk);
              }
              // Force truncate if single sentence is too large
              currentChunk = this.truncateToLimit(sentence, maxTokensPerChunk);
            }
          }
        } else {
          currentChunk = paragraph;
        }
      }
    }

    if (currentChunk) {
      chunks.push(currentChunk);
    }

    return chunks;
  }

  /**
   * Calculate compression ratio for optimization.
   */
  static compressionRatio(original: string, optimized: string): number {
    const originalTokens = this.count(original);
    const optimizedTokens = this.count(optimized);

    if (originalTokens === 0) return 1;

    return optimizedTokens / originalTokens;
  }

  /**
   * Estimate cost based on token count (approximate).
   */
  static estimateCost(
    inputTokens: number,
    outputTokens: number,
    model: 'haiku' | 'sonnet' | 'opus' = 'sonnet'
  ): { inputCost: number; outputCost: number; totalCost: number } {
    // Approximate costs per 1M tokens (as of early 2025)
    const costs: Record<typeof model, { input: number; output: number }> = {
      haiku: { input: 0.25, output: 1.25 },
      sonnet: { input: 3, output: 15 },
      opus: { input: 15, output: 75 },
    };

    const modelCosts = costs[model];
    const inputCost = (inputTokens / 1_000_000) * modelCosts.input;
    const outputCost = (outputTokens / 1_000_000) * modelCosts.output;

    return {
      inputCost,
      outputCost,
      totalCost: inputCost + outputCost,
    };
  }
}

/**
 * Shorthand for token counting.
 */
export function countTokens(text: string): number {
  return TokenCounter.count(text);
}

/**
 * Shorthand for token truncation.
 */
export function truncateTokens(text: string, maxTokens: number): string {
  return TokenCounter.truncateToLimit(text, maxTokens);
}
