/**
 * API Client for Vercel Serverless Backend
 * Updated for Neo4j + Vercel architecture
 */

import type { ContentAxisSettingsMap } from './contentAxes';

// ───────────────────────────────────────────────────────────────────────────
// API Base URL Configuration
// ───────────────────────────────────────────────────────────────────────────

const publicApiUrl = import.meta.env.VITE_PUBLIC_API_URL as string | undefined;
let base = publicApiUrl;

if (!base) {
  if (typeof window !== 'undefined') {
    // Browser: use same origin
    base = window.location.origin;
  } else {
    // SSR: use Vercel URL or localhost
    base = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : 'http://localhost:3000';
  }
}

const API_BASE = base.startsWith('http') ? base : `https://${base}`;

// ───────────────────────────────────────────────────────────────────────────
// Error Classes
// ───────────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message: string, detail?: unknown) {
    super(message, 401, detail);
    this.name = 'UnauthorizedError';
  }
}

// ───────────────────────────────────────────────────────────────────────────
// API Response Types (Vercel format)
// ───────────────────────────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ───────────────────────────────────────────────────────────────────────────
// Request Helper
// ───────────────────────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: init?.credentials ?? 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    let message = `API request failed: ${response.status}`;
    let detail: unknown;

    try {
      const errorBody: ApiResponse = await response.json();
      detail = errorBody;
      if (errorBody.error) {
        message = errorBody.error;
      }
    } catch (error) {
      // Ignore parse errors
      void error;
    }

    if (response.status === 401) {
      throw new UnauthorizedError(message, detail);
    }
    throw new ApiError(message, response.status, detail);
  }

  // Handle new API response format
  const result: ApiResponse<T> = await response.json();

  if (!result.success) {
    throw new ApiError(result.error || 'Request failed', response.status);
  }

  return result.data as T;
}

// ───────────────────────────────────────────────────────────────────────────
// Type Definitions (Updated for Neo4j)
// ───────────────────────────────────────────────────────────────────────────

export type StoryStatus = 'active' | 'completed' | 'killed';

export interface Story {
  id: string;
  title: string;
  premise: string;
  status: StoryStatus;
  createdAt: Date | string;
  completedAt?: Date | string;
  completionReason?: string;
  coverImageUrl?: string;
  styleAuthors: string[];
  narrativePerspective: string;
  tone: string;
  genreTags: string[];
  estimatedReadingMinutes: number;
  totalTokens: number;
}

export interface Chapter {
  id: string;
  chapterNumber: number;
  content: string;
  createdAt: Date | string;
  tokensUsed: number;
  generationTimeMs: number;
  modelUsed: string;
  wordCount: number;
  contentLevels: ContentLevels;
  chaos?: ChaosParameters;
}

export interface ChaosParameters {
  absurdity: number;
  surrealism: number;
  ridiculousness: number;
  insanity: number;
}

export interface ContentLevels {
  sexualContent: number;
  violence: number;
  strongLanguage: number;
  drugUse: number;
  horrorSuspense: number;
  goreGraphicImagery: number;
  romanceFocus: number;
  crimeIllicitActivity: number;
  politicalIdeology: number;
  supernaturalOccult: number;
  cosmicHorror: number;
  bureaucraticSatire: number;
  archivalGlitch: number;
}

export interface Evaluation {
  id: string;
  chapterNumber: number;
  overallScore: number;
  coherenceScore: number;
  noveltyScore: number;
  engagementScore: number;
  pacingScore: number;
  shouldContinue: boolean;
  reasoning: string;
  issues: string[];
  evaluatedAt: Date | string;
  modelUsed: string;
}

export interface Entity {
  id: string;
  name: string;
  canonicalName: string;
  entityType: string;
  description?: string;
  aliases: string[];
  firstSeenAt: Date | string;
  totalMentions: number;
  importance: number;
  updatedAt: Date | string;
}

export interface EntityMention {
  entity: Entity;
  firstChapterNumber: number;
  lastChapterNumber: number;
  mentionCount: number;
  importance: number;
  sentiment: string;
  relationshipToTom: string;
}

export interface TomVariant {
  variantName: string;
  role: string;
  characterization?: string;
  firstAppearanceChapter: number;
}

export interface StoryWithDetails extends Story {
  chapters: Chapter[];
  evaluations: Evaluation[];
  entities: EntityMention[];
  tomVariant?: TomVariant;
}

export interface StatsResponse {
  stories: {
    active: number;
    completed: number;
    killed: number;
    total: number;
  };
  chapters: {
    total: number;
    recentChapters: Chapter[];
  };
  tokens: {
    total: number;
  };
  chaos: ChaosParameters;
  content: Partial<ContentLevels>;
  entities: {
    total: number;
    topEntities: Array<{
      name: string;
      mentions: number;
      importance: number;
    }>;
  };
  universes: {
    total: number;
    clusters: number;
  };
  tom: {
    totalAppearances: number;
    variants: string[];
  };
}

