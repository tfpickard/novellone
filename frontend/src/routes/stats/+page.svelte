<script lang="ts">
  import type { PageData } from './$types';
  import { queueMetaRefresh, UnauthorizedError } from '$lib/api';

  export let data: PageData;

  const chapterLink = (item: PageData['stats']['recent_activity'][number]) =>
    `/story/${item.story_id}#chapter-${item.chapter_number}`;

  const preview = (text: string, limit = 160) => {
    if (!text) return '';
    const normalised = text.replace(/\s+/g, ' ').trim();
    if (normalised.length <= limit) {
      return normalised;
    }
    return `${normalised.slice(0, limit - 1).trimEnd()}…`;
  };

  const formatCohesion = (value: number | null | undefined) =>
    typeof value === 'number' ? value.toFixed(2) : '0.00';

  const metaRuns = data.meta?.runs ?? [];
  const metaSummary = data.meta?.summary ?? {};
  const metaRuntime = data.meta?.runtime ?? {};
  const summaryEntries = Object.entries(metaSummary);

  const formatDuration = (value: number | null | undefined) =>
    typeof value === 'number' ? `${value.toFixed(1)} ms` : '—';

  const formatPercent = (value: number | null | undefined) =>
    typeof value === 'number' ? `${(value * 100).toFixed(0)}%` : '—';

  const formatDate = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : '—';

  let refreshPending = false;
  let refreshMessage: string | null = null;
  let refreshError: string | null = null;

  const triggerFullRefresh = async () => {
    refreshPending = true;
    refreshMessage = null;
    refreshError = null;
    try {
      await queueMetaRefresh({ full_rebuild: true });
      refreshMessage = 'Queued a full meta-analysis refresh.';
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        refreshError = 'Admin access required to queue meta-analysis jobs.';
      } else if (error instanceof Error) {
        refreshError = error.message;
      } else {
        refreshError = 'Failed to queue refresh.';
      }
    } finally {
      refreshPending = false;
    }
  };
</script>

