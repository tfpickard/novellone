/**
 * Authentication & Authorization
 *
 * Simple session-based auth for admin endpoints.
 * Uses bcrypt for password hashing and JWT for session tokens.
 */

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { kv } from '@vercel/kv';
import type { VercelRequest, VercelResponse } from '@vercel/node';

// ───────────────────────────────────────────────────────────────────────────
// Configuration
// ───────────────────────────────────────────────────────────────────────────

const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD_HASH = process.env.ADMIN_PASSWORD_HASH; // Pre-hashed password
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-in-production';
const SESSION_TTL_SECONDS = parseInt(process.env.SESSION_TTL_SECONDS || '604800'); // 7 days

if (!ADMIN_PASSWORD_HASH) {
  console.warn('⚠️  ADMIN_PASSWORD_HASH not set. Admin login will fail.');
  console.warn('    Generate with: node -e "require(\'bcrypt\').hash(\'your-password\', 10).then(console.log)"');
}

// ───────────────────────────────────────────────────────────────────────────
// Types
// ───────────────────────────────────────────────────────────────────────────

export interface SessionData {
  username: string;
  createdAt: number;
  expiresAt: number;
}

export interface AuthenticatedRequest extends VercelRequest {
  session?: SessionData;
}

// ───────────────────────────────────────────────────────────────────────────
// Password Utilities
// ───────────────────────────────────────────────────────────────────────────

/**
 * Hash a password using bcrypt.
 */
export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

/**
 * Verify a password against a hash.
 */
export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// ───────────────────────────────────────────────────────────────────────────
// Session Management
// ───────────────────────────────────────────────────────────────────────────

/**
 * Create a new session for a user.
 * Returns a JWT token to be stored in cookies.
 */
export async function createSession(username: string): Promise<string> {
  const now = Date.now();
  const expiresAt = now + SESSION_TTL_SECONDS * 1000;

  const sessionData: SessionData = {
    username,
    createdAt: now,
    expiresAt,
  };

  // Sign JWT
  const token = jwt.sign(sessionData, SESSION_SECRET, {
    expiresIn: SESSION_TTL_SECONDS,
  });

  // Store in Vercel KV for server-side validation
  const sessionKey = `session:${token}`;
  await kv.set(sessionKey, sessionData, { ex: SESSION_TTL_SECONDS });

  console.log(`[Auth] Session created for ${username}`);

  return token;
}

/**
 * Verify and decode a session token.
 */
export async function verifySession(token: string): Promise<SessionData | null> {
  try {
    // Verify JWT signature
    const decoded = jwt.verify(token, SESSION_SECRET) as SessionData;

    // Check expiration
    if (Date.now() >= decoded.expiresAt) {
      console.log('[Auth] Session expired');
      return null;
    }

    // Verify in KV (protects against token reuse after logout)
    const sessionKey = `session:${token}`;
    const stored = await kv.get<SessionData>(sessionKey);

    if (!stored) {
      console.log('[Auth] Session not found in KV');
      return null;
    }

    return decoded;
  } catch (error) {
    console.error('[Auth] Session verification failed:', error);
    return null;
  }
}

/**
 * Destroy a session.
 */
export async function destroySession(token: string): Promise<void> {
  const sessionKey = `session:${token}`;
  await kv.del(sessionKey);
  console.log('[Auth] Session destroyed');
}

// ───────────────────────────────────────────────────────────────────────────
// Authentication Middleware
// ───────────────────────────────────────────────────────────────────────────

/**
 * Extract session token from request cookies.
 */
function extractToken(req: VercelRequest): string | null {
  const cookieHeader = req.headers.cookie;
  if (!cookieHeader) return null;

  const cookies = cookieHeader.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    acc[key] = value;
    return acc;
  }, {} as Record<string, string>);

  return cookies['session'] || null;
}

/**
 * Middleware: Require authentication.
 * Attaches session data to request if valid.
 * Returns 401 if not authenticated.
 */
export async function requireAuth(
  req: AuthenticatedRequest,
  res: VercelResponse
): Promise<boolean> {
  const token = extractToken(req);

  if (!token) {
    res.status(401).json({
      success: false,
      error: 'Authentication required',
    });
    return false;
  }

  const session = await verifySession(token);

  if (!session) {
    res.status(401).json({
      success: false,
      error: 'Invalid or expired session',
    });
    return false;
  }

  req.session = session;
  return true;
}

/**
 * Middleware: Optional authentication.
 * Attaches session data if available, but doesn't require it.
 */
export async function optionalAuth(req: AuthenticatedRequest): Promise<void> {
  const token = extractToken(req);
  if (!token) return;

  const session = await verifySession(token);
  if (session) {
    req.session = session;
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Login Flow
// ───────────────────────────────────────────────────────────────────────────

/**
 * Authenticate a user with username and password.
 * Returns a session token if successful.
 */
export async function authenticate(
  username: string,
  password: string
): Promise<string | null> {
  // Check username
  if (username !== ADMIN_USERNAME) {
    console.log(`[Auth] Invalid username: ${username}`);
    return null;
  }

  // Check password
  if (!ADMIN_PASSWORD_HASH) {
    console.error('[Auth] ADMIN_PASSWORD_HASH not configured');
    return null;
  }

  const isValid = await verifyPassword(password, ADMIN_PASSWORD_HASH);
  if (!isValid) {
    console.log('[Auth] Invalid password');
    return null;
  }

  // Create session
  const token = await createSession(username);
  return token;
}

// ───────────────────────────────────────────────────────────────────────────
// Utilities
// ───────────────────────────────────────────────────────────────────────────

/**
 * Set session cookie in response.
 */
export function setSessionCookie(res: VercelResponse, token: string): void {
  const isProduction = process.env.NODE_ENV === 'production';
  const maxAge = SESSION_TTL_SECONDS;

  res.setHeader(
    'Set-Cookie',
    `session=${token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${maxAge}${isProduction ? '; Secure' : ''}`
  );
}

/**
 * Clear session cookie.
 */
export function clearSessionCookie(res: VercelResponse): void {
  res.setHeader(
    'Set-Cookie',
    'session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0'
  );
}
