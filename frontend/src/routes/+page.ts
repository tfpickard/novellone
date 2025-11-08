import type { PageLoad } from './$types';

const base = (import.meta.env.VITE_PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';
const normalized = base.startsWith('http') ? base : `http://${base}`;

export const load: PageLoad = async ({ url, fetch }) => {
  const params = new URLSearchParams(url.searchParams);
  const response = await fetch(`${normalized}/api/stories?${params.toString()}`);
  const stories = await response.json();

  const configRes = await fetch(`${normalized}/api/config`);
  const config = await configRes.json();

  return {
    stories,
    config
  };
};
