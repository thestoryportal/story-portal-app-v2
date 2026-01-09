/**
 * Context assembler layer.
 * Combines context from all sources for prompt optimization.
 * Maps to spec section 3 - Context Assembly.
 */

import type {
  AssembledContext,
  ContextInjection,
} from '../types/index.js';
import {
  SessionContextProvider,
  ProjectContextProvider,
  UserContextProvider,
  TerminalContextProvider,
} from '../context/index.js';

/**
 * Default token budgets for each context source.
 */
const DEFAULT_TOKEN_BUDGETS = {
  session: 500,
  project: 200,
  user: 100,
  terminal: 100,
  total: 800,
};

/**
 * Context assembler configuration.
 */
export interface ContextAssemblerConfig {
  /** Enable session context */
  enableSession?: boolean;
  /** Enable project context */
  enableProject?: boolean;
  /** Enable user context */
  enableUser?: boolean;
  /** Enable terminal context */
  enableTerminal?: boolean;
  /** Token budgets */
  tokenBudgets?: Partial<typeof DEFAULT_TOKEN_BUDGETS>;
}

/**
 * Context assembler layer.
 */
export class ContextAssembler {
  private sessionProvider: SessionContextProvider;
  private projectProvider: ProjectContextProvider;
  private userProvider: UserContextProvider;
  private terminalProvider: TerminalContextProvider;
  private config: Required<ContextAssemblerConfig>;

  constructor(config: ContextAssemblerConfig = {}) {
    this.sessionProvider = new SessionContextProvider();
    this.projectProvider = new ProjectContextProvider();
    this.userProvider = new UserContextProvider();
    this.terminalProvider = new TerminalContextProvider();

    this.config = {
      enableSession: config.enableSession ?? true,
      enableProject: config.enableProject ?? true,
      enableUser: config.enableUser ?? true,
      enableTerminal: config.enableTerminal ?? true,
      tokenBudgets: {
        ...DEFAULT_TOKEN_BUDGETS,
        ...config.tokenBudgets,
      },
    };
  }

  /**
   * Assemble context from all sources.
   */
  async assemble(projectPath?: string): Promise<AssembledContext> {
    const contexts: Partial<AssembledContext> = {};
    let totalTokens = 0;
    let confidence = 1.0;

    // Gather session context
    if (this.config.enableSession) {
      const sessionContext = this.sessionProvider.getContext();
      if (sessionContext.conversationHistory && sessionContext.conversationHistory.length > 0) {
        contexts.session = sessionContext;
        totalTokens += this.estimateTokens(JSON.stringify(sessionContext));
        confidence *= 0.95; // Slight reduction for session context uncertainty
      }
    }

    // Gather project context
    if (this.config.enableProject) {
      try {
        const projectContext = await this.projectProvider.getContext(projectPath);
        if (projectContext.language || projectContext.framework) {
          contexts.project = projectContext;
          totalTokens += this.estimateTokens(JSON.stringify(projectContext));
          confidence *= 0.98;
        }
      } catch {
        // Project context unavailable
        confidence *= 0.9;
      }
    }

    // Gather user context
    if (this.config.enableUser) {
      const userContext = this.userProvider.getContext();
      contexts.user = userContext;
      totalTokens += this.estimateTokens(JSON.stringify(userContext));
    }

    // Gather terminal context
    if (this.config.enableTerminal) {
      const terminalContext = this.terminalProvider.getContext();
      if (terminalContext.cwd) {
        contexts.terminal = terminalContext;
        totalTokens += this.estimateTokens(JSON.stringify(terminalContext));
      }
    }

    return {
      ...contexts,
      totalTokens,
      confidence: Math.max(0.5, confidence),
    } as AssembledContext;
  }

