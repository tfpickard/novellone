/**
 * Entity Operations
 *
 * Handles entity extraction, linking, and relationship management in the graph.
 */

import { v4 as uuidv4 } from 'uuid';
import {
  executeRead,
  executeWrite,
  executeWriteTransaction,
  extractNodeProperties,
  toNumber,
} from './neo4j.js';
import { extractEntities } from './openai.js';
import type { Entity, EntityMention } from './types.js';

// ───────────────────────────────────────────────────────────────────────────
// Entity Extraction
// ───────────────────────────────────────────────────────────────────────────

/**
 * Extract entities from chapter content and link them to the story.
 */
export async function extractAndLinkEntities(
  storyId: string,
  chapterId: string,
  chapterNumber: number,
  content: string
): Promise<number> {
  console.log(`[Entity] Extracting entities from chapter ${chapterNumber} of story ${storyId}...`);

  // Extract entities using OpenAI
  const extractedEntities = await extractEntities(content);

  if (extractedEntities.length === 0) {
    console.log(`[Entity] No entities extracted`);
    return 0;
  }

  console.log(`[Entity] Extracted ${extractedEntities.length} entities:`, extractedEntities.map(e => e.name));

  let linkedCount = 0;

  // Process each entity
  for (const extracted of extractedEntities) {
    try {
      await createOrUpdateEntity(
        storyId,
        chapterId,
        chapterNumber,
        extracted.name,
        extracted.type,
        extracted.importance
      );
      linkedCount++;
    } catch (error) {
      console.error(`[Entity] Failed to create/link entity "${extracted.name}":`, error);
    }
  }

  console.log(`[Entity] Linked ${linkedCount} entities to story`);

  return linkedCount;
}

/**
 * Create or update an entity and link it to a story.
 */
