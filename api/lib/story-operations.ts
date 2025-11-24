/**
 * Story Operations
 *
 * Core CRUD operations and graph queries for stories, chapters, and evaluations.
 * This module provides the data access layer for the API endpoints.
 */

import { v4 as uuidv4 } from 'uuid';
import {
  executeRead,
  executeWrite,
  executeWriteTransaction,
  extractNodeProperties,
  toNumber,
  toDate,
} from './neo4j.js';
import type {
  Story,
  StoryWithDetails,
  Chapter,
  ChapterWithChaos,
  Evaluation,
  ChaosParameters,
  ContentLevels,
  Entity,
  EntityMention,
  TomVariant,
} from './types.js';

// ───────────────────────────────────────────────────────────────────────────
// Story CRUD Operations
// ───────────────────────────────────────────────────────────────────────────

/**
 * Create a new story.
 */
export async function createStory(params: {
  title: string;
  premise: string;
  styleAuthors: string[];
  narrativePerspective: string;
  tone: string;
  genreTags: string[];
  tomVariant: string;
}): Promise<Story> {
  const storyId = uuidv4();

  const query = `
    CREATE (s:Story {
      id: $id,
      title: $title,
      premise: $premise,
      status: 'active',
      createdAt: timestamp(),
      styleAuthors: $styleAuthors,
      narrativePerspective: $narrativePerspective,
      tone: $tone,
      genreTags: $genreTags,
      totalTokens: 0,
      estimatedReadingMinutes: 0
    })
    WITH s
    MATCH (tom:Tom {id: 'tom-canonical'})
    CREATE (s)-[:FEATURES_TOM {
      variantName: $tomVariant,
      role: 'protagonist',
      firstAppearanceChapter: 1
    }]->(tom)
    SET tom.totalAppearances = tom.totalAppearances + 1
    RETURN s
  `;

  const result = await executeWrite(query, {
    id: storyId,
    ...params,
  });

  const node = result.records[0]?.get('s');
  return extractNodeProperties<Story>(node);
}

/**
 * Get a story by ID.
 */
export async function getStory(storyId: string): Promise<Story | null> {
  const query = `
    MATCH (s:Story {id: $storyId})
    RETURN s
  `;

  const result = await executeRead(query, { storyId });

  if (result.records.length === 0) {
    return null;
  }

  const node = result.records[0].get('s');
  return extractNodeProperties<Story>(node);
}

/**
 * Get a story with full details (chapters, evaluations, entities).
 */
export async function getStoryWithDetails(
  storyId: string
): Promise<StoryWithDetails | null> {
  const query = `
    MATCH (s:Story {id: $storyId})
    OPTIONAL MATCH (s)-[hc:HAS_CHAPTER]->(c:Chapter)
    OPTIONAL MATCH (s)-[:WAS_EVALUATED]->(ev:Evaluation)
    OPTIONAL MATCH (s)-[m:MENTIONS]->(e:Entity)
    OPTIONAL MATCH (s)-[ft:FEATURES_TOM]->(:Tom)
    RETURN s,
           COLLECT(DISTINCT {chapter: c, chaos: properties(hc)}) as chapters,
           COLLECT(DISTINCT ev) as evaluations,
           COLLECT(DISTINCT {entity: e, mention: m}) as entities,
           ft
    ORDER BY c.chapterNumber
  `;

  const result = await executeRead(query, { storyId });

  if (result.records.length === 0) {
    return null;
  }

  const record = result.records[0];
  const story = extractNodeProperties<Story>(record.get('s'));

  // Process chapters
  const chaptersRaw = record.get('chapters');
  const chapters: ChapterWithChaos[] = chaptersRaw
    .filter((ch: any) => ch.chapter !== null)
    .map((ch: any) => ({
      ...extractNodeProperties<Chapter>(ch.chapter),
      chaos: ch.chaos as ChaosParameters,
    }));

  // Process evaluations
  const evaluationsRaw = record.get('evaluations');
  const evaluations: Evaluation[] = evaluationsRaw
    .filter((ev: any) => ev !== null)
    .map((ev: any) => extractNodeProperties<Evaluation>(ev));

  // Process entities
  const entitiesRaw = record.get('entities');
  const entities: EntityMention[] = entitiesRaw
    .filter((em: any) => em.entity !== null)
    .map((em: any) => ({
      entity: extractNodeProperties<Entity>(em.entity),
      firstChapterNumber: toNumber(em.mention.firstChapterNumber),
      lastChapterNumber: toNumber(em.mention.lastChapterNumber),
      mentionCount: toNumber(em.mention.mentionCount),
      importance: em.mention.importance || 0,
      sentiment: em.mention.sentiment || 'neutral',
      relationshipToTom: em.mention.relationshipToTom || 'unknown',
    }));

  // Process Tom variant
  const tomRaw = record.get('ft');
  const tomVariant: TomVariant | undefined = tomRaw
    ? {
        variantName: tomRaw.variantName,
        role: tomRaw.role,
        characterization: tomRaw.characterization,
        firstAppearanceChapter: toNumber(tomRaw.firstAppearanceChapter),
      }
    : undefined;

  return {
    ...story,
    chapters,
    evaluations,
    entities,
    tomVariant,
  };
}

