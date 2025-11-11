<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { updateConfig, spawnStory, resetSystem, updatePromptState, runCoverBackfill } from '$lib/api';
  import type { CoverBackfillStatus, PremisePromptState, RuntimeConfig } from '$lib/api';
  import {
    CONTENT_AXIS_KEYS,
    CONTENT_AXIS_METADATA,
    CONTENT_AXIS_DEFAULTS,
    sanitizeContentAxisSettings,
    type ContentAxisKey,
    type ContentAxisSettings,
    type ContentAxisSettingsMap
  } from '$lib/contentAxes';
  import type { PageData } from './$types';

  export let data: PageData;

  type NumericKind = 'int' | 'float';
  type NumericConfigKey =
    | 'chapter_interval_seconds'
    | 'evaluation_interval_chapters'
    | 'quality_score_min'
    | 'max_chapters_per_story'
    | 'min_active_stories'
    | 'max_active_stories'
    | 'context_window_chapters'
    | 'openai_temperature_chapter'
    | 'openai_temperature_premise'
    | 'openai_temperature_eval'
    | 'premise_prompt_refresh_interval'
    | 'premise_prompt_stats_window'
    | 'premise_prompt_variation_strength'
    | 'chaos_initial_min'
    | 'chaos_initial_max'
    | 'chaos_increment_min'
    | 'chaos_increment_max';

  type StringConfigKey = 'openai_model' | 'openai_premise_model' | 'openai_eval_model';

  type ConfigKey = NumericConfigKey | StringConfigKey;

  type ConfigValues = {
    [K in NumericConfigKey]: number;
  } & {
    [K in StringConfigKey]: string;
  };

  type NumericConfigItem = {
    key: NumericConfigKey;
    label: string;
    description: string;
    hint?: string;
    kind: 'number';
    type: NumericKind;
    min: number;
    max?: number;
    step: number;
  };

  type TextConfigItem = {
    key: StringConfigKey;
    label: string;
    description: string;
    hint?: string;
    kind: 'string';
    placeholder?: string;
  };

  type ConfigItem = NumericConfigItem | TextConfigItem;

  const runtimeConfig = data.config as RuntimeConfig | undefined;

  const baseConfig: ConfigValues = {
    chapter_interval_seconds: 60,
    evaluation_interval_chapters: 2,
    quality_score_min: 0.65,
    max_chapters_per_story: 20,
    min_active_stories: 1,
    max_active_stories: 3,
    context_window_chapters: 3,
    openai_model: 'gpt-4o-mini',
    openai_premise_model: 'gpt-4o-mini',
    openai_eval_model: 'gpt-4o-mini',
    openai_temperature_chapter: 1.0,
    openai_temperature_premise: 1.0,
    openai_temperature_eval: 0.3,
    premise_prompt_refresh_interval: 6,
    premise_prompt_stats_window: 12,
    premise_prompt_variation_strength: 0.65,
    chaos_initial_min: 0.05,
    chaos_initial_max: 0.25,
    chaos_increment_min: 0.02,
    chaos_increment_max: 0.15
  };

  if (runtimeConfig) {
    for (const key of Object.keys(baseConfig) as ConfigKey[]) {
      const value = runtimeConfig[key];
      if (value !== undefined && value !== null) {
        baseConfig[key] = value as (typeof baseConfig)[typeof key];
      }
    }
  }

  let config: ConfigValues = { ...baseConfig };

  type CoverBackfillForm = {
    enabled: boolean;
    interval: number;
    batchSize: number;
    pauseSeconds: number;
  };

  const initialCoverBaseline: CoverBackfillForm = {
    enabled: runtimeConfig?.cover_backfill_enabled ?? true,
    interval: runtimeConfig?.cover_backfill_interval_minutes ?? 180,
    batchSize: runtimeConfig?.cover_backfill_batch_size ?? 3,
    pauseSeconds: runtimeConfig?.cover_backfill_pause_seconds ?? 5
  };

  type CoverField = 'interval' | 'batchSize' | 'pauseSeconds';

  const coverFieldMeta: Record<CoverField, { label: string; min: number; max: number; step: number; type: NumericKind; hint: string }> = {
    interval: {
      label: 'Interval (minutes)',
      min: 5,
      max: 1440,
      step: 5,
      type: 'int',
      hint: 'How often the worker searches for missing covers.'
    },
    batchSize: {
      label: 'Batch size',
      min: 1,
      max: 25,
      step: 1,
      type: 'int',
      hint: 'Maximum stories processed per run.'
    },
    pauseSeconds: {
      label: 'Pause between stories (seconds)',
      min: 0,
      max: 120,
      step: 0.5,
      type: 'float',
      hint: 'Throttle between image generations to avoid rate limits.'
    }
  };

  let coverBaseline: CoverBackfillForm = { ...initialCoverBaseline };
  let coverEnabled = coverBaseline.enabled;
  let coverInputs: Record<CoverField, string> = {
    interval: coverBaseline.interval.toString(),
    batchSize: coverBaseline.batchSize.toString(),
    pauseSeconds: coverBaseline.pauseSeconds.toString()
  };
  let coverErrors: Record<CoverField, string | null> = {
    interval: null,
    batchSize: null,
    pauseSeconds: null
  };
  let coverDirty = false;
  let coverSaving = false;
  let coverRunning = false;
  let coverStatus: CoverBackfillStatus | null = runtimeConfig?.cover_backfill_status ?? null;

  function parseCoverField(field: CoverField, raw: string): number {
    const numeric = Number(raw);
    if (!Number.isFinite(numeric)) {
      return NaN;
    }
    return coverFieldMeta[field].type === 'int' ? Math.round(numeric) : numeric;
  }

  function validateCoverField(field: CoverField, raw: string): string | null {
    if (!raw.trim()) {
      return 'Value is required';
    }
    const numeric = Number(raw);
    if (!Number.isFinite(numeric)) {
      return 'Must be a number';
    }
    const meta = coverFieldMeta[field];
    if (meta.type === 'int' && !Number.isInteger(Math.round(numeric))) {
      return 'Must be an integer';
    }
    if (numeric < meta.min || numeric > meta.max) {
      return `Must be between ${meta.min} and ${meta.max}`;
    }
    return null;
  }

  function updateCoverDirty(): void {
    const intervalValue = parseCoverField('interval', coverInputs.interval);
    const batchValue = parseCoverField('batchSize', coverInputs.batchSize);
    const pauseValue = parseCoverField('pauseSeconds', coverInputs.pauseSeconds);
    const intervalValid = !coverErrors.interval && Number.isFinite(intervalValue);
    const batchValid = !coverErrors.batchSize && Number.isFinite(batchValue);
    const pauseValid = !coverErrors.pauseSeconds && Number.isFinite(pauseValue);

    const intervalChanged = intervalValid && intervalValue !== coverBaseline.interval;
    const batchChanged = batchValid && batchValue !== coverBaseline.batchSize;
    const pauseChanged =
      pauseValid && Number(pauseValue.toFixed(3)) !== Number(coverBaseline.pauseSeconds.toFixed(3));

    coverDirty =
      coverEnabled !== coverBaseline.enabled || intervalChanged || batchChanged || pauseChanged;
  }

  function handleCoverInput(field: CoverField, raw: string): void {
    resetBanners();
    coverInputs = { ...coverInputs, [field]: raw };
    const validation = validateCoverField(field, raw);
    coverErrors = { ...coverErrors, [field]: validation };
    updateCoverDirty();
  }

  function resetCoverForm(): void {
    coverInputs = {
      interval: coverBaseline.interval.toString(),
      batchSize: coverBaseline.batchSize.toString(),
      pauseSeconds: coverBaseline.pauseSeconds.toString()
    };
    coverErrors = {
      interval: null,
      batchSize: null,
      pauseSeconds: null
    };
    coverEnabled = coverBaseline.enabled;
    updateCoverDirty();
  }

  function handleCoverToggle(event: Event): void {
    resetBanners();
    const target = event.currentTarget as HTMLInputElement;
    coverEnabled = target.checked;
    updateCoverDirty();
  }

  $: coverErrorsPresent = Object.values(coverErrors).some((value) => Boolean(value));

  async function saveCoverBackfill(): Promise<void> {
    if (coverSaving || !coverDirty) {
      return;
    }
    resetBanners();
    const fields: CoverField[] = ['interval', 'batchSize', 'pauseSeconds'];
    const parsed: Record<CoverField, number> = {
      interval: coverBaseline.interval,
      batchSize: coverBaseline.batchSize,
      pauseSeconds: coverBaseline.pauseSeconds
    };
    let hasErrors = false;
    for (const field of fields) {
      const raw = coverInputs[field];
      const validation = validateCoverField(field, raw);
      coverErrors = { ...coverErrors, [field]: validation };
      if (validation) {
        hasErrors = true;
      } else {
        parsed[field] = parseCoverField(field, raw);
      }
    }
    if (hasErrors) {
      errorMessage = 'Please correct the highlighted cover backfill values.';
      updateCoverDirty();
      return;
    }
    const payload = {
      cover_backfill_enabled: coverEnabled,
      cover_backfill_interval_minutes: parsed.interval,
      cover_backfill_batch_size: parsed.batchSize,
      cover_backfill_pause_seconds: Number(parsed.pauseSeconds.toFixed(2))
    } as Partial<RuntimeConfig>;
    try {
      coverSaving = true;
      const runtime = await updateConfig(payload);
      applyRuntimeConfig(runtime);
      successMessage = 'Cover art backfill settings saved.';
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update cover art settings.';
      errorMessage = message;
    } finally {
      coverSaving = false;
    }
  }

  async function triggerCoverBackfill(): Promise<void> {
    if (coverRunning) {
      return;
    }
    resetBanners();
    coverRunning = true;
    try {
      const response = await runCoverBackfill();
      if (response?.status) {
        coverStatus = response.status as CoverBackfillStatus;
      } else if (response?.status === null) {
        coverStatus = null;
      }
      const message = typeof response?.message === 'string' ? response.message : 'Cover art backfill triggered.';
      successMessage = message;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to run cover art backfill.';
      errorMessage = message;
    } finally {
      coverRunning = false;
    }
  }

  const initialContentAxes: ContentAxisSettingsMap = sanitizeContentAxisSettings(
    runtimeConfig?.content_axes ?? CONTENT_AXIS_DEFAULTS
  );

  const fallbackPromptState: PremisePromptState = {
    directives: [],
    rationale: null,
    generated_at: null,
    variation_strength: null,
    manual_override: false,
    stats_snapshot: null,
    hurllol_title: null,
    hurllol_title_components: null,
    hurllol_title_generated_at: null
  };

  function normalisePromptState(state: PremisePromptState | undefined | null): PremisePromptState {
    if (!state) {
      return { ...fallbackPromptState };
    }
    return {
      directives: Array.isArray(state.directives) ? [...state.directives] : [],
      rationale: state.rationale ?? null,
      generated_at: state.generated_at ?? null,
      variation_strength:
        typeof state.variation_strength === 'number' ? state.variation_strength : null,
      manual_override: Boolean(state.manual_override),
      stats_snapshot: state.stats_snapshot ?? null,
      hurllol_title: state.hurllol_title ?? null,
      hurllol_title_components: Array.isArray(state.hurllol_title_components)
        ? [...state.hurllol_title_components]
        : null,
      hurllol_title_generated_at: state.hurllol_title_generated_at ?? null
    };
  }

  let promptState: PremisePromptState = normalisePromptState(data.prompts?.premise ?? null);
  let promptDirectivesInput = promptState.directives.join('\n');
  let promptRationaleInput = promptState.rationale ?? '';
  let promptSaving = false;
  let promptError: string | null = null;

  const configItems: ConfigItem[] = [
    {
      key: 'chapter_interval_seconds',
      label: 'Chapter Interval',
      description: 'Time between automatic chapter generations for active stories.',
      hint: 'Lower values increase pacing but demand more resources.',
      kind: 'number',
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
      kind: 'number',
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
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
    },
    {
      key: 'premise_prompt_refresh_interval',
      label: 'Premise Prompt Refresh Interval',
      description: 'How many new stories to spawn before asking the model to remix the premise instructions.',
      hint: 'Lower numbers keep the prompt volatile; higher numbers stabilize it.',
      kind: 'number',
      type: 'int',
      min: 1,
      max: 200,
      step: 1
    },
    {
      key: 'premise_prompt_stats_window',
      label: 'Premise Stats Window',
      description: 'Number of recent stories considered when summarising performance for prompt remixing.',
      hint: 'Larger windows smooth out noise; smaller ones react quickly to new patterns.',
      kind: 'number',
      type: 'int',
      min: 1,
      max: 200,
      step: 1
    },
    {
      key: 'premise_prompt_variation_strength',
      label: 'Premise Variation Strength',
      description: 'Scales how aggressively the remix model pushes for weirdness and novelty in new premises.',
      hint: 'Values near 1 lean into high-risk, high-variance instructions.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
    },
    {
      key: 'max_chapters_per_story',
      label: 'Max Chapters Per Story',
      description: 'Upper bound on the length of an autonomous run before forced completion.',
      kind: 'number',
      type: 'int',
      min: 1,
      max: 500,
      step: 1
    },
    {
      key: 'min_active_stories',
      label: 'Minimum Active Stories',
      description: 'Floor for concurrently running stories maintained by the scheduler.',
      kind: 'number',
      type: 'int',
      min: 0,
      max: 100,
      step: 1
    },
    {
      key: 'max_active_stories',
      label: 'Maximum Active Stories',
      description: 'Ceiling for simultaneous story generation jobs.',
      kind: 'number',
      type: 'int',
      min: 1,
      max: 200,
      step: 1
    },
    {
      key: 'context_window_chapters',
      label: 'Context Window',
      description: 'Number of previous chapters retained when prompting the model.',
      kind: 'number',
      type: 'int',
      min: 1,
      max: 50,
      step: 1
    },
    {
      key: 'openai_model',
      label: 'Chapter Model',
      description: 'Primary model used for chapter generation prompts.',
      hint: 'Enter a deployable model name such as gpt-4o-mini or its fine-tuned variant.',
      kind: 'string',
      placeholder: 'gpt-4o-mini'
    },
    {
      key: 'openai_premise_model',
      label: 'Premise Model',
      description: 'Model leveraged for new story premises and theming.',
      kind: 'string',
      placeholder: 'gpt-4o-mini'
    },
    {
      key: 'openai_eval_model',
      label: 'Evaluation Model',
      description: 'Model used by the quality gate to score chapter batches.',
      kind: 'string',
      placeholder: 'gpt-4o-mini'
    },
    {
      key: 'openai_temperature_chapter',
      label: 'Chapter Temperature',
      description: 'Creativity dial for chapter generation (higher values increase chaos).',
      hint: 'Range: 0 (deterministic) to 2 (maximum creativity).',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 2,
      step: 0.05
    },
    {
      key: 'openai_temperature_premise',
      label: 'Premise Temperature',
      description: 'Controls novelty when birthing new story premises and themes.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 2,
      step: 0.05
    },
    {
      key: 'openai_temperature_eval',
      label: 'Evaluation Temperature',
      description: 'Should stay low so the reviewer remains consistent and strict.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 2,
      step: 0.05
    },
    {
      key: 'chaos_initial_min',
      label: 'Chaos Initial Minimum',
      description: 'Lowest starting chaos factor applied to new stories across all dimensions.',
      hint: 'Must be less than or equal to the maximum and between 0 and 1.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
    },
    {
      key: 'chaos_initial_max',
      label: 'Chaos Initial Maximum',
      description: 'Highest starting chaos factor applied to new stories.',
      hint: 'Must be greater than or equal to the minimum and between 0 and 1.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
    },
    {
      key: 'chaos_increment_min',
      label: 'Chaos Increment Minimum',
      description: 'Smallest per-chapter chaos increase expected when generating chapters.',
      hint: 'Must be less than or equal to the maximum and between 0 and 1.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
    },
    {
      key: 'chaos_increment_max',
      label: 'Chaos Increment Maximum',
      description: 'Largest per-chapter chaos increase expected during generation.',
      hint: 'Must be greater than or equal to the minimum and between 0 and 1.',
      kind: 'number',
      type: 'float',
      min: 0,
      max: 1,
      step: 0.01
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

  const axisKeys = CONTENT_AXIS_KEYS;
  type AxisField = keyof ContentAxisSettings;
  const axisFields: AxisField[] = ['average_level', 'momentum', 'premise_multiplier'];

  const axisFieldMeta: Record<AxisField, { label: string; hint: string; min: number; max: number; step: number }> = {
    average_level: {
      label: 'Average Level',
      hint: 'Target mean intensity across the story (0–10).',
      min: 0,
      max: 10,
      step: 0.1
    },
    momentum: {
      label: 'Chapter Momentum',
      hint: 'Expected change per chapter (-1 to 1).',
      min: -1,
      max: 1,
      step: 0.05
    },
    premise_multiplier: {
      label: 'Premise Remix Multiplier',
      hint: 'Influences how strongly the premise leans into this axis (0–10).',
      min: 0,
      max: 10,
      step: 0.1
    }
  };

  function createAxisInputEntry(settings: ContentAxisSettings): Record<AxisField, string> {
    return {
      average_level: settings.average_level.toString(),
      momentum: settings.momentum.toString(),
      premise_multiplier: settings.premise_multiplier.toString()
    };
  }

  function createAxisInputMap(
    values: ContentAxisSettingsMap
  ): Record<ContentAxisKey, Record<AxisField, string>> {
    const result = {} as Record<ContentAxisKey, Record<AxisField, string>>;
    for (const axis of axisKeys) {
      result[axis] = createAxisInputEntry(values[axis]);
    }
    return result;
  }

  function createAxisDirtyEntry(initial: boolean): Record<AxisField, boolean> {
    return axisFields.reduce(
      (acc, field) => ({ ...acc, [field]: initial }),
      {} as Record<AxisField, boolean>
    );
  }

  function createAxisDirtyMap(initial: boolean): Record<ContentAxisKey, Record<AxisField, boolean>> {
    const result = {} as Record<ContentAxisKey, Record<AxisField, boolean>>;
    for (const axis of axisKeys) {
      result[axis] = createAxisDirtyEntry(initial);
    }
    return result;
  }

  function createAxisErrorEntry(): Record<AxisField, string | null> {
    return axisFields.reduce(
      (acc, field) => ({ ...acc, [field]: null }),
      {} as Record<AxisField, string | null>
    );
  }

  function createAxisErrorMap(): Record<ContentAxisKey, Record<AxisField, string | null>> {
    const result = {} as Record<ContentAxisKey, Record<AxisField, string | null>>;
    for (const axis of axisKeys) {
      result[axis] = createAxisErrorEntry();
    }
    return result;
  }

  let inputs = createStringMap(config);
  let dirtyFlags = createBooleanMap(false);
  let errors = createErrorMap();
  let contentAxes: ContentAxisSettingsMap = { ...initialContentAxes };
  let axisInputs = createAxisInputMap(contentAxes);
  let axisDirtyFlags = createAxisDirtyMap(false);
  let axisErrors = createAxisErrorMap();
  let axisSaving: ContentAxisKey | null = null;
  let savingKey: ConfigKey | null = null;
  let successMessage: string | null = null;
  let errorMessage: string | null = null;
  let spawning = false;
  let spawnError: string | null = null;
  let resetting = false;
  let resetError: string | null = null;
  let loggingOut = false;
  let logoutError: string | null = null;

  const equals = (item: ConfigItem, nextValue: number | string): boolean => {
    const currentValue = config[item.key] as number | string;
    if (item.kind === 'string') {
      return String(currentValue) === String(nextValue);
    }

    const numericCurrent = currentValue as number;
    const numericNext = nextValue as number;
    if (item.type === 'float') {
      return Math.abs(numericCurrent - numericNext) < 1e-6;
    }
    return Math.round(numericCurrent) === Math.round(numericNext);
  }

  function parseValue(item: ConfigItem, raw: string): number | string {
    if (item.kind === 'string') {
      return raw.trim();
    }
    const value = Number(raw);
    return item.type === 'int' ? Math.round(value) : value;
  }

  function validateValue(item: ConfigItem, raw: string): string | null {
    if (!raw.trim()) {
      return 'A value is required.';
    }

    if (item.kind === 'string') {
      return null;
    }

    const numeric = Number(raw);
    if (Number.isNaN(numeric)) {
      return 'Enter a numeric value.';
    }
    if (item.type === 'int' && !Number.isInteger(numeric)) {
      return 'Enter a whole number.';
    }

    const parsedNumber = parseValue(item, raw) as number;
    if (parsedNumber < item.min) {
      return `Minimum value is ${item.min}.`;
    }
    if (item.max !== undefined && parsedNumber > item.max) {
      return `Maximum value is ${item.max}.`;
    }
    if (item.key === 'min_active_stories') {
      const maxRaw = inputs.max_active_stories;
      const maxValue = Number(maxRaw);
      if (maxRaw.trim() && !Number.isNaN(maxValue) && parsedNumber > maxValue) {
        return 'Minimum active stories cannot exceed the maximum.';
      }
    }
    if (item.key === 'max_active_stories') {
      const minRaw = inputs.min_active_stories;
      const minValue = Number(minRaw);
      if (minRaw.trim() && !Number.isNaN(minValue) && parsedNumber < minValue) {
        return 'Maximum active stories must be at least the minimum.';
      }
    }
    if (item.key === 'chaos_initial_min') {
      const maxRaw = inputs.chaos_initial_max;
      const maxValue = Number(maxRaw);
      if (maxRaw.trim() && !Number.isNaN(maxValue) && parsedNumber > maxValue) {
        return 'Initial minimum cannot exceed the maximum.';
      }
    }
    if (item.key === 'chaos_initial_max') {
      const minRaw = inputs.chaos_initial_min;
      const minValue = Number(minRaw);
      if (minRaw.trim() && !Number.isNaN(minValue) && parsedNumber < minValue) {
        return 'Initial maximum must be at least the minimum.';
      }
    }
    if (item.key === 'chaos_increment_min') {
      const maxRaw = inputs.chaos_increment_max;
      const maxValue = Number(maxRaw);
      if (maxRaw.trim() && !Number.isNaN(maxValue) && parsedNumber > maxValue) {
        return 'Increment minimum cannot exceed the maximum.';
      }
    }
    if (item.key === 'chaos_increment_max') {
      const minRaw = inputs.chaos_increment_min;
      const minValue = Number(minRaw);
      if (minRaw.trim() && !Number.isNaN(minValue) && parsedNumber < minValue) {
        return 'Increment maximum must be at least the minimum.';
      }
    }
    return null;
  }

  function validateAxisValue(field: AxisField, raw: string): string | null {
    if (!raw.trim()) {
      return 'Provide a value.';
    }
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) {
      return 'Enter a numeric value.';
    }
    const { min, max } = axisFieldMeta[field];
    if (numeric < min || numeric > max) {
      return `Value must be between ${min} and ${max}.`;
    }
    return null;
  }

  function parseAxisValue(field: AxisField, raw: string): number {
    const numeric = Number(raw);
    const { min, max } = axisFieldMeta[field];
    const clamped = Math.max(min, Math.min(max, numeric));
    const precision = field === 'momentum' ? 3 : 2;
    return Number(clamped.toFixed(precision));
  }

  function axisValueEquals(current: number, next: number, field: AxisField): boolean {
    const tolerance = field === 'momentum' ? 1e-3 : 1e-2;
    return Math.abs(current - next) < tolerance;
  }

  function axisHasErrors(axis: ContentAxisKey): boolean {
    return axisFields.some((field) => Boolean(axisErrors[axis][field]));
  }

  function axisIsDirty(axis: ContentAxisKey): boolean {
    const baseline = contentAxes[axis];
    const inputsForAxis = axisInputs[axis];
    const errorsForAxis = axisErrors[axis];
    if (!baseline || !inputsForAxis || !errorsForAxis) {
      return false;
    }
    const baselineStrings = createAxisInputEntry(baseline);
    return axisFields.some((field) => {
      const raw = inputsForAxis[field] ?? '';
      const trimmed = raw.trim();
      const baselineRaw = baselineStrings[field];
      if (!trimmed) {
        return trimmed !== baselineRaw;
      }
      if (errorsForAxis[field]) {
        return trimmed !== baselineRaw;
      }
      const parsed = parseAxisValue(field, raw);
      return !axisValueEquals(baseline[field], parsed, field);
    });
  }

  function handleAxisInput(axis: ContentAxisKey, field: AxisField, raw: string) {
    resetBanners();
    axisInputs = { ...axisInputs, [axis]: { ...axisInputs[axis], [field]: raw } };
    const validation = validateAxisValue(field, raw);
    axisErrors = { ...axisErrors, [axis]: { ...axisErrors[axis], [field]: validation } };
    if (validation) {
      const baseline = createAxisInputEntry(contentAxes[axis])[field];
      const dirty = raw.trim() !== baseline;
      axisDirtyFlags = { ...axisDirtyFlags, [axis]: { ...axisDirtyFlags[axis], [field]: dirty } };
      return;
    }
    const parsed = parseAxisValue(field, raw);
    const dirty = !axisValueEquals(contentAxes[axis][field], parsed, field);
    axisDirtyFlags = { ...axisDirtyFlags, [axis]: { ...axisDirtyFlags[axis], [field]: dirty } };
  }

  function resetAxis(axis: ContentAxisKey) {
    resetBanners();
    const settings = contentAxes[axis];
    axisInputs = { ...axisInputs, [axis]: createAxisInputEntry(settings) };
    axisErrors = { ...axisErrors, [axis]: createAxisErrorEntry() };
    axisDirtyFlags = { ...axisDirtyFlags, [axis]: createAxisDirtyEntry(false) };
  }

  async function saveAxis(axis: ContentAxisKey) {
    if (axisSaving) return;

    const metadata = CONTENT_AXIS_METADATA[axis];
    const nextSettings: ContentAxisSettings = { ...contentAxes[axis] };

    for (const field of axisFields) {
      const raw = axisInputs[axis][field];
      const validation = validateAxisValue(field, raw);
      axisErrors = { ...axisErrors, [axis]: { ...axisErrors[axis], [field]: validation } };
      if (validation) {
        errorMessage = validation;
        return;
      }
      nextSettings[field] = parseAxisValue(field, raw);
    }

    if (axisFields.every((field) => axisValueEquals(contentAxes[axis][field], nextSettings[field], field))) {
      successMessage = `${metadata.label} already up to date.`;
      axisDirtyFlags = { ...axisDirtyFlags, [axis]: createAxisDirtyEntry(false) };
      return;
    }

    const payload = {
      content_axes: {
        [axis]: nextSettings
      }
    } as Partial<RuntimeConfig>;

    try {
      axisSaving = axis;
      const runtime = await updateConfig(payload);
      applyRuntimeConfig(runtime);
      successMessage = `${metadata.label} settings saved.`;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update content axis.';
      errorMessage = message;
    } finally {
      axisSaving = null;
    }
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
    const dirty = !equals(item, parsed);
    dirtyFlags = { ...dirtyFlags, [item.key]: dirty };
  }

  function applyRuntimeConfig(runtime: RuntimeConfig) {
    const nextConfig = { ...config } as ConfigValues;
    for (const key of configKeys) {
      nextConfig[key] = runtime[key] as (typeof nextConfig)[typeof key];
    }
    config = nextConfig;
    contentAxes = sanitizeContentAxisSettings(runtime.content_axes ?? CONTENT_AXIS_DEFAULTS);
    inputs = createStringMap(config);
    dirtyFlags = createBooleanMap(false);
    errors = createErrorMap();
    axisInputs = createAxisInputMap(contentAxes);
    axisDirtyFlags = createAxisDirtyMap(false);
    axisErrors = createAxisErrorMap();
    coverBaseline = {
      enabled: runtime.cover_backfill_enabled ?? coverBaseline.enabled,
      interval: runtime.cover_backfill_interval_minutes ?? coverBaseline.interval,
      batchSize: runtime.cover_backfill_batch_size ?? coverBaseline.batchSize,
      pauseSeconds: runtime.cover_backfill_pause_seconds ?? coverBaseline.pauseSeconds
    };
    coverEnabled = coverBaseline.enabled;
    coverInputs = {
      interval: coverBaseline.interval.toString(),
      batchSize: coverBaseline.batchSize.toString(),
      pauseSeconds: coverBaseline.pauseSeconds.toString()
    };
    coverErrors = {
      interval: null,
      batchSize: null,
      pauseSeconds: null
    };
    coverStatus = runtime.cover_backfill_status ?? null;
    updateCoverDirty();
  }

  const hurllolFallback = 'Hurl Unmasks Recursive Literature Leaking Out Love';

  function normaliseDirectiveInput(raw: string): string[] {
    return raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
  }

  function directivesEqual(a: string[], b: string[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((value, index) => value === b[index]);
  }

  function applyPromptState(state: PremisePromptState) {
    promptState = normalisePromptState(state);
    promptDirectivesInput = promptState.directives.join('\n');
    promptRationaleInput = promptState.rationale ?? '';
    promptError = null;
  }

  function resetPromptForm() {
    applyPromptState(promptState);
  }

  function formatTimestamp(value: string | null): string {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString();
  }

  let promptDirty = false;

  $: currentDirectiveList = normaliseDirectiveInput(promptDirectivesInput);
  $: trimmedPromptRationale = promptRationaleInput.trim();
  $: storedPromptRationale = (promptState.rationale ?? '').trim();
  $: promptDirty =
    !directivesEqual(currentDirectiveList, promptState.directives) ||
    trimmedPromptRationale !== storedPromptRationale;

  $: directiveTextareaRows = Math.max(4, currentDirectiveList.length + 1);
  $: hurllolTitle = promptState.hurllol_title ?? hurllolFallback;

  async function savePromptState() {
    if (promptSaving || !promptDirty) {
      return;
    }
    promptSaving = true;
    promptError = null;
    resetBanners();

    const payloadDirectives = currentDirectiveList;
    const payload = {
      directives: payloadDirectives,
      rationale: trimmedPromptRationale || null
    };

    try {
      const response = await updatePromptState(payload);
      applyPromptState(response.premise);
      successMessage = 'Premise directives saved.';
    } catch (error) {
      console.error('Failed to update prompt directives', error);
      promptError = error instanceof Error ? error.message : 'Unable to update prompt directives.';
      errorMessage = promptError;
    } finally {
      promptSaving = false;
    }
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
    const payload = { [item.key]: parsed } as Partial<RuntimeConfig>;

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

  async function handleSignOut() {
    if (loggingOut) return;
    loggingOut = true;
    logoutError = null;
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });
      if (!response.ok) {
        let message = `Failed to sign out (${response.status})`;
        try {
          const payload = await response.json();
          if (typeof payload === 'string' && payload) {
            message = payload;
          } else if (payload?.detail) {
            message = Array.isArray(payload.detail)
              ? payload.detail.map((entry: any) => entry?.msg ?? entry).join(', ')
              : payload.detail;
          }
        } catch (error) {
          void error;
        }
        throw new Error(message);
      }
      await invalidateAll();
      await goto('/login', { replaceState: true });
    } catch (error) {
      logoutError =
        error instanceof Error && error.message ? error.message : 'Unable to sign out right now.';
    } finally {
      loggingOut = false;
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
    <div class="session-controls">
      <span>Signed in as {data.user?.username ?? 'admin'}</span>
      <button on:click={handleSignOut} disabled={loggingOut}>
        {loggingOut ? 'Signing out…' : 'Sign out'}
      </button>
    </div>
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
  {#if logoutError}
    <div class="banner error">{logoutError}</div>
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
              type={item.kind === 'string' ? 'text' : 'number'}
              step={item.kind === 'number' ? item.step : undefined}
              min={item.kind === 'number' ? item.min : undefined}
              max={item.kind === 'number' ? item.max ?? undefined : undefined}
              placeholder={item.kind === 'string' ? item.placeholder ?? '' : undefined}
              autocapitalize="off"
              spellcheck={item.kind === 'string' ? false : undefined}
              value={inputs[item.key]}
              inputmode={
                item.kind === 'number'
                  ? item.type === 'int'
                    ? 'numeric'
                    : 'decimal'
                  : 'text'
              }
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

  <section class="cover-backfill-section">
    <header>
      <h2>Cover Art Backfill</h2>
      <p>
        Keep completed stories illustrated by automatically queuing missing cover art. Adjust the
        cadence and throttle to fit your OpenAI quota, and run an on-demand sweep if you add
        stories manually.
      </p>
    </header>

    <div class="cover-backfill-status">
      <div class="status-grid">
        <div>
          <span class="status-label">Automation</span>
          <strong>{(coverStatus?.enabled ?? coverBaseline.enabled) ? 'Enabled' : 'Disabled'}</strong>
        </div>
        <div>
          <span class="status-label">Last run</span>
          <strong>{formatTimestamp(coverStatus?.last_run_at ?? null)}</strong>
          {#if coverStatus?.reason}
            <span class="status-note">{coverStatus.reason.replaceAll('_', ' ')}</span>
          {/if}
        </div>
        <div>
          <span class="status-label">Next run due</span>
          <strong>{formatTimestamp(coverStatus?.next_run_due_at ?? null)}</strong>
        </div>
        <div>
          <span class="status-label">Stories remaining</span>
          <strong>
            {#if typeof coverStatus?.remaining === 'number'}
              {coverStatus.remaining}
            {:else}
              —
            {/if}
          </strong>
        </div>
        <div>
          <span class="status-label">Last batch</span>
          <strong>
            {#if coverStatus}
              {coverStatus.generated} generated · {coverStatus.failed} failed
            {:else}
              —
            {/if}
          </strong>
        </div>
      </div>
      <button class="secondary" on:click={triggerCoverBackfill} disabled={coverRunning}>
        {coverRunning ? 'Running…' : 'Run backfill now'}
      </button>
    </div>

    <form class="cover-backfill-form" on:submit|preventDefault={saveCoverBackfill}>
      <label class="cover-toggle">
        <input type="checkbox" checked={coverEnabled} on:change={handleCoverToggle} />
        <span>Enable automatic cover art backfill</span>
      </label>

      <div class="cover-backfill-grid">
        {#each Object.entries(coverFieldMeta) as [field, meta]}
          {@const typedField = field as CoverField}
          <div class="cover-field">
            <label for={`cover-${field}`}>{meta.label}</label>
            <div class="cover-input-row">
              <input
                id={`cover-${field}`}
                type="number"
                min={meta.min}
                max={meta.max}
                step={meta.step}
                inputmode={meta.type === 'int' ? 'numeric' : 'decimal'}
                value={coverInputs[typedField]}
                class:invalid={Boolean(coverErrors[typedField])}
                on:input={(event) => handleCoverInput(typedField, event.currentTarget.value)}
              />
              <span class="cover-hint">{meta.hint}</span>
            </div>
            {#if coverErrors[typedField]}
              <p class="error-message">{coverErrors[typedField]}</p>
            {/if}
          </div>
        {/each}
      </div>

      <div class="cover-actions">
        <button type="submit" disabled={!coverDirty || coverSaving || coverErrorsPresent}>
          {coverSaving ? 'Saving…' : coverDirty ? 'Save backfill settings' : 'Saved'}
        </button>
        <button type="button" on:click={resetCoverForm} disabled={!coverDirty || coverSaving}>
          Reset
        </button>
      </div>
    </form>
  </section>

  <section class="content-axis-config">
    <header>
      <h2>Content Intensity Controls</h2>
      <p>
        Tune how boldly each thematic axis should manifest. Average level guides overall tone,
        momentum nudges per-chapter swings, and the remix multiplier influences premise remixes.
      </p>
    </header>

    <div class="axis-grid">
      {#each axisKeys as axis}
        {@const metadata = CONTENT_AXIS_METADATA[axis]}
        <article
          class="axis-card"
          style={`--axis-color:${metadata.color}; --axis-color-soft:${metadata.color}33`}
        >
          <header>
            <h3>{metadata.label}</h3>
            <p>{metadata.description}</p>
          </header>

          <form class="axis-form" on:submit|preventDefault={() => saveAxis(axis)}>
            {#each axisFields as field}
              {@const fieldMeta = axisFieldMeta[field]}
              <div class="axis-field">
                <label for={`axis-${axis}-${field}`}>{fieldMeta.label}</label>
                <div class="axis-input-row">
                  <input
                    id={`axis-${axis}-${field}`}
                    type="number"
                    step={fieldMeta.step}
                    min={fieldMeta.min}
                    max={fieldMeta.max}
                    value={axisInputs[axis][field]}
                    class:invalid={Boolean(axisErrors[axis][field])}
                    class:dirty={axisDirtyFlags[axis][field]}
                    inputmode="decimal"
                    on:input={(event) => handleAxisInput(axis, field, event.currentTarget.value)}
                  />
                  <span class="axis-hint">{fieldMeta.hint}</span>
                </div>
                {#if axisErrors[axis][field]}
                  <p class="error-message">{axisErrors[axis][field]}</p>
                {/if}
              </div>
            {/each}

            <div class="axis-actions">
              <button
                type="submit"
                disabled={!axisIsDirty(axis) || axisHasErrors(axis) || axisSaving === axis}
              >
                {axisSaving === axis ? 'Saving…' : axisIsDirty(axis) ? 'Save axis' : 'Saved'}
              </button>
              <button
                type="button"
                on:click={() => resetAxis(axis)}
                disabled={axisSaving === axis || !axisIsDirty(axis)}
              >
                Reset
              </button>
            </div>
          </form>
        </article>
      {/each}
    </div>
  </section>

  <section class="prompt-section">
    <header>
      <div>
        <h2>Premise Prompt Remix</h2>
        <p>
          Review, tweak, or replace the variation directives currently appended to the base premise
          prompt. These adjustments take effect immediately for the next refresh cycle.
        </p>
      </div>
      <div class="hurllol-card">
        <span>Current HURLLOL banner</span>
        <strong>{hurllolTitle}</strong>
        {#if promptState.hurllol_title_generated_at}
          <small>Refreshed {formatTimestamp(promptState.hurllol_title_generated_at)}</small>
        {/if}
      </div>
    </header>

    <div class="prompt-meta">
      <span>
        Last directive update:
        {promptState.generated_at ? formatTimestamp(promptState.generated_at) : '—'}
      </span>
      <span>
        Variation strength:
        {promptState.variation_strength !== null
          ? promptState.variation_strength.toFixed(2)
          : '—'}
      </span>
      {#if promptState.manual_override}
        <span class="manual-chip">Manual override active</span>
      {/if}
    </div>

    <form class="prompt-form" on:submit|preventDefault={savePromptState}>
      <label for="prompt-directives">Dynamic directives (one per line)</label>
      <textarea
        id="prompt-directives"
        rows={directiveTextareaRows}
        bind:value={promptDirectivesInput}
        placeholder={'Push toward dream-logic multiverses\nEmbrace slapstick temporal loops'}
      ></textarea>
      {#if promptError}
        <p class="field-error">{promptError}</p>
      {/if}

      <label for="prompt-rationale">Rationale / Operator notes</label>
      <textarea
        id="prompt-rationale"
        rows="3"
        bind:value={promptRationaleInput}
        placeholder="Document why these directives are in play so future refreshes have context."
      ></textarea>

      <div class="prompt-actions">
        <button type="submit" disabled={!promptDirty || promptSaving}>
          {promptSaving ? 'Saving…' : promptDirty ? 'Save directives' : 'Saved'}
        </button>
        <button type="button" on:click={resetPromptForm} disabled={!promptDirty || promptSaving}>
          Reset changes
        </button>
      </div>
    </form>

    {#if promptState.stats_snapshot}
      <details class="prompt-stats">
        <summary>Recent stats snapshot</summary>
        <pre>{JSON.stringify(promptState.stats_snapshot, null, 2)}</pre>
      </details>
    {/if}
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

  .session-controls {
    margin-top: 1.5rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
  }

  .session-controls span {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.7;
  }

  .session-controls button {
    border: 1px solid rgba(148, 163, 184, 0.4);
    border-radius: 999px;
    background: transparent;
    color: #e2e8f0;
    padding: 0.5rem 1.2rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
  }

  .session-controls button:hover:not(:disabled) {
    border-color: rgba(96, 165, 250, 0.6);
    color: #bfdbfe;
    transform: translateY(-1px);
  }

  .session-controls button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
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

  .cover-backfill-section {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 24px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    box-shadow: 0 18px 48px rgba(8, 13, 32, 0.35);
  }

  .cover-backfill-section header h2 {
    margin: 0 0 0.5rem;
    font-size: 1.35rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .cover-backfill-section header p {
    margin: 0;
    max-width: 760px;
    line-height: 1.6;
    opacity: 0.85;
  }

  .cover-backfill-status {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    align-items: flex-start;
    justify-content: space-between;
    background: rgba(30, 41, 59, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 18px;
    padding: 1.5rem;
  }

  .cover-backfill-status .status-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    flex: 1 1 auto;
  }

  .status-label {
    display: block;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    opacity: 0.6;
    margin-bottom: 0.25rem;
  }

  .status-note {
    display: block;
    font-size: 0.7rem;
    opacity: 0.6;
    margin-top: 0.15rem;
    text-transform: capitalize;
  }

  .cover-backfill-status strong {
    display: block;
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .cover-backfill-status button.secondary {
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.4);
    background: transparent;
    color: #e2e8f0;
    padding: 0.6rem 1.6rem;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
  }

  .cover-backfill-status button.secondary:hover:not(:disabled) {
    border-color: rgba(96, 165, 250, 0.6);
    color: #bfdbfe;
    transform: translateY(-1px);
  }

  .cover-backfill-status button.secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .cover-backfill-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 18px;
    padding: 1.5rem;
  }

  .cover-toggle {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .cover-toggle input {
    width: 1.25rem;
    height: 1.25rem;
    accent-color: #60a5fa;
  }

  .cover-backfill-grid {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }

  .cover-field label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.35rem;
  }

  .cover-input-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .cover-input-row input {
    flex: 0 0 120px;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.6);
    color: #e2e8f0;
    padding: 0.45rem 0.6rem;
  }

  .cover-input-row input.invalid {
    border-color: rgba(239, 68, 68, 0.6);
  }

  .cover-hint {
    font-size: 0.75rem;
    opacity: 0.6;
  }

  .cover-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .cover-actions button {
    border-radius: 999px;
    padding: 0.6rem 1.6rem;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border: none;
    cursor: pointer;
    transition: transform 0.15s ease, opacity 0.15s ease;
  }

  .cover-actions button:first-child {
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    color: #0f172a;
  }

  .cover-actions button:last-child {
    background: rgba(148, 163, 184, 0.15);
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.3);
  }

  .cover-actions button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    transform: none;
  }

  .cover-actions button:not(:disabled):hover {
    transform: translateY(-1px);
  }

  .content-axis-config {
    margin-top: 2.5rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 24px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    box-shadow: 0 18px 48px rgba(8, 13, 32, 0.35);
  }

  .content-axis-config header h2 {
    margin: 0 0 0.5rem;
    font-size: 1.35rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .content-axis-config header p {
    margin: 0;
    max-width: 720px;
    line-height: 1.6;
    opacity: 0.85;
  }

  .content-axis-config .axis-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .content-axis-config .axis-card {
    background: rgba(2, 6, 23, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 20px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.4);
  }

  .axis-card header h3 {
    margin: 0 0 0.35rem;
    font-size: 1.1rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .axis-card header p {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.5;
    opacity: 0.8;
  }

  .axis-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .axis-field label {
    display: block;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.35rem;
    color: rgba(226, 232, 240, 0.85);
  }

  .axis-input-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .axis-input-row input {
    width: 120px;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.65);
    color: #e2e8f0;
    padding: 0.45rem 0.65rem;
    font-size: 0.95rem;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .axis-input-row input:focus {
    outline: none;
    border-color: var(--axis-color);
    box-shadow: 0 0 0 3px var(--axis-color-soft);
  }

  .axis-input-row input.invalid {
    border-color: rgba(248, 113, 113, 0.75);
  }

  .axis-input-row input.dirty:not(.invalid) {
    border-color: var(--axis-color);
  }

  .axis-hint {
    font-size: 0.75rem;
    opacity: 0.7;
    flex: 1;
    min-width: 140px;
  }

  .axis-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 0.25rem;
  }

  .axis-actions button {
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.75);
    color: #e2e8f0;
    padding: 0.45rem 1.2rem;
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    cursor: pointer;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }

  .axis-actions button:first-child {
    background: linear-gradient(135deg, var(--axis-color), rgba(2, 6, 23, 0.9));
    border-color: var(--axis-color);
    color: #0f172a;
  }

  .axis-actions button:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  .axis-actions button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .prompt-section {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 24px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    box-shadow: 0 18px 48px rgba(2, 6, 23, 0.35);
  }

  .prompt-section header {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    justify-content: space-between;
    align-items: flex-start;
  }

  .prompt-section h2 {
    margin: 0 0 0.5rem;
    font-size: 1.35rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .prompt-section p {
    margin: 0;
    max-width: 640px;
    line-height: 1.6;
    opacity: 0.85;
  }

  .hurllol-card {
    min-width: 220px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(192, 132, 252, 0.22));
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 18px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    color: #e0f2fe;
    box-shadow: 0 16px 40px rgba(59, 130, 246, 0.25);
  }

  .hurllol-card span {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    opacity: 0.75;
  }

  .hurllol-card strong {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.05rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .hurllol-card small {
    font-size: 0.7rem;
    opacity: 0.75;
  }

  .prompt-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
    opacity: 0.85;
  }

  .manual-chip {
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: rgba(249, 115, 22, 0.18);
    border: 1px solid rgba(249, 115, 22, 0.4);
    color: #fdba74;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }

  .prompt-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .prompt-form label {
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.7;
  }

  .prompt-form textarea {
    width: 100%;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.85);
    color: #f8fafc;
    padding: 0.85rem 1rem;
    font-size: 1rem;
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.6;
    resize: vertical;
    min-height: 130px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .prompt-form textarea:focus {
    outline: none;
    border-color: rgba(56, 189, 248, 0.7);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
  }

  .prompt-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .prompt-actions button {
    border: none;
    border-radius: 999px;
    padding: 0.65rem 1.4rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    background: linear-gradient(135deg, #38bdf8, #6366f1);
    color: #0f172a;
    transition: transform 0.15s ease, filter 0.15s ease;
  }

  .prompt-actions button[type='button'] {
    background: rgba(148, 163, 184, 0.18);
    color: #e2e8f0;
  }

  .prompt-actions button:disabled {
    cursor: not-allowed;
    filter: grayscale(0.4);
    opacity: 0.7;
  }

  .prompt-actions button:not(:disabled):hover {
    transform: translateY(-1px);
  }

  .field-error {
    margin: 0;
    font-size: 0.85rem;
    color: #fecaca;
  }

  .prompt-stats {
    background: rgba(2, 6, 23, 0.6);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 1rem 1.25rem;
  }

  .prompt-stats summary {
    cursor: pointer;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(148, 163, 184, 0.85);
  }

  .prompt-stats pre {
    margin-top: 0.75rem;
    background: rgba(15, 23, 42, 0.9);
    border-radius: 12px;
    padding: 1rem;
    max-height: 320px;
    overflow: auto;
    font-size: 0.8rem;
    line-height: 1.45;
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

  @media (max-width: 720px) {
    .prompt-section header {
      flex-direction: column;
    }

    .hurllol-card {
      width: 100%;
    }
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
