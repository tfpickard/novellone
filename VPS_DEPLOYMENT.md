# VPS Deployment Guide - hurl.lol

Complete guide for deploying Eternal Stories on a VPS with nginx reverse proxy and SSL.

## Overview

This deployment uses:
- **VPS**: Your own Ubuntu/Debian server
- **Docker Compose**: Container orchestration (production config)
- **Nginx**: Reverse proxy and SSL termination
- **Let's Encrypt**: Free SSL certificates via certbot
- **Systemd**: Service management for auto-start
- **Domain**: https://hurl.lol

## Prerequisites

### 1. VPS Requirements

- **OS**: Ubuntu 22.04+ or Debian 11+ (recommended)
- **RAM**: Minimum 2GB, 4GB recommended
- **Disk**: 20GB+ available
- **CPU**: 2+ cores recommended
- **Network**: Public IP address with SSH access
- **Ports**: 80, 443, and 8000, 4000 available (backend and frontend)

### 2. Domain Setup

Before starting, configure your DNS:

1. Point `hurl.lol` A record to your VPS IP address
2. Point `www.hurl.lol` A record to your VPS IP address (optional)
3. Wait for DNS propagation (can take up to 48 hours, usually minutes)

Verify DNS with:
```bash
dig hurl.lol +short
# Should return your VPS IP
```

### 3. Required Credentials

Have these ready:
- OpenAI API key (with credits)
- Strong passwords for:
  - PostgreSQL database
  - Admin account
  - Session secret (generate with `openssl rand -hex 32`)

## Quick Deployment (Automated)

The automated script handles everything:

### On Your Local Machine

1. **Push code to your git repository:**
```bash
git add .
git commit -m "Prepare VPS deployment"
git push origin main
```

### On Your VPS

2. **SSH into your VPS:**
```bash
ssh root@your-vps-ip
```

3. **Download and run the deployment script:**
```bash
apt-get update && apt-get install -y git
git clone https://github.com/your-username/novellone.git /tmp/novellone-setup
cd /tmp/novellone-setup
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

The script will:
- Install all dependencies (Docker, nginx, certbot, etc.)
- Create application user and directories
- Clone your repository
- Configure environment variables (interactive)
- Build Docker images
- Set up nginx with SSL
- Configure firewall
- Start the application
- Enable auto-start on boot

**That's it!** Your app should be live at https://hurl.lol

## Manual Deployment (Step-by-Step)

If you prefer manual control:

### Step 1: Initial VPS Setup

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y \
    git \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    curl \
    ufw

# Start Docker
systemctl start docker
systemctl enable docker
```

### Step 2: Create Application User

```bash
# Create dedicated user
useradd -r -m -s /bin/bash novellone
usermod -aG docker novellone

# Create application directory
mkdir -p /opt/novellone
chown novellone:novellone /opt/novellone
```

### Step 3: Clone Repository

```bash
# Switch to app user
sudo -u novellone bash

# Clone your repository
cd /opt/novellone
git clone https://github.com/your-username/novellone.git .

# Exit back to root
exit
```

### Step 4: Configure Environment

```bash
cd /opt/novellone

# Copy environment template
cp env.production.example .env.production

# Edit with your values
nano .env.production
```

**Critical variables to set:**
- `DATABASE_URL` - Set a strong password
- `POSTGRES_PASSWORD` - Same password as above
- `OPENAI_API_KEY` - Your actual API key
- `ADMIN_PASSWORD` - Strong admin password
- `SESSION_SECRET` - Random 64-char hex string

Generate a secure session secret:
```bash
openssl rand -hex 32
```

### Step 5: Build Docker Images

```bash
cd /opt/novellone
sudo -u novellone docker compose -f docker-compose.prod.yml build
```

### Step 6: Configure Nginx

```bash
# Install nginx config
cp /opt/novellone/nginx/novellone.conf /etc/nginx/sites-available/novellone

# Create symlink
ln -s /etc/nginx/sites-available/novellone /etc/nginx/sites-enabled/

# Remove default site
rm /etc/nginx/sites-enabled/default

# Test configuration
nginx -t
```

### Step 7: Configure Firewall

```bash
# Enable firewall
ufw --force enable

# Allow SSH (important - don't lock yourself out!)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Check status
ufw status
```

### Step 8: Get SSL Certificate

```bash
# Start nginx (temporarily for ACME challenge)
systemctl restart nginx

# Get certificate
certbot --nginx -d hurl.lol -d www.hurl.lol

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended)

# Certificate will be automatically installed and nginx reloaded
```

### Step 9: Set Up Systemd Service

```bash
# Install systemd service
cp /opt/novellone/systemd/novellone.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable novellone

# Start service
systemctl start novellone

# Check status
systemctl status novellone
```

