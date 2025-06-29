#!/bin/bash

echo "📦 Scandy Backup"
echo "================"

# Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker läuft nicht. Backup nicht möglich."
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
    exit 1
fi

cd "$PROJECT_DIR"

echo "✅ Projekt gefunden: $PROJECT_DIR"

# Erstelle Backup-Verzeichnis
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Erstelle Zeitstempel
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="scandy_backup_$TIMESTAMP"
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
fi

echo ""
echo "📁 Kopiere Dateien..."

# Kopiere wichtige Verzeichnisse
if [[ -d "data/uploads" ]]; then
    echo "- Upload-Dateien..."
    cp -r "data/uploads" "$BACKUP_PATH/"
fi

if [[ -d "data/backups" ]]; then
    echo "- Backup-Dateien..."
    cp -r "data/backups" "$BACKUP_PATH/"
fi

if [[ -d "data/logs" ]]; then
    echo "- Log-Dateien..."
    cp -r "data/logs" "$BACKUP_PATH/"
fi

if [[ -d "data/static" ]]; then
    echo "- Statische Dateien..."
    cp -r "data/static" "$BACKUP_PATH/"
fi

echo ""
echo "📋 Erstelle Backup-Info..."

# Erstelle Backup-Info
cat > "$BACKUP_PATH/backup_info.txt" << EOF
Backup erstellt am: $(date)
Projekt: $PROJECT_DIR
Zeitstempel: $TIMESTAMP

Enthaltene Daten:
EOF

if [[ -f "$BACKUP_PATH/mongodb_backup.archive" ]]; then
    echo "- MongoDB-Datenbank" >> "$BACKUP_PATH/backup_info.txt"
fi
if [[ -d "$BACKUP_PATH/uploads" ]]; then
    echo "- Upload-Dateien" >> "$BACKUP_PATH/backup_info.txt"
fi
if [[ -d "$BACKUP_PATH/backups" ]]; then
    echo "- Backup-Dateien" >> "$BACKUP_PATH/backup_info.txt"
fi
if [[ -d "$BACKUP_PATH/logs" ]]; then
    echo "- Log-Dateien" >> "$BACKUP_PATH/backup_info.txt"
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
    exit 1
fi

# Lösche temporäres Verzeichnis
rm -rf "$BACKUP_PATH"

echo ""
echo "✅ Backup erfolgreich erstellt!"
echo "📁 Backup-Datei: $BACKUP_PATH.tar.gz"
echo "📏 Größe: $(du -h "$BACKUP_PATH.tar.gz" | cut -f1)"

echo ""
echo "📋 Backup-Inhalt:"
if [[ -f "$BACKUP_PATH.tar.gz" ]]; then
    echo "- MongoDB-Datenbank (falls verfügbar)"
    echo "- Upload-Dateien"
    echo "- Backup-Dateien"
    echo "- Log-Dateien"
    echo "- Statische Dateien"
    echo "- Backup-Informationen"
fi

echo ""
echo "💡 Tipp: Bewahren Sie das Backup an einem sicheren Ort auf!"
echo "" 