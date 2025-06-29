#!/bin/bash

echo "🚀 Scandy mit Backup-Prüfung starten"
echo "===================================="

# Prüfe ob wir im richtigen Verzeichnis sind
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "Führen Sie zuerst install.sh aus."
    exit 1
fi

echo "✅ Scandy-Installation gefunden"

# Starte Container
echo ""
echo "🔄 Starte Scandy Container..."
docker-compose up -d

if [[ $? -ne 0 ]]; then
    echo "❌ Fehler beim Starten der Container!"
    exit 1
fi

echo ""
echo "✅ Container erfolgreich gestartet!"
echo ""
echo "📋 Container-Status:"
docker-compose ps

echo ""
echo "🌐 Scandy ist verfügbar unter: http://localhost:5000"
echo ""

# Prüfe automatische Backups
echo "🔍 Prüfe automatische Backup-Einrichtung..."
./check-backup-setup.sh

echo ""
echo "✅ Scandy ist bereit!"
echo "" 