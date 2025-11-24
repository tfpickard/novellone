/**
 * Story Evaluation Cron Job
 * Runs every 30 minutes (configured in vercel.json)
 *
 * Tasks:
 * - Evaluate active stories that are due for evaluation
 * - Complete stories that fall below quality threshold
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { evaluateActiveStories } from '../lib/story-worker.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  // Verify this is a cron request
  const authHeader = req.headers.authorization;
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  const startTime = Date.now();

  console.log('🔄 Starting story evaluation cron job...');

  try {
    // Evaluate active stories
    console.log('📊 Evaluating active stories...');
    const result = await evaluateActiveStories();
    console.log(`  ✓ Evaluated: ${result.evaluated}, Completed: ${result.completed}`);

    const duration = Date.now() - startTime;

    console.log(`✅ Cron job completed in ${duration}ms`);

    res.status(200).json({
      success: true,
      message: 'Story evaluation cron job completed',
      duration,
      results: {
        storiesEvaluated: result.evaluated,
        storiesCompleted: result.completed,
      },
    });
  } catch (error) {
    console.error('❌ Error in story evaluation cron:', error);

    const duration = Date.now() - startTime;

    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration,
    });
  }
}