export interface RuntimeConfig {
  minActiveStories: number;
  maxActiveStories: number;
  maxChaptersPerStory: number;
  chapterIntervalMinutes: number;
  evaluationIntervalChapters: number;
  qualityScoreMin: number;
  coverArtBackfillEnabled: boolean;
  coverArtBackfillBatchSize: number;
  modelPremise: string;
  modelChapter: string;
  modelEvaluation: string;
  modelCoverArt: string;
  maxTokensPremise: number;
  maxTokensChapter: number;
  maxTokensEvaluation: number;
}

// ───────────────────────────────────────────────────────────────────────────
// API Functions
// ───────────────────────────────────────────────────────────────────────────

export function getStories(params?: {
  status?: StoryStatus;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<Story>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  return request(`/api/stories${query ? `?${query}` : ''}`);
}

export function getStory(id: string): Promise<StoryWithDetails> {
  return request(`/api/stories/${id}`);
}

export function killStory(id: string, reason?: string): Promise<Story> {
  const body = reason ? { reason } : {};
  return request(`/api/stories/${id}/kill`, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

export function deleteStory(id: string): Promise<void> {
  return request(`/api/stories/${id}`, {
    method: 'DELETE'
  });
}

export function spawnStory(): Promise<Story> {
  return request('/api/admin/spawn', {
    method: 'POST'
  });
}

export function resetSystem(confirm: string = 'DELETE_ALL_STORIES'): Promise<void> {
  return request('/api/admin/reset', {
    method: 'POST',
    body: JSON.stringify({ confirm })
  });
}

export function getStats(): Promise<StatsResponse> {
  return request('/api/stats');
}

export function getConfig(): Promise<RuntimeConfig> {
  return request('/api/config');
}

export function updateConfig(payload: Partial<RuntimeConfig>): Promise<RuntimeConfig> {
  return request('/api/config', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

// ───────────────────────────────────────────────────────────────────────────
// Health Check
// ───────────────────────────────────────────────────────────────────────────

export function getHealth(): Promise<{
  status: string;
  database: {
    connected: boolean;
    serverInfo?: {
      version: string;
      address: string;
    };
  };
}> {
  return request('/api/health');
}

// ───────────────────────────────────────────────────────────────────────────
// Legacy Compatibility (TODO: Remove after frontend migration)
// ───────────────────────────────────────────────────────────────────────────

export function getUniverseOverview(): Promise<any> {
  // TODO: Implement universe overview endpoint
  console.warn('Universe overview not yet implemented in new API');
  return Promise.resolve({ entities: [], themes: [], links: [] });
}

export function getUniverseMetrics(): Promise<any> {
  // TODO: Implement universe metrics endpoint
  console.warn('Universe metrics not yet implemented in new API');
  return Promise.resolve({});
}

export function getStoryRecommendations(): Promise<any> {
  // TODO: Implement recommendations endpoint
  console.warn('Recommendations not yet implemented in new API');
  return Promise.resolve({ recommended: [] });
}

export function generateChapter(id: string): Promise<any> {
  // TODO: Implement manual chapter generation endpoint
  console.warn('Manual chapter generation not yet implemented in new API');
  return Promise.resolve({});
}

export function runCoverBackfill(): Promise<any> {
  // Cron job handles this automatically now
  console.warn('Cover backfill now runs automatically via cron job');
  return Promise.resolve({});
}

// Stub types for legacy compatibility
export type EntityOverridePayload = any;
export type EntityOverrideUpdatePayload = any;

export function createEntityOverride(payload: EntityOverridePayload): Promise<any> {
  console.warn('Entity overrides not yet implemented in new API');
  return Promise.resolve({});
}

export function updateEntityOverride(id: string, payload: EntityOverrideUpdatePayload): Promise<any> {
  console.warn('Entity overrides not yet implemented in new API');
  return Promise.resolve({});
}

export function deleteEntityOverride(id: string): Promise<any> {
  console.warn('Entity overrides not yet implemented in new API');
  return Promise.resolve({});
}

export function listEntityOverrides(params?: any): Promise<any> {
  console.warn('Entity overrides not yet implemented in new API');
  return Promise.resolve({ overrides: [] });
}

export function queueMetaRefresh(payload?: any): Promise<any> {
  console.warn('Meta refresh not yet implemented in new API');
  return Promise.resolve({});
}

export type PremisePromptState = any;
export type PromptStateResponse = any;
export type PromptUpdatePayload = any;
export type HurllolBanner = any;

export function getPromptState(): Promise<PromptStateResponse> {
  console.warn('Prompt state not yet implemented in new API');
  return Promise.resolve({});
}

export function updatePromptState(payload: PromptUpdatePayload): Promise<PromptStateResponse> {
  console.warn('Prompt state updates not yet implemented in new API');
  return Promise.resolve({});
}

export function getHurllol(): Promise<HurllolBanner> {
  console.warn('Hurllol banner not yet implemented in new API');
  return Promise.resolve({ title: null, components: [], generated_at: null });
}

// Export API base for SSE
export { API_BASE };
