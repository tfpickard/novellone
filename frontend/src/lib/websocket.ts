export type StorySocketMessage =
  | { type: 'new_chapter'; story_id: string; chapter: any }
  | { type: 'story_completed'; story_id: string; reason: string; cover_image_url?: string }
  | { type: 'system_reset'; deleted_stories: number };

export function createStorySocket(onMessage: (message: StorySocketMessage) => void) {
  let endpoint = import.meta.env.VITE_PUBLIC_WS_URL as string | undefined;
  if (!endpoint) {
    if (typeof window !== 'undefined') {
      // Use same host as current page (goes through Caddy/nginx proxy)
      // In production: wss://hurl.lol/ws/stories
      // In development: ws://localhost:4000/ws/stories
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      endpoint = `${scheme}://${window.location.host}/ws/stories`;
    } else {
      // SSR fallback
      endpoint = 'ws://backend:8000/ws/stories';
    }
  }

  const socket = new WebSocket(endpoint);
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Failed to parse socket message', error);
    }
  };

  return socket;
}
