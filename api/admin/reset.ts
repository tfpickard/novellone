/**
 * Reset System Endpoint
 * POST /api/admin/reset
 *
 * Delete all stories and reset the system (dangerous operation).
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { executeWrite } from '../lib/neo4j.js';
import { resetConfig } from '../lib/config.js';
import { requireAuth, type AuthenticatedRequest } from '../lib/auth.js';
import type { ApiResponse } from '../lib/types.js';

export default async function handler(
  req: AuthenticatedRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  // Require authentication (this is a dangerous operation!)
  const isAuthenticated = await requireAuth(req, res);
  if (!isAuthenticated) return;

  try {

    // Parse confirmation from request body
    const { confirm } = req.body as { confirm?: string };

    if (confirm !== 'DELETE_ALL_STORIES') {
      res.status(400).json({
        success: false,
        error: 'Confirmation required. Send { "confirm": "DELETE_ALL_STORIES" }',
      } as ApiResponse);
      return;
    }

    console.log('⚠️  Resetting system: deleting all stories...');

    // Delete all stories, chapters, evaluations, entities, etc.
    // Keep Tom canonical node
    const query = `
      MATCH (n)
      WHERE NOT n:Tom
      DETACH DELETE n
    `;

    await executeWrite(query);

    // Reset configuration to defaults
    await resetConfig();

    console.log('✓ System reset complete');

    const response: ApiResponse = {
      success: true,
      message: 'System reset successfully. All stories deleted.',
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error resetting system:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
