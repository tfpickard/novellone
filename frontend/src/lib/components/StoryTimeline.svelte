<script lang="ts">
  import {
    getTopContentAxes,
    CONTENT_AXIS_METADATA,
    formatContentLevel
  } from '$lib/contentAxes';

  type TimelineChapter = {
    id: string;
    chapter_number: number;
    created_at: string;
    tokens_used?: number | null;
    generation_time_ms?: number | null;
    absurdity?: number | null;
    surrealism?: number | null;
    ridiculousness?: number | null;
    insanity?: number | null;
    content_levels?: Record<string, unknown>;
  };

  type TimelineEvaluation = {
    chapter_number: number;
    overall_score: number;
    coherence_score: number;
    novelty_score: number;
    engagement_score: number;
    pacing_score: number;
    issues?: string[] | null;
    evaluated_at: string;
  };

  export let chapters: TimelineChapter[] = [];
  export let evaluations: TimelineEvaluation[] = [];

  $: sortedChapters = [...chapters].sort(
    (left, right) => left.chapter_number - right.chapter_number
  );
  $: evaluationByChapter = new Map(
    evaluations.map((evaluation) => [evaluation.chapter_number, evaluation])
  );
  $: events = sortedChapters.map((chapter) => ({
    chapter,
    evaluation: evaluationByChapter.get(chapter.chapter_number),
    topAxes: getTopContentAxes(chapter.content_levels ?? null, 3)
  }));

  $: firstTimestamp = sortedChapters[0]?.created_at ?? null;
  $: maxTokens =
    events.reduce((max, event) => Math.max(max, event.chapter.tokens_used ?? 0), 1) || 1;

  function formatDate(value: string | null | undefined): string {
    if (!value) return 'Unknown';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function normalizedChaos(value: number | null | undefined): number {
    if (value === null || value === undefined || Number.isNaN(value)) return 0;
    const normalised = value / 2;
    return Math.min(Math.max(normalised, 0), 1);
  }

  function normalizedTokens(value: number | null | undefined): number {
    if (!value || value <= 0) return 0;
    return Math.min(Math.max(value / maxTokens, 0), 1);
  }

  function timeSinceStart(value: string | null | undefined): string {
    if (!value || !firstTimestamp) return '';
    const start = new Date(firstTimestamp).getTime();
    const current = new Date(value).getTime();
    if (Number.isNaN(start) || Number.isNaN(current)) return '';
    const diff = Math.max(current - start, 0);
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'at launch';
    if (minutes < 60) return `${minutes}m from start`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      const remaining = minutes % 60;
      return remaining ? `${hours}h ${remaining}m from start` : `${hours}h from start`;
    }
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return remainingHours ? `${days}d ${remainingHours}h from start` : `${days}d from start`;
  }

  function scoreColor(score: number): string {
    if (score >= 8.5) return 'var(--score-high, #34d399)';
    if (score >= 6.5) return 'var(--score-mid, #facc15)';
    return 'var(--score-low, #f97316)';
  }
</script>