<div class="page-container stats-page">
  <header>
    <h1>System Statistics</h1>
    <p>Monitoring the health of the autonomous story engine.</p>
  </header>

  <section class="summary">
    <div>
      <span>Total Stories</span>
      <strong>{data.stats.total_stories}</strong>
    </div>
    <div>
      <span>Total Chapters</span>
      <strong>{data.stats.total_chapters}</strong>
    </div>
    <div>
      <span>Active</span>
      <strong>{data.stats.active_stories}</strong>
    </div>
    <div>
      <span>Completed</span>
      <strong>{data.stats.completed_stories}</strong>
    </div>
    <div>
      <span>Average Chapters</span>
      <strong>{data.stats.average_chapters_per_story.toFixed(2)}</strong>
    </div>
    <div>
      <span>Total Tokens</span>
      <strong>{data.stats.total_tokens_used.toLocaleString()}</strong>
    </div>
  </section>

  {#if data.stats.text_statistics && data.stats.text_statistics.total_word_count > 0}
    <section class="text-stats-summary">
      <h2>Text Statistics</h2>
      <div class="text-stats-grid">
        <div class="text-stat-card">
          <span>Total Words</span>
          <strong>{data.stats.text_statistics.total_word_count.toLocaleString()}</strong>
        </div>
        <div class="text-stat-card">
          <span>Avg Words/Chapter</span>
          <strong>{data.stats.text_statistics.avg_words_per_chapter.toFixed(0)}</strong>
        </div>
        <div class="text-stat-card">
          <span>Avg Word Length</span>
          <strong>{data.stats.text_statistics.avg_word_length.toFixed(2)} chars</strong>
        </div>
        <div class="text-stat-card">
          <span>Avg Sentence Length</span>
          <strong>{data.stats.text_statistics.avg_sentence_length.toFixed(1)} words</strong>
        </div>
        <div class="text-stat-card">
          <span>Unique Words</span>
          <strong>{data.stats.text_statistics.total_unique_words.toLocaleString()}</strong>
        </div>
        <div class="text-stat-card">
          <span>Lexical Diversity</span>
          <strong>{(data.stats.text_statistics.overall_lexical_diversity * 100).toFixed(1)}%</strong>
        </div>
      </div>
    </section>
  {/if}

  <section class="chaos-summary">
    <h2>Average Chaos Parameters</h2>
    <div class="chaos-grid">
      <div class="chaos-stat" style="--color: #f59e0b;">
        <span>Absurdity</span>
        <strong>{data.stats.average_absurdity?.toFixed(3) ?? '0.000'}</strong>
        <div class="chaos-bar">
          <div class="chaos-bar-fill" style="width: {((data.stats.average_absurdity ?? 0) * 100).toFixed(0)}%; background: #f59e0b;"></div>
        </div>
      </div>
      <div class="chaos-stat" style="--color: #8b5cf6;">
        <span>Surrealism</span>
        <strong>{data.stats.average_surrealism?.toFixed(3) ?? '0.000'}</strong>
        <div class="chaos-bar">
          <div class="chaos-bar-fill" style="width: {((data.stats.average_surrealism ?? 0) * 100).toFixed(0)}%; background: #8b5cf6;"></div>
        </div>
      </div>
      <div class="chaos-stat" style="--color: #ec4899;">
        <span>Ridiculousness</span>
        <strong>{data.stats.average_ridiculousness?.toFixed(3) ?? '0.000'}</strong>
        <div class="chaos-bar">
          <div class="chaos-bar-fill" style="width: {((data.stats.average_ridiculousness ?? 0) * 100).toFixed(0)}%; background: #ec4899;"></div>
        </div>
      </div>
      <div class="chaos-stat" style="--color: #ef4444;">
        <span>Insanity</span>
        <strong>{data.stats.average_insanity?.toFixed(3) ?? '0.000'}</strong>
        <div class="chaos-bar">
          <div class="chaos-bar-fill" style="width: {((data.stats.average_insanity ?? 0) * 100).toFixed(0)}%; background: #ef4444;"></div>
        </div>
      </div>
    </div>
  </section>

  <section class="activity">
    <h2>Recent Activity</h2>
    <ul>
      {#each data.stats.recent_activity as item}
        <li>
          <a class="activity-link" href={chapterLink(item)}>
            <div>
              <strong>Chapter {item.chapter_number}</strong>
              <span>{new Date(item.created_at).toLocaleString()}</span>
            </div>
            <p>{preview(item.content)}</p>
          </a>
        </li>
      {/each}
    </ul>
  </section>

  {#if data.universe}
    <section class="universe-intel">
      <div class="section-heading">
        <h2>Shared Universe Intelligence</h2>
        <p>Automatically detected clusters, recurring characters, and dominant motifs.</p>
      </div>

      {#if data.universe.clusters.length > 0}
        <div class="cluster-grid">
          {#each data.universe.clusters as cluster}
            <article class="cluster-card">
              <header>
                <h3>{cluster.label ?? 'Untitled Cluster'}</h3>
                <div class="cluster-meta">
                  <span><strong>{cluster.size}</strong> stories</span>
                  <span>Cohesion <strong>{formatCohesion(cluster.cohesion)}</strong></span>
                </div>
              </header>
              {#if cluster.top_entities.length > 0}
                <div class="cluster-section">
                  <h4>Key Characters</h4>
                  <div class="chip-row">
                    {#each cluster.top_entities as entity}
                      <span class="chip">{entity}</span>
                    {/each}
                  </div>
                </div>
              {/if}
              {#if cluster.top_themes.length > 0}
                <div class="cluster-section">
                  <h4>Shared Motifs</h4>
                  <div class="chip-row">
                    {#each cluster.top_themes as theme}
                      <span class="chip">{theme}</span>
                    {/each}
                  </div>
                </div>
              {/if}
            </article>
          {/each}
        </div>
      {:else}
        <p class="empty-state">No continuity clusters detected yet. Trigger a meta-analysis run once stories accumulate.</p>
      {/if}

      <div class="universe-aggregates">
        <div class="aggregate-card">
          <h3>Most Referenced Characters</h3>
          {#if data.universe.top_entities.length > 0}
            <ol>
              {#each data.universe.top_entities as entity}
                <li>
                  <div>
                    <strong>{entity.name}</strong>
                    <span>{entity.story_count} stories</span>
                  </div>
                  <span class="count">{entity.total_occurrences.toLocaleString()} mentions</span>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="empty-state">No recurring characters catalogued yet.</p>
          {/if}
        </div>
        <div class="aggregate-card">
          <h3>Dominant Themes</h3>
          {#if data.universe.top_themes.length > 0}
            <ol>
              {#each data.universe.top_themes as theme}
                <li>
                  <div>
                    <strong>{theme.name}</strong>
                  </div>
                  <span class="count">{theme.story_count} stories</span>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="empty-state">No shared motifs detected yet.</p>
          {/if}
        </div>
      </div>
    </section>
  {/if}

  <section class="meta-ops">
    <div class="section-heading">
      <h2>Meta-analysis Operations</h2>
      <p>Track extraction jobs, inspect metrics, and trigger manual refreshes.</p>
    </div>

    <div class="meta-actions">
      <button class="refresh-button" disabled={refreshPending} on:click={triggerFullRefresh}>
        {refreshPending ? 'Queuing…' : 'Queue Full Refresh'}
      </button>
      {#if refreshMessage}
        <span class="meta-status success">{refreshMessage}</span>
      {:else if refreshError}
        <span class="meta-status error">{refreshError}</span>
      {/if}
    </div>

    <div class="meta-runtime">
      <div>
        <span>Last continuity rebuild</span>
        <strong>{formatDate(metaRuntime.last_universe_refresh)}</strong>
      </div>
      <div>
        <span>Last full reanalysis</span>
        <strong>{formatDate(metaRuntime.last_full_refresh)}</strong>
      </div>
    </div>

    {#if summaryEntries.length}
      <div class="meta-summary-grid">
        {#each summaryEntries as [runType, info]}
          <article class="meta-summary-card">
            <header>
              <h3>{runType.replace('_', ' ')}</h3>
              <span class="meta-count">{info.total_runs} runs</span>
            </header>
            <dl>
              <div>
                <dt>Success Rate</dt>
                <dd>{formatPercent(info.success_rate)}</dd>
              </div>
              <div>
                <dt>Average Duration</dt>
                <dd>{formatDuration(info.avg_duration_ms)}</dd>
              </div>
              <div>
                <dt>Latest Status</dt>
                <dd>{info.latest_status}</dd>
              </div>
              <div>
                <dt>Last Finished</dt>
                <dd>{formatDate(info.latest_finished_at)}</dd>
              </div>
            </dl>
          </article>
        {/each}
      </div>
    {/if}

    <div class="meta-runs">
      <h3>Recent Runs</h3>
      {#if metaRuns.length}
        <div class="meta-table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Processed</th>
                <th>Duration</th>
                <th>Finished</th>
              </tr>
            </thead>
            <tbody>
              {#each metaRuns as run}
                <tr>
                  <td class="meta-run-type">{run.run_type.replace('_', ' ')}</td>
                  <td>
                    <span class={`status-chip ${run.status}`}>
                      {run.status}
                    </span>
                  </td>
                  <td>{run.processed_items.toLocaleString()}</td>
                  <td>{formatDuration(run.duration_ms)}</td>
                  <td>{formatDate(run.finished_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="empty-state">No meta-analysis runs have been recorded yet.</p>
      {/if}
    </div>
  </section>
</div>

<style>
  .stats-page header {
    margin-bottom: 2rem;
  }

  .stats-page h1 {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.5rem;
    margin: 0 0 0.5rem;
  }

  .summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
  }

  .summary div {
    background: rgba(15, 23, 42, 0.7);
    padding: 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    text-align: center;
  }

  .summary span {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin-bottom: 0.5rem;
  }

  .summary strong {
    font-size: 1.75rem;
    color: #f97316;
  }

  .activity ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .activity li {
    background: rgba(2, 6, 23, 0.6);
    border-radius: 18px;
    padding: 1.5rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .activity a {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    color: inherit;
    text-decoration: none;
  }

  .activity a:hover strong {
    text-decoration: underline;
  }

  .activity strong {
    color: #38bdf8;
  }

  .activity span {
    display: block;
    font-size: 0.8rem;
    opacity: 0.7;
  }

  .activity p {
    margin-top: 0.75rem;
    line-height: 1.6;
    opacity: 0.85;
  }

  .chaos-summary {
    margin-bottom: 3rem;
  }

  .chaos-summary h2 {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    color: #38bdf8;
  }

  .chaos-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .chaos-stat {
    background: rgba(15, 23, 42, 0.7);
    padding: 1.5rem;
    border-radius: 18px;
    border: 2px solid var(--color);
    text-align: center;
  }

  .chaos-stat span {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin-bottom: 0.5rem;
  }

  .chaos-stat strong {
    display: block;
    font-size: 1.75rem;
    color: var(--color);
    margin-bottom: 1rem;
  }

  .chaos-bar {
    background: rgba(255, 255, 255, 0.1);
    height: 8px;
    border-radius: 999px;
    overflow: hidden;
  }

  .chaos-bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
  }

  .text-stats-summary {
    margin-bottom: 3rem;
  }

  .text-stats-summary h2 {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    color: #38bdf8;
  }

  .text-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .text-stat-card {
    background: rgba(15, 23, 42, 0.7);
    padding: 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    text-align: center;
  }

  .text-stat-card span {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin-bottom: 0.5rem;
  }

  .text-stat-card strong {
    font-size: 1.75rem;
    color: #38bdf8;
  }

  .universe-intel {
    margin-bottom: 3rem;
  }

  .section-heading {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .section-heading h2 {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    color: #38bdf8;
    margin: 0;
  }

  .section-heading p {
    margin: 0;
    opacity: 0.7;
  }

  .cluster-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .cluster-card {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .cluster-card header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .cluster-card h3 {
    margin: 0;
    font-size: 1.2rem;
    color: #f97316;
  }

  .cluster-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
    opacity: 0.8;
  }

  .cluster-meta strong {
    color: #38bdf8;
    margin: 0 0.25rem 0 0;
  }

  .cluster-section h4 {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin: 0 0 0.5rem;
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .chip {
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 999px;
    padding: 0.25rem 0.75rem;
    font-size: 0.8rem;
  }

  .universe-aggregates {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .aggregate-card {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1.5rem;
  }

  .aggregate-card h3 {
    margin: 0 0 1rem;
    font-size: 1.1rem;
    color: #f97316;
  }

  .aggregate-card ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .aggregate-card li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    font-size: 0.9rem;
  }

  .aggregate-card li strong {
    color: #38bdf8;
  }

  .aggregate-card .count {
    opacity: 0.7;
    font-size: 0.8rem;
  }

  .meta-ops {
    margin: 3rem 0 6rem;
  }

  .meta-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .refresh-button {
    background: linear-gradient(135deg, #38bdf8, #0ea5e9);
    border: none;
    color: #0b1120;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    border-radius: 999px;
    cursor: pointer;
    transition: transform 0.2s ease, opacity 0.2s ease;
  }

  .refresh-button:disabled {
    opacity: 0.6;
    cursor: progress;
  }

  .refresh-button:not(:disabled):hover {
    transform: translateY(-2px);
  }

  .meta-status {
    font-size: 0.9rem;
    font-weight: 600;
  }

  .meta-status.success {
    color: #34d399;
  }

  .meta-status.error {
    color: #f87171;
  }

  .meta-runtime {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .meta-runtime div {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1rem 1.25rem;
  }

  .meta-runtime span {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin-bottom: 0.5rem;
  }

  .meta-runtime strong {
    font-size: 1.1rem;
    color: #38bdf8;
  }

  .meta-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2.5rem;
  }

  .meta-summary-card {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .meta-summary-card header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .meta-summary-card h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #f97316;
    text-transform: capitalize;
  }

  .meta-count {
    font-size: 0.8rem;
    opacity: 0.7;
  }

  .meta-summary-card dl {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin: 0;
  }

  .meta-summary-card dt {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.65;
  }

  .meta-summary-card dd {
    margin: 0.25rem 0 0;
    font-size: 1.1rem;
    font-weight: 600;
    color: #38bdf8;
  }

  .meta-runs {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .meta-runs h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #f97316;
  }

  .meta-table-wrapper {
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    overflow-x: auto;
    background: rgba(15, 23, 42, 0.6);
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  }

  th {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .meta-run-type {
    font-weight: 600;
    text-transform: capitalize;
  }

  .status-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .status-chip.success {
    background: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.4);
  }

  .status-chip.failed {
    background: rgba(248, 113, 113, 0.15);
    color: #f87171;
    border: 1px solid rgba(248, 113, 113, 0.4);
  }

  .empty-state {
    margin: 0;
    padding: 1.5rem;
    border-radius: 18px;
    border: 1px dashed rgba(148, 163, 184, 0.4);
    background: rgba(15, 23, 42, 0.5);
    text-align: center;
    font-size: 0.9rem;
    opacity: 0.75;
  }
</style>
