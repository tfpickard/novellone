#!/bin/bash
# Backup script for Eternal Stories database
# Add to crontab for automated backups:
#   0 2 * * * /opt/novellone/scripts/backup.sh

set -e

APP_DIR="/opt/novellone"
BACKUP_DIR="$APP_DIR/backups"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

echo "Creating database backup..."

# Create backup
cd "$APP_DIR"
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U storyuser stories | gzip > "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# Remove old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Get backup size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup size: $SIZE"

# Count remaining backups
COUNT=$(ls -1 "$BACKUP_DIR"/db_backup_*.sql.gz | wc -l)
echo "Total backups: $COUNT"

