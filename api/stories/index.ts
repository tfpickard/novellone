/**
 * Stories List Endpoint
 * GET /api/stories
 *
 * Returns paginated list of stories with optional status filter.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getStories } from '../lib/story-operations.js';
import type { ApiResponse, PaginatedResponse, Story } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // Parse query parameters
    const status = req.query.status as string | undefined;
    const limit = Math.min(parseInt(req.query.limit as string) || 50, 100);
    const offset = parseInt(req.query.offset as string) || 0;

    // Validate status if provided
    if (status && !['active', 'completed', 'killed'].includes(status)) {
      res.status(400).json({
        success: false,
        error: 'Invalid status. Must be: active, completed, or killed',
      } as ApiResponse);
      return;
    }

    // Fetch stories
    const stories = await getStories({ status, limit: limit + 1, offset });

    // Check if there are more results
    const hasMore = stories.length > limit;
    const items = hasMore ? stories.slice(0, limit) : stories;

    const response: ApiResponse<PaginatedResponse<Story>> = {
      success: true,
      data: {
        items,
        total: items.length, // Note: actual total would require a separate count query
        page: Math.floor(offset / limit) + 1,
        pageSize: limit,
        hasMore,
      },
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error fetching stories:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
