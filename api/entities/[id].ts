/**
 * Entity Details Endpoint
 * GET /api/entities/[id]
 *
 * Get details about a specific entity including all its appearances.
 */

import type { VercelRequest, VercelResponse} from '@vercel/node';
import {
  getEntityWithAppearances,
  getRelatedEntities,
} from '../lib/entity-operations.js';
import type { ApiResponse } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const entityId = req.query.id as string;

  if (!entityId) {
    res.status(400).json({
      success: false,
      error: 'Entity ID is required',
    } as ApiResponse);
    return;
  }

  try {
    const result = await getEntityWithAppearances(entityId);
    const related = await getRelatedEntities(entityId, 10);

    const response: ApiResponse = {
      success: true,
      data: {
        ...result,
        relatedEntities: related,
      },
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error fetching entity:', error);
    res.status(404).json({
      success: false,
      error: error instanceof Error ? error.message : 'Entity not found',
    } as ApiResponse);
  }
}
