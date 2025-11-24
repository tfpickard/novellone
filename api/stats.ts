/**
 * Statistics Endpoint
 * GET /api/stats
 *
 * Returns aggregate statistics about stories, chapters, and the universe.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import {
  getStoryCounts,
  getTotalChapterCount,
  getTotalTokens,
  getChapters,
} from './lib/story-operations.js';
import { executeRead, toNumber } from './lib/neo4j.js';
import type { ApiResponse, StatsResponse } from './lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // Fetch story counts
    const storyCounts = await getStoryCounts();

    // Fetch chapter counts
    const totalChapters = await getTotalChapterCount();

    // Fetch total tokens
    const totalTokens = await getTotalTokens();

    // Fetch average chaos levels
    const chaosQuery = `
      MATCH (:Story)-[hc:HAS_CHAPTER]->(:Chapter)
      RETURN AVG(hc.absurdity) as avgAbsurdity,
             AVG(hc.surrealism) as avgSurrealism,
             AVG(hc.ridiculousness) as avgRidiculousness,
             AVG(hc.insanity) as avgInsanity
    `;
    const chaosResult = await executeRead(chaosQuery);
    const chaosRecord = chaosResult.records[0];

    const chaos = {
      avgAbsurdity: chaosRecord?.get('avgAbsurdity') || 0,
      avgSurrealism: chaosRecord?.get('avgSurrealism') || 0,
      avgRidiculousness: chaosRecord?.get('avgRidiculousness') || 0,
      avgInsanity: chaosRecord?.get('avgInsanity') || 0,
    };

    // Fetch average content levels
    const contentQuery = `
      MATCH (c:Chapter)
      RETURN AVG(c.sexualContent) as avgSexualContent,
             AVG(c.violence) as avgViolence,
             AVG(c.strongLanguage) as avgStrongLanguage,
             AVG(c.drugUse) as avgDrugUse,
             AVG(c.horrorSuspense) as avgHorrorSuspense,
             AVG(c.goreGraphicImagery) as avgGoreGraphicImagery,
             AVG(c.romanceFocus) as avgRomanceFocus,
             AVG(c.crimeIllicitActivity) as avgCrimeIllicitActivity,
             AVG(c.politicalIdeology) as avgPoliticalIdeology,
             AVG(c.supernaturalOccult) as avgSupernaturalOccult,
             AVG(c.cosmicHorror) as avgCosmicHorror,
             AVG(c.bureaucraticSatire) as avgBureaucraticSatire,
             AVG(c.archivalGlitch) as avgArchivalGlitch
    `;
    const contentResult = await executeRead(contentQuery);
    const contentRecord = contentResult.records[0];

    const content = contentRecord
      ? {
          sexualContent: contentRecord.get('avgSexualContent') || 0,
          violence: contentRecord.get('avgViolence') || 0,
          strongLanguage: contentRecord.get('avgStrongLanguage') || 0,
          drugUse: contentRecord.get('avgDrugUse') || 0,
          horrorSuspense: contentRecord.get('avgHorrorSuspense') || 0,
          goreGraphicImagery: contentRecord.get('avgGoreGraphicImagery') || 0,
          romanceFocus: contentRecord.get('avgRomanceFocus') || 0,
          crimeIllicitActivity: contentRecord.get('avgCrimeIllicitActivity') || 0,
          politicalIdeology: contentRecord.get('avgPoliticalIdeology') || 0,
          supernaturalOccult: contentRecord.get('avgSupernaturalOccult') || 0,
          cosmicHorror: contentRecord.get('avgCosmicHorror') || 0,
          bureaucraticSatire: contentRecord.get('avgBureaucraticSatire') || 0,
          archivalGlitch: contentRecord.get('avgArchivalGlitch') || 0,
        }
      : {};

    // Fetch entity counts
    const entityQuery = `
      MATCH (e:Entity)
      RETURN COUNT(e) as total
    `;
    const entityResult = await executeRead(entityQuery);
    const entityTotal = toNumber(entityResult.records[0]?.get('total') || 0);

    // Fetch top entities
    const topEntitiesQuery = `
      MATCH (e:Entity)
      RETURN e.name as name, e.totalMentions as mentions, e.importance as importance
      ORDER BY e.totalMentions DESC
      LIMIT 10
    `;
    const topEntitiesResult = await executeRead(topEntitiesQuery);
    const topEntities = topEntitiesResult.records.map((record) => ({
      name: record.get('name'),
      mentions: toNumber(record.get('mentions')),
      importance: record.get('importance') || 0,
    }));

    // Fetch recent chapters
    const recentChaptersQuery = `
      MATCH (:Story)-[:HAS_CHAPTER]->(c:Chapter)
      RETURN c
      ORDER BY c.createdAt DESC
      LIMIT 10
    `;
    const recentChaptersResult = await executeRead(recentChaptersQuery);
    const recentChapters = recentChaptersResult.records.map((record) => {
      const node = record.get('c');
      return node.properties;
    });

    // Fetch Tom stats
    const tomQuery = `
      MATCH (tom:Tom {id: 'tom-canonical'})
      OPTIONAL MATCH (:Story)-[ft:FEATURES_TOM]->(tom)
      WITH tom, COLLECT(DISTINCT ft.variantName) as variants
      RETURN tom.totalAppearances as totalAppearances, variants
    `;
    const tomResult = await executeRead(tomQuery);
    const tomRecord = tomResult.records[0];
    const tom = {
      totalAppearances: toNumber(tomRecord?.get('totalAppearances') || 0),
      variants: tomRecord?.get('variants') || [],
    };

    // Build response
    const stats: StatsResponse = {
      stories: storyCounts,
      chapters: {
        total: totalChapters,
        recentChapters,
      },
      tokens: {
        total: totalTokens,
      },
      chaos,
      content,
      entities: {
        total: entityTotal,
        topEntities,
      },
      universes: {
        total: 0, // TODO: implement universe counting
        clusters: 0,
      },
      tom,
    };

    const response: ApiResponse<StatsResponse> = {
      success: true,
      data: stats,
    };

    res.status(200).json(response);
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
