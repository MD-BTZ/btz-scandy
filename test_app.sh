#!/bin/bash

echo "🚀 Starte Scandy Test-Version..."
echo "=================================="

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ist nicht gestartet!"
    exit 1
fi

# Stoppe und entferne alte Test-Container falls vorhanden
echo "🧹 Räume alte Test-Container auf..."
docker-compose -f docker-compose.test.yml down -v 2>/dev/null

# Baue das neue Image
echo "🔨 Baue neues Docker-Image..."
docker-compose -f docker-compose.test.yml build

# Starte die Test-Container
echo "🚀 Starte Test-Container..."
docker-compose -f docker-compose.test.yml up -d

# Warte bis MongoDB bereit ist
echo "⏳ Warte auf MongoDB..."
sleep 10

# Prüfe Container-Status
echo "📊 Container-Status:"
docker-compose -f docker-compose.test.yml ps

# Prüfe Logs
echo "📋 Letzte Logs der Scandy-App:"
docker-compose -f docker-compose.test.yml logs --tail=20 scandy-test

echo ""
echo "✅ Test-Version ist bereit!"
echo "🌐 Zugriff: http://localhost:5002"
echo "🗄️ MongoDB: localhost:27019"
echo ""
echo "📝 Nützliche Befehle:"
echo "  Logs anzeigen: docker-compose -f docker-compose.test.yml logs -f scandy-test"
echo "  Container stoppen: docker-compose -f docker-compose.test.yml down"
echo "  Container neu starten: docker-compose -f docker-compose.test.yml restart"
echo ""
echo "🔍 Teste die Anwendung und prüfe ob alle Funktionen funktionieren!" 