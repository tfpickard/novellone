/**
 * Health Check Endpoint
 * GET /api/health
 *
 * Verifies Neo4j connectivity and returns system status.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { healthCheck, ensureTomExists } from './lib/neo4j.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // Check Neo4j connection
    const dbHealth = await healthCheck();

    if (!dbHealth.connected) {
      res.status(503).json({
        status: 'unhealthy',
        service: 'hurl-unmasks-recursive-literature-leaking-out-light',
        database: dbHealth,
      });
      return;
    }

    // Ensure Tom canonical node exists
    await ensureTomExists();

    res.status(200).json({
      status: 'healthy',
      service: 'hurl-unmasks-recursive-literature-leaking-out-light',
      database: dbHealth,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}
