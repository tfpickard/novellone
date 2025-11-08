<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;

  type ConfigKey =
    | 'chapter_interval_seconds'
    | 'evaluation_interval_chapters'
    | 'quality_score_min'
    | 'max_chapters_per_story'
    | 'min_active_stories'
    | 'max_active_stories'
    | 'context_window_chapters';

  type ConfigItem = {
    key: ConfigKey;
    label: string;
    description: string;
    hint?: string;
  };

  const config = data.config as Record<ConfigKey, number | undefined> | undefined;

  const configItems: ConfigItem[] = [
    {
      key: 'chapter_interval_seconds',
      label: 'Chapter Interval',
      description: 'Time between automatic chapter generations for active stories.',
      hint: 'Lower values increase pacing but demand more resources.'
    },
    {
      key: 'evaluation_interval_chapters',
      label: 'Evaluation Interval',
      description: 'How frequently the evaluation agent reviews story quality.',
      hint: 'A smaller interval keeps stories on course but costs more tokens.'
    },
    {
      key: 'quality_score_min',
      label: 'Minimum Quality Score',
      description: 'Threshold required for a story to continue without intervention.',
      hint: 'Scores below this trigger escalation or termination workflows.'
    },
    {
      key: 'max_chapters_per_story',
      label: 'Max Chapters Per Story',
      description: 'Upper bound on the length of an autonomous run before forced completion.'
    },
    {
      key: 'min_active_stories',
      label: 'Minimum Active Stories',
      description: 'Floor for concurrently running stories maintained by the scheduler.'
    },
    {
      key: 'max_active_stories',
      label: 'Maximum Active Stories',
      description: 'Ceiling for simultaneous story generation jobs.'
    },
    {
      key: 'context_window_chapters',
      label: 'Context Window',
      description: 'Number of previous chapters retained when prompting the model.'
    }
  ];

  function formatValue(value: number | undefined): string {
    if (value === undefined || value === null) return '—';
    const maximumFractionDigits = Number.isInteger(value) ? 0 : 2;
    return value.toLocaleString(undefined, { maximumFractionDigits });
  }
</script>

<div class="page-container config-page">
  <header class="page-header">
    <h1>System Configuration</h1>
    <p>
      Reference values that guide how the autonomous story engine schedules new chapters,
      evaluates quality, and balances load across active narratives.
    </p>
  </header>

  <section class="config-grid">
    {#each configItems as item}
      <article class="config-card">
        <header>
          <h2>{item.label}</h2>
          <span>{item.key.replaceAll('_', ' ')}</span>
        </header>
        <div class="value">{formatValue(config?.[item.key])}</div>
        <p>{item.description}</p>
        {#if item.hint}
          <footer>{item.hint}</footer>
        {/if}
      </article>
    {/each}
  </section>

  <section class="config-footnotes">
    <h3>Operational Notes</h3>
    <ul>
      <li>
        Values originate from the backend service configuration and mirror the active runtime
        environment. Adjustments require updating the FastAPI service settings.
      </li>
      <li>
        Pair intervals thoughtfully&mdash;short chapter intervals with long evaluations can lead to
        quality dips before the system reacts.
      </li>
      <li>
        The context window determines how much history the model sees. Increasing it can improve
        coherence at the expense of additional tokens per request.
      </li>
    </ul>
  </section>
</div>

<style>
  .config-page {
    display: flex;
    flex-direction: column;
    gap: 3rem;
  }

  .page-header h1 {
    margin: 0 0 0.75rem;
    font-family: 'Orbitron', sans-serif;
    font-size: 2.5rem;
  }

  .page-header p {
    margin: 0;
    max-width: 760px;
    line-height: 1.6;
    opacity: 0.85;
  }

  .config-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  .config-card {
    background: rgba(15, 23, 42, 0.75);
    border-radius: 20px;
    padding: 1.75rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.35);
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 220px;
  }

  .config-card header {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .config-card h2 {
    margin: 0;
    font-size: 1.1rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .config-card span {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.6;
  }

  .config-card .value {
    font-size: 2.4rem;
    font-weight: 600;
    color: #38bdf8;
  }

  .config-card p {
    margin: 0;
    line-height: 1.6;
    opacity: 0.8;
  }

  .config-card footer {
    margin-top: auto;
    font-size: 0.8rem;
    line-height: 1.4;
    color: rgba(248, 250, 252, 0.75);
  }

  .config-footnotes {
    background: linear-gradient(135deg, rgba(30, 64, 175, 0.35), rgba(8, 47, 73, 0.35));
    border-radius: 24px;
    padding: 2rem;
    border: 1px solid rgba(59, 130, 246, 0.25);
    box-shadow: 0 18px 44px rgba(2, 6, 23, 0.45);
  }

  .config-footnotes h3 {
    margin: 0 0 1rem;
    font-size: 1.3rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .config-footnotes ul {
    margin: 0;
    padding-left: 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    line-height: 1.6;
    opacity: 0.85;
  }

  @media (max-width: 720px) {
    .config-card {
      min-height: auto;
    }

    .config-card .value {
      font-size: 2rem;
    }
  }
</style>
