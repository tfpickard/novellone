# 🚀 Migration to Vercel + Neo4j

This guide covers the complete migration from the FastAPI + PostgreSQL stack to Vercel + Neo4j.

---

## 📋 Overview

### What Changed

| Component | Before | After |
|-----------|--------|-------|
| **Backend** | FastAPI (Python) | Vercel Serverless Functions (TypeScript) |
| **Database** | PostgreSQL + SQLAlchemy | Neo4j Aura (Graph Database) |
| **Background Worker** | APScheduler | Vercel Cron Jobs |
| **Image Storage** | File system / URL storage | Vercel Blob Storage |
| **Real-time Updates** | WebSocket | Server-Sent Events (SSE) |
| **Frontend** | SvelteKit | SvelteKit (minimal changes) |
| **Deployment** | Docker Compose / VPS | Vercel (serverless) |

### Why This Is Better

1. **Graph-Native Data Model** - Stories, entities, and universe connections are natural graph relationships
2. **Serverless Scalability** - No server management, auto-scaling
3. **Cost Efficiency** - Pay only for what you use (~$85/mo vs VPS costs)
4. **Simplified Deployment** - `git push` to deploy, no Docker management
5. **Tom as Universal Anchor** - Canonical Tom node connects all stories

---

## 🗄️ Part 1: Database Migration

### Step 1: Set Up Neo4j Aura

1. Go to https://neo4j.com/cloud/aura/
2. Create a free instance (or paid for production)
3. Save your connection details:
   ```
   URI: neo4j+s://xxxxx.databases.neo4j.io
   Username: neo4j
   Password: [your-password]
   ```

### Step 2: Initialize Schema

```bash
# From project root
cd neo4j

# Connect to Neo4j Browser (http://localhost:7474 or Aura Console)
# Run the initialization script
cat init.cypher | cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD
```

This creates:
- Constraints (unique IDs)
- Indexes (for performance)
- Full-text search indexes
- Tom canonical node

### Step 3: Migrate Data (Optional)

If you have existing stories in PostgreSQL:

```bash
# Export from PostgreSQL
pg_dump -U storyuser -d stories -t stories -t chapters -t story_evaluations > backup.sql

# Run migration script (creates Neo4j nodes from PostgreSQL data)
npm run migrate-data
```

> **Note:** Migration script needs to be created based on your data volume and structure.

---

## 🔧 Part 2: Local Development Setup

### Step 1: Install Dependencies

```bash
# API dependencies
cd api
npm install

# Frontend dependencies (if changed)
cd ../frontend
npm install
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.vercel.example .env.local

# Edit .env.local with your credentials
```

Required variables:
```bash
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-...
CRON_SECRET=$(openssl rand -base64 32)
```

### Step 3: Run Locally

```bash
# Start Vercel dev server (runs serverless functions locally)
cd api
npm run dev

# In another terminal, start frontend
cd frontend
npm run dev
```

Visit:
- Frontend: http://localhost:3000
- API: http://localhost:3000/api/health

---

## ☁️ Part 3: Deploy to Vercel

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Link Project

```bash
# From project root
vercel link
```

Follow prompts to create a new Vercel project.

### Step 3: Add Vercel Integrations

1. **Neo4j** - Already external, just add env vars
2. **Vercel Blob** - Add via Vercel dashboard (Storage tab)
3. **Vercel KV** - Add via Vercel dashboard (Storage tab, create Redis store)

### Step 4: Set Environment Variables

In Vercel dashboard (Settings → Environment Variables):

```bash
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-...
CRON_SECRET=your-random-secret
```

Vercel automatically sets:
- `BLOB_READ_WRITE_TOKEN`
- `KV_URL`, `KV_REST_API_URL`, `KV_REST_API_TOKEN`

### Step 5: Deploy

```bash
# Deploy to production
vercel --prod
```

Deployment includes:
- API functions in `/api`
- Cron jobs configured in `vercel.json`
- Frontend (if using Vercel for frontend)

### Step 6: Verify Cron Jobs

In Vercel dashboard (Settings → Cron Jobs):

You should see:
- `/api/cron/generate` - Every 15 minutes
- `/api/cron/evaluate` - Every 30 minutes
- `/api/cron/backfill-covers` - Every hour

---

## 🧪 Part 4: Testing

### Test Health Endpoint

```bash
curl https://your-project.vercel.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "hurl-unmasks-recursive-literature-leaking-out-light",
  "database": {
    "connected": true,
    "serverInfo": { ... }
  }
}
```

### Test Story Spawning

