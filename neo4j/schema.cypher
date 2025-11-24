// ═══════════════════════════════════════════════════════════════════════════
// HURL UNMASKS RECURSIVE LITERATURE LEAKING OUT LIGHT
// Neo4j Graph Schema - Designed for autonomous storytelling universe
// ═══════════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────────
// NODE TYPES
// ───────────────────────────────────────────────────────────────────────────

// Story - A narrative with chapters and metadata
// Properties: id, title, premise, status, createdAt, completedAt,
//             completionReason, coverImageUrl, styleAuthors[],
//             narrativePerspective, tone, genreTags[]
(:Story {
  id: "UUID",
  title: "string",
  premise: "text",
  status: "active|completed|killed",
  createdAt: "timestamp",
  completedAt: "timestamp?",
  completionReason: "string?",
  coverImageUrl: "string?",
  styleAuthors: ["author1", "author2"],
  narrativePerspective: "first-person|third-person-limited|third-person-omniscient",
  tone: "dark|humorous|philosophical|surreal",
  genreTags: ["tag1", "tag2"],
  estimatedReadingMinutes: "number",
  totalTokens: "number"
})

// Chapter - Individual installment of a story with chaos readings
// Properties: id, chapterNumber, content, createdAt, tokensUsed,
//             generationTimeMs, modelUsed, wordCount
// Content intensity levels stored as properties
(:Chapter {
  id: "UUID",
  chapterNumber: "number",
  content: "text (markdown)",
  createdAt: "timestamp",
  tokensUsed: "number",
  generationTimeMs: "number",
  modelUsed: "string",
  wordCount: "number",

  // Content intensity readings for this chapter
  sexualContent: "0.0-1.0",
  violence: "0.0-1.0",
  strongLanguage: "0.0-1.0",
  drugUse: "0.0-1.0",
  horrorSuspense: "0.0-1.0",
  goreGraphicImagery: "0.0-1.0",
  romanceFocus: "0.0-1.0",
  crimeIllicitActivity: "0.0-1.0",
  politicalIdeology: "0.0-1.0",
  supernaturalOccult: "0.0-1.0",
  cosmicHorror: "0.0-1.0",
  bureaucraticSatire: "0.0-1.0",
  archivalGlitch: "0.0-1.0"
})

// Entity - Character, place, object, or concept mentioned in stories
// The graph naturally tracks which stories share entities
(:Entity {
  id: "UUID",
  name: "string",
  canonicalName: "string", // normalized version
  entityType: "character|place|object|concept|organization",
  description: "text?",
  aliases: ["alias1", "alias2"],
  firstSeenAt: "timestamp",
  totalMentions: "number",
  importance: "0.0-1.0", // calculated from mention frequency & story count
  updatedAt: "timestamp"
})

// Theme - Thematic element explored in stories
(:Theme {
  id: "UUID",
  name: "string",
  category: "philosophical|technological|social|existential|absurd",
  description: "text?",
  firstSeenAt: "timestamp",
  storyCount: "number",
  updatedAt: "timestamp"
})

// Universe - A cluster of stories that share significant connections
// Could be thematic, entity-based, or stylistic
(:Universe {
  id: "UUID",
  name: "string",
  description: "text",
  createdAt: "timestamp",
  storyCount: "number",
  cohesionScore: "0.0-1.0", // how tightly connected
  primaryThemes: ["theme1", "theme2"],
  primaryEntities: ["entity1", "entity2"]
})

// Evaluation - Quality assessment of a story at a specific chapter
(:Evaluation {
  id: "UUID",
  chapterNumber: "number",
  overallScore: "0.0-1.0",
  coherenceScore: "0.0-1.0",
  noveltyScore: "0.0-1.0",
  engagementScore: "0.0-1.0",
  pacingScore: "0.0-1.0",
  shouldContinue: "boolean",
  reasoning: "text",
  issues: ["issue1", "issue2"],
  evaluatedAt: "timestamp",
  modelUsed: "string"
})

