/**
 * Anthropic API client for the prompt optimizer.
 * Provides direct SDK integration with mock support for testing.
 */

import Anthropic from '@anthropic-ai/sdk';
import type {
  ClassificationRequest,
  ClassificationResponse,
  OptimizationRequest,
  OptimizationResponse,
  VerificationRequest,
  VerificationResponse,
  OptimizerApiClient,
} from '../types/index.js';
import type { ClientConfig, RequestOptions, ParsedResponse } from './types.js';
import {
  CLASSIFICATION_PROMPT,
  PASS_ONE_PROMPT,
  VERIFICATION_PROMPT,
  MODEL_CONFIG,
  RETRY_CONFIG,
} from '../constants/index.js';
import { OptimizerApiError, RateLimitError } from '../types/api.js';

/** Mock responses for testing */
const MOCK_RESPONSES = {
  classification: {
    category: 'OPTIMIZE' as const,
    domain: 'CODE' as const,
    complexity: 'MODERATE' as const,
    confidence: 0.85,
    reasoning: 'Mock classification response',
    cacheHit: false,
    latencyMs: 50,
  },
  verification: {
    status: 'VERIFIED' as const,
    similarityScore: 0.92,
    preservedRatio: 0.95,
    issues: [],
    recommendation: 'Optimization verified successfully',
  },
};

