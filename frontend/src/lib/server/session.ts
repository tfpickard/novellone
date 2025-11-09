import { createHmac, timingSafeEqual } from 'crypto';

export type SessionUser = {
	username: string;
	roles: string[];
	expiresAt: number;
};

export class SessionError extends Error {}

const DEFAULT_COOKIE_NAME = 'novellone_session';
const DEFAULT_SAMESITE = 'lax';

function getSessionSecret(): string {
	const secret = process.env.SESSION_SECRET;
	if (!secret) {
		throw new Error('SESSION_SECRET environment variable is required for session parsing.');
	}
	return secret;
}

export const SESSION_COOKIE_NAME = process.env.SESSION_COOKIE_NAME ?? DEFAULT_COOKIE_NAME;

const cookieDomain = process.env.SESSION_COOKIE_DOMAIN || undefined;
const cookieSecure = (process.env.SESSION_COOKIE_SECURE ?? 'false').toLowerCase() === 'true';
const cookieSameSiteRaw = (process.env.SESSION_COOKIE_SAMESITE ?? DEFAULT_SAMESITE).toLowerCase();
const cookieSameSite = (['lax', 'strict', 'none'] as const).includes(
	cookieSameSiteRaw as 'lax' | 'strict' | 'none'
)
	? (cookieSameSiteRaw as 'lax' | 'strict' | 'none')
	: DEFAULT_SAMESITE;
const cookieMaxAge = Number.parseInt(process.env.SESSION_TTL_SECONDS ?? '', 10);

export const COOKIE_OPTIONS = {
	path: '/' as const,
	httpOnly: true,
	secure: cookieSecure,
	sameSite: cookieSameSite as 'lax' | 'strict' | 'none',
	domain: cookieDomain,
	maxAge: Number.isFinite(cookieMaxAge) ? cookieMaxAge : undefined
};

function base64UrlDecode(value: string): Buffer {
	return Buffer.from(value, 'base64url');
}

function canonicalPayload(payload: object): Buffer {
	return Buffer.from(JSON.stringify(payload, Object.keys(payload).sort(), 0), 'utf8');
}

export function parseSessionToken(token: string): SessionUser {
	const parts = token.split('.');
	if (parts.length !== 2) {
		throw new SessionError('Malformed session token');
	}

	const [payloadPart, signaturePart] = parts;

	let payloadBuffer: Buffer;
	let signatureBuffer: Buffer;

	try {
		payloadBuffer = base64UrlDecode(payloadPart);
		signatureBuffer = base64UrlDecode(signaturePart);
	} catch (error) {
		throw new SessionError('Unable to decode session token');
	}

	const expectedSignature = createHmac('sha256', getSessionSecret())
		.update(payloadBuffer)
		.digest();

	if (
		expectedSignature.length !== signatureBuffer.length ||
		!timingSafeEqual(expectedSignature, signatureBuffer)
	) {
		throw new SessionError('Invalid session signature');
	}

	let payload: { sub?: unknown; roles?: unknown; exp?: unknown };
	try {
		payload = JSON.parse(payloadBuffer.toString('utf8'));
	} catch (error) {
		throw new SessionError('Invalid session payload');
	}

	if (typeof payload.sub !== 'string' || !payload.sub) {
		throw new SessionError('Invalid session payload');
	}

	if (!Array.isArray(payload.roles) || payload.roles.some((role) => typeof role !== 'string')) {
		throw new SessionError('Invalid session payload');
	}

	const expiresAt = Number(payload.exp);
	if (!Number.isFinite(expiresAt) || expiresAt <= Math.floor(Date.now() / 1000)) {
		throw new SessionError('Session expired');
	}

	return {
		username: payload.sub,
		roles: Array.from(new Set(payload.roles)),
		expiresAt
	};
}

export function createSessionToken(username: string, roles: string[], ttlSeconds: number): string {
	const expiresAt = Math.floor(Date.now() / 1000) + ttlSeconds;
	const payload = {
		exp: expiresAt,
		roles: Array.from(new Set(roles)),
		sub: username
	};
	const payloadBuffer = canonicalPayload(payload);
	const signature = createHmac('sha256', getSessionSecret()).update(payloadBuffer).digest();
	return `${payloadBuffer.toString('base64url')}.${signature.toString('base64url')}`;
}

