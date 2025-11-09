import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

export function renderMarkdown(text: string | null | undefined): string {
  if (!text) {
    return '';
  }

  const html = marked.parse(text, {
    breaks: true,
    gfm: true
  });

  return DOMPurify.sanitize(html);
}

