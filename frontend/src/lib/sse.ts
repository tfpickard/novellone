/**
 * Server-Sent Events (SSE) Client
 * Replaces WebSocket for real-time story updates
 */

import { API_BASE } from './api';

// ───────────────────────────────────────────────────────────────────────────
// Event Types
// ───────────────────────────────────────────────────────────────────────────

export type SSEEventType =
  | 'new_story'
  | 'new_chapter'
  | 'story_completed'
  | 'story_evaluated'
  | 'system_reset';

export interface SSEStoryEvent {
  type: SSEEventType;
  storyId?: string;
  chapterNumber?: number;
  title?: string;
  reason?: string;
  data?: any;
}

// Legacy compatibility - map to old WebSocket format
export type StorySocketMessage =
  | { type: 'new_chapter'; story_id: string; chapter: any }
  | { type: 'story_completed'; story_id: string; reason: string; cover_image_url?: string }
  | { type: 'system_reset'; deleted_stories: number };

// ───────────────────────────────────────────────────────────────────────────
// SSE Connection
// ───────────────────────────────────────────────────────────────────────────

export function createStorySSE(onMessage: (message: StorySocketMessage) => void): EventSource {
  const endpoint = `${API_BASE}/api/events`;

  console.log(`[SSE] Connecting to: ${endpoint}`);

  const eventSource = new EventSource(endpoint);

  // Handle connection opened
  eventSource.addEventListener('open', () => {
    console.log('[SSE] Connection established');
  });

  // Handle connection errors
  eventSource.addEventListener('error', (error) => {
    console.error('[SSE] Connection error:', error);
    // EventSource automatically reconnects
  });

  // Handle new_story events
  eventSource.addEventListener('new_story', (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE] New story:', data);
      // Note: This doesn't map to old format, just log for now
    } catch (error) {
      console.error('[SSE] Failed to parse new_story event:', error);
    }
  });

  // Handle new_chapter events
  eventSource.addEventListener('new_chapter', (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE] New chapter:', data);

      // Map to legacy format
      onMessage({
        type: 'new_chapter',
        story_id: data.storyId,
        chapter: {
          id: data.chapterId,
          chapter_number: data.chapterNumber,
          content: data.content,
        },
      });
    } catch (error) {
      console.error('[SSE] Failed to parse new_chapter event:', error);
    }
  });

  // Handle story_completed events
  eventSource.addEventListener('story_completed', (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE] Story completed:', data);

      // Map to legacy format
      onMessage({
        type: 'story_completed',
        story_id: data.storyId,
        reason: data.reason || 'Completed',
        cover_image_url: data.coverImageUrl,
      });
    } catch (error) {
      console.error('[SSE] Failed to parse story_completed event:', error);
    }
  });

  // Handle story_evaluated events
  eventSource.addEventListener('story_evaluated', (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE] Story evaluated:', data);
      // This doesn't have a legacy equivalent, just log
    } catch (error) {
      console.error('[SSE] Failed to parse story_evaluated event:', error);
    }
  });

  // Handle system_reset events
  eventSource.addEventListener('system_reset', (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE] System reset:', data);

      // Map to legacy format
      onMessage({
        type: 'system_reset',
        deleted_stories: data.deletedStories || 0,
      });
    } catch (error) {
      console.error('[SSE] Failed to parse system_reset event:', error);
    }
  });

  // Handle generic data messages (fallback)
  eventSource.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);

      // Handle connected event
      if (data.type === 'connected') {
        console.log('[SSE] Connected at', new Date(data.timestamp));
        return;
      }

      console.log('[SSE] Generic message:', data);
    } catch (error) {
      console.error('[SSE] Failed to parse message:', error);
    }
  });

  return eventSource;
}

// ───────────────────────────────────────────────────────────────────────────
// Legacy WebSocket Compatibility
// ───────────────────────────────────────────────────────────────────────────

/**
 * Creates an SSE connection that mimics the old WebSocket interface.
 * Drop-in replacement for createStorySocket.
 *
 * @deprecated Use createStorySSE directly
 */
export function createStorySocket(onMessage: (message: StorySocketMessage) => void): { close: () => void } {
  const eventSource = createStorySSE(onMessage);

  // Return object with close method to match WebSocket interface
  return {
    close: () => {
      console.log('[SSE] Closing connection');
      eventSource.close();
    },
  };
}

