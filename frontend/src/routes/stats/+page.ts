import type { PageLoad } from './$types';
import { getStats, getConfig, getUniverseOverview, getUniverseMetrics } from '$lib/api';

export const load: PageLoad = async () => {
  const [stats, config, universe, meta] = await Promise.all([
    getStats(),
    getConfig(),
    getUniverseOverview(),
    getUniverseMetrics()
  ]);
  return { stats, config, universe, meta };
};

