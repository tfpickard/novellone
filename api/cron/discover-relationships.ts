/**
 * Entity Relationship Discovery Cron Job
 * Runs daily (configured in vercel.json)
 *
 * Tasks:
 * - Discover entity co-occurrence patterns
 * - Create RELATED_TO relationships
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { discoverEntityRelationships } from '../lib/entity-operations.js';

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

  console.log('🔄 Starting entity relationship discovery cron job...');

  try {
    // Discover relationships (entities that appear together in 2+ stories)
    console.log('🔗 Discovering entity relationships...');
    const relationshipsCreated = await discoverEntityRelationships(2);
    console.log(`  ✓ Created/updated: ${relationshipsCreated} relationships`);

    const duration = Date.now() - startTime;

    console.log(`✅ Cron job completed in ${duration}ms`);

    res.status(200).json({
      success: true,
      message: 'Entity relationship discovery completed',
      duration,
      results: {
        relationshipsCreated,
      },
    });
  } catch (error) {
    console.error('❌ Error in entity relationship discovery cron:', error);

    const duration = Date.now() - startTime;

    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration,
    });
  }
}