// ───────────────────────────────────────────────────────────────────────────
// Modern SSE API
// ───────────────────────────────────────────────────────────────────────────

export interface StoryEventHandlers {
  onNewStory?: (data: { storyId: string; title: string }) => void;
  onNewChapter?: (data: { storyId: string; chapterNumber: number; title: string }) => void;
  onStoryCompleted?: (data: { storyId: string; reason: string; coverImageUrl?: string }) => void;
  onStoryEvaluated?: (data: { storyId: string; overallScore: number; shouldContinue: boolean }) => void;
  onSystemReset?: (data: { deletedStories: number }) => void;
  onConnected?: () => void;
  onError?: (error: Event) => void;
}

/**
 * Create an SSE connection with typed event handlers.
 * Modern API for real-time story updates.
 */
export function createStoryEventSource(handlers: StoryEventHandlers): EventSource {
  const endpoint = `${API_BASE}/api/events`;
  const eventSource = new EventSource(endpoint);

  eventSource.addEventListener('open', () => {
    console.log('[SSE] Connection established');
    handlers.onConnected?.();
  });

  eventSource.addEventListener('error', (error) => {
    console.error('[SSE] Connection error:', error);
    handlers.onError?.(error);
  });

  eventSource.addEventListener('new_story', (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onNewStory?.(data);
    } catch (error) {
      console.error('[SSE] Failed to parse new_story event:', error);
    }
  });

  eventSource.addEventListener('new_chapter', (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onNewChapter?.(data);
    } catch (error) {
      console.error('[SSE] Failed to parse new_chapter event:', error);
    }
  });

  eventSource.addEventListener('story_completed', (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onStoryCompleted?.(data);
    } catch (error) {
      console.error('[SSE] Failed to parse story_completed event:', error);
    }
  });

  eventSource.addEventListener('story_evaluated', (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onStoryEvaluated?.(data);
    } catch (error) {
      console.error('[SSE] Failed to parse story_evaluated event:', error);
    }
  });

  eventSource.addEventListener('system_reset', (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onSystemReset?.(data);
    } catch (error) {
      console.error('[SSE] Failed to parse system_reset event:', error);
    }
  });

  eventSource.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'connected') {
        console.log('[SSE] Connected at', new Date(data.timestamp));
      }
    } catch (error) {
      // Ignore parse errors for keepalive comments
    }
  });

  return eventSource;
}

// ───────────────────────────────────────────────────────────────────────────
// Helper: Auto-reconnecting SSE
// ───────────────────────────────────────────────────────────────────────────

/**
 * Creates an auto-reconnecting SSE connection with exponential backoff.
 * Handles connection failures gracefully.
 */
export function createReconnectingSSE(
  handlers: StoryEventHandlers,
  options: {
    maxRetries?: number;
    initialDelay?: number;
    maxDelay?: number;
  } = {}
): { close: () => void; reconnect: () => void } {
  const { maxRetries = Infinity, initialDelay = 1000, maxDelay = 30000 } = options;

  let eventSource: EventSource | null = null;
  let retryCount = 0;
  let retryTimeout: number | null = null;
  let isClosed = false;

  function connect() {
    if (isClosed) return;

    eventSource = createStoryEventSource({
      ...handlers,
      onConnected: () => {
        retryCount = 0; // Reset retry count on successful connection
        handlers.onConnected?.();
      },
      onError: (error) => {
        handlers.onError?.(error);

        // Auto-reconnect with exponential backoff
        if (retryCount < maxRetries) {
          const delay = Math.min(initialDelay * Math.pow(2, retryCount), maxDelay);
          console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})`);

          retryTimeout = window.setTimeout(() => {
            retryCount++;
            connect();
          }, delay);
        } else {
          console.error('[SSE] Max retries reached, giving up');
        }
      },
    });
  }

  connect();

  return {
    close: () => {
      isClosed = true;
      if (retryTimeout) {
        clearTimeout(retryTimeout);
        retryTimeout = null;
      }
      eventSource?.close();
      console.log('[SSE] Connection closed');
    },
    reconnect: () => {
      retryCount = 0;
      eventSource?.close();
      connect();
    },
  };
}
