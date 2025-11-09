import type { PageLoad } from './$types';
import { getStories } from '$lib/api';

export const load: PageLoad = async ({ url }) => {
  const params = new URLSearchParams(url.searchParams);
  const stories = await getStories(params);
  return { stories };
};


