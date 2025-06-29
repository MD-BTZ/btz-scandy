#!/bin/bash

echo "📦 Automatisches Scandy Backup"
echo "============================="
echo "Zeit: $(date)"
echo ""

# Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker läuft nicht. Backup nicht möglich."
    echo "Backup fehlgeschlagen: $(date) - Docker nicht verfügbar" >> auto_backup.log
    exit 1
fi

# Finde Projekt-Verzeichnis
PROJECT_DIR=""
for dir in *_project; do
    if [[ -d "$dir" && -f "$dir/docker-compose.yml" ]]; then
        PROJECT_DIR="$dir"
        break
    fi
done

if [[ -z "$PROJECT_DIR" ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "Backup fehlgeschlagen: $(date) - Keine Installation gefunden" >> auto_backup.log
    exit 1
fi

cd "$PROJECT_DIR"

echo "✅ Projekt gefunden: $PROJECT_DIR"

# Erstelle Backup-Verzeichnis
BACKUP_DIR="backups/auto"
mkdir -p "$BACKUP_DIR"

# Erstelle Zeitstempel
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="auto_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo "📅 Backup-Zeitstempel: $TIMESTAMP"
echo "📁 Backup-Pfad: $BACKUP_PATH"

# Erstelle Backup-Verzeichnis
mkdir -p "$BACKUP_PATH"

echo ""
echo "🔄 Erstelle Datenbank-Backup..."

# MongoDB Backup
echo "- MongoDB-Daten..."
if docker-compose exec -T scandy-mongodb mongodump --username admin --password scandy123 --authenticationDatabase admin --db scandy --archive > "$BACKUP_PATH/mongodb_backup.archive" 2>/dev/null; then
    echo "✅ MongoDB-Backup erstellt"
else
    echo "⚠️  MongoDB-Backup fehlgeschlagen (Container läuft möglicherweise nicht)"
    echo "Backup fehlgeschlagen: $(date) - MongoDB-Backup fehlgeschlagen" >> auto_backup.log
    exit 1
fi

echo ""
echo "📁 Kopiere wichtige Dateien..."

# Kopiere wichtige Verzeichnisse (nur kritische Daten)
if [[ -d "data/uploads" ]]; then
    echo "- Upload-Dateien..."
    cp -r "data/uploads" "$BACKUP_PATH/"
fi

if [[ -d "data/static" ]]; then
    echo "- Statische Dateien..."
    cp -r "data/static" "$BACKUP_PATH/"
fi

echo ""
echo "📋 Erstelle Backup-Info..."

# Erstelle Backup-Info
cat > "$BACKUP_PATH/backup_info.txt" << EOF
Automatisches Backup erstellt am: $(date)
Projekt: $PROJECT_DIR
Zeitstempel: $TIMESTAMP
Typ: Automatisches Backup

Enthaltene Daten:
EOF

if [[ -f "$BACKUP_PATH/mongodb_backup.archive" ]]; then
    echo "- MongoDB-Datenbank" >> "$BACKUP_PATH/backup_info.txt"
fi
if [[ -d "$BACKUP_PATH/uploads" ]]; then
    echo "- Upload-Dateien" >> "$BACKUP_PATH/backup_info.txt"
fi
if [[ -d "$BACKUP_PATH/static" ]]; then
    echo "- Statische Dateien" >> "$BACKUP_PATH/backup_info.txt"
fi

echo ""
echo "📦 Erstelle komprimiertes Backup..."

# Erstelle TAR-Archiv
if tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_PATH" .; then
    echo "✅ Komprimiertes Backup erstellt"
else
    echo "❌ Fehler beim Erstellen des TAR-Archivs!"
    echo "Backup fehlgeschlagen: $(date) - TAR-Erstellung fehlgeschlagen" >> auto_backup.log
    exit 1
fi

# Lösche temporäres Verzeichnis
rm -rf "$BACKUP_PATH"

echo ""
echo "✅ Automatisches Backup erfolgreich erstellt!"
echo "📁 Backup-Datei: $BACKUP_PATH.tar.gz"

# Logge erfolgreiches Backup
echo "Backup erfolgreich: $(date) - $BACKUP_PATH.tar.gz" >> auto_backup.log

# Lösche alte automatische Backups (behalte nur die letzten 14)
echo ""
echo "🧹 Bereinige alte automatische Backups..."
COUNT=0
for file in $(ls -t "$BACKUP_DIR"/auto_backup_*.tar.gz 2>/dev/null); do
    ((COUNT++))
    if [[ $COUNT -gt 14 ]]; then
        echo "Lösche altes Backup: $(basename "$file")"
        rm -f "$file"
    fi
done

echo ""
echo "📊 Backup-Statistik:"
echo "- Neue Backups: 1"
echo "- Behaltene Backups: 14 (7 Tage × 2x täglich)"
echo "- Gesamtgröße: $(du -h "$BACKUP_PATH.tar.gz" | cut -f1)"

echo ""
echo "✅ Automatisches Backup abgeschlossen!"
exit 0 