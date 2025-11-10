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
  openai_model: string;
  openai_premise_model: string;
  openai_eval_model: string;
  openai_temperature_chapter: number;
  openai_temperature_premise: number;
  openai_temperature_eval: number;
  premise_prompt_refresh_interval: number;
  premise_prompt_stats_window: number;
  premise_prompt_variation_strength: number;
  chaos_initial_min: number;
  chaos_initial_max: number;
  chaos_increment_min: number;
  chaos_increment_max: number;
};

export type PremisePromptState = {
  directives: string[];
  rationale: string | null;
  generated_at: string | null;
  variation_strength: number | null;
  manual_override: boolean;
  stats_snapshot?: Record<string, unknown> | null;
  hurllol_title: string | null;
  hurllol_title_components?: string[] | null;
  hurllol_title_generated_at: string | null;
};

export type PromptStateResponse = {
  premise: PremisePromptState;
};

export type PromptUpdatePayload = {
  directives?: string[];
  rationale?: string | null;
};

export type HurllolBanner = {
  title: string | null;
  components: string[];
  generated_at: string | null;
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

export function getUniverseOverview(): Promise<any> {
  return request('/api/universe/overview');
}

export function getUniverseMetrics(): Promise<any> {
  return request('/api/universe/metrics');
}

export function getStoryRecommendations(): Promise<any> {
  return request('/api/recommendations');
}

export type EntityOverridePayload = {
  story_id?: string | null;
  name: string;
  action: 'suppress' | 'merge';
  target_name?: string | null;
  notes?: string | null;
};

export type EntityOverrideUpdatePayload = Partial<{
  name: string;
  action: 'suppress' | 'merge';
  target_name: string | null;
  notes: string | null;
}>;

export function createEntityOverride(payload: EntityOverridePayload): Promise<any> {
  return request('/api/universe/overrides', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function updateEntityOverride(id: string, payload: EntityOverrideUpdatePayload): Promise<any> {
  return request(`/api/universe/overrides/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteEntityOverride(id: string): Promise<any> {
  return request(`/api/universe/overrides/${id}`, {
    method: 'DELETE'
  });
}

export function listEntityOverrides(params?: { story_id?: string | null }): Promise<any> {
  const search = new URLSearchParams();
  if (params?.story_id) {
    search.set('story_id', params.story_id);
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : '';
  return request(`/api/universe/overrides${suffix}`);
}

export function queueMetaRefresh(payload?: { story_id?: string | null; full_rebuild?: boolean }): Promise<any> {
  return request('/api/universe/refresh', {
    method: 'POST',
    body: JSON.stringify(payload ?? {})
  });
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

export function getPromptState(): Promise<PromptStateResponse> {
  return request('/api/prompts');
}

export function updatePromptState(payload: PromptUpdatePayload): Promise<PromptStateResponse> {
  return request('/api/prompts', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function getHurllol(): Promise<HurllolBanner> {
  return request('/api/hurllol');
}

export function generateChapter(id: string): Promise<any> {
  return request(`/api/stories/${id}/generate`, {
    method: 'POST'
  });
}

