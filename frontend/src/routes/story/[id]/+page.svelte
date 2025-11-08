<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import type { PageData } from './$types';
  import { applyStoryTheme, type StoryTheme } from '$lib/theme';
  import { createStorySocket, type StorySocketMessage } from '$lib/websocket';
  import { killStory as killStoryRequest } from '$lib/api';

  export let data: PageData;

  let story = data.story;
  let container: HTMLElement;
  let socket: WebSocket | null = null;
  let killing = false;
  let killError: string | null = null;

  const theme = story.theme_json as StoryTheme;

  async function handleSocket(message: StorySocketMessage) {
    if (message.story_id !== story.id) return;
    if (message.type === 'new_chapter') {
      story = {
        ...story,
        chapters: [...story.chapters, message.chapter],
        chapter_count: story.chapter_count + 1,
        total_tokens:
          (story.total_tokens ?? 0) + (message.chapter.tokens_used ?? 0)
      };
      await tick();
      const last = document.querySelector('.chapter:last-of-type');
      last?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
    if (message.type === 'story_completed') {
      story = {
        ...story,
        status: 'completed',
        completion_reason: message.reason,
        summary: message.summary ?? story.summary,
        cover_art_url: message.cover_art_url ?? story.cover_art_url
      };
    }
  }

  async function handleKill() {
    if (killing || story.status !== 'active') {
      return;
    }
    const input = window.prompt('Provide a reason for ending this story', story.completion_reason ?? 'Terminated manually');
    if (input === null) {
      return;
    }
    killing = true;
    killError = null;
    try {
      const updated = await killStoryRequest(story.id, input.trim() || undefined);
      story = updated;
    } catch (error) {
      console.error('Failed to kill story', error);
      killError = error instanceof Error ? error.message : 'Failed to end story';
    } finally {
      killing = false;
    }
  }

  onMount(() => {
    if (container && theme) {
      applyStoryTheme(theme, container);
    }
    socket = createStorySocket(handleSocket);
  });

  onDestroy(() => {
    socket?.close();
  });
</script>

<div class="page-container story-detail" bind:this={container}>
  <header class="story-header">
    <div>
      <span class="status" data-live={story.status === 'active'}>{story.status}</span>
      <h1>{story.title}</h1>
      <p class="premise">{story.premise}</p>
      <div class="badges">
        {#if theme?.aesthetic}<span class="badge">{theme.aesthetic}</span>{/if}
        {#if theme?.mood}<span class="badge">{theme.mood}</span>{/if}
      </div>
    </div>
    <div class="side-panel">
      <aside class="meta">
        <div>
          <span>Chapters</span>
          <strong>{story.chapter_count}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{story.status}</strong>
        </div>
        <div>
          <span>Tokens</span>
          <strong>{story.total_tokens ?? 0}</strong>
        </div>
      </aside>
      {#if story.status === 'active'}
        <button class="kill-button" on:click={handleKill} disabled={killing}>
          {killing ? 'Ending…' : 'Kill Story'}
        </button>
      {/if}
      {#if killError}
        <p class="kill-error">{killError}</p>
      {/if}
    </div>
  </header>

  {#if story.status === 'completed' && story.completion_reason}
    <div class="completion">
      Story completed: {story.completion_reason}
    </div>
  {/if}

  {#if story.cover_art_url}
    <figure class="cover-art">
      <img src={story.cover_art_url} alt={`Cover art for ${story.title}`} loading="lazy" />
      {#if story.summary}
        <figcaption>{story.summary}</figcaption>
      {/if}
    </figure>
  {:else if story.summary}
    <section class="story-summary">
      <h2>Story Summary</h2>
      <p>{story.summary}</p>
    </section>
  {/if}

  <section class="chapters">
    {#each story.chapters as chapter (chapter.id)}
      <article class="chapter">
        <h2>Chapter {chapter.chapter_number}</h2>
        <time>{new Date(chapter.created_at).toLocaleString()}</time>
        <p>{chapter.content}</p>
      </article>
    {/each}
  </section>
</div>

<style>
  .story-detail {
    background: var(--background-color, rgba(2, 6, 23, 0.8));
    color: var(--text-color, #e2e8f0);
    border-radius: 24px;
    padding: 2.5rem;
    box-shadow: var(--shadow-style, 0 18px 40px rgba(15, 23, 42, 0.45));
  }

  .story-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 2rem;
    margin-bottom: 2rem;
  }

  .cover-art {
    margin: 0 0 2rem 0;
    display: grid;
    gap: 1rem;
    justify-items: center;
    background: rgba(15, 23, 42, 0.65);
    padding: 1.5rem;
    border-radius: 20px;
    box-shadow: 0 16px 30px rgba(8, 47, 73, 0.35);
  }

  .cover-art img {
    max-width: min(100%, 480px);
    border-radius: 16px;
    box-shadow: 0 18px 36px rgba(2, 6, 23, 0.6);
  }

  .cover-art figcaption {
    font-size: 1rem;
    line-height: 1.6;
    opacity: 0.9;
  }

  .story-summary {
    margin-bottom: 2rem;
    background: rgba(15, 23, 42, 0.65);
    padding: 1.5rem;
    border-radius: 20px;
    box-shadow: 0 16px 30px rgba(8, 47, 73, 0.35);
  }

  .story-summary h2 {
    margin-top: 0;
    font-family: var(--font-heading, 'Orbitron', sans-serif);
    color: var(--primary-color, #38bdf8);
  }

  .side-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .story-header h1 {
    margin: 0.5rem 0 1rem;
    font-size: 2.5rem;
    font-family: var(--font-heading, 'Orbitron', sans-serif);
    color: var(--primary-color, #38bdf8);
  }

  .premise {
    margin: 0;
    line-height: 1.7;
    opacity: 0.9;
    font-size: 1.1rem;
  }

  .badges {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .badge {
    background: var(--secondary-color, rgba(59, 130, 246, 0.25));
    color: var(--text-secondary, #cbd5f5);
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
  }

  .meta {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    min-width: 240px;
  }

  .meta div {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }

  .meta span {
    font-size: 0.75rem;
    text-transform: uppercase;
    opacity: 0.7;
  }

  .meta strong {
    font-size: 1.4rem;
  }

  .kill-button {
    background: #dc2626;
    color: #f8fafc;
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1.5rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 10px 24px rgba(220, 38, 38, 0.35);
  }

  .kill-button:hover:enabled {
    transform: translateY(-2px);
    box-shadow: 0 16px 30px rgba(220, 38, 38, 0.45);
  }

  .kill-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .kill-error {
    color: #fca5a5;
    font-size: 0.85rem;
    margin: 0;
  }

  .status {
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.5);
    color: #34d399;
    animation: pulse 2s infinite;
  }

  .status[data-live='false'] {
    animation: none;
    opacity: 0.7;
  }

  .completion {
    padding: 1rem 1.5rem;
    border: 1px dashed var(--accent-color, rgba(125, 211, 252, 0.7));
    border-radius: 16px;
    background: rgba(14, 116, 144, 0.2);
    margin-bottom: 2rem;
  }

  .chapters {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    max-height: 60vh;
    overflow-y: auto;
    padding-right: 1rem;
  }

  .chapter {
    background: rgba(2, 6, 23, 0.45);
    border-radius: 20px;
    padding: 1.5rem 1.75rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .chapter h2 {
    margin: 0 0 0.75rem;
    font-family: var(--font-heading, 'Orbitron', sans-serif);
    color: var(--accent-color, #f97316);
  }

  .chapter time {
    display: block;
    font-size: 0.8rem;
    opacity: 0.7;
    margin-bottom: 1rem;
  }

  .chapter p {
    white-space: pre-line;
    line-height: 1.6;
  }

  @media (max-width: 900px) {
    .story-header {
      flex-direction: column;
    }

    .meta {
      width: 100%;
    }

    .side-panel {
      width: 100%;
    }
  }
</style>