/** Common spelling corrections - programming and general terms */
const SPELLING_CORRECTIONS: Record<string, string> = {
  // Programming terms
  'fucntion': 'function',
  'funtion': 'function',
  'funciton': 'function',
  'fucniton': 'function',
  'functon': 'function',
  'fuction': 'function',
  'compoennt': 'component',
  'componet': 'component',
  'compnent': 'component',
  'componant': 'component',
  'compenent': 'component',
  'compoent': 'component',
  'vairable': 'variable',
  'varialbe': 'variable',
  'variabel': 'variable',
  'varaible': 'variable',
  'vaiable': 'variable',
  'wirte': 'write',
  'wrtie': 'write',
  'wriet': 'write',
  'wtire': 'write',
  'reutrn': 'return',
  'retrun': 'return',
  'retrn': 'return',
  'retunr': 'return',
  'improt': 'import',
  'imoprt': 'import',
  'ipmort': 'import',
  'exoprt': 'export',
  'exprot': 'export',
  'exort': 'export',
  'clas': 'class',
  'calss': 'class',
  'clss': 'class',
  'interfce': 'interface',
  'inteface': 'interface',
  'iterface': 'interface',
  'arary': 'array',
  'arry': 'array',
  'arrya': 'array',
  'stirng': 'string',
  'strng': 'string',
  'sring': 'string',
  'strnig': 'string',
  'nubmer': 'number',
  'numbr': 'number',
  'numebr': 'number',
  'boolen': 'boolean',
  'booelean': 'boolean',
  'bolean': 'boolean',
  'obejct': 'object',
  'objcet': 'object',
  'ojbect': 'object',
  'null': 'null',
  'nul': 'null',
  'undifined': 'undefined',
  'undefiend': 'undefined',
  'udnefined': 'undefined',
  'consle': 'console',
  'consloe': 'console',
  'cosole': 'console',
  'debuger': 'debugger',
  'degugger': 'debugger',
  'asnync': 'async',
  'aysnc': 'async',
  'asycn': 'async',
  'awiat': 'await',
  'awayt': 'await',
  'awit': 'await',
  'promies': 'promise',
  'pormise': 'promise',
  'pormsie': 'promise',
  'databse': 'database',
  'datbase': 'database',
  'databaes': 'database',
  'qurey': 'query',
  'qeury': 'query',
  'quert': 'query',
  'resopnse': 'response',
  'reponse': 'response',
  'respone': 'response',
  'reqeust': 'request',
  'reuqest': 'request',
  'requets': 'request',
  'parasm': 'params',
  'parms': 'params',
  'paramters': 'parameters',
  'parametrs': 'parameters',
  'paremeter': 'parameter',
  'templete': 'template',
  'tempalte': 'template',
  'templat': 'template',
  'modle': 'model',
  'mdoel': 'model',
  'modl': 'model',
  'schem': 'schema',
  'shcema': 'schema',
  'schmea': 'schema',
  'endpint': 'endpoint',
  'ednpoint': 'endpoint',
  'enpoint': 'endpoint',
  'midelware': 'middleware',
  'middlware': 'middleware',
  'midleware': 'middleware',
  'authetication': 'authentication',
  'authenticaiton': 'authentication',
  'athentication': 'authentication',
  'atuhentication': 'authentication',
  'authoriation': 'authorization',
  'authorizaiton': 'authorization',
  'validaton': 'validation',
  'valdiation': 'validation',
  'vaidation': 'validation',
  'configration': 'configuration',
  'configuraiton': 'configuration',
  'confg': 'config',
  'ocnfig': 'config',
  'initalize': 'initialize',
  'intiialize': 'initialize',
  'initailize': 'initialize',
  // React specific
  'reat': 'react',
  'raect': 'react',
  'recat': 'react',
  'porps': 'props',
  'prpos': 'props',
  'pops': 'props',
  'satte': 'state',
  'staet': 'state',
  'stae': 'state',
  'rendrer': 'renderer',
  'renderr': 'render',
  'redner': 'render',
  'hoks': 'hooks',
  'hokos': 'hooks',
  'useStae': 'useState',
  'usestate': 'useState',
  'useEffct': 'useEffect',
  'useeffect': 'useEffect',
  'useMemo': 'useMemo',
  'usememo': 'useMemo',
  'useCallbakc': 'useCallback',
  'usecallback': 'useCallback',
  'useRef': 'useRef',
  'useref': 'useRef',
  'useConext': 'useContext',
  'usecontext': 'useContext',
  // Common words
  'teh': 'the',
  'hte': 'the',
  'adn': 'and',
  'nad': 'and',
  'taht': 'that',
  'thta': 'that',
  'wiht': 'with',
  'wtih': 'with',
  'whit': 'with',
  'fo': 'of',
  'ot': 'to',
  'si': 'is',
  'ti': 'it',
  'nto': 'not',
  'ont': 'not',
  'cna': 'can',
  'coudl': 'could',
  'woudl': 'would',
  'shoudl': 'should',
  'jsut': 'just',
  'jstu': 'just',
  'waht': 'what',
  'whta': 'what',
  'hwat': 'what',
  'hwo': 'how',
  'woh': 'who',
  'hwy': 'why',
  'wehn': 'when',
  'wher': 'where',
  'wheer': 'where',
  'htis': 'this',
  'tihs': 'this',
  'thsi': 'this',
  'fiel': 'file',
  'flie': 'file',
  'floder': 'folder',
  'fodler': 'folder',
  'cerate': 'create',
  'craete': 'create',
  'creat': 'create',
  'delte': 'delete',
  'deleet': 'delete',
  'deleete': 'delete',
  'upate': 'update',
  'udpate': 'update',
  'upadte': 'update',
  'serach': 'search',
  'saerch': 'search',
  'seach': 'search',
  'buton': 'button',
  'buttn': 'button',
  'buttno': 'button',
  'mehtod': 'method',
  'metohd': 'method',
  'mehod': 'method',
  'errro': 'error',
  'erorr': 'error',
  'erro': 'error',
  'mesage': 'message',
  'messge': 'message',
  'messgae': 'message',
  'plase': 'please',
  'pleae': 'please',
  'palese': 'please',
  'pls': 'please',
  'hlep': 'help',
  'hep': 'help',
  'halp': 'help',
  'expalin': 'explain',
  'explian': 'explain',
  'explani': 'explain',
  'implment': 'implement',
  'impelment': 'implement',
  'implmenet': 'implement',
  'refator': 'refactor',
  'refacor': 'refactor',
  'refatcor': 'refactor',
  'optmize': 'optimize',
  'optimze': 'optimize',
  'optmise': 'optimize',
  'debg': 'debug',
  'degub': 'debug',
  'dubug': 'debug',
  'isue': 'issue',
  'isseu': 'issue',
  'isssue': 'issue',
  'prolbem': 'problem',
  'probelm': 'problem',
  'porblem': 'problem',
  'soltuion': 'solution',
  'soluton': 'solution',
  'soltuin': 'solution',
  'examlpe': 'example',
  'exmaple': 'example',
  'exampel': 'example',
  'docuemnt': 'document',
  'documnet': 'document',
  'documetn': 'document',
  'applicaiton': 'application',
  'applcation': 'application',
  'aplication': 'application',
  'infomation': 'information',
  'informaiton': 'information',
  'infromation': 'information',
  'difefrent': 'different',
  'differnt': 'different',
  'diferent': 'different',
  'beacuse': 'because',
  'becuase': 'because',
  'becasue': 'because',
  'probaly': 'probably',
  'probalby': 'probably',
  'porbably': 'probably',
  'specifc': 'specific',
  'specfic': 'specific',
  'sepcifc': 'specific',
  // More common typos
  'knwo': 'know',
  'konw': 'know',
  'kwno': 'know',
  'knwon': 'known',
  'unkown': 'unknown',
  'unknwon': 'unknown',
  'recieve': 'receive',
  'recieved': 'received',
  'occured': 'occurred',
  'occuring': 'occurring',
  'seperate': 'separate',
  'definately': 'definitely',
  'defintely': 'definitely',
  'definetly': 'definitely',
  'basicly': 'basically',
  'basicaly': 'basically',
  'esentially': 'essentially',
  'essentialy': 'essentially',
  'necesary': 'necessary',
  'neccessary': 'necessary',
  'succesful': 'successful',
  'successfull': 'successful',
  'succesfully': 'successfully',
  'immediatly': 'immediately',
  'immedialtey': 'immediately',
  'probem': 'problem',
  'porbelm': 'problem',
  'alot': 'a lot',
  'somthing': 'something',
  'somethign': 'something',
  'anythign': 'anything',
  'everthing': 'everything',
  'everythign': 'everything',
  'nothign': 'nothing',
  'actualy': 'actually',
  'acutally': 'actually',
  'accross': 'across',
  'untill': 'until',
  'supprot': 'support',
  'suport': 'support',
  'langauge': 'language',
  'languaeg': 'language',
  'beggining': 'beginning',
  'begining': 'beginning',
  'enviroment': 'environment',
  'enviornment': 'environment',
  'developement': 'development',
  'devlopment': 'development',
  'managment': 'management',
  'managemnt': 'management',
  'perfomance': 'performance',
  'performace': 'performance',
  'dependancy': 'dependency',
  'dependecies': 'dependencies',
  'dependancies': 'dependencies',
  'repositroy': 'repository',
  'repostiory': 'repository',
  'directroy': 'directory',
  'direcotry': 'directory',
  'librray': 'library',
  'libary': 'library',
  'framwork': 'framework',
  'framewrok': 'framework',
  'syntaxt': 'syntax',
  'sytax': 'syntax',
  'arguemnt': 'argument',
  'arguement': 'argument',
  'arugment': 'argument',
  'properyt': 'property',
  'proprety': 'property',
  'attribtue': 'attribute',
  'atribute': 'attribute',
  'elemnt': 'element',
  'elment': 'element',
  'containter': 'container',
  'contaienr': 'container',
  'exectue': 'execute',
  'excute': 'execute',
  'excecute': 'execute',
  'proccess': 'process',
  'porcess': 'process',
  'acces': 'access',
  'acccess': 'access',
  'conneciton': 'connection',
  'conection': 'connection',
  'sesison': 'session',
  'sesson': 'session',
  'broswer': 'browser',
  'brwoser': 'browser',
  'reuslt': 'result',
  'resutl': 'result',
  'outptu': 'output',
  'ouptut': 'output',
  'inpute': 'input',
  'ipnut': 'input',
};

