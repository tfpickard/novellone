<script lang="ts">
  import type { PageData } from './$types';

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
      <strong>{data.stats.total_tokens_used}</strong>
    </div>
  </section>

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
</style>
