<script lang="ts">
  import {
    CONTENT_AXIS_KEYS,
    CONTENT_AXIS_METADATA,
    sanitizeContentAxisSettings,
    sanitizeContentLevels
  } from '$lib/contentAxes';
  import type { ContentAxisKey, ContentAxisSettingsMap } from '$lib/contentAxes';

  type StorySummary = {
    id: string;
    title: string;
    chapter_count: number;
    total_tokens?: number | null;
    absurdity_initial: number;
    surrealism_initial: number;
    ridiculousness_initial: number;
    insanity_initial: number;
    absurdity_increment: number;
    surrealism_increment: number;
    ridiculousness_increment: number;
    insanity_increment: number;
    created_at: string;
    completed_at?: string | null;
    content_settings?: Record<string, unknown>;
    content_axis_averages?: Record<string, unknown>;
  };

  type Chapter = {
    chapter_number: number;
    created_at: string;
    generation_time_ms?: number | null;
    content_levels?: Record<string, unknown>;
  };

  type Evaluation = {
    overall_score: number;
    pacing_score: number;
    engagement_score: number;
    evaluated_at: string;
  };

  export let story: StorySummary;
  export let chapters: Chapter[] = [];
  export let evaluations: Evaluation[] = [];

  const RADAR_SIZE = 200;
  const INNER_RADIUS = 40;
  const OUTER_RADIUS = 90;
  const axisKeys = CONTENT_AXIS_KEYS;

  function computeContentAverages(
    items: Chapter[]
  ): Partial<Record<ContentAxisKey, number>> {
    const totals: Partial<Record<ContentAxisKey, { total: number; count: number }>> = {};
    for (const chapter of items ?? []) {
      const levels = sanitizeContentLevels(chapter.content_levels);
      for (const [axis, value] of Object.entries(levels) as Array<[ContentAxisKey, number]>) {
        const entry = totals[axis] ?? { total: 0, count: 0 };
        entry.total += value;
        entry.count += 1;
        totals[axis] = entry;
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

  function chaosProjection(initial: number, increment: number, chaptersCount: number): number {
    const growth = increment * Math.max(chaptersCount - 1, 0);
    return initial + growth;
  }

  function average(values: number[]): number {
    if (!values.length) return 0;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function hoursBetween(start: string | null | undefined, end: string | null | undefined): number {
    if (!start || !end) return 0;
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    if (Number.isNaN(startTime) || Number.isNaN(endTime)) return 0;
    return Math.max((endTime - startTime) / 3_600_000, 0);
  }

  const orderedChapters = [...chapters].sort(
    (left, right) => left.chapter_number - right.chapter_number
  );
  const firstChapter = orderedChapters[0];
  const lastChapter = orderedChapters.length ? orderedChapters[orderedChapters.length - 1] : null;
  const avgGenerationTimeSec = average(
    orderedChapters
      .map((chapter) => (chapter.generation_time_ms ?? 0) / 1000)
      .filter((value) => value > 0)
  );
  const avgOverallScore = average(evaluations.map((evaluation) => evaluation.overall_score));
  const avgEngagement = average(evaluations.map((evaluation) => evaluation.engagement_score));
  const avgPacing = average(evaluations.map((evaluation) => evaluation.pacing_score));

  const chaosAbsurdity = chaosProjection(
    story.absurdity_initial,
    story.absurdity_increment,
    story.chapter_count
  );
  const chaosSurrealism = chaosProjection(
    story.surrealism_initial,
    story.surrealism_increment,
    story.chapter_count
  );
  const chaosRidiculousness = chaosProjection(
    story.ridiculousness_initial,
    story.ridiculousness_increment,
    story.chapter_count
  );
  const chaosInsanity = chaosProjection(
    story.insanity_initial,
    story.insanity_increment,
    story.chapter_count
  );

  $: contentAxisSettings = sanitizeContentAxisSettings(
    story.content_settings
  ) as ContentAxisSettingsMap;
  $: storedContentAverages = sanitizeContentLevels(story.content_axis_averages);
  $: derivedContentAverages = computeContentAverages(chapters);
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

  const elapsedHours = hoursBetween(firstChapter?.created_at, lastChapter?.created_at ?? story.completed_at ?? null);
  const chaptersPerHour = elapsedHours > 0 ? story.chapter_count / elapsedHours : story.chapter_count;
  const tokensPerChapter =
    story.chapter_count > 0 ? (story.total_tokens ?? 0) / story.chapter_count : story.total_tokens ?? 0;

  type MetricDefinition = {
    id: string;
    label: string;
    value: number;
    max: number;
    hint: string;
  };

  $: metrics = [
    {
      id: 'absurdity',
      label: 'Absurdity',
      value: chaosAbsurdity,
      max: 2.2,
      hint: 'Projected absurdity after current chapter count'
    },
    {
      id: 'surrealism',
      label: 'Surrealism',
      value: chaosSurrealism,
      max: 2.2,
      hint: 'Projected surrealism after current chapter count'
    },
    {
      id: 'ridiculousness',
      label: 'Ridiculousness',
      value: chaosRidiculousness,
      max: 2.2,
      hint: 'Projected ridiculousness after current chapter count'
    },
    {
      id: 'insanity',
      label: 'Insanity',
      value: chaosInsanity,
      max: 2.2,
      hint: 'Projected insanity after current chapter count'
    },
    {
      id: 'quality',
      label: 'Quality',
      value: avgOverallScore,
      max: 10,
      hint: 'Average evaluator overall score'
    },
    {
      id: 'momentum',
      label: 'Momentum',
      value: chaptersPerHour,
      max: 4,
      hint: 'Chapters produced per hour of story runtime'
    },
    {
      id: 'engagement',
      label: 'Engagement',
      value: avgEngagement,
      max: 10,
      hint: 'Average engagement score from evaluations'
    },
    {
      id: 'pacing',
      label: 'Pacing',
      value: avgPacing,
      max: 10,
      hint: 'Average pacing score from evaluations'
    },
    {
      id: 'token-density',
      label: 'Token Density',
      value: tokensPerChapter / 1000,
      max: 4,
      hint: 'Thousands of tokens per chapter on average'
    },
    {
      id: 'chapter-length',
      label: 'Chapter Length',
      value: avgGenerationTimeSec,
      max: 90,
      hint: 'Average generation time in seconds'
    }
  ] as MetricDefinition[];

  function normalise(value: number, max: number): number {
    if (!Number.isFinite(value) || max <= 0) return 0;
    return Math.min(Math.max(value / max, 0), 1);
  }

  $: polygonPoints = metrics
    .map((metric, index, array) => {
      const angle = (Math.PI * 2 * index) / array.length - Math.PI / 2;
      const normalised = normalise(metric.value, metric.max);
      const radius = INNER_RADIUS + normalised * (OUTER_RADIUS - INNER_RADIUS);
      const x = RADAR_SIZE / 2 + radius * Math.cos(angle);
      const y = RADAR_SIZE / 2 + radius * Math.sin(angle);
      return `${x},${y}`;
    })
    .join(' ');

  const rings = [1, 0.75, 0.5, 0.25];

  function ringPoints(ratio: number, total: number): string {
    const radius = INNER_RADIUS + ratio * (OUTER_RADIUS - INNER_RADIUS);
    return Array.from({ length: total }, (_, index) => {
      const angle = (Math.PI * 2 * index) / total - Math.PI / 2;
      const x = RADAR_SIZE / 2 + radius * Math.cos(angle);
      const y = RADAR_SIZE / 2 + radius * Math.sin(angle);
      return `${x},${y}`;
    }).join(' ');
  }
</script>

<section class="dna">
  <header>
    <h2>Story DNA</h2>
    <p>
      A fingerprint of this narrative’s temperament. Chaos projections blend with evaluator feedback
      to reveal the story’s personality at a glance.
    </p>
  </header>

  <div class="content">
    <figure>
      <svg viewBox={`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`} role="presentation">
        <defs>
          <radialGradient id="dna-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(56, 189, 248, 0.35)" />
            <stop offset="60%" stop-color="rgba(79, 70, 229, 0.2)" />
            <stop offset="100%" stop-color="rgba(15, 23, 42, 0)" />
          </radialGradient>
          <linearGradient id="dna-polygon" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85" />
            <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.75" />
          </linearGradient>
        </defs>

        <circle
          cx={RADAR_SIZE / 2}
          cy={RADAR_SIZE / 2}
          r={OUTER_RADIUS + 6}
          fill="url(#dna-glow)"
          opacity="0.7"
        />

        {#each rings as ratio}
          <polygon
            points={ringPoints(ratio, metrics.length)}
            fill="none"
            stroke="rgba(148, 163, 184, 0.2)"
            stroke-width="1"
          />
        {/each}

        <polygon
          class="footprint"
          points={polygonPoints}
          fill="url(#dna-polygon)"
          stroke="rgba(56, 189, 248, 0.7)"
          stroke-width="1.8"
          stroke-linejoin="round"
          opacity="0.85"
        />

        {#each metrics as metric, index}
          {#if metric.label}
            {@const angle = (Math.PI * 2 * index) / metrics.length - Math.PI / 2}
            {@const labelRadius = OUTER_RADIUS + 14}
            {@const lx = RADAR_SIZE / 2 + labelRadius * Math.cos(angle)}
            {@const ly = RADAR_SIZE / 2 + labelRadius * Math.sin(angle)}
            <text
              x={lx}
              y={ly}
              text-anchor="middle"
              alignment-baseline="middle"
              class="label"
            >
              {metric.label}
            </text>
          {/if}
        {/each}
      </svg>
    </figure>

    <div class="readout">
      <ul>
        {#each metrics as metric}
          <li>
            <span class="title" title={metric.hint}>{metric.label}</span>
            <div class="bar" style={`--progress:${normalise(metric.value, metric.max)}`}>
              <div class="progress"></div>
            </div>
            <span class="value">
              {metric.value > 1000
                ? metric.value.toFixed(0)
                : metric.value >= 10
                ? metric.value.toFixed(1)
                : metric.value.toFixed(2)}
            </span>
          </li>
        {/each}
      </ul>

      <footer>
        <div>
          <span>Chapters</span>
          <strong>{story.chapter_count}</strong>
        </div>
        <div>
          <span>Total Tokens</span>
          <strong>{story.total_tokens ?? 0}</strong>
        </div>
        <div>
          <span>Timeline</span>
          <strong>
            {firstChapter && lastChapter
              ? `${new Date(firstChapter.created_at).toLocaleDateString()} → ${new Date(
                  lastChapter.created_at ?? story.completed_at ?? story.created_at
                ).toLocaleDateString()}`
              : new Date(story.created_at).toLocaleDateString()}
          </strong>
        </div>
      </footer>
    </div>
  </div>

  {#if contentAxisSummaries.length}
    <div class="content-axes">
      <h3>Content Axis Targets</h3>
      <p>
        Story directives for each content dimension compared against chapter averages so far.
      </p>
      <div class="axis-grid">
        {#each contentAxisSummaries as axis (axis.key)}
          <article
            class="axis-card"
            style={`--axis-color:${axis.color}; --axis-color-soft:${axis.color}33`}
          >
            <header>
              <h4>{axis.label}</h4>
              <p>{axis.description}</p>
            </header>
            <div class="bars">
              <div class="bar">
                <span>Target {axis.targetDisplay}</span>
                <div class="bar-track">
                  <div class="bar-fill" style={`--progress:${axis.targetProgress}`}></div>
                </div>
              </div>
              <div class="bar">
                <span>Observed {axis.observedDisplay}</span>
                <div class="bar-track">
                  <div class="bar-fill" style={`--progress:${axis.observedProgress}`}></div>
                </div>
              </div>
            </div>
            <footer>
              <span>Momentum {axis.momentumDisplay}</span>
              <span>Premise {axis.multiplierDisplay}</span>
            </footer>
          </article>
        {/each}
      </div>
    </div>
  {/if}
</section>

<style>
  .dna {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 24px;
    padding: 2rem;
    box-shadow: 0 16px 44px rgba(8, 13, 32, 0.45);
  }

  header h2 {
    margin: 0 0 0.35rem;
    font-size: 1.5rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  header p {
    margin: 0;
    opacity: 0.75;
    line-height: 1.6;
  }

  .content {
    display: grid;
    grid-template-columns: minmax(0, 340px) minmax(0, 1fr);
    gap: 2rem;
    align-items: center;
  }

  figure {
    margin: 0;
    display: flex;
    justify-content: center;
  }

  svg {
    width: min(360px, 100%);
    height: auto;
  }

  .label {
    font-size: 0.65rem;
    fill: rgba(226, 232, 240, 0.75);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }

  .footprint {
    filter: drop-shadow(0 10px 25px rgba(56, 189, 248, 0.45));
  }

  .readout ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .readout li {
    display: grid;
    grid-template-columns: 140px minmax(0, 1fr) auto;
    gap: 0.8rem;
    align-items: center;
  }

  .title {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    opacity: 0.75;
  }

  .bar {
    position: relative;
    height: 8px;
    background: rgba(71, 85, 105, 0.4);
    border-radius: 999px;
    overflow: hidden;
  }

  .bar .progress {
    position: absolute;
    inset: 0;
    transform-origin: left;
    transform: scaleX(var(--progress));
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.6), rgba(139, 92, 246, 0.9));
    transition: transform 0.4s ease;
  }

  .value {
    font-variant-numeric: tabular-nums;
    font-size: 0.9rem;
  }

  footer {
    margin-top: 1.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    background: rgba(15, 118, 110, 0.2);
    border-radius: 16px;
    padding: 1rem 1.25rem;
    border: 1px solid rgba(20, 184, 166, 0.35);
  }

  footer span {
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.7rem;
    opacity: 0.7;
  }

  footer strong {
    font-size: 1rem;
  }

  .content-axes {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 20px;
    padding: 1.5rem;
  }

  .content-axes h3 {
    margin: 0;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .content-axes p {
    margin: 0;
    max-width: 620px;
    font-size: 0.85rem;
    line-height: 1.5;
    opacity: 0.75;
  }

  .axis-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  .axis-card {
    background: rgba(2, 6, 23, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 16px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .axis-card header h4 {
    margin: 0 0 0.2rem;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--axis-color);
  }

  .axis-card header p {
    margin: 0;
    font-size: 0.75rem;
    line-height: 1.4;
    opacity: 0.75;
  }

  .axis-card .bars {
    display: grid;
    gap: 0.6rem;
  }

  .axis-card .bar {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .axis-card .bar span {
    font-size: 0.72rem;
    opacity: 0.75;
  }

  .axis-card .bar-track {
    background: rgba(255, 255, 255, 0.1);
    height: 6px;
    border-radius: 999px;
    overflow: hidden;
  }

  .axis-card .bar-fill {
    height: 100%;
    border-radius: 999px;
    width: calc(var(--progress, 0) * 100%);
    background: linear-gradient(135deg, var(--axis-color), rgba(255, 255, 255, 0.2));
    transition: width 0.3s ease;
  }

  .axis-card footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    opacity: 0.75;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  @media (max-width: 960px) {
    .content {
      grid-template-columns: 1fr;
    }

    .readout li {
      grid-template-columns: 120px minmax(0, 1fr) auto;
    }
  }

  @media (max-width: 640px) {
    .dna {
      padding: 1.5rem;
    }

    .readout li {
      grid-template-columns: 1fr;
      gap: 0.4rem;
    }

    .bar {
      order: 3;
    }

    .value {
      order: 2;
      justify-self: flex-start;
    }
  }
</style>

