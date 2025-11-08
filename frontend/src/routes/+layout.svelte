<script lang="ts">
  import { page } from '$app/stores';

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

  $: currentPath = $page.url.pathname;
</script>

<svelte:head>
  <title>Eternal Stories</title>
</svelte:head>

<nav class="site-nav">
  <div class="page-container nav-content">
    <a class="brand" href="/">Eternal Stories</a>
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

  @media (max-width: 720px) {
    .nav-content {
      flex-direction: column;
      align-items: flex-start;
      padding-top: 1rem;
      padding-bottom: 1rem;
      gap: 0.75rem;
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
  }
</style>
