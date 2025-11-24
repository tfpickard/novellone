/**
 * Login Endpoint
 * POST /api/auth/login
 *
 * Authenticates a user and returns a session cookie.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { authenticate, setSessionCookie } from '../lib/auth.js';
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
    const { username, password } = req.body as {
      username?: string;
      password?: string;
    };

    if (!username || !password) {
      res.status(400).json({
        success: false,
        error: 'Username and password required',
      } as ApiResponse);
      return;
    }

    const token = await authenticate(username, password);

    if (!token) {
      res.status(401).json({
        success: false,
        error: 'Invalid credentials',
      } as ApiResponse);
      return;
    }

    // Set session cookie
    setSessionCookie(res, token);

    const response: ApiResponse<{ username: string }> = {
      success: true,
      data: { username },
      message: 'Logged in successfully',
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
