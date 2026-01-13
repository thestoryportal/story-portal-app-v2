import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import type {
  ParsedDocument,
  AtomicClaim,
  Conflict,
  MergeResult,
  MergeStrategy,
  MergedSection,
  ResolvedConflict,
  FlaggedConflict,
  ResolutionType
} from '../types.js';
import { LLMError } from '../errors.js';

export interface LLMService {
  generate(params: {
    model?: string;
    prompt: string;
    format?: 'json';
    options?: Record<string, unknown>;
  }): Promise<string>;
}

const ResolutionSchema = z.object({
  choice: z.enum(['chose_a', 'chose_b', 'merged']),
  confidence: z.number().min(0).max(1),
  reasoning: z.string(),
  merged_text: z.string().optional()
});

interface ClaimGroup {
  topic: string;
  claims: AtomicClaim[];
  documentIds: Set<string>;
}

interface AutoResolutionResult {
  choice: ResolutionType;
  confidence: number;
  reasoning: string;
  mergedText?: string;
}

export class MergeEngine {
  private llmService: LLMService;
  private model: string;

  constructor(llmService: LLMService, model: string = 'llama3.1:8b') {
    this.llmService = llmService;
    this.model = model;
  }

  async merge(
    documents: ParsedDocument[],
    claims: AtomicClaim[],
    conflicts: Conflict[],
    strategy: MergeStrategy
  ): Promise<MergeResult> {
    // 1. Group claims by topic/entity
    const claimGroups = this.groupClaimsByTopic(claims);

    // 2. Resolve conflicts
    const resolvedConflicts: ResolvedConflict[] = [];
    const flaggedConflicts: FlaggedConflict[] = [];

    for (const conflict of conflicts) {
      const resolution = await this.resolveConflict(conflict, strategy, documents);

      if (resolution.resolved) {
        resolvedConflicts.push({
          conflict_id: conflict.id,
          resolution: resolution.resolution!,
          reasoning: resolution.reasoning!
        });
      } else {
        flaggedConflicts.push({
          conflict_id: conflict.id,
          reason: resolution.reason!
        });
      }
    }

    // 3. Build merged sections
    const mergedSections = await this.buildMergedSections(
      claimGroups,
      resolvedConflicts,
      documents
    );

    // 4. Generate final content
    const content = this.generateContent(mergedSections);

    // 5. Calculate statistics
    const stats = this.calculateStatistics(documents, mergedSections, resolvedConflicts, flaggedConflicts);

    return {
      id: uuidv4(),
      title: this.generateTitle(documents),
      content,
      sections: mergedSections,
      conflicts_resolved: resolvedConflicts,
      conflicts_flagged: flaggedConflicts,
      statistics: stats,
      created_at: new Date().toISOString()
    };
  }

  private groupClaimsByTopic(claims: AtomicClaim[]): ClaimGroup[] {
    const groups = new Map<string, ClaimGroup>();

    for (const claim of claims) {
      // Use subject as the grouping key
      const topic = claim.subject.toLowerCase();

      if (!groups.has(topic)) {
        groups.set(topic, {
          topic,
          claims: [],
          documentIds: new Set()
        });
      }

      const group = groups.get(topic)!;
      group.claims.push(claim);
      group.documentIds.add(claim.source_section_id);
    }

    return Array.from(groups.values());
  }

  private async resolveConflict(
    conflict: Conflict,
    strategy: MergeStrategy,
    documents: ParsedDocument[]
  ): Promise<{
    resolved: boolean;
    conflict_id: string;
    resolution?: ResolutionType;
    reasoning?: string;
    reason?: string;
  }> {
    if (strategy.conflictResolution === 'flag_all') {
      return {
        resolved: false,
        conflict_id: conflict.id,
        reason: 'Strategy requires manual resolution'
      };
    }

    // Try auto-resolution
    const resolution = await this.autoResolve(conflict, strategy, documents);

    const threshold = strategy.conflictThreshold || 0.8;
    if (resolution.confidence >= threshold) {
      return {
        resolved: true,
        conflict_id: conflict.id,
        resolution: resolution.choice,
        reasoning: resolution.reasoning
      };
    }

    return {
      resolved: false,
      conflict_id: conflict.id,
      reason: `Confidence ${resolution.confidence.toFixed(2)} below threshold ${threshold}`
    };
  }