```bash
curl -X POST https://your-project.vercel.app/api/admin/spawn
```

This should:
1. Call OpenAI to generate a premise
2. Create a Story node in Neo4j
3. Link it to Tom canonical node
4. Return the new story

### Test SSE (Real-time Updates)

```bash
curl -N https://your-project.vercel.app/api/events
```

You should see:
```
data: {"type":"connected","timestamp":1234567890}
```

### Monitor Cron Jobs

Check Vercel logs to see cron job execution:

```bash
vercel logs --follow
```

Look for:
```
🔄 Starting story generation cron job...
✍️  Generating chapters...
✅ Cron job completed in 3452ms
```

---

## 🎨 Part 5: Frontend Updates

### Update API Client

The frontend needs to point to the new API:

**File: `frontend/src/lib/api.ts`**

```typescript
const API_BASE_URL = import.meta.env.VITE_PUBLIC_API_URL ||
                      'https://your-project.vercel.app/api';

// SSE connection
const SSE_URL = import.meta.env.VITE_PUBLIC_SSE_URL ||
                'https://your-project.vercel.app/api/events';
```

### Replace WebSocket with SSE

**File: `frontend/src/lib/sse.ts`** (new file)

```typescript
export function createSSEConnection(onEvent: (event: any) => void) {
  const eventSource = new EventSource(SSE_URL);

  eventSource.addEventListener('new_chapter', (e) => {
    onEvent(JSON.parse(e.data));
  });

  eventSource.addEventListener('story_completed', (e) => {
    onEvent(JSON.parse(e.data));
  });

  // ... other event types

  return () => eventSource.close();
}
```

### Update Environment Variables

```bash
# frontend/.env
VITE_PUBLIC_API_URL=https://your-project.vercel.app/api
VITE_PUBLIC_SSE_URL=https://your-project.vercel.app/api/events
```

---

## 📊 Part 6: Monitoring & Maintenance

### View Neo4j Data

Use Neo4j Browser (Aura Console) to run queries:

```cypher
// See all stories
MATCH (s:Story) RETURN s LIMIT 25;

// See Tom's connections
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
RETURN s.title, f.variantName, f.role;

// Visualize universe connections
MATCH (s1:Story)-[r:SHARES_UNIVERSE_WITH]->(s2:Story)
WHERE r.weight > 0.5
RETURN s1, r, s2;
```

### Monitor Vercel Functions

- **Logs**: Vercel dashboard → Logs
- **Metrics**: Function invocations, duration, errors
- **Cron execution**: Vercel dashboard → Cron Jobs

### Cost Monitoring

- **Vercel**: Dashboard → Usage
- **Neo4j**: Aura Console → Metrics
- **OpenAI**: OpenAI Dashboard → Usage

Expected monthly costs:
- Vercel Pro: $20/mo
- Neo4j Aura: $65/mo (production tier)
- Vercel Blob: ~$5/mo (depends on usage)
- OpenAI: Variable (depends on story generation volume)

---

## 🚨 Troubleshooting

### "Neo4j connection failed"

- Check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in env vars
- Verify Neo4j Aura instance is running
- Check IP allowlist in Neo4j Aura (allow Vercel IPs)

### "Cron jobs not running"

- Verify `CRON_SECRET` is set in Vercel env vars
- Check cron job configuration in `vercel.json`
- View logs in Vercel dashboard

### "Cover images not uploading"

- Verify Vercel Blob is added to project
- Check `BLOB_READ_WRITE_TOKEN` is set (should be automatic)
- Check OpenAI DALL-E API access

### "SSE not working"

- SSE requires modern browsers (works in Safari 13+, Chrome, Firefox)
- Check that `/api/events` endpoint returns `text/event-stream`
- Verify Vercel KV is added to project

---

## 🎯 Next Steps

1. **Authentication** - Add proper admin authentication for protected endpoints
2. **Entity Extraction** - Implement full entity extraction and graph linking
3. **Universe Analysis** - Build universe clustering and graph visualization
4. **Performance Optimization** - Add caching, optimize Neo4j queries
5. **Monitoring** - Set up Sentry or Datadog for error tracking
6. **Rate Limiting** - Add rate limiting to API endpoints

---

## 📚 Resources

- [Neo4j Graph Database](https://neo4j.com/docs/)
- [Neo4j Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Cron Jobs](https://vercel.com/docs/cron-jobs)
- [Vercel Blob Storage](https://vercel.com/docs/storage/vercel-blob)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

---

**Questions?** Check the Neo4j schema documentation in `/neo4j/README.md`.