/**
 * Apply spelling corrections to text.
 */
function applySpellingCorrections(text: string): { corrected: string; corrections: Array<{ from: string; to: string }> } {
  const corrections: Array<{ from: string; to: string }> = [];
  let corrected = text;

  // Split into words while preserving punctuation and spacing
  const wordPattern = /\b([a-zA-Z]+)\b/g;
  let match;

  while ((match = wordPattern.exec(text)) !== null) {
    const word = match[1];
    const lowerWord = word.toLowerCase();

    if (SPELLING_CORRECTIONS[lowerWord]) {
      const correction = SPELLING_CORRECTIONS[lowerWord];
      // Preserve original case pattern
      let fixedWord = correction;
      if (word[0] === word[0].toUpperCase()) {
        fixedWord = correction.charAt(0).toUpperCase() + correction.slice(1);
      }
      if (word === word.toUpperCase()) {
        fixedWord = correction.toUpperCase();
      }

      if (word !== fixedWord) {
        corrections.push({ from: word, to: fixedWord });
        // Replace in the corrected string
        corrected = corrected.replace(new RegExp(`\\b${word}\\b`), fixedWord);
      }
    }
  }

  return { corrected, corrections };
}

/**
 * Apply grammar and punctuation fixes.
 */
function applyGrammarFixes(text: string): { corrected: string; fixes: string[] } {
  let corrected = text;
  const fixes: string[] = [];

  // Capitalize first letter of sentence
  if (corrected.length > 0 && corrected[0] !== corrected[0].toUpperCase()) {
    corrected = corrected.charAt(0).toUpperCase() + corrected.slice(1);
    fixes.push('Capitalized first letter');
  }

  // Fix multiple spaces
  if (/\s{2,}/.test(corrected)) {
    corrected = corrected.replace(/\s{2,}/g, ' ');
    fixes.push('Fixed multiple spaces');
  }

  // Fix "i" to "I" when standalone
  if (/\bi\b/.test(corrected)) {
    corrected = corrected.replace(/\bi\b/g, 'I');
    fixes.push('Capitalized "I"');
  }

  // Fix missing space after punctuation
  if (/[.!?,][a-zA-Z]/.test(corrected)) {
    corrected = corrected.replace(/([.!?,])([a-zA-Z])/g, '$1 $2');
    fixes.push('Added space after punctuation');
  }

  // Fix "dont" -> "don't", "cant" -> "can't", etc.
  const contractionFixes: Record<string, string> = {
    'dont': "don't",
    'cant': "can't",
    'wont': "won't",
    'isnt': "isn't",
    'arent': "aren't",
    'wasnt': "wasn't",
    'werent': "weren't",
    'hasnt': "hasn't",
    'havent': "haven't",
    'hadnt': "hadn't",
    'doesnt': "doesn't",
    'didnt': "didn't",
    'couldnt': "couldn't",
    'wouldnt': "wouldn't",
    'shouldnt': "shouldn't",
    'im': "I'm",
    'ive': "I've",
    'id': "I'd",
    'ill': "I'll",
    'youre': "you're",
    'youve': "you've",
    'youd': "you'd",
    'youll': "you'll",
    'hes': "he's",
    'shes': "she's",
    'its': "it's", // Be careful - "its" is also valid possessive
    'theyre': "they're",
    'theyve': "they've",
    'theyd': "they'd",
    'theyll': "they'll",
    'weve': "we've",
    'wed': "we'd",
    'well': "we'll", // Careful - "well" is also a word
    'whats': "what's",
    'thats': "that's",
    'heres': "here's",
    'theres': "there's",
    'wheres': "where's",
    'hows': "how's",
    'lets': "let's",
  };

  for (const [wrong, right] of Object.entries(contractionFixes)) {
    const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
    if (regex.test(corrected)) {
      // Skip "well" and "its" as they have valid uses
      if (wrong === 'well' || wrong === 'its') continue;
      corrected = corrected.replace(regex, right);
      fixes.push(`Fixed "${wrong}" to "${right}"`);
    }
  }

  // Trim whitespace
  if (corrected !== corrected.trim()) {
    corrected = corrected.trim();
    fixes.push('Trimmed whitespace');
  }

  return { corrected, fixes };
}

