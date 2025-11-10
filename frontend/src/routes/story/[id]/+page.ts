import type { PageLoad } from './$types';
import { getStory, getConfig, UnauthorizedError } from '$lib/api';

export const load: PageLoad = async ({ params }) => {
  const story = await getStory(params.id);

  let config: Awaited<ReturnType<typeof getConfig>> | null = null;
  try {
    config = await getConfig();
  } catch (error) {
    if (!(error instanceof UnauthorizedError)) {
      throw error;
    }
  }

  return { story, config };
};

