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
		throw redirect(302, redirectParam);
	}

	return resolve(event);
};

