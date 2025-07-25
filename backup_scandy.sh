#!/bin/bash

# Scandy Backup Skript
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="scandy_backup_$DATE"

echo "Erstelle Backup: $BACKUP_NAME"

# Erstelle Backup-Verzeichnis
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup MongoDB
mongodump --db scandy --out "$BACKUP_DIR/$BACKUP_NAME/mongodb"

# Backup Uploads
cp -r app/uploads "$BACKUP_DIR/$BACKUP_NAME/"

# Backup Konfiguration
cp .env "$BACKUP_DIR/$BACKUP_NAME/"

# Erstelle Archiv
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo "Backup erstellt: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
