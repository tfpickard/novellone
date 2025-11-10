import type { PageLoad } from './$types';
import { getStories } from '$lib/api';

export const load: PageLoad = async ({ url }) => {
  const params = new URLSearchParams(url.searchParams);
  if (!params.has('page_size')) {
    params.set('page_size', '20');
  }
  if (!params.has('page')) {
    params.set('page', '1');
  }

  const stories = await getStories(params);
  const baseParams = new URLSearchParams(params);
  baseParams.delete('page');

  return {
    stories,
    initialSearch: baseParams.toString()
  };
};


