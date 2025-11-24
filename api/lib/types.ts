/**
 * Type Definitions
 *
 * Domain types for the graph database and API responses.
 */

// ───────────────────────────────────────────────────────────────────────────
// Story Types
// ───────────────────────────────────────────────────────────────────────────

export type StoryStatus = 'active' | 'completed' | 'killed';

export type NarrativePerspective =
  | 'first-person'
  | 'third-person-limited'
  | 'third-person-omniscient';

export type Tone = 'dark' | 'humorous' | 'philosophical' | 'surreal' | 'absurd';

export interface Story {
  id: string;
  title: string;
  premise: string;
  status: StoryStatus;
  createdAt: Date;
  completedAt?: Date;
  completionReason?: string;
  coverImageUrl?: string;
  styleAuthors: string[];
  narrativePerspective: NarrativePerspective;
  tone: Tone;
  genreTags: string[];
  estimatedReadingMinutes: number;
  totalTokens: number;
}

export interface StoryWithDetails extends Story {
  chapters: ChapterWithChaos[];
  evaluations: Evaluation[];
  entities: EntityMention[];
  tomVariant?: TomVariant;
}

// ───────────────────────────────────────────────────────────────────────────
// Chapter Types
// ───────────────────────────────────────────────────────────────────────────

export interface Chapter {
  id: string;
  chapterNumber: number;
  content: string; // Markdown
  createdAt: Date;
  tokensUsed: number;
  generationTimeMs: number;
  modelUsed: string;
  wordCount: number;
  contentLevels: ContentLevels;
}

export interface ChapterWithChaos extends Chapter {
  chaos: ChaosParameters;
}

export interface ChaosParameters {
  absurdity: number;
  surrealism: number;
  ridiculousness: number;
  insanity: number;
}

export interface ContentLevels {
  sexualContent: number;
  violence: number;
  strongLanguage: number;
  drugUse: number;
  horrorSuspense: number;
  goreGraphicImagery: number;
  romanceFocus: number;
  crimeIllicitActivity: number;
  politicalIdeology: number;
  supernaturalOccult: number;
  cosmicHorror: number;
  bureaucraticSatire: number;
  archivalGlitch: number;
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Types
// ───────────────────────────────────────────────────────────────────────────

export type EntityType = 'character' | 'place' | 'object' | 'concept' | 'organization';

export interface Entity {
  id: string;
  name: string;
  canonicalName: string;
  entityType: EntityType;
  description?: string;
  aliases: string[];
  firstSeenAt: Date;
  totalMentions: number;
  importance: number;
  updatedAt: Date;
}

export interface EntityMention {
  entity: Entity;
  firstChapterNumber: number;
  lastChapterNumber: number;
  mentionCount: number;
  importance: number;
  sentiment: 'positive' | 'negative' | 'neutral' | 'complex';
  relationshipToTom: 'ally' | 'antagonist' | 'neutral' | 'unknown';
}

// ───────────────────────────────────────────────────────────────────────────
// Theme Types
// ───────────────────────────────────────────────────────────────────────────

export type ThemeCategory =
  | 'philosophical'
  | 'technological'
  | 'social'
  | 'existential'
  | 'absurd';

export interface Theme {
  id: string;
  name: string;
  category: ThemeCategory;
  description?: string;
  firstSeenAt: Date;
  storyCount: number;
  updatedAt: Date;
}

export interface ThemeExploration {
  theme: Theme;
  weight: number;
  introducedInChapter: number;
  lastSeenInChapter: number;
  prominence: 'major' | 'minor' | 'background';
}

// ───────────────────────────────────────────────────────────────────────────
// Evaluation Types
// ───────────────────────────────────────────────────────────────────────────

export interface Evaluation {
  id: string;
  chapterNumber: number;
  overallScore: number;
  coherenceScore: number;
  noveltyScore: number;
  engagementScore: number;
  pacingScore: number;
  shouldContinue: boolean;
  reasoning: string;
  issues: string[];
  evaluatedAt: Date;
  modelUsed: string;
}

// ───────────────────────────────────────────────────────────────────────────
// Universe Types
// ───────────────────────────────────────────────────────────────────────────

export interface Universe {
  id: string;
  name: string;
  description: string;
  createdAt: Date;
  storyCount: number;
  cohesionScore: number;
  primaryThemes: string[];
  primaryEntities: string[];
}

export interface UniverseLink {
  sourceStory: string;
  targetStory: string;
  weight: number;
  sharedEntities: string[];
  sharedThemes: string[];
  similarityChaosProfile: number;
  similarityContentProfile: number;
  discoveredAt: Date;
}

// ───────────────────────────────────────────────────────────────────────────
// Tom Types
// ───────────────────────────────────────────────────────────────────────────

export interface TomVariant {
  variantName: string; // "Tom", "Tommy", "Thomas", etc.
  role: string; // "protagonist", "engineer", "tinkerer", "observer"
  characterization?: string; // How Tom is characterized in this story
  firstAppearanceChapter: number;
}

export interface TomCanonical {
  id: 'tom-canonical';
  name: 'Tom';
  description: string;
  role: 'canonical-character';
  totalAppearances: number;
  createdAt: Date;
}

// ───────────────────────────────────────────────────────────────────────────
// Story Generation Types
// ───────────────────────────────────────────────────────────────────────────

export interface GenerationConfig {
  // Chaos initialization
  absurdityInitial: number;
  surrealismInitial: number;
  ridiculousnessInitial: number;
  insanityInitial: number;

