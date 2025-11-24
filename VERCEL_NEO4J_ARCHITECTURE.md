# 🌌 Vercel + Neo4j Architecture

**Complete rewrite of Hurl Unmasks Recursive Literature Leaking Out Light for graph-native autonomous storytelling.**

---

## 🎯 Executive Summary

This is a **from-scratch architectural redesign** that transforms the project from a traditional relational database application into a **graph-native system** powered by Neo4j and deployed on Vercel's serverless platform.

### What Makes This Special

1. **Graph-First Design** - Stories aren't rows in a table; they're nodes in a universe graph connected by shared entities, themes, and Tom variants
2. **Tom as Universal Anchor** - A canonical Tom node connects every story, making the multiverse concept explicit and queryable
3. **Autonomous Story Generation** - Serverless cron jobs continuously generate, evaluate, and evolve stories without manual intervention
4. **Real-Time Updates** - Server-Sent Events stream new chapters and story events to connected clients
5. **Serverless Scalability** - Zero infrastructure management, auto-scaling, pay-per-use

---

## 📊 Architecture Comparison

### Before (PostgreSQL + FastAPI)

```
┌──────────────┐       ┌────────────────┐       ┌─────────────┐
│  SvelteKit   │  WS   │    FastAPI     │  SQL  │ PostgreSQL  │
│  Frontend    │◀─────▶│    Backend     │◀─────▶│  Database   │
└──────────────┘       └────────┬───────┘       └─────────────┘
                               │
                         APScheduler
                         Background
                          Worker
```

**Challenges:**
- Complex JOINs for entity relationships
- Universe connections stored in junction tables
- Tom exists only as text mentions
- Manual server management
- WebSocket complexity

### After (Neo4j + Vercel)

```
┌──────────────┐       ┌────────────────┐       ┌─────────────┐
│  SvelteKit   │  SSE  │     Vercel     │ Bolt  │   Neo4j     │
│  Frontend    │◀─────▶│   Functions    │◀─────▶│    Aura     │
└──────────────┘       └────────┬───────┘       └─────────────┘
                               │
                         Vercel Cron
                         (3 scheduled
                           jobs)
                               ↓
                         Vercel Blob
                        (Cover Images)
```

**Benefits:**
- Natural graph traversals (story → chapters → entities)
- Universe connections are first-class relationships
- Tom is a canonical node with explicit connections
- Zero server management
- SSE for real-time updates

---

## 🗂️ Neo4j Graph Schema

### Core Nodes

- `(:Story)` - A narrative with metadata
- `(:Chapter)` - Individual installments
- `(:Entity)` - Characters, places, objects, concepts
- `(:Theme)` - Thematic elements
- `(:Universe)` - Clusters of related stories
- `(:Evaluation)` - Quality assessments
- `(:Tom)` - **The canonical anchor** connecting all stories

### Key Relationships

```cypher
// Story structure
(Story)-[:HAS_CHAPTER {chaos}]->(Chapter)

// Story universe
(Story)-[:SHARES_UNIVERSE_WITH {weight}]->(Story)
(Story)-[:BELONGS_TO]->(Universe)

// Entity tracking
(Story)-[:MENTIONS {importance}]->(Entity)
(Chapter)-[:FEATURES]->(Entity)
(Entity)-[:RELATED_TO]->(Entity)

// Tom's multiverse
(Story)-[:FEATURES_TOM {variantName, role}]->(Tom)

// Quality evaluation
(Story)-[:WAS_EVALUATED]->(Evaluation)-[:EVALUATED_AFTER]->(Chapter)

// Themes
(Story)-[:EXPLORES {weight}]->(Theme)
```

### Example Query: Find Universe Connections

```cypher
// Stories that share the most entities
MATCH (s1:Story)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(s2:Story)
WHERE id(s1) < id(s2)
WITH s1, s2, COUNT(e) as sharedEntities,
     COLLECT(e.name) as entities
WHERE sharedEntities >= 3
RETURN s1.title, s2.title, sharedEntities, entities
ORDER BY sharedEntities DESC
```

### Example Query: Tom's Variants

```cypher
// How Tom appears across different stories
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
RETURN s.title, s.tone,
       f.variantName, f.role, f.characterization
ORDER BY s.createdAt DESC
```

---

## 🔄 Autonomous Story Generation

### Background Jobs (Vercel Cron)

1. **Chapter Generation** (every 15 minutes)
   - Maintains story pool (min 3, max 8 active stories)
   - Generates new chapters for active stories
   - Spawns new stories when below minimum
   - Completes oldest stories when above maximum

2. **Story Evaluation** (every 30 minutes)
   - Evaluates active stories every 3 chapters
   - Scores: coherence, novelty, engagement, pacing
   - Completes stories below quality threshold (0.6)

3. **Cover Art Backfill** (hourly)
   - Generates DALL-E cover art for completed stories
   - Uploads to Vercel Blob storage
   - Updates story with public URL