### Step 10: Verify Deployment

```bash
# Check service status
systemctl status novellone

# Check containers are running
docker ps

# Check logs
journalctl -u novellone -f

# Test the application
curl https://hurl.lol/api/health
# Should return: {"status":"healthy","service":"eternal-stories-backend"}

# Visit in browser
# https://hurl.lol
```

## Post-Deployment Setup

### 1. Configure Admin Access

1. Visit https://hurl.lol/login
2. Log in with your `ADMIN_USERNAME` and `ADMIN_PASSWORD`
3. Go to https://hurl.lol/config to adjust settings

### 2. Set Up Automated Backups

```bash
# Make backup script executable
chmod +x /opt/novellone/scripts/backup.sh

# Test backup
/opt/novellone/scripts/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /opt/novellone/scripts/backup.sh >> /var/log/novellone-backup.log 2>&1
```

### 3. SSL Certificate Auto-Renewal

Certbot automatically sets up a renewal timer. Verify it:

```bash
# Check certbot timer
systemctl status certbot.timer

# Test renewal (dry run)
certbot renew --dry-run
```

### 4. Log Rotation

Create log rotation config:

```bash
cat > /etc/logrotate.d/novellone << 'EOF'
/opt/novellone/logs/backend/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
EOF
```

## Managing Your Deployment

### Common Commands

```bash
# View service status
systemctl status novellone

# Restart service
systemctl restart novellone

# Stop service
systemctl stop novellone

# Start service
systemctl start novellone

# View service logs
journalctl -u novellone -f

# View container logs
cd /opt/novellone
sudo -u novellone docker compose -f docker-compose.prod.yml logs -f

# View specific container
sudo -u novellone docker compose -f docker-compose.prod.yml logs -f backend
sudo -u novellone docker compose -f docker-compose.prod.yml logs -f frontend
sudo -u novellone docker compose -f docker-compose.prod.yml logs -f db
```

### Updating the Application

Use the provided update script:

```bash
cd /opt/novellone
./scripts/update.sh
```

Or manually:

```bash
cd /opt/novellone

# Pull latest code
sudo -u novellone git pull origin main

# Rebuild images
sudo -u novellone docker compose -f docker-compose.prod.yml build

# Restart with new images
sudo -u novellone docker compose -f docker-compose.prod.yml down
sudo -u novellone docker compose -f docker-compose.prod.yml up -d

# Run migrations
sudo -u novellone docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Database Management

**Backup database:**
```bash
cd /opt/novellone
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U storyuser stories > backup.sql
```

**Restore database:**
```bash
cd /opt/novellone
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T db \
    psql -U storyuser stories
```

**Access database shell:**
```bash
cd /opt/novellone
docker compose -f docker-compose.prod.yml exec db \
    psql -U storyuser stories
```

### Monitoring Resources

```bash
# Docker stats
docker stats

# Disk usage
df -h
docker system df

# Check logs size
du -sh /opt/novellone/logs/

# System resources
htop  # or: top
```

## Troubleshooting

### Application Won't Start

**Check service status:**
```bash
systemctl status novellone
journalctl -u novellone -xe
```

**Check Docker containers:**
```bash
cd /opt/novellone
sudo -u novellone docker compose -f docker-compose.prod.yml ps
sudo -u novellone docker compose -f docker-compose.prod.yml logs
```

**Common issues:**
- Environment variables not set correctly in `.env.production`
- Database password mismatch
- Ports 8000 or 4000 already in use
- Docker not running

### SSL Certificate Issues

**Certificate not obtained:**
```bash
# Check DNS is pointing to your server
dig hurl.lol +short

# Try manual certificate
certbot --nginx -d hurl.lol --manual

# Check nginx config
nginx -t
```

**Certificate renewal failing:**
```bash
# Check renewal
certbot renew --dry-run

# Force renewal
certbot renew --force-renewal
```

### Nginx 502 Bad Gateway

**Causes:**
- Backend containers not running
- Wrong port configuration
- Firewall blocking internal connections

**Fix:**
```bash
# Check containers
docker ps

# Check nginx error logs
tail -f /var/log/nginx/novellone_error.log

# Restart services
systemctl restart novellone
systemctl restart nginx
```

### Database Connection Errors

**Check database container:**
```bash
cd /opt/novellone
docker compose -f docker-compose.prod.yml logs db
```

**Verify DATABASE_URL:**
```bash
# Should be: postgresql+asyncpg://storyuser:PASSWORD@db:5432/stories
cat .env.production | grep DATABASE_URL
```

**Test database connection:**
```bash
docker compose -f docker-compose.prod.yml exec backend python -c \
    "from database import engine; import asyncio; asyncio.run(engine.dispose())"
