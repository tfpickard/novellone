/**
 * Story Worker
 *
 * Core logic for autonomous story generation, evaluation, and management.
 * Called by Vercel Cron Jobs to maintain the story pool.
 */

import {
  getActiveStories,
  getStoryCounts,
  createStory,
  addChapter,
  getChapters,
  createEvaluation,
  getLatestEvaluation,
  completeStory,
} from './story-operations.js';
import {
  generatePremise,
  generateChapter,
  evaluateStory,
  generateCoverArt,
  extractEntities,
} from './openai.js';
import { uploadCoverImage } from './blob.js';
import { getConfig } from './config.js';
import type {
  ChaosParameters,
  ContentLevels,
  PremiseResponse,
} from './types.js';

// ───────────────────────────────────────────────────────────────────────────
// Story Pool Management
// ───────────────────────────────────────────────────────────────────────────

/**
 * Ensure the story pool maintains the target number of active stories.
 * Spawns new stories if below minimum, completes oldest if above maximum.
 */
export async function maintainStoryPool(): Promise<{
  spawned: number;
  completed: number;
}> {
  const config = await getConfig();
  const { active } = await getStoryCounts();

  let spawned = 0;
  let completed = 0;

  console.log(`📊 Active stories: ${active} (target: ${config.minActiveStories}-${config.maxActiveStories})`);

  // If above maximum, complete the oldest story
  if (active > config.maxActiveStories) {
    const activeStories = await getActiveStories();
    const oldestStory = activeStories.sort(
      (a, b) => a.story.createdAt.getTime() - b.story.createdAt.getTime()
    )[0];

    if (oldestStory) {
      console.log(`🏁 Completing oldest story: ${oldestStory.story.title}`);
      await completeStory(
        oldestStory.story.id,
        'Pool capacity reached - completing oldest story'
      );
      completed++;
    }
  }

  // If below minimum, spawn new stories
  while (active + spawned < config.minActiveStories) {
    console.log(`✨ Spawning new story...`);
    await spawnNewStory();
    spawned++;
  }

  return { spawned, completed };
}

/**
 * Spawn a new story with AI-generated premise.
 */
export async function spawnNewStory(): Promise<string> {
  const config = await getConfig();

  console.log('🎲 Generating premise...');
  const premise = await generatePremise({
    model: config.modelPremise,
    maxTokens: config.maxTokensPremise,
    temperature: 0.9,
  });

  console.log(`📖 Created premise: "${premise.title}"`);

  const story = await createStory({
    title: premise.title,
    premise: premise.premise,
    styleAuthors: premise.styleAuthors,
    narrativePerspective: premise.narrativePerspective,
    tone: premise.tone,
    genreTags: premise.genreTags,
    tomVariant: premise.tomVariant,
  });

  console.log(`✓ Story created: ${story.id}`);

  // TODO: Emit SSE event for new story

  return story.id;
}

// ───────────────────────────────────────────────────────────────────────────
// Chapter Generation
// ───────────────────────────────────────────────────────────────────────────

/**
 * Generate chapters for active stories that are ready for the next chapter.
 */
export async function generateChaptersForActiveStories(): Promise<{
  generated: number;
}> {
  const config = await getConfig();
  const activeStories = await getActiveStories();

  let generated = 0;

  for (const { story, lastChapterNumber, lastChapterAt } of activeStories) {
    // Check if story has reached max chapters
    if (lastChapterNumber && lastChapterNumber >= config.maxChaptersPerStory) {
      console.log(`📚 Story "${story.title}" reached max chapters, completing...`);
      await completeStory(story.id, 'Maximum chapter count reached');
      continue;
    }

    // Check if enough time has passed since last chapter
    const now = new Date();
    const intervalMs = config.chapterIntervalMinutes * 60 * 1000;

    if (lastChapterAt) {
      const timeSinceLastChapter = now.getTime() - lastChapterAt.getTime();
      if (timeSinceLastChapter < intervalMs) {
        console.log(`⏳ Story "${story.title}" not ready for next chapter yet`);
        continue;
      }
    }

    // Generate next chapter
    const nextChapterNumber = (lastChapterNumber || 0) + 1;

    console.log(`✍️  Generating chapter ${nextChapterNumber} for "${story.title}"...`);

    try {
      await generateChapterForStory(story.id, nextChapterNumber);
      generated++;

      // TODO: Emit SSE event for new chapter
    } catch (error) {
      console.error(`Error generating chapter for story ${story.id}:`, error);
    }
  }

  return { generated };
}

