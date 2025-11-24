// ═══════════════════════════════════════════════════════════════════════════
// INITIALIZATION SCRIPT
// Run this to set up a fresh Neo4j database for the project
// ═══════════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────────
// 1. CREATE CONSTRAINTS
// ───────────────────────────────────────────────────────────────────────────

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

CREATE CONSTRAINT entity_canonical_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.canonicalName IS UNIQUE;

// ───────────────────────────────────────────────────────────────────────────
// 2. CREATE INDEXES
// ───────────────────────────────────────────────────────────────────────────

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

// ───────────────────────────────────────────────────────────────────────────
// 3. CREATE FULL-TEXT SEARCH INDEXES
// ───────────────────────────────────────────────────────────────────────────

CREATE FULLTEXT INDEX entity_search_idx IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

CREATE FULLTEXT INDEX story_search_idx IF NOT EXISTS
FOR (s:Story) ON EACH [s.title, s.premise];

CREATE FULLTEXT INDEX chapter_search_idx IF NOT EXISTS
FOR (c:Chapter) ON EACH [c.content];

// ───────────────────────────────────────────────────────────────────────────
// 4. INITIALIZE CANONICAL TOM NODE
// ───────────────────────────────────────────────────────────────────────────

MERGE (tom:Tom {id: "tom-canonical"})
SET tom.name = "Tom",
    tom.description = "The tinkering engineer who anchors every premise",
    tom.role = "canonical-character",
    tom.totalAppearances = 0,
    tom.createdAt = timestamp();

// ───────────────────────────────────────────────────────────────────────────
// 5. VERIFICATION
// ───────────────────────────────────────────────────────────────────────────

// Verify Tom exists
MATCH (tom:Tom {id: "tom-canonical"})
RETURN tom;

// Show all constraints
SHOW CONSTRAINTS;

// Show all indexes
SHOW INDEXES;