// Tom - The canonical protagonist who appears in every story
// Each story creates a variant relationship to this node
(:Tom {
  id: "tom-canonical",
  name: "Tom",
  description: "The tinkering engineer who anchors every premise",
  role: "canonical-character",
  totalAppearances: "number",
  createdAt: "timestamp"
})

// ───────────────────────────────────────────────────────────────────────────
// RELATIONSHIPS
// ───────────────────────────────────────────────────────────────────────────

// Story contains chapters (ordered)
(:Story)-[:HAS_CHAPTER {
  order: "number", // same as chapterNumber but on relationship for ordering

  // Chaos parameters at this point in the story
  absurdity: "0.0-1.0",
  surrealism: "0.0-1.0",
  ridiculousness: "0.0-1.0",
  insanity: "0.0-1.0",

  // These are calculated from story's initial + increment * order
  createdAt: "timestamp"
}]->(:Chapter)

// Story mentions entities (weighted by frequency)
(:Story)-[:MENTIONS {
  firstChapterNumber: "number",
  lastChapterNumber: "number",
  mentionCount: "number",
  importance: "0.0-1.0", // how central to the story
  sentiment: "positive|negative|neutral|complex",
  relationshipToTom: "ally|antagonist|neutral|unknown"
}]->(:Entity)

// Story explores themes (weighted by prominence)
(:Story)-[:EXPLORES {
  weight: "0.0-1.0",
  introducedInChapter: "number",
  lastSeenInChapter: "number",
  prominence: "major|minor|background"
}]->(:Theme)

// Stories share universe connections
(:Story)-[:SHARES_UNIVERSE_WITH {
  weight: "0.0-1.0", // strength of connection
  sharedEntities: ["entity1", "entity2"],
  sharedThemes: ["theme1", "theme2"],
  similarityChaosProfile: "0.0-1.0",
  similarityContentProfile: "0.0-1.0",
  discoveredAt: "timestamp"
}]->(:Story)

// Story belongs to universe clusters
(:Story)-[:BELONGS_TO {
  joinedAt: "timestamp",
  membershipStrength: "0.0-1.0",
  contributingFactors: ["shared-entities", "thematic-overlap", "style-similarity"]
}]->(:Universe)

// Story was evaluated
(:Story)-[:WAS_EVALUATED {
  atChapterNumber: "number",
  evaluatedAt: "timestamp"
}]->(:Evaluation)

// Evaluation references the chapter it was performed after
(:Evaluation)-[:EVALUATED_AFTER]->(:Chapter)

// Entities can be related to each other
(:Entity)-[:RELATED_TO {
  relationshipType: "appears-with|opposes|allied-with|transformed-from",
  cooccurrenceCount: "number",
  stories: ["storyId1", "storyId2"],
  strength: "0.0-1.0"
}]->(:Entity)

// Every story has a Tom variant
(:Story)-[:FEATURES_TOM {
  variantName: "Tom|Thomas|T.|Tommy", // how Tom appears in this story
  role: "protagonist|engineer|tinkerer|observer",
  characterization: "text", // how Tom is characterized in this story
  firstAppearanceChapter: "number"
}]->(:Tom)

// Chapters introduce or feature entities
(:Chapter)-[:INTRODUCES {
  introducedAt: "timestamp",
  context: "text?" // brief context of introduction
}]->(:Entity)

(:Chapter)-[:FEATURES {
  prominence: "major|minor|mention",
  sentimentInChapter: "positive|negative|neutral"
}]->(:Entity)

// ───────────────────────────────────────────────────────────────────────────
// CONSTRAINTS & INDEXES
// ───────────────────────────────────────────────────────────────────────────

// Unique constraints
CREATE CONSTRAINT story_id_unique IF NOT EXISTS
FOR (s:Story) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT chapter_id_unique IF NOT EXISTS
FOR (c:Chapter) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT theme_id_unique IF NOT EXISTS
FOR (t:Theme) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT universe_id_unique IF NOT EXISTS
FOR (u:Universe) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT evaluation_id_unique IF NOT EXISTS
FOR (ev:Evaluation) REQUIRE ev.id IS UNIQUE;