/**
 * Generate a single chapter for a story.
 */
export async function generateChapterForStory(
  storyId: string,
  chapterNumber: number
): Promise<void> {
  const config = await getConfig();

  // Fetch story and previous chapters
  const chapters = await getChapters(storyId);
  const story = chapters[0]?.story; // This won't work - need to fetch story separately

  // Actually, let's fetch story properly
  const { getStory } = await import('./story-operations.js');
  const storyData = await getStory(storyId);
  if (!storyData) {
    throw new Error(`Story ${storyId} not found`);
  }

  // Calculate chaos parameters for this chapter
  // For now, use simple linear progression
  // TODO: Extract initial chaos and increments from premise
  const chaos: ChaosParameters = {
    absurdity: 0.1 + (chapterNumber - 1) * 0.05,
    surrealism: 0.1 + (chapterNumber - 1) * 0.05,
    ridiculousness: 0.1 + (chapterNumber - 1) * 0.05,
    insanity: 0.05 + (chapterNumber - 1) * 0.03,
  };

  // Default content targets (could be configured per story)
  const contentTargets: Partial<ContentLevels> = {
    bureaucraticSatire: 0.6,
    archivalGlitch: 0.4,
    cosmicHorror: 0.3,
  };

  // Get previous chapter content (limited context window)
  const previousChapters = chapters
    .slice(Math.max(0, chapters.length - 3)) // Last 3 chapters
    .map((ch) => ch.content);

  // Generate chapter
  const startTime = Date.now();

  const chapterData = await generateChapter({
    storyTitle: storyData.title,
    premise: storyData.premise,
    previousChapters,
    chapterNumber,
    chaos,
    contentTargets,
    model: config.modelChapter,
    maxTokens: config.maxTokensChapter,
    temperature: 0.85,
  });

  const generationTimeMs = Date.now() - startTime;

  // Add chapter to database
  await addChapter({
    storyId,
    chapterNumber,
    content: chapterData.content,
    chaos: chapterData.chaos,
    contentLevels: chapterData.contentLevels,
    tokensUsed: chapterData.tokensUsed,
    generationTimeMs,
    modelUsed: config.modelChapter,
  });

  console.log(`✓ Chapter ${chapterNumber} generated for story ${storyId}`);

  // Extract entities (in the background, don't block)
  if (chapterData.entities && chapterData.entities.length > 0) {
    extractAndLinkEntities(storyId, chapterNumber, chapterData.content)
      .catch((err) => console.error('Error extracting entities:', err));
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Story Evaluation
// ───────────────────────────────────────────────────────────────────────────

/**
 * Evaluate active stories that are due for evaluation.
 */
export async function evaluateActiveStories(): Promise<{
  evaluated: number;
  completed: number;
}> {
  const config = await getConfig();
  const activeStories = await getActiveStories();

  let evaluated = 0;
  let completed = 0;

  for (const { story, lastChapterNumber } of activeStories) {
    if (!lastChapterNumber || lastChapterNumber < 3) {
      // Don't evaluate until at least 3 chapters
      continue;
    }

    // Check if evaluation is due
    const lastEval = await getLatestEvaluation(story.id);
    const chaptersSinceLastEval = lastEval
      ? lastChapterNumber - lastEval.chapterNumber
      : lastChapterNumber;

    if (chaptersSinceLastEval < config.evaluationIntervalChapters) {
      continue;
    }

    console.log(`📊 Evaluating story "${story.title}" at chapter ${lastChapterNumber}...`);

    try {
      const shouldContinue = await evaluateStoryAtChapter(
        story.id,
        lastChapterNumber
      );

      evaluated++;

      if (!shouldContinue) {
        console.log(`🛑 Story "${story.title}" failed evaluation, completing...`);
        await completeStory(story.id, 'Quality score below threshold');
        completed++;
      }

      // TODO: Emit SSE event for evaluation
    } catch (error) {
      console.error(`Error evaluating story ${story.id}:`, error);
    }
  }

  return { evaluated, completed };
}

/**
 * Evaluate a story at a specific chapter.
 * Returns true if the story should continue, false otherwise.
 */
export async function evaluateStoryAtChapter(
  storyId: string,
  chapterNumber: number
): Promise<boolean> {
  const config = await getConfig();

  // Fetch story and all chapters
  const { getStory } = await import('./story-operations.js');
  const story = await getStory(storyId);
  if (!story) {
    throw new Error(`Story ${storyId} not found`);
  }

  const chapters = await getChapters(storyId);
  const chapterContents = chapters.map((ch) => ch.content);

  // Evaluate using OpenAI
  const evaluation = await evaluateStory({
    storyTitle: story.title,
    premise: story.premise,
    chapters: chapterContents,
    chapterNumber,
    model: config.modelEvaluation,
    maxTokens: config.maxTokensEvaluation,
    temperature: 0.3,
  });

  // Store evaluation in database
  await createEvaluation({
    storyId,
    chapterNumber,
    overallScore: evaluation.overallScore,
    coherenceScore: evaluation.coherenceScore,
    noveltyScore: evaluation.noveltyScore,
    engagementScore: evaluation.engagementScore,
    pacingScore: evaluation.pacingScore,
    shouldContinue: evaluation.shouldContinue,
    reasoning: evaluation.reasoning,
    issues: evaluation.issues,
    modelUsed: config.modelEvaluation,
  });

  console.log(`  Overall score: ${evaluation.overallScore.toFixed(2)}`);
  console.log(`  Should continue: ${evaluation.shouldContinue}`);

  return evaluation.shouldContinue && evaluation.overallScore >= config.qualityScoreMin;
}

// ───────────────────────────────────────────────────────────────────────────
// Cover Art Generation
// ───────────────────────────────────────────────────────────────────────────

/**
 * Generate cover art for completed stories that don't have covers yet.
 */
export async function backfillCoverArt(): Promise<{
  generated: number;
}> {
  const config = await getConfig();

  if (!config.coverArtBackfillEnabled) {
    return { generated: 0 };
  }

  // Find completed stories without cover art
  const { executeRead } = await import('./neo4j.js');
  const query = `
    MATCH (s:Story)
    WHERE s.status IN ['completed', 'killed']
      AND (s.coverImageUrl IS NULL OR s.coverImageUrl = '')
    RETURN s
    ORDER BY s.completedAt DESC
    LIMIT $limit
  `;

  const result = await executeRead(query, { limit: config.coverArtBackfillBatchSize });

  let generated = 0;

  for (const record of result.records) {
    const story = record.get('s').properties;

    console.log(`🎨 Generating cover art for "${story.title}"...`);

    try {
      // Generate cover with DALL-E
      const imageUrl = await generateCoverArt({
        storyTitle: story.title,
        premise: story.premise,
        tone: story.tone,
        genreTags: story.genreTags || [],
        model: config.modelCoverArt,
      });

      // Upload to Vercel Blob
      const blobUrl = await uploadCoverImage(story.id, imageUrl);

      // Update story with cover URL
      const { updateStoryCoverImage } = await import('./story-operations.js');
      await updateStoryCoverImage(story.id, blobUrl);

      console.log(`✓ Cover art generated: ${blobUrl}`);
      generated++;
    } catch (error) {
      console.error(`Error generating cover for story ${story.id}:`, error);
    }
  }

  return { generated };
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Extraction & Linking
// ───────────────────────────────────────────────────────────────────────────

/**
 * Extract entities from chapter content and link them to the story.
 */
async function extractAndLinkEntities(
  storyId: string,
  chapterNumber: number,
  content: string
): Promise<void> {
  // TODO: Implement entity extraction and linking using Neo4j
  // This is a placeholder for future graph-aware entity tracking

  const entities = await extractEntities(content);

  console.log(`  Extracted ${entities.length} entities from chapter ${chapterNumber}`);

  // TODO: Create Entity nodes and MENTIONS relationships
  // For now, this is just logging
}
