/**
 * Segment analyzer for partial prompt optimization.
 * Identifies clear vs vague segments and enables targeted optimization.
 * Maps to spec section 5.1 - Partial Optimization.
 */

import type { PromptSegment, SegmentStatus } from '../types/index.js';

/**
 * Clarity indicators that suggest a segment is well-formed.
 */
const CLARITY_INDICATORS = [
  // Specific file/code references
  /`[^`]+`/,
  /[\/\\][\w\-.]+\.\w+/,
  // Specific numbers/versions
  /\b\d+\.\d+(?:\.\d+)?\b/,
  /\b\d+\s*(?:px|em|rem|%|ms|s|kb|mb|gb)\b/i,
  // Explicit constraints
  /\b(?:must|should|exactly|specifically|only|never)\b/i,
  // Technical terms with context
  /\b(?:using|with|in|via)\s+\w+/i,
  // Quoted content
  /"[^"]+"/,
  /'[^']+'/,
];

/**
 * Vagueness indicators that suggest a segment needs clarification.
 */
const VAGUENESS_INDICATORS = [
  // Generic references
  /\b(?:it|this|that|thing|stuff|something)\b/i,
  // Vague quality descriptors
  /\b(?:good|better|best|nice|cool|awesome|great)\b/i,
  // Uncertainty markers
  /\b(?:maybe|perhaps|might|could|idk|dunno)\b/i,
  // Generic actions
  /\b(?:fix|help|make|do)\s+(?:it|this|that)\b/i,
  // Vague amounts
  /\b(?:some|few|lots|many|much)\b/i,
];

/**
 * Segment analysis result.
 */
export interface SegmentAnalysis {
  /** Analyzed segments */
  segments: PromptSegment[];
  /** Overall clarity score (0-1) */
  overallClarity: number;
  /** Segments that need optimization */
  vagueSegments: PromptSegment[];
  /** Segments that are clear */
  clearSegments: PromptSegment[];
  /** Suggested improvements for vague segments */
  suggestions: Map<number, string[]>;
}

/**
 * Segment analyzer class.
 */
export class SegmentAnalyzer {
  /**
   * Analyze a prompt and break it into segments.
   */
  analyze(prompt: string): SegmentAnalysis {
    const segments = this.segmentPrompt(prompt);
    const analyzed = segments.map((seg, idx) => this.analyzeSegment(seg, idx));

    const vagueSegments = analyzed.filter((s) => s.status === 'NEEDS_OPTIMIZATION');
    const clearSegments = analyzed.filter((s) => s.status === 'CLEAR');

    const overallClarity = clearSegments.length / analyzed.length;

    const suggestions = new Map<number, string[]>();
    for (const segment of vagueSegments) {
      suggestions.set(segment.index, this.generateSuggestions(segment));
    }

    return {
      segments: analyzed,
      overallClarity,
      vagueSegments,
      clearSegments,
      suggestions,
    };
  }

  /**
   * Break prompt into logical segments.
   */
  private segmentPrompt(prompt: string): Array<{ content: string; start: number; end: number }> {
    const segments: Array<{ content: string; start: number; end: number }> = [];

    // Split by sentences and logical breaks
    const sentencePattern = /[^.!?\n]+[.!?\n]+|[^.!?\n]+$/g;
    let match;

    while ((match = sentencePattern.exec(prompt)) !== null) {
      const content = match[0].trim();
      if (content.length > 0) {
        segments.push({
          content,
          start: match.index,
          end: match.index + match[0].length,
        });
      }
    }

    // If no sentences found, treat whole prompt as one segment
    if (segments.length === 0 && prompt.trim().length > 0) {
      segments.push({
        content: prompt.trim(),
        start: 0,
        end: prompt.length,
      });
    }

    return segments;
  }

  /**
   * Analyze a single segment.
   */
  private analyzeSegment(
    segment: { content: string; start: number; end: number },
    index: number
  ): PromptSegment {
    const { content, start, end } = segment;

    // Count clarity and vagueness indicators
    let clarityScore = 0;
    let vaguenessScore = 0;

    for (const pattern of CLARITY_INDICATORS) {
      if (pattern.test(content)) {
        clarityScore++;
      }
    }

    for (const pattern of VAGUENESS_INDICATORS) {
      if (pattern.test(content)) {
        vaguenessScore++;
      }
    }

    // Calculate confidence
    const totalIndicators = clarityScore + vaguenessScore;
    const confidence = totalIndicators > 0
      ? clarityScore / totalIndicators
      : 0.5; // Neutral if no indicators

    // Determine status
    let status: SegmentStatus;
    if (confidence >= 0.7) {
      status = 'CLEAR';
    } else if (confidence >= 0.4) {
      status = 'NEEDS_OPTIMIZATION';
    } else {
      status = 'NEEDS_CLARIFICATION';
    }

    // Determine type
    const type = this.detectSegmentType(content);

    return {
      content,
      start,
      end,
      status,
      confidence,
      type,
      index,
    };
  }

  /**
   * Detect the type of segment.
   */
  private detectSegmentType(content: string): 'instruction' | 'context' | 'constraint' | 'question' | 'reference' {
    const lower = content.toLowerCase();

    // Question
    if (content.includes('?') || /^(?:what|why|how|when|where|who|can|could|would|should)\b/i.test(content)) {
      return 'question';
    }

    // Constraint
    if (/\b(?:must|should|don't|do not|never|always|only|without|except)\b/i.test(content)) {
      return 'constraint';
    }

    // Reference (file, code, URL)
    if (/[\/\\][\w\-.]+\.\w+|`[^`]+`|https?:\/\//.test(content)) {
      return 'reference';
    }

    // Context (background information)
    if (/\b(?:because|since|given|assuming|context|background)\b/i.test(lower)) {
      return 'context';
    }

    // Default to instruction
    return 'instruction';
  }

  /**
   * Generate suggestions for improving a vague segment.
   */
  private generateSuggestions(segment: PromptSegment): string[] {
    const suggestions: string[] = [];
    const content = segment.content.toLowerCase();

    // Check for generic "it" references
    if (/\b(?:it|this|that)\b/.test(content)) {
      suggestions.push('Replace pronouns (it, this, that) with specific names');
    }

    // Check for vague quality descriptors
    if (/\b(?:good|better|best|nice)\b/.test(content)) {
      suggestions.push('Define specific criteria for "good" or "better"');
    }

    // Check for vague actions
    if (/\b(?:fix|help|make)\s+(?:it|this|that)\b/.test(content)) {
      suggestions.push('Describe what is broken and expected behavior');
    }

    // Check for missing specificity
    if (segment.type === 'instruction' && !CLARITY_INDICATORS.some((p) => p.test(segment.content))) {
      suggestions.push('Add specific details like file paths, function names, or expected output');
    }

    // Default suggestion
    if (suggestions.length === 0) {
      suggestions.push('Add more context or specific requirements');
    }

    return suggestions;
  }

  /**
   * Optimize only vague segments while preserving clear ones.
   */
  optimizePartially(
    original: string,
    analysis: SegmentAnalysis,
    optimizedSegments: Map<number, string>
  ): string {
    // Build result by combining clear and optimized segments
    let result = '';
    let lastEnd = 0;

    for (const segment of analysis.segments.sort((a, b) => a.start - b.start)) {
      // Add any text between segments
      if (segment.start > lastEnd) {
        result += original.slice(lastEnd, segment.start);
      }

      // Add segment (optimized if vague, original if clear)
      if (segment.status === 'CLEAR') {
        result += segment.content;
      } else {
        result += optimizedSegments.get(segment.index) ?? segment.content;
      }

      lastEnd = segment.end;
    }

    // Add any trailing text
    if (lastEnd < original.length) {
      result += original.slice(lastEnd);
    }

    return result;
  }

  /**
   * Check if prompt needs segmented optimization.
   */
  needsSegmentedOptimization(analysis: SegmentAnalysis): boolean {
    // Use segmented optimization if:
    // - There are both clear and vague segments
    // - Overall clarity is between 0.3 and 0.8
    return (
      analysis.clearSegments.length > 0 &&
      analysis.vagueSegments.length > 0 &&
      analysis.overallClarity >= 0.3 &&
      analysis.overallClarity <= 0.8
    );
  }
}

/**
 * Create a segment analyzer.
 */
export function createSegmentAnalyzer(): SegmentAnalyzer {
  return new SegmentAnalyzer();
}
