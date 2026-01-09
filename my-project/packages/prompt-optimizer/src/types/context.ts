/**
 * Context types for the prompt optimizer.
 * Maps to spec section 6: Context Awareness System.
 */

/** A message in conversation history */
export interface Message {
  /** Role of the speaker */
  role: 'user' | 'assistant' | 'system';
  /** Content of the message */
  content: string;
  /** Timestamp of the message */
  timestamp?: number;
}

/** Session context from conversation history */
export interface SessionContext {
  /** Last N turns of conversation */
  lastTurns?: ConversationTurn[];
  /** Current active task thread if identifiable */
  activeTask?: string;
  /** Files, functions, concepts mentioned */
  referencedEntities?: ReferencedEntity[];
  /** Maximum tokens for session context */
  maxTokens?: number;
  /** Conversation history as messages */
  conversationHistory?: Message[];
  /** Recent topics discussed */
  recentTopics?: string[];
  /** Current task being worked on */
  currentTask?: string | null;
}

/** A single turn in conversation history */
export interface ConversationTurn {
  /** Role of the speaker */
  role: 'user' | 'assistant';
  /** Content of the turn */
  content: string;
  /** Timestamp of the turn */
  timestamp: string;
}

/** An entity referenced in conversation */
export interface ReferencedEntity {
  /** Type of entity */
  type: 'file' | 'function' | 'concept' | 'variable' | 'class';
  /** Name of the entity */
  name: string;
  /** Context where it was mentioned */
  context?: string;
}

/** Project context from codebase */
export interface ProjectContext {
  /** Project name */
  name?: string;
  /** Project type (library, application, monorepo) */
  type?: string | null;
  /** Primary programming language */
  language?: string | null;
  /** Detected framework */
  framework?: string | null;
  /** Key directories and files */
  structure?: ProjectStructure;
  /** Dependencies from package.json, etc. */
  dependencies?: string[];
  /** Last modified files */
  recentFiles?: string[];
  /** Whether project has tests */
  hasTests?: boolean;
  /** Whether project has CI */
  hasCi?: boolean;
  /** Maximum tokens for project context */
  maxTokens?: number;
}

/** Project directory structure */
export interface ProjectStructure {
  /** Root directory path */
  rootDir: string;
  /** Key directories */
  keyDirs: string[];
  /** Key files */
  keyFiles: string[];
  /** Detected project type */
  projectType?: 'node' | 'python' | 'rust' | 'go' | 'java' | 'other';
}

/** User preferences configuration */
export interface UserPreferences {
  /** Number of optimization passes (1-3) */
  optimizationLevel: 1 | 2 | 3;
  /** Response verbosity preference */
  verbosity: 'concise' | 'normal' | 'detailed';
  /** Whether to auto-optimize prompts */
  autoOptimize: boolean;
  /** Confidence threshold for auto-confirmation */
  confirmThreshold: number;
  /** Preferred domains for optimization */
  preferredDomains: string[];
  /** Style preferences */
  stylePreferences: StylePreference;
}

/** Style preferences */
export interface StylePreference {
  /** Code style preference */
  codeStyle: 'concise' | 'verbose' | 'commented';
  /** Explanation depth */
  explanationDepth: 'brief' | 'medium' | 'detailed';
  /** Format preference */
  formatPreference: 'plain' | 'markdown' | 'structured';
}

/** User context from profile */
export interface UserContext {
  /** User's expertise level */
  expertiseLevel?: 'beginner' | 'intermediate' | 'senior' | 'expert';
  /** Preferred response verbosity */
  preferredVerbosity?: 'concise' | 'balanced' | 'detailed';
  /** Common domains the user works in */
  commonDomains?: Record<string, number>;
  /** Optimization acceptance rate */
  optimizationAcceptanceRate?: number;
  /** Average confidence at acceptance */
  averageConfidenceAtAcceptance?: number;
  /** Custom rules defined by user */
  customRules?: string[];
  /** Maximum tokens for user context */
  maxTokens?: number;
  /** User preferences */
  preferences?: UserPreferences;
  /** Frequent usage patterns */
  frequentPatterns?: string[];
  /** Acceptance rate */
  acceptanceRate?: number;
}

/** Terminal context from recent commands */
export interface TerminalContext {
  /** Current working directory */
  cwd?: string;
  /** Previous terminal commands */
  lastCommands?: string[];
  /** Current git status */
  gitStatus?: GitStatus;
  /** Current working directory (alias) */
  currentDirectory?: string;
  /** Running processes */
  runningProcesses?: string[];
  /** Maximum tokens for terminal context */
  maxTokens?: number;
  /** Current shell */
  shell?: string | null;
  /** Recent command */
  recentCommand?: string | null;
  /** Recent command output */
  recentOutput?: string | null;
  /** Last exit code */
  exitCode?: number | null;
  /** Relevant environment variables */
  environment?: Record<string, string>;
  /** Terminal size */
  terminalSize?: { columns: number; rows: number } | null;
}

/** Git repository status */
export interface GitStatus {
  /** Current branch name */
  branch: string;
  /** Whether there are uncommitted changes */
  hasUncommittedChanges: boolean;
  /** List of modified files */
  modifiedFiles?: string[];
  /** Whether ahead/behind remote */
  aheadBehind?: {
    ahead: number;
    behind: number;
  };
}

/** Assembled context from all sources */
export interface AssembledContext {
  /** Session history context */
  session?: SessionContext;
  /** Project metadata context */
  project?: ProjectContext;
  /** User preferences context */
  user?: UserContext;
  /** Terminal state context */
  terminal?: TerminalContext;
  /** Total tokens used by context */
  totalTokens: number;
  /** Context assembly confidence */
  confidence: number;
}

/** Context injection decision */
export interface ContextInjection {
  /** Language to inject */
  language?: string;
  /** Framework to inject */
  framework?: string;
  /** Relevant files to mention */
  relevantFiles?: string[];
  /** Expertise adjustment */
  expertiseAdjustment?: string;
  /** Session references to include */
  sessionReferences?: string[];
  /** Terminal state to mention */
  terminalState?: string;
  /** Total tokens used */
  contextTokensUsed: number;
  /** Confidence in injection */
  injectionConfidence: number;
}

/** Context injection rules */
export interface ContextInjectionRules {
  /** Always inject these */
  alwaysInject: string[];
  /** Conditionally inject based on prompt */
  conditionallyInject: string[];
  /** Never inject these */
  neverInject: string[];
  /** Maximum context expansion ratio */
  maxExpansionRatio: number;
}
