# VPS Deployment Guide

This guide will help you deploy Novellone on a VPS (Virtual Private Server) with nginx as a reverse proxy.

## Prerequisites

- Ubuntu 22.04 or similar Linux distribution
- Root or sudo access
- Domain name pointing to your VPS IP address
- At least 2GB RAM recommended

## 1. Initial Server Setup

### Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages
```bash
sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx git
```

### Enable Docker service
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### Add your user to docker group (optional, to run docker without sudo)
```bash
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

## 2. Clone and Configure Application

### Clone repository
```bash
cd /opt
sudo git clone <your-repo-url> novellone
cd novellone
sudo chown -R $USER:$USER /opt/novellone
```

### Create environment file
```bash
cp .env.example .env
nano .env
```

**Important environment variables for VPS:**
```bash
# Replace with your actual domain
PUBLIC_API_URL=https://your-domain.com/api
PUBLIC_WS_URL=wss://your-domain.com/ws/stories

# Or for initial HTTP setup:
# PUBLIC_API_URL=http://your-domain.com/api
# PUBLIC_WS_URL=ws://your-domain.com/ws/stories

# Security settings
ADMIN_PASSWORD=<strong-password-here>
SESSION_SECRET=<generate-random-secret>
SESSION_COOKIE_SECURE=true  # Set to true after SSL setup
SESSION_COOKIE_DOMAIN=your-domain.com
DB_PASSWORD=<strong-database-password>

# OpenAI
OPENAI_API_KEY=<your-openai-key>
```

**Generate secure secrets:**
```bash
# Generate SESSION_SECRET
openssl rand -base64 32

# Generate DB_PASSWORD
openssl rand -base64 24
```

## 3. Configure Nginx

### Copy nginx configuration
```bash
sudo cp /opt/novellone/nginx.conf /etc/nginx/sites-available/novellone
```

### Edit the configuration with your domain
```bash
sudo nano /etc/nginx/sites-available/novellone
# Replace 'your-domain.com' with your actual domain
```

### Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/novellone /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

### Test nginx configuration
```bash
sudo nginx -t
```

### Reload nginx
```bash
sudo systemctl reload nginx
```

## 4. Start Application with Docker Compose

### Build and start services
```bash
cd /opt/novellone
docker-compose up -d
```

### Check logs
```bash
docker-compose logs -f
```

### Verify services are running
```bash
docker-compose ps
```

You should see:
- backend (port 8000)
- frontend (port 3000)
- db (PostgreSQL)

## 5. SSL Certificate Setup (HTTPS)

### Obtain SSL certificate with Certbot
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts:
- Enter your email address
- Agree to terms of service
- Choose whether to redirect HTTP to HTTPS (recommended: yes)

### Certbot will automatically:
- Obtain the certificate
- Update nginx configuration
- Set up auto-renewal

### Verify auto-renewal
```bash
sudo certbot renew --dry-run
```

### Update nginx configuration for SSL
After obtaining certificates, edit `/etc/nginx/sites-available/novellone`:

1. Comment out the HTTP-only listeners (port 80)
2. Uncomment the HTTPS listeners (port 443)
3. Uncomment SSL certificate paths
4. Uncomment SSL configuration options
5. Uncomment the HTTP redirect server block

```bash
sudo nano /etc/nginx/sites-available/novellone
sudo nginx -t
sudo systemctl reload nginx
```

### Update environment variables for HTTPS
```bash
nano /opt/novellone/.env
```

Update:
```bash
PUBLIC_API_URL=https://your-domain.com/api
PUBLIC_WS_URL=wss://your-domain.com/ws/stories
SESSION_COOKIE_SECURE=true
```

Restart services:
```bash
docker-compose down
docker-compose up -d
```

## 6. Firewall Configuration

### Configure UFW (Uncomplicated Firewall)
```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status
```

## 7. Monitoring and Maintenance

### View application logs
```bash
cd /opt/novellone
docker-compose logs -f backend
docker-compose logs -f frontend
```

### View nginx logs
```bash
sudo tail -f /var/log/nginx/novellone_access.log
sudo tail -f /var/log/nginx/novellone_error.log
```

### Restart services
```bash
cd /opt/novellone
docker-compose restart
```

### Update application
```bash
cd /opt/novellone
git pull
docker-compose build
docker-compose up -d
```

### Database backup
```bash
docker-compose exec db pg_dump -U storyuser stories > backup_$(date +%Y%m%d).sql
```

### Database restore
```bash
cat backup_20240101.sql | docker-compose exec -T db psql -U storyuser stories
```

## 8. System Service (Optional)

Create a systemd service to auto-start on boot:

```bash
sudo nano /etc/systemd/system/novellone.service
```

```ini
[Unit]
Description=Novellone Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/novellone
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=root

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable novellone
sudo systemctl start novellone
```

## 9. Troubleshooting

### Application not responding
```bash
# Check if containers are running
docker-compose ps

# Restart containers
docker-compose restart

# Check logs for errors
docker-compose logs -f
```

### 502 Bad Gateway from nginx
```bash
# Check if backend/frontend are listening
docker-compose ps
netstat -tlnp | grep -E ':(8000|3000)'

# Check nginx error logs
sudo tail -f /var/log/nginx/novellone_error.log
```

### Database connection errors
```bash
# Check if database is healthy
docker-compose exec db pg_isready -U storyuser

# Verify DATABASE_URL in .env matches docker-compose.yml
```

### WebSocket connection fails
- Ensure nginx WebSocket configuration is correct
- Check that `/ws/` location block has `proxy_set_header Upgrade` and `Connection "upgrade"`
- Verify PUBLIC_WS_URL uses `wss://` (for HTTPS) or `ws://` (for HTTP)

### Favicon 404 errors
- Clear browser cache
- Verify `/frontend/static/favicon.svg` exists
- Restart frontend: `docker-compose restart frontend`

## 10. Performance Optimization

### Enable gzip compression in nginx
Add to the `http` block in `/etc/nginx/nginx.conf`:
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
```

### Increase nginx worker connections
Edit `/etc/nginx/nginx.conf`:
```nginx
events {
    worker_connections 2048;
}
```

### Docker resource limits
Edit `docker-compose.yml` to add resource limits:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

## 11. Security Checklist

- [ ] Strong passwords set for ADMIN_PASSWORD and DB_PASSWORD
- [ ] SESSION_SECRET is random and secure
- [ ] SSL/HTTPS configured with Let's Encrypt
- [ ] Firewall (UFW) enabled and configured
- [ ] SSH key authentication enabled (password auth disabled)
- [ ] Regular system updates scheduled
- [ ] Database backups automated
- [ ] Nginx security headers enabled
- [ ] Docker containers running as non-root (where possible)
- [ ] Environment files (.env) have restricted permissions: `chmod 600 .env`

## Support

For issues or questions:
- Check application logs: `docker-compose logs -f`
- Check nginx logs: `sudo tail -f /var/log/nginx/novellone_error.log`
- Review this documentation
- Check the main README.md for application-specific details
