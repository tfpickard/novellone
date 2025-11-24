/**
 * Story Generation Cron Job
 * Runs every 15 minutes (configured in vercel.json)
 *
 * Tasks:
 * - Maintain story pool (spawn new stories if needed)
 * - Generate chapters for active stories
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import {
  maintainStoryPool,
  generateChaptersForActiveStories,
} from '../lib/story-worker.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  // Verify this is a cron request (Vercel sets this header)
  const authHeader = req.headers.authorization;
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  const startTime = Date.now();

  console.log('🔄 Starting story generation cron job...');

  try {
    // Step 1: Maintain story pool
    console.log('📊 Maintaining story pool...');
    const poolResult = await maintainStoryPool();
    console.log(`  ✓ Spawned: ${poolResult.spawned}, Completed: ${poolResult.completed}`);

    // Step 2: Generate chapters
    console.log('✍️  Generating chapters...');
    const chapterResult = await generateChaptersForActiveStories();
    console.log(`  ✓ Generated: ${chapterResult.generated} chapters`);

    const duration = Date.now() - startTime;

    console.log(`✅ Cron job completed in ${duration}ms`);

    res.status(200).json({
      success: true,
      message: 'Story generation cron job completed',
      duration,
      results: {
        storiesSpawned: poolResult.spawned,
        storiesCompleted: poolResult.completed,
        chaptersGenerated: chapterResult.generated,
      },
    });
  } catch (error) {
    console.error('❌ Error in story generation cron:', error);

    const duration = Date.now() - startTime;

    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration,
    });
  }
}
