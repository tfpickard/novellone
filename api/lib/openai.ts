/**
 * OpenAI Client
 *
 * Handles all interactions with OpenAI's API for story generation, evaluation, and cover art.
 */

import OpenAI from 'openai';
import type {
  PremiseResponse,
  ChapterResponse,
  EvaluationResponse,
  ChaosParameters,
  ContentLevels,
} from './types.js';

// ───────────────────────────────────────────────────────────────────────────
// Client Initialization
// ───────────────────────────────────────────────────────────────────────────

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

if (!process.env.OPENAI_API_KEY) {
  console.warn('⚠️  OPENAI_API_KEY not set. Story generation will fail.');
}

// ───────────────────────────────────────────────────────────────────────────
// Constants
// ───────────────────────────────────────────────────────────────────────────

const DEFAULT_PREMISE_MODEL = 'gpt-4-turbo-preview';
const DEFAULT_CHAPTER_MODEL = 'gpt-4-turbo-preview';
const DEFAULT_EVAL_MODEL = 'gpt-4-turbo-preview';
const DEFAULT_IMAGE_MODEL = 'dall-e-3';

const CONTENT_AXIS_LABELS: Record<keyof ContentLevels, string> = {
  sexualContent: 'Sexual content/intimacy',
  violence: 'Violence/combat intensity',
  strongLanguage: 'Strong language/profanity',
  drugUse: 'Drug and substance use',
  horrorSuspense: 'Horror and suspense',
  goreGraphicImagery: 'Gore and graphic imagery',
  romanceFocus: 'Romantic relationship focus',
  crimeIllicitActivity: 'Crime and illicit activity',
  politicalIdeology: 'Political or ideological themes',
  supernaturalOccult: 'Supernatural or occult elements',
  cosmicHorror: 'Cosmic horror and existential dread',
  bureaucraticSatire: 'Bureaucratic satire and paperwork absurdity',
  archivalGlitch: 'Archival glitches, redactions, and broken records',
};

// ───────────────────────────────────────────────────────────────────────────
// Premise Generation
// ───────────────────────────────────────────────────────────────────────────

export async function generatePremise(options: {
  model?: string;
  maxTokens?: number;
  temperature?: number;
}= {}): Promise<PremiseResponse> {
  const { model = DEFAULT_PREMISE_MODEL, maxTokens = 2000, temperature = 0.9 } = options;

  const systemPrompt = `You are a science fiction premise generator for "Hurl Unmasks Recursive Literature Leaking Out Light" — an autonomous storytelling system.

Your task: Create a novel, surreal, and engaging science fiction premise featuring Tom, a tinkering engineer.

Tom is the universal constant across all stories:
- Always an engineer or tinkerer
- Curious, resourceful, slightly absurd
- Can be called Tom, Tommy, Thomas, T., or variations
- Anchors the narrative but isn't necessarily the sole focus

Respond with a JSON object containing:
{
  "title": "Evocative, poetic title (5-8 words)",
  "premise": "Story premise in Markdown (200-400 words). Set up the world, introduce Tom, establish the central conflict or mystery. Be surreal, philosophical, and visually rich.",
  "styleAuthors": ["Author 1", "Author 2"], // 1-3 sci-fi authors whose styles to blend
  "narrativePerspective": "first-person|third-person-limited|third-person-omniscient",
  "tone": "dark|humorous|philosophical|surreal|absurd",
  "genreTags": ["tag1", "tag2", "tag3"], // 3-5 genre/style tags
  "tomVariant": "Tom|Tommy|Thomas|T.", // How Tom is named in this story
  "chaosInitial": {
    "absurdity": 0.1-0.3,
    "surrealism": 0.1-0.3,
    "ridiculousness": 0.1-0.3,
    "insanity": 0.05-0.2
  },
  "chaosIncrements": {
    "absurdity": 0.03-0.08,
    "surrealism": 0.03-0.08,
    "ridiculousness": 0.03-0.08,
    "insanity": 0.02-0.06
  }
}

Guidelines:
- Premises should be NOVEL — avoid clichés and well-trodden ground
- Embrace bureaucratic absurdity, paperwork theater, archival mysteries
- Think: Borges, Calvino, Lem, Le Guin, Zelazny, Dick
- Tom should feel essential but not dominant
- Chaos parameters control how weird the story gets over time
- Higher initial values = start strange; higher increments = accelerate weirdness`;

  const response = await client.chat.completions.create({
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: 'Generate a new science fiction premise featuring Tom.' },
    ],
    max_tokens: maxTokens,
    temperature,
    response_format: { type: 'json_object' },
  });

  const content = response.choices[0]?.message?.content;
  if (!content) {
    throw new Error('No content returned from OpenAI');
  }

  const parsed = JSON.parse(content) as PremiseResponse;

  // Validate and normalize
  if (!parsed.title || !parsed.premise) {
    throw new Error('Invalid premise response: missing title or premise');
  }

  return parsed;
}

