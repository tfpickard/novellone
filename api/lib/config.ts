/**
 * Configuration Management
 *
 * Runtime configuration stored in Neo4j SystemConfig nodes.
 * Provides defaults and utilities for reading/updating configuration.
 */

import { executeRead, executeWrite } from './neo4j.js';
import type { RuntimeConfig } from './types.js';

// ───────────────────────────────────────────────────────────────────────────
// Default Configuration
// ───────────────────────────────────────────────────────────────────────────

export const DEFAULT_CONFIG: RuntimeConfig = {
  // Story pool management
  minActiveStories: 3,
  maxActiveStories: 8,
  maxChaptersPerStory: 20,

  // Timing (in minutes for cron jobs)
  chapterIntervalMinutes: 15,
  evaluationIntervalChapters: 3,

  // Quality thresholds
  qualityScoreMin: 0.6,

  // Cover art generation
  coverArtBackfillEnabled: true,
  coverArtBackfillBatchSize: 5,

  // OpenAI models
  modelPremise: 'gpt-4-turbo-preview',
  modelChapter: 'gpt-4-turbo-preview',
  modelEvaluation: 'gpt-4-turbo-preview',
  modelCoverArt: 'dall-e-3',

  // Token budgets
  maxTokensPremise: 2000,
  maxTokensChapter: 3000,
  maxTokensEvaluation: 1500,
};

// ───────────────────────────────────────────────────────────────────────────
// Get Configuration
// ───────────────────────────────────────────────────────────────────────────

/**
 * Get the current runtime configuration.
 * Merges stored config with defaults.
 */
export async function getConfig(): Promise<RuntimeConfig> {
  const query = `
    MATCH (sc:SystemConfig)
    RETURN sc.key as key, sc.value as value
  `;

  const result = await executeRead(query);

  const storedConfig: Partial<RuntimeConfig> = {};
  for (const record of result.records) {
    const key = record.get('key') as keyof RuntimeConfig;
    const value = record.get('value');
    storedConfig[key] = value;
  }

  return { ...DEFAULT_CONFIG, ...storedConfig };
}

/**
 * Get a single configuration value.
 *
 * @param key - Configuration key
 * @returns Configuration value or default
 */
export async function getConfigValue<K extends keyof RuntimeConfig>(
  key: K
): Promise<RuntimeConfig[K]> {
  const query = `
    MATCH (sc:SystemConfig {key: $key})
    RETURN sc.value as value
  `;

  const result = await executeRead(query, { key });

  if (result.records.length === 0) {
    return DEFAULT_CONFIG[key];
  }

  return result.records[0].get('value') as RuntimeConfig[K];
}

// ───────────────────────────────────────────────────────────────────────────
// Update Configuration
// ───────────────────────────────────────────────────────────────────────────

/**
 * Update configuration values.
 *
 * @param updates - Partial configuration object with values to update
 */
export async function updateConfig(
  updates: Partial<RuntimeConfig>
): Promise<void> {
  for (const [key, value] of Object.entries(updates)) {
    await updateConfigValue(key as keyof RuntimeConfig, value);
  }
}

/**
 * Update a single configuration value.
 *
 * @param key - Configuration key
 * @param value - New value
 */
export async function updateConfigValue<K extends keyof RuntimeConfig>(
  key: K,
  value: RuntimeConfig[K]
): Promise<void> {
  const query = `
    MERGE (sc:SystemConfig {key: $key})
    SET sc.value = $value,
        sc.updatedAt = timestamp()
    RETURN sc
  `;

  await executeWrite(query, { key, value });
}

// ───────────────────────────────────────────────────────────────────────────
// Reset Configuration
// ───────────────────────────────────────────────────────────────────────────

/**
 * Reset all configuration to defaults.
 */
export async function resetConfig(): Promise<void> {
  const query = `
    MATCH (sc:SystemConfig)
    DELETE sc
  `;

  await executeWrite(query);

  // Re-insert defaults
  for (const [key, value] of Object.entries(DEFAULT_CONFIG)) {
    await updateConfigValue(key as keyof RuntimeConfig, value);
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Validation
// ───────────────────────────────────────────────────────────────────────────

/**
 * Validate configuration values.
 * Throws an error if any value is invalid.
 */
export function validateConfig(config: Partial<RuntimeConfig>): void {
  if (config.minActiveStories !== undefined && config.minActiveStories < 1) {
    throw new Error('minActiveStories must be at least 1');
  }

  if (
    config.maxActiveStories !== undefined &&
    config.minActiveStories !== undefined &&
    config.maxActiveStories < config.minActiveStories
  ) {
    throw new Error('maxActiveStories must be >= minActiveStories');
  }

  if (
    config.maxChaptersPerStory !== undefined &&
    config.maxChaptersPerStory < 1
  ) {
    throw new Error('maxChaptersPerStory must be at least 1');
  }

  if (
    config.chapterIntervalMinutes !== undefined &&
    config.chapterIntervalMinutes < 1
  ) {
    throw new Error('chapterIntervalMinutes must be at least 1');
  }

  if (
    config.evaluationIntervalChapters !== undefined &&
    config.evaluationIntervalChapters < 1
  ) {
    throw new Error('evaluationIntervalChapters must be at least 1');
  }

  if (
    config.qualityScoreMin !== undefined &&
    (config.qualityScoreMin < 0 || config.qualityScoreMin > 1)
  ) {
    throw new Error('qualityScoreMin must be between 0 and 1');
  }
}
