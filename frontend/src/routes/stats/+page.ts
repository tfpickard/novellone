import type { PageLoad } from './$types';
import {
  getStats,
  getConfig,
  getUniverseOverview,
  getUniverseMetrics,
  UnauthorizedError
} from '$lib/api';

export const load: PageLoad = async () => {
  const stats = await getStats();
  const universe = await getUniverseOverview();

  let config: Awaited<ReturnType<typeof getConfig>> | null = null;
  let meta: Awaited<ReturnType<typeof getUniverseMetrics>> | null = null;

  try {
    config = await getConfig();
  } catch (error) {
    if (!(error instanceof UnauthorizedError)) {
      throw error;
    }
  }

  try {
    meta = await getUniverseMetrics();
  } catch (error) {
    if (!(error instanceof UnauthorizedError)) {
      throw error;
    }
  }

  return { stats, config, universe, meta };
};

