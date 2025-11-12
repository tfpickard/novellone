<script lang="ts">
  import { generateChapter, UnauthorizedError } from '$lib/api';
  import type { PageData } from './$types';

  export let data: PageData;

  type Metric = PageData['recommendations']['metrics'][number];
  type MetricEntry = NonNullable<Metric['best']>;

  const metrics: Metric[] = data.recommendations?.metrics ?? [];

  const allEntries: MetricEntry[] = metrics.flatMap((metric) =>
    [metric.best, metric.worst].filter(Boolean) as MetricEntry[]
  );

  const formatStatus = (status: string) =>
    status ? status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()) : '';

  const normalizeGenreLabel = (value: string) =>
    value
      .replace(/&amp;/gi, '&')
      .replace(/\s+/g, ' ')
      .trim();
  const stripMarkup = (value: string) => value.replace(/\[[^\]]*\]/g, ' ').replace(/<[^>]*>/g, ' ');
  const cleanGenreSegment = (value: string) =>
    normalizeGenreLabel(value)
      .replace(/^['"‘’“”]+|['"‘’“”]+$/g, '')
      .replace(/^\((.*)\)$/g, '$1')
      .replace(/^(?:and|with|featuring|versus|vs\.?|against|plus|or|x|x's)\s+/i, '')
      .replace(/^(?:a|an|the)\s+/i, '')
      .replace(/[()]+$/g, '')
      .replace(/^[()]+/g, '')
      .replace(/[.!?]+$/, '');
  const explodeGenreTag = (value: string) => {
    const normalized = normalizeGenreLabel(stripMarkup(value));
    if (!normalized) return [] as string[];
    const separators = /[,;:\/•·|&+]+/;
    const connectorBreaks = /\b(?:and\/or|and|with|featuring|versus|vs\.?|against|plus|or|x|x's)\b/gi;
    const dashSplit = normalized
      .replace(/[\r\n]+/g, ',')
      .replace(/\(([^)]+)\)/g, (_, inner: string) => `,${inner},`)
      .split(/\s*[–—]\s*|\s+-\s+/);
    const segments = dashSplit
      .map((segment) => segment.replace(connectorBreaks, ','))
      .map((segment) => segment.split(separators))
      .flat()
      .map((segment) => cleanGenreSegment(segment))
      .filter(Boolean);
    return segments.length > 0 ? segments : [normalized];
  };
  const explodeGenreTags = (values: string[] | string | null | undefined) => {
    if (!values) return [] as string[];
    const source = Array.isArray(values) ? values : [values];
    const tags: string[] = [];
    const seen = new Set<string>();
    const keyFor = (value: string) => normalizeGenreLabel(value).toLowerCase();
    for (const value of source) {
      if (!value) continue;
      for (const segment of explodeGenreTag(value)) {
        if (!segment) continue;
        const key = keyFor(segment);
        if (seen.has(key)) continue;
        seen.add(key);
        tags.push(segment);
      }
    }
    return tags;
  };
  const genreKey = (value: string) => normalizeGenreLabel(value).toLowerCase();

  const availableStatuses = Array.from(new Set(allEntries.map((entry) => entry.status))).sort();

  const genreAggregates = new Map<string, { label: string; count: number }>();
  for (const entry of allEntries) {
    for (const tag of explodeGenreTags(entry.genre_tags)) {
      if (!tag) continue;
      const label = normalizeGenreLabel(tag);
      if (!label) continue;
      const key = genreKey(label);
      const aggregate = genreAggregates.get(key);
      if (aggregate) {
        aggregate.count += 1;
      } else {
        genreAggregates.set(key, { label, count: 1 });
      }
    }
  }

  const genreCloudBase = Array.from(genreAggregates.entries()).map(([key, { label, count }]) => ({
    key,
    label,
    count
  }));

  genreCloudBase.sort((a, b) => {
    if (a.count !== b.count) {
      return b.count - a.count;
    }
    return a.label.localeCompare(b.label);
  });

  const maxGenreCount = genreCloudBase.reduce((max, { count }) => Math.max(max, count), 0) || 1;

  const genreCloud = genreCloudBase.map(({ key, label, count }) => ({
    key,
    label,
    count,
    weight: 0.85 + (count / maxGenreCount) * 0.75
  }));

  let selectedStatus: string = 'all';
  let selectedGenre: string = 'all';
  let showPriorityOnly = false;

  let queueing: Record<string, boolean> = {};
  let queueFeedback: Record<string, { type: 'success' | 'error'; message: string } | null> = {};

  const formatValue = (metric: Metric, entry: MetricEntry | null) => {
    if (!entry || entry.value === null || entry.value === undefined) {
      return '—';
    }
    const decimals = metric.decimals ?? 2;
    if (decimals === 0) {
      return Math.round(entry.value).toLocaleString();
    }
    return entry.value.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  };

  const formatNumber = (metric: Metric, value: number) => {
    const decimals = metric.decimals ?? 2;
    return value.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  };

  const formatDisplayValue = (metric: Metric, entry: MetricEntry | null) => {
    const base = formatValue(metric, entry);
    if (base === '—') return base;
    return metric.unit ? `${base}${metric.unit}` : base;
  };

  const guidanceText = (metric: Metric) =>
    metric.higher_is_better
      ? 'Higher values indicate stronger performance.'
      : 'Lower values indicate stronger performance.';

  const formatDate = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : null;

  const formatRelativeTime = (value: string | null | undefined) => {
    if (!value) return null;
    const timestamp = new Date(value).getTime();
    if (Number.isNaN(timestamp)) return null;
    const diff = Date.now() - timestamp;
    if (diff < 0) return 'in the future';
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'moments ago';
    if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;
    const years = Math.floor(days / 365);
    return `${years} year${years === 1 ? '' : 's'} ago`;
  };

  const previewText = (text: string | null | undefined, limit = 160) => {
    if (!text) return '';
    const normalised = text.replace(/\s+/g, ' ').trim();
    if (normalised.length <= limit) {
      return normalised;
    }
    return `${normalised.slice(0, limit - 1).trimEnd()}…`;
  };

  const entryMatches = (entry: MetricEntry | null | undefined) => {
    if (!entry) return false;
    if (selectedStatus !== 'all' && entry.status !== selectedStatus) {
      return false;
    }
    if (selectedGenre !== 'all') {
      const genres = explodeGenreTags(entry.genre_tags).map((genre) => genreKey(genre));
      if (!genres.includes(selectedGenre)) {
        return false;
      }
    }
    return true;
  };

  const entryFilteredOut = (entry: MetricEntry | null | undefined) => {
    if (!entry) return false;
    return !entryMatches(entry);
  };

  const grouped = metrics.reduce(
    (acc, metric) => {
      const key = metric.group ?? 'Other Metrics';
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(metric);
      return acc;
    },
    {} as Record<string, Metric[]>
  );

  const groupedEntries = Object.entries(grouped).map(([groupName, entries]) => ({
    name: groupName,
    order: entries[0]?.order ?? 0,
    metrics: entries
  }));

  groupedEntries.sort((a, b) => a.order - b.order);

  const chapterLink = (entry: MetricEntry) =>
    `/story/${entry.story_id}#chapter-${entry.latest_chapter_number ?? entry.chapter_count}`;

  const analyticsLink = (entry: MetricEntry) => `/stats?story=${entry.story_id}`;

  const canQueue = (entry: MetricEntry) => entry.status === 'active';

  const queueChapter = async (entry: MetricEntry) => {
    queueing = { ...queueing, [entry.story_id]: true };
    queueFeedback = { ...queueFeedback, [entry.story_id]: null };
    try {
      await generateChapter(entry.story_id);
      queueFeedback = {
        ...queueFeedback,
        [entry.story_id]: { type: 'success', message: 'Queued a fresh chapter.' }
      };
    } catch (error) {
      let message = 'Failed to queue a new chapter.';
      if (error instanceof UnauthorizedError) {
        message = 'Admin access required to queue chapter generation.';
      } else if (error instanceof Error && error.message) {
        message = error.message;
      }
      queueFeedback = {
        ...queueFeedback,
        [entry.story_id]: { type: 'error', message }
      };
    } finally {
      queueing = { ...queueing, [entry.story_id]: false };
    }
  };

  const buildSparkline = (points: number[] | null | undefined) => {
    if (!points || points.length === 0) return null;
    const width = 120;
    const height = 40;
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const step = points.length > 1 ? width / (points.length - 1) : width;
    const path = points
      .map((value, index) => {
        const x = index * step;
        const y = height - ((value - min) / range) * height;
        return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
    return { width, height, path, min, max };
  };

  const getTrendBadge = (metric: Metric, change: number | null | undefined) => {
    if (change === null || change === undefined) return null;
    const decimals = Math.min(metric.decimals ?? 2, 2);
    const formatted = Math.abs(change).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
    if (change > 0) {
      return { label: `▲ ${formatted}`, direction: 'positive' as const };
    }
    if (change < 0) {
      return { label: `▼ ${formatted}`, direction: 'negative' as const };
    }
    return { label: '—', direction: 'neutral' as const };
  };

  const metricTrendContext = (metric: Metric) =>
    metric.group.toLowerCase().includes('chaos') ? 'since first chapter' : 'since first evaluation';

  const formatNarrativePerspective = (value: string | null | undefined) =>
    value ? formatStatus(value) : null;

  const statusLabel = (value: string) => (value === 'all' ? 'All statuses' : formatStatus(value));

  $: selectedGenreLabel =
    selectedGenre === 'all'
      ? null
      : genreCloud.find((entry) => entry.key === selectedGenre)?.label ?? null;

  const toggleGenreFilter = (genre: string) => {
    const key = genreKey(genre);
    selectedGenre = selectedGenre === key ? 'all' : key;
  };

  $: filteredSections = groupedEntries
    .map((section) => ({
      ...section,
      metrics: section.metrics.filter((metric) => {
        if (showPriorityOnly && !metric.priority) return false;
        const bestMatches = entryMatches(metric.best);
        const worstMatches = entryMatches(metric.worst);
        return bestMatches || worstMatches;
      })
    }))
    .filter((section) => section.metrics.length > 0);

  $: hasFilteredMetrics = filteredSections.length > 0;
</script>

<div class="page-container recommendations-page">
  <header class="page-header">
    <h1>Recommended/Discouraged Stories</h1>
    <p>
      Extremes across every tracked metric. Explore the standout stories that shine — and the ones that
      spiral delightfully off the rails.
    </p>
  </header>

  {#if metrics.length === 0}
    <section class="empty-state">
      <p>No story metrics are available yet. Generate a few chapters to unlock recommendations.</p>
    </section>
  {:else}
    <section class="controls">
      <div class="control-group">
        <label>
          <span>Status</span>
          <select bind:value={selectedStatus}>
            <option value="all">{statusLabel('all')}</option>
            {#each availableStatuses as status}
              <option value={status}>{statusLabel(status)}</option>
            {/each}
          </select>
        </label>
      </div>
      <label class="toggle">
        <input type="checkbox" bind:checked={showPriorityOnly} />
        <span>Show only priority metrics</span>
      </label>
    </section>

    {#if genreCloud.length > 0}
      <section class="tag-cloud" aria-label="Browse stories by tag">
        <div class="tag-cloud-header">
          <div class="tag-cloud-title">
            <h2>Browse by tag</h2>
            {#if selectedGenreLabel}
              <span class="active-tag-label" aria-live="polite">
                Showing stories tagged <strong>{selectedGenreLabel}</strong>
              </span>
            {/if}
          </div>
          {#if selectedGenre !== 'all'}
            <button type="button" class="clear-tags" on:click={() => (selectedGenre = 'all')}>
              Clear tag filter
            </button>
          {/if}
        </div>
        <div class="tag-cloud-list">
          <button
            type="button"
            class={`tag-cloud-item all ${selectedGenre === 'all' ? 'active' : ''}`}
            style="--tag-weight: 1"
            aria-pressed={selectedGenre === 'all'}
            on:click={() => (selectedGenre = 'all')}
          >
            <span class="tag-label">All tags</span>
          </button>
          {#each genreCloud as { key, label, count, weight }}
            <button
              type="button"
              class={`tag-cloud-item ${selectedGenre === key ? 'active' : ''}`}
              style={`--tag-weight: ${weight}`}
              aria-pressed={selectedGenre === key}
              on:click={() => toggleGenreFilter(key)}
            >
              <span class="tag-label">{label}</span>
              <span class="tag-count">{count}</span>
            </button>
          {/each}
        </div>
      </section>
    {/if}

    {#if !hasFilteredMetrics}
      <section class="empty-state">
        <p>No metrics match the current filters. Adjust the filters to explore more stories.</p>
      </section>
    {:else}
      {#each filteredSections as section}
        <section class="metric-section">
          <header class="section-heading">
            <h2>{section.name}</h2>
          </header>
          <div class="metric-grid">
            {#each section.metrics as metric}
              <article class="metric-card">
                <header class="metric-header">
                  <div class="metric-meta">
                    <div class="metric-title">
                      <h3>{metric.label}</h3>
                      {#if metric.description}
                        <button
                          type="button"
                          class="info-button"
                          aria-label={`What is ${metric.label}?`}
                          title={metric.description}
                        >
                          ⓘ
                        </button>
                      {/if}
                    </div>
                    {#if metric.description}
                      <p>{metric.description}</p>
                    {/if}
                  </div>
                  <div class="metric-guidance">
                    <span>{guidanceText(metric)}</span>
                    {#if metric.priority}
                      <span class="priority-badge" title="This metric is highlighted in the priority filter">Priority</span>
                    {/if}
                  </div>
                </header>
                <div class="story-pair">
                  {#if metric.best}
                    {@const trendBadge = getTrendBadge(metric, metric.best.trend_change)}
                    {@const sparkline = buildSparkline(metric.best.trend_samples)}
                    {@const bestGenres = explodeGenreTags(metric.best.genre_tags)}
                    <article class={`story-card positive ${entryFilteredOut(metric.best) ? 'filtered' : ''}`}>
                      <span class="story-tag positive">Recommended</span>
                      <div class="story-overview">
                        <div class={`story-cover ${metric.best.cover_image_url ? 'has-cover' : ''}`}>
                          {#if metric.best.cover_image_url}
                            <img
                              src={metric.best.cover_image_url}
                              alt={`Cover art for ${metric.best.title}`}
                              loading="lazy"
                            />
                          {:else}
                            <span class="cover-fallback">{metric.best.title.slice(0, 1)}</span>
                          {/if}
                        </div>
                        <div class="story-summary">
                          <a class="story-title" href={`/story/${metric.best.story_id}`}>{metric.best.title}</a>
                          <div class="story-meta">
                            <span>{formatStatus(metric.best.status)}</span>
                            <span>{metric.best.chapter_count} chapters</span>
                            {#if metric.best.completed_at}
                              <span>Completed {formatDate(metric.best.completed_at)}</span>
                            {/if}
                            {#if metric.best.last_activity_at}
                              <span>Updated {formatRelativeTime(metric.best.last_activity_at)}</span>
                            {/if}
                          </div>
                          {#if bestGenres.length}
                            <div class="story-genres">
                              {#each bestGenres as genre}
                                {@const label = normalizeGenreLabel(genre)}
                                {@const key = genreKey(genre)}
                                {#if label}
                                  <button
                                    type="button"
                                    class={`story-genre ${selectedGenre === key ? 'active' : ''}`}
                                    aria-pressed={selectedGenre === key}
                                    on:click={() => toggleGenreFilter(label)}
                                    title={`Show stories tagged ${label}`}
                                  >
                                    {label}
                                  </button>
                                {/if}
                              {/each}
                            </div>
                          {/if}
                          {#if metric.best.style_authors?.length || metric.best.tone || metric.best.narrative_perspective}
                            <div class="story-context">
                              {#if metric.best.style_authors?.length}
                                <span>Inspired by {metric.best.style_authors.join(', ')}</span>
                              {/if}
                              {#if metric.best.tone}
                                <span>Tone: {formatStatus(metric.best.tone)}</span>
                              {/if}
                              {#if metric.best.narrative_perspective}
                                <span>Perspective: {formatNarrativePerspective(metric.best.narrative_perspective)}</span>
                              {/if}
                            </div>
                          {/if}
                        </div>
                      </div>
                      {#if metric.best.premise}
                        <p class="story-premise">{previewText(metric.best.premise)}</p>
                      {/if}
                      <div class="story-stats">
                        <div class="story-value-group">
                          <span class="story-value">{formatDisplayValue(metric, metric.best)}</span>
                          <span class="story-value-label">{metric.label}</span>
                        </div>
                        <div class="trend-block">
                          {#if trendBadge}
                            <span class={`trend-badge ${trendBadge.direction}`}>
                              {trendBadge.label}
                              <small>{metricTrendContext(metric)}</small>
                            </span>
                          {/if}
                          {#if sparkline}
                            <div class="sparkline" aria-hidden="true">
                              <svg
                                viewBox={`0 0 ${sparkline.width} ${sparkline.height}`}
                                preserveAspectRatio="none"
                              >
                                <path d={sparkline.path} />
                              </svg>
                            </div>
                            <span class="sparkline-range">
                              {formatNumber(metric, sparkline.min)} – {formatNumber(metric, sparkline.max)}
                            </span>
                          {/if}
                        </div>
                      </div>
                      <div class="story-actions">
                        <a class="story-action primary" href={`/story/${metric.best.story_id}`}>Open story</a>
                        <a class="story-action secondary" href={chapterLink(metric.best)}>Latest chapter</a>
                        <button
                          class="story-action tertiary"
                          type="button"
                          on:click|preventDefault={() => queueChapter(metric.best)}
                          disabled={!canQueue(metric.best) || queueing[metric.best.story_id]}
                        >
                          {queueing[metric.best.story_id] ? 'Queuing…' : 'Queue chapter'}
                        </button>
                        <a class="story-action secondary" href={analyticsLink(metric.best)}>View analytics</a>
                      </div>
                      {#if queueFeedback[metric.best.story_id]}
                        <p class={`action-feedback ${queueFeedback[metric.best.story_id]?.type}`}>
                          {queueFeedback[metric.best.story_id]?.message}
                        </p>
                      {/if}
                    </article>
                  {:else}
                    <div class="story-card empty">
                      <span>No recommended story yet.</span>
                    </div>
                  {/if}

                  {#if metric.worst}
                    {@const trendBadge = getTrendBadge(metric, metric.worst.trend_change)}
                    {@const sparkline = buildSparkline(metric.worst.trend_samples)}
                    {@const worstGenres = explodeGenreTags(metric.worst.genre_tags)}
                    <article class={`story-card negative ${entryFilteredOut(metric.worst) ? 'filtered' : ''}`}>
                      <span class="story-tag negative">Discouraged</span>
                      <div class="story-overview">
                        <div class={`story-cover ${metric.worst.cover_image_url ? 'has-cover' : ''}`}>
                          {#if metric.worst.cover_image_url}
                            <img
                              src={metric.worst.cover_image_url}
                              alt={`Cover art for ${metric.worst.title}`}
                              loading="lazy"
                            />
                          {:else}
                            <span class="cover-fallback">{metric.worst.title.slice(0, 1)}</span>
                          {/if}
                        </div>
                        <div class="story-summary">
                          <a class="story-title" href={`/story/${metric.worst.story_id}`}>{metric.worst.title}</a>
                          <div class="story-meta">
                            <span>{formatStatus(metric.worst.status)}</span>
                            <span>{metric.worst.chapter_count} chapters</span>
                            {#if metric.worst.completed_at}
                              <span>Completed {formatDate(metric.worst.completed_at)}</span>
                            {/if}
                            {#if metric.worst.last_activity_at}
                              <span>Updated {formatRelativeTime(metric.worst.last_activity_at)}</span>
                            {/if}
                          </div>
                          {#if worstGenres.length}
                            <div class="story-genres">
                              {#each worstGenres as genre}
                                {@const label = normalizeGenreLabel(genre)}
                                {@const key = genreKey(genre)}
                                {#if label}
                                  <button
                                    type="button"
                                    class={`story-genre ${selectedGenre === key ? 'active' : ''}`}
                                    aria-pressed={selectedGenre === key}
                                    on:click={() => toggleGenreFilter(label)}
                                    title={`Show stories tagged ${label}`}
                                  >
                                    {label}
                                  </button>
                                {/if}
                              {/each}
                            </div>
                          {/if}
                          {#if metric.worst.style_authors?.length || metric.worst.tone || metric.worst.narrative_perspective}
                            <div class="story-context">
                              {#if metric.worst.style_authors?.length}
                                <span>Inspired by {metric.worst.style_authors.join(', ')}</span>
                              {/if}
                              {#if metric.worst.tone}
                                <span>Tone: {formatStatus(metric.worst.tone)}</span>
                              {/if}
                              {#if metric.worst.narrative_perspective}
                                <span>Perspective: {formatNarrativePerspective(metric.worst.narrative_perspective)}</span>
                              {/if}
                            </div>
                          {/if}
                        </div>
                      </div>
                      {#if metric.worst.premise}
                        <p class="story-premise">{previewText(metric.worst.premise)}</p>
                      {/if}
                      <div class="story-stats">
                        <div class="story-value-group">
                          <span class="story-value">{formatDisplayValue(metric, metric.worst)}</span>
                          <span class="story-value-label">{metric.label}</span>
                        </div>
                        <div class="trend-block">
                          {#if trendBadge}
                            <span class={`trend-badge ${trendBadge.direction}`}>
                              {trendBadge.label}
                              <small>{metricTrendContext(metric)}</small>
                            </span>
                          {/if}
                          {#if sparkline}
                            <div class="sparkline" aria-hidden="true">
                              <svg
                                viewBox={`0 0 ${sparkline.width} ${sparkline.height}`}
                                preserveAspectRatio="none"
                              >
                                <path d={sparkline.path} />
                              </svg>
                            </div>
                            <span class="sparkline-range">
                              {formatNumber(metric, sparkline.min)} – {formatNumber(metric, sparkline.max)}
                            </span>
                          {/if}
                        </div>
                      </div>
                      <div class="story-actions">
                        <a class="story-action primary" href={`/story/${metric.worst.story_id}`}>Open story</a>
                        <a class="story-action secondary" href={chapterLink(metric.worst)}>Latest chapter</a>
                        <button
                          class="story-action tertiary"
                          type="button"
                          on:click|preventDefault={() => queueChapter(metric.worst)}
                          disabled={!canQueue(metric.worst) || queueing[metric.worst.story_id]}
                        >
                          {queueing[metric.worst.story_id] ? 'Queuing…' : 'Queue chapter'}
                        </button>
                        <a class="story-action secondary" href={analyticsLink(metric.worst)}>View analytics</a>
                      </div>
                      {#if queueFeedback[metric.worst.story_id]}
                        <p class={`action-feedback ${queueFeedback[metric.worst.story_id]?.type}`}>
                          {queueFeedback[metric.worst.story_id]?.message}
                        </p>
                      {/if}
                    </article>
                  {:else}
                    <div class="story-card empty">
                      <span>No discouraged story yet.</span>
                    </div>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        </section>
      {/each}
    {/if}
  {/if}
</div>

<style>
  .recommendations-page {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .page-header {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .page-header h1 {
    font-size: clamp(2rem, 3vw, 3rem);
    margin: 0;
    color: #f8fafc;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .page-header p {
    margin: 0 auto;
    max-width: 60ch;
    color: rgba(226, 232, 240, 0.8);
    line-height: 1.6;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.5rem;
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.18);
  }

  .tag-cloud {
    margin-top: 1.5rem;
    padding: 1.25rem 1.5rem;
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.18);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .tag-cloud-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .tag-cloud-title {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .tag-cloud-title h2 {
    margin: 0;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(226, 232, 240, 0.85);
  }

  .active-tag-label {
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.85);
  }

  .active-tag-label strong {
    color: #f8fafc;
  }

  .clear-tags {
    border: none;
    background: rgba(148, 163, 184, 0.12);
    color: #f8fafc;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .clear-tags:hover {
    background: rgba(59, 130, 246, 0.3);
    color: #e0f2fe;
  }

  .tag-cloud-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .tag-cloud-item {
    border: none;
    border-radius: 999px;
    padding: 0.45rem 0.9rem;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(59, 130, 246, 0.14);
    color: #bfdbfe;
    cursor: pointer;
    font-size: calc(0.85rem * var(--tag-weight));
    line-height: 1;
    transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease;
  }

  .tag-cloud-item.all {
    background: rgba(148, 163, 184, 0.16);
    color: rgba(226, 232, 240, 0.9);
  }

  .tag-cloud-item .tag-count {
    font-size: 0.7em;
    opacity: 0.7;
  }

  .tag-cloud-item:hover,
  .tag-cloud-item:focus-visible {
    transform: translateY(-2px);
    background: rgba(59, 130, 246, 0.28);
    color: #e0f2fe;
  }

  .tag-cloud-item.active {
    background: rgba(56, 189, 248, 0.4);
    color: #f8fafc;
    box-shadow: 0 8px 18px rgba(14, 165, 233, 0.25);
  }

  .control-group {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .control-group label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.9rem;
    color: rgba(226, 232, 240, 0.85);
  }

  .control-group select {
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.4);
    background: rgba(2, 6, 23, 0.85);
    color: #f8fafc;
  }

  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: rgba(226, 232, 240, 0.85);
  }

  .toggle input[type='checkbox'] {
    width: 1.25rem;
    height: 1.25rem;
  }

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 4rem 0;
    border-radius: 24px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.15);
  }

  .empty-state p {
    margin: 0;
    color: rgba(226, 232, 240, 0.8);
    font-size: 1.05rem;
  }

  .metric-section {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .section-heading h2 {
    margin: 0;
    font-size: 1.4rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #38bdf8;
  }

  .metric-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card {
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.7));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 24px;
    padding: 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    box-shadow: 0 25px 45px rgba(15, 23, 42, 0.45);
  }

  .metric-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .metric-meta {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .metric-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .metric-meta h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #f8fafc;
  }

  .metric-meta p {
    margin: 0;
    color: rgba(226, 232, 240, 0.75);
    line-height: 1.5;
  }

  .info-button {
    border: none;
    background: rgba(59, 130, 246, 0.2);
    color: #38bdf8;
    border-radius: 999px;
    width: 1.5rem;
    height: 1.5rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    cursor: help;
  }

  .metric-guidance {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.85);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .priority-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    background: rgba(250, 204, 21, 0.16);
    color: #facc15;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
  }

  .story-pair {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 1.5rem;
  }

  .story-pair .story-card + .story-card {
    position: relative;
  }

  .story-pair .story-card + .story-card::before {
    content: '';
    position: absolute;
    top: -0.75rem;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      rgba(148, 163, 184, 0),
      rgba(148, 163, 184, 0.3),
      rgba(148, 163, 184, 0)
    );
  }

  .story-card {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.4rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.1);
    background: rgba(2, 6, 23, 0.6);
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .story-card:hover {
    transform: translateY(-4px);
    border-color: rgba(59, 130, 246, 0.35);
    box-shadow: 0 18px 30px rgba(30, 64, 175, 0.35);
  }

  .story-card.positive {
    border-color: rgba(34, 197, 94, 0.4);
  }

  .story-card.negative {
    border-color: rgba(239, 68, 68, 0.4);
  }

  .story-card.filtered {
    opacity: 0.5;
  }

  .story-card.empty {
    justify-content: center;
    align-items: center;
    text-align: center;
    color: rgba(148, 163, 184, 0.8);
    border-style: dashed;
  }

  .story-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.15);
    color: #38bdf8;
    width: fit-content;
  }

  .story-tag.positive {
    background: rgba(34, 197, 94, 0.18);
    color: #4ade80;
  }

  .story-tag.negative {
    background: rgba(239, 68, 68, 0.18);
    color: #fca5a5;
  }

  .story-overview {
    display: flex;
    gap: 1rem;
  }

  .story-cover {
    width: 96px;
    height: 128px;
    border-radius: 12px;
    overflow: hidden;
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(148, 163, 184, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .story-cover img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .story-cover .cover-fallback {
    font-size: 2rem;
    font-weight: 600;
    color: rgba(226, 232, 240, 0.8);
  }

  .story-summary {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .story-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #f8fafc;
  }

  .story-title:hover {
    text-decoration: underline;
  }

  .story-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 0.75rem;
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.9);
    letter-spacing: 0.04em;
  }

  .story-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .story-genres .story-genre {
    padding: 0.2rem 0.5rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.12);
    color: #93c5fd;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    border: none;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
  }

  .story-genres .story-genre:hover,
  .story-genres .story-genre:focus-visible {
    background: rgba(59, 130, 246, 0.25);
    color: #e0f2fe;
    transform: translateY(-1px);
  }

  .story-genres .story-genre.active {
    background: rgba(14, 165, 233, 0.35);
    color: #f8fafc;
    box-shadow: 0 6px 14px rgba(14, 165, 233, 0.25);
  }

  .story-context {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
    font-size: 0.8rem;
    color: rgba(148, 163, 184, 0.85);
  }

  .story-premise {
    margin: 0;
    color: rgba(226, 232, 240, 0.78);
    line-height: 1.5;
    font-size: 0.95rem;
  }

  .story-stats {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
  }

  .story-value-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .story-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.08em;
    color: #fbbf24;
  }

  .story-card.positive .story-value {
    color: #4ade80;
  }

  .story-card.negative .story-value {
    color: #f87171;
  }

  .story-value-label {
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.8);
  }

  .trend-block {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-end;
    min-width: 0;
  }

  .trend-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: rgba(59, 130, 246, 0.18);
    color: #38bdf8;
  }

  .trend-badge.positive {
    background: rgba(34, 197, 94, 0.2);
    color: #4ade80;
  }

  .trend-badge.negative {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
  }

  .trend-badge small {
    font-size: 0.65rem;
    letter-spacing: normal;
    text-transform: none;
    color: rgba(226, 232, 240, 0.75);
  }

  .sparkline {
    width: 120px;
    height: 40px;
  }

  .sparkline svg {
    width: 100%;
    height: 100%;
  }

  .sparkline path {
    fill: none;
    stroke: rgba(59, 130, 246, 0.8);
    stroke-width: 2;
  }

  .sparkline-range {
    font-size: 0.75rem;
    color: rgba(148, 163, 184, 0.85);
  }

  .story-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .story-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.45rem 0.85rem;
    border-radius: 999px;
    font-size: 0.85rem;
    border: 1px solid rgba(59, 130, 246, 0.35);
    background: rgba(15, 23, 42, 0.6);
    color: #93c5fd;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .story-action.primary {
    background: rgba(59, 130, 246, 0.3);
    color: #f8fafc;
    border-color: rgba(59, 130, 246, 0.5);
  }

  .story-action.tertiary {
    border-style: dashed;
  }

  .story-action:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .story-action:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(30, 64, 175, 0.35);
  }

  .action-feedback {
    margin: 0;
    font-size: 0.8rem;
    padding: 0.4rem 0.6rem;
    border-radius: 8px;
    background: rgba(59, 130, 246, 0.12);
    color: #93c5fd;
    width: fit-content;
  }

  .action-feedback.success {
    background: rgba(34, 197, 94, 0.18);
    color: #4ade80;
  }

  .action-feedback.error {
    background: rgba(239, 68, 68, 0.18);
    color: #fca5a5;
  }

  @media (max-width: 960px) {
    .story-pair {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .controls {
      flex-direction: column;
      align-items: stretch;
    }

    .trend-block {
      align-items: flex-start;
    }
  }
</style>