  // Chaos increments per chapter
  absurdityIncrement: number;
  surrealismIncrement: number;
  ridiculousnessIncrement: number;
  insanityIncrement: number;

  // Content axis targets (average levels to aim for)
  contentTargets: Partial<ContentLevels>;

  // Generation parameters
  maxTokens: number;
  temperature: number;
  model: string;
}

export interface PremiseResponse {
  title: string;
  premise: string; // Markdown
  styleAuthors: string[];
  narrativePerspective: NarrativePerspective;
  tone: Tone;
  genreTags: string[];
  tomVariant: string; // How Tom appears in this story
  chaosInitial: ChaosParameters;
  chaosIncrements: ChaosParameters;
}

export interface ChapterResponse {
  content: string; // Markdown
  chaos: ChaosParameters; // Actual values from this chapter
  contentLevels: ContentLevels;
  entities?: string[]; // Extracted entities mentioned
  tokensUsed: number;
}

export interface EvaluationResponse {
  overallScore: number;
  coherenceScore: number;
  noveltyScore: number;
  engagementScore: number;
  pacingScore: number;
  shouldContinue: boolean;
  reasoning: string;
  issues: string[];
}

// ───────────────────────────────────────────────────────────────────────────
// API Response Types
// ───────────────────────────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface StatsResponse {
  stories: {
    active: number;
    completed: number;
    killed: number;
    total: number;
  };
  chapters: {
    total: number;
    recentChapters: Chapter[];
  };
  tokens: {
    total: number;
  };
  chaos: {
    avgAbsurdity: number;
    avgSurrealism: number;
    avgRidiculousness: number;
    avgInsanity: number;
  };
  content: Partial<ContentLevels>;
  entities: {
    total: number;
    topEntities: Array<{
      name: string;
      mentions: number;
      importance: number;
    }>;
  };
  universes: {
    total: number;
    clusters: number;
  };
  tom: {
    totalAppearances: number;
    variants: string[];
  };
}

// ───────────────────────────────────────────────────────────────────────────
// Configuration Types
// ───────────────────────────────────────────────────────────────────────────

export interface RuntimeConfig {
  // Story pool management
  minActiveStories: number;
  maxActiveStories: number;
  maxChaptersPerStory: number;

  // Timing
  chapterIntervalMinutes: number;
  evaluationIntervalChapters: number;

  // Quality thresholds
  qualityScoreMin: number;

  // Cover art generation
  coverArtBackfillEnabled: boolean;
  coverArtBackfillBatchSize: number;

  // OpenAI models
  modelPremise: string;
  modelChapter: string;
  modelEvaluation: string;
  modelCoverArt: string;

  // Token budgets
  maxTokensPremise: number;
  maxTokensChapter: number;
  maxTokensEvaluation: number;
}

// ───────────────────────────────────────────────────────────────────────────
// SSE Event Types
// ───────────────────────────────────────────────────────────────────────────

export type SSEEventType =
  | 'new_story'
  | 'new_chapter'
  | 'story_completed'
  | 'story_evaluated'
  | 'system_reset';

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
  timestamp: number;
}
