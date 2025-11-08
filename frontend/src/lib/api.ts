const publicApiUrl = import.meta.env.VITE_PUBLIC_API_URL as string | undefined;
let base = publicApiUrl;
if (!base) {
  if (typeof window !== 'undefined') {
    base = `${window.location.hostname}:8000`;
  } else {
    base = 'localhost:8000';
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
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export function getStories(params: URLSearchParams): Promise<any> {
  return request(`/api/stories?${params.toString()}`);
}

export function getStory(id: string): Promise<any> {
  return request(`/api/stories/${id}`);
}

export function getStats(): Promise<any> {
  return request('/api/stats');
}

export function getConfig(): Promise<any> {
  return request('/api/config');
}
