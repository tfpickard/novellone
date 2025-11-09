#!/bin/bash
# Update script for Eternal Stories
# Run this on your VPS to pull latest changes and redeploy

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_DIR="/opt/novellone"
APP_USER="novellone"

echo -e "${GREEN}Eternal Stories - Update Deployment${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

cd "$APP_DIR"

echo -e "${GREEN}Step 1: Backing up current state...${NC}"
BACKUP_DIR="$APP_DIR/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U storyuser stories > "$BACKUP_DIR/database_backup.sql" \
    || echo -e "${YELLOW}Warning: Could not backup database${NC}"
echo "Backup saved to: $BACKUP_DIR"

echo ""
echo -e "${GREEN}Step 2: Pulling latest code...${NC}"
sudo -u "$APP_USER" git fetch origin
sudo -u "$APP_USER" git pull origin main

echo ""
echo -e "${GREEN}Step 3: Rebuilding Docker images...${NC}"
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml build

echo ""
echo -e "${GREEN}Step 4: Restarting services...${NC}"
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml down
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml up -d

echo ""
echo -e "${GREEN}Step 5: Running migrations...${NC}"
sleep 5
sudo -u "$APP_USER" docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

echo ""
echo -e "${GREEN}Step 6: Cleaning up old images...${NC}"
docker image prune -f

echo ""
echo -e "${GREEN}Update complete!${NC}"
echo ""
echo "View logs with: sudo -u $APP_USER docker compose -f $APP_DIR/docker-compose.prod.yml logs -f"

