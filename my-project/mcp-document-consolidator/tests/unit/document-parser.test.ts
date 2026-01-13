import { describe, it, expect, beforeEach } from 'vitest';
import { DocumentParser } from '../../src/components/document-parser.js';

describe('DocumentParser', () => {
  let parser: DocumentParser;

  beforeEach(() => {
    parser = new DocumentParser();
  });

  describe('parse', () => {
    it('should parse a simple markdown document', async () => {
      const content = `# Hello World

This is the introduction.

## Section One

Content of section one.

## Section Two

Content of section two.`;

      const result = await parser.parse(content, 'test.md');

      expect(result.format).toBe('markdown');
      expect(result.source_path).toBe('test.md');
      expect(result.title).toBe('Hello World');
      expect(result.sections).toHaveLength(3);
      expect(result.raw_content).toBe(content);
    });

    it('should extract frontmatter from markdown', async () => {
      const content = `---
title: My Document
author: Test Author
version: 1.0
---

# Content

Some content here.`;

      const result = await parser.parse(content, 'doc.md');

      expect(result.frontmatter).toEqual({
        title: 'My Document',
        author: 'Test Author',
        version: 1.0
      });
      expect(result.title).toBe('My Document');
    });

    it('should detect JSON format', async () => {
      const content = '{"key": "value"}';
      const result = await parser.parse(content, 'data.json');

      expect(result.format).toBe('json');
    });

    it('should detect YAML format for .yaml extension', async () => {
      const content = 'key: value';
      const result = await parser.parse(content, 'config.yaml');

      expect(result.format).toBe('yaml');
    });

    it('should detect YAML format for .yml extension', async () => {
      const content = 'key: value';
      const result = await parser.parse(content, 'config.yml');

      expect(result.format).toBe('yaml');
    });

    it('should default to text format for unknown extensions', async () => {
      const content = 'plain text content';
      const result = await parser.parse(content, 'file.txt');

      expect(result.format).toBe('text');
    });

    it('should generate a unique id for each document', async () => {
      const content = '# Test';
      const result1 = await parser.parse(content, 'test1.md');
      const result2 = await parser.parse(content, 'test2.md');

      expect(result1.id).toBeTruthy();
      expect(result2.id).toBeTruthy();
      expect(result1.id).not.toBe(result2.id);
    });

    it('should generate content hash', async () => {
      const content = '# Test Content';
      const result = await parser.parse(content, 'test.md');

      expect(result.content_hash).toBeTruthy();
      expect(result.content_hash).toHaveLength(64); // SHA-256 hex
    });

    it('should generate same hash for same content', async () => {
      const content = '# Same Content';
      const result1 = await parser.parse(content, 'test1.md');
      const result2 = await parser.parse(content, 'test2.md');

      expect(result1.content_hash).toBe(result2.content_hash);
    });

    it('should include created_at timestamp', async () => {
      const content = '# Test';
      const result = await parser.parse(content, 'test.md');

      expect(result.created_at).toBeTruthy();
      expect(new Date(result.created_at)).toBeInstanceOf(Date);
    });
  });

  describe('section extraction', () => {
    it('should extract multiple header levels', async () => {
      const content = `# Level 1

Content 1

## Level 2

Content 2

### Level 3

Content 3`;

      const result = await parser.parse(content, 'test.md');

      expect(result.sections).toHaveLength(3);
      expect(result.sections[0].level).toBe(1);
      expect(result.sections[0].header).toBe('Level 1');
      expect(result.sections[1].level).toBe(2);
      expect(result.sections[1].header).toBe('Level 2');
      expect(result.sections[2].level).toBe(3);
      expect(result.sections[2].header).toBe('Level 3');
    });

    it('should extract section content correctly', async () => {
      const content = `# Header

Line 1
Line 2
Line 3`;

      const result = await parser.parse(content, 'test.md');

      expect(result.sections[0].content).toBe('Line 1\nLine 2\nLine 3');
    });

    it('should handle content before first header', async () => {
      const content = `Introduction text before any header.

# First Section

Section content.`;

      const result = await parser.parse(content, 'test.md');

      expect(result.sections).toHaveLength(2);
      expect(result.sections[0].header).toBe('Introduction');
      expect(result.sections[0].content).toContain('Introduction text');
    });

    it('should handle document with no headers', async () => {
      const content = 'Just some plain text\nwith multiple lines\nbut no headers.';
      const result = await parser.parse(content, 'test.md');

      expect(result.sections).toHaveLength(1);
      expect(result.sections[0].header).toBe('Introduction');
    });

    it('should track line numbers for sections', async () => {
      const content = `# Section One

Content here.

# Section Two

More content.`;

      const result = await parser.parse(content, 'test.md');

      expect(result.sections[0].start_line).toBe(1);
      expect(result.sections[0].end_line).toBe(4); // 0-indexed position of "# Section Two"
      expect(result.sections[1].start_line).toBe(5);
    });

    it('should generate unique ids for each section', async () => {
      const content = `# Section One

Content.

# Section Two

Content.`;

      const result = await parser.parse(content, 'test.md');

      expect(result.sections[0].id).toBeTruthy();
      expect(result.sections[1].id).toBeTruthy();
      expect(result.sections[0].id).not.toBe(result.sections[1].id);
    });

    it('should create single section for non-markdown formats', async () => {
      const content = '{"data": "test"}';
      const result = await parser.parse(content, 'data.json');

      expect(result.sections).toHaveLength(1);
      expect(result.sections[0].header).toBe('Content');
      expect(result.sections[0].content).toBe(content);
    });
  });

  describe('extractCodeBlocks', () => {
    it('should extract code blocks with language', () => {
      const content = `Some text

\`\`\`typescript
const x = 1;
const y = 2;
\`\`\`

More text`;

      const codeBlocks = parser.extractCodeBlocks(content);

      expect(codeBlocks).toHaveLength(1);
      expect(codeBlocks[0].language).toBe('typescript');
      expect(codeBlocks[0].code).toBe('const x = 1;\nconst y = 2;');
    });

    it('should extract multiple code blocks', () => {
      const content = `\`\`\`javascript
function foo() {}
\`\`\`

\`\`\`python
def bar():
    pass
\`\`\``;

      const codeBlocks = parser.extractCodeBlocks(content);

      expect(codeBlocks).toHaveLength(2);
      expect(codeBlocks[0].language).toBe('javascript');
      expect(codeBlocks[1].language).toBe('python');
    });

    it('should handle code blocks without language', () => {
      const content = `\`\`\`
plain code
\`\`\``;

      const codeBlocks = parser.extractCodeBlocks(content);

      expect(codeBlocks).toHaveLength(1);
      expect(codeBlocks[0].language).toBe('text');
    });

    it('should track start line of code blocks', () => {
      const content = `Line 1
Line 2
\`\`\`js
code
\`\`\``;

      const codeBlocks = parser.extractCodeBlocks(content);

      expect(codeBlocks[0].startLine).toBe(3);
    });

    it('should return empty array if no code blocks', () => {
      const content = 'Just plain text without code blocks.';
      const codeBlocks = parser.extractCodeBlocks(content);

      expect(codeBlocks).toHaveLength(0);
    });
  });

  describe('extractLinks', () => {
    it('should extract markdown links', () => {
      const content = 'Check out [Google](https://google.com) and [GitHub](https://github.com).';
      const links = parser.extractLinks(content);

      expect(links).toHaveLength(2);
      expect(links[0]).toEqual({ text: 'Google', url: 'https://google.com' });
      expect(links[1]).toEqual({ text: 'GitHub', url: 'https://github.com' });
    });

    it('should extract relative links', () => {
      const content = 'See [docs](./docs/readme.md) for more info.';
      const links = parser.extractLinks(content);

      expect(links).toHaveLength(1);
      expect(links[0]).toEqual({ text: 'docs', url: './docs/readme.md' });
    });

    it('should return empty array if no links', () => {
      const content = 'No links here.';
      const links = parser.extractLinks(content);

      expect(links).toHaveLength(0);
    });

    it('should handle links with special characters in text', () => {
      const content = 'See [API v2.0](https://api.example.com).';
      const links = parser.extractLinks(content);

      expect(links[0].text).toBe('API v2.0');
    });
  });

  describe('extractTables', () => {
    it('should extract simple markdown table', () => {
      const content = `| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |`;

      const tables = parser.extractTables(content);

      expect(tables).toHaveLength(1);
      expect(tables[0].headers).toEqual(['Header 1', 'Header 2']);
      expect(tables[0].rows).toEqual([
        ['Cell 1', 'Cell 2'],
        ['Cell 3', 'Cell 4']
      ]);
    });

    it('should handle table with alignment markers', () => {
      const content = `| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |`;

      const tables = parser.extractTables(content);

      expect(tables).toHaveLength(1);
      expect(tables[0].headers).toEqual(['Left', 'Center', 'Right']);
    });

    it('should extract multiple tables', () => {
      const content = `| A | B |
|---|---|
| 1 | 2 |

Some text between tables.

| X | Y |
|---|---|
| 3 | 4 |`;

      const tables = parser.extractTables(content);

      expect(tables).toHaveLength(2);
    });

    it('should return empty array if no tables', () => {
      const content = 'No tables in this content.';
      const tables = parser.extractTables(content);

      expect(tables).toHaveLength(0);
    });

    it('should handle table at end of content', () => {
      const content = `Some intro text.

| Col |
|-----|
| Val |`;

      const tables = parser.extractTables(content);

      expect(tables).toHaveLength(1);
    });
  });
});
