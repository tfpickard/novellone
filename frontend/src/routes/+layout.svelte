<script lang="ts">
  import { page } from '$app/stores';
  import type { LayoutData } from './$types';

  export let data: LayoutData;

  const fallbackTitle = 'Hurl Unmasks Recursive Literature Leaking Out Love';

  type NavItem = {
    href: string;
    label: string;
    isActive: (path: string) => boolean;
  };

  const navItems: NavItem[] = [
    {
      href: '/',
      label: 'Stories',
      isActive: (path) => path === '/' || path.startsWith('/story')
    },
    {
      href: '/stats',
      label: 'Stats',
      isActive: (path) => path.startsWith('/stats')
    },
    {
      href: '/config',
      label: 'Config',
      isActive: (path) => path.startsWith('/config')
    }
  ];

  const githubRepoUrl = 'https://github.com/tfpickard/novellone.git';

  $: currentPath = $page.url.pathname;
  $: hurllolTitle =
    (data?.hurllol?.title && typeof data.hurllol.title === 'string'
      ? data.hurllol.title
      : '') || fallbackTitle;
</script>

<svelte:head>
  <title>{hurllolTitle}</title>
</svelte:head>

<nav class="site-nav">
  <div class="page-container nav-content">
    <a class="brand" href="/">{hurllolTitle}</a>
    <div class="nav-actions">
      <div class="nav-links">
        {#each navItems as item}
          {@const active = item.isActive(currentPath)}
          <a
            class="nav-link"
            class:active={active}
            href={item.href}
            aria-current={active ? 'page' : undefined}
          >
            {item.label}
          </a>
        {/each}
      </div>
      <a
        class="nav-link github-link"
        href={githubRepoUrl}
        target="_blank"
        rel="noreferrer noopener"
        aria-label="View the project on GitHub"
      >
        <svg class="github-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 4.01 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.74.54 1.49 0 1.07-.01 1.93-.01 2.19 0 .21.15.46.55.38A8 8 0 0 0 8 0"
          />
        </svg>
        <span>GitHub</span>
      </a>
    </div>
  </div>
</nav>

<slot />

<style>
  :global(body) {
    margin: 0;
    font-family: 'Inter', system-ui, sans-serif;
    background: #020617;
    color: #e2e8f0;
    min-height: 100vh;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(a) {
    color: inherit;
    text-decoration: none;
  }

  :global(.page-container) {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  .site-nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(2, 6, 23, 0.85);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  }

  .nav-content {
    padding-top: 1.25rem;
    padding-bottom: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
  }

  .brand {
    font-family: 'Orbitron', sans-serif;
    font-size: 1rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    font-weight: 600;
    color: #38bdf8;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .nav-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .nav-link {
    padding: 0.5rem 0.9rem;
    border-radius: 999px;
    font-size: 0.95rem;
    letter-spacing: 0.02em;
    color: rgba(226, 232, 240, 0.85);
    transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
  }

  .nav-link:hover {
    background: rgba(59, 130, 246, 0.25);
    color: #f8fafc;
  }

  .nav-link.active {
    background: rgba(59, 130, 246, 0.35);
    color: #f8fafc;
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.25);
  }

  .github-link {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    white-space: nowrap;
  }

  .github-icon {
    width: 1rem;
    height: 1rem;
  }

  @media (max-width: 720px) {
    .nav-content {
      flex-direction: column;
      align-items: flex-start;
      padding-top: 1rem;
      padding-bottom: 1rem;
      gap: 0.75rem;
    }

    .nav-actions {
      width: 100%;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .nav-links {
      flex-wrap: wrap;
      width: 100%;
      gap: 0.5rem;
    }

    .nav-link {
      flex: 1 1 auto;
      text-align: center;
    }

    .github-link {
      flex: 0 0 auto;
    }
  }
</style>