// ───────────────────────────────────────────────────────────────────────────
// Chapter Generation
// ───────────────────────────────────────────────────────────────────────────

export async function generateChapter(options: {
  storyTitle: string;
  premise: string;
  previousChapters: string[]; // Array of previous chapter content (limited context window)
  chapterNumber: number;
  chaos: ChaosParameters;
  contentTargets: Partial<ContentLevels>;
  model?: string;
  maxTokens?: number;
  temperature?: number;
}): Promise<ChapterResponse> {
  const {
    storyTitle,
    premise,
    previousChapters,
    chapterNumber,
    chaos,
    contentTargets,
    model = DEFAULT_CHAPTER_MODEL,
    maxTokens = 3000,
    temperature = 0.85,
  } = options;

  // Build content axis instructions
  const contentInstructions = Object.entries(contentTargets)
    .filter(([_, value]) => value !== undefined && value > 0)
    .map(([key, value]) => {
      const label = CONTENT_AXIS_LABELS[key as keyof ContentLevels];
      return `- ${label}: ${value.toFixed(1)}`;
    })
    .join('\n');

  const systemPrompt = `You are writing Chapter ${chapterNumber} of "${storyTitle}".

Story Premise:
${premise}

Previous Chapters Summary:
${previousChapters.length > 0 ? previousChapters.map((ch, i) => `Chapter ${i + 1}: ${ch.slice(0, 500)}...`).join('\n\n') : 'This is the first chapter.'}

Chaos Parameters (how strange this chapter should be):
- Absurdity: ${chaos.absurdity.toFixed(2)}
- Surrealism: ${chaos.surrealism.toFixed(2)}
- Ridiculousness: ${chaos.ridiculousness.toFixed(2)}
- Insanity: ${chaos.insanity.toFixed(2)}

Content Intensity Targets:
${contentInstructions || '- No specific content targets'}

Instructions:
- Write Chapter ${chapterNumber} in Markdown format (800-1500 words)
- Continue the narrative, escalating tension and weirdness according to chaos parameters
- Match the tone and style established in previous chapters
- Include vivid descriptions, character development, and plot progression
- Report actual chaos and content levels for this chapter

Respond with JSON:
{
  "content": "Chapter content in Markdown",
  "chaos": {
    "absurdity": "actual absurdity level in this chapter (0.0-1.0)",
    "surrealism": "actual surrealism level (0.0-1.0)",
    "ridiculousness": "actual ridiculousness level (0.0-1.0)",
    "insanity": "actual insanity level (0.0-1.0)"
  },
  "contentLevels": {
    "sexualContent": 0.0-1.0,
    "violence": 0.0-1.0,
    "strongLanguage": 0.0-1.0,
    "drugUse": 0.0-1.0,
    "horrorSuspense": 0.0-1.0,
    "goreGraphicImagery": 0.0-1.0,
    "romanceFocus": 0.0-1.0,
    "crimeIllicitActivity": 0.0-1.0,
    "politicalIdeology": 0.0-1.0,
    "supernaturalOccult": 0.0-1.0,
    "cosmicHorror": 0.0-1.0,
    "bureaucraticSatire": 0.0-1.0,
    "archivalGlitch": 0.0-1.0
  },
  "entities": ["Entity1", "Entity2", ...] // Major characters, places, objects mentioned
}`;

  const startTime = Date.now();

  const response = await client.chat.completions.create({
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: `Write Chapter ${chapterNumber}.` },
    ],
    max_tokens: maxTokens,
    temperature,
    response_format: { type: 'json_object' },
  });

  const generationTimeMs = Date.now() - startTime;
  const content = response.choices[0]?.message?.content;
  const tokensUsed = response.usage?.total_tokens || 0;

  if (!content) {
    throw new Error('No content returned from OpenAI');
  }

  const parsed = JSON.parse(content) as ChapterResponse;
  parsed.tokensUsed = tokensUsed;

  return parsed;
}

// ───────────────────────────────────────────────────────────────────────────
// Story Evaluation
// ───────────────────────────────────────────────────────────────────────────

