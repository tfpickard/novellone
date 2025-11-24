/**
 * Spawn Story Endpoint
 * POST /api/admin/spawn
 *
 * Manually trigger creation of a new story.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';
import { generatePremise } from '../lib/openai.js';
import { createStory } from '../lib/story-operations.js';
import { getConfig } from '../lib/config.js';
import type { ApiResponse, Story } from '../lib/types.js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // TODO: Add authentication check here
    // For now, allow spawning (add auth later)

    const config = await getConfig();

    // Generate premise using OpenAI
    console.log('Generating premise...');
    const premise = await generatePremise({
      model: config.modelPremise,
      maxTokens: config.maxTokensPremise,
    });

    // Create story in Neo4j
    console.log('Creating story in database...');
    const story = await createStory({
      title: premise.title,
      premise: premise.premise,
      styleAuthors: premise.styleAuthors,
      narrativePerspective: premise.narrativePerspective,
      tone: premise.tone,
      genreTags: premise.genreTags,
      tomVariant: premise.tomVariant,
    });

    const response: ApiResponse<Story> = {
      success: true,
      data: story,
      message: 'Story spawned successfully',
    };

    res.status(201).json(response);
  } catch (error) {
    console.error('Error spawning story:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
    } as ApiResponse);
  }
}
