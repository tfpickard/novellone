/**
 * Current User Endpoint
 * GET /api/auth/me
 *
 * Returns the currently authenticated user's information.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { optionalAuth, type AuthenticatedRequest } from '../lib/auth.js';
import type { ApiResponse } from '../lib/types.js';

export default async function handler(
  req: AuthenticatedRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    await optionalAuth(req);

    if (!req.session) {
      res.status(401).json({
        success: false,
        error: 'Not authenticated',
      } as ApiResponse);
      return;
    }

    const response: ApiResponse<{
      username: string;
      expiresAt: number;
    }> = {
      success: true,
      data: {
        username: req.session.username,
        expiresAt: req.session.expiresAt,
      },
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Auth check error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
