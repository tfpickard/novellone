<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getStories } from '$lib/api';
  import { onDestroy, onMount, tick } from 'svelte';
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
      href: '/recommended',
      label: 'Recommended',
      isActive: (path) => path.startsWith('/recommended')
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

  type SearchResult = {
    id: string;
    title: string;
    premise: string;
    status: string;
    cover_image_url?: string | null;
    completed_at?: string | null;
  };

  let showSearch = false;
  let searchQuery = '';
  let searchResults: SearchResult[] = [];
  let searchLoading = false;
  let searchError: string | null = null;
  let searchInput: HTMLInputElement | null = null;
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;
  let searchNonce = 0;

  const resetSearch = () => {
    searchNonce += 1;
    searchQuery = '';
    searchResults = [];
    searchError = null;
    searchLoading = false;
    if (searchTimeout) {
      clearTimeout(searchTimeout);
      searchTimeout = null;
    }
  };

  const closeSearch = () => {
    showSearch = false;
    resetSearch();
  };

  const openSearch = async () => {
    showSearch = true;
    await tick();
    searchInput?.focus();
  };

  const handleKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && showSearch) {
      closeSearch();
    }
  };

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
  });

  onDestroy(() => {
    window.removeEventListener('keydown', handleKeydown);
    if (searchTimeout) {
      clearTimeout(searchTimeout);
      searchTimeout = null;
    }
  });

  const performSearch = async (term: string) => {
    const currentNonce = ++searchNonce;
    searchLoading = true;
    searchError = null;
    try {
      const params = new URLSearchParams();
      params.set('page_size', '100');
      params.set('page', '1');
      const response = await getStories(params);
      const items = (response.items ?? []) as SearchResult[];
      const normalised = term.trim().toLowerCase();
      const matches = items.filter((item) => {
        const title = item.title?.toLowerCase?.() ?? '';
        const premise = item.premise?.toLowerCase?.() ?? '';
        return title.includes(normalised) || premise.includes(normalised);
      });
      if (currentNonce === searchNonce) {
        searchResults = matches.slice(0, 20);
      }
    } catch (error) {
      if (currentNonce === searchNonce) {
        searchError =
          error instanceof Error ? error.message : 'Failed to load search results.';
      }
    } finally {
      if (currentNonce === searchNonce) {
        searchLoading = false;
      }
    }
  };

  const handleSearchInput = (event: Event) => {
    const value = (event.currentTarget as HTMLInputElement).value;
    searchQuery = value;
    if (searchTimeout) {
      clearTimeout(searchTimeout);
      searchTimeout = null;
    }
    if (value.trim().length < 2) {
      searchResults = [];
      searchError = null;
      searchLoading = false;
      return;
    }
    searchTimeout = setTimeout(() => {
      void performSearch(value);
    }, 200);
  };

  const openStory = async (result: SearchResult) => {
    closeSearch();
    await goto(`/story/${result.id}`);
  };

  const handleSearchSubmit = (event: Event) => {
    event.preventDefault();
    if (searchResults.length > 0) {
      void openStory(searchResults[0]);
    }
  };

  const formatStatus = (status: string) =>
    status
      ? status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
      : '';

  const formatCompletedDate = (value: string | null | undefined) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleDateString();
  };
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
      <button
        class="nav-link search-trigger"
        type="button"
        on:click={openSearch}
        aria-haspopup="dialog"
        aria-expanded={showSearch}
      >
        Search
      </button>
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