export async function evaluateStory(options: {
  storyTitle: string;
  premise: string;
  chapters: string[]; // All chapter content so far
  chapterNumber: number;
  model?: string;
  maxTokens?: number;
  temperature?: number;
}): Promise<EvaluationResponse> {
  const {
    storyTitle,
    premise,
    chapters,
    chapterNumber,
    model = DEFAULT_EVAL_MODEL,
    maxTokens = 1500,
    temperature = 0.3,
  } = options;

  const systemPrompt = `You are a story quality evaluator for "Hurl Unmasks Recursive Literature Leaking Out Light".

Story: "${storyTitle}"
Premise: ${premise}

Chapters so far: ${chapters.length}
Current chapter: ${chapterNumber}

Your task: Evaluate the story's quality and determine if it should continue.

Criteria:
1. **Coherence** (0.0-1.0): Does the narrative make sense? Are plot threads consistent?
2. **Novelty** (0.0-1.0): Is the story original and surprising? Does it avoid clichés?
3. **Engagement** (0.0-1.0): Is it compelling? Would a reader want to continue?
4. **Pacing** (0.0-1.0): Is the story moving forward? Is the pacing appropriate?

Overall Score: Weighted average (coherence 25%, novelty 30%, engagement 30%, pacing 15%)

Should Continue: True if overall score >= 0.6 and no critical issues

Respond with JSON:
{
  "coherenceScore": 0.0-1.0,
  "noveltyScore": 0.0-1.0,
  "engagementScore": 0.0-1.0,
  "pacingScore": 0.0-1.0,
  "overallScore": 0.0-1.0,
  "shouldContinue": true|false,
  "reasoning": "2-3 sentence explanation of the evaluation",
  "issues": ["issue1", "issue2"] // Array of specific problems, if any
}`;

  const chaptersText = chapters.map((ch, i) => `--- Chapter ${i + 1} ---\n${ch}`).join('\n\n');

  const response = await client.chat.completions.create({
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: `Evaluate this story:\n\n${chaptersText}` },
    ],
    max_tokens: maxTokens,
    temperature,
    response_format: { type: 'json_object' },
  });

  const content = response.choices[0]?.message?.content;
  if (!content) {
    throw new Error('No content returned from OpenAI');
  }

  return JSON.parse(content) as EvaluationResponse;
}

// ───────────────────────────────────────────────────────────────────────────
// Cover Art Generation
// ───────────────────────────────────────────────────────────────────────────

export async function generateCoverArt(options: {
  storyTitle: string;
  premise: string;
  tone: string;
  genreTags: string[];
  model?: string;
}): Promise<string> {
  const { storyTitle, premise, tone, genreTags, model = DEFAULT_IMAGE_MODEL } = options;

  // Extract key visual elements from premise (first 500 chars)
  const visualHint = premise.slice(0, 500);

  const prompt = `Book cover for science fiction story titled "${storyTitle}".

Style: ${tone}, ${genreTags.join(', ')}.

Visual elements from story: ${visualHint}

Design requirements:
- Title typography featured prominently: "${storyTitle}"
- Abstract, surreal, sci-fi aesthetic
- Evocative color palette matching the ${tone} tone
- No human faces or explicit content
- Focus on atmosphere, symbols, and abstract concepts
- Professional book cover quality`;

  const response = await client.images.generate({
    model,
    prompt,
    n: 1,
    size: '1024x1792', // Tall book cover format
    quality: 'standard',
    style: 'vivid',
  });

  const imageUrl = response.data[0]?.url;
  if (!imageUrl) {
    throw new Error('No image URL returned from DALL-E');
  }

  return imageUrl;
}

// ───────────────────────────────────────────────────────────────────────────
// Utility: Extract Entities from Text (using GPT)
// ───────────────────────────────────────────────────────────────────────────

export async function extractEntities(text: string): Promise<Array<{
  name: string;
  type: 'character' | 'place' | 'object' | 'concept' | 'organization';
  importance: number;
}>> {
  const response = await client.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [
      {
        role: 'system',
        content: `Extract named entities from the text. Return JSON array:
[
  {
    "name": "Entity name",
    "type": "character|place|object|concept|organization",
    "importance": 0.0-1.0 (how central to the narrative)
  }
]

Focus on:
- Major characters (especially Tom and variants)
- Significant locations
- Important objects or technologies
- Key concepts or organizations
- Exclude minor mentions and generic terms`,
      },
      { role: 'user', content: text },
    ],
    max_tokens: 1000,
    temperature: 0.3,
    response_format: { type: 'json_object' },
  });

  const content = response.choices[0]?.message?.content;
  if (!content) {
    return [];
  }

  const parsed = JSON.parse(content);
  return Array.isArray(parsed.entities) ? parsed.entities : [];
}

// ───────────────────────────────────────────────────────────────────────────
// Exports
// ───────────────────────────────────────────────────────────────────────────

export { client as openaiClient };
