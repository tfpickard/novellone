/**
 * Universe Graph Endpoint
 * GET /api/universe/graph
 *
 * Returns graph data for visualization: stories as nodes, connections as edges.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { executeRead, toNumber } from '../lib/neo4j.js';
import type { ApiResponse } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const minWeight = parseFloat(req.query.minWeight as string) || 0.3;
    const limit = Math.min(parseInt(req.query.limit as string) || 50, 100);

    // Get stories and their universe connections
    const query = `
      // Get all stories with connections
      MATCH (s1:Story)-[r:SHARES_UNIVERSE_WITH]->(s2:Story)
      WHERE r.weight >= $minWeight
        AND s1.status IN ['active', 'completed']
        AND s2.status IN ['active', 'completed']

      // Collect story data
      WITH s1, s2, r
      RETURN {
        id: s1.id,
        title: s1.title,
        status: s1.status,
        tone: s1.tone,
        chapterCount: SIZE((s1)-[:HAS_CHAPTER]->())
      } as source,
      {
        id: s2.id,
        title: s2.title,
        status: s2.status,
        tone: s2.tone,
        chapterCount: SIZE((s2)-[:HAS_CHAPTER]->())
      } as target,
      {
        weight: r.weight,
        sharedEntities: r.sharedEntities,
        sharedThemes: r.sharedThemes
      } as link
      LIMIT $limit
    `;

    const result = await executeRead(query, { minWeight, limit });

    // Build nodes and links
    const nodesMap = new Map<string, any>();
    const links: any[] = [];

    for (const record of result.records) {
      const source = record.get('source');
      const target = record.get('target');
      const link = record.get('link');

      // Add nodes
      if (!nodesMap.has(source.id)) {
        nodesMap.set(source.id, {
          id: source.id,
          title: source.title,
          status: source.status,
          tone: source.tone,
          chapterCount: toNumber(source.chapterCount),
        });
      }

      if (!nodesMap.has(target.id)) {
        nodesMap.set(target.id, {
          id: target.id,
          title: target.title,
          status: target.status,
          tone: target.tone,
          chapterCount: toNumber(target.chapterCount),
        });
      }

      // Add link
      links.push({
        source: source.id,
        target: target.id,
        weight: link.weight,
        sharedEntities: link.sharedEntities || [],
        sharedThemes: link.sharedThemes || [],
      });
    }

    const nodes = Array.from(nodesMap.values());

    // Also get isolated nodes (stories with no connections)
    if (nodes.length < limit) {
      const isolatedQuery = `
        MATCH (s:Story)
        WHERE s.status IN ['active', 'completed']
          AND NOT (s)-[:SHARES_UNIVERSE_WITH]-()
        RETURN s
        LIMIT $remaining
      `;

      const isolatedResult = await executeRead(isolatedQuery, {
        remaining: limit - nodes.length,
      });

      for (const record of isolatedResult.records) {
        const story = record.get('s').properties;
        if (!nodesMap.has(story.id)) {
          nodes.push({
            id: story.id,
            title: story.title,
            status: story.status,
            tone: story.tone,
            chapterCount: 0, // Will be calculated if needed
          });
        }
      }
    }

    const response: ApiResponse<{
      nodes: any[];
      links: any[];
      stats: {
        totalNodes: number;
        totalLinks: number;
        avgConnectionsPerNode: number;
      };
    }> = {
      success: true,
      data: {
        nodes,
        links,
        stats: {
          totalNodes: nodes.length,
          totalLinks: links.length,
          avgConnectionsPerNode: nodes.length > 0 ? links.length / nodes.length : 0,
        },
      },
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error fetching universe graph:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