/**
 * Add clarity improvements for Claude Code context.
 */
function addClarityImprovements(text: string): { improved: string; improvements: string[] } {
  let improved = text;
  const improvements: string[] = [];

  // Add "Please" if starting with imperative verbs without politeness
  const imperativeStarts = /^(help|show|explain|create|make|write|fix|debug|refactor|implement|add|remove|delete|update|find|search|list|get|set|run|test|build|deploy)\b/i;
  if (imperativeStarts.test(improved) && !/^please\b/i.test(improved)) {
    improved = 'Please ' + improved.charAt(0).toLowerCase() + improved.slice(1);
    improvements.push('Added polite prefix');
  }

  // Expand common abbreviations
  const abbreviations: Record<string, string> = {
    'pls': 'please',
    'plz': 'please',
    'thx': 'thanks',
    'ty': 'thank you',
    'ur': 'your',
    'u': 'you',
    'r': 'are',
    'b4': 'before',
    'w/': 'with',
    'w/o': 'without',
    'bc': 'because',
    'rn': 'right now',
    'rly': 'really',
    'rlly': 'really',
    'sry': 'sorry',
    'srry': 'sorry',
    'cuz': 'because',
    'tho': 'though',
    'thru': 'through',
    'msg': 'message',
    'msgs': 'messages',
    'func': 'function',
    'funcs': 'functions',
    'var': 'variable',
    'vars': 'variables',
    'param': 'parameter',
    'params': 'parameters',
    'arg': 'argument',
    'args': 'arguments',
    'btn': 'button',
    'btns': 'buttons',
    'img': 'image',
    'imgs': 'images',
    'db': 'database',
    'dev': 'development',
    'prod': 'production',
    'env': 'environment',
    'repo': 'repository',
    'repos': 'repositories',
    'dir': 'directory',
    'dirs': 'directories',
    'config': 'configuration',
    'configs': 'configurations',
    'deps': 'dependencies',
    'idk': "I don't know",
    'tbh': 'to be honest',
    'imo': 'in my opinion',
    'fyi': 'for your information',
    'asap': 'as soon as possible',
    'afaik': 'as far as I know',
    'atm': 'at the moment',
  };

  for (const [abbr, full] of Object.entries(abbreviations)) {
    const regex = new RegExp(`\\b${abbr}\\b`, 'gi');
    if (regex.test(improved)) {
      improved = improved.replace(regex, full);
      improvements.push(`Expanded "${abbr}" to "${full}"`);
    }
  }

  return { improved, improvements };
}

