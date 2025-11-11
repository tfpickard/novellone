<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import type { PageData } from './$types';
  import { applyStoryTheme, type StoryTheme } from '$lib/theme';
  import { createStorySocket, type StorySocketMessage } from '$lib/websocket';
  import {
    killStory as killStoryRequest,
    deleteStory as deleteStoryRequest,
    generateChapter as generateChapterRequest,
    createEntityOverride,
    deleteEntityOverride,
    UnauthorizedError
  } from '$lib/api';
  import {
    CONTENT_AXIS_KEYS,
    CONTENT_AXIS_METADATA,
    sanitizeContentAxisSettings,
    sanitizeContentLevels,
    getTopContentAxes,
    type ContentAxisKey,
    type ContentAxisSettingsMap
  } from '$lib/contentAxes';
  import StoryTimeline from '$lib/components/StoryTimeline.svelte';
  import StoryDna from '$lib/components/StoryDna.svelte';
  import { renderMarkdown } from '$lib/markdown';

  export let data: PageData;

  let story = data.story;
  $: isAuthenticated = Boolean(data.config);
  let container: HTMLElement;
  let socket: WebSocket | null = null;
  let killing = false;
  let killError: string | null = null;
  let deleting = false;
  let deleteError: string | null = null;
  let generating = false;
  let generateError: string | null = null;
  const pendingChapterIds: Set<string> = new Set();

  const axisKeys = CONTENT_AXIS_KEYS;

  function computeContentAverages(
    chapters: Array<{ content_levels?: Record<string, unknown> }>
  ): Partial<Record<ContentAxisKey, number>> {
    const totals: Partial<Record<ContentAxisKey, { total: number; count: number }>> = {};
    for (const chapter of chapters ?? []) {
      const levels = sanitizeContentLevels(chapter.content_levels);
      for (const [axis, value] of Object.entries(levels) as Array<[ContentAxisKey, number]>) {
        const record = totals[axis] ?? { total: 0, count: 0 };
        record.total += value;
        record.count += 1;
        totals[axis] = record;
      }
    }
    const averages: Partial<Record<ContentAxisKey, number>> = {};
    for (const axis of axisKeys) {
      const entry = totals[axis];
      if (entry && entry.count > 0) {
        averages[axis] = Number((entry.total / entry.count).toFixed(3));
      }
    }
    return averages;
  }

  function chapterTopAxes(chapter: { content_levels?: Record<string, unknown> }) {
    return getTopContentAxes(chapter?.content_levels ?? null, 4);
  }

  let theme = story.theme_json as StoryTheme;
  let universe = story.universe;
  $: theme = story.theme_json as StoryTheme;
  $: universe = story.universe;
  $: if (container && theme) {
    applyStoryTheme(theme, container);
  }
  $: premiseHtml = renderMarkdown(story.premise);

  $: contentAxisSettings = sanitizeContentAxisSettings(story.content_settings) as ContentAxisSettingsMap;
  $: storedContentAverages = sanitizeContentLevels(story.content_axis_averages);
  $: derivedContentAverages = computeContentAverages(story.chapters ?? []);
  $: combinedContentAverages = {
    ...storedContentAverages,
    ...derivedContentAverages
  } as Partial<Record<ContentAxisKey, number>>;
  $: contentAxisSummaries = axisKeys.map((axis) => {
    const metadata = CONTENT_AXIS_METADATA[axis];
    const settings = contentAxisSettings[axis];
    const observed = combinedContentAverages[axis];
    return {
      key: axis,
      label: metadata.label,
      description: metadata.description,
      color: metadata.color,
      target: settings.average_level,
      targetDisplay: settings.average_level.toFixed(2),
      targetProgress: Math.min(Math.max(settings.average_level / 10, 0), 1),
      momentum: settings.momentum,
      momentumDisplay: `${settings.momentum >= 0 ? '+' : ''}${settings.momentum.toFixed(2)}/ch`,
      multiplier: settings.premise_multiplier,
      multiplierDisplay: `×${settings.premise_multiplier.toFixed(2)}`,
      observed,
      observedDisplay:
        observed === null || observed === undefined ? '—' : Number(observed).toFixed(2),
      observedProgress:
        observed === null || observed === undefined
          ? 0
          : Math.min(Math.max(Number(observed) / 10, 0), 1)
    };
  });

  let overrides = (story.entity_overrides as any[]) ?? [];
  let overrideScope: 'story' | 'global' = 'story';
  let overrideAction: 'suppress' | 'merge' = 'suppress';
  let overrideName = '';
  let overrideTarget = '';
  let overrideNotes = '';
  let overrideSaving = false;
  let overrideError: string | null = null;
  const removingOverrides: Record<string, boolean> = {};

  let coverModalOpen = false;

  const openCoverModal = () => {
    if (!story.cover_image_url) return;
    coverModalOpen = true;
  };

  const closeCoverModal = () => {
    coverModalOpen = false;
  };

  const handleCoverKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      closeCoverModal();
    }
  };

  $: if (typeof document !== 'undefined') {
    document.body.classList.toggle('cover-modal-open', coverModalOpen);
  }

  const hasUniverseContext = (context: any) => {
    if (!context) return false;
    const relatedCount = context.related_stories?.length ?? 0;
    return Boolean(context.cluster_id || relatedCount > 0);
  };

  const formatCohesion = (value: number | null | undefined) =>
    typeof value === 'number' ? value.toFixed(2) : '0.00';

  const formatTimestamp = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : '—';

  const resetOverrideForm = () => {
    overrideScope = 'story';
    overrideAction = 'suppress';
    overrideName = '';
    overrideTarget = '';
    overrideNotes = '';
  };

  const submitOverride = async () => {
    if (!isAuthenticated) {
      overrideError = 'Admin access required to manage overrides.';
      return;
    }
    if (overrideSaving) return;
    overrideSaving = true;
    overrideError = null;
    try {
      const name = overrideName.trim();
      const target = overrideTarget.trim();
      if (!name) {
        overrideError = 'Entity name is required.';
        return;
      }
      if (overrideAction === 'merge' && !target) {
        overrideError = 'Provide the canonical name to merge into.';
        return;
      }

      const created = await createEntityOverride({
        story_id: overrideScope === 'story' ? story.id : null,
        name,
        action: overrideAction,
        target_name: overrideAction === 'merge' ? target : null,
        notes: overrideNotes.trim() || null
      });
      overrides = [created, ...overrides.filter((item) => item.id !== created.id)];
      story = { ...story, entity_overrides: overrides } as typeof story;
      resetOverrideForm();
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        overrideError = 'Admin access required to manage overrides.';
      } else if (error instanceof Error) {
        overrideError = error.message;
      } else {
        overrideError = 'Failed to save override.';
      }
    } finally {
      overrideSaving = false;
    }
  };

  const removeOverride = async (overrideId: string) => {
    if (!isAuthenticated) {
      overrideError = 'Admin access required to manage overrides.';
      return;
    }
    if (removingOverrides[overrideId]) return;
    removingOverrides[overrideId] = true;
    overrideError = null;
    try {
      await deleteEntityOverride(overrideId);
      overrides = overrides.filter((item) => item.id !== overrideId);
      story = { ...story, entity_overrides: overrides } as typeof story;
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        overrideError = 'Admin access required to manage overrides.';
      } else if (error instanceof Error) {
        overrideError = error.message;
      } else {
        overrideError = 'Failed to delete override.';
      }
    } finally {
      delete removingOverrides[overrideId];
    }
  };

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
    if (!isAuthenticated || killing || story.status !== 'active') {
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
    if (!isAuthenticated || deleting) return;
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
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', handleCoverKeydown);
    }
  });
  async function handleGenerateChapter() {
    if (!isAuthenticated || generating || story.status !== 'active') return;
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
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleCoverKeydown);
    }
    if (typeof document !== 'undefined') {
      document.body.classList.remove('cover-modal-open');
    }
  });
