# CORS and API Connection Fixes

## Problem

The frontend was trying to access the backend directly at `http://hurl.lol:8000`, bypassing the Caddy reverse proxy. This caused CORS errors because:

1. Direct backend access isn't allowed (backend only binds to localhost)
2. Browsers block cross-origin requests without proper CORS headers
3. The SSL certificate is on Caddy, not the backend

## Solution

Updated the frontend to use **same-origin requests** - all API and WebSocket calls go through the same domain/port the frontend is served from.

### Files Changed

1. **`frontend/src/lib/api.ts`**
   - Changed from: `window.location.hostname:8000`
   - Changed to: `window.location.origin`
   - Result: Uses `https://hurl.lol` in production, `http://localhost:4000` in dev

2. **`frontend/src/lib/websocket.ts`**
   - Changed from: `${scheme}://${window.location.hostname}:8000/ws/stories`
   - Changed to: `${scheme}://${window.location.host}/ws/stories`
   - Result: Uses `wss://hurl.lol/ws/stories` in production

3. **`frontend/vite.config.ts`**
   - Added proxy configuration for development
   - Proxies `/api`, `/auth`, `/ws` to backend:8000
   - Allows development to work through localhost:4000

4. **`docker-compose.prod.yml`**
   - Removed explicit `VITE_PUBLIC_API_URL` and `VITE_PUBLIC_WS_URL`
   - Frontend now auto-detects using same-origin approach

## How It Works

### Production (with Caddy)
```
Browser → https://hurl.lol/api/login
         ↓
      Caddy (ports 80/443)
         ↓
      Backend (localhost:8000)
```

### Development (with Vite proxy)
```
Browser → http://localhost:4000/api/login
         ↓
      Vite Dev Server (port 4000)
         ↓
      Backend (backend:8000 via Docker)
```

## Deployment Steps

After pulling these changes on your VPS:

```bash
# SSH into VPS
ssh root@your-vps-ip

# Navigate to app directory
cd /opt/novellone

# Pull latest changes
sudo -u novellone git pull origin main

# Rebuild and restart
sudo -u novellone docker compose -f docker-compose.prod.yml down
sudo -u novellone docker compose -f docker-compose.prod.yml build frontend
sudo -u novellone docker compose -f docker-compose.prod.yml up -d

# Check logs
sudo -u novellone docker compose -f docker-compose.prod.yml logs -f frontend
```

## Testing

After deployment:

```bash
# Test health endpoint
curl https://hurl.lol/api/health

# Should return:
# {"status":"healthy","service":"hurl-unmasks-recursive-literature-leaking-out-love-backend"}
```

Then visit https://hurl.lol in your browser - login and API calls should work without CORS errors!

## Benefits

✅ No CORS issues - same origin for all requests
✅ Works in both development and production
✅ No need to manually set API URLs
✅ Proper SSL/TLS encryption throughout
✅ Simpler configuration
✅ WebSockets work automatically

## Environment Variables No Longer Needed

You can remove these from your deployment (they're now optional):
- `VITE_PUBLIC_API_URL` 
- `VITE_PUBLIC_WS_URL`

Keep this one for SvelteKit SSR:
- `ORIGIN=https://hurl.lol`