/**
 * Generate a mock optimized prompt based on the input.
 * Performs rule-based spelling correction, grammar fixes, and clarity improvements.
 */
function generateMockOptimization(original: string): {
  optimized: string;
  changes: Array<{ type: 'CLARIFY'; originalSegment: string; newSegment: string; reason: string }>;
  preservedElements: string[];
  passesUsed: number;
  confidence: number;
  intentSimilarity: number;
  explanation: string;
  tip: string;
  latencyMs: number;
} {
  const changes: Array<{ type: 'CLARIFY'; originalSegment: string; newSegment: string; reason: string }> = [];
  let optimized = original;

  // Step 1: Apply spelling corrections
  const { corrected: afterSpelling, corrections } = applySpellingCorrections(optimized);
  if (corrections.length > 0) {
    for (const c of corrections) {
      changes.push({
        type: 'CLARIFY' as const,
        originalSegment: c.from,
        newSegment: c.to,
        reason: 'Fixed spelling',
      });
    }
    optimized = afterSpelling;
  }

  // Step 2: Apply grammar fixes
  const { corrected: afterGrammar, fixes } = applyGrammarFixes(optimized);
  if (fixes.length > 0) {
    changes.push({
      type: 'CLARIFY' as const,
      originalSegment: optimized,
      newSegment: afterGrammar,
      reason: fixes.join(', '),
    });
    optimized = afterGrammar;
  }

  // Step 3: Add clarity improvements
  const { improved: afterClarity, improvements } = addClarityImprovements(optimized);
  if (improvements.length > 0) {
    changes.push({
      type: 'CLARIFY' as const,
      originalSegment: optimized,
      newSegment: afterClarity,
      reason: improvements.join(', '),
    });
    optimized = afterClarity;
  }

  // Calculate confidence based on changes made
  const confidence = changes.length > 0 ? 0.85 + (0.05 * Math.min(changes.length, 3)) : 0.75;

  // Generate explanation
  const explanationParts: string[] = [];
  if (corrections.length > 0) {
    explanationParts.push(`Fixed ${corrections.length} spelling error${corrections.length > 1 ? 's' : ''}`);
  }
  if (fixes.length > 0) {
    explanationParts.push('Applied grammar corrections');
  }
  if (improvements.length > 0) {
    explanationParts.push('Improved clarity');
  }
  const explanation = explanationParts.length > 0
    ? explanationParts.join(', ')
    : 'No changes needed';

  // Generate tip based on what was corrected
  let tip = 'Your prompt looks good!';
  if (corrections.length > 0) {
    tip = 'Consider using a spell checker or typing more carefully.';
  } else if (improvements.length > 0) {
    tip = 'Using polite language and full words helps Claude understand your intent better.';
  }

  return {
    optimized,
    changes,
    preservedElements: original.split(' ').filter(w => w.length > 3),
    passesUsed: 1,
    confidence,
    intentSimilarity: 0.95,
    explanation,
    tip,
    latencyMs: 10, // Fast since it's rule-based
  };
}

