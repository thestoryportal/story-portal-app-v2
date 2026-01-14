import { Ollama } from 'ollama';
import { LLMError } from '../errors.js';

export interface LLMConfig {
  host?: string;
  baseUrl?: string;
  defaultModel?: string;
  models?: {
    general: string;
    reasoning: string;
    code: string;
    fast: string;
  };
  temperature?: number;
  maxTokens?: number;
  timeout?: number;
  defaultOptions?: {
    temperature: number;
    num_ctx: number;
    num_predict: number;
  };
}

export interface GenerateParams {
  model?: string;
  prompt: string;
  system?: string;
  format?: 'json';
  temperature?: number;
  maxTokens?: number;
  options?: {
    temperature?: number;
    num_ctx?: number;
    num_predict?: number;
    seed?: number;
  };
}

export class LLMPipeline {
  private ollama: Ollama;
  private defaultModel: string;
  private models: { general: string; reasoning: string; code: string; fast: string };
  private defaultOptions: { temperature: number; num_ctx: number; num_predict: number };

  constructor(config: LLMConfig) {
    const host = config.baseUrl || config.host || 'http://localhost:11434';
    this.ollama = new Ollama({ host });
    this.defaultModel = config.defaultModel || 'llama3.1:8b';
    this.models = config.models || {
      general: this.defaultModel,
      reasoning: this.defaultModel,
      code: 'codellama:7b',
      fast: 'mistral:7b'
    };
    this.defaultOptions = config.defaultOptions || {
      temperature: config.temperature || 0.1,
      num_ctx: 8192,
      num_predict: config.maxTokens || 2048
    };
  }

  async generate(params: GenerateParams): Promise<string> {
    const model = params.model || this.models.general;
    try {
      const response = await this.ollama.generate({
        model,
        prompt: params.prompt,
        system: params.system,
        format: params.format,
        stream: false,
        options: {
          temperature: params.temperature ?? params.options?.temperature ?? this.defaultOptions.temperature,
          num_ctx: params.options?.num_ctx ?? this.defaultOptions.num_ctx,
          num_predict: params.maxTokens ?? params.options?.num_predict ?? this.defaultOptions.num_predict,
          seed: params.options?.seed
        }
      });

      return response.response;
    } catch (error) {
      throw new LLMError(
        model,
        error instanceof Error ? error.message : 'Unknown error'
      );
    }
  }

  async chat(messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>, params?: {
    model?: string;
    format?: 'json';
    options?: Partial<LLMConfig['defaultOptions']>;
  }): Promise<string> {
    const model = params?.model || this.models.general;
    try {
      const response = await this.ollama.chat({
        model,
        messages,
        format: params?.format,
        stream: false,
        options: {
          temperature: params?.options?.temperature ?? this.defaultOptions.temperature,
          num_ctx: params?.options?.num_ctx ?? this.defaultOptions.num_ctx,
          num_predict: params?.options?.num_predict ?? this.defaultOptions.num_predict
        }
      });

      return response.message.content;
    } catch (error) {
      throw new LLMError(
        model,
        error instanceof Error ? error.message : 'Unknown error'
      );
    }
  }

