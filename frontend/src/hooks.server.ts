import { redirect, type Handle } from '@sveltejs/kit';

import {
	COOKIE_OPTIONS,
	SESSION_COOKIE_NAME,
	SessionError,
	parseSessionToken,
	type SessionUser
} from '$lib/server/session';

const REDIRECT_PARAM = 'redirect';

function buildRedirectTarget(url: URL): string {
	const target = url.pathname + url.search;
	return `/login?${REDIRECT_PARAM}=${encodeURIComponent(target)}`;
}

function isValidRedirect(redirect: string): boolean {
	// Only allow relative paths that start with /
	// Reject protocol-relative URLs (//evil.com), absolute URLs, and anything with special schemes
	if (!redirect.startsWith('/')) {
		return false;
	}
	
	// Reject protocol-relative URLs
	if (redirect.startsWith('//')) {
		return false;
	}
	
	// Reject URLs with backslashes (could be used to bypass checks)
	if (redirect.includes('\\')) {
		return false;
	}
	
	try {
		// Try parsing as URL - if it has a protocol/host, it's not a relative path
		const url = new URL(redirect, 'http://dummy.local');
		// If the host changed from our dummy, it means it had an absolute URL
		if (url.host !== 'dummy.local') {
			return false;
		}
	} catch {
		// If URL parsing fails, that's fine - it's likely a simple relative path
	}
	
	return true;
}

function sanitizeUser(session: SessionUser | null): SessionUser | null {
	if (!session) {
		return null;
	}

	return {
		username: session.username,
		roles: [...session.roles],
		expiresAt: session.expiresAt
	};
}

export const handle: Handle = async ({ event, resolve }) => {
	const token = event.cookies.get(SESSION_COOKIE_NAME);
	let session: SessionUser | null = null;

	if (token) {
		try {
			session = parseSessionToken(token);
		} catch (error) {
			if (error instanceof SessionError) {
				event.cookies.delete(SESSION_COOKIE_NAME, COOKIE_OPTIONS);
			} else {
				console.error('Unexpected session parse failure', error);
			}
		}
	}

	event.locals.user = sanitizeUser(session);

	const isConfigRoute = event.url.pathname.startsWith('/config');
	if (isConfigRoute && !event.locals.user) {
		throw redirect(302, buildRedirectTarget(event.url));
	}

	if (event.url.pathname === '/login' && event.locals.user) {
		const redirectParam = event.url.searchParams.get(REDIRECT_PARAM) ?? '/config';
		const safeRedirect = isValidRedirect(redirectParam) ? redirectParam : '/config';
		throw redirect(302, safeRedirect);
	}

	return resolve(event);
};

