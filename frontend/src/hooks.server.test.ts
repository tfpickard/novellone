import { describe, expect, it, vi } from 'vitest';

import { handle } from './hooks.server';
import { SESSION_COOKIE_NAME, createSessionToken } from '$lib/server/session';

type CookieStore = Map<string, string>;

function createCookieJar(store: CookieStore) {
	return {
		get: (name: string) => store.get(name),
		set: (name: string, value: string) => {
			store.set(name, value);
		},
		delete: (name: string) => {
			store.delete(name);
		}
	};
}

function createEvent(path: string, store: CookieStore) {
	const url = new URL(`https://example.com${path}`);
	return {
		url,
		request: new Request(url),
		locals: { user: null },
		cookies: createCookieJar(store),
		isDataRequest: false,
		route: { id: null },
		setHeaders: () => {},
		params: {},
		getClientAddress: () => '127.0.0.1',
		fetch: fetch
	} as unknown as Parameters<typeof handle>[0]['event'];
}

describe('handle hook', () => {
	it('redirects unauthenticated users away from /config', async () => {
		const cookies: CookieStore = new Map();
		const event = createEvent('/config', cookies);
		const resolve = vi.fn();

		await expect(handle({ event, resolve })).rejects.toMatchObject({
			status: 302,
			location: '/login?redirect=%2Fconfig'
		});
		expect(resolve).not.toHaveBeenCalled();
	});

	it('allows authenticated users to continue', async () => {
		const cookies: CookieStore = new Map();
		const token = createSessionToken('admin', ['admin'], 3600);
		cookies.set(SESSION_COOKIE_NAME, token);

		const event = createEvent('/config', cookies);
		const resolve = vi.fn().mockResolvedValue(new Response('ok'));

		const response = await handle({ event, resolve });

		expect(response).toBeInstanceOf(Response);
		expect(resolve).toHaveBeenCalledOnce();
		expect(event.locals.user?.username).toBe('admin');
	});

	it('redirects authenticated users away from /login', async () => {
		const cookies: CookieStore = new Map();
		const token = createSessionToken('admin', ['admin'], 3600);
		cookies.set(SESSION_COOKIE_NAME, token);

		const event = createEvent('/login', cookies);
		const resolve = vi.fn();

		await expect(handle({ event, resolve })).rejects.toMatchObject({
			status: 302,
			location: '/config'
		});
	});

	it('drops invalid session cookies', async () => {
		const cookies: CookieStore = new Map();
		cookies.set(SESSION_COOKIE_NAME, 'invalid.token');

		const event = createEvent('/config', cookies);
		const resolve = vi.fn();

		await expect(handle({ event, resolve })).rejects.toMatchObject({
			status: 302
		});
		expect(cookies.has(SESSION_COOKIE_NAME)).toBe(false);
	});
});

