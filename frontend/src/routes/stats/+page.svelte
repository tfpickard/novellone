<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;
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

  <section class="activity">
    <h2>Recent Activity</h2>
    <ul>
      {#each data.stats.recent_activity as item}
        <li>
          <div>
            <strong>Chapter {item.chapter_number}</strong>
            <span>{new Date(item.created_at).toLocaleString()}</span>
          </div>
          <p>{item.content.slice(0, 160)}...</p>
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
</style>
