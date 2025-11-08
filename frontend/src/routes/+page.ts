import type { PageLoad } from './$types';
import { getStories, getConfig } from '$lib/api';

export const load: PageLoad = async ({ url }) => {
  const params = new URLSearchParams(url.searchParams);
  const [stories, config] = await Promise.all([getStories(params), getConfig()]);
  return { stories, config };
};


