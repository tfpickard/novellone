import type { PageLoad } from './$types';
import { getStats } from '$lib/api';

export const load: PageLoad = async () => {
  const stats = await getStats();
  return { stats };
};

