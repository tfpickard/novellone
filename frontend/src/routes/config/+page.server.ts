import { env } from '$env/dynamic/private';
import { error, redirect } from '@sveltejs/kit';

import { COOKIE_OPTIONS, SESSION_COOKIE_NAME } from '$lib/server/session';

import type { PageServerLoad } from './$types';

const LOGIN_ROUTE = '/login';
const DEFAULT_API_HOST = 'backend:8000';

function ensureHttp(url: string): string {
	if (!url.startsWith('http://') && !url.startsWith('https://')) {
		return `http://${url}`;
	}
	return url;
}

function resolveApiBase(): string {
	const candidate =
		env.VITE_PUBLIC_API_URL ??
		env.PUBLIC_API_URL ??
		env.PUBLIC_API_BASE ??
		env.API_BASE_URL ??
		DEFAULT_API_HOST;
	return ensureHttp(candidate);
}

function buildRedirect(url: URL): string {
	const target = url.pathname + url.search;
	return `${LOGIN_ROUTE}?redirect=${encodeURIComponent(target)}`;
}

export const load: PageServerLoad = async ({ locals, fetch, cookies, url }) => {
	if (!locals.user) {
		throw redirect(302, buildRedirect(url));
	}

	const sessionCookie = cookies.get(SESSION_COOKIE_NAME);
	const apiBase = resolveApiBase();
	const headers: Record<string, string> = {
		accept: 'application/json'
	};

	if (sessionCookie) {
		headers.cookie = `${SESSION_COOKIE_NAME}=${sessionCookie}`;
	}

        const [configResponse, promptResponse] = await Promise.all([
                fetch(`${apiBase}/api/config`, {
                        method: 'GET',
                        headers,
                        credentials: 'include'
                }),
                fetch(`${apiBase}/api/prompts`, {
                        method: 'GET',
                        headers,
                        credentials: 'include'
                })
        ]);

        if (configResponse.status === 401 || promptResponse.status === 401) {
                cookies.delete(SESSION_COOKIE_NAME, COOKIE_OPTIONS);
                throw redirect(302, buildRedirect(url));
        }

        if (!configResponse.ok) {
                throw error(configResponse.status, 'Unable to load runtime configuration.');
        }

        if (!promptResponse.ok) {
                throw error(promptResponse.status, 'Unable to load prompt state.');
        }

        const [config, prompts] = await Promise.all([
                configResponse.json(),
                promptResponse.json()
        ]);

        return {
                config,
                prompts,
                user: locals.user
        };
};