</script>

<div class="page-container story-detail" bind:this={container}>
  <header class="story-header">
    <div class="header-content">
      {#if story.cover_image_url && story.status === 'completed'}
        <button
          type="button"
          class="cover-image-wrapper"
          on:click={openCoverModal}
          aria-haspopup="dialog"
          aria-label={`View full-size cover art for ${story.title}`}
        >
          <img src={story.cover_image_url} alt="{story.title} cover" class="cover-image" />
        </button>
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

      {#if hasUniverseContext(universe)}
        <aside class="universe-panel">
          <h3>Shared Universe</h3>
          {#if universe?.cluster_id}
            <div class="universe-cluster">
              <div class="cluster-label">{universe?.cluster_label ?? 'Continuity Cluster'}</div>
              <div class="cluster-meta">
                <span><strong>{universe?.cluster_size ?? 0}</strong> stories linked</span>
                <span>Cohesion <strong>{formatCohesion(universe?.cohesion)}</strong></span>
              </div>
            </div>
          {/if}

          {#if universe?.related_stories?.length}
            <div class="related-block">
              <h4>Intersecting Stories</h4>
              <ul>
                {#each universe.related_stories as related}
                  <li>
                    <a href={`/story/${related.story_id}`}>
                      <div class="related-heading">
                        <strong>{related.title || 'Untitled Story'}</strong>
                        <span class="related-weight">Affinity {formatCohesion(related.weight)}</span>
                      </div>
                      {#if related.shared_entities?.length}
                        <div class="shared-row">
                          <span class="shared-label">Characters</span>
                          <div class="shared-chips">
                            {#each related.shared_entities.slice(0, 4) as entity}
                              <span class="chip">{entity}</span>
                            {/each}
                            {#if related.shared_entities.length > 4}
                              <span class="chip more">+{related.shared_entities.length - 4}</span>
                            {/if}
                          </div>
                        </div>
                      {/if}
                      {#if related.shared_themes?.length}
                        <div class="shared-row">
                          <span class="shared-label">Motifs</span>
                          <div class="shared-chips">
                            {#each related.shared_themes.slice(0, 4) as theme}
                              <span class="chip">{theme}</span>
                            {/each}
                            {#if related.shared_themes.length > 4}
                              <span class="chip more">+{related.shared_themes.length - 4}</span>
                            {/if}
                          </div>
                        </div>
                      {/if}
                    </a>
                  </li>
                {/each}
              </ul>
            </div>
          {:else if universe?.cluster_id}
            <p class="universe-empty">This story shares a continuity thread, but no direct crossovers have surfaced yet.</p>
          {/if}

          <div class="override-block">
            <h4>Manual Corrections</h4>
            {#if isAuthenticated}
              <form class="override-form" on:submit|preventDefault={submitOverride}>
                <div class="field">
                  <label for="override-name">Entity Name</label>
                  <input
                    id="override-name"
                    type="text"
                    bind:value={overrideName}
                    placeholder="e.g. Captain Voss"
                    required
                  />
                </div>
                <div class="field">
                  <label for="override-action">Action</label>
                  <select id="override-action" bind:value={overrideAction}>
                    <option value="suppress">Suppress</option>
                    <option value="merge">Merge Alias</option>
                  </select>
                </div>
                {#if overrideAction === 'merge'}
                  <div class="field">
                    <label for="override-target">Merge Into</label>
                    <input
                      id="override-target"
                      type="text"
                      bind:value={overrideTarget}
                      placeholder="Canonical name"
                      required
                    />
                  </div>
                {/if}
                <div class="field">
                  <label for="override-scope">Scope</label>
                  <select id="override-scope" bind:value={overrideScope}>
                    <option value="story">This Story</option>
                    <option value="global">All Stories</option>
                  </select>
                </div>
                <div class="field notes">
                  <label for="override-notes">Notes</label>
                  <textarea
                    id="override-notes"
                    bind:value={overrideNotes}
                    rows="1"
                    placeholder="Optional context or reasoning"
                  ></textarea>
                </div>
                <div class="field action">
                  <button type="submit" class="override-submit" disabled={overrideSaving}>
                    {overrideSaving ? 'Saving…' : 'Save Override'}
                  </button>
                </div>
              </form>
            {:else}
              <p class="override-info-text">Sign in to manage manual overrides.</p>
            {/if}
            {#if overrideError}
              <p class="override-error">{overrideError}</p>
            {/if}

            {#if overrides.length}
              <ul class="override-list">
                {#each overrides as item (item.id)}
                  <li class="override-item">
                    <div class="override-info">
                      <div class="override-heading">
                        <span class={`scope-badge ${item.scope}`}>
                          {item.scope === 'global' ? 'Global' : 'Story'}
                        </span>
                        <strong>{item.name}</strong>
                        <span class="override-action">{item.action}</span>
                        {#if item.action === 'merge' && item.target_name}
                          <span class="merge-target">→ {item.target_name}</span>
                        {/if}
                      </div>
                      {#if item.notes}
                        <p class="override-notes">{item.notes}</p>
                      {/if}
                      <div class="override-meta">
                        Updated {formatTimestamp(item.updated_at)}
                      </div>
                    </div>
                    {#if isAuthenticated}
                      <button
                        class="override-remove"
                        on:click|preventDefault={() => removeOverride(item.id)}
                        disabled={removingOverrides[item.id]}
                      >
                        {removingOverrides[item.id] ? 'Removing…' : 'Remove'}
                      </button>
                    {/if}
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="universe-empty">No manual overrides for this story yet.</p>
            {/if}
          </div>
        </aside>
      {/if}

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
      <aside class="content-params">
        <h3>Content Axes</h3>
        <div class="content-axis-grid">
          {#each contentAxisSummaries as axis (axis.key)}
            <div
              class="content-axis-card"
              style={`--axis-color:${axis.color}; --axis-color-soft:${axis.color}33`}
            >
              <header>
                <h4>{axis.label}</h4>
                <p>{axis.description}</p>
              </header>
              <div class="content-bars">
                <div class="bar target">
                  <div class="bar-track">
                    <div class="bar-fill" style={`--progress:${axis.targetProgress}`}></div>
                  </div>
                  <span>Target {axis.targetDisplay}</span>
                </div>
                <div class="bar observed">
                  <div class="bar-track">
                    <div class="bar-fill" style={`--progress:${axis.observedProgress}`}></div>
                  </div>
                  <span>Observed {axis.observedDisplay}</span>
                </div>
              </div>
              <footer>
                <span>Momentum {axis.momentumDisplay}</span>
                <span>Premise {axis.multiplierDisplay}</span>
              </footer>
            </div>
          {/each}
        </div>
      </aside>
      {#if story.status === 'active' && isAuthenticated}
        <button class="generate-button" on:click={handleGenerateChapter} disabled={generating}>
          {generating ? 'Generating…' : 'Generate New Chapter'}
        </button>
      {/if}
      {#if story.status === 'active' && isAuthenticated}
        <button class="kill-button" on:click={handleKill} disabled={killing}>
          {killing ? 'Ending…' : 'Kill Story'}
        </button>
      {/if}
      {#if isAuthenticated}
        <button class="delete-button" on:click={handleDelete} disabled={deleting}>
          {deleting ? 'Deleting…' : 'Delete Story'}
        </button>
      {/if}
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
            {#if chapterTopAxes(chapter).length}
              <div class="chapter-content-levels">
                {#each chapterTopAxes(chapter) as axis (axis.key)}
                  <span
                    class="content-level-badge"
                    style={`--axis-color:${CONTENT_AXIS_METADATA[axis.key].color}; --axis-color-soft:${CONTENT_AXIS_METADATA[axis.key].color}26`}
                  >
                    <span class="content-label">{CONTENT_AXIS_METADATA[axis.key].label}</span>
                    <span class="content-value">{axis.value.toFixed(1)}</span>
                  </span>
                {/each}
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

{#if coverModalOpen && story.cover_image_url}
  <div class="cover-modal" role="dialog" aria-modal="true" aria-label={`Full-size cover art for ${story.title}`}>
    <button class="cover-modal-backdrop" type="button" on:click={closeCoverModal} aria-label="Close cover preview"></button>
    <div class="cover-modal-content">
      <button class="cover-modal-close" type="button" on:click={closeCoverModal} aria-label="Close cover preview">
        ×
      </button>
      <img src={story.cover_image_url} alt="{story.title} full cover art" loading="lazy" />
    </div>
  </div>
{/if}

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
    padding: 0;
    border: none;
    background: none;
    cursor: zoom-in;
    border-radius: 18px;
  }

  .cover-image-wrapper:focus-visible {
    outline: 3px solid var(--accent-color, rgba(56, 189, 248, 0.85));
    outline-offset: 4px;
  }

  .cover-image {
    width: 200px;
    height: 200px;
    object-fit: cover;
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    border: 2px solid var(--accent-color, rgba(125, 211, 252, 0.5));
  }

  .cover-modal {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: clamp(1.5rem, 4vw, 3rem);
  }

  .cover-modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(7, 11, 20, 0.82);
    border: none;
    padding: 0;
    margin: 0;
    cursor: pointer;
  }

  .cover-modal-content {
    position: relative;
    z-index: 1;
    max-width: min(85vw, 720px);
    max-height: min(90vh, 960px);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .cover-modal-content img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    border-radius: 20px;
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.75);
    border: 2px solid rgba(56, 189, 248, 0.4);
  }

  .cover-modal-close {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    border: none;
    background: rgba(15, 23, 42, 0.85);
    color: #e2e8f0;
    font-size: 1.5rem;
    line-height: 1;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 999px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  }

  .cover-modal-close:hover,
  .cover-modal-close:focus-visible {
    background: rgba(30, 64, 175, 0.85);
    color: #f8fafc;
  }

  :global(body.cover-modal-open) {
    overflow: hidden;
  }

  .side-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .universe-panel {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .universe-panel h3 {
    margin: 0;
    font-size: 1.2rem;
    color: #38bdf8;
  }

  .universe-cluster {
    background: rgba(56, 189, 248, 0.1);
    border-radius: 14px;
    padding: 1rem;
    border: 1px solid rgba(56, 189, 248, 0.25);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .cluster-label {
    font-weight: 600;
    color: #f97316;
  }

  .universe-panel .cluster-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: 0.85rem;
    opacity: 0.8;
  }

  .universe-panel .cluster-meta strong {
    color: #38bdf8;
    margin-right: 0.25rem;
  }

  .related-block ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .related-block a {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-decoration: none;
    color: inherit;
    padding: 0.75rem;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.15);
    background: rgba(2, 6, 23, 0.5);
    transition: border-color 0.2s ease, transform 0.2s ease;
  }

  .related-block a:hover {
    border-color: rgba(56, 189, 248, 0.4);
    transform: translateY(-2px);
  }

  .related-heading {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
  }

  .related-heading strong {
    color: #f1f5f9;
  }

  .related-weight {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .shared-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .shared-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.65;
  }

  .shared-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .chip {
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    font-size: 0.75rem;
  }

  .chip.more {
    background: rgba(15, 23, 42, 0.8);
    border-style: dashed;
  }

  .universe-empty {
    margin: 0;
    font-size: 0.85rem;
    opacity: 0.75;
    background: rgba(2, 6, 23, 0.5);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    border: 1px dashed rgba(148, 163, 184, 0.3);
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

  .content-params {
    background: rgba(15, 23, 42, 0.6);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .content-params h3 {
    margin: 0;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.8;
  }

  .content-axis-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  }

  .content-axis-card {
    background: rgba(2, 6, 23, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .content-axis-card header h4 {
    margin: 0 0 0.25rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--axis-color);
  }

  .content-axis-card header p {
    margin: 0;
    font-size: 0.75rem;
    line-height: 1.4;
    opacity: 0.75;
  }

  .content-bars {
    display: grid;
    gap: 0.5rem;
  }

  .content-bars .bar {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .content-bars .bar span {
    font-size: 0.7rem;
    opacity: 0.75;
  }

  .bar-track {
    background: rgba(255, 255, 255, 0.08);
    height: 6px;
    border-radius: 999px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 999px;
    width: calc(var(--progress, 0) * 100%);
    background: linear-gradient(135deg, var(--axis-color), rgba(255, 255, 255, 0.15));
    transition: width 0.3s ease;
  }

  .content-axis-card footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    opacity: 0.75;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .chapter-content-levels {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.5rem 0;
  }

  .content-level-badge {
    display: inline-flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.35rem 0.55rem;
    border-radius: 10px;
    border: 1px solid var(--axis-color, rgba(148, 163, 184, 0.4));
    background: rgba(15, 23, 42, 0.6);
    min-width: 120px;
  }

  .content-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .content-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--axis-color, #38bdf8);
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

  .override-block {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 0.5rem;
  }

  .override-block h4 {
    margin: 0;
    font-size: 0.95rem;
    color: #f97316;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .override-form {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem 1rem;
    align-items: end;
  }

  .override-form .field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .override-form label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .override-form input,
  .override-form select,
  .override-form textarea {
    background: rgba(2, 6, 23, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 12px;
    padding: 0.6rem 0.75rem;
    color: inherit;
    font-size: 0.9rem;
  }

  .override-form textarea {
    resize: vertical;
    min-height: 2.5rem;
  }

  .override-form .notes {
    grid-column: 1 / -1;
  }

  .override-form .action {
    grid-column: 1 / -1;
  }

  .override-submit {
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: #38bdf8;
    padding: 0.6rem 1.5rem;
    border-radius: 999px;
    cursor: pointer;
    font-weight: 600;
    align-self: flex-start;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }

  .override-submit:disabled {
    opacity: 0.6;
    cursor: progress;
  }

  .override-submit:not(:disabled):hover {
    transform: translateY(-1px);
    border-color: rgba(56, 189, 248, 0.7);
  }

  .override-error {
    margin: 0;
    color: #f87171;
    font-size: 0.85rem;
  }

  .override-info-text {
    margin: 0;
    font-size: 0.85rem;
    opacity: 0.75;
  }

  .override-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .override-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 0.75rem;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(2, 6, 23, 0.5);
  }

  .override-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .scope-badge {
    border-radius: 999px;
    padding: 0.15rem 0.65rem;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border: 1px solid rgba(148, 163, 184, 0.4);
  }

  .scope-badge.global {
    border-color: rgba(249, 115, 22, 0.5);
    color: #fb923c;
  }

  .scope-badge.story {
    border-color: rgba(56, 189, 248, 0.4);
    color: #38bdf8;
  }

  .override-action {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .merge-target {
    color: #38bdf8;
    font-weight: 600;
  }

  .override-notes {
    margin: 0 0 0.5rem;
    opacity: 0.8;
    line-height: 1.4;
  }

  .override-meta {
    font-size: 0.75rem;
    opacity: 0.6;
  }

  .override-remove {
    background: transparent;
    border: 1px solid rgba(248, 113, 113, 0.4);
    color: #f87171;
    border-radius: 12px;
    padding: 0.35rem 0.9rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
  }

  .override-remove:disabled {
    opacity: 0.6;
    cursor: progress;
  }


</style>
