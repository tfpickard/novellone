import type { PageLoad } from './$types';

const base = (import.meta.env.VITE_PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';
const normalized = base.startsWith('http') ? base : `http://${base}`;

export const load: PageLoad = async ({ fetch, params }) => {
  const storyRes = await fetch(`${normalized}/api/stories/${params.id}`);
  if (!storyRes.ok) {
    throw new Error('Story not found');
  }
  const story = await storyRes.json();
  const configRes = await fetch(`${normalized}/api/config`);
  const config = await configRes.json();
  return { story, config };
};
