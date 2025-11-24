/**
 * Server-Sent Events (SSE) Endpoint
 * GET /api/events
 *
 * Streams real-time updates about story generation, new chapters, and evaluations.
 * Uses Vercel KV for pub/sub-like functionality.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { kv } from '@vercel/kv';

// Event types
export type EventType =
  | 'new_story'
  | 'new_chapter'
  | 'story_completed'
  | 'story_evaluated'
  | 'system_reset';

export interface SSEEvent {
  type: EventType;
  data: unknown;
  timestamp: number;
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering

  // Send initial connection message
  res.write(`data: ${JSON.stringify({ type: 'connected', timestamp: Date.now() })}\n\n`);

  // Poll for events from Vercel KV
  // (In production, you'd want a proper pub/sub system like Pusher or Ably)

  let lastEventId = 0;
  const pollInterval = 5000; // 5 seconds

  const poll = async () => {
    try {
      // Fetch recent events from Vercel KV
      const events = await kv.zrange<SSEEvent>(
        'sse:events',
        lastEventId,
        '+inf',
        {
          byScore: true,
          offset: 0,
          count: 10,
        }
      );

      for (const event of events) {
        res.write(`event: ${event.type}\n`);
        res.write(`data: ${JSON.stringify(event.data)}\n`);
        res.write(`id: ${event.timestamp}\n\n`);

        lastEventId = event.timestamp;
      }

      // Send keepalive comment every 30 seconds
      if (Date.now() % 30000 < pollInterval) {
        res.write(': keepalive\n\n');
      }
    } catch (error) {
      console.error('Error polling for events:', error);
    }
  };

  // Poll for events
  const intervalId = setInterval(poll, pollInterval);

  // Clean up on connection close
  req.on('close', () => {
    clearInterval(intervalId);
    console.log('SSE connection closed');
  });

  // Keep connection alive (Vercel has a 60s function timeout, but Edge functions can run longer)
  // For long-lived connections, consider using Vercel Edge Functions
}

/**
 * Publish an event to all SSE clients.
 * Call this from worker functions when events occur.
 */
export async function publishEvent(event: SSEEvent): Promise<void> {
  try {
    // Store event in Vercel KV with timestamp as score
    await kv.zadd('sse:events', {
      score: event.timestamp,
      member: JSON.stringify(event),
    });

    // Keep only last 100 events (cleanup old events)
    await kv.zremrangebyrank('sse:events', 0, -101);

    console.log(`📡 Published SSE event: ${event.type}`);
  } catch (error) {
    console.error('Error publishing SSE event:', error);
  }
}

/**
 * Helper to create and publish events from worker functions.
 */
export async function emitStoryEvent(
  type: EventType,
  data: unknown
): Promise<void> {
  await publishEvent({
    type,
    data,
    timestamp: Date.now(),
  });
}
