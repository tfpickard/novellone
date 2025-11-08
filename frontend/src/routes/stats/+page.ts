import type { PageLoad } from './$types';

const base = (import.meta.env.VITE_PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';
const normalized = base.startsWith('http') ? base : `http://${base}`;

export const load: PageLoad = async ({ fetch }) => {
  const statsRes = await fetch(`${normalized}/api/stats`);
  const configRes = await fetch(`${normalized}/api/config`);
  return {
    stats: await statsRes.json(),
    config: await configRes.json()
  };
};
