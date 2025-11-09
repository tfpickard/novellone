import type { SessionUser } from '$lib/server/session';

declare global {
	namespace App {
		interface Locals {
			user: SessionUser | null;
		}

		interface PageData {
			user?: SessionUser | null;
		}
	}
}

export {};

