const publicApiUrl = import.meta.env.VITE_PUBLIC_API_URL as string | undefined;
let base = publicApiUrl;

if (!base) {
  if (typeof window !== 'undefined') {
    // Browser fallback: use same origin (goes through Caddy/nginx proxy)
    // In production, this will be https://hurl.lol
    // In development, this will be http://localhost:4000
    base = window.location.origin;
  } else {
    // SSR in Docker fallback: use the Compose service DNS name
    base = 'http://backend:8000';
  }
}

const API_BASE = base.startsWith('http') ? base : `http://${base}`;

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
      const errorBody = await response.json();
      detail = errorBody;
      if (typeof errorBody === 'string' && errorBody) {
        message = errorBody;
      } else if (errorBody?.detail) {
        message = Array.isArray(errorBody.detail)
          ? errorBody.detail.map((entry: any) => entry?.msg ?? entry).join(', ')
          : errorBody.detail;
      }
    } catch (error) {
      // ignore parse errors and fall back to status message
      void error;
    }
    if (response.status === 401) {
      throw new UnauthorizedError(message, detail);
    }
    throw new ApiError(message, response.status, detail);
  }

  return response.json();
}

export type RuntimeConfig = {
  chapter_interval_seconds: number;
  evaluation_interval_chapters: number;
  quality_score_min: number;
  max_chapters_per_story: number;
  min_active_stories: number;
  max_active_stories: number;
  context_window_chapters: number;
};

export function getStories(params: URLSearchParams): Promise<any> {
  return request(`/api/stories?${params.toString()}`);
}

export function getStory(id: string): Promise<any> {
  return request(`/api/stories/${id}`);
}

export function killStory(id: string, reason?: string): Promise<any> {
  const body = reason ? { reason } : {};
  return request(`/api/stories/${id}/kill`, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

export function deleteStory(id: string): Promise<any> {
  return request(`/api/stories/${id}`, {
    method: 'DELETE'
  });
}

export function spawnStory(): Promise<any> {
  return request('/api/admin/spawn', {
    method: 'POST'
  });
}

export function resetSystem(): Promise<any> {
  return request('/api/admin/reset', {
    method: 'POST'
  });
}

export function getStats(): Promise<any> {
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

export function generateChapter(id: string): Promise<any> {
  return request(`/api/stories/${id}/generate`, {
    method: 'POST'
  });
}

// Universe Prompt API

export type UniversePromptSummary = {
  id: string;
  name: string;
  description: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  character_weight: number;
  setting_weight: number;
  theme_weight: number;
  lore_weight: number;
  element_count: number;
};

export type UniverseElement = {
  id: string;
  universe_prompt_id: string;
  source_story_id: string;
  element_type: string;
  name: string;
  description: string | null;
  metadata: any;
  extracted_at: string;
};

export type UniversePromptDetail = UniversePromptSummary & {
  characters: Record<string, any> | null;
  settings: Record<string, any> | null;
  themes: Record<string, any> | null;
  lore: Record<string, any> | null;
  narrative_constraints: string[] | null;
  elements: UniverseElement[];
};

export type UniversePromptCreate = {
  name: string;
  description?: string | null;
  characters?: Record<string, any> | null;
  settings?: Record<string, any> | null;
  themes?: Record<string, any> | null;
  lore?: Record<string, any> | null;
  narrative_constraints?: string[] | null;
  character_weight?: number;
  setting_weight?: number;
  theme_weight?: number;
  lore_weight?: number;
};

export type UniversePromptUpdate = Partial<UniversePromptCreate>;

export type CohesionMetric = {
  id: string;
  story_id: string;
  universe_prompt_id: string | null;
  character_recurrence_score: number;
  thematic_overlap_score: number;
  timeline_continuity_score: number;
  overall_cohesion_score: number;
  details: any;
  calculated_at: string;
};

export function getUniversePrompts(params?: URLSearchParams): Promise<{ total: number; page: number; page_size: number; items: UniversePromptSummary[] }> {
  const queryString = params ? `?${params.toString()}` : '';
  return request(`/api/universe-prompts${queryString}`);
}

export function getUniversePrompt(id: string): Promise<UniversePromptDetail> {
  return request(`/api/universe-prompts/${id}`);
}

export function createUniversePrompt(payload: UniversePromptCreate): Promise<UniversePromptDetail> {
  return request('/api/universe-prompts', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function updateUniversePrompt(id: string, payload: UniversePromptUpdate): Promise<UniversePromptDetail> {
  return request(`/api/universe-prompts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteUniversePrompt(id: string): Promise<{ message: string; deleted: boolean }> {
  return request(`/api/universe-prompts/${id}`, {
    method: 'DELETE'
  });
}

export function extractUniverseElements(promptId: string, storyIds: string[]): Promise<{ message: string; universe_prompt_id: string; story_count: number }> {
  return request(`/api/universe-prompts/${promptId}/extract`, {
    method: 'POST',
    body: JSON.stringify({ universe_prompt_id: promptId, story_ids: storyIds })
  });
}

export function getCohesionMetrics(params?: URLSearchParams): Promise<{ items: CohesionMetric[]; count: number }> {
  const queryString = params ? `?${params.toString()}` : '';
  return request(`/api/cohesion-metrics${queryString}`);
}