async function createOrUpdateEntity(
  storyId: string,
  chapterId: string,
  chapterNumber: number,
  name: string,
  entityType: string,
  importance: number
): Promise<void> {
  // Normalize name to canonical form (lowercase, trimmed)
  const canonicalName = name.toLowerCase().trim();

  const query = `
    // Merge entity (create if doesn't exist)
    MERGE (e:Entity {canonicalName: $canonicalName})
    ON CREATE SET
      e.id = $entityId,
      e.name = $name,
      e.entityType = $entityType,
      e.description = null,
      e.aliases = [],
      e.firstSeenAt = timestamp(),
      e.totalMentions = 0,
      e.importance = $importance,
      e.updatedAt = timestamp()
    ON MATCH SET
      e.totalMentions = e.totalMentions + 1,
      e.importance = (e.importance + $importance) / 2.0,
      e.updatedAt = timestamp()

    // Link to story
    WITH e
    MATCH (s:Story {id: $storyId})
    MERGE (s)-[m:MENTIONS]->(e)
    ON CREATE SET
      m.firstChapterNumber = $chapterNumber,
      m.lastChapterNumber = $chapterNumber,
      m.mentionCount = 1,
      m.importance = $importance,
      m.sentiment = 'neutral',
      m.relationshipToTom = 'unknown'
    ON MATCH SET
      m.lastChapterNumber = $chapterNumber,
      m.mentionCount = m.mentionCount + 1,
      m.importance = ($importance + m.importance) / 2.0

    // Link to chapter
    WITH e
    MATCH (c:Chapter {id: $chapterId})
    MERGE (c)-[f:FEATURES {
      prominence: CASE WHEN $importance > 0.7 THEN 'major'
                       WHEN $importance > 0.4 THEN 'minor'
                       ELSE 'mention' END,
      sentimentInChapter: 'neutral'
    }]->(e)

    RETURN e
  `;

  await executeWrite(query, {
    entityId: uuidv4(),
    canonicalName,
    name,
    entityType,
    importance,
    storyId,
    chapterId,
    chapterNumber,
  });
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Queries
// ───────────────────────────────────────────────────────────────────────────

/**
 * Get all entities for a story.
 */
export async function getStoryEntities(storyId: string): Promise<EntityMention[]> {
  const query = `
    MATCH (s:Story {id: $storyId})-[m:MENTIONS]->(e:Entity)
    RETURN e, m
    ORDER BY m.importance DESC, m.mentionCount DESC
  `;

  const result = await executeRead(query, { storyId });

  return result.records.map((record) => {
    const entity = extractNodeProperties<Entity>(record.get('e'));
    const mention = record.get('m').properties;

    return {
      entity,
      firstChapterNumber: toNumber(mention.firstChapterNumber),
      lastChapterNumber: toNumber(mention.lastChapterNumber),
      mentionCount: toNumber(mention.mentionCount),
      importance: mention.importance || 0,
      sentiment: mention.sentiment || 'neutral',
      relationshipToTom: mention.relationshipToTom || 'unknown',
    };
  });
}

/**
 * Get top entities across all stories.
 */
export async function getTopEntities(limit: number = 20): Promise<Entity[]> {
  const query = `
    MATCH (e:Entity)
    RETURN e
    ORDER BY e.totalMentions DESC, e.importance DESC
    LIMIT $limit
  `;

  const result = await executeRead(query, { limit });

  return result.records.map((record) =>
    extractNodeProperties<Entity>(record.get('e'))
  );
}

/**
 * Get entity with all its story appearances.
 */
export async function getEntityWithAppearances(entityId: string): Promise<{
  entity: Entity;
  appearances: Array<{
    storyId: string;
    storyTitle: string;
    mentionCount: number;
    importance: number;
    firstChapter: number;
    lastChapter: number;
  }>;
}> {
  const query = `
    MATCH (e:Entity {id: $entityId})
    OPTIONAL MATCH (s:Story)-[m:MENTIONS]->(e)
    RETURN e,
           COLLECT({
             storyId: s.id,
             storyTitle: s.title,
             mentionCount: m.mentionCount,
             importance: m.importance,
             firstChapter: m.firstChapterNumber,
             lastChapter: m.lastChapterNumber
           }) as appearances
  `;

  const result = await executeRead(query, { entityId });

  if (result.records.length === 0) {
    throw new Error(`Entity ${entityId} not found`);
  }

  const record = result.records[0];
  const entity = extractNodeProperties<Entity>(record.get('e'));
  const appearances = record.get('appearances');

  return {
    entity,
    appearances: appearances.map((a: any) => ({
      storyId: a.storyId,
      storyTitle: a.storyTitle,
      mentionCount: toNumber(a.mentionCount),
      importance: a.importance || 0,
      firstChapter: toNumber(a.firstChapter),
      lastChapter: toNumber(a.lastChapter),
    })),
  };
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Relationships
// ───────────────────────────────────────────────────────────────────────────

/**
 * Discover and create relationships between entities that co-occur in stories.
 * This should be run periodically to build the entity relationship graph.
 */
export async function discoverEntityRelationships(
  minCooccurrences: number = 2
): Promise<number> {
  console.log('[Entity] Discovering entity relationships...');

  const query = `
    // Find entities that appear together in stories
    MATCH (e1:Entity)<-[:MENTIONS]-(s:Story)-[:MENTIONS]->(e2:Entity)
    WHERE id(e1) < id(e2)
    WITH e1, e2,
         COUNT(DISTINCT s) as coappearances,
         COLLECT(DISTINCT s.id) as storyIds
    WHERE coappearances >= $minCooccurrences

    // Create or update RELATED_TO relationship
    MERGE (e1)-[r:RELATED_TO]->(e2)
    SET r.cooccurrenceCount = coappearances,
        r.stories = storyIds,
        r.strength = coappearances / 10.0,
        r.relationshipType = 'appears-with'

    RETURN COUNT(r) as relationshipsCreated
  `;

  const result = await executeWrite(query, { minCooccurrences });
  const count = toNumber(result.records[0]?.get('relationshipsCreated') || 0);

  console.log(`[Entity] Created/updated ${count} entity relationships`);

  return count;
}

/**
 * Get entities that frequently appear with a given entity.
 */
export async function getRelatedEntities(
  entityId: string,
  limit: number = 10
): Promise<Array<{
  entity: Entity;
  cooccurrences: number;
  strength: number;
  stories: string[];
}>> {
  const query = `
    MATCH (e1:Entity {id: $entityId})-[r:RELATED_TO]-(e2:Entity)
    RETURN e2 as entity, r
    ORDER BY r.strength DESC
    LIMIT $limit
  `;

  const result = await executeRead(query, { entityId, limit });

  return result.records.map((record) => ({
    entity: extractNodeProperties<Entity>(record.get('entity')),
    cooccurrences: toNumber(record.get('r').properties.cooccurrenceCount),
    strength: record.get('r').properties.strength || 0,
    stories: record.get('r').properties.stories || [],
  }));
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Merging & Deduplication
// ───────────────────────────────────────────────────────────────────────────

/**
 * Merge two entities (consolidate mentions and relationships).
 * Useful when the same entity is extracted with different names.
 */
export async function mergeEntities(
  sourceEntityId: string,
  targetEntityId: string
): Promise<void> {
  console.log(`[Entity] Merging entity ${sourceEntityId} into ${targetEntityId}...`);

  await executeWriteTransaction(async (tx) => {
    // 1. Copy all MENTIONS relationships from source to target
    await tx.run(`
      MATCH (source:Entity {id: $sourceEntityId})<-[sm:MENTIONS]-(s:Story)
      MATCH (target:Entity {id: $targetEntityId})
      MERGE (s)-[tm:MENTIONS]->(target)
      ON CREATE SET tm = sm
      ON MATCH SET
        tm.mentionCount = tm.mentionCount + sm.mentionCount,
        tm.importance = (tm.importance + sm.importance) / 2.0,
        tm.lastChapterNumber = CASE
          WHEN tm.lastChapterNumber > sm.lastChapterNumber
          THEN tm.lastChapterNumber
          ELSE sm.lastChapterNumber
        END
    `, { sourceEntityId, targetEntityId });

    // 2. Copy all FEATURES relationships from source to target
    await tx.run(`
      MATCH (source:Entity {id: $sourceEntityId})<-[sf:FEATURES]-(c:Chapter)
      MATCH (target:Entity {id: $targetEntityId})
      MERGE (c)-[tf:FEATURES]->(target)
      ON CREATE SET tf = sf
    `, { sourceEntityId, targetEntityId });

    // 3. Update target entity's total mentions
    await tx.run(`
      MATCH (target:Entity {id: $targetEntityId})
      MATCH (target)<-[m:MENTIONS]-(:Story)
      WITH target, SUM(m.mentionCount) as totalMentions
      SET target.totalMentions = totalMentions,
          target.updatedAt = timestamp()
    `, { targetEntityId });

    // 4. Delete source entity
    await tx.run(`
      MATCH (source:Entity {id: $sourceEntityId})
      DETACH DELETE source
    `, { sourceEntityId });
  });

  console.log(`[Entity] Merge complete`);
}

/**
 * Find potential entity duplicates based on name similarity.
 * Returns pairs of entities that might be the same.
 */
export async function findPotentialDuplicates(): Promise<Array<{
  entity1: Entity;
  entity2: Entity;
  similarity: number;
}>> {
  const query = `
    // Find entities with similar canonical names
    MATCH (e1:Entity), (e2:Entity)
    WHERE id(e1) < id(e2)
      AND (
        e1.canonicalName CONTAINS e2.canonicalName
        OR e2.canonicalName CONTAINS e1.canonicalName
      )
    RETURN e1, e2,
           CASE
             WHEN e1.canonicalName = e2.canonicalName THEN 1.0
             ELSE 0.8
           END as similarity
    ORDER BY similarity DESC
    LIMIT 50
  `;

  const result = await executeRead(query);

  return result.records.map((record) => ({
    entity1: extractNodeProperties<Entity>(record.get('e1')),
    entity2: extractNodeProperties<Entity>(record.get('e2')),
    similarity: record.get('similarity') || 0,
  }));
}

// ───────────────────────────────────────────────────────────────────────────
// Entity Statistics
// ───────────────────────────────────────────────────────────────────────────

/**
 * Get entity statistics for the dashboard.
 */
export async function getEntityStats(): Promise<{
  totalEntities: number;
  totalRelationships: number;
  topEntityTypes: Array<{ type: string; count: number }>;
  avgMentionsPerEntity: number;
}> {
  // Total entities
  const totalQuery = `MATCH (e:Entity) RETURN COUNT(e) as total`;
  const totalResult = await executeRead(totalQuery);
  const totalEntities = toNumber(totalResult.records[0]?.get('total') || 0);

  // Total relationships
  const relationshipsQuery = `MATCH ()-[r:RELATED_TO]->() RETURN COUNT(r) as total`;
  const relationshipsResult = await executeRead(relationshipsQuery);
  const totalRelationships = toNumber(relationshipsResult.records[0]?.get('total') || 0);

  // Top entity types
  const typesQuery = `
    MATCH (e:Entity)
    RETURN e.entityType as type, COUNT(e) as count
    ORDER BY count DESC
    LIMIT 5
  `;
  const typesResult = await executeRead(typesQuery);
  const topEntityTypes = typesResult.records.map((record) => ({
    type: record.get('type'),
    count: toNumber(record.get('count')),
  }));

  // Average mentions
  const avgQuery = `MATCH (e:Entity) RETURN AVG(e.totalMentions) as avg`;
  const avgResult = await executeRead(avgQuery);
  const avgMentionsPerEntity = avgResult.records[0]?.get('avg') || 0;

  return {
    totalEntities,
    totalRelationships,
    topEntityTypes,
    avgMentionsPerEntity,
  };
}
