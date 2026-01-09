/**
 * Metrics collector for gathering performance and quality metrics.
 */

import type {
  MetricsEntry,
  LatencyMetrics,
  QualityMetrics,
  ClassificationMetrics,
  OptimizationMetrics,
  InteractionMetrics,
  Category,
  Domain,
  Complexity,
} from '../types/index.js';
import { MetricsStore, createMetricsStore } from '../storage/metrics-store.js';

/**
 * Timing context for tracking latency.
 */
export interface TimingContext {
  /** Overall start time */
  startTime: number;
  /** Classification timing */
  classification?: { start: number; end?: number };
  /** Optimization timing */
  optimization?: { start: number; end?: number };
  /** Verification timing */
  verification?: { start: number; end?: number };
  /** Context assembly timing */
  context?: { start: number; end?: number };
}

/**
 * Classification result for metrics.
 */
export interface ClassificationResult {
  category: Category;
  domain: Domain | null;
  complexity: Complexity;
  confidence: number;
  cacheHit: boolean;
}

/**
 * Optimization result for metrics.
 */
export interface OptimizationResult {
  changesCount: number;
  changeTypes: string[];
  originalLength: number;
  optimizedLength: number;
  contextInjected: boolean;
  templateUsed: string | null;
}

/**
 * Quality result for metrics.
 */
export interface QualityResult {
  confidence: number;
  intentPreservation: number;
  elementPreservation: number;
  passesUsed: number;
}

/**
 * Metrics collector class.
 */
export class MetricsCollector {
  private store: MetricsStore;
  private sessionId: string;
  private activeTiming: TimingContext | null = null;
  private pendingClassification: ClassificationResult | null = null;
  private pendingOptimization: OptimizationResult | null = null;
  private pendingQuality: QualityResult | null = null;

  constructor(sessionId?: string, store?: MetricsStore) {
    this.sessionId = sessionId ?? `session_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    this.store = store ?? createMetricsStore();
  }

  /**
   * Start timing for a new optimization.
   */
  startTiming(): void {
    this.activeTiming = {
      startTime: Date.now(),
    };
    this.pendingClassification = null;
    this.pendingOptimization = null;
    this.pendingQuality = null;
  }

  /**
   * Start classification timing.
   */
  startClassification(): void {
    if (this.activeTiming) {
      this.activeTiming.classification = { start: Date.now() };
    }
  }

  /**
   * End classification timing with result.
   */
  endClassification(result: ClassificationResult): void {
    if (this.activeTiming?.classification) {
      this.activeTiming.classification.end = Date.now();
    }
    this.pendingClassification = result;
  }

  /**
   * Start optimization timing.
   */
  startOptimization(): void {
    if (this.activeTiming) {
      this.activeTiming.optimization = { start: Date.now() };
    }
  }

  /**
   * End optimization timing with result.
   */
  endOptimization(result: OptimizationResult): void {
    if (this.activeTiming?.optimization) {
      this.activeTiming.optimization.end = Date.now();
    }
    this.pendingOptimization = result;
  }

  /**
   * Start verification timing.
   */
  startVerification(): void {
    if (this.activeTiming) {
      this.activeTiming.verification = { start: Date.now() };
    }
  }

  /**
   * End verification timing.
   */
  endVerification(): void {
    if (this.activeTiming?.verification) {
      this.activeTiming.verification.end = Date.now();
    }
  }

  /**
   * Start context assembly timing.
   */
  startContext(): void {
    if (this.activeTiming) {
      this.activeTiming.context = { start: Date.now() };
    }
  }

  /**
   * End context assembly timing.
   */
  endContext(): void {
    if (this.activeTiming?.context) {
      this.activeTiming.context.end = Date.now();
    }
  }

  /**
   * Record quality metrics.
   */
  recordQuality(quality: QualityResult): void {
    this.pendingQuality = quality;
  }

  /**
   * Record user interaction.
   */
  recordInteraction(
    action: 'accept' | 'reject' | 'modify' | 'skip',
    decisionTimeMs?: number,
    reviewRequired: boolean = false,
    feedbackProvided: boolean = false
  ): void {
    const interaction: InteractionMetrics = {
      action,
      decisionTimeMs: decisionTimeMs ?? null,
      reviewRequired,
      feedbackProvided,
    };

    this.finalize(interaction);
  }

  /**
   * Finalize and store metrics entry.
   */
  private finalize(interaction?: InteractionMetrics): void {
    if (!this.activeTiming) {
      return;
    }

    const now = Date.now();

    // Calculate latency metrics
    const latency: LatencyMetrics = {
      totalMs: now - this.activeTiming.startTime,
      classificationMs: this.calculateDuration(this.activeTiming.classification),
      optimizationMs: this.calculateDuration(this.activeTiming.optimization),
      verificationMs: this.calculateDuration(this.activeTiming.verification),
      contextMs: this.calculateDuration(this.activeTiming.context),
    };

    // Build quality metrics
    const quality: QualityMetrics = this.pendingQuality
      ? {
          confidence: this.pendingQuality.confidence,
          intentPreservation: this.pendingQuality.intentPreservation,
          elementPreservation: this.pendingQuality.elementPreservation,
          optimizationRatio: this.pendingOptimization
            ? this.pendingOptimization.optimizedLength / Math.max(1, this.pendingOptimization.originalLength)
            : 1,
          passesUsed: this.pendingQuality.passesUsed,
        }
      : {
          confidence: 0,
          intentPreservation: 1,
          elementPreservation: 1,
          optimizationRatio: 1,
          passesUsed: 0,
        };

    // Build classification metrics
    const classification: ClassificationMetrics = this.pendingClassification
      ? {
          category: this.pendingClassification.category,
          domain: this.pendingClassification.domain,
          complexity: this.pendingClassification.complexity,
          confidence: this.pendingClassification.confidence,
          cacheHit: this.pendingClassification.cacheHit,
        }
      : {
          category: 'PASS_THROUGH',
          domain: null,
          complexity: 'SIMPLE',
          confidence: 0,
          cacheHit: false,
        };

    // Build optimization metrics
    const optimization: OptimizationMetrics = this.pendingOptimization ?? {
      changesCount: 0,
      changeTypes: [],
      originalLength: 0,
      optimizedLength: 0,
      contextInjected: false,
      templateUsed: null,
    };

    // Build interaction metrics
    const interactionMetrics: InteractionMetrics = interaction ?? {
      action: null,
      decisionTimeMs: null,
      reviewRequired: false,
      feedbackProvided: false,
    };

    // Create entry
    const entry: MetricsEntry = {
      id: `metrics_${now}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: now,
      sessionId: this.sessionId,
      latency,
      quality,
      classification,
      optimization,
      interaction: interactionMetrics,
    };

