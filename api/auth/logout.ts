/**
 * Logout Endpoint
 * POST /api/auth/logout
 *
 * Destroys the user's session.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { destroySession, clearSessionCookie } from '../lib/auth.js';
import type { ApiResponse } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // Extract token from cookie
    const cookieHeader = req.headers.cookie;
    if (cookieHeader) {
      const cookies = cookieHeader.split(';').reduce((acc, cookie) => {
        const [key, value] = cookie.trim().split('=');
        acc[key] = value;
        return acc;
      }, {} as Record<string, string>);

      const token = cookies['session'];
      if (token) {
        await destroySession(token);
      }
    }

    // Clear cookie
    clearSessionCookie(res);

    const response: ApiResponse = {
      success: true,
      message: 'Logged out successfully',
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
