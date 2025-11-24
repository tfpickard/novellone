// ═══════════════════════════════════════════════════════════════════════════
// COMMON QUERIES - Practical Cypher patterns for the application
// ═══════════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────────
// STORY OPERATIONS
// ───────────────────────────────────────────────────────────────────────────

// Create a new story with initial chaos parameters
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
RETURN s;

// Get active stories (for story pool management)
MATCH (s:Story {status: 'active'})
OPTIONAL MATCH (s)-[hc:HAS_CHAPTER]->(c:Chapter)
WITH s, MAX(c.chapterNumber) as lastChapter, MAX(c.createdAt) as lastChapterAt
RETURN s, lastChapter, lastChapterAt
ORDER BY s.createdAt DESC;

// Get story with full details (chapters, evaluations, entities)
MATCH (s:Story {id: $storyId})
OPTIONAL MATCH (s)-[hc:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (s)-[:WAS_EVALUATED]->(ev:Evaluation)
OPTIONAL MATCH (s)-[m:MENTIONS]->(e:Entity)
RETURN s,
       COLLECT(DISTINCT {chapter: c, chaos: properties(hc)}) as chapters,
       COLLECT(DISTINCT ev) as evaluations,
       COLLECT(DISTINCT {entity: e, mentions: m}) as entities
ORDER BY c.chapterNumber;

// Complete a story
MATCH (s:Story {id: $storyId})
SET s.status = 'completed',
    s.completedAt = timestamp(),
    s.completionReason = $reason
RETURN s;

// Kill a story early
MATCH (s:Story {id: $storyId})
SET s.status = 'killed',
    s.completedAt = timestamp(),
    s.completionReason = $reason
RETURN s;

// Update story cover image URL (after generating with DALL-E and uploading to Blob)
MATCH (s:Story {id: $storyId})
SET s.coverImageUrl = $coverImageUrl
RETURN s;

// ───────────────────────────────────────────────────────────────────────────
// CHAPTER OPERATIONS
// ───────────────────────────────────────────────────────────────────────────

// Add a chapter to a story with chaos evolution
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
    s.estimatedReadingMinutes = s.totalTokens / 250 // ~250 tokens per minute reading
RETURN c;

// Get chapters for a story in order
MATCH (s:Story {id: $storyId})-[hc:HAS_CHAPTER]->(c:Chapter)
RETURN c, hc
ORDER BY c.chapterNumber;

// Get latest chapter for a story
MATCH (s:Story {id: $storyId})-[hc:HAS_CHAPTER]->(c:Chapter)
RETURN c, hc
ORDER BY c.chapterNumber DESC
LIMIT 1;

// ───────────────────────────────────────────────────────────────────────────
// EVALUATION OPERATIONS
// ───────────────────────────────────────────────────────────────────────────

// Create an evaluation for a story
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
RETURN ev;

// Get evaluation history for a story
MATCH (s:Story {id: $storyId})-[:WAS_EVALUATED]->(ev:Evaluation)
RETURN ev
ORDER BY ev.chapterNumber;

// Get latest evaluation
MATCH (s:Story {id: $storyId})-[:WAS_EVALUATED]->(ev:Evaluation)
RETURN ev
ORDER BY ev.chapterNumber DESC
LIMIT 1;

// ───────────────────────────────────────────────────────────────────────────
// ENTITY OPERATIONS
// ───────────────────────────────────────────────────────────────────────────

// Create or update an entity
MERGE (e:Entity {canonicalName: $canonicalName})
ON CREATE SET
  e.id = $id,
  e.name = $name,
  e.entityType = $entityType,
  e.description = $description,
  e.aliases = $aliases,
  e.firstSeenAt = timestamp(),
  e.totalMentions = 1,
  e.importance = 0.5
ON MATCH SET
  e.totalMentions = e.totalMentions + 1,
  e.updatedAt = timestamp()
RETURN e;

// Link entity to story
MATCH (s:Story {id: $storyId})
MATCH (e:Entity {id: $entityId})
MERGE (s)-[m:MENTIONS]->(e)
ON CREATE SET
  m.firstChapterNumber = $chapterNumber,
  m.lastChapterNumber = $chapterNumber,
  m.mentionCount = 1,
  m.importance = $importance,
  m.sentiment = $sentiment,
  m.relationshipToTom = $relationshipToTom
ON MATCH SET
  m.lastChapterNumber = $chapterNumber,
  m.mentionCount = m.mentionCount + 1,
  m.importance = ($importance + m.importance) / 2.0
RETURN m;

// Link entity to chapter
MATCH (c:Chapter {id: $chapterId})
MATCH (e:Entity {id: $entityId})
MERGE (c)-[f:FEATURES {
  prominence: $prominence,
  sentimentInChapter: $sentiment
}]->(e)
RETURN f;

// Find entities by name (fuzzy search)
CALL db.index.fulltext.queryNodes('entity_search_idx', $searchTerm)
YIELD node, score
RETURN node as entity, score
ORDER BY score DESC
LIMIT 10;

// Get entity with all its story appearances
MATCH (e:Entity {id: $entityId})
OPTIONAL MATCH (s:Story)-[m:MENTIONS]->(e)
RETURN e, COLLECT({
  story: s,
  mentionCount: m.mentionCount,
  importance: m.importance,
  firstChapter: m.firstChapterNumber,
  lastChapter: m.lastChapterNumber
}) as appearances
ORDER BY m.importance DESC;

// Find entities that appear together frequently
MATCH (e1:Entity)<-[:MENTIONS]-(s:Story)-[:MENTIONS]->(e2:Entity)
WHERE id(e1) < id(e2) AND e1.id = $entityId
WITH e1, e2, COUNT(DISTINCT s) as coappearances, COLLECT(DISTINCT s.id) as storyIds
WHERE coappearances >= $minCoappearances
MERGE (e1)-[r:RELATED_TO]->(e2)
SET r.cooccurrenceCount = coappearances,
    r.stories = storyIds,
    r.strength = coappearances / 10.0,
    r.relationshipType = 'appears-with'
RETURN e1, e2, r;

// ───────────────────────────────────────────────────────────────────────────
// UNIVERSE & CLUSTERING OPERATIONS
// ───────────────────────────────────────────────────────────────────────────

// Find stories that share entities and create universe links
MATCH (s1:Story)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(s2:Story)
WHERE s1.id < s2.id
WITH s1, s2,
     COLLECT(DISTINCT e.name) as sharedEntities,
     COUNT(DISTINCT e) as entityCount
WHERE entityCount >= $minSharedEntities
MATCH (s1)-[:EXPLORES]->(t:Theme)<-[:EXPLORES]-(s2)
WITH s1, s2, sharedEntities, entityCount,
     COLLECT(DISTINCT t.name) as sharedThemes,
     COUNT(DISTINCT t) as themeCount
WITH s1, s2, sharedEntities, sharedThemes,
     (entityCount * 0.6 + themeCount * 0.4) / 10.0 as weight
MERGE (s1)-[r:SHARES_UNIVERSE_WITH]->(s2)
SET r.weight = weight,
    r.sharedEntities = sharedEntities,
    r.sharedThemes = sharedThemes,
    r.discoveredAt = timestamp()
RETURN s1, s2, r;

// Create or update a universe cluster
MERGE (u:Universe {id: $universeId})
ON CREATE SET
  u.name = $name,
  u.description = $description,
  u.createdAt = timestamp(),
  u.storyCount = 0,
  u.cohesionScore = 0.0
RETURN u;

// Add story to universe
MATCH (s:Story {id: $storyId})
MATCH (u:Universe {id: $universeId})
MERGE (s)-[b:BELONGS_TO {
  joinedAt: timestamp(),
  membershipStrength: $strength,
  contributingFactors: $factors
}]->(u)
SET u.storyCount = u.storyCount + 1
RETURN b;

// Get universe with all its stories
MATCH (u:Universe {id: $universeId})
OPTIONAL MATCH (s:Story)-[b:BELONGS_TO]->(u)
RETURN u,
       COLLECT({story: s, membership: b}) as members
ORDER BY b.membershipStrength DESC;

// ───────────────────────────────────────────────────────────────────────────
// ANALYTICS & INSIGHTS
// ───────────────────────────────────────────────────────────────────────────

// Get chaos evolution across all stories (for stats dashboard)
MATCH (s:Story)-[hc:HAS_CHAPTER]->(c:Chapter)
WHERE s.status IN ['active', 'completed']
RETURN AVG(hc.absurdity) as avgAbsurdity,
       AVG(hc.surrealism) as avgSurrealism,
       AVG(hc.ridiculousness) as avgRidiculousness,
       AVG(hc.insanity) as avgInsanity;

// Get content intensity averages
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
       AVG(c.archivalGlitch) as avgArchivalGlitch;

// Get story statistics
MATCH (s:Story)
WITH s.status as status, COUNT(s) as count
RETURN status, count;

// Get total chapter count
MATCH (:Story)-[:HAS_CHAPTER]->(c:Chapter)
RETURN COUNT(c) as totalChapters;

// Get total tokens used
MATCH (s:Story)
RETURN SUM(s.totalTokens) as totalTokens;

// Find most frequently appearing entities (across all stories)
MATCH (e:Entity)
RETURN e.name, e.entityType, e.totalMentions, e.importance
ORDER BY e.totalMentions DESC
LIMIT 20;

// Find most explored themes
MATCH (t:Theme)<-[:EXPLORES]-(s:Story)
WITH t, COUNT(DISTINCT s) as storyCount
SET t.storyCount = storyCount
RETURN t.name, t.category, storyCount
ORDER BY storyCount DESC
LIMIT 20;

// Get recent activity (chapters published)
MATCH (:Story)-[:HAS_CHAPTER]->(c:Chapter)
RETURN c
ORDER BY c.createdAt DESC
LIMIT 20;

// Find Tom variants across stories
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
RETURN s.id, s.title, s.status,
       f.variantName, f.role, f.characterization
ORDER BY s.createdAt DESC;

// Get story universe connections (graph visualization data)
MATCH (s1:Story)-[r:SHARES_UNIVERSE_WITH]->(s2:Story)
WHERE r.weight >= $minWeight
RETURN s1.id, s1.title, s2.id, s2.title,
       r.weight, r.sharedEntities, r.sharedThemes
ORDER BY r.weight DESC;

// ───────────────────────────────────────────────────────────────────────────
// CLEANUP & MAINTENANCE
// ───────────────────────────────────────────────────────────────────────────

// Delete a story and all related nodes
MATCH (s:Story {id: $storyId})
OPTIONAL MATCH (s)-[:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (s)-[:WAS_EVALUATED]->(ev:Evaluation)
DETACH DELETE s, c, ev;

// Reset entire database (admin operation)
MATCH (n)
WHERE NOT n:Tom
DETACH DELETE n;

// Recalculate entity importance across all stories
MATCH (e:Entity)<-[m:MENTIONS]-(s:Story)
WITH e, COUNT(DISTINCT s) as storyCount, SUM(m.mentionCount) as totalMentions
SET e.importance = (storyCount * 0.4 + totalMentions * 0.6) / 100.0,
    e.totalMentions = totalMentions;

// Update universe cohesion scores
MATCH (u:Universe)<-[b:BELONGS_TO]-(s:Story)
WITH u, AVG(b.membershipStrength) as avgStrength
SET u.cohesionScore = avgStrength;