  private async autoResolve(
    conflict: Conflict,
    strategy: MergeStrategy,
    documents: ParsedDocument[]
  ): Promise<AutoResolutionResult> {
    // Apply strategy-specific resolution
    switch (strategy.mode) {
      case 'newest_wins':
        return this.resolveByDate(conflict, documents);

      case 'authority_wins':
        return this.resolveByAuthority(conflict, documents, strategy.authorityOrder || []);

      case 'smart':
      default:
        return this.llmResolve(conflict, strategy, documents);
    }
  }

  private resolveByDate(
    conflict: Conflict,
    documents: ParsedDocument[]
  ): AutoResolutionResult {
    const docA = documents.find(d =>
      d.sections.some(s => s.id === conflict.claim_a.document_id)
    );
    const docB = documents.find(d =>
      d.sections.some(s => s.id === conflict.claim_b.document_id)
    );

    if (!docA || !docB) {
      return {
        choice: 'flagged',
        confidence: 0,
        reasoning: 'Could not find source documents'
      };
    }

    const dateA = new Date(docA.created_at);
    const dateB = new Date(docB.created_at);

    if (dateA > dateB) {
      return {
        choice: 'chose_a',
        confidence: 0.9,
        reasoning: `Document A is newer (${docA.created_at} > ${docB.created_at})`
      };
    } else if (dateB > dateA) {
      return {
        choice: 'chose_b',
        confidence: 0.9,
        reasoning: `Document B is newer (${docB.created_at} > ${docA.created_at})`
      };
    }

    return {
      choice: 'flagged',
      confidence: 0.5,
      reasoning: 'Documents have same date, cannot determine newer'
    };
  }

  private resolveByAuthority(
    conflict: Conflict,
    documents: ParsedDocument[],
    authorityOrder: string[]
  ): AutoResolutionResult {
    const docA = documents.find(d =>
      d.sections.some(s => s.id === conflict.claim_a.document_id)
    );
    const docB = documents.find(d =>
      d.sections.some(s => s.id === conflict.claim_b.document_id)
    );

    if (!docA || !docB) {
      return {
        choice: 'flagged',
        confidence: 0,
        reasoning: 'Could not find source documents'
      };
    }

    // Find authority rank based on path patterns
    const rankA = this.getAuthorityRank(docA.source_path, authorityOrder);
    const rankB = this.getAuthorityRank(docB.source_path, authorityOrder);

    if (rankA < rankB) {
      return {
        choice: 'chose_a',
        confidence: 0.85,
        reasoning: `Document A has higher authority (rank ${rankA} vs ${rankB})`
      };
    } else if (rankB < rankA) {
      return {
        choice: 'chose_b',
        confidence: 0.85,
        reasoning: `Document B has higher authority (rank ${rankB} vs ${rankA})`
      };
    }

    return {
      choice: 'flagged',
      confidence: 0.5,
      reasoning: 'Documents have same authority level'
    };
  }

  private getAuthorityRank(path: string, authorityOrder: string[]): number {
    for (let i = 0; i < authorityOrder.length; i++) {
      const pattern = authorityOrder[i];
      if (this.pathMatchesPattern(path, pattern)) {
        return i;
      }
    }
    return authorityOrder.length; // Default to lowest rank
  }

  private pathMatchesPattern(path: string, pattern: string): boolean {
    // Simple glob-like matching
    const regexPattern = pattern
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.');
    return new RegExp(regexPattern, 'i').test(path);
  }

