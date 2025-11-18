import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

export function renderMarkdown(text: string | null | undefined): string {
  if (!text) {
    return '';
  }

  const html = marked(text, {
    breaks: true,
    gfm: true
  });

  return DOMPurify.sanitize(html);
}

export function stripMarkdown(text: string | null | undefined): string {
  if (!text) return '';
  return (
    text
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_~>#-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  );
}