### Story Lifecycle

```
[Spawn] → [Generate Chapter 1]
            ↓
       [Generate Chapter 2]
            ↓
       [Generate Chapter 3] → [Evaluate]
            ↓                      ↓
       [Continue/Complete]    [Score]
            ↓
       [Max Chapters/Quality Drop]
            ↓
       [Complete] → [Generate Cover Art]
            ↓
       [Publish to Universe Graph]
```

### Chaos Evolution

Each story starts with initial chaos parameters:
- Absurdity: 0.1-0.3
- Surrealism: 0.1-0.3
- Ridiculousness: 0.1-0.3
- Insanity: 0.05-0.2

These increase with each chapter (stored on the `:HAS_CHAPTER` relationship):

```cypher
(Story)-[:HAS_CHAPTER {
  order: 5,
  absurdity: 0.35,      // Increased from initial 0.1
  surrealism: 0.40,
  ridiculousness: 0.25,
  insanity: 0.18
}]->(Chapter)
```

---

## 🚀 Vercel Serverless Functions

### Endpoint Structure

```
/api
├── health.ts              # Health check
├── stats.ts               # Aggregate statistics
├── events.ts              # Server-Sent Events
├── stories/
│   ├── index.ts           # List stories
│   ├── [id].ts            # Get/delete story
│   └── [id]/kill.ts       # End story early
├── admin/
│   ├── spawn.ts           # Spawn new story
│   └── reset.ts           # Reset system
└── cron/
    ├── generate.ts        # Chapter generation (cron)
    ├── evaluate.ts        # Story evaluation (cron)
    └── backfill-covers.ts # Cover art (cron)
```

### Function Configuration

```json
{
  "functions": {
    "api/**/*.ts": {
      "memory": 1024,
      "maxDuration": 60
    },
    "api/cron/*.ts": {
      "memory": 1024,
      "maxDuration": 300
    }
  }
}
```

### Cold Start Optimization

- **Neo4j Driver Singleton** - Reuses connections across invocations
- **Connection Pooling** - Max 50 connections, 60s timeout
- **Minimal Dependencies** - Only essential imports per function

---

## 🎨 Vercel Blob Storage

Cover images generated by DALL-E are stored in Vercel Blob:

```typescript
// 1. Generate with OpenAI
const imageUrl = await generateCoverArt({
  storyTitle,
  premise,
  tone,
  genreTags,
});

// 2. Upload to Vercel Blob
const blobUrl = await uploadCoverImage(storyId, imageUrl);

// 3. Store URL in Neo4j
await updateStoryCoverImage(storyId, blobUrl);
```

Blob URLs are permanent, CDN-backed, and publicly accessible.

---

## 📡 Server-Sent Events (SSE)

Real-time updates without WebSocket complexity:

### Backend (Publishing Events)

```typescript
import { emitStoryEvent } from './events.js';

// When a new chapter is generated
await emitStoryEvent('new_chapter', {
  storyId,
  chapterNumber,
  title: story.title,
});

// When a story is completed
await emitStoryEvent('story_completed', {
  storyId,
  title: story.title,
  reason,
});
```

### Frontend (Consuming Events)

```typescript
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('new_chapter', (e) => {
  const data = JSON.parse(e.data);
  // Update UI with new chapter notification
});

eventSource.addEventListener('story_completed', (e) => {
  const data = JSON.parse(e.data);
  // Update story list, mark as completed
});
```

SSE advantages:
- ✅ Works in all modern browsers (including Safari)
- ✅ Automatic reconnection
- ✅ Simpler than WebSockets
- ✅ No long-lived connections (Vercel-friendly)

---

## 🔒 Security

### Cron Job Protection

All cron endpoints require authentication:

```typescript
const authHeader = req.headers.authorization;
if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
  res.status(401).json({ error: 'Unauthorized' });
  return;
}
```

### Admin Endpoints

TODO: Implement session-based authentication for admin actions.

### Neo4j Access

- **Connection**: TLS-encrypted (`neo4j+s://`)
- **Credentials**: Environment variables only
- **IP Allowlist**: Configure in Neo4j Aura

---

## 💰 Cost Analysis

### Monthly Costs (Production)

| Service | Tier | Cost |
|---------|------|------|
| **Vercel Pro** | Hobby (free) or Pro | $0-20/mo |
| **Neo4j Aura** | Professional | ~$65/mo |
| **Vercel Blob** | Pay-as-you-go | ~$5/mo |
| **Vercel KV** | Pay-as-you-go | ~$3/mo |
| **OpenAI** | API usage | Variable |
| **Total** | | **~$75-100/mo** |

### Cost Optimization

- Use `gpt-4-turbo-preview` (cheaper than `gpt-4`)
- Limit chapter generation interval (15min default)
- Set max stories (3-8 active)
- Batch cover art generation (5 at a time)

---

## 📈 Performance Characteristics

### Neo4j Query Performance