CREATE CONSTRAINT tom_id_unique IF NOT EXISTS
FOR (tm:Tom) REQUIRE tm.id IS UNIQUE;

// Property uniqueness
CREATE CONSTRAINT entity_canonical_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.canonicalName IS UNIQUE;

// Indexes for common queries
CREATE INDEX story_status_idx IF NOT EXISTS
FOR (s:Story) ON (s.status);

CREATE INDEX story_created_idx IF NOT EXISTS
FOR (s:Story) ON (s.createdAt);

CREATE INDEX chapter_number_idx IF NOT EXISTS
FOR (c:Chapter) ON (c.chapterNumber);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.entityType);

CREATE INDEX theme_name_idx IF NOT EXISTS
FOR (t:Theme) ON (t.name);

CREATE INDEX evaluation_chapter_idx IF NOT EXISTS
FOR (ev:Evaluation) ON (ev.chapterNumber);

// Full-text search indexes
CREATE FULLTEXT INDEX entity_search_idx IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

CREATE FULLTEXT INDEX story_search_idx IF NOT EXISTS
FOR (s:Story) ON EACH [s.title, s.premise];

CREATE FULLTEXT INDEX chapter_search_idx IF NOT EXISTS
FOR (c:Chapter) ON EACH [c.content];

// ───────────────────────────────────────────────────────────────────────────
// INITIALIZATION
// ───────────────────────────────────────────────────────────────────────────

// Create the canonical Tom node
MERGE (tom:Tom {id: "tom-canonical"})
SET tom.name = "Tom",
    tom.description = "The tinkering engineer who anchors every premise",
    tom.role = "canonical-character",
    tom.totalAppearances = 0,
    tom.createdAt = timestamp();

// ───────────────────────────────────────────────────────────────────────────
// EXAMPLE QUERIES
// ───────────────────────────────────────────────────────────────────────────

// Find all active stories
// MATCH (s:Story {status: "active"}) RETURN s ORDER BY s.createdAt DESC;

// Get a story with all its chapters in order
// MATCH (s:Story {id: $storyId})-[r:HAS_CHAPTER]->(c:Chapter)
// RETURN s, r, c ORDER BY r.order;

// Find stories that share the most entities
// MATCH (s1:Story)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(s2:Story)
// WHERE id(s1) < id(s2)
// WITH s1, s2, COUNT(e) as sharedEntities
// ORDER BY sharedEntities DESC
// RETURN s1.title, s2.title, sharedEntities LIMIT 10;

// Find all appearances of an entity across stories
// MATCH (e:Entity {name: "Tom"})<-[m:MENTIONS]-(s:Story)
// RETURN s.title, m.mentionCount, m.importance
// ORDER BY m.importance DESC;

// Get chaos evolution for a story
// MATCH (s:Story {id: $storyId})-[r:HAS_CHAPTER]->(c:Chapter)
// RETURN c.chapterNumber, r.absurdity, r.surrealism, r.ridiculousness, r.insanity
// ORDER BY c.chapterNumber;

// Find universes and their stories
// MATCH (u:Universe)<-[:BELONGS_TO]-(s:Story)
// RETURN u.name, u.cohesionScore, COLLECT(s.title) as stories;

// Find Tom's most interesting variants
// MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
// WHERE s.status = "completed"
// RETURN s.title, f.variantName, f.role, f.characterization
// ORDER BY s.createdAt DESC LIMIT 20;

// Get evaluation history for a story
// MATCH (s:Story {id: $storyId})-[:WAS_EVALUATED]->(ev:Evaluation)
// RETURN ev ORDER BY ev.chapterNumber;

// Find entities that frequently appear together
// MATCH (e1:Entity)<-[:MENTIONS]-(s:Story)-[:MENTIONS]->(e2:Entity)
// WHERE id(e1) < id(e2)
// WITH e1, e2, COUNT(DISTINCT s) as coappearances
// WHERE coappearances > 1
// RETURN e1.name, e2.name, coappearances
// ORDER BY coappearances DESC LIMIT 20;
