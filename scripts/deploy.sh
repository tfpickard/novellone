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
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    curl \
    ufw

# Install Caddy
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

# Start and enable services
systemctl start docker
systemctl enable docker
systemctl enable caddy

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
echo -e "${GREEN}Step 7: Setting up Caddy...${NC}"
if [ ! -f "/etc/caddy/Caddyfile" ]; then
    # Backup original Caddyfile if it exists
    [ -f "/etc/caddy/Caddyfile" ] && mv /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup
    
    # Install our Caddyfile
    cp "$APP_DIR/Caddyfile" /etc/caddy/Caddyfile
    
    echo "Caddyfile installed"
else
    echo "Caddyfile already exists, updating..."
    cp "$APP_DIR/Caddyfile" /etc/caddy/Caddyfile
fi

# Set permissions
chown root:root /etc/caddy/Caddyfile
chmod 644 /etc/caddy/Caddyfile

# Create log directory
mkdir -p /var/log/caddy
chown caddy:caddy /var/log/caddy

# Test Caddy config
caddy validate --config /etc/caddy/Caddyfile

echo ""
echo -e "${GREEN}Step 8: Setting up firewall...${NC}"
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw status

echo ""
echo -e "${GREEN}Step 9: Starting Caddy (SSL auto-configured)...${NC}"
# Caddy automatically obtains SSL certificates on first start
systemctl restart caddy

# Wait a moment for Caddy to obtain certificates
echo "Waiting for Caddy to obtain SSL certificates..."
sleep 5

# Check Caddy status
systemctl status caddy --no-pager || echo -e "${YELLOW}Check Caddy logs: journalctl -u caddy -f${NC}"

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
echo "  Restart Caddy:      sudo systemctl restart caddy"
echo "  View Caddy logs:    sudo journalctl -u caddy -f"
echo "  View container logs: cd $APP_DIR && sudo -u $APP_USER docker compose -f docker-compose.prod.yml logs -f"
echo "  Update deployment:  cd $APP_DIR && sudo ./scripts/update.sh"
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  1. Review and secure $APP_DIR/.env.production"
echo "  2. Configure backups for PostgreSQL database (see scripts/backup.sh)"
echo "  3. Monitor Caddy logs for any SSL issues"
echo ""
echo -e "${GREEN}Caddy will automatically:${NC}"
echo "  - Obtain SSL certificates from Let's Encrypt"
echo "  - Renew certificates before expiration"
echo "  - Redirect HTTP to HTTPS"
echo ""

