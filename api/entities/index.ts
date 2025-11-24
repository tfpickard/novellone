/**
 * Entities List Endpoint
 * GET /api/entities
 *
 * Returns paginated list of entities across all stories.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getTopEntities, getEntityStats } from '../lib/entity-operations.js';
import type { ApiResponse, Entity } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 50, 100);
    const includeStats = req.query.stats === 'true';

    const entities = await getTopEntities(limit);

    let stats;
    if (includeStats) {
      stats = await getEntityStats();
    }

    const response: ApiResponse<{
      entities: Entity[];
      stats?: any;
    }> = {
      success: true,
      data: {
        entities,
        ...(stats && { stats }),
      },
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error fetching entities:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
