import type { PageLoad } from './$types';
import { getConfig } from '$lib/api';

export const load: PageLoad = async () => {
  const config = await getConfig();
  return { config };
};
