<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;

  type Metric = PageData['recommendations']['metrics'][number];
  type MetricEntry = NonNullable<Metric['best']>;

  const metrics: Metric[] = data.recommendations?.metrics ?? [];

  const formatStatus = (status: string) =>
    status ? status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()) : '';

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

  const formatDisplayValue = (metric: Metric, entry: MetricEntry | null) => {
    const base = formatValue(metric, entry);
    if (base === '—') return base;
    return metric.unit ? `${base}${metric.unit}` : base;
  };

  const guidanceText = (metric: Metric) =>
    metric.higher_is_better
      ? 'Higher values indicate stronger performance.'
      : 'Lower values indicate stronger performance.';

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
    {#each groupedEntries as section}
      <section class="metric-section">
        <header class="section-heading">
          <h2>{section.name}</h2>
        </header>
        <div class="metric-grid">
          {#each section.metrics as metric}
            <article class="metric-card">
              <header>
                <div class="metric-meta">
                  <h3>{metric.label}</h3>
                  {#if metric.description}
                    <p>{metric.description}</p>
                  {/if}
                </div>
                <span class="metric-guidance">{guidanceText(metric)}</span>
              </header>
              <div class="story-pair">
                {#if metric.best}
                  <a class="story-card positive" href={`/story/${metric.best.story_id}`}>
                    <span class="story-tag positive">Recommended</span>
                    <h4>{metric.best.title}</h4>
                    <div class="story-value">{formatDisplayValue(metric, metric.best)}</div>
                    <div class="story-meta">
                      <span>{formatStatus(metric.best.status)}</span>
                      <span>{metric.best.chapter_count} chapters</span>
                    </div>
                  </a>
                {:else}
                  <div class="story-card empty">
                    <span>No recommended story yet.</span>
                  </div>
                {/if}

                {#if metric.worst}
                  <a class="story-card negative" href={`/story/${metric.worst.story_id}`}>
                    <span class="story-tag negative">Discouraged</span>
                    <h4>{metric.worst.title}</h4>
                    <div class="story-value">{formatDisplayValue(metric, metric.worst)}</div>
                    <div class="story-meta">
                      <span>{formatStatus(metric.worst.status)}</span>
                      <span>{metric.worst.chapter_count} chapters</span>
                    </div>
                  </a>
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
    font-size: 1.5rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #38bdf8;
  }

  .metric-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .metric-card {
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.7));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 24px;
    padding: 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    box-shadow: 0 25px 45px rgba(15, 23, 42, 0.45);
  }

  .metric-card header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
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

  .metric-guidance {
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.8);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .story-pair {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .story-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1.25rem;
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

  .story-card h4 {
    margin: 0;
    font-size: 1.05rem;
    color: #f8fafc;
  }

  .story-card .story-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.08em;
    color: #fbbf24;
  }

  .story-card.positive {
    border-color: rgba(34, 197, 94, 0.4);
  }

  .story-card.positive .story-value {
    color: #4ade80;
  }

  .story-card.negative {
    border-color: rgba(239, 68, 68, 0.4);
  }

  .story-card.negative .story-value {
    color: #f87171;
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
  }

  .story-tag.positive {
    background: rgba(34, 197, 94, 0.18);
    color: #4ade80;
  }

  .story-tag.negative {
    background: rgba(239, 68, 68, 0.18);
    color: #fca5a5;
  }

  .story-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.25rem;
    font-size: 0.85rem;
    color: rgba(148, 163, 184, 0.9);
    letter-spacing: 0.04em;
  }

  @media (max-width: 720px) {
    .story-pair {
      grid-template-columns: 1fr;
    }

    .metric-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
