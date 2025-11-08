const publicApiUrl = import.meta.env.VITE_PUBLIC_API_URL as string | undefined;
let base = publicApiUrl;

if (!base) {
  if (typeof window !== 'undefined') {
    // Browser fallback: call the host you’re visiting on port 8000
    base = `${window.location.hostname}:8000`;
  } else {
    // SSR in Docker fallback: use the Compose service DNS name
    base = 'backend:8000';
  }
}

const API_BASE = base.startsWith('http') ? base : `http://${base}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    let message = `API request failed: ${response.status}`;
    try {
      const errorBody = await response.json();
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
    throw new Error(message);
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

