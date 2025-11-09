<script lang="ts">
  import { updateConfig, spawnStory, resetSystem } from '$lib/api';
  import type { RuntimeConfig } from '$lib/api';
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

  type NumericKind = 'int' | 'float';
  type ConfigValues = Record<ConfigKey, number>;

  type ConfigItem = {
    key: ConfigKey;
    label: string;
    description: string;
    hint?: string;
    type: NumericKind;
    min: number;
    max?: number;
    step: number;
  };

  const initialConfig = (data.config as RuntimeConfig | undefined) ?? {
    chapter_interval_seconds: 60,
    evaluation_interval_chapters: 2,
    quality_score_min: 0.65,
    max_chapters_per_story: 20,
    min_active_stories: 1,
    max_active_stories: 3,
    context_window_chapters: 3
  };

  let config: ConfigValues = { ...initialConfig };

  const configItems: ConfigItem[] = [
    {
      key: 'chapter_interval_seconds',
      label: 'Chapter Interval',
      description: 'Time between automatic chapter generations for active stories.',
      hint: 'Lower values increase pacing but demand more resources.',
      type: 'int',
      min: 10,
      max: 3600,
      step: 5
    },
    {
      key: 'evaluation_interval_chapters',
      label: 'Evaluation Interval',
      description: 'How frequently the evaluation agent reviews story quality.',
      hint: 'A smaller interval keeps stories on course but costs more tokens.',
      type: 'int',
      min: 1,
      max: 50,
      step: 1
    },
    {
      key: 'quality_score_min',
      label: 'Minimum Quality Score',
      description: 'Threshold required for a story to continue without intervention.',
      hint: 'Scores below this trigger escalation or termination workflows.',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.05
    },
    {
      key: 'max_chapters_per_story',
      label: 'Max Chapters Per Story',
      description: 'Upper bound on the length of an autonomous run before forced completion.',
      type: 'int',
      min: 1,
      max: 500,
      step: 1
    },
    {
      key: 'min_active_stories',
      label: 'Minimum Active Stories',
      description: 'Floor for concurrently running stories maintained by the scheduler.',
      type: 'int',
      min: 0,
      max: 100,
      step: 1
    },
    {
      key: 'max_active_stories',
      label: 'Maximum Active Stories',
      description: 'Ceiling for simultaneous story generation jobs.',
      type: 'int',
      min: 1,
      max: 200,
      step: 1
    },
    {
      key: 'context_window_chapters',
      label: 'Context Window',
      description: 'Number of previous chapters retained when prompting the model.',
      type: 'int',
      min: 1,
      max: 50,
      step: 1
    }
  ];

  const configKeys = configItems.map((item) => item.key);

  function createStringMap(values: ConfigValues): Record<ConfigKey, string> {
    const result = {} as Record<ConfigKey, string>;
    for (const key of configKeys) {
      result[key] = values[key]?.toString() ?? '';
    }
    return result;
  }

  function createBooleanMap(value: boolean): Record<ConfigKey, boolean> {
    const result = {} as Record<ConfigKey, boolean>;
    for (const key of configKeys) {
      result[key] = value;
    }
    return result;
  }

  function createErrorMap(): Record<ConfigKey, string | null> {
    const result = {} as Record<ConfigKey, string | null>;
    for (const key of configKeys) {
      result[key] = null;
    }
    return result;
  }

  let inputs = createStringMap(config);
  let dirtyFlags = createBooleanMap(false);
  let errors = createErrorMap();
  let savingKey: ConfigKey | null = null;
  let successMessage: string | null = null;
  let errorMessage: string | null = null;
  let spawning = false;
  let spawnError: string | null = null;
  let resetting = false;
  let resetError: string | null = null;

  const equals = (a: number, b: number, kind: NumericKind): boolean => {
    if (kind === 'float') {
      return Math.abs(a - b) < 1e-6;
    }
    return Math.round(a) === Math.round(b);
  };

  function parseValue(item: ConfigItem, raw: string): number {
    const value = Number(raw);
    return item.type === 'int' ? Math.round(value) : value;
  }

  function validateValue(item: ConfigItem, raw: string): string | null {
    if (!raw.trim()) {
      return 'A value is required.';
    }
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) {
      return 'Enter a numeric value.';
    }
    if (item.type === 'int' && !Number.isInteger(numeric)) {
      return 'Enter a whole number.';
    }
    const parsed = parseValue(item, raw);
    if (parsed < item.min) {
      return `Minimum value is ${item.min}.`;
    }
    if (item.max !== undefined && parsed > item.max) {
      return `Maximum value is ${item.max}.`;
    }
    if (item.key === 'min_active_stories') {
      const maxRaw = inputs.max_active_stories;
      const maxValue = Number(maxRaw);
      if (maxRaw.trim() && !Number.isNaN(maxValue) && parsed > maxValue) {
        return 'Minimum active stories cannot exceed the maximum.';
      }
    }
    if (item.key === 'max_active_stories') {
      const minRaw = inputs.min_active_stories;
      const minValue = Number(minRaw);
      if (minRaw.trim() && !Number.isNaN(minValue) && parsed < minValue) {
        return 'Maximum active stories must be at least the minimum.';
      }
    }
    return null;
  }

  function resetBanners() {
    successMessage = null;
    errorMessage = null;
  }

  function handleInput(item: ConfigItem, raw: string) {
    resetBanners();
    inputs = { ...inputs, [item.key]: raw };
    const validation = validateValue(item, raw);
    errors = { ...errors, [item.key]: validation };
    if (validation) {
      dirtyFlags = { ...dirtyFlags, [item.key]: false };
      return;
    }
    const parsed = parseValue(item, raw);
    const dirty = !equals(parsed, config[item.key], item.type);
    dirtyFlags = { ...dirtyFlags, [item.key]: dirty };
  }

  function applyRuntimeConfig(runtime: RuntimeConfig) {
    config = { ...runtime };
    inputs = createStringMap(config);
    dirtyFlags = createBooleanMap(false);
    errors = createErrorMap();
  }

  async function save(item: ConfigItem) {
    if (savingKey) return;
    const currentError = errors[item.key];
    if (currentError) {
      errorMessage = currentError;
      return;
    }
    const value = inputs[item.key];
    const validation = validateValue(item, value);
    if (validation) {
      errors = { ...errors, [item.key]: validation };
      errorMessage = validation;
      return;
    }

    const parsed = parseValue(item, value);
    const payload: Partial<ConfigValues> = { [item.key]: parsed };

    try {
      savingKey = item.key;
      const runtime = await updateConfig(payload);
      applyRuntimeConfig(runtime);
      successMessage = `${item.label} saved.`;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update configuration.';
      errorMessage = message;
    } finally {
      savingKey = null;
    }
  }

  async function handleSpawnStory() {
    if (spawning) return;
    spawning = true;
    spawnError = null;
    resetBanners();
    try {
      const story = await spawnStory();
      successMessage = `Spawned story "${story.title}".`;
    } catch (error) {
      console.error('Failed to spawn story', error);
      spawnError = error instanceof Error ? error.message : 'Failed to generate story.';
    } finally {
      spawning = false;
    }
  }

  async function handleResetSystem() {
    if (resetting) return;
    const confirmed = window.confirm(
      'This will remove all stories and reset the system configuration. Continue?'
    );
    if (!confirmed) return;

    resetting = true;
    resetError = null;
    resetBanners();
    try {
      const result = await resetSystem();
      successMessage = `System reset: ${result.deleted_stories} stories deleted.`;
    } catch (error) {
      console.error('Failed to reset system', error);
      resetError = error instanceof Error ? error.message : 'Failed to reset system.';
    } finally {
      resetting = false;
    }
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

  <section class="admin-actions">
    <button on:click={handleSpawnStory} disabled={spawning}>
      {spawning ? 'Generating…' : '+ Generate New Story'}
    </button>
    <button class="danger" on:click={handleResetSystem} disabled={resetting}>
      {resetting ? 'Clearing…' : 'Reset System'}
    </button>
  </section>

  {#if successMessage}
    <div class="banner success">{successMessage}</div>
  {/if}
  {#if errorMessage}
    <div class="banner error">{errorMessage}</div>
  {/if}
  {#if spawnError}
    <div class="banner error">{spawnError}</div>
  {/if}
  {#if resetError}
    <div class="banner error">{resetError}</div>
  {/if}

  <section class="config-grid">
    {#each configItems as item}
      <article class="config-card">
        <header>
          <h2>{item.label}</h2>
          <span>{item.key.replaceAll('_', ' ')}</span>
        </header>
        <form class="config-form" on:submit|preventDefault={() => save(item)}>
          <label class="sr-only" for={`config-${item.key}`}>{item.label}</label>
          <div class="input-row">
            <input
              id={`config-${item.key}`}
              class:invalid={Boolean(errors[item.key])}
              class:dirty={dirtyFlags[item.key]}
              type="number"
              step={item.step}
              min={item.min}
              max={item.max ?? ''}
              value={inputs[item.key]}
              inputmode={item.type === 'int' ? 'numeric' : 'decimal'}
              on:input={(event) => handleInput(item, event.currentTarget.value)}
            />
            <button
              type="submit"
              disabled={savingKey === item.key || !dirtyFlags[item.key] || Boolean(errors[item.key])}
            >
              {savingKey === item.key ? 'Saving…' : dirtyFlags[item.key] ? 'Save' : 'Saved'}
            </button>
          </div>
        </form>
        <p>{item.description}</p>
        {#if item.hint}
          <footer>{item.hint}</footer>
        {/if}
        {#if errors[item.key]}
          <p class="error-message">{errors[item.key]}</p>
        {/if}
      </article>
    {/each}
  </section>

  <section class="config-footnotes">
    <h3>Operational Notes</h3>
    <ul>
      <li>
        Values originate from the backend service configuration and mirror the active runtime
        environment. Adjustments made here persist immediately in the database.
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

  .banner {
    border-radius: 16px;
    padding: 1rem 1.25rem;
    font-weight: 500;
    border: 1px solid transparent;
  }

  .banner.success {
    background: rgba(34, 197, 94, 0.1);
    border-color: rgba(34, 197, 94, 0.35);
    color: #bbf7d0;
  }

  .banner.error {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.4);
    color: #fecaca;
  }

  .admin-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }

  .admin-actions button {
    border: none;
    border-radius: 999px;
    padding: 0.7rem 1.6rem;
    font-size: 0.9rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }

  .admin-actions button:not(.danger) {
    background: linear-gradient(135deg, #38bdf8, #6366f1);
    color: #0f172a;
    box-shadow: 0 12px 28px rgba(56, 189, 248, 0.35);
  }

  .admin-actions button.danger {
    background: rgba(220, 38, 38, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(252, 165, 165, 0.6);
    box-shadow: 0 10px 24px rgba(220, 38, 38, 0.25);
  }

  .admin-actions button:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  .admin-actions button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    box-shadow: none;
  }

  .config-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
    min-height: 260px;
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

  .config-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .input-row {
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }

  .input-row input {
    flex: 1;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.85);
    color: #f8fafc;
    padding: 0.65rem 0.85rem;
    font-size: 1.05rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .input-row input:focus {
    outline: none;
    border-color: rgba(56, 189, 248, 0.6);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
  }

  .input-row input.invalid {
    border-color: rgba(239, 68, 68, 0.65);
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.15);
  }

  .input-row input.dirty:not(.invalid) {
    border-color: rgba(59, 130, 246, 0.6);
  }

  .input-row button {
    border: none;
    border-radius: 12px;
    padding: 0.65rem 1.1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    background: linear-gradient(135deg, #38bdf8, #6366f1);
    color: #0f172a;
    transition: transform 0.15s ease, filter 0.15s ease;
  }

  .input-row button:disabled {
    cursor: not-allowed;
    filter: grayscale(0.4);
    opacity: 0.7;
  }

  .input-row button:not(:disabled):hover {
    transform: translateY(-1px);
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

  .error-message {
    margin: -0.25rem 0 0;
    font-size: 0.8rem;
    color: #fca5a5;
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
    font-size: 1.2rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .config-footnotes ul {
    margin: 0;
    padding-left: 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    opacity: 0.85;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 640px) {
    .input-row {
      flex-direction: column;
      align-items: stretch;
    }

    .input-row button {
      width: 100%;
    }
  }
</style>