```

### WebSocket Not Connecting

**Check browser console** for WebSocket errors.

**Verify nginx WebSocket config:**
```bash
# /etc/nginx/sites-available/novellone should have:
# - Upgrade $http_upgrade
# - Connection "upgrade"
# - Long timeouts for /ws/ location

nginx -t
systemctl reload nginx
```

**Test WebSocket endpoint:**
```bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
    https://hurl.lol/ws/stories
```

### Out of Disk Space

**Clean up Docker:**
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# System-wide cleanup
docker system prune -a --volumes
```

**Clean up logs:**
```bash
# Truncate large logs
truncate -s 0 /opt/novellone/logs/backend/backend.log

# Remove old backups
find /opt/novellone/backups -mtime +30 -delete
```

## Security Best Practices

### 1. Firewall Configuration

```bash
# Only allow necessary ports
ufw status
# Should show: 22 (SSH), 80 (HTTP), 443 (HTTPS)

# Block all other incoming
ufw default deny incoming
ufw default allow outgoing
```

### 2. SSH Hardening

```bash
# Disable password authentication (use SSH keys)
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no

systemctl restart sshd
```

### 3. Keep System Updated

```bash
# Regular updates
apt-get update && apt-get upgrade -y

# Automatic security updates
apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

### 4. Monitor Access Logs

```bash
# Nginx access logs
tail -f /var/log/nginx/novellone_access.log

# Failed SSH attempts
grep "Failed password" /var/log/auth.log
```

### 5. Environment Security

```bash
# Ensure .env.production is not readable by others
chmod 600 /opt/novellone/.env.production
chown novellone:novellone /opt/novellone/.env.production

# Never commit to git
echo ".env.production" >> /opt/novellone/.gitignore
```

## Performance Optimization

### 1. Enable Docker BuildKit

```bash
export DOCKER_BUILDKIT=1
# Add to /etc/environment for persistence
```

### 2. Configure Nginx Caching

Add to nginx config:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;
```

### 3. Adjust Story Generation Parameters

Via `/config` or `.env.production`:
- Increase `CHAPTER_INTERVAL_SECONDS` to reduce API calls
- Decrease `MAX_ACTIVE_STORIES` on smaller VPS
- Adjust `WORKER_TICK_INTERVAL` based on load

### 4. Monitor and Limit Resources

```bash
# Set Docker memory limits in docker-compose.prod.yml
# Add under services:
#   backend:
#     mem_limit: 1g
#     cpus: 1.0
```

## Cost Estimation

Typical VPS costs:

| Provider | Plan | RAM | Storage | Price/mo |
|----------|------|-----|---------|----------|
| DigitalOcean | Basic | 2GB | 50GB SSD | $12 |
| Linode | Nanode | 1GB | 25GB SSD | $5 |
| Vultr | Cloud Compute | 2GB | 55GB SSD | $12 |
| Hetzner | CX21 | 4GB | 40GB SSD | €4.90 |

Plus OpenAI API costs (depends on usage).

## Monitoring and Alerts

### Set Up Uptime Monitoring

Use external services:
- [UptimeRobot](https://uptimerobot.com/) (free)
- [Pingdom](https://www.pingdom.com/)
- [StatusCake](https://www.statuscake.com/)

Monitor endpoint: `https://hurl.lol/api/health`

### Log Monitoring

```bash
# Watch for errors in real-time
journalctl -u novellone -f | grep -i error

# Count errors
journalctl -u novellone --since today | grep -i error | wc -l
```

## Backup and Recovery

### Full System Backup

1. **Database backup** (automated via cron)
2. **Environment file**: `/opt/novellone/.env.production`
3. **Nginx config**: `/etc/nginx/sites-available/novellone`
4. **SSL certificates**: `/etc/letsencrypt/`

### Disaster Recovery

```bash
# On new VPS, restore from backup:
1. Run deploy.sh
2. Restore .env.production
3. Restore database: cat backup.sql | docker compose exec -T db psql...
4. Restart services
```

## CI/CD Setup (Optional)

For automated deployments from GitHub:

### 1. Set Up GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: novellone
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/novellone
            ./scripts/update.sh
```

### 2. Add GitHub Secrets

In GitHub repo settings:
- `VPS_HOST`: Your VPS IP
- `SSH_PRIVATE_KEY`: SSH key for novellone user

## Support

- Check logs first: `journalctl -u novellone -f`
- Review docker logs: `docker compose logs`
- Test health endpoint: `curl https://hurl.lol/api/health`

---

Enjoy your autonomous storytelling platform at https://hurl.lol! 🚀📚

