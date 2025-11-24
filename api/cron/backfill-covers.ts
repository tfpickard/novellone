/**
 * Cover Art Backfill Cron Job
 * Runs hourly (configured in vercel.json)
 *
 * Tasks:
 * - Generate cover art for completed stories that don't have covers
 * - Upload to Vercel Blob storage
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { backfillCoverArt } from '../lib/story-worker.js';

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

  console.log('🔄 Starting cover art backfill cron job...');

  try {
    // Backfill cover art
    console.log('🎨 Backfilling cover art...');
    const result = await backfillCoverArt();
    console.log(`  ✓ Generated: ${result.generated} covers`);

    const duration = Date.now() - startTime;

    console.log(`✅ Cron job completed in ${duration}ms`);

    res.status(200).json({
      success: true,
      message: 'Cover art backfill cron job completed',
      duration,
      results: {
        coversGenerated: result.generated,
      },
    });
  } catch (error) {
    console.error('❌ Error in cover art backfill cron:', error);

    const duration = Date.now() - startTime;

    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration,
    });
  }
}