/**
 * Anthropic API client with mock support.
 */
export class AnthropicClient implements OptimizerApiClient {
  private client: Anthropic | null = null;
  private useMock: boolean;
  private timeout: number;
  private retries: number;

  constructor(config: ClientConfig = {}) {
    this.useMock = config.useMock ?? process.env.NODE_ENV === 'test';
    this.timeout = config.timeout ?? 30000;
    this.retries = config.retries ?? RETRY_CONFIG.maxRetries;

    if (!this.useMock) {
      const apiKey = config.apiKey ?? process.env.ANTHROPIC_API_KEY;
      if (!apiKey) {
        throw new OptimizerApiError(
          'ANTHROPIC_API_KEY is required. Set it in environment or pass apiKey in config.',
          undefined,
          'MISSING_API_KEY'
        );
      }
      this.client = new Anthropic({
        apiKey,
        baseURL: config.baseUrl,
        timeout: this.timeout,
      });
    }
  }

  /**
   * Classify a prompt into one of four categories.
   */
  async classify(request: ClassificationRequest): Promise<ClassificationResponse> {
    if (this.useMock) {
      await this.mockDelay(50);
      return { ...MOCK_RESPONSES.classification };
    }

    const startTime = Date.now();
    const response = await this.makeRequest<{
      category: string;
      domain: string | null;
      complexity: string;
      confidence: number;
      reasoning: string;
    }>({
      model: MODEL_CONFIG.classification,
      systemPrompt: CLASSIFICATION_PROMPT,
      userMessage: this.buildClassificationMessage(request),
      maxTokens: 500,
      temperature: 0,
    });

    return {
      category: response.data.category as ClassificationResponse['category'],
      domain: response.data.domain as ClassificationResponse['domain'],
      complexity: response.data.complexity as ClassificationResponse['complexity'],
      confidence: response.data.confidence,
      reasoning: response.data.reasoning,
      cacheHit: false,
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Optimize a prompt based on classification.
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    if (this.useMock) {
      await this.mockDelay(100);
      return generateMockOptimization(request.original);
    }

    const startTime = Date.now();
    const model = this.selectOptimizationModel(request);
    const systemPrompt = this.buildOptimizationPrompt(request);

    const response = await this.makeRequest<{
      optimized_prompt: string;
      changes_made: Array<{ type: string; original: string; new: string; reason: string }>;
      preserved_elements: string[];
      initial_confidence: number;
    }>({
      model,
      systemPrompt,
      userMessage: request.original,
      maxTokens: 2000,
      temperature: 0.3,
    });

    return {
      optimized: response.data.optimized_prompt,
      changes: response.data.changes_made.map((c) => ({
        type: c.type as OptimizationResponse['changes'][0]['type'],
        originalSegment: c.original,
        newSegment: c.new,
        reason: c.reason,
      })),
      preservedElements: response.data.preserved_elements,
      passesUsed: 1,
      confidence: response.data.initial_confidence,
      intentSimilarity: 0.9, // Will be updated by verification
      explanation: 'Optimization complete',
      tip: 'Consider being more specific in future prompts',
      latencyMs: Date.now() - startTime,
    };
  }

  /**
   * Verify intent preservation between original and optimized prompts.
   */
  async verify(request: VerificationRequest): Promise<VerificationResponse> {
    if (this.useMock) {
      await this.mockDelay(50);
      return { ...MOCK_RESPONSES.verification };
    }

    const response = await this.makeRequest<{
      status: string;
      similarity_score: number;
      preserved_ratio: number;
      issues: Array<{ type: string; severity: string; description: string }>;
      recommendation: string;
    }>({
      model: MODEL_CONFIG.intentVerification,
      systemPrompt: VERIFICATION_PROMPT.replace('{original}', request.original)
        .replace('{optimized}', request.optimized)
        .replace('{preserved_elements}', request.preservedElements.join(', ')),
      userMessage: 'Verify the intent preservation.',
      maxTokens: 500,
      temperature: 0,
    });

    return {
      status: response.data.status as VerificationResponse['status'],
      similarityScore: response.data.similarity_score,
      preservedRatio: response.data.preserved_ratio,
      issues: response.data.issues.map((i) => ({
        type: i.type as VerificationResponse['issues'][0]['type'],
        severity: i.severity as VerificationResponse['issues'][0]['severity'],
        description: i.description,
      })),
      recommendation: response.data.recommendation,
    };
  }

  /**
   * Generate embeddings for semantic similarity.
   * Note: Anthropic doesn't have a native embedding API, so we use a simple approach.
   */
  async embed(_text: string): Promise<number[]> {
    // For now, return empty array - we'll compute similarity differently
    // In production, consider using a dedicated embedding service
    return [];
  }

  /**
   * Make an API request with retry logic.
   */
  private async makeRequest<T>(options: RequestOptions): Promise<ParsedResponse<T>> {
    if (!this.client) {
      throw new OptimizerApiError('Client not initialized', undefined, 'CLIENT_NOT_INITIALIZED');
    }

    let lastError: Error | null = null;
    let delay: number = RETRY_CONFIG.initialDelayMs;

    for (let attempt = 0; attempt <= this.retries; attempt++) {
      try {
        const startTime = Date.now();
        const response = await this.client.messages.create({
          model: options.model,
          max_tokens: options.maxTokens ?? 1000,
          system: options.systemPrompt,
          messages: [{ role: 'user', content: options.userMessage }],
          temperature: options.temperature,
        });

        const textContent = response.content.find((c) => c.type === 'text');
        if (!textContent || textContent.type !== 'text') {
          throw new OptimizerApiError('No text content in response', undefined, 'NO_TEXT_CONTENT');
        }

        const parsed = this.parseJsonResponse<T>(textContent.text);

        return {
          data: parsed,
          raw: textContent.text,
          usage: {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
          },
          latencyMs: Date.now() - startTime,
        };
      } catch (error) {
        lastError = error as Error;

        if (this.isRateLimitError(error)) {
          const retryAfter = this.getRetryAfter(error);
          throw new RateLimitError('Rate limited by Anthropic API', retryAfter);
        }

        if (!this.isRetryableError(error) || attempt === this.retries) {
          break;
        }

        await this.sleep(delay);
        delay = Math.min(delay * RETRY_CONFIG.backoffMultiplier, RETRY_CONFIG.maxDelayMs);
      }
    }

    throw new OptimizerApiError(
      `API request failed after ${this.retries + 1} attempts: ${lastError?.message}`,
      undefined,
      'REQUEST_FAILED',
      false
    );
  }

  /**
   * Parse JSON from response text.
   * Handles markdown code blocks and multi-line strings.
   */
  private parseJsonResponse<T>(text: string): T {
    // Extract JSON from markdown code blocks if present
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    let jsonText = jsonMatch ? jsonMatch[1] : text;

    // Try direct parse first
    try {
      return JSON.parse(jsonText.trim()) as T;
    } catch {
      // If that fails, try to fix common issues
    }

    // Try to extract just the JSON object (in case of surrounding text)
    const objectMatch = jsonText.match(/\{[\s\S]*\}/);
    if (objectMatch) {
      jsonText = objectMatch[0];
    }

    // Fix unescaped newlines inside string values
    // This handles cases where the model returns multi-line strings without escaping
    jsonText = jsonText.replace(
      /"([^"]*(?:\\.[^"]*)*)"/g,
      (match) => {
        // Escape unescaped newlines inside string values
        return match.replace(/(?<!\\)\n/g, '\\n');
      }
    );

    try {
      return JSON.parse(jsonText.trim()) as T;
    } catch (e) {
      throw new OptimizerApiError(
        `Failed to parse JSON response: ${text.substring(0, 100)}...`,
        undefined,
        'JSON_PARSE_ERROR'
      );
    }
  }

  /**
   * Build classification message from request.
   */
  private buildClassificationMessage(request: ClassificationRequest): string {
    let message = `Classify this prompt:\n\n${request.input}`;

    if (request.context) {
      message += '\n\n## Context';
      if (request.context.projectLanguage) {
        message += `\nLanguage: ${request.context.projectLanguage}`;
      }
      if (request.context.projectFramework) {
        message += `\nFramework: ${request.context.projectFramework}`;
      }
      if (request.context.expertiseLevel) {
        message += `\nExpertise: ${request.context.expertiseLevel}`;
      }
    }

    return message;
  }

  /**
   * Build optimization prompt with context.
   */
  private buildOptimizationPrompt(request: OptimizationRequest): string {
    let prompt = PASS_ONE_PROMPT;

    prompt = prompt.replace('{domain}', request.classification.domain ?? 'UNKNOWN');
    prompt = prompt.replace('{session_context}', JSON.stringify(request.context.session ?? {}));
    prompt = prompt.replace('{project_context}', JSON.stringify(request.context.project ?? {}));
    prompt = prompt.replace('{user_preferences}', JSON.stringify(request.context.user ?? {}));

    return prompt;
  }

  /**
   * Select optimization model based on complexity.
   */
  private selectOptimizationModel(request: OptimizationRequest): string {
    if (request.classification.complexity === 'COMPLEX') {
      return MODEL_CONFIG.complexOptimization;
    }
    return MODEL_CONFIG.simpleOptimization;
  }

  /**
   * Check if error is rate limit.
   */
  private isRateLimitError(error: unknown): boolean {
    if (error && typeof error === 'object' && 'status' in error) {
      return (error as { status: number }).status === 429;
    }
    return false;
  }

  /**
   * Get retry-after from rate limit error.
   */
  private getRetryAfter(error: unknown): number | undefined {
    if (error && typeof error === 'object' && 'headers' in error) {
      const headers = (error as { headers: Record<string, string> }).headers;
      const retryAfter = headers['retry-after'];
      if (retryAfter) {
        return parseInt(retryAfter, 10) * 1000;
      }
    }
    return undefined;
  }

  /**
   * Check if error is retryable.
   */
  private isRetryableError(error: unknown): boolean {
    if (error && typeof error === 'object' && 'status' in error) {
      const status = (error as { status: number }).status;
      return status >= 500 || status === 429;
    }
    return true; // Retry network errors
  }

  /**
   * Sleep for specified milliseconds.
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Mock delay for testing.
   */
  private mockDelay(ms: number): Promise<void> {
    return this.sleep(ms);
  }
}

/** Create a new Anthropic client */
export function createAnthropicClient(config?: ClientConfig): AnthropicClient {
  return new AnthropicClient(config);
}