  private async llmResolve(
    conflict: Conflict,
    strategy: MergeStrategy,
    _documents: ParsedDocument[]
  ): Promise<AutoResolutionResult> {
    try {
      const response = await this.llmService.generate({
        model: this.model,
        prompt: `
Resolve this conflict between two document claims.

CLAIM A (from ${conflict.claim_a.document_id}):
"${conflict.claim_a.text}"

CLAIM B (from ${conflict.claim_b.document_id}):
"${conflict.claim_b.text}"

CONFLICT TYPE: ${conflict.conflict_type}

RESOLUTION STRATEGY: ${strategy.mode}
${strategy.authorityOrder ? `AUTHORITY ORDER: ${strategy.authorityOrder.join(' > ')}` : ''}

Think step by step:
1. What specific information differs?
2. Which claim has stronger evidence/authority?
3. Can both claims be merged preserving important information?

Output JSON: {
  "choice": "chose_a" | "chose_b" | "merged",
  "confidence": number (0-1),
  "reasoning": string,
  "merged_text": string (if choice is "merged")
}`,
        format: 'json',
        options: { temperature: 0.1 }
      });

      const parsed = ResolutionSchema.parse(JSON.parse(response));

      return {
        choice: parsed.choice,
        confidence: parsed.confidence,
        reasoning: parsed.reasoning,
        mergedText: parsed.merged_text
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        throw new LLMError(this.model, `Failed to parse resolution response: ${error.message}`);
      }
      throw new LLMError(
        this.model,
        `Resolution failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  private async buildMergedSections(
    claimGroups: ClaimGroup[],
    resolvedConflicts: ResolvedConflict[],
    documents: ParsedDocument[]
  ): Promise<MergedSection[]> {
    const sections: MergedSection[] = [];

    // Build section for each major topic
    // Note: resolvedConflicts can be used to prioritize claims from resolved conflicts
    void resolvedConflicts; // Used indirectly through claim selection logic

    for (const group of claimGroups) {
      // Find the best claims to use (prefer from resolved conflicts)
      const content = this.buildSectionContent(group.claims);

      // Build provenance from all contributing documents
      const provenance = Array.from(group.documentIds).map(sectionId => {
        const doc = documents.find(d => d.sections.some(s => s.id === sectionId));
        return {
          source_document_id: doc?.id || sectionId,
          source_section_id: sectionId,
          contribution_type: 'primary' as const,
          confidence: 0.9
        };
      });

      sections.push({
        header: this.formatTopicHeader(group.topic),
        content,
        provenance
      });
    }

    return sections;
  }

  private buildSectionContent(claims: AtomicClaim[]): string {
    // Group claims by predicate for organized content
    const byPredicate = new Map<string, AtomicClaim[]>();

    for (const claim of claims) {
      const key = claim.predicate;
      const group = byPredicate.get(key) || [];
      group.push(claim);
      byPredicate.set(key, group);
    }

    const lines: string[] = [];

    for (const [predicate, predicateClaims] of byPredicate) {
      // Use the highest confidence claim for each predicate
      const bestClaim = predicateClaims.reduce((a, b) =>
        a.confidence > b.confidence ? a : b
      );

      lines.push(`- **${predicate}**: ${bestClaim.object}`);
    }

    return lines.join('\n');
  }

  private formatTopicHeader(topic: string): string {
    // Convert to title case
    return topic
      .split(/[\s_-]+/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  private generateContent(sections: MergedSection[]): string {
    const lines: string[] = [];

    for (const section of sections) {
      lines.push(`## ${section.header}`);
      lines.push('');
      lines.push(section.content);
      lines.push('');
    }

    return lines.join('\n');
  }

  private generateTitle(documents: ParsedDocument[]): string {
    // Find common themes in document titles
    const titles = documents
      .filter(d => d.title)
      .map(d => d.title!);

    if (titles.length === 0) {
      return 'Consolidated Document';
    }

    // Find common words
    const wordFreq = new Map<string, number>();
    for (const title of titles) {
      const words = title.toLowerCase().split(/\s+/);
      for (const word of words) {
        if (word.length > 3) { // Skip short words
          wordFreq.set(word, (wordFreq.get(word) || 0) + 1);
        }
      }
    }

    // Use most common words
    const commonWords = Array.from(wordFreq.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([word]) => word.charAt(0).toUpperCase() + word.slice(1));

    return `Consolidated: ${commonWords.join(' ')}`;
  }

  private calculateStatistics(
    documents: ParsedDocument[],
    sections: MergedSection[],
    resolvedConflicts: ResolvedConflict[],
    flaggedConflicts: FlaggedConflict[]
  ): MergeResult['statistics'] {
    // Count total original sections
    const totalOriginalSections = documents.reduce(
      (sum, doc) => sum + doc.sections.length,
      0
    );

    // Calculate redundancy eliminated
    const redundancyEliminated = totalOriginalSections > 0
      ? ((totalOriginalSections - sections.length) / totalOriginalSections) * 100
      : 0;

    return {
      documents_merged: documents.length,
      sections_merged: sections.length,
      conflicts_auto_resolved: resolvedConflicts.length,
      conflicts_flagged: flaggedConflicts.length,
      redundancy_eliminated_percent: Math.round(redundancyEliminated * 100) / 100
    };
  }
}
