# 🚀 Deployment Checklist

Quick reference for deploying the Vercel + Neo4j architecture.

---

## ✅ Prerequisites

- [ ] Neo4j Aura account (https://neo4j.com/cloud/aura/)
- [ ] Vercel account (https://vercel.com)
- [ ] OpenAI API key with GPT-4 and DALL-E access
- [ ] Vercel CLI installed (`npm install -g vercel`)

---

## 📋 Step-by-Step Deployment

### 1. Set Up Neo4j Database

```bash
# 1.1. Create Neo4j Aura instance
# - Visit https://neo4j.com/cloud/aura/
# - Create free or professional instance
# - Save credentials

# 1.2. Initialize database
export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your-password

./scripts/init-neo4j.sh

# 1.3. Verify Tom canonical node exists
# Open Neo4j Browser and run:
# MATCH (tom:Tom {id: 'tom-canonical'}) RETURN tom;
```

### 2. Configure Vercel Project

```bash
# 2.1. Link to Vercel
cd /path/to/novellone
vercel link

# 2.2. Add Vercel integrations
# - Go to Vercel dashboard
# - Add "Vercel Blob" (Storage tab)
# - Add "Vercel KV" (Storage tab)

# 2.3. Set environment variables
vercel env add NEO4J_URI
# Paste: neo4j+s://xxxxx.databases.neo4j.io

vercel env add NEO4J_USER
# Paste: neo4j

vercel env add NEO4J_PASSWORD
# Paste: your-password

vercel env add OPENAI_API_KEY
# Paste: sk-...

vercel env add CRON_SECRET
# Generate with: openssl rand -base64 32
# Paste the generated secret
```

### 3. Deploy to Production

```bash
# 3.1. Deploy
vercel --prod

# 3.2. Note the deployment URL
# Example: https://novellone.vercel.app
```

### 4. Verify Deployment

```bash
# 4.1. Health check
curl https://your-project.vercel.app/api/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "hurl-unmasks-recursive-literature-leaking-out-light",
#   "database": {
#     "connected": true,
#     ...
#   }
# }

# 4.2. Spawn a test story
curl -X POST https://your-project.vercel.app/api/admin/spawn

# 4.3. Check stats
curl https://your-project.vercel.app/api/stats

# 4.4. Test SSE
curl -N https://your-project.vercel.app/api/events
```

### 5. Verify Cron Jobs

```bash
# 5.1. Check Vercel dashboard
# - Go to Settings → Cron Jobs
# - Verify 3 jobs are listed:
#   - /api/cron/generate (every 15 minutes)
#   - /api/cron/evaluate (every 30 minutes)
#   - /api/cron/backfill-covers (every hour)

# 5.2. View logs
vercel logs --follow

# Look for:
# 🔄 Starting story generation cron job...
# ✅ Cron job completed in 3452ms
```

### 6. Configure Neo4j Aura Access

```bash
# 6.1. Add Vercel IPs to allowlist
# - Go to Neo4j Aura Console
# - Navigate to your instance
# - Go to "Connect" tab
# - Add these IP ranges (Vercel):
#   - 0.0.0.0/0 (for testing, narrow down later)
#
# For production, get Vercel's IP ranges from:
# https://vercel.com/docs/concepts/deployments/regions
```

---

## 🧪 Testing the System

### Test 1: Story Generation

```bash
# Spawn a new story
curl -X POST https://your-project.vercel.app/api/admin/spawn

# Wait 15 minutes for first chapter
# Check stories
curl https://your-project.vercel.app/api/stories?status=active
```

### Test 2: Real-Time Updates

```bash
# Open SSE stream
curl -N https://your-project.vercel.app/api/events

# In another terminal, spawn a story
curl -X POST https://your-project.vercel.app/api/admin/spawn

# You should see events in the SSE stream:
# event: new_story
# data: {"storyId":"...","title":"..."}
```

### Test 3: Neo4j Queries

```cypher
// Open Neo4j Browser and run:

// 1. Count stories
MATCH (s:Story) RETURN count(s);

// 2. See all Tom connections
MATCH (s:Story)-[f:FEATURES_TOM]->(tom:Tom)
RETURN s.title, f.variantName, f.role;

// 3. Visualize universe (after multiple stories)
MATCH (s1:Story)-[r:SHARES_UNIVERSE_WITH]->(s2:Story)
RETURN s1, r, s2;
```

---

## 🔧 Troubleshooting

### Issue: "Neo4j connection failed"

**Solution:**
1. Check environment variables in Vercel dashboard
2. Verify Neo4j Aura instance is running
3. Check IP allowlist in Neo4j Aura
4. Test connection locally:
   ```bash
   export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=your-password
   node -e "
     import('neo4j-driver').then(neo4j => {
       const driver = neo4j.driver(process.env.NEO4J_URI,
         neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD));
       driver.verifyConnectivity()
         .then(() => console.log('✓ Connected'))
         .catch(console.error);
     });
   "
   ```

### Issue: "Cron jobs not running"

**Solution:**
1. Check `CRON_SECRET` is set in Vercel env vars
2. Verify cron jobs are listed in Vercel dashboard
3. Check function logs: `vercel logs --follow`
4. Ensure functions don't exceed 300s timeout

### Issue: "Cover images not uploading"

**Solution:**
1. Verify Vercel Blob is added to project
2. Check `BLOB_READ_WRITE_TOKEN` is present (automatic)
3. Test DALL-E access:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

### Issue: "SSE not working"

**Solution:**
1. Check Vercel KV is added to project
2. Verify KV environment variables are set
3. Test locally:
   ```bash
   curl -N http://localhost:3000/api/events
   ```
4. Check browser console for errors

---

## 📊 Monitoring

### Vercel Dashboard

- **Functions**: View invocation count, duration, errors
- **Logs**: Real-time logs for all functions
- **Cron Jobs**: Execution history and status
- **Usage**: Bandwidth, function executions, storage

### Neo4j Aura Console

- **Metrics**: Query performance, storage usage
- **Queries**: Slow query log
- **Connections**: Active connections

### OpenAI Dashboard

- **Usage**: Token consumption by model
- **Costs**: API usage costs

---

## 💰 Cost Monitoring

Set up budget alerts:

1. **Vercel**: Settings → Usage → Set spending limit
2. **Neo4j**: Billing → Set budget alerts
3. **OpenAI**: Usage limits → Set soft/hard limits

Expected monthly costs: **$75-100**

---

## 🔄 Ongoing Maintenance

### Weekly

- [ ] Check error logs in Vercel
- [ ] Review Neo4j query performance
- [ ] Monitor OpenAI token usage
- [ ] Review story quality scores

### Monthly

- [ ] Backup Neo4j database (export to JSON)
- [ ] Review and optimize slow queries
- [ ] Check for Neo4j/Vercel updates
- [ ] Review cost optimization opportunities

### Quarterly

- [ ] Review system architecture
- [ ] Evaluate new OpenAI models
- [ ] Consider Neo4j schema optimizations
- [ ] Update dependencies (`npm update`)

---

## 🚨 Emergency Procedures

### System Reset

```bash
# WARNING: This deletes ALL stories!

curl -X POST https://your-project.vercel.app/api/admin/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "DELETE_ALL_STORIES"}'
```

### Rollback Deployment

```bash
# List deployments
vercel ls

# Rollback to previous
vercel rollback
```

### Database Backup

```bash
# Export all data from Neo4j
cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD \
  "CALL apoc.export.json.all('backup.json', {useTypes:true})"
```

---

## ✅ Post-Deployment

- [ ] Health check passes
- [ ] First story spawned successfully
- [ ] Chapter generated after 15 minutes
- [ ] SSE events streaming
- [ ] Cron jobs running
- [ ] Monitoring set up
- [ ] Budget alerts configured
- [ ] Documentation reviewed by team

---

## 📚 Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Project Architecture](./VERCEL_NEO4J_ARCHITECTURE.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
- [Neo4j Schema](./neo4j/README.md)

---

**Need help?** Check the migration guide or architecture documentation.
