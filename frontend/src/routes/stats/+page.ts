import type { PageLoad } from './$types';
import { getStats, getConfig, getUniverseOverview } from '$lib/api';

export const load: PageLoad = async () => {
  const [stats, config, universe] = await Promise.all([
    getStats(),
    getConfig(),
    getUniverseOverview()
  ]);
  return { stats, config, universe };
};

