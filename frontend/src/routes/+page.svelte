<script lang="ts">
  import type { PageData } from './$types';
  import { createThemeAction, type StoryTheme } from '$lib/theme';

  export let data: PageData;

  const stories = data.stories.items ?? [];
</script>

<div class="page-container">
  <header class="hero">
    <div>
      <h1>Eternal Stories</h1>
      <p>Autonomous science fiction tales evolving in real time.</p>
    </div>
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
        <strong>{data.stories.total ?? stories.length}</strong>
      </div>
    </div>
  </header>

  <section class="grid">
    {#each stories as story}
      <a class="story-card" href={`/story/${story.id}`} use:createThemeAction={story.theme_json as StoryTheme}>
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
        <p class="premise">{story.premise}</p>
        <footer>
          <span>{story.chapter_count} chapters</span>
          <span>{story.status === 'active' ? 'Live' : 'Completed'}</span>
        </footer>
      </a>
    {/each}
  </section>
</div>

<style>
  .hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    margin-bottom: 2.5rem;
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

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.5rem;
  }

  .story-card {
    background: var(--card-background, rgba(15, 23, 42, 0.9));
    border-radius: var(--border-radius, 16px);
    padding: 1.75rem;
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.2));
    box-shadow: var(--shadow-style, 0 12px 24px rgba(15, 23, 42, 0.35));
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    transition: transform var(--animation-speed, 0.3s) ease, box-shadow var(--animation-speed, 0.3s) ease;
    color: var(--text_color, #e2e8f0);
    background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.04), transparent 40%);
  }

  .story-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 20px 40px rgba(14, 165, 233, 0.25);
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

  @media (max-width: 768px) {
    .hero {
      flex-direction: column;
      align-items: flex-start;
    }

    .stats {
      width: 100%;
    }
  }
</style>
