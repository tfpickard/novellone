export type StorySocketMessage =
  | { type: 'new_chapter'; story_id: string; chapter: any }
  | {
      type: 'story_completed';
      story_id: string;
      reason: string;
      summary?: string | null;
      cover_art_url?: string | null;
    };

export function createStorySocket(onMessage: (message: StorySocketMessage) => void) {
  let endpoint = import.meta.env.VITE_PUBLIC_WS_URL as string | undefined;
  if (!endpoint) {
    if (typeof window !== 'undefined') {
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      endpoint = `${scheme}://${window.location.hostname}:8000/ws/stories`;
    } else {
      endpoint = 'ws://localhost:8000/ws/stories';
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
