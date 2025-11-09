<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import type { PageData } from './$types';

	export let data: PageData;

	const publicApiUrl = import.meta.env.VITE_PUBLIC_API_URL as string | undefined;
	let base = publicApiUrl;

	if (!base) {
		if (typeof window !== 'undefined') {
			base = `${window.location.hostname}:8000`;
		} else {
			base = 'backend:8000';
		}
	}

	const API_BASE = base.startsWith('http') ? base : `http://${base}`;

	let username = '';
	let password = '';
	let error: string | null = null;
	let loading = false;

	async function handleSubmit() {
		error = null;
		loading = true;
		try {
			const response = await fetch(`${API_BASE}/api/auth/login`, {
				method: 'POST',
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ username, password })
			});

			if (!response.ok) {
				let message = 'Invalid username or password.';
				try {
					const payload = await response.json();
					if (typeof payload === 'string' && payload) {
						message = payload;
					} else if (payload?.detail) {
						message = Array.isArray(payload.detail)
							? payload.detail.map((entry: any) => entry?.msg ?? entry).join(', ')
							: payload.detail;
					}
				} catch (parseError) {
					void parseError;
				}
				throw new Error(message);
			}

			await invalidateAll();
			await goto(data.redirectTo ?? '/config', { replaceState: true });
		} catch (err) {
			error =
				err instanceof Error && err.message
					? err.message
					: 'Unable to sign in. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="login-page">
	<section class="login-card">
		<header>
			<h1>Admin Access</h1>
			<p>Enter the administrator credentials to configure the story engine.</p>
		</header>

		<form class="login-form" on:submit|preventDefault={handleSubmit}>
			<label>
				<span>Username</span>
				<input
					name="username"
					type="text"
					bind:value={username}
					required
					autocomplete="username"
					placeholder="admin"
				/>
			</label>

			<label>
				<span>Password</span>
				<input
					name="password"
					type="password"
					bind:value={password}
					required
					autocomplete="current-password"
					placeholder="••••••••"
				/>
			</label>

			{#if error}
				<p class="error-message">{error}</p>
			{/if}

			<button type="submit" disabled={loading}>
				{loading ? 'Signing in…' : 'Sign in'}
			</button>
		</form>
	</section>
</div>

<style>
	.login-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: 2rem;
		background: radial-gradient(circle at top, rgba(59, 130, 246, 0.15), transparent 55%),
			radial-gradient(circle at bottom, rgba(147, 51, 234, 0.15), transparent 50%);
	}

	.login-card {
		width: min(420px, 100%);
		padding: 2.5rem;
		border-radius: 24px;
		background: rgba(15, 23, 42, 0.92);
		border: 1px solid rgba(148, 163, 184, 0.2);
		box-shadow: 0 24px 60px rgba(2, 6, 23, 0.5);
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		color: #e2e8f0;
	}

	.login-card header h1 {
		margin: 0;
		font-size: 1.8rem;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}

	.login-card header p {
		margin: 0.75rem 0 0;
		line-height: 1.6;
		opacity: 0.75;
	}

	.login-form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.9rem;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		opacity: 0.9;
	}

	input {
		border-radius: 14px;
		border: 1px solid rgba(148, 163, 184, 0.35);
		padding: 0.9rem 1rem;
		background: rgba(15, 23, 42, 0.85);
		color: #f8fafc;
		font-size: 1rem;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
	}

	input:focus {
		outline: none;
		border-color: rgba(56, 189, 248, 0.6);
		box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
	}

	button {
		border: none;
		border-radius: 14px;
		padding: 0.85rem 1.2rem;
		font-weight: 600;
		font-size: 0.95rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		cursor: pointer;
		background: linear-gradient(135deg, #38bdf8, #6366f1);
		color: #0f172a;
		transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.2s ease;
	}

	button:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 16px 36px rgba(99, 102, 241, 0.4);
	}

	button:disabled {
		cursor: not-allowed;
		opacity: 0.6;
		filter: grayscale(0.3);
	}

	.error-message {
		margin: 0;
		font-size: 0.85rem;
		color: #fca5a5;
	}

	@media (max-width: 640px) {
		.login-card {
			padding: 2rem;
		}
	}
</style>

