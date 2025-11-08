import type { PageLoad } from './$types';
import { getStats, getConfig } from '$lib/api';

export const load: PageLoad = async () => {
  const [stats, config] = await Promise.all([getStats(), getConfig()]);
  return { stats, config };
};