/**
 * Get all stories (with optional status filter and pagination).
 */
export async function getStories(params: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<Story[]> {
  const { status, limit = 50, offset = 0 } = params;

  const query = status
    ? `
      MATCH (s:Story {status: $status})
      RETURN s
      ORDER BY s.createdAt DESC
      SKIP $offset
      LIMIT $limit
    `
    : `
      MATCH (s:Story)
      RETURN s
      ORDER BY s.createdAt DESC
      SKIP $offset
      LIMIT $limit
    `;

  const result = await executeRead(query, { status, offset, limit });

  return result.records.map((record) =>
    extractNodeProperties<Story>(record.get('s'))
  );
}

/**
 * Get active stories (for worker operations).
 */
export async function getActiveStories(): Promise<Array<{
  story: Story;
  lastChapterNumber: number | null;
  lastChapterAt: Date | null;
}>> {
  const query = `
    MATCH (s:Story {status: 'active'})
    OPTIONAL MATCH (s)-[hc:HAS_CHAPTER]->(c:Chapter)
    WITH s, MAX(c.chapterNumber) as lastChapter, MAX(c.createdAt) as lastChapterAt
    RETURN s, lastChapter, lastChapterAt
    ORDER BY s.createdAt DESC
  `;

  const result = await executeRead(query);

  return result.records.map((record) => ({
    story: extractNodeProperties<Story>(record.get('s')),
    lastChapterNumber: record.get('lastChapter')
      ? toNumber(record.get('lastChapter'))
      : null,
    lastChapterAt: record.get('lastChapterAt')
      ? toDate(record.get('lastChapterAt'))
      : null,
  }));
}

/**
 * Complete a story.
 */
export async function completeStory(
  storyId: string,
  reason: string
): Promise<Story> {
  const query = `
    MATCH (s:Story {id: $storyId})
    SET s.status = 'completed',
        s.completedAt = timestamp(),
        s.completionReason = $reason
    RETURN s
  `;

  const result = await executeWrite(query, { storyId, reason });
  const node = result.records[0]?.get('s');
  return extractNodeProperties<Story>(node);
}

/**
 * Kill a story (end it early).
 */
export async function killStory(
  storyId: string,
  reason: string
): Promise<Story> {
  const query = `
    MATCH (s:Story {id: $storyId})
    SET s.status = 'killed',
        s.completedAt = timestamp(),
        s.completionReason = $reason
    RETURN s
  `;

  const result = await executeWrite(query, { storyId, reason });
  const node = result.records[0]?.get('s');
  return extractNodeProperties<Story>(node);
}

/**
 * Delete a story and all related nodes.
 */
export async function deleteStory(storyId: string): Promise<void> {
  const query = `
    MATCH (s:Story {id: $storyId})
    OPTIONAL MATCH (s)-[:HAS_CHAPTER]->(c:Chapter)
    OPTIONAL MATCH (s)-[:WAS_EVALUATED]->(ev:Evaluation)
    DETACH DELETE s, c, ev
  `;

  await executeWrite(query, { storyId });
}

/**
 * Update story cover image URL.
 */
export async function updateStoryCoverImage(
  storyId: string,
  coverImageUrl: string
): Promise<void> {
  const query = `
    MATCH (s:Story {id: $storyId})
    SET s.coverImageUrl = $coverImageUrl
  `;

  await executeWrite(query, { storyId, coverImageUrl });
}

// ───────────────────────────────────────────────────────────────────────────
// Chapter Operations
// ───────────────────────────────────────────────────────────────────────────

/**
 * Add a chapter to a story.
 */
export async function addChapter(params: {
  storyId: string;
  chapterNumber: number;
  content: string;
  chaos: ChaosParameters;
  contentLevels: ContentLevels;
  tokensUsed: number;
  generationTimeMs: number;
  modelUsed: string;
}): Promise<Chapter> {
  const {
    storyId,
    chapterNumber,
    content,
    chaos,
    contentLevels,
    tokensUsed,
    generationTimeMs,
    modelUsed,
  } = params;

  const chapterId = uuidv4();
  const wordCount = content.split(/\s+/).length;

  const query = `
    MATCH (s:Story {id: $storyId})
    CREATE (c:Chapter {
      id: $chapterId,
      chapterNumber: $chapterNumber,
      content: $content,
      createdAt: timestamp(),
      tokensUsed: $tokensUsed,
      generationTimeMs: $generationTimeMs,
      modelUsed: $modelUsed,
      wordCount: $wordCount,
      sexualContent: $contentLevels.sexualContent,
      violence: $contentLevels.violence,
      strongLanguage: $contentLevels.strongLanguage,
      drugUse: $contentLevels.drugUse,
      horrorSuspense: $contentLevels.horrorSuspense,
      goreGraphicImagery: $contentLevels.goreGraphicImagery,
      romanceFocus: $contentLevels.romanceFocus,
      crimeIllicitActivity: $contentLevels.crimeIllicitActivity,
      politicalIdeology: $contentLevels.politicalIdeology,
      supernaturalOccult: $contentLevels.supernaturalOccult,
      cosmicHorror: $contentLevels.cosmicHorror,
      bureaucraticSatire: $contentLevels.bureaucraticSatire,
      archivalGlitch: $contentLevels.archivalGlitch
    })
    CREATE (s)-[:HAS_CHAPTER {
      order: $chapterNumber,
      absurdity: $chaos.absurdity,
      surrealism: $chaos.surrealism,
      ridiculousness: $chaos.ridiculousness,
      insanity: $chaos.insanity,
      createdAt: timestamp()
    }]->(c)
    SET s.totalTokens = s.totalTokens + $tokensUsed,
        s.estimatedReadingMinutes = s.totalTokens / 250
    RETURN c
  `;

  const result = await executeWrite(query, {
    storyId,
    chapterId,
    chapterNumber,
    content,
    chaos,
    contentLevels,
    tokensUsed,
    generationTimeMs,
    modelUsed,
    wordCount,
  });

  const node = result.records[0]?.get('c');
  return extractNodeProperties<Chapter>(node);
}

/**
 * Get chapters for a story.
 */
export async function getChapters(storyId: string): Promise<ChapterWithChaos[]> {
  const query = `
    MATCH (s:Story {id: $storyId})-[hc:HAS_CHAPTER]->(c:Chapter)
    RETURN c, hc
    ORDER BY c.chapterNumber
  `;

  const result = await executeRead(query, { storyId });

  return result.records.map((record) => ({
    ...extractNodeProperties<Chapter>(record.get('c')),
    chaos: record.get('hc').properties as ChaosParameters,
  }));
}

/**
 * Get latest chapter for a story.
 */
export async function getLatestChapter(
  storyId: string
): Promise<ChapterWithChaos | null> {
  const query = `
    MATCH (s:Story {id: $storyId})-[hc:HAS_CHAPTER]->(c:Chapter)
    RETURN c, hc
    ORDER BY c.chapterNumber DESC
    LIMIT 1
  `;

  const result = await executeRead(query, { storyId });

  if (result.records.length === 0) {
    return null;
  }

  const record = result.records[0];
  return {
    ...extractNodeProperties<Chapter>(record.get('c')),
    chaos: record.get('hc').properties as ChaosParameters,
  };
}

// ───────────────────────────────────────────────────────────────────────────
// Evaluation Operations
// ───────────────────────────────────────────────────────────────────────────

/**
 * Create an evaluation for a story.
 */
export async function createEvaluation(params: {
  storyId: string;
  chapterNumber: number;
  overallScore: number;
  coherenceScore: number;
  noveltyScore: number;
  engagementScore: number;
  pacingScore: number;
  shouldContinue: boolean;
  reasoning: string;
  issues: string[];
  modelUsed: string;
}): Promise<Evaluation> {
  const evaluationId = uuidv4();

  const query = `
    MATCH (s:Story {id: $storyId})
    MATCH (s)-[:HAS_CHAPTER]->(c:Chapter {chapterNumber: $chapterNumber})
    CREATE (ev:Evaluation {
      id: $evaluationId,
      chapterNumber: $chapterNumber,
      overallScore: $overallScore,
      coherenceScore: $coherenceScore,
      noveltyScore: $noveltyScore,
      engagementScore: $engagementScore,
      pacingScore: $pacingScore,
      shouldContinue: $shouldContinue,
      reasoning: $reasoning,
      issues: $issues,
      evaluatedAt: timestamp(),
      modelUsed: $modelUsed
    })
    CREATE (s)-[:WAS_EVALUATED {
      atChapterNumber: $chapterNumber,
      evaluatedAt: timestamp()
    }]->(ev)
    CREATE (ev)-[:EVALUATED_AFTER]->(c)
    RETURN ev
  `;

  const result = await executeWrite(query, {
    evaluationId,
    ...params,
  });

  const node = result.records[0]?.get('ev');
  return extractNodeProperties<Evaluation>(node);
}

/**
 * Get evaluations for a story.
 */
export async function getEvaluations(storyId: string): Promise<Evaluation[]> {
  const query = `
    MATCH (s:Story {id: $storyId})-[:WAS_EVALUATED]->(ev:Evaluation)
    RETURN ev
    ORDER BY ev.chapterNumber
  `;

  const result = await executeRead(query, { storyId });

  return result.records.map((record) =>
    extractNodeProperties<Evaluation>(record.get('ev'))
  );
}

/**
 * Get latest evaluation for a story.
 */
export async function getLatestEvaluation(
  storyId: string
): Promise<Evaluation | null> {
  const query = `
    MATCH (s:Story {id: $storyId})-[:WAS_EVALUATED]->(ev:Evaluation)
    RETURN ev
    ORDER BY ev.chapterNumber DESC
    LIMIT 1
  `;

  const result = await executeRead(query, { storyId });

  if (result.records.length === 0) {
    return null;
  }

  return extractNodeProperties<Evaluation>(result.records[0].get('ev'));
}

// ───────────────────────────────────────────────────────────────────────────
// Count Operations
// ───────────────────────────────────────────────────────────────────────────

/**
 * Get story counts by status.
 */
export async function getStoryCounts(): Promise<{
  active: number;
  completed: number;
  killed: number;
  total: number;
}> {
  const query = `
    MATCH (s:Story)
    RETURN s.status as status, COUNT(s) as count
  `;

  const result = await executeRead(query);

  const counts = { active: 0, completed: 0, killed: 0, total: 0 };

  for (const record of result.records) {
    const status = record.get('status');
    const count = toNumber(record.get('count'));
    counts[status as keyof typeof counts] = count;
    counts.total += count;
  }

  return counts;
}

/**
 * Get total chapter count.
 */
export async function getTotalChapterCount(): Promise<number> {
  const query = `
    MATCH (:Story)-[:HAS_CHAPTER]->(c:Chapter)
    RETURN COUNT(c) as count
  `;

  const result = await executeRead(query);
  return toNumber(result.records[0]?.get('count') || 0);
}

/**
 * Get total tokens used.
 */
export async function getTotalTokens(): Promise<number> {
  const query = `
    MATCH (s:Story)
    RETURN SUM(s.totalTokens) as total
  `;

  const result = await executeRead(query);
  return toNumber(result.records[0]?.get('total') || 0);
}
