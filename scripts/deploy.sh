#!/bin/bash
# Initial deployment script for Eternal Stories on VPS
# Run this script on your VPS to set up the application for the first time

set -e

echo "========================================"
echo "Eternal Stories VPS Deployment"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_USER="novellone"
APP_DIR="/opt/novellone"
DOMAIN="hurl.lol"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    git \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    curl \
    ufw

# Start and enable Docker
systemctl start docker
systemctl enable docker

echo ""
echo -e "${GREEN}Step 2: Creating application user...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash "$APP_USER"
    usermod -aG docker "$APP_USER"
    echo "Created user: $APP_USER"
else
    echo "User $APP_USER already exists"
fi

echo ""
echo -e "${GREEN}Step 3: Setting up application directory...${NC}"
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    echo "Created directory: $APP_DIR"
fi

# Check if git repo exists
if [ ! -d "$APP_DIR/.git" ]; then
    echo -e "${YELLOW}Please enter your git repository URL:${NC}"
    read -r GIT_REPO
    sudo -u "$APP_USER" git clone "$GIT_REPO" "$APP_DIR"
else
    echo "Git repository already exists"
fi

# Set ownership
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo ""
echo -e "${GREEN}Step 4: Setting up environment file...${NC}"
if [ ! -f "$APP_DIR/.env.production" ]; then
    echo -e "${YELLOW}Copying environment template...${NC}"
    cp "$APP_DIR/env.production.example" "$APP_DIR/.env.production"
    echo -e "${RED}IMPORTANT: Edit $APP_DIR/.env.production with your actual values!${NC}"
    echo "Press Enter to edit now (nano will open)..."
    read -r
    nano "$APP_DIR/.env.production"
else
    echo ".env.production already exists"
fi

echo ""
echo -e "${GREEN}Step 5: Creating log directory...${NC}"
mkdir -p "$APP_DIR/logs/backend"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/logs"

echo ""
echo -e "${GREEN}Step 6: Building Docker images...${NC}"
cd "$APP_DIR"
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml build

echo ""
echo -e "${GREEN}Step 7: Setting up nginx...${NC}"
if [ ! -f "/etc/nginx/sites-available/novellone" ]; then
    cp "$APP_DIR/nginx/novellone.conf" /etc/nginx/sites-available/novellone
    
    # Remove SSL lines temporarily (before we have certificates)
    sed -i 's/ssl_certificate/#ssl_certificate/g' /etc/nginx/sites-available/novellone
    sed -i 's/ssl_trusted/#ssl_trusted/g' /etc/nginx/sites-available/novellone
    sed -i 's/ssl_stapling/#ssl_stapling/g' /etc/nginx/sites-available/novellone
    sed -i 's/listen 443/#listen 443/g' /etc/nginx/sites-available/novellone
    
    ln -sf /etc/nginx/sites-available/novellone /etc/nginx/sites-enabled/
    
    # Remove default site if exists
    rm -f /etc/nginx/sites-enabled/default
    
    echo "Nginx configuration installed"
else
    echo "Nginx configuration already exists"
fi

# Test nginx config
nginx -t

echo ""
echo -e "${GREEN}Step 8: Setting up firewall...${NC}"
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw status

echo ""
echo -e "${GREEN}Step 9: Obtaining SSL certificate...${NC}"
# Restart nginx to serve HTTP for ACME challenge
systemctl restart nginx

# Get certificate
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --redirect \
    || echo -e "${YELLOW}Certificate generation failed. You may need to run: sudo certbot --nginx -d $DOMAIN${NC}"

# Restore full nginx config with SSL
cp "$APP_DIR/nginx/novellone.conf" /etc/nginx/sites-available/novellone
nginx -t && systemctl reload nginx

echo ""
echo -e "${GREEN}Step 10: Setting up systemd service...${NC}"
cp "$APP_DIR/systemd/novellone.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable novellone
systemctl start novellone

echo ""
echo -e "${GREEN}Step 11: Verifying deployment...${NC}"
sleep 10
systemctl status novellone --no-pager

echo ""
echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Your application should now be running at: https://$DOMAIN"
echo ""
echo "Useful commands:"
echo "  View logs:          sudo journalctl -u novellone -f"
echo "  Restart service:    sudo systemctl restart novellone"
echo "  View container logs: cd $APP_DIR && sudo -u $APP_USER docker compose -f docker-compose.prod.yml logs -f"
echo "  Update deployment:  cd $APP_DIR && sudo ./scripts/update.sh"
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  1. Review and secure $APP_DIR/.env.production"
echo "  2. Set up automated certificate renewal (certbot does this automatically)"
echo "  3. Configure backups for PostgreSQL database"
echo ""

