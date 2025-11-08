import type { PageLoad } from './$types';
import { getStory, getConfig } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
  const [story, config] = await Promise.all([getStory(params.id), getConfig()]);
  return { story, config };
};

