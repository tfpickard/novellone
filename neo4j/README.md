# 🌌 Neo4j Graph Database Schema

## Philosophy: Why Graph?

The original PostgreSQL schema was **relational** - stories, chapters, and entities were stored as rows with foreign keys connecting them. This works, but misses the fundamental nature of this project: **stories exist in a connected universe**.

### Graph-Native Design Advantages

1. **Universe Relationships Are First-Class**
   - In PostgreSQL: Junction tables, multiple JOINs, complex queries
   - In Neo4j: `(Story)-[:SHARES_UNIVERSE_WITH]->(Story)` - natural and efficient

2. **Entity Tracking Across Stories**
   - In PostgreSQL: Cross-table queries with aggregations
   - In Neo4j: Traverse from entity to all stories instantly

3. **Tom as the Universal Anchor**
   - In PostgreSQL: Tom is mentioned in text, hard to query
   - In Neo4j: Tom is a canonical node, every story connects to him

4. **Chaos Evolution Over Time**
   - In PostgreSQL: Chaos values stored in chapters
   - In Neo4j: Chaos values on relationships, showing evolution

5. **Theme and Entity Co-occurrence**
   - In PostgreSQL: Complex self-joins and subqueries
   - In Neo4j: Pattern matching - `(e1)<-[:MENTIONS]-(s)-[:MENTIONS]->(e2)`

## Core Graph Patterns

### Pattern 1: Story Timeline
```
(Story)-[:HAS_CHAPTER {chaos}]->(Chapter)
                                   ↓
                             [:FEATURES]
                                   ↓
                              (Entity)
```

Each chapter relationship carries the chaos parameters at that point in the story. This creates a temporal graph where we can see how absurdity, surrealism, ridiculousness, and insanity evolve.

### Pattern 2: Universe Web
```
(Story)-[:SHARES_UNIVERSE_WITH {weight}]->(Story)
   ↓                                          ↓
[:MENTIONS]                             [:MENTIONS]
   ↓                                          ↓
(Entity) ←────── [:RELATED_TO] ──────────→ (Entity)
```

Stories connect through shared entities and themes. The weight on the relationship indicates connection strength. This creates organic universe clusters without manual categorization.

### Pattern 3: Tom's Multiverse
```
(Story₁)-[:FEATURES_TOM {variant: "Tom"}]→(Tom:Canonical)
(Story₂)-[:FEATURES_TOM {variant: "Tommy"}]→(Tom:Canonical)
(Story₃)-[:FEATURES_TOM {variant: "Thomas"}]→(Tom:Canonical)
```

Every story has its own Tom variant, but they all connect to the canonical Tom node. This lets us:
- Track how Tom is characterized differently across stories
- Find patterns in how Tom appears (role, characterization)
- Ensure Tom truly anchors the entire narrative universe

### Pattern 4: Quality Assessment
```
(Story)-[:WAS_EVALUATED]->(Evaluation)-[:EVALUATED_AFTER]->(Chapter)
```

Evaluations are decision points. They reference both the story and the specific chapter they were performed after, creating a historical record of quality over time.

## Data Model vs Relational Model

| Concept | PostgreSQL | Neo4j |
|---------|-----------|-------|
| **Story** | Row in `stories` table | Node with `:Story` label |
| **Chapter** | Row in `chapters` table | Node with `:Chapter` label |
| **Story→Chapter** | `story_id` foreign key | `-[:HAS_CHAPTER]->` relationship |
| **Chaos Evolution** | Columns in `chapters` | Properties on `[:HAS_CHAPTER]` |
| **Entity Mentions** | Junction table | `-[:MENTIONS]->` with properties |
| **Universe Links** | `story_universe_links` table | `-[:SHARES_UNIVERSE_WITH]->` |
| **Tom** | Mentioned in text | Canonical `(:Tom)` node |
| **Themes** | `story_themes` table | Nodes + `-[:EXPLORES]->` |

## Query Performance Characteristics

### Fast in Neo4j
- **Traversals**: Following relationships (story → chapters → entities)
- **Pattern matching**: Finding stories with shared entities
- **Network analysis**: Universe clusters, entity co-occurrence
- **Recursive queries**: Stories connected through multiple hops

### Fast in PostgreSQL
- **Full table scans**: COUNT(*) on large tables
- **Aggregations on single table**: AVG(chaos_value)
- **Exact ID lookups**: WHERE id = ?

### Design Decision
Since this application is **relationship-heavy** (universe connections, entity tracking, Tom variants), Neo4j provides better performance and more intuitive queries.

## Schema Files

- **`schema.cypher`** - Node types, relationships, constraints, indexes
- **`queries.cypher`** - Common query patterns for the application
- **`README.md`** - This file

## Indexes & Constraints

### Uniqueness Constraints
Ensure no duplicate nodes:
- `story.id`, `chapter.id`, `entity.id`, `theme.id`, `universe.id`, `evaluation.id`
- `entity.canonicalName` (normalized entity names)

### Property Indexes
Speed up common filters:
- `story.status`, `story.createdAt` (for active story queries)
- `chapter.chapterNumber` (for ordering)
- `entity.name`, `entity.entityType` (for entity searches)
- `theme.name` (for theme searches)

### Full-Text Indexes
Enable fuzzy search:
- `entity_search_idx` on `entity.name` and `entity.description`
- `story_search_idx` on `story.title` and `story.premise`
- `chapter_search_idx` on `chapter.content`

## Key Queries Explained