  /**
   * Generate context injection for a prompt.
   */
  generateInjection(
    prompt: string,
    context: AssembledContext
  ): ContextInjection {
    const injection: ContextInjection = {
      contextTokensUsed: 0,
      injectionConfidence: context.confidence,
    };

    // Inject language/framework if detected and not in prompt
    if (context.project) {
      const promptLower = prompt.toLowerCase();

      if (context.project.language && !promptLower.includes(context.project.language)) {
        injection.language = context.project.language;
      }

      if (context.project.framework && !promptLower.includes(context.project.framework)) {
        injection.framework = context.project.framework;
      }
    }

    // Inject relevant files from session context
    if (context.session?.recentTopics) {
      const fileTopics = context.session.recentTopics.filter(
        (t) => t.includes('.') && t.includes('/')
      );
      if (fileTopics.length > 0) {
        injection.relevantFiles = fileTopics.slice(0, 3);
      }
    }

    // Inject expertise adjustment
    if (context.user?.expertiseLevel) {
      if (context.user.expertiseLevel === 'beginner') {
        injection.expertiseAdjustment = 'Provide detailed explanations.';
      } else if (context.user.expertiseLevel === 'expert') {
        injection.expertiseAdjustment = 'Assume advanced knowledge.';
      }
    }

    // Inject session references
    if (context.session?.currentTask) {
      injection.sessionReferences = [context.session.currentTask];
    }

    // Inject terminal state if relevant
    if (context.terminal?.recentCommand) {
      const errorPatterns = ['error', 'fail', 'exception', 'denied', 'not found'];
      const lastOutput = context.terminal.recentOutput?.toLowerCase() ?? '';

      if (errorPatterns.some((p) => lastOutput.includes(p))) {
        injection.terminalState = `Recent command: ${context.terminal.recentCommand}`;
      }
    }

    // Calculate tokens used
    injection.contextTokensUsed = this.estimateTokens(JSON.stringify(injection));

    return injection;
  }

  /**
   * Apply context injection to a prompt.
   */
  applyInjection(prompt: string, injection: ContextInjection): string {
    const parts: string[] = [];

    // Add context header
    const contextParts: string[] = [];

    if (injection.language) {
      contextParts.push(`Language: ${injection.language}`);
    }

    if (injection.framework) {
      contextParts.push(`Framework: ${injection.framework}`);
    }

    if (injection.relevantFiles && injection.relevantFiles.length > 0) {
      contextParts.push(`Relevant files: ${injection.relevantFiles.join(', ')}`);
    }

    if (injection.terminalState) {
      contextParts.push(injection.terminalState);
    }

    // Build context string
    if (contextParts.length > 0) {
      parts.push(`[Context: ${contextParts.join('; ')}]`);
    }

    // Add expertise adjustment as suffix
    if (injection.expertiseAdjustment) {
      parts.push(injection.expertiseAdjustment);
    }

    // Add session references
    if (injection.sessionReferences && injection.sessionReferences.length > 0) {
      parts.push(`(Continuing: ${injection.sessionReferences[0]})`);
    }

    // Combine with prompt
    if (parts.length > 0) {
      return `${parts.join(' ')}\n\n${prompt}`;
    }

    return prompt;
  }

  /**
   * Estimate token count for a string.
   */
  private estimateTokens(text: string): number {
    // Simple estimation: ~4 characters per token
    return Math.ceil(text.length / 4);
  }

  /**
   * Get session provider for external use.
   */
  getSessionProvider(): SessionContextProvider {
    return this.sessionProvider;
  }

  /**
   * Get project provider for external use.
   */
  getProjectProvider(): ProjectContextProvider {
    return this.projectProvider;
  }

  /**
   * Get user provider for external use.
   */
  getUserProvider(): UserContextProvider {
    return this.userProvider;
  }

  /**
   * Get terminal provider for external use.
   */
  getTerminalProvider(): TerminalContextProvider {
    return this.terminalProvider;
  }

  /**
   * Set providers for testing.
   */
  setProviders(providers: {
    session?: SessionContextProvider;
    project?: ProjectContextProvider;
    user?: UserContextProvider;
    terminal?: TerminalContextProvider;
  }): void {
    if (providers.session) this.sessionProvider = providers.session;
    if (providers.project) this.projectProvider = providers.project;
    if (providers.user) this.userProvider = providers.user;
    if (providers.terminal) this.terminalProvider = providers.terminal;
  }
}

/**
 * Create a context assembler.
 */
export function createContextAssembler(
  config?: ContextAssemblerConfig
): ContextAssembler {
  return new ContextAssembler(config);
}
