import { redirect } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

const REDIRECT_PARAM = 'redirect';
const DEFAULT_REDIRECT = '/config';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (locals.user) {
		const target = url.searchParams.get(REDIRECT_PARAM) ?? DEFAULT_REDIRECT;
		throw redirect(302, target);
	}

	return {
		redirectTo: url.searchParams.get(REDIRECT_PARAM) ?? DEFAULT_REDIRECT
	};
};

