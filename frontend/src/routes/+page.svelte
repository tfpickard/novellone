<script lang="ts">
  import { onMount } from 'svelte';
  import { getStories } from '$lib/api';
  import type { PageData } from './$types';
  import { createThemeAction, type StoryTheme } from '$lib/theme';

  export let data: PageData;

  const initialStories = data.stories.items ?? [];
  type StorySummary = (typeof initialStories)[number];
  let stories: StorySummary[] = [...initialStories];
  let storyIds = new Set(stories.map((story) => story.id));
  let baseParams = new URLSearchParams(data.initialSearch ?? '');
  let total = data.stories.total ?? stories.length;
  let currentPage =
    data.stories.page ?? Number.parseInt(baseParams.get('page') ?? '1', 10);
  if (!baseParams.has('page_size')) {
    const fallbackSize =
      data.stories.page_size ?? Number.parseInt(baseParams.get('page_size') ?? '20', 10);
    baseParams.set('page_size', String(fallbackSize));
  }
  baseParams.delete('page');

  let loadingMore = false;
  let loadError: string | null = null;
  let sentinel: HTMLDivElement | null = null;
  let observer: IntersectionObserver | null = null;
  let observerReady = false;
  $: hasMore = stories.length < total;

  $: if (data) {
    const freshStories = (data.stories.items ?? []) as StorySummary[];
    stories = [...freshStories];
    storyIds = new Set(freshStories.map((story) => story.id));
    baseParams = new URLSearchParams(data.initialSearch ?? '');
    currentPage =
      data.stories.page ?? Number.parseInt(baseParams.get('page') ?? '1', 10);
    if (!baseParams.has('page_size')) {
      const fallbackSize =
        data.stories.page_size ?? Number.parseInt(baseParams.get('page_size') ?? '20', 10);
      baseParams.set('page_size', String(fallbackSize));
    }
    baseParams.delete('page');
    loadingMore = false;
    loadError = null;
    total = data.stories.total ?? freshStories.length;
    if (observerReady) {
      setupObserver();
    }
  }

  let selectedView: 'all' | 'active' | 'completed' | 'featured' = 'all';
  let sortMode: 'latest' | 'oldest' | 'chapters' = 'latest';
  const coerceTheme = (value: unknown): StoryTheme | undefined =>
    (value ?? undefined) as StoryTheme | undefined;

  const toDate = (value: string | null | undefined): number => {
    if (!value) return 0;
    const time = new Date(value).getTime();
    return Number.isNaN(time) ? 0 : time;
  };

  function stripMarkdown(text: string): string {
    return (
      text
        // Remove code fences
        .replace(/```[\s\S]*?```/g, '')
        // Remove inline code
        .replace(/`([^`]+)`/g, '$1')
        // Remove images
        .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
        // Replace links with link text
        .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
        // Remove emphasis markers
        .replace(/[*_~>#-]+/g, ' ')
        // Collapse whitespace
        .replace(/\s+/g, ' ')
        .trim()
    );
  }

  function preview(text: string | null | undefined, limit = 180): string {
    if (!text) return '';
    const plain = stripMarkdown(text);
    if (plain.length <= limit) return plain;
    return `${plain.slice(0, limit - 1).trimEnd()}…`;
  }

  function sortComparator(a: StorySummary, b: StorySummary): number {
    switch (sortMode) {
      case 'oldest':
        return toDate(a.created_at) - toDate(b.created_at);
      case 'chapters':
        return b.chapter_count - a.chapter_count || toDate(b.created_at) - toDate(a.created_at);
      case 'latest':
      default:
        return toDate(b.created_at) - toDate(a.created_at);
    }
  }

  $: activeCount = stories.filter((story) => story.status === 'active').length;
  $: completedCount = stories.filter((story) => story.status === 'completed').length;
  $: coverStories = stories.filter(
    (story) => story.status === 'completed' && Boolean(story.cover_image_url)
  );

  $: filteredStories = (() => {
    switch (selectedView) {
      case 'active':
        return stories.filter((story) => story.status === 'active');
      case 'completed':
        return stories.filter((story) => story.status === 'completed');
      case 'featured':
        return coverStories;
      case 'all':
      default:
        return stories;
    }
  })();

  $: displayStories = [...filteredStories].sort(sortComparator);

  function disconnectObserver(): void {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  }

  function setupObserver(): void {
    if (!observerReady || !hasMore || !sentinel || typeof IntersectionObserver === 'undefined') {
      return;
    }
    disconnectObserver();
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void loadMore();
        }
      },
      {
        rootMargin: '200px 0px'
      }
    );
    observer.observe(sentinel);
  }

  async function loadMore(): Promise<void> {
    if (loadingMore || !hasMore) {
      return;
    }
    loadingMore = true;
    loadError = null;

    try {
      const params = new URLSearchParams(baseParams);
      params.set('page', String(currentPage + 1));
      const nextPage = await getStories(params);

      const incomingItems = (nextPage.items ?? []) as StorySummary[];
      currentPage = nextPage.page ?? currentPage + 1;
      total = nextPage.total ?? total;

      const uniqueItems = incomingItems.filter((item) => {
        if (storyIds.has(item.id)) {
          return false;
        }
        storyIds.add(item.id);
        return true;
      });

      if (uniqueItems.length > 0) {
        stories = [...stories, ...uniqueItems];
      }

      if (uniqueItems.length === 0 && incomingItems.length === 0) {
        total = stories.length;
      }
    } catch (error) {
      if (error instanceof Error) {
        loadError = error.message;
      } else {
        loadError = 'Failed to load more stories.';
      }
    } finally {
      loadingMore = false;

      if (loadError) {
        disconnectObserver();
      } else if (hasMore) {
        setupObserver();
      } else {
        disconnectObserver();
      }
    }
  }

  $: if (observerReady && sentinel) {
    setupObserver();
  }

  onMount(() => {
    observerReady = true;
    setupObserver();
    return () => {
      disconnectObserver();
    };
  });
</script>


<div class="page-container">
  <header class="hero">
    <div>
      <h1>Hurl Unmasks Recursive Literature Leaking Out Love</h1>
      <p>Autonomous science fiction tales evolving in real time.</p>
    </div>
    <div class="hero-right">
      <div class="stats">
        <div>
          <span>Active</span>
          <strong>{stories.filter((s) => s.status === 'active').length}</strong>
        </div>
        <div>
          <span>Completed</span>
          <strong>{stories.filter((s) => s.status === 'completed').length}</strong>
        </div>
        <div>
          <span>Total</span>
          <strong>{total}</strong>
        </div>
      </div>
    </div>
  </header>

  {#if coverStories.length}
    <section class="cover-gallery">
      <header>
        <h2>Featured Covers</h2>
        <p>
          Completed stories crowned with bespoke cover art. Tap a cover to revisit the finale and
          explore its full journey.
        </p>
      </header>
      <div class="cover-scroll">
        {#each coverStories.slice(0, 12) as story}
          <a class="cover-card" href={`/story/${story.id}`}>
            <div class="cover-art">
              <img src={story.cover_image_url} alt="{story.title} cover artwork" loading="lazy" />
              <div class="cover-overlay">
                <span class="cover-status">{story.chapter_count} chapters</span>
                <h3>{story.title}</h3>
                <p>{preview(story.premise, 120)}</p>
              </div>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  <section class="listing-controls">
    <div class="view-toggle">
      <button
        class:selected={selectedView === 'all'}
        on:click={() => (selectedView = 'all')}
        type="button"
        aria-pressed={selectedView === 'all'}
      >
        All <span>{total}</span>
      </button>
      <button
        class:selected={selectedView === 'active'}
        on:click={() => (selectedView = 'active')}
        type="button"
        aria-pressed={selectedView === 'active'}
      >
        Active <span>{activeCount}</span>
      </button>
      <button
        class:selected={selectedView === 'completed'}
        on:click={() => (selectedView = 'completed')}
        type="button"
        aria-pressed={selectedView === 'completed'}
      >
        Completed <span>{completedCount}</span>
      </button>
      <button
        class:selected={selectedView === 'featured'}
        on:click={() => (selectedView = 'featured')}
        type="button"
        disabled={!coverStories.length}
        aria-pressed={selectedView === 'featured'}
      >
        Covers <span>{coverStories.length}</span>
      </button>
    </div>

    <label class="sort-control">
      <span>Sort by</span>
      <select bind:value={sortMode}>
        <option value="latest">Latest first</option>
        <option value="oldest">Oldest first</option>
        <option value="chapters">Most chapters</option>
      </select>
    </label>
  </section>

  <section class="grid">
    {#if displayStories.length === 0}
      <p class="empty-state">
        No stories match this view yet. Spawn a new tale or adjust the filters above.
      </p>
    {:else}
      {#each displayStories as story}
        <a
          class="story-card"
          href={`/story/${story.id}`}
          use:createThemeAction={coerceTheme(story.theme_json)}
        >
          {#if story.cover_image_url && story.status === 'completed'}
            <div class="card-cover-image">
              <img src={story.cover_image_url} alt="{story.title} cover" loading="lazy" />
            </div>
          {/if}
          <div class="card-content">
            <div class="status" data-live={story.status === 'active'}>{story.status}</div>
            <h2>{story.title}</h2>
            <div class="badges">
              {#if story.theme_json?.aesthetic}
                <span class="badge">{story.theme_json.aesthetic}</span>
              {/if}
              {#if story.theme_json?.mood}
                <span class="badge">{story.theme_json.mood}</span>
              {/if}
            </div>
            <p class="premise">{preview(story.premise)}</p>
            <footer>
              <span>{story.chapter_count} chapters</span>
              <span>{story.status === 'active' ? 'Live' : 'Completed'}</span>
            </footer>
          </div>
        </a>
      {/each}
    {/if}
  </section>

  <div class="load-more-section" aria-live="polite">
    {#if loadError}
      <div class="load-message error" role="alert">
        <p>{loadError}</p>
        <button
          type="button"
          class="load-more-button"
          on:click={() => void loadMore()}
          disabled={loadingMore}
        >
          Try again
        </button>
      </div>
    {/if}

    {#if hasMore && !loadError}
      <div class="load-message">
        {#if loadingMore}
          <p>Loading more stories…</p>
        {:else}
          <button
            type="button"
            class="load-more-button"
            on:click={() => void loadMore()}
            disabled={loadingMore}
          >
            Load more stories
          </button>
        {/if}
      </div>
    {:else if !hasMore && !loadError && stories.length > 0}
      <p class="load-message done">You've reached the end of the archive.</p>
    {/if}
  </div>

  <div class="load-sentinel" bind:this={sentinel} aria-hidden="true"></div>
</div>

<style>
  .hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    margin-bottom: 2.5rem;
  }

  .hero-right {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    align-items: flex-end;
  }

  .hero h1 {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.5rem;
    margin: 0 0 0.5rem 0;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    background: rgba(15, 23, 42, 0.7);
    border-radius: 1rem;
    padding: 1rem 1.5rem;
    box-shadow: 0 10px 30px rgba(2, 6, 23, 0.4);
  }

  .stats div {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .stats span {
    text-transform: uppercase;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .stats strong {
    font-size: 1.5rem;
    color: #38bdf8;
  }

  .cover-gallery {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 2.5rem;
  }

  .cover-gallery header h2 {
    margin: 0;
    font-size: 1.4rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .cover-gallery header p {
    margin: 0;
    opacity: 0.7;
  }

  .cover-scroll {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: minmax(220px, 280px);
    gap: 1.25rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
    scroll-snap-type: x mandatory;
  }

  .cover-scroll::-webkit-scrollbar {
    height: 8px;
  }

  .cover-scroll::-webkit-scrollbar-thumb {
    background: rgba(56, 189, 248, 0.4);
    border-radius: 999px;
  }

  .cover-card {
    scroll-snap-align: start;
    text-decoration: none;
    color: inherit;
  }

  .cover-art {
    position: relative;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.25);
    box-shadow: 0 18px 36px rgba(8, 24, 60, 0.45);
    height: 360px;
    display: flex;
  }

  .cover-art img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.35s ease;
  }

  .cover-card:hover img {
    transform: scale(1.04);
  }

  .cover-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 1.5rem;
    gap: 0.75rem;
    color: #f8fafc;
    text-shadow: 0 2px 6px rgba(2, 6, 23, 0.55);
  }

  .cover-overlay::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      rgba(11, 16, 32, 0.05) 0%,
      rgba(11, 16, 32, 0.25) 35%,
      rgba(11, 16, 32, 0.88) 75%,
      rgba(11, 16, 32, 0.95) 100%
    );
    backdrop-filter: blur(3px);
  }

  .cover-overlay > * {
    position: relative;
    z-index: 1;
  }

  .cover-overlay h3 {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    line-height: 1.2;
  }

  .cover-overlay p {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 500;
    opacity: 0.92;
    line-height: 1.45;
    line-clamp: 2;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .cover-status {
    align-self: flex-start;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.6);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
  }

  .listing-controls {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.5rem;
    align-items: center;
  }

  .view-toggle {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .view-toggle button {
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.55);
    color: #e2e8f0;
    padding: 0.55rem 0.9rem;
    border-radius: 999px;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  }

  .view-toggle button span {
    background: rgba(56, 189, 248, 0.25);
    border-radius: 999px;
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
  }

  .view-toggle button.selected {
    border-color: rgba(56, 189, 248, 0.75);
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.35), rgba(99, 102, 241, 0.35));
    box-shadow: 0 10px 24px rgba(56, 189, 248, 0.25);
  }

  .view-toggle button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .view-toggle button:not(:disabled):hover {
    transform: translateY(-1px);
  }

  .sort-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.75;
  }

  .sort-control select {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(148, 163, 184, 0.4);
    color: #e2e8f0;
    border-radius: 999px;
    padding: 0.45rem 0.9rem;
    font-size: 0.85rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.5rem;
  }

  .grid .empty-state {
    grid-column: 1 / -1;
    background: rgba(15, 23, 42, 0.5);
    border: 1px dashed rgba(56, 189, 248, 0.35);
    border-radius: 18px;
    padding: 2rem;
    text-align: center;
    font-size: 0.95rem;
    opacity: 0.75;
  }

  .story-card {
    background: var(--card-background, rgba(15, 23, 42, 0.9));
    border-radius: var(--border-radius, 16px);
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.2));
    box-shadow: var(--shadow-style, 0 12px 24px rgba(15, 23, 42, 0.35));
    display: flex;
    flex-direction: column;
    transition: transform var(--animation-speed, 0.3s) ease, box-shadow var(--animation-speed, 0.3s) ease;
    color: var(--text_color, #e2e8f0);
    background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.04), transparent 40%);
    overflow: hidden;
  }

  .story-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 20px 40px rgba(14, 165, 233, 0.25);
  }

  .card-cover-image {
    width: 100%;
    height: 180px;
    overflow: hidden;
  }

  .card-cover-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .card-content {
    padding: 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    flex: 1;
  }

  .story-card h2 {
    margin: 0;
    font-family: var(--font-heading, 'Orbitron', sans-serif);
    color: var(--primary-color, #38bdf8);
  }

  .badges {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .badge {
    background: var(--secondary-color, rgba(59, 130, 246, 0.25));
    color: var(--text-secondary, #bae6fd);
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .premise {
    flex: 1;
    margin: 0;
    line-height: 1.5;
    color: var(--text-color, #e2e8f0);
    opacity: 0.9;
  }

  footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    opacity: 0.8;
  }

  .status {
    align-self: flex-start;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    background: rgba(15, 118, 110, 0.2);
    border: 1px solid rgba(45, 212, 191, 0.6);
    color: #2dd4bf;
    animation: pulse 2s infinite;
  }

  .status[data-live='false'] {
    animation: none;
    opacity: 0.6;
  }

  @keyframes pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.3);
    }
    70% {
      box-shadow: 0 0 0 12px rgba(45, 212, 191, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(45, 212, 191, 0);
    }
  }

  .load-more-section {
    margin-top: 2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .load-message {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: center;
    color: #e2e8f0;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.35);
  }

  .load-message p {
    margin: 0;
  }

  .load-message.error {
    border-color: rgba(248, 113, 113, 0.6);
    background: rgba(248, 113, 113, 0.12);
    color: #fecaca;
  }

  .load-message.done {
    border-style: dashed;
    border-color: rgba(56, 189, 248, 0.4);
  }

  .load-more-section button {
    margin-top: 0.75rem;
  }

  .load-more-button {
    border: 1px solid rgba(56, 189, 248, 0.6);
    background: rgba(15, 23, 42, 0.7);
    color: #e0f2fe;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.65rem 1.5rem;
    border-radius: 999px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
  }

  .load-more-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 12px 24px rgba(56, 189, 248, 0.25);
  }

  .load-more-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .load-sentinel {
    width: 100%;
    height: 1px;
  }

  @media (max-width: 768px) {
    .hero {
      flex-direction: column;
      align-items: flex-start;
    }

    .hero-right {
      width: 100%;
      align-items: stretch;
    }

    .stats,
    .cover-scroll,
    .listing-controls {
      width: 100%;
    }

    .cover-scroll {
      grid-auto-columns: minmax(200px, 240px);
    }
  }
</style>
