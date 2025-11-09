<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import type { PageData } from './$types';
  import { applyStoryTheme, type StoryTheme } from '$lib/theme';
  import { createStorySocket, type StorySocketMessage } from '$lib/websocket';
  import {
    killStory as killStoryRequest,
    deleteStory as deleteStoryRequest,
    generateChapter as generateChapterRequest
  } from '$lib/api';
  import StoryTimeline from '$lib/components/StoryTimeline.svelte';
  import StoryDna from '$lib/components/StoryDna.svelte';
  import { renderMarkdown } from '$lib/markdown';

  export let data: PageData;

  let story = data.story;
  let container: HTMLElement;
  let socket: WebSocket | null = null;
  let killing = false;
  let killError: string | null = null;
  let deleting = false;
  let deleteError: string | null = null;
  let generating = false;
  let generateError: string | null = null;
  const pendingChapterIds: Set<string> = new Set();

  let theme = story.theme_json as StoryTheme;
  $: theme = story.theme_json as StoryTheme;
  $: if (container && theme) {
    applyStoryTheme(theme, container);
  }
  $: premiseHtml = renderMarkdown(story.premise);

  async function handleSocket(message: StorySocketMessage) {
    if (message.type === 'system_reset') {
      await goto('/');
      return;
    }
    if (message.story_id !== story.id) return;
    if (message.type === 'new_chapter') {
      if (pendingChapterIds.has(message.chapter.id)) {
        pendingChapterIds.delete(message.chapter.id);
        return;
      }
      if (story.chapters.some((existing) => existing.id === message.chapter.id)) {
        return;
      }
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
        cover_image_url: message.cover_image_url || story.cover_image_url
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

  async function handleDelete() {
    if (deleting) return;
    const confirmed = window.confirm(`Are you sure you want to permanently delete "${story.title}"? This action cannot be undone.`);
    if (!confirmed) return;
    
    deleting = true;
    deleteError = null;
    try {
      await deleteStoryRequest(story.id);
      // Navigate back to the main page after deletion
      await goto('/');
    } catch (error) {
      console.error('Failed to delete story', error);
      deleteError = error instanceof Error ? error.message : 'Failed to delete story';
      deleting = false;
    }
  }

  onMount(() => {
    socket = createStorySocket(handleSocket);
  });
  async function handleGenerateChapter() {
    if (generating || story.status !== 'active') return;
    generating = true;
    generateError = null;
    try {
      const updated = await generateChapterRequest(story.id);
      story = updated;
      pendingChapterIds.clear();
      updated.chapters.forEach((chapter) => pendingChapterIds.add(chapter.id));
      await tick();
      const last = document.querySelector('.chapter:last-of-type');
      last?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      console.error('Failed to generate chapter', error);
      generateError = error instanceof Error ? error.message : 'Failed to generate chapter';
    } finally {
      generating = false;
      Array.from(pendingChapterIds).forEach((id) => {
        if (!story.chapters.some((chapter) => chapter.id === id)) {
          pendingChapterIds.delete(id);
        }
      });
    }
  }

  onDestroy(() => {
    socket?.close();
  });
</script>

<div class="page-container story-detail" bind:this={container}>
  <header class="story-header">
    <div class="header-content">
      {#if story.cover_image_url && story.status === 'completed'}
        <div class="cover-image-wrapper">
          <img src={story.cover_image_url} alt="{story.title} cover" class="cover-image" />
        </div>
      {/if}
      <div class="header-text">
        <span class="status" data-live={story.status === 'active'}>{story.status}</span>
        <h1>{story.title}</h1>
        <div class="premise">
          {@html premiseHtml}
        </div>
        <div class="badges">
          {#if theme?.aesthetic}<span class="badge">{theme.aesthetic}</span>{/if}
          {#if theme?.mood}<span class="badge">{theme.mood}</span>{/if}
          {#if story.tone}<span class="badge badge-tone">{story.tone}</span>{/if}
          {#if story.narrative_perspective}<span class="badge badge-perspective">{story.narrative_perspective}</span>{/if}
        </div>
        {#if story.style_authors && story.style_authors.length > 0}
          <div class="style-authors">
            <strong>Stylistic Influences:</strong> {story.style_authors.join(', ')}
          </div>
        {/if}
        {#if story.genre_tags && story.genre_tags.length > 0}
          <div class="genre-tags">
            {#each story.genre_tags as tag}
              <span class="genre-tag">{tag}</span>
            {/each}
          </div>
        {/if}
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
        {#if story.estimated_reading_time_minutes}
          <div>
            <span>Reading Time</span>
            <strong>{story.estimated_reading_time_minutes} min</strong>
          </div>
        {/if}
        {#if story.aggregate_stats}
          <div>
            <span>Total Words</span>
            <strong>{story.aggregate_stats.total_word_count.toLocaleString()}</strong>
          </div>
          <div>
            <span>Avg Words/Ch</span>
            <strong>{story.aggregate_stats.avg_words_per_chapter.toFixed(0)}</strong>
          </div>
          <div>
            <span>Avg Word Length</span>
            <strong>{story.aggregate_stats.avg_word_length.toFixed(1)} chars</strong>
          </div>
          <div>
            <span>Lexical Diversity</span>
            <strong>{(story.aggregate_stats.overall_lexical_diversity * 100).toFixed(1)}%</strong>
          </div>
        {/if}
      </aside>
      
      <aside class="chaos-params">
        <h3>Chaos Parameters</h3>
        <div class="param">
          <span>Absurdity</span>
          <div class="param-bar">
            <div class="param-fill" style="width: {(story.absurdity_initial * 100).toFixed(0)}%; background: #f59e0b;"></div>
          </div>
          <span class="param-value">{story.absurdity_initial.toFixed(2)} +{story.absurdity_increment.toFixed(2)}/ch</span>
        </div>
        <div class="param">
          <span>Surrealism</span>
          <div class="param-bar">
            <div class="param-fill" style="width: {(story.surrealism_initial * 100).toFixed(0)}%; background: #8b5cf6;"></div>
          </div>
          <span class="param-value">{story.surrealism_initial.toFixed(2)} +{story.surrealism_increment.toFixed(2)}/ch</span>
        </div>
        <div class="param">
          <span>Ridiculousness</span>
          <div class="param-bar">
            <div class="param-fill" style="width: {(story.ridiculousness_initial * 100).toFixed(0)}%; background: #ec4899;"></div>
          </div>
          <span class="param-value">{story.ridiculousness_initial.toFixed(2)} +{story.ridiculousness_increment.toFixed(2)}/ch</span>
        </div>
        <div class="param">
          <span>Insanity</span>
          <div class="param-bar">
            <div class="param-fill" style="width: {(story.insanity_initial * 100).toFixed(0)}%; background: #ef4444;"></div>
          </div>
          <span class="param-value">{story.insanity_initial.toFixed(2)} +{story.insanity_increment.toFixed(2)}/ch</span>
        </div>
      </aside>
      {#if story.status === 'active'}
        <button class="generate-button" on:click={handleGenerateChapter} disabled={generating}>
          {generating ? 'Generating…' : 'Generate New Chapter'}
        </button>
      {/if}
      {#if story.status === 'active'}
        <button class="kill-button" on:click={handleKill} disabled={killing}>
          {killing ? 'Ending…' : 'Kill Story'}
        </button>
      {/if}
      <button class="delete-button" on:click={handleDelete} disabled={deleting}>
        {deleting ? 'Deleting…' : 'Delete Story'}
      </button>
      {#if killError}
        <p class="kill-error">{killError}</p>
      {/if}
      {#if deleteError}
        <p class="delete-error">{deleteError}</p>
      {/if}
      {#if generateError}
        <p class="generate-error">{generateError}</p>
      {/if}
    </div>
  </header>

  {#if story.status === 'completed' && story.completion_reason}
    <div class="completion">
      Story completed: {story.completion_reason}
    </div>
  {/if}

  <section class="analysis">
    <StoryDna story={story} chapters={story.chapters ?? []} evaluations={story.evaluations ?? []} />
    <StoryTimeline chapters={story.chapters ?? []} evaluations={story.evaluations ?? []} />
  </section>

  <section class="chapters">
    {#each story.chapters as chapter (chapter.id)}
      <article class="chapter" id={`chapter-${chapter.chapter_number}`}>
        <div class="chapter-header">
          <div>
            <h2>Chapter {chapter.chapter_number}</h2>
            <time>{new Date(chapter.created_at).toLocaleString()}</time>
          </div>
          <div class="chapter-metadata">
            {#if chapter.absurdity !== null && chapter.absurdity !== undefined}
              <div class="chapter-chaos">
                <div class="chaos-badge" style="background: rgba(245, 158, 11, 0.2); border-color: rgba(245, 158, 11, 0.5);">
                  <span class="chaos-label">A</span>
                  <span class="chaos-value">{chapter.absurdity.toFixed(2)}</span>
                </div>
                <div class="chaos-badge" style="background: rgba(139, 92, 246, 0.2); border-color: rgba(139, 92, 246, 0.5);">
                  <span class="chaos-label">S</span>
                  <span class="chaos-value">{chapter.surrealism?.toFixed(2) ?? 'N/A'}</span>
                </div>
                <div class="chaos-badge" style="background: rgba(236, 72, 153, 0.2); border-color: rgba(236, 72, 153, 0.5);">
                  <span class="chaos-label">R</span>
                  <span class="chaos-value">{chapter.ridiculousness?.toFixed(2) ?? 'N/A'}</span>
                </div>
                <div class="chaos-badge" style="background: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.5);">
                  <span class="chaos-label">I</span>
                  <span class="chaos-value">{chapter.insanity?.toFixed(2) ?? 'N/A'}</span>
                </div>
              </div>
            {/if}
            {#if chapter.stats}
              <div class="chapter-stats">
                <span class="stat-item" title="Word count">
                  <span class="stat-label">Words:</span>
                  <span class="stat-value">{chapter.stats.word_count}</span>
                </span>
                <span class="stat-item" title="Average word length">
                  <span class="stat-label">Avg:</span>
                  <span class="stat-value">{chapter.stats.avg_word_length} chars</span>
                </span>
                <span class="stat-item" title="Sentence count">
                  <span class="stat-label">Sentences:</span>
                  <span class="stat-value">{chapter.stats.sentence_count}</span>
                </span>
                <span class="stat-item" title="Lexical diversity">
                  <span class="stat-label">Diversity:</span>
                  <span class="stat-value">{(chapter.stats.lexical_diversity * 100).toFixed(1)}%</span>
                </span>
              </div>
            {/if}
          </div>
        </div>
        <div class="chapter-body">
          {@html renderMarkdown(chapter.content)}
        </div>
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

  .header-content {
    display: flex;
    gap: 2rem;
    align-items: flex-start;
    flex: 1;
  }

  .header-text {
    flex: 1;
  }

  .cover-image-wrapper {
    flex-shrink: 0;
  }

  .cover-image {
    width: 200px;
    height: 200px;
    object-fit: cover;
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    border: 2px solid var(--accent-color, rgba(125, 211, 252, 0.5));
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
    font-size: 1.05rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .premise :global(p) {
    margin: 0;
  }

  .premise :global(ul),
  .premise :global(ol) {
    padding-left: 1.25rem;
    margin: 0;
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

  .badge-tone {
    background: rgba(168, 85, 247, 0.25);
    color: #e9d5ff;
  }

  .badge-perspective {
    background: rgba(34, 197, 94, 0.25);
    color: #bbf7d0;
  }

  .style-authors {
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    background: rgba(15, 23, 42, 0.5);
    border-left: 3px solid var(--accent-color, #38bdf8);
    border-radius: 8px;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  .style-authors strong {
    color: var(--primary-color, #38bdf8);
    margin-right: 0.5rem;
  }

  .genre-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .genre-tag {
    background: rgba(249, 115, 22, 0.2);
    color: #fed7aa;
    padding: 0.3rem 0.75rem;
    border-radius: 6px;
    font-size: 0.7rem;
    text-transform: lowercase;
    border: 1px solid rgba(249, 115, 22, 0.3);
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

  .generate-button {
    background: linear-gradient(135deg, #38bdf8, #6366f1);
    color: #0f172a;
    border: none;
    border-radius: 999px;
    padding: 0.65rem 1.6rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    font-weight: 700;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 12px 28px rgba(56, 189, 248, 0.35);
  }

  .generate-button:hover:enabled {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(56, 189, 248, 0.4);
  }

  .generate-button:disabled {
    opacity: 0.65;
    cursor: not-allowed;
    box-shadow: none;
  }

  .delete-button {
    background: #7f1d1d;
    color: #f8fafc;
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1.5rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 10px 24px rgba(127, 29, 29, 0.35);
  }

  .delete-button:hover:enabled {
    transform: translateY(-2px);
    box-shadow: 0 16px 30px rgba(127, 29, 29, 0.45);
  }

  .delete-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .kill-error {
    color: #fca5a5;
    font-size: 0.85rem;
    margin: 0;
  }

  .delete-error {
    color: #fca5a5;
    font-size: 0.85rem;
    margin: 0;
  }

  .generate-error {
    color: #facc15;
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

  .analysis {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .chapter {
    background: rgba(2, 6, 23, 0.45);
    border-radius: 20px;
    padding: 1.5rem 1.75rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .chapter-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .chapter h2 {
    margin: 0 0 0.5rem;
    font-family: var(--font-heading, 'Orbitron', sans-serif);
    color: var(--accent-color, #f97316);
  }

  .chapter time {
    display: block;
    font-size: 0.8rem;
    opacity: 0.7;
  }

  .chapter-chaos {
    display: flex;
    gap: 0.5rem;
  }

  .chaos-badge {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.6rem;
    border-radius: 999px;
    border: 1px solid;
    font-size: 0.75rem;
  }

  .chaos-label {
    font-weight: 600;
    opacity: 0.8;
  }

  .chaos-value {
    font-weight: 700;
  }

  .chapter-metadata {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .chapter-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding: 0.5rem 0;
    font-size: 0.8rem;
  }

  .stat-item {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.6rem;
    background: rgba(100, 116, 139, 0.15);
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .stat-label {
    opacity: 0.7;
    font-size: 0.75rem;
  }

  .stat-value {
    font-weight: 600;
    color: #38bdf8;
  }

  .chaos-params {
    background: rgba(15, 23, 42, 0.6);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
  }

  .chaos-params h3 {
    margin: 0 0 1rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.8;
  }

  .param {
    margin-bottom: 0.75rem;
  }

  .param:last-child {
    margin-bottom: 0;
  }

  .param > span:first-child {
    display: block;
    font-size: 0.75rem;
    margin-bottom: 0.3rem;
    opacity: 0.7;
  }

  .param-bar {
    background: rgba(255, 255, 255, 0.1);
    height: 6px;
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 0.3rem;
  }

  .param-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
  }

  .param-value {
    display: block;
    font-size: 0.7rem;
    opacity: 0.6;
  }

  .chapter-body {
    line-height: 1.65;
    display: grid;
    gap: 1rem;
    font-size: 1rem;
  }

  .chapter-body :global(p) {
    margin: 0;
  }

  .chapter-body :global(ul),
  .chapter-body :global(ol) {
    margin: 0;
    padding-left: 1.25rem;
    display: grid;
    gap: 0.35rem;
  }

  .chapter-body :global(code) {
    background: rgba(15, 23, 42, 0.6);
    padding: 0.2rem 0.4rem;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .chapter-body :global(pre) {
    background: rgba(15, 23, 42, 0.75);
    border-radius: 12px;
    padding: 1rem;
    overflow: auto;
  }

  @media (max-width: 900px) {
    .story-header {
      flex-direction: column;
    }

    .header-content {
      flex-direction: column;
    }

    .cover-image {
      width: 100%;
      height: auto;
      max-width: 300px;
    }

    .meta {
      width: 100%;
    }

    .side-panel {
      width: 100%;
    }
  }
</style>