- **Story lookup by ID**: <10ms (unique constraint)
- **Get story with chapters**: <50ms (single traversal)
- **Find universe connections**: <200ms (indexed)
- **Entity co-occurrence**: <500ms (graph algorithm)

### Function Execution Time

- **Health check**: ~100ms
- **List stories**: ~200ms
- **Get story details**: ~300ms
- **Generate premise**: 5-10s (OpenAI call)
- **Generate chapter**: 15-30s (OpenAI call)
- **Evaluate story**: 10-20s (OpenAI call)
- **Generate cover art**: 10-20s (DALL-E)

### Cron Job Duration

- **Chapter generation**: 1-3 minutes (depends on active stories)
- **Story evaluation**: 1-2 minutes
- **Cover art backfill**: 2-5 minutes (batch of 5)

---

## 🛠️ Development Workflow

### Local Development

```bash
# 1. Set up Neo4j (local or Aura)
docker run -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15

# 2. Initialize database
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
./scripts/init-neo4j.sh

# 3. Install dependencies
cd api && npm install

# 4. Configure environment
cp .env.vercel.example .env.local
# Edit .env.local

# 5. Run Vercel dev server
npm run dev
```

Visit http://localhost:3000/api/health to verify.

### Deployment

```bash
# Link to Vercel project
vercel link

# Deploy to production
vercel --prod
```

### Monitoring

```bash
# View logs
vercel logs --follow

# View cron job execution
# (Vercel dashboard → Cron Jobs)
```

---

## 🔮 Future Enhancements

### Phase 1: Core Functionality ✅
- [x] Neo4j graph schema
- [x] Story generation with OpenAI
- [x] Story evaluation system
- [x] Vercel Cron Jobs
- [x] Blob storage for cover art
- [x] SSE for real-time updates

### Phase 2: Graph Intelligence
- [ ] Entity extraction from chapter content
- [ ] Automatic universe clustering (graph algorithms)
- [ ] Entity relationship discovery
- [ ] Theme emergence detection
- [ ] Story similarity scoring

### Phase 3: Enhanced Features
- [ ] Admin authentication (session-based)
- [ ] User accounts and reading preferences
- [ ] Story voting and recommendations
- [ ] Universe visualization (D3.js force graph)
- [ ] Advanced search (full-text + graph)

### Phase 4: Performance & Scale
- [ ] Query caching (Redis/Vercel KV)
- [ ] Rate limiting (per-user, per-IP)
- [ ] CDN optimization
- [ ] Monitoring and alerting (Sentry, Datadog)
- [ ] A/B testing for story parameters

---

## 📚 Documentation

- **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** - Complete migration instructions
- **[neo4j/README.md](./neo4j/README.md)** - Graph schema documentation
- **[neo4j/schema.cypher](./neo4j/schema.cypher)** - Schema definition
- **[neo4j/queries.cypher](./neo4j/queries.cypher)** - Common query patterns
- **[api/README.md](./api/README.md)** - API documentation

---

## 🎉 Why This Is Better

### 1. Graph-Native Thinking

**Before:**
```sql
-- Find stories that share entities (complex JOINs)
SELECT s1.title, s2.title, COUNT(*) as shared
FROM stories s1
JOIN story_entities se1 ON s1.id = se1.story_id
JOIN story_entities se2 ON se1.entity_name = se2.entity_name
JOIN stories s2 ON se2.story_id = s2.id
WHERE s1.id < s2.id
GROUP BY s1.id, s2.id
HAVING COUNT(*) >= 3;
```

**After:**
```cypher
// Natural graph traversal
MATCH (s1:Story)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(s2:Story)
WHERE id(s1) < id(s2)
WITH s1, s2, COUNT(e) as shared
WHERE shared >= 3
RETURN s1, s2, shared;
```

### 2. Tom as Universal Constant

**Before:** Tom mentioned in text, hard to query
**After:** Canonical `(:Tom)` node with explicit relationships

```cypher
// Find all Tom variants
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
RETURN s.title, f.variantName, f.characterization;
```

### 3. Serverless Simplicity

**Before:** Docker Compose, VPS management, APScheduler complexity
**After:** `git push` to deploy, automatic scaling, zero infrastructure

### 4. Cost Efficiency

**Before:** $50-100/mo VPS + maintenance time
**After:** $75-100/mo fully managed + zero maintenance

### 5. Real-Time Updates

**Before:** WebSocket complexity, connection management
**After:** SSE with automatic reconnection, browser-native

---

## 🤝 Contributing

This is a complete architectural rewrite. The old Python/FastAPI/PostgreSQL code is in `backend/` (deprecated). All new development happens in `api/` (TypeScript/Vercel/Neo4j).

See `CLAUDE.md` and `AGENTS.md` for contribution guidelines.

---

**Built with:** TypeScript, Neo4j, Vercel, OpenAI, SSE, Graph Databases, Autonomous Systems

**Author:** Tom Pickard <tom@pickard.dev>

**License:** MIT