  /**
   * Self-consistency verification using multiple samples
   */
  async selfConsistencyVerify(
    prompt: string,
    numSamples: number = 5
  ): Promise<{ answer: string; confidence: number; agreementRate: number }> {
    const samples = await Promise.all(
      Array(numSamples).fill(null).map((_, i) =>
        this.generate({
          prompt,
          format: 'json',
          options: { temperature: 0.7, seed: i * 1000 }
        })
      )
    );

    // Parse and count responses
    const parsed = samples.map(s => {
      try {
        return JSON.parse(s);
      } catch {
        return { verdict: 'uncertain' };
      }
    });

    const verdictCounts = parsed.reduce((acc, p) => {
      const verdict = p.verdict || 'uncertain';
      acc[verdict] = (acc[verdict] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const entries = Object.entries(verdictCounts).sort((a, b) => (b[1] as number) - (a[1] as number));
    const maxVerdict = entries[0] as [string, number];

    return {
      answer: maxVerdict[0],
      confidence: maxVerdict[1] / numSamples,
      agreementRate: maxVerdict[1] / numSamples
    };
  }

  /**
   * Ensemble voting across multiple models
   */
  async ensembleVote(
    prompt: string,
    models?: string[]
  ): Promise<{ verdict: string; confidence: number; votes: Record<string, string> }> {
    const modelsToUse = models || [
      this.models.general,
      this.models.reasoning,
      this.models.fast
    ];

    const votes = await Promise.all(
      modelsToUse.map(async (model) => {
        try {
          const response = await this.generate({ model, prompt, format: 'json' });
          const parsed = JSON.parse(response);
          return { model, verdict: parsed.verdict || 'uncertain' };
        } catch {
          return { model, verdict: 'uncertain' };
        }
      })
    );

    const verdictCounts = votes.reduce((acc, v) => {
      acc[v.verdict] = (acc[v.verdict] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const entries = Object.entries(verdictCounts).sort((a, b) => b[1] - a[1]);
    const maxVerdict = entries[0];

    return {
      verdict: maxVerdict[0],
      confidence: maxVerdict[1] / modelsToUse.length,
      votes: Object.fromEntries(votes.map(v => [v.model, v.verdict]))
    };
  }

  /**
   * Adversarial debate between advocate and skeptic
   */
  async debate(
    claim: string,
    evidence: string
  ): Promise<{ verdict: string; confidence: number; reasoning: string }> {
    // Advocate argues TRUE
    const advocateResponse = await this.generate({
      model: this.models.general,
      prompt: `
You must argue that this claim is TRUE.
Claim: "${claim}"
Evidence: ${evidence}
Make your strongest case with specific citations.
Output JSON: { "arguments": string[], "strength": number }`,
      format: 'json'
    });

    // Skeptic argues FALSE
    const skepticResponse = await this.generate({
      model: this.models.reasoning,
      prompt: `
You must argue that this claim is FALSE or MISLEADING.
Claim: "${claim}"
Evidence: ${evidence}
Challenge assumptions and find contradictions.
Output JSON: { "arguments": string[], "strength": number }`,
      format: 'json'
    });

    // Judge evaluates
    const judgeResponse = await this.generate({
      model: this.models.general,
      prompt: `
Evaluate these arguments about the claim.
Claim: "${claim}"

ADVOCATE'S CASE: ${advocateResponse}
SKEPTIC'S CASE: ${skepticResponse}

Which side has stronger evidence?
Output JSON: { "verdict": "verified" | "refuted" | "uncertain", "confidence": number, "reasoning": string }`,
      format: 'json'
    });

    try {
      return JSON.parse(judgeResponse);
    } catch {
      return {
        verdict: 'uncertain',
        confidence: 0.5,
        reasoning: 'Failed to parse judge response'
      };
    }
  }

  /**
   * Structured output extraction with retry
   */
  async extractStructured<T>(
    prompt: string,
    parseResponse: (response: string) => T,
    maxRetries: number = 3
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await this.generate({
          prompt,
          format: 'json',
          options: { temperature: 0.1 }
        });

        return parseResponse(response);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');

        // Add feedback to prompt for retry
        if (attempt < maxRetries - 1) {
          prompt += `\n\nPrevious attempt failed with: ${lastError.message}. Please fix the JSON format.`;
        }
      }
    }

    throw new LLMError(
      this.models.general,
      `Failed after ${maxRetries} attempts: ${lastError?.message}`
    );
  }

  /**
   * Check if a model is available
   */
  async isModelAvailable(model: string): Promise<boolean> {
    try {
      const response = await this.ollama.list();
      return response.models.some(m => m.name === model || m.name.startsWith(model + ':'));
    } catch {
      return false;
    }
  }

  /**
   * Pull a model if not available
   */
  async ensureModel(model: string): Promise<void> {
    const available = await this.isModelAvailable(model);
    if (!available) {
      await this.ollama.pull({ model });
    }
  }
}

/**
 * Mock LLM Pipeline for when Ollama is disabled.
 * Returns placeholder responses that indicate LLM processing is unavailable.
 */
export class MockLLMPipeline {
  async generate(_params: GenerateParams): Promise<string> {
    return JSON.stringify({
      note: 'LLM processing disabled',
      claims: [],
      entities: [],
      summary: 'LLM analysis unavailable'
    });
  }

  async chat(_messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>, _params?: {
    model?: string;
    format?: 'json';
    options?: Record<string, unknown>;
  }): Promise<string> {
    return JSON.stringify({ note: 'LLM chat disabled' });
  }

  async selfConsistencyVerify(
    _prompt: string,
    _numSamples: number = 5
  ): Promise<{ answer: string; confidence: number; agreementRate: number }> {
    return { answer: 'unavailable', confidence: 0, agreementRate: 0 };
  }

  async ensembleVote(
    _prompt: string,
    _models?: string[]
  ): Promise<{ verdict: string; confidence: number; votes: Record<string, string> }> {
    return { verdict: 'unavailable', confidence: 0, votes: {} };
  }

  async debate(
    _claim: string,
    _evidence: string
  ): Promise<{ verdict: string; confidence: number; reasoning: string }> {
    return { verdict: 'unavailable', confidence: 0, reasoning: 'LLM disabled' };
  }

  async extractStructured<T>(
    _prompt: string,
    parseResponse: (response: string) => T,
    _maxRetries: number = 3
  ): Promise<T> {
    return parseResponse(JSON.stringify({ note: 'LLM disabled' }));
  }

  async isModelAvailable(_model: string): Promise<boolean> {
    return false;
  }

  async ensureModel(_model: string): Promise<void> {
    // No-op
  }
}
