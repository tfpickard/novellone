/**
 * Story Details Endpoint
 * GET /api/stories/[id]
 * DELETE /api/stories/[id]
 *
 * Get or delete a single story with full details.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import {
  getStoryWithDetails,
  deleteStory,
} from '../lib/story-operations.js';
import type { ApiResponse, StoryWithDetails } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  const storyId = req.query.id as string;

  if (!storyId) {
    res.status(400).json({
      success: false,
      error: 'Story ID is required',
    } as ApiResponse);
    return;
  }

  try {
    switch (req.method) {
      case 'GET':
        await handleGet(storyId, res);
        break;

      case 'DELETE':
        await handleDelete(storyId, res);
        break;

      default:
        res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (error) {
    console.error('Error handling story request:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}

async function handleGet(
  storyId: string,
  res: VercelResponse
): Promise<void> {
  const story = await getStoryWithDetails(storyId);

  if (!story) {
    res.status(404).json({
      success: false,
      error: 'Story not found',
    } as ApiResponse);
    return;
  }

  const response: ApiResponse<StoryWithDetails> = {
    success: true,
    data: story,
  };

  res.status(200).json(response);
}

async function handleDelete(
  storyId: string,
  res: VercelResponse
): Promise<void> {
  // TODO: Add authentication check here
  // For now, allow deletion (add auth later)

  await deleteStory(storyId);

  const response: ApiResponse = {
    success: true,
    message: 'Story deleted successfully',
  };

  res.status(200).json(response);
}