    // Store entry
    this.store.record(entry);

    // Reset state
    this.activeTiming = null;
    this.pendingClassification = null;
    this.pendingOptimization = null;
    this.pendingQuality = null;
  }

  /**
   * Calculate duration from timing.
   */
  private calculateDuration(timing?: { start: number; end?: number }): number {
    if (!timing) return 0;
    return (timing.end ?? Date.now()) - timing.start;
  }

  /**
   * Abort current timing without recording.
   */
  abort(): void {
    this.activeTiming = null;
    this.pendingClassification = null;
    this.pendingOptimization = null;
    this.pendingQuality = null;
  }

  /**
   * Record a simple metric without full timing.
   */
  recordSimple(
    category: Category,
    latencyMs: number,
    success: boolean
  ): void {
    const now = Date.now();

    const entry: MetricsEntry = {
      id: `metrics_${now}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: now,
      sessionId: this.sessionId,
      latency: {
        totalMs: latencyMs,
        classificationMs: latencyMs,
        optimizationMs: 0,
        verificationMs: 0,
        contextMs: 0,
      },
      quality: {
        confidence: success ? 1 : 0,
        intentPreservation: 1,
        elementPreservation: 1,
        optimizationRatio: 1,
        passesUsed: 0,
      },
      classification: {
        category,
        domain: null,
        complexity: 'SIMPLE',
        confidence: success ? 1 : 0,
        cacheHit: false,
      },
      optimization: {
        changesCount: 0,
        changeTypes: [],
        originalLength: 0,
        optimizedLength: 0,
        contextInjected: false,
        templateUsed: null,
      },
      interaction: {
        action: null,
        decisionTimeMs: null,
        reviewRequired: false,
        feedbackProvided: false,
      },
    };

    this.store.record(entry);
  }

  /**
   * Get the session ID.
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Get the metrics store.
   */
  getStore(): MetricsStore {
    return this.store;
  }

  /**
   * Flush metrics to disk.
   */
  flush(): void {
    this.store.flush();
  }
}

/**
 * Create a metrics collector.
 */
export function createMetricsCollector(
  sessionId?: string,
  store?: MetricsStore
): MetricsCollector {
  return new MetricsCollector(sessionId, store);
}
