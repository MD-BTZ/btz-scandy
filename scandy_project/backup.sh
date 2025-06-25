#!/bin/bash
BACKUP_DIR="./scandy_data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Erstelle Backup..."

# Erstelle Backup-Verzeichnis
mkdir -p "$BACKUP_DIR"

# MongoDB Backup
echo "Backup MongoDB..."
docker exec scandy-mongodb mongodump --out /tmp/backup
docker cp scandy-mongodb:/tmp/backup "$BACKUP_DIR/mongodb_$TIMESTAMP"

# App-Daten Backup
echo "Backup App-Daten..."
tar -czf "$BACKUP_DIR/app_data_$TIMESTAMP.tar.gz" -C ./scandy_data uploads backups logs

echo "Backup erstellt: $BACKUP_DIR"