{#if showSearch}
  <div class="search-overlay" role="presentation" on:click|self={closeSearch}>
    <div
      class="search-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="search-dialog-title"
    >
      <form class="search-header" on:submit={handleSearchSubmit}>
        <label class="search-label" for="global-search-input" id="search-dialog-title">
          Search Stories
        </label>
        <div class="search-input-wrapper">
          <input
            id="global-search-input"
            class="search-input"
            type="search"
            placeholder="Search by title or premise"
            bind:this={searchInput}
            bind:value={searchQuery}
            on:input={handleSearchInput}
            autocomplete="off"
          />
          <button class="close-search" type="button" on:click={closeSearch} aria-label="Close search">
            ×
          </button>
        </div>
      </form>
      <div class="search-body">
        {#if searchQuery.trim().length < 2}
          <p class="search-hint">Type at least two characters to search stories.</p>
        {:else if searchLoading}
          <p class="search-hint">Searching…</p>
        {:else if searchError}
          <p class="search-hint error">{searchError}</p>
        {:else if searchResults.length === 0}
          <p class="search-hint">No stories matched “{searchQuery}”.</p>
        {:else}
          <ul class="search-results">
            {#each searchResults as result}
              {@const completed = formatCompletedDate(result.completed_at)}
              <li>
                <button class="search-result" type="button" on:click={() => void openStory(result)}>
                  {#if result.cover_image_url}
                    <img src={result.cover_image_url} alt="" class="search-cover" loading="lazy" />
                  {:else}
                    <div class="search-cover placeholder" aria-hidden="true">📖</div>
                  {/if}
                  <div class="search-result-details">
                    <span class="search-result-title">{result.title}</span>
                    <span class="search-result-meta">
                      {formatStatus(result.status)}
                      {#if completed}
                        · Completed {completed}
                      {/if}
                    </span>
                    <span class="search-result-premise">{result.premise}</span>
                  </div>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}

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
    border: none;
    background: transparent;
    cursor: pointer;
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

  .search-trigger {
    border: 1px solid rgba(59, 130, 246, 0.3);
    background: rgba(15, 23, 42, 0.55);
    color: #bfdbfe;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }

  .search-trigger:hover,
  .search-trigger:focus-visible {
    border-color: rgba(59, 130, 246, 0.6);
    background: rgba(59, 130, 246, 0.25);
    outline: none;
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

  .search-overlay {
    position: fixed;
    inset: 0;
    background: rgba(2, 6, 23, 0.75);
    backdrop-filter: blur(18px);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 6rem 1.5rem 2rem;
    z-index: 20;
  }

  .search-modal {
    width: min(720px, 100%);
    background: rgba(15, 23, 42, 0.95);
    border-radius: 24px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 40px 70px rgba(15, 23, 42, 0.65);
    padding: 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .search-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin: 0;
  }

  .search-label {
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #38bdf8;
  }

  .search-input-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    border-radius: 999px;
    padding: 0.4rem 0.6rem 0.4rem 1rem;
    border: 1px solid rgba(59, 130, 246, 0.35);
    background: rgba(2, 6, 23, 0.75);
  }

  .search-input {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    color: #f8fafc;
    font-size: 1rem;
    outline: none;
  }

  .close-search {
    border: none;
    background: transparent;
    color: rgba(226, 232, 240, 0.7);
    font-size: 1.6rem;
    line-height: 1;
    padding: 0.2rem 0.45rem;
    border-radius: 999px;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .close-search:hover,
  .close-search:focus-visible {
    background: rgba(59, 130, 246, 0.25);
    color: #f8fafc;
    outline: none;
  }

  .search-body {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-height: 60vh;
    overflow-y: auto;
    padding-right: 0.25rem;
  }

  .search-hint {
    margin: 0;
    color: rgba(226, 232, 240, 0.75);
    font-size: 0.95rem;
  }

  .search-hint.error {
    color: #fca5a5;
  }

  .search-results {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .search-result {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
    width: 100%;
    border: 1px solid rgba(59, 130, 246, 0.3);
    background: rgba(15, 23, 42, 0.6);
    border-radius: 18px;
    padding: 0.75rem 1rem;
    text-align: left;
    color: inherit;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
  }

  .search-result:hover,
  .search-result:focus-visible {
    border-color: rgba(59, 130, 246, 0.6);
    background: rgba(30, 64, 175, 0.35);
    transform: translateY(-2px);
    outline: none;
  }

  .search-cover {
    width: 3rem;
    height: 3rem;
    border-radius: 12px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .search-cover.placeholder {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(30, 41, 59, 0.8);
    color: #cbd5f5;
    font-size: 1.4rem;
  }

  .search-result-details {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .search-result-title {
    font-weight: 600;
    color: #f8fafc;
  }

  .search-result-meta {
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.85);
  }

  .search-result-premise {
    font-size: 0.85rem;
    color: rgba(226, 232, 240, 0.75);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
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

    .search-overlay {
      padding-top: 5rem;
    }

    .search-modal {
      padding: 1.5rem;
      gap: 1.25rem;
    }

    .search-result {
      flex-direction: column;
      align-items: stretch;
      gap: 0.75rem;
    }

    .search-cover {
      width: 100%;
      height: 10rem;
    }
  }
</style>
