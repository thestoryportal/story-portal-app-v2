import matter from 'gray-matter';
import { v4 as uuidv4 } from 'uuid';
import type { ParsedDocument, Section, DocumentFormat } from '../types.js';

export class DocumentParser {
  async parse(content: string, path: string): Promise<ParsedDocument> {
    const format = this.detectFormat(path);
    const { data: frontmatter, content: body } = matter(content);

    const sections = await this.extractSections(body, format);
    const title = (frontmatter.title as string) || sections[0]?.header || path;

    return {
      id: uuidv4(),
      source_path: path,
      content_hash: await this.hash(content),
      format,
      frontmatter,
      title,
      sections,
      raw_content: content,
      created_at: new Date().toISOString()
    };
  }

  private detectFormat(path: string): DocumentFormat {
    const lowerPath = path.toLowerCase();
    if (lowerPath.endsWith('.md') || lowerPath.endsWith('.markdown')) {
      return 'markdown';
    }
    if (lowerPath.endsWith('.json')) {
      return 'json';
    }
    if (lowerPath.endsWith('.yaml') || lowerPath.endsWith('.yml')) {
      return 'yaml';
    }
    return 'text';
  }

  private async extractSections(content: string, format: DocumentFormat): Promise<Section[]> {
    if (format !== 'markdown') {
      return [{
        id: uuidv4(),
        header: 'Content',
        level: 1,
        content,
        start_line: 1,
        end_line: content.split('\n').length
      }];
    }

    const sections: Section[] = [];
    const lines = content.split('\n');
    let currentSection: Partial<Section> | null = null;
    let sectionContent: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);

      if (headerMatch) {
        // Save previous section
        if (currentSection) {
          currentSection.content = sectionContent.join('\n').trim();
          currentSection.end_line = i;
          sections.push(currentSection as Section);
        }

        // Start new section
        currentSection = {
          id: uuidv4(),
          header: headerMatch[2],
          level: headerMatch[1].length,
          start_line: i + 1
        };
        sectionContent = [];
      } else if (currentSection) {
        sectionContent.push(line);
      } else {
        // Content before first header - create implicit section
        if (line.trim()) {
          currentSection = {
            id: uuidv4(),
            header: 'Introduction',
            level: 1,
            start_line: 1
          };
          sectionContent = [line];
        }
      }
    }

    // Save final section
    if (currentSection) {
      currentSection.content = sectionContent.join('\n').trim();
      currentSection.end_line = lines.length;
      sections.push(currentSection as Section);
    }

    // If no sections found, create one with all content
    if (sections.length === 0) {
      sections.push({
        id: uuidv4(),
        header: 'Content',
        level: 1,
        content: content.trim(),
        start_line: 1,
        end_line: lines.length
      });
    }

    return sections;
  }

  private async hash(content: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Extract code blocks from markdown content
   */
  extractCodeBlocks(content: string): Array<{ language: string; code: string; startLine: number }> {
    const codeBlocks: Array<{ language: string; code: string; startLine: number }> = [];
    const lines = content.split('\n');
    let inCodeBlock = false;
    let currentLanguage = '';
    let currentCode: string[] = [];
    let startLine = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const codeBlockMatch = line.match(/^```(\w*)$/);

      if (codeBlockMatch) {
        if (inCodeBlock) {
          // End of code block
          codeBlocks.push({
            language: currentLanguage,
            code: currentCode.join('\n'),
            startLine
          });
          inCodeBlock = false;
          currentCode = [];
        } else {
          // Start of code block
          inCodeBlock = true;
          currentLanguage = codeBlockMatch[1] || 'text';
          startLine = i + 1;
        }
      } else if (inCodeBlock) {
        currentCode.push(line);
      }
    }

    return codeBlocks;
  }

  /**
   * Extract links from markdown content
   */
  extractLinks(content: string): Array<{ text: string; url: string }> {
    const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
    const links: Array<{ text: string; url: string }> = [];
    let match;

    while ((match = linkPattern.exec(content)) !== null) {
      links.push({
        text: match[1],
        url: match[2]
      });
    }

    return links;
  }

  /**
   * Extract tables from markdown content
   */
  extractTables(content: string): Array<{ headers: string[]; rows: string[][] }> {
    const tables: Array<{ headers: string[]; rows: string[][] }> = [];
    const lines = content.split('\n');
    let inTable = false;
    let currentHeaders: string[] = [];
    let currentRows: string[][] = [];

    for (const line of lines) {
      const trimmedLine = line.trim();

      // Check if line is a table row
      if (trimmedLine.startsWith('|') && trimmedLine.endsWith('|')) {
        const cells = trimmedLine
          .slice(1, -1)
          .split('|')
          .map(cell => cell.trim());

        // Skip separator rows
        if (cells.every(cell => /^[-:]+$/.test(cell))) {
          continue;
        }

        if (!inTable) {
          // First row is headers
          inTable = true;
          currentHeaders = cells;
        } else {
          currentRows.push(cells);
        }
      } else if (inTable) {
        // End of table
        if (currentHeaders.length > 0) {
          tables.push({
            headers: currentHeaders,
            rows: currentRows
          });
        }
        inTable = false;
        currentHeaders = [];
        currentRows = [];
      }
    }

    // Handle table at end of content
    if (inTable && currentHeaders.length > 0) {
      tables.push({
        headers: currentHeaders,
        rows: currentRows
      });
    }

    return tables;
  }
}