<section class="timeline">
  <header>
    <h2>Story Timeline</h2>
    <p>
      Monitor how the narrative has unfolded across time. Each event highlights production pace,
      chaos fluctuations, and evaluation feedback when available.
    </p>
  </header>

  {#if !events.length}
    <p class="empty-state">No chapters yet. This story hasn’t started its journey.</p>
  {:else}
    <div class="timeline-grid">
      {#each events as event (event.chapter.id)}
        <article class="timeline-event">
          <div class="marker">
            <span>{event.chapter.chapter_number}</span>
          </div>
          <div class="content">
            <div class="heading">
              <h3>Chapter {event.chapter.chapter_number}</h3>
              <time datetime={event.chapter.created_at}>
                {formatDate(event.chapter.created_at)}
                <span>{timeSinceStart(event.chapter.created_at)}</span>
              </time>
            </div>

            <div class="metrics">
              <div class="metric tokens" style={`--progress:${normalizedTokens(event.chapter.tokens_used)}`}>
                <span>Tokens</span>
                <strong>{event.chapter.tokens_used ?? '—'}</strong>
              </div>

            <div class="metric chaos">
              <span>Chaos</span>
              <div class="chaos-bars">
                <div class="bar absurdity" title="Absurdity" style={`--value:${normalizedChaos(event.chapter.absurdity)}`}></div>
                <div class="bar surrealism" title="Surrealism" style={`--value:${normalizedChaos(event.chapter.surrealism)}`}></div>
                <div class="bar ridiculousness" title="Ridiculousness" style={`--value:${normalizedChaos(event.chapter.ridiculousness)}`}></div>
                <div class="bar insanity" title="Insanity" style={`--value:${normalizedChaos(event.chapter.insanity)}`}></div>
              </div>
            </div>

            {#if event.topAxes.length}
              <div class="metric content">
                <span>Content</span>
                <div class="content-pills">
                  {#each event.topAxes as axis (axis.key)}
                    {@const metadata = CONTENT_AXIS_METADATA[axis.key]}
                    {@const color = metadata?.color ?? '#475569'}
                    {@const softColor = color.startsWith('#') && color.length === 7 ? `${color}26` : color}
                    <span
                      class={`content-pill${metadata ? '' : ' content-pill--unknown'}`}
                      style={`--axis-color:${color}; --axis-color-soft:${softColor}`}
                    >
                      <span class="label">{metadata?.label ?? axis.key}</span>
                      <span class="value">{formatContentLevel(axis.value)}</span>
                    </span>
                  {/each}
                </div>
              </div>
            {/if}

            {#if event.evaluation}
              <div class="evaluation">
                <span>Quality</span>
                <strong style={`color:${scoreColor(event.evaluation.overall_score)}`}>
                    {event.evaluation.overall_score.toFixed(2)}
                  </strong>
                  <ul>
                    <li title="Coherence score">
                      <span>Co</span>
                      <span>{event.evaluation.coherence_score.toFixed(1)}</span>
                    </li>
                    <li title="Novelty score">
                      <span>No</span>
                      <span>{event.evaluation.novelty_score.toFixed(1)}</span>
                    </li>
                    <li title="Engagement score">
                      <span>En</span>
                      <span>{event.evaluation.engagement_score.toFixed(1)}</span>
                    </li>
                    <li title="Pacing score">
                      <span>Pa</span>
                      <span>{event.evaluation.pacing_score.toFixed(1)}</span>
                    </li>
                  </ul>
                </div>
              {/if}
            </div>

            {#if event.evaluation?.issues?.length}
              <details>
                <summary>Evaluation notes</summary>
                <ul>
                  {#each event.evaluation.issues as issue}
                    <li>{issue}</li>
                  {/each}
                </ul>
              </details>
            {/if}
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .timeline {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 24px;
    padding: 2rem;
  }

  header h2 {
    margin: 0 0 0.35rem;
    font-size: 1.5rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  header p {
    margin: 0;
    opacity: 0.75;
    line-height: 1.6;
  }

  .empty-state {
    margin: 0;
    padding: 2rem;
    background: rgba(15, 23, 42, 0.35);
    border-radius: 18px;
    text-align: center;
    opacity: 0.7;
  }

  .timeline-grid {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    padding-left: 1.5rem;
  }

  .timeline-grid::before {
    content: '';
    position: absolute;
    top: 0.5rem;
    bottom: 0.5rem;
    left: 0.5rem;
    width: 2px;
    background: linear-gradient(180deg, rgba(56, 189, 248, 0.6), rgba(129, 140, 248, 0.15));
  }

  .timeline-event {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
    position: relative;
  }

  .marker {
    position: relative;
    z-index: 1;
    flex-shrink: 0;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 50%;
    background: linear-gradient(135deg, #38bdf8, #6366f1);
    display: grid;
    place-items: center;
    font-weight: 700;
    color: #0b1120;
    box-shadow: 0 12px 24px rgba(56, 189, 248, 0.35);
  }

  .content {
    flex: 1;
    background: rgba(9, 13, 28, 0.75);
    border-radius: 18px;
    padding: 1.5rem;
    border: 1px solid rgba(56, 189, 248, 0.2);
    box-shadow: 0 10px 24px rgba(8, 24, 60, 0.35);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .heading {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .heading h3 {
    margin: 0;
    font-size: 1.2rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  time {
    display: flex;
    flex-direction: column;
    font-size: 0.85rem;
    opacity: 0.7;
  }

  time span {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .metrics {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .metric { 
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    background: rgba(15, 23, 42, 0.45);
    border-radius: 14px;
    padding: 0.85rem;
    border: 1px solid rgba(71, 85, 105, 0.5);
  }

  .metric span {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
  }

  .metric strong {
    font-size: 1.1rem;
  }

  .metric.content {
    gap: 0.6rem;
  }

  .content-pills {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .content-pill {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.6rem;
    border-radius: 10px;
    border: 1px solid var(--axis-color, rgba(148, 163, 184, 0.35));
    background: rgba(15, 23, 42, 0.55);
    font-size: 0.75rem;
    gap: 0.5rem;
  }

  .content-pill--unknown {
    border-style: dashed;
    opacity: 0.75;
  }

  .content-pill .label {
    opacity: 0.7;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .content-pill .value {
    font-weight: 600;
    color: var(--axis-color, #38bdf8);
  }

  .metric.tokens {
    position: relative;
    overflow: hidden;
  }

  .metric.tokens::after {
    content: '';
    position: absolute;
    inset: 0;
    transform: scaleX(var(--progress));
    transform-origin: left;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.35), rgba(96, 165, 250, 0.55));
    z-index: 0;
    border-radius: inherit;
  }

  .metric.tokens span,
  .metric.tokens strong {
    position: relative;
    z-index: 1;
  }

  .chaos-bars {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.4rem;
  }

  .chaos-bars .bar {
    position: relative;
    height: 48px;
    border-radius: 10px;
    background: rgba(30, 41, 59, 0.6);
    overflow: hidden;
  }

  .chaos-bars .bar::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: calc(min(var(--value, 0) * 100%, 100%));
    transition: height 0.3s ease;
  }

  .chaos-bars .bar.absurdity::after {
    background: linear-gradient(180deg, rgba(250, 204, 21, 0.8), rgba(217, 119, 6, 0.8));
  }

  .chaos-bars .bar.surrealism::after {
    background: linear-gradient(180deg, rgba(129, 140, 248, 0.8), rgba(107, 114, 128, 0.8));
  }

  .chaos-bars .bar.ridiculousness::after {
    background: linear-gradient(180deg, rgba(251, 191, 36, 0.8), rgba(244, 114, 182, 0.8));
  }

  .chaos-bars .bar.insanity::after {
    background: linear-gradient(180deg, rgba(96, 165, 250, 0.9), rgba(22, 78, 99, 0.9));
  }

  .evaluation {
    background: rgba(15, 118, 110, 0.2);
    border: 1px solid rgba(20, 184, 166, 0.4);
    border-radius: 14px;
    padding: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .evaluation ul {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.35rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .evaluation li {
    background: rgba(13, 148, 136, 0.25);
    border-radius: 10px;
    padding: 0.4rem 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    display: flex;
    justify-content: space-between;
  }

  details {
    background: rgba(15, 23, 42, 0.35);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    border: 1px dashed rgba(148, 163, 184, 0.35);
    font-size: 0.9rem;
  }

  details ul {
    margin: 0.75rem 0 0;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  @media (max-width: 720px) {
    .timeline {
      padding: 1.5rem;
    }

    .timeline-grid {
      padding-left: 1.25rem;
    }

    .marker {
      width: 1.5rem;
      height: 1.5rem;
      font-size: 0.8rem;
    }

    .heading {
      flex-direction: column;
      align-items: stretch;
    }

    .metrics {
      grid-template-columns: 1fr;
    }
  }
</style>

