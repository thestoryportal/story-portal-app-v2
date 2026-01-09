/**
 * Test fixtures for prompt classification and optimization.
 */

/** Well-formed prompts that should PASS_THROUGH */
export const PASS_THROUGH_PROMPTS = [
  {
    input: 'How do I implement a binary search algorithm in TypeScript?',
    expectedCategory: 'PASS_THROUGH',
    expectedDomain: 'CODE',
  },
  {
    input: 'Write a function that validates email addresses using regex in Python',
    expectedCategory: 'PASS_THROUGH',
    expectedDomain: 'CODE',
  },
  {
    input: 'Explain the difference between REST and GraphQL APIs, including pros and cons of each approach',
    expectedCategory: 'PASS_THROUGH',
    expectedDomain: 'RESEARCH',
  },
  {
    input: 'Create a React component called UserProfile that displays a user\'s name, email, and avatar image',
    expectedCategory: 'PASS_THROUGH',
    expectedDomain: 'CODE',
  },
];

/** Debug prompts that should route to DEBUG */
export const DEBUG_PROMPTS = [
  {
    input: `I'm getting this error when running my app:
\`\`\`
TypeError: Cannot read property 'map' of undefined
    at UserList.render (UserList.js:15)
\`\`\`
What's wrong?`,
    expectedCategory: 'DEBUG',
    expectedDomain: 'CODE',
  },
  {
    input: 'My build is failing with "Module not found: Can\'t resolve \'lodash\'". How do I fix this?',
    expectedCategory: 'DEBUG',
    expectedDomain: 'CODE',
  },
  {
    input: `The API returns 500 error:
\`\`\`json
{"error": "Internal Server Error", "stack": "Error: Database connection failed\\n    at connect..."}
\`\`\`
Please help debug`,
    expectedCategory: 'DEBUG',
    expectedDomain: 'CODE',
  },
];

/** Vague prompts that should be OPTIMIZED */
export const OPTIMIZE_PROMPTS = [
  {
    input: 'help with my code',
    expectedCategory: 'OPTIMIZE',
    expectedDomain: 'CODE',
  },
  {
    input: 'make it better',
    expectedCategory: 'OPTIMIZE',
    expectedDomain: null,
  },
  {
    input: 'the thing is broken idk',
    expectedCategory: 'OPTIMIZE',
    expectedDomain: null,
  },
  {
    input: 'fix the function',
    expectedCategory: 'OPTIMIZE',
    expectedDomain: 'CODE',
  },
  {
    input: 'i need a website but not sure what kind',
    expectedCategory: 'OPTIMIZE',
    expectedDomain: 'CODE',
  },
];

/** Ambiguous prompts that should CLARIFY */
export const CLARIFY_PROMPTS = [
  {
    input: 'hi',
    expectedCategory: 'CLARIFY',
    expectedDomain: null,
  },
  {
    input: 'that',
    expectedCategory: 'CLARIFY',
    expectedDomain: null,
  },
  {
    input: 'rm -rf /',
    expectedCategory: 'CLARIFY',
    expectedDomain: null,
  },
  {
    input: 'delete all the data',
    expectedCategory: 'CLARIFY',
    expectedDomain: null,
  },
];

/** Domain-specific prompts for domain detection testing */
export const DOMAIN_PROMPTS = {
  CODE: [
    'Write a function in JavaScript',
    'Debug this TypeScript error',
    'Refactor the React component',
    'Fix the API endpoint',
  ],
  WRITING: [
    'Write a professional email to my boss',
    'Create a blog post about AI',
    'Draft a formal letter',
    'Write an essay on climate change',
  ],
  ANALYSIS: [
    'Compare the performance of these two algorithms',
    'Analyze the sales data from Q3',
    'Create a comparison table of React vs Vue',
    'What are the metrics showing?',
  ],
  CREATIVE: [
    'Write a short story about a robot',
    'Brainstorm ideas for a logo',
    'Design a creative concept for an app',
    'Imagine a world where cars fly',
  ],
  RESEARCH: [
    'Explain how neural networks work',
    'What is the difference between SQL and NoSQL?',
    'Teach me about machine learning',
    'How does blockchain technology work?',
  ],
};

/** Prompts with elements that must be preserved */
export const PRESERVATION_PROMPTS = [
  {
    input: 'Update the file at `/src/components/Button.tsx` to add a loading state',
    mustPreserve: ['/src/components/Button.tsx', 'loading state'],
  },
  {
    input: 'Don\'t use any external libraries, just vanilla JavaScript',
    mustPreserve: ["Don't use any external libraries"],
  },
  {
    input: 'The version is `v2.3.1` and the API endpoint is https://api.example.com/v1',
    mustPreserve: ['v2.3.1', 'https://api.example.com/v1'],
  },
  {
    input: 'Never modify the `config.json` file directly',
    mustPreserve: ['Never modify', 'config.json'],
  },
];

/** Optimization examples with expected improvements */
export const OPTIMIZATION_EXAMPLES = [
  {
    input: 'help with react thing not working',
    expectedImprovements: ['language', 'framework', 'specific issue'],
  },
  {
    input: 'write me a story about a robot',
    expectedImprovements: ['length hint', 'creative freedom preserved'],
  },
  {
    input: 'compare those two things',
    expectedImprovements: ['specific comparison', 'criteria', 'format'],
  },
];
