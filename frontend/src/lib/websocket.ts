/**
 * WebSocket Compatibility Layer
 *
 * This module maintains backwards compatibility with the old WebSocket API
 * while using Server-Sent Events (SSE) under the hood.
 *
 * @deprecated Use `import { createStorySSE, createStoryEventSource } from './sse'` instead
 */

export { createStorySocket, type StorySocketMessage } from './sse';

// Note: The WebSocket has been replaced with Server-Sent Events (SSE).
// The createStorySocket function now returns an object with a close() method
// that mimics the WebSocket API for backwards compatibility.
//
// For new code, use the SSE API directly:
// import { createStoryEventSource } from './sse';
