# 🌌 API - Vercel Serverless Functions

TypeScript serverless functions for Hurl Unmasks Recursive Literature Leaking Out Light.

## Architecture

```
api/
├── lib/                    # Shared libraries
│   ├── neo4j.ts           # Neo4j driver & connection
│   ├── openai.ts          # OpenAI client & generation logic
│   ├── blob.ts            # Vercel Blob storage
│   ├── config.ts          # Runtime configuration
│   ├── types.ts           # TypeScript type definitions
│   ├── story-operations.ts # Story CRUD operations
│   └── story-worker.ts    # Story generation & evaluation logic
├── stories/                # Story endpoints
│   ├── index.ts           # GET /api/stories (list)
│   ├── [id].ts            # GET/DELETE /api/stories/:id
│   └── [id]/
│       └── kill.ts        # POST /api/stories/:id/kill
├── admin/                  # Admin endpoints
│   ├── spawn.ts           # POST /api/admin/spawn
│   └── reset.ts           # POST /api/admin/reset
├── cron/                   # Cron jobs
│   ├── generate.ts        # Chapter generation (every 15min)
│   ├── evaluate.ts        # Story evaluation (every 30min)
│   └── backfill-covers.ts # Cover art generation (hourly)
├── health.ts               # GET /api/health
├── stats.ts                # GET /api/stats
├── events.ts               # GET /api/events (SSE)
├── package.json
└── tsconfig.json
```

## Development

### Install Dependencies

```bash
npm install
```

### Environment Setup

```bash
cp ../.env.vercel.example .env.local

# Edit .env.local with your credentials
```

### Run Locally

```bash
npm run dev
```

This starts the Vercel dev server at http://localhost:3000.

### Type Check

```bash
npm run typecheck
```

## Endpoints

### Public Endpoints

- `GET /api/health` - Health check
- `GET /api/stories` - List stories (with pagination & filtering)
- `GET /api/stories/:id` - Get story details
- `GET /api/stats` - Aggregate statistics
- `GET /api/events` - Server-Sent Events stream

### Admin Endpoints

- `POST /api/admin/spawn` - Manually spawn a new story
- `POST /api/admin/reset` - Reset system (dangerous!)
- `POST /api/stories/:id/kill` - End a story early
- `DELETE /api/stories/:id` - Delete a story

### Cron Endpoints (protected)

- `POST /api/cron/generate` - Generate chapters (called by Vercel Cron)
- `POST /api/cron/evaluate` - Evaluate stories (called by Vercel Cron)
- `POST /api/cron/backfill-covers` - Generate cover art (called by Vercel Cron)

## Key Libraries

### Neo4j Driver (`lib/neo4j.ts`)

Singleton driver with connection pooling:

```typescript
import { executeRead, executeWrite } from './lib/neo4j.js';

// Read query
const result = await executeRead('MATCH (s:Story) RETURN s LIMIT 10');

// Write query
await executeWrite('CREATE (s:Story {id: $id, title: $title})', { id, title });
```

### OpenAI Client (`lib/openai.ts`)

```typescript
import { generatePremise, generateChapter, evaluateStory } from './lib/openai.js';

const premise = await generatePremise();
const chapter = await generateChapter({ storyTitle, premise, ... });
const evaluation = await evaluateStory({ storyTitle, chapters, ... });
```

### Story Operations (`lib/story-operations.ts`)

```typescript
import {
  createStory,
  getStory,
  getActiveStories,
  addChapter,
  createEvaluation,
} from './lib/story-operations.js';

const story = await createStory({ title, premise, ... });
const chapter = await addChapter({ storyId, content, ... });
```

### Story Worker (`lib/story-worker.ts`)

High-level worker logic:

```typescript
import {
  maintainStoryPool,
  generateChaptersForActiveStories,
  evaluateActiveStories,
} from './lib/story-worker.js';

// Called by cron jobs
await maintainStoryPool(); // Spawn/complete stories
await generateChaptersForActiveStories(); // Generate new chapters
await evaluateActiveStories(); // Evaluate quality
```

## Cron Jobs

Configured in `vercel.json`:

```json
{
  "crons": [
    { "path": "/api/cron/generate", "schedule": "*/15 * * * *" },
    { "path": "/api/cron/evaluate", "schedule": "*/30 * * * *" },
    { "path": "/api/cron/backfill-covers", "schedule": "0 * * * *" }
  ]
}
```

### Security

Cron endpoints verify `Authorization: Bearer $CRON_SECRET` header.

## Server-Sent Events

The `/api/events` endpoint streams real-time updates using SSE.

Event types:
- `new_story` - New story spawned
- `new_chapter` - New chapter generated
- `story_completed` - Story completed
- `story_evaluated` - Story evaluated
- `system_reset` - System reset

Client example:

```javascript
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('new_chapter', (e) => {
  const data = JSON.parse(e.data);
  console.log('New chapter:', data);
});
```

## Deployment

```bash
# Deploy to production
vercel --prod
```

Vercel automatically:
- Builds TypeScript functions
- Sets up cron jobs
- Provides environment variables (Blob, KV)

## Environment Variables

Required:
- `NEO4J_URI` - Neo4j connection URI
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `OPENAI_API_KEY` - OpenAI API key
- `CRON_SECRET` - Secret for cron job authentication

Automatic (provided by Vercel):
- `BLOB_READ_WRITE_TOKEN` - Vercel Blob token
- `KV_URL`, `KV_REST_API_*` - Vercel KV tokens

## Performance

- **Function Memory**: 1024 MB (standard), 1024 MB (cron)
- **Function Timeout**: 60s (standard), 300s (cron)
- **Cold Start**: ~500ms (with connection pooling)
- **Neo4j Queries**: <100ms (with indexes)
- **OpenAI Generation**: 5-30s (depends on model)

## Troubleshooting

### "Cannot connect to Neo4j"

Check environment variables:
```bash
vercel env ls
```

Verify Neo4j Aura is accessible:
```bash
curl -I $NEO4J_URI
```

### "Cron jobs not running"

View logs:
```bash
vercel logs --follow
```

Check cron job configuration in Vercel dashboard.

### "Type errors"

Run type check:
```bash
npm run typecheck
```

## Testing

```bash
# Test health endpoint
curl http://localhost:3000/api/health

# Test story spawning
curl -X POST http://localhost:3000/api/admin/spawn

# Test SSE
curl -N http://localhost:3000/api/events
```

## Resources

- [Vercel Functions Documentation](https://vercel.com/docs/functions)
- [Neo4j Driver Documentation](https://neo4j.com/docs/javascript-manual/current/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
