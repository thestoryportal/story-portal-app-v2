/**
 * Layer exports for the prompt optimizer package.
 */

export { Classifier, createClassifier } from './classifier.js';
export { IntentVerifier, createIntentVerifier } from './intent-verifier.js';
export { ContextAssembler, createContextAssembler } from './context-assembler.js';
export type { ContextAssemblerConfig } from './context-assembler.js';
export { ReviewGate, createReviewGate } from './review-gate.js';
export type { ReviewDecision, ReviewGateOptions } from './review-gate.js';

// Optimization layer exports
export {
  PassOneOptimizer,
  createPassOneOptimizer,
  PassTwoOptimizer,
  createPassTwoOptimizer,
  PassThreeOptimizer,
  createPassThreeOptimizer,
  MultiPassOptimizer,
  createMultiPassOptimizer,
} from './optimization/index.js';

// Template exports
export {
  TemplateRegistry,
  createTemplateRegistry,
  BaseDomainTemplate,
  CodeTemplate,
  createCodeTemplate,
  WritingTemplate,
  createWritingTemplate,
  AnalysisTemplate,
  createAnalysisTemplate,
  CreativeTemplate,
  createCreativeTemplate,
  ResearchTemplate,
  createResearchTemplate,
} from './optimization/templates/index.js';
export type {
  DomainTemplateConfig,
  EnhancementStrategy,
  IssuePattern,
} from './optimization/templates/index.js';

// Feedback layer exports
export {
  FeedbackLayer,
  createFeedbackLayer,
} from './feedback.js';
export type {
  FeedbackRequest,
  FeedbackResponse,
} from './feedback.js';
