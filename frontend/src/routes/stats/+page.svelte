<script lang="ts">
  import type { PageData } from './$types';
  import { CONTENT_AXIS_KEYS, CONTENT_AXIS_METADATA } from '$lib/contentAxes';

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

  const contentAxisSummaries = CONTENT_AXIS_KEYS.map((axis) => {
    const metadata = CONTENT_AXIS_METADATA[axis];
    const value = data.stats.average_content_levels?.[axis] ?? 0;
    return {
      key: axis,
      label: metadata.label,
      description: metadata.description,
      color: metadata.color,
      value,
      progress: Math.min(Math.max(value / 10, 0), 1)
    };
  });
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

  <section class="content-axis-summary">
    <h2>Content Intensity Averages</h2>
    <p class="content-axis-description">
      Long-term averages across all chapters give a quick sense of how strongly each thematic axis is
      appearing in the current catalogue.
    </p>
    <div class="content-axis-grid">
      {#each contentAxisSummaries as axis}
        <article
          class="content-axis-card"
          style={`--axis-color:${axis.color}; --axis-color-soft:${axis.color}33`}
        >
          <header>
            <h3>{axis.label}</h3>
            <p>{axis.description}</p>
          </header>
          <div class="content-axis-bar">
            <div class="bar-track">
              <div class="bar-fill" style={`--progress:${axis.progress}`}></div>
            </div>
            <span>{axis.value.toFixed(2)} / 10</span>
          </div>
        </article>
      {/each}
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

  .content-axis-summary {
    margin-bottom: 3rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 24px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .content-axis-summary h2 {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    margin: 0;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .content-axis-description {
    margin: 0;
    max-width: 720px;
    line-height: 1.6;
    opacity: 0.75;
  }

  .content-axis-grid {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  .content-axis-card {
    background: rgba(2, 6, 23, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 18px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .content-axis-card header h3 {
    margin: 0 0 0.35rem;
    font-size: 1rem;
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

  .content-axis-bar {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .content-axis-bar .bar-track {
    height: 6px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.1);
    overflow: hidden;
  }

  .content-axis-bar .bar-fill {
    height: 100%;
    border-radius: 999px;
    width: calc(var(--progress, 0) * 100%);
    background: linear-gradient(135deg, var(--axis-color), rgba(255, 255, 255, 0.2));
    transition: width 0.3s ease;
  }

  .content-axis-bar span {
    font-size: 0.85rem;
    font-weight: 600;
    opacity: 0.85;
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
