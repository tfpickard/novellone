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

