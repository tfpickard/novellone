import { env } from '$env/dynamic/private';

import type { LayoutServerLoad } from './$types';

const DEFAULT_API_HOST = 'backend:8000';

function ensureHttp(url: string): string {
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    return `http://${url}`;
  }
  return url;
}

function resolveApiBase(): string {
  const candidate =
    env.VITE_PUBLIC_API_URL ??
    env.PUBLIC_API_URL ??
    env.PUBLIC_API_BASE ??
    env.API_BASE_URL ??
    DEFAULT_API_HOST;
  return ensureHttp(candidate);
}

export const load: LayoutServerLoad = async ({ fetch }) => {
  const apiBase = resolveApiBase();

  try {
    const response = await fetch(`${apiBase}/api/hurllol`, {
      method: 'GET',
      headers: { accept: 'application/json' }
    });

    if (response.ok) {
      const hurllol = await response.json();
      return { hurllol };
    }
  } catch (error) {
    console.error('Failed to fetch HURLLOL banner', error);
  }

  return {
    hurllol: {
      title: null,
      components: [],
      generated_at: null
    }
  };
};