### 1. Get Story with Full Context
```cypher
MATCH (s:Story {id: $storyId})
OPTIONAL MATCH (s)-[hc:HAS_CHAPTER]->(c:Chapter)
OPTIONAL MATCH (s)-[:WAS_EVALUATED]->(ev:Evaluation)
OPTIONAL MATCH (s)-[m:MENTIONS]->(e:Entity)
RETURN s,
       COLLECT(DISTINCT {chapter: c, chaos: properties(hc)}) as chapters,
       COLLECT(DISTINCT ev) as evaluations,
       COLLECT(DISTINCT {entity: e, mentions: m}) as entities
ORDER BY c.chapterNumber;
```

**Why it's elegant in Neo4j:**
- Single query traverses multiple relationship types
- `properties(hc)` extracts chaos evolution from the relationship
- No JOINs needed - just follow the graph

### 2. Find Universe Connections
```cypher
MATCH (s1:Story)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(s2:Story)
WHERE s1.id < s2.id
WITH s1, s2,
     COLLECT(DISTINCT e.name) as sharedEntities,
     COUNT(DISTINCT e) as entityCount
WHERE entityCount >= $minSharedEntities
MATCH (s1)-[:EXPLORES]->(t:Theme)<-[:EXPLORES]-(s2)
WITH s1, s2, sharedEntities,
     COLLECT(DISTINCT t.name) as sharedThemes,
     COUNT(DISTINCT t) as themeCount
WITH s1, s2, sharedEntities, sharedThemes,
     (entityCount * 0.6 + themeCount * 0.4) / 10.0 as weight
MERGE (s1)-[r:SHARES_UNIVERSE_WITH]->(s2)
SET r.weight = weight,
    r.sharedEntities = sharedEntities,
    r.sharedThemes = sharedThemes
RETURN s1, s2, r;
```

**What this does:**
- Finds stories that mention the same entities
- Also checks if they share themes
- Creates weighted `SHARES_UNIVERSE_WITH` relationships
- This runs periodically to build the universe graph

### 3. Tom's Multiverse
```cypher
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
WHERE s.status = "completed"
RETURN s.title, f.variantName, f.role, f.characterization
ORDER BY s.createdAt DESC;
```

**Why it matters:**
- Tom is the canonical anchor across all stories
- This query reveals how Tom is characterized differently
- Can analyze patterns (is Tom always an engineer? what variations exist?)

### 4. Entity Co-occurrence Network
```cypher
MATCH (e1:Entity)<-[:MENTIONS]-(s:Story)-[:MENTIONS]->(e2:Entity)
WHERE id(e1) < id(e2)
WITH e1, e2, COUNT(DISTINCT s) as coappearances, COLLECT(s.id) as storyIds
WHERE coappearances >= 2
MERGE (e1)-[r:RELATED_TO]->(e2)
SET r.cooccurrenceCount = coappearances,
    r.stories = storyIds,
    r.strength = coappearances / 10.0
RETURN e1, e2, r;
```

**What this builds:**
- Creates relationships between entities that appear together
- Strength based on how many stories they share
- Enables "related entities" suggestions
- Can visualize entity networks

## Migration from PostgreSQL

To migrate existing data:

1. **Export stories, chapters, evaluations** from PostgreSQL
2. **Run entity extraction** on chapter content
3. **Create nodes** in Neo4j using the exported data
4. **Create relationships** based on foreign keys and extracted entities
5. **Calculate universe connections** using the shared entity/theme queries
6. **Initialize Tom canonical node** and link all stories

A migration script will be provided in `/scripts/migrate-to-neo4j.ts`.

## Accessing Neo4j

### Local Development
```bash
docker run \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:5.15
```

Visit http://localhost:7474 to use Neo4j Browser.

### Production (Neo4j Aura)
- Create a free instance at https://neo4j.com/cloud/aura/
- Get connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
- Set environment variables:
  ```
  NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=your-password
  ```

## Querying from TypeScript

```typescript
import neo4j from 'neo4j-driver';

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD)
);

async function getStory(storyId: string) {
  const session = driver.session();
  try {
    const result = await session.run(
      'MATCH (s:Story {id: $storyId}) RETURN s',
      { storyId }
    );
    return result.records[0].get('s').properties;
  } finally {
    await session.close();
  }
}
```

## Visualization

Neo4j Browser provides built-in graph visualization. Useful for:
- Seeing universe connections
- Exploring entity networks
- Debugging relationship weights
- Presenting the story universe to users

## Performance Tips

1. **Always use parameters** (`$paramName`) to prevent query caching issues
2. **Create indexes** on properties you filter by
3. **Use `LIMIT`** for large result sets
4. **Avoid Cartesian products** - always connect patterns with relationships
5. **Use `EXPLAIN`** and `PROFILE`** to analyze query performance
6. **Batch writes** using `UNWIND` for multiple node creation

## Graph Advantages for This Project

| Feature | Graph Advantage |
|---------|----------------|
| **Universe clustering** | Natural community detection algorithms |
| **Entity tracking** | Traverse entity→stories instantly |
| **Tom variants** | Single canonical node, multiple characterizations |
| **Story similarity** | Graph algorithms (similarity, PageRank) |
| **Timeline exploration** | Follow chapter relationships in order |
| **Theme networks** | See which themes connect stories |
| **Chaos evolution** | Properties on relationships show temporal change |

## Next Steps

1. ✅ Schema designed
2. ⏳ Set up Neo4j driver in `/api/lib/neo4j.ts`
3. ⏳ Implement story CRUD operations
4. ⏳ Build entity extraction pipeline
5. ⏳ Create universe connection analyzer
6. ⏳ Migrate existing data from PostgreSQL

---

**Graph thinking:** Don't ask "what table does this go in?" Ask "what node and relationships does this create?"
