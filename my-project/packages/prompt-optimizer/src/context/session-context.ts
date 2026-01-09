/**
 * Session context provider.
 * Tracks conversation history and recent interactions.
 * Maps to spec section 3.1 - Session Context.
 */

import type { SessionContext, Message } from '../types/index.js';

/**
 * Maximum number of messages to keep in session history.
 */
const MAX_HISTORY_LENGTH = 20;

/**
 * Maximum age for session context in milliseconds (30 minutes).
 */
const MAX_SESSION_AGE_MS = 30 * 60 * 1000;

/**
 * Session context provider.
 */
export class SessionContextProvider {
  private messages: Message[] = [];
  private lastActivity: number = Date.now();
  private sessionStarted: number = Date.now();

  /**
   * Add a message to session history.
   */
  addMessage(message: Message): void {
    this.messages.push({
      ...message,
      timestamp: message.timestamp ?? Date.now(),
    });

    // Trim to max length
    if (this.messages.length > MAX_HISTORY_LENGTH) {
      this.messages = this.messages.slice(-MAX_HISTORY_LENGTH);
    }

    this.lastActivity = Date.now();
  }

  /**
   * Get recent messages for context.
   */
  getRecentMessages(limit: number = 5): Message[] {
    return this.messages.slice(-limit);
  }

  /**
   * Get session context for assembly.
   */
  getContext(): SessionContext {
    // Check if session is stale
    if (Date.now() - this.lastActivity > MAX_SESSION_AGE_MS) {
      this.reset();
    }

    return {
      conversationHistory: this.messages.slice(-10),
      recentTopics: this.extractTopics(),
      currentTask: this.inferCurrentTask(),
    };
  }

  /**
   * Extract topics from recent messages.
   */
  private extractTopics(): string[] {
    const topics = new Set<string>();
    const recentMessages = this.messages.slice(-5);

    for (const message of recentMessages) {
      // Extract code-related topics
      const codePatterns = [
        /\b(function|class|component|api|endpoint|database|test)\b/gi,
        /\b(bug|error|fix|issue|problem)\b/gi,
        /\b(react|vue|angular|node|python|typescript)\b/gi,
      ];

      for (const pattern of codePatterns) {
        const matches = message.content.match(pattern);
        if (matches) {
          matches.forEach((m) => topics.add(m.toLowerCase()));
        }
      }

      // Extract file paths as topics
      const filePaths = message.content.match(/[\/\w-]+\.\w+/g);
      if (filePaths) {
        filePaths.slice(0, 3).forEach((p) => topics.add(p));
      }
    }

    return Array.from(topics).slice(0, 10);
  }

  /**
   * Infer current task from recent messages.
   */
  private inferCurrentTask(): string | null {
    if (this.messages.length === 0) {
      return null;
    }

    const lastUserMessage = [...this.messages]
      .reverse()
      .find((m) => m.role === 'user');

    if (!lastUserMessage) {
      return null;
    }

    // Look for task indicators
    const taskPatterns = [
      /^(create|write|implement|add|build|make)\s+(.+)/i,
      /^(fix|debug|solve|resolve)\s+(.+)/i,
      /^(refactor|optimize|improve)\s+(.+)/i,
      /^(explain|describe|document)\s+(.+)/i,
    ];

    for (const pattern of taskPatterns) {
      const match = lastUserMessage.content.match(pattern);
      if (match) {
        return match[0].slice(0, 100);
      }
    }

    // Default to first sentence of last message
    const firstSentence = lastUserMessage.content.split(/[.!?\n]/)[0];
    return firstSentence.slice(0, 100) || null;
  }

  /**
   * Get session duration in milliseconds.
   */
  getSessionDuration(): number {
    return Date.now() - this.sessionStarted;
  }

  /**
   * Get message count.
   */
  getMessageCount(): number {
    return this.messages.length;
  }

  /**
   * Check if session has context.
   */
  hasContext(): boolean {
    return this.messages.length > 0;
  }

  /**
   * Reset session context.
   */
  reset(): void {
    this.messages = [];
    this.lastActivity = Date.now();
    this.sessionStarted = Date.now();
  }

  /**
   * Export session for persistence.
   */
  export(): { messages: Message[]; sessionStarted: number } {
    return {
      messages: this.messages,
      sessionStarted: this.sessionStarted,
    };
  }

  /**
   * Import session from persistence.
   */
  import(data: { messages: Message[]; sessionStarted: number }): void {
    this.messages = data.messages;
    this.sessionStarted = data.sessionStarted;
    this.lastActivity = Date.now();
  }
}

/**
 * Create a session context provider.
 */
export function createSessionContextProvider(): SessionContextProvider {
  return new SessionContextProvider();
}
