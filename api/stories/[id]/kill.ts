/**
 * Kill Story Endpoint
 * POST /api/stories/[id]/kill
 *
 * End a story early with a specified reason.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { killStory } from '../../lib/story-operations.js';
import type { ApiResponse, Story } from '../../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const storyId = req.query.id as string;

  if (!storyId) {
    res.status(400).json({
      success: false,
      error: 'Story ID is required',
    } as ApiResponse);
    return;
  }

  try {
    // Parse request body
    const { reason } = req.body as { reason?: string };
    const killReason = reason || 'Manually killed by admin';

    // Kill the story
    const story = await killStory(storyId, killReason);

    const response: ApiResponse<Story> = {
      success: true,
      data: story,
      message: 'Story killed successfully',
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error killing story:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
