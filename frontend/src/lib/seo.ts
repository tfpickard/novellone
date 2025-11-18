export const SITE_NAME = 'Hurl Unmasks Recursive Literature Leaking Out Love';
export const SITE_URL = 'https://hurl.lol';
export const SITE_DESCRIPTION =
  'Autonomous science-fiction tales evolving in real time with AI chapters, cover art, and live stats.';
export const META_KEYWORDS =
  'autonomous storytelling, science fiction anthology, ai writing experiment, live novel, dall-e covers, tom the engineer';
export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-card.svg`;

export function buildCanonicalUrl(path?: string | URL | null): string {
  if (!path) {
    return SITE_URL;
  }
  const pathname = typeof path === 'string' ? path : path.pathname;
  if (!pathname || pathname === '/' || pathname === '//') {
    return SITE_URL;
  }
  return `${SITE_URL}${pathname.startsWith('/') ? pathname : `/${pathname}`}`;
}
