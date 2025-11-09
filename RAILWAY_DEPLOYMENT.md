# Railway Deployment Guide

This guide walks you through deploying Hurl Unmasks Recursive Literature Leaking Out Love to Railway with full CI/CD automation from GitHub.

## Why Railway?

Railway is the recommended hosting platform for this project because:
- **Native Docker support** - works with existing Dockerfiles
- **Managed PostgreSQL** - included database with automatic backups
- **Built-in CI/CD** - auto-deploy on git push
- **WebSocket support** - handles real-time features
- **Simple pricing** - $5 free credit/month, pay-as-you-grow
- **Zero config** - automatically detects and deploys services

## Prerequisites

1. **GitHub Account** - Repository must be pushed to GitHub
2. **Railway Account** - Sign up at [railway.app](https://railway.app)
3. **OpenAI API Key** - Required for story generation

## Deployment Steps

### 1. Push Your Code to GitHub

Ensure your code is committed and pushed to a GitHub repository:

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Create a New Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub account
5. Select your `novellone` repository

### 3. Add PostgreSQL Database

Railway needs a database service first:

1. In your Railway project, click **"+ New"**
2. Select **"Database"**
3. Choose **"PostgreSQL"**
4. Railway will provision the database and auto-generate `DATABASE_URL`

### 4. Deploy Backend Service

1. In your Railway project, click **"+ New"**
2. Select **"GitHub Repo"**
3. Choose your repository
4. Railway will detect the `backend/Dockerfile` automatically
5. Click on the backend service to configure it

#### Backend Environment Variables

Click **"Variables"** tab and add these (use `env.railway.example` as reference):

**Required Variables:**
```
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_PREMISE_MODEL=gpt-4o-mini
OPENAI_EVAL_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS_CHAPTER=2000
OPENAI_MAX_TOKENS_PREMISE=1500
OPENAI_MAX_TOKENS_EVAL=800
OPENAI_TEMPERATURE_CHAPTER=1.0
OPENAI_TEMPERATURE_PREMISE=1.2
OPENAI_TEMPERATURE_EVAL=0.3

CHAPTER_INTERVAL_SECONDS=300
EVALUATION_INTERVAL_CHAPTERS=3
WORKER_TICK_INTERVAL=15

MIN_ACTIVE_STORIES=3
MAX_ACTIVE_STORIES=5
CONTEXT_WINDOW_CHAPTERS=5
MAX_CHAPTERS_PER_STORY=50
MIN_CHAPTERS_BEFORE_EVAL=3

QUALITY_SCORE_MIN=0.6
COHERENCE_WEIGHT=0.35
NOVELTY_WEIGHT=0.25
ENGAGEMENT_WEIGHT=0.25
PACING_WEIGHT=0.15

LOG_LEVEL=INFO
LOG_DIR=/app/logs
LOG_MAX_BYTES=5000000
LOG_BACKUP_COUNT=5
ENABLE_WEBSOCKET=true

ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here
SESSION_SECRET=generate-a-random-32-char-string-here
SESSION_TTL_SECONDS=604800
SESSION_COOKIE_NAME=novellone_session
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
```

**Railway Auto-Provides:**
- `DATABASE_URL` - Link the PostgreSQL service (click "Add Reference" → select your database)
- `PORT` - Railway automatically sets this

#### Backend Settings

1. Go to **"Settings"** tab
2. Set **Root Directory** to `backend`
3. Set **Start Command** to `sh railway-start.sh` (or leave empty, Docker CMD handles it)
4. Enable **"Watch Paths"** to trigger rebuilds on backend changes only

#### Generate Public Domain

1. Go to **"Settings"** tab
2. Click **"Generate Domain"** under "Networking"
3. Copy the URL (e.g., `https://backend-production-xxxx.up.railway.app`)
4. This is your `PUBLIC_API_URL`

### 5. Deploy Frontend Service

1. In your Railway project, click **"+ New"**
2. Select **"GitHub Repo"**
3. Choose the same repository
4. Create a new service (Railway allows multiple services from one repo)

#### Frontend Environment Variables

Click **"Variables"** tab and add:

```
VITE_PUBLIC_API_URL=https://your-backend-url.up.railway.app
VITE_PUBLIC_WS_URL=wss://your-backend-url.up.railway.app/ws/stories
ORIGIN=https://your-frontend-url.up.railway.app
```

**Replace:**
- `your-backend-url.up.railway.app` with your backend's Railway domain
- `your-frontend-url.up.railway.app` with your frontend's Railway domain (generate after setup)

**Railway Auto-Provides:**
- `PORT` - Railway automatically sets this

#### Frontend Settings

1. Go to **"Settings"** tab
2. Set **Root Directory** to `frontend`
3. Set **Start Command** to `node build` (or leave empty, Docker CMD handles it)
4. Enable **"Watch Paths"** to trigger rebuilds on frontend changes only

#### Generate Public Domain

1. Go to **"Settings"** tab
2. Click **"Generate Domain"**
3. Copy the URL and update the `ORIGIN` environment variable
4. **Important:** Go back to frontend variables and set `ORIGIN` to this URL

### 6. Link Services

Ensure the backend can find the database:

1. Click on your **backend service**
2. Go to **"Variables"** tab
3. Click **"Add Reference"**
4. Select your PostgreSQL database
5. Railway will automatically inject `DATABASE_URL`

### 7. Deploy and Monitor

Railway will automatically:
1. Build Docker images for both services
2. Run database migrations (via `railway-start.sh`)
3. Start both services
4. Provide health checks via `/api/health`

Monitor deployment:
- Click on each service to see build logs
- Check **"Deployments"** tab for status
- View **"Metrics"** for CPU/memory usage

### 8. Verify Deployment

1. Visit your frontend URL: `https://your-frontend-url.up.railway.app`
2. You should see the story index page
3. Go to `/login` and use your `ADMIN_USERNAME` and `ADMIN_PASSWORD`
4. Visit `/config` to adjust runtime settings
5. Stories should start generating automatically

### 9. Enable CI/CD (Auto-Deploy)

Railway automatically sets up GitHub webhooks:

1. Every push to `main` branch triggers redeployment
2. Railway detects which services changed
3. Only modified services are rebuilt
4. Zero-downtime deployments

To customize:
- Go to **"Settings"** → **"Service"**
- Set **"Deploy Trigger"** to specific branch
- Configure **"Watch Paths"** for smarter rebuilds

## Custom Domain (Optional)

To use your own domain:

1. Go to service **"Settings"** → **"Networking"**
2. Click **"Custom Domain"**
3. Add your domain (e.g., `stories.yourdomain.com`)
4. Update your DNS with Railway's CNAME record
5. Update environment variables (`ORIGIN`, `VITE_PUBLIC_API_URL`) accordingly

## Cost Management

### Free Tier Strategy

Railway provides **$5 free credit/month**:

- **PostgreSQL**: ~$5-7/month (may exceed free tier)
- **Backend**: ~$1-3/month (depends on generation frequency)
- **Frontend**: ~$0.50-1/month (mostly static)

**To stay within free tier:**

1. **Use external free database:**
   - [Neon](https://neon.tech) (free PostgreSQL with 3GB storage)
   - [Supabase](https://supabase.com) (free PostgreSQL with 500MB)
   - Update `DATABASE_URL` in Railway backend to point to external DB

2. **Reduce background worker frequency:**
   - Increase `CHAPTER_INTERVAL_SECONDS` to 600-900
   - Increase `WORKER_TICK_INTERVAL` to 30-60

3. **Limit active stories:**
   - Set `MIN_ACTIVE_STORIES=1` and `MAX_ACTIVE_STORIES=2`

### Monitoring Costs

1. Go to your Railway project dashboard
2. Click **"Usage"** to see current month's costs
3. Set up billing alerts in **"Settings"** → **"Billing"**

## Troubleshooting

### Backend Not Starting

**Check:**
1. Environment variables are set correctly
2. `DATABASE_URL` is linked from PostgreSQL service
3. OpenAI API key is valid
4. Build logs for errors: Click service → "Deployments" → latest deployment

**Common fixes:**
```bash
# Verify health endpoint
curl https://your-backend-url.up.railway.app/api/health

# Check if migrations ran
# Look for "Running Alembic migrations..." in deploy logs
```

### Frontend Can't Connect to Backend

**Check:**
1. `VITE_PUBLIC_API_URL` points to correct backend URL (with `https://`)
2. `VITE_PUBLIC_WS_URL` uses `wss://` (not `ws://`) for HTTPS
3. Backend CORS is allowing frontend origin
4. Backend service is running (check Deployments)

**Fix:**
- Rebuild frontend after updating environment variables
- Verify URLs don't have trailing slashes

### Database Connection Errors

**Check:**
1. PostgreSQL service is running
2. `DATABASE_URL` uses `postgresql+asyncpg://` scheme
3. Backend has database reference added

**Fix:**
```bash
# In Railway, click backend service
# Variables → Add Reference → Select PostgreSQL
# Redeploy
```

### WebSocket Not Working

**Check:**
1. `VITE_PUBLIC_WS_URL` uses `wss://` protocol
2. Backend `ENABLE_WEBSOCKET=true`
3. Railway allows WebSocket connections (it does by default)

**Fix:**
- Ensure WebSocket URL includes `/ws/stories` path
- Check browser console for connection errors

### Stories Not Generating

**Check:**
1. OpenAI API key is valid and has credits
2. Background worker is running (check backend logs)
3. Configuration values are valid (sum of weights = 1.0)

**Fix:**
```bash
# Trigger manual spawn via API
curl -X POST https://your-backend-url.up.railway.app/api/admin/spawn \
  -H "Cookie: your-session-cookie"
```

### Build Failures

**Common issues:**

1. **Docker context errors:**
   - Ensure `Root Directory` is set correctly in Railway settings
   - Backend: `backend`, Frontend: `frontend`

2. **Dependency installation fails:**
   - Check `requirements.txt` or `package.json` for invalid versions
   - Review build logs for specific errors

3. **Migration errors:**
   - Database might not be ready when migrations run
   - Railway handles this with retries, but check logs

## Rollback

If a deployment breaks:

1. Go to service → **"Deployments"**
2. Find the last working deployment
3. Click **"⋯"** menu → **"Redeploy"**
4. Railway will rollback to that version

## Monitoring and Logs

### View Logs

1. Click on a service
2. Go to **"Deployments"** tab
3. Click on active deployment
4. View real-time logs

### Set Up Alerts

Railway doesn't have built-in alerting, but you can:

1. Use the health check endpoint: `/api/health`
2. Set up external monitoring (e.g., UptimeRobot, Pingdom)
3. Monitor the `/api/stats` endpoint for story generation activity

## Next Steps

1. **Monitor your first deployment** - Watch stories generate
2. **Tune parameters** - Adjust via `/config` endpoint
3. **Set up custom domain** - Make it production-ready
4. **Add external database** - If staying within free tier
5. **Enable GitHub Actions** - Add tests before deployment (optional)

## Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Project Issues:** GitHub issues in your repository

## Security Checklist

Before going live:

- [ ] Change `ADMIN_PASSWORD` to a strong, unique password
- [ ] Generate a cryptographically random `SESSION_SECRET` (32+ chars)
- [ ] Verify `SESSION_COOKIE_SECURE=true` (Railway uses HTTPS)
- [ ] Keep `OPENAI_API_KEY` secret and never commit to git
- [ ] Review Railway access logs periodically
- [ ] Set up billing alerts to avoid unexpected charges
- [ ] Consider rate limiting for public endpoints (add nginx if needed)

---

Enjoy your autonomous storytelling platform! 🚀📚

