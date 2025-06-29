#!/bin/bash

echo "🚀 Starte Scandy mit automatischem Backup..."
echo "=========================================="

# Prüfe ob wir im Projektverzeichnis sind
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ ERROR: docker-compose.yml nicht gefunden!"
    echo "Bitte führen Sie dieses Script im Projektverzeichnis aus."
    exit 1
fi

# Erstelle Backup vor dem Start
echo "📦 Erstelle Backup vor dem Start..."
if [ -f "backup.sh" ]; then
    ./backup.sh
    echo "✅ Backup erstellt"
else
    echo "⚠️  Backup-Script nicht gefunden, überspringe Backup"
fi

echo ""
echo "🚀 Starte Container..."
docker-compose up -d

echo ""
echo "⏳ Warte auf Container-Start..."
sleep 15

echo ""
echo "📊 Container-Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ Scandy gestartet!"
echo "=========================================="
echo "Scandy: http://localhost:5000"
echo "Mongo Express: http://localhost:8081"
echo "=========================================="
echo "" 