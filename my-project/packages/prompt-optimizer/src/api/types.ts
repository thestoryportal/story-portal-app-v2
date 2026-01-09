/**
 * Internal API types for the Anthropic client.
 */

/** Anthropic message content */
export interface MessageContent {
  type: 'text';
  text: string;
}

/** Anthropic message */
export interface Message {
  role: 'user' | 'assistant';
  content: string | MessageContent[];
}

/** Anthropic API request */
export interface AnthropicRequest {
  model: string;
  max_tokens: number;
  messages: Message[];
  system?: string;
  temperature?: number;
}

/** Anthropic API response */
export interface AnthropicResponse {
  id: string;
  type: 'message';
  role: 'assistant';
  content: MessageContent[];
  model: string;
  stop_reason: 'end_turn' | 'max_tokens' | 'stop_sequence';
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

/** Client configuration */
export interface ClientConfig {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
  retries?: number;
  useMock?: boolean;
}

/** Request options */
export interface RequestOptions {
  model: string;
  systemPrompt: string;
  userMessage: string;
  maxTokens?: number;
  temperature?: number;
}

/** Parsed JSON response */
export interface ParsedResponse<T> {
  data: T;
  raw: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
  };
  latencyMs: number;
}
